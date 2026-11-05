# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Drive the IMASViz application from an MCP agent.

Two layers, kept apart on purpose:

* ``core`` -- `McpGuiCore`, the gestures of one application session, written
  against the application's own entries (`QViz*` commands, `Viz_API`) and
  importing nothing but `imasviz` and PySide6. It is what the test suite
  drives directly, and what a bridge into a running GUI would call.

* ``server`` / ``tools`` -- the MCP protocol surface: the server built on the
  official `mcp` SDK, streamable HTTP on localhost, and the tool
  declarations that dispatch every call to the GUI thread through
  `GuiDispatcher` and back into ``core``.

The package sits **outside** the `imasviz` package so the module stack the
application is loaded from never reaches the SDK's dependencies, and so the
import sweep of `tests/test_99` does not count modules that import it.
"""
