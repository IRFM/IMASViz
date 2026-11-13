# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""A client for an OpenAI-compatible chat/completions endpoint.

Standard library only: ``urllib.request`` and ``json``. No new dependency.

The configuration is read from ``QVizPreferences``:
``AgentLLMEndpoint`` (default ``http://127.0.0.1:11434/v1``),
``AgentLLMModel`` (default ``qwen3.8:27b``; an empty model is read from the
first entry of ``/v1/models``),
``AgentLLMApiKey`` (default: empty, no ``Authorization`` header).

Refusals are named (the style of this repository):
* connection refused/timeout → ``ConnectionError``;
* ``finish_reason == 'length'`` → ``ValueError`` (response truncated);
* empty ``content`` with no ``tool_calls`` → ``ValueError`` (empty answer);
* non-2xx → ``RuntimeError`` with the status and body.
"""

import json
import logging
import urllib.error
import urllib.request
import urllib.parse


def _messagesForRequest(messages):
    """The messages as sent, with the loop's tail made endpoint-safe.

    The agent loop ends a request on a ``tool`` result and asks again.
    An endpoint that requires the last message to be a user message
    -- Ollama answers ``HTTP 500: no user query found in messages`` on
    exactly that shape -- is not asked for anything but its answer: one
    short user line is appended, and nothing else is moved.
    """
    if messages and messages[-1].get('role') == 'tool':
        return list(messages) + [
            {'role': 'user', 'content': 'Continue.'}]
    return messages


class LLMResponse:
    """One response from the LLM, as the agent loop reads it.

    ``content`` is the text answer (may be empty when ``tool_calls`` is set).
    ``tool_calls`` is a list of ``{'name': str, 'args': dict}``.
    ``finish_reason`` is the string the server sent: ``'stop'``,
    ``'tool_calls'``, ``'length'``, or another.
    """
    def __init__(self, content='', tool_calls=None, finish_reason='stop',
                 usage=None):
        self.content = content or ''
        self.tool_calls = tool_calls
        self.finish_reason = finish_reason
        self.usage = usage

    def __repr__(self):
        return ('LLMResponse(content=%r, tool_calls=%r, finish_reason=%r)'
                % (self.content[:40], self.tool_calls, self.finish_reason))


class LLMClient:
    """One LLM endpoint: its URL, its model, and the ``chat`` method.

    Built from ``QVizPreferences``; a ``timeout`` in seconds is passed to
    ``urllib.request`` for every request.
    """
    def __init__(self, endpoint=None, model=None, api_key=None,
                 timeout=120.0):
        from imasviz.VizUtils import QVizPreferences
        # A field typed on a command line or in the REPL never passed through
        # the preferences reader, so a stray room at its end would stand: strip
        # it here, where it is read for the URL, the model name and the header.
        self.endpoint = (endpoint or
                         QVizPreferences.AgentLLMEndpoint).strip().rstrip('/')
        self.model = (model or QVizPreferences.AgentLLMModel or
                      '').strip() or None
        self.api_key = (api_key or
                        QVizPreferences.AgentLLMApiKey or '').strip()
        self.timeout = timeout
        self._model_resolved = False

    def _resolveModel(self):
        """If the model name is empty, read the first entry from /v1/models."""
        if self._model_resolved or self.model:
            return self.model
        try:
            req = urllib.request.Request(self.endpoint + '/models',
                                         method='GET')
            if self.api_key:
                req.add_header('Authorization', 'Bearer ' + self.api_key)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode())
            items = data.get('data', [])
            if items:
                self.model = items[0].get('id', '')
            else:
                raise ValueError(
                    'LLM /v1/models returned no entries; set AgentLLMModel '
                    'in the preferences file or the AgentLLMModel '
                    'environment to name one.')
        except urllib.error.URLError as e:
            raise ConnectionError(
                'Cannot reach the LLM endpoint at %s: %s. '
                'Start the server (e.g. llama-server --port 8080) or set '
                'AgentLLMEndpoint in the preferences file.'
                % (self.endpoint, e.reason))
        self._model_resolved = True
        return self.model

    def chat(self, messages, tools=None, max_tokens=2048, temperature=0.2):
        """One chat/completions call. Returns an ``LLMResponse``.

        Raises a named exception on refusal (see module docstring).
        """
        model = self._resolveModel()
        payload = {
            'model': model,
            'messages': _messagesForRequest(messages),
            'max_tokens': max_tokens,
            'temperature': temperature,
            'reasoning_effort': 'none',
        }
        if tools:
            payload['tools'] = tools
            payload['tool_choice'] = 'auto'

        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            self.endpoint + '/chat/completions',
            data=body,
            method='POST',
            headers={'Content-Type': 'application/json'},
        )
        if self.api_key:
            req.add_header('Authorization', 'Bearer ' + self.api_key)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status = resp.status
                raw = resp.read().decode()
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else ''
            raise RuntimeError(
                'LLM returned HTTP %d: %s' % (e.code, body[:200]))
        except urllib.error.URLError as e:
            raise ConnectionError(
                'Cannot reach the LLM endpoint at %s: %s.'
                % (self.endpoint, e.reason))

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                'LLM returned invalid JSON (%s): %s' % (e, raw[:200]))

        choice = data.get('choices', [{}])[0]
        message = choice.get('message', {})
        finish_reason = choice.get('finish_reason', 'stop')
        content = message.get('content', '') or ''
        tool_calls = None
        if message.get('tool_calls'):
            tool_calls = []
            for tc in message['tool_calls']:
                fn = tc.get('function', {})
                try:
                    args = json.loads(fn.get('arguments', '{}'))
                except json.JSONDecodeError:
                    args = {'_raw': fn.get('arguments', '')}
                tool_calls.append({'name': fn.get('name', ''), 'args': args})

        response = LLMResponse(
            content=content, tool_calls=tool_calls,
            finish_reason=finish_reason,
            usage=data.get('usage'),
        )

        # Named refusals (the style of this repository):
        if finish_reason == 'length':
            raise ValueError(
                'response truncated by max_tokens=%d; increase max_tokens '
                'or shorten the prompt.' % max_tokens)
        if not content and not tool_calls:
            raise ValueError(
                'LLM returned empty content with finish_reason=%r; '
                'the model may be out of budget or misconfigured.'
                % finish_reason)

        return response
