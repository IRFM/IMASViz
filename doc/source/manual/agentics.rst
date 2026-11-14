..
   Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
   and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
   CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
   The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

.. include:: ../icons.inc

.. _agentics:

Agentics: IMASViz driven by name
================================

IMASViz 3.0.0 is addressed by name as well as it is clicked. A prompt asks the
application for a run of its own gestures -- open the case, load the IDS, select
the quantities, draw the curves and the pictures, save the session, write the
reports, take the screenshots -- and what the run produced is indistinguishable
from what you drew yourself: the same figures in the :guilabel:`Windows` menu,
the same named refusals in the log panel, the same sessions in the same folder.
:ref:`scripting` drives those same gestures from Python; this page drives them
from a sentence.

It is one core and one tool set, seen through five faces:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - the face
     - the entry
     - what it is
   * - the in-app agent
     - :guilabel:`File --> Agent`
     - a window of the session: the transcript on top, the prompt below, the
       run's LLM calls and one loop. The figures it opens are figures of the
       session.
   * - the MCP service
     - ``python -m mcp_server``
     - the official Model Context Protocol endpoint of one session,
       ``http://127.0.0.1:8765/mcp``, for any MCP client.
   * - the line client
     - ``python3 -m viz_cli``
     - the same agent without its window: a REPL, offscreen by default, its
       images and its transcript on disk.
   * - the web client
     - ``python3 -m viz_web``
     - the same agent on a page: the chat, the gestures, the captures of the
       turns, the IMASViz window offscreen.
   * - the multi-user gateway
     - ``python3 -m viz_gateway``
     - one web session per user, behind a token: the pool, the login page, the
       budget.

All five read the model from the same three preferences lines
(:ref:`agentics_llm`), speak the same words to the quantity a case holds
(:ref:`agentics_axes`), and refuse by name: a refusal is the sentence the face
answers with, never a silent failure.

The in-app agent
----------------

The entry is :guilabel:`File --> Agent`, on the menu bar of the application
window -- on the bar that is on screen whatever window you are looking at, the
bar that also carries the session entries and :guilabel:`Quit`.

The first click builds one window; a second click brings that one back to the
front. It is a **window of the session**, like the Profiles panel and the
Equilibrium chart: it is top-level (not in the MDI area), it is registered in
the session under a key of its own kind (``Agent:1``), and it is listed by
the :guilabel:`Windows` menu next to the figures the user drew. What that
listing is not, two things: a saved session does **not** write the
conversation down -- a transcript is not a gesture a restore could replay, and
the run that closes the panel leaves the cases, the loads and the figures it
drew where they are, the ones a session can put back. It opens **whether or
not a case is on screen**: the agent can be asked what this run holds, and the
case is opened by the gesture it answers with.

The window holds, from the top:

- the **transcript**, read-only, one line per event of the run -- the
  prompt, every tool the loop called with the arguments it named, every
  answer, and every refusal;
- the **prompt box**, one line or several;
- three buttons: :guilabel:`Tourner` (run the loop on what is typed),
  :guilabel:`Arrêter` (stop the loop at the next turn boundary) and
  :guilabel:`Effacer` (clear the transcript and the box).

The button labels are in French, as the panel speaks its own language. The
transcript it fills is what the run leaves: the words the loop spoke, and each
refusal among them; what the run drew as figures stays in the session, and
nothing else of it is written down.

While a run is on:

- the LLM call runs on a **worker thread**, so the GUI stays responsive
  through a call that takes minutes;
- every gesture runs on the **GUI thread**, through the same bridge the MCP
  service uses, so the widget tree is only ever touched from the thread that
  owns it;
- the loop is bounded: it stops at the turn limit (the face names it), and a
  run that refuses is refused **with its reason in the transcript**, prefixed
  ``REFUSAL`` -- the style of this application, kept through the loop.

The LLM is not configured at the window: the endpoint, the model name and the
key come from the preferences (:ref:`agentics_llm`), and the **first run** is
what connects. A first run against an endpoint that does not answer is a
named refusal naming the endpoint it asked, not a hang.

