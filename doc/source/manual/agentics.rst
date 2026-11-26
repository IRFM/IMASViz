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
     - ``manage_case``
     - one tool for the cases the session works on, and ``action`` says
       which ask: ``open`` opens one case by URI (an HDF5 path, or an UDA
       URI), ``dd_version`` pinning the data dictionary it is read at --
       left out, the case is asked which one its own IDSs were written
       with; ``list`` answers the cases open and the occurrences each one
       holds; ``close`` takes one open case, its view, its windows and its
       bookkeeping away for good.
   * - the IDSs
     - ``manage_idss``
     - one tool for the IDSs of a case, and ``action`` says which ask:
       ``declared`` answers every IDS the data dictionary declares, with
       the occurrences each one holds, the roots that hold no data
       included; ``filled`` the short list of the IDS the case **actually**
       holds -- the one to trust; ``load`` puts one occurrence of one IDS
       into the tree, ``slices`` being "first" for the slice a plain load
       keeps and "all" for the whole dynamic array.
   * - the tree
     - ``inspect_tree``
     - one tool for what the tree says about itself, and ``action`` says
       which ask: ``search`` matches the leaves by a substring of their
       spellings (any of a match's three spellings is what the plot tools
       take, and its ``kind`` says whether a plot would make a curve, a
       picture or nothing of it); ``node`` answers what one leaf holds
       (units, size, finite minimum and maximum, the zero/nan/inf counts, a
       bounded preview); ``ids`` what the dictionary says of an IDS; and
       ``quantities`` the filled tensors of an occurrence grouped by the
       array of structures that drives them.
   * - the selection
     - ``manage_selection``
     - one tool for the case selection, and ``action`` says which ask:
       ``select`` puts the named paths in as the tree clicks would (a path
       the tree does not hold is refused by name and nothing is put in, and
       ``additive=false`` empties the selection first), ``clear`` empties
       it -- answering how many were dropped -- and ``list`` reads it back
       in the order it was put in, path, data name, IDS and occurrence of
       each; an empty selection answers ``count: 0``, which is an answer
       and not a refusal.
   * - the drawing
     - ``plot``, ``get_signal``
     - one tool, and ``mode`` says which drawing is meant: ``single`` puts one
       quantity into the figure its axes call for (a curve for one axis, a
       picture for two), ``slice`` answers a 1D-profile at a single instant,
       ``selection`` draws what the case selection holds, ``table`` one panel
       per quantity in a Table Plot View, ``stacked`` the stacked view. The
       **values** of a leaf, as JSON, are the other tool: the same read the
       plots use, so the figure a viewer sees and the numbers a read reports
       are the same element of the same array.
   * - the equilibrium
     - ``equilibrium``
     - one tool for the two readings of the *Equilibrium* plugin, and
       ``action`` says which: ``surfaces`` answers the flux surfaces of
       several named instants side by side in one window, ``at_time`` one
       instant with the radial profiles under it and the slice's global
       quantities in the answer. Each instant answers the **nearest slice the
       case holds**, and the answer keeps ``time_requested`` and
       ``time_slice_time`` apart -- see :ref:`IMASViz_plugins`.
   * - the curves already drawn
     - ``transform_curve``, ``read_figure``
     - one tool, and ``operation`` says what is done to the curve: ``scale``
       multiplies it, ``shift`` offsets it, ``normalize`` divides it by a
       reference of its own (``reference``: ``max``, ``first``, ``mean``),
       ``reset`` puts it back to the values it was drawn with, ``remove``
       takes it off. All reversible, all read back by one tool of its own --
       ``read_figure``, whose ``action`` says which read: ``stats`` answers
       the sample count, the finite min/max/mean/std, the nan/inf counts and
       the peak with its abscissa, ``export`` writes the values **as they
       stand** to :file:`~/.imasviz/exports`. The tree, the leaf and the
       case are unchanged by every one of them.
   * - the axes and the slices of a window
     - ``configure_axes``
     - one tool, and ``operation`` says which of the five moves is meant:
       ``range`` pins the span of a figure by name and number (a picture
       window takes the same span on each of its pictures),
       ``image_window`` sets the **window of pictures** -- moved with
       ``start``, resized with ``count``; ``slice_index`` poses one row of
       a slider band at a named index, in the words the band spells that
       row; ``log`` dresses an axis, refused where the values cross zero;
       ``invert`` turns one around. A table and a stacked window are
       refused by name, and so is a row a band does
       not hold -- naming the rows it does.
   * - the physics of a signal
     - ``analyze_signal``
     - one tool, and ``action`` says which of the six reads is meant:
       ``events`` finds the events of a leaf's series (``elm`` an excursion
       up, ``sawtooth`` a crash down, ``lh`` a threshold crossing),
       optionally marked on a named curve figure; ``clear_events`` takes
       those marks off; ``events_report`` is the same detection as an HTML
       report. ``spectrum`` is what the series oscillates at -- the dominant
       frequency and period, the leading peaks with their share of the
       power, the share inside a named band; ``correlate`` is how far one
       leaf **lags or leads** another and at what the two oscillate
       together; ``spectrum_report`` is the same spectral facts on a page.
       The signal is the one
       ``get_signal`` answers, so what is measured and what a figure of the same
       leaf draws are one read; see :ref:`physical_bricks`.
   * - what a case says
     - ``derived_quantity``
     - one tool for the three numbers a case is judged on, and ``quantity``
       says which one: ``greenwald`` is ``f_G = n_e / n_G`` over the three
       leaves the caller names, and ``beta_normal`` and ``total_pressure``
       are the case's own numbers **read off the leaf the case keeps them
       in** -- never computed here. The answer names the path it read, the
       points, and the mean, peak and floor. A case that does not hold the
       leaf is refused by name, never with a plausible-looking value.
   * - a campaign of shots
     - ``trend_campaign``
     - one tool for a series of shots, and ``action`` says which ask:
       ``values`` answers the trend of one leaf in the order named -- one
       value per shot (``at`` an index of its curve, or ``which`` of
       ``mean``, ``max``, ``min``), then the per-shot values, the
       least-squares slope over the shot index, the first-to-last change,
       the min and max with the shots they came from, and the direction;
       ``report`` writes that same answer as a page under
       :file:`~/.imasviz/reports`. A campaign of one shot or of all-equal
       values refuses in words.
   * - the windows
     - ``manage_window``
     - one tool, and ``action`` says which of the five is meant: ``list``
       answers the session's windows in the order the menus draw them (kind,
       label, key, on screen) and asks for no window; ``show`` puts one back
       on the screen, ``hide`` takes one off without deleting it, ``close``
       deletes one for good, and ``focus`` is the "show me this" gesture: a
       window brought forward (shown when off screen, raised when not), at
       the size it holds, and the pixels only when they are named. The window
       is one word for all four -- ``window``, the application, a figure key
       or a case URI -- although three of the gestures name it ``key`` in
       Python. Showing is the user's command, not something the loop does
       after a draw: the figure is in the *Windows*
       menu, and that is where the raise lives.
   * - the plugins
     - ``plugin``
     - one tool, and ``action`` says which of the two is meant: ``list``
       answers the entries an IDS root earns, in registration order, with the
       refusals of the plugins the case cannot offer **named alongside**;
       ``run`` runs one of those entries with the answers the entry would have
       asked the user -- the ``occurrence``, and the ``time`` of an entry that
       asks an instant. Which
       branch the line is asked on is a parameter too: left out, it is
       **resolved** by searching the case for the branches that earn that entry,
       and several branches earning it (a plugin offered on any IDS) is refused
       with them named rather than settled on the first branch of the tree. An
       entry that refuses is a refusal for the loop, not an answer saying it ran:
       the plugin's own words come back, and a window that was not drawn is not
       reported. What the entry drew comes back under its own key (``drawn``,
       and ``reused`` names the window it drew again) -- a claim about that
       window stands on the entry that drew it. An entry whose window already
       stands is drawn **into that window**: the stamp the entry left on it when
       it drew it says which one that is, so asking the same line twice -- once
       from a session put back and once from the agent, say -- leaves one window
       showing the second answer instead of two on the screen. What still makes
       two windows is asking an entry *and* the tool that entry answers with,
       since ``equilibriumsurfaces`` entry 0 *is*
       ``equilibrium(action="surfaces")`` and entry 1 *is*
       ``equilibrium(action="at_time")``.
   * - sessions and configurations
     - ``manage_session``
     - the run kept and read back, and ``action`` says which of the eight is
       meant. ``save`` writes the whole screen as the application writes it
       -- the cases, the loads, the selection, the windows and what a hand
       styled on them; ``restore`` puts one of those sessions back the way
       the gesture replays it, naming the cases that came back. ``name`` is
       a session file there, and a configuration file (``.lsp`` as
       ``.pcfg``) for the three asks that name one. ``list_sessions`` answers
       the ``.vsess`` files the folder holds and ``list_configurations`` the
       plot and selection files, ``kind`` narrowing to one of the two kinds
       -- a kind the application does not answer is refused by name,
       ``session`` among them. ``apply`` selects on a case the quantities one
       saved configuration names (the IDSs the case would need and does not
       hold are loaded first, the way the menu does it), ``save_selection``
       writes the case's selection out as a ``.lsp`` and
       ``save_plot_configuration`` one Table Plot View out as a ``.pcfg``,
       its panels and the places they held -- any other window is refused by
       name. ``new`` is the *New session* of the *File* menu asked the way
       the page asks it: every case view and every figure of the run closed
       and **nothing written** -- the sessions on disk and the reports stay
       where they are -- and it answers how many windows it closed. Like the
       *Windows* menu's close, it is a gesture the loop names out loud before
       it runs it.
   * - the reports
     - ``generate_report``
     - a self-contained HTML file on disk, and ``scope`` says which one is
       meant: ``plot`` is a window of curves (the image of the window and one
       row per curve, with its statistics), ``case_loaded`` is the loaded tree
       of a case the same way, and ``case_ids`` is the case itself: every IDS
       the case holds
       and the occurrences each holds, the ones the session loaded, the
       header of each loaded occurrence's ``ids_properties`` values, and
       the signals the tree holds for each occurrence -- the ones the
       tree carries as available (the same test its own colouring
       applies), a 0-D scalar held by the dynamic array among them
       (``global_quantities.ip`` on the reference case). A scope asked
       without the subject it needs (a ``figure_key`` for ``plot``, a
       ``uri`` for the two others) is refused by naming what the call is
       missing.
   * - the export
     - ``export_to_ids``
     - the opened IDSs of a case into the target case, under the data
       dictionary the case was read at.
   * - the screen
     - ``get_screenshot``
     - a window as it stands, in PNG -- the application, one figure, or the
       shot view of a case. The pixels are asked for, never handed out after a
       draw; the window that brings itself forward is
       ``manage_window(action="focus")``, in the group of the windows it
       moves.
   * - the log
     - ``get_logs``
     - the log panel of one case, or of every case: the last lines the gestures
       wrote there, the named refusals among them -- where a loop reads what a
       dialog would have told a hand.
   * - the journals
     - ``manage_note``
     - one tool for the notebook, and its ``action`` says which of the eight
       is meant: ``search``, ``list``, ``read``, ``add``, ``edit``,
       ``delete``, ``stats``, ``reindex``. The two journals of the run: the
       **personal** one (the author's own notes, under ``~/.imasviz/journals``)
       and the **shared** one (:ref:`agentics_journal_shared`) -- a note is one
       file with its own front matter (*machine*, *campaign*, *shot*, *date*,
       *author*, *title*) and its body, and a search narrows by any of the
       filters and ranks by meaning when the embeddings endpoint is named
       (:ref:`agentics_journal_llm`), by words while it is not. ``scope`` says
       which of the two journals an action runs on -- a word the write
       gestures already answered for themselves, which is why the group took
       ``action`` as its discriminant and not ``scope``. ``reindex`` puts a
       journal back in step with its index: an index that is empty, stale, or
       **guarded** because it was written under an embeddings endpoint this
       run is no longer under.
   * - the documents corpus
     - ``manage_documents``
     - one tool for the corpus the agent *reads*, and its ``action`` says
       which of the five is meant: ``list``, ``search``, ``read``,
       ``reindex``, ``stats``. The agent's own reading of **the user's
       writing**: the markdown, text and (when the reader is importable)
       PDF files under :code:`AgentDocsDir` in the preferences. A search
       answers ranked **chunks** -- one hit per chunk, with the document's
       ``rel``, the chunk and a snippet -- and names the method it ranked
       with; ``read`` gives the full text of one document by the ``rel`` a
       hit named; ``list`` is the corpus as named; ``stats`` is its state,
       which is where "it is not indexed yet" and "it was indexed under
       another endpoint" are answered; ``reindex`` sets the corpus and its
       index back in step. A corpus with no folder named is refused by
       name, naming the folder it would have read (:ref:`agentics_documents`).
   * - the prompts
     - ``manage_prompt``
     - one tool for the catalogue of prompts **the user wrote themselves**,
       and ``action`` says which of the six is meant: ``list`` answers the
       catalogue grouped by category, each category saying how many it
       holds, narrowed by ``category`` or a word of ``query``; ``detail``
       answers one prompt whole, with for each of its holes -- spelled with
       braces -- the value it would take today and **where that value comes
       from**; ``fill`` fills those holes from four sources in order (what
       the call names, the last value typed for **that** prompt, what this
       session knows, the default the file declares), a hole none of them
       answers being a refusal **naming the holes** rather than a prompt
       sent with ``{shot}`` still in it; ``save``, ``edit`` and ``delete``
       write the catalogue, ``scope`` saying the user's own folder or the
       shared one. Filling is not running: no face offers a ``run_prompt``
       gesture, so the text comes back and the face asks the turn with it
       (:ref:`agentics_prompts`).

.. _agentics_documents:

The documents corpus
--------------------

The journals are what the agent writes; the **documents corpus** is what it
*reads*. It is one preferences line -- :code:`AgentDocsDir`, empty by default --
naming a folder of the user's own markdown, text and PDF files. Nothing about it
is IMASViz's: the folder, its layout and its language are the user's, and the
corpus is the agent's memory of it.

The corpus is indexed, not reread on every question: each document is cut into
chunks and the chunks are stored in the same index the two journals use, so
``manage_documents(action="search")`` answers the chunks that carry the answer
rather than a file name, and ``manage_documents(action="read")`` is the one to
ask when a hit is worth reading whole.
Ranking follows the same rule as the journals (:ref:`agentics_journal_llm`): by
**embeddings** when the embeddings endpoint is named and answers, by **words**
while it is not, and the answer says which -- ``hybrid``, ``embeddings``,
``keyword`` or ``empty``.

Two states are worth reading before concluding the corpus does not work:

- **an empty index**: a document added to the folder announces itself to nobody.
  ``manage_documents(action="reindex")`` walks the folder, keeps what it has,
  embeds what moved and drops what left;
  ``manage_documents(action="stats")`` names how many documents and chunks
  stand, under which endpoint and model, and when that was built.
- **a guarded index**: an index written under one embeddings endpoint and read
  under another is kept out of the ranking -- its vectors live in a different
  space than the query does -- and the search falls back to words, naming the
  guard. A fresh ``manage_documents(action="reindex")`` under the endpoint of
  the run is what clears it.

A folder that is not named is a refusal that names the line missing; it is not a
search that quietly answers nothing, and the journals keep answering beside it.

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

The read: ``manage_note(action="search")`` (the query and the filters),
``manage_note(action="list")`` (the filters alone, in date order),
``manage_note(action="read")`` (the body by the id a search or a list names),
and ``manage_note(action="stats")`` (what the two journals hold on this node,
and whether the embeddings endpoint is named and the model it names). The
write: ``manage_note(action="add")`` (a new line in one of the two, the
fields that name it, and the body), ``manage_note(action="edit")`` (one of
the lines, changed in place — the note
keeps the id it reads under, a field the caller names takes the place of
the one it held, a field left out keeps it, and an empty one clears it,
leaving the author and the body the two a note does not go without), and
``manage_note(action="delete")`` (one of them, gone). Every refusal the read
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

The ranking: ``manage_note(action="search")`` ranks by **embeddings** when
:code:`AgentEmbedEndpoint` is named and the server answers (the
:ref:`agentics_journal_llm`), and by **words** while it is not, or while the
server does not answer -- which is what ``manage_note(action="stats")``
says, in ``method`` and, for the fallback case, in ``fallback_from`` and
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
gives them -- and :code:`plot` (its "single" and "slice" modes) and
:code:`get_signal` take that pair in exactly the same shape, so the number a
read reports and the element a figure draws are one and the same thing.

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
   :code:`plot(mode="single", uri,
   "equilibrium.time_slice[0].profiles_1d.pressure", indices={"psi": 50})` --
   the curve it answers is the 49 samples of the case's ``time_slice``, not a
   point.
2. **Along the coordinate that is not the time.** *"the pressure as a
   function of psi"* is the same call with :code:`along="psi"` -- 101 samples,
   x running over the coordinate of the leaf itself, where along the time it
   was 49 samples over about 16 seconds. :code:`get_signal` with the same
   address reports the same curve: a figure and a read that disagree about
   the abscissa have been a refusal since this release.
3. **A slice at an instant.** *"the pressure of the slice closest to 35 s"*
   is :code:`plot(mode="slice", uri, leaf, time=35)` -- the value the
   Access Layer answers at that instant (its own slice read, not a GUI-side
   interpolation), with
   ``linear`` (the default), ``closest`` or ``previous`` interpolation. A
   ``time`` outside the case's range answers the nearest slice it holds, and
   the answer names the time asked and the slice time **apart**, not a value
   that resembles one. ``time`` and the ``along``/``indices`` pair are
   refused together: they are two opposite ways of reading the array.

Two figures, two ways (and two ways only):

- **Stacking on the figure already open.** The first drawing opens the
  figure and **is** what its key is (``Plot1``); the next ones pass that key
  and are drawn on it. N indices of **the same leaf** is N curves on **one**
  figure: each curve is pinned to the index it carried, and the slider the
  figure holds is not touched when stacking -- which is what the four identical
  curves of the old bug would have been, all of them answering the last value
  the slider was set to.
- **Select first, draw after.** :code:`manage_selection` asked with
  ``action`` ``select`` and the paths, then :code:`plot(mode="selection",
  uri)`: one selection, one figure per figure kind the selection calls for.

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
a figure, the window was gone from ``manage_window(action="list")``, and the
loop noticed it itself, without having asked for it.

A dictionary of ready phrases, with what they answer on the reference case:

.. list-table::
   :header-rows: 1
   :widths: auto

   * - the ask
     - say to the agent
     - what answers
   * - the pressure along the time, at one psi
     - "trace the pressure at psi = 50"
     - :code:`plot(mode="single", ..., indices={"psi": 50})` -- "along" left
       out
   * - the pressure as a function of psi
     - "draw the pressure as a function of psi"
     - :code:`plot(mode="single", ..., along="psi")`
   * - three psi's on **one** figure
     - "draw psi = 0, 10 and 50 on **one** figure"
     - three :code:`plot(mode="single")`, the two last with the first's key
   * - two probes, then two loops
     - "draw probe 2 and probe 10, then loop 2 and loop 10"
     - **two** figures
   * - a slice at an instant
     - "the pressure of the slice at 35 s"
     - :code:`plot(mode="slice", ..., time=35)`
   * - the value at one psi
     - "read the pressure at psi = 50"
     - :code:`get_signal(..., indices={"psi": 50})`
   * - to see the figure
     - "show me Plot1" / "bring Plot1 forward"
     - :code:`manage_window(action="focus", window="Plot1")` -- the window
       comes forward, at the size it holds; *"en grand"* adds the pixels to
       put it at
   * - a capture of the figure
     - "a capture of Plot1"
     - :code:`get_screenshot(window="Plot1")`

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
- **A re-capture is asked, by the name of the figure.** *"show me Plot1"*
  brings that figure forward (``manage_window(action="focus")``, at the
  size it holds); *"a capture of Plot1"* saves it (``get_screenshot``). The
  page's own
  button on a capture card does the second one. A figure the answer only
  *names* is not among these: a show is the user's command, and the
  mention stays in the transcript, beside the PNG the turn that drew it
  already left.

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
  called (``get_signal`` / ``plot``), and refused again when they repeat
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

.. _agentics_prompts:

The prompt catalogue
--------------------

A prompt the user wrote once is worth filing: the wording works, the turn it
starts is the one they ask again next week, and typing it a second time is
the cost the catalogue takes away. A prompt is a file of a front matter the
reader chooses on -- a *name*, a *category*, a one-line *description*, the
*variables* it asks for and their defaults, an *author* -- and the text
itself, with its holes spelled with braces:

.. code-block:: text

   name: Profils des trois occurrences
   category: équilibre
   description: trace les profils des occurrences 0 à 2 d'equilibrium
   variables: shot=; rho=0.85
   author: g2lfleur

   Ouvre le cas de la décharge {shot} et trace les profils de equilibrium
   aux occurrences 0, 1 et 2, en marquant le rayon normalisé {rho}.

The two catalogues are the two the journals answer by:

- the **personal** one, under ``~/.imasviz/prompts/``, one for each user of
  the node; and
- the **shared** one, under :code:`SharedPromptsDir` in the preferences
  (:ref:`agentics_prompts_shared`) -- an AFS directory the writers of the
  node reach, so a prompt one writer filed is on the menu of the others.

The catalogue answers one tool, ``manage_prompt``, whose ``action`` says
which ask is meant. The read: ``action="list"`` (the catalogue, by category
and by name, narrowed by ``category`` or a word of ``query``, and answering
how many prompts each category holds) and ``action="detail"`` (one prompt
whole: its text and, for each of its holes, the value it would take today
and **where that value comes from**). The write: ``action="save"`` (a new
file, the id being the slug of its name), ``action="edit"`` (one of the
prompts, changed in place -- it keeps the id its values were remembered
under) and ``action="delete"`` (one of them, and the values remembered for
it, gone).

The holes are filled by four sources, in that order, and the answer names
which one answered each:

1. the value the caller names for this run;
2. the last value typed for **that** prompt, kept in the user's own folder
   (a shared prompt keeps its last values locally: a rerun costs the same
   typing for the one who typed them and nothing for anybody else);
3. what **this session** knows -- ``case``, ``uri``, ``shot``, ``run``,
   ``database`` when the session holds exactly one open case, and
   ``figure`` when it holds exactly one window; two cases open is not a
   guess, it is a question, and the reason is named;
4. the default the file declares.

A hole none of the four answers is a **refusal naming the holes**. A prompt
is never sent with ``{shot}`` still in it, and never sent with a value the
application made up for it -- which is the whole reason filling is a separate
ask from running.

Filling is not running. There is no ``run_prompt`` gesture, and no face
pretends there is one: ``manage_prompt(action="fill")`` answers the text,
and the face asks it as its own turn -- the panel puts it in its box and
*Tourner* runs it, the page puts it in its box or sends it through its
*Run*, the client runs it on the line. A prompt of the catalogue is the
user's own ask, and the turn it
starts is the turn the transcript shows.

The four faces, and the catalogue each asks of the same two folders:

- the **panel** (*Windows → Agent*): a box of the catalogue beside the box of
  the history -- the categories grouped, each line saying its name and its
  description -- which fills the prompt box, and a *Prompts…* window for the
  holes nothing answered, the write of a new prompt, and the delete;
- the **page** (*viz_web*): a *Prompts* section under the notes, with its
  category chips, a values form naming the source of every value, and
  *Put in the box* / *Run*; every request of the list carries a *Save as
  prompt* button, so filing the wording of a turn that worked is one name and
  one line of description;
- the **client** (*viz_cli*): ``/prompt`` (the catalogue), ``/prompt list``,
  ``/prompt show``, ``/prompt run`` -- which asks the holes it cannot answer
  on the line, never in a dialog -- and ``/prompt save``;
- the **loop** itself: the one tool above with its six actions, so that
  *relance le prompt sur les instabilités* is a question asked of what the
  user filed, not a sentence the model invents for it.

The refusals, all named: a hole none of the four sources answers names the
holes; a second prompt filed under an id the catalogue holds is refused, and
the refusal names ``manage_prompt(action="edit")`` as the way to change the
one it is; a hole declared and never opened by the text is refused by name,
because a hole nobody is ever asked for is a declaration of nothing; an id
two prompts carry as their display name names both ids and asks which one;
and a shared
catalogue with no folder named costs **its own half** of a listing -- the
personal prompts still answer, with the reason in ``catalogues_unavailable``
-- while one write that names ``shared`` and gets no folder is refused,
because a write silently filed in the personal folder is a prompt its author
believes shared.

``manage_prompt(action="save", scope="shared")``, like a note written to the
shared journal, is a line other people read: the loop runs it when the request
asks for it in the user's own words, not because a turn drew a figure worth
keeping. The same goes for ``manage_prompt(action="delete")``, which takes
away a file the user wrote.

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
