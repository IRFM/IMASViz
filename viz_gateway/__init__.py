# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
# __init__.py
"""The tenancy layer around the IMASViz web sessions.

`python3 -m viz_gateway` answers more than one user at a time. Each user is an
`Authorization` token that maps to one `viz_web` instance -- a local one this
process spawns on its own loopback port, isolated by its own
$HOME/.imasviz, or a remote one registered by its `https://` URL. The layer
has **no** widget of its own: `starlette` and `httpx` route each request to the
one instance `entryFor` names, and the pool holds those instances, not the Qt --
the `QApplication`, the `Viz_API` and the `GuiDispatcher` of every user live in
their own process, which is what makes a user's case invisible to another's.

* `userstore` -- the token to user to backend catalog, and the named refusal
  when a token is unknown; the file is the `users.json` under the gateway's
  directory.
* `ports` -- one loopback port per spawned instance, chosen by the kernel.
* `spawner` -- the pool: one backend per user, its budget (the live ceiling and
  the idle reaping), and their health.
* `proxy` -- the reverse proxy that streams the `/api/agent` event stream and
  answers the JSON of every gesture, the hop-by-hop headers of the two sides
  kept apart.
* `run` / `__main__` -- the command line, and the one uvicorn loop that pumps
  both the proxy and the pool's reaping.

It sits **outside** the `imasviz` package, as `viz_web` and `viz_cli` do, so the
import sweep of `tests/test_99` does not count it. `starlette`, `uvicorn` and
`httpx` -- all importable here -- are the only dependencies: the Qt and the IMAS
HLI live in the spawned children, not in this one.
"""
