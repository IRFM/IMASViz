# Copyright holders: Commissariat à l'Energie Atomique et aux Energies
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
"""A show of a figure the user names by the way a person names it.

The field report, in the user's words: « certaines fois (après 4 figures
environ) incapable de montrer la dernière figure. La figure existe, je l'ai
vue dans un tour précédent, mais dans un tour suivant elle ne s'affiche
plus. J'ai beau dire "montre-moi plot4", la figure (capture) n'est pas
affichée. »

The model spells a figure the way a person does ("plot3", "3", "la
dernière figure"); the session holds it by the application's own key
(``SlicesPlot3``, ``TablePlotView:1``). Before this, neither the show
(``McpGuiCore._resolveWindow``) nor the capture of the turn
(``saveShots``) resolved the one to the other -- so a show was answered
with a refusal or a silent "here it is", and the picture the user asked
for never reached the page. The one resolver, ``resolveFigureKey``, is now
what the core asks before it shows or grabs a frame and what the capture
asks before it saves a PNG, so the two agree on which figure they named --
and a name it does not settle is answered, refused by name, as the rest of
the loop does.
"""

import base64
import os

import pytest

from imasviz.VizAgent.core import resolveFigureKey
from imasviz.VizAgent.llm_client import LLMResponse
from mcp_server.agent_mode import saveShots

from test_119_viz_web_session import (
    PNG_1x1, FakeCore, FakeLLMClient, build, inWorker)

PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ'
    'AAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')


class HeldCore:
    """A stand-in core holding the figures it holds: the `list_windows` the
    capture asks, and a `screenshot` it answers for a held key or the app.
    A name it does not hold is refused by name, the way the real core does."""

    def __init__(self, keys):
        self._windows = [
            {'kind': 'SlicesPlot', 'label': 'SlicesPlot %d' % n,
             'key': 'SlicesPlot%d' % n, 'visible': True, 'cases': []}
            for n in keys]

    def list_windows(self):
        return list(self._windows)

    def screenshot(self, window):
        if window == 'app' or any(record['key'] == window
                                  for record in self._windows):
            return PNG
        raise ValueError('no such window: %r' % window)

    def get_screenshot(self, window='app'):
        return self.screenshot(window)


# --------------------------------------------------------------- the resolver

def test_exact_key_is_itself():
    assert resolveFigureKey('Plot3', ['Plot1', 'Plot3']) == 'Plot3'
    assert resolveFigureKey('TablePlotView:1', ['TablePlotView:1']) \
        == 'TablePlotView:1'


def test_the_number_a_person_spells_stands_for_the_figure_it_names():
    # The user spells the number; the key the session holds spells the kind.
    assert resolveFigureKey('plot3', ['SlicesPlot3']) == 'SlicesPlot3'
    assert resolveFigureKey('3', ['SlicesPlot3']) == 'SlicesPlot3'
    assert resolveFigureKey('figure 3', ['SlicesPlot3']) == 'SlicesPlot3'
    assert resolveFigureKey('plot2', ['SlicesPlot1',
                                      'SlicesPlot2']) == 'SlicesPlot2'


def test_the_newest_is_the_last_one_in_creation_order():
    # "la dernière figure" is the newest figure the session drew, which is
    # the order the caller already keeps here. Held in creation order
    # (earliest to latest), the last one is the newest.
    assert resolveFigureKey('la derniere figure', ['SlicesPlot1',
                                                   'SlicesPlot2'],
                            order=['SlicesPlot1', 'SlicesPlot2']) \
        == 'SlicesPlot2'
    assert resolveFigureKey('last', ['SlicesPlot1', 'SlicesPlot2'],
                            order=['SlicesPlot1', 'SlicesPlot2']) \
        == 'SlicesPlot2'
    assert resolveFigureKey('the last figure', ['SlicesPlot1',
                                                'SlicesPlot2'],
                            order=['SlicesPlot1', 'SlicesPlot2']) \
        == 'SlicesPlot2'


def test_a_number_that_names_several_is_refused_naming_them():
    with pytest.raises(ValueError) as refused:
        resolveFigureKey('plot3', ['SlicesPlot3', 'TablePlotView:3'])
    message = str(refused.value)
    assert 'SlicesPlot3' in message and 'TablePlotView:3' in message, \
        'an ambiguous reference names none of its options: %r' % message
    assert 'several' in message or 'name the one' in message, \
        'the refusal does not say the name matched several: %r' % message


