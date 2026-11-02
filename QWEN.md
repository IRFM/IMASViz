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
  behavior. Its look is **in the repository**: Sphinx's own `basic` theme plus
  `doc/source/_static/imasviz.css` and `imasviz.js`, so a build needs no theme package. The sheet
  carries its colours as a light/dark token block between `/* tokens:begin … */` markers.

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
| `make doc` / `make -C doc html` | Sphinx route (`cd doc && make html`), and it **works**: `build succeeded`, exit 0, **0 warnings**, **3,87 s**, 21 sources → **23** pages under `doc/build/html` (gitignored). Nothing but Sphinx is needed — since T47 the manual wears `doc/source/_static/imasviz.css` over the `basic` theme. What it stopped on before is recorded because the docs and the README said the opposite: `sphinx-build` 7.2.6 has been on PATH here all along (no module), and what was missing was the theme `conf.py` asked for — `Theme error: no theme named 'sphinx_rtd_theme' found (missing theme.conf?)`, `make: *** [Makefile:27: doc] Error 2`. The two `conf.py` warnings the override route used to print (`language = None`, the pre-1.0 `intersphinx_mapping` form) are gone with those settings. |
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

Sphinx 7.2.6 is on this node and needs no module, and since T47 nothing else is needed either:
the manual's look is `doc/source/_static/imasviz.css` (+ `imasviz.js` for the light/dark choice)
over the `basic` theme, so `make doc` builds. `-D html_theme=alabaster` is no longer how the
manual is built and checked here — it is no longer *needed* — and the two `conf.py` warnings it
used to answer (`language = None`, the pre-1.0 `intersphinx_mapping` form) went with the settings
that caused them: `language = 'en'`, and `sphinx.ext.intersphinx` out of `extensions` (its one mapping —
`docs.python.org` — was fetched over the network for **0** `:py:` roles in a manual documenting a GUI).

There is a pytest suite (see Testing below), but **no CI config, linter config, or
packaging manifest** in this repo.

## Architecture map

