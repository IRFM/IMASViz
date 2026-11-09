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
"""The size of a screenshot, and the gesture that prepares one.

What it pins, in the order the session must answer it:

* **the size a figure leaves the embed in.** The subwindow settles on the
  size hint of the frame it holds, and a frame that answers no size hint
  (a bare content widget, or a container whose layout does not propagate its
  children) settles to 120×28 whatever it was told before the show -- and
  `QWidget.grab()` renders at whatever size the window is, so a freshly
  drawn figure of that shape would be a 120×28 pixel screenshot. The rule
  judges the floor from the size the subwindow *settles to* and hands it
  `DEFAULT_FIGURE_SIZE` when that is below 300 on a side: a frame that
  already answers a readable size keeps it, and a session's saved geometry
  is applied after the embed, over the rule.

* **`focus_window`.** The core gesture the page's buttons and the agent's
  tool list take: a window is shown (a hid one put back), raised to the
  front, and resized -- to the named pixels, or to `DEFAULT_FIGURE_SIZE`
  the same constant the embed handed the frame in question. "app" is the
  main window; a size that is not a positive pair of integers is refused by
  name, and a name the session does not hold is refused from the open ones.

* **the address of a picture.** `saveShots` answers the `(window, path)`
  pairs it wrote -- the window is what `focus_window` and `get_screenshot`
  take back -- which is what the page's gallery acts on each card with.

* **the tool the loop offers.** `focus_window` in `TOOLS` answers the
  parameters it takes and refuses the ones it does not (the resolution on
  the core is `test_116`'s, parametrized over `TOOLS`).
"""

import base64
import os

import pytest
from PySide6.QtWidgets import QMdiArea, QWidget

from imasviz.Viz_API import DEFAULT_FIGURE_SIZE, Viz_API
from imasviz.VizAgent.core import McpGuiCore
from imasviz.VizAgent.tools import TOOLS, unknownParameters
from mcp_server.agent_mode import saveShots


def makeCore(api, main_window=None):
    """The concrete core the loop dispatches against, with the parts the
    gesture it answers needs: the api that serves the windows, and the
    main window when the session was built with one. The two methods
    `focus_window` goes through (`_resolveWindow`, `setWindowVisible`,
    `mdiWindowOf`) run on those two attributes and on nothing else, which
    is what keeps this stand-in from growing the rest of the session."""
    core = McpGuiCore.__new__(McpGuiCore)
    core.main_window = main_window
    core.api = api
    return core


def embeddedFrame(mdi, qtbot, sized=None):
    """One frame in the area, the way `addPlotWidgetToMDI` embedded it.

    A `sized=None` frame is the one the agent draws: no constructor in the
    application resizes it, so it is at its initial size when the embed
    copies the size onto the subwindow. Named is the one that chose a
    size itself (a panel, a case view), kept as it is by the floor.
    """
    frame = QWidget()
    if sized is not None:
        frame.resize(*sized)
    api = Viz_API(parent=mdi)
    subWindow = api.addPlotWidgetToMDI(frame)
    return api, frame, subWindow


# ------------------------------------------------- the size at the creation

def test_a_frame_that_never_got_a_size_leaves_the_embed_at_the_default(
        qapp, qtbot):
    """The measured defect: the first show settles the subwindow on the size
    hint of the frame it holds, and a bare content widget answers no size
    hint at all -- so it settles to 120×28, the size the `grab()` answered,
    whatever it was told before the show (a bare one is even created at
    640×480, which the pre-show reading of the old rule skipped). Judged on
    the size it settles to, the rule now re-asserts the default after the
    show, and that is a size a `grab()` can read."""
    mdi = QMdiArea()
    qtbot.addWidget(mdi)
    mdi.show()
    qapp.processEvents()
    api, frame, subWindow = embeddedFrame(mdi, qtbot, sized=None)

    expected = DEFAULT_FIGURE_SIZE
    assert (subWindow.size().width(), subWindow.size().height()) == expected, \
        'a figure nobody sized is a %sx%s screenshot' % (
            subWindow.size().width(), subWindow.size().height())
    # The frame it holds is inside the shell it answers with: the picture
    # the page serves is the frame's `grab()`, and it answers the default
    # minus the shell's own chrome -- never the 120×28 it settled to.
    assert frame.size().width() <= expected[0]
    assert frame.size().height() <= expected[1]
    assert frame.size().width() > expected[0] // 2
    assert frame.size().height() > expected[1] // 2


