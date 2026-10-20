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
- **A table of two quantities died on one of them, and kept the window.**
  *(fixed by T6)* Measured on real `QVizTreeNode`s: selecting a 1D leaf and a
  `FLT_2D` leaf and asking *TablePlotView → New (default axis)* raised
  `TypeError: 'QVizDataArrayHandle' object is not subscriptable` out of the entry —
  `plot1DSelectedSignals` indexes the answer as `v.shape[0]` / `t[0]` whatever the
  shape it got. It died after `AddNodeToFigure` had recorded both nodes and after
  the window had been registered: `figureframes['TablePlotView:1']` held an object
  with **no `multiPlotView`**, and neither quantity was on screen.
- **The same quantity, asked for the time axis, came back as something else.**
  *(fixed by T6)* Under `plotAxis='TIME'` that 2D leaf drew **one curve of 5
  points** — one element of it, `[0, 100, 200, 300, 400]` — titled as the whole
  quantity, with no control and no word saying which of its 4×2 elements had been
  picked. Nothing refused it: `GetSignal` answered, and the frame drew the answer.
- **Three of the four entries asked the same question.** *(fixed by T6)* Both
  "All IMAS Databases" actions and the "This IMAS Database" action of the 'TIME'
  submenu were wired with `plotAxis='TIME'`; only one of the four took the
  `defaultPlotAxisForSelection()` answer, and that one computed it behind
  `shareSameCoordinates` — measured `False` for the two-coordinate selection the
  window drew correctly, so the measured entry took `'TIME'` anyway.
- **Its panels were keyed the wrong way round, twice.** *(fixed by T6)* The column
  count came from the screen width (measured `cols=1` with 2 panels on this
  display, 3 rows for 3 quantities), while `plot()` set `column = n // cols` and
  `row = n % cols` — the other way round from where the panel was laid. The
  configuration file writes `key=(row, column)` and
  `applyPlotConfigurationAfterPlotting` compares `(plotItem.column,
  plotItem.row)`: a saved configuration re-applied to a panel only when it sat on
  the diagonal of the table.
- **The window survived its own close button.** *(fixed by T6 and T7, the pattern
  T0 pinned elsewhere)* `QVizMultiPlotWindow` writes `figureframes[self.figureKey]`
  twice (:79 and :166) and embeds itself in a plain `QMdiSubWindow` instead of
  `QVizMdiSubWindow`, so nothing tells the api the key is free: measured on the
  stacked window, `figureframes` held `['StackedPlotView:1']` before `close()` and
  `['StackedPlotView:1']` after it, and the next window was handed
  `StackedPlotView:2`.
- **The stacked window's four entries could not be reached.** *(fixed by T7)* The
  `StackedPlotView` submenu was built with `menu.addMenu('StackedPlotView')`, which
  hands back a `QMenu` held only by a Python local, so its C++ object died when
  `menuPlotSelectedSignalNodes` returned: measured, reading the *Figure* and
  *TablePlotView* submenus of the same menu answers, and asking the
  `StackedPlotView` one for its actions raises `RuntimeError: Internal C++ object
  (PySide6.QtWidgets.QMenu) already deleted`. The same dangling-submenu default T0
  found in the *Show/Hide* branches.
- **It never shared an abscissa, which is all it is for.** *(fixed by T7)*
  `StackedPlotWindow.plot` sets `self.plotItemFirst = None` at the top of **every
  call**, so the `setXLink`/`setYLink(self.plotItemFirst)` that follows links each
  panel to nothing: measured on two panels, the first was its own link and the
  second was linked on neither axis — `(False, False)` — while the manual promises
  "All plots displays always share the same X and Y range, even when using plot
  interaction features".
- **Neither of its two checkboxes did what its label says.** *(fixed by T7)*
  *Group pan mode* read `self.viewBoxes`, an attribute that class never sets (it
  sets `viewBoxList`): toggling it raised `AttributeError: 'QVizStackedPlotView'
  object has no attribute 'viewBoxes'`. *Display X axis of all plots* rewrote the
  tick-label style the linking had already decided and never read a state of its
  own: measured `[False, True]` — one panel labelled, the other not — in both
  states. And the titles were the first panel's only: measured, plot 0 carried
  `StackedPlotView:1` and plot 1 carried `''`.
