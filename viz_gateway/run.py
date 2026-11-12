# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""Run the gateway: the catalog, the pool, one uvicorn loop, one reaper.

    python3 -m viz_gateway                 # on 127.0.0.1:8760, defaults
    python3 -m viz_gateway --port 8761 --max-users 20 --idle-timeout 1800

This process owns **no** Qt: the one that owns it is the pool's child, the
`viz_web` it spawns per local user. The gateway here is a Starlette app over a
loop of its own and a reaper of idle instances on a thread of its own -- the
same shape the run's transport takes, so a gateway that is up and a
`viz_web` that has not come up are two different refusals, each named.

It is started from a shell that already loaded the modules the run needs
(`module load IMAS-Python/2.3.0-...`, the `VIZ_HOME`, `VIZ_PRODUCTION`), because
every child it spawns inherits that environment and isolates itself only by
its own $HOME.
"""

import argparse
import signal
import threading
import time


def parseArguments(argv=None):
    """The command line of one gateway."""
    parser = argparse.ArgumentParser(
        prog='viz_gateway',
        description='More than one user at a time, each behind its own '
                    'IMASViz instance: the token decides, the pool holds the '
                    'instances and their budget.')
    parser.add_argument('--host', default='127.0.0.1',
                        help='interface the gateway listens on (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=8760,
                        help='port of the gateway (default: 8760)')
    parser.add_argument('--users-dir', dest='users_dir',
                        default='~/.imasviz/gateway',
                        help='directory the users.json sits in '
                             '(default: ~/.imasviz/gateway)')
    parser.add_argument('--idle-timeout', dest='idle_timeout', type=int,
                        default=1800,
                        help='seconds of inactivity before an instance is '
                             'reaped (default: 1800)')
    parser.add_argument('--max-users', dest='max_users', type=int, default=20,
                        help='the pool budget: how many live instances at '
                             'once (default: 20)')
    parser.add_argument('--max-turns', dest='max_turns', type=int, default=12,
                        help='the agent loop turn limit forwarded to every '
                             'local instance it spawns (default: 12, the '
                             'viz_web default)')
    return parser.parse_args(argv)


def main(argv=None):
    """Build the catalog and the pool, serve the gateway, reap the idle ones."""
    args = parseArguments(argv)

    from viz_gateway.userstore import UserStore
    from viz_gateway.spawner import Pool
    from viz_gateway.proxy import buildApp
    import uvicorn

    store = UserStore(args.users_dir)
    pool = Pool(idleTimeout=args.idle_timeout, maxUsers=args.max_users,
                maxTurns=args.max_turns)
    app = buildApp(store, pool)

    config = uvicorn.Config(app, host=args.host, port=args.port,
                            log_level='warning', lifespan='on')
    uv = uvicorn.Server(config)
    uv.install_signal_handlers = lambda: None

    # The reaper: a plain thread that asks the pool twice a minute for the
    # users idle past the budget. It touches no widget -- none lives here.
    stop = threading.Event()

    def _reap():
        while not stop.wait(30):
            try:
                pool.reapIdle()
            except Exception:
                pass

    threading.Thread(target=_reap, daemon=True,
                     name='viz-gateway-reaper').start()

    def _shutdown(*_args):
        uv.should_exit = True

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    print('IMASViz gateway is up on http://%s:%s' % (args.host, args.port),
          flush=True)
    try:
        uv.run()
    finally:
        stop.set()
        pool.close()
    return 0
