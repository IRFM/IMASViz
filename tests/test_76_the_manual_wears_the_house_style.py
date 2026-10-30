# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The manual wears the house style, and builds with nothing but Sphinx.

What the user asked for was an appeal: « comment améliorer le style de la
documentation (fonds bleu un peu terne) ? ». The cause of that blue was worth
finding first, and it was not a taste question. ``doc/source/conf.py`` asked for
``sphinx_rtd_theme``, which is **not installed on this node** (measured: of the
themes IMASViz could use, only Sphinx's own are importable -- ``sphinx_rtd_theme``,
``furo``, ``pydata_sphinx_theme``, ``sphinx_book_theme``, ``sphinx_design``,
``sphinx_copybutton`` all answer ``False`` to ``importlib.util.find_spec``, and
Sphinx is 7.2.6), so ``make doc`` stopped with ``no theme named
'sphinx_rtd_theme' found``. A manual nobody can rebuild keeps whatever it shipped
with -- the pale-blue admonition boxes, the 2018 layout -- and the two warnings
its own ``conf.py`` produced on every build (``language = None`` and the pre-1.0
``intersphinx_mapping`` form) went unread for the same reason.

So the look now lives in ``doc/source/_static/imasviz.css``, written against the
markup of Sphinx's own ``basic`` theme, and a build needs nothing but Sphinx.
Measured after the change: a quiet build over the whole manual answers exit **0**
and **no output at all** in **3,8 s** (before: exit 2 on the theme, and with a
theme forced, 2 warnings). ``basic`` was chosen over ``alabaster`` because it is
part of Sphinx itself and because its markup is the one this sheet was written
against -- ``div.related``, ``div.document``, ``div.body``, ``div.sphinxsidebar``.

Why a test file checks CSS at all: nobody can look at a stylesheet in a test run,
and a stylesheet is a program -- an unbalanced brace, a variable nothing declares,
a rule that reaches across the network, and the manual silently loses its look on
a node where the build still says success. So the sheet is checked the way a
program is: it parses, every name it uses is defined, the two themes define the
same names, and every colour a reader has to read clears the contrast floor on
the ground it is painted on -- the same floor the curve palettes are held to.

