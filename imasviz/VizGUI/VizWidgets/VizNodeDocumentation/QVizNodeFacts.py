# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""What a shot view knows about one node, said in words the user can check.

Nothing here touches Qt: the panel draws, this decides what is worth drawing.
That split is what makes the answers testable, and the answers were worth
deciding because the panel this replaces answered wrong in four measured ways
on real nodes of the reference case:

* `Number of zeros` was `len(np.where(values == 0))`. For a one-dimension array
  `np.where` returns a one-element tuple, so that length is **1** whatever the
  array holds: measured, an array of 3 values without a single zero, an array
  with 3 zeros and the 101 values of `equilibrium.time_slice[0].profiles_1d/psi`
  all three answered `1`.
* `Min` and `Max` were the plain minimum and maximum, so an array holding
  infinities answered `Min: -inf` and `Max: inf` -- which says neither what the
  quantity reaches nor that the entries in question are not numbers. Measured on
  `[1, nan, inf, -inf, 0]`.
* A string array went through the same numeric branch: measured on `['a', 'b']`,
  `Min: 'a'`, `Max: 'b'`, `Number of zeros: 1`, and the two `Invalid entries`
  rows left at `/` by the bare `except:` that caught `np.isnan` refusing strings.
* The value of an array was `str(values)`, which for an IMAS-Python array is the
  wrapper first: `<IDSNumericArray (IDS:equilibrium, time_slice[0]/profiles_1d/
  psi, FLT_1D)>` then the numbers -- 1543 characters for 101 values. And the
  widget's constructor set `np.set_printoptions(threshold=sys.maxsize)` for the
  whole process, never undone: measured, the threshold went from 1000 to
  9223372036854775807 and stayed there, and printing a million floats answered
  12,166,667 characters in 75.08 s where the default answers 78 characters in
  0.02 s.

So the values are formatted here, bounded, and the process-wide printing options
are left alone. When the values cannot be read at all, that is what the panel
says, with the reason -- rather than keeping, as the old one did, the previous
node's name and numbers on screen while every field it had shown was hidden.
"""

import numpy as np

from imasviz.VizUtils import QVizGlobalOperations

# Values shown at each end of an array longer than twice this. The old widget
# used the same 200 but still formatted the whole array first, which is where the
# 75 seconds went.
PREVIEW = 200

# The types whose entries are numbers: `np.isnan` refuses the others, and the old
# widget answered the first letters of the alphabet for them.
NUMERIC_KINDS = 'iufc'


class QVizNodeFacts:
    """The node's name, documentation and values, as rows for the panel.

    A node is asked for its values once. Whether it has any comes from the
    dictionary through `isIDSRoot` and `getDataType`, not from a guess: a
    structure or an array of structures holds no values of its own, an IDS root
    holds none either, and everything else is read.
    """

    def __init__(self, node):
        self.name = _nameOf(node)
        self.documentation = node.getDocumentation() or ''
        self.status = _statusOf(node)
        self.size = None
        self.shape = None
        self.minimum = None
        self.maximum = None
        self.zeros = None
        self.nans = None
        self.infs = None
        self.preview = None
        self.value = None
        self.refusal = None
        self.units = node.getUnits() or ''

        if node.isIDSRoot() or _holdsNoValues(node):
            return
        self._read(node)

    def _read(self, node):
        """The node's values, or the reason they could not be had."""
        if node.is0D():
            # The walk left the scalar's text in the tree, and that text is what
            # the user checks. Reading through the runtime instead answers the
            # wrapper: measured, an unset `tf.ids_properties/provider` is an
            # empty STR_0D whose string is `<IDSString0D (IDS:tf,
            # ids_properties/provider, empty STR_0D)>`.
            self.value = _textOf(node)
            return
        expression = QVizGlobalOperations.makePythonPath(node.getPath())
        try:
            values = node.resolvePath(expression)
        except Exception as error:
            # Not swallowed, as the old widget swallowed the same failure: the
            # user clicked this node to learn what is in it, and "nothing" is
            # only an answer if it says why.
            self.refusal = '%s: %s' % (type(error).__name__, error)
            return
        if values is None:
            self.refusal = 'this node holds no value in the opened case.'
            return
        self._describe(values)

    def _describe(self, values):
        """Size, shape, counts and a bounded preview of an array."""
        array = np.asarray(values)
        if array.ndim <= 1:
            self.size = str(array.size)
        else:
            self.shape = str(array.shape)
            self.size = str(array.size)
        if array.dtype.kind not in NUMERIC_KINDS:
            self.preview = _preview(array)
            return
        finite = array[np.isfinite(array)]
        self.zeros = str(int(np.count_nonzero(array == 0)))
        self.nans = str(int(np.count_nonzero(np.isnan(array))))
        self.infs = str(int(np.count_nonzero(np.isinf(array))))
        if finite.size:
            self.minimum = repr(float(finite.min()))
            self.maximum = repr(float(finite.max()))
        elif array.size:
            # Said rather than left out, because the two rows a reader came for
            # are the two that are missing.
            self.refusal = ('none of the %d entries is a number, so there is '
                            'no minimum and no maximum.' % array.size)
        self.preview = _preview(array)

    def rows(self):
        """The rows to draw, in the order the panel shows them.

        A row this node cannot answer is absent rather than left at `/`: the old
        panel pre-filled every row with that one character and showed it, so a
        two-dimension quantity -- for which it never computed a minimum -- read
        `Min: /` on the reference case.
        """
        rows = [('Node: ', self.name)]
        if self.documentation:
            rows.append(('Documentation: ', self.documentation))
        if self.status:
            rows.append(('Data dictionary status: ', self.status))
        if self.units:
            rows.append(('Units: ', self.units))
        if self.value is not None:
            rows.append(('Value: ', self.value))
        if self.shape is not None:
            rows.append(('Array shape: ', self.shape))
        if self.size is not None:
            rows.append(('Array size: ', self.size))
        if self.minimum is not None:
            rows.append(('Min: ', self.minimum))
        if self.maximum is not None:
            rows.append(('Max: ', self.maximum))
        if self.zeros is not None:
            rows.append(('Number of zeros: ', self.zeros))
        if self.nans is not None:
            rows.append(('Invalid entries (nan): ', self.nans))
        if self.infs is not None:
            rows.append(('Invalid entries (inf): ', self.infs))
        if self.preview is not None:
            rows.append(('Content: ', self.preview))
        if self.refusal:
            rows.append(('No values: ', self.refusal))
        return rows


