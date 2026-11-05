# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
# __init__.py
"""The in-app agent: the gestures, the LLM client, the loop, and the panel.

`core` is the layer the agent drives: the gestures of one IMASViz session,
importing nothing but `imasviz` and PySide6. `dispatcher` runs a function
on the GUI thread from any worker thread. `llm_client` talks to an
OpenAI-compatible endpoint. `agent` is the LLM → tool loop. `tools` holds
the system instructions and the tool schemas. `panel` is the MDI window.
"""
