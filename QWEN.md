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
  `AttributeError` wherever it appears. Since T13 it appears in **no executable
  statement**: the 6 places that asked it — the shot view's empty tree,
  `hasAvailableData`, the three `Viz_API` occurrence helpers and the Profiles plugin's
  entry — now ask the case through `DBEntry.list_all_occurrences` (0.10 s for the whole
  inventory of the reference case), and six mentions survive as comments naming what
  was replaced. What survived after T13 was `eval` on an **attribute path of a
  loaded IDS object** — `eval(self.ids_related + ".time[time_index]")`, **15** sites in
  `viz_Profiles/viz_profiles/VizProfiles.py` — fed by an `exec(idsName + " = …")` in
  the same breath, and `QVizTreeNode.evalPath`'s `eval(path)`. **T31 took all of it
  out**: a path is walked off the loaded IDS object now (`resolveIDSPath`), because
  the `exec`/`eval` pair only ever worked by leaving a name in the caller's frame
  locals — see the *Pitfalls* list. Since T27 nothing in the repository reaches the
  generated modules at
  all: `viz_equi/ids_read_multiprocess.py`, which called `imas.ids(shot, run)` and
  `idd.open_env(...)`, is gone.
  Do not write new code against generated `imas.<ids>()` classes; they do not exist
  on this node.
- **Two python HLIs are installed on this node, and only one of them runs IMASViz.**
  Measured: `IMAS-Python/2.0.1`, `2.1.0` and `2.3.0` (distribution `imas-python`,
  homepage `github.com/iterorganization/imas-python`) all ship `ids_data_type.py`,
  `ids_struct_array.py` and `ids_metadata.py`, and 2.3.0 exposes `IDSDataType` and
  `IDSStructArray` at the package root too. `IMAS-AL-Python/5.4.0-*-DD-<dd>` (the
  generated HLI from `git.iter.org/imas/al-python.git`, distribution `imas`, built
  once per data dictionary) holds `ids_base.py`, `ids_names.py`, `db_entry.py`,
  `dd_units.py` plus one generated module per IDS, exports `DBEntry`, `IDSName`,
  `IDSBase`, `get_al_version` — and the string `IDSDataType` appears in **none** of
  its files, so `import imas` and `imas.DBEntry` both succeed there while the
  metadata walk cannot start. The README used to state the opposite of this, which
  is how a user ends up on the wrong HLI; it now says what is measured, and
  `VizDataAccess/QVizAccessLayerHLI.py` asks the two reflection names once and
  refuses by name — printing the package that is in charge, what it lacks, and the
  `module load IMAS-Python/<version>` line to answer with — instead of dying on a
  `ModuleNotFoundError` inside a leaf import.
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
| `IMAS_VERSION` | The version of the **data dictionary**, not of the Access Layer. IMAS-Python reads this variable itself (`imas.dd_zip.dd_etree`), so nothing in `imasviz` needs it; it must be a version the distribution bundles — measured: 35 of them, `3.22.0` through `4.1.1`. The IMAS-Python module exports `AL_VERSION` (5.7.1) and **not** `IMAS_VERSION`; `QVizGlobalValues` used to copy the former into the latter when only the first was set, which is what made opening a pulse die (see the T28 row of `LEGACY_REPLACEMENT.md`). That copy is gone from both branches, and `IMAS_MAJOR_VERSION` with it: nothing reads either. |
| `TS_MAPPINGS_DIR` | Same "default only if unset" rule; `$VIZ_HOME/ts_mapping_files` does exist in the repo. |
| `UDA_DISABLED` | `1` disables UDA. Forced to `1` in TESTING mode. |
| `AL_VERSION` | Exported by the IMAS-Python module (**5.7.1** here). **Nothing in `imasviz/` reads it any more**: since T29 no statement asks which Access Layer major version is loaded, so there is no Access Layer 4 branch left to feed — no entry built from six positional numbers, no `legacy_attributes`, no URI box disabled at start-up. Do not "restore" one. It is an Access Layer number, never a data dictionary version — see `IMAS_VERSION` above, and the T28 row for what confusing the two cost. |
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
| `make doc` / `make -C doc html` | Sphinx route (`cd doc && make html`). **It stops on this node, but not for the reason this row used to give**: `sphinx-build` **is** reachable — 7.2.6, at `Python-bundle-PyPI/2023.10-GCCcore-13.2.0/bin/sphinx-build`, on PATH without loading any module — and what is missing is the theme `doc/source/conf.py:90` asks for: `Theme error: no theme named 'sphinx_rtd_theme' found (missing theme.conf?)`, `make: *** [Makefile:27: doc] Error 2`. `pip3 install sphinx_rtd_theme` is what `make doc` still needs; `doc/build/` is gitignored. |
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

