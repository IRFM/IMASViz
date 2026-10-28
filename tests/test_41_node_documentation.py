# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""What the node documentation panel says, measured before and after.

The panel is what a click on the shot view answers when a user asks "what is
this node?". The widget it replaces was measured on nodes built the way
`QVizDataTreeViewBuilder` builds them, on the reference case, and the numbers
below are those measurements -- which is why they are pinned one by one:

* `Number of zeros` was `len(np.where(values == 0))`, the length of a
  one-element tuple: `1` for an array of 3 values with no zero, `1` for an array
  with 3 zeros, `1` for the 101 values of `profiles_1d/psi`.
* `Min`/`Max` were the plain extremes, so `[1, nan, inf, -inf, 0]` answered
  `-inf` and `inf`.
* A string array went through the numeric branch: `['a', 'b']` answered
  `Min: a`, `Max: b`, `Number of zeros: 1`.
* The content of an array was `str(values)`: the IMAS-Python wrapper first,
  `<IDSNumericArray (IDS:equilibrium, time_slice[0]/profiles_1d/psi, FLT_1D)>`,
  then the numbers -- 1543 characters for 101 values.
* The constructor called `np.set_printoptions(threshold=sys.maxsize)` and never
  undid it: the threshold went from 1000 to 9223372036854775807 for the whole
  process, and a million floats printed 12,166,667 characters in 75.08 s.
* It pre-filled its twenty labels with `/` and showed them, so a quantity with
  no minimum read `Min: /`.
* It hid its fields, then died reading, so a failed read left the previous
  node's `Node: equilibrium.psi`, `Array size: 101` and `Content: [-7.9 ...`
  in labels that were all hidden.
* It defined `update(self, item, dataTreeView)` on a QWidget, so the
  no-argument `update()` Qt itself calls answered `TypeError: ... missing 2
  required positional arguments`.