def test_a_frame_that_chose_a_size_keeps_it(qapp, qtbot):
    """The opposite must not break: a frame that answers a size hint of its
    own -- a pyqtgraph figure, the shape the curves and images in the
    application are -- settles on that size, which is already readable, and
    the floor only reaches frames that settle below 300 on a side. So the
    figure keeps its own size and is not resized into the default. This is
    the faithful stand-in: a bare `QWidget` answers no size hint and settles
    to 120×28, which is the other test, not this one."""
    import pyqtgraph as pg

    mdi = QMdiArea()
    qtbot.addWidget(mdi)
    mdi.show()
    qapp.processEvents()
    frame = pg.PlotWidget()
    api = Viz_API(parent=mdi)
    subWindow = api.addPlotWidgetToMDI(frame)

    width = subWindow.size().width()
    height = subWindow.size().height()
    # It settles on its own size hint (a pyqtgraph figure answers ~600×480)
    # plus the shell's own chrome -- readable on both sides...
    assert width >= 500 and height >= 400, \
        'a figure that answers a size hint of its own is still a %sx%s screenshot' % (
            width, height)
    # ...and is not the one the floor reached: the default is not on it.
    assert (width, height) != DEFAULT_FIGURE_SIZE, \
        'the floor resized a readable figure into the default'


# ---------------------------------------------------------------- focus_window

def test_focus_window_puts_a_figure_forward_at_the_read(qapp, qtbot):
    """The gesture the page's buttons take: a figure the session holds is
    shown, raised, and resized to the default figure size -- and the
    answer is the size it then holds, so the caller knows what the
    screenshot will answer. `focus_window` takes the figure key
    `list_windows` names, and the subwindow it resizes is the shell the
    *Windows* menu acts on."""
    mdi = QMdiArea()
    qtbot.addWidget(mdi)
    mdi.show()
    qapp.processEvents()
    api, frame, subWindow = embeddedFrame(mdi, qtbot, sized=(400, 300))
    api.figureframes['Plot1'] = frame
    core = makeCore(api)
    api.setWindowVisible(frame, False)  # a figure the close box hid is the one a focus most earns

    out = core.focus_window('Plot1')

    assert out['window'] == 'Plot1'
    assert out['visible'] is True
    # The shell is resized to the pixels `focus_window` takes, and the
    # frame it carries is inside it -- the frame answers at most the shell,
    # minus the shell's own chrome, and never above it.
    assert (subWindow.size().width(), subWindow.size().height()) == DEFAULT_FIGURE_SIZE
    assert frame.size().width() <= DEFAULT_FIGURE_SIZE[0]
    assert frame.size().height() <= DEFAULT_FIGURE_SIZE[1]
    assert frame.size().width() > 0 and frame.size().height() > 0


def test_focus_window_takes_the_named_pixels(qtbot):
    mdi = QMdiArea()
    qtbot.addWidget(mdi)
    api, frame, subWindow = embeddedFrame(mdi, qtbot, sized=(400, 300))
    api.figureframes['Plot1'] = frame
    core = makeCore(api)

    out = core.focus_window('Plot1', width=900, height=600)

    assert (subWindow.size().width(), subWindow.size().height()) == (900, 600)
    assert out['size'] == [frame.size().width(), frame.size().height()]


def test_focus_window_on_the_app_answers_the_main_window(qapp, qtbot):
    mdi = QMdiArea()
    qtbot.addWidget(mdi)
    api, frame, subWindow = embeddedFrame(mdi, qtbot, sized=None)
    main = QWidget()
    qtbot.addWidget(main)
    main.resize(700, 500)
    main.show()
    qapp.processEvents()
    core = makeCore(api, main_window=main)

    out = core.focus_window('app', width=1000, height=800)

    # "app" raises the main window and answers its own size -- the figure
    # it carries is not resized by a gesture that names the application.
    assert out['window'] == 'app'
    assert out['visible'] is True
    assert (subWindow.size().width(), subWindow.size().height()) == DEFAULT_FIGURE_SIZE


def test_focus_window_refuses_a_name_the_session_does_not_hold(qtbot):
    mdi = QMdiArea()
    qtbot.addWidget(mdi)
    api, frame, subWindow = embeddedFrame(mdi, qtbot, sized=None)
    core = makeCore(api)
    with pytest.raises(ValueError) as excinfo:
        core.focus_window('Banana')
    assert 'Banana' in str(excinfo.value)


def test_focus_window_refuses_a_size_that_is_not_pixels(qtbot):
    mdi = QMdiArea()
    qtbot.addWidget(mdi)
    api, frame, subWindow = embeddedFrame(mdi, qtbot, sized=None)
    api.figureframes['Plot1'] = frame
    core = makeCore(api)

    with pytest.raises(ValueError) as excinfo:
        core.focus_window('Plot1', width='x')
    assert 'width' in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        core.focus_window('Plot1', width=0)
    assert '0' in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        core.focus_window('Plot1', height=-5)
    assert 'height' in str(excinfo.value)


