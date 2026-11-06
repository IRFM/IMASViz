# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
# __init__.py
"""IMASViz without its window: a client for the in-app agent's prompts.

`python3 -m viz_cli` opens one session of the application offscreen --
the same construction order the MCP service builds it in -- and holds it
open for the whole REPL: a line runs it, the arrows walk the prompts of
the run and of the runs before it, and each turn leaves its images and
its transcript under the turns directory.

* `session` -- one session, and the one turn a prompt is asked of;
  the LLM's running parameters (`/llm`'s) sit on the `Client` it owns.
* `commands` -- the `/` commands, parsed and answered by name.
* `run` -- the entry: the REPL, `main`, the arguments, readline's file.

The package sits **outside** the `imasviz` package, as `mcp_server`
does, so the import sweep of `tests/test_99` does not count it, and the
one-shot path reuses `mcp_server.agent_mode.runAgentMode` instead of
carrying a second copy of it.
"""
