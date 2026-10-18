# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""What the shot view says about a scalar, and about how a node is allowed to be used.

Two things the walk already knows and never hands on:

The scalar value. The walk stores the runtime object itself in the element's
``content`` attribute. Nothing downstream can then serialise the tree -- ElementTree
refuses an attribute that is not text -- and what the documentation panel shows for
a scalar is whatever that object's string happens to be, not the value.

The lifecycle status. The dictionary says whether a node is ``required``,
``optional``, ``experimental``, ``alpha`` or ``obsolescent``; the walk copies it
onto the shadow element and the tree builder drops it, so a quantity the data
dictionary marks as obsolete looks on screen exactly like one it marks as
mandatory. On the reference case's three IDSs alone that is 86 obsolescent nodes
and 40 alpha ones.
"""

import xml.etree.ElementTree as ET

import pytest

from imasviz.VizGUI.VizWidgets.QVizNodeDocumentationWidget import QVizNodeDocumentationWidget

from support.caseTrees import loadCaseTrees, leafByText, nodeAsTheBuilderBuildsIt
from support.fakes import FakeDocItem, FakeTreeView


@pytest.fixture(scope='module')
def case(qapp):
    return loadCaseTrees(qapp, ('tf',))


@pytest.mark.case
def test_the_shadow_tree_of_a_real_case_can_be_written_out(case):
    # The tree is an XML tree: being unable to serialise it is not a limitation
    # of a corner case, it means nothing can be done with it but walk it in
    # memory -- no dump, no comparison between two runs, no export.
    ET.tostring(case['trees']['tf'])


@pytest.mark.case
def test_every_attribute_of_the_shadow_tree_is_text(case):
    for element in case['trees']['tf'].iter():
        for name, value in element.attrib.items():
            assert isinstance(value, str), \
                '%s of %r holds a %s' % (name, element.get('name'),
                                         type(value).__name__)


@pytest.mark.case
def test_a_scalar_leaf_carries_its_value_as_text(case):
    leaf = leafByText(case['trees']['tf'], 'tf.ids_properties.homogeneous_time')
    assert leaf.get('content') == '1'


@pytest.mark.case
def test_a_scalar_leaf_is_not_described_by_its_runtime_wrapper(case):
    # '<IDSString0D (IDS:tf, ids_properties/provider, empty STR_0D)>' is the
    # string of the object, and it was what the panel showed for an unset scalar.
    leaf = leafByText(case['trees']['tf'], 'tf.ids_properties.provider')
    content = leaf.get('content')
    assert content == ''
    assert '<IDS' not in ET.tostring(leaf, encoding='unicode')


@pytest.mark.case
def test_the_tree_node_carries_the_lifecycle_status_of_its_dictionary_node(case,
                                                                           treeView):
    obsolescent = None
    for element in case['trees']['tf'].iter():
        if element.get('lifecycle_status') == 'obsolescent' and \
                element.find('name') is not None:
            obsolescent = element
            break
    assert obsolescent is not None, 'no obsolescent node in this IDS'

    node = nodeAsTheBuilderBuildsIt(obsolescent, 'tf', case['runtime']['tf'], treeView)

    assert node.getInfoDict()['lifecycle_status'] == 'obsolescent'


@pytest.fixture
def treeView(qapp, case):
    from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource
    view = FakeTreeView(uri=case['uri'])
    view.dataSource = QVizIMASDataSource('native', case['uri'])
    return view


@pytest.fixture
def panel(qtbot):
    widget = QVizNodeDocumentationWidget()
    qtbot.addWidget(widget)
    # A child widget only reports itself visible when its parents are, so the
    # panel has to be shown for a visibility assertion to mean what it says.
    widget.show()
    return widget


@pytest.mark.ui
def test_the_panel_shows_the_lifecycle_status_of_a_node(panel):
    panel.update(FakeDocItem(lifecycleStatus='obsolescent'), None)

    assert panel.lNodeLifecycleText.text() == 'obsolescent'
    assert panel.lNodeLifecycleText.isVisible()
    assert panel.lNodeLifecycleTitle.isVisible()


@pytest.mark.ui
def test_the_panel_shows_nothing_about_a_status_the_dictionary_does_not_give(panel):
    panel.update(FakeDocItem(), None)

    assert panel.lNodeLifecycleText.text() == ''
    assert not panel.lNodeLifecycleTitle.isVisible()


@pytest.mark.ui
def test_a_scalar_node_shows_its_value_in_the_panel(panel):
    # The value, not the object: the panel is where a user checks which number a
    # node holds, and a wrapper repr answers nothing.
    panel.update(FakeDocItem(content='2.42'), None)

    assert panel.lNodeContentsText.text() == '2.42'
