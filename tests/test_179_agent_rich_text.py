# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The rich reading of the assistant's lines, on the two surfaces that
are not the page.

What it pins, scripted, off the reference case:

* the shared reading -- the one rule the surfaces hold together (only
  the assistant's own words are read), the math the page's own rules
  carry (the tokens to their unicode, ``\\frac`` and ``\\sqrt`` to
  their readable shapes, ``\\text`` and ``\\mathrm`` out of their
  braces, the unknown kept, ``_`` and ``^`` spelled), and the two
  renderers: the HTML the panel's engine paints (the bold, the italic,
  the code, the links it may open, the injection escaped, and the math
  left spelled for the engine that composes it) and the terminal the
  client reads (the ANSI codes when asked and none off a tty, the math
  the page's reading carries, the code and the links as the words
  they are).
* the panel -- an assistant line with a bold and a formula lands in the
  transcript bold and composed (the engine consumes the ``$...$``), a
  refusal keeps its asterisks, the transcript is ``NoWrap`` the way the
  window's width was capped for it, and ``Clear`` empties it without
  touching the prompt history.
* the client -- a turn's answer is carried to the console the way the
  page carries it (the bold read, the math to its unicode, no codes on
  a piped stdout), while the transcript file the turn saves keeps the
  plain words: the file that is audited is not the console.
