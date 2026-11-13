# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""Closing a figure on the web surface: what the page keeps after it.

The user's report: "quand je ferme une figure via une demande à
l'agent depuis la fenêtre de tchat, la figure reste ouverte, bien que
l'agent affirme que ça s'est bien passé — la fenêtre reste ouverte
sous mes yeux."

The close is **real** on the application side: `close_window` takes
the window off the screen and out of the bookkeeping (`Viz_API.
closeWindow`, the shape the *Windows* menu's *Delete* line uses), and
the loop's `closed: key` is the true answer of what it did. The page's
"figure" is a different thing: the capture of the turn that drew it,
and the gallery the page builds — live and on the reload of the page —
is built from the session's records (`image_windows`, in each turn's
`turn.json`, rebuilt from `/api/turns`). The close that does not take
the figure out of those records is the one the user reads back: the
agent's words are true on their side, and the page is what keeps the
figure under their eyes. And the card it kept is a dead address: its
`Focus` and `Screenshot` name a key the session no longer holds.

So the close must take the figure out of the records -- the live
record of a turn (`runTurn`), the direct ask of the page
(`callGesture`), and the records on disk (`turn.json` rewritten), so
the reload of the page and the restart of the server keep it gone --
and the page must drop the card the close names from its gallery.
"""

import json
import os

from imasviz.VizAgent.llm_client import LLMClient, LLMResponse

from test_119_viz_web_session import (
    CASE_URI, DEAD_ENDPOINT, FakeCore, FakeLLMClient, FakeWindow,
    build, inWorker)

from viz_web.web_session import WebSession


def _restart_session(shots_dir):
    """A new process on the same captures directory: the restart."""
    from viz_cli.session import Client
    session = WebSession(app=None, window=FakeWindow(), core=FakeCore(),
                         client=Client(LLMClient(
                             endpoint=DEAD_ENDPOINT,
                             model='stub', timeout=2.0)),
                         shots_dir=str(shots_dir), max_turns=8)
    return session


def test_closing_a_figure_takes_it_out_of_the_records_of_the_session(qapp,
                                                                     tmp_path):
    """One turn draws the figure and asks the interface, the next
    closes the figure. After the close, the session no longer names
    the figure: the record of the turn that drew it has lost it (the
    one the page's gallery is built from), but it keeps the capture
    the close did not name -- the removal is keyed on the key the
    close answered, not on the turn's pictures -- and the record on
    disk is rewritten: the reload of the page rebuilds from the disk,
    and the restart of the server reads it back from there too. The
    turn's answer carries the closed keys: the address the page uses
    to drop the card it kept.

    The close itself is still what the application side did: the
    window is gone from the core's holding, and the loop said so.
    What was missing was the page's side of the truth."""
    llm = FakeLLMClient([
        # First: the figure is drawn, and the interface is asked.
        LLMResponse(tool_calls=[
            {'name': 'plot_one',
             'args': {'uri': CASE_URI, 'path': 'core.ion[0].temp'}}],
            content=''),
        LLMResponse(tool_calls=[
            {'name': 'get_screenshot', 'args': {'window': 'app'}}],
            content=''),
        LLMResponse(content='La figure est tracée, et l''interface.',
                    finish_reason='stop'),
        # Second: the figure is closed -- the interface stays named.
        LLMResponse(tool_calls=[
            {'name': 'close_window', 'args': {'key': 'SlicesPlot1'}}],
            content=''),
        LLMResponse(content='La figure est fermée.', finish_reason='stop'),
    ])
    session, core = build(qapp, tmp_path, llm=llm)

    first = inWorker(
        lambda: session.runTurn('trace une figure et l''interface'), qapp)
    assert first['error'] is None
    assert sorted(first['image_files']) == ['00_app.png', 'SlicesPlot1.png']

    second = inWorker(lambda: session.runTurn('ferme la figure'), qapp)
    assert second['error'] is None
    # The application side of the closure: the window is gone, and the
    # loop said so in the transcript the page reads.
    assert not any(r['key'] == 'SlicesPlot1' for r in core.list_windows()), \
        'close_window ran: the core must hold the window no more'
    text = '\n'.join(second['lines'])
    assert 'close_window' in text
    assert 'closed=SlicesPlot1' in text or "'closed': 'SlicesPlot1'" in text
    # The page's side of the truth: the record of the turn that drew
    # it no longer names the figure -- and it keeps the capture the
    # close did not name: the removal is keyed on the key the close
    # answered, not on the turn's pictures.
    assert session.turns[0]['image_windows'] \
        == [{'name': '00_app.png', 'window': 'app'}], \
        'la figure fermée est toujours nommée dans le record du tour qui ' \
        'l\'a tracée: la galerie la tient encore sous les yeux'
    assert session.turns[0]['image_files'] == ['00_app.png']
    # ... on disk, not only in memory: the reload of the page and the
    # restart of the server read the record from the turn's directory.
    with open(os.path.join(session.turns[0]['dir'], 'turn.json'),
              encoding='utf-8') as f:
        on_disk = json.load(f)
    assert on_disk['image_windows'] == [{'name': '00_app.png',
                                         'window': 'app'}]
    assert on_disk['image_files'] == ['00_app.png']
    # ... and for the restart: a new process on the same directory.
    restarted = _restart_session(tmp_path / 'shots')
    assert restarted.turns[0]['image_files'] == ['00_app.png'], \
        'le redémarrage relit le record qui tient encore la figure fermée'
    # The done event hands the page the keys it drops from its gallery:
    assert second['closed'] == ['SlicesPlot1'], \
        'le tour qui ferme ne nomme pas la figure qu\'il a fermée: la page ' \
        'n\'a pas l\'adresse de la carte à retirer'


def test_the_page_asking_the_close_updates_the_records_the_same_way(qapp,
                                                                    tmp_path):
    """`callGesture` is the direct ask of the page (`POST /api/tool`):
    a `close_window` it answers runs the same core gesture, and the
    figure it closes leaves the records the same way the loop's turn
    takes it out -- the two asks cannot leave two different truths in
    the gallery behind them. And a key the core does not hold is the
    refusal of the core, named, with the records left as they are:
    there is no card to drop for a figure that is not there."""
    session, core = build(qapp, tmp_path)
    llm = FakeLLMClient([
        LLMResponse(tool_calls=[
            {'name': 'plot_one',
             'args': {'uri': CASE_URI, 'path': 'core.ion[0].temp'}}],
            content=''),
        LLMResponse(content='La figure est tracée.', finish_reason='stop'),
    ])
    session.agent.llm = llm
    first = inWorker(lambda: session.runTurn('trace une figure'), qapp)
    assert first['image_files'] == ['SlicesPlot1.png']

    out = inWorker(lambda: session.callGesture(
        'close_window', {'key': 'SlicesPlot1'}), qapp)
    assert out['error'] is None
    assert not any(r['key'] == 'SlicesPlot1' for r in core.list_windows())
    assert session.turns[0]['image_windows'] == [], \
        'la fermeture demandée par la page doit quitter les records comme ' \
        'celle de l''agent'
    assert session.turns[0]['image_files'] == []
    with open(os.path.join(session.turns[0]['dir'], 'turn.json'),
              encoding='utf-8') as f:
        assert json.load(f)['image_files'] == []

    # The key the session no longer holds is refused by name -- and a
    # refusal of a close is not a close: nothing is taken out.
    out2 = inWorker(lambda: session.callGesture(
        'close_window', {'key': 'SlicesPlot1'}), qapp)
    assert out2['error'] is not None
    assert 'SlicesPlot1' in out2['error']


def test_new_session_marks_every_capture_the_records_hold(qapp, tmp_path):
    """The *New session* the page and the agent share closes every
    case view and every figure (`Viz_API.closeAll`): the records of
    the session no longer name a single capture -- the figures and
    the interface asks alike. The button of the page answers the same
    gesture and then clears its own screen; the records are what the
    screen rebuilds from on the reload, so the clean slate must be in
    them, or the reload brings the session back.

    (The turn that drew the capture keeps its transcript on disk:
    what leaves is the figure the record names, not the request it
    was the answer to.)"""
    llm = FakeLLMClient([
        LLMResponse(tool_calls=[
            {'name': 'plot_one',
             'args': {'uri': CASE_URI, 'path': 'core.ion[0].temp'}}],
            content=''),
        LLMResponse(tool_calls=[
            {'name': 'get_screenshot', 'args': {'window': 'app'}}],
            content=''),
        LLMResponse(content='La figure est tracée, et l''interface.',
                    finish_reason='stop'),
    ])
    session, core = build(qapp, tmp_path, llm=llm)
    first = inWorker(
        lambda: session.runTurn('trace une figure et l''interface'), qapp)
    assert first['error'] is None
    assert sorted(first['image_files']) == ['00_app.png', 'SlicesPlot1.png']

    out = inWorker(lambda: session.callGesture('new_session', {}), qapp)
    assert out['error'] is None
    assert core.list_windows() == [] or all(
        r['key'] is None for r in core.list_windows())
    for record in session.turns:
        assert record['image_windows'] == [], \
            'la nouvelle session ferme tout: aucune capture ne doit ' \
            'survivre dans les records -- %r' % record['image_windows']
        assert record['image_files'] == []
        with open(os.path.join(record['dir'], 'turn.json'),
                  encoding='utf-8') as f:
            assert json.load(f)['image_files'] == []
    # And a restart of the server on the same directory reads the
    # clean slate back.
    restarted = _restart_session(tmp_path / 'shots')
    for record in restarted.turns:
        assert record['image_files'] == []


def test_the_page_drops_the_cards_the_turn_closed():
    """The page's side of the closure, pinned the way `test_131`
    pins the page's behaviour on its own source: the card carries
    the window it shows (`data-window`), the `done` event hands the
    turn's closed list to the removal (`data.closed`), the removal
    asks the gallery for the cards by that address and recounts the
    group that held them under their name; and the server's `done`
    event is what carries the list the page drops by."""
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
    with open(os.path.join(root, 'viz_web', 'static', 'index.html'),
              encoding='utf-8') as f:
        page = f.read()

    # The card keeps the address of the window it shows: what a close
    # names, and what the Focus and Screenshot buttons of the card
    # already send.
    shot = page[page.index('function shotCard'):]
    shot = shot[:shot.index('function turnGroup')]
    assert 'data-window' in shot, \
        'la carte ne porte pas l''adresse de la fenêtre qu''elle montre ' \
        ': on ne saurait retirer de la galerie celle qu''on a fermée'

    # The removal: the cards the closed keys name leave the gallery,
    # and the group that held them counts what remains.
    rm = page[page.index('function removeClosed'):]
    rm = rm[:rm.index('function galleryEmpty')]
    assert 'data-window' in rm and 'remove()' in rm, \
        'la fermeture d''un tour doit retirer les cartes qu''elle nomme ' \
        'de la galerie'
    assert 'shotGroupCount' in rm, \
        'le groupe qui tenait la figure doit compter ce qu''il reste'

    # And the done event is what asks for the removal: the page reads
    # the closed list from the turn's answer.
    done = page[page.index('function onTurnDone'):]
    done = done[:done.index('function handleBlock')]
    assert 'data.closed' in done and 'removeClosed' in done, \
        'le done d''un tour qui ferme ne retire rien de la galerie: ' \
        'la figure y reste sous les yeux'

    # The server's done event carries the closed keys of the record.
    with open(os.path.join(root, 'viz_web', 'server.py'),
              encoding='utf-8') as f:
        server = f.read()
    ev = server[server.index('def _turnEvent'):]
    ev = ev[:ev.index('def _turnSummary')]
    assert "'closed'" in ev, \
        'l''evenement done ne porte pas les figures fermées: la page ' \
        'n''a pas de quoi retirer leurs cartes'
