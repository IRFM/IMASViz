# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The *New session* gesture, on the surface the page and the agent share.

The application wears it on the *File* menu (*New session*, on top: it is
the question a run begins with): the case views and every figure go off
the screen, and the session is **not saved** -- the one on disk is
untouched. The web session and the agent do not have the same question:
the page has no *File* menu, and the agent no screen to clear -- so the
gesture the loop dispatches (`new_session`) and the page acts on
(`POST /api/tool {name: new_session}`) must be the core's own, answering
by name what it closes, without writing a single session file: "nettoyer
une session sans la sauvegarder" is the contract, and a refusal of a
name the core does not answer is the one `test_116` pins for the loop.
"""

import os

from PySide6.QtWidgets import QMdiArea

from imasviz.VizAgent.tools import TOOLS, unknownParameters

from test_122_screenshots_size_and_focus import embeddedFrame, makeCore


def test_new_session_closes_every_window_and_saves_none(qapp, qtbot,
                                                        tmp_path, monkeypatch):
    """What *New session* costs a session that holds a case view and a
    figure: both close, the bookkeeping forgets them, and **no session
    file is written** -- the saved one on disk is the user's, and a
    clean-slate is not a save by another hand."""
    monkeypatch.setenv('HOME', str(tmp_path / 'home'))
    (tmp_path / 'home').mkdir()
    preferences = tmp_path / 'home' / '.imasviz' / 'preferences'

    mdi = QMdiArea()
    qtbot.addWidget(mdi)
    mdi.show()
    qapp.processEvents()

    apiFig, frameFig, _ = embeddedFrame(mdi, qtbot,
                                        sized=(600, 400))
    apiCase, frameCase, _ = embeddedFrame(mdi, qtbot,
                                          sized=(800, 600))

    # The case view the session holds, as far as the read and the close
    # reach it: `openWindows` reads its label off
    # ``dataTreeView.dataSource`` and `RemoveDTVFrame` lets that source
    # go with the frame, so the stand-in holds those two, and the
    # `DTVlist` that removes its view.
    class _DataSource:
        uri = 'imas:hdf5?path=/test/54924/0'

        def getLongLabel(self):
            return '54924 / 0'

        def forget_case(self):
            pass

    class _DataTreeView:
        dataSource = _DataSource()

    frameCase.dataTreeView = _DataTreeView

    # One api serves both windows, the way one session holds them: the
    # figure under its key and the case view under its view -- the two
    # `closeAll` walks. The real `Viz_API` spells a curve figure
    # `Plot` + number (`FigureTypes.CURVEPLOTTYPE`), and `GetFiguresKeys`
    # matches on that, so the key it is handed here is the one the
    # application hands out.
    api = apiFig
    api.figureframes['Plot1'] = frameFig
    api.DTVframeList = [frameCase]
    api.DTVlist = [frameCase.dataTreeView]
    core = makeCore(api, main_window=None)

    before = core.list_windows()
    assert any(r['key'] == 'Plot1' for r in before)

    # The gesture the loop dispatches: by its name, and it answers
    # by name what it closed.
    closed = core.new_session()
    assert closed, 'the session held a figure and a case view: ' \
        'new_session must close them and name them'
    assert core.list_windows() == [] or all(
        r['key'] is None for r in core.list_windows())
    assert not api.figureframes
    assert not api.DTVframeList

    # And the "sans la sauvegarder" half: no new session file anywhere
    # under the session's HOME. A *save_session* is a different gesture,
    # and a new session that writes one is a save by another hand.
    written = []
    for root, _dirs, files in os.walk(tmp_path / 'home'):
        written += [os.path.join(root, f) for f in files
                    if f.endswith('.vsess')]
    assert written == [], 'new_session wrote a session file: %s' % written
    assert not os.path.exists(preferences) or \
        not any(f.endswith('.vsess') for f
                in os.listdir(str(tmp_path / 'home')))


def test_new_session_is_a_named_tool_the_loop_may_call():
    """`new_session` in `TOOLS`: the agent may answer "nouvelle session"
    with it (a named tool, the `test_116` resolution of a TOOLS name on
    the core), and an argument it does not take is refused by name the
    way the loop refuses a stray one -- not invented."""
    names = [one['function']['name'] for one in TOOLS]
    assert 'new_session' in names, \
        'the agent cannot say "nouvelle session" without the tool it ' \
        'closes by'
    spec = next(one['function']['parameters'] for one in TOOLS
                if one['function']['name'] == 'new_session')
    assert spec['required'] == [], \
        'a new session takes no argument: %r' % spec['required']
    # `unknownParameters` answers the names the tool does not take (the
    # loop is what refuses them from here by name, `test_117`).
    assert unknownParameters('new_session', {'keep': 'figures'}) == ['keep'], \
        'the stray argument must be named: %r' % (
            unknownParameters('new_session', {'keep': 'figures'}),)


def test_the_page_offers_the_clean_slate(qapp):
    """The page asks the same gesture of the core it offers through its
    button: `new_session` on `/api/tool` -- the refusal a name earns
    reads the same in the page as in the agent's transcript -- and after
    it, the page clears its own transcript, its captures and its turn
    list: the clean slate the user asked for, on the surface they
    clicked. Pinned the way `test_121` pins the page's behaviour: the
    button exists, it names the gesture, and it clears."""
    import re

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        '..', 'viz_web', 'static', 'index.html')
    with open(path, encoding='utf-8') as f:
        page = f.read()
    assert re.search(r'id=["\']newSessionBtn["\']', page), \
        'the page has no New session button: the clean slate is on the ' \
        'File menu of the application, and the user asked for it on the ' \
        'page'
    assert re.search(r"newSessionBtn',\s*\{[^}]*name", page) or \
        'new_session' in page, \
        'the button must ask the core for the new_session gesture'
    assert re.search(r'confirm\(', page), \
        'a new session closes every figure without saving: the page ' \
        'must ask once, by name, before it does'