def test_a_number_the_session_does_not_hold_is_refused_naming_what_it_holds():
    with pytest.raises(ValueError) as refused:
        resolveFigureKey('plot99', ['SlicesPlot1', 'SlicesPlot2'])
    message = str(refused.value)
    assert '99' in message, 'the refusal does not name the number: %r' \
        % message
    assert 'SlicesPlot1' in message and 'SlicesPlot2' in message, \
        'the refusal does not name the figures it holds: %r' % message


def test_a_name_with_no_number_and_no_last_is_the_sole_open_figure():
    assert resolveFigureKey('figure', ['SlicesPlot7']) == 'SlicesPlot7'
    with pytest.raises(ValueError):
        resolveFigureKey('figure', ['SlicesPlot1', 'SlicesPlot2'])


def test_a_name_when_the_session_holds_none_is_refused():
    with pytest.raises(ValueError) as refused:
        resolveFigureKey('plot3', [])
    assert 'none' in str(refused.value).lower()


def test_a_name_with_no_figure_word_in_it_is_rejected_as_the_name_it_is():
    # A loose reference is a word a person uses for a figure: "figure",
    # "plot3", "la dernière figure". A name no such word in spells is not
    # a reference but a made-up name, and a session that happens to hold
    # exactly one figure does not hand it over: the wrong guess would
    # reach a wrong window silently, and the model would believe it asked
    # for the window it named. The refusal, instead, names what the
    # session holds, the way the rest of the loop answers a name it does
    # not settle.
    for name in ('no/such/thing', 'no such thing', ''):
        with pytest.raises(ValueError) as refused:
            resolveFigureKey(name, ['SlicesPlot7'])
        assert 'SlicesPlot7' in str(refused.value), \
            'the refusal does not name the figure the session holds: %r' \
            % str(refused.value)


def test_a_reference_with_a_figure_word_resolves_the_sole_figure():
    # The other side of the line: a reference that names a figure resolves
    # the one open figure, whatever other words it carries.
    assert resolveFigureKey('la figure', ['SlicesPlot7']) == 'SlicesPlot7'
    assert resolveFigureKey('plot', ['SlicesPlot7']) == 'SlicesPlot7'
    assert resolveFigureKey('ma table', ['TablePlotView:2']) \
        == 'TablePlotView:2'


# --------------------------------------------------------------- the capture

def test_saveShots_saves_a_loose_reference_under_the_key_it_stands_for(
        qtbot, tmp_path):
    """The hole on the capture side: a web or a REPL hands the raw gesture
    argument ("plot3", "la derniere") to the save, and a name the session
    holds under its own key was refused for the mismatch. Now the name is
    resolved to the key it stands for and saved under that key -- and a name
    it does not is refused, named, the way an ask that cannot be made is
    answered everywhere else."""
    core = HeldCore([1, 3])

    # The user's "montre-moi plot3", held as SlicesPlot3: the PNG is the one
    # of the figure it stands for.
    saved, refused = saveShots(core, str(tmp_path / 'loose'),
                               figures={'plot3'})
    assert refused == [], 'a loose reference to a held figure is refused: %r' \
        % refused
    assert [window for window, _ in saved] == ['SlicesPlot3'], \
        'the capture is not under the key it stands for: %r' \
        % [window for window, _ in saved]
    with open(tmp_path / 'loose' / 'SlicesPlot3.png', 'rb') as f:
        assert f.read() == PNG

    # "la derniere figure": the newest one is the one saved.
    saved, refused = saveShots(core, str(tmp_path / 'last'),
                               figures={'la derniere figure'})
    assert [window for window, _ in saved] == ['SlicesPlot3'], \
        'the newest figure is not the one saved: %r' \
        % [window for window, _ in saved]
    assert refused == []

    # A name it does not hold is refused, and is named so the caller reads
    # why -- the one held is still the one that comes to disk.
    saved, refused = saveShots(core, str(tmp_path / 'missing'),
                               figures={'plot1', 'plot99'})
    assert [window for window, _ in saved] == ['SlicesPlot1']
    assert len(refused) == 1
    assert 'plot99' in refused[0]
    assert 'not captured' in refused[0]


def test_saveShots_still_saves_all_when_the_caller_names_none(
        qtbot, tmp_path):
    """The one-shot (`figures` left out) is the fresh app: it saves every
    window the session still holds a key for. The tolerance it now gets for
    the names it does hold must not cost that default."""
    core = HeldCore([1, 2])
    saved, refused = saveShots(core, str(tmp_path / 'all'))
    assert refused == []
    assert sorted(window for window, _ in saved) == ['SlicesPlot1',
                                                     'SlicesPlot2']