def test_focus_window_refuses_the_app_the_session_was_built_without(qtbot):
    mdi = QMdiArea()
    qtbot.addWidget(mdi)
    api, frame, subWindow = embeddedFrame(mdi, qtbot, sized=None)
    core = makeCore(api)  # no main_window
    with pytest.raises(ValueError) as excinfo:
        core.focus_window('app')
    assert 'No application window' in str(excinfo.value)


# ---------------------------------------------------------- the picture address

def test_saveShots_saves_the_figures_by_default(qtbot, tmp_path):
    """The capture of a turn is its plots: `saveShots` answers the
    `(window, path)` pairs it wrote -- the window is what `focus_window`
    and `get_screenshot` take back -- which is what the page's gallery
    acts on each card with. The stand-in holds one figure and no case,
    and no extra is asked for: the application is not saved, because a
    capture of the interface is an ask, and this one is a turn that drew
    a figure and nothing besides."""
    png = base64.b64decode(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ'
        'AAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')

    class ShotsCore:
        def list_windows(self):
            return [{'kind': 'Plot', 'label': 'Plot 1',
                     'key': 'Plot1', 'visible': True, 'cases': []}]

        def screenshot(self, window):
            return png

    saved, refused = saveShots(ShotsCore(), str(tmp_path / 'shots'))
    assert refused == []
    assert [window for window, _ in saved] == ['Plot1']
    assert [os.path.basename(path) for _, path in saved] == ['Plot1.png']
    for window, path in saved:
        assert path.startswith(str(tmp_path / 'shots'))
        assert os.path.isfile(path)


def test_saveShots_saves_the_interface_when_it_is_asked(qtbot, tmp_path):
    """The other half of the same rule: `extras` is where an ask of the
    interface stands, and a ask of the application (and one of a case,
    which the stand-in holds) is the one saved beside the figure. A
    name `EXTRA_SHOTS` does not hold is refused by naming the ones it
    does, because a caller that spells one wrongly meant to have saved
    it -- the refusal is a value the caller reads, and the run is not
    saved half of nothing."""
    from mcp_server.agent_mode import EXTRA_SHOTS

    png = base64.b64decode(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ'
        'AAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')
    case_uri = ('imas:hdf5?path='
                '/afs/eufus.eu/user/g/g2lfleur/public/imasdb/west/3/54924/0')

    class ShotsCore:
        def list_windows(self):
            return [
                {'kind': 'case view', 'label': '54924 / 0', 'key': None,
                 'visible': True, 'cases': [case_uri]},
                {'kind': 'Plot', 'label': 'Plot 1',
                 'key': 'Plot1', 'visible': True, 'cases': []},
            ]

        def screenshot(self, window):
            return png

    # Default: the figure alone.
    saved, refused = saveShots(ShotsCore(), str(tmp_path / 'shots'))
    assert refused == []
    assert [window for window, _ in saved] == ['Plot1']

    # Asked: the application and the case are saved beside the figure --
    # the case under the URI the core takes for it (the address the page
    # acts on), the application under its own name.
    saved, refused = saveShots(ShotsCore(), str(tmp_path / 'shots2'),
                               extras=('app', 'case-views'))
    assert refused == []
    assert sorted(window for window, _ in saved) == \
        ['Plot1', 'app', case_uri]
    names = sorted(os.path.basename(path) for _, path in saved)
    assert '00_app.png' in names
    assert any(name.startswith('case_') for name in names)

    # A name the capture set does not hold: refused by naming the ones
    # it has, before a single PNG is written.
    with pytest.raises(ValueError) as excinfo:
        saveShots(ShotsCore(), str(tmp_path / 'shots3'), extras=('panel',))
    assert 'panel' in str(excinfo.value)
    assert 'app' in str(excinfo.value) and 'case-views' in str(excinfo.value)
    assert tuple(EXTRA_SHOTS) == ('app', 'case-views')


# ------------------------------------------------------------------ the tool

def test_focus_window_is_in_tools_with_its_parameters():
    focus = next(t for t in TOOLS
                 if t['function']['name'] == 'focus_window')
    props = focus['function']['parameters']['properties']
    assert set(props) == {'window', 'width', 'height'}
    assert focus['function']['parameters']['additionalProperties'] is False


def test_focus_window_refuses_a_parameter_it_does_not_hold():
    assert unknownParameters('focus_window',
                             {'window': 'Plot1', 'width': 2,
                              'height': 3, 'zoom': 1}) == ['zoom']
    # The two names it takes are the ones the page's buttons and the
    # agent's call hold.
    assert unknownParameters('focus_window',
                             {'window': 'Plot1', 'width': 2,
                              'height': 3}) == []
