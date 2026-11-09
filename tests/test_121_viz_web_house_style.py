# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""What `viz_web` may be made of, and the colours the page wears.

Two halves of the same agreement, the way `test_76` and `test_77` pin it for
the manual and the application:

* **what the package is made of.** Every module of `viz_web` imports against
  the real Qt binding (the smoke check `test_99` gives the `imasviz` package),
  and nothing in it reaches for a web framework this node does not hold:
  `flask` and `fastapi` are refused by name, because the page is served by
  `starlette` and `uvicorn`, both present, and a framework that is imported
  but not installed is a run that dies at import with no window.

* **the colours the page wears.** One self-contained page, no build, and the
  colours are the application's: the `tokens:begin`/`tokens:end` block of
  `viz_web/static/index.html` is checked, token by token and theme by theme,
  against `QVizStyle.TOKENS`, the one table the application paints from. The
  page's block holds both themes in one region (`:root, [data-theme="light"]`
  and `[data-theme="dark"]`), so this test takes each theme's rule out of that
  region and reads its `--name: value` pairs -- the border the agreement needs
  to be checkable, the same `test_77` reads on `imasviz.css`.
"""

import ast
import importlib
import os
import re

import pytest

from imasviz.VizGUI.VizGuiCustomization import QVizStyle

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE = 'viz_web'
PACKAGE_DIR = os.path.join(REPO_ROOT, PACKAGE)
INDEX = os.path.join(PACKAGE_DIR, 'static', 'index.html')


# ------------------------------------------------------------------ the package

def collectModules():
    """Every importable module of `viz_web`, the way `test_99` walks `imasviz`."""
    names = []
    for dirpath, dirnames, fileNames in os.walk(PACKAGE_DIR):
        if '__pycache__' in dirpath:
            continue
        packageName = dirpath[len(REPO_ROOT) + 1:].replace(os.sep, '.')
        for fileName in sorted(fileNames):
            if not fileName.endswith('.py'):
                continue
            moduleName = fileName[:-3]
            names.append(packageName if moduleName == '__init__'
                         else packageName + '.' + moduleName)
    return sorted(set(names))


MODULES = collectModules()


def test_the_package_walks():
    # A discovery that found nothing would pass the rest of the file for no
    # reason: an empty list is a guard broken, not an agreement kept.
    assert 'viz_web' in MODULES
    assert 'viz_web.server' in MODULES
    assert 'viz_web.web_session' in MODULES
    assert 'viz_web.run' in MODULES


@pytest.mark.parametrize('moduleName', MODULES)
def test_every_module_imports(moduleName):
    importlib.import_module(moduleName)


def test_no_web_framework_the_node_does_not_hold():
    """`flask` and `fastapi` are refused where the page is served.

    The run dies at import with no window and no named refusal when a module
    asks for a package the node does not carry; `starlette` and `uvicorn`,
    both present, are the ones the run is built on. Measured: `import flask`
    and `import fastapi` are both `ModuleNotFoundError` on this node.
    """
    refused = []
    for dirpath, dirnames, fileNames in os.walk(PACKAGE_DIR):
        if '__pycache__' in dirpath:
            continue
        for fileName in fileNames:
            if not fileName.endswith('.py'):
                continue
            path = os.path.join(dirpath, fileName)
            with open(path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split('.')[0] in ('flask', 'fastapi'):
                            refused.append('%s: import %s' % (fileName, alias.name))
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.split('.')[0] in ('flask', 'fastapi'):
                        refused.append('%s: from %s import' % (fileName, node.module))
    assert not refused, 'refuse the frameworks this node does not hold: ' + '; '.join(refused)


# -------------------------------------------------------------------- the colours

def _region(text):
    """The `tokens:begin`/`tokens:end` region of the page, and nothing else."""
    found = re.search(r'/\* tokens:begin \*/(.*?)/\* tokens:end \*/', text, re.S)
    assert found is not None, 'no tokens:begin/tokens:end block in index.html'
    return found.group(1)


def _themeRule(region, theme):
    """The declaration block the page gives one theme, and nothing else.

    The region holds both themes; the rule names the theme, and the selector
    before it may carry a fallback (the light one is `:root, [data-theme="light"]`),
    which is why the selector is refused before the block is read.
    """
    pattern = r'[^\n{]*\[\s*data-theme\s*=\s*"%s"\s*\]\s*\{([^}]*)\}' % theme
    found = re.search(pattern, region, re.S)
    assert found is not None, 'no data-theme="%s" rule in the token region' % theme
    return found.group(1)


def declaredTokens(theme):
    """The colours the page declares of one theme, `{name: '#rrggbb'}`."""
    with open(INDEX, 'r', encoding='utf-8') as f:
        text = f.read()
    body = _themeRule(_region(text), theme)
    pairs = re.findall(r'(--[\w-]+)\s*:\s*([^;]+)\s*;', body)
    tokens = {name[2:]: value.strip() for name, value in pairs}
    assert tokens, 'the %s token rule holds no colour' % theme
    return tokens


@pytest.mark.parametrize('theme', QVizStyle.NAMES)
def test_the_page_wears_the_application_s_colours(theme):
    """Token by token, theme by theme: the same palette on screen and in code.

    `QVizStyle.TOKENS` is the one table the application paints from, the one
    the *Windows* menu and the log are checked against (`test_77`), and the
    one the manual wears (`test_76`). The page is the third place the same
    table must hold; a colour that drifts in only one of them is named here,
    not left for the user to see as the wrong grey.
    """
    onThePage = declaredTokens(theme)
    inTheApplication = QVizStyle.TOKENS[theme]
    assert set(inTheApplication) == set(onThePage), \
        '%s: only the app has %s / only the page has %s' % (
            theme,
            ', '.join(sorted(set(inTheApplication) - set(onThePage))),
            ', '.join(sorted(set(onThePage) - set(inTheApplication))))
    for name, value in sorted(inTheApplication.items()):
        assert onThePage[name] == value, \
            '%s: %s is %s in the application and %s on the page' % (
                theme, name, value, onThePage[name])


def test_the_page_wears_both_themes():
    """The light and the dark: the page's two themes, and the toggle that
    flips between them, so the user is never left on the wrong half."""
    with open(INDEX, 'r', encoding='utf-8') as f:
        text = f.read()
    assert 'data-theme="light"' in text
    assert 'data-theme="dark"' in text
    assert 'viz_web_theme' in text, 'no stored choice of theme for the page'


def test_the_page_keeps_its_screenshots_and_can_act_on_them():
    """The screenshots are the point of the page, and the page keeps them.

    What it pins: the gallery accumulates a request instead of replacing
    the previous ones, and the pictures are rebuilt from `/api/turns` on
    load -- served from the request's directory on disk
    (`/api/turns/{n}/shots/…`), which is what makes a reload of the page
    cost nothing. Each picture is addressed to the window it shows (the
    name `focus_window` and `get_screenshot` take), and a click
    enlarges it in the lightbox.
    """
    with open(INDEX, 'r', encoding='utf-8') as f:
        text = f.read()
    # The gallery, and that it is rebuilt from the request history on load.
    assert 'buildGallery' in text, 'no rebuild of the gallery from /api/turns'
    assert '/api/turns' in text, 'the gallery is not served from the request history'
    assert '/shots/' in text, 'the pictures are not served from the request directories'
    assert 'prependTurnShots' in text, 'a request replaces the previous ones, not joins them'
    # The address of a picture, and the two gestures it answers.
    assert 'image_windows' in text, 'the cards are not addressed to the window they show'
    assert 'focus_window' in text, 'no Focus button on the screenshot cards'
    assert 'get_screenshot' in text, 'no Screenshot button on the screenshot cards'
    # The enlargement, and the section the page calls it by.
    assert 'lightbox' in text, 'a picture has no way to be read full size'
    assert 'Screenshots' in text


def test_the_page_groups_the_captures_per_request():
    """One group per request, closed until it is opened.

    What it pins: a capture group is a `details` (collapsed until the
    user opens it, so the page shows the request names and their counts,
    not a wall of pictures), the groups are named by the request number
    (the "Request 3" the user reads, not the "Turn" it used to read),
    and the reports take the same grouping -- a request names the ones
    it wrote, and the ones none of the requests wrote sit together
    under their own name. The rarely used raw gestures sit in a closed
    section of the agent's column, not in a column of their own.
    """
    with open(INDEX, 'r', encoding='utf-8') as f:
        text = f.read()
    # The collapsible group of the captures, and its closed-until-asked
    # reading: a `details` the page builds, one per request.
    assert 'shotGroup' in text, 'no per-request group for the captures'
    # The naming: the request, not the turn.
    assert 'Request ' in text, 'the groups are not named by the request'
    assert 'Requests' in text, 'no list of the requests of the session'
    # The reports grouped the way the captures are, and the folder named.
    assert 'reportGroup' in text, 'no per-request group for the reports'
    assert 'Earlier requests' in text, 'no group for the reports none of the requests wrote'
    assert 'reportsFolder' in text, 'the folder a report either is or is not is not named'
    # The raw gestures: a closed section, not a column.
    assert 'rawGestures' in text, 'no closed section for the raw gestures'
    assert 'id="tools"' not in text, 'the gestures are still a column of their own'


def test_the_page_is_english():
    """The interface the user reads is in the language the user reads.

    What it pins: the buttons and the empty states stand in English --
    the Run / Stop / Clear of the agent, the empty of the captures --
    and the French the page carried before does not stand in the visible
    strings. The transcript is the loop's, and the loop answers as it
    answers, so it is not what this pins.
    """
    with open(INDEX, 'r', encoding='utf-8') as f:
        text = f.read()
    # The buttons the user presses.
    assert '>Run<' in text, 'no Run button'
    assert '>Stop<' in text, 'no Stop button'
    assert '>Clear<' in text, 'no Clear button'
    # The French the page carried is the one gone from the visible
    # strings: the buttons and the empties the user reads.
    for gone in ('>Tourner<', '>Arrêter<', '>Effacer<',
                 'Aucun screenshot'):
        assert gone not in text, 'the visible strings still hold the French: %s' % gone
    # The page's own name, in the language it is read.
    assert 'lang="en"' in text, 'the page does not name its language'
    assert 'the agent, offscreen' in text, 'the page does not name itself'
