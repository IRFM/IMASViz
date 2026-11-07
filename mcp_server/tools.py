# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The tool declarations of one IMASViz session, on the official MCP SDK.

Each tool is a thin name over the core: the agent's words map one-to-one
onto a method of `McpGuiCore`, and the value that comes back is the value
the core answered -- a named `ValueError` included, which FastMCP hands
back as the error content of the call, so the refusal reads the same in
the transcript as it does in the log panel.

`dispatcher` is what runs the method on the GUI thread: the SDK answers
tool calls on its worker threads, and those may compute but must not
touch the widgets -- the rule the dispatcher exists for.
"""

import base64
from functools import partial
from typing import Optional

from mcp.server.fastmcp import FastMCP
from mcp import types as mcp_types

INSTRUCTIONS = """IMASViz, the ITER/CEA visualization front-end for IMAS plasma-fusion
cases, driven by name and answered by name.

How to work with it:
1. open_case(uri) -- the data dictionary is asked of the case when you do
   not name one;
2. list_idss(uri) tells which IDSs the case holds and which occurrences;
3. load_ids(uri, ids_name, occurrence) builds the tree branch;
4. search_nodes(uri, query) names the leaves in every spelling the tree
   holds -- the paths select_signals, plot_one and get_signal take are
   any of those spellings;
5. plot_one / plot_selection / plot_table / plot_stacked draw, and
   get_screenshot answers a PNG of the window;
6. state is read with list_selection (what the case holds selected) and
   describe_node (what one node holds: documentation, units, size, the
   finite minimum and maximum, the nan and inf counts, a bounded
   preview) -- answers, not guesses, and empty is an answer too;
7. a report is self-contained HTML on disk, with the statistics of each
   curve: plot_report names one window of curves (its image, one row per
   trace it drew), and case_report names the whole loaded tree of a case
   (one row per curve, in tree order).

