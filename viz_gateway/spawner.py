# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The pool of local backends: one instance per user, its budget, its health.

A `local` user is one process of the run the gateway itself already knows -- a
`python3 -m viz_web` bound to one loopback port and given its own HOME, which
is what isolates its `$HOME/.imasviz` (its reports, its preferences, its
shots) and its `Viz_API` and its `QVizDBEntryRegistry` from every other user's.
A remote user is a URL the gateway reaches by name, and it is not in this pool
at all: the proxy resolves it straight to its `entry['url']`.

Two things of the pool are load-bearing:

* a user is not started twice. `ensure` reuses the one instance that user
  already holds, and the port it chose the first time.
* a user is not kept live without a call. After `idleTimeout` of inactivity
  the instance is stopped, its port released, and the budget it held given
  back. The token still names the user -- the next call starts a fresh
  instance behind it, and nothing tells the difference to the caller.

The `spawn` and `health` asks are injectable, so a test can run the pool's
whole budget and reaping logic against a fake that never starts a process.
"""

# the real spawn; tests inject their own `spawn` and `health`

import os
import threading
import time
import subprocess

from viz_gateway.ports import freePort


class Instance:
    """One live backend and the moment it was last asked for something."""

    __slots__ = ('user', 'entry', 'port', 'url', 'handle', 'lastActive',
                 'running')

    def __init__(self, user, entry, port, url, handle, startedAt):
        self.user = user
        self.entry = entry
        self.port = port
        self.url = url
        self.handle = handle
        self.lastActive = startedAt
        self.running = True


def spawnEnv(entry):
    """The environment a local backend starts with: this gateway's, but its own HOME.

    `HOME` is the isolation: it is what the run's reports, preferences and
    shots are written under, and each user has one of its own. Moving it,
    though, moves the interpreter's own user-site packages (starlette,
    uvicorn, PySide6, the IMAS HLI on this node all live in one) out of reach,
    so they are put back on `PYTHONPATH`: every path this gateway sees that is
    not under the child's HOME. The child then imports what the parent
    imported, and the two still cannot see one another's `$HOME/.imasviz`,
    which is where the isolation has to live.
    """
    import sys

    env = dict(os.environ)
    home = os.path.abspath(os.path.expanduser(entry['home']))
    env['HOME'] = home
    env.setdefault('QT_QPA_PLATFORM', 'offscreen')
    keep = []
    for dirName in sys.path:
        if not dirName:
            continue
        real = os.path.abspath(dirName)
        if not os.path.isdir(real):
            continue
        if real == home or real.startswith(home + os.sep):
            continue
        if real not in keep:
            keep.append(real)
    inherited = os.environ.get('PYTHONPATH', '')
    parts = [p for p in (inherited.split(os.pathsep) if inherited else []) if p]
    env['PYTHONPATH'] = os.pathsep.join(parts + keep)
    return env


def spawnVizWeb(user, entry, port, env, max_turns=12):
    """One live `viz_web` on its port, in `env`. Returns the process handle.

    --max-turns is forwarded to the child: the child's default (12) is the
    same as here, so an operator who does not set either gets the same loop
    limit whether or not there is a gateway.
    """
    command = ['python3', '-m', 'viz_web',
               '--host', '127.0.0.1', '--port', str(port), '--offscreen',
               '--max-turns', str(max_turns)]
    return subprocess.Popen(command, env=env)


def pollHealth(url, handle, timeout=90.0):
    """Wait for the backend at `url` to answer `/api/health`, or refuse by name.

    A process that dies before it is ready -- named by its exit code -- and a
    process that comes up but does not answer in `timeout` -- both are raised
    with the words that name them. This is the one that makes the pool refuse
    a user whose backend did not come up, rather than hand out a URL that 404s.
    """
    import httpx

    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        if handle is not None:
            poll = getattr(handle, 'poll', None)
            if callable(poll) and poll() is not None:
                code = getattr(handle, 'returncode', '?')
                raise ValueError(
                    'the backend at %s died before it was ready, answered %s -- '
                    'check the module the operator loaded and the HOME %r it was '
                    'given.' % (url, code, getattr(handle, 'home', '?')))
        try:
            client = httpx.Client(timeout=2.0)
            try:
                answer = client.get(url + '/api/health')
            finally:
                client.close()
            if answer.status_code == 200:
                return
            last = '%s %s' % (answer.status_code, answer.text[:120])
        except Exception as exc:  # not up yet, or the socket not open
            last = '%s: %s' % (type(exc).__name__, exc)
        time.sleep(0.3)
    raise ValueError(
        'the backend at %s did not answer /api/health within %.0f s: %s'
        % (url, timeout, last))


class Pool:
    """The live instances of the local users of one gateway.

    The one the gateway answers every `local` user through. `spawn` and
    `health` are injected where a test wants the pool to run its budget and
    reaping without starting a process; the defaults start a `viz_web` and
    wait for it to answer.
    """

    def __init__(self, spawn=None, health=None, idleTimeout=1800,
                 maxUsers=20, host='127.0.0.1', maxTurns=12,
                 clock=time.monotonic):
        if maxUsers < 1:
            raise ValueError('a pool holds at least one user; its max is %d.'
                             % maxUsers)
        self._maxTurns = maxTurns
        self._spawn = spawn or spawnVizWeb
        self._health = health if health is not None else pollHealth
        self._idleTimeout = idleTimeout
        self._maxUsers = maxUsers
        self._host = host
        self._clock = clock
        self._instances = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ asks

    def ensure(self, user, entry):
        """The base URL of the instance `user` runs behind, starting it if absent.

        Reuses the one already up, else starts it on a fresh loopback port,
        waits for it to answer, and remembers it. A pool at its budget refuses
        the next user by name. Returns the base URL -- what the proxy reaches
        -- not the process.
        """
        with self._lock:
            now = self._clock()
            live = self._live()
            existing = self._instances.get(user)
            if existing is not None and existing.running:
                existing.lastActive = now
                return existing.url
            if len(live) >= self._maxUsers:
                raise ValueError(
                    'the pool is full: %d instance(s) are live and its budget '
                    'is %d. Stop one, or raise --max-users.'
                    % (len(live), self._maxUsers))
            port = freePort(self._host)
            url = 'http://%s:%d' % (self._host, port)
            handle = self._spawn(user, entry, port, spawnEnv(entry),
                                 self._maxTurns)
            self._health(url, handle)
            self._instances[user] = Instance(user, entry, port, url, handle,
                                             now)
            return url

    def touch(self, user):
        """A call came in for `user`: its instance's inactivity clock resets."""
        with self._lock:
            inst = self._instances.get(user)
            if inst is not None and inst.running:
                inst.lastActive = self._clock()

    def reapIdle(self):
        """The users idle for longer than the budget, stopped by name.

        Returns the user names it stopped, in the order it read them. A live
        instance a user touched recently is left alone.
        """
        with self._lock:
            now = self._clock()
            stale = [user for user in sorted(self._instances)
                     if self._instances[user].running
                     and (now - self._instances[user].lastActive)
                     > self._idleTimeout]
            for user in stale:
                self._stopLocked(user)
            return stale

    def stop(self, user):
        """Stop the instance of `user`: it is gone, its port released."""
        with self._lock:
            self._stopLocked(user)

    def liveUsers(self):
        with self._lock:
            return [inst.user for inst in self._live()]

    def close(self):
        """Stop every instance the pool holds: called on the gateway's way out."""
        with self._lock:
            for user in list(self._instances):
                self._stopLocked(user)

    # ------------------------------------------------------------ internals

    def _live(self):
        return [inst for inst in self._instances.values() if inst.running]

    def _stopLocked(self, user):
        inst = self._instances.pop(user, None)
        if inst is None or not inst.running:
            return
        inst.running = False
        terminate = getattr(inst.handle, 'terminate', None)
        if callable(terminate):
            try:
                terminate()
            except Exception:
                terminate = None
        if terminate is not None:
            wait = getattr(inst.handle, 'wait', None)
            if callable(wait):
                try:
                    wait(timeout=5)
                except Exception:
                    kill = getattr(inst.handle, 'kill', None)
                    if callable(kill):
                        kill()