```
imasviz/
├── Viz_API.py                 # Viz_API: scripting API + central session state
├── VizUtils/                  # global constants, prefs, logging, window geometry
├── VizDataSource/             # opens a case: URI building, DBEntry, Tore-Supra, factory,
│                              # QVizCaseOccurrences (which occurrences the case holds),
│                              # QVizDBEntryRegistry (one record per case: the entry, its
│                              # reference count, its IDS handles, and which of them are lazy)
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
  it is a *Windows* menu group that can never be filled. Because of that, `GetFiguresCount`,
  `GetNextKeyForFigure`, `GetFiguresKeys` and `GetFigureKey` take no default `figureType`:
  a call naming no kind used to mean the dead one silently.
  Allocate keys through
  the `GetNextKeyFor*` accessors, never by hand — **except when a key arrives from
  a session file**, which is answered by `Viz_API.FigureKeyFor(type, key)`: the key
  is the identity the *Windows* menu — its lines, and the *Delete* sub-menu beside
  them — and the *add to that figure* entries address
  a window by, so the three plot commands take a `figureKey=` and honour it, and a
  key a live window already holds is refused (measured before that: a file naming
  `SlicesPlot1` came back as `SlicesPlot2`, and `QVizPlotAsStacked` was the last of
  the three still asking for the next key).
- **the windows of a run** — `Viz_API.openWindows()` is the one answer to "what is open":
  the case views of `DTVframeList` first, then `figureframes` walked through
  `FigureTypes.MENU_ORDER`, each window a `QVizWindowRecord` (kind label, icon, label, and
  weakrefs to the frame and the api — a menu line that outlives its window costs nothing, and
  `QVizWindowRecord.frame()` asks `shiboken6.isValid` because a QWidget released with
  `deleteLater()` **keeps its Python wrapper** while anything else holds a reference, so asking
  that wrapper answers `RuntimeError: Internal C++ object … already deleted`).
  `VizGUICommands/VizMenusManagement/QVizWindowMenu.py` draws that list on the application menu
  bar **and** on every shot view's bar — one object, refilled on `aboutToShow` through
  `QVizMenuRefill.refill`. One checkable line per window (the check is the screen, the click
  toggles), grouped by kind, then `Show all` / `Hide all`, then a separate `Delete` sub-menu
  (one line per window plus one `All` per kind); `Next window` / `Previous window` on `Ctrl+Tab`
  / `Ctrl+Shift+Tab` hang on the application bar only, a shot view owning no MDI area. The node
  right-click pop-up lists no window any more — it is about the node under the mouse — and the
  shot view's old *Plot windows* menu is gone. Why `refill` exists: `QMenu.clear()` removes
  actions and **keeps the child QMenus** (measured: **7** children and **0** actions after three
  refills), while `refill()` leaves **1** once the deferred deletes are flushed.
- **what the close box of a window costs** — **hide, and keep the key**.
  `QVizMdiSubWindow.closeEvent` and the `QVizClosableWindow` mixin (which answers `windowApi()`)
  ask `Viz_API.closeFromTitleBar`: the window leaves the screen, `figureframes` is left alone, so
  the *Windows* menu still names it (unchecked) and a saved session writes it `hidden`.
  `Close_button_deletes=1` in `$HOME/.imasviz/preferences` makes the box mean what the *Delete*
  line means — `closeWindow`, i.e. hide + `deleteLater()` + `forgetWindow`. Measured before the
  rule: a curve figure closed with its own box left `figureframes` **empty**, its subwindow
  hidden inside `subWindowList()`, its frame alive with no key reaching it, and the next figure
  of that kind was handed `SlicesPlot1` again — two windows under one name, one unreachable by
  any gesture. A plugin window the plugin shows itself (`PlotView:` and `EquiPlotView:` are both
  top-level, parented on the shot view) is not an MDI subwindow, so nothing routes its box for
  it: the frame mixes in `QVizClosableWindow` and answers `windowApi()` with the api it is
  registered in — held through a `weakref`, per the T25 rule.
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
- **a session** — `VizConfigurations/QVizSessionFile.py` owns the third kind,
  `.vsess` under the same folder and behind the same name guard and listing
  (`EXTENSIONS` gained `SESSION`): an `<IMASVizSession version="5">` root (`1`, `2`,
  `3` and `4` stay readable), one `<Case uri dd_version label>` per case holding
  `<Load ids occurrence slices>`, `<Expanded ids [occurrence]>`,
  `<Selection path occurrence>` and `<PluginWindow key plugin entry ids
  occurrence>`, then one `<Figure key kind [axis] [tensor]>`
  per window holding `<Quantity path occurrence [uri] [row column]/>` and —
  only when the user actually set something — `<Cursors folded><Cursor key
  index/></Cursors>`, `<View x0 x1 y0 y1 autoX autoY xInverted yInverted/>`,
  `<Errors bars="all|step=N" bands="1"/>` and `<Window x y w h maximized
  hidden/>`. Version 4 adds what a hand changed through *Configure Plot*: a
  `<Style trace color style width symbol size fill outline/>` under the
  `<Quantity>` that drew the trace — `trace` being its rank among **that quantity's**
  traces, never its position in the window — and a `<TextStyle side text bold italic
  size/>` under `<Figure>` for the window's own title and axes or under `<Quantity>` for
  the labels of one panel. Both are written **only** for what a hand touched: the frame
  records which traces and labels were touched and the values are read off the live
  curves at save time, so the palette a figure chose for itself is chosen again next
  time rather than frozen into the file (measured: an untouched two-trace figure writes
  **0** `<Style>`, one coloured trace writes **1**; an image window writes neither,
  having no trace to dress). Version 5 adds the colours of a picture window: one
  `<ColourScale map low high/>` under the `<Figure>` — **one for the window**, because
  its pictures share one map and one level range — again written only for the half a
  hand moved, so a window nobody dressed writes nothing and comes back with the map
  this node holds (`viridis`) and the span its own pictures settle on. `QVizSaveSession
  .scaleOf` reads it off `QVizImageColourScale.state()`, which answers `None` for a
  figure that holds no picture, and `QVizRestoreSession.applyColourScale` puts it back
  **after** the styling and **before** the cursors: on a picture window either half on
  its own is a whole answer, and a name this node cannot resolve is named in the log of
  the case while the **range still goes on** (measured: an undrawable map costs the
  colours and not the numbers). A `<ColourScale>` naming neither a map nor a range, an
  unknown attribute, an empty `map` and `low > high` are all refused at the file — the
  last one because pyqtgraph answers the *midpoint* of two reversed ends, so a range
  nobody wrote would reach the screen as a flat one.
  `VizGUICommands/VizSession/` holds the two commands: `QVizSaveSession`
  reads the screen out of the api, `QVizRestoreSession` **replays the gestures**
  rather than rebuilding widgets — the body of `QVizOpenShotView.Open`,
  `QVizLoadOccurrence`, `QVizPlotOneNode`, `QVizPlotAsTable`,
  `QVizPlotAsStacked`, and the plugin entry behind a plugin window — so a restored
  window owns its sliders, its abscissa and
  its menu line; the states are then put back **after** the window is drawn
  and re-shown, in that order: styling (a style is a hand, and a replayed one must be
  dressed before anything moves its traces), cursors (moving an index reloads the curves that
  stand on it), error lines, range, window. Three consequences of that choice,
  each said in the module: the loads are synchronous (a figure whose tree is
  still being built is an empty window), a case that cannot be opened costs
  **its own** windows and names the file and the URI in the log, and the
  selection is applied **last** because a Stacked Plot View is filled from the
  selection of its view. A plugin window (`PlotView:`, `EquiPlotView:`) is **not**
  a `<Figure>` — it is not in the MDI area and answers no key of its own — so it
  is a `<PluginWindow>` under the case whose view offered its entry, and the
  restore asks that entry again through `view.pluginCatalog` (built there if the
  menu was never opened) with `QVizPluginAnswers(occurrence, figureKey)`: nothing
  is asked of the user, where the Profiles occurrence question is a **modal
  `QInputDialog`** that held a probe **240 s**. That needs two things of a plugin,
  both in the howto: `execute(self, vizAPI, pluginEntry, answers=None)`, and a
  `QVizPluginWindow(uri, plugin, entry, ids, occurrence)` stamp left on the window
  it drew — `QVizPluginCatalog.run(entry, answers=)` refuses by name an `execute`
  that cannot take the answers. A window comes back **as its entry draws it**: the
  time index it starts on, not the one a slider was dragged to, and no tab the
  user added. Two things a `<Figure>`
  cannot say are said at the restore instead of pretended: the band of a table
  or stacked window belongs to a **panel**, and an image window answers one view
  box per **picture**. Two Qt facts behind the shape of those elements:
  `QMdiArea` has **no** `saveState`/`restoreState` on this PySide6 (measured with
  `hasattr`), so the place of a window is four numbers in the clear; and
  pyqtgraph **pads** a range it is asked for, so replaying a stored one needs
  `setRange(..., padding=0.)` — asking that box for `[0, 1]` answers
  `[[-0,0416, 1,0416]]` otherwise, and a window would widen at every save.
  A slider's key is the tuple `QVizAxis.key()` answers, spelled
  `AOS/magnetics/flux_loop`, with the **level as a number** — a letter matches
  no axis. Closing the application writes `last_session.vsess` from
  `QVizMainWindow.closeEvent` (before Qt starts taking windows away, not from a
  `destroyed` handler) and the next start **asks** whether to put it back; no
  file, no question, and *Load session* lists it like any other name. **Both ends
  of that are a preference now, and it is off** — `QVizPreferences.Auto_save_session`,
  read from `$HOME/.imasviz/preferences` like the four options before it, decided
  once by `QtVIZ_GUI.autoSavesSession()` (a module function, because `closeEvent`
  and `askForLastSession` are driven on stand-ins that cannot carry a new method).
  Off: nothing is written and nothing is asked, even when a `last_session.vsess`
  an earlier release left is still in the folder.
- **reading a case is lazy** — `QVizIMASDataSource.LAZY_READS` is `True`, so every
  `entry.get()` of the application asks IMAS-Python for a lazy IDS: the handle is a
  window onto the open file, and the values are read when something asks for them.
  Measured on the reference case, walking `equilibrium` occurrence 0: **0,10 s** and
  **+7,7 Mo** lazily, against **3,99 s** and **+122,8 Mo** read whole — and the tree
  is the same either way (**7203** elements, **7030** leaves). Two consequences to
  keep in mind. A lazy handle **dies with the entry**: after `entry.close()` it
  answers `RuntimeError: Cannot lazy load the requested data`, which is why
  `tests/support/caseTrees.py` releases its source through `request.addfinalizer`
  and why `QVizDBEntryRegistry.release()` forgets the lazy handles only once the
  entry is closed (`cache_ids(..., lazy=True)` records which ones). And a lazy IDS
  is **read-only** to IMAS-Python: `put(lazy=True)` answers `Lazy loaded IDSs
  cannot be used in put or put_slice` and `get(destination=lazy=True)` answers
  `Lazy-loaded IDSs are read-only`, so `QVizExportToIDS.wholeCopyOf` re-reads whole
  the IDS it is about to write instead of handing the lazy one over. The marker to
  ask is `ids._lazy`. To know whether a dataset holds anything without reading it,
  `DBEntry.list_filled_paths` answers the filled paths — **141** for `equilibrium`
  in **0,020 s** — but the tree is not built from it; the walk keeps its own rules.
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
- **the *File* menu belongs to the root window** — `QVizFileMenu` (T46) hangs
  `Save session` / `Load session ▸` / `Quit` (`Ctrl+Q`) on `QVizMainWindow.menuBar()`.
  Before it, the application window had **no menu bar at all** — the only menu bars
  in the package were a shot view's `Actions`/`Node Selection Actions`/`Plot windows`
  (`QVizDataTreeView.addMenuBar`) and the plugins' own — while the manual sent the
  user to `Actions → Save session` and `askForLastSession`'s log said "open it from
  the File menu": the two entries existed only on the start panel's right-click
  pop-up (`GUIFrame.showPopUpMenu`), under no title, and `updateMenu` no longer
  calls `menuSession`. Two things to keep: `Viz_API` is **not** a singleton
  (`QVizOpenShotView.__init__` makes one), so the entries are asked of the start
  window's controller through `QVizMainWindow.startMenuController()` — a controller
  of the menu's own would hold a second bookkeeping of the same windows and save an
  empty session; and the menu is refilled on `aboutToShow`, which means deleting the
  lines it is replacing — `QMenu.clear()` removes actions and **keeps the objects**,
  and a sub-menu parented on the menu (the only shape that survives, see T0/T7/T21)
  stays its child, so a refill that does not delete shows the same entries twice.
  Since T52 both that menu and the *Windows* menu answer it with the one helper,
  `VizGUICommands/VizMenusManagement/QVizMenuRefill.refill(menu)`; the *Windows* menu
  of the application bar hangs next to *File* (`QVizMainWindow.addWindowMenu`), and
  `Plot windows` is gone from the shot view, which hangs a *Windows* menu instead.

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
   `execute(vizAPI, pluginEntry, answers=None)` (receiving that same number, and the
   `QVizPluginAnswers` of a session restore when the entry is replayed), optional
   `getPluginsConfiguration()`, `getDescription()`. A plugin may gate on
   `self.selectedTreeNode.getIDSName()` against a `supported_idss` list — that is how the
   Equilibrium chart claims its one IDS — or claim every IDS root and ask the case what it
   holds, which is what `VizProfiles_plugin` does now: `isEnabled` is true for any IDS, and
   `execute` refuses by name when the occurrence it was handed is not in the case. Inheriting `VizPlugin` is not what puts a plugin in the menu: the
   catalog binds `setSelectedTreeNode(node)` **and** `setDataTreeView(view)` and asks the
   methods, so a plugin outside the hierarchy that honours them is offered like any other.
   The view binding is load-bearing and was missing for three slices: a plugin that reads
   `self.dataTreeView` — which is how `VizProfiles_plugin` asks the case which occurrences
   it holds — answered `AttributeError` on the first line of `execute()`, and the guard in
   `QVizPluginCatalog.run` reported it as `Plugin ... failed`, so the entry looked broken
   rather than unbound. A test that only checks "a failing plugin is named in the log"
   passes right over that; `test_43` now pins the binding itself. A window the plugin
   draws is in a session only if the plugin says so: it leaves a
   `QVizPluginWindow(uri, plugin, entry, ids, occurrence)` stamp on the frame it opened
   (`VizPlugins/VizPlugin.py`), and its `execute` must accept `answers` —
   `QVizPluginCatalog.run(entry, answers=)` reads the signature with `inspect` and refuses
   by name an entry that cannot be handed the answers, which is what a restore needs to
   skip the question the entry would otherwise ask (the Profiles occurrence question is a
   **modal `QInputDialog`**: measured, a probe sat in it **240 s**). A window the plugin
   shows itself is a third thing the plugin owes: it is not an MDI subwindow, so nothing
   routes its close box — the frame mixes in `QVizClosableWindow` and answers `windowApi()`
   with the api it is registered in, which is what makes that box hide the window and keep
   its key (or close it for good under `Close_button_deletes=1`) instead of leaving a window
   no *Windows* menu line can bring back.
2. Register the class in the `RegisteredPlugins` dict in `VizPlugins/VizPlugin.py`
   (`'PluginName': 'viz_<name>.PluginName'` — the class must bear the key's name, since
   that is what the catalog takes out of the module). Several entries are commented out —
   an unregistered plugin never loads, and a registered path that no longer resolves is
   refused in the log of the case without costing the other plugins. No submodule-provided
   plugin remains: the ETSViz submodule and `imasviz/VizPlugins/viz_ETS/` were removed on
   request, so `'ETSpluginIMASViz'` must stay commented out (an active entry would now
   raise `ModuleNotFoundError`). **That table is what IMASViz ships, and a plugin of the
   user's own does not belong in it** — see *Two origins* below. `registerPlugin`, which
   used to write into it at run time, is gone: a catalog is built once per shot view, so a
   plugin injected that way was on one view's menu for ever and on no other's at all, and
   it made a shipped name look editable when nothing in that table is.
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

### Two origins: what IMASViz ships, and what this user wrote

`VizPlugins/QVizPluginSource.py` owns the difference, and the whole point of it is what
may be **written**. A plugin is either `builtin` (the `RegisteredPlugins` table, code
under `$VIZ_HOME/imasviz/VizPlugins/`) or `user` (a folder of their own,
`$HOME/.imasviz/plugins`, next to `preferences` and the `.pcfg` files). `writable` is
`origin == USER` and nothing else, so the three places the boundary is answered cannot
disagree: the editor's text area, the *Edit* line of the Plugins sub-menu (not drawn at
all for a shipped plugin — `QVizPluginMenu.editable`), and `writeSource`, which refuses the
write whatever asked for it. Reading a shipped plugin is useful only if changing one starts
from it, so `copyIntoUserFolder` takes its **whole folder** — sub-packages included,
`__pycache__` left out — renames the module to the class name and rewrites that identifier
across every file it copies (measured for `VizProfiles_plugin`: the copy carries **3**
files — the entry module and the two of its sub-package — and rewrites the name in **1**
of them, because since the panel replaced the plugin's own grid only the entry module
spells `VizProfiles_plugin`; `test_82` pins both numbers and compiles every file of the
copy), and returns the
copy plus the files it touched; the file is renamed **before** the words are rewritten, or
the answer names paths that no longer exist.

What is in the user's folder is **found by looking**, not registered: a folder counts as a
plugin when it holds a module declaring a class of that module's name, read off the
*source* with `ast` (`declaresClass`). Listing must not import — importing is where the
cost is (the shipped set alone is where matplotlib comes in). A file that no longer parses
is still listed: the plugin the user broke in the editor is the one they most need to
open, and the catalog is where it is refused, by name. A name is a folder, a module and a
class at once, so `checkPluginName` refuses what is not an identifier and what IMASViz
already ships; `pluginNameFor` is the **one** spelling rule, asked by the creator and by
*copy into my plugins* alike (two rules is how a plugin ends up with a module whose class
has another name — the one thing the scan cannot read).

A user plugin is imported under a **synthetic package**, `imasviz_user_plugins`, a module
object with a `__path__` — not a `sys.path` entry, which is process-wide and already
mutated at import time here. One package name gives every plugin a stable import name,
which is what a reload needs: `forgetUserModules()` drops the whole subtree, the folder's
own package with it (`importlib.reload` of one module leaves its siblings and the parent's
cached attribute alone, so a deleted plugin would never be forgotten at all).

Four modules carry the feature: `QVizPluginSource` (the boundary and the disk),
`QVizPluginEditor` (a `QPlainTextEdit` with line numbers — every refusal IMASViz answers
about a plugin names a line), `QVizPluginManager` (the table of both origins, opened from
*File → Plugins...*, with `New plugin…`, `Read…`/`Edit…`, `Copy into my plugins…`, `Reload
now`, `Delete`), and `QVizPluginWatcher` (the hot reload, held by `QVizMainWindow` as
`pluginWatcher` — one instance per session, not per view). `File → New plugin...` and
`File → Plugins...` are two of the `QVizFileMenu` entries. `createPlugin` writes into the
user folder, and its template draws through `QVizPlotOneNode` — the same command the tree's
*Plot* gesture uses — so the first click on a freshly created plugin puts a real figure in
the MDI area instead of printing.

**What a reload does and does not do**: `QVizPluginCatalog.reload()` puts one view back to
the disk, `reloadEverywhere(api)` every open view (and answers how many, because a reload
nobody can count is a reload nobody believes); the sub-menu is rebuilt on every right click,
so no Qt menu surgery is needed. A window a plugin already opened is **not** re-drawn, and
a shipped plugin is never re-imported mid-session (two copies of its classes, with
matplotlib bound to both, is how a session ends up with figures that refuse each other).
Three `QFileSystemWatcher` facts decided the watcher's shape, measured on this Qt: an
in-place save is **one** `fileChanged`; a save by rename (vim, emacs) is **two** signals —
a `directoryChanged` and a `fileChanged` naming the *old* path — and afterwards the file is
**no longer in `files()`**, so `watch()` has to run again after every flush; a file that
appears announces itself **only** as a `directoryChanged`. Hence one debounce timer
(`DEBOUNCE = 300` ms) and a `compileCheck` **before** anything is replaced: a half-typed
file costs its own entry — named in the log of every open case with the line that stopped
it — and the module that answers the menu today stays.

Two PySide6 6.6 facts found the hard way while wiring this: `QFileSystemWatcher` is in
`QtCore`, not `QtWidgets`; and `QPlainTextEdit::viewportOffset` — the method every Qt
line-number snippet calls — is **protected in C++ and not exposed** (`hasattr` answers
False; `contentOffset` is the one that exists). Asking for it raised inside a paint event,
which left the paint device open (`QPaintDevice: Cannot destroy paint device that is being
painted`) and killed the process in a **later** paint event, in another window, with
nothing in the traceback naming the file at fault — so `paintLineNumbers` ends its painter
in a `finally`.

`test_imas_viz_plugin.py` instantiates a plugin with a hardcoded `dictDataSource`
(shot 50642, `west_equinox`) and calls `execute()` directly — the pattern for exercising a
plugin without the full GUI. `tests/test_43_plugins_in_the_menu.py` drives the menu
instead, with stub plugins registered through a fake module in `sys.modules`.

**Two** plugins are registered (`VizPlugin.py:32-36`), and both are run end to end on
the reference case by `tests/test_51_*` and `tests/test_85_*` (Profiles),
`tests/test_69_*` (what a session does with a Profiles window) and `tests/test_53_*`
(Equilibrium).
The Equilibrium one (`viz_equi/equilibriumcharts.py`, **1 253 l.**, author J. Morales) is
the only matplotlib window in the application: it does not draw through the axes model, so
it is registered under its own `FigureTypes.EQUILIBRIUMPLOTTYPE` (`EquiPlotView:`) — a
**6th** `MENU_ORDER` kind, so a line of the *Windows* menu and one of its *Delete*
sub-menu reach it — and it registers **no**
node in `figToNodes`, which is why the "add this quantity to that figure" entries do not
offer it. Measured facts worth keeping: it reads **occurrence 0** and does not ask (the
Profiles panel, which offers every occurrence the case holds, carries that choice as a
combo on its own window); its window is parented to the shot view and is **not** an MDI
subwindow (`mdiWindowOf` answers `None`), so it goes
with the view it came from; **6,73 s** cold for the first run of a process, **0,98–1,45 s**
once the IDS is in memory. And `QVizPreferences.Ignore_GGD` does **not** cover the plugin's
own `get`: with the GGD walk of the tree reactivated, the same case cost **287 s** in a
probe, which is why `test_53` pins that preference at **1**. Because that window is shown
by the plugin and not embedded, its close box is routed by the frame itself: `PlotFrame`
mixes in `QVizClosableWindow` and answers `windowApi()` with a `weakref` to the api it is
registered in, so its box hides it and keeps its key like every other window's.

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
python3 -m pytest tests/ -q     # 1461 passed, 1 xfailed, 12 warnings, ~13 min, offscreen
```

