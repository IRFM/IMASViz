# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
# __init__.py
"""IMASViz without its window, on a page: the agent and the raw gestures.

`python3 -m viz_web` opens one session of the application offscreen -- the
same construction order the REPL and the MCP service build it in -- holds it
open, and answers it from the browser. The page (`static/index.html`) is one
self-contained file, no build and no external dependency: a column for the
chat (a prompt runs the same `AgentLoop`, and its lines stream over
`POST /api/agent` as they arrive), and one for every gesture of the core
(open, load, search, plot, list, reports ...) driven by hand over
`POST /api/tool`. Every turn leaves its images and its transcript under the
turns directory, the way the REPL leaves them, and the page shows the
current set inline and holds the history behind a path.

* `web_session` -- one session of the core and its agent, and the turn a
  prompt is asked of; the LLM's running parameters sit on the `Client` it
  owns (the one the REPL reads too).
* `server` -- the Starlette app: the routes the page talks to, streaming
  the agent's transcript and the gestures' answers.
* `run` -- the entry: the arguments, the offscreen application, the
  transport on its own daemon thread, and the main thread in `app.exec_()`
  that every gesture is queued onto through the `GuiDispatcher`.

The package sits **outside** the `imasviz` package, as `viz_cli` and
`mcp_server` do, so the import sweep of `tests/test_99` does not count it,
and the one-shot path and the dispatcher both come from `mcp_server` and
`imasviz.VizAgent` -- nothing is carried twice.
"""