"""

import pytest

from imasviz.VizAgent import rich
from imasviz.VizAgent.llm_client import LLMResponse
from viz_cli.session import CliSession, Client


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    """Both surfaces write the one prompt history the whole application
    shares, under ``$HOME/.imasviz``: a test here must not read or write
    the user's real list, so every test points ``HOME`` at its own
    folder (the ``test_113`` / ``test_118`` pattern)."""
    monkeypatch.setenv('HOME', str(tmp_path))


# ------------------------------------------------------------- the shared reading

def test_only_the_assistant_line_is_read():
    assert rich.isAssistantLine('LLM: hello')
    assert rich.isAssistantLine('LLM:hello')
    assert not rich.isAssistantLine('User: hello')
    assert not rich.isAssistantLine('REFUSAL — a refusal')
    assert not rich.isAssistantLine(None)
    assert rich.assistantBody('LLM: hello') == 'hello'


def test_math_to_unicode_is_the_page_reading():
    assert rich.mathToUnicode(r'\alpha + \beta') == 'α + β'
    assert rich.mathToUnicode(r'\frac{a}{b}') == '(a)/(b)'
    assert rich.mathToUnicode(r'\sqrt{x}') == '√(x)'
    assert rich.mathToUnicode(r'\text{eq}') == 'eq'
    assert rich.mathToUnicode(r'\mathrm{eq}') == 'eq'
    # a token the map does not read is kept, not guessed
    assert rich.mathToUnicode(r'\zzz') == r'\zzz'
    # subscripts and exponents stay spelled, the same as the page
    assert rich.mathToUnicode(r'\beta_{eff}') == r'β_{eff}'


def test_to_html_reads_bold_italic_and_code():
    html = rich.toHtml('LLM: **gras** et *italique* et `core.time_slice`')
    assert '<b>LLM:</b>' in html
    assert '<b>gras</b>' in html
    assert '<i>italique</i>' in html
    assert '<code>core.time_slice</code>' in html
    assert '**' not in html and '`' not in html
    # the other spelling of the bold
    assert '<b>gras</b>' in rich.toHtml('LLM: __gras__')


def test_to_html_carries_the_math_the_page_carries():
    # the engine the panel's document is painted by composes no math
    # (measured), so the page's own reading carries it: the tokens to
    # their unicode, the two structures to their readable shapes, the
    # two commands it does not read out of their braces
    html = rich.toHtml(r'LLM: $\frac{a}{b}$')
    assert '(a)/(b)' in html
    assert '$' not in html
    html = rich.toHtml(r'LLM: $\text{eq}$')
    assert 'eq' in html
    assert r'\text' not in html


def test_to_html_escapes_the_injection():
    html = rich.toHtml('LLM: **<script>alert(1)</script>**')
    assert '<script>' not in html
    assert '&lt;script&gt;' in html


def test_to_html_links_only_what_a_reader_can_open():
    html = rich.toHtml('LLM: [ITER](https://www.iter.org)')
    assert '<a href="https://www.iter.org">ITER</a>' in html
    # a scheme the reader cannot open keeps the words it gave
    html = rich.toHtml('LLM: [x](javascript:alert(1))')
    assert '<a' not in html
    assert 'x' in html


def test_to_html_leaves_the_other_lines_verbatim():
    assert rich.toHtml('REFUSAL — **brut**') == 'REFUSAL — **brut**'
    # the five that end a tag or an attribute are still escaped
    assert rich.toHtml('<script>') == '&lt;script&gt;'


def test_to_html_carries_the_line_breaks_the_model_gave():
    """The model's ``\\n`` are the line breaks the page reads with
    ``white-space: pre-wrap``; the Qt engine flattens a bare ``\\n``
    into a space, so they are carried as ``<br>`` — one per newline, an
    empty one for two. A real answer's list (shape of the transcript)
    lands in separate lines, not on one."""
    line = ('LLM: Les deux figures redessinées :\n\n'
            '- **Plot7** : 101 points\n'
            '- **Plot8** : 101 points\n\n'
            'Veux-tu que je :\n'
            '- **les remette à l\'écran** ?')
    html = rich.toHtml(line)
    # no bare newline survives: it is all <br>, and the two break the
    # empty line the way pre-wrap reads it
    assert '\n' not in html
    assert '<br>' in html
    assert '<br><br>' in html
    # the list items stand where the model put them (the apostrophe is
    # escaped the way the reader expects it in an HTML attribute context)
    assert '- <b>Plot7</b> : 101 points<br>' in html
    assert '<br>- <b>les remette à l&#39;écran</b> ?' in html


def test_to_html_keeps_the_fenced_code_breaks():
    """The line breaks inside a fenced block are its own, kept by
    ``<pre>``: the prose around it gets ``<br>`` and the code keeps its
    newlines, not a double break for each."""
    html = rich.toHtml('LLM: avant\n```\nline one\nline two\n```\naprès')
    assert '<pre>line one\nline two</pre>' in html
    assert 'avant<br>' in html
    assert '<br>après' in html


def test_to_terminal_reads_bold_and_carries_the_math():
    text = rich.toTerminal(r'LLM: **gras** et $\alpha + \frac{a}{b}$',
                           ansi=True)
    assert '\x1b[1mgras\x1b[0m' in text
    assert 'α + (a)/(b)' in text
    assert '**gras**' not in text
    # italic is its own code
    text = rich.toTerminal('LLM: *italique*', ansi=True)
    assert '\x1b[3mitalique\x1b[0m' in text


def test_to_terminal_off_a_tty_keeps_the_plain_words():
    text = rich.toTerminal(r'LLM: **gras** et $\alpha$', ansi=False)
    assert '\x1b' not in text
    assert 'gras' in text
    assert 'α' in text


def test_to_terminal_left_out_answers_the_output():
    # a stdout that is not a terminal -- the test's stand-in -- answers
    # no, and the math is still carried
    text = rich.toTerminal(r'LLM: **gras** et $\alpha$')
    assert '\x1b' not in text
    assert 'α' in text


def test_to_terminal_keeps_the_code_the_links_and_the_other_lines():
    text = rich.toTerminal(
        'LLM: `plot_one` et [ITER](https://iter.org)', ansi=False)
    assert 'plot_one' in text
    assert '`' not in text
    assert '[ITER](https://iter.org)' in text
    line = 'REFUSAL — **brut**'
    assert rich.toTerminal(line) == line


# ------------------------------------------------------------------- the panel

def _buildPanel(qapp):
    from imasviz.VizAgent.panel import QVizAgentPanel
    return QVizAgentPanel(main_window=None, api=None, agent=None)


def test_panel_reads_bold_and_carries_the_math(qapp):
    """The assistant's own words land in the transcript read: the bold is
    painted (the engine it is painted by answers a weight of 700 for it),
    and the math the model spelled is carried the way the page carries
    it -- the ``$...$`` it stood in is gone from the plain text."""
    panel = _buildPanel(qapp)
    panel._appendTranscript(r'LLM: **gras** et $\frac{a}{b}$')
    assert 'font-weight:700' in panel.transcript.toHtml()
    plain = panel.transcript.toPlainText()
    assert 'gras' in plain
    assert '(a)/(b)' in plain
    assert '$' not in plain


def test_panel_keeps_the_other_lines_verbatim(qapp):
    """A refusal is the shape the loop names: its asterisks are an
    argument, not emphasis, and they stand where the loop left them."""
    panel = _buildPanel(qapp)
    panel._appendTranscript('REFUSAL — **brut**')
    assert '**brut**' in panel.transcript.toPlainText()
    assert '<b>' not in panel.transcript.toHtml()


def test_panel_reads_a_list_as_separate_lines(qapp):
    """The one answer the user reported flat: a list. The model gives it
    with its line breaks, and the panel reads them the way the page
    does -- one line per item, the empty one for the two breaks --
    instead of flattening the ``\\n`` into spaces."""
    panel = _buildPanel(qapp)
    panel._appendTranscript(
        'LLM: Les deux figures redessinées :\n\n'
        '- **Plot7** : 101 points\n'
        '- **Plot8** : 101 points')
    plain = panel.transcript.toPlainText()
    # each item stands on its own line, the way the page's pre-wrap reads
    # it -- not one line, not the newlines flattened into spaces
    assert 'Les deux figures redessinées :' in plain
    assert '- Plot7 : 101 points' in plain
    assert '- Plot8 : 101 points' in plain
    lines = [l for l in plain.split('\n') if l.strip()]
    assert '- Plot7 : 101 points' in lines
    assert '- Plot8 : 101 points' in lines
    assert len(lines) == 3


def test_panel_transcript_is_nowrap_and_clears(qapp):
    """The transcript keeps the rule the window's width was capped for
    -- a long line scrolls instead of wrapping -- and ``Clear`` empties
    it without touching the prompt history it sits beside."""
    from PySide6.QtWidgets import QTextBrowser

    panel = _buildPanel(qapp)
    assert panel.transcript.lineWrapMode() == QTextBrowser.LineWrapMode.NoWrap
    panel._appendTranscript('LLM: a line of the transcript')
    assert 'a line of the transcript' in panel.transcript.toPlainText()
    panel._onClear()
    assert panel.transcript.toPlainText() == ''


# --------------------------------------------------------------------- the client

class _ScriptedLLM:
    """One scripted response: the answer, no gesture."""
    def __init__(self, content):
        self._content = content

    def chat(self, messages, tools=None, **kwargs):
        return LLMResponse(content=self._content, tool_calls=None,
                           finish_reason='stop')


class _Core:
    """A session that holds no figure: the turn draws nothing, so the
    captures of the turn are none."""
    def list_windows(self):
        return []


class _Window:
    """What the session asks of the window: no api, and a hide at exit."""
    def sessionApi(self):
        return None

    def hide(self):
        pass


def test_console_reads_the_answer_the_page_reads(qapp, tmp_path, capsys):
    """A turn's answer reaches the console the way the page reads it:
    the bold is read, the math is carried to its unicode, and a stdout
    that is not a terminal gets no codes -- while the transcript file
    the turn saves keeps the plain words the loop gave, the one that is
    audited."""
    llm = Client(_ScriptedLLM(r'**gras** et $\alpha + \frac{a}{b}$'))
    session = CliSession(app=qapp, window=_Window(), core=_Core(), llm=llm,
                         shots_dir=str(tmp_path / 'shots'), max_turns=4)
    session.runPrompt('trace le champ')

    out = capsys.readouterr().out
    assert '\x1b' not in out
    assert '**gras**' not in out
    assert 'gras' in out
    assert 'α + (a)/(b)' in out

    transcripts = list((tmp_path / 'shots').rglob('transcript.txt'))
    assert len(transcripts) == 1
    raw = transcripts[0].read_text()
    assert r'LLM: **gras** et $\alpha + \frac{a}{b}$' in raw