def _nameOf(node):
    """The name the tree shows, the IMAS path when the dictionary gives one."""
    return node.getDataName() or node.getName() or ''


def _statusOf(node):
    """How the dictionary allows this node to be used: required, optional,
    experimental, alpha, obsolescent -- or nothing when it does not say."""
    data = node.getData()
    if isinstance(data, dict):
        return data.get('lifecycle_status')
    return None


def _holdsNoValues(node):
    """Whether the dictionary gives this node values to read at all.

    The old widget asked `isDynamicData()` and `isStaticData()` and fell through
    to a name-and-documentation display for everything else, which is what a
    structure needs -- but it reached that branch by falling off the end of the
    chain, so a leaf whose kind it did not recognise was shown as if it had no
    values.
    """
    return node.getDataType() in ('structure', 'struct_array')


def _textOf(node):
    """The value of a scalar, as the walk left it in the tree.

    The walk copies the runtime object itself when the case holds one and `None`
    when it holds nothing; its string is what the user checks, and `None` has to
    be said rather than printed.
    """
    data = node.getData()
    content = data.get('0D_content') if isinstance(data, dict) else None
    if content is None:
        return 'no value stored in the opened case'
    if content == '':
        return 'empty'
    return str(content)


def _preview(array):
    """At most PREVIEW values at each end, formatted without touching numpy's
    process-wide options."""
    flat = array.reshape(-1) if array.ndim > 1 else array
    if flat.size <= 2 * PREVIEW:
        return _format(flat)
    return '%s\n... %d of %d values not shown ...\n%s' % (
        _format(flat[:PREVIEW]), flat.size - 2 * PREVIEW, flat.size,
        _format(flat[-PREVIEW:]))


def _format(values):
    """A bounded, readable rendering of a slice of an array."""
    if values.size == 0:
        return '(empty)'
    return np.array2string(values, max_line_width=100, separator=', ')
