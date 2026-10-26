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
- **The *Save Plot Configuration* button wrote no file at all.** *(fixed by T9)*
  `QVizSavePlotConfig` read 23 keys out of `PlotDataItem.opts` by name and calls
  `QPen` methods on whatever the pen had become. Measured on the window of two
  panels: `KeyError: 'name'` — pyqtgraph 0.13.7 has 22 of the 23 — and with that
  key injected by hand, `AttributeError: 'tuple' object has no attribute
  'brush'`, because `opts['pen']` is a tuple there. Re-measured on a window
  holding a curve of 1642 points: the same two. `git` shows no file created.
- **A window whose first panel carried no `signalData` was written anyway.**
  *(fixed by T9)* The save loop `break`ed there. Measured: a file of **363
  bytes** with **0** `PlotItem` and **0** `sourceInfo` in it, and no word in the
  log — the user pressed OK and got a configuration naming nothing.
- **The place a panel sat was written and never read back.** *(fixed by T9)*
  The old writer put `key="(row, column)"` and `row`/`column` attributes on every
  panel; the reader kept two attributes per panel — path and occurrence — and
  `QVizPlotAsTable` asked neither. Measured: a file naming **(0, 0)** and
  **(1, 1)** laid its two panels at **(0, 0)** and **(0, 1)**, while the manual
  promises the place back.
- **The abscissa the window was drawn with was not in the file.** *(fixed by
  T9)* Measured: a table drawn along `time` and re-applied came back along
  `rho_tor` and `theta_poloidal`, first abscissa values `[0, 1, 2, 3]` — not the
  time base — and the two menu strategies could not be told apart in the result.
- **The reader asked the file name, not the file.** *(fixed by T9)* The same XML
  named `probe.xyz` answered `{'paths': [], 'occurrences': []}` without a word;
  `endswith('lsp')` — no dot — took `probe.notlsp` for a node selection; and a
  truncated file raised `ParseError: no element found: line 1, column 35` out of
  the slot that was asked to apply it.
- **The name typed in the dialog was trusted.** *(fixed by T9)* `configName[:-3]`
  on a four-character extension: typing `probe.lsp` wrote **`probe..lsp`**. And
  nothing looked at separators: typing `../outside` wrote `$HOME/outside.lsp`,
  outside the configuration folder.