One agreement is pinned here and matters beyond the manual: the colour block of
``imasviz.css`` is the **same** palette ``QVizStyle`` paints the application with.
See ``test_77`` for the application side of it.
"""

import ast
import contextlib
import io
import os
import re
import xml.etree.ElementTree as ElementTree
from types import SimpleNamespace

import pytest

import sphinx

from conftest import REPO_ROOT

DOC = os.path.join(REPO_ROOT, 'doc')
SOURCE = os.path.join(DOC, 'source')
STATIC = os.path.join(SOURCE, '_static')
CONF = os.path.join(SOURCE, 'conf.py')
INDEX = os.path.join(SOURCE, 'index.rst')
CSS = os.path.join(STATIC, 'imasviz.css')
JS = os.path.join(STATIC, 'imasviz.js')
ICON = os.path.join(STATIC, 'imasviz_icon.svg')
MARK = os.path.join(REPO_ROOT, 'resources', 'VizIcons', 'imasviz_mark.svg')

# Body text has to clear WCAG AA; a graphic element clears 3:1, and the mark is
# one (see test_the_mark_is_valid_svg...).
CONTRAST_FLOOR = 4.5
GRAPHIC_FLOOR = 3.0

# What each colour is painted on, in the sheet: the text tokens sit on the three
# grounds a page is made of, the accent is a link on those same grounds.
GROUNDS = ('surface', 'surface-alt', 'field', 'canvas')
TEXT_TOKENS = ('ink', 'ink-soft', 'ink-faint', 'accent')

# The pairs where the sheet turns the rule around: the log panel, the selection,
# the active line of the navigation. Each has a ground of its own with one ink on
# it, and each is a thing a reader has to read.
INVERTED_PAIRS = (('log-info', 'log-ground'), ('log-warn', 'log-ground'),
                  ('log-error', 'log-ground'), ('on-selection', 'selection'),
                  ('accent-strong', 'accent-soft'))


def read(path):
    with open(path) as handle:
        return handle.read()


def uncommented(text):
    """The same file with its comments taken out.

    Every file of this repository carries a licence header with a URL in it, and a
    check that a script reaches no network has to ask the code, not the licence.
    """
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    return re.sub(r'(?m)^\s*//.*$', '', text)



def confValue(name):
    """One assignment of ``conf.py``, read without importing it."""
    for node in ast.parse(read(CONF)).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError('%s is not set in conf.py' % name)


def luminance(rgb):
    def channel(value):
        value = value / 255.0
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(value) for value in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(first, second):
    lighter, darker = max(luminance(first), luminance(second)), \
                      min(luminance(first), luminance(second))
    return (lighter + 0.05) / (darker + 0.05)


def rgbOf(hexText):
    text = hexText.lstrip('#')
    return tuple(int(text[i:i + 2], 16) for i in (0, 2, 4))


def tokenBlock(kind):
    """The declared colours of one theme, as ``{name: '#rrggbb'}``.

    The block is delimited in the sheet on purpose: the colours of the manual and
    the colours of the application are one agreement, and an agreement needs a
    border to be checkable.
    """
    found = re.search(r'/\* tokens:begin %s \*/(.*?)/\* tokens:end %s \*/'
                      % (kind, kind), read(CSS), re.S)
    assert found is not None, 'no tokens:begin %s block in imasviz.css' % kind
    pairs = re.findall(r'(--[\w-]+):\s*([^;]+);', found.group(1))
    colours = {}
    for name, value in pairs:
        value = value.strip()
        if value.startswith('#'):
            colours[name[2:]] = value
    assert colours, 'the %s token block holds no colour' % kind
    return colours


def declaredVariables():
    """Every custom property the sheet defines, colours and metrics together."""
    return {name[2:] for name in re.findall(r'(--[\w-]+):', read(CSS))}


def namesOf(tokens):
    return ', '.join(sorted(tokens))


@pytest.fixture(scope='module')
def build(tmp_path_factory):
    """The manual, built the way ``make doc`` builds it -- and once.

    In process, quietly, into a throwaway folder, with the warnings sent to a file
    of their own: that file is what "the build says nothing" is read from, because
    ``-q`` silences the console without silencing the build's complaints. Measured:
    3,8 s for the whole manual, exit 0, an empty warning file.
    """
    from sphinx.cmd.build import build_main

    out = str(tmp_path_factory.mktemp('manual'))
    warnings = os.path.join(out, 'warnings.txt')
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
        status = build_main(['-q', '-b', 'html', '-w', warnings, SOURCE, out])

    return SimpleNamespace(folder=out, status=status,
                           output=captured.getvalue(),
                           notes=read(warnings) if os.path.exists(warnings) else '')


# ---------------------------------------------------------------------------
# A build that works, on a node that has nothing but Sphinx
# ---------------------------------------------------------------------------

def test_the_theme_asked_for_is_one_sphinx_ships():
    """The whole failure this row is about: a theme named and not installed.

    ``make doc`` answered ``Theme error: no theme named 'sphinx_rtd_theme' found
    (missing theme.conf?)`` and stopped. A manual that cannot be rebuilt does not
    get restyled, which is how the blue boxes survived.
    """
    theme = confValue('html_theme')
    themes = os.listdir(os.path.join(os.path.dirname(sphinx.__file__), 'themes'))
    assert theme in themes, '%r is not one of %s' % (theme, sorted(themes))


def test_the_documented_route_builds_it_without_an_override(build):
    """The recipe this node used to need was ``-D html_theme=alabaster``.

    Neither Makefile passes one any more, so what the manual says to run is what
    actually works -- measured on the plain build the fixture just ran.
    """
    for makefile in (os.path.join(REPO_ROOT, 'Makefile'),
                     os.path.join(DOC, 'Makefile')):
        assert '-D html_theme' not in read(makefile), makefile
    assert build.status == 0, build.output


def test_the_build_says_nothing(build):
    """Exit 0 and an empty warning file. Before: exit 2, and 2 warnings forced."""
    assert build.status == 0, build.output
    assert build.notes.strip() == '', build.notes
    assert 'warning' not in build.output.lower(), build.output


def test_the_pages_of_the_manual_came_out(build):
    built = os.path.join(build.folder, 'index.html')
    assert os.path.exists(built)
    for part in ('manual/user_preferences.html', 'manual/other_GUI_features.html',
                 'howto/plugins/plugin_getting_started.html'):
        assert os.path.exists(os.path.join(build.folder, part)), part


# ---------------------------------------------------------------------------
# What the built page links, and in which order
# ---------------------------------------------------------------------------

def test_the_house_sheet_is_loaded_after_the_theme(build):
    """Equal specificity, so the order is the whole argument.

    ``basic.css`` lays the page out with floats; the house sheet re-lays it out.
    Loaded before it, the manual would come out as ``basic`` with a hint of colour.
    """
    assert 'imasviz.css' in confValue('html_css_files')
    page = read(os.path.join(build.folder, 'index.html'))
    # The built href carries a content hash Sphinx appends (``?v=8a249c91``), so
    # the file name is what sits before the query, not before the quote.
    links = re.findall(
        r'<link rel="stylesheet"[^>]*href="[^"]*?([\w.-]+\.css)(?:\?[^"]*)?"',
        page)
    assert links.index('imasviz.css') > links.index('basic.css'), links


def test_the_theme_control_is_on_every_page(build):
    assert 'imasviz.js' in confValue('html_js_files')
    page = read(os.path.join(build.folder, 'index.html'))
    assert 'imasviz.js' in page


def test_the_mark_is_in_the_header_and_in_the_tab(build):
    for option in ('html_logo', 'html_favicon'):
        target = confValue(option)
        assert target.startswith('_static/'), '%s points at %r' % (option, target)
        assert os.path.exists(os.path.join(SOURCE, target)), target
    page = read(os.path.join(build.folder, 'index.html'))
    assert 'class="logo"' in page
    assert os.path.exists(os.path.join(build.folder, '_static/imasviz_icon.svg'))


def test_the_navigation_column_holds_the_tree_and_the_search_box(build):
    """And not the source link: a user manual is not read from its ``.rst``."""
    sidebars = confValue('html_sidebars')['**']
    assert 'globaltoc.html' in sidebars
    assert 'searchbox.html' in sidebars
    assert 'sourcelink.html' not in sidebars
    assert confValue('html_show_sourcelink') is False
    page = read(os.path.join(build.folder, 'index.html'))
    assert 'main navigation' in page, 'no navigation column on the page'
    assert '<form' in page and 'search' in page, 'no search box in the column'
    assert 'Source page' not in page


# ---------------------------------------------------------------------------
# The sheet, checked the way a program is checked
# ---------------------------------------------------------------------------

def test_the_sheet_balances_and_reaches_no_network():
    """A stylesheet is a program: an unbalanced brace loses everything after it."""
    sheet = read(CSS)
    assert sheet.count('{') == sheet.count('}'), 'unbalanced braces'
    assert '@import' not in sheet, 'a manual that fetches a stylesheet is a manual ' \
                                   'that fails offline'
    assert 'url(http' not in sheet and 'url(//' not in sheet
    assert not re.search(r'\burl\(\s*["\']?https?:', sheet)
    assert '&' not in sheet, 'a nested selector: plain CSS has no &'


def test_every_variable_the_sheet_uses_is_declared():
    """A name nothing defines resolves to nothing, and the rule is dropped."""
    declared = declaredVariables()
    used = {name for name in re.findall(r'var\((--[\w-]+)', read(CSS))}
    missing = sorted({name[2:] for name in used} - declared)
    assert missing == [], 'used but never declared: %s' % namesOf(missing)


def test_the_two_themes_declare_the_same_colours():
    """A theme missing one token paints that one thing with the other theme's ink."""
    light, dark = tokenBlock('light'), tokenBlock('dark')
    assert set(light) == set(dark), 'light-only %s / dark-only %s' % (
        namesOf(set(light) - set(dark)), namesOf(set(dark) - set(light)))
    for name, value in list(light.items()) + list(dark.items()):
        assert re.fullmatch(r'#[0-9a-f]{6}', value), '%s is %r' % (name, value)