A refused gesture is not a failure of the server: it is an answer, with
the reason the application names it. get_logs(uri) holds those reasons
as the user reads them in the log panel."""


def buildServer(core, dispatcher, name='imasviz'):
    """The FastMCP server of one session: the tools, their names, their words.

    FastMCP reads each tool's description off its docstring, so the
    docstrings say what the agent needs to know, in the order the words
    are asked.
    """
    server = FastMCP(name, instructions=INSTRUCTIONS)

    def _run(function):
        """Ask the GUI thread, and hand back what it answers -- value or
        named exception alike."""
        return dispatcher.call(function)

    # ------------------------------------------------------------------ cases

    @server.tool(name='open_case')
    def open_case(uri: str, dd_version: Optional[str] = None):
        """Open one IMAS case by URI (imas:hdf5?path=..., or an UDA URI).

        `dd_version` pins the data dictionary the case is read at; left
        out, the case is asked which one its own IDSs were written with,
        because a case stored under another major version is refused at
        every read otherwise.
        """
        return _run(partial(core.open_case, uri, dd_version=dd_version))

    @server.tool(name='list_cases')
    def list_cases():
        """The cases open in this session, with their loaded occurrences."""
        # The SDK answers a top-level list as one content block per
        # element; the list is a value under a name, not the answer.
        return {'cases': _run(core.list_cases)}

    @server.tool(name='close_case')
    def close_case(uri: str):
        """Close one open case: its view, its windows, its bookkeeping."""
        return _run(partial(core.close_case, uri))

    # -------------------------------------------------------------------- ids

    @server.tool(name='list_idss')
    def list_idss(uri: str):
        """Every IDS the case's data dictionary declares, and the occurrences
        each one holds -- including the roots that hold no data (an empty
        occurrence list). Asked of the case itself, never listed from a file.

        For the short list of the IDS the case actually holds, use
        list_case_idss instead: its names can be trusted as the case's own,
        because they are read from the case through
        DBEntry.list_all_occurrences, not recalled.
        """
        return {'idss': _run(partial(core.list_idss, uri))}

    @server.tool(name='list_case_idss')
    def list_case_idss(uri: str):
        """Only the IDS the case actually holds, and the occurrences each one
        names -- the roots the dictionary declares but the case does not fill
        are left out.

        The source of truth for "what is in this case". Do not present an IDS
        list you did not read from this call.
        """
        return {'idss': _run(partial(core.list_case_idss, uri))}

    @server.tool(name='load_ids')
    def load_ids(uri: str, ids_name: str, occurrence: int = 0,
                 slices: str = 'first'):
        """Load one occurrence of one IDS into the tree, synchronously.

        `slices` is "first" for the slice a plain load keeps, "all" for
        the whole dynamic array -- and an occurrence the case does not
        hold is refused by the load with its reason.
        """
        return _run(partial(core.load_ids, uri, ids_name, occurrence,
                            slices=slices))

    @server.tool(name='search_nodes')
    def search_nodes(uri: str, query: str = '',
                     ids_name: Optional[str] = None, limit: int = 200):
        """The leaves of the case, matched by a substring of their spellings.

        `query` is a case-insensitive substring matched against the
        display path, the data name and the parametrized path of every
        leaf; `ids_name` narrows to one IDS. The answer holds the three
        spellings of every match, and any of them is what
        `select_signals`, `plot_one` and `get_signal` take.
        """
        return {'matches': _run(partial(core.search_nodes, uri, query,
                                        ids_name=ids_name, limit=limit))}

    @server.tool(name='select_signals')
    def select_signals(uri: str, paths: list, additive: bool = True):
        """Put the named paths into the case selection, as clicks would.

        A path the tree does not hold is refused by name, and the
        selection is left as it was; `additive=False` clears it first.
        """
        return _run(partial(core.select_signals, uri, paths,
                            additive=additive))

    @server.tool(name='unselect_all')
    def unselect_all(uri: str):
        """Empty the case selection; the answer says how many were dropped."""
        return _run(partial(core.unselect_all, uri))

    @server.tool(name='list_selection')
    def list_selection(uri: str):
        """The case's current selection, in the order it was put in.

        The path, the data name, the IDS and the occurrence of each;
        empty is an answer, count 0 -- not a refusal.
        """
        return _run(partial(core.list_selection, uri))

    @server.tool(name='describe_node')
    def describe_node(uri: str, path: str):
        """What this node holds, as the application's documentation says it.

        Dictionary documentation and units, and for an array the size,
        shape, the finite minimum and maximum, the counts of zeros, nan
        and inf entries, and a bounded preview of the values. A leaf the
        tree does not hold is refused by name.
        """
        return _run(partial(core.describe_node, uri, path))

    # -------------------------------------------------------------- plotting

    @server.tool(name='plot_one')
    def plot_one(uri: str, path: str, along_time: Optional[bool] = None,
                 into_figure_key: Optional[str] = None):
        """Draw one quantity, into the figure its axes call for.

        A curve figure for one axis to draw, a picture window for two.
        `along_time`: true reads the quantity as a history, false along
        its own coordinate; `into_figure_key` adds it to an open curve
        figure instead of opening one. A quantity the read cannot answer
        is refused with the reason the application names in its log.
        """
        return _run(partial(core.plot_one, uri, path,
                            along_time=along_time,
                            into_figure_key=into_figure_key))

    @server.tool(name='plot_selection')
    def plot_selection(uri: str):
        """Draw the case selection: one curve figure, one window per picture.

        `select_signals` first. The selection of this case alone, not the
        other open cases -- the figure keys the windows carry come back.
        """
        return _run(partial(core.plot_selection, uri))

    @server.tool(name='plot_table')
    def plot_table(uri: str, paths: list, columns: Optional[int] = None,
                   plot_axis: Optional[str] = None):
        """One panel per named path, in a Table Plot View.

        `columns` sets the width of the row, `plot_axis` "TIME" reads
        every quantity along time; a quantity that reads nothing is
        refused with the reason it gave.
        """
        return _run(partial(core.plot_table, uri, paths, columns=columns,
                            plot_axis=plot_axis))

    @server.tool(name='plot_stacked')
    def plot_stacked(uri: str, paths: list, plot_axis: str = 'TIME'):
        """The named paths stacked one panel per quantity.

        Against the abscissa `plot_axis` names, the default being the
        clock.
        """
        return _run(partial(core.plot_stacked, uri, paths,
                            plot_axis=plot_axis))

    @server.tool(name='get_signal')
    def get_signal(uri: str, path: str,
                   as_function_of_time: Optional[bool] = None,
                   coordinate_index: int = 0,
                   time_index: Optional[int] = None):
        """The values the tree read gives for one leaf, as JSON.

        The same read the plots use: the coordinate and value arrays of
        a slice, or the named coordinates and values of a taller
        quantity. `as_function_of_time` true reads it along the clock,
        false along its own axis.
        """
        return _run(partial(core.get_signal, uri, path,
                            as_function_of_time=as_function_of_time,
                            coordinate_index=coordinate_index,
                            time_index=time_index))

    # -------------------------------------------------------------- windows

    @server.tool(name='list_windows')
    def list_windows():
        """Every window of the session, in the order the menus draw them.

        The case views, the figures, the plugin windows: each with its
        kind, its label, its key and whether it is on screen.
        """
        return {'windows': _run(core.list_windows)}

    @server.tool(name='show_window')
    def show_window(key: str):
        """Put a window back on the screen; it keeps its key either way."""
        return _run(partial(core.show_window, key))

    @server.tool(name='hide_window')
    def hide_window(key: str):
        """Take a window off the screen without deleting it: it keeps its
        key and `show_window` brings it back."""
        return _run(partial(core.hide_window, key))

    @server.tool(name='close_window')
    def close_window(key: str):
        """Close a window for good: it is deleted and forgets its key."""
        return _run(partial(core.close_window, key))

    # -------------------------------------------------------------- plugins

    @server.tool(name='list_plugins')
    def list_plugins(uri: str, ids_name: str):
        """The entries an IDS root earns, in registration order.

        The feature number, its label, its description for each -- and
        with the answer, the refusals of the plugins the case cannot
        offer, named.
        """
        return _run(partial(core.list_plugins, uri, ids_name))

    @server.tool(name='run_plugin')
    def run_plugin(uri: str, plugin: str, entry: int, occurrence: int = 0,
                   ids_name: Optional[str] = None):
        """Run one entry of a plugin, with the answers the entry would
        have asked the user.

        `occurrence` is the one the entry plots, handed instead of being
        asked -- which is what keeps a modal question off the path of an
        agent. Refused by name when the case does not offer that entry.
        """
        return _run(partial(core.run_plugin, uri, plugin, entry,
                            occurrence=occurrence, ids_name=ids_name))

    # --------------------------------------------------------------- session

    @server.tool(name='save_session')
    def save_session(name: Optional[str] = None,
                     path: Optional[str] = None):
        """Write the session as the application writes it.

        The cases, the loads, the selection, the windows and their
        styling. `name` is a file under the configuration folder, `path`
        a full file name; the answer is the file that holds it.
        """
        return _run(partial(core.save_session, name=name, path=path))

    @server.tool(name='restore_session')
    def restore_session(name: Optional[str] = None,
                        path: Optional[str] = None):
        """Put a session back: the cases open, the loads replayed, the
        figures and plugin windows drawn the way the file named them."""
        return _run(partial(core.restore_session, name=name, path=path))

    @server.tool(name='list_sessions')
    def list_sessions():
        """The sessions the configuration folder holds, as the dialog lists them."""
        return {'sessions': _run(core.list_sessions)}

    @server.tool(name='list_configurations')
    def list_configurations(kind: Optional[str] = None):
        """The plot (.pcfg) and selection (.lsp) configurations the folder holds.

        `kind` narrows to one of the two kinds; a kind the application
        does not answer is refused by name, 'session' among them.
        """
        return _run(partial(core.list_configurations, kind))

    @server.tool(name='select_from_configuration')
    def select_from_configuration(uri: str, name: str):
        """Apply one saved configuration: select the quantities it names.

        A .lsp as a .pcfg; the IDSs the case would need and does not
        hold are loaded first, the way the menu does it. A name the
        folder does not hold is refused by name, naming the ones it does.
        """
        return _run(partial(core.select_from_configuration, uri, name))

    @server.tool(name='save_selection')
    def save_selection(uri: str, name: str):
        """Write the current selection of the case out as a .lsp.

        Nothing selected is refused by name; the name goes through the
        guard the application applies in its own dialog.
        """
        return _run(partial(core.save_selection, uri, name))

    @server.tool(name='save_plot_configuration')
    def save_plot_configuration(uri: str, figure_key: str, name: str):
        """Write one Table Plot View out as a .pcfg, the panels and their places.

        A window that is not a Table Plot View is refused by name.
        """
        return _run(partial(core.save_plot_configuration, uri,
                            figure_key, name))

    # --------------------------------------------------------------- reports

    @server.tool(name='plot_report')
    def plot_report(figure_key: str, name: Optional[str] = None):
        """A window of curves as a self-contained HTML report on disk.

        The image of the window, and one row per trace it drew -- the
        quantity, the number of samples, the finite minimum and maximum,
        and the nan/inf counts. The file lands in `~/.imasviz/reports`;
        `name` is the report name (a place, not a report, is refused).
        A window that draws no curve it could stat is refused by name.
        """
        return _run(partial(core.plot_report, figure_key, name=name))

    @server.tool(name='case_report')
    def case_report(uri: str, name: Optional[str] = None):
        """The loaded tree of a case as a self-contained HTML report on disk.

        One row per curve the tree holds -- the numeric arrays its leaves
        read, in tree order -- with the statistics of each. `name` is the
        report name (a place, not a report, is refused). A case whose
        loaded tree has no curve is refused by name.
        """
        return _run(partial(core.case_report, uri, name=name))

    # ---------------------------------------------------------------- export

    @server.tool(name='export_to_ids')
    def export_to_ids(uri: str, target_uri: str,
                      dd_version: Optional[str] = None):
        """Copy the opened IDSs of one case into the target case.

        `target_uri` is the case the Access Layer writes to
        (imas:hdf5?path=...); the write goes under the data dictionary
        the case was read at unless `dd_version` says otherwise.
        """
        return _run(partial(core.export_to_ids, uri, target_uri,
                            dd_version=dd_version))

    # ------------------------------------------------------------ screenshot

    @server.tool(name='get_screenshot')
    def get_screenshot(window: str = 'app'):
        """A window as it stands, in PNG.

        "app" for the application, a figure key for one figure, a case
        URI for its shot view -- the image content of the answer is the
        picture itself.
        """
        png = _run(partial(core.screenshot, window))
        return [
            mcp_types.TextContent(
                type='text',
                text='PNG of %s, %d bytes.' % (window, len(png))),
            mcp_types.ImageContent(
                type='image',
                data=base64.b64encode(png).decode('ascii'),
                mimeType='image/png'),
        ]

    # ------------------------------------------------------------------- log

    @server.tool(name='get_logs')
    def get_logs(uri: Optional[str] = None, tail: int = 200):
        """The log panel of one case, or of every case when `uri` is left
        out: the last `tail` lines the gestures wrote there, the named
        refusals among them -- where an agent reads what a dialog would
        have told it."""
        return _run(partial(core.get_logs, uri, tail=tail))

    return server