Two uncontended runs of the same tree (T50) agree at **874,27 s** and **875,65 s**;
the run that closed T52 answers **797,34 s** for **1461** ids, against the **794,17 s**
for **1429** ids the T51 row recorded — 32 ids more for the same wall time, so the
menus and their stand-in frames cost nothing measurable. ~13 to ~15 min is what this
suite costs on this node right now. Wall time belongs to the node (AFS, other tenants),
not to the tree: quote it with its date, and never explain it without measuring.

`tests/conftest.py` sets the whole environment (`VIZ_HOME`, `VIZ_PRODUCTION`,
`IMAS_VERSION`, `QT_QPA_PLATFORM=offscreen`, …) at conftest
import time, **before** any test imports `imasviz` — which is mandatory, because
`QVizGlobalValues` and `QVizGlobalOperations.checkEnvSettings()` can `sys.exit()`.
Markers: `ui`, `dd`, `case`; `timeout = 180` caps every test. The 1
`xfail(strict=True)` entry is an environment limit, listed in `TESTING.md` §4.

`pytest.ini` carries one `filterwarnings` line, narrowed to
`matplotlib.backends.backend_qt`, and its comment says why: that module asks Qt
for the deprecated `AA_UseHighDpiPixmaps` attribute **every time it is asked for
an icon pixmap**, and `QApplication.setStyle`/`setStyleSheet` re-polishes every
live widget — so a test that dresses the application while another file's
matplotlib toolbar is still alive collects one warning per icon per dressing
(**1940 warnings** on such a run before the filter, **0** from the same file run
alone; a real session dresses the application once, before any plugin window
exists). Anything raised from IMASViz's own code still shows.

