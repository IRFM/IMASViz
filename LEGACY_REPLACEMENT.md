# Replacing the legacy plot path, one user command at a time

The reading layer is already unified: every IMAS source goes through
`QVizTensorDataAccess`, driven by the axes model (`QVizAxesSpec`), and the
`Tensor_based_reading` switch is gone. What is still legacy is everything the
user actually touches on the data tree: the **frames** a command fills, the
**commands** that fill them, and the **node model** those commands derive their
branches from.

This file is the work list. It is ordered by one criterion: **a task counts only
if it deletes legacy files behind it.** The "kills" column is what disappears
when the task is done; a task that kills nothing is a refactor, not a step.

Keep this file current: when a task changes rank or a file is deleted, update it
here, not only in the commit message.

## 1. Where the user can act

Three entry points, no others:

| Entry point | Code |
| --- | --- |
| Gestures on the tree (left click, double click, Return, right click, Shift+right click) | `QVizDataTreeView.onLeftClickItem`, `.loadDefaultOccurrence`, `.contextMenuEvent`, `.keyPressEvent` |
| The context menu on a node | `QVizSignalHandling.buildContextMenu` (:59), `QVizHandleRightClick`, `QVizHandleShiftAndRightClick` |
| The menu bar of the shot view | `QVizDataTreeViewFrame.addMenuBar` |

## 2. Defects found while taking the inventory

They motivate the rank of the task that owns them. The ones T0 owned are marked;
the rest are not fixed yet.

- **The new figures are unmanageable.** *(fixed by T0)* `QVizPlotAsSlices` keyed
  its frames `SlicesPlot*` / `SlicesImage*`, while `Viz_API.GetFiguresKeys`
  filtered `figureframes` by prefix against the five `FigureTypes`. So those
  frames were counted nowhere, could not be shown, hidden or deleted from any
  menu, and closing their MDI subwindow left them in `figureframes` — the
  count-based numbering then grew for nothing.
- **The Show/Hide and Delete submenus were being deleted under the menu.**
  *(fixed by T0)* All five branches built their submenus with
  `menu.addMenu('Figure')`. PySide6 keeps the `QMenu` that call creates under
  Python ownership, so it is deleted when the local variable goes out of scope at
  the end of `menusShowHideAndDelete` — the entry is there to look at and dangling
  to click. A submenu has to be built as `QMenu(title, parent)` and added with
  `addMenu(submenu)`.
- **A quantity of three axes got nothing at all.** *(fixed by T1)* The context
  menu branched on `is2D()` then on `not is2DOrLarger() and data_type !=
  'STR_1D'`. A leaf the dictionary ranks 3D matches neither, so right clicking
  `pow_fusion`-shaped data offered no entry to select it and no entry to draw it —
  while the read walks those axes and draws them. The same hole opened for a
  *scalar* held by three arrays of structures: rank 3 as a quantity, `FLT_0D` on
  the leaf.
- **A static two-dimension leaf could not be selected.** *(fixed by T1)*
  `is2DOrLarger()` (`QVizTreeNode.py:488`) requires `isDynamicData()` and
  **returns `None`** when it is not: a static `FLT_2D` node fell into the branch
  written for curves, where none of the `is0DAndDynamic()` / `is1D()` gates
  matched it. The user could look at it and do nothing with it.
- **The frame choice was worked out twice.** *(fixed by T1)* `QVizPlotAsSlices`
  computed the number of axes a picture shows inline, and the node model needed
  the same answer to offer the right entry. Two copies of that rule is how a menu
  entry and the picture it produces come apart.
