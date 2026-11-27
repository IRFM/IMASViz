# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""What an assistant line may be read as, on the two surfaces that are not the page.

The loop gives its answer as words with a little markup (the
``SYSTEM_INSTRUCTIONS`` and ``CHAT_INSTRUCTIONS`` of ``tools`` ask the
model for it): ``**bold**`` the idea, ``*italic*`` a node or unit,
`` `code` `` around the paths, ``$...$`` a symbol, ``$$...$$`` a
formula on a line of its own. The page already reads that markup
(``viz_web/static/index.html``, ``renderRich`` / ``convertMath``); the
in-app panel and the client read it here, with the same rules, because
what a surface paints is the words the loop gave, not a re-reading of
them.

The one rule they all share: only the assistant's own words are read
(``^LLM:``). Every other line -- a tool call, an answer, a refusal, the
stop -- is a shape the loop names, kept verbatim, and a ``*`` in a tool
argument is an argument, not emphasis.

The two renderers are two media of the same reading:

* ``toHtml`` feeds the panel's transcript. It maps the markup onto the
  tags the Qt rich text engine paints -- ``<b>``, ``<i>``, ``<code>``,
  ``<pre>``, ``<a href>`` -- and carries the math the way the page
  carries it, because the engine it would otherwise be left to composes
  none of it (measured on this Qt: a ``$...$`` stays spelled in the
  document, ``setHtml`` and ``insertHtml`` alike).
* ``toTerminal`` feeds the client's console and the one-shot's stdout.
  A terminal composes nothing, and the math is carried the way the page
  carries it: the named tokens to their unicode (``\\alpha`` to
  α), ``\\frac{a}{b}`` to ``(a)/(b)``, ``\\sqrt{a}`` to ``√(a)``, and a
  token the map does not read stands as it is -- a symbol the map does
  not know is kept, not guessed. Bold and italic are the ANSI codes,
  only when the output is a terminal and ``NO_COLOR`` is not set: a
  piped or scripted stdout keeps the plain words, which is also the
  shape the tests' stand-in answers.