The suite runs on **one numpy generation and the tool has to survive the other**.
Measured here: the module stack brings numpy **1.26.2**
(`SciPy-bundle/2023.11-gfbf-2023b`) and `~/.local` holds **2.4.6**, with the module
paths winning `sys.path` — so every case test, every plugin and every plot of this
suite runs on NumPy 1, and a name only NumPy 2 refuses is invisible to all of them.
That is how the Equilibrium overview plugin died in the field: `np.dtype((np.unicode_,
12))` answers `<U12>` under 1.26.2 and raises `AttributeError` under NumPy 2, and every
test that ever drove that plugin passed. The suite **cannot** be moved onto numpy 2 here
to watch it fail — forcing `~/.local` first makes `import imas` die in scipy with
`numpy.dtype size changed, may indicate binary incompatibility`, the Access Layer being
compiled against numpy 1. `tests/test_78_*` is the guard: an AST walk of every source of
the package (following `import numpy as np` and `from numpy import x` alike) against a
table of names measured present on NumPy 1 and refused on NumPy 2, the far generation
read in a subprocess and the table's own recommendations checked on both sides. Two
asymmetries worth knowing before editing that table: `np.float_` is refused by NumPy 2
and answered here — the canonical-looking spelling, and the shape of answer numpy's own
message suggests — while `np.bool` is refused **here** (removed in 1.24, with a
`FutureWarning`) and answered by NumPy 2, where it names the scalar type.

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
- A plain-Python helper stored on a Qt widget may not keep a **bound method** of that
  widget. `QVizCurvePlot` owns `QVizCurveErrors`, and that object has to ask the frame
  which curve came from which node; handing it `self.errorQuantities` — a bound method,
  so a strong reference back — makes a cycle, so the frame is freed by the **cyclic
  collector** instead of at its refcount, and on this stack a Qt widget freed there is
  freed while Qt still owes it a paint event: `Fatal Python error: Segmentation fault`
  under `Garbage-collecting`, in whichever file happens to call `gc.collect()`
  (`tests/test_44_plot_frame_ownership.py` died 2 runs in 2, and passes 3 in 3 without
  it). The shape to write instead is what T25 wrote: pass the owner and hold it through
  `weakref.ref`, answer `[]` once it is gone. `test_58`'s last test pins it —
  `weakref.ref(frame)()` answers `None` the moment the last reference goes.
- Two pytest runs of this suite **at the same time** are not two independent runs: they
  read the same reference case over AFS and one of them stalled past a 20 min `timeout`
  without printing a summary, in a position that had nothing to do with the code under
  test. One run at a time; when a run dies with no summary, check for a concurrent one
  before believing a hang (`-o faulthandler_timeout=45` is the flag that names a real
  hang — `--faulthandler-timeout` is not an option of this pytest).
- A curve figure's slice indices are **per trace**, not per figure (T35), and a plot
  entry draws an **element**: the arrays of structures the tree node stands on are
  pinned to the indices that node carries and written into the legend
  (`magnetics.flux_loop[3].flux.data`), so no control exists for them — only the leaf's
  own coordinate keeps one. The tensor representation is a **separate entry**,
  *Explore this tensor along \<axis\>* (`QVizPlotOneNode(tensor=True)`), which puts a
  slider on every axis the curve leaves out, opened on the indices the tree stood on,
  with *Keep this curve* freezing a trace so a family can pile up. There is **one such
  entry per abscissa** — `Explore this tensor along time axis`, `… along psi`,
  `… along its index` (`QVizCurveAbscissa.axisPhrase`) — because which arrays are left
  out depends on the axis the curve runs along: along time a quantity of the dynamic
  array has **nothing** to explore, so only the second heading exists for it. Each
  heading takes **its own** abscissa to the read (`exploreTensorCommand(alongTime=)`);
  measured before T41, a heading that only *named* an abscissa while the command was
  asked with no opinion opened a figure along the clock under a title saying `psi`. It
  is answered by `QVizSignalHandling.menuExploreThisTensor(parentMenu)` and hung at the
  **pop-up's top level**, right after the two single-curve entries (T37) — not inside
  `Plot <node> to → Figure`, where it sat below the list of figures it may join
  while it answers a different question than "which window". Since T38 each is a
  **sub-menu**: `New`, then one line per open figure drawn along that abscissa whose
  sliders are those very arrays (`exploreTensorCommand(intoFigureKey=)`). Since T41
  there are several, held in `self.exploreTensorMenus` — the single `exploreTensorMenu`
  of T38 could only ever name one abscissa.
  A Qt fact came with it: `QMenu(title, parent)`
  only sets the Qt **parent** — nothing hung it on the pop-up, and a QMenu no Python
  reference holds dies with the wrapper that made it (the dangling submenu T0 removed);
  `parentMenu.addMenu(menu)` is what makes it appear.
  Beside its abscissa a curve figure now keeps **the arrays its band walks**
  (`QVizCurvePlot.walkingArrays`, settled by the first tensor asked into it), and one
  pure function — `QVizCurveAbscissa.axesLeftOut` / `arraysLeftOut` — is the **mirror of
  the read** for that: `QVizTensorDataAccess._plottedPositions` / `_timeAxis` delegate to
  it, `QVizNodePlotting.tensorAxes(abscissa)` asks it, `QVizCurvePlot.accepts(treeNode,
  tensor)` answers it, and `Viz_API.figureDrawsSameCurveAxis(figureKey, treeNode,
  tensor=)` relays it. The rule is **narrower than it looks**: it applies to a tensor
  entering a figure and to a figure that already has a band, **not** to two plain
  elements — those still share only the abscissa (T36), which is what lets a flux loop
  and its neighbour probe be compared; the first cut asked the arrays of every trace and
  turned 4 tests red. An element added to a tensor figure is **frozen on all its axes**
  (no control, `isFrozen()`, its legend spelling the whole index set). Do not "restore" a
  control for a pinned AOS on a plain plot entry: measured before the change, that
  shared dict made
  two elements of one array answer **identical samples** (`flux_loop`, 17 filled
  elements of 17 344 samples). Two facts to keep when driving this: an AOS index is read
  back under its **level's** letter (`QVizGlobalValues.indices[level]`), not the letter
  spelled in the parametrized path — a stub writing `foo.ion[j]` for a level-1 array
  answers `axis.index is None` — and a curve figure's band **folds** to one summary line
  (`QVizSliceControls(foldable=True)`), while an image window and a table panel stay
  unfolded because there the rows are the only place saying which slice is drawn.
- A Table Plot View asks the width of its grid **once for the table**, from how many
  panels it holds (`QVizTablePlot.layoutTable` → `columnsFor(len(self._panels))`), and
  lays the panels on that grid — never one panel at a time against a width read for
  that panel. Asked per arrival it answered 1, then 2 until the fifth, then 3, while the
  row came from the panel count: measured on a 15-panel table, **14 cells for 15
  panels**, row 0 holding only (0,0) and (0,1), cell **(1,1) holding two panels**, (0,2)
  never filled. `QGridLayout` accepts two widgets in one cell **without a word of
  warning** — no exception, no Qt warning — so the only symptom is what the user counts
  on screen. What keeps the two answers together: `panelsInTable()` reads the layout,
  and `getPlotItemsDict()` reads it through that, because recomputing the places from
  the panel count wrote a `.pcfg` naming (0,2) where no panel sat and (1,1) once for
  two panels, and re-applying such a file laid the overlap again. A quantity the read
  refuses costs its panel **and takes it back** (`plot()` draws before it keeps the
  panel, and calls `deleteLater()` on the refusal): a `QVizPanel(self)` that no layout
  owns stays visible on the window, over the panels that were accepted. In the file, an
  absent place is **no attribute** — the reader turns a missing `row` into a missing
  place, so writing `str(None)` made the file unreadable (`invalid literal for int()
  with base 10: 'None'`) and that entry drew nothing. `tests/test_65_*` pins all of it
  on stubs, the 15- and 16-panel shapes cell by cell.

