# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""No module of the package may ask numpy for a name a generation refuses.

The report was the Equilibrium plugin refused, its window never drawn, one line in
the log panel and nothing under it::

    Plugin equilibriumcharts failed: AttributeError: `np.unicode_` was removed in
    the NumPy 2.0 release. Use `np.str_` instead.

One statement, one line, in a plugin this tool has shipped for releases:

    imasviz/VizPlugins/viz_equi/equilibriumcharts.py:259
        unicode_type = np.dtype((np.unicode_, 12))

What makes that line hard rather than trivial is **where the suite runs**. Measured
on this node:

* the numpy of the module stack is **1.26.2** (``SciPy-bundle/2023.11-gfbf-2023b``)
  and it answers ``<U12>`` for both spellings -- under it the plugin is fine, so
  every test that ever drove it passed, including the one that runs it end to end on
  a real case;
* the numpy of ``~/.local`` is **2.4.6** and has **no ``unicode_``** at all -- the
  ``AttributeError`` above is that numpy's own removal shim. ``np.dtype((np.str_,
  12))`` answers ``<U12>`` under either.
* the suite cannot simply be moved onto the numpy 2 of this node to watch it fail:
  forcing ``~/.local`` first makes ``import imas`` die a level lower, in scipy --
  ``ValueError: numpy.dtype size changed, may indicate binary incompatibility.
  Expected 96 from C header, got 88 from PyObject`` -- because the Access Layer of
  this stack was compiled against numpy 1. The failure only shows on a node whose
  whole IMAS stack is built against numpy 2, which is where the user met it.

A test that asks only the installed numpy therefore cannot catch this: on the
generation the suite runs on, the name is there. The guard has to carry what the
*other* generation refuses -- and that list was measured, not copied, because
copying is how a guard ends up refusing code that runs. ``dir(numpy 1.26.2) -
dir(numpy 2.4.6)`` answers **102** names, and it is not a list to paste: beside the
aliases it holds lazily imported submodule names and private C plumbing. Two names
measured here show the two directions a list can get wrong:

* ``np.float_`` -- the canonical-looking spelling, and the shape of answer the numpy
  message itself gives for ``unicode_`` -- is **gone** in 2.4 while the suite's
  numpy answers it. That is the trap this file guards.
* ``np.bool`` goes the other way. Removed in 1.24 with the built-in aliases -- the
  suite's 1.26.2 refuses it, with a ``FutureWarning`` -- NumPy 2 **redefines it** as
  the scalar type. A list written from the 1.24 release notes would refuse a name
  that works over there, while the assertion that catches it over here is the plain
  one: ask the numpy that is loaded.

So the table is one-directional by construction: names this numpy answers and the
other refuses, measured between 1.26.2 and 2.4.6, kept to the family application
code reaches for (dtype aliases, the inf/nan constants, the old reductions, the
scalar-type helpers). It is not the whole 102. And what it promises is held to: an
entry recommends a spelling, and every recommendation that names a numpy attribute
or an ndarray method is checked on **both** generations, because advice pointing at
a second wrong name is how a refusal stops being a fix. Where no single name answers
both (``trapz``) the entry says so rather than naming one.