def test_every_colour_a_reader_has_to_read_clears_the_contrast_floor():
    """The same floor the curve palettes are held to, for the same reason.

    Measured on the sheet as written: the weakest pair answers **4,77** --
    ``ink-faint`` on ``canvas``, the ink of a caption on the page ground. The
    first value tried, ``#6b7784``, answered 4,33 on ``surface-alt``, 4,24 on
    ``field`` and 4,03 on ``canvas``: a caption nobody can read, and a build that
    says nothing about it.
    """
    for kind in ('light', 'dark'):
        tokens = tokenBlock(kind)
        for text in TEXT_TOKENS:
            for ground in GROUNDS:
                ratio = contrast(rgbOf(tokens[text]), rgbOf(tokens[ground]))
                assert ratio >= CONTRAST_FLOOR, \
                    '%s: %s on %s (%s) answers %0.2f' % (
                        kind, text, ground, tokens[ground], ratio)
        for text, ground in INVERTED_PAIRS:
            ratio = contrast(rgbOf(tokens[text]), rgbOf(tokens[ground]))
            assert ratio >= CONTRAST_FLOOR, \
                '%s: %s on %s (%s) answers %0.2f' % (
                    kind, text, ground, tokens[ground], ratio)


def test_the_button_names_itself_in_a_legible_colour():
    """A filled button is the one place the ink is the accent and the accent the ground."""
    # That ink has its own token, ``--on-accent``, because it is the one colour
    # that flips between the themes: white on the dark accent of the light page,
    # near-black on the light accent of the dark one. Reading it off ``surface``
    # or ``canvas`` would have passed while the sheet painted something else.
    for kind in ('light', 'dark'):
        tokens = tokenBlock(kind)
        assert 'on-accent' in tokens, '%s declares no --on-accent' % kind
        assert contrast(rgbOf(tokens['on-accent']),
                        rgbOf(tokens['accent'])) >= CONTRAST_FLOOR, \
            '%s: on-accent on accent answers %0.2f' % (
                kind, contrast(rgbOf(tokens['on-accent']), rgbOf(tokens['accent'])))