- **A quantity it should have refused was drawn, or killed the window.** *(fixed
  by T7)* A `FLT_2D` leaf in a stacked selection raised
  `TypeError: 'QVizDataArrayHandle' object is not subscriptable` out of the entry,
  leaving `figureframes['StackedPlotView:7']` holding a window with **no
  `multiPlotView`** and `figToNodes` holding both nodes. An empty selection left
  the same husk. A scalar was drawn along time with no control anywhere on the
  window to say or move which element the curve answered for.
- **The menu bar builds that menu with no node.** `QVizDataTreeView.py:623` calls
  `QVizSignalHandling(self.dataTreeView)`, so `self.treeNode` is `None`, and the
  legacy branch asked that `None` for its plot axis (:350). Measured with T7, the
  menu bar reached that line only through `defaultPlotAxisForSelection`, which the
  stacked branch called behind `shareSameCoordinates`; both are gone, and the
  branch names its two strategies in the submenu titles instead of asking a node
  that may not exist. The node under a right click still answers for itself,
  through the read and not through the menu.
- `QVizSignalHandling.py:903`: `logging.getLogger(...).error(str(e))` outside any
  `except` — a `NameError` where the user asked for a message.
- ~~`QVizSignalHandling.py:724`: "Delete → StackedPlotView → All" calls
  `deleteAllFigures(TABLEPLOTTYPE)` — it deletes the tables.~~ *(fixed by T0: the
  five copied branches are gone, and the one loop cannot mix the prefixes up.)*
- ~~`QVizSelectSignalsFromConfig.py:35` builds `pathsMap = []` and :78 assigns
  `pathsMap['paths'] = …`: a guaranteed `TypeError`. Nothing calls the class
  except its own `__init__.py` — *Apply Configuration* goes through
  `QVizGlobalOperations.getSignalsPathsFromConfigurationFile`. Dead and broken.~~
  *(fixed by T8: the class is gone. Measured, it died one line earlier still —
  `AttributeError: 'dict' object has no attribute 'find'` on a dictionary
  configuration — so the `TypeError` was never even reached.)*
- **The selection was written twice, and the tree was coloured from the wrong
  record.** *(fixed by T8)* `selectedSignalsDict` — which every frame built since
  T3 reads — and `infoDict['isSelected']`, which the menu and the colours read.
  Measured on real tree items: unselecting `a` while the tree's current item was
  `b` left `a` **red** and turned `b` **blue** — a selected node shown free and a
  free one shown selected, because the command recoloured `selectedItem` rather
  than the node it was asked about. And with the flag set and the dictionary not
  holding the key, the entry read "Unselect a…" and its slot answered
  `KeyError`, leaving the flag set: the node could be neither selected nor
  unselected.
- **An entry could record the wrong node.** *(fixed by T8)*
  `QVizSelectSignal` keyed the entry with the asked node and stored
  `dataTreeView.selectedItem` in it. Measured: selecting `a` while the tree was
  pointed at `b` left one entry, keyed for `a`, whose `QTreeWidgetItem` was **b** —
  so a plot of that selection drew b and never a. The node the user clicked was
  not what the plot commands read.
- **The AOS entry matched a regular expression over the display path.** *(fixed
  by T8)* `re.sub("[\(\[].*?[\)\]]", "", path)` removes every bracketed run, so
  the occurrence is not in the string it compares. Asked on `core/time_slice(0)/a`
  in a view holding five nodes it selected **three**: the other structure element
  (right) and `core/time_slice(0)/a` of the **second occurrence of the IDS**,
  which the user never touched. Asked a second time it re-added what was already
  selected and overwrote its place — three entries all recorded index `2`. And it
  wrote `selectedItem` for every node it walked, leaving the tree pointed at
  whatever its loop touched last.
- **"Unselect All" deleted by counting on the wrong list.** *(fixed by T8)* It
  scanned the whole signal list for every selected node comparing dictionaries,
  then ran `for i in range(len(selectedSignalsDict)): keysToRemove[i]`. Measured
  with three selected nodes and one the tree no longer listed: `IndexError: list
  index out of range` after dropping two, leaving the third **selected and red**.
