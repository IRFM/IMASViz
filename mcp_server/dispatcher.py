# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""Run one function on the GUI thread from any worker thread, and wait for it.

This is a re-export for backward compatibility. The real implementation
lives in ``imasviz.VizAgent.dispatcher``.
"""

from imasviz.VizAgent.dispatcher import GuiDispatcher

__all__ = ['GuiDispatcher']