def test_the_sheet_is_not_the_blue_it_replaces():
    """The report was « fonds bleu un peu terne ».

    The boxes that read that way are the admonitions of the theme this sheet
    replaces, whose grounds are ``#eff9ff`` and ``#e7f2fa``. Refusing those two
    hexes by name is cheap insurance that the pale blue is not back under another
    token.
    """
    sheet = read(CSS).lower()
    for dull in ('#eff9ff', '#e7f2fa', '#2980b9', '#343131', '#fcfcfc'):
        assert dull not in sheet, 'the sheet is painting %s again' % dull


# ---------------------------------------------------------------------------
# The control
# ---------------------------------------------------------------------------

def test_the_control_picks_the_theme_before_the_first_paint():
    """A page that arrives light and turns dark a frame later is worse than one
    that was dark all along. So the attribute is set before the control exists."""
    script = read(JS)
    assert script.index('documentElement.setAttribute') < \
        script.index('DOMContentLoaded')
    assert 'localStorage' in script
    assert 'prefers-color-scheme' in script


def test_the_control_reaches_nothing_over_the_network():
    """Asked of the code, not of the licence header, which does carry a URL."""
    script = uncommented(read(JS))
    for away in ('fetch(', 'XMLHttpRequest', 'import(', 'http'):
        assert away not in script, 'the theme control asks for %s' % away


# ---------------------------------------------------------------------------
# The mark, and the copy the manual keeps of it
# ---------------------------------------------------------------------------

