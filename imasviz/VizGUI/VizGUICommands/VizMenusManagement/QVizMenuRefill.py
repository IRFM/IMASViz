# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Taking a menu back before it is filled again.

Every menu IMASVIZ refills when it is opened does it in two moves: take out what
is on screen, draw what is on screen *now*. The first move is where the bugs
live. ``QMenu.clear()`` removes the actions and **keeps the objects**, and a
sub-menu built with its parent -- the only shape that survives on PySide6, see
T0, T7 and T21 -- stays a child of the menu it hangs on. A refill that stops at
``clear()`` therefore leaves behind a whole branch the user cannot reach, and it
leaves one more on every opening.

Measured on a plain menu with one sub-menu: after ``clear()`` the actions answer
**0** and the ``QMenu`` children still answer **1**; three refills of two
parented sub-menus each answer **7** children for **0** actions. That is the
state the shot view's *Plot windows* menu was in -- it called ``clear()`` and
rebuilt -- and it is why ``QVizFileMenu`` deletes what it replaces by hand. The
helper is here so the three refills of the package cannot drift apart again.
"""

from PySide6.QtWidgets import QMenu


def refill(menu):
    """Take every entry of that menu out, the sub-menus included.

    The sub-menus are taken out by what they are, not by what an action points
    at: the leak this exists for is exactly the branch no action reaches any
    more, so walking ``actions()`` alone would leave it on the menu.
    """
    for action in list(menu.actions()):
        menu.removeAction(action)
        action.deleteLater()
    for submenu in menu.findChildren(QMenu):
        submenu.deleteLater()