Sphinx 7.2.6 is on this node and needs no module; `sphinx_rtd_theme` is not installed, and
that is what `make doc` stops on. `python3 -m sphinx -b html -D html_theme=alabaster
doc/source <out>` is how the manual gets built and checked here: 21 source files, exit 0,
two warnings, both about `conf.py` itself (`language = None`, and the pre-1.0
`intersphinx_mapping` form).

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
│   └── VizConfigurations/
├── VizPlugins/                # plugin framework + plugins (see below)
└── VizExamples/               # example_*.py and test_*.py standalone scripts
```

Core concepts, in the vocabulary used by the code and docs:

- **DTV / shot view** — one `QVizDataTreeViewFrame` per opened case, tracked in
  `Viz_API.DTVframeList` / `DTVlist`.
- **figure frames** — `Viz_API.figureframes`, keyed by `FigureTypes` prefix + number
  (`SlicesPlot1`, `SlicesImage1`, `TablePlotView0`, `StackedPlotView0`, `ProfilesPlot…`).
  Five kinds since T22(c): the `Figure:` namespace the legacy curve window handed out is
  gone with the window, as the `Image:` one went before it — a prefix with no frame behind
  it is a Show/Hide sub-menu that can never be filled. Because of that, `GetFiguresCount`,
  `GetNextKeyForFigure`, `GetFiguresKeys` and `GetFigureKey` take no default `figureType`:
  a call naming no kind used to mean the dead one silently.
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
  figures and shot views are `QMdiSubWindow`s inside it. Both the **figure** paths and the
  **shot view** paths ask what a frame's parent *is* (`Viz_API.mdiWindowOf`) before they show,
  hide or delete it — T21 took out of `QVizMainMenuController` the last three comparisons that
  asked what the top-level window was *called*, and the four copies of `getMDI` that no caller
  reached and that all four hinged on that name. The string is still load-bearing in one place:
  `GUIFrame.getMDI` walks it to find the area it hands to `QVizOpenShotView` at construction,
  and `QVizMainWindow.getMDI` returns its own area without deciding anything. Embedding is not
  showing: `QMdiArea.addSubWindow`
  leaves the subwindow hidden when the area is already on screen, which is the state of the
  running application, so `addPlotWidgetToMDI` shows what it embeds — and `ShowDataTree` shows
  the window it embeds a shot view in, since showing the frame is not what makes it visible.

Naming convention: Qt widget classes are prefixed `QViz` (`QVizCurvePlot`, `QVizLogger`);
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
   catalog binds `setSelectedTreeNode(node)` **and** `setDataTreeView(view)` and asks the
   methods, so a plugin outside the hierarchy that honours them is offered like any other.
   The view binding is load-bearing and was missing for three slices: a plugin that reads
   `self.dataTreeView` — which is how `VizProfiles_plugin` asks the case which occurrences
   it holds — answered `AttributeError` on the first line of `execute()`, and the guard in
   `QVizPluginCatalog.run` reported it as `Plugin ... failed`, so the entry looked broken
   rather than unbound. A test that only checks "a failing plugin is named in the log"
   passes right over that; `test_43` now pins the binding itself.
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

**Two** plugins are registered (`VizPlugin.py:32-36`), and both are now run end to end on
the reference case by `tests/test_51_*` (Profiles) and `tests/test_53_*` (Equilibrium).
The Equilibrium one (`viz_equi/equilibriumcharts.py`, **1 253 l.**, author J. Morales) is
the only matplotlib window in the application: it does not draw through the axes model, so
it is registered under its own `FigureTypes.EQUILIBRIUMPLOTTYPE` (`EquiPlotView:`) — a
**6th** `MENU_ORDER` kind, so *Show/Hide* and *Delete* reach it — and it registers **no**
node in `figToNodes`, which is why the "add this quantity to that figure" entries do not
offer it. Measured facts worth keeping: it reads **occurrence 0** and does not ask (unlike
Profiles, whose occurrence question is a modal `QInputDialog`); its window is parented to
the shot view and is **not** an MDI subwindow (`mdiWindowOf` answers `None`), so it goes
with the view it came from; **6,73 s** cold for the first run of a process, **0,98–1,45 s**
once the IDS is in memory. And `QVizPreferences.Ignore_GGD` does **not** cover the plugin's
own `get`: with the GGD walk of the tree reactivated, the same case cost **287 s** in a
probe, which is why `test_53` pins that preference at **1**.

### matplotlib is not pinned here

The plugin's drawing library comes from `~/.local/lib/python3.11/site-packages`, not from a
module — measured **3.11.2** on this node, while the sources were written against something
older. Two call shapes that file used are refused by it, and both failures land inside a Qt
slot, so the traceback prints and the caller is not told: `set_xdata(<number>)` answers
`RuntimeError: x must be a sequence` (a vertical line carries two points: `set_xdata([v, v])`),
and `grid(b=…, which=…, linestyle=…)` answers `ValueError: keyword grid_b is not recognized`
(as soon as another keyword follows `b=`, use `grid(True, which=…, linestyle=…)` /
`grid(False)`). Check the matplotlib version before blaming a plugin for a blank window.

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
python3 -m pytest tests/ -q     # 817 passed, 1 xfailed, ~126 s, offscreen
```