The one core and the one tool set
---------------------------------

There is **one** core: the class that drives one IMASViz session with the
application's own commands -- opening a case, loading an occurrence, selecting
a path, drawing a quantity, saving the session -- written once, importing the
application and nothing else, and shared by every face of this page. The MCP
core, the in-app agent's core, the REPL's core and the page's core are the
same class. That is what keeps the five faces from drifting apart: a tool that
refuses on one face refuses on every face, and a figure the MCP client drew is
the one the *Windows* menu names.

The tool set the core offers is declared in one place, and every face takes it
unchanged -- the loop is handed its schemas, the web page validates its
requests against the same ones, and the MCP server reads each tool's words off
the same descriptions. The tools, in the order the faces group them:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - the group
     - the tools
     - what they answer
   * - cases
     - ``open_case``, ``list_cases``, ``close_case``
     - open one case by URI (an HDF5 path, or an UDA URI), the cases open and
       the occurrences each one holds, close one for good.
   * - the IDSs
     - ``list_idss``, ``list_case_idss``, ``load_ids``
     - every IDS the data dictionary declares, the short list of the IDS the
       case **actually** holds (the one to trust), and the load of one
       occurrence into the tree -- "first" for the slice a plain load keeps,
       "all" for the whole dynamic array.
   * - the tree
     - ``search_nodes``, ``describe_node``, ``describe_ids``,
       ``list_quantities``
     - the leaves matched by a substring of their spellings (any of the
       match's three spellings is what the plot tools take), what a node holds
       (units, size, finite minimum and maximum, the zero/nan/inf counts, a
       bounded preview), what the dictionary says of an IDS, and the filled
       tensors of an occurrence grouped by the array of structures that drives
       them.
   * - the selection
     - ``select_signals``, ``unselect_all``, ``list_selection``
     - put paths into the case selection as clicks would (a path the tree does
       not hold is refused by name and the selection is left as it was), empty
       it, read it back.
   * - the drawing
     - ``plot_one``, ``plot_slice``, ``plot_selection``, ``plot_table``,
       ``plot_stacked``, ``get_signal``
     - one quantity into the figure its axes call for (a curve for one axis, a
       picture for two), a 1D-profile at a single instant, the selection, one
       panel per quantity in a Table Plot View, the stacked view, and the
       **values** of a leaf, as JSON -- the same read the plots use, so the
       figure a viewer sees and the numbers a read reports are the same
       element of the same array.
   * - the windows
     - ``list_windows``, ``show_window``, ``hide_window``, ``close_window``
     - the session's windows in the order the menus draw them (kind, label,
       key, on screen), put one back, take one off without deleting it, delete
       one for good.
   * - the plugins
     - ``list_plugins``, ``run_plugin``
     - the entries an IDS root earns, in registration order, with the refusals
       of the plugins the case cannot offer **named alongside**; and one entry
       run with the answers the entry would have asked the user -- which is
       what keeps a modal question off the path of a loop.
   * - sessions and configurations
     - ``save_session``, ``restore_session``, ``list_sessions``,
       ``list_configurations``, ``select_from_configuration``,
       ``save_selection``, ``save_plot_configuration``
     - the whole screen as the application writes it, put a session back the
       way the gesture replays it, the sessions the folder holds, the plot
       (``.pcfg``) and selection (``.lsp``) files, apply one of them (the
       IDSs the case would need and does not hold are loaded first, the way
       the menu does it), and the two saves.
   * - the reports
     - ``plot_report``, ``case_report``
     - a window of curves as a self-contained HTML file on disk (the image of
       the window and one row per trace, with its statistics), and the loaded
       tree of a case the same way.
   * - the export
     - ``export_to_ids``
     - the opened IDSs of a case into the target case, under the data
       dictionary the case was read at.
   * - the screen
     - ``get_screenshot``, ``focus_window``
     - a window as it stands, in PNG -- the application, one figure, or the
       shot view of a case -- and bringing a window forward at a readable
       size, the preparation of a capture.
   * - the log
     - ``get_logs``
     - the log panel of one case, or of every case: the last lines the gestures
       wrote there, the named refusals among them -- where a loop reads what a
       dialog would have told a hand.
   * - the journals
     - ``search_journals``, ``list_notes``, ``read_note``, ``add_note``,
       ``delete_note``, ``journal_stats``
     - the two journals of the run: the **personal** one (the author's own
       notes, under ``~/.imasviz/journals``) and the **shared** one
       (:ref:`agentics_journal_shared`) -- a note is one file with its own
       front matter (*machine*, *campaign*, *shot*, *date*, *author*,
       *title*) and its body, and a search narrows by any of the filters and
       ranks by meaning when the embeddings endpoint is named
       (:ref:`agentics_journal_llm`), by words while it is not.