Nothing here is a surface: no widget, no ``print``, and the transcript
artifact the client writes to disk (the ``fullLine`` render) is not
touched by either -- the file that is audited stays plain text.
"""

import os
import re
import sys


# The one line the loop gives its answer: everything else is kept verbatim.
ASSISTANT_RE = re.compile(r'^LLM:\s?')


def isAssistantLine(text):
    """Whether the line is the assistant's own words, the only lines
    the markup is read on."""
    return isinstance(text, str) and bool(ASSISTANT_RE.match(text))


def assistantBody(line):
    """The line without its ``LLM:`` lead-in, the content a renderer
    reads."""
    return ASSISTANT_RE.sub('', str(line), count=1)


# The named tokens, and what they carry to the reader. The one table the
# page holds (``MATH_TOKENS`` of ``viz_web/static/index.html``), kept here
# with the same entries and the same order, so the client and the page
# read a symbol the same way.
MATH_TOKENS = {
    'alpha': 'α', 'beta': 'β', 'gamma': 'γ', 'delta': 'δ', 'epsilon': 'ε',
    'zeta': 'ζ', 'eta': 'η', 'theta': 'θ', 'kappa': 'κ', 'lambda': 'λ',
    'mu': 'μ', 'nu': 'ν', 'xi': 'ξ', 'pi': 'π', 'rho': 'ρ', 'sigma': 'σ',
    'tau': 'τ', 'upsilon': 'υ', 'phi': 'φ', 'chi': 'χ', 'psi': 'ψ',
    'omega': 'ω', 'Gamma': 'Γ', 'Delta': 'Δ', 'Theta': 'Θ', 'Lambda': 'Λ',
    'Pi': 'Π', 'Sigma': 'Σ', 'Phi': 'Φ', 'Psi': 'Ψ', 'Omega': 'Ω',
    'approx': '≈', 'sim': '∼', 'equiv': '≡', 'propto': '∝', 'leq': '≤',
    'le': '≤', 'geq': '≥', 'ge': '≥', 'neq': '≠', 'ne': '≠', 'times': '×',
    'div': '÷', 'cdot': '·', 'pm': '±', 'mp': '∓', 'infty': '∞',
    'sum': '∑', 'prod': '∏', 'int': '∫', 'partial': '∂', 'nabla': '∇',
    'to': '→', 'gets': '←', 'in': '∈', 'subset': '⊂', 'supset': '⊃',
    'cup': '∪', 'cap': '∩', 'cdots': '⋯', 'ldots': '…',
}


def mathToUnicode(body):
    """The math of an assistant line, carried to a reader that composes
    nothing -- the port of the page's ``convertMath``, its rules and all.

    ``\\frac{a}{b}`` is the one structure worth a special case,
    ``\\sqrt{a}`` keeps its radical, and ``\\text{...}`` /
    ``\\mathrm{...}`` are read as their content. The named tokens go to
    their unicode, and a token the map does not read stands as it is:
    a symbol the map does not know is kept, not guessed. Subscripts and
    exponents (``_`` / ``^``) stay spelled, the same as the page.
    """
    s = str(body)
    s = re.sub(r'\\frac\{([^{}]*)\}(\{[^{}]*\})',
               lambda m: '(%s)/(%s)' % (m.group(1), m.group(2)[1:-1]), s)
    s = re.sub(r'\\sqrt\{([^{}]*)\}', r'√(\1)', s)
    s = re.sub(r'\\text\{([^{}]*)\}', r'\1', s)
    s = re.sub(r'\\mathrm\{([^{}]*)\}', r'\1', s)
    s = re.sub(r'\\([A-Za-z]+)',
               lambda m: MATH_TOKENS.get(m.group(1), m.group(0)), s)
    return s


def _htmlEscape(text):
    """The five that end a tag or an attribute, the same set the page
    escapes: the two that can open or close a tag, and the two that can
    lift the reader out of the attribute of a link the model gave."""
    return (str(text)
            .replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;').replace("'", '&#39;'))


# The links the model may give: only a web address is a link a reader can
# open -- the LLM reads case data it is not trusted to hand back as code,
# so a scheme it cannot open keeps the words it gave and drops the click
# (the same rule the page applies).
_LINK_RE = re.compile(r'\[([^\]]+)\]\(\s*([^)\s]+)\s*\)')
_LINK_OK = re.compile(r'^(?:https?|mailto):', re.I)
_LINK_BAD = re.compile(r'^(?:javascript|vbscript|data):', re.I)


def _protect(regions):
    """One region out of the text, behind a number nothing else reads."""
    def protect(html):
        regions.append(html)
        return '\x00%d\x00' % (len(regions) - 1)
    return protect


def toHtml(line):
    """An assistant line, mapped onto the tags the Qt rich text engine
    paints -- the reading the panel's transcript is, and nothing else.

    Code and links are read before the prose is escaped, so the ``**``
    of a command and the ``$`` of a path are not swallowed as markup.
    The math is carried the way the page carries it (``mathToUnicode``)
    -- the engine the panel's document is painted by composes none of
    it, measured -- and a line that is not the assistant's own is
    escaped and left exactly as it is.
    """
    if not isAssistantLine(line):
        return _htmlEscape(line)
    regions = []
    protect = _protect(regions)
    src = assistantBody(line)
    # fenced code, inline code, links: read before the prose is escaped
    src = re.sub(r'```(?:\w+\s)?([\s\S]*?)```',
                 lambda m: protect('<pre>' + _htmlEscape(m.group(1).strip('\n'))
                                 + '</pre>'), src)
    src = re.sub(r'`([^`]+)`',
                 lambda m: protect('<code>' + _htmlEscape(m.group(1))
                                  + '</code>'), src)

    def _link(m):
        label, href = m.group(1), m.group(2)
        if not _LINK_OK.match(href) or _LINK_BAD.match(href):
            return _htmlEscape(label)
        return protect('<a href="%s">%s</a>'
                       % (_htmlEscape(href), _htmlEscape(label)))

    src = _LINK_RE.sub(_link, src)
    # the prose: escaped once, then read for the emphasis
    src = _htmlEscape(src)
    src = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', src)
    src = re.sub(r'__([^_]+)__', r'<b>\1</b>', src)
    src = re.sub(r'\*([^*\n]+)\*', r'<i>\1</i>', src)
    # the math: the page's own reading carries it, because the engine
    # this document is painted by composes none of it (measured)
    src = re.sub(r'\$\$([^$]+)\$\$',
                 lambda m: mathToUnicode(m.group(1)), src)
    src = re.sub(r'\$([^$\n]+)\$', lambda m: mathToUnicode(m.group(1)), src)
    # the protected regions come back whole, the markup having gone
    # around them
    src = re.sub(r'\x00(\d+)\x00', lambda m: regions[int(m.group(1))], src)
    # the lead-in, painted the way the page paints its label
    return '<b>LLM:</b> ' + src


def _ansiEnabled():
    """Whether the output a reader is looking at is a terminal that asks
    for codes: a piped or scripted stdout answers no, and ``NO_COLOR``
    is the reader's own word for the same."""
    if os.environ.get('NO_COLOR') is not None:
        return False
    try:
        return sys.stdout.isatty()
    except (AttributeError, ValueError, OSError):
        return False


def toTerminal(line, ansi=None):
    """An assistant line, carried to a reader that composes nothing.

    Bold and italic are the ANSI codes when ``ansi`` is true, and
    neither when it is false; left out, the output answers for itself
    (``_ansiEnabled``). The math is the page's own reading -- the
    tokens to their unicode, ``\\frac`` and ``\\sqrt`` to their
    readable shapes, the unknown kept -- and code and links stay
    spelled: a terminal reads them as the words they are. A line that
    is not the assistant's own comes back exactly as it is.
    """
    if not isAssistantLine(line):
        return line
    if ansi is None:
        ansi = _ansiEnabled()

    def bold(text):
        return '\x1b[1m' + text + '\x1b[0m' if ansi else text

    def italic(text):
        return '\x1b[3m' + text + '\x1b[0m' if ansi else text

    regions = []
    protect = _protect(regions)
    src = assistantBody(line)
    # code and links stay as the reader sees them: protected, not read
    src = re.sub(r'```(?:\w+\s)?([\s\S]*?)```',
                 lambda m: protect(m.group(1).strip('\n')), src)
    src = re.sub(r'`([^`]+)`', lambda m: protect(m.group(1)), src)
    src = _LINK_RE.sub(lambda m: protect(m.group(0)), src)
    # the emphasis, and the math the page's own reading carries
    src = re.sub(r'\*\*([^*]+)\*\*', lambda m: bold(m.group(1)), src)
    src = re.sub(r'__([^_]+)__', lambda m: bold(m.group(1)), src)
    src = re.sub(r'\*([^*\n]+)\*', lambda m: italic(m.group(1)), src)
    src = re.sub(r'\$\$([^$]+)\$\$',
                 lambda m: mathToUnicode(m.group(1)), src)
    src = re.sub(r'\$([^$\n]+)\$', lambda m: mathToUnicode(m.group(1)), src)
    src = re.sub(r'\x00(\d+)\x00', lambda m: regions[int(m.group(1))], src)
    return 'LLM: ' + src