"""

import numpy as np
import pytest
from PySide6.QtWidgets import QWidget

from imasviz.VizGUI.VizWidgets.VizNodeDocumentation \
    import QVizNodeDocumentationPanel, QVizNodeFacts

from support.caseTrees import loadCaseTrees, elementByTreePath, \
    nodeAsTheBuilderBuildsIt
from support.fakes import FakeDocItem, FakeTreeView


@pytest.fixture
def panel(qtbot):
    widget = QVizNodeDocumentationPanel()
    qtbot.addWidget(widget)
    widget.show()
    return widget


def node(**kwargs):
    """A node of the kind the panel is asked about, without a case."""
    kwargs.setdefault('dataType', 'FLT_1D')
    kwargs.setdefault('is0D', False)
    kwargs.setdefault('is1D', True)
    kwargs.setdefault('documentation', 'documentation of psi')
    kwargs.setdefault('name', 'psi')
    kwargs.setdefault('dataName', 'equilibrium.psi')
    kwargs.setdefault('path', 'equilibrium/psi')
    return FakeDocItem(**kwargs)


def rowWith(panel, label):
    rows = [row for row in panel.displayedRows() if row.startswith(label)]
    assert len(rows) == 1, 'no %r row in %r' % (label, panel.displayedRows())
    return rows[0]


@pytest.mark.ui
def test_the_panel_says_it_has_nothing_to_show_before_the_first_click(panel):
    assert panel.displayedRows() == ['Node: no node selected yet']


@pytest.mark.ui
def test_the_panel_leaves_the_way_numpy_prints_everything_alone(panel):
    # Measured: the replaced widget's constructor called
    # np.set_printoptions(threshold=sys.maxsize) and nothing put it back, so
    # every array printed in the process -- by another widget, in the log, in a
    # test -- stopped being truncated.
    threshold = np.get_printoptions()['threshold']

    panel.showNode(node(values=np.arange(5000.)))

    assert np.get_printoptions()['threshold'] == threshold


@pytest.mark.ui
def test_the_no_argument_update_qt_calls_is_still_the_one_from_qt(panel):
    # Measured: the replaced class answered panel.update() with
    # "TypeError: QVizNodeDocumentationWidget.update() missing 2 required
    # positional arguments: 'item' and 'dataTreeView'".
    assert 'update' not in vars(QVizNodeDocumentationPanel)
    assert QVizNodeDocumentationPanel.update is QWidget.update
    panel.update()


@pytest.mark.ui
@pytest.mark.parametrize('values, expected', [
    ([1.5, 2.5, 3.5], '0'),      # measured answer: 1
    ([0.0, 0.0, 1.0, 0.0], '3'),  # measured answer: 1
    (list(np.linspace(-7.97, -7.78, 101)), '0'),   # measured answer: 1
    ([0.0] * 49, '49'),
])
def test_the_number_of_zeros_counts_the_zeros(panel, values, expected):
    panel.showNode(node(values=np.array(values)))

    assert rowWith(panel, 'Number of zeros: ') == 'Number of zeros: ' + expected


@pytest.mark.ui
def test_min_and_max_are_of_the_entries_that_are_numbers(panel):
    # Measured on that very array: Min '-inf', Max 'inf' -- which says neither
    # what the quantity reaches nor that two of its entries are not numbers.
    panel.showNode(node(values=np.array([1.0, np.nan, np.inf, -np.inf, 0.0])))

    assert rowWith(panel, 'Min: ') == 'Min: 0.0'
    assert rowWith(panel, 'Max: ') == 'Max: 1.0'
    assert rowWith(panel, 'Invalid entries (nan): ') == \
        'Invalid entries (nan): 1'
    assert rowWith(panel, 'Invalid entries (inf): ') == \
        'Invalid entries (inf): 2'
    assert rowWith(panel, 'Number of zeros: ') == 'Number of zeros: 1'


@pytest.mark.ui
def test_an_array_of_nothing_but_non_numbers_says_it_has_no_extremes(panel):
    panel.showNode(node(values=np.array([np.nan, np.inf, -np.inf])))

    assert not [row for row in panel.displayedRows()
                if row.startswith(('Min: ', 'Max: '))]
    assert rowWith(panel, 'No values: ') == \
        'No values: none of the 3 entries is a number, so there is no minimum ' \
        'and no maximum.'


@pytest.mark.ui
def test_a_string_array_is_not_described_with_numbers(panel):
    # Measured on ['a', 'b']: Min 'a', Max 'b', Number of zeros '1', and the two
    # Invalid entries rows left at '/' by the bare except: that caught np.isnan
    # refusing strings.
    panel.showNode(node(values=np.array(['a', 'b']), dataType='STR_1D'))

    rows = panel.displayedRows()
    assert not [row for row in rows
                if row.startswith(('Min: ', 'Max: ', 'Number of zeros: ',
                                   'Invalid entries'))]
    assert rowWith(panel, 'Array size: ') == 'Array size: 2'
    assert "'a'" in rowWith(panel, 'Content: ')
    assert "'b'" in rowWith(panel, 'Content: ')


@pytest.mark.ui
def test_a_long_array_is_previewed_and_says_what_is_missing(panel):
    # The replaced widget formatted the whole array before showing 200 values at
    # each end: 1543 characters for 101 values, and 12,166,667 for a million.
    panel.showNode(node(values=np.arange(1000.)))

    content = rowWith(panel, 'Content: ')
    assert '600 of 1000 values not shown' in content
    assert len(content) < 6000


@pytest.mark.ui
def test_an_array_short_enough_is_shown_whole(panel):
    panel.showNode(node(values=np.arange(10.)))

    assert 'not shown' not in rowWith(panel, 'Content: ')
    assert '9.' in rowWith(panel, 'Content: ')


@pytest.mark.ui
def test_the_content_of_an_array_is_its_values_not_the_object_holding_them(panel):
    # The 101 values of the reference case's profiles_1d/psi, so the numbers
    # checked here are the ones a user reads on screen.
    panel.showNode(node(values=np.linspace(-7.974793228488357,
                                           -7.779899606708878, 101)))

    content = rowWith(panel, 'Content: ')
    assert 'IDSNumericArray' not in content
    assert content.startswith('Content: [-7.97479323')


@pytest.mark.ui
def test_a_two_dimension_array_gives_its_shape_and_its_size(panel):
    panel.showNode(node(values=np.zeros((3, 4)), dataType='FLT_2D', is1D=False,
                        is2DOrLarger=True))

    assert rowWith(panel, 'Array shape: ') == 'Array shape: (3, 4)'
    assert rowWith(panel, 'Array size: ') == 'Array size: 12'


@pytest.mark.ui
def test_a_question_the_node_cannot_answer_is_absent_rather_than_a_slash(panel):
    # Measured on a real FLT_2D with no values in it: 'Min: /', 'Max: /',
    # 'Content: /' -- twenty labels prefilled with that one character.
    panel.showNode(node(values=np.zeros((0, 0)), dataType='FLT_2D', is1D=False,
                        is2DOrLarger=True))

    for row in panel.displayedRows():
        assert not row.endswith(': /'), row
    assert rowWith(panel, 'Content: ') == 'Content: (empty)'


@pytest.mark.ui
def test_the_units_the_dictionary_gives_are_shown(panel):
    panel.showNode(node(values=np.array([1.0]), units='Wb'))

    assert rowWith(panel, 'Units: ') == 'Units: Wb'


@pytest.mark.ui
def test_a_scalar_shows_the_value_the_walk_left_on_the_node(panel):
    panel.showNode(FakeDocItem(content='2.42'))

    assert rowWith(panel, 'Value: ') == 'Value: 2.42'


@pytest.mark.ui
def test_a_scalar_the_case_leaves_empty_says_so(panel):
    # Two different "nothing": the walk copies None when the case holds no
    # value, and the empty string when it holds an empty one. Measured on the
    # reference case: 3518 of the 5706 zero-dimension leaves of equilibrium's
    # tree carry no content at all.
    panel.showNode(FakeDocItem(content=''))
    assert rowWith(panel, 'Value: ') == 'Value: empty'

    panel.showNode(FakeDocItem(content=None))
    assert rowWith(panel, 'Value: ') == \
        'Value: no value stored in the opened case'


@pytest.mark.ui
def test_a_scalar_is_never_described_by_its_runtime_wrapper(panel):
    # The reference case's unset tf.ids_properties/provider is an empty STR_0D
    # whose string is '<IDSString0D (IDS:tf, ids_properties/provider, empty
    # STR_0D)>'.
    panel.showNode(FakeDocItem(content=None, dataType='STR_0D'))

    assert 'IDSString' not in ''.join(panel.displayedRows())


@pytest.mark.ui
def test_a_structure_holds_no_values_and_says_nothing_about_values(panel):
    panel.showNode(node(dataType='structure', values=None))

    rows = panel.displayedRows()
    assert not [row for row in rows
                if row.startswith(('Array size: ', 'Array shape: ',
                                   'Content: ', 'No values: '))]


@pytest.mark.ui
def test_an_ids_root_shows_its_name_and_its_documentation(panel):
    panel.showNode(FakeDocItem(name='equilibrium', dataName='equilibrium',
                               documentation='MHD equilibrium and transport',
                               isIDSRoot=True, dataType=None, units=None))

    assert panel.displayedRows() == ['Node: equilibrium',
                                     'Documentation: MHD equilibrium and '
                                     'transport']


@pytest.mark.ui
def test_a_node_whose_values_cannot_be_read_says_why(panel):
    panel.showNode(node(readError=AttributeError(
        "IDS structure 'equilibrium' has no attribute 'comment'")))

    assert rowWith(panel, 'No values: ') == \
        'No values: AttributeError: IDS structure \'equilibrium\' has no ' \
        'attribute \'comment\''


@pytest.mark.ui
def test_a_failed_read_leaves_nothing_of_the_previous_node(panel):
    # Measured: the replaced widget hid its fields first and then died reading,
    # so the hidden labels still held Node 'equilibrium.psi', Array size '101'
    # and Content '[-7.9 ...' -- the identity of a node nobody had clicked.
    panel.showNode(node(values=np.linspace(-7.97, -7.78, 101)))
    panel.showNode(node(name='ghost', dataName='equilibrium.ghost',
                        readError=RuntimeError('no such node')))

    rows = panel.displayedRows()
    assert '101' not in ''.join(rows)
    assert '-7.9' not in ''.join(rows)
    assert rowWith(panel, 'Node: ') == 'Node: equilibrium.ghost'


@pytest.mark.ui
def test_the_second_node_replaces_the_first_wholesale(panel):
    panel.showNode(node(name='psi', dataName='equilibrium.psi',
                        documentation='Poloidal flux', units='Wb',
                        values=np.array([1.0, 2.0])))
    panel.showNode(node(name='r', dataName='equilibrium.r',
                        documentation='Major radius', units='m',
                        values=np.array([3.0])))

    rows = panel.displayedRows()
    assert 'psi' not in ''.join(rows)
    assert 'Wb' not in ''.join(rows)
    assert rowWith(panel, 'Node: ') == 'Node: equilibrium.r'
    assert rowWith(panel, 'Max: ') == 'Max: 3.0'


@pytest.fixture(scope='module')
def case(qapp, request):
    return loadCaseTrees(qapp, ('equilibrium',), request=request)


@pytest.fixture
def realView(qapp, case):
    return FakeTreeView(uri=case['uri'])


def realNode(case, view, path):
    """The node the shot view would show under that path, reading for real."""
    element, walked = elementByTreePath(case['trees']['equilibrium'],
                                        'equilibrium', path)
    return nodeAsTheBuilderBuildsIt(element, 'equilibrium',
                                    case['runtime']['equilibrium'], view,
                                    path=walked)


@pytest.mark.ui
@pytest.mark.case
def test_a_real_leaf_shows_the_numbers_the_case_holds(panel, case, realView):
    # Measured on the replaced widget for this very leaf: Array size '72',
    # Min '2.578317930647737', Max '2.8251454055323495', zeros '1' (there are
    # none), Content '<IDSNumericArray (IDS:equilibrium, time_slice[0]/boundary
    # /ou...'.
    panel.showNode(realNode(case, realView,
                            'equilibrium/time_slice(0)/boundary/outline/r'))

    rows = panel.displayedRows()
    assert rowWith(panel, 'Node: ') == \
        'Node: equilibrium.time_slice[0].boundary.outline.r'
    assert rowWith(panel, 'Documentation: ') == 'Documentation: Major radius'
    assert rowWith(panel, 'Units: ') == 'Units: m'
    assert rowWith(panel, 'Array size: ') == 'Array size: 72'
    assert rowWith(panel, 'Min: ') == 'Min: 2.578317930647737'
    assert rowWith(panel, 'Max: ') == 'Max: 2.8251454055323495'
    assert rowWith(panel, 'Number of zeros: ') == 'Number of zeros: 0'
    assert 'IDSNumericArray' not in ''.join(rows)


@pytest.mark.ui
@pytest.mark.case
def test_a_real_leaf_shows_its_numbers_and_says_how_many_there_are(panel, case,
                                                                   realView):
    panel.showNode(realNode(case, realView,
                            'equilibrium/time_slice(0)/profiles_1d/psi'))

    content = rowWith(panel, 'Content: ')
    assert 'IDSNumericArray' not in content
    assert content.startswith('Content: [-7.97479323')
    assert rowWith(panel, 'Array size: ') == 'Array size: 101'


@pytest.mark.ui
@pytest.mark.case
def test_a_real_leaf_without_values_says_the_shape_it_has(panel, case, realView):
    # 48 of equilibrium's leaves are FLT_2D and 6 are FLT_4D; measured, the
    # replaced widget showed 'Array shape: (0, 0)' under the label of its data
    # type, then 'Min: /', 'Max: /' and 'Content: /'.
    panel.showNode(realNode(case, realView,
                            'equilibrium/time_slice(0)/coordinate_system/'
                            'grid/volume_element'))

    rows = panel.displayedRows()
    assert not [row for row in rows if row.endswith(': /')]
    assert rowWith(panel, 'Array shape: ') == 'Array shape: (0, 0)'
    assert rowWith(panel, 'Content: ') == 'Content: (empty)'


@pytest.mark.ui
@pytest.mark.case
def test_a_real_scalar_shows_its_value(panel, case, realView):
    panel.showNode(realNode(case, realView,
                            'equilibrium/ids_properties/homogeneous_time'))

    assert rowWith(panel, 'Value: ') == 'Value: 0'


@pytest.mark.ui
@pytest.mark.case
def test_a_real_scalar_the_case_leaves_empty_says_empty(panel, case, realView):
    # Measured: this leaf's content is the empty string, which is a filled node
    # holding nothing -- different from the 3652 leaves of this IDS whose
    # content is None.
    panel.showNode(realNode(case, realView, 'equilibrium/ids_properties/source'))

    assert rowWith(panel, 'Value: ') == 'Value: empty'


@pytest.mark.ui
@pytest.mark.case
def test_a_real_scalar_the_case_does_not_fill_says_so(panel, case, realView):
    panel.showNode(realNode(case, realView,
                            'equilibrium/ids_properties/source/name'))

    assert rowWith(panel, 'Value: ') == \
        'Value: no value stored in the opened case'


@pytest.mark.ui
@pytest.mark.case
def test_a_real_structure_says_what_it_holds_without_inventing_numbers(panel,
                                                                       case,
                                                                       realView):
    panel.showNode(realNode(case, realView,
                            'equilibrium/time_slice(0)/profiles_1d'))

    rows = panel.displayedRows()
    assert rowWith(panel, 'Node: ') == 'Node: profiles_1d'
    assert not [row for row in rows
                if row.startswith(('Array size: ', 'Array shape: ',
                                   'Content: '))]


@pytest.mark.ui
@pytest.mark.case
def test_the_walk_of_a_real_leaf_leaves_numpy_printing_as_it_found_it(panel,
                                                                      case,
                                                                      realView):
    threshold = np.get_printoptions()['threshold']

    panel.showNode(realNode(case, realView,
                            'equilibrium/time_slice(0)/profiles_1d/psi'))

    assert np.get_printoptions()['threshold'] == threshold


def test_the_facts_of_a_node_are_asked_once():
    asked = []

    class Counting(FakeDocItem):
        def resolvePath(self, expression):
            asked.append(expression)
            return np.array([1.0, 2.0])

    facts = QVizNodeFacts(Counting(dataType='FLT_1D', is0D=False, is1D=True))

    assert asked == ['tf.rho_tor']
    assert facts.size == '2'