.. _agentics_journal:

The two journals
----------------

A note is one line in a journal: a file of a front matter the reader filters
on -- the *machine* (the tokamak), the *campaign*, the *shot* number, the
*date* of the shot, the *author* of the note (required on every write, the
``$USER`` of the run when the one that wrote it did not name one), and a *title*
-- and a body. A note may name a shot and a machine, and one as well as an
observation with neither: the *date* of a shot is still a date the note
answers by, and the body is what a query runs on while the fields name the
note the filters do not.

The two are:

- the **personal** one, under ``~/.imasviz/journals/``, one for each user of
  the node; and
- the **shared** one, under :code:`SharedJournalDir` in the preferences
  (:ref:`agentics_journal_shared`) -- an AFS directory the writers of the
  node reach, so that a note written by one is reachable by the others, and
  the author of the note is the ``$USER`` of the writer, written by hand.

The read: ``search_journals`` (the query and the filters), ``list_notes`` (the
filters alone, in date order), ``read_note`` (the body by the id a search or
a list names), and ``journal_stats`` (what the two journals hold on this node,
and whether the embeddings endpoint is named and the model it names). The
write: ``add_note`` (a new line in one of the two, the fields that name it,
and the body), and ``delete_note`` (one of them, gone). Every refusal the read
answers is one the write does not take: a note with no author is refused by
name, a body that is empty is refused by name, and an explicit ask for the
shared journal on a node that does not hold one names the reason, not the
other journal.

The shared journal is a visible line the writers read: a write to the shared
one is **asked for, not taken** -- the loop runs it only when the request
names the shared journal in the user's own words (*publier au journal
partagé*, *share this*, *cahier de manip*, or in English), and a write
the model reaches for on a request that names no shared journal is a named
refusal: the gesture, the journal that would hold the line, and nothing was
written. The same rule wears on the *Windows* menu's close and on the *File*
menu's new session: a close the model runs, the loop names the gesture and
the rule, the case and the session are still in force.

The ranking: ``search_journals`` ranks by **embeddings** when
:code:`AgentEmbedEndpoint` is named and the server answers (the
:ref:`agentics_journal_llm`), and by **words** while it is not, or while the
server does not answer -- which is what ``journal_stats`` says, in
``method`` and, for the fallback case, in ``fallback_from`` and
``fallback_reason``: a search that ran on the keyword with the reason named
is not a search that presented itself as an embeddings answer. The vectors
the endpoints answer are cached under the note's journal folder, keyed on
the note's body, so a second search of the same corpus asks the endpoint for
the query and reads the rest.

.. _agentics_axes:

Asking for a quantity of several axes
-------------------------------------

A quantity is not drawn "at random". It is addressed with **one axis to run
along** and **the other axes pinned at their index** under the names the tree
gives them -- and :code:`plot_one`, :code:`plot_slice` and :code:`get_signal`
take that pair in exactly the same shape, so the number a read reports and the
element a figure draws are one and the same thing.

The two words:

- **``along``** -- the axis the curve runs along: the clock (leave it out, and
  the clock is what the quantity runs with), or one of its own axes, named by
  its name (``psi``, for the pressure profile of ``equilibrium``). A word no
  axis answers is refused by name, with the axes the read holds.
- **``indices``** -- the other axes, one index each, each under the name of
  its axis: a *structure* array (``time_slice``, ``profiles_1d``, ``ion``,
  ...) -- one entry per such array the quantity sits in -- or the leaf's own
  coordinate (``psi``). The index is 0-based, and the extent is the one the
  tree holds: an index past it is a refusal with the reason, not a silent 0.

Three spellings of the same address still stand, and are the way the faces
before this release spoke it: ``along_time`` (a curve), and
``as_function_of_time`` / ``coordinate_index`` / ``time_index`` (a read).
They answer as before; the pair above is the one the loop is taught first.

Three ways to ask for one quantity, on the reference case (WEST 54924, run 0)
for the pressure profile of ``equilibrium``:

1. **Along the time.** The profile is held by the dynamic array, so it runs
   along the clock by default. *"the pressure at psi = 50"* is
   ``plot_one(uri, "equilibrium.time_slice[0].profiles_1d.pressure",
   indices={"psi": 50})`` -- the curve it answers is the 49 samples of the
   case's ``time_slice``, not a point.
2. **Along the coordinate that is not the time.** *"the pressure as a
   function of psi"* is ``plot_one(uri, ..., along="psi")`` -- 101 samples, x
   running over the coordinate of the leaf itself, where along the time it
   was 49 samples over about 16 seconds. :code:`get_signal` with the same
   address reports the same curve: a figure and a read that disagree about
   the abscissa have been a refusal since this release.
3. **A slice at an instant.** *"the pressure of the slice closest to 35 s"*
   is ``plot_slice(uri, leaf, time=35)`` -- the value the Access Layer answers
   at that instant (its own slice read, not a GUI-side interpolation), with
   ``linear`` (the default), ``closest`` or ``previous`` interpolation. A
   ``time`` outside the case's range answers the nearest slice it holds, and
   the answer names the time asked and the slice time **apart**, not a value
   that resembles one. ``time`` and the ``along``/``indices`` pair are
   refused together: they are two opposite ways of reading the array.

Two figures, two ways (and two ways only):

- **Stacking on the figure already open.** The first :code:`plot_one` opens the
  figure and **is** what its key is (``Plot1``); the next ones pass that key
  and are drawn on it. N indices of **the same leaf** is N curves on **one**
  figure: each curve is pinned to the index it carried, and the slider the
  figure holds is not touched when stacking -- which is what the four identical
  curves of the old bug would have been, all of them answering the last value
  the slider was set to.
- **Select first, draw after.** :code:`select_signals` then
  :code:`plot_selection`: one selection, one figure per figure kind the
  selection calls for.

What a superposition is **not**: two different structures (two probes, then two
loops) is **two** figures, not four in one. The structure is already fixed by
the path that named the leaf -- a family index is not a slider of the figure,
and the faces refuse to treat it as one.

And a run never closes what you did not ask to close. The three gestures that
empty the bookkeeping -- close a figure, close a case, restart the session --
happen only when **this run** asks for them, in French or English
(*ferme Plot5*, *referme le cas*, *nouvelle session* ...) -- any other run
that poses one meets a named refusal, the gesture is not taken, and the answer
says so: nothing was closed. That is the way the old bug went: the loop closed
a figure, the window was gone from ``list_windows``, and the loop noticed it
itself, without having asked for it.

