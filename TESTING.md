# Running the IMASViz test suite

The suite lives in `tests/` (outside the `imasviz/` package) and runs on
**pytest + pytest-qt**. It needs the same environment as the application, plus
three test-only packages. Everything is driven offscreen: no X display is needed.

## 1. Prerequisites

### Python packages

| Package | Purpose | Verified version |
| --- | --- | --- |
| `pytest` | runner | 7.4.3 |
| `pytest-qt` | drives Qt widgets (`qtbot`, the `qapp` fixture) | 4.5.0 |
| `pytest-cov` | coverage report (optional) | installed |
| `pytest-timeout` | kills a hung test | installed |
| `PySide6` | the binding the sources import | 6.6.2 |
| `pyqtgraph` | plotting | 0.13.7 |
| `imas` (IMAS Python HLI) | data access | 2.3.0 |

### Environment modules

`module load ach-modules` pulls in `UDA/2.9.0-GCC-13.2.0` and
`IMAS-AL-Core/5.5.1-foss-2023b` automatically. Those two conflict with the
`IMAS-Core/5.7.1` stack, so they must be unloaded **before** it can load,
otherwise `import imas` fails with `ModuleNotFoundError`:

```bash
module load ach-modules
module unload IMAS-AL-Core
module unload UDA
module load IMAS-Core/5.7.1-foss-2023b
module load IMAS-Python/2.3.0-foss-2023b
module load PySide6/6.6.2-GCCcore-13.2.0
module load PyQtGraph/0.13.7-foss-2023b
```

`module` is a shell function: never pipe a `module load` into another command,
the subshell loses `MODULEPATH`.

Do **not** set `PYTHONPATH=$VIZ_HOME`. That replaces the `PYTHONPATH` exported by
the modules and `import PySide6` / `import imas` then fail. `tests/conftest.py`
puts the repository root on `sys.path` instead.

### Data and resources

The suite reads two resources. Both are overridable from the shell, and the
tests that need them are skipped when they are absent.

| Variable | Default | What it is |
| --- | --- | --- |
| `IMASVIZ_TEST_DD_DIR` | `/afs/eufus.eu/g2itmdev/user/g2lfleur/viz/imas_data_dictionaries` | directory holding `IDSDef_<IMAS_VERSION>.xml` |
| `IMASVIZ_TEST_URI` | `imas:hdf5?path=/afs/eufus.eu/g2itmdev/user/g2lfleur/public/imasdb/west/3/54924/0` | reference case, opened through the Access Layer URI form |
| `IMASVIZ_TEST_IMAS_VERSION` | `3.23.3` | data dictionary version the harness runs against |
| `IMASVIZ_TEST_CASE_DD_VERSION` | `3.35.0` | data dictionary the reference case was written with |

Everything else the application needs (`VIZ_HOME`, `VIZ_PRODUCTION`,
`TS_MAPPINGS_DIR`, `UDA_DISABLED`, `QT_QPA_PLATFORM=offscreen`) is set by
`tests/conftest.py`; you do not have to export it.

## 2. Running

```bash
cd $VIZ_HOME                      # repository root
python3 -m pytest tests/ -q       # 659 passed, 7 xfailed, ~34 s
```

Useful variants:

```bash
python3 -m pytest tests/ -m 'not case'      # skip the real-case integration
python3 -m pytest tests/ -m ui -v           # only the widget tests
python3 -m pytest tests/ --cov=imasviz --cov-report=term-missing
python3 -m pytest tests/test_34_one_image.py -v
```

Markers declared in `pytest.ini`: `ui` (Qt widgets), `dd` (needs the data
dictionary), `case` (needs the reference case). `timeout = 180` caps every test,
which matters because several application code paths can block on a modal
dialog or a remote backend.

## 3. What the suite covers