`tests/conftest.py` sets the whole environment (`VIZ_HOME`, `VIZ_PRODUCTION`,
`IMAS_VERSION`, `QT_QPA_PLATFORM=offscreen`, …) at conftest
import time, **before** any test imports `imasviz` — which is mandatory, because
`QVizGlobalValues` and `QVizGlobalOperations.checkEnvSettings()` can `sys.exit()`.
Markers: `ui`, `dd`, `case`; `timeout = 180` caps every test. The 1
`xfail(strict=True)` entry is an environment limit, listed in `TESTING.md` §4.

A test that **shows** a plot frame must keep it alive for the whole session —
`support/ownership.py`'s `keep()`, which is what the application does through
`Viz_API.figureframes`. Measured: of the 110 plot frames a run builds, 79 lose their
Python wrapper before the run ends, and the 11 that had been shown without being
closed are the ones a queued paint event can kill the process on — the run died at a
fixed position with `Fatal Python error: Segmentation fault` inside pyqtgraph's
`GraphicsView.paintEvent`, in a file several away from the one at fault. An autouse
fixture in `conftest.py` now names the test at fault at its own teardown; a frame
never shown, or closed before it is forgotten, is not a hazard (the production
refusal paths close the window they opened, and that cleanup is what tests check
for). Since T21 the guard counts **hidden** as another way out of the paint queue,
which is what production uses when it deletes a window rather than refusing:
`Delete` on a shot view hides the MDI window — a hide reaches the children
recursively — and then asks Qt to delete it, so the preview plot nested in that
frame dies legitimately. `test_44` pins both halves, including the recursive hide.

The suite does **not** isolate `$HOME`. A test that lets the application write a
configuration, a preference or a plot-configuration file writes into the real
`~/.imasviz`; `tests/test_39_configurations.py` shows the pattern — point `HOME`
at `tmp_path` with `monkeypatch`, which works because those helpers read `HOME`
when they are called, not at import.

