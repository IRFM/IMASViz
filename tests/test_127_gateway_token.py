# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The gateway's token catalog: who a token holds, and the refusal when none.

The catalog is pure file logic (no Qt, no IMAS), so it is tested directly:
`issue` writes a user and its backend and answers a fresh token, `entryFor`
resolves a token back to that user and its backend, and every shape of a wrong
token -- absent, blank, one no user holds -- is refused *by name*, the way the
rest of the application names its refusals instead of answering a silence.
"""

import json
import os

import pytest

from viz_gateway.userstore import UserStore


@pytest.fixture
def catalog(tmp_path):
    return UserStore(str(tmp_path / 'gateway'))


@pytest.fixture
def home(tmp_path):
    return tmp_path / 'home-alice'


def test_issued_local_user_resolves_its_entry(catalog, home):
    token = catalog.issue('alice', 'local', home=str(home))
    user, entry = catalog.entryFor(token)
    assert user == 'alice'
    assert entry['kind'] == 'local'
    assert entry['token'] == token
    assert entry['home'] == str(home)
    assert entry['url'] is None


def test_a_local_user_without_a_home_gets_one_under_the_gateway(catalog):
    token = catalog.issue('alice', 'local')
    _, entry = catalog.entryFor(token)
    assert entry['kind'] == 'local'
    # `alice` is isolated: its HOME is a folder of its own under the gateway.
    assert entry['home'].endswith('alice')
    assert 'gateway' in entry['home']


def test_issued_remote_user_keeps_its_url_and_no_home(catalog):
    token = catalog.issue('bob', 'remote', url='https://viz.example/8770/')
    user, entry = catalog.entryFor(token)
    assert user == 'bob'
    assert entry['kind'] == 'remote'
    assert entry['url'] == 'https://viz.example/8770/'
    assert entry['home'] is None


def test_a_remote_user_without_a_url_is_refused_by_name(catalog):
    with pytest.raises(ValueError) as exc:
        catalog.issue('carol', 'remote')
    assert 'needs its URL' in str(exc.value)
    assert 'carol' in str(exc.value)


def test_a_kind_outside_local_and_remote_is_refused_by_name(catalog):
    with pytest.raises(ValueError) as exc:
        catalog.issue('dave', 'hybrid')
    assert '"local"' in str(exc.value)
    assert '"remote"' in str(exc.value)


def test_issuing_a_name_twice_is_refused(catalog):
    catalog.issue('alice', 'local')
    with pytest.raises(ValueError) as exc:
        catalog.issue('alice', 'local')
    assert '"alice"' in str(exc.value)


def test_an_issued_token_survives_a_reload(catalog):
    token = catalog.issue('alice', 'local')
    reloaded = UserStore(catalog.dirName)
    user, entry = reloaded.entryFor(token)
    assert user == 'alice'
    assert entry['kind'] == 'local'
    assert reloaded.userCount() == 1


def test_a_token_no_user_holds_is_refused_by_name(catalog):
    catalog.issue('alice', 'local')
    with pytest.raises(ValueError) as exc:
        catalog.entryFor('a-token-alice-did-not-get')
    message = str(exc.value)
    assert 'unknown token' in message
    # The refusal names the token that came in and the user the file holds.
    assert 'a-token-alice-did-not-get' in message
    assert '"alice"' in message


def test_an_absent_token_is_refused(catalog):
    with pytest.raises(ValueError) as exc:
        catalog.entryFor(None)
    assert 'no token' in str(exc.value)


def test_a_blank_token_is_refused_not_matched(catalog):
    catalog.issue('alice', 'local')
    with pytest.raises(ValueError) as exc:
        catalog.entryFor('   ')
    assert 'no token' in str(exc.value)


def test_a_users_json_that_is_not_an_object_is_refused(catalog):
    os.makedirs(catalog.dirName, exist_ok=True)
    with open(catalog.path, 'w') as f:
        json.dump(['a', 'b'], f)
    with pytest.raises(ValueError) as exc:
        catalog.entryFor('anything')
    assert 'not an object' in str(exc.value)
    assert 'list' in str(exc.value)


def test_users_lists_the_names_the_catalog_holds(catalog):
    catalog.issue('alice', 'local')
    catalog.issue('bob', 'remote', url='https://viz.example/8770/')
    assert catalog.users() == ['alice', 'bob']
    assert catalog.userCount() == 2
