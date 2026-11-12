# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""Two *real* instances of the run, behind the gateway, each invisible to the other.

The other files in this set pin the pool and the proxy against fakes. This one
spawns the real thing -- two `python3 -m viz_web`, one per `local` user, the
pool's own spawn and health -- and drives them through the gateway's one route,
so what it proves is the one that matters: user A opens the reference case,
and user B, behind his own instance and his own HOME, does not see it. That is
the isolation the process-per-user model buys, answered over the wire rather
than asserted in the tree.

It is a `case`: it needs the HLI importable (so a child can `import imas` too)
and the reference case on disk. It is skipped when either is absent, the way
the other real-case tests are.
"""

import pytest

from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI,
                      case_uri_or_skip)

from starlette.testclient import TestClient

from viz_gateway.proxy import buildApp
from viz_gateway.spawner import Pool
from viz_gateway.userstore import UserStore


@pytest.mark.case
def test_two_local_users_are_isolated(tmp_path):
    pytest.importorskip('imas')
    uri = case_uri_or_skip()
    if uri is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)

    store = UserStore(str(tmp_path / 'gateway'))
    tokenA = store.issue('alice', 'local', home=str(tmp_path / 'home-a'))
    tokenB = store.issue('bob', 'local', home=str(tmp_path / 'home-b'))
    pool = Pool(maxUsers=2, idleTimeout=3600)
    client = TestClient(buildApp(store, pool), base_url='http://gateway')
    authA = {'authorization': 'Bearer %s' % tokenA}
    authB = {'authorization': 'Bearer %s' % tokenB}

    try:
        baseA = pool.ensure('alice', store.entryFor(tokenA)[1])
        baseB = pool.ensure('bob', store.entryFor(tokenB)[1])
        # Two loopback instances: the isolation the model buys, in the base.
        assert baseA != baseB

        # User A opens the reference case.
        openByA = client.post(
            '/api/tool',
            json={'name': 'open_case',
                  'args': {'uri': uri,
                           'dd_version': CASE_DATA_DICTIONARY_VERSION}},
            headers=authA)
        assert openByA.status_code == 200, openByA.text

        healthA = client.get('/api/health', headers=authA).json()
        healthB = client.get('/api/health', headers=authB).json()

        # A holds the case A opened.
        casesA = healthA.get('cases')
        assert casesA, 'user A should hold the case it opened'

        # B does not: his instance, his HOME, his bookkeeping.
        assert healthB.get('cases') in (None, [], ''), \
            'user B saw a case he did not open: %s' % (healthB, )
    finally:
        pool.close()