## Verified in situ (ACH/Gateway module stack)

Checked on this machine with `module load ach-modules` + `PySide6/6.6.2-GCCcore-13.2.0` +
`IMAS-Python/2.3.0-foss-2023b` + `PyQtGraph/0.13.7-foss-2023b`:

- `imas`, `PySide6` (reports **6.6.3**), `pyqtgraph` (0.13.7), `numpy`, `matplotlib` all import.
- Import sweep of the `imasviz` package (skipping `VizExamples/` and standalone scripts):
  it walks **114** modules and **113** of them import. The one failure is Qt-Designer
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
  directory with it — that directory held no `__init__.py` and nothing else. T25 added
  **1**: `VizGUI/VizPlot/QVizCurveErrors.py`, the error bars and the confidence band of a
  figure's curves, which the curve frames and the Profiles plugin now share instead of
  each carrying a copy. T33 added **1**: `VizGUI/VizPlot/QVizCurveColors.py`, the palette
  of trace colours a curve figure hands out in the order the traces were drawn — pyqtgraph
  hands out none of its own, see the colour bullet below. T40a added **4**:
  `VizGUI/VizConfigurations/QVizSessionFile.py` and the `VizGUICommands/VizSession/`
  package (`__init__`, `QVizSaveSession`, `QVizRestoreSession`); T40b added **none** —
  version 2 of the session format lives in the module that owns version 1, and the last
  session is written and read by the two commands T40a created, from `QtVIZ_GUI`. T40c
  added **none** either: version 3 of the format, the `QVizPluginWindow` stamp and the
  `answers` argument all live in modules the sweep already walked, which is why the
  sweep answers **114** modules and **113** imports after both tasks. T43 added **1**:
  `VizGUI/VizPlot/QVizPlotStyling.py`, the *Configure Plot* entry of every window that
  draws curves, the record of **which** traces and labels a hand touched, the two
  readers/writers of a pen and of a label, and the window-level
  `sourcesOf`/`styledTraces`/`styledText`/`replayCurves`/`replayText` a session asks of
  a window — so the sweep answers **115** modules and **114** imports. T44 added **2**:
  `VizGUI/VizPlot/QVizColourScales.py` (the colour scale of a picture window — one map
  and one level range for all its pictures, the `viridis` default, the derived
  `rounding`, the swatch a chooser paints, and the record of whether a hand was on
  either) and `VizGUI/VizPlot/QVizColourScaleUI.py` (the *Colour Scale...* dialogue),
  so the sweep answers **117** modules and **116** imports — measured with
  `python3 -m pytest tests/test_99_import_sweep.py -q`, which prints **118 passed, 1
  xfailed** for those 117: two of the passed ids are `test_the_walk_finds_the_package`
  and `test_known_unimportable_list_is_not_stale`, not modules, so the module count is
  the id count minus two. T45 added **none** — the colours of a cut live in
  `QVizSliceLines`, the module that already owns the lines. T46 added **1**:
  `VizGUI/VizGUICommands/VizMenusManagement/QVizFileMenu.py`, the *File* menu of the
  application window (the session entries, the way out, and the refill on
  `aboutToShow`) — so the sweep answers **118** modules and **117** imports,
  measured with `python3 -m pytest tests/test_99_import_sweep.py -q`, which prints
  **119 passed, 1 xfailed** for those 118. T47 added **none** — the house style of
  the manual is a `.css`, a `.js` and an `.svg`, not a module. T48 added **1**:
  `VizGUI/VizGuiCustomization/QVizStyle.py`, the theme of the application (the two
  palettes, the palette a Qt style paints from, the style sheet that paints what a
  palette has no role for, the font resolution, the log colour, the window mark),
  so the sweep answers **119** modules and **118** imports — measured with
  `python3 -m pytest tests/test_99_import_sweep.py -q`, which prints **120 passed,
  1 xfailed** for those 119. T49 added **none** — the fix is one numpy name inside
  `viz_equi/equilibriumcharts.py` and its guard lives in `tests/`, so the sweep still
  answers 119 modules and 118 imports. T50 added **none** either — the sizes are
  constants of `QVizStyle.py` and one call in `QVizDataTreeView.py`, both modules the
  walk already took, and the guard is in `tests/`; still 119 modules and 118 imports.
  The plugin creator of the pass before this one added **2** (`VizPlugins/create_plugin.py`
  and `VizPlugins/QVizPluginCreatorDialog.py`), and this one adds **4**:
  `VizPlugins/QVizPluginSource.py` (where a plugin comes from, and whether it may be
  written), `VizPlugins/QVizPluginEditor.py`, `VizPlugins/QVizPluginManager.py` and
  `VizPlugins/QVizPluginWatcher.py` — so the sweep answers **125** modules and **124**
  imports, measured with `python3 -m pytest tests/test_99_import_sweep.py -q`, which
  prints **126 passed, 1 xfailed** for those 125. The first step of the Profiles
  rewrite adds **1**: `VizPlugins/viz_Profiles/viz_profiles/QVizProfileOffer.py`, what
  one IDS of one case can be drawn as, read off the tree that case built instead of
  listed by hand — so the sweep answers **126** modules and **125** imports, measured
  the same way, which prints **127 passed, 1 xfailed**. The second step takes **5**
  out and puts **1** back: the plugin's own figure island (`viz_profiles/VizProfiles.py`,
  `QVizTablePlotView.py`, `CustomizedViewBox.py`, `tabQt.py`, `menu.py` — 5 files that
  drew a grid the rest of the application could not see) goes, and
  `viz_profiles/QVizProfilePanel.py` replaces it — so the sweep answers **122** modules
  and **121** imports, measured the same way, which prints **123 passed, 1 xfailed**
  (two of those ids are `test_the_walk_finds_the_package` and
  `test_known_unimportable_list_is_not_stale`, not modules). The *Windows* menu of T52
  adds **2** — `VizGUICommands/VizMenusManagement/QVizWindowMenu.py` (the one menu, hung
  by both bars) and `QVizMenuRefill.py` (the refill that does not leave its sub-menus
  behind) — so the sweep answers **123** modules and **122** imports, measured the same
  way, which prints **125 passed, 1 xfailed**.
  Note that
  the sweep skips `test_*.py` by name, which is why the demo
  `viz_equi/test_equilibriumcharts_plugin.py` (59 l.) was never in that count and its
  removal costs no test. It collects the modules and parametrizes on them, so a new
  module costs four more ids and no counter anywhere.
