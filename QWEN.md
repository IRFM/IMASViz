# QWEN.md — IMASViz

Context for AI agents working in this repository. Derived from reading the sources, the
`Makefile`s, the Sphinx docs and `git log`.

## Project overview

**IMASViz** is the graphical visualization front-end of **IMAS** (Integrated Modelling
Analysis Suite, IRFM/CEA). It browses and plots plasma-fusion data stored in IMAS **IDS**
(Int Interface Data Structures) held in IMAS databases (HDF5 / MDS+), either local or reached
remotely through **UDA**.

- Language: Python 3, GUI built on **Qt for Python (PySide6)**; plotting on **pyqtgraph**
  (plus matplotlib where used).
- 135 `.py` files, all inside the single package `imasviz/`.
- License: **CeCILL-C**, holders CEA (France) and LECAD / University of Ljubljana (Slovenia).
  Authors banner: `L. Fleury, X. Li, D. Penko`.
- Depends on the IMAS **Python HLI** — the `imas` module. **Corrected by
  measurement**: the stack this checkout runs on loads `IMAS-Python/2.3.0-foss-2023b`,
  i.e. the ITER **IMAS-Python** bindings (they export `DBEntry`, `IDSFactory`,
  `convert_ids`, `OLDEST_SUPPORTED_VERSION`), not the old generated-module HLI at
  `ssh://git@git.iter.org/imas/al-python.git`. What the sources were written
  against is the older surface, so the mismatch is real but points the other way:
  `hasattr(imas, 'equilibrium')` is **False** here, so the idiom the sources were
  written against — `eval("imas." + idsName + "().getMaxOccurrences()")` — raises
  `AttributeError` wherever it appears. Since T12 it appears in **one** place, the
  unregistered-path `viz_Profiles/VizProfiles_plugin.py`; the 5 places that stood on
  a tree gesture (the shot view's empty tree, `hasAvailableData`, the three
  `Viz_API` occurrence helpers) now ask the case through `DBEntry.list_all_occurrences`.
  Do not write new code against generated `imas.<ids>()` classes; they do not exist
  on this node.
- Documentation is a first-class artifact of the repo: Sphinx/RST under `doc/source`, built with
  `make doc`. The RST manual is the authoritative user guide — consult it before inventing
  behavior.

### Qt binding — corrected in this pass

`README` used to list **PyQt5** while no source imports it; the README now states **PySide6** and
documents the ACH module stack (`PySide6/6.6.2-GCCcore-13.2.0`,
`IMAS-Python/2.3.0-foss-2023b`, `PyQtGraph/0.13.7-foss-2023b`). All Qt references in the sources
are `PySide6`; legacy `PyQt5` mentions survive only inside comments. **PySide6 is the single
binding — there is no PyQt5 fallback shim.**

## Environment variables drive everything

The app has no CLI-installed configuration: `QVizGlobalValues.py` and `QVizGlobalOperations.py`
read/derive `os.environ` at import time. Importing `imasviz` without the environment set will
print warnings and take fallback paths.

| Variable | Meaning |
| --- | --- |
| `VIZ_HOME` | Repo root. Put on `sys.path`; used to locate `ts_mapping_files`, `config`, `resources/VizIcons`, plugin `.ui` dirs. |
| `VIZ_PRODUCTION` | `1` = production (installed modules). `0`/unset ⇒ `QVizGlobalValues.TESTING = True` (dev/testing mode). |
| `IMAS_VERSION` | e.g. `5.7.1`; `IMAS_MAJOR_VERSION` is derived as its first char. **The IMAS-Python module exports `AL_VERSION` (5.7.1) but not `IMAS_VERSION`** — `QVizGlobalValues` now copies `AL_VERSION` into `IMAS_VERSION` when only the former is set (consistent with the `UAL_VERSION → AL_VERSION` commit). |
| `IMAS_DATA_DICTIONARIES_DIR` | Defaults to `$VIZ_HOME/imas_data_dictionaries` **only when not already exported**, so a module/user-supplied path wins. That repo path is absent, so without an explicit export `getIDSDefFile` finds no `IDSDef_<ver>.xml`. |
| `TS_MAPPINGS_DIR` | Same "default only if unset" rule; `$VIZ_HOME/ts_mapping_files` does exist in the repo. |
| `UDA_DISABLED` | `1` disables UDA. Forced to `1` in TESTING mode. |
| `IMAS_VIZ_VERSION` | Displayed in window titles; warns if undefined. |
| `HOSTNAME`, `HOME`, `USER`, `WEST`, `DATABASE_NAME` | Used in testing-mode path resolution. |

