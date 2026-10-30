# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The theme the application wears, and the one place its colours are written.

The manual was given a house style first (T47): the colour block of
``doc/source/_static/imasviz.css`` is what a reader sees. This module holds the
same block in Python, under the same names, so that the tool and the book about
it cannot drift into two different products -- ``tests/test_77`` reads both
tables and refuses the drift token by token. It is the palette that is shared,
not the rendering: a stylesheet lays out a page, a ``QPalette`` and a Qt
style sheet lay out a window, and the two spell things differently.

Three things are decided here and nowhere else:

* **which colours** -- ``TOKENS``, one table per theme, every value a
  ``#rrggbb`` string;
* **what the platform is asked to do with them** -- ``paletteFor``, because a
  Qt style paints most of a window from the palette and would otherwise paint
  the desktop's own greys;
* **what the palette cannot reach** -- ``styleSheet``, for the few places a
  ``QPalette`` has no role for: the frame of an input, the section of a header
  view, the handle of a scroll bar, the title of an MDI window, the ground of
  the docks and of the log.

The style is set to ``Fusion`` before any of it, and that is a measured choice,
not a taste: ``QStyleFactory.keys()`` answers ``['Windows', 'Fusion']`` on this
node, and the ``Windows`` style ignores most of what a palette is handed --
under it a themed selection ground or a themed button simply does not appear.
``Fusion`` is the style Qt draws itself, identically wherever it runs.

