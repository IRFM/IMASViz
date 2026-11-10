# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The pool of local backends: one per user, one port each, a budget, a reaping.

Hermetic: the `spawn` the pool is handed starts no process (it records the
call and answers a handle with a flag the assertions read), the `health` it is
handed is a no-op, and the clock is the one the test moves. So the file pins
the pool's whole budget and reaping logic -- the isolation that makes one user
instance invisible to another's -- without a Qt, an IMAS case, or a socket.
"""

import pytest

from viz_gateway.spawner import Pool


class FakeHandle:
    def __init__(self):
        self.pollResult = None
        self.terminated = False

    def poll(self):
        return self.pollResult

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        return 0


def localEntry(home):
    # The shape one `local` user holds in the catalog: a home to isolate under.
    return {'token': 'a-token', 'kind': 'local', 'home': home, 'url': None}


def makeSpawn(registry):
    def spawn(user, entry, port, env):
        handle = FakeHandle()
        registry[user] = {'port': port, 'env': env, 'handle': handle}
        return handle
    return spawn


def makeClock():
    box = [0.0]
    return (lambda: box[0],
            lambda steps=1.0: box.__setitem__(0, box[0] + steps))


def test_each_local_user_gets_its_own_instance_and_port(tmp_path):
    registry = {}
    pool = Pool(spawn=makeSpawn(registry), health=lambda url, h: None,
                maxUsers=3)
    urlAlice = pool.ensure('alice', localEntry(str(tmp_path / 'alice')))
    urlBob = pool.ensure('bob', localEntry(str(tmp_path / 'bob')))
    assert urlAlice != urlBob
    # Two loopback ports, neither on a fixed range, both distinct.
    assert registry['alice']['port'] != registry['bob']['port']
    # Each isolated by its own HOME.
    assert registry['alice']['env']['HOME'] == str(tmp_path / 'alice')
    assert registry['bob']['env']['HOME'] == str(tmp_path / 'bob')
    assert pool.liveUsers() == ['alice', 'bob']
    pool.close()


def test_ensure_is_idempotent_per_user(tmp_path):
    registry = {}
    pool = Pool(spawn=makeSpawn(registry), health=lambda url, h: None,
                maxUsers=3)
    first = pool.ensure('alice', localEntry(str(tmp_path / 'alice')))
    second = pool.ensure('alice', localEntry(str(tmp_path / 'alice')))
    assert first == second
    assert len(registry) == 1                      # started once
    pool.close()


def test_a_pool_at_its_budget_refuses_the_next_by_name(tmp_path):
    registry = {}
    pool = Pool(spawn=makeSpawn(registry), health=lambda url, h: None,
                maxUsers=2)
    pool.ensure('alice', localEntry(str(tmp_path / 'a')))
    pool.ensure('bob', localEntry(str(tmp_path / 'b')))
    with pytest.raises(ValueError) as exc:
        pool.ensure('carol', localEntry(str(tmp_path / 'c')))
    message = str(exc.value)
    assert 'pool is full' in message
    assert 'budget is 2' in message
    assert 'carol' not in message  # the budget, not that user, is the refusal
    pool.close()


def test_a_pool_with_an_impossible_budget_is_refused():
    with pytest.raises(ValueError) as exc:
        Pool(maxUsers=0)
    assert 'at least one' in str(exc.value)


def test_an_idle_instance_is_reaped_and_frees_the_budget(tmp_path):
    registry = {}
    clock, tick = makeClock()
    pool = Pool(spawn=makeSpawn(registry), health=lambda url, h: None,
                idleTimeout=3600, maxUsers=1, clock=clock)
    pool.ensure('alice', localEntry(str(tmp_path / 'a')))
    tick(3700)
    reaped = pool.reapIdle()
    assert reaped == ['alice']
    assert pool.liveUsers() == []
    assert registry['alice']['handle'].terminated
    # The budget it held is back: the budget-1 pool takes a new user again.
    pool.ensure('bob', localEntry(str(tmp_path / 'b')))
    assert pool.liveUsers() == ['bob']
    pool.close()


def test_a_user_active_since_recently_is_not_reaped(tmp_path):
    registry = {}
    clock, tick = makeClock()
    pool = Pool(spawn=makeSpawn(registry), health=lambda url, h: None,
                idleTimeout=3600, maxUsers=3, clock=clock)
    pool.ensure('alice', localEntry(str(tmp_path / 'a')))
    pool.ensure('bob', localEntry(str(tmp_path / 'b')))
    tick(3700)            # both now idle
    pool.touch('bob')     # bob just got a call
    reaped = pool.reapIdle()
    assert reaped == ['alice']
    assert pool.liveUsers() == ['bob']
    assert not registry['bob']['handle'].terminated
    assert registry['alice']['handle'].terminated
    pool.close()


def test_stopping_a_user_frees_its_budget(tmp_path):
    registry = {}
    pool = Pool(spawn=makeSpawn(registry), health=lambda url, h: None,
                maxUsers=1)
    pool.ensure('alice', localEntry(str(tmp_path / 'a')))
    pool.stop('alice')
    assert pool.liveUsers() == []
    assert registry['alice']['handle'].terminated
    pool.ensure('bob', localEntry(str(tmp_path / 'b')))
    assert pool.liveUsers() == ['bob']
    pool.close()