It does **not** isolate the case either. `dataSource.data_entries` is
`QVizDBEntryRegistry.ids_cache(uri, mode, dd_version)` — one dict per **case** for
the whole process — so any file that opens the reference case shares its cache,
and a test that asserts that cache is empty, or asserts the exact set of files an
export writes, is reading whatever the earlier files left behind (measured in a
full run: `calorimetry/0` through `tf/0` before another file's first load). The
application never meets it, because `QVizOpenShotView.Open` reuses the one view of
a case. A test that needs a cache of its own has to own a case, and that case has
to be copied **through the Access Layer**: the reference run directory holds one
6 365-byte `master.h5` whose groups are HDF5 links into `../4/equilibrium.h5`, so
a file-system copy answers `Unable to open HDF5 group: equilibrium`.
`tests/test_49_export_then_open_what_was_written.py` shows both patterns.

`tests/test_45_one_user_journey.py` is the one file that joins gestures into a
continuous journey (open a case, load, select, draw, save, replay in a second
window on another shot, close it), and it carries two constraints worth knowing
before writing any case-driven test. A shot view **must** be built through
`Viz_API.CreateDataTree` — the call `QVizOpenShotView.Open` makes — because that
is what appends the frame to `DTVframeList` and the view to `DTVlist`; a frame
constructed by hand with a bare `Viz_API` passes each gesture in isolation and
then cannot draw a selection: `QVizPlotAsSlices` defaults to `all_DTV=True`, asks
`api.DTVlist`, and answers `ValueError: No signal selected.` on a selection the
view itself holds. Second, the journey is one scenario, so its tests run in the
order written and assert on the figure keys the api handed out while they ran.
`QVizDBEntryRegistry` is one dict for the process: other files open the same case,
so a reference count there is only meaningful as an invariant (the reference case
sits at 12 in a full run), and `RemoveDTVFrame` → `forget_case` drops the whole
record for the case it was the last to show.

The real-case files are where the suite's time goes, and one walk dominates:
`tests/test_46_time_slices_on_a_real_case.py` alone is **+42 s**, because asking
`equilibrium` for *all* its time slices keeps **164 792** signals and takes **26 s**
to walk (a plain load keeps one slice: **3 368** signals). Those numbers are pinned
in the file so nobody re-measures them; a slice index the case does not hold is
**not** raised at the caller — `QVizIDSViewParser.run()` catches the `ValueError`
and consigns it to the log of the case, so the assertion belongs on the log
(`caplog`), and the refused view is left with nothing loaded at all.

The environment modules must be loaded in a specific order here: `ach-modules`
auto-loads `UDA/2.9.0` and `IMAS-AL-Core/5.5.1`, which conflict with the
`IMAS-Core/5.7.1` stack, so both have to be unloaded first or `import imas` fails.

### The legacy scripts in VizExamples are demos, not tests

- `imasviz/VizExamples/example{1,2,2b,3,4}.py`, `test.py`, `test_plugin.py`, plus per-plugin
  `test_*.py` / `run_plugin_ui_standalone.py` — scripted usage of the `Viz_API` without the
  GUI. (`test_QVizPlotLayoutWidget.py` was one of them until T22(c) deleted the widget it
  drove.)
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

- The `eval`-on-an-IMAS-symbol-name idiom is **gone** — T31 took out its last two
  homes, `QVizTreeNode.evalPath` and the **15** sites of the Profiles plugin's
  `viz_profiles/VizProfiles.py`. It was never a way to reach generated IDS classes
  (`imas.<ids>` does not exist on this node), and it was never a way to read a value
  either: every site was fed by `exec(idsName + " = self.getIDSRef()")`, which writes
  into the **frame-locals mapping of its caller** and leaves `eval` to find that name
  back there. That is a CPython implementation detail — it answers on this node's
  3.11.5, it stopped answering on a newer CPython elsewhere, and every node of a real
  session died with `NameError: name 'magnetics' is not defined` inside `updateStyle`,
  with nothing in the traceback naming the case or the IDS. A path is walked off the
  loaded IDS object now (`QVizTreeNode.resolveIDSPath`), which is also **3,6×** faster
  on a real view. Do not add an `exec`/`eval` pair back; `test_56` compiles the module
  and refuses the names. Earlier T12/T13 had already taken out the 6
  `eval("imas." + idsName + "().getMaxOccurrences()")` sites — do not "restore" those
  either; the case answers that through `DBEntry.list_all_occurrences`.
- `sys.path.append(os.environ['VIZ_HOME'])` is done for side effects at import time, so import
  order matters. It used to append `$HOME/.imasviz/VizGeneratedCode` too, for the generated
  parser classes: that folder is gone with the reflection based parser.
- Mutating `os.environ` as module state in `QVizGlobalValues` means import order and repeated
  imports have visible effects.
- `pyqtgraph.exporters.Exporter.Exporters` is a **class** attribute, and the export dialogue
  fills its format list from it each time it is built (`exportDialog.py:104`): a module that
  edits it edits every figure of the session, not the plot that asked. The Profiles plugin
  did exactly that from its view box's constructor — measured on one curve figure, the
  dialogue answered **5** formats before a `CustomizedViewBox` existed and **4** after, the
  missing one being the `Matplotlib Window` the manual documents — and the copy it meant to
  put in that place (`VizGUI/VizExporters/QVizMatplotlibExporter.py`) was imported by nobody,
  so its `register()` never ran and the patch only ever subtracted. T23 deleted the class,
  its directory and the patch; `test_57` refuses any module of the package naming
  `Exporter.Exporters`.
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
- A thread that does not own a widget may not touch one, and on this Qt 6.6.3 stack the
  failure is not a warning but a **hang**: measured with no IMAS and no case in it, a
  `QThread` calling `close()` on a shown `QProgressBar` stayed inside `QWindow::close()`
  past a 20 s watchdog while the GUI thread pumped events. `QVizIDSViewParser.run()` used
  to do exactly that on its failure paths, which lost the walk thread, so `finished` never
  fired, the parser was never dropped from `dataSource.runningParsers`, and the occurrence
  stayed in `QVizDataTreeView.loadsInProgress` for the rest of the session — every later
  request for it then refused as "already being loaded". It no longer does (T18): the walk
  logs and, when it is synchronous only, takes its bar down; asynchronously the source's
  `_loadFinished` does it, on the thread that made the bar. A worker may compute, log and
  `postEvent`; anything that creates, shows, renames or closes a window belongs on the GUI
  thread. The symptom to recognise is a probe or test that stops printing with no exception
  — confirm it with `faulthandler.dump_traceback_later(n, exit=True)`, do not guess.

## Verified in situ (ACH/Gateway module stack)

Checked on this machine with `module load ach-modules` + `PySide6/6.6.2-GCCcore-13.2.0` +
`IMAS-Python/2.3.0-foss-2023b` + `PyQtGraph/0.13.7-foss-2023b`:

- `imas`, `PySide6` (reports **6.6.3**), `pyqtgraph` (0.13.7), `numpy`, `matplotlib` all import.
- Import sweep of the `imasviz` package (skipping `VizExamples/` and standalone scripts):
  it walks **107** modules and **106** of them import. The one failure is Qt-Designer
  scaffolding only, not in the
  launch chain and not registered: `viz_example/exampleplugin.py`
  (`QPyDesignerCustomWidgetPlugin` absent in PySide6 6.6 — only
  `QPyDesignerCustomWidgetCollection`). Before the SOLPS plugin was removed the sweep
  walked 126 modules with 5 failures; `viz_solps/` and its `src/` subtree accounted for 9
  of those modules, 4 of the failures. T22(c) took **7** more out of the walk — five
  production modules of the legacy figure island, the `viz_tests` package and its module.
  The HLI gate added **1** to the walk and T27 took **1** back:
  `viz_equi/ids_read_multiprocess.py`, the module that spoke the generated HLI; T23 took
  **1** more, `VizGUI/VizExporters/QVizMatplotlibExporter.py`, and the `VizExporters/`
  directory with it — that directory held no `__init__.py` and nothing else. Note that
  the sweep skips `test_*.py` by name, which is why the demo
  `viz_equi/test_equilibriumcharts_plugin.py` (59 l.) was never in that count and its
  removal costs no test.
- In this PySide6 build `Slot`, `Signal`, `QThread` and `exec_()` **do** exist, while
  `QVariant` and `pyqtProperty` do **not**. `QWidget`/`QGridLayout`/`QMainWindow` are in
  `QtWidgets`; `QIntValidator` is in `QtGui`.
- With `VIZ_PRODUCTION=1 VIZ_HOME=$PWD IMAS_VIZ_VERSION=… UDA_DISABLED=1` exported, the whole
  launch chain imports headless (`sys.argv = [..., '-platform', 'offscreen']` **before** the
  import — `QtVIZ_GUI` builds a `QApplication` at module level). A plain run stops only at
  `qt.qpa.plugin: Could not load the Qt platform plugin "xcb"`, i.e. no X display.
- What the suite **does** reach: the reference case is opened by `tests/conftest.py`
  (`imas:hdf5?path=…/west/3/54924/0`, pinned at data dictionary `3.35.0` while the
  harness dictionary is `4.0.0`), its shadow trees are walked, and since T12 a real
  `QVizDataTreeViewFrame` is built on it — **69** IDS roots, which are the IDS names
  the **entry** declares for the dictionary that case is stored with (`DBEntry.dd_version`
  → `IDSFactory.ids_names()`), not the contents of an `IDSDef_<version>.xml` file: since
  T28 no such file is read anywhere, and the `55` this section used to report was that
  file's count at `3.23.3`. Occurrences are read from the entry, one occurrence loaded.
  Since T30 a source built from a URI **without** an explicit pin no longer settles on the
  newest dictionary the package holds: `QVizIMASDataSource.pinToCaseDictionary` runs before
  the entry is taken from `QVizDBEntryRegistry` (the registry key *is* `(uri, mode,
  dd_version)`), reads the major the URI spells and asks the case the exact minor its first
  filled IDS names at `ids_properties/version_put/data_dictionary` — **slashes**, points
  answer `ValueError: Invalid node name` — so that case opens at `3.35.0` whatever the
  harness dictionary is. Measured cost: **0,10 s** for the occurrence inventory of the whole
  case, **0,41 s** for the version node of one IDS. The harness' explicit pin keeps the
  numbers above; an entry left unpinned on this node settles on **4.1.1** (the newest of the
  **35** dictionaries IMAS-Python bundles), which declares **82** roots for that case and
  then refuses **every** `get` with `RuntimeError: On-disk data is stored in DD 3.35.0 which
  has a different major version than the requested DD version (4.1.1)` — while
  `list_all_occurrences` answers through the major, which is why the view was built and only
  the loads died. Pinning the major alone is not enough either: the walk of `equilibrium`
  occurrence 0 holds **3519** leaves at `3.35.0` against **3594** at `3.42.2`.
  `QVizPreferences().build()` has to have run first, or
  `setStyleForIDS` calls `setForeground(0, None)` and answers `TypeError`; `QtVIZ_GUI`
  and `Viz_API` both call it at start-up, a test has to.
- A plugin entry **is** run end to end now — `tests/test_51_profiles_plugin_figure_menu.py`
  chooses the registered Profiles entry on the reference case and pins what it puts on
  screen (**2** tabs, **41** plots, **41** curves, `PlotView:1`). Two measured defects
  in that plugin stood in the way, and both are fixed: labelling its time slider
  formatted a 0D time node, which on IMAS-Python is an `IDSFloat0D` — a `numbers.Real`
  wrapper with `__float__` and **no `__format__`** — so `f"{tmin:.2f}"` raised
  `TypeError: unsupported format string passed to IDSFloat0D.__format__`
  (`VizProfiles.py:504`) inside `setUI`, leaving everything under the tabs unbuilt;
  and `CustomizedViewBox.getMenu` walked `self.menu.leftMenu`, which pyqtgraph
  **0.13.7** does not keep (the actions are in `ViewBoxMenu.mouseModes`), so the right
  click on a plugin plot answered `AttributeError` before the menu opened. What is
  **still** true of that plugin: the occurrence question is a **modal `QInputDialog`**
  — with the **4** occurrences this case holds for `equilibrium` a probe sat in
  `VizProfiles_plugin.askForOccurrence` for **240 s** until the watchdog killed it — so
  a test patches the dialog at module level (`setattr(profilesPlugin, 'QInputDialog',
  StubDialog)`) and asserts on the question rather than answering it by hand. And a
  plugin window is registered like a figure (`PlotView:1` in `figureframes`) but is a
  **top-level** window: measured `parent() is None`, never embedded in the MDI area.
  Since T22(b) its three figure gestures run `QVizPlotOneNode` like every other gesture,
  so the frames they build are `SlicesPlot1`/`SlicesPlot2` in the MDI area, and the
  "add this quantity to that figure" gate lives on `Viz_API`
  (`figureDrawsSameCurveAxis`, next to the `figToNodes` record it reads) where the shot
  view's menu and a plugin's view box ask the same question.
- The manual **is** built and checked here, with the theme overridden: `python3 -m sphinx
  -b html -D html_theme=alabaster doc/source <out>` answers exit 0 over 21 source files and
  two `conf.py` warnings, and it is the only route that works — `make doc` itself still
  fails, on `sphinx_rtd_theme`, not on Sphinx (`sphinx-build` 7.2.6 is on PATH here). Its
  output is throwaway: `make clean` takes `doc/build` back.