A dictionary of ready phrases, with what they answer on the reference case:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - the ask
     - say to the agent
     - what answers
   * - the pressure along the time, at one psi
     - "trace the pressure at psi = 50"
     - :code:`plot_one(..., along` left out`, indices={"psi": 50})`
   * - the pressure as a function of psi
     - "draw the pressure as a function of psi"
     - :code:`plot_one(..., along="psi")`
   * - three psi's on **one** figure
     - "draw psi = 0, 10 and 50 on **one** figure"
     - three :code:`plot_one`, the two last with the first's key
   * - two probes, then two loops
     - "draw probe 2 and probe 10, then loop 2 and loop 10"
     - **two** figures
   * - a slice at an instant
     - "the pressure of the slice at 35 s"
     - :code:`plot_slice(..., time=35)`
   * - the value at one psi
     - "read the pressure at psi = 50"
     - :code:`get_signal(..., indices={"psi": 50})`
   * - a capture of the figure
     - "show me Plot1" / "capture of Plot1"
     - :code:`focus_window(window="Plot1")` /
       :code:`get_screenshot(window="Plot1")`

The MCP service
---------------

The service keeps the application as the main program -- the same
construction as the window, the same preferences, the same log panel -- and
adds to it the MCP endpoint of its tools: the official SDK over
``streamable_http_app()``, served by uvicorn in a thread of its own event
loop, and every tool is queued to the GUI thread by the same bridge the
panel uses. Nothing here changes the application; the application gains a
door.

.. code-block:: console

   $ python -m mcp_server --port 8765
   IMASViz is serving its tools on http://127.0.0.1:8765/mcp

The endpoint is ``http://127.0.0.1:8765/mcp`` (``--host`` and ``--port``
are the two words; 127.0.0.1 and 8765 are the ones it answers by default).
Point a client at it, in the client's own way -- the configuration a Qwen
Code session reads, for example:

.. code-block:: json
   :emphasize-lines: 3

   { "mcpServers": {
       "imasviz": {
         "url": "http://127.0.0.1:8765/mcp" } } }

Two things to know before pointing at it:

- a **port** that another service holds is refused by name -- the run does not
  die silently, and the application window does not start either, because on
  this path the service **is** the application;
- ``--offscreen`` is the switch for a node without a display: the window is
  built offscreen, and everything on this page still stands, capture
  included, because the captures are read off the window, not off a screen.

**One-shot mode** is the way a node without a display uses the same loop: a
prompt, run on the in-app agent, its figures saved as PNGs, and its
transcript saved beside them. It does not serve the MCP endpoint on that
path, and it is not a second copy of the loop -- it is the one the panel
runs, driven offscreen.

.. code-block:: console

   $ python -m mcp_server --agent "Ouvre le cas imas:hdf5?path=…/west/3/54924/0, \
   ouvre equilibrium 0, trace la pression le long de psi, et donne-moi la capture" \
       --llm-url http://127.0.0.1:8080/v1 \
       --llm-model qwen3.8:27b \
       [--llm-key KEY] \
       [--max-turns 8] \
       [--shots ./agent_shots] \
       [--extra-shots app,case-views]

The run exits **0** when the loop answered, **1** when it refused -- the
refusal is a line on the standard error, named. The defaults are the
preferences' (endpoint, model), the turn limit is 8, the directory is
``./agent_shots``, and ``--extra-shots`` adds captures of the interface
itself (the application, the case views) beside the run's figures. The
transcript of the run is on disk where the shots are: the loop's words, and
the loop's refusals among them, the way you would have read them in the panel
of :guilabel:`File --> Agent`.

The line client
---------------

The REPL is the same loop and the same tools, run **without the window**:
one offscreen session, kept open for the whole life of the client, so a prompt
can point at what the one before it named. The keyboard is the client's own:
a small line editor over the terminal, because the node's Python holds the
``readline`` module without the C extension behind it (measured), and with it
go the arrows, the history and the completion. The history the client keeps is
one file, ``~/.imasviz/cli_history``, held between runs the way the
preferences are held, and ``Tab`` completes the commands, the fields they
steer, and the gestures the session answers today.

.. code-block:: console

   $ python3 -m viz_cli
   IMASViz client — the agent, offscreen. Endpoint http://127.0.0.1:11434/v1,
   model qwen3.8:27b, 12 turns. A line runs it: its images and its transcript
   are saved under /home/you/.imasviz/cli/shots. Commands: /help.
   IMASViz>

