# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Which coordinate a node records when asked to change one of them.

setCoordinate() and setDefaultCoordinate() take a coordinate number but wrote
their time flag and their child label under coordinate 1 whatever was asked.
Nothing reaches coordinate 2 through the menus today (QVizSignalHandling builds
a coordinate1 menu only), so the defect stays latent until a caller asks.
"""

import pytest

from imasviz.VizGUI.VizTreeView.QVizTreeNode import QVizTreeNode

from PySide6.QtWidgets import QTreeWidgetItem


def makeNode(coordinates, defaults=None, flags=None):
    infoDict = {'IDSName': 'equilibrium', 'occurrence': 0, 'name': 'psi',
                'data_type': 'FLT_2D', 'isSignal': 1, 'isStatic': 0}
    node = QVizTreeNode(None, ['psi'], infoDict)
    node.coordinates = list(coordinates)
    node.default_coordinates = dict(defaults or {})
    node.coordinates_explicitly_time_dependent = dict(flags or {})
    return node


def test_a_non_time_coordinate_clears_its_own_time_flag(qapp):
    node = makeNode(['time', 'rho_tor_norm'], flags={1: 1, 2: 1})

    node.setCoordinate(2, 'rho_tor_norm')

    assert node.isCoordinateTimeDependent(2) is False
    # Coordinate 1 was left alone: its flag is not the one being set here.
    assert node.isCoordinateTimeDependent(1) is True


def test_a_time_coordinate_flags_the_number_being_set(qapp):
    node = makeNode(['rho_tor_norm', 'time'], flags={1: 0, 2: 0})

    node.setCoordinate(2, 'time_slice[itime].time')

    assert node.isCoordinateTimeDependent(2) is True
    assert node.isCoordinateTimeDependent(1) is False


def test_the_default_coordinate_clears_its_own_time_flag(qapp):
    node = makeNode(['time', 'z'], defaults={0: 'time', 1: 'r'},
                    flags={1: 1, 2: 1})

    node.setDefaultCoordinate(2)

    assert node.coordinates[1] == 'r'
    assert node.isCoordinateTimeDependent(2) is False
    assert node.isCoordinateTimeDependent(1) is True


def test_the_renamed_child_is_the_coordinate_being_set(qapp):
    node = makeNode(['time', 'rho_tor_norm'])
    QTreeWidgetItem(node, ['coordinate1=time'])
    QTreeWidgetItem(node, ['coordinate2=rho_tor_norm'])

    node.setCoordinate(2, '1..N')

    assert node.child(0).text(0) == 'coordinate1=time'
    assert node.child(1).text(0) == 'coordinate2=1..N'


def test_the_default_child_is_renamed_under_its_own_name(qapp):
    node = makeNode(['time', 'z'], defaults={0: 'time', 1: 'r'})
    QTreeWidgetItem(node, ['coordinate1=time'])
    QTreeWidgetItem(node, ['coordinate2=z'])

    node.setDefaultCoordinate(2)

    assert node.child(0).text(0) == 'coordinate1=time'
    assert node.child(1).text(0) == 'coordinate2=r'
