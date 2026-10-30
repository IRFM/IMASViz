# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The application wears the house theme, and the manual and it wear the same one.

The second half of « améliorer le style de la documentation et de l'interface ».
The manual was dressed first (T47); this file holds the two things that make the
application's dress worth trusting:

**One palette, not two.** The colour block of ``imasviz.css`` and ``QVizStyle.
TOKENS`` are checked to define the same names with the same values, theme by
theme. A tool and the book about it drifting into two palettes is not a cosmetic
affair -- it is the point at which the screenshots stop being the product. The
font stack is checked the same way: the families ``QVizStyle.FONT_FAMILIES`` are
the head of the CSS ``--font-sans`` list.

**A theme that is really on screen.** Nobody can look at a stylesheet in a test
run, and a Qt style sheet fails quietly: a selector that matches nothing paints
nothing and says nothing. Two rules that looked perfectly right and measured
false are the reason this file samples pixels instead of reading strings -- a
``background`` on ``QMdiArea`` (the widget paints its own ground, taken once at
construction from ``QPalette::Dark``) and a ``QStatusBar#statusbar`` (an id the
main window's bar does not carry). So the chrome is rendered and the pixels are
compared with the tokens, in both themes.

What is deliberately pinned the other way: **a plot keeps its black ground.**
pyqtgraph paints ``'background': 'k'`` behind every figure and the two trace
palettes, the colour maps and the slice-line colours were all measured against
that black (T33, T34, T44, T45). A theme reaching a ``QGraphicsView`` would
silently invalidate every one of those measurements, so one test renders a plot
under each theme and refuses to let it be anything but ``#000000``.