A line that is not a command is the prompt. The commands, the words they take,
and the two of them that **persist** (``endpoint``, ``model`` and ``key`` are
written into the preferences file the GUI reads; the other fields of the same
line are run-local):

.. list-table::
   :header-rows: 1
   :widths: auto

   * - the command
     - what it answers
   * - ``/llm``
     - the parameters in force -- endpoint, model, key, the turn limit, the
       temperature, the max tokens of the calls the loop sends
   * - ``/llm endpoint URL``
     - the model's endpoint, ``http://host:port/v1`` (persisted)
   * - ``/llm model NAME``
     - the model to send; ``auto`` is the endpoint's first ``/v1/models``
       entry, read on first use (persisted)
   * - ``/llm key TOKEN``
     - sent as an Authorization header when non-empty (persisted)
   * - ``/llm max_turns N`` / ``temperature X`` / ``max_tokens N``
     - this run only: the loop's turn limit, and the two fields of every call
       it sends
   * - ``/mcp`` / ``/mcp NAME``
     - the endpoint, its models and the tools of this session -- and one
       tool, its words and its parameters, the same schema the loop takes
   * - ``/ids [URI]``
     - the IDSs the open case actually holds, **raw**: the names and their
       occurrences, read of the case's entry with no LLM in between
   * - ``/shots [DIR]``
     - where the turns save their images (``~/.imasviz/cli/shots`` by default)
   * - ``/session`` / ``/session save NAME`` / ``/session restore NAME``
     - the cases open in this session, and the two gestures of the *File*
       menu, the same files, the same rules
   * - ``/history``
     - the prompts of this run of the client
   * - ``/help`` / ``/quit``
     - this list, and the leave
   * - (a line)
     - the prompt, run on the loop; its images and its transcript are saved,
       named after the turn, under the shots directory

The one-shot mode is the same as the one of the MCP service, one command to
the other: ``python3 -m viz_cli "trace le champ, donne-moi la capture"`` runs
offscreen, writes the figures and the transcript under ``--shots`` (``~/.imasviz/cli/shots``
by default), and exits 0 when it answered, 1 when it refused. ``--display``
keeps the display when the node has one. ``Ctrl+C`` during a run stops it at
the next turn boundary -- and still saves what it drew.

The web client
--------------

.. code-block:: console

   $ python3 -m viz_web --port 8770
   IMASViz web is up on http://127.0.0.1:8770

The point of the web is that the IMASViz window stays **off the screen**: the
application is built offscreen by default (``--offscreen`` names the choice,
``--host`` is the other word), and the page is the session -- the loop with a
picture. One self-contained page, no build and no external dependency; the
routes it speaks to, and the two of them that matter:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - the route
     - what it is
   * - ``POST /api/agent``
     - the prompt, run on the loop; its lines stream over this route as they
       are written, a :code:`Stop` is ``POST /api/agent/stop``
   * - ``POST /api/tool``
     - one gesture of the core, driven by hand -- the same tool set, the same
       refusal rules, the same values
   * - ``GET /api/turns`` / ``/api/turns/{n}`` / ``/api/turns/{n}/shots/{name}``
     - the turns of the session: the list, one turn, and the captures of the
       turn -- the PNGs are on disk under the shots directory, and the page
       asks for them when the group is opened
   * - ``GET /api/reports`` / ``/api/reports/{name}``
     - the reports, the way the loop names them
   * - ``GET/POST /api/llm``
     - the parameters of the loop, the way ``/llm`` answers them
   * - ``GET /api/tools``, ``GET /api/health``
     - the tools of the session, and the one line that says the session is up

The captures are grouped **by turn**: the turn on screen is open, the turns
before it are closed until they are opened, and on a reload the page rebuilds
the whole group from ``/api/turns`` -- the images are on disk, never lost,
only folded. Two things a page that shows fewer pictures than it should
answers by default:

