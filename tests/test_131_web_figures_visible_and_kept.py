# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The figures a web session drew: visible in the page, kept by a restart.

The user's report, in two halves:

* **"aucune figure n'est visible"** -- the agent answered "la figure
  Plot1 est affichée" the moment its loop wrote it, and the capture is
  on disk (the record holds it, `saveShots` wrote it). What the page
  then did with it: a `details` group, **closed**, prepended at the top
  -- so the figure is behind a bar its user does not click, while the
  agent's own words say it is shown. The live prepend must open the
  group it inserts: the request just finished, its pictures are the
  answer, and the answer is not left closed in the drawer.

* **"redémarré le serveur … aucune figure"** -- the turns of a session
  are in memory of the process. The captures are on disk (`/api/turns/
  {n}/shots/{name}` serves them from the turn's `dir`), and the reports
  are on disk. A restart of the server kept the PNGs and lost the list
  that names them: the page then rebuilt its gallery from an empty
  `/api/turns` and answered "No capture yet" for a session that had
  drawn. The record of a turn is written in the turn's own directory,
  and a session that starts on the same `shots_dir` reads them back
  before it answers `/api/turns`.
"""

import os

from imasviz.VizAgent.llm_client import LLMResponse
from viz_web.web_session import WebSession

from test_119_viz_web_session import (
    CASE_URI, FakeLLMClient, FakeWindow, build, inWorker)


def test_a_server_restart_keeps_the_turns_and_their_captures(qapp, tmp_path):
    """One session in a directory, then **a new process on the same
    directory** -- the restart. Its turn list holds the previous turn,
    its pictures, their names, and the directory their PNGs are under;
    and the PNG is on disk where the record points (the route that
    serves it is one `os.path.join`, and a directory that points at the
    nothing is the capture nobody can get back)."""
    shots = str(tmp_path / 'shots')
    session, core = build(qapp, tmp_path)

    session.agent.llm = FakeLLMClient([
        LLMResponse(tool_calls=[
            {'name': 'plot_one',
             'args': {'uri': CASE_URI, 'path': 'core.ion[0].temp'}}],
            content=''),
        LLMResponse(content='tracé.', finish_reason='stop'),
    ])
    record = inWorker(lambda: session.runTurn('trace une figure'), qapp)
    assert record['image_files'] == ['SlicesPlot1.png'], \
        record['image_files']
    png = os.path.join(record['dir'], 'SlicesPlot1.png')
    assert os.path.isfile(png)

    # The restart: a fresh session on the same captures directory.
    from viz_cli.session import Client
    from imasviz.VizAgent.llm_client import LLMClient
    from test_119_viz_web_session import FakeCore
    session2 = WebSession(app=None, window=FakeWindow(),
                          core=FakeCore(),
                          client=Client(LLMClient(
                              endpoint='http://127.0.0.1:65531/v1',
                              model='stub', timeout=2.0)),
                          shots_dir=shots, max_turns=8)

    # The list the page rebuilds its gallery from:
    assert session2.turns, \
        'a new process on the same captures directory answers no turn: ' \
        'the previous session drew one, and its pictures are on disk ' \
        'where its record points'
    one = session2.turns[0]
    assert one['prompt'] == 'trace une figure', one['prompt']
    assert one['image_files'] == ['SlicesPlot1.png'], one['image_files']
    assert one['image_windows'][0]['window'] == 'SlicesPlot1'
    # And the capture itself, where the record says it is:
    assert os.path.isfile(os.path.join(one['dir'], 'SlicesPlot1.png'))


def test_the_page_opens_the_group_of_the_just_finished_request():
    """The figure the live prepend inserts is the answer of the request
    that just finished: the group it goes under is open. The groups the
    page rebuilds after a reload are history -- they stay closed the
    way they have been (the request names itself and its count, and
    it reveals its pictures when it is opened). Pinned on the page's
    own source, the way `test_121` pins it: the live path opens, the
    rebuild path does not."""
    import re

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        '..', 'viz_web', 'static', 'index.html')
    with open(path, encoding='utf-8') as f:
        page = f.read()

    live = page[page.index('function prependTurnShots'):]
    live = live[:live.index('function galleryEmpty')]
    assert re.search(r'\.open\s*=\s*true', live), \
        'the live prepend leaves its group closed: the figure the agent ' \
        'says it showed is behind a bar the user does not click'

    rebuild = page[page.index('function buildGallery'):]
    rebuild = rebuild[:rebuild.index('function gesture')]
    assert '.open = true' not in rebuild, \
        'the rebuilt history must stay closed: the live answer is the ' \
        'one that opens, not the wall the reload would make'