The measured numbers this file stands on, all taken on this node with
``QT_QPA_PLATFORM=offscreen``: the MDI ground before the palette named ``Dark``
was ``#9f9f9f`` in both themes (Qt's own derived grey); the chrome after, per
theme, is ``#ffffff``/``#181d22`` for a tree, ``#f4f7f8``/``#12171b`` for an
input, ``#f6f8f9``/``#12171b`` for the log, ``#eef1f3``/``#0f1317`` for the
canvas. The family ``QFontInfo`` resolves from the house stack here is
``Cantarell``; ``QFont('Open Sans')`` -- the family ``GlobalFonts`` used to name
on all four of its fonts -- resolves to ``DejaVu Sans``, which is what every
label of the application was actually drawn with.
"""

import logging
import os
import re

import pytest

from conftest import REPO_ROOT
from support.ownership import keep
from test_76_the_manual_wears_the_house_style import contrast, rgbOf, tokenBlock

from PySide6.QtGui import QFont, QFontInfo, QPalette
from PySide6.QtWidgets import (QLineEdit, QMdiArea, QMdiSubWindow,
                               QLabel, QPlainTextEdit, QPushButton, QStyle,
                               QTreeWidget, QTreeWidgetItem)

import pyqtgraph as pg

from imasviz.VizGUI.VizGuiCustomization import QVizStyle
from imasviz.VizGUI.VizWidgets.VizNodeDocumentation.QVizNodeDocumentationPanel import (
    QVizNodeDocumentationPanel)
from imasviz.VizUtils import GlobalColors, GlobalFonts, QVizPreferences, QVizLogger

CSS = os.path.join(REPO_ROOT, 'doc', 'source', '_static', 'imasviz.css')

# The same floor the manual and the curve palettes are held to.
CONTRAST_FLOOR = 4.5

# What a preference line of each kind looks like in the manual, and what it has
# to answer. Six names of colours, two spellings of a hex, and the index the old
# reader took.
COLOUR_OPTIONS = (
    ('#ff0000', '#ff0000'),
    ('ff0000', '#ff0000'),
    ('red', '#ff0000'),
    ('#0b7285', '#0b7285'),
)

# What neither spelling can mean. ``QColor`` accepts a Qt colour name, so the
# refusals have to be things no name, no hex and no index can read.
BAD_COLOURS = ('pas_une_couleur', '#gg0000', '9')


@pytest.fixture(autouse=True)
def privateHome(tmp_path, monkeypatch):
    """A ``$HOME`` of one's own for the whole file, and nothing left behind.

    The preferences file lives at ``$HOME/.imasviz/preferences``, and a test that
    lets ``QVizPreferences.build()`` read the real one reads whatever the machine
    happens to hold -- and writes the class attributes of ``QVizPreferences`` for
    the rest of the run. Every attribute ``build()`` may set is therefore saved
    here and put back, not only the theme: a test that turns ``Ignore_GGD=0`` on
    would otherwise hand the next file a different application.
    """
    (tmp_path / '.imasviz').mkdir()
    monkeypatch.setenv('HOME', str(tmp_path))
    saved = {name: getattr(QVizPreferences, name) for name in (
        'Theme', 'SelectionColor', 'ColorOfNodesContainingData',
        'Allow_data_to_be_plotted_with_different_units', 'Ignore_GGD',
        'Auto_save_session', 'userPreferencesInitialized')}
    try:
        yield tmp_path
    finally:
        for name, value in saved.items():
            setattr(QVizPreferences, name, value)


@pytest.fixture(params=QVizStyle.NAMES)
def dressed(request, qapp):
    """The application dressed in one of the two themes, and undressed after.

    The ``QApplication`` of a pytest-qt session is one object for the whole run,
    so dressing it is a change to every test that comes after: the style, the
    palette, the sheet, the font, the window icon and the four ``GlobalFonts``
    are all taken back down at the teardown. ``standardPalette`` is asked of the
    style *before* anything is put on it, because once a sheet is set the style
    is a proxy and no longer answers for the platform's own colours.
    """
    before = {'style': qapp.style().objectName() or 'Fusion',
              'palette': qapp.style().standardPalette(),
              'font': qapp.font(),
              'icon': qapp.windowIcon(),
              'theme': QVizPreferences.Theme,
              'family': GlobalFonts.FAMILY}
    QVizPreferences.Theme = request.param
    chosen = QVizStyle.applyToApplication(qapp)
    assert chosen == request.param
    try:
        yield chosen
    finally:
        qapp.setStyleSheet('')
        qapp.setStyle(before['style'])
        qapp.setPalette(before['palette'])
        qapp.setFont(before['font'])
        qapp.setWindowIcon(before['icon'])
        QVizPreferences.Theme = before['theme']
        GlobalFonts.useFamily(before['family'])


def pixels(widget):
    """The widget rendered to an image -- without being shown.

    ``grab()`` paints a widget that is not on screen, which is what keeps this
    file out of the hazard ``support/ownership`` exists for: a widget that is
    never shown is never owed a paint event by a queue outliving its wrapper.
    """
    return widget.grab().toImage()


def ground(widget, x, y):
    image = pixels(widget)
    colour = image.pixelColor(x, y)
    return '#%02x%02x%02x' % (colour.red(), colour.green(), colour.blue())


def stylesheetOf(kind):
    """The whole ``QVizStyle`` sheet of one theme."""
    return QVizStyle.styleSheet(kind)


def ruleFor(selector, kind):
    """The declarations of one selector of the sheet, and nothing else.

    A test that reads the whole sheet for a colour proves nothing: a colour that
    appears somewhere says nothing about which widget it was written for. This
    takes the block that names the selector and nothing but that block, which is
    how the documentation panel and the log can be refused two different answers
    to the same question.
    """
    sheet = stylesheetOf(kind)
    at = sheet.find(selector)
    assert at >= 0, 'nothing in the %s sheet names %s' % (kind, selector)
    opening = sheet.index('{', at)
    return sheet[opening + 1:sheet.index('}', opening)]


# --------------------------------------------------------------- one palette --

@pytest.mark.parametrize('kind', QVizStyle.NAMES)
def test_the_application_and_the_manual_wear_the_same_colours(kind):
    """Token by token, theme by theme: the same palette or a named difference.

    ``test_76`` checks the manual's block against itself (both themes define the
    same names, every value a ``#rrggbb``). This is the other half of the
    agreement: the table the application paints with is the same table.
    """
    fromTheManual = tokenBlock(kind)
    fromTheApplication = QVizStyle.TOKENS[kind]
    assert set(fromTheApplication) == set(fromTheManual), \
        '%s: only the app has %s / only the manual has %s' % (
            kind,
            ', '.join(sorted(set(fromTheApplication) - set(fromTheManual))),
            ', '.join(sorted(set(fromTheManual) - set(fromTheApplication))))
    for name, value in sorted(fromTheManual.items()):
        assert fromTheApplication[name] == value, \
            '%s: %s is %s in the manual and %s in the application' % (
                kind, name, value, fromTheApplication[name])


def test_the_application_asks_for_the_head_of_the_manual_s_font_stack():
    """The families the chrome asks for are the manual's, in the manual's order.

    Only the head is shared, and that is the honest agreement: the CSS list goes
    on with ``system-ui`` and ``-apple-system``, which are a browser's business
    and mean nothing to ``QFont``.
    """
    with open(CSS) as handle:
        declared = re.search(r'--font-sans:\s*([^;]+);', handle.read())
    assert declared is not None, 'no --font-sans in %s' % CSS
    stack = [one.strip().strip('"').strip("'")
             for one in declared.group(1).split(',')]
    assert stack[:len(QVizStyle.FONT_FAMILIES)] == list(QVizStyle.FONT_FAMILIES), \
        'the CSS stack starts %s, QVizStyle asks %s' % (
            stack[:5], list(QVizStyle.FONT_FAMILIES))


def test_both_themes_answer_the_same_questions():
    """``colour()`` takes a name, and a name missing from one theme is a bug."""
    for kind in QVizStyle.NAMES:
        for token in sorted(QVizStyle.TOKENS[kind]):
            assert QVizStyle.colour(token, kind) == QVizStyle.TOKENS[kind][token]


def test_an_unknown_theme_is_refused_by_its_name():
    """A preference typed by hand is where a theme name goes wrong.

    ``KeyError: 'Night'`` is not an answer anyone can do anything with; the
    refusal names what was asked and what IMASViz actually wears.
    """
    with pytest.raises(ValueError) as raised:
        QVizStyle.forName('Night')
    refused = str(raised.value)
    assert 'Night' in refused, refused
    for known in QVizStyle.NAMES:
        assert known in refused, '%s does not say it wears %s: %s' % (
            refused, known, refused)


def test_an_unknown_colour_is_refused_the_same_way():
    with pytest.raises(ValueError) as raised:
        QVizStyle.colour('chartreuse-du-fond', 'light')
    assert 'chartreuse-du-fond' in str(raised.value)


def test_the_default_theme_is_the_one_the_manual_is_read_on():
    """Light, and a name the tool actually wears -- not a third thing."""
    assert QVizStyle.DEFAULT in QVizStyle.NAMES
    assert QVizStyle.DEFAULT == 'light'


# ------------------------------------------------------- the preferences file --

def readPreferences(folder, text):
    """Write one preferences file and let the application read it, once."""
    (folder / 'preferences').write_text(text)
    QVizPreferences.userPreferencesInitialized = False
    QVizPreferences.Theme = QVizStyle.DEFAULT
    QVizPreferences().build()


def test_the_theme_is_read_from_the_file_the_manual_documents(privateHome):
    """``Theme=dark`` in :file:`~/.imasviz/preferences`, like the five before it."""
    readPreferences(privateHome / '.imasviz', 'Theme=dark\nIgnore_GGD=1\n')
    assert QVizPreferences.Theme == 'dark'
    assert QVizStyle.name() == 'dark'
    assert QVizStyle.current() is QVizStyle.TOKENS['dark']


def test_a_commented_theme_line_changes_nothing(privateHome):
    """The file is read line by line, and a commented option is not a line."""
    readPreferences(privateHome / '.imasviz',
                    '#Theme=dark\nIgnore_GGD=1\n')
    assert QVizPreferences.Theme == QVizStyle.DEFAULT


def test_an_unknown_theme_is_named_and_costs_only_its_own_line(privateHome,
                                                               caplog):
    """One bad line used to cost the whole start-up.

    ``build()`` is called by ``QtVIZ_GUI.main()`` with nothing around it, so a
    ``ValueError`` out of one option was a start that never showed a window. The
    reader now answers for its own line: the value is named in the log, the
    option falls back, and the line below it is still read.
    """
    with caplog.at_level(logging.WARNING):
        readPreferences(privateHome / '.imasviz',
                        'Theme=Night\nIgnore_GGD=0\n')
    assert QVizPreferences.Theme == QVizStyle.DEFAULT
    assert QVizPreferences.Ignore_GGD == 0, 'the next line was lost with it'
    named = [record.getMessage() for record in caplog.records]
    assert any('Theme' in one and 'Night' in one for one in named), named


@pytest.mark.parametrize('written,expected', COLOUR_OPTIONS)
def test_a_colour_option_reads_what_the_manual_writes(privateHome, written,
                                                      expected):
    """``Nodes_selection_colour=#ff0000`` is what the manual says to write.

    The reader took an index into six brushes with ``int(text)`` and nothing
    else, so the file the manual documents answered ``ValueError`` -- and took
    the application down with it, since nothing guards the call in ``main()``.
    A hex, a bare hex and a Qt colour name are read now; the index still is too.
    """
    readPreferences(privateHome / '.imasviz',
                    'Nodes_selection_colour=%s\n' % written)
    assert QVizPreferences.SelectionColor.color().name() == expected


@pytest.mark.parametrize('index', ('1', '6'))
def test_a_colour_option_still_takes_its_index(privateHome, index):
    """The six brushes stay reachable by number, for a file written years ago."""
    readPreferences(privateHome / '.imasviz',
                    'Nodes_selection_colour=%s\n' % index)
    assert (QVizPreferences.SelectionColor.color().name()
            == GlobalColors.getAvailableColorForNodes(int(index) - 1).color().name())


@pytest.mark.parametrize('written', BAD_COLOURS)
def test_a_colour_that_means_nothing_is_named_and_costs_only_its_own_line(
        privateHome, caplog, written):
    with caplog.at_level(logging.WARNING):
        readPreferences(privateHome / '.imasviz',
                        'Nodes_selection_colour=%s\nIgnore_GGD=0\n' % written)
    assert (QVizPreferences.SelectionColor.color().name()
            == GlobalColors.RED.color().name()), 'the default did not stand'
    assert QVizPreferences.Ignore_GGD == 0, 'the next line was lost with it'
    named = [record.getMessage() for record in caplog.records]
    assert any('Nodes_selection_colour' in one and written in one
               for one in named), named


# ------------------------------------------------------------ on the screen --

@pytest.mark.ui
def test_the_theme_is_put_on_the_application(dressed, qapp):
    """Style, palette, sheet, font, icon -- and the answer says which theme."""
    assert dressed in QVizStyle.NAMES
    assert qapp.styleSheet(), 'nothing was put on the application'
    table = QVizStyle.TOKENS[dressed]
    assert (qapp.palette().color(QPalette.ColorRole.Highlight).name()
            == table['selection'])
    assert (qapp.palette().color(QPalette.ColorRole.WindowText).name()
            == table['ink'])
    assert qapp.font().pointSize() == QVizStyle.POINT_SIZE
    assert qapp.windowIcon().isNull() is False, 'the mark of the application is null'


@pytest.mark.ui
def test_fusion_is_underneath_the_sheet(dressed, qapp):
    """The style the palette is painted by, proved by a metric it delegates.

    ``app.style().objectName()`` answers the **empty string** once a sheet is on:
    the style is a ``QStyleSheetStyle`` proxy and no longer says what it proxies.
    What it still delegates are the metrics, and the two below are the ones that
    tell the two styles of this Qt apart -- ``QStyleFactory.keys()`` answers
    ``['Windows', 'Fusion']`` here, and the ``Windows`` style is the one that
    ignores most of what a palette is handed.
    """
    style = qapp.style()
    assert (style.pixelMetric(QStyle.PixelMetric.PM_ScrollBarExtent) == 14
            ), 'the Windows style answers 16, Fusion 14'
    assert (style.pixelMetric(QStyle.PixelMetric.PM_MenuPanelWidth) == 0
            ), 'the Windows style answers 2, Fusion 0'


@pytest.mark.ui
def test_the_chrome_is_painted_with_the_theme(dressed, qapp):
    """Rendered pixels, not rule strings: a selector that matches nothing is quiet.

    The coordinates are of widgets of a known size, sampled away from any border,
    any text and any gradient. The MDI canvas is the one worth reading closely --
    it is painted by the widget itself from ``QPalette::Dark``, which is why
    ``paletteFor`` names that role and why the area is built *after* the theme is
    on: the brush is taken once, at construction.
    """
    table = QVizStyle.TOKENS[dressed]

    tree = QTreeWidget()
    tree.resize(220, 140)
    tree.addTopLevelItem(QTreeWidgetItem(['une branche']))
    tree.addTopLevelItem(QTreeWidgetItem(['une autre']))
    tree.setCurrentItem(tree.topLevelItem(0))
    image = pixels(tree)
    assert image.pixelColor(60, 90).name() == table['surface'], \
        'the ground a tree is read on'
    assert image.pixelColor(60, 6).name() == table['surface-alt'], 'its header'
    assert image.pixelColor(60, 30).name() == table['selection'], 'the selected line'

    field = QLineEdit()
    field.resize(200, 30)
    assert pixels(field).pixelColor(100, 15).name() == table['field']

    log = QPlainTextEdit()
    log.resize(200, 90)
    assert pixels(log).pixelColor(100, 45).name() == table['log-ground']

    canvas = QMdiArea()
    canvas.resize(320, 180)
    assert pixels(canvas).pixelColor(300, 160).name() == table['canvas'], \
        'the canvas every figure floats on: Qt paints it from QPalette::Dark'

    button = QPushButton('Ok')
    button.resize(120, 30)
    assert pixels(button).pixelColor(12, 15).name() == table['surface']


@pytest.mark.ui
def test_a_window_on_the_canvas_keeps_its_own_frame(dressed, qapp):
    """A figure window is a surface with a title, not a hole in the canvas."""
    canvas = QMdiArea()
    canvas.resize(340, 200)
    sub = QMdiSubWindow()
    sub.setWidget(QLabel('figure'))
    canvas.addSubWindow(sub)
    sub.resize(200, 90)
    sub.show()
    image = pixels(canvas)
    frame = sub.frameGeometry()
    table = QVizStyle.TOKENS[dressed]
    assert image.pixelColor(frame.center().x(), frame.top() + 4).name() \
        == table['surface-alt'], 'the title of a window'
    assert image.pixelColor(frame.center().x(), frame.bottom() - 10).name() \
        == table['surface'], 'the body of a window'


@pytest.mark.ui
def test_a_plot_keeps_its_black_ground(dressed, qapp):
    """The one ground the theme must not reach, in either of its two faces.

    pyqtgraph's own default is ``'background': 'k'`` (``pyqtgraph/__init__.py:45``)
    and the window paints it, which is why no rule of ``styleSheet`` names a
    ``QGraphicsView``. Every trace palette (T33, T34), every colour map (T44) and
    every slice-line colour (T45) was measured against that black: a theme that
    reached it would not look different, it would make every one of those
    measurements -- and the tests that pin them -- read false.
    """
    figure = pg.GraphicsLayoutWidget()
    figure.resize(240, 140)
    figure.addPlot(title='courbe')
    keep(figure)
    assert pixels(figure).pixelColor(120, 98).name() == '#000000', \
        '%s theme reached a plot' % dressed


@pytest.mark.ui
def test_the_sheet_never_names_a_plot_and_never_paints_every_widget(dressed):
    """The two silences that would repaint half the application by accident."""
    sheet = stylesheetOf(dressed)
    assert 'QGraphicsView' not in sheet, 'a rule reached the ground of a plot'
    assert not re.search(r'\bQWidget\s*\{[^}]*background', sheet), \
        'a blanket QWidget ground paints everything that has no rule of its own'


@pytest.mark.ui
def test_the_sheet_costs_no_stylesheet_warning(dressed, qapp):
    """An unparseable declaration is printed, never raised -- so it is collected.

    ``QStyleSheetStyle`` answers a warning naming the property it did not know
    and carries on with the style's own colour, which is the quietest possible
    way to lose the theme on one widget.
    """
    from PySide6.QtCore import qInstallMessageHandler
    notes = []
    previous = qInstallMessageHandler(
        lambda kind, context, text: notes.append(text))
    try:
        widgets = [QLineEdit(), QPushButton('Ok'), QTreeWidget(),
                   QPlainTextEdit(), QMdiArea()]
        for one in widgets:
            one.resize(180, 90)
            pixels(one)
    finally:
        qInstallMessageHandler(previous)
    refused = [one for one in notes
               if 'Could not parse' in one or 'Unknown property' in one
               or 'Could not preload' in one]
    assert refused == [], refused[:4]


# ------------------------------------------------------- what follows the ink --

@pytest.mark.ui
def test_a_log_line_wears_the_theme_and_never_a_hard_black(dressed, qapp):
    """The three levels, each legible on the ground the panel is painted with.

    The handler used to decide a colour from the *text* -- whether the formatted
    line contained the word ERROR -- and to paint every other line with a fixed
    ``<font color='black'>``, which is invisible the moment the panel is dressed
    for the dark theme. The colour comes from the level now, and from the theme.
    """
    handler = QVizLogger()
    received = []
    handler.new_signal_emiter.new_signal.connect(received.append)
    table = QVizStyle.TOKENS[dressed]
    for level, token in ((logging.INFO, 'log-info'),
                         (logging.WARNING, 'log-warn'),
                         (logging.ERROR, 'log-error')):
        received[:] = []
        handler.emit(logging.LogRecord('logPanel', level, __file__, 1,
                                       'une ligne', None, None))
        assert len(received) == 1, 'nothing reached the log panel'
        line = received[0]
        assert line.startswith("<font color='%s'>" % table[token]), line
        assert "color='black'" not in line
        ratio = contrast(rgbOf(table[token]), rgbOf(table['log-ground']))
        assert ratio >= CONTRAST_FLOOR, '%s on %s answers %0.2f' % (
            token, table['log-ground'], ratio)


@pytest.mark.ui
def test_the_documentation_panel_and_the_sheet_agree(dressed, qapp):
    """One ground, said once, by the widget and by the sheet.

    The panel sets its own palette brush -- it used to paint ``LIGHT_CYAN``
    (``#cce5ff``), which answers **1,01** against the ink of the dark theme. A
    style sheet wins over a palette, so a sheet rule naming another colour for
    that object name would repaint the panel without anyone touching the panel,
    and the measurement above would be a measurement of nothing.
    """
    panel = QVizNodeDocumentationPanel()
    table = QVizStyle.TOKENS[dressed]
    assert panel.palette().brush(
        panel.backgroundRole()).color().name() == table['surface-alt']
    block = ruleFor('#QVizNodeDocumentationPanel', dressed)
    assert table['surface-alt'] in block, block
    assert table['log-ground'] not in block, \
        'the panel would be painted with the ground of the log: %s' % block


@pytest.mark.ui
def test_the_family_of_the_chrome_is_a_family_this_node_has(dressed, qapp):
    """Naming a font is not getting it, so the answer is asked of ``QFontInfo``.

    Measured here: ``Inter`` -> DejaVu Sans, ``Segoe UI`` -> Cantarell,
    ``Open Sans`` -> DejaVu Sans, ``Cantarell`` -> Cantarell. The application
    font and the four ``GlobalFonts`` are then built on the one that answered for
    itself, which is the only way the two can be the same face.
    """
    family = QVizStyle.resolvedFontFamily()
    assert QFontInfo(QFont(family)).family() == family, \
        '%s is not installed, so it is not an answer' % family
    assert qapp.font().family() == family
    assert GlobalFonts.FAMILY == family, \
        'the sheet asks %s and the labels ask %s' % (family, GlobalFonts.FAMILY)


@pytest.mark.ui
def test_the_four_chrome_fonts_follow_the_family_without_losing_their_sizes(
        qapp):
    """``useFamily`` changes the face and keeps what the layout was measured on."""
    saved = {name: getattr(GlobalFonts, name)
             for name in ('FAMILY', 'TITLE_MEDIUM', 'TITLE_BIG',
                          'TEXT_MEDIUM', 'TEXT_BIG')}
    try:
        GlobalFonts.useFamily('DejaVu Sans')
        assert GlobalFonts.FAMILY == 'DejaVu Sans'
        for name, size, bold in (('TITLE_MEDIUM', 11, True),
                                 ('TITLE_BIG', 15, True),
                                 ('TEXT_MEDIUM', 10, False),
                                 ('TEXT_BIG', 11, False)):
            one = getattr(GlobalFonts, name)
            assert one.family() == 'DejaVu Sans', name
            assert one.pointSize() == size, '%s is %s pt' % (name, one.pointSize())
            assert one.bold() is bold, name
    finally:
        for name, value in saved.items():
            setattr(GlobalFonts, name, value)


@pytest.mark.ui
def test_the_theme_of_the_application_is_the_theme_of_the_preferences(privateHome,
                                                                     dressed,
                                                                     qapp):
    """The file says it, ``name()`` answers it, ``applyToApplication`` wears it.

    Asked with no theme argument -- which is how ``QtVIZ_GUI.main()`` asks it,
    and the one place where the preference in the file becomes the colour on the
    screen. ``dressed`` is here for its teardown: it takes the sheet, the palette,
    the font and the icon back off the session's ``QApplication``.
    """
    readPreferences(privateHome / '.imasviz', 'Theme=%s\n' % dressed)
    assert QVizStyle.name() == dressed
    assert QVizStyle.applyToApplication(qapp) == dressed