Runtime state lives under **`$HOME/.imasviz/`**, not in the repo:
`preferences` and `*.pcfg` plot-configuration files
(`Viz_API.GetPlotConfigurationPath`). Never assume the repo-level
`config/preferences` is the file the app reads — it is not; `$HOME/.imasviz/preferences` is.
The former `VizGeneratedCode/` folder is gone: the data dictionary is walked at run time.

## Build / run / test commands

Always from the repo root with `VIZ_HOME` exported (`cd` into the checkout, not into a `viz`
directory — the README's `cd viz` predates the `imasviz/` rename):

```bash
export VIZ_PRODUCTION=1
export VIZ_HOME=$PWD
export UDA_DISABLED=1          # optional: no remote UDA servers
```

| Command | Effect |
| --- | --- |
| `make` | Default is now `all: doc` — builds docs only. The `default` target (submodule fetch) still exists for explicit `make default`, but no submodule is configured any more (see ETSViz note). |
| `make doc` / `make -C doc html` | Sphinx route (`cd doc && make html`). **Sphinx is not on the ACH module stack** — `sphinx-build: command not found` here until `pip3 install sphinx sphinx_rtd_theme` is done. `doc/build/` is gitignored. |
| `make clean` | Deletes `doc/build` only. It used to delete `$HOME/.imasviz/VizGeneratedCode` as well; that folder is gone with the reflection based parser. |
| `make -C doc html` / `-M latexpdf` | Direct Sphinx route; `doc/Makefile` adds a custom `latexpdf` rule copying `source/_static/*.mp4` next to the LaTeX output. |

Running the GUI requires the IMAS HLI, which is **not vendored here** — on this ACH/Gateway
stack it comes from environment modules (all four verified to load; PySide6 reports 6.6.3):

```bash
module load ach-modules
module load PySide6/6.6.2-GCCcore-13.2.0
module load IMAS-Python/2.3.0-foss-2023b      # provides imas, numpy, matplotlib, AL_VERSION
module load PyQtGraph/0.13.7-foss-2023b       # provides pyqtgraph

python $VIZ_HOME/imasviz/VizGUI/QtVIZ_GUI.py  # from sources, needs an X display
viz                                           # installed module (ITER HPC: module load Viz/2.3.7-...)
viz -u <user> -d <database> -s <shot> -r <run> -b <backend>   # backend 13 = HDF5, 12 = MDS+
```

`module` is a shell function: piping a `module load` into another command runs it in a subshell
and loses `MODULEPATH` — load it in the same shell as the consuming command.

Sphinx is **not** provided by that module stack (`sphinx-build: command not found`); `pip3 install
sphinx sphinx_rtd_theme` is still required for `make doc`.

There is a pytest suite (see Testing below), but **no CI config, linter config, or
packaging manifest** in this repo.

## Architecture map

```
imasviz/
├── Viz_API.py                 # Viz_API: scripting API + central session state
├── VizUtils/                  # global constants, prefs, logging, window geometry
├── VizDataSource/             # opens a case: URI building, DBEntry, Tore-Supra, factory,
│                              # QVizCaseOccurrences (which occurrences the case holds)
├── VizDataAccess/             # QVizIDSViewParser: walks the dictionary through imas reflection
│   └── VizTimeSlices/         #   how many elements of a dynamic AOS a view keeps
├── VizEntities/               # data-array handles
├── VizGUI/
│   ├── QtVIZ_GUI.py           # entry point: QVizMainWindow, MDI area, start window
│   ├── VizGUICommands/        # command objects (loading/selection/menus/opening/plotting)
│   ├── VizTreeView/           # the IDS tree view (shot view, "DTV")
│   ├── VizPlot/ + VizPlotFrames/  # plot widgets and frames
│   ├── VizWidgets/            # db browser, nodes-selection window, VizNodeDocumentation/
│   │                          # (QVizNodeFacts: what a node holds; the panel draws it)
│   ├── VizGuiCustomization/   # QVizDefault defaults
│   └── VizConfigurations/, VizExporters/
├── VizPlugins/                # plugin framework + plugins (see below)
└── VizExamples/               # example_*.py and test_*.py standalone scripts
```

Core concepts, in the vocabulary used by the code and docs:

- **DTV / shot view** — one `QVizDataTreeViewFrame` per opened case, tracked in
  `Viz_API.DTVframeList` / `DTVlist`.
- **figure frames** — `Viz_API.figureframes`, keyed by `FigureTypes` prefix + number
  (`SlicesPlot1`, `SlicesImage1`, `TablePlotView0`, `StackedPlotView0`, `ProfilesPlot…`; the
  legacy `Figure:` namespace still keys frames those old paths open, the legacy `Image:`
  one is gone with the frame that used it).
  Allocate keys through
  the `GetNextKeyFor*` accessors, never by hand.
- **commands** — everything user-facing is a `QViz*` object with an `.execute()` method
  (`QVizLoadOccurrence`, `QVizSelectNodes`, `QVizSelectFromConfiguration`,
  `QVizSaveNodeSelection`, `QVizSavePlotConfiguration`, `QVizPlotOneNode`,
  `QVizPlotAsSlices`, `QVizPlotAsTable`, `QVizPlotAsStacked`, `QVizExportToIDS`).
  `Viz_API` methods are
  thin wrappers that instantiate one of these and call `.execute()`. A command
  raises `ValueError` with the reason; the menu slot that fires it puts that
  reason in the log panel — no dialog lives inside a widget slot, and no gesture
  swallows a failure in a bare `except:`.
- **the selection** — one record only: `dataTreeView.selectedSignalsDict`, keyed by
  `dataSource.dataKey(node)` (name, uri, path, **occurrence**), holding the
  `QTreeWidgetItem` itself. The node carries no `isSelected` flag of its own, and
  neither the menu label nor the label colour reads one; both ask the dictionary.
  The AOS family is `getParametrizedDataPath()` (index *names*, e.g.
  `core.time_slice[i].a`) plus the occurrence — never a regular expression over the
  display path, which does not spell the occurrence.
- **configurations** — `VizConfigurations/QVizConfigurationFile.py` owns the file:
  an `<IMASVizConfiguration kind="plot|selection" version abscissa>` root with one
  `<Quantity path occurrence row column uri/>` each, under `$HOME/.imasviz`
  (`.pcfg`, `.lsp`). Reading dispatches on the **root element**, not the extension,
  and the two shapes the previous writers produced (`PlotConfiguration` with
  `GraphicsWindow/PlotItem/sourceInfo`, `SignalSelection` with `IDSPath`) are still
  read — their paths spelled with dots and brackets, converted by
  `QVizGlobalOperations.makeIMASPaths`, which is why that helper stays. Anything
  else is refused with a `ValueError` naming the root or the parse error; nothing
  about a configuration is raised out of a button or a menu slot. A file written
  now holds no styling, so the "styling is not applied" log line is only for the
  old ones (`styledPanels`).
- **MDI** — a `QMdiArea` under `QVizMainWindow` (root window `objectName() == "IMASViz root window"`);
  figures and shot views are `QMdiSubWindow`s inside it. Show/hide and delete logic branches on
  whether a frame is MDI-embedded — that string comparison is load-bearing.

Naming convention: Qt widget classes are prefixed `QViz` (`QVizPlotWidget`, `QVizLogger`);
plain API/framework classes are not (`Viz_API`, `VizPlugin`). `__init__.py` files re-export with
relative imports (`from .QVizLogger import QVizLogger`) and a `# __init__.py` first line, so
callers import as `from imasviz.VizUtils import QVizLogger`.

## Plugin system

`imasviz/VizPlugins/` is an extension mechanism, not dead code. To add a plugin:

1. Create `imasviz/VizPlugins/viz_<name>/PluginName.py` subclassing `VizPlugin` and implement:
   `isEnabled()` (return `True` to activate), `getEntries()` (the entry *numbers* this
   node earns), `getAllEntries()` (`[(number, menu_text), …]` — the text is looked up
   **by that number**, and a number it does not describe is refused by name),
   `execute(vizAPI, pluginEntry)` (receiving that same number), optional
   `getPluginsConfiguration()`, `getDescription()`. Gate on
   `self.selectedTreeNode.getIDSName()` against a `supported_idss` list — that is how
   plugins claim IDSs. Inheriting `VizPlugin` is not what puts a plugin in the menu: the
   catalog binds `setSelectedTreeNode(node)` and asks the methods, so a plugin outside
   the hierarchy that honours them is offered like any other.
2. Register the class in the `RegisteredPlugins` dict in `VizPlugins/VizPlugin.py`
   (`'PluginName': 'viz_<name>.PluginName'` — the class must bear the key's name, since
   that is what the catalog takes out of the module). Several entries are commented out —
   an unregistered plugin never loads, and a registered path that no longer resolves is
   refused in the log of the case without costing the other plugins. No submodule-provided
   plugin remains: the ETSViz submodule and `imasviz/VizPlugins/viz_ETS/` were removed on
   request, so `'ETSpluginIMASViz'` must stay commented out (an active entry would now
   raise `ModuleNotFoundError`).
3. `.ui`-based plugins register a **dictionary** in `RegisteredPlugins` instead of a
   module path — `UiFile`, `dir` (anchored on `os.environ['VIZ_HOME']`), `targetIDSroot`,
   `targetOccurrence` — and are loaded by `QVizPluginCatalog._loadUiPlugin` with
   `PySide6.QtUiTools.QUiLoader` (`from PySide6 import uic` does not exist in PySide6 6.6).
   Such a window claims one IDS, and its one menu entry is the window itself, which loads
   that IDS through `QVizLoadOccurrence`. Measured limit: a `.ui` drawn around a widget
   class of its own cannot be shown on this stack — Qt answers *"unable to create a custom
   widget of the class 'exampleWidget'; defaulting to base class 'QWidget'"* and drops the
   connections the file makes to it (10 in `examplePlugin.ui`), and overriding
   `createWidget` changes nothing because it is never called; such a plugin is refused by
   name, naming the class, so the repository's only `.ui` plugin stays unregistered.
   `viz_example/` ships a `run_plugin_ui_standalone.py` for off-GUI development of it.
   The SOLPS plugin (`viz_solps/`, 11 files and 1 451 lines, with its own `SOLPSwidget`
   class and a `.ui` that lost 3 connections the same way) was removed on request: it was
   never registered, and the manual's section that documented it is gone with it.

The menu side is two modules: `VizPlugins/QVizPluginCatalog.py` (the registered plugins of
one shot view, imported and built **once for that view**, each asked on its own, every
refusal named in the log of that case — reachable as `dataTreeView.pluginCatalog`) and
`VizGUI/VizGUICommands/VizMenusManagement/QVizPluginMenu.py` (the "Plugins" sub-menu the
three gestures share: right click on an IDS root, right click on a quantity, Shift+right
click anywhere; it answers how many lines it added, so an empty sub-menu is not left on
screen, and builds that sub-menu with its parent at construction — `addMenu(title)` hands
out a QMenu the Python wrapper owns, which then dies before it can be clicked).
`QVizPluginsHandler` and `QVizPluginsPopUpMenu` are gone, and so are the per-name lookup
tables `VizPlugin` used to carry: a plugin is asked itself, once per view.

`test_imas_viz_plugin.py` instantiates a plugin with a hardcoded `dictDataSource`
(shot 50642, `west_equinox`) and calls `execute()` directly — the pattern for exercising a
plugin without the full GUI. `tests/test_43_plugins_in_the_menu.py` drives the menu
instead, with stub plugins registered through a fake module in `sys.modules`.

## Development conventions

- **License header is mandatory and byte-exact.** Every `.py` file (and the RST files) begins with
  the 4-line CeCILL-C copyright block followed by the authors banner:

  ```python
  # ****************************************************
  #     Authors L. Fleury, X. Li, D. Penko
  # ****************************************************
  ```

  Any new source file must carry the identical header; `git log` shows it was applied repo-wide
  in one commit.
- **Commit messages**: plain capitalized imperatives, no Conventional-Commit prefixes —
  `Renaming UAL_VERSION to AL_VERSION`, `Adding license header to all source files`,
  `README: fixing requirments`. Match that style.
- **Branches**: `main` (current, `origin/HEAD`) and `origin/develop`. The README tells users to
  `git checkout develop`; verify the live branch with `git branch` before assuming which one a
  fix belongs on.
- `ts_mapping_files/*_v1.xml` are Time-Series mapping resources; `resources/VizIcons/` holds the
  `.svg`/`.png`/`.ico` icon set (the `README.txt` there documents the ImageMagick/Inkscape
  regeneration commands). Icons are resolved at runtime through `$VIZ_HOME` in `GlobalIcons`.
- `.gitignore` excludes IDE project files, `doc/build/`, and the test artefacts
  (`__pycache__/`, `.pytest_cache/`, `.coverage`, `/htmlcov/`).

## Testing

There is now a **pytest + pytest-qt suite in `tests/`** (outside the package), with
`pytest.ini` at the repo root and `TESTING.md` as the user guide. Run it from the repo
root after loading the modules:

```bash
python3 -m pytest tests/ -q     # 695 passed, 2 xfailed, ~39 s, offscreen
```

`tests/conftest.py` sets the whole environment (`VIZ_HOME`, `VIZ_PRODUCTION`,
`IMAS_VERSION`, `IMAS_DATA_DICTIONARIES_DIR`, `QT_QPA_PLATFORM=offscreen`, …) at conftest
import time, **before** any test imports `imasviz` — which is mandatory, because
`QVizGlobalValues` and `QVizGlobalOperations.checkEnvSettings()` can `sys.exit()`.
Markers: `ui`, `dd`, `case`; `timeout = 180` caps every test. The 2 `xfail(strict=True)`
entries are real defects and environment limits, listed in `TESTING.md` §4.

A test that **shows** a plot frame must keep it alive for the whole session —
`support/ownership.py`'s `keep()`, which is what the application does through
`Viz_API.figureframes`. Measured: of the 110 plot frames a run builds, 79 lose their
Python wrapper before the run ends, and the 11 that had been shown without being
closed are the ones a queued paint event can kill the process on — the run died at a
fixed position with `Fatal Python error: Segmentation fault` inside pyqtgraph's
`GraphicsView.paintEvent`, in a file several away from the one at fault. An autouse
fixture in `conftest.py` now names the test at fault at its own teardown; a frame
never shown, or closed before it is forgotten, is not a hazard (the production
refusal paths close the window they opened, and that cleanup is what tests check for).

The suite does **not** isolate `$HOME`. A test that lets the application write a
configuration, a preference or a plot-configuration file writes into the real
`~/.imasviz`; `tests/test_39_configurations.py` shows the pattern — point `HOME`
at `tmp_path` with `monkeypatch`, which works because those helpers read `HOME`
when they are called, not at import.

The environment modules must be loaded in a specific order here: `ach-modules`
auto-loads `UDA/2.9.0` and `IMAS-AL-Core/5.5.1`, which conflict with the
`IMAS-Core/5.7.1` stack, so both have to be unloaded first or `import imas` fails.

### The legacy scripts in VizExamples are demos, not tests

- `imasviz/VizExamples/example{1,2,2b,3,4}.py`, `test.py`, `test_plugin.py`,
  `test_QVizPlotLayoutWidget.py`, plus per-plugin `test_*.py` /
  `run_plugin_ui_standalone.py` — scripted usage of the `Viz_API` without the GUI.
- They instantiate a `QApplication`, build a hardcoded datasource dict, and call the class
  directly. To "test" a change, add such a script and run it — but note it needs the IMAS HLI
  and a real case to be meaningful, which is unavailable in most checkouts.
- They are not self-bootstrapping: they need `$VIZ_HOME` on `sys.path`. Prepend it
  (`PYTHONPATH=$PWD:$PYTHONPATH`) — assigning `PYTHONPATH=$VIZ_HOME` *replaces* the
  `PYTHONPATH` the modules export and the `PySide6`/`imas` imports then fail.

### Why those scripts cannot be automated

Two verified properties make them unusable in automation:

- They end with `app.exec_()`, which **never returns** — wrap them in `timeout` or they hang
  until you kill the GUI (a `timeout 45` run of `test_QVizPlotLayoutWidget.py` exits 124).
- Most call `QVizGlobalOperations.askForShot()` (`QVizGlobalOperations.py:413`), which is a
  **`QInputDialog`**, not `stdin` — the shot cannot be fed from a pipe, and the process blocks
  on the dialog before doing any work.

## Pitfalls and code smells already present

Do not "clean these up" while doing unrelated work — they are existing, intentional-looking
artifacts of this codebase, and several are load-bearing:

- `eval`/`exec` on IMAS symbol names survives in `QVizTreeNode.evalPath`
  (`eval(path)` on a `Path` spelling) and in `viz_Profiles/VizProfiles_plugin.py`.
  It is **not** a working idiom for reaching generated IDS classes: on this node
  `imas.<ids>` does not exist, and T12 took out the 5 sites that asked
  `eval("imas." + idsName + "().getMaxOccurrences()")` on a tree gesture — the case
  answers that question through `DBEntry.list_all_occurrences` instead. Do not add
  a new site; do not "restore" the old one.
- `sys.path.append(os.environ['VIZ_HOME'])` is done for side effects at import time, so import
  order matters. It used to append `$HOME/.imasviz/VizGeneratedCode` too, for the generated
  parser classes: that folder is gone with the reflection based parser.
- Mutating `os.environ` as module state in `QVizGlobalValues` means import order and repeated
  imports have visible effects.
- `QVizGlobalOperations.check(...)` / `checkEnvSettings()` print and exit rather than raising
  typed exceptions — error handling at the GUI level expects `ValueError`, so wrap accordingly.
- The root `Makefile` default is now `all: doc`. The `default` (submodule-fetch) target is kept
  for explicit use but is a no-op: **no submodule is configured any more**.
- ETSViz was removed on request — `.gitmodules` and `imasviz/VizPlugins/viz_ETS/` are deleted
  (they held only `ETSpluginIMASViz.py`, `__init__.py` and two unpopulated submodule entries),
  and `'ETSpluginIMASViz'` stays commented out in `RegisteredPlugins`.
- Logging uses a dedicated logger named `'logPanel'` wired to an in-GUI `QPlainTextEdit`
  through `QVizLogger`'s custom Qt signal. Retrieve it as
  `logging.getLogger(self.dataTreeView.uri)` per-shot as the existing code does; a generic
  `logging.info` will not surface in the app.

## Verified in situ (ACH/Gateway module stack)

Checked on this machine with `module load ach-modules` + `PySide6/6.6.2-GCCcore-13.2.0` +
`IMAS-Python/2.3.0-foss-2023b` + `PyQtGraph/0.13.7-foss-2023b`:

- `imas`, `PySide6` (reports **6.6.3**), `pyqtgraph` (0.13.7), `numpy`, `matplotlib` all import.
- Import sweep of the `imasviz` package (skipping `VizExamples/` and standalone scripts):
  **116/117 modules import**. The one failure is Qt-Designer scaffolding only, not in the
  launch chain and not registered: `viz_example/exampleplugin.py`
  (`QPyDesignerCustomWidgetPlugin` absent in PySide6 6.6 — only
  `QPyDesignerCustomWidgetCollection`). Before the SOLPS plugin was removed the sweep
  walked 126 modules with 5 failures; `viz_solps/` and its `src/` subtree accounted for 9
  of those modules, 4 of the failures.
- In this PySide6 build `Slot`, `Signal`, `QThread` and `exec_()` **do** exist, while
  `QVariant` and `pyqtProperty` do **not**. `QWidget`/`QGridLayout`/`QMainWindow` are in
  `QtWidgets`; `QIntValidator` is in `QtGui`.
- With `VIZ_PRODUCTION=1 VIZ_HOME=$PWD IMAS_VIZ_VERSION=… UDA_DISABLED=1` exported, the whole
  launch chain imports headless (`sys.argv = [..., '-platform', 'offscreen']` **before** the
  import — `QtVIZ_GUI` builds a `QApplication` at module level). A plain run stops only at
  `qt.qpa.plugin: Could not load the Qt platform plugin "xcb"`, i.e. no X display.
- What the suite **does** reach: the reference case is opened by `tests/conftest.py`
  (`imas:hdf5?path=…/west/3/54924/0`, pinned at data dictionary `3.35.0` while the
  harness dictionary is `3.23.3`), its shadow trees are walked, and since T12 a real
  `QVizDataTreeViewFrame` is built on it — 55 IDS roots, occurrences read from the
  entry, one occurrence loaded. `QVizPreferences().build()` has to have run first, or
  `setStyleForIDS` calls `setForeground(0, None)` and answers `TypeError`; `QtVIZ_GUI`
  and `Viz_API` both call it at start-up, a test has to.
- Still **not** exercised: plugin runtimes, and `make doc` (`sphinx-build: command not
  found` — Sphinx is not on this stack; `python3 -m sphinx -b html -D html_theme=alabaster`
  is how the manual gets checked here).
