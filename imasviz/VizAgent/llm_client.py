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

The round trip is shared by both clients: one ``_request`` helper, one
retry policy. A connection failure -- the server is absent or slow -- is
retried once, with a short backoff; a non-2xx answer is never retried,
because the server said something and a second try would only repeat it.
"""

import json
import time
import urllib.error
import urllib.request


class HTTPStatusError(RuntimeError):
    """A non-2xx answer from the endpoint, carrying the status and the body.

    It is a ``RuntimeError`` so the callers -- which refuse by name -- see
    the same shape as any other named refusal; the status is kept so a
    caller can tell a ``501`` (no embedding table) apart from any other
    failure without re-parsing the message.
    """

    def __init__(self, label, status, body):
        super().__init__(
            'the %s endpoint answered HTTP %d: %s' % (label, status, body[:200]))
        self.status = status
        self.body = body


def _request(method, url, payload, api_key, timeout, *, label,
             hint='', attempts=2, backoff=0.5):
    """One round trip to the endpoint, with the retry policy of the module.

    Returns the raw 2xx body. A connection failure is retried once with
    ``backoff`` seconds between the two tries; a non-2xx is never retried.
    Raises ``HTTPStatusError`` (a ``RuntimeError``) for a non-2xx answer and
    ``ConnectionError`` for an unreachable endpoint -- the two named refusals
    the callers raise. ``hint`` is appended to the connection message so a
    caller can name what to do about it (``_resolveModel`` names the
    server and the preference to point at).
    """
    for attempt in range(attempts):
        try:
            return _round_trip(method, url, payload, api_key, timeout,
                               label=label, hint=hint)
        except ConnectionError:
            if attempt + 1 >= attempts:
                raise
            time.sleep(backoff)
    raise ConnectionError('unreachable')


def _round_trip(method, url, payload, api_key, timeout, *, label, hint=''):
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=body, method=method,
                                 headers={'Content-Type': 'application/json'})
    if api_key:
        req.add_header('Authorization', 'Bearer ' + api_key)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode()
    except urllib.error.HTTPError as e:
        text = e.read().decode() if e.fp else ''
        raise HTTPStatusError(label, e.code, text)
    except urllib.error.URLError as e:
        raise ConnectionError(
            'Cannot reach the %s endpoint at %s: %s.%s'
            % (label, url, e.reason, hint))
    except (TimeoutError, OSError) as e:
        raise ConnectionError(
            'Cannot reach the %s endpoint at %s: %s.%s'
            % (label, url, e, hint))


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
        raw = _request(
            'GET', self.endpoint + '/models', None, self.api_key,
            self.timeout, label='LLM',
            hint=' Start the server (e.g. llama-server --port 8080) or '
                 'set AgentLLMEndpoint in the preferences file.')
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                'LLM returned invalid JSON (%s): %s' % (e, raw[:200]))
        items = data.get('data', [])
        if items:
            self.model = items[0].get('id', '')
        else:
            raise ValueError(
                'LLM /v1/models returned no entries; set AgentLLMModel '
                'in the preferences file or the AgentLLMModel '
                'environment to name one.')
        self._model_resolved = True
        return self.model

    def chat(self, messages, tools=None, max_tokens=8192, temperature=0.2):
        """One chat/completions call. Returns an ``LLMResponse``.

        Raises a named exception on refusal (see module docstring).

        ``max_tokens`` defaults to 8192: the in-app model (a local 27B) writes
        French prose with markdown tables and inline math before it answers,
        and the refusal path in ``AgentLoop`` turns a truncated response into
        a silent "nothing happened" on the user's screen rather than a
        shorter-but-valid answer.  2048 was the first observed limit; on this
        node the longest observed turn finished around 3 100 tokens.
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

        raw = _request('POST', self.endpoint + '/chat/completions', payload,
                       self.api_key, self.timeout, label='LLM')

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