What is deliberately **not** touched: the ground of a plot. pyqtgraph paints
``'background': 'k'`` behind every figure (``pyqtgraph/__init__.py:45``) and the
two trace palettes and the colour maps were all measured against that black
(T33, T34, T44, T45). A theme that reached a ``QGraphicsView`` would silently
invalidate every one of those measurements, so no rule of ``styleSheet`` names
one, and ``test_77`` pins the black.
"""

import os

#: The two themes, and the one a start takes when the preferences say nothing.
#: Light is the default: the tool is used on a desktop in a lit room, and the
#: screenshots the manual carries were taken on light chrome.
NAMES = ('light', 'dark')
DEFAULT = 'light'

#: The colour block, by name, of the house palette. Every value here is also in
#: ``doc/source/_static/imasviz.css`` between ``tokens:begin`` and
#: ``tokens:end``, with the same name and the same value: a colour that means
#: one thing means it in one way in both places.
TOKENS = {
    'light': {
        'canvas': '#eef1f3',
        'surface': '#ffffff',
        'surface-alt': '#f7f9fa',
        'field': '#f4f7f8',
        'line': '#dde3e7',
        'line-soft': '#eaeff1',
        'ink': '#1f2933',
        'ink-soft': '#4a5560',
        'ink-faint': '#616b77',
        'accent': '#0b7285',
        'accent-strong': '#085c6b',
        'accent-soft': '#e3f0f2',
        'on-accent': '#ffffff',
        'selection': '#bfe3ea',
        'on-selection': '#10222a',
        'log-ground': '#f6f8f9',
        'log-info': '#1f2933',
        'log-warn': '#9a5b00',
        'log-error': '#b3261e',
    },
    'dark': {
        'canvas': '#0f1317',
        'surface': '#181d22',
        'surface-alt': '#141a1f',
        'field': '#12171b',
        'line': '#2a333a',
        'line-soft': '#222a31',
        'ink': '#dbe2e8',
        'ink-soft': '#a7b3bd',
        'ink-faint': '#8494a0',
        'accent': '#5fd4e4',
        'accent-strong': '#8ce3ef',
        'accent-soft': '#1d3238',
        'on-accent': '#0f1317',
        'selection': '#22505a',
        'on-selection': '#eaf6f8',
        'log-ground': '#12171b',
        'log-info': '#dbe2e8',
        'log-warn': '#e0b070',
        'log-error': '#f19a92',
    },
}

#: The families the application asks for, in order, and the fact that decides
#: the order: none of them is guaranteed on a node. ``QFontInfo`` is what tells
#: an installed family from a substitution -- ``QFont('Open Sans')``, the family
#: ``GlobalFonts`` used to name, answers ``DejaVu Sans`` here, so naming a font
#: is not the same as getting it and the answer has to be asked for.
FONT_FAMILIES = ('Inter', 'Segoe UI', 'Cantarell', 'DejaVu Sans',
                 'Liberation Sans')

#: The point size of everything but a plot. Nine was what Qt answered on this
#: node; ten is what the labels of this application fit in, and the tree is read
#: at arm's length all day.
POINT_SIZE = 10

#: The Qt style the application asks for. ``QStyleFactory.keys()`` answers
#: ``['Windows', 'Fusion']`` on this node, and ``Windows`` is the style that
#: ignores most of what a palette is handed: a themed selection ground or a
#: themed button simply does not appear under it. ``Fusion`` is the style Qt
#: draws itself, so the tool looks the same on a Gateway node, a laptop and a
#: bare X session.
#:
#: Asking for it is only half of it, and the other half is a trap for the next
#: reader: once a style sheet is set on the application, ``app.style()`` answers
#: a ``QStyleSheetStyle`` whose ``objectName()`` is the **empty string**, so the
#: style can no longer be recognised by its name. What still says Fusion is a
#: metric the proxy delegates -- ``PM_ScrollBarExtent`` 14 where the Windows
#: style answers 16, ``PM_MenuPanelWidth`` 0 where it answers 2.
STYLE = 'Fusion'

#: The mark, in the repository, that every window of the application carries.
MARK = os.path.join('resources', 'VizIcons', 'imasviz_mark.svg')


def forName(name):
    """The colour table of one theme, refusing an unknown name by the name.

    A preference typed by hand is where a theme name goes wrong, and a
    ``KeyError`` on ``'Light'`` is not an answer a user can do anything with.
    """
    if name not in TOKENS:
        raise ValueError('unknown theme %r: IMASViz wears %s'
                         % (name, ' or '.join(repr(one) for one in NAMES)))
    return TOKENS[name]


def name():
    """Which theme this session is configured to wear.

    Read through ``QVizPreferences``, which is where the file is parsed and
    where an unknown value is refused; a value that got through anyway -- a
    preference set on the class by a test, say -- falls back on the default
    rather than raising in the middle of painting a window.
    """
    from imasviz.VizUtils.QVizGlobalValues import QVizPreferences
    asked = getattr(QVizPreferences, 'Theme', DEFAULT)
    return asked if asked in TOKENS else DEFAULT


def current():
    """The colour table of the theme in force."""
    return forName(name())


def colour(token, theme=None):
    """One colour of the palette, as a ``#rrggbb`` string."""
    table = forName(theme) if theme else current()
    if token not in table:
        raise ValueError('unknown colour %r: the palette holds %s'
                         % (token, ', '.join(sorted(table))))
    return table[token]


def resolvedFontFamily():
    """The family the application will actually be drawn with.

    The first of ``FONT_FAMILIES`` that is installed, which ``QFontInfo`` is
    asked because it answers what Qt resolved, not what was requested. With none
    of them installed the answer is whatever the platform's default resolves to,
    which is honest: the application draws with a real font either way, and the
    name is here for the log and the tests.
    """
    from PySide6.QtGui import QFont, QFontInfo
    for family in FONT_FAMILIES:
        if QFontInfo(QFont(family)).family() == family:
            return family
    return QFontInfo(QFont()).family()


def font(family=None, pointSize=None, bold=False):
    """A font of the house stack, at the size the chrome is drawn at."""
    from PySide6.QtGui import QFont
    asked = QFont(family or resolvedFontFamily(),
                  POINT_SIZE if pointSize is None else pointSize)
    asked.setBold(bold)
    return asked