The far generation is read in a subprocess -- this node has both, and a node with
one has nothing to check against, so those tests say so and skip.
"""

import ast
import json
import os
import subprocess
import sys
import warnings

import numpy
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE_ROOT = os.path.join(REPO_ROOT, 'imasviz')

# Names the numpy of this stack answers and a NumPy 2 refuses, measured here
# between 1.26.2 and 2.4.6, kept to what application code asks for. The value is
# what to write instead: a bare name -- of the numpy module or of an ndarray --
# when one answers both generations, which the test below checks on both; a
# sentence where none does.
REMOVED_IN_NUMPY_2 = {
    # dtype aliases. The built-in spellings (`np.float`, `np.int`, `np.str`,
    # `np.bytes`, `np.object`, `np.complex`, `np.unicode`) went in NumPy 1.24 and
    # are refused on **both** sides of the pair measured here -- 1.26.2 refuses
    # them too, with a FutureWarning -- so the plain assertion on the loaded numpy
    # catches them wherever a suite runs and they are not listed. What is listed is
    # what this side answers and the far one refuses.
    'unicode_': 'str_',
    'string_': 'bytes_',
    'float_': 'float64',
    'complex_': 'complex128',
    'longfloat': 'longdouble',
    'clongfloat': 'clongdouble',
    'singlecomplex': 'complex64',
    'longcomplex': 'clongdouble',
    'cfloat': 'complex128',
    'int0': 'int_',
    'uint0': 'uint',
    'bool8': 'bool_',
    'object0': 'object_',
    'void0': 'void',
    # the inf/nan constants
    'NaN': 'nan',
    'NAN': 'nan',
    'Inf': 'inf',
    'Infinity': 'inf',
    'infty': 'inf',
    'PINF': 'inf',
    'NINF': 'the negated inf, which has no name of its own',
    'PZERO': '0.0',
    'NZERO': '-0.0',
    # reductions and array helpers
    'alltrue': 'all',
    'sometrue': 'any',
    'product': 'prod',
    'cumproduct': 'cumprod',
    'round_': 'round',
    'in1d': 'isin',
    'trapz': 'trapezoid, which only exists from NumPy 2: no single name answers '
            'both generations',
    'msort': 'sort along the first axis',
    'asfarray': 'asarray with a float dtype',
    'mat': 'a 2-D array, or numpy.matrix',
    # scalar-type introspection, retired with the promotion rules
    'find_common_type': 'promote_types',
    'issubsctype': 'issubdtype',
    'issctype': 'issubdtype',
    'maximum_sctype': 'the widest dtype of the family',
    'obj2sctype': 'the scalar type of the value',
    'sctype2char': 'the dtype char',
    'sctypes': 'the dtype families spelled out',
    'cast': 'astype',
    'chararray': 'a bytes or str array',
    'format_parser': 'numpy.format_float_positional',
    'compare_chararrays': 'a comparison over the array',
    'numarray': 'the numpy namespace itself',
    'oldnumeric': 'the numpy namespace itself',
    # plumbing that went with Python 2
    'set_string_function': 'set_printoptions',
    'safe_eval': 'ast.literal_eval',
    'recfromcsv': 'genfromtxt',
    'recfromtxt': 'genfromtxt',
    'deprecate': 'warnings.warn',
    'deprecate_with_doc': 'warnings.warn',
    'disp': 'the built-in print',
    'lookfor': 'the documentation search',
    'who': 'the documentation search',
    'compat': 'the standard library',
    'byte_bounds': 'the buffer protocol',
    'get_array_wrap': 'the ndarray subclass machinery',
    'DataSource': 'pathlib, or the standard library',
    'RankWarning': 'numpy.exceptions.RankWarning, which moved',
    'geterrobj': 'errstate',
    'seterrobj': 'errstate',
    'fastCopyAndTranspose': 'copy, then transpose',
    'set_numeric_ops': 'no replacement',
    'issubclass_': 'the built-in issubclass',
    'source': 'inspect.getsource',
}


def userSiteFolder():
    return os.path.join(os.path.expanduser('~'), '.local', 'lib',
                        'python%d.%d' % sys.version_info[:2], 'site-packages')


def otherGenerationNumpy():
    """``(version, moduleNames, ndarrayNames)`` for a second numpy, or None.

    Read in a subprocess: importing a second numpy inside the process running the
    suite would replace the one under test, and on this node it would take ``imas``
    down with it -- the ABI error the docstring records. The ndarray names come
    along because a recommendation can be a method, and a method is not in
    ``dir(numpy)``.
    """
    if hasattr(otherGenerationNumpy, '_cache'):
        return otherGenerationNumpy._cache
    found = None
    site = userSiteFolder()
    if os.path.isdir(site):
        code = ('import json, sys; sys.path.insert(0, %r); import numpy;'
                ' print(json.dumps([numpy.__version__,'
                ' sorted(n for n in dir(numpy) if not n.startswith("_")),'
                ' sorted(dir(numpy.ndarray))]))' % site)
        try:
            done = subprocess.run([sys.executable, '-c', code],
                                  capture_output=True, text=True, timeout=180)
        except Exception:
            done = None
        if done and done.returncode == 0:
            try:
                version, moduleNames, arrayNames = json.loads(
                    done.stdout.strip().splitlines()[-1])
            except Exception:
                version = None
            if version and version != numpy.__version__:
                found = (version, set(moduleNames), set(arrayNames))
    otherGenerationNumpy._cache = found
    return found


OTHER = otherGenerationNumpy()
needs_two_generations = pytest.mark.skipif(
    OTHER is None,
    reason='this node has a single numpy generation to check the list against')
needs_numpy1 = pytest.mark.skipif(
    numpy.__version__.split('.')[0] != '1',
    reason='the table lists what a NumPy 1 answers; this suite runs on %s'
           % numpy.__version__)


def numpyAnswers(name, module=None):
    """``hasattr`` with the going-out-of-use notice kept out of the run.

    Half the names in the table are deprecated aliases even where they still answer
    -- `np.uint0`, `np.bool8`, `np.void0` warn on 1.26 -- and asking them the plain
    way leaves a DeprecationWarning in every run of this file for names no module of
    the package uses. The warning belongs to the probe, not to the suite, whose
    warning count is a signal people read.
    """
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        return hasattr(numpy if module is None else module, name)


def answersHere(name):
    """Does the numpy running this answer `name`, as a module attribute or a method?"""
    return numpyAnswers(name) or numpyAnswers(name, numpy.ndarray)


def answersThere(name):
    """The same question of the other generation, when this node has one."""
    _version, moduleNames, arrayNames = OTHER
    return name in moduleNames or name in arrayNames


def pythonSources():
    """Every .py of the package, demos and standalone runners included.

    Wider than the import sweep on purpose: a demo that asks a dead name is the
    same dead name, and it is run by hand by whoever writes the next plugin.
    """
    found = []
    for dirPath, _dirNames, fileNames in os.walk(PACKAGE_ROOT):
        for fileName in sorted(fileNames):
            if fileName.endswith('.py'):
                found.append(os.path.join(dirPath, fileName))
    return sorted(found)


def numpyNamesAskedBy(source, label='<source>'):
    """``{(name, lineno)}`` for every numpy attribute `source` looks up.

    Follows the alias the file gives numpy -- ``import numpy``, ``import numpy as
    np``, and the names a ``from numpy import ...`` binds -- so a module calling its
    import ``numeric`` is scanned like any other.
    """
    tree = ast.parse(source, label)
    aliases, imported = set(), {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == 'numpy':
                    aliases.add(alias.asname or 'numpy')
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split('.')[0] == 'numpy':
                for alias in node.names:
                    imported[alias.asname or alias.name] = alias.name
    asked = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id in aliases:
                asked.add((node.attr, node.lineno))
        elif isinstance(node, ast.Name) and node.id in imported:
            asked.add((imported[node.id], node.lineno))
    return asked


def askedAcrossThePackage():
    """``{(name, [where, ...])}`` over every source of the package."""
    asked = {}
    for path in pythonSources():
        with open(path, encoding='utf-8') as handle:
            source = handle.read()
        try:
            names = numpyNamesAskedBy(source, path)
        except SyntaxError as error:
            pytest.fail('%s does not parse: %s' % (path, error))
        for name, lineno in names:
            asked.setdefault(name, []).append(
                '%s:%d' % (os.path.relpath(path, REPO_ROOT), lineno))
    return {name: sorted(where) for name, where in asked.items()}


ASKED = askedAcrossThePackage()


def recommendedNames():
    """The recommendations that name one thing, so both generations can be judged.

    The rest of the column is a sentence ('the built-in print', '0.0', 'no
    replacement'), which is what the entry says when no bare name answers both.
    """
    return sorted(value for value in REMOVED_IN_NUMPY_2.values()
                  if value.isidentifier())


def test_the_walk_finds_the_names_the_package_actually_asks():
    """An empty scan would pass every other test in this file.

    Measured: 26 distinct numpy names across the package.
    """
    assert len(ASKED) > 20, sorted(ASKED)
    for name in ('zeros', 'array', 'linspace', 'dtype'):
        assert name in ASKED, name


def test_every_numpy_name_the_package_asks_exists_on_the_numpy_running_this():
    """The numpy in charge answers every name the package looks up.

    This assertion needs no table. It catches a typo and it catches a removal --
    but only on the generation the suite happens to run on, which is why it is not
    enough on its own. It is also the assertion that catches the name going the
    other way, ``np.bool``, which a NumPy 2 answers and this one refuses.
    """
    missing = sorted(name for name in ASKED if not numpyAnswers(name))
    assert not missing, 'numpy %s has no %s, asked by %s' % (
        numpy.__version__, ', '.join(missing),
        '; '.join('%s -> %s' % (name, ASKED[name]) for name in missing))


@needs_numpy1
def test_the_table_lists_names_this_generation_answers_in_full():
    """Every entry is a name the suite's numpy answers -- so no test here can see it.

    That is the definition of the trap this file exists for, and it is what keeps
    the table from drifting into a list of names that are simply wrong, which the
    test above already covers.
    """
    invisible = sorted(name for name in REMOVED_IN_NUMPY_2
                       if not numpyAnswers(name))
    assert not invisible, ('numpy %s refuses %s already: those are not the '
                           'far-side trap this table lists'
                           % (numpy.__version__, ', '.join(invisible)))


def test_no_module_asks_a_name_numpy_2_refuses():
    """The guard the suite's own numpy cannot give.

    The reference case, the plugins and every plot of the tool run on the numpy of
    the module stack; a name the other generation refused stays invisible here until
    someone on a numpy 2 stack opens the menu and gets a log line where a window
    should be.
    """
    offenders = sorted(name for name in ASKED if name in REMOVED_IN_NUMPY_2)
    assert not offenders, 'asked by %s; write %s' % (
        '; '.join('%s (%s)' % (name, ', '.join(ASKED[name]))
                  for name in offenders),
        ', '.join('%s -> %s' % (name, REMOVED_IN_NUMPY_2[name])
                  for name in offenders))


def test_a_dead_name_is_refused_naming_the_file_the_line_and_the_fix():
    """The guard answers, on a source written for it.

    Without this, a scan that silently finds nothing -- a broken alias rule, a
    package that moved -- would keep the tests above green forever.
    """
    snippet = ('import numpy as np\n'
               'label = np.array([None] * 3, dtype=np.dtype((np.unicode_, 12)))\n')
    asked = {name for name, _line in numpyNamesAskedBy(snippet, 'snippet.py')}
    assert 'unicode_' in asked, sorted(asked)
    dead = {name for name in asked if name in REMOVED_IN_NUMPY_2}
    assert dead == {'unicode_'}, sorted(dead)
    # and the refusal has somewhere to send the reader
    assert REMOVED_IN_NUMPY_2['unicode_'].isidentifier()


@pytest.mark.parametrize('spelling', ['np.unicode_', 'np.float_', 'np.trapz',
                                      'np.NaN', 'np.string_', 'np.mat'])
def test_a_name_that_reads_as_plain_numpy_is_in_the_list(spelling):
    """None of these is exotic, and every one of them is refused on the other side."""
    name = spelling.split('.')[1]
    assert name in REMOVED_IN_NUMPY_2, spelling
    assert name not in ASKED, spelling


def test_a_name_that_changed_sides_is_not_in_the_list():
    """``np.bool`` is the trap the other way, and it is not this table's business.

    Removed in 1.24 with the built-in aliases -- measured refused by the 1.26.2 the
    suite runs on -- NumPy 2 redefines it as the scalar type, measured answered by
    2.4.6. A list copied from the 1.24 release notes would refuse code that runs
    over there, and the first false refusal is the one that gets a guard switched
    off. What catches it on *this* side is the plain assertion on the loaded numpy.
    """
    assert 'bool' not in REMOVED_IN_NUMPY_2
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        refusedHere = not hasattr(numpy, 'bool')
    if refusedHere:
        # The 1.24 removal, announced rather than raised. Asking it quietly would
        # leave a FutureWarning in every run of this file for a name no module of
        # the package uses.
        assert any('np.bool' in str(one.message) for one in caught), caught
        # A NumPy 1 that already refused it: the far side is what it comes back to.
        if OTHER is not None:
            assert answersThere('bool'), (
                'the table stays one-directional only while NumPy 2 answers bool '
                'again -- check which side this node is on')


@needs_two_generations
def test_the_table_refuses_what_the_other_generation_actually_refuses():
    """Every entry of the table is gone from the other numpy, measured.

    This is what keeps the list honest instead of remembered: an entry the other
    generation answers would refuse code that runs, and an entry that has quietly
    come back belongs in the ground it came from.
    """
    version, moduleNames, _arrayNames = OTHER
    still_there = sorted(name for name in REMOVED_IN_NUMPY_2 if name in moduleNames)
    assert not still_there, 'numpy %s answers %s -- drop them from the table' % (
        version, ', '.join(still_there))


@needs_two_generations
def test_the_spellings_the_table_recommends_answer_on_both_generations():
    """Advice is checked where it is given, on both sides.

    ``trapz`` is why this test exists: its replacement, ``trapezoid``, only exists
    from NumPy 2, so naming it would trade a refusal for a refusal. That entry says
    there is no single name instead of pointing at one. ``cast`` is why methods count
    too: ``astype`` answers on the array, never on the module.
    """
    version = OTHER[0]
    missing = [value for value in recommendedNames()
               if not answersHere(value) or not answersThere(value)]
    assert not missing, ('the table recommends %s, which one of numpy %s and numpy '
                         '%s does not answer'
                         % (', '.join(missing), numpy.__version__, version))


@needs_two_generations
def test_the_two_generations_the_docstring_measures_are_the_ones_on_this_node():
    """The docstring quotes 1.26.2 and 2.4.6 across two majors.

    Nothing breaks when a stack moves -- the measurements simply stop being the ones
    taken -- and this says so at the moment they stop, rather than leaving a table
    that was verified against a pair nobody has any more.
    """
    version = OTHER[0]
    assert numpy.__version__.split('.')[0] in ('1', '2'), numpy.__version__
    assert version.split('.')[0] != numpy.__version__.split('.')[0], (
        'the second numpy on this node is generation %s and the suite runs on %s: '
        'the table was measured across 1.x and 2.x'
        % (version.split('.')[0], numpy.__version__.split('.')[0]))