class EmbeddingClient:
    """A client for an OpenAI-compatible ``/embeddings`` endpoint.

    The same ``urllib`` plumbing as ``LLMClient``, on an endpoint of
    its own: ``AgentEmbedEndpoint`` and ``AgentEmbedModel`` in the
    preferences, read when the fields are left out of the call. A
    chat endpoint (the ``qwen3.8:27b`` the application runs) is not an
    embedding one — the model that answers ``/embeddings`` has to
    carry an embedding table, so the two are named apart, and a
    preference that sets the chat one does not set this one.

    ``embed(text)`` is one text to one vector (the shape the journals
    ask of, one note at a time), and ``embed_batch(texts)`` is the same
    with a list. Refusals are named: an endpoint with no server, one
    that answers a non-2xx, and one that does not answer the shape this
    client reads are all a ``ValueError`` with the reason, the rule the
    ``LLMClient`` applies to its own call.
    """
    def __init__(self, endpoint=None, model=None, api_key=None,
                 timeout=120.0):
        from imasviz.VizUtils import QVizPreferences
        self.endpoint = (endpoint or
                         QVizPreferences.AgentEmbedEndpoint or '').strip()
        self.endpoint = self.endpoint.rstrip('/')
        self.model = (model or QVizPreferences.AgentEmbedModel or '').strip()
        self.api_key = (api_key or '').strip()
        self.timeout = timeout

    def __call__(self, text):
        """One text to its vector. The journals' ``rankByVector`` asks
        of it one note at a time, and it is the callable the core hands
        to that (a ``text -> list[float]``). An endpoint that is not
        named is a named refusal: the caller reads it and falls back to
        the keyword, and the ``journals`` module is the one that names
        the fallback in the answer, not this client."""
        return self.embed(text)

    def probe(self):
        """The one call that asks the endpoint for its dimension.

        ``dal-rag``'s ``probe`` is the model: one short text, the
        ``501`` read as "no embedding table" (a llama-server that was
        not started with ``--embeddings`` answers ``501``), the
        dimension of the one vector it answers read back. A refusal is
        named: an endpoint not named, one that does not answer, one
        that answers a body the client does not read — the same shape
        ``embed`` refuses, because a probe that does not know its
        dimension answers a search that could not rank."""
        payload = {'input': ['probe']}
        if self.model:
            payload['model'] = self.model
        try:
            raw = _request('POST', self.endpoint + '/embeddings', payload,
                           self.api_key, self.timeout, label='embeddings')
        except HTTPStatusError as e:
            if e.status == 501:
                raise RuntimeError(
                    'the endpoint %s answers 501 for /embeddings: it was '
                    'not started with an embedding table (e.g. '
                    'llama-server --embeddings). Start it, or point '
                    'AgentEmbedEndpoint at an endpoint that carries one.'
                    % (self.endpoint or '(none named)'))
            raise
        items = json.loads(raw).get('data')
        if not isinstance(items, list) or not items \
                or not isinstance(items[0], dict) \
                or not isinstance(items[0].get('embedding'), list):
            raise ValueError(
                'the endpoint did not answer a vector to the probe: its '
                'body holds no embedding to read the dimension from.')
        return {'dim': len(items[0]['embedding'])}

    def embed(self, text, input_type=None):
        """One text to its vector, the one OpenAI-compatible shape the
        servers on this stack answer. A text that does not vectorise
        (an empty one, or a shape the endpoint does not answer) is a
        named refusal, the rule ``LLMClient.chat`` applies to its
        empty answer.

        ``input_type`` is the ``E5``-style side the text is on
        (``'query'`` for a question being ranked, ``'passage'`` for a
        note being indexed), the one ``dal-rag``'s ``embed_texts``
        sends: an embedder that needs the two sides prefixed otherwise
        silently degrades retrieval, and the one an endpoint that does
        not know the field ignores, so a model that does not need it is
        untouched by naming it."""
        text = (text or '').strip()
        if not text:
            raise ValueError(
                'a text that is empty does not vectorise: name one.')
        if not self.endpoint:
            raise ValueError(
                'the embeddings endpoint is not named: set '
                'AgentEmbedEndpoint in ~/.imasviz/preferences to point '
                'at one (llama-server --embeddings, or an Ollama that '
                'serves an embedding model). The keyword search is the '
                'one that answers while it is not named.')
        payload = {'input': text}
        if self.model:
            payload['model'] = self.model
        if input_type is not None:
            payload['input_type'] = input_type
        context = 'one text: %r' % (text[:40] if len(text) > 40 else text)
        return self._embedResponse(_request(
            'POST', self.endpoint + '/embeddings', payload,
            self.api_key, self.timeout, label='embeddings'),
            context=context)

    def embed_batch(self, texts, input_type=None):
        """Several texts to their vectors, in the order they were
        asked (the response is re-ordered by its ``index`` field, the
        one ``dal-rag``'s ``embed_texts`` sorts on, so a server that
        answers out of order still hands the Nth vector back against
        the Nth text). The journals use it to index a note's text at
        once (the eager upsert); the shape the later ``Store.reindex``
        wants to ask a whole batch at a time is the one this answers,
        and the refusal is the one ``embed`` has: an endpoint it does
        not answer is a named error on the whole batch, not a half of
        it.

        ``input_type`` is the same ``E5``-style side ``embed`` takes
        (``'passage'`` for the indexed text), the one ``dal-rag``
        sends on the indexing side so the query and the note meet in
        the same space."""
        texts = [one for one in (texts or []) if (one or '').strip()]
        if not texts:
            raise ValueError('a batch that is empty does not vectorise.')
        if not self.endpoint:
            raise ValueError(
                'the embeddings endpoint is not named: set '
                'AgentEmbedEndpoint in ~/.imasviz/preferences to point '
                'at it.')
        payload = {'input': texts}
        if self.model:
            payload['model'] = self.model
        if input_type is not None:
            payload['input_type'] = input_type
        return self._embedResponse(_request(
            'POST', self.endpoint + '/embeddings', payload,
            self.api_key, self.timeout, label='embeddings'),
            context='%d text(s)' % len(texts),
            batch=True)

    @staticmethod
    def _embedResponse(raw, context='', batch=False):
        """The one vector or the list a ``/embeddings`` call answers,
        read off its body. The shape this client answers is the
        OpenAI one (``data``: a list of ``{"embedding": [...]}``), and
        a body that is not that shape is a named refusal, the rule the
        ``LLMClient`` has for a JSON it cannot read."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                'the embeddings endpoint answered a body this client '
                'does not read (%s): %s' % (e, raw[:200]))
        items = data.get('data')
        if not isinstance(items, list) or not items:
            raise ValueError(
                'the embeddings endpoint did not answer %s: its body '
                'holds no embedding to read.' % (context or 'this text'))
        items = [item for item in items
                 if isinstance(item, dict) and item.get('embedding')]
        # Re-order by the ``index`` the server stamps each entry with, so
        # the Nth vector comes back against the Nth text the caller asked
        # (dal-rag sorts on this: a server that answers out of order would
        # otherwise hand the wrong vector to the wrong note). An entry
        # without an index keeps its position.
        if batch:
            def _order(item):
                idx = item.get('index')
                if isinstance(idx, int):
                    return (0, idx)
                return (1, 0)
            items = sorted(items, key=_order)
        vectors = [item['embedding'] for item in items]
        if not vectors:
            raise ValueError(
                'the embeddings endpoint did not answer %s: its body '
                'holds no vector under `embedding` to read.'
                % (context or 'this text'))
        if batch:
            return vectors
        return vectors[0]
