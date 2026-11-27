# Copyright holders : Commissariat à l'Energie Atomique et aux Energies
# Alternatives (CEA), France; and Laboratory for Engineering Design - LECAD,
# University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C
# open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted
# upon downloading the software and/or exercising any of the rights granted
# under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The LLM client's retry policy and its shared HTTP plumbing.

Every endpoint call -- the LLM, the embeddings -- goes through the one
``_request`` helper: a connection failure -- the server is absent or slow,
the transient shape -- is retried once with a short backoff; a non-2xx
answer is never retried, because the server said something; a caller
asking for one attempt gets one. ``HTTPStatusError`` carries the status
and the body so a caller (the embeddings probe) can tell a 501 apart
from any other non-2xx without re-parsing the message.
"""

import io
import urllib.error

import pytest

from imasviz.VizAgent.llm_client import HTTPStatusError, _request


def test_a_transient_failure_is_retried_once(monkeypatch):
    """The server is absent -- the transient shape: one retry, then the
    answer or the named refusal. Never a second refusal in a row, never
    silence."""
    calls = []

    class Response:
        def read(self):
            return b'{"ok": true}'

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=None):
        calls.append(1)
        if len(calls) == 1:
            raise urllib.error.URLError('connection refused')
        return Response()

    monkeypatch.setattr('urllib.request.urlopen', fake_urlopen)
    raw = _request('POST', 'http://127.0.0.1:1/x', {'a': 1}, None, 1.0,
                   label='LLM', attempts=2, backoff=0.01)
    assert raw == '{"ok": true}'
    assert len(calls) == 2


def test_a_non_2xx_is_never_retried(monkeypatch):
    """The server said something; a second try would only repeat it."""
    calls = []

    def fake_urlopen(req, timeout=None):
        calls.append(1)
        raise urllib.error.HTTPError(
            'http://127.0.0.1:1/x', 500, 'Internal', {},
            io.BytesIO(b'boom'))

    monkeypatch.setattr('urllib.request.urlopen', fake_urlopen)
    with pytest.raises(HTTPStatusError) as excinfo:
        _request('POST', 'http://127.0.0.1:1/x', {'a': 1}, None, 1.0,
                 label='LLM', attempts=2, backoff=0.01)
    assert excinfo.value.status == 500
    assert len(calls) == 1


def test_one_attempt_when_it_is_asked_for(monkeypatch):
    calls = []

    def fake_urlopen(req, timeout=None):
        calls.append(1)
        raise urllib.error.URLError('connection refused')

    monkeypatch.setattr('urllib.request.urlopen', fake_urlopen)
    with pytest.raises(ConnectionError):
        _request('POST', 'http://127.0.0.1:1/x', {'a': 1}, None, 1.0,
                 label='LLM', attempts=1, backoff=0.01)
    assert len(calls) == 1


def test_a_persistent_connection_failure_names_the_endpoint(monkeypatch):
    def fake_urlopen(req, timeout=None):
        raise urllib.error.URLError('connection refused')

    monkeypatch.setattr('urllib.request.urlopen', fake_urlopen)
    with pytest.raises(ConnectionError) as excinfo:
        _request('POST', 'http://127.0.0.1:1/x', {'a': 1}, None, 0.1,
                 label='LLM', attempts=2, backoff=0.01)
    assert '127.0.0.1:1' in str(excinfo.value)