- **The order of the user's clicks was off by one.** *(fixed by T8)* `index =
  len(selectedSignalsDict) - 1`, computed before the insertion: three clicks were
  recorded `-1, 0, 1`. The value is read by nobody in `imasviz/` — no command,
  frame or plugin indexes on it — so the defect is cosmetic; the entry *shape* is
  load-bearing, and it is the node object that was wrong.
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
| T6 | TablePlotView — the four "New (default axis)" / "New ('TIME' axis)" × This/All entries | `onPlotToTablePlotView` → `QVizPlotAsTable` → `QVizTablePlot`: one panel per quantity, each read on the axes it sits on, each carrying the controls for the axes that read pins; the configuration file names the quantities and the place each panel held | `QVizTablePlotView.py` (283 l.), the `shareSameCoordinates` gate on these entries, the `plotItem.column`/`plotItem.row` pair the configuration was keyed by, `QVizMultiPlotWindow.addMenuBar`/`onSavePlotConf` and the two `TablePlotView` branches of `checkFigureKey`/`setMultiPlotView` (43 l.), the second registration of the window's own key | fait — **correction of the "kills" as first written**: the row announced "two duplicate menu entries"; measured, the four entries are four distinct menu items, and what was duplicated is their *wiring* — three of the four asked for `plotAxis='TIME'`. What survives: `QVizMultiPlotWindow` itself (StackedPlotView, T7) with `applyPlotConfigurationAfterPlotting`, now unreachable for the table since its only caller was the deleted frame; `Viz_API.GetNextKeyForTablePlotView`, kept as the documented scripting accessor; the `TablePlotView:` namespace, which T0's Show/Hide/Delete address. The panel is not offered the right-click `Configure Plot` dialog, and the styling a configuration file holds is refused by name in the log — both owned by T9 ("the configuration format: save and style") |
| T7 | StackedPlotView — the same four entries | `onPlotToStackedPlotView` → `QVizPlotAsStacked` → `QVizStackedPlot`: the T6 panel, moved out of the table into `QVizPanel.py` because both windows lay the same panel out; one panel per quantity in one column, the abscissa the first quantity read fixes, the X and Y ranges of the others linked to it, and two checkboxes that do what their labels say — a quantity read along another abscissa is refused by name, with TablePlotView pointed at | `QVizStackedPlotView.py` (459 l.), `QVizMultiPlotWindow.py` (496 l.), and then `QVizPlotWidget.py` (596 l.) | fait — **correction of the "kills" as first written**: measured, the two window modules are 457 and 463 lines (920 gone), but `QVizPlotWidget.py` (595 l. measured, not 596) does **not** go with them: its consumers outlive the stacked window — `Viz_API.CreatePlotWidget:630/647` and `GetPlotWidget:659`, which `AddPlot1DToFig:696`, `plot0D_DataVsTimeCommand:737` and `plotVsTimeAtGivenCoordinate1:793/831` still call, the menu inside a figure (`QVizCustomPlotContextMenu:213/233`), the registered Profiles plugin (`CustomizedViewBox.py:198/441`), `QVizTreeNode.nodeDataShareSameCoordinatesAs:846`, and `tests/test_13_plot_axes.py` / `test_32_preview.py`. It goes with the scripting surface and the plugin, i.e. T13 and whatever owns `AddPlot1DToFig`. What T7 did kill beyond the two windows: the `menu.addMenu` submenu that died before it could be clicked, and the gate those entries hid behind — `shareSameCoordinates`, `shareSameCoordinates2` and `defaultPlotAxisForSelection` (117 lines out of `QVizSignalHandling`, 50 back). `Viz_API.GetNextKeyForStackedPlotView` and the `StackedPlotView:` namespace stay, as T0's Show/Hide/Delete address them |
| T8 | Select / unselect — one node, all of the same AOS, everything, This/All | One command, `QVizSelectNodes`: `toggle` for the node entry, `sameAos` for the structure family (read off the parametrized path and the occurrence, not off a display string), `unselectAll(all_DTV)` for This/All, `isSelected` for the label the menu offers — so the menu asks the selection what it holds instead of asking the node a flag it keeps for itself | `QVizSelectSignalsFromConfig.py` (dead), the AOS regex, the writes into `infoDict['isSelected']` | fait — **correction of the "kills" as first written**: measured, five modules go, 285 lines — `QVizSelectOrUnselectSignal` (46), `QVizSelectSignal` (47), `QVizSelectSignalsGroup` (48), `QVizUnselectAllSignals` (58) and the dead `QVizSelectSignalsFromConfig` (86) — not one file plus two habits. `QVizSelectSignals` stays (T9 owns the configuration path) but delegates, and `infoDict['isSelected']` is now written nowhere in the package, so the selection has one record. What was *not* killed, and was measured before removing anything: the toolbar's "Unselect All Nodes" sub-menu survives the commands and keeps both its actions, and `all_DTV` empties every opened view — neither had a defect to claim. Still standing, out of T8's way: `updateMenuNodeSelection`, which rebuilds its menu on every `aboutToShow`, and the `selectedItem` crutch the menu and `QVizPlotOneNode` still read |
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
Since T6: **451 passed, 8 xfailed** — eighteen tests in
`tests/test_36_table_plot_entries.py`, driven through the four menu entries and
through the configuration-file path, pinning that the two window kinds ask two
different questions and read along different axes, that a panel holds one quantity
so two coordinates give two panels each with its own abscissa, that a quantity with
two axes to draw is refused by name and costs the others nothing, that each panel
names and bounds its pinned coordinates, that the table's keys are `(row, column)`
and that the registry releases the key when the window closes, and that a `.pcfg`
draws the paths it names while its styling is refused out loud. The sweep gained
one: the deleted frame module is one fewer import, the command and the frame are
two more (432 + 18 − 1 + 2 = 451).
Since T7: **474 passed, 8 xfailed** — twenty-two tests in
`tests/test_37_stacked_entries.py`, driven through the four menu entries and
through one action triggered from the menu itself, pinning that the
`StackedPlotView` submenu is still alive after the call that built it (the legacy
one was a deleted C++ object), that the two entries read along different axes,
that every panel of a window shares the ranges of the first — `linkedView` asked
of the view boxes, which is where a range lives — that the two checkboxes change
what they say they change, that a quantity read along another abscissa is refused
by name with both axes named and the panel not left on screen, that the first
quantity read is the one that fixes the abscissa, that the panels are keyed by
their row in one column, and that closing the window frees its key. The sweep
gained one again: two window modules gone, one panel module, one frame and one
command added (451 + 22 − 2 + 3 = 474), and the sweep itself is 116 passed /
5 xfailed over 121 modules.
Since T8: **494 passed, 8 xfailed** — twenty-four tests in
`tests/test_38_selection_entries.py`, driven through the node menu as the click
fires it (`selectOrUnselectSignal`, `actionSelectOrUnselectSignalNode().text()`,
`selectAllSignalsFromSameAOS`, `onUnselectSignals`) on real `QVizTreeNode`s built
with the `itemDataDict` the tree builder writes and a `dataKey` copied verbatim
from `QVizIMASDataSource`, pinning that an entry holds the node it was asked for
and not the tree's current item, that unselecting recolours the label it was
asked about, that the menu's label follows the dictionary rather than a flag the
node keeps, that the AOS family is the elements of that structure in the clicked
occurrence, that asking it twice adds nothing and moves nothing, that "Unselect
All" clears a node the tree no longer lists and recolours every label it
clears, and that a selection read from a configuration records the same entry.
The sweep lost four modules: five selection modules gone and the command added
takes one back, so 121 − 5 + 1 = 117 modules and 112 passed / 5 xfailed
(474 − 5 + 1 + 24 = 494).

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
`Viz_DataSelection_API:45`). T6 took the table's one with the frame it deleted:
**five remain** (`QVizPlotSignal:55`, `QVizStackedPlotView:239`, `Viz_API:929/952`,
`Viz_DataSelection_API:45`) — `QVizTablePlot` and `QVizPlotAsTable` read through
`QVizTensorDataAccess` directly, as the other new frames do. T7 took the stacked
window's one with the window: **four remain** (`QVizPlotSignal:55`,
`Viz_API:929/952`, `Viz_DataSelection_API:45`) — `QVizStackedPlot` draws with the
same `QVizPanel` as the table, and that panel calls `QVizTensorDataAccess.GetSignal`
itself. None of the four is a tree gesture any more. The two in `Viz_API` answer
`getAllPlottable_0D_1D_Signals` / `updateAllPlottable_0D_1D_Signals`, which no tree
gesture calls: they go with the scripting surface that reaches them.

Frames are tested offscreen, as everywhere else in the suite: no X display is
assumed.