- **A figure is captured in the turn that drew it.** A turn that does not
  draw -- words only, a refusal, one capture alone -- does not leave a PNG.
  Draw **and** ask for the figure in the same prompt: *"trace the pressure at
  psi = 0, 10 and 50 on one figure, and give me the capture"* -- one run, one
  image, the group arrives open.
- **A re-capture is asked by the name of the figure.** *"show me Plot1"*
  brings that figure forward (``focus_window``); *"a capture of Plot1"* saves
  it (``get_screenshot``). The page's own button on a capture card does the
  second one.

The multi-user gateway
----------------------

A session of IMASViz is one user by construction: one application, one window,
one ``Viz_API``, one registry of cases for the whole process. Two users in one
process are two mice on the same screen -- the cases of one visible to the
other. The gateway is the way to keep **more than one user at a time**
without touching any of the layers it wraps: **one instance per user**, each
in its own process and its own :file:`HOME`, and the gateway is the proxy and
the supervisor around them -- it has no widget of its own.

.. code-block:: console

   $ python3 -m viz_gateway --port 8760 --users-dir ~/.imasviz/gateway \
       --max-users 20 --idle-timeout 1800 --max-turns 12

The words it takes:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - the word
     - what it decides
   * - ``--host`` / ``--port``
     - the interface and the port the gateway listens on (127.0.0.1, 8760)
   * - ``--users-dir``
     - the directory the user table ``users.json`` sits in
       (``~/.imasviz/gateway``) -- the mapping token → user → backend
   * - ``--max-users``
     - the pool's budget: how many **live** instances at once (20)
   * - ``--idle-timeout``
     - the seconds of silence before an instance is reaped (1800 s): its
       port is kept, its budget goes back to the pool, and the token
       **remains valid** -- the next request comes up with a new instance
       behind it, and the caller does not notice
   * - ``--max-turns``
     - the turn limit the local instance is told (12, what the web answers by
       default)

A user is a row of the table and a token of the gateway. The table holds a
backend of the user -- **local** (an instance the gateway launches here, on
127.0.0.1 of a port of its own) or **remote** (the URL of an already running
backend, the token reaching it as a header), and the issuance is scripted:

.. code-block:: python

   from viz_gateway.userstore import UserStore
   store = UserStore('~/.imasviz/gateway')
   store.issue('alice', 'local')                          # → her token
   store.issue('bob', 'remote', url='https://viz.example:8770')

The browser is then pointed at ``http://127.0.0.1:8760``, and the gateway
answers with the **login page**: one field -- its token, *the one the
gateway issued to you* -- and one word to press, :guilabel:`In`. The token
the table holds is checked against it, and is set as the cookie
``imasviz_token`` (``HttpOnly``), and the session continues on top of it: the
browser logs in once, and a wrong token is refused *by name* in the words the
table says, with a 401 the page prints. The rest of the page is transited as
it is written -- the chat, the tools, the captures, the reports -- and a
script keeps the ``Authorization: Bearer <token>`` header, or gets the cookie
back with a ``POST /login`` of a JSON body.

The refusals are the page's words, and the gateway's are named, not swallowed:

- **No token** → 401, the sentence that says so.
- **Unknown token** → 401, the token named **and** the users the table holds.
- **A pool full** → 503, the number of live instances and the budget it
  answers.
- **An instance that does not come up** → the name of its port, of its
  :file:`HOME`, and of its exit code if it is dead.

The cost per user is a **Qt process** (about 150–300 MB, and the Qt thread
itself) -- it is not the port. On a node, it is the memory that bounds the
number of concurrent users, before a port runs out (the range available is of
the order of 35 thousand).

.. warning::

   In this release the local backends listen on 127.0.0.1: another **local
   account** on the same machine can technically reach that port (the loopback
   is shared). The token is a control of access to the **content** of one
   user, not to the socket. The route that closes the gap is each local
   backend listening on a Unix domain socket, isolated by its permissions
   (client of the proxy pointing at that socket, the port disappears), and the
   token answering the same way. The manual of the gateway, in French -- its
   prerequisites, the way to start, the issuance of a user, the diagnosis of
   an instance that does not come up, the refusals, the budget, and the FAQ
   for a colleague -- is :file:`viz_gateway/USAGE.md`, at the root of the
   repository.