def test_the_manual_shows_the_mark_the_application_ships():
    """One mark, two places. A copy that drifts is a brand with two faces."""
    assert read(ICON) == read(MARK), \
        'doc/source/_static/imasviz_icon.svg is not resources/VizIcons/imasviz_mark.svg'


def test_the_mark_is_valid_svg_and_does_not_ask_for_currentColor():
    """An image is an isolated document: ``currentColor`` there answers black,
    which on the dark theme is an invisible logo and on every theme a black one.

    Asked of the markup, not of the comment that explains why it is not used.
    """
    markup = re.sub(r'<!--.*?-->', '', read(MARK), flags=re.S)
    ElementTree.fromstring(read(MARK))
    assert 'currentColor' not in markup
    assert '#1493a8' in markup


def test_the_mark_clears_the_floor_a_graphic_element_has_to_clear():
    """3:1, on the two grounds it is drawn on: the light surface and the dark one."""
    ink = rgbOf('#1493a8')
    for kind in ('light', 'dark'):
        tokens = tokenBlock(kind)
        for ground in ('surface', 'surface-alt', 'canvas'):
            ratio = contrast(ink, rgbOf(tokens[ground]))
            assert ratio >= GRAPHIC_FLOOR, '%s on %s/%s answers %0.2f' % (
                kind, ground, tokens[ground], ratio)


# ---------------------------------------------------------------------------
# The landing page
# ---------------------------------------------------------------------------

def headingOf(page):
    """The title of an RST page: the line its own underline sits on."""
    lines = page.splitlines()
    for index, line in enumerate(lines[1:], start=1):
        if re.fullmatch(r'={3,}', line.strip() or '') and lines[index - 1].strip():
            return lines[index - 1].strip()
    raise AssertionError('the page has no title')


def test_the_landing_page_names_the_tool():
    """It said ``Welcome to IMASViz's documentation!`` since sphinx-quickstart 2018."""
    page = read(INDEX)
    assert headingOf(page) == 'IMASViz'
    assert "Welcome to IMASViz's documentation" not in page


def test_the_landing_page_points_three_ways_in():
    page = read(INDEX)
    for part in (':doc:`intro/index`', ':doc:`manual/index`', ':doc:`howto/index`'):
        assert part in page, part
    assert '.. toctree::' in page, 'the root toctree is what makes the navigation'


def test_every_page_of_the_manual_is_in_the_tree(build):
    """A page no toctree points at is written and never reachable.

    The manual is 21 sources; the navigation column is drawn from the tree, so a
    page outside it is a page a reader cannot get to -- and the only thing that
    says so is a build warning nobody reads.
    """
    sources = []
    for folder, _ignored, files in os.walk(SOURCE):
        for name in files:
            if name.endswith('.rst'):
                sources.append(os.path.relpath(os.path.join(folder, name), SOURCE))
    assert len(sources) == 21, sources
    for source in sources:
        page = os.path.join(build.folder, source[:-4] + '.html')
        assert os.path.exists(page), '%s did not come out' % source
        assert 'main navigation' in read(page), '%s has no navigation' % source


# ---------------------------------------------------------------------------
# The extensions that asked something of the build this node cannot give
# ---------------------------------------------------------------------------

def test_the_manual_no_longer_reaches_the_network_to_build():
    """Nothing in the manual points outside it -- not one ``:py:`` role is written
    -- so the inventory fetch answered no link and one warning per build."""
    extensions = confValue('extensions')
    assert 'sphinx.ext.intersphinx' not in extensions
    assert 'sphinx.ext.coverage' not in extensions
    assert 'sphinx.ext.autodoc' in extensions, 'kept: API pages may still come'
    assert 'intersphinx_mapping' not in read(CONF), \
        'a leftover mapping is an unknown configuration value once its extension is gone'


def test_the_manual_says_what_language_it_is_written_in():
    """``language = None`` took the build machine's locale and said so, every build."""
    assert confValue('language') == 'en'