- **The preview answered a question nobody asked.** *(fixed by T2)* The left
  click gated the panel on `hasAvailableData() and (isDynamicData() or is1D())`,
  so a static `FLT_2D` leaf never reached it; and whatever the gate let through
  that the command did not recognise (`STR_1D`, `data is None`, a leaf ranking
  three) made `execute()` return **without clearing** what the last accepted
  click had drawn. Measured here on real tree nodes: clicking a text leaf after a
  profile left the profile's curve on the panel (`plot=True, image=False,
  curves=1`) under the label `No preview available` — showing neither the node
  clicked nor a reason for not showing it.
- **The thumbnail's words came from the selection, not from the node.**
  *(fixed by T2)* `QVizPreviewPlotSignal.plot1DSignal` built its labels through
  `dataTreeView.selectedItem.plotOptions(...)`, so previewing a node nobody had
  selected drew its curve under another node's name. It also drew `v[0]`/`t[0]`
  only, and named no slice on a picture.
- **A quantity of two axes cost an empty window and a traceback.** *(fixed by
  T3)* Measured here on real `QVizTreeNode`s: "Plot matrix to → Figure → New" on
  a `FLT_2D` leaf registered `Figure:1` in `figureframes` **with 0 curves**, left
  `figToNodes` empty, logged nothing, and raised `TypeError: object of type
  'QVizDataArrayHandle' has no len()` out of `QVizPlotSignal.execute:59`. The
  window is opened by `GetPlotWidget` *before* any read, so the user got a figure
  to close by hand and no reason for it. The `only 1D plots are currently
  supported` message is never reached for that shape: the read hands back a
  handle and `len()` on it dies first.
- **"As function of time" drew another node's numbers.** *(fixed by T3)* The
  entry was connected to `api.plotSignalVsTimeCommand(self.dataTreeView)` — the
  node the menu was built on is never passed — and the command read
  `dataTreeView.selectedItem`. It took the index to pin from
  `treeNode.infoDict['i']`, the loop letter of the *first* enclosing array of
  structures: measured on a node the dictionary does not tag it died with
  `KeyError: 'i'`, and on a node held by two arrays it reads the outer element.
  Its gate (`is1DAndDynamic() and time_dependent(path)`) answered `False` for a
  1D static leaf, so the entry was missing where the history is plainly readable.
- **Three plot menus, one per leaf spelling, all listing frames they cannot
  fill.** *(fixed by T3)* `menuPlotCurrentSignalNode`,
  `menuPlotCurrentSignal0DNode` and the 2D-array branch each listed the open
  `Figure:` windows and filtered them through `nodeDataShareSameCoordinates`,
  which calls `api.GetPlotWidget` — the legacy frame factory — from a *menu*. Both
  plot menus still built their submenu with `menu.addMenu('Figure')`, the
  dangling submenu T0 removed from the Show/Hide menus.
- **The image window was built before anything was read, and from the wrong
  node.** *(fixed by T4)* Measured here on real `QVizTreeNode`s: on a leaf holding
  no values, "Plot matrix to → image → New" registered `Image:1` in
  `figureframes`, drew **0 pictures**, logged the reduction error twice
  (`zero-size array to reduction operation fmin which has no identity`) **without
  naming the path**, and left the window to close by hand. Nothing went into
  `figToNodes`, so no menu could say what the window held, and its key lived in a
  second namespace (`Image:` beside `SlicesImage:`) that the "add to" entries
  could not fill. The frame was built from `dataTreeView.selectedItem`: right
  clicking one node while another was selected plotted the other — the menu titled
  itself after the selection, `Plot other to`, and drew `[9, 9, 9]` where the node
  under the menu held `[[1, 2, 3]]`.
- **Its picture did not say what it was a picture of.** *(fixed by T4)* Both axes
  carried the same label, `'1..N'` bottom and `'1..N'` left, because the label code
  spells every unbounded coordinate `'1..N'` whichever dimension it is. Inside a
  dynamic array it drew one picture of the element the tree carried with no control
  to move it and no time named anywhere: `getTimeCoordinateDim()` came back `None`.
  Its ROI lines stood in element ranks — which agreed with its own axis labels, and
  with nothing else — and its slices ran against `range(len(slice))`, so a curve
  two metres wide carried element numbers under a label naming metres.
- **A selection of three quantities drew one curve, and cost a window on the
  way.** *(fixed by T5)* Measured on real `QVizTreeNode`s: with a two-axis
  quantity in the selection, `plot1DSelectedSignals` logged `Plots dimension
  larger than 1D are currently not supported.` and `return`ed **out of the loop
  over the selection** — 1 curve out of 3, the node after the refused one never
  read. The figure is opened by `GetPlotWidget` and embedded in the MDI area
  before anything is read, so a refusal left a window to close by hand.
- **Its curve answered an element nothing named.** *(fixed by T5)* A 1D quantity
  held by a dynamic array came back with the four coordinate values along the
  abscissa and the time element pinned at the index the tree happened to carry,
  under `title: ''` and with no control to move it: the numbers on screen were a
  slice whose position had been decided by an earlier click elsewhere in the tree.
- **An emptied selection raised out of the menu.** *(fixed by T5)* Emptying the
  selection between the menu being built and the click — what
  `updateMenuNodeSelection` rebuilds it against — reached
  `logging.getLogger(self.dataTreeView.uri).error(str(e)).error("No selection
  found.")` (`QVizSignalHandling.py:707`), outside any `except`: `UnboundLocalError:
  cannot access local variable 'e' where it is not associated with a value`.
- **The gate that hid the entry answered `True` for quantities whose first
  coordinates differ.** *(fixed by T5)* `shareSameCoordinates` asks the legacy
  predicates and the legacy frame factory, not the axes: measured `True` for
  `rho_tor` against `theta_poloidal`. When it answered `False`, the entry was
  simply absent from the menu, with no reason anywhere — and the two entries drew
  the same selection anyway, one through the old factory and one through the read.
- **The menu bar builds that menu with no node.** `QVizDataTreeView.py:623` calls
  `QVizSignalHandling(self.dataTreeView)`, so `self.treeNode` is `None`, and the
  legacy branch asked that `None` for its plot axis (:350). The selection menu now
  answers the question itself (`defaultPlotAxisForSelection`) instead of asking a
  node that may not exist; the node under a right click still answers for itself.
- `QVizSignalHandling.py:903`: `logging.getLogger(...).error(str(e))` outside any
  `except` — a `NameError` where the user asked for a message.
- ~~`QVizSignalHandling.py:724`: "Delete → StackedPlotView → All" calls
  `deleteAllFigures(TABLEPLOTTYPE)` — it deletes the tables.~~ *(fixed by T0: the
  five copied branches are gone, and the one loop cannot mix the prefixes up.)*
- `QVizSelectSignalsFromConfig.py:35` builds `pathsMap = []` and :78 assigns
  `pathsMap['paths'] = …`: a guaranteed `TypeError`. Nothing calls the class
  except its own `__init__.py` — *Apply Configuration* goes through
  `QVizGlobalOperations.getSignalsPathsFromConfigurationFile`. Dead and broken.
- `QVizViewLoadingStrategy` defines `setIdentifier` twice (:26, :29).
- `QVizDataTreeView.updateMenuNodeSelection` (:575-620) destroys and rebuilds a
  menu on every `aboutToShow`, and writes `dataTreeView.selectedItem` on the way.
- `QVizMainMenuController.deleteAllViews` takes an `index` it never receives
  (wired to `triggered`, so it gets a bool) and iterates a list it mutates:
  *Delete → Views → All* in the root window's menu bar. Not on T0's perimeter
  (shot views, not figures) — owned by T12.

## 3. The work list

| # | User command | Implemented today by | Kills | Status |
| --- | --- | --- | --- | --- |
| T0 | Manage the open figures — "Show/Hide", "Delete", the *Plot windows* menu | `QVizSignalHandling.menusShowHideAndDelete` (one loop over `FigureTypes.MENU_ORDER`), `Viz_API.GetFiguresCount` / `GetNextKeyForFigure` / `ForgetFigure` / `ForgetFigureOf`, `QVizMdiSubWindow` | the five near-identical branches and the five counts fed to them, `update_menus`, the `:724` bug, the duplicated `addPlotWidgetToMDI` and `getMDI` in `QVizSignalHandling`, the blindness to the new frames, the key a closed window used to keep | fait |
| T1 | Decide what a node allows — `is0D/is1D/is2D/is2DOrLarger/is0DAndDynamic`, `getPlotAxisForDefaultPlotting`, `plotOptions` | `QVizNodePlotting` (the axes the read would walk, known without opening the shot), answering `buildContextMenu` | the menu's calls to `is2D`/`is2DOrLarger`/`is1D`/`is0DAndDynamic`, its `STR_1D` and `aos_parents_count` tests, the duplicated axis count in `QVizPlotAsSlices` | fait (the predicates themselves survive until the frames that still call them go: T2-T7, T11) |
| T2 | Preview on left click | `onLeftClickItem` :191 → `QVizSignalHandling.plotPreviewSignalCommand` → `QVizPreviewPlot.forView(...).showNode(node)`: decides on `QVizNodePlotting`, reads one slice through `QVizTensorDataAccess.GetSignal(..., plotWidget=None)`, and says which refusal it made when it draws nothing | `QVizPreviewPlotSignal.py` (135 l.), `QVizPreviewPlotWidget.py` (202 l.), the left-click gate (`hasAvailableData`/`isDynamicData`/`is1D`), the panel's own `is0D`/`is1D`/`is2D` branches, the first of the nine `Viz_API.GetSignal` callers | fait (the panel is a plain `QWidget`: no `sliderGroup`; `PlotTypes.PREVIEW_PLOT` and the four `ID_MENU_PREVIEW_PLOT*` constants now have no consumer left — no menu entry ever referred to them) |
| T3 | Plot one node — "as function of time", "Plot … to → Figure → New/N", 0D vs time | `plotSignalCommand`, `actionPlotAsFunctionOfTime`, `addSignalPlotToFig` → `QVizPlotOneNode`: asks `QVizNodePlotting.plottedAxes()` which frame the quantity needs (two → `QVizImagePlot`, one → `QVizCurvePlot`, a number with only a time base → a curve read along time), opens the window only once the read can answer, keys it in the `SlicesPlot`/`SlicesImage` namespaces, and draws the node the menu was built on at the index the tree carries | `Viz_API.plotSignalVsTimeCommand` (36 l.), `QVizSignalHandling.menuPlotCurrentSignal0DNode` (36 l.) and its gate branch, `QVizNodePlotting.legacyCanDrawScalarAgainstTime`, the `Figure:` listing and the `nodeDataShareSameCoordinates` call in the node menu, `QVizSignalHandling.currentFigureKey`, the 8 call sites of the `getXAxisValues`/`get1DSignalValue` statics, 7 dead `QVizPlotSignal` imports | fait — **but `QVizPlotSignal.py` (199 l.) is still alive**, and the earlier "kills" for this row was wrong: it also engines the legacy slider (`QVizPlotWidget.executePlot:577/584`), the menu *inside* a figure (`QVizCustomPlotContextMenu:213/224/233`), the 1D-from-ROI path (`QvizPlotImageWidget:360 → plot1DInNewFigure`) and the registered Profiles plugin (`CustomizedViewBox.py:198/429-441`). It goes with `QVizPlotWidget` in T7, and so do `AddPlot1DToFig`, `plotVsTimeAtGivenCoordinate1` and `plot0D_DataVsTimeCommand` — none of them reachable from the tree any more |
| T4 | Plot one 2D array — "Plot … to → Image → New" | the node menu's 'Image' submenu (`menuPlotCurrentSignalNode`, named after the frame the entry opens) → `QVizPlotOneNode` → `QVizImagePlot`, with the ROI in `QVizSliceLines`: a movable line per drawn axis, placed in the coordinates the picture is laid over and reading the nearest element, the slice drawn against the other axis's values, the slice following the window and the pinned controls, kept slices frozen, and the keep/delete commands as buttons on the frame instead of a viewBox menu | `QvizPlotImageWidget.py` (409 l.), `QViz2DArrayHandling.py` (89 l.), `QVizImageCustomPlotContextMenu.py` (99 l.), `QVizImageSlicesPlotConfigUI.py` (38 l.) — the image window's whole right-click menu went with them, `Viz_API.Plot2DArray` / `plot1DInNewFigure` / `GetNextKeyForImagePlots` / `GetImagePlotsCount` (54 l.), `FigureTypes.IMAGETYPE` and its `MENU_ORDER` entry, `QVizSignalHandling.actionPlot2DArray` and the `legacyCanDrawAsImage` branch, the `QvizPlotImageWidget` branch of `QVizPlotConfigUI.getLegendItem`, `tests/test_10_plot_image_widget.py` (80 l.) and the two `VizExamples` demos that drove the class (85 + 124 l.) | fait — the `Image:` namespace is gone, so `MENU_ORDER` has six entries and one kind of picture window; the 1D-from-ROI path (`plot1DInNewFigure`) died with the widget, which is one of the four consumers `QVizPlotSignal.py` was kept for in T3's row |
| T5 | Plot the selection as curves — "Plot selected nodes to → Figure", This/All, New/N | `plotSelectedSignals`, `addSelectedSignalsPlotToFig` → `QVizPlotAsSlices` with an `intoFigureKey`: the command asks `plottedAxes()` per node and picks the frame (one axis → the curve figure, two → one window per picture), reads through the tensor read, and refuses by name what a frame cannot show | `QVizPlotSelectedSignals.py` (171 l.), the second selection entry ("Curves and images with slice controls") and `QVizSignalHandling.plotAsSlices`, the gate `nodeDataShareSameCoordinates`/`currentSelectionShareSameCoordinates`, the `Figure:` listing in the selection menu, one `Viz_API.GetSignal` caller | fait — **correction of the "kills" as first written**: `figToNodes` stays (it is the bookkeeping of the new commands: which node each window answers for, and the menus that list it), and `shareSameCoordinates`/`shareSameCoordinates2` stay until T6/T7, whose frames still ask them. `Viz_API.PlotSelectedSignals` / `PlotSelectedSignalsFrom` (documented in `scripting.rst`) are re-pointed at the new command rather than deleted |
| T6 | TablePlotView — the four "New (default axis)" / "New ('TIME' axis)" × This/All entries | `onPlotToTablePlotView` → `QVizMultiPlotWindow` → `QVizTablePlotView.py:128` | `QVizTablePlotView.py` (285 l.), two duplicate menu entries | to do |
| T7 | StackedPlotView — the same four entries | `onPlotToStackedPlotView` → `QVizStackedPlotView.py:241` | `QVizStackedPlotView.py` (459 l.), `QVizMultiPlotWindow.py` (496 l.), and then `QVizPlotWidget.py` (596 l.) | to do |
| T8 | Select / unselect — one node, all of the same AOS, everything, This/All | `QVizSelectOrUnselectSignal`, `QVizSelectSignalsGroup` (regex on the path), `QVizUnselectAllSignals` (nested loop, unguarded `keysToRemove[i]`) | `QVizSelectSignalsFromConfig.py` (dead), the AOS regex, the writes into `infoDict['isSelected']` | to do |
| T9 | "Apply Configuration" / save a configuration | `QVizConfigurationListsWindow` (394 l.), `QVizSavePlotConfig` (335 l.) | the hand-parsed `GraphicsWindow/PlotItem/sourceInfo` XML | to do |
| T10 | "Export to IDS" | a 100-line inline dialog in `QVizDataTreeViewFrame.onExportToLocal` + `dataSource.build_uri` (xfail: `ImportError` on `_al_lowlevel`) | the inline dialog, the bare `except:` | to do |
| T11 | Node documentation on left click | `QVizNodeDocumentationWidget` (651 l., sets `np.set_printoptions(threshold=sys.maxsize)` globally) | — | to do |
| T12 | Load an occurrence — double click, Return, "Get … data for occurrence", "Add a new view", Shift+right click | `loadDefaultOccurrence` :424, `QVizLoadDataHandling`, `QVizViewLoadingStrategy` (identifiers 1-4 hardcoded, `QInputDialog` without a parent) | the magic identifiers, the duplicated `setIdentifier` | to do |
| T13 | Plugins in the menu | `QVizPluginsPopUpMenu`, `QVizPluginsHandler` | — (last: plugins call the frames, so they follow them) | to do |

## 4. Why this order

- **T0 and T1 before anything else.** Every command migrated to the new frames
  produces windows the user cannot close (T0), and every menu branch is still
  decided on the dictionary dimension instead of the axes (T1). Without them,
  T2-T7 recreate the problem they claim to solve.
- **T2 before T3.** The preview fires on every left click — the most frequent
  path in the application — and it is the only one dragging a widget that
  *inherits* `QVizPlotWidget` and its `sliderGroup`.
- **After T7**, `QVizPlotWidget` has no consumer left and goes with it. What
  remains of legacy (T9-T13) no longer touches reading at all.

## 5. How a task is done

Always the same shape, two commits (implementation, then tests), nothing pushed:

1. A test that reproduces the defect of that command first. `tests/support/fakes.py`
   and `tests/support/plotting.py` already give a tree view and a selection
   without a real case.
2. The replacement, reusing what exists: `QVizAxesSpec.fromTreeNode`,
   `QVizTensorDataAccess` (`GetSignal`, `plan`, `framesFor`, `GetFrames`),
   `QVizCurvePlot`, `QVizImagePlot`, `QVizSliceControls`/`QVizFramesWindow`,
   and `QVizPlotAsSlices` for the selection-to-frame routing.
3. Actually deleting the files in the "kills" column, and merging the menu
   entries: one "Plot selected nodes to", the command picks the frame.

## 6. How progress is measured

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -q
```

Reference at the start of this work: **366 passed, 8 xfailed**. Since T0: **373
passed, 8 xfailed** — seven tests in `tests/test_30_figure_registry.py` pin the
registry and the menus built from it. Since T1: **387 passed, 8 xfailed** —
thirteen tests in `tests/test_31_node_plotting.py` pin the node model and the menu
built from it, on real `QVizTreeNode`s with a hand-built `infoDict`, so the legacy
predicates answer for real and a wrong menu is the menu's fault, not a stub's; the
fourteenth is `tests/test_99_import_sweep.py` counting the new module, which is
how that sweep earns its keep. Since T2: **398 passed, 8 xfailed** — twelve tests
in `tests/test_32_preview.py` pin what the thumbnail draws and what it says when
it draws nothing, driven through `plotPreviewSignalCommand`, the entry point that
survived; the refusals run on real `QVizTreeNode`s with `idsRef` left `None`, so a
refusal that read the shot first would crash instead of answering. The sweep went
one shorter, not one longer: it lost the two deleted modules and gained the panel
(387 + 12 − 1 = 398). Since T3: **408 passed, 8 xfailed** — nine tests in
`tests/test_33_plot_one_node.py` drive the three tree entries as the click does
(`plotSignalCommand`, `actionPlotAsFunctionOfTime().trigger()`,
`addSignalPlotToFig`, `menuPlotCurrentSignalNode`) and pin which frame the
quantity lands in, that the node under the menu is the node drawn, and that a
refusal costs no window; the sweep gained the command module (398 + 9 + 1 = 408).
Since T4: **420 passed, 8 xfailed** — twenty-one tests in
`tests/test_34_one_image.py`, driven both through the tree entry
(`plotSignalCommand`, `menuPlotCurrentSignalNode`) and on the frame, pinning that a
two-axis quantity lands in `SlicesImage` and is recorded in `figToNodes`, that no
`Image:` key is produced, that the submenu is named after the frame the entry opens,
then the ROI: lines bounded by the coordinate extents, the slice read at the nearest
element and drawn against the other axis's values, the label naming the axis it
stands on, the slice following the window of pictures and a pinned array, kept
slices staying put when the line moves, and the commands as buttons on the frame.
The suite lost the five tests of the deleted image widget and one entry of
`test_30_figure_registry.py`'s legacy-type parametrization — the `Image:` namespace
is gone, so there is no Show/Hide entry left to pin for it — and the sweep lost the
four deleted modules and gained `QVizSliceLines` (408 + 21 − 5 − 1 − 4 + 1 = 420).
The `build_uri` xfail can only be lifted by T10; the five Qt Designer modules stay.
Since T5: **432 passed, 8 xfailed** — thirteen tests in
`tests/test_35_selection_entries.py`, driven through the two entries as the menu
fires them (`plotSelectedSignals`, `addSelectedSignalsPlotToFig`,
`menuPlotSelectedSignalNodes`), pinning that a selection of two quantities draws
two curves read along time, that a two-axis quantity in the selection costs the
others nothing (one curve figure with 2 curves plus a picture window with 3
pictures), that an emptied selection and a selection that reads as nothing both
answer with a reason and leave no window, that the windows land under the
`SlicesPlot`/`SlicesImage` keys with their nodes in `figToNodes` and no `Figure:`
key appears, that the pinned coordinate is named and bounded on the figure, and
that the menu offers one 'Figure' entry whose submenus name the curve figures it
can fill. The sweep went one shorter: the deleted command module is one fewer
module to import (420 + 13 − 1 = 432).

A second number T1 owns: **what a right click reads**. The context menu used to
answer its questions from the dictionary only, which was cheap but wrong; the new
model answers from `QVizAxesSpec.fromTreeNode`, which is also cheap. `plottedAxes`
is the one question that needs the shot, and only the command that draws pays for
it — so a right click still extracts no tensor. Keep it that way when T2-T7 come.

Besides the tests, count what is left of the legacy surface — the number of
callers of `Viz_API.GetSignal` and of legacy frame classes imported. Starting
point: nine callers (`QVizPreviewPlotSignal:42`, `QVizPlotSignal:55`,
`QVizPlotSelectedSignals:101`, `QVizTablePlotView:128`, `QVizStackedPlotView:241`,
`Viz_API:629/911/934`, `Viz_DataSelection_API:45`). After T7: none in a plotting
path. T1 changed none of them: it moved the *decision*, not the read. T2 took the
first one out: the panel reads through `QVizTensorDataAccess` itself, handing that
read no plot widget, because it has no control to be read through. T3 changed none
either — the command it deleted read through `QVizPlotSignal`, which is still
counted, while `QVizPlotOneNode` reads through the frames, and they call
`QVizTensorDataAccess` directly. **Correction measured while doing T5**: the list
above counted three callers inside `Viz_API`; there were two (`920`/`943` at the
start of T5), so seven remained, not eight. T5 took the one in the command it
deleted (`QVizPlotSelectedSignals:100`): **six remain** (`QVizPlotSignal:55`,
`QVizTablePlotView:126`, `QVizStackedPlotView:239`, `Viz_API:917/940`,
`Viz_DataSelection_API:45`). The two in `Viz_API` answer
`getAllPlottable_0D_1D_Signals` / `updateAllPlottable_0D_1D_Signals`, which no tree
gesture calls: they go with the scripting surface that reaches them.

Frames are tested offscreen, as everywhere else in the suite: no X display is
assumed.