def paletteFor(theme=None):
    """The ``QPalette`` a Qt style paints a window from.

    Only the roles a window is really made of are named. The disabled group is
    left to Qt: a style dims a disabled colour itself, and a hand-dimmed colour
    on top of that answers grey-on-grey.

    ``Dark`` is named because the canvas of the application needs it and nothing
    else gives it. A ``QMdiArea`` -- the canvas every figure and every shot view
    floats on -- takes its ground once, at construction, from ``QPalette::Dark``
    and paints it in its own ``paintEvent``: measured, it answers Qt's stock
    ``#9f9f9f`` grey under a themed palette, a ``background`` rule in a style
    sheet never reaches it, and a palette changed *after* the widget exists does
    not move it either (it is read again only through ``setBackground``). Naming
    the role here is what puts the canvas behind the windows -- ``#eef1f3`` light,
    ``#0f1317`` dark -- and it has to be on the application before the first
    window is built, which is what ``applyToApplication`` does.
    """
    from PySide6.QtGui import QColor, QPalette
    table = forName(theme) if theme else current()
    put = lambda role, key: palette.setColor(role, QColor(table[key]))

    palette = QPalette()
    put(QPalette.Window, 'surface-alt')
    put(QPalette.WindowText, 'ink')
    put(QPalette.Base, 'surface')
    put(QPalette.AlternateBase, 'surface-alt')
    put(QPalette.Text, 'ink')
    put(QPalette.ToolTipBase, 'surface')
    put(QPalette.ToolTipText, 'ink')
    put(QPalette.BrightText, 'log-error')
    put(QPalette.Button, 'surface-alt')
    put(QPalette.ButtonText, 'ink')
    put(QPalette.Highlight, 'selection')
    put(QPalette.HighlightedText, 'on-selection')
    put(QPalette.Link, 'accent')
    put(QPalette.PlaceholderText, 'ink-faint')
    put(QPalette.Dark, 'canvas')
    return palette