- **The application wears a theme, and it is the manual's palette** (T48).
  `VizGUI/VizGuiCustomization/QVizStyle.py` holds both of them (`light`, `dark`),
  **19** colour names each, byte for byte the `tokens:begin` block of
  `doc/source/_static/imasviz.css` — `test_77` refuses the drift token by token and
  pins that `FONT_FAMILIES` is the head of the CSS `--font-sans`. `QtVIZ_GUI.main()`
  calls `QVizStyle.applyToApplication(app)` after `QVizPreferences().build()` and
  before `QVizMainWindow()`; the theme is the `Theme=` line of
  `$HOME/.imasviz/preferences`, `light` by default, chosen at start-up — there is no
  live switch, on purpose, because every colour on screen is read against the ground
  a theme moves. Three measured Qt facts decide the shape: `QStyleFactory.keys()`
  answers `['Windows', 'Fusion']` here and the `Windows` style ignores most of what a
  palette is handed, so `Fusion` is asked first; once a style sheet is set,
  `app.style()` is a `QStyleSheetStyle` whose `objectName()` is the **empty string**,
  so the style can only be recognised through a metric it delegates
  (`PM_ScrollBarExtent` **14** where Windows answers **16**, `PM_MenuPanelWidth` **0**
  where it answers **2**); and a `QMdiArea` paints its **own** ground from
  `QPalette::Dark`, read **once at construction** — a `background` rule in a style
  sheet never reaches it, and a palette changed after the widget exists does not move
  it either (`setBackground` does). Measured: `#9f9f9f` (Qt's stock derived grey)
  before, `#eef1f3` light / `#0f1317` dark after `paletteFor` named `Dark`. A fresh
  `QPalette` whose `Window` is set still answers `#9f9f9f` for `Dark` — derived roles
  are **not** recomputed from the colours you set. Two sheet rules that measured
  false were dropped for this reason (a `background` on `QMdiArea`, and
  `QStatusBar#statusbar`, an id the main window's bar does not carry); a rule that
  matches nothing is worse than no rule, because the next reader believes the colour
  is on screen. `titlebar-close-icon: none` went too — it removes the button that
  closes a dock.
- **A theme never reaches a plot.** No rule of `styleSheet` names a `QGraphicsView`
  and none names `QWidget` with a `background`; a pyqtgraph figure answers
  **`#000000`** under either theme (measured, and pinned by `test_77`), which is what
  keeps the trace palettes (T33/T34), the colour maps (T44) and the slice-line colours
  (T45) true. The chrome it does paint, per theme: tree `#ffffff`/`#181d22`, header
  and menu bar `#f7f9fa`/`#141a1f`, selection `#bfe3ea`/`#22505a`, input
  `#f4f7f8`/`#12171b`, log `#f6f8f9`/`#12171b`, the body of a sub-window
  `#ffffff`/`#181d22` inside a 12 px band of `line` (`#dde3e7`/`#2a333a`) — since T50
  the title bar of that window is **not** in the list: Fusion paints it from the
  palette (measured `#c9ecf3`-class tint in the light theme). `QWidget.grab()`
  renders a widget that was never `show()`n, which is how a theme test samples pixels
  without entering the paint-queue hazard `tests/support/ownership.py` exists for.
- **A style sheet takes over the subcontrol it names, and then the geometry of the
  control comes out of the rule** (T50). The report came from a tablet: a figure
  window could no longer be resized by its corner, and the data tree showed no arrows.
  Both were the T48 sheet's doing, and neither was a colour. `QMdiSubWindow` hit-tests
  its own frame with `QStyle.PM_MdiSubWindowFrameWidth`, and a style sheet answers that
  metric with the width of the `border` it declares: measured **4** with no sheet,
  **1** with the `border: 1px` the sheet carried, and exactly the declared number
  otherwise (8/12/16 all honoured). `QTreeView::branch { background: … }` with no
  `image` draws **no** branch indicator at all — 20 px of arrow with no sheet, 20 with
  the rule deleted, **0** with it, and **0 even when the rule carries an `image` that
  cannot be read** — and the colour it set (`surface`) was the ground the view already
  had. `QMdiSubWindow::title` stopped Fusion drawing the reduce/restore/close buttons:
  the 72 px at the right end of the bar answers **2** colours dressed, 23 light / 28
  dark undressed, and `PM_TitleBarHeight` fell 24 → 20. So the sheet now declares the
  band it wants and names neither the branch nor the title (`QVizStyle.POINTER` =
  `WINDOW_FRAME` 12, `SCROLL_BAR` 20 — style default 14, sheet of T48 12 — `SPLITTER`
  14 — rendered 14 although `PM_SplitterWidth` still answers 4 — and a tree row 26 px
  at the house font where T48 answered 20). `TREE_INDENTATION` 28 is **not** a QSS
  number: `QTreeView` reads it from `setIndentation`, so `QVizDataTreeViewFrame` asks
  `QVizStyle.TREE_INDENTATION` itself. `test_77` refuses the two rules by shape (a
  `QTreeView::branch` rule must carry an `image`; no rule may name `QMdiSubWindow::title`)
  — and that guard strips `/* */` comments before scanning, because the sheet *explains*
  both removals in prose that spells the two names out: with the comments in, it matched
  the sentence about the branch and read the body of the next real rule as its own. Two
  things to keep: a colour on screen is not a control under the hand — `test_77` pinned
  the colours of exactly these three subcontrols and none of their affordances — and the
  sizes are identical in both themes (measured, light and dark, one table): band
  1 → 12, bar 12 → 20, handle 4 → 14, arrows 0 → 20 px, row 20 → 26, indentation 20 → 28.
- **Naming a font is not getting one, and one bad preference line is not a stop.**
  `GlobalFonts` named `'Open Sans'` on all four of its fonts; `QFontInfo` answers
  `DejaVu Sans` for that name here. `QVizStyle.resolvedFontFamily()` asks
  `QFontInfo` over `FONT_FAMILIES` and returns the one that answers for itself —
  **Cantarell** on this node — at `POINT_SIZE` **10**, and `GlobalFonts.useFamily()`
  rebuilds the four on it (sizes and bold flags kept) in the same call that dresses
  the application. On the same path: `build()` is called by `main()` with nothing
  around it, and the two colour options were read with `int(text)` while the manual
  documents `Nodes_selection_colour=#ff0000` — the file the manual tells you to write
  raised `ValueError` and the run died before a window appeared. Each line answers for
  itself now (`QVizPreferences.colour` reads a hex with or without `#`, a Qt colour
  name, or the index **1..6**; `theme()` asks `QVizStyle` and names what was *typed*),
  the value is named in the log panel, and the rest of the file is still read.
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
  screen (**10** tabs and **191** quantities for `equilibrium` occurrence 0, and the same
  entry offered for `core_profiles`, `magnetics` and `wall` — the two last of those never
  had a line, because the read that panel used kept only what it called dynamic). Two
  measured defects stood in the way when that file was written, and both went with the
  code that carried them: labelling the old window's time slider formatted a 0D time node,
  which on IMAS-Python is an `IDSFloat0D` — a `numbers.Real` wrapper with `__float__` and
  **no `__format__`** — so `f"{tmin:.2f}"` raised
  `TypeError: unsupported format string passed to IDSFloat0D.__format__`
  (`VizProfiles.py:504`) inside `setUI`, leaving everything under the tabs unbuilt (the
  Equilibrium plugin had the same defect in its own label, and still guards against it);
  and `CustomizedViewBox.getMenu` walked `self.menu.leftMenu`, which pyqtgraph **0.13.7**
  does not keep (the actions are in `ViewBoxMenu.mouseModes`), so the right click on a
  plugin plot answered `AttributeError` before the menu opened. That island — the plugin's
  grid, view box, tabs and page arithmetic — is gone: the panel names quantities and
  `QVizPlotAsTable` / `QVizPlotOneNode` draw them, so what the plugin puts in
  `figureframes` is one `PlotView:` window of its own plus the `TablePlotView:` and
  `SlicesPlot:` figures its clicks ask for.
  What is **no longer** true of it: the occurrence question is not a **modal
  `QInputDialog`** any more — that dialog is what a probe left alone for **240 s** on this
  case, and it is a combo bounded by the case now, which a session restore answers in the
  user's place. A test asserts the absence (`not hasattr(profilesPlugin, 'QInputDialog')`)
  rather than patching the dialog. And a plugin window is still registered like a figure
  (`PlotView:1` in `figureframes`) but is a **top-level** window: measured
  `parent() is None`, never embedded in the MDI area.
  The gestures inside that window run `QVizPlotOneNode` like every other gesture,
  so the frames they build are `SlicesPlot:` figures in the MDI area, and the
  "add this quantity to that figure" gate lives on `Viz_API`
  (`figureDrawsSameCurveAxis`, which since T36 asks **the frame** — `figureframes`
  and the abscissa it carries — and no longer re-walks the `figToNodes` record)
  where the shot
  view's menu and a plugin's view box ask the same question. The plugin no longer carries
  any error-bar behaviour of its own: `QVizCurveErrors` is owned by the curve frame alone
  (`test_58` pins it), so a panel of a Table Plot View — which is what a Profiles page is
  — answers *Configure Plot* and **no** error-bar line, and the error fields the offer
  counts reach their bars through *Draw the selected quantity*.
  A curve figure answers those three lines too: its right click goes from pyqtgraph's
  **4** entries to **7**, and since T43 `Configure Plot` is **not** plugin-only any more:
  row T32 of `LEGACY_REPLACEMENT.md` is answered on every window that draws curves — the
  curve figure (whose right click then answers **8** lines), each panel of a Table Plot
  View, each display of a Stacked Plot View — by `VizGUI/VizPlot/QVizPlotStyling.py`,
  which owns the entry, the record of **which** traces and labels a hand touched, the two
  readers/writers of a pen (`curveStyle`/`applyCurveStyle`) and of a label
  (`textStyle`/`applyTextStyle`), and the window-level `styledTraces`/`replayCurves`/
  `styledText`/`replayText` a session asks of a window. `ENTRY` is spelled once in that
  module and hung by `QVizCurvePlot` and by `QVizPanel`, so a figure and a panel cannot
  drift apart in spelling — and since the plugin's own view box is gone, there is no third
  place it could.
  That dialogue **asks** its caller and does not name it: the view box answers
  `styleCurves()`, `styleText()` and `styleMargins()`; for a panel, `styleMargins()`
  delegates to its frame, and `QVizTablePlot.styleMargins()` and
  `QVizStackedPlot.styleMargins()` answer the **one** grid their panels live in — never one
  answer per panel, the same reason `layoutTable` asks its width once. A curve frame answers
  `None`, so it gets no margins section. (The window that used to answer it was the Profiles
  plugin's own grid; deleting that left the section with no caller, which is how the two
  methods came to exist.) T43 added a fourth
  question, `tracesForStyling()` answering `[(treeNode, rank, curve)]`, whose `rank`
  ranks a trace among **its own quantity's** traces and not in the figure: a figure of two
  single-trace quantities holds two traces both at rank **0** — and the session keys a
  style by `(path, occurrence)` (`styleKey()`), never by object identity, because a Table
  Plot View fills its panels from a configuration file, so the node a panel holds is not
  the node the gesture named. An image window answers no such entry: it has no trace to
  dress, and the manual says so.
- **The Profiles panel is a list of quantities and three buttons, and every window it
  opens is one of the application's.** `viz_Profiles/VizProfiles_plugin.py` (entry, offered
  on **any** IDS root) → `viz_profiles/QVizProfileOffer.py` (what this occurrence can be
  drawn as, walked off the view's nodes: groups, pages, error fields, time bases) →
  `viz_profiles/QVizProfilePanel.py` (the window: occurrence combo, abscissa combo, one tab
  per array of structures, a page list, three buttons, one folded `QVizSliceControls` band).
  `drawQuantities` builds a `QVizConfigurationFile(kind=PLOT, quantities=[QVizQuantity(
  path, occurrence, None, None, uri)])` and hands it to `QVizPlotAsTable(configuration=)` —
  the in-memory seam the command already offered — so a page is a `TablePlotView:` key in
  the MDI area, a line of the *Windows* menu, styled by *Configure Plot*, put back by a session
  (`test_69` restores a page and reads `panelCount()` and `getPlotAxis()` back off it).
  `drawQuantity` is `QVizPlotOneNode`, which is how a quantity of two axes of its own
  leaves the panel and becomes a picture. Six things this panel does **not** do, and each
  is pinned where it is said:
  * it does not draw a page that read nothing: `QVizPlotAsTable.execute()` **raises**
    `ValueError: Nothing to plot: none of the quantities named gave a value along an axis
    a panel can draw.` and deletes the frame it had started, so the panel logs the sentence
    in the log of the case and answers `None` — no empty window (measured on `wall`
    occurrence 0: 22 quantities, 0 panels);
  * it does not invent an occurrence: the entry asks `view.occurrences.occurrencesOf(ids)`
    and refuses by name — `the opened case holds no occurrence 7 of the wall IDS: it
    answers 0.` — which is what a session file naming another one reads back;
  * it does not load asynchronously: the offer walks the tree that load builds, so the
    entry and `ensureLoaded` both ask `QVizLoadOccurrence(..., asynch=False)` (**0,6 s** for
    `equilibrium`);
  * it does not offer a cursor for an axis a window draws: the band holds the subset of
    `offer().timeBases()` that an open window's panels actually pin, and `magnetics`
    (`homogeneous_time = 1`) answers no base at all;
  * it does not carry the plugin's own view box, grid or palette any more, so a table
    panel answers *Configure Plot* and no error-bar line (`QVizCurveErrors` belongs to the
    curve frame, `test_58`), and its traces wear the one palette every other frame uses;
  * it does not write anything: like the rest of the read path it works on the **lazy**
    handles IMAS-Python hands back, which are read-only to `put` — the export command is
    the one that has to re-read whole (see the lazy bullet above).
  Measured on the reference case: `equilibrium` 0 **0,67 s / 10 tabs / 191 quantities / 536
  error fields**; `core_profiles` **0,30 s / 9 / 220 / 558**; `magnetics` **0,91 s / 4 / 21
  / 16**; `wall` **0,20 s / 4 / 52 / 96**; occurrence **2** adds a `profiles_2d` tab, **289**
  quantities, and the one group longer than a page (**111** in `time_slice/constraints` —
  drawing that page costs **45 s**, so `test_85` pins the paging at the list level).
  **Never draw a `constraints` page in a test.**
- **pyqtgraph 0.13.7 hands out no colour of its own**, so a figure cannot rely on it:
  `colorCycle`, `colorLists` and `currentColor` appear **0** time in the package, and a
  curve drawn without a pen keeps the instance default `opts['pen'] == (200, 200, 200)`
  (`graphicsItems/PlotDataItem.py:348`). Measured on the reference case before T33, the
  two traces of a figure holding `magnetics/flux_loop(0)/flux/data` and
  `magnetics/bpol_probe(0)/field/data` both answered `tuple(200, 200, 200)` — the same
  grey twice, for the one window whose purpose is a comparison. `QVizCurveColors` answers
  the pen of the index-th trace now, cycling through **8** colours. Two measured facts
  decide that palette: the ground those lines are painted on is **black**, and it is the
  *window* that paints it — `PlotWidget.backgroundBrush()` answers `SolidPattern
  (0, 0, 0, 255)`, from pyqtgraph's own configuration default (`'background': 'k'`,
  `pyqtgraph/__init__.py:45`), not from any IMASViz preference, of which there is none
  about colours. **Do not read `viewBox.background.brush()`**: that `QGraphicsRectItem`
  is hidden and its brush `NoBrush` unless `setBackgroundColor` was called, which nowhere
  in this package does, while its `color()` still answers `(0, 0, 0, 255)` — that reading
  reported the Profiles plugin's **white** window as black; and the confidence band of
  `QVizCurveErrors` is filled with `(255, 0, 0)` in `DiagCrossPattern`, which is why
  neither palette holds pure red.
- **There is one trace palette, because there is one ground.** The other ground used to be
  the Profiles plugin's table window — the only `setBackground` in the package (white,
  `QVizTablePlotView.py:75`) — and it justified a second palette: **5** of the 8 colours of
  the black list answer a contrast under **2,5** on white (cyan 1,25, chartreuse 1,30,
  spring green 1,35, gold 1,40, orange 2,33), where the light list's weakest answered
  **4,77**. That window is gone, its curves are drawn by `QVizTablePlot` panels on the
  black every other frame paints, and `LIGHT_CURVE_COLOURS` / `LIGHT_CYCLE` /
  `lightColourFor` / `lightNameFor` went with it. `test_61` keeps the reason alive in both
  directions: an AST walk of the package refuses any call named `setBackground` or
  `setBackgroundColor` (so a second ground cannot come back unnoticed), pins the weakest
  contrast of the shipped palette on black at **4,66** (violet, floor 4,5), and pins that
  the same 8 colours would fail on white — **5** of them under **2,5** — so the palette is
  known to be ground-specific, not merely "the house colours". Until T34 that window drew
  all **41** of its curves in `getRGBColorList()[0]`, one blue reached by walking
  `GlobalColors.__dict__` for attributes ending in `HEX` — **8** of those 18 answers are
  under a contrast of 2 on the white they were drawn on. The function and the eighteen
  `*_HEX` attributes are gone (`GlobalColors` itself stays: the tree, the preferences and
  the documentation panel ask its six brushes).
