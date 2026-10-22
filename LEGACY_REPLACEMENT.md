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
  drops the 10 connections it makes to that class (3 for `SOLPSplugin.ui`), and
  `createWidget` is never called. Such a plugin is now refused by name, naming
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
cannot build — pinned on both `.ui` files the repository ships, `exampleWidget`
and `SOLPSwidget` — and, for a window drawn with Qt classes only, the load going
through `QVizLoadOccurrence` like every other load. On the reference case: three
lines for `equilibrium`, two for `core_profiles`, no sub-menu at all for
`magnetics`, and the Shift+right click of that one writing a line in the log
instead of opening an empty menu.

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