def styleSheet(theme=None):
    """The Qt style sheet that paints what a ``QPalette`` has no role for.

    Written against the Qt classes of the widgets the application actually
    builds, and against the few object names it really puts on them
    (``MDI``, ``DockWidgetContents_LOG``, ``QVizNodeDocumentation*``). Every rule
    here was checked to change a pixel: a rule that matches nothing is worse than
    no rule, because the next reader believes the colour is on screen. Two that
    looked right and measured false are gone -- a ``background`` on ``QMdiArea``
    (see ``paletteFor``, which is where the canvas is really painted) and a
    ``QStatusBar#statusbar``, an id the main window's bar does not carry.
    No rule names a ``QGraphicsView`` and none names ``QWidget`` with a
    ``background``, for the reason in the module docstring: the ground of a plot
    is measured and stays black.
    """
    table = forName(theme) if theme else current()
    c = lambda key: table[key]
    return """
/* -- the frame of the application ------------------------------------- */
QMainWindow, QDialog { background: %(canvas)s; }
QStatusBar { background: %(surfaceAlt)s; color: %(inkSoft)s;
             border-top: 1px solid %(line)s; }

/* -- the windows floating on the canvas ------------------------------- */
QMdiSubWindow { background: %(surface)s; border: 1px solid %(line)s; }
QMdiSubWindow::title { background: %(surfaceAlt)s; color: %(inkSoft)s;
                       padding: 3px 6px; }
QMdiSubWindow::title:active { background: %(accentSoft)s;
                              color: %(accentStrong)s; }

/* -- the menus -------------------------------------------------------- */
QMenuBar { background: %(surfaceAlt)s; color: %(inkSoft)s;
           border-bottom: 1px solid %(line)s; }
QMenuBar::item { background: transparent; padding: 4px 9px; }
QMenuBar::item:selected { background: %(accentSoft)s;
                          color: %(accentStrong)s; border-radius: 4px; }
QMenu { background: %(surface)s; color: %(ink)s;
        border: 1px solid %(line)s; padding: 4px 0; }
QMenu::item { padding: 4px 22px 4px 20px; }
QMenu::item:selected { background: %(accentSoft)s; color: %(accentStrong)s; }
QMenu::item:disabled { color: %(inkFaint)s; }
QMenu::separator { height: 1px; background: %(lineSoft)s; margin: 4px 8px; }

/* -- the tree, and every table like it -------------------------------- */
QTreeView, QTableView, QListView {
    background: %(surface)s; color: %(ink)s;
    alternate-background-color: %(surfaceAlt)s;
    border: 1px solid %(line)s; selection-background-color: %(selection)s;
    selection-color: %(onSelection)s; outline: 0;
}
QTreeView::item, QTableView::item, QListView::item { padding: 2px 1px; }
QTreeView::item:selected, QTableView::item:selected,
QListView::item:selected { background: %(selection)s; color: %(onSelection)s; }
QTreeView::branch { background: %(surface)s; }
QHeaderView { background: %(surfaceAlt)s; border: 0; }
QHeaderView::section { background: %(surfaceAlt)s; color: %(inkSoft)s;
                       border: 0; border-bottom: 1px solid %(line)s;
                       padding: 4px 6px; }

/* -- what the user types into ----------------------------------------- */
QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QAbstractSpinBox, QComboBox {
    background: %(field)s; color: %(ink)s; border: 1px solid %(line)s;
    border-radius: 4px; padding: 3px 6px;
    selection-background-color: %(selection)s;
    selection-color: %(onSelection)s;
}
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QComboBox:focus { border: 1px solid %(accent)s; }
QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled,
QSpinBox:disabled, QDoubleSpinBox:disabled { color: %(inkFaint)s; }
QComboBox::drop-down { border: 0; width: 18px; }
QComboBox QAbstractItemView { background: %(surface)s; color: %(ink)s;
    border: 1px solid %(line)s; selection-background-color: %(selection)s;
    selection-color: %(onSelection)s; }

/* -- the buttons ------------------------------------------------------ */
QPushButton { background: %(surface)s; color: %(ink)s;
              border: 1px solid %(line)s; border-radius: 4px;
              padding: 4px 12px; }
QPushButton:hover { border-color: %(accent)s; background: %(accentSoft)s;
                    color: %(accentStrong)s; }
QPushButton:pressed { background: %(accent)s; color: %(onAccent)s; }
QPushButton:default { border: 1px solid %(accent)s; background: %(accent)s;
                      color: %(onAccent)s; }
QPushButton:disabled { color: %(inkFaint)s; background: %(surfaceAlt)s; }
QToolButton { background: transparent; color: %(inkSoft)s; border: 0;
              border-radius: 4px; padding: 3px; }
QToolButton:hover, QToolButton:checked { background: %(accentSoft)s;
                                         color: %(accentStrong)s; }

/* -- the tabs the plugins and the views are laid out with ------------- */
QTabWidget::pane { border: 1px solid %(line)s; background: %(surface)s; }
QTabBar::tab { background: %(surfaceAlt)s; color: %(inkSoft)s;
               border: 1px solid %(line)s; border-bottom: 0;
               padding: 5px 12px; }
QTabBar::tab:selected { background: %(surface)s; color: %(accentStrong)s; }
QTabBar::tab:hover { color: %(accent)s; }

/* -- the docks: the log and the node documentation -------------------- */
QDockWidget { color: %(inkSoft)s; }
QDockWidget::title { background: %(surfaceAlt)s; color: %(inkSoft)s;
                     padding: 4px 8px; border-bottom: 1px solid %(line)s; }
QDockWidget::title:active { color: %(accentStrong)s; }
QPlainTextEdit, #DockWidgetContents_LOG {
    background: %(logGround)s; color: %(ink)s; border: 1px solid %(line)s;
}
/* The node documentation dock answers what a node holds in labels, not in a
   stream of lines, so it wears the dock ground -- the same ``surface-alt`` the
   panel itself asks of the palette. It is written here because a style sheet
   wins over a palette: a rule naming ``log-ground`` for it would repaint the
   panel without anyone touching the panel. */
#QVizNodeDocumentationPanel, #QVizNodeDocumentationScroll,
#QVizNodeDocumentationContents {
    background: %(surfaceAlt)s; color: %(ink)s; border: 0;
}

/* -- the scroll bars -------------------------------------------------- */
QScrollBar:vertical { background: %(surface)s; width: 12px; margin: 0; }
QScrollBar:horizontal { background: %(surface)s; height: 12px; margin: 0; }
QScrollBar::handle { background: %(line)s; border-radius: 5px;
                     min-height: 24px; min-width: 24px; }
QScrollBar::handle:hover { background: %(inkFaint)s; }
QScrollBar::add-line, QScrollBar::sub-line { background: none; border: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }

/* -- the rest of the chrome ------------------------------------------- */
QToolTip { background: %(surface)s; color: %(ink)s;
           border: 1px solid %(accent)s; padding: 4px 6px; }
QSplitter::handle { background: %(lineSoft)s; }
QGroupBox { border: 1px solid %(line)s; border-radius: 4px; margin-top: 8px; }
QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px;
                   color: %(inkSoft)s; }
QProgressBar { background: %(field)s; color: %(ink)s;
               border: 1px solid %(line)s; border-radius: 4px; }
QProgressBar::chunk { background: %(accent)s; }
""" % {'canvas': c('canvas'), 'surface': c('surface'),
       'surfaceAlt': c('surface-alt'), 'field': c('field'),
       'line': c('line'), 'lineSoft': c('line-soft'),
       'ink': c('ink'), 'inkSoft': c('ink-soft'), 'inkFaint': c('ink-faint'),
       'accent': c('accent'), 'accentStrong': c('accent-strong'),
       'accentSoft': c('accent-soft'), 'onAccent': c('on-accent'),
       'selection': c('selection'), 'onSelection': c('on-selection'),
       'logGround': c('log-ground')}