- **A picture window colours with one map and one range** (T44), and the library pieces
  that promise is built on were measured on `PyQtGraph/0.13.7-foss-2023b` before being
  wired:

  * `ColorBarItem.__init__` takes **`colorMap=`**, not the `cmap=` of the online
    documentation — the snippet on the project's own docs page is for a newer release;
    `rounding` defaults to **1 unit**, so dragging the handles of a quantity spanning
    `0,011 .. 0,023` answers `(0, 1)` and empties the pictures. It is derived here
    (`span/1000`, measured on the real radiance at **2,4e8**) with a `1e-12` floor for a
    flat picture, which the library divides the drag by;
  * `setImageItem` **accepts a list** (`img_list = [weakref.ref(item) for item in img]`,
    `ColorBarItem.py:194`) and **replaces** it on every call. Calling it once per
    picture — which is what this window did, on the reading that a bar answers one
    image — leaves it driving the last one, and that single defect is what the manual's
    "no `Configure Plot` on an image window" was covering: `colorMapMenu` is **True** by
    default, so the right click on the bar already opened the library's map list and
    recoloured one picture of three (`images luts [False, False, False]` before any map
    was picked);
  * with no `values`, the bar takes its levels off the one image it is bound to —
    measured `(0.0, 15.0)` beside a window whose scale is `(0.0, 215.0)`. The numbers
    next to the ramp were not the scale the pictures were painted against, which is the
    one question a colour bar answers. So the window settles `_levels` over all the
    pictures **before** drawing them and hands the bar `values=`;
  * `setLevels(values=(low, None))` accepts a hole — "Either value can be None to leave
    the previous value unchanged" — and **emits nothing**; one drag of the handles emits
    `sigLevelsChanged` **3 times**. `setLevels` also refuses a reversal by answering the
    **midpoint** of the two ends, which is why `low > high` is refused at the session
    file rather than handed down;
  * `ImageItem.setImage(data)` **re-fits the levels to that array** — a re-read of a
    20x20 slice answered `(0, 399)` over a window scaled to `(0, 215)` — so every
    repaint would undo a range the user set. `setImage(data, levels=…)` holds them,
    which is what `_drawPicture` does now; and the lookup table **survives** both
    `setImage` and `clear()`, so a chosen map does not have to be re-applied on every
    refresh (an earlier probe said otherwise, from an ordering artifact: it looked at a
    LUT that had never been set). `ImageItem` answers `setColorMap`/`getColorMap`/
    `setLevels`/`getLevels` and has **no** `sigLevelsChanged` — the bar is the only
    thing that moves a level;
  * `pg.colormap.listMaps()` answers **71** names here (`colors/maps/*.csv|hex`);
    `get(name, source='matplotlib')` resolves **182** more, which is what the library's
    own bar menu offers. An unknown name raises `FileNotFoundError` naming a path inside
    the package, so `mapNamed` refuses by the *name*. `ColorMap` answers `getGradient()`
    (a `QLinearGradient` of **256** stops — that is what a chooser's swatch is painted
    from), `getLookupTable()` and `getColors()`; there is no `getLut()` and no
    `length()`;
  * a `ViewBox` builds its `menu` in `__init__` when `enableMenu`, so each picture has a
    real `QMenu` to hang *Colour Scale...* on; the bar's own view box answers `menu is
    None`, because `ColorBarItem` calls `setMenuEnabled(False)` — its right click goes
    through `mouseClickEvent` to a `ColorMapMenu` built on the spot.
  The default is `viridis`: it ships here (CC0), it is uniform in perceptual distance,
  and it stays legible to a colour-blind eye. Like the curve palette, it is a property
  of **this node** and never written to a file by a window nobody dressed.
- **The cuts of a picture window are coloured by their side** (T45), and what made one
  invisible was read off the library before being fixed: `pg.mkPen(width=1)` with no
  colour falls back on `mkColor('l')` = **(200,200,200)** (`functions.py:58` with
  `:355-356`) — the very grey a curve drawn without a pen gets — while
  `QVizSliceLines` drew its live cut with `color='k'` **on the black ground** (the
  user's report: *the plot under the pictures is invisible*) and every kept record
  with that grey, so no two records told apart and none could be told from the curve
  it was copied from. `QVizCurveColors` answers it now: `colourFor(0)` on the bottom
  side, `colourFor(1)` on the left, worn by the line, its markers and the live curve —
  the colour is the only cue saying which line a panel answers, since the panel under a
  vertical line runs along the *other* axis. Kept records cycle from `colourFor(2)` and
  close after `CYCLE - len(SIDES)` = **6** colours, so a record never wears a live
  colour. Three library facts decide the shape: `InfiniteLine` with no pen takes
  **(200,200,100)** olive with a pure-red hover pen (`InfiniteLine.py:87-93`) — the
  lines were never the invisible part; `InfLineLabel` hands its options to `TextItem`
  and does **not** follow the pen of its line, so a coloured line keeps a white label
  (pin the pen, never the label); and `PlotItem.addItem` takes a legend entry from
  `item.name()` **as it adds** (`PlotItem.py:516-552`), so `addLegend()` has to precede
  the named `plot()` — which is why `keep()` asks for the legend there and then, and
  `removeItem` drops the entry with the curve (`PlotItem.py:595`). A legend row is a
  `(sample, LabelItem)` pair and its text is `label.text`, **not** `toPlainText()`
  (`LegendItem.py:215-221`); `plotItem.titleLabel` is the same shape.
- **A picture window is never freed at its refcount** (measured, and **not** fixed
  here): a bare `QVizImagePlot` — nothing plotted, no colour scale involved — stays
  reachable from the closure cells of `_makeSliceButtons` (`cad1c3c`, the two
  `lambda checked=False, side=side:` connected to the *Keep this slice* and *Add a new
  marker* buttons) even after `gc.collect()`. This is a **leak**, not the dangling-owner
  crash of the T25 rule: the window is never freed at all, so nothing is freed while Qt
  owes it a paint event. What it costs is that `test_58`'s behavioural ownership check
  cannot be run on this frame, and that every picture window opened in a session is
  retained to the end of it.
- **A curve figure has one abscissa, and it is an identity, not a spelling** (T36).
  `QVizCurveAbscissa` answers it once: `TIME` unifies the three ways IMAS writes one
  clock — the dynamic array (`IDS.time`), `<aos>/time`, bare `time` — and which one a
  case uses follows `ids_properties.homogeneous_time`, measured on the reference case
  as **0** for `equilibrium` and **1** for `magnetics`; a coordinate named by the
  dictionary is keyed by that name with the loop decoration (`(itime)`, `[itime]`), the
  slashes and the IDS root taken out; an axis left unbounded (`1..N`) is keyed by its
  **units**, because what the read draws under it is the element rank. The figure
  settles its abscissa on its first curve (`QVizCurvePlot.abscissa`, and each
  `QVizTrace` carries the one it was drawn on), the read follows it (`plan` /
  `GetSignal` / `slicesFor` take `abscissa`), the bottom label is put **from the
  abscissa, once**, and `Viz_API.figureDrawsSameCurveAxis(figureKey, treeNode)` asks
  the frame. Two things to not "restore": a key spelled off one quantity's axes
  compared against another's — measured to answer **False** for
  `profiles_1d.f` and `profiles_1d.psi`, one structure, both read along time — and a
  `plotAxis` string on the curve frame, which is what made the plain entry draw **101**
  points against `psi` where the manual's walkthrough of that very leaf says X is
  `equilibrium.time` (**49** points). `plotAxis` / `getPlotAxis` stay on the **table**
  and the **stacked** window, whose entries *New (default axis)* and *New ('TIME'
  axis)* are documented, and `isPlotToPerformAlongTimeAxis` stays for the **3** legacy
  label sites of `QVizTreeNode`. A quantity with **no axis of its own** (a scalar held
  by an array) has nothing to disagree with, so it takes the figure's abscissa and is
  spread over it, said in the log; refused on an empty figure.
  `abscissae()` answers TIME **first**, and that is the reading of every plain entry —
  which left the coordinate half of the model with no way in from the tree: the preview
  panel asked the read with `along_time=False` and drew the profile while the pop-up
  could not (T41). `QVizNodePlotting.coordinateAbscissae()` is the answer, and
  `QVizSignalHandling.actionPlotAsFunctionOfCoordinate()` hangs it as a third top-level
  line titled by `axisPhrase` — **Plot as function of psi** on
  `equilibrium.time_slice[i].profiles_1d.f`, **101** points where its neighbour answers
  **49** — refusing the line where the leaf has no abscissa but the clock, a coordinate
  that *is* a time base (`flux_loop[i].flux.time`) being the same axis spelled
  differently, not a second curve to offer. `test_70` pins both entries, on the stubs
  and on the case.
- The manual **is** built and checked here, with no theme override: `make doc` answers
  `build succeeded`, exit 0 and **0 warnings** over **21** source files (**3,87 s**, 23 pages),
  because the look is in the repository — `doc/source/_static/imasviz.css` over `basic`, with
  `imasviz.js` choosing light or dark (T47). `tests/test_76_the_manual_wears_the_house_style.py`
  (**24**) is the guard: it builds the manual in process through
  `sphinx.cmd.build.build_main` into a `tmp_path_factory` folder, with the warnings going to a
  file of their own (`-q` silences the console, not the complaints), and reads what came out — so
  it refuses a build that warns, a sheet that loads before `basic.css`, a token used but never
  declared, a colour pair under the WCAG 4,5 floor, the five pale values of the theme this sheet
  replaces, and a `conf.py` that asks a theme this node does not have. Its one measured wrinkle:
  Sphinx appends a content hash to every static href (`_static/imasviz.css?v=8a249c91`), which
  the first cut of the sheet-order assertion read as `'imasviz.css' is not in list`. Its output
  is throwaway: `make clean` takes `doc/build` back, and the test never writes there.