| File | Component | Notes |
| --- | --- | --- |
| `test_00_configuration.py` | `VizUtils` environment contract | `checkEnvSettings()` exits the process instead of raising, so a broken harness shows up here |
| `test_01_entities.py` | `VizEntities` array handles | one-based coordinates, time coordinate, no-copy values |
| `test_02_data_source.py` | `VizDataSource` | AL major version, URI/DBEntry lifecycle |
| `test_03_case_integration.py` | real WEST case | occurrences, filled paths, cross-DD-version reading |
| `test_04_view_parser.py` | `VizDataAccess` view parser | dictionary reflection; pins the shadow-tree node counts measured on the parsers it replaced |
| `test_11_layout_and_table.py` | layout widget, IDS table model | locks the Qt6 migration (`QVariant` is gone) |
| `test_12_plot_labels.py` | legends, axis labels, units, title | case label instead of the URI; labels set per curve |
| `test_13_plot_axes.py` | `QVizPlotWidget` axes | `xunits`/`yunits` reach the axis labels |
| `test_14_coordinate_units.py` | coordinate units → X axis label | the unit of the coordinate an array is indexed by |
| `test_15_node_coordinates.py` | `QVizTreeNode` coordinates | which coordinate a node records when asked to change one |
| `test_16_db_entry_registry.py` | IMAS entry registry | one entry per URI, references counted |
| `test_17_axes_spec.py` | `QVizAxesSpec` | the axes a leaf has to be plotted along; unbounded `1..N` spelling |
| `test_18_case_readings.py` | reference case, through the axes model | readings frozen as numbers: 17 344 samples, 49 slices, 1 642 × 101 grid |
| `test_19_time_coordinate_rule.py` | `homogeneous_time` | where a time coordinate gets its values |
| `test_20_plugins.py` | `VizPlugins` framework | registration table, `VizPlugin` contract |
| `test_20_tensor_data_access.py` | the IMAS reader and the factory | one reader for both IMAS sources; the (arrays, handle) contract |
| `test_21_slice_sliders.py` | the axes a plot does not draw | each one fixed in front of the user, not silently |
| `test_22_slice_controls.py` | `QVizSliceControls` | controls driven from the axes model rather than a flag |
| `test_23_scalar_content_and_lifecycle.py` | shot view, scalars | a scalar's value, and `lifecycle_status` |
| `test_24_curve_plot.py` | `QVizCurvePlot` end to end | a rank 3 quantity becomes a curve whose slices move; a scalar spread along the drawn axis |
| `test_25_plot_as_slices.py` | `QVizPlotAsSlices` | selection to figure through the tensor read |
| `test_26_image_plot.py` | `QVizImagePlot` end to end | pictures read along one axis, a window on it, one colour scale |
| `test_27_plot_routing.py` | routing a selection | a curve draws one axis, an image two; refusal names the quantity |
| `test_28_radiance_case.py` | WEST 55799 | a rank 3 quantity a real shot holds values for (`hard_x_rays`) |
| `test_29_inherited_coordinates.py` | parser, inherited coordinates | the coordinates a structure declares, carried down to its arrays |
| `test_30_figure_registry.py` | the frame registry and the menus built from it | show/hide, delete, and the key a closed window has to lose |
| `test_31_node_plotting.py` | `QVizNodePlotting`, on real tree nodes | which entries the context menu offers, decided on the axes the read would walk |
| `test_32_preview.py` | the left-click preview panel | what the thumbnail draws, and what it says when it draws nothing |
| `test_33_plot_one_node.py` | the entries that plot one node | which frame the quantity lands in; the node under the menu is the node drawn |
| `test_34_one_image.py` | the image window, from the tree entry to its slices | the entry names the frame the quantity needs; the ROI lines stand in coordinates, the slice follows the window, kept slices stay; no case |
| `test_35_selection_entries.py` | the entries that draw a selection | the two menu entries as they fire (`plotSelectedSignals`, `addSelectedSignalsPlotToFig`): which frame each quantity lands in, that a refusal costs no window and names the path, one 'Figure' entry listing the open curve figures; no case |
| `test_36_table_plot_entries.py` | the four `TablePlotView` entries | the four menu entries as they fire (`New (default axis)` / `New ('TIME' axis)` x This/All): the two strategies read along different axes, one panel per quantity with its own abscissa and named slices, a two-axis quantity refused by name, the `(row, column)` keys and the key released at close, a `.pcfg` drawing its paths while refusing its styling; no case |
| `test_37_stacked_entries.py` | the four `StackedPlotView` entries | the four menu entries as they fire, plus one action triggered from the menu: the submenu is still alive after the call that built it, the two strategies read along different axes, every panel shares the ranges of the first (links asked of the view boxes), the two checkboxes change what they say, a quantity read along another abscissa is refused by name and leaves no panel, the first quantity read fixes the abscissa, one-column keys, the key released at close; no case |
| `test_38_selection_entries.py` | selecting and unselecting nodes | the node menu as the click fires it (`selectOrUnselectSignal`, the label the menu offers, `selectAllSignalsFromSameAOS`, `onUnselectSignals` This/All): one record for the selection, the entry holding the node it was asked for, the label recoloured where it was asked, the AOS family kept inside the clicked occurrence, "Unselect All" surviving a node the tree dropped; no case |
| `test_39_configurations.py` | the configuration file and the commands that save and apply it | one module owns the format: read by its root element rather than its extension, the two shapes the old writers produced still read (and their styling counted), a name that names a place refused, the button that used to write no file now naming every panel and the place each sits in, the abscissa the window was drawn with applied back, a selection saved from one view selecting the same nodes in another, `Viz_API.SelectSignals` taking the plain list of paths `scripting.rst` shows; `HOME` redirected into `tmp_path`, because the suite does not isolate `$HOME`; no case |
| `test_40_export_to_ids.py` | "Export to IDS": the case it writes and the IDSs it writes | the URI spelled once, in the data layer, and read back by the same layer (`_readCaseFromUri(caseUri(…))`); the two versions the format needs — `version=3` in the URI while the entry is built at `3.35.0` (`dd_version='3'` answers `UnknownDDVersion`); a field left empty or holding a separator named instead of sent to the Access Layer, including the `/` the old dialog prefilled; the shot box refusing letters where `int()` used to answer from the OK button; a run of 0 kept distinct from a run left blank; the backend as a choice, not as `13`; the entry never asked to `open()` a second time and closed even when a `put` fails; one refused IDS named while the others are written, counted as `2 of 3 IDS(s) written`; and one round trip on the reference case — a real `pulse_schedule` written into a `path=` case under `tmp_path` and found again at occurrence 0. No invented database name: an URI naming a database that does not exist *creates* one under the login's `~/public/imasdb`. The Access Layer stands in for everything but that round trip, so `ui`/`case` mark the two kinds of real thing it drives |
| `test_41_node_documentation.py` | the panel a left click answers with | what the reference case measured the old widget answering wrong, pinned one row at a time: the zero count (0, 3 and 49 where it answered 1, 1 and 1), `Min`/`Max` taken on the entries that are numbers with the `nan`/`inf` counts beside them, a string array given no `Min`, no `Max` and no zero count, a `Content:` row holding the numbers and never `IDSNumericArray`, a preview saying `600 of 1000 values not shown`, no row ending `: /`, a failed read naming its exception with nothing of the previous node left on screen, a scalar shown as its value or as `empty` or as `no value stored in the opened case`, and `panel.update()` still the no-argument method of `QWidget`. Six tests run on real nodes, asked by the path the shot view spells (`shadowTreePaths`, because `element.text` spells the same road with dots and brackets and evaluates against the runtime as something else). numpy's printing options are asserted untouched before and after |
| `test_42_load_an_occurrence.py` | loading one occurrence: double click, Return, "Get … data for occurrence", "Add a new view" | the four slice choices as objects, not as the integers 1-4: the window each keeps out of 49 slices, `First time slice only` on an empty array keeping nothing (the old one invented 11 nodes of 77 on `tf`), an index past the end refused before the walk with the count and the bound in the sentence, the menu choice that still needs a number refusing rather than opening a dialog in the middle of a script; the case answering which occurrences it holds (`[0,1,2,3]` for `equilibrium`, `[]` for `core_sources`) where the data dictionary question raised `AttributeError` at 5 places and killed the shot view; the guard against a double load living on the view, so two views load the same occurrence and one never loads it twice; both sub-menus built from what the case and the view answer, and the slice question recorded through a stub dialog — parented to the view, bounded at 48 when 49 slices are in memory; the walk asking the choice for its window, recording the dynamic arrays it met, and refusing an index under the name of the array that cannot take it. Six tests drive a real shot view of the reference case — 55 IDS roots built, an occurrence labelled `occurrence 0 [displaying first time slice]` and marked dynamic, `homogeneous_time` read off the loaded instance, the double click delivered through the event loop with the walk held alive until it finishes — and three check the deletion itself: `find_spec` answering None for the three modules that used to do this work |
| `test_99_import_sweep.py` | every module of the package | walks the tree and imports each module |