def logColour(level):
    """The colour one line of the log panel is painted with.

    Never a hard black: the panel is painted on ``--log-ground``, which is dark
    in one of the two themes, and the information lines used to be wrapped in
    ``<font color='black'>`` -- invisible there. The three colours are the
    palette's own, each measured against that ground (13,85 / 5,09 / 6,14 in the
    light theme, 13,79 / 9,12 / 8,40 in the dark one).
    """
    table = current()
    if level >= 40:
        return table['log-error']
    if level >= 30:
        return table['log-warn']
    return table['log-info']


def windowIcon():
    """The mark every window of the application carries, or ``None``.

    ``None`` when the file is not there: a start must not fail on an icon, and
    Qt answers a null icon for a path it cannot read anyway.
    """
    from PySide6.QtGui import QIcon
    home = os.environ.get('VIZ_HOME')
    if not home:
        return None
    path = os.path.join(home, MARK)
    if not os.path.exists(path):
        return None
    icon = QIcon(path)
    return None if icon.isNull() else icon


def applyToApplication(app, theme=None):
    """Dress the application, and answer which theme was put on it.

    The order is the order Qt wants: the style first, because a style sheet is
    read through the style that is set, then the palette the style paints from,
    then the sheet that says what the palette cannot. Called once, from
    ``QtVIZ_GUI.main``, after the preferences have been read -- before them it
    would dress the window in a theme the user did not ask for.

    ``GlobalFonts`` goes on the same family in the same call: a sheet asking for
    one typeface and a font table asking for another is the drift this module
    exists to refuse.
    """
    from imasviz.VizUtils.QVizGlobalValues import GlobalFonts
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QStyleFactory

    chosen = theme or name()
    forName(chosen)
    if STYLE in QStyleFactory.keys():
        app.setStyle(STYLE)
    app.setPalette(paletteFor(chosen))
    app.setStyleSheet(styleSheet(chosen))
    family = resolvedFontFamily()
    asked = QFont(family, POINT_SIZE)
    app.setFont(asked)
    GlobalFonts.useFamily(family)
    icon = windowIcon()
    if icon is not None:
        app.setWindowIcon(icon)
    return chosen
