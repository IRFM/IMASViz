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
python3 -m pytest tests/ -q       # 165 passed, 8 xfailed, ~11 s
```

Useful variants:

```bash
python3 -m pytest tests/ -m 'not case'      # skip the real-case integration
python3 -m pytest tests/ -m ui -v           # only the widget tests
python3 -m pytest tests/ --cov=imasviz --cov-report=term-missing
python3 -m pytest tests/test_10_plot_image_widget.py -v
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
| `test_10_plot_image_widget.py` | image plot widget | synthetic array, no case and no data dictionary |
| `test_11_layout_and_table.py` | layout widget, IDS table model | locks the Qt6 migration (`QVariant` is gone) |
| `test_20_plugins.py` | `VizPlugins` framework | registration table, `VizPlugin` contract |
| `test_99_import_sweep.py` | every module of the package | walks the tree and imports each module |

The import sweep is the broad one: it fails when a Qt-binding change breaks an
import anywhere in the package.

## 4. The 8 expected failures

They are `xfail(strict=True)`, so they surface as `XFAIL` while still failing
the run once fixed — a fix must remove the marker.

- 5 modules that cannot import: the Qt Designer scaffolding
  (`viz_example/exampleplugin`, `viz_solps/SOLPSplugin`,
  `viz_solps/src/getIDSplugin`, `viz_solps/SOLPSwidget`,
  `viz_solps/src/GGDDialog`). `QPyDesignerCustomWidgetPlugin` does not exist in
  PySide6 6.6, and the `viz_solps/src` subtree imports its siblings as
  `src.<mod>`. None of them is registered in `RegisteredPlugins`, so none is on
  a code path.
- `QVizIMASDataSource.build_uri` raises `ImportError`: it does
  `from imas import _al_lowlevel as ll` (`QVizIMASDataSource.py:45`) and
  IMAS-Python 2.3.0 exposes no `_al_lowlevel`. Legacy URI building is therefore
  broken on an AL5 stack.
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

**36 668 leaves — 19 % of the case — are rank 3 or larger.** Today none of them
can be plotted: `QVizIMASNativeDataAccess.GetSignal` matches no branch and
returns `None` without a word. Real examples of each rank:

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


