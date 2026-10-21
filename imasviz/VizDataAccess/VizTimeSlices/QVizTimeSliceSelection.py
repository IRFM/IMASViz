# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""How many elements of a dynamic array of structures a view keeps.

A dynamic IDS holds its quantities along an array of structures -- 49 time
slices for `equilibrium` in the reference case. A shot view may keep all of them,
the first one, one in ten, or one the user names. That choice used to travel as
an integer: `QVizViewLoadingStrategy` named the four choices and a static
`getLoadingStrategyIdentifier` turned each name into 1, 2, 3 or 4, and the walk
then compared the integer to those four literals at
`QVizIDSViewParser.py:426-437`. Measured consequences:

* a name that is not one of the four becomes **1 in silence** -- `all time
  slices` (a lower case a), `All slices`, `Toutes`, and `None` all answered 1,
  so a typo silently loads the first slice of a case the user asked to see whole;
* the four are handed to the menu in the order 3, 2, 1, 4, so the menu order and
  the code order disagree by construction;
* `setIdentifier` is defined twice in the same class, the second definition
  winning, and both do the same thing;
* `getLabel()` returns None unless a flag named `is_ids_dynamic` is set, and that
  flag is set **only in the branch for 4** -- measured, all four strategies answer
  `getLabel() == None` coming out of `getAllStrategies()`, so three of the four
  views get no label in the tree and the occurrence node cannot tell them apart;
* asking for slice 49 of 49 is refused only four seconds later, deep in the walk,
  by `ValueError: Bad input from user: time index too large.`.

So the choice is one object here, knowing its menu words, the words the tree
shows, and the window it wants out of an array of a given length. No integer
travels anywhere, and the refusal of an index past the end names how many slices
there are.
"""

from imas.ids_data_type import IDSDataType


class QVizTimeSliceSelection:
    """One way of slicing a dynamic array of structures, named by what it does."""

    def __init__(self, menuLabel, viewLabel, window):
        self._menuLabel = menuLabel
        self._viewLabel = viewLabel
        self._window = window

    def menuLabel(self):
        """What the entry in the menu says."""
        return self._menuLabel

    def viewLabel(self):
        """What the occurrence node says about the view it heads.

        Always available: the label of a view does not depend on the walk having
        noticed a dynamic array, which is what made the old one invisible for
        three of the four choices.
        """
        return self._viewLabel

    def window(self, length):
        """The first, the past-the-end and the step this selection keeps.

        `length` is how many elements the array holds. The refusal says how many
        there are, rather than reaching the walk and failing there.
        """
        return self._window(length)

    def asksForAnIndex(self):
        """Whether this selection still needs a number from the user."""
        return False

    def __repr__(self):
        return '<QVizTimeSliceSelection %s>' % self._menuLabel

    #: What an unbounded question accepts: the largest index a spin box takes.
    #: Only used when the number of elements cannot be known before the walk.
    LARGEST_INDEX = 2147483647


ALL_SLICES = QVizTimeSliceSelection(
    'All time slices', 'displaying all time slices',
    lambda length: (0, length, 1))

ONE_IN_TEN = QVizTimeSliceSelection(
    'One over 10 time slices', 'displaying one over 10 time slices',
    lambda length: (0, length, 10))

FIRST_SLICE = QVizTimeSliceSelection(
    'First time slice only', 'displaying first time slice',
    # An array that holds nothing has no first element: on the reference case
    # `tf.time_slice` is empty, and asking for slice 0 of it invented a whole
    # empty subtree -- 11 nodes on 77 -- where the walk kept none.
    lambda length: (0, 1 if length else 0, 1))


def atIndex(index):
    """The selection that keeps one named element, or asks for it later.

    `atIndex(None)` is the menu entry, which knows it must ask before it can
    answer; `atIndex(7)` is the answer to that question.
    """
    if index is None:
        return _AskForAnIndex()
    return QVizTimeSliceSelection(
        'Specific time slice only',
        'displaying time slice with index=%d' % index,
        _windowForIndex(index))


def _windowForIndex(index):
    def window(length):
        if not 0 <= index < length:
            # Said here, before the walk, with the number that makes it obvious:
            # measured, slice 48 of the 49 equilibrium slices passes and 49 is
            # refused -- by a message that named neither the count nor the bound.
            raise ValueError('%r is not a time slice of this IDS: it holds %d, '
                             'so the index runs from 0 to %d.'
                             % (index, length, length - 1))
        return index, index + 1, 1
    return window


class _AskForAnIndex(QVizTimeSliceSelection):
    """The menu entry for one named element, before the element is named."""

    def __init__(self):
        QVizTimeSliceSelection.__init__(
            self, 'Specific time slice only', 'specific time slice',
            _refuseAnUnansweredQuestion)

    def asksForAnIndex(self):
        return True


def _refuseAnUnansweredQuestion(length):
    raise ValueError('No time slice index was given: this IDS holds %d, so the '
                     'index runs from 0 to %d.' % (length, length - 1))


def menuSelections():
    """The four selections, in the order the menu lists them.

    The manual lists them as all, one over ten, specific, first; the old menu
    reached that order by listing four names and mapping them to 3, 2, 1, 4.
    """
    return [ALL_SLICES, ONE_IN_TEN, atIndex(None), FIRST_SLICE]


def dynamicArrayCount(idsInstance):
    """How many elements the widest dynamic array of a loaded IDS holds.

    The number bounds the question the "Specific time slice only" entry asks:
    measured on the reference case, the reference `equilibrium` occurrence 0
    holds 49 time slices, and the spin box that asked the question accepted
    anything up to 2147483647. An IDS can hold more than one dynamic array --
    `equilibrium` holds `time_slice` (49) and `grids_ggd` (1) -- and the choice
    is one index for all of them, so the widest is the one worth offering: the
    narrower array refuses an index past its own end, naming its count.

    None is returned when there is no IDS instance in memory to ask -- an
    occurrence not loaded yet -- and then the question stays open and `window`
    refuses an index past the end, naming the count.
    """
    if idsInstance is None:
        return None
    widest = None
    for childMeta in idsInstance.metadata:
        if childMeta.data_type is IDSDataType.STRUCT_ARRAY \
                and childMeta.type.is_dynamic:
            try:
                length = len(getattr(idsInstance, childMeta.name))
            except Exception:
                continue
            if widest is None or length > widest:
                widest = length
    return widest