The import sweep is the broad one: it fails when a Qt-binding change breaks an
import anywhere in the package.

## 4. The 7 expected failures

They are `xfail(strict=True)`, so they surface as `XFAIL` while still failing
the run once fixed — a fix must remove the marker.

- 5 modules that cannot import: the Qt Designer scaffolding
  (`viz_example/exampleplugin`, `viz_solps/SOLPSplugin`,
  `viz_solps/src/getIDSplugin`, `viz_solps/SOLPSwidget`,
  `viz_solps/src/GGDDialog`). `QPyDesignerCustomWidgetPlugin` does not exist in
  PySide6 6.6, and the `viz_solps/src` subtree imports its siblings as
  `src.<mod>`. None of them is registered in `RegisteredPlugins`, so none is on
  a code path.
- `list_filled_paths` raises `packaging InvalidVersion: "+1"` when the harness
  dictionary (3.23.3) is loaded against a case written with DD 3.35.0.
- `VizPlugin.getAllEntries` is declared twice in the class: the instance stub
  raising `ValueError` (`VizPlugin.py:52`) is shadowed by the static lookup
  table (`VizPlugin.py:130`), so the base-class contract method is unreachable.

## 5. Reading a case across data-dictionary versions

The reference case is stored with DD 3.35.0 while the Access Layer loads its own
default (4.1.1). IMAS-Python refuses to read an IDS across a DD major version,
so:

```python
entry = imas.DBEntry(uri, 'r')                          # lists occurrences, paths
entry = imas.DBEntry(uri, 'r', dd_version='3.35.0')     # actually reads IDSs
```

The URI cannot carry the pin (`path=…;dd_version=…` is ignored), and
`QVizIMASDataSource.createDBEntry()` does not pass that keyword, so the
application itself cannot read this case on an AL5 stack until it forwards a DD
version. The suite documents this in `test_03_case_integration.py`.

## 6. What the reflection walk costs

Measured on the reference case (WEST 54924, DD 3.35.0), both arms on the same
data source with the same GGD setting, so the node counts are comparable. The
emitted arm runs the parsers still on disk under `~/.imasviz/VizGeneratedCode`
(494 885 lines for the GGD-pruned one, 634 001 for the full one). The generator
left the repository in `01d6f8d`, so only already-generated code can be timed:
its one-off generation cost is not included, which favours that arm.

| IDS, GGD ignored | nodes | reflection walk | emitted walk |
| --- | --- | --- | --- |
| `tf` | 77 | 0.001 s | 0.002 s |
| `magnetics` | 18 142 | 0.052 s | 0.031 s |
| `interferometer` | 2 053 | 0.006 s | 0.002 s |
| `pulse_schedule` | 7 196 | 0.020 s | 0.007 s |
| `equilibrium` | 7 203 | 0.038 s | 0.152 s |
| `equilibrium`, GGD kept | 408 043 | 2.45 s | 1.62 s |

Two things those numbers say:

- **Reading the IDS costs more than walking it.** `equilibrium` occurrence 0
  takes 4.1 s in `db_entry.get` against 0.038 s to build its 7 203 shadow-tree
  nodes. Importing the generated module costs 0.13 s with a cached `.pyc`.
- **The reflection tree is bigger.** It carries `path_doc`,
  `coordinateN_same_as` and `coordinateN_units`: 92.6 MB of text and attributes
  against 59.1 MB for the same 408 043-node GGD tree. That is the deliberate
  price of the attributes the plot labels now read.

Coordinate spellings are resolved through the dictionary once per IDS walk
(`QVizIDSViewParser.coordinateMetaData`), which took the descent count from
84 708 for 16 distinct spellings down to 16. That bought 8 % of the walk: the
descents were not the hotspot, building the elements is. The cache stays
because the work it removes grows with the node count, and
`test_04_view_parser.py` pins that count below 64 on the 7 203-node
`equilibrium` tree — a bound no machine timing could offer.

## 7. How many leaves are more than 2D

Rank here is the number of dimensions a plot would have to draw, not the data
dictionary `data_type`: **rank = enclosing arrays of structures + ndim of the
leaf**. The shadow tree already carries both (`buildLeaf` sets
`aos_parents_count`, and the walk only grows its level when it enters a
`struct_array`).

Counted over every IDS that holds data in the reference case — 26 at
occurrence 0, 24 walked:

| rank | leaves, GGD pruned |
| --- | --- |
| 0 | 1 747 |
| 1 | 83 371 |
| 2 | 69 697 |
| 3 | 34 819 |
| 4 | 1 843 |
| 5 | 6 |
| **total** | **191 483** |

**36 668 leaves — 19 % of the case — are rank 3 or larger.** The reader the
application used until now had no branch for that shape: it evaluated one Python
expression per time slice, left the static array's placeholder unsubstituted,
watched every slice fail to evaluate, and handed back two empty arrays — an empty
curve, with nothing said about why. Such a leaf is read whole along its axes now,
and a quantity with more to draw than a frame can hold is refused by name. Real
examples of each rank:

- rank 3: `calorimetry.group[i].component[j].power.data`
- rank 4: `core_profiles.profiles_1d[i].ion[j].state[k].z_average_1d`
- rank 5: `equilibrium.time_slice[i].coordinate_system.tensor_covariant`

With the GGD structures kept, `equilibrium` alone adds rank 5 (105 459 leaves)
and rank 6 (84 348): 189 913 of its leaves are rank 3 or larger, under five
nested arrays of structures (`grids_ggd[i].grid[j].space[k]
.objects_per_dimension[l].object[q]`). Any rank policy has to assume 8 axes,
not 6: the dictionary caps the leaf at 6D and the arrays of structures at 7
nested levels.

Two IDSs, `hard_x_rays` and `langmuir_probes`, do not walk at all: the AL
cannot open their `time` dataset (`al_plugin_read_data: Unable to open HDF5
dataset: time`), and the walk surfaces that as an `AttributeError`. That is a
pre-existing hole, not a new one, and whatever reads data on the new path has
to survive it rather than propagate it.

Walking 24 IDSs took 337.8 s, again dominated by `db_entry.get`: the rank
question is about what can be plotted, not about how long it takes.


