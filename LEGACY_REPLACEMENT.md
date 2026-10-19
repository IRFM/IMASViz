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
| The context menu on a node | `QVizSignalHandling.buildContextMenu` (:59), `QViz2DArrayHandling.menuPlotCurrentArrayNode`, `QVizHandleRightClick`, `QVizHandleShiftAndRightClick` |
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
| T2 | Preview on left click | `onLeftClickItem` :186 → `QVizPreviewPlotSignal` → `QVizPreviewPlotWidget` (a `QVizPlotWidget` subclass, so it carries `sliderGroup`) | `QVizPreviewPlotSignal.py` (135 l.), `QVizPreviewPlotWidget.py` (202 l.) | to do |
| T3 | Plot one node — "as function of time", "Plot … to → Figure → New/N", 0D vs time | `plotSignalVsTimeCommand`, `plot0D_DataVsTimeCommand`, `plotSignalCommand`, `addSignalPlotToFig` → `QVizPlotSignal` + `QVizPlotWidget` | `QVizPlotSignal.py` (199 l.), `plotVsTimeAtGivenCoordinate1`, `AddPlot1DToFig` | to do |
| T4 | Plot one 2D array — "Plot … to → Image → New" | `QViz2DArrayHandling` (half commented out) → `Viz_API.Plot2DArray` :622 → `QvizPlotImageWidget` | `QvizPlotImageWidget.py` (409 l.), `QViz2DArrayHandling.py`, `Plot2DArray` | to do |
| T5 | Plot the selection as curves — "Plot selected nodes to → Figure", This/All, New/N | `plotSelectedSignals`, `addSelectedSignalsPlotToFig` → `QVizPlotSelectedSignals` (refuses rank ≥ 2 at :51-53) | `QVizPlotSelectedSignals.py` (171 l.), `shareSameCoordinates`, `currentSelectionShareSameCoordinates`, most of `figToNodes` | to do |
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
predicates answer for real and a wrong menu is the menu's fault, not a stub's. The
`build_uri` xfail can only be lifted by T10; the five Qt Designer modules stay.

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
path. T1 changed none of them: it moved the *decision*, not the read.

Frames are tested offscreen, as everywhere else in the suite: no X display is
assumed.