What a refusal costs
--------------------

The five faces answer a refusal the same way, and the cost of a refusal is
**nothing**:

- no empty figure -- a refusal of the read does not open a window before
  naming it: the figure is not there, the key is not taken, and the next
  figure of the kind is numbered where the last one ended, not over a hole;
- no window answering to a name that is already taken -- a key a live window
  already holds is refused to the run, and two windows under one name, one of
  them unreachable by any gesture, is what that refusal keeps out;
- a sentence, on the face that asked for it -- the transcript of the panel, a
  line of the standard error of the one-shot, a 401 of the gateway with its
  two words -- and the same sentence is in the log panel of the case, where
  ``get_logs`` reads it when it is the loop that asked for it.

And the loop is **not** allowed to make up an answer it did not read. Three
guards, and each is a refusal of the face, named:

- **The number.** A number the run reports must be one the tool read **this
  run**. A figure and a number of a table, without a single call to a tool
  that reads, are a refusal of the run, renouncing the two tools that must be
  called (``get_signal`` / ``plot_one``), and refused again when they repeat
  it. A value the case does not hold is a refusal with the extent the tree
  holds, not a 0.
- **The name of a figure.** A name of a figure without a single opener of a
  figure on this run is a fabrication: the refusal renames the tools the loop
  must call, and ``get_screenshot`` of a window that does not exist refuses it
  by the name of the window -- not an image, not a guess.
- **The closure.** The three gestures that empty the bookkeeping are only
  taken when the run asks for them. Every other run that poses them is a
  named refusal, the gesture is not done, the figure, the case, the session
  are left standing -- and the answer says so, that nothing was closed.

.. _agentics_llm:

The model of the session
------------------------

The faces read the model from three lines of the preferences file of
:ref:`user_preferences`, and there is no other door:

.. code-block:: text

   AgentLLMEndpoint=http://127.0.0.1:11434/v1
   AgentLLMModel=qwen3.8:27b
   AgentLLMApiKey=

- **``AgentLLMEndpoint``** -- the endpoint of a chat that speaks the OpenAI
  shape; the last word of it is ``/v1``. The default above is the one a local
  server answers on port 11434.
- **``AgentLLMModel``** -- the name of the model, sent with every call. An
  empty name is **not** a refusal: the endpoint is asked, and the first entry
  of its ``/v1/models`` is what is sent, on the first connect. A name the
  endpoint does not hold is a named refusal that costs the call -- it is never
  silently replaced by the one the endpoint does hold.
- **``AgentLLMApiKey``** -- the token that goes with the endpoint. Sent **only
  when non-empty**, as an ``Authorization`` header; empty, the request is sent
  without a header, and a local server does not ask for one. It is not
  repeated in a log line or a transcript.

The faces that take them from a word rather than from the file
(``--llm-url``, ``--llm-model``, ``--llm-key``) are the two command lines of
the one-shot and of the service, and the word ``auto`` of the REPL's
:code:`/llm model` is the empty name above: the endpoint's first
:code:`/v1/models` entry is what is sent. The three lines are the same ones
the :guilabel:`File --> Agent` panel reads: there is no other table for them,
and no other answer to the question *which model does this run talk to*.

.. note::

   Every face needs the environment of the application -- the stack of
   :ref:`getting_started`, and the application's own variables -- and the
   faces that serve over a port each import their transport in a package of
   their own, outside the application: the SDK of the MCP for the service, and
   the proxy and the loop of the web and of the gateway for the two of them,
   so a module stack the application is loaded from never reaches them. The
   model is not a dependency of any of them: the faces read it when they talk
   to it, and a face without a model is a face that refuses by name, not a
   face that hangs.