- **The scripted entry the manual shows did not accept the form the manual
  shows.** *(fixed by T9)* `scripting.rst:137/214` is
  `api.SelectSignals(f1, pathsList1)` with a plain list of paths; measured, that
  raised `TypeError: list indices must be integers or slices, not str`. Given the
  dictionary form, the command rewrote the caller's own list on the way in
  (`['foo.time_slice[i].vector']` came back as `['foo/time_slice(i)/vector']` in
  the caller's dict), and three paths with two occurrences raised `IndexError:
  list index out of range` instead of the `ValueError` written two lines below.
- **The configuration list was refreshed by a chain of three attributes.**
  *(fixed by T9)* `dataTreeView.parent.configurationListsWindow.updateList('lsp')`
  — no guard on any link. A configuration saved from anywhere else (the plot
  window's button, another shot view, the user's editor) left the list stale, and
  two clicks on *Actions → Apply Configuration* built two windows.
- **The export wrote no IDS, and said nothing about it.** *(fixed by T10)* Three
  defects stacked, each hiding the next. The handler's first statement built the
  URI through a helper doing `from imas import _al_lowlevel as ll`; IMAS-Python
  2.3.0 has no such module, so the click answered `ImportError: cannot import
  name '_al_lowlevel'` — and that statement sat **outside** the `try`, so nothing
  was caught: **0 files**. With the URI spelled by hand, the handler called
  `open()` on an entry built from that URI; IMAS-Python opens it at construction
  and answers `RuntimeError: This DBEntry is already open`, which the bare
  `except:` turned into one *info* line ("Unable to create pulse file with URI:
  …"): **1 file**, a 1912-byte `master.h5`, **0 IDSs**. And an entry built
  without a data dictionary refuses every IDS — `RuntimeError: Provided IDS uses
  DD 3.35.0 which has a different major version than the Data Entry (-1)`; pinned
  at `3.35.0`, the same two IDSs came out as `master.h5` 2000 bytes and
  `pulse_schedule.h5` 83662 bytes, read back at occurrence 0.
- **One version was carried where the format needs two.** *(fixed by T10)* The
  URI carries the **major** of the data dictionary (the real cases sit under
  `west/3/54924/0`) and the entry is built at the **full** number: `dd_version='3'`
  answers `UnknownDDVersion: Data dictionary version '3' cannot be found`. The
  old code took its single number from `IMAS_MAJOR_VERSION`, the Access Layer's
  own — `5` on this stack — so measured, an export named `no_such_db` wrote
  `no_such_db/5/1/0/`: bytes on disk, in a directory no reader of this
  application looks in.
- **The dialog trusted text boxes, and prefilled a user called `/`.** *(fixed by
  T10)* Its shot and run boxes were read with `int()` inside the handler, so a
  shot of `abc` answered `ValueError: invalid literal for int() with base 10:
  'abc'`; the backend was asked for as the number `13`, which the manual never
  mentions; and the user and the database started at `/`, which the Access Layer
  accepted without a word.
- **A database that does not exist is not refused, it is created.** *(left as
  measured)* The manual's second note warns that the database must exist; the
  Access Layer does not enforce it. Six probe URIs naming invented databases each
  created `<db>/<version>/<shot>/<run>/` under the login's own `~/public/imasdb`
  tree, silently. Nothing here can promise the note's warning is checked, so the
  note stays a warning and the log names the URI that was written to.
- **The panel that answers "what is this node?" answered wrong in five ways.**
  *(fixed by T11)* Measured on nodes built the way `QVizDataTreeViewBuilder`
  builds them, on the reference case, and none of it printed an error.
  `Number of zeros` was `len(np.where(values == 0))`, the length of a one-element
  tuple: **1** for three values with no zero, **1** for four values with three
  zeros, **1** for the 101 values of `profiles_1d/psi` — and 49 for
  `code/output_flag`, which is where the answer happened to be right. `Min` and
  `Max` were the plain extremes, so `[1, nan, inf, -inf, 0]` read `-inf` and
  `inf`. A string array went down the same branch: `['a', 'b']` read `Min: a`,
  `Max: b`, `Number of zeros: 1`, and the two `Invalid entries` rows were left at
  `/` by the `except:` that caught `np.isnan` refusing strings. The content of an
  array was `str(values)`, so an IMAS-Python array showed its wrapper —
  `<IDSNumericArray (IDS:equilibrium, time_slice[0]/profiles_1d/psi, FLT_1D)>` —
  **1543 characters for 101 values**, where the numbers the user came for are
  what `Content:` holds. And the constructor called
  `np.set_printoptions(threshold=sys.maxsize)` for the whole process and never
  undid it: the threshold went from 1000 to 9223372036854775807, after which
  `str()` of a million floats answered **12,166,667 characters in 75.08 s** where
  the default answers 78 characters in 0.02 s — for a panel that shows 200 values
  at each end, which `np.array2string(value[:5])` answers in 0.0001 s.
- **Twenty labels prefilled with one character.** *(fixed by T11)* Every field
  started at `/` and was shown, so a real `FLT_2D` with nothing in it — 48 of
  them in this IDS, and 6 `FLT_4D` — read `Array shape: (0, 0)`, `Min: /`,
  `Max: /`, `Content: /`. A row a node cannot answer is now absent.
- **A failed read left another node's identity on screen.** *(fixed by T11)*
  `update` hid its fields first and then read, so when the read raised — a leaf
  the runtime does not hold — every field went blank while the hidden labels kept
  `Node: equilibrium.psi`, `Array size: 101`, `Content: [-7.9 ...`, and the
  exception reached the slot, where PySide6 6.6 prints a traceback and lets the
  process live: **exit 0**, the preview update sitting after it in the same slot
  never run. The panel now rebuilds from nothing for every node and says the
  reason a read failed.
- **The widget took the method Qt itself calls.** *(fixed by T11)* It defined
  `update(self, item, dataTreeView)` on a `QWidget`, so the no-argument
  `update()` that schedules a repaint was gone: `panel.update()` answered
  `TypeError: QVizNodeDocumentationWidget.update() missing 2 required positional
  arguments: 'item' and 'dataTreeView'`. The entry point is `showNode`.
- **The click hunted the panel by object name and raised when it missed.**
  *(fixed by T11)* `onLeftClickItem` did `self.parent.findChild(QWidget,
  "QVizNodeDocumentationWidget")` and, on a miss, `raise ValueError` — out of a
  slot, where nothing shows it to the user and where, measured, it stops the rest
  of the slot. The frame now hands the panel to the view it belongs to.
- **The question every load starts with could not be answered at all.**
  *(fixed by T12)* Which occurrences a case holds was asked of the data
  dictionary with `eval("imas." + idsName + "().getMaxOccurrences()")` at **5
  places** — `QVizIMASDataSource.containsData:288`, `QVizTreeNode:365`,
  `Viz_API:628/637/646`. `hasattr(imas, 'equilibrium')` is **False** on this
  IMAS-Python: every one answers `AttributeError: module 'imas' has no attribute
  '<ids>'`. And because the first sits above `containsData`'s own `try`,
  **building the shot view of the reference case died on the first IDS of the
  list** (`amns_data`) — so no occurrence could be chosen by any gesture, and the
  guard under two of the helpers (`if availableOccurrences is None: return`) was
  dead code: that helper has no path returning None. Asked of the case instead
  (`DBEntry.list_all_occurrences`), the whole inventory of the 55 IDS names costs
  **0.10 s** against **336 s** for reading each IDS to answer the same question.
- **A double click with nothing selected answered `IndexError`.** *(fixed by
  T12)* `loadDefaultOccurrence` took `selected[0]` without looking.
- **The guard against loading one occurrence twice guarded nothing.** *(fixed by
  T12)* It was a class attribute `Lock` keyed by IDS name, shared by every shot
  view — loading `equilibrium` in one view blocked the other — and `__init__`
  wrote `Lock[IDSName] = False`: measured `{'equilibrium': True}` straight after
  a load started and `{'equilibrium': False}` again as soon as the next command
  object was constructed, before anything was asked of the case.
- **The slice choice travelled as an integer, and three of the four views got no
  name.** *(fixed by T12)* An unrecognised name became **1 in silence** (`all
  time slices`, `All slices`, `None` all answered 1); the four are handed to the
  menu in the order 3, 2, 1, 4; and `getLabel()` answered **None for all four**
  coming out of `getAllStrategies()`, because the flag it read was raised only in
  the branch of the fourth — which is also the flag that made "Add a new view"
  reachable, so a view built with the default choice could never be looked at
  another way.
- **An index past the end was refused four seconds later, in the wrong place.**
  *(fixed by T12)* Slice 49 of the 49 the reference `equilibrium` occurrence
  holds: `ValueError: Bad input from user: time index too large.` — naming
  neither the count nor the bound. The dialog that asks for it had **no parent**
  and its spin box accepted anything up to **2147483647** while 0 to 48 are valid.
- **The walk built the tree in a thread that does not own the widget.** *(fixed
  by T12)* `updateView` started a Python thread and waited on a `Condition`:
  measured, it ran in `Dummy-1` while the main thread sat in `cv.wait()`. `load`
  overrode its own `asynch` argument with `False` and handed the walk to a fresh
  `QThreadPool` per load, a pool the caller cannot wait on.
- **Two things were left behind by every load, and one attribute was written for
  nobody.** *(fixed by T12)* A `QProgressBar` per load, `hide()`-ed and never
  `close()`-ed — a dozen loads, a dozen live windows; and `limited_nodes` set on
  every array of structures the walk met, read by nothing in the package.
- **A menu that imported the world, once per right click, once per view.**
  *(fixed by T13)* `QVizPluginsHandler` called `VizPlugin.getPluginsObjects`,
  which imported every registered plugin and built its objects anew: **0,999 s**
  for the first menu of a process on the reference case, 0,0425 s for the second,
  0,0008 s after that — 4,186 s cold for that one call, and the launch chain
  imports no plugin at all, so the whole cost (matplotlib among them) was paid on
  the gesture. Nothing was kept either, so a `.ui` plugin rebuilt its
  `QMainWindow` and `sys.path.append`-ed its folder on every click.
- **One plugin's exception took every other plugin's lines with it.** *(fixed by
  T13)* A plugin raising inside `getEntries` left **0 entries** in the menu and
  the exception escaped the right click; a stale entry in the registration table
  did the same with a `ModuleNotFoundError`. Now each plugin is asked on its own
  and the one that failed is named in the log of the case, the others keeping
  their lines.
- **The words of an entry were read at its position; its number was never used.**
  *(fixed by T13)* `getAllEntries()` is documented as `[(number, description)]`
  and `execute(vizAPI, pluginEntry)` is documented as receiving that number; the
  menu indexed the list by position and gave every entry the same id, **9999**,
  under a `# TODO: properly set ID` — then read that id back and threw it away.
  A plugin declaring entries `[2]` with two descriptions answered `IndexError`;
  asking the same handler twice for the same menu showed **6 lines instead of 3**.
- **A plugin was invisible if it did not inherit, and the fallback tables named
  plugins that are not registered.** *(fixed by T13)* A plugin honouring every
  documented method but not subclassing `VizPlugin` got **no line and no word**;
  `getPluginsConfigurationFor` and `getEntriesFor` answered `KeyError` for both
  registered plugins, because their tables named only the two that are not; and
  `getAllEntries` was declared twice, the static table shadowing the contract
  stub, so `VizPlugin().getAllEntries()` answered `TypeError: missing 1 required
  positional argument: 'pluginsName'` — the contract the manual documents was
  unreachable. `getMenuItem` read `self.getSubjects()`, which no class in the
  package defines.
- **A sub-menu with nothing in it, on 42 of the 55 IDS names.** *(fixed by T13)*
  The 'Plugins' heading was added before anyone asked, and Shift+right click —
  which offers the plugins and nothing else — opened an empty menu.
- **The sub-menu died before the click could reach it.** *(fixed by T13)* Built
  with `parentMenu.addMenu(title)`, its C++ object belongs to the Python wrapper
  that call returns; the gestures dropped that wrapper, and reading the sub-menu
  back from its action answered `RuntimeError: Internal C++ object
  (PySide6.QtWidgets.QMenu) already deleted`. The menu is now given its parent at
  construction, as the rest of the package does.
- **The plugins were asked about the view's selection, not the node under the
  cursor.** *(fixed by T13)* The manual says a plugin decides from
  `self.selectedTreeNode`; the framework handed it the selection, and with
  nothing selected right-clicking a quantity answered `AttributeError:
  'NoneType' object has no attribute 'getDataType'`.
- **A `.ui` plugin's window came out hollow, and the Profiles plugin hid its
  failure behind a logging error of its own.** *(fixed by T13)* `from PySide6
  import uic` does not exist on this stack; with the loader this PySide6 does
  have, `examplePlugin.ui` loads but Qt answers "unable to create a custom
  widget of the class 'exampleWidget'; defaulting to base class 'QWidget'" and
  drops the 10 connections it makes to that class (the SOLPS plugin's window
  answered the same way — 3 connections, no child of the class it declares — and
  that plugin is out of the repository since T14), and `createWidget` is never
  called. Such a plugin is now refused by name, naming
  the class. `VizProfiles_plugin` chained a second `getLogger` onto the first —
  `AttributeError: 'Logger' object has no attribute 'getLogger'` — which is what
  the user read instead of the `AttributeError` of the sixth and last
  `eval("imas." + ids + "…")` of the package; its `data_found` built a name with
  `exec` and read it back with `eval`.
- **The manual documented two tables no code defines.** *(fixed by T13, in the
  manual)* `plugin_QTdesigner.rst` describes `RegisteredPluginsConfiguration` and
  `EntriesPerSubject`; neither exists. What the same howto *does* show — a
  `.ui` plugin registered as a dictionary inside `RegisteredPlugins` — is what
  the new catalog reads.
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
| T9 | "Apply Configuration" / save a configuration | One module owns the file — `QVizConfigurationFile` (both kinds, read by root element, the two shapes the old writers produced still readable) — and four commands use it: `QVizSavePlotConfiguration` (the window's button), `QVizSaveNodeSelection` (the menu entry), `QVizSelectFromConfiguration` (applying either to a shot view, loading the IDS a path belongs to), `QVizApplyConfigurations` (the two-tab window, re-read from the folder on every show) | the hand-parsed `GraphicsWindow/PlotItem/sourceInfo` XML | fait — **correction of the "kills" as first written**: the row announced two files (394 + 335 l.); measured, four modules go — `QVizSavePlotConfig.py` (342), `QVizConfigurationListsWindow.py` (399), `QVizSaveSignalSelection.py` (117) and the `QVizSelectSignals.py` (151) that T8's row left standing — **1009 lines**, plus 94 lines of `QVizGlobalOperations` helpers (`getConfFilePath`, `printCode`, `getConfFilesList`, `getConfigurationFilesDirectory`, `getSignalsPathsFromConfigurationFile`) and the `ET` import they justified. `makeIMASPath`/`makeIMASPaths` stay: the new reader uses them on the old files, whose paths are spelled with dots and brackets. `Viz_API.GetPlotConfigurationPath` and `GetPlotConfigurationPath`'s documented scripting role stay, re-pointed at `QVizSelectFromConfiguration`; so does `getNextPanelKey`, which nothing calls and nothing in T9 owns |
| T10 | "Export to IDS" | `onExportToLocal` → `QVizExportToIDS`: `QVizExportTarget` holds the four fields and validates them where they are typed, `QVizExportDialog` asks for them (and the backend as a choice), the write entry is built at the data dictionary the IDSs were read at and closed in a `finally`, and what is written is the cache the plots read — each IDS on its own occurrence, a refused IDS named in the log without costing the others | the inline dialog, the bare `except:` | fait — **correction of the "kills" as first written**: the row announced "a 100-line inline dialog" and two kills; measured, four things go. The dialog in `QVizDataTreeViewFrame` is **127 lines removed** (15 added back: a 7-line slot and its import), and with it the three Qt classes it was the only user of (`QDialog`, `QLineEdit`, `QPushButton`). `QVizIMASDataSource.build_legacy_uri` (the `from imas import _al_lowlevel as ll` path) and `QVizIMASDataSource.exportToLocal` (70 l., never called by the gesture) go too — 55 lines out of the data source, 47 back as `caseUri`, the spelling `_readCaseFromUri` reads back and the one `QtVIZ_GUI`'s `-u -d -s -r -b` path and the example plugin call. That lift is the **`build_uri` xfail of `test_02_data_source.py` going green**, the first xfail of this work to die. Four modules added, 485 l.: `QVizExportTarget` (150), `QVizExportToIDS` (206), `QVizExportDialog` (125), `__init__` (4). Nothing was grafted: the bare `except:` is gone, and so is the `entry.open()` call that was its whole failure — an entry built from an URI is open at construction |
| T11 | Node documentation on left click | `onLeftClickItem` → `QVizNodeDocumentationPanel.showNode(node)`, drawing what `QVizNodeFacts` decided: the name, the documentation, the data-dictionary status, the units, the shape and size, the zeros and the nan/inf counts, the extremes of the entries that *are* numbers, a preview bounded to 200 values at each end — and, when the read cannot answer, the reason, said once | `QVizNodeDocumentationWidget.py` (651 l., 12 methods, 20 `QLabel`s), its `np.set_printoptions(threshold=sys.maxsize)` — process-wide, never undone — its `update(self, item, dataTreeView)` sitting on `QWidget.update`, the 9 labels prefilled with `/`, the 7 `showFieldsFor…`/`hideAllFields`/`showAllFields` switches that prefilled them, the two bare `except:`, the duplicated dynamic-1D and static-1D branches, and in the view the `findChild(QWidget, "QVizNodeDocumentationWidget")` lookup with its `raise ValueError` | fait — **correction of the "kills" as first written**: the row announced nothing; measured, the widget is 651 lines (650 by `wc -l`) and five of its habits were answering wrong on real nodes, listed in §2. What replaces it is 335 lines in three files — `QVizNodeFacts` (231, no Qt: the facts, and the reason a read failed), `QVizNodeDocumentationPanel` (100, no arithmetic: the rows it is given, rebuilt from nothing at every click), `__init__` (4). `QVizDataTreeView` gives back 12 lines and takes 27 — the `ndw` dummy became the panel the frame hands over. Nothing was grafted: no `set_printoptions`, no `findChild`, no `raise` out of a slot, no prefilled label, and a scalar is read off the tree rather than through the runtime, which is the only way it does not answer `<IDSString0D …>` |
| T12 | Load an occurrence — double click, Return, "Get … data for occurrence", "Add a new view", Shift+right click | `QVizCaseOccurrences` (the case answers which occurrences hold data, `unloaded`/`nextUnloaded` on top of it), `QVizTimeSliceSelection` (one object per choice, knowing its menu words, the words the tree shows and the window it wants), `QVizLoadOccurrence` (one command, guard on the view that owns the load), `QVizOccurrenceMenu` (both sub-menus and the one question the fourth choice asks, parented to that view and bounded by what is in memory) | `QVizViewLoadingStrategy.py` (94 l., identifiers 1-4 hardcoded, `setIdentifier` defined twice), `QVizLoadDataHandling.py` (109 l.), `QVizLoadSelectedData.py` (43 l., the class-level `Lock`) — **246 lines**; and in the modules that stay: `containsData` (21 l.) and the `Worker(QRunnable)` wrapper (8 l.) out of `QVizIMASDataSource`, its `asynch = False` override and the per-load `QThreadPool`, the `load` override of `QvizIMASPublicDataSource` (22 l.), `QVizDataTreeView`'s `cv = Condition()` and the thread `updateView` waited on, the `eval("imas.<ids>()")` of `QVizTreeNode.hasAvailableData`, the three of `Viz_API`, and the `limited_nodes` attribute nothing read | fait — **correction of the "kills" as first written**: the row announced three identifiers and one duplicated method; measured, five `eval("imas." …)` sites answered `AttributeError` on this IMAS-Python and one of them sat above `containsData`'s `try`, so **the shot view of the reference case did not build at all** — there was no occurrence to load. `QVizDataTreeView` gives back 158 lines and takes 250 (`+204/-…` on the diff): the empty tree now asks the case (0.10 s for the 55 IDS names, 1.22 s to build where it used to raise), `updateView` builds in the thread that owns the widget, and `homogeneous_time` is read off the instance the walk loaded instead of by reading the case. 446 lines in five new files replace 246 in three. One limit kept from the old behaviour and said in the code: one index applies to every dynamic array of the IDS, so the refusal names the array that cannot take it (`grids_ggd: 30 is not a time slice of this IDS: it holds 1`) |
| T13 | Plugins in the menu | `QVizPluginCatalog` (the registered plugins of one shot view, imported and built **once for it**, each asked on its own, every refusal named in the log of that case) and `QVizPluginMenu` (the sub-menu the three gestures share; a line carries its plugin and the entry number *that plugin declared*, and the caller is told how many lines there are) | `QVizPluginsHandler.py` (140 l.) and `QVizPluginsPopUpMenu.py` (29 l.) — **169 lines**; and inside what stays: the four per-name lookups of `VizPlugin.py` (`getPluginsObjects`, `getPluginsNames`, `getPluginsConfigurationFor`, `getEntriesFor`) and the static `EntriesPerSubject`-style table that shadowed the `getAllEntries` contract — 45 lines out (156 → 111) — `getMenuItem`/`getSubjects`, the id `9999` and the dispatch by position, the `except:` with `traceback.print_exc()` and `print("Unable to execute plugin…")`; in the registered Profiles plugin, the **sixth and last `eval("imas." + ids + "…")` of the package**, the `logging.getLogger(uri).getLogger(uri)` chain that hid it, and the last `exec`/`eval` of the package (5 dead imports given back) | fait — **correction of the "kills" as first written**: the row announced no kill ("plugins call the frames, so they follow them"); measured, that is backwards — the *menu* is what the gestures call, and both of its modules die now, 169 lines. Two of the three claims in that parenthetical are also wrong about where the cost is: the launch chain imports **no** plugin, so all of it (matplotlib among them) sat on the gesture — **0,999 s** for the first right click of a process, 4,186 s for `getPluginsObjects` alone cold. What the new pair adds: 286 + 98 lines. Two limits kept and said in the code: a **.ui plugin drawn around a widget class of its own cannot be shown on PySide6 6.6** (measured: `QUiLoader` falls back to a bare `QWidget` and drops 10 connections for `examplePlugin.ui`, 3 for `SOLPSplugin.ui`; overriding `createWidget` changes nothing, it is never called) — it is refused by name, naming the class; and `Viz_API`'s documented plugin hooks stay as they are |
| T14 | The SOLPS plugin — a window drawn in Qt Designer, and the manual page that promises it | nothing: no replacement was written, because nothing was reached. `QVizPluginCatalog` (T13) already refuses a `.ui` drawn around a widget class of its own by name, which is what the user of that plugin would have needed to be told | `imasviz/VizPlugins/viz_solps/` — **11 files, 1 451 lines**: `SOLPSwidget.py` (292), `SOLPSplugin.ui` (114), `SOLPSplugin.py` (80), `run_plugin_ui_standalone.py` (20) and `src/` (`getIDS.py` 380, `getEPGGD.py` 204, `GGDDialog.py` 186, `quadPlotCanvas.py` 103, `getIDSplugin.py` 72, two empty `__init__.py`); the commented `SOLPS_UiPlugin` registration; the manual's two sections (**108 lines** of `manual/plugins.rst`, 279 → 171) and its 6 figures; `howto/plugins/plugin_QTdesigner.rst` (**1 338 lines**) and its entry in the plugins toctree | fait — measured before deleting, because "unused" is a claim and not a fact: `RegisteredPlugins` holds **2** entries and none names SOLPS; the import sweep collected **9** of its modules, 5 of which import — and are reached by nothing outside the subtree, which imports its siblings as `src.<mod>`; **4 of the 5 xfails** of the sweep were that subtree. Handed to `QUiLoader`, its window comes out as a `QMainWindow` holding 3 `QPushButton`s and **no child of the `SOLPSwidget` class it declares**, with Qt reporting the 3 dropped connections (`setEPIDS`, `setGGDdata`, `plotData`) — the same hollow window T13 refuses by name. So what dies is a manual promising a window that cannot open on this stack, and 4 expected failures. **Kept, and said here so it is a choice rather than an oversight: the media that page used.** `howto/plugins/images/` holds 34 PNGs (1,4 Mo); 3 are still used by the two howtos that stay, so **31 are orphaned**, as is `_static/QtDesigner_and_IMASViz_plugin_short_demo.mp4` — they document `viz_example/`, which stays in the tree; `release_notes.rst` keeps its historical line. Suite: **688 passed, 2 xfailed**; sweep: **117 modules, 116 passed / 1 xfailed** |
| T15 | The harness dropping the plot frames it shows — the segfault that made a journey test unthinkable | `support/ownership.py`: `keep()` gives the harness the holder the application has (`Viz_API.figureframes`), and a passive watch records every frame built through weak references, so the measurement cannot be what keeps anything alive. An autouse fixture in `conftest.py` reports a hazard on the test at fault, once, at its own teardown | The dropped owners in three files: `test_25_plot_as_slices.py` (4 frames — the one test there that builds its two commands by hand, outside `support/plotting.py` and its `_keptAlive` list), `test_35_selection_entries.py` (1), `test_36_table_plot_entries.py` (6) — their shot fixtures parented a real `Viz_API` to a `QMdiArea` hanging off an unpowned `QObject`, so the frames the entries *show* died with the fixture's locals; and the unreadable failure mode itself, a dead interpreter in a file several away from the one at fault | fait — measured first, in weak references only: of the **110** plot frames a run builds, **79** lose their wrapper before the run ends, **11** of them after being shown and without ever being closed (6 / 4 / 1 across those three files) — the only ones Qt can paint, which is why the run died at a fixed position, 3/3, with `Fatal Python error: Segmentation fault` in `GraphicsView.paintEvent`. The first rule was too wide and said so loudly: "no frame may die" produced **479 cascading failures**, because a frame never shown is never painted, and closing one is what the production refusal paths are *tested* for (5 of them). What is enforced now is "shown, then gone without being closed". Suite: **695 passed, 2 xfailed**, exit 0 on three consecutive runs; the same three runs, with one failing test inserted early, used to die at test 54 |
| T16 | One continuous user journey: open a case, browse its tree, load an occurrence, select, draw, save the selection, replay it in a second window on another shot, close that window | `tests/test_45_one_user_journey.py` — 13 tests over two real cases, opening its views the way the application does (`QVizDataSourceFactory` then `Viz_API.CreateDataTree`, which is what `QVizOpenShotView.Open` calls) and never touching a frame constructor | **nothing in `imasviz/`** — this task deletes no legacy line, and says so. What it removes is the reason not to touch the frames: until now no test joined two gestures, so every seam between them was untested and unmeasurable | fait — measured before writing, and the first measurement was itself the finding: a shot view built by hand (the frame constructed in the test, a bare `Viz_API` hung on it) passes every gesture one at a time and still cannot draw a selection of two, because `QVizPlotAsSlices` takes `all_DTV=True` by default, asks `api.DTVlist` for every opened view, finds it empty, and answers `ValueError: No signal selected.` on a selection the view itself holds. On the reference case: 55 roots and **0 signals** until an occurrence is loaded; `occurrencesOf('equilibrium')` answers `[0, 1, 2, 3]` from the case; loading occurrence 0 gives **3 368** leaves, the walk taking 0,58 s; three selected leaves draw **one** `QVizCurvePlot` (`SlicesPlot1`) — the two-axis leaf `coordinate_system.r` is sent to a picture frame that finds `no values in the image` and is dropped, so this case cannot exercise the picture branch at all; the table refuses that same leaf, naming it; the `.lsp` written for 54924 selects **3** in a window on 55799 (the file carries the uri it was written from, and `findNode` matches `getPath()` plus the occurrence — the manual's "apply this selection to another database"); `hard_x_rays` there adds **5 687** signals and yields `SlicesImage1` with `isDrawing()` True; closing that window leaves 1 frame, 1 view and no record for 55799. Two facts the suite refuses to pin as counts: the file is written in click order, not sorted, so the assertion spells the click order; and the reference case arrives at **12** entry references in a full run, because `QVizDBEntryRegistry` is one dict for the process and other files open the same case — that one became an invariant (unchanged by closing another case) after the number was measured. Suite: **708 passed, 2 xfailed** in 46 s (was 695 in 39 s) |
| T17 | How much tree each of the four time-slice views really builds — the manual promises *All / One over 10 / Specific / First*, no test had ever walked one | `tests/test_46_time_slices_on_a_real_case.py` — 10 tests, one cold shot view per strategy, the case opened the way `QVizOpenShotView.Open` opens it | **nothing in `imasviz/`** — this task deletes no legacy line. What it retires is the excuse that the sizes were unknowable: `test_42_load_an_occurrence.py` pins the plumbing of the choice against a fake source that records the call, and could not say what each choice builds | fait — every number measured on a cold view before it was written (WEST 54924 run 0, DD 3.35.0). A plain load keeps slice 0: **3 368** signals, the occurrence node reading `occurrence 0 [displaying first time slice]`; the case answers **49** for its widest dynamic array and its two dynamic arrays are `time_slice` (49) and `grids_ggd` (1) — the manual's sentence, read off the case; one over ten keeps 5 slices for **16 820** signals; all 49 cost **164 792** signals and **26 s** of walking, the slowest thing in the suite by a wide margin. Three facts the first probe got wrong. An index past the end never reaches the caller: `QVizIDSViewParser.run()` catches the `ValueError` and consigns it to the log of the case, so the refusal is an ERROR line naming the array, its count and its bound. A refused view loads **nothing at all**: `atIndex(49)` on a cold view leaves 0 signals and `loadedOccurrences` empty, so the occurrence is not even marked loaded — not "the previous view survives". And the narrower array only refuses when the walk meets it: with `Ignore_GGD=1` (what the harness leaves it at) `grids_ggd` is skipped and `atIndex(1)` is accepted; with `Ignore_GGD=0` the same index is refused naming `grids_ggd`. One defect pinned as what happens today, not as a promise: a second view whose slices overlap the first **duplicates** them — slice 0 then one over ten gives 3 368 + 16 820 = **20 188** signals for five distinct slices, with the `time_slice(0)` paths present twice. Suite: **718 passed, 2 xfailed** in **87,9 s** (was 708 in 46 s) — the +42 s is the price of walking the same occurrence four times, and it is written down rather than hidden |
| T18 | The load every menu entry actually takes — `asynch=True` is the default, and no test had ever watched the window between the call returning and the tree being built | `tests/test_47_loading_asynchronously.py` — 9 tests on the reference case, plus the fix: the walk no longer touches a window it does not own, and `QVizIMASDataSource._loadFinished` takes the progress bar down on the thread that made it | **the walk taking a window down from its own thread** — three `closeProgressBar()` calls in the failure branches of `QVizIDSViewParser.run()`, replaced by one guarded call (synchronous only) and one in the source's `finished` handler; with them goes the `closeProgressBar()` docstring's claim that closing a bar is the walk's business | fait — measured before writing, and the measurement hung, which is how the defect was found. The flight: `execute()` returns in **0,010 s** having built nothing — 0 signals, the view saying the load is in flight, one parser held alive; the walk runs on `Dummy-1`, the tree is built on `MainThread` (**6 058** signals for `magnetics`, **3 368** for one slice of `equilibrium`); while a walk runs, the same occurrence asked of the same view meets the guard and starts nothing, asked of *another* view goes through — which is what the retired class-level `Lock` prevented. The defect: on the refusal path of an asynchronous walk, `run()` closed the progress bar from the walk's own thread, and on this Qt stack that call **never returns** — reproduced with no IMAS and no case in it, a `QThread` staying inside `QWindow::close()` past a 20 s watchdog while the GUI thread pumped events. So the thread is lost, `finished` never fires, the parser is never dropped, the occurrence stays in `loadsInProgress` for the rest of the session and every later request for it is refused as already being loaded — and the bar stays on screen. Reproduced a second time as a hanging pytest run, which is why the fix precedes the green. One accumulation pinned rather than fixed: the bar of a finished load is closed, not destroyed, so one window stays alive per load (asserted as `+1`, off screen). Suite: **727 passed, 2 xfailed** in **97,75 s** (was 718 in 87,9 s) |
| T19 | The life of a figure window — the menus that show it, the menus that delete it, and whether the window a menu drew ever reaches the screen | `tests/test_48_figure_lifecycle_through_the_menus.py` — 12 tests over one session on the reference case, from an empty registry to the last window closed, the actions triggered as the click triggers them; plus the fix in `Viz_API`: `mdiWindowOf`, and `addPlotWidgetToMDI` showing the window it embeds | **the branch decided on the name of the top-level window** — the two `frame.window().objectName() == "IMASViz root window"` tests in `ShowHideFigure` and `DeleteFigure`, replaced by one question about what the parent *is*; **the 38 menu ids of `GlobalIDs`** — counted, 38 declared, **0** read anywhere outside the declaration (`RESULT_EVENT` alone is read, at 2 sites), so the `wxDataTreeView.py` / `SignalHandling.py` / `LoadDataHandling.py` blocks they numbered go with them | fait — measured first, on a session built the way the application builds it (a root window carrying that object name, the MDI area inside it, `equilibrium` occurrence 0 = **3 368** signals). The three kinds were handed `SlicesPlot1`, `TablePlotView:1`, `StackedPlotView:1`; with nothing open the two menus come back **disabled, 0 entry each**. The defect: `QMdiArea.addSubWindow` does not show the subwindow once the area is on screen, and only one of the four plot entries calls `show()` itself — measured, the selected-signals, table and stacked entries registered and embedded windows that stayed **invisible**, named in the Show/Hide and Delete menus, never reaching the screen: 1 entry in 4 worked. The second defect is the name test: on a plain area it fails, and then Show/Hide hides the *frame* and leaves an empty window on screen, while Delete closes the frame and leaves the window visible — measured both ways before and after. The numbering is pinned as it now behaves: deleting the middle of `SlicesPlot1..3` leaves the next curve at `SlicesPlot4` (a hole is not a gift), while emptying a kind puts its number back in play (`TablePlotView:1` again, the window title agreeing); closing with the X frees the key from `figureframes` **and** `figToNodes`; and `DeleteFigure` on an unregistered key raises nothing — so the `except ValueError` wrapped around the delete slot catches a failure that cannot happen, pinned rather than killed, since it costs nothing. Suite: **739 passed, 2 xfailed** in **98,79 s** (was 727 in 97,75 s) |
| T20 | Exporting what a shot view holds into another case — and opening again, for real, what was written | `tests/test_49_export_then_open_what_was_written.py` — 10 tests on a shot view built the way the application builds one: an empty cache refusing, one occurrence loaded, a second, the export, the written case opened again by the Access Layer, the values read back | **the round trip proved on a stub** — `test_an_exported_ids_is_found_again_in_the_case_it_was_written_to` in `tests/test_40_export_to_ids.py`: a `StubTreeView` whose cache was filled by hand from an `imas.DBEntry` the test had opened itself, which proved the command can write an object it was handed and never that the gesture finds one. **No `imasviz/` code leaves with T20** — the command it exercises was rebuilt in an earlier slice; what dies here is the proof that stood in for a real one. The stubs stay where a stub is the right tool: the refusal paths, where the simulated access layer is the thing under test | fait — measured first, on a real view. A view whose case is open and nothing loaded answers `data_entries == {}` and refuses with "no IDS is open". `pulse_schedule` occurrence 0 costs **0,34 s**, puts one key (`pulse_schedule/0`) in the cache and **264** leaves in the tree; `equilibrium` occurrence 0 costs **4,6 s** and takes the tree to **3 632**. The command finds the two IDSs named by the cache keys, and the instance it is handed **is** the cached one, not a copy it fetched. Written in **0,85 s**: `master.h5` **2 056** bytes, `equilibrium.h5` **13 326 708**, `pulse_schedule.h5` **83 618**. Reopened (**3,63 s**): occurrence `[0]` for each, the same filled-path counts as the source (**133** / **15**), `ip` -77009.31617883372, a `time` array of **49** samples equal element for element. Two facts the sentence "export what is open" hides. The tree keeps **one** time slice — `time_slice[0]` on all 3 368 leaves — while the cache and the written case keep all **49**: what the user sees and what the user exports are two amounts, and the second is larger. And `data_entries` is `QVizDBEntryRegistry.ids_cache(uri, mode, dd_version)`, **one dict per case for the whole process**: in a full run the reference case's cache already held `calorimetry/0` through `tf/0` before this file loaded anything, and an export from it writes every one of those. The application never meets that — `QVizOpenShotView.Open` reuses the one view of a case — so the file works on a case of its own, copied through the Access Layer: a file-system copy of the run answers `Unable to open HDF5 group: equilibrium`, because that run holds one 6 365-byte `master.h5` whose groups link into `../4/equilibrium.h5`. Suite: **748 passed, 2 xfailed** in **117,35 s** (was 739 in 98,79 s) |
| T21 | The life of a *case view* — opening it the way the start window opens it, hiding it, showing it back, deleting it, and the menu that offers all four | `tests/test_50_shot_views_through_the_menus.py` — 13 tests over one session built the way `QtVIZ_GUI` builds it (a root window carrying the object name, the MDI area inside it, shown before any gesture), driven through `QVizMainMenuController.updateMenu` and the actions it hands out; `QVizOpenShotView.Open` driven for the first time in the suite, where four other files rebuild its body by hand | **the three branches decided on the window's name** — `objectName() == "IMASViz root window"` in `showHideView`, `deleteView` and `deleteAllViews` — replaced by the one question T19 introduced, *what is this frame's parent*; **the four copies of `getMDI` no caller ever reached** — `QVizMainMenuController`, `QVizStartWindow` in `QtVIZ_GUI`, and one each on the view and the frame of `QVizDataTreeView`, all four gagged on that same name; the `print("QVizOpenShotView::legacy_attributes=", …)` fired on every open; the TODO that blamed Qt for a `deleteLater()` nobody dared uncomment | fait — four defects, measured first. **(1)** The two *Views* sub-menus were built with `menu_showHide.addMenu('Views')`, and the QMenu that call hands out belongs to the Python wrapper it comes back in: once `menusShowHideAndDelete` returns, the QAction still names a menu whose C++ object is gone, and reading it answers `Internal C++ object (PySide6.QtWidgets.QMenu) already deleted` — whether it dies at once is timing-dependent (a standalone probe kept it alive, a pytest run did not), the same trap T7 met in `QVizPluginMenu`. **(2)** A hidden view never came back: `ShowDataTree` showed the frame and never the window holding it, measured both through `Open` and through `ShowDataTree` itself — the T19 defect, which had not reached the shot view. **(3)** Delete released nothing: `deleteLater()` sat commented out under a TODO claiming it "results in a bug when trying to run the delete DTV feature the second time"; on Qt 6.6.3 it does not — one delete costs **0,041 s**, a second delete and a re-open answer no exception — and what the commented release was costing is counted: four openings and two deletions left **8** MDI windows in the area for **2** live views. A released window leaves `QMdiArea.subWindowList()` only once the deferred deletes are delivered (**2 → 1** after `sendPostedEvents`, where `processEvents` alone answered **2**), so the harness delivers them before counting. **(4)** On an MDI area without that object name — the branch the application does not take, commented "e.g. when running examples" — Show/Hide hid the **whole window** holding the area, and every other view in it went with it. `deleteAllViews` took an `index` no signal ever passes: the QAction answers a `checked` flag, so it was fed `False`, behaved as index 0, and emptied the lists only because the loop bound shrank underneath it. Costs: building the menu **0,31 s** the first time; opening **0,70 s**, then **0,15 s** for a second case, then **0,00 s** when the case is already open — and **0** frame for an unreachable URI, consigned to the log of the case. Suite: **763 passed, 2 xfailed** in **124,27 s** (was 748 in 117,35 s) — `tests/support/ownership.py` gained the other way out of the paint queue, because releasing a view legitimately deletes the frames nested in its window: the window is hidden first, a hide reaches the children recursively, and `test_44` pins both halves |
| T22 | The orphan the inventory lost: the legacy figure widget, and the `Viz_API` surface that still engines it | nothing — (c) deleted it. What stood there until then: `QVizPlotWidget.py` (**595** l.), `QVizPlotSignal.py` (**198** l.), `QVizCustomPlotContextMenu.py` (**454** l.) and `QvizPlotLayoutWidget.py` (**127** l.), with the **six** `Viz_API` entries that reach them: `CreatePlotWidget:698`, `GetPlotWidget:729`, `AddPlot1DToFig:750`, `plot0D_DataVsTimeCommand:795`, `plotVsTimeAtGivenCoordinate1:815`, `plotVsCoordinate1AtGivenTime:874` — plus the `nodeDataShareSameCoordinates` chain (`Viz_API:778/788`, `QVizTreeNode:838`) and the `Figure:` namespace (`FigureTypes.FIGURETYPE`, still in `MENU_ORDER`, listed by `test_30`) | **1 388 lines** across five modules went in (c) — `QVizPlotWidget` **595**, `QVizCustomPlotContextMenu` **454**, `QVizPlotSignal` **198**, `QvizPlotLayoutWidget` **127**, `QVizAbstractPlot` **14** — with **236** lines of `Viz_API` (**ten** entries, not the six first counted), **26** of `QVizTreeNode`, `FigureTypes.FIGURETYPE` and its `MENU_ORDER` entry, a **126**-line demo, the **91**-line unregistered `CompareFLT1DPlugin` with its package, and the **77**-line `test_13` that pinned the frame's axes. When this row was written it claimed no kill and said so, and the reason was a promise rather than a plan: T7's row said `QVizPlotWidget` goes with "T13 and **whatever owns `AddPlot1DToFig`**", T13 is closed, and **no row carried that owner**. Reachability measured while opening T22: it is a **closed island** — `QVizPlotWidget` is built only by `CreatePlotWidget`; `QVizCustomPlotContextMenu` is attached only to `QVizPlotWidget:239` and `QvizPlotLayoutWidget:79`, and that layout widget has **no production caller at all** (only `test_11` and a `VizExamples` demo); `viz_tests/CompareFLT1DPlugin.py:35` is **not registered** (`RegisteredPlugins` has it commented out); `test_35_selection_entries.py` turned out **not** to be a consumer, as an earlier count of mine claimed. The one door left is the registered Profiles plugin, whose own `CustomizedViewBox:198/431/441` calls three of the six entries and so creates `Figure:` windows the manual documents (`plugins.rst:137-148`, step 6). **Step (a) kills nothing either**: it repairs two defects in the island's own code and adds the test that walks the door; the 1 374 lines were still ahead of it then — (c) took them, and **14** more with the `QVizAbstractPlot` base nobody had counted | fait — **all three steps are done** (`5d4830d`, `5cff391`, `015e51e`): the door was walked, what it opened was measured, and the island is gone. (a) had to fix two defects first. It was impassable: since T24 the plugin reaches `execute()` and registers `PlotView:1`, then raises `TypeError: unsupported format string passed to IDSFloat0D.__format__` labelling its time slider (`VizProfiles.py:504`) — an `IDSFloat0D` is a `numbers.Real` wrapper with `__float__` and no `__format__` — which, raised inside `setUI`, left the whole control row under the tabs unbuilt (`slider_time`, `spinBox_timeIndex`, `lineEdit_timeValue`, `plotButton` absent, `addNewTabsButton` `None`); and `CustomizedViewBox.getMenu` raised `AttributeError: 'ViewBoxMenu' object has no attribute 'leftMenu'`, because on pyqtgraph **0.13.7** the "Mouse Mode" sub-menu is a local of `ViewBoxMenu.__init__` and only `mouseModes` survives. So the manual's steps 4, 5 and 6 (`plugins.rst:137-148`) were not slow features, they were no features. Measured on the reference case through `tests/test_51_profiles_plugin_figure_menu.py` — the suite's **first** plugin-runtime test, `10` tests: the case holds occurrences **[0,1,2,3]** of `equilibrium` and `core_profiles` and none of the three other supported IDSs, so the occurrence question is always asked, of the view that owns the menu, bounded 0..3; `run` returns in **4,94 s**, the window is on screen **6,5 s** later, registered as `PlotView:1`, a **top-level** window (`parent() is None`), **2** tabs, **41** plots, **41** curves, every view box a `CustomizedViewBox` — **37** curves over the **101**-point radial coordinate, **4** over their own **72** points (the boundary outlines carry their own base); slider **0..48**, `n_t = 49; t_min = 32.13`, `t_max = 48.55`, time field `32.1336784362793`; `getMenu()` **0,03 s** for **13** actions, the same 13 on three openings. Its `Plot <quantity> to` sub-menu holds **0** line while no curve figure exists — it lists the figures whose curves run along the same abscissa — and the two new-figure entries built `Figure:1` (**101** points along coordinate1) and `Figure:2` (**49** along time) in **0,05 s** each, after which the sub-menu listed both. **Step (b) re-pointed those three calls** at `QVizPlotOneNode`, the command the shot view's menu runs: the same two gestures now build `SlicesPlot1` (a `QVizCurvePlot` embedded in the MDI area, **101** points, **0,013 s**) and `SlicesPlot2` (**49** points along time, **0,061 s**), the sub-menu lists those, and choosing one of its lines adds a curve to the figure it names without opening a window. Same curve, same abscissa, same cost — what changed is which frame holds it. The abscissa gate moved from `QVizSignalHandling` to `Viz_API`, next to the `figToNodes` record it reads (**14** lines out of the menu controller, **21** into the registry): the shot view's menu and a plugin's menu must not answer that question differently. Measured, all 41 quantities the plugin draws answer `curveAxisKey = ('LEAF', 'equilibrium', 'time_slice(itime).profiles_1d.psi')` — one leaf axis (the psi coordinate) plus a time base — and a quantity with two axes to draw gets no line at all. **(c) deleted the island** (`015e51e`): the five modules, the **ten** `Viz_API` entries, the `nodeDataShareSameCoordinates` chain on both classes, and the `Figure:` namespace with its `MENU_ORDER` entry — four of the registry's helpers (`GetFiguresCount`, `GetNextKeyForFigure`, `GetFiguresKeys`, `GetFigureKey`) and three of the menu controller's (`showHideFigure`, `deleteAllFigures`, `deleteFigure`) lost their `figureType=FIGURETYPE` default with it, because a call naming no kind used to mean the dead one silently. What the user loses was measured, not assumed: the right click on a new figure answers pyqtgraph's own **4** entries (`View All`, `X axis`, `Y axis`, `Mouse Mode`) plus the scene's **1** `Export...` line — measured on both `QVizCurvePlot` and `QVizImagePlot`, and the registered exporters are the five pyqtgraph brings (CSV, HDF5, image, matplotlib, SVG), so the manual's Export feature survives because it came from the scene and not from the menu that went. What survives **only inside the Profiles plugin's window** is `Configure Plot`, `Show/Hide error bars`, `Show error bars (with slicing)` and `Show/Hide confidence bands`, which its own `CustomizedViewBox` still builds — and `QVizPlotConfigUI` stays in the package for exactly that reason, which is also what T23 now reaches. Suite: **760 passed, 2 xfailed** in **129,19 s** (was 776 in 126,47 s) — the 16 are 6 from `test_13`, 3 from `test_11`'s layout grid, and **7** cases of the import sweep, which walks **108** modules where it walked **115** |
| T23 | "Export plot" — the exporter whose own docstring asks to be deleted | pyqtgraph's own `MatplotlibExporter`, and nothing else: the gesture is `GraphicsScene`'s own `Export...` action (`GraphicsScene.py:102`) and the dialogue fills its format list from `Exporter.Exporters` each time it is built (`exportDialog.py:104`) | `QVizMatplotlibExporter.py` (**190** l.) — the class, the `QVizMatplotlibWindow` it opened and the `register()` at its end — and the `VizGUI/VizExporters/` directory around it, which held no `__init__.py` and nothing else; `CustomizedViewBox.updateExportersList` (**14** l.), the call its constructor made (`:67`), and the `from pyqtgraph.exporters.Matplotlib import Exporter` that existed only to feed it | fait — measured before touching anything. `Exporter.Exporters` on the pinned stack answers **5** names (`CSV of original plot data`, `HDF5 Export: plot (x,y)`, `Image File (PNG, TIF, JPG, ...)`, `Matplotlib Window`, `Scalable Vector Graphics (SVG)`); the dialogue of a curve figure lists exactly those **5**, and **4** once a `CustomizedViewBox` exists — `Matplotlib Window` being the one missing, which is the format the manual promises ("Export plot", `other_GUI_features.rst:130`, and the export list of `plotting_1d_arrays.rst`, "matplotlib window"). Two things made that worse than a stale class. The copy the patch existed to install was imported by **nobody** in the package, so its `register()` never ran, the name the patch looked for (`Matplotlib Window (v2)`) was never in the list, and the patch only ever **subtracted**. And `Exporters` is a **class** attribute read when the dialogue is built, so the subtraction reached every figure of the process: the test opens the dialogue of a figure the plugin never touched and still asks for it. That predates T22(c) — the deleted `QVizCustomPlotContextMenu:58` did the same — so it was recorded as a defect on both paths, and it made T23 cheaper than it looked: deleting the class and its patch **restores** a documented entry instead of replacing one. The two defects the class cites against pyqtgraph **0.10.0** are not what 0.13.7 does: the stock exporter multiplies the data by the axis' `autoSIPrefixScale`, so a quantity of 1,5e6 / 2,4e6 arrives labelled `gap (x1e+06)` carrying **1,5** and **2,4** — label and values agree; and closing every matplotlib window of a session fired `aboutToQuit` **0** times, the window being a top-level window held in `MatplotlibExporter.windows` while the main window stays on screen. What the replacement answers on a figure this application drew: **2** matplotlib lines for **2** curves, one axes, the figure's own labels; the first export of a process costs **1,05 s** (it is where matplotlib is imported), **0,03 s** once it is. **No documented feature dies** — the manual describes the gesture and the four formats and never named the class, and the entry it documents is what the deletion brings back. **`test_57`** pins the `Export...` action, the five names in list order, a `CustomizedViewBox` being built without taking any of them away, the two lines, the scientific notation agreeing, and a walk of the package's sources refusing the text `Exporter.Exporters`: one line in one view box costs a documented format to every figure of the session. Suite: **817 passed, 1 xfailed** in **125,84 s**; sweep **107** modules, **106** import — the deleted file was one of them |
| T24 | A registered plugin that could no longer reach its own case | `tests/test_43_plugins_in_the_menu.py` — `2` tests and a stub shaped like `VizProfiles_plugin`: it does not call the base constructor, so nothing but the framework can give it a view | nothing leaves, and the row says so: what this removes is the **silence**, not the code — `QVizPluginCatalog` bound the node and not the view, while the contract it documents says both are set when the menu is built. The handler the catalog superseded called `setDataTreeView` on every plugin (`VizPlugin.py:97` of `467d3db^`); the catalog kept the method on the base class and stopped calling it | fait — measured on the reference case: the registered Profiles plugin answered **every** entry with `AttributeError: 'VizProfiles_plugin' object has no attribute 'dataTreeView'`, raised on the first line of `execute()` where it asks its view which occurrences the case holds. What hid it for three slices is the guard, not the binding: `run` logs `Plugin %s failed: …`, so a test asserting that a failing plugin is *named in the log* passes over an unbound one. Costs paid before the failure: opening the view **1,32 s**, asking the `equilibrium` node what is offered **0,89 s** for **3** entries, running the first entry **4,91 s**. What the same probe found and this row does **not** fix, recorded rather than quietly patched: the plugin gets as far as registering `PlotView:1`, then raises `TypeError: unsupported format string passed to IDSFloat0D.__format__` labelling its time slider (`VizProfiles.py:504`), and the probe added that it builds **0** plot — **that count was wrong, and T22 corrected it**: it came from `findChildren(pyqtgraph.PlotItem)`, which answers **0** on a `GraphicsLayoutWidget` whatever is drawn there, because such a widget keeps its `PlotItem`s as *scene* items and not as Qt children. What that window really drew was **41**. Both defects are fixed in T22's first step, which runs the entry and pins the count. And this case holds **4** occurrences of `equilibrium`, which the plugin asks through a modal `QInputDialog` that sat **240 s** offscreen until the watchdog killed the process. Suite: **765 passed, 2 xfailed** in **127,16 s** |
| T25 | Style a curve by hand, and show its error bars or its confidence band — on the figure that drew it | `QVizCurveErrors` (**289** l.) — the three entries the manual names, the bars, the band, the step question, the refusal by name and the beam bound, written **once**. `QVizCurvePlot.__init__:79-80` builds one over its own view box and binds the three lines onto the figure's menu; `plot()` and `refresh()` call `errors.refresh()`, because a bar left over the samples the curve no longer draws is not stale but wrong. `CustomizedViewBox:69` builds one over itself and its menu calls its three toggles — what the plugin keeps is its menu and the one thing the shared object cannot know, which curve came from which node (`errorQuantities`). `tests/test_58_error_bars_and_confidence_bands_on_the_figure_that_drew_them.py` — **14** tests on the reference case | the plugin's copy: **202 lines out of `CustomizedViewBox.py`, 445 → 272** — eleven methods (`showHideViewConfidenceBands:227`, `removeConfidenceBands:235`, `updateConfidenceBands:252`, `updateErrorBars:258`, `removeErrorBars:268`, `showHideViewErrorBars:284`, `showHideViewErrorBarsWithSlicing:292`, `addConfidenceBands:308`, `addConfidenceBandsForDataItem:317`, `addErrorBars:355`, `addErrorBarsForDataItem:376`, HEAD numbers) and the four imports only they used (`numpy as np`, `logging`, `QtCore.Qt`, `QInputDialog`). The three titles stop being spelled twice: both menus read `ERROR_BARS`, `ERROR_BARS_SLICED`, `CONFIDENCE_BANDS`. **`Configure Plot` is not carried and nothing of it dies**: `showConfigurePlot:224` and `QVizPlotConfigUI` (**1 342** l.) stay as they were, and that remaining entry gets its own row — T32 | fait — measured first, and this row corrects the count it opened with: the file was **445** lines, not 466, and the copy was **202**, not 311. On a curve figure of the reference case the right click goes from pyqtgraph's **4** lines to **7**, in the order pinned: `View All`, `X axis`, `Y axis`, `Mouse Mode`, then `Show/Hide error bars`, `Show error bars (with slicing)`, `Show/Hide confidence bands`. What the case answers for `magnetics/flux_loop(0)/flux/data` (**6 058** signal nodes in that occurrence, **1 681** with both error siblings, **4 377** with neither, **none** with only one — so "one and not the other" is this case leaving a field unfilled, not a dictionary shape): **17 344** points under **one** `ErrorBarItem`, symmetric because only the upper is filled, drawn **0,072851** s wide where the raw span/sample is **0,0042** s (span **72,850972**) — a bar one sample wide there is invisible, which is what the `span/1000` bound is for. Costs: bars over those 17 344 points **0,016 s**, a band (two borders + the fill, **3** items, a one-curve figure going from **1** view-box item to **4**) **0,216 s**; the band's borders start at **0,00619676…** and **0,01619676…** where the curve starts at **0,00619676…**. Slicing asks `(None, 'Enter a step value for slicing', 'Step:', 10, 1)` — modal, so recorded rather than answered, as `test_51` does for the plugin's occurrence question — and at **3** draws **5 782** bars, the last at the curve's own last sample; the copy asked `x[0:len(x)-1:3]` and drew **5 781**, leaving the end of the curve without a bar. Refusing the question changes nothing. A quantity holding no error (`magnetics/time`) draws nothing and is named in the log of its own case: `No error data available for: magnetics/time`. A quantity added after the bars were clicked joins them (**1 → 2**), and both survive a `refresh()`. **The move cost a discovery worth more than the move.** Handing the helper `self.errorQuantities` — a bound method, so a reference back to the frame — makes a cycle, and a Qt widget freed by the cyclic collector rather than at its refcount is freed while Qt still owes it a paint event: `Fatal Python error: Segmentation fault` **inside `gc.collect()`**, in `tests/test_44_plot_frame_ownership.py`, 2 runs out of 2, isolated and in the full run, while that same file on HEAD passes 3 of 3. Bisected in a throw-away worktree of HEAD with the new files copied in: keeping the helper and dropping its menu entries still crashes (2/2), replacing the bound method with a plain function stops it (0/2) — the menu is innocent, the cycle is not. So the owner is held through `weakref` and asked when needed, and `test_58`'s last test pins the rule: after the last reference goes, `weakref.ref(frame)()` answers `None` and `quantities()` answers `[]`. Suite: **832 passed, 1 xfailed, 52 warnings** in **127,40 s** — the baseline measured on a clean worktree of the same commit is **817 passed, 1 xfailed, 52 warnings** in **129,68 s**, so the **+15** is the 14 tests plus one more module in the import sweep, which walks **108** modules and **107** import where it walked **107** and **106** imported. The manual is corrected where this row makes it wrong: the note under *Basic plot display features* and the note in *Displaying error bars and/or confidence bands* both used to say those three lines live in the plugin's plots only; the two MultiPlot notes about `Configure Plot` stay as they are, because that entry did not move |
| T26 | Starting the application at all, on the python HLI that cannot carry the tree | `QVizAccessLayerHLI` — the two names the walk takes from the python HLI (`IDSDataType`, `IDSStructArray`), asked **once**, package root first because that is what a binding promises and the submodule second because that is where this one keeps them; `QVizIDSViewParser`, `QVizTensorExtractor` and `QVizTimeSliceSelection` import them from there instead of each importing an `imas` internal on its own | nothing, and the row says so: no file leaves. What goes is the **silence** — three leaf imports that each died on their own `ModuleNotFoundError: No module named 'imas.ids_data_type'`, naming neither the package that was loaded nor what to load. The legacy side of this row is the other HLI itself, and it is **not** removed by it: `IMAS-AL-Python` stays installable on this node. What this row left standing *inside* the package — `viz_equi/ids_read_multiprocess.py:30`, speaking `imas.ids(shot, run)` and `idd.open_env(user, machine, '3')`, imported by the registered `equilibriumcharts` — is gone since **T27**, the row that sentence promised. **Correction made when T27 ran**: as of that row no line of this repository names the generated HLI any more, so the gate of this row is the only place the two HLIs are told apart | fait — measured before writing anything: `IMAS-Python/2.0.1`, `2.1.0` and `2.3.0` (distribution `imas-python`, homepage `github.com/iterorganization/imas-python`) all ship `ids_data_type.py`, and 2.3.0 also exposes both names at the package root; `IMAS-AL-Python/5.4.0-foss-2023b-DD-3.42.0` (distribution `imas`, "IMAS High Level Interface for Python") holds `ids_base.py`, `ids_names.py`, `db_entry.py`, `dd_units.py` and one generated module per IDS, exports `DBEntry`/`IDSName`/`IDSBase`/`get_al_version`, and the string `IDSDataType` appears in **none** of its files — so `import imas` and `imas.DBEntry` both succeed there and the walk still cannot start. That is why the refusal asks for the two names and not for `imas`: an HLI-presence test would never fire. Measured after: the launch chain imports on the real stack (`missingSurface()` → `[]`, `loadedHLI()` naming `IMAS-Python/2.3.0`), and with a generated-HLI stub in front of `sys.path` it answers the refusal and exits **1** with **no** `ModuleNotFoundError` in its output; with no `imas` at all it says so. **`test_52`** carries the three, in a **child process** — the refusal fires during import and takes the process down, so in-process it would end the run rather than one test — plus the identity of the two objects, which is what `walkIDS` compares (`childMeta.data_type is IDSDataType.STRUCT_ARRAY`). Suite: **764 passed, 2 xfailed** in **132,19 s**; sweep now walks **110** modules, **109** import. And the README, which is where a user looks first, stated the **opposite** of what is measured — "only compatible with … al-python.git", "NOT compatible with … IMAS-Python" — one of the ways a user ends up on an HLI the application cannot run on; it now states the measurement |
| T27 | The **Equilibrium overview plugin** the manual documents — right click the `equilibrium` node, and the window with its slider, time-value box, *Run* and *Enable Grid* controls (`manual/plugins.rst:16-102`, 3 figures) | `equilibriumcharts.execute`, which now allocates its key through `vizAPI.GetNextKeyForFigure(FigureTypes.EQUILIBRIUMPLOTTYPE)` and registers the window in `figureframes`, so T0's *Show/Hide* and *Delete* reach a matplotlib window for the first time (`EquiPlotView:1`, a **6th** `MENU_ORDER` kind, no node in `figToNodes` — the "add this quantity to that figure" entries walk that record and could not fill a window that does not draw through the axes model); `DataGen`, which answers **12** refusals **by name** — occurrence, uri, the counts that disagree — instead of a `status` the caller tests; and `tests/test_53_equilibrium_plugin_on_a_real_case.py`, **14** tests on the reference case | `imasviz/VizPlugins/viz_equi/ids_read_multiprocess.py` (**64 l.** — the last line of this repository speaking the generated HLI: `imas.ids(shot, run)` and `idd.open_env(user, machine, '3')`, imported by a **registered** plugin and called by nothing); `viz_equi/test_equilibriumcharts_plugin.py` (**59 l.** — a demo ending in `app.exec_()`, so unreachable from automation like every `VizExamples` script); the plugin's own `if (__name__ == '__main__'):` block (**48 l.**, which read a `uri` nothing in the file defines); the three methods **no statement connects** — `on_save_plot` (5 l.), `flash_status_message` (6 l.), `on_flash_status_off` (3 l.) — and the `status` sentinel: **6** `status = -1` sites in `DataGen`, **4** `if status` tests in `PlotFrame.__init__`, which then returned *after* building the window, so a read that could not answer left a half-built frame on screen and the caller none the wiser. **185 lines** out of the subtree; `equilibriumcharts.py` **1 268 → 1 253** (`+150/−165` — the difference is the measured notes left in the code) | fait — measured before touching anything, and the entry itself was **not** the problem: the catalog offers it on the `equilibrium` root only (the `getEntries()` gate on `getIDSName()` works), and the label is looked up by the number the plugin declared (`0` → `Equilibrium overview...`). What `run` answered was `Plugin equilibriumcharts failed: TypeError: unsupported format string passed to IDSFloat0D.__format__`, with `plugin.frame` never built and `figureframes` empty — **the manual's whole section was unreachable on this stack**, and the reason is the one T22 fixed at `VizProfiles.py:504`: two title sites format `vacuum_toroidal_field.r0`, an `IDSFloat0D` — a `numbers.Real` wrapper with `__float__` and **no `__format__`** — so `float()` is the idiom. Two refusals more stood under it, both inside a Qt slot, where the traceback is printed and the caller is not told: `set_xdata(<number>)` answering `RuntimeError: x must be a sequence` on the **6** vertical time lines, which ended `update_figure` before its `canvas.draw()` — so the **slider the manual documents left the picture on the previous slice**, at every release and at every *Run* tick; and `grid(b=…, which=…, linestyle=…)` answering `ValueError: keyword grid_b is not recognized`, so the **Enable Grid** checkbox did nothing at all. Both are matplotlib **3.11.2** refusals, and that version is not what the module stack exports: it loads from `~/.local/lib/python3.11/site-packages`, a user-site install nothing here pins — a drift to check before blaming the plugin. What the window really holds, now pinned: **14** axes, `Psi_val (49, 7229)`, `prof_1d (49, 9, 101)`, `wall (2, 164)`, `b0 (49,)` with `b0[0] = -3.763` at `r0 = 2.42`, a `TriContourSet` on the surfaces panel under lines of **1 / 1 / 164 / 201** points, slider **0..48** over `32.1336784362793 → 48.54828643798828`, the title naming the field it draws (`Psi with B0=-3.763 [T] at R0=2.420 [m]`) and the window titled with the key it is registered under — the `title` argument this signature accepted was used by **no** statement, so two of these windows sat on screen with empty title bars while the menus named two identical-looking lines. Costs: **6,73 s** for the first run of a process, **0,98–1,45 s** once the IDS is in memory, **0,44 s** for a second window — which takes its own key (`EquiPlotView:2`), is listed beside the first by both menus, and leaves the registry when *Delete* takes it, as T0 pins. Refusals cost **0,03 s** and add **0** window. Limits kept and said here rather than quietly carried: the plugin still reads **occurrence 0** and does not ask, unlike the Profiles plugin; its window is parented to the shot view and is **not** an MDI subwindow (`mdiWindowOf` answers `None`), so it is not movable in the area and it goes with the view it came from; and its **28** `print()` calls stay — they predate the log panel, and converting them is not this row. One measurement worth keeping: `Ignore_GGD` does **not** cover the plugin's own `get` — with the GGD walk of the tree reactivated, the same case cost **287 s** in a probe, which is why the test fixture pins the preference at **1** and the file stays under the **180 s** cap. Suite: **777 passed, 2 xfailed** in **138,91 s**; sweep: **108** modules, **107** import. **No documented feature dies**, and it is worth saying because this is the first row of this inventory whose plugin *is* in the manual: the four interactions `plugins.rst` promises — slider, time-value box, *Run*, *Enable Grid* — are measured answering all four now, three of them for the first time on this stack, and the section gained the two things it did not say (which occurrence is read, and that the window is listed under *Plot windows*). What went was never documented and never reachable: a module no statement called, two demo entry points that could not run, three methods no signal or action was connected to, a return code no caller tested. And the entry's menu tip — `getDescription()`, read through `QVizPluginCatalog:229` — advertised "Saving the plot to a file from a menu", an action **no menu ever held**; it now lists what the window answers |

| T28 | Opening a pulse at all — the shot view and the tree of IDSs it draws before anything is loaded | `QVizDataTreeView.createEmptyIDSsTree()`, with no argument: it opens the case, asks the **entry** which data dictionary that case is stored at (`DBEntry.dd_version`), and takes both things the `IDSDef_<version>.xml` file used to supply from that entry's own factory — `IDSFactory(ids_names())` for the roots and `IDSFactory.new(name).metadata.documentation` for their documentation. The occurrences already came from the case (T12, `QVizCaseOccurrences`), so the file was the last thing the tree asked of the environment | `QVizGlobalOperations.getIDSDefFile` (**24 l.**, with its `IDSDEF_PATH` override and its `$IMAS_PREFIX/include/IDSDef.xml` fallback — and its own `if IDSDef_path is None:` branch, which no path through the method could reach); the `IDSDefFile` argument through three signatures (`QVizDataTreeView`, `QVizDataTreeViewFrame`, `Viz_API.CreateDataTree`) and the `xml.etree.ElementTree` import it justified; `QVizDataTreeView.idsNamesList`, filled on every root and read by nothing; `IMAS_DATA_DICTIONARIES_DIR` (mandatory in both `checkEnvSettings`, defaulted in both branches, and `TESTING_IMAS_DATA_DICTIONARIES_DIR` with it); `IMAS_MAJOR_VERSION` (mandatory, defaulted, and derived as `IMAS_VERSION[:1]` in both branches — no application code read it); the `AL_VERSION → IMAS_VERSION` copy in both branches of `QVizGlobalValues`; in the harness, `IMASVIZ_TEST_DD_DIR` and the checkout of `imas_data_dictionaries` it existed for. **50 lines** out of `QVizGlobalOperations`, **20** out of `QVizGlobalValues`, **8** out of `Viz_API` — 183 in, of which most is measured notes and two tests | fait — measured before touching anything, on the report that opened the row (`[Errno 2] No such file or directory: '/home/ITER/fleuryl/IMASViz/imas_data_dictionaries/IDSDef_5.7.1.xml'`): the chain is `Viz_API.CreateDataTree:142` → `getIDSDefFile(IMAS_VERSION)` → `QVizDataTreeView:153 ET.parse`, and `QVizOpenShotView.Open:42` catches `ValueError` only, so a pulse died **outside** the gesture that asked for it. The version in that path was never a dictionary version: `IMAS_VERSION` was copied from `AL_VERSION`, which is **5.7.1** here — an Access Layer number. IMAS-Python/2.3.0 bundles **35** dictionary versions in a zip inside the package, `3.22.0` through `4.1.1`, and 5.7.1 is not one of them, so the named file has never existed on any stack that exports `AL_VERSION`; the harness hid that because it exported a directory that does hold `IDSDef_3.23.3.xml`. What the entry answers instead, on the reference case: `dd_version` → `'3.35.0'` (0,000 s), `ids_names()` → **69 names** (0,000 s once parsed), all **69** documentations through the public `new(name)` in **0,401 s**, none empty. `new(name, _lazy=True)` answers the same 69 in 0,000 s but is marked "Internal usage only !", so the public call is kept: **0,4 s** per view is not worth reaching past a private parameter. A version the package does not hold is now refused **before** the view exists, naming itself — `UnknownDDVersion: Data dictionary version '5.7.1' cannot be found. Did you mean '3.37.1'?` — a `ValueError`, so `QVizOpenShotView.Open` logs it like every other refusal. Consequence, pinned rather than assumed: the case shows **69** roots where the harness file held **55** — `3.35.0` gained `calorimetry`, `camera_ir`, `camera_visible`, `camera_x_rays`, `cryostat`, `dataset_fair`, `disruption`, `divertors`, `ec_launchers`, `gas_pumping`, `real_time_data`, `refractometer`, `spectrometer_mass`, `spectrometer_uv`, `spectrometer_x_ray_crystal`, `workflow`, and lost `ec_antennas` and `sdn`. The harness dictionary moves to **4.0.0**, which the package carries. One xfail dies on the way, and its death is a measurement of its own: `list_filled_paths` answered `packaging.version.InvalidVersion: Invalid version: '+1'` at `3.23.3` — where the entry of this case answers `dd_version == -1` and logs "Ignoring missing Data Dictionary version in loaded DD" — and answers **112 paths** at `4.0.0`, so `test_03` asserts it now; reading an IDS across a major version still refuses (`RuntimeError: … different major version`), which the neighbouring test keeps. **No documented feature dies**: `manual/loading_IDS.rst:95` promises "a list of all IDSs", the filled ones in blue, and the tree answers that list — from the dictionary of the case now, and with **14 more entries** on the reference case than the file gave. Suite: **780 passed, 1 xfailed** in **131,33 s**; sweep unchanged: **108** modules, **107** import |
| T29 | Opening a case from the start window — the **IMAS database browser** (`manual/loading_IDS.rst:56`: double clicking fills the parameters) and the tab that takes the `-u -d -s -r -b` command line | `QVizIMASdbBrowserWidget.doubleClickHandler` resolves the five labels of the row double clicked (`_caseLabelsOf` walks up from the leaf instead of four blind `parent()` steps), sets `activeUsername` / `activeBackend` / `activeDatabase` / `activeShot` / `activeRun` **together**, and emits `onItemDoubleClick` in that case only; `BACKENDS = {'HDF5': 13, 'MDS+': 12}` is one table for the two labels the `Worker` writes into the tree and the two ids `-b` takes; `setActiveBackend` takes an **id** and refuses another by name; `GUIFrame.updateIDSparam` reads the five, refuses an incomplete selection in the log of the session, and only then writes its five widgets. The tab is named **"Local data source"** — the name `manual/loading_IDS.rst:26` asks the user for | `QVizIMASDataSource.getVersion()`, the `AL_VERSION` parse every Access Layer 4 branch hung on, and with it the four things it decided: the `legacy_attributes` dict `build_uri` answered as a second value, the entry built from six positional numbers in `createDBEntry`, the `entry.open()` of `buildEntry` and the `Unknown Access Layer version` fall-through under both. The `legacy_attributes` attribute itself — on the source, on the factory (its `__init__` and its "required legacy parameters" refusal) and carried through `QVizOpenShotView.Open`; the `database_name` key `caseLabel` read before its URI, a key no URI spells; the URI box disabled in the second tab and the three AL4 warnings at start-up; `print("QtVizGui::legacy_attributes=", ...)`, which is the line that was still printing on the console of the report; the `import os` left without a user. **195 lines out, 456 in** over 17 files, 244 of them the new test file | fait — measured before touching anything, on the report that opened the row (`AttributeError: 'QVizIMASdbBrowserWidget' object has no attribute 'backend'` at `QtVIZ_GUI.py:199`, printed on the console with **nothing** in the log panel): the constructor set four `active*` attributes and never the fifth, and `doubleClickHandler` set its five values only for a run leaf while emitting the signal **whatever** had been clicked — measured on the shot, database, backend and user rows, all four ran the frame's update with three `None` and no backend at all. `QLineEdit.setText(None)` answers no error on PySide6 6.6.3 and leaves the field empty (measured, and it is *why* the traceback reaches line 199 rather than 196: the four earlier writes went through), so what the user had typed disappeared one field at a time before the fifth line died. `setActiveBackend` mapped its two labels with two tests and no `else`: `'hdf5'` — the labels are case sensitive — and `'ITER'` both answered `UnboundLocalError: cannot access local variable 'backend'`. And `getVersion()` answered **5** on every stack this application runs on (`AL_VERSION` is 5.7.1 here), so the AL4 path had been unreachable for as long as the bindings have been IMAS-Python's: the pair `build_uri` answered was always `(uri, {})`, and nothing read the dict — which is what made its plumbing removable rather than merely unused. **`test_54`** carries the gesture: five values out of a browser nobody clicked, a run leaf spelling the whole case (**13**, and **12** under the `MDS+` label), the four other rows emitting nothing and naming themselves in the log, a tree of another depth refused, an unknown backend label refused by name, `updateIDSparam` leaving the five parameters untouched on a partial selection while a full one fills them and moves the combo. One test dies with the behaviour it pinned (`test_12`: a label is read from the URI only), and `test_02` trades its two `getVersion` tests for the assertion that nothing asks that version any more. A trap the suite already knew cost ten failures in the first draft of that file: `QVizIMASdbBrowserWidget(QMainWindow())` dies with a parent built inline, because Shiboken does not keep a parent's wrapper alive from its child — every test then answers `RuntimeError: Internal C++ object (QVizIMASdbBrowserWidget) already deleted`; the window is held through `support.ownership.keep`, as `test_48` and `test_50` do. **No documented feature dies**: the manual's double click fills the parameters, as before, from a run row — the level its figure shows — and a click that spells no case now says so in the log instead of blanking the fields. Suite: **791 passed, 1 xfailed** in **131,13 s**; sweep unchanged: **108** modules, **107** import |
| T30 | Opening a case — **at which data dictionary** the entry is built, and what a refused read answers (the manual never names the dictionary, so nothing documented is at stake) | `QVizIMASDataSource.pinToCaseDictionary()`: the major is read off the URI (`dataVersionFromUri` — `version=3`, or the `<db>/<data version>/<shot>/<run>` of a path case), the case is probed at the newest bundled dictionary of that major, and the exact version is taken from the case itself through `list_all_occurrences(name, 'ids_properties/version_put/data_dictionary')`; the entry is then built pinned — **before** the registry key, since the record is keyed `(uri, mode, dd_version)`. An explicit `dd_version` is never overruled. `get()` raises a `ValueError` naming the IDS, the occurrence, the case, the dictionary and the Access Layer sentence | The `except BaseException` in `get` that turned every refusal into a **None and cached it** under `IDSName/occurrence`, so the next ask never reached the Access Layer and the caller died on `None.metadata` one floor up; the `print(e)` that was the only place a failed `open()` left a clue, and the `raise ValueError(e)` that stripped the message; the walk's invented diagnosis — *“the data dictionary of the data entry does not match the fields IMASViz expects”*; `def exists(self, IDSName=None): return True`, which answered yes for every IDS of every case and that nothing called; `data_dictionary_version`, read by nothing | fait — measured before touching anything, by replaying the application's own objects on the reference case, and the report came out line for line (`QVizIDSViewParser.py:220` then `:283`, `'NoneType' object has no attribute 'metadata'`). An entry built from an URI with no `dd_version` settles on the version `IMAS_VERSION` names or on the newest bundled one — **4.1.1** here, variable unset — and `DBEntry.get` then raises `RuntimeError: On-disk data is stored in DD 3.35.0 which has a different major version than the requested DD version (4.1.1)` for **every** IDS of the case, while `list_all_occurrences` answers across a major: the shot view is built, the names are coloured as holding data, only the loads die. The case answers the version question for one price: **0,41 s** for the four occurrences of `equilibrium`, no IDS read — the node path spelled with **obliques** (dots answer `ValueError: Invalid node name`), and only askable of an entry whose major already matches, hence the URI guess. Occurrences of one IDS can name different minors (`magnetics`: 3.35.0 **and** 3.37.0). Pinning at the newest of the major instead would have been cheaper and wrong: walking `equilibrium` 0 gives **3519 leaves at 3.35.0** against **3594 at 3.42.2** (4,14 s / 4,52 s) — 75 nodes the newest dictionary adds to a case written with an older one. 35 dictionaries are bundled, `3.22.0` … `4.1.1`, so the major the reference case spells is not the newest; `list_filled_paths` takes a required `ids_name`, so it cannot enumerate a case. **`test_55`** pins the URI readings, the first guess, an unpinned case opening at 3.35.0, the roots of an unpinned case being the **69** of its own dictionary and not the **82** of the newest one, a read across a major naming everything it refuses on, an IDS the case does not hold refused by name, a refusal not left in place of an answer, the walk carrying the refusal and inventing no diagnosis, and a missing case refused with the Access Layer sentence. One test changes contract, not intent (`test_16`: the reference still comes back, through a `ValueError` now). **No documented feature dies**: the manual never mentions the data dictionary, and `IMAS_VERSION` keeps its meaning as the fallback for a case that spells no version. Suite: **802 passed, 1 xfailed** in **138,42 s**; targeted run 112 passed in 38,12 s; sweep unchanged: **108** modules, **107** import |
| T31 | Reading what a node holds — the value behind a path the shot view holds as **text**: the style a tree item takes, the coordinates a quantity is read against, the error bars, the node documentation panel, and the Profiles plugin's time slider, spin box and labels | `QVizTreeNode.resolveIDSPath(path, idsName, idsInstance)`: one `NODE_NAME` match or one `ELEMENT_INDEX` match after the other, straight off the loaded IDS object. `resolvePath` is the node's own door to it, and the plugin asks for its IDS once, through `getIDSInstance()`, then uses attribute access | The pair itself — `exec(idsName + " = self.getIDSRef()")` and `return eval(path)` — in `updateStyle`, in the two error-bar readers, in `coordinateValues`, and **five** more times in `viz_Profiles/viz_profiles/VizProfiles.py` (one `exec`, **15** `eval` reads after it). Six methods that could only be reached through it and had no caller left: `coordinateLength` (the only producer of a `len(...)` expression the walk could never answer), `getGlobalTimeForArraysInDynamicAOS`, `timeMaxValue`, `getDataTimeSlices`, `hasClosedOutline`, and in `QVizGlobalOperations` `isTimeHomogeneous` and `getCoordinate_array` (**25** lines). The bare `except:` of the error-bar readers and the two commented-out `expression_error_*_path` lines that justified it | fait — measured before touching anything, on a real shot view of the reference case, by recording every path it asks. The trigger came from a session elsewhere: `QVizDataTreeView.py:574 in event` → `:594 onResult` → `:359 updateView` → `:377 update_view` → `:429 buildTreeView` → `:467/:462 addChildren` → `QVizDataTreeViewBuilder.py:84 addNewNode` → `:165 build_nodes` → `updateStyle` → `QVizTreeNode.py:579` → `:836 return eval(path)` → **`NameError: name 'magnetics' is not defined`** — nothing naming the case, the IDS or the path, and the tree stopping at the node that asks. The pair never read the IDS: `exec` writes into the **frame-locals mapping** of its caller and `eval` is left to find the name back there, which is a CPython implementation detail. It answers on this node's **3.11.5** — which is why the failure cannot be replayed here: no python ≥3.12 is reachable — and on the frame semantics of 3.13 (PEP 667) the binding is not visible to the following `eval`, so what was changed is the dependency, not a version. The cost of the pair, measured on the same case at its own dictionary 3.35.0: building `magnetics` 0 asks **11 428** paths and `equilibrium` 0 **3 703** more, **15 131** over **802** distinct shapes and **0** failures, **0,189 s** against **0,053 s** walked; the callers still reached, over the **9 426** signal nodes of those two views, answer **22 658** identical paths in **0,630 s** against **0,076 s**. Two callers ask none: `QVizPlotAsSlices` went through the axes model long ago, and the panel asks **3**. The **543** expressions the walk cannot answer (`magnetics.1…2` for **537** nodes, `equilibrium.1…3` for **6**) live in the callers that were already refusing them: the dictionary spells those coordinates as a **range**, `coordinateValues` only catches the literal `1..N`, and what reached the evaluator was refused with `SyntaxError: invalid syntax (<string>, line 1)` — naming neither node nor coordinate — and swallowed by the caller's `except:`. They are refused by name now. An early probe reported *14 417 failures* and was an artefact of the probe itself: it called the error-bar readers on every node, so `…_error_upper_error_upper` was asked of leaves that never had them. A leaf the opened object does not hold keeps IMAS-Python's own `AttributeError` — `IDS structure 'flux_loop[0]/flux' has no attribute 'not_a_node'` — because it names more than a rewritten message and the panel already shows it. **No documented feature dies**: `doc/source` names none of the six removed methods and never named `evalPath`. **`test_56`** pins the values, the refusals and the guard — it compiles the module of the shot view and of the plugin and refuses the names `eval` and `exec` in their `co_names` at any depth, so the pair cannot come back one call site at a time. Suite: **812 passed, 1 xfailed** in **123,89 s**; targeted run 68 passed in 20,10 s; sweep unchanged: **108** modules, **107** import |
| T32 | Styling a curve by hand — the **`Configure Plot`** dialogue, which the manual documents with three figures (`manual/plotting_1d_arrays.rst`, *Plot Configuration and Customization*) and which only the plots of the Profiles plugin offer (`:97`, `:618`, and refused twice, at `:735` and `:938`) | `QVizPlotStyleUI` (**565** l.), **asked rather than named**: the view box that offers the entry answers `styleCurves()`, `styleText()` and `styleMargins()`, and the window answers where its panels live — `QVizTablePlotView.panelLayout()` is `ci.layout`. One `CurveStyle` per curve: its seven properties and the state it had on opening. `TextLabel` and its two ways in (`TitleLabel`, `AxisLabel`), one list `CURVE_COLUMNS` feeding both the header and the rows, and four readings the old code did by hand — `penOf`, `styleNameOf`, `symbolNameOf`, `fontSizeOf` | `QVizPlotConfigUI.py` — **1 342** lines: the four name branches of `getLegendItem`/`getPlotItem` (`:50-59`), `TabLegendProperties` + `SampleCopyFromLegend` — **339** l. of legend — the flat `eventsData` of `TabLineProperties` (**358** l.), `TabTextProperties.updateAxisBottomLabel`, `TabPlotDesignProperties.setNewMargin:1203` with its two `hasattr` probes and its bare `QWidget()` fallback, `AxisConfWidget`, the empty `setHideLegend`, and the `viewBox.id` its title read — the `id` itself with it, on the plugin's view box (`CustomizedViewBox:56`) and on the panel that set it (`QVizTablePlotView:207`) | fait — **measured first**, offscreen and without a case, on the only caller there is. The name walk: `objectName()` answers **'QVizPlugin'**, so the `TablePlotView` and `StackedPlotView` branches never ran, and the fourth is dead for every frame of the package — `hasattr(qWidgetParent, 'pgPlotWidget')` answers **False**. The dialogue answers **3** sections in **0,080 s** there and `plotItem.legend` answers **None**, which is what the 339 legend lines were guarding: a marker never drawn. Four measured defects. The header held **8** labels over **7** widgets — a colour button under the label `Line`, every label one column off. The tab held **one** flat `eventsData` dict rewritten once per row, so with **3** curves and **9** colour buttons the first row changed **neither** the first nor the second curve: every row wrote `listPlotDataItems[-1]`. `reject()` changed **nothing** — a margin written through it read back `(40.0, 9.0, 9.0, 9.0)` after. And a curve drawn without a pen, carrying pyqtgraph's instance default `opts['pen'] == (200, 200, 200)`, killed the constructor at `:281` with `AttributeError: 'tuple' object has no attribute 'color'`. Margins, which T25 could not settle: `centralWidget` **is** `ci`; the layout the panels live in is `ci.layout`, **(9.0, 9.0, 9.0, 9.0)** on a fresh window, and setting its left margin to 120 moved three panels from x = 9.0, 305.0, 601.0 to **120.0, 379.0, 638.0** — while `centralLayout`, the name `setNewMargin` probed for and `hasattr` still answers True for, is a **deleted** C++ object: reading it answers `RuntimeError: Internal C++ object (QGraphicsGridLayout) already deleted`, because `GraphicsLayoutWidget` replaces the central widget `GraphicsView` built. `listDataItems()` answers **4** curves on a panel holding 4 curves plus an `ErrorBarItem`, an `InfiniteLine` and a `FillBetweenItem` — all three decorations in `addedItems` — so the answer needs no list of item types to skip. Two label readings cost a fix each: a fresh title's opts are `{'color': None, 'justify': 'center', 'size': '11pt'}`, carrying **no `bold`**, so a restore that hands that dict back leaves a bold title bold; and a fresh axis style is `{'color': '#969696'}` with no size, so a size box reading a stored default rather than the label shows a number the label is not drawn at. **`test_62`** (**18** tests, no case) pins the three answers and the two-section window that answers no layout, the header agreeing with a row, a row reaching its own curve and no other, the pen-less curve, the two dictionary refusals, the axes offered being **2** on a plugin panel — top and right answer an empty `labelText` and a hidden label, where the old tab built all four — the CSS an axis label really carries (`font-size:26px` in its HTML), the margins landing in `ci.layout` with the panel moving and both ways back, and Cancel taking back pen, width, title text **and** `bold`, the axis style down to the single colour it started with, margins back to 9. The guard reads the module's syntax tree, not its prose: no `objectName`, no `qWidgetParent`, no `pgPlotWidget`, no `centralLayout`, no `legend`. **No documented feature dies**: `doc/source` names no legend styling, no bold, no symbols, and the three refusals above are still true — the entry is the plugin's alone, as it was. Suite: **888 passed, 1 xfailed, 52 warnings** in **129,73 s** (was 870 passed, 1 xfailed, 52 warnings, 132,84 s); targeted run **172 passed, 1 xfailed** in **17,87 s**; sweep unchanged: **109** modules, **108** import — one module out, one in |
| T33 | The colour each trace of a curve figure is drawn with — the **six** entries that put a second trace under the user's eyes: *Plot X to → Figure → New*, the same with an open figure named, *Plot selected nodes to → Figure → New* or an open figure (This/All), the Profiles plugin's *plot to figure*, and the two `Viz_API` wrappers (`:473`, `:612`) | `QVizCurveColors`: `CURVE_COLOURS` (**8** named rgb triples), `CYCLE`, `colourFor`, `nameFor`, `penFor` — one colour per index, cycling once the list is used up. `QVizCurvePlot.plot()` asks it once per drawn row and spells the legend label `path[row]` when one quantity answers several rows | **nothing** — and the row says so: what this replaces is pyqtgraph's own instance default, not an IMASViz statement, so no legacy line dies here. What it **opens** is the row below | fait — measured first, on the reference case at its own dictionary 3.35.0. pyqtgraph **0.13.7** gives a curve drawn without a pen `opts['pen'] == (200, 200, 200)`, a plain instance default, and holds **no** colour cycle: `colorCycle`, `colorLists` and `currentColor` appear **0** time in the package. So `magnetics/flux_loop(0)/flux/data` and `magnetics/bpol_probe(0)/field/data` on one figure drew **2** curves, both `tuple(200, 200, 200)` — as did the selection figure built from **3** selected nodes, which drew **2** traces, the third refused for want of values along the plotted axis. Those lines are drawn on **black**, and the ground is painted by the *view*, which is a `QGraphicsView`: `PlotWidget.backgroundBrush()` answers `SolidPattern (0, 0, 0, 255)`, from pyqtgraph's own configuration default `'background': 'k'`; the only `setBackground` in `imasviz` is the Profiles plugin's, and it is white. (Corrected in T34: this row first wrote that black as `background 'k'` "in the configuration" and read it off `viewBox.background.brush()` — there is no such preference here, and that brush belongs to a `QGraphicsRectItem` which is **hidden** with **NoBrush** unless `setBackgroundColor` was called, while its `color()` still answers `(0, 0, 0, 255)`.) Hence the palette is **not** `getRGBColorList()`: that list carries `#FFFF00` and three near-whites (`#cce5ff`, `#d3d3d3`, `#C0C0C0`) sized for a white page, and its order comes out of `GlobalColors.__dict__`. And it holds **no pure red**, because `QVizCurveErrors` fills its confidence band with `(255, 0, 0)` in `DiagCrossPattern` — a band in the colour of a trace is the confusion this row removes, not one it should bring back. Measured after: **(255, 140, 0)** then **(0, 255, 255)**, in the order the traces were laid down; the band's two borders still `tuple(200, 200, 200)` and taking no place in the cycle; `refresh()` leaving the colours alone while it re-reads the samples through `setData`; and **3** rows of one quantity taking **3** colours and **3** labels — a shape the real read never answers here (`y.shape == (1, 17344)` for every quantity read along time), so `test_59` drives it with the real read wrapped to repeat its answer, axes, values and slice controls left real. One side effect: `QVizPlotConfigUI.py:281` reads `pdItem.opts['pen'].color()` and so already assumed a real `QPen` — it now gets one. **`test_59`** (8 tests) pins the two colours and the legend, the selection figure, the three-row figure, the cycle at `CYCLE+1`, `refresh`, the band's grey borders, the palette's invariants — no `(200, 200, 200)`, no `(255, 0, 0)`, one channel at 255 and one at or under 140 for the black, two consecutive colours more than **20 000** apart in squared rgb — and that a picture figure answers `images()` and no `curves()` to colour. Suite: **841 passed, 1 xfailed, 52 warnings** in **126,20 s** (was 832 passed, 1 xfailed, 52 warnings, 127,40 s); targeted run **165 passed, 1 xfailed** in **11,09 s**; sweep **109** modules, **108** import (was 108/107) |
| T34 | The colour of the curves the **Profiles plugin** draws in its own window — **41** plots, all in one blue | `LIGHT_CURVE_COLOURS` in `QVizCurveColors` (**8** named rgb triples picked against a **white** ground), `LIGHT_CYCLE`, `lightColourFor`, `lightNameFor`; `QVizTablePlotView` asks `lightColourFor(0)` — `navy` — at its own `PLOT_LINE_WIDTH = 3`, `SolidLine` | `QVizTablePlotView.setPen()`, a staticmethod answering `pg.mkPen(getRGBColorList()[0], width=3)` whose own comment read *"self.RGBlist[0] -> blue color"*; `getRGBColorList()` (`QVizGlobalValues.py:238`) with the **18** `*_HEX` attributes it existed to walk out of `GlobalColors.__dict__`, and their export in `VizUtils/__init__.py` | fait — **measured first**, on the reference case through the entry the shot view offers: **41** panels, **41** curves, every pen `(0, 0, 255)` at width **3**, `SolidLine`. What that blue sits on is painted by the *view*, which is a `QGraphicsView`: `QVizTablePlotView.backgroundBrush()` answers `SolidPattern (255, 255, 255, 255)` — its own `setBackground` at `:75`, the only one in the package — against `SolidPattern (0, 0, 0, 255)` for a figure of curves. **A sentence this file wrote for T33 is corrected**: it credited that black to `background 'k'` "in the configuration" and read it off `viewBox.background.brush()`. No such preference exists in `imasviz`; and that brush belongs to a `QGraphicsRectItem` pyqtgraph only shows after `setBackgroundColor`, which nothing here calls — measured in both windows: **hidden**, `NoBrush`, while its `color()` still answers `(0, 0, 0, 255)`. That is the reading that reported the plugin's white window as black. The single colour is the case's answer, not a taste: those **41** panels carry **41 distinct parametrized paths**, one panel per path, so a colour has nothing to group and a cycle would answer the same colour five times in one window. Nor could the plugin borrow the black palette: **5** of its **8** colours fall under a contrast of **2,5** on that white (cyan 1,25, chartreuse 1,30, spring green 1,35, gold 1,40, orange 2,33) — and **8** of the old list's **18** entries are under **2** there (`#FFFF00` 1,07, cyan 1,25, `#cce5ff` 1,29). The light list's weakest answers **4,77**, its smallest consecutive distance — the closing pair included, which a per-entry check misses — **32 768**, and it holds no pure red because those panels carry the same `QVizCurveErrors` band as a curve figure. **What survives on purpose**: `GlobalColors` and its six brushes — the tree paints its nodes `BLACK`, the preferences turn a number into `BLUE`/`RED`/`CYAN`… through `getAvailableColorForNodes`, the documentation panel fills itself `LIGHT_CYAN` — and the width **3**, which a panel a few tens of points wide needs and the library's 1 does not. **`test_61`** (**10** tests, no case) pins the contrast floor, the two refusals, the cyclic distance, that 5 of the 8 black colours vanish on white, that the two windows paint the two grounds *and* that a `ViewBox` is not what paints them, and the guard: no module of the package imports the hex walk, `GlobalColors` keeps no `*_HEX` for nobody, `QVizTablePlotView` has no `setPen` — the name itself is allowed to survive only in the prose that buries it. The **41** pens, their width and the white they are drawn on are pinned on the real window in `test_51` |
| T35 | Drawing **an element** of a tensor, and **exploring the tensor** it belongs to — every plot entry of the shot view, plus the new *Explore this tensor* entry under `Plot X to → Figure` | `QVizCurvePlot`, rewritten around per-trace state: `QVizTrace` (one record per drawn curve — the node, the row, the curve, its abscissa kind, the indices **frozen** for it and the **movable** ones, its legend label), `exploresTensor`, `_pinning`, `_readSlices`, `_controlsFor`, `refresh` (skips frozen traces, rewrites a live trace's label), `keepCurve` / `dropKeptCurve` / `keptCount` behind a `Keep this curve` box; `QVizSliceControls(foldable=True)` with a summary row — `summaryText`, `toggleFold`, `isFolded`, and folding is a **visibility**, never a rebuild, so a folded band still answers the read; `elementLabel` in `QVizSlices.py` (the parametrized path with the array indices spelled out) and `QVizNodePlotting.tensorAxes()`, which gates the entry; `QVizPlotOneNode(tensor=True)` and the `exploreTensorCommand` slot | the `addTimeSlider` / `addCoordinateSlider` / `sliderGroup` trio, out of `QVizCurvePlot`, `QVizImagePlot`, `QVizPanel` and the Profiles plugin's `GlobalPlotWidget` (the third was called by nobody, the two others answered a widget no longer built); the two branches of `QVizTensorDataAccess` that fed it, and the fallback they left — its `sliceControls.indices()` is now the band's, asked per trace; the slider half of `QVizTreeNode.labels()`, whose signature did not change | fait — **measured first**, on the reference case (WEST 54924 at 3.35.0): `magnetics.flux_loop[i].flux.data` declares **17** elements and the case fills all **17**, **17 344** samples each. Plotting element 0 then element 1 into one figure answered **IDENTICAL SAMPLES: True** — both curves starting `0.00619676` — where the same runtime answers `0.00817774` for element 1: the figure held **one** index per axis, shared by every curve, and the read took the element from there. The legend spelled both traces `magnetics.flux_loop[i].flux.data`, so nothing on screen said the user had drawn one curve twice. The band cost **1 line = 30 px of a 480 px window** and stayed at 1 line for **10** traces, with **10** identical legend labels. Measured after: element mode answers **0** band line, legends `flux_loop[0]` / `flux_loop[1]`, and samples equal to the runtime's; tensor mode (`frame.plot(node, tensor=True)`) opens on the indices the tree stood on, and with the slider at 5 the samples **are** `flux_loop[5]`'s and the legend follows; `Keep this curve` freezes a trace at 5 while the live one goes to 9, unkeeping takes it back out (**2** traces → **1**) and refuses by name when nothing is kept; the band of two rows folds to one summary line — `ion 1 / 1   dimension 1 0 / 2` — with `indices()` identical folded and unfolded. One pyqtgraph **0.13.7** fact the probe caught: `Legend.item(curve)` answers **None** for the `PlotDataItem` that `plot()` returns, so the label of a live trace is read back from `legend.items[-1]` (a `(sample, LabelItem)` pair, its string in `LabelItem.text`) and matched against the name just asked for — with `Legend.item` the moved trace kept naming the element the figure opened on. **What survives on purpose**: `legacyCanDrawAsCurve` / `legacyCanDrawAsImage`, `plotAxis` / `getPlotAxis` and `isPlotToPerformAlongTimeAxis`, which answer questions of their own; the band itself on an image window and a table panel, which stay unfolded — there the rows are the only place saying which slice the colours and the panel numbers stand for, and the manual says so. Two limits kept and said in the code: the leaf's own coordinate keeps its control even in element mode (the tree does not fix it), and a picture figure **refuses** to explore its tensor — the axis an exploration would move is the one the pictures are spread over — a refusal named in the log of the case and costing no window. **`test_60`** (**17** tests, **2** of them on the case: the two elements answer different samples with no band line at all, and walking a real slider answers the samples that element's own figure answers) plus `test_24` (a rank 3 element keeps its own index; two quantities of one array still share one control), `test_25`, `test_59` (legend labels now spell the element). One stub defect came out with it: `test_24`'s scalar-in-an-array passed by **inheriting** another curve's index, because its node spelled its level-1 array `foo.ion[j]` while the axes model reads an index under its **level's** letter (`QVizGlobalValues.indices[level]`) — the node's own index is asked now, so the stub spells `foo.ion[i]` |

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
The `build_uri` xfail was lifted by T10 — the first of the eight to go; the five
Qt Designer modules stay.
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
Since T9: **525 passed, 8 xfailed** — thirty tests in
`tests/test_39_configurations.py`, the first in the suite to redirect `HOME` into
`tmp_path` (the suite does not isolate `$HOME`, so a configuration saved by a
test would otherwise land in the folder the user works with). They pin the file
by what it holds rather than the name it wears, the two shapes the old writers
produced still read and their styling counted, a name that names a place refused
before anything is written, the button that used to write nothing now naming
every panel the window shows, the place re-applied where it was written, the
abscissa the window was drawn with coming back as the abscissa it is applied
with, a selection saved from one view selecting the same nodes in another, and
the scripted entry taking the list of paths the manual shows. The sweep gained a
module — four configuration modules gone, five added: 117 − 4 + 5 = 118 modules,
113 passed / 5 xfailed (494 + 30 + 1 = 525).
Since T10: **573 passed, 7 xfailed** — forty-three tests in
`tests/test_40_export_to_ids.py` and the `build_uri` test of
`tests/test_02_data_source.py`, which stops being an xfail: the spelling lives in
the data layer now, so 525 + 43 + 1 = 569, and the sweep gained the four modules
of `VizDataExport` — 118 + 4 = 122 modules, 117 passed / 5 xfailed — for 573.
They pin the URI as the inverse of the reader (`_readCaseFromUri(caseUri(…))`
gives the case back), the two versions the format needs — `version=3` in the URI
while the entry is built at `3.35.0`, because `dd_version='3'` answers
`UnknownDDVersion` — a field left empty or holding a separator named instead of
sent to the Access Layer, the `/` the old dialog prefilled refused by name, a shot
box that cannot hold letters, a run of 0 kept distinct from a run left blank, the
backend asked as a choice, the entry never asked to `open()` a second time, the
entry closed when a `put` fails, one refused IDS named while the other two are
written, `2 of 3 IDS(s) written` counted in the log, and — the one proof that
matters for a gesture that wrote 0 IDSs — a real `pulse_schedule` read from the
reference case, written into a `path=` case under `tmp_path`, and found again at
occurrence 0. The suite needed one harness fix for them: `support/plotting.py`
dropped the command it built, and with it the api holding the plot frames, so Qt
deleted `QVizCurvePlot` widgets a queued `paintEvent` still pointed at — a
segfault in a test three files away. It held at HEAD, but only until an extra
module shifted the garbage collection: **525 passed, 8 xfailed** there, three
runs, and 573 passed here, three runs.

Since T11: **608 passed, 7 xfailed** — thirty-three tests in
`tests/test_41_node_documentation.py`, the three `ui` tests of
`tests/test_23_scalar_content_and_lifecycle.py` re-pointed at the new panel
(their intention unchanged: a status shown when the dictionary gives one,
nothing when it does not, a scalar shown as its value), and the sweep's two extra
modules — 122 to 124, **119 passed / 5 xfailed**. 573 + 33 + 2 = 608. They pin
the five measured wrong answers of §2 one by one: the zero count on three arrays
answering 0, 3 and 49 where the old one answered 1, 1 and 1; `Min`/`Max` taken on
the finite entries with the nan and inf counts beside them; no `Min`, no `Max` and
no zero count at all for a string array; a `Content:` row that holds the numbers
and never `IDSNumericArray`; a preview that says `600 of 1000 values not shown`
and stays under 6000 characters; no row ending `: /`; a failed read naming its
exception with nothing of the previous node left on screen; and `panel.update()`
still the one from `QWidget`. Six of them run on nodes of the reference case,
found by the path the shot view spells — `equilibrium/time_slice(0)/boundary/
outline/r` answering 72 values, `2.578317930647737`, `2.8251454055323495` and 0
zeros — which is why the harness grew `shadowTreePaths` and `elementByTreePath`:
`element.text` spells that road with dots and brackets, and a `Path` built from
it evaluates against the runtime as something else. `nodeAsTheBuilderBuildsIt`
now copies `0D_content` the way `build_nodes` does, or a real scalar shows nothing
and the test proves the wrong thing. T11 changed none of the four remaining
`Viz_API.GetSignal` callers: the panel asks one node for its own values, through
the node's own path, and never goes through the scripting layer.

Since T12: **659 passed, 7 xfailed** — forty-nine tests in
`tests/test_42_load_an_occurrence.py`, and the sweep at **126 modules, 121 passed /
5 xfailed** (three modules deleted, five added). 610 + 49 = 659. They pin, on the
reference case, the answer that used to make the whole gesture unreachable:
`occurrencesOf` giving `[0, 1, 2, 3]` for `equilibrium`, `[0]` for
`pulse_schedule`, `[0, 1]` for `magnetics` and `[]` for `core_sources` — and a
shot view of that case **built**, 55 IDS roots in 1.22 s, which is the first time
in this work that the tree exists to be clicked on. Four of them drive the real
frame: an occurrence loaded with the default choice labelled `occurrence 0
[displaying first time slice]` and marked dynamic (the flag the old code raised
only for the fourth choice), `homogeneous_time` read off the instance, the double
click delivering its view through the event loop with the walk held alive until it
finishes, and a double click with nothing selected saying so instead of answering
`IndexError`. The rest drive the four choices as objects: the windows they keep out
of 49 slices, `FIRST_SLICE` on an empty array keeping nothing where the old one
invented 11 nodes of 77, the refusal naming the count and the bound, the choice
that still needs a number refusing rather than opening a dialog in the middle of a
script, the guard on the view rather than on the class — two views, the same
occurrence, both loaded — and the slice question recorded through a stub dialog:
parented to the view, bounded at 48 when 49 slices are in memory. Three tests
check the deletion itself: `find_spec` answering None for the three modules, no
`identifier` anywhere near a choice, and no `limited_nodes` attribute left on any
element of a walked tree.

Since T13: **693 passed, 6 xfailed** — twenty-nine tests in
`tests/test_43_plugins_in_the_menu.py`, and `tests/test_20_plugins.py` rewritten
from eleven tests around the deleted machinery to fifteen around the contract that
survives: **one of the seven xfails died**, the strict one that said the
`getAllEntries` contract was unreachable (`659 − 10 + 15 + 29 = 693`, `7 − 1 = 6`).
The sweep stays at **126 modules, 121 passed / 5 xfailed**: two modules deleted,
two added. They pin the numbers the measurement gave: the plugins of a view
imported and built **once**, however many menus are built (`view.pluginCatalog`,
and one construction counted where the old code paid 0,999 s per click); an entry
found by the **number** its plugin declared, `7` reaching `execute` as 7 and not
as its place in the menu; a plugin raising in `getEntries` leaving the other
plugin's line in place and its own refusal in the log; a plugin that does not
inherit the base class being offered like the others; an undescribed number
refused with the numbers that *are* described; the sub-menu taken back out when
empty; the sub-menu still alive when read back from its action after the gesture
that built it is gone; a `.ui` file refused by name for the widget class this Qt
cannot build — pinned on both `.ui` files the repository shipped then,
`exampleWidget` and `SOLPSwidget`, the second of them gone since T14 — and, for
a window drawn with Qt classes only, the load going
through `QVizLoadOccurrence` like every other load. On the reference case: three
lines for `equilibrium`, two for `core_profiles`, no sub-menu at all for
`magnetics`, and the Shift+right click of that one writing a line in the log
instead of opening an empty menu.

Since T14: **688 passed, 2 xfailed** — the SOLPS plugin and the manual page that
promised it. The sweep loses 9 modules (**126 → 117**) and 4 of its 5 expected
failures; 5 of those modules imported, and nothing outside their subtree called
them (`693 − 5 − 1 + 1 = 688`, `6 − 4 = 2`): five passing sweep tests for the
importable modules, one parametrized case of `test_43` that pinned the refusal of
`SOLPSplugin.ui`, one test added in `test_20` pinning that the package is gone
(`importlib.util.find_spec` answers None for it, and asking for a module inside it
answers `ModuleNotFoundError` — which is the fact worth pinning, since a missing
module under a live package answers None instead). `TESTING.md` §4 goes from 5
import failures to 1, and `QWEN.md` from **121/126** to **116/117**. One honest
correction to make here: a test of mine that asserted `find_spec` answers None for
those submodules *failed*, and a failing test early in the run was enough to shift
the allocation timings of the whole run — the suite then died at a fixed position,
3 runs out of 3, `Fatal Python error: Segmentation fault` inside
`GraphicsView.paintEvent`, the last test reported as having passed being the last of
`test_25_plot_as_slices.py`. With that test fixed, two full runs came back green.
`test_25` and `test_26` pass on their own (31 tests), so this is the harness's known
fragility — an owner dropped while Qt still has a paint event queued — not something
T14 introduced. It was fixed by T15, which is also what makes a seven-gesture
journey test possible at all; the paragraph above stayed as written because the
measurement in it is what T15 stands on.

Since T15: **695 passed, 2 xfailed** — `7` tests added in
`tests/test_44_plot_frame_ownership.py`, the xfail count untouched. Measured before
the fix, with weak references only so the measurement was not what kept anything
alive: of the **110** plot frames a run builds, **79** lose their Python wrapper
before the run ends, and **11** of those had been *shown* without ever being closed
— the only ones Qt can paint, and therefore the ones a queued paint event can kill
the process on: 6 in `test_36_table_plot_entries.py`, 4 in
`test_25_plot_as_slices.py`, 1 in `test_35_selection_entries.py`. The other 68 die
harmlessly, which is why the first version of the rule — "no frame may die" — turned
into **479 cascading failures** out of 690. Three call sites hold what they build
now, and an autouse fixture reports a hazard on the test at fault, once, at its own
teardown — where before the only symptom was a dead interpreter in an unrelated
file. Suite: exit 0 on three consecutive runs; the same three runs before the fix,
with one failing test inserted early, died at test 54.

Since T16: **708 passed, 2 xfailed** in 46 s — `13` tests added in
`tests/test_45_one_user_journey.py`, the xfail count untouched. The suite had 695
tests and not one of them joined two gestures: every file drove one command against
a fixture, so nothing tested the seams the user lives in — whether the view a
command reads is the view another command built. Two numbers came out of probing
before writing. The first is a trap for any future test: a shot view built by hand
passes every gesture alone and cannot draw a selection, because `QVizPlotAsSlices`
defaults to `all_DTV=True`, asks `api.DTVlist`, and answers `ValueError: No signal
selected.` on a selection the view itself holds — the file therefore opens its views
through `Viz_API.CreateDataTree`, the call `QVizOpenShotView` makes. The second is a
limit of the reference case, not of the code: of its 3 368 `equilibrium` leaves, the
48 with two axes to draw all sit under `coordinate_system` and hold no values, so
the picture frame built for one is dropped with `no values in the image`; the
picture branch is exercised on WEST 55799 instead, where `hard_x_rays` adds 5 687
signals and yields `SlicesImage1`. Suite time went from 39 s to 46 s — that is the
price of walking two real cases end to end.

Since T17: **718 passed, 2 xfailed** in **87,9 s** — `10` tests added in
`tests/test_46_time_slices_on_a_real_case.py`. The time is the honest headline:
**+42 s**, because the file walks the same occurrence of a real case four times
over, and the widest of those walks (all 49 slices, 164 792 signals) takes **26 s**
on its own. That is what the manual's four views actually cost, and it was written
down rather than trimmed to keep the suite quick — the marker pair `case`/`dd` is
what lets it be deselected, not a smaller number in the table. What the walking
bought: the sizes of the four views (3 368 / 16 820 / 164 792 signals), the case
answering 49 for its widest dynamic array, and three facts about refusals that the
first probe had wrong — a slice index past the end never reaches the caller (the
parser logs it), a refused view leaves the occurrence **not loaded at all** rather
than keeping the previous view, and the narrower dynamic array (`grids_ggd`, 1
element) only refuses an index when `Ignore_GGD=0` puts it in the walk's way. One
defect is pinned as what happens today rather than promised as behaviour: two views
of one occurrence whose slices overlap **duplicate** those slices (20 188 signals
for five distinct slices, `time_slice(0)` spelled twice).

Since T18: **727 passed, 2 xfailed** in **97,75 s** — `9` tests added in
`tests/test_47_loading_asynchronously.py`, and this is the first task of the run
that changes `imasviz/` rather than only watching it: three `closeProgressBar()`
calls in the failure branches of `QVizIDSViewParser.run()` are gone. The
measurement is the story, because it hung. On the refusal path of an
*asynchronous* load — the default, and the one every menu entry takes — the walk
took its own progress bar down, and a window closed from a thread that does not
own it never comes back here: reproduced with no IMAS and no case, a `QThread`
still inside `QWindow::close()` after a 20 s watchdog, and reproduced again as a
pytest run that had to be killed. What that costs the user is not a message but a
session: the walk thread is lost, `finished` never fires, the parser is never
dropped, the occurrence stays in `loadsInProgress` forever, so every later request
for it is refused as already being loaded, and the bar never leaves the screen.
The rest of the flight was measured to be sound and is pinned as such: the
request returns in 0,010 s with nothing built, the walk runs on `Dummy-1` while
the tree is built on `MainThread` (6 058 signals for `magnetics`, 3 368 for one
slice of `equilibrium`), the in-flight guard stops a second walk in the same view
and leaves another view free to load the same occurrence — which is what the
retired class-level `Lock` used to prevent.

Since T19: **739 passed, 2 xfailed** in **98,79 s** — `12` tests added in
`tests/test_48_figure_lifecycle_through_the_menus.py`, and two more pieces of
`imasviz/` gone. One is arithmetic: `GlobalIDs` carried **38** integer ids for
menu items, counted one by one against every `.py` and `.rst` in the repository,
read **0** times — the three comment blocks above them named consumers
(`wxDataTreeView.py`, `SignalHandling.py`, `LoadDataHandling.py`) that no longer
exist, and a PySide6 menu entry carries a callable, not a number. Only
`RESULT_EVENT` survives, read in two places. The other is a question asked the
wrong way: `ShowHideFigure` and `DeleteFigure` decided what kind of window a
figure sat in by comparing `frame.window().objectName()` against the string
`"IMASViz root window"`, which is true of the application's main window and of
nothing else. `Viz_API.mdiWindowOf` asks what the parent *is* instead. Measured
on a plain MDI area, the old test decided wrong and both entries then acted on
the frame: Show/Hide hid the content and left an empty window on screen, Delete
closed the frame and left the window visible.

The measurement that found the larger defect is the one that asked a simple
question of a session built the way the application builds it: the area is on
screen before the user plots anything, and `QMdiArea.addSubWindow` does not show
what it is given. So three of the four plot entries — selected signals as slices,
TablePlotView, StackedPlotView — registered a window, listed it in the Show/Hide
and Delete menus, and never put it in front of the user; only the one-node entry
called `show()` itself, and only its window appeared. `addPlotWidgetToMDI` now
shows what it embeds, because whoever embeds a figure means it to be seen. The
numbering came out of the same session and is pinned as it behaves: three curves
`SlicesPlot1..3`, delete the middle, the next curve is `SlicesPlot4` — a hole left
by a deletion is not handed back while a higher number is still open — while a
kind emptied entirely restarts at `1`, title included.

Since T20: **748 passed, 2 xfailed** in **117,35 s** — `10` tests added in
`tests/test_49_export_then_open_what_was_written.py` and one taken out of
`tests/test_40_export_to_ids.py`. T20 removes no line of `imasviz/`: the command
it exercises was rebuilt earlier. What it removes is a proof — the round trip of
`test_40`, made on a `StubTreeView` whose cache had been filled by hand from an
`imas.DBEntry` the test opened for itself. That proved the command can put an
object it was handed; it could not show that the gesture finds an object to
write, which is the failure the user cannot see.

Two measurements came out of building the real thing, and both contradict the
sentence "export what is open". The tree of a view keeps the *view*: one time
slice of `equilibrium`, `time_slice[0]` spelled on all **3 368** leaves, while
the cache behind it — and therefore the case that gets written — holds the whole
IDS, **49** slices and **133** filled paths, the same counts the source answers.
And `dataSource.data_entries` is `QVizDBEntryRegistry.ids_cache(uri, mode,
dd_version)`: one dict per **case**, for the whole process. A full run showed the
reference case's cache holding `calorimetry/0` through `tf/0` before this file
loaded anything, so an export from a view of that case writes every one of them.
The application never meets that — `QVizOpenShotView.Open` asks
`isDataSourceAlreadyOpened` and reuses the one view of a case — so the file works
on a case of its own. That case is copied through the Access Layer, not the file
system: the reference run directory holds one 6 365-byte `master.h5` whose groups
are links into `../4/equilibrium.h5`, and a copied directory answers `Unable to
open HDF5 group: equilibrium` the moment the layer follows one.

A third number belongs to the command rather than the test: writing the two IDSs
costs **0,85 s** and reopening what they wrote costs **3,63 s**, against the
**4,6 s** of the tree walk that loaded `equilibrium` in the first place. An
export is not the slow part of this gesture.

Since T21: **763 passed, 2 xfailed** in **124,27 s** — `13` tests added in
`tests/test_50_shot_views_through_the_menus.py` and `2` in
`tests/test_44_plot_frame_ownership.py`. What T21 kills is decided by measurement,
not by taste: the three comparisons that asked what a shot view's top-level window
was *called*, the four copies of `getMDI` that no caller ever reached — all four
gagged on that same name — and the `print` of `legacy_attributes` that every open
paid for.

Four defects, and the order they were found in is not the order of their size. The
one that was hardest to see is the one that made the first run of the new file
answer `RuntimeError: Internal C++ object (PySide6.QtWidgets.QMenu) already
deleted`: `menusShowHideAndDelete` built its two *Views* sub-menus with
`addMenu('Views')`, and that call hands out a QMenu owned by the Python wrapper it
comes back in, so the QAction went on naming a menu whose C++ object had already
died. A standalone probe kept that menu alive and the pytest run did not, which is
how it survived review — and it is the same trap T7 recorded in `QVizPluginMenu`,
which is why the fix is the idiom the rest of `imasviz` already uses: build the
submenu with its parent at construction.

The other three are the shot view's own life. `ShowDataTree` showed the frame and
never the window holding it, so a view hidden from the menu and re-opened from the
start window stayed invisible. `Delete` hid the window and released nothing, under
a commented-out `deleteLater()` and a TODO blaming Qt for a bug that Qt 6.6.3 does
not reproduce: four openings and two deletions left **8** windows in the area for
**2** live views. And on an MDI area that does not carry the magic name — the
branch the sources themselves comment as "e.g. when running examples" — Show/Hide
hid the whole window holding the area, taking every other view with it.

Two of those numbers only hold if the harness asks for them properly, and both
were measured rather than assumed. A window released by `deleteLater()` stays in
`QMdiArea.subWindowList()` until the deferred-delete events are delivered:
`processEvents()` alone answered **2**, `sendPostedEvents(None, DeferredDelete)`
answers **1** — so a window count taken without that reports what the *previous*
test left behind, which is how one of these tests first failed in the wrong
direction. And the ownership guard had to learn the other way out of the paint
queue: deleting a view hides its window, a hide reaches the children recursively,
and then Qt deletes that window at a point of the event loop Qt chose — so the
preview plot nested inside the frame dies legitimately, and `test_44` now pins
both halves of that rule.

Since T24: **765 passed, 2 xfailed** in **127,16 s** — `2` tests added in
`tests/test_43_plugins_in_the_menu.py`. This row kills nothing and says so; what it
removes is the silence around a plugin that had stopped working. Measured on the
reference case, the registered Profiles plugin answered **every** entry with
`AttributeError: 'VizProfiles_plugin' object has no attribute 'dataTreeView'`, on
the first line of `execute()` — the line that asks its view which occurrences the
case holds. The catalog that replaced the old handler bound the node the menu was
built on and never the view, although its own docstring says both are set when the
menu is built; `git` shows the handler it superseded calling `setDataTreeView` on
every plugin. So the documented way for a plugin to reach its case had no framework
behind it, and the guard that is otherwise a good idea — `run` logging `Plugin %s
failed: …` — is what made a test asserting "a failing plugin is named in the log"
pass right over it.

Two things the same probe measured and this slice deliberately left alone, because
they belong to the plugin and not to the framework, and fixing them quietly would
hide a second defect behind a first: the plugin now gets as far as registering its
window as `PlotView:1`, then raises `TypeError: unsupported format string passed to
IDSFloat0D.__format__` while labelling its time slider (`VizProfiles.py:504`) — the
same family of IMAS-Python mismatch as the `eval("imas." + ids + "()")` sites T12
removed; and this case holds **4** occurrences of `equilibrium`, which the plugin
asks through a modal `QInputDialog` that sat **240 s** offscreen until the watchdog
killed the process. The second is why no test in the suite drove a plugin entry end
to end — until T22's first step, which fixed the first as well.

That probe also wrote that the plugin "builds **0** plot". **That count was wrong**,
and it is worth keeping the error in the record: it came from
`window.findChildren(pyqtgraph.PlotItem)`, which answers **0** on a
`GraphicsLayoutWidget` whatever is drawn there, because such a widget keeps its
`PlotItem`s as *scene* items rather than Qt children. Count them through
`layout.ci.items`, and `test_51` pins that difference — on that same window it
answers **41** where `findChildren` answers 0.

Since T22(a): **775 passed, 2 xfailed** in **131,70 s** — `10` tests added in
`tests/test_51_profiles_plugin_figure_menu.py`, the suite's first to run a plugin
entry end to end. Two defects stood in the way, both in the plugin and not in the
framework: an `IDSFloat0D` formatted with `:.2f` (a `numbers.Real` wrapper with
`__float__` and no `__format__`), raised inside `setUI`, which left the whole
control row under the plugin's tabs unbuilt; and `CustomizedViewBox.getMenu`
walking `self.menu.leftMenu`, a sub-menu pyqtgraph **0.13.7** keeps as a local of
`ViewBoxMenu.__init__`, so the right click answered `AttributeError` before the
menu could open. Between them, steps 4, 5 and 6 of the manual's Profiles walkthrough
(`doc/source/manual/plugins.rst`) were not slow features but absent ones. With both
fixed, the reference case answers: occurrences **[0,1,2,3]** for `equilibrium` and
`core_profiles`, none for the three other IDSs the plugin claims; `run` back in
**4,94 s**, window on screen **6,5 s** later as `PlotView:1` — top-level, `parent()`
`None`, never embedded in the MDI area, unlike the figure frames T19 put there;
**2** tabs, **41** plots, **41** curves (**37** over the **101**-point radial
coordinate, **4** over their own **72**); slider **0..48**; `getMenu()` **0,03 s**
for **13** actions, the same 13 on three openings. Nothing left the repository in
this step — the island the Profiles plugin reaches is intact, and now measured.

Since T22(b): **776 passed, 2 xfailed** in **126,47 s** — `1` test added, and the
three tests that pinned the `Figure:` windows re-pointed with the code. The
plugin's three calls into the island (`AddPlot1DToFig`,
`plotVsCoordinate1AtGivenTime`, `plotVsTimeAtGivenCoordinate1`, made by its own
`CustomizedViewBox`) now run `QVizPlotOneNode`, the command the shot view's menu
runs. What the two new-figure gestures answer changed in kind, not in amount:
`Figure:1`/`Figure:2` at **0,05 s** each became `SlicesPlot1` (**101** points,
**0,013 s**) and `SlicesPlot2` (**49** points along time, **0,061 s**) — the same
curve over the same abscissa, in a frame the Show/Hide and Delete menus fill and
the "add to" gestures offer, embedded in the MDI area. The `Plot <quantity> to`
sub-menu lists the open curve figures whose curves run along the same abscissa,
and one of its lines adds a curve without opening a window. What this killed is a
duplicated rule rather than a module: the abscissa gate lived on
`QVizSignalHandling`, and the plugin needed the same answer, so it moved to
`Viz_API` beside the `figToNodes` record it reads — **14** lines out of the menu
controller, **21** into the registry, and one question with one answer. Measured,
every one of the plugin's 41 quantities answers the same `curveAxisKey` —
`('LEAF', 'equilibrium', 'time_slice(itime).profiles_1d.psi')`, one leaf axis
beside the time base — which is why the gate is what decides, and not a name.

Since T22(c): **760 passed, 2 xfailed** in **129,19 s** — the island is out of the
repository, **2 080** lines deleted against **149** added over 35 files. Five
modules go (`QVizPlotWidget` 595, `QVizCustomPlotContextMenu` 454, `QVizPlotSignal`
198, `QvizPlotLayoutWidget` 127, `QVizAbstractPlot` 14), and with them the **ten**
`Viz_API` entries that handed out their keys and read through them — the first
count of this row said six, and was wrong by four (`nodeDataShareSameCoordinates`,
`nodeDataShareSameCoordinatesAs`, `GetFigurePlotsCount`, `GetNextKeyForFigurePlots`)
— **236** lines out of the api and **26** out of `QVizTreeNode`. A demo script
(126), the unregistered `CompareFLT1DPlugin` with its package (91) and the
`test_13` that pinned the frame's axes (77) go too. `FigureTypes.FIGURETYPE` and
its `MENU_ORDER` entry go: the Show/Hide and Delete menus walked five kinds that
day (six since T27 added the Equilibrium plugin's window), and
`test_30` pins the consequence — a frame still registered under `Figure:` sits in
the bookkeeping and is named by **no** line, so the two menus come back disabled
rather than offering a sub-menu no command can fill. Four registry helpers and
three menu-controller ones lost their `figureType=FIGURETYPE` default, which is
what made a call naming no kind mean the dead one silently.

What the user loses, measured before it was written down rather than after. On a
new curve or image figure the right click answers pyqtgraph's own **4** entries —
`View All`, `X axis`, `Y axis`, `Mouse Mode` — and the scene adds exactly **1**
line, `Export...`, offering the five exporters the pinned stack registers (CSV,
HDF5, image file, matplotlib, SVG): so the manual's Export feature came from the
scene, not from the menu that went, and survives. What does **not** survive on the
new frames is `Configure Plot`, `Show/Hide error bars`, `Show error bars (with
slicing)` and `Show/Hide confidence bands` — the four entries the deleted
`QVizCustomPlotContextMenu` copied from the Profiles plugin's own view box, and
which the new frames never had. They are reachable today only inside the plugin's
window, which is why `QVizPlotConfigUI` stays in the package: its one caller left
is `CustomizedViewBox:230`. That is a gap in the new path, not a regression from
the old one, and it is named here rather than smoothed over: closing it means
carrying those four onto `QVizCurvePlot`, where the copy that survives is the
plugin's own — the deleted menu was the second one, so (c) did not duplicate the
error-bar and confidence-band code, it left exactly one copy, on the wrong class.

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