# ------------------------------------------------------ the core, end to end

def _figureCore(qapp, qtbot):
    """A real core over a real `Viz_API`, holding one embedded frame, the
    way the figure the user is about to show was built. This drives the
    real `focus_window` / `screenshot`, including the resolver they share."""
    from PySide6.QtWidgets import QMdiArea, QWidget

    from imasviz.Viz_API import Viz_API
    from imasviz.VizAgent.core import McpGuiCore

    mdi = QMdiArea()
    qtbot.addWidget(mdi)
    mdi.show()
    qapp.processEvents()
    api = Viz_API(parent=mdi)
    frame = QWidget()
    api.addPlotWidgetToMDI(frame)
    api.figureframes['Plot3'] = frame
    core = McpGuiCore.__new__(McpGuiCore)
    core.main_window = None
    core.api = api
    return core, api, frame


def test_focus_window_resolves_the_name_the_user_spells(qapp, qtbot):
    """The show itself: focus_window takes the reference the user spells and
    brings the figure it stands for to the front, keeping the size it holds,
    exactly as it does for the exact key. A name the session does not hold
    is still refused, naming what is open."""
    core, api, frame = _figureCore(qapp, qtbot)

    out = core.focus_window('plot3')
    assert out['visible'] is True
    assert out['size'] == [frame.size().width(), frame.size().height()], \
        'a show of the loose name does not size the figure it stands for: %r' \
        % out
    assert frame.isVisible()

    # A name the session does not hold is refused, and the refusal names the
    # figures it does.
    with pytest.raises(ValueError) as refused:
        core.focus_window('plot99')
    assert 'Plot3' in str(refused.value)


# --------------------------------------------------------- the web, end to end

class ShowCore(FakeCore):
    """A web stand-in holding a figure an earlier turn drew, and showing it
    the way the real `focus_window` shows it: the reference the user spells
    resolves to the key it stands for, so a loose name and its own key show
    the same figure."""

    def __init__(self, keys):
        super(ShowCore, self).__init__()
        self._windows = [
            {'kind': 'SlicesPlot', 'label': 'SlicesPlot %d' % n,
             'key': 'SlicesPlot%d' % n, 'visible': True, 'cases': []}
            for n in keys]

    def focus_window(self, window='app', width=None, height=None):
        if window == 'app':
            return {'window': 'app', 'visible': True, 'size': [800, 600]}
        held = [record['key'] for record in self._windows]
        try:
            key = resolveFigureKey(window, held, order=held)
        except ValueError:
            raise ValueError(
                'No window holds the figure "%s" any more' % window)
        return {'window': key, 'visible': True, 'size': [800, 600]}


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    """A turn lands in the one prompt history the application shares, under
    $HOME/.imasviz; the panel reads it at build -- so the test points HOME
    at its own folder, the pattern test_119 keeps."""
    monkeypatch.setenv('HOME', str(tmp_path))


def test_a_show_of_a_prior_figure_reaches_the_page(qapp, tmp_path):
    """The user's exact case, end to end: a figure an earlier turn drew and
    showed still stands now, and the later turn that asks to see it --
    "montre-moi plot3" -- is answered with the figure it stands for, the PNG
    on disk, the address the page acts on. Before this, the model spelled the
    figure the way a person does and the session held it by its own key, so
    the show came back as a refusal or a silent "here it is" and the picture
    never reached the page."""
    core = ShowCore([3])
    llm = FakeLLMClient([
        LLMResponse(tool_calls=[
            {'name': 'focus_window', 'args': {'window': 'plot3'}}],
            content=''),
        LLMResponse(content='Voici la figure.', finish_reason='stop'),
    ])
    session, core = build(qapp, tmp_path, llm=llm, core=core)

    record = inWorker(lambda: session.runTurn('montre-moi plot3'), qapp)

    assert record['error'] is None, \
        'a show of the figure the user named was refused: %r' \
        % record['error']
    assert record['refusals'] == [], \
        'the capture of the show was refused: %r' % record['refusals']
    assert record['image_files'] == ['SlicesPlot3.png'], \
        'the figure the user asked to see is not on the page: %r' \
        % record['image_files']
    assert record['image_windows'] == [{'name': 'SlicesPlot3.png',
                                        'window': 'SlicesPlot3'}], \
        'the address the page acts on is not the key it shows: %r' \
        % record['image_windows']
    png = record['images'][0]
    assert png['window'] == 'SlicesPlot3'
    assert base64.b64decode(png['b64']) == PNG
