# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The guards the agent loop applies to the model's own answers.

A final answer that claims work no tool did, a figure key that was never
handed to the user, or a sentence of certainty about the case the case
does not support is refused by name -- the same named-refusal style as
every other refusal in this repository. The loop itself lives in
``agent.py`` and imports the one spelling it reaches here; the regexes
and the sets behind them stay private to this module.
"""

import re

from imasviz.VizAgent.tools import TOOLS, memberNames, offeredNames


# The loop's own surface: the tool names the model quotes to point the user
# at a gesture (restore_session in `restore_session(name="from_web")`)
# are the agent's own vocabulary, not names it recites from the case.
# `_unfoundedIdsRefusal` keeps them out of its count for exactly that
# reason: a "how do I do it later" answer is not a list.
#
# Three spellings belong in that stop-list, and the seam is why. The names
# on offer, the names the groups answer, and every gesture name the table
# holds -- a gesture whose group is merged away is no longer something the
# model may CALL, but a saved prompt (`~/.imasviz/agent_prompts`), a journal
# line from before the merge, or a "how did I do it last time" answer may
# still name it in words. Counting such a name as one the model invented
# would refuse an honest answer for a spelling this application wrote itself.
_TOOL_NAMES = frozenset(
    [tool['function']['name'] for tool in TOOLS]
    + list(offeredNames())
    + list(memberNames())
)


def _bareNames(text):
    """The snake_case names that stand on their own in that text.

    A name that is a segment of a longer spelling is not one of them --
    ``magnetics.flux_loop[0].flux.data`` is a path, ``west/3/54924`` a
    branch of one, ``rapport_flux_loop_10.html`` a file (a dot followed
    by two or more letters: an extension, not the period of the
    sentence, which is why ``equilibrium_time`` at the end of one still
    counts). Nor is the loop's own tool vocabulary: the names in
    ``TOOLS`` are quoted to point the user at a gesture, not recited
    from the case. What is left is the set of names the text is
    presenting, if it is presenting any.
    """
    names = set()
    for m in re.finditer(r'\b[a-z][0-9a-z]*(?:_[0-9a-z]+)+\b',
                         text.lower()):
        name = m.group(0)
        if name in _TOOL_NAMES:
            continue
        before = text[m.start() - 1] if m.start() else ''
        after = text[m.end()] if m.end() < len(text) else ''
        if before in './':
            continue
        if after == '/':
            continue
        if after == '.' and re.match(r'[A-Za-z]{2,}', text[m.end() + 1:]):
            continue
        names.add(name)
    return names


# The word families the fabricated-artifact guard uses to tell the
# *claim* (the fabrication it refuses) from the *honest mention* (the
# self-correction it must allow). A content word says the answer
# presents the figure with data ("Plot3 shows a curve"), not just names
# it ("Plot3 was closed" is in the ground set, "Plot3 does not exist"
# is negated, "compare Plot1 and Plot5" names Plot5 with no content,
# so none of those stand as a fabrication). A negation within the same
# clause is the honest shape ("the report was never written").
# The figure-key spellings a session can produce (the ``FigureTypes``
# kinds without their trailing number): the guard scans these even while
# no figure is open, so a fabrication on a fresh session is caught. They
# mirror ``FigureTypes`` in ``imasviz/VizUtils/QVizGlobalValues.py``; the
# agent panel prefix is not a data figure and is not listed here.
_FIGURE_KEY_PREFIXES = (
    'StackedPlotView:', 'TablePlotView:', 'EquiPlotView:', 'PlotView:',
    'EquiSurfaces:', 'Image', 'Plot',
)
_FIGURE_CONTENT_WORDS = (
    'shows', 'holds', 'contains', 'displays', 'value', 'values',
    'sample', 'samples', 'curve', 'curves', 'points', 'point',
    'data', 'tracé', 'trace', 'montre', 'contient', 'valeur',
    'valeurs', 'échantillon', 'échantillons', 'courbe', 'courbes',
    'donnée', 'données', 'figure', 'graphe',
)
# A *claim* is a first-person or present-assertion voice near the report
# reference: "j'ai généré", "le rapport est prêt", "I generated the
# report". A past participle alone -- "``rapport_flux.html`` généré" in a
# quoted log, "``[INFO]`` Rapport HTML généré:" as a log line label -- is
# a description or a quotation, not a claim, and stays allowed (the
# honest "le rapport n'a jamais été écrit" is negated into the refusal
# below, the quoted log simply has no agent voice to key on).
_AGENT_VOICE = (
    "j'ai", "j' ai", "est prêt", "est généré", "est écrit",
    "est produit", "est ready", "i generated", "i wrote", "i saved",
    "i created", "i have", "the report is", "we generated", "we saved",
    "we wrote", "generated the report", "wrote the report",
    "saved the report",
)
_NEGATIONS = (
    'not', "n't", 'never', 'no report', 'no html',
    'n\'ai pas', "n'a pas", "n'a jamais", 'jamais',
    'n\'existe', "n'existe", 'n\'existent', "n'existent",
    'inexistant', 'impossible', 'sans rapport', 'sans html',
    'invented', 'inventée', 'inventées', 'inventé', 'inventés',
)


def reportClaimed(text):
    """Whether the text asserts -- in the agent's own voice -- that a
    report was written.

    A ``.html`` path or the report noun is only a *reference*; it becomes
    a *claim* when a first-person or present-assertion voice sits near it
    ("j'ai généré", "le rapport est prêt", "I generated the report"). A
    quoted log ("``Rapport`` : rapport_…html généré"), a past participle
    with no agent subject, and a negation ("le rapport n'a jamais été
    écrit") are descriptions or self-corrections, not claims -- this
    answers False for each, and the guard lets them stand.
    """
    text = (text or '').lower()
    # The one reference the guard can key on: a ``.html`` file on disk, or
    # the report noun. Without either there is no report to claim.
    if not (re.search(r'report|rapport|\.html', text)):
        return False
    # A claim is a reference with an agent voice near it and no negation.
    for m in re.finditer(r'rapport|report|\.html', text):
        window = text[max(0, m.start() - 70):m.end() + 40]
        if not any(voice in window for voice in _AGENT_VOICE):
            continue
        if any(neg in window for neg in _NEGATIONS):
            continue
        return True
    return False


# A note is a *line in a journal*, and the one reference the guard
# keys on is that noun: "note", "cahier", "journal", "mémo". A claim is
# a noun with a *write verb* near it and no negation -- the same
# apartness the fabricated-artifact guard keeps between a report
# claimed and one that was refused. The voice is a verb at a word
# boundary (not a bare substring): "node"/"nodes" (tree paths) and
# "address" do not read as "note" or "add", and "j'ai lu tes notes" is a
# read with no write verb near the noun, so both stand out of the guard.
# A negation near the noun -- "n'ai pas", "n'avais pas", "refusée",
# and in English "not"/"never" -- is the honest refusal or
# self-correction the guard lets stand.
_NOTE_NOUN_RE = re.compile(
    r'\bnotes?\b|\bcahier\b|\bjournal\b|\bmémo\b|\bmemo\b')
_NOTE_VOICE_RE = re.compile(r'''
    # French write verbs, as stems so the -ée / -és forms land
    \bajout\w*
  | \bnot(?:é|ée|er)\w*
  | \binscrit\w*
  | \benregistr\w*
  | \bconsign\w*
  | \brang(?:é|ée)s?
  # English write verbs, at a word boundary so "add" is not "address"
  | \badd(?:ed|ing)?\b
  | \blogged\b
  | \brecord(?:ed|ing)?\b
  | \bnoted\b
  | \b(?:kept|keep)s?\s+a\s+note\b
  | \bsaved?\s+the\s+note\b
  | \bwrote\b
''', re.VERBOSE)
_NOTE_NEGATION_RE = re.compile(
    r'\bpas\b|\bnot\b|\bnever\b|\brefus\w*|\bimpossible\b')


def noteClaimed(text):
    """Whether the text asserts -- in the agent's own voice -- that a
    note / a journal line was written, edited, or deleted.

    A ``note`` / ``cahier`` / ``journal`` noun near a write verb and no
    negation is the claim the guard refuses; a read ("j'ai lu tes
    notes", "ton cahier contient déjà une note sur le flux"), a refusal
    ("je n'ai pas pu la noter", "la note n'a pas été ajoutée", "la
    publication au journal partagé a été refusée"), and a
    self-correction ("je n'avais pas ajouté") are honest shapes and
    stand out of the guard the way a report that was never written does.
    """
    text = (text or '').lower()
    for m in _NOTE_NOUN_RE.finditer(text):
        window = text[max(0, m.start() - 70):m.end() + 40]
        if not _NOTE_VOICE_RE.search(window):
            continue
        if _NOTE_NEGATION_RE.search(window):
            continue
        return True
    return False


def _figureKeyMentions(text, known):
    """[(spelling, start, end)] of each figure key the text spells.

    The kinds the session can produce are scanned (so a key on a fresh
    session is read), then the keys the session names in ``known`` in
    their own spelling. Longest kind first, and a boundary before the
    stem and a digit after it, so a short stem ("plot") does not match
    inside a longer key ("tableplotview:1") and "plot-view" is not a
    key. The text is read lowercased, and the spellings are the ones
    the session uses. Shared by the two claim guards, so the two read
    the same key out of the same sentence.
    """
    text = (text or '').lower()
    canonical = {}
    for prefix in _FIGURE_KEY_PREFIXES:
        canonical.setdefault(prefix.lower(), prefix)
    for key in set(known or set()):
        if key:
            stem = re.sub(r'[0-9]+$', '', key)
            if stem:
                canonical.setdefault(stem.lower(), stem)
    if not canonical:
        return []
    mentions = []
    for stem, spelling in sorted(canonical.items(),
                                 key=lambda pair: len(pair[1]),
                                 reverse=True):
        pat = r'(?<![0-9A-Za-z_])' + re.escape(stem) + \
            r'\d+(?![0-9A-Za-z_])'
        for m in re.finditer(pat, text):
            mentions.append((spelling + m.group(0)[len(stem):],
                             m.start(), m.end()))
    return mentions


def fabricatedFigureKeys(text, held, closed):
    """The figure keys the session does not hold and the answer presents
    with a content word, un-negated.

    The keys the session actually holds now (``held``) and the ones a
    close this request ran (``closed``) form the ground set: a figure
    the loop never drew and never closed is not grounded. The kinds the
    session can produce are scanned (so a fabrication on a fresh session
    is caught, not just the invented keys beside real ones), matched
    case-insensitively against the answer and reported back in the
    canonical spelling the session uses. A content word, no negation
    nearby, and a key outside the ground set is what the guard refuses.
    """
    text = (text or '').lower()
    ground = {k.lower() for k in (set(held or set()) | set(closed or set()))
              if k}
    if not any(word in text for word in _FIGURE_CONTENT_WORDS):
        return set()
    found = set()
    for spelling, start, end in _figureKeyMentions(
            text, set(held or set()) | set(closed or set())):
        if spelling.lower() in ground:
            continue
        window = text[max(0, start - 40):end + 40]
        if any(neg in window for neg in _NEGATIONS):
            continue
        found.add(spelling)
    return found


# The change-claim words the work guard cross-checks against the calls
# of the request: a verb the answer uses to say a draw, a curve
# transform or an axis state LANDED on a figure -- "j'ai ajouté",
# "tracée", "multipliée par 3", "en log", "pinned", "reset". These say
# work is done, and the guard asks of the loop what call of this
# request did the work on that figure, or read it back. A *description*
# word ("montre", "contient") is not in this family on purpose:
# describing a standing figure is what a read answers for, and the
# ground it applies to is the read, not the write -- the same apartness
# the content word and the assertion keep in the fabricated-artifact
# guard. The French forms are matched as the accented stem they all
# carry ("ajouté" is in "ajoutée"/"ajoutés"/"ajoutées" and not in
# "ajouter"; "tracé" is not in "trace"), the English as word forms, so
# "trace" (the noun) is not "traced" (the voice).
_CHANGE_CLAIM_SUBSTRINGS = (
    'ajout', 'tracé', 'multiplié', 'décalé', 'normalisé',
    'réinitialisé', 'retiré', 'supprimé', 'inversé', 'restauré',
    'échelle log', 'en log', 'logarithmique', 'borné',
)
_CHANGE_CLAIM_RE = re.compile(
    r'\badded?\b|\btraced?\b|\bmultiplied\b|\bshifted?\b|'
    r'\bnormalized?\b|\breset\b|\brestored?\b|\bremoved?\b|'
    r'\binverted?\b|\bscaled?\b|\bpinned?\b|\blog\s?axis\b|\blog\s?scale\b')
# A refusal or a failure word near the claim is the report of the loop
# itself ("a été refusée", "n'a pas pu", "not able to") and stands on
# whatever the figure is: the guard refuses the work *done*, not the
# reason it was not. "n't" keeps its accent-free shape; "not" and
# "pas" are worded, because "note" and "passer" carry them unaided.
_CLAIM_NEGATIONS = tuple(neg for neg in _NEGATIONS if neg != 'not') + (
    'refusé', 'échou', 'failed', 'could not', 'not able')
_CLAIM_NEGATION_RE = re.compile(r'\bnot\b|\bpas\b|\bnever\b')
# The gestures whose success grounds a claim of work on, or a read
# back of, the figure they name: the draws (a curve into the figure, a
# window of its own) and the curve transforms and the axis moves on
# one side, the reads that answer for what a figure holds on the
# other. A success is one that found its figure (`_windowForKey` is
# what refuses a key it does not hold), so the ask of such a call is as
# grounded as its answer.
# `run_plugin` belongs here with the draws, not beside them: an entry
# draws a window of its own, and it did. Left out, the turn that ran
# `run_plugin` on `equilibriumsurfaces` and answered « j'ai tracé les
# surfaces sur EquiSurfaces:1 » met a guard that had seen no work on
# that key, and its re-anchor ("do the work: draw it") sent the model
# to the drawing tool -- a second, identical window. `run_plugin`
# answers the keys it drew as `drawn` for exactly that reading.
_WORK_GESTURES = frozenset((
    'plot_one', 'plot_slice', 'plot_selection',
    'plot_table', 'plot_stacked', 'equilibrium_surfaces',
    'equilibrium_at_time', 'run_plugin', 'scale_curve', 'shift_curve',
    'normalize_curve', 'reset_curve', 'remove_curve', 'set_axis_range',
    'set_log_scale', 'invert_axis'))
# `list_windows` is a read of the session's own figures: the answer is
# the standing windows, and a claim of a state on one of them that the
# read answered for stands the way a `curve_stats` read does.
_READ_GESTURES = frozenset(('curve_stats', 'export_curve', 'list_windows'))


def _groundedFigureKeys(args, result):
    """The figure keys a successful call stands behind.

    The key the answer spells (``figure`` / ``window`` / ``figures``)
    and the key the call asked of (``figure_key``, ``into_figure_key``):
    a gesture that answered is one that found its figure, and a read
    whose answer does not spell it (``export_curve`` names its file) is
    grounded on the ask alone.
    """
    keys = []
    for ask in ('figure_key', 'into_figure_key'):
        value = (args or {}).get(ask)
        if isinstance(value, str) and value:
            keys.append(value)
    if isinstance(result, dict):
        for field in ('figure', 'window'):
            value = result.get(field)
            if isinstance(value, str) and value:
                keys.append(value)
        # `figures` is what the multi-window draws answer; `drawn` is what
        # `run_plugin` answers for the windows its entry registered. Neither
        # is the whole screen: a plugin entry answers `windows` too, and that
        # list is every window of the session, so reading it would ground a
        # claim of work on a figure this request never touched.
        for field in ('figures', 'drawn'):
            for value in result.get(field) or ():
                if isinstance(value, str):
                    keys.append(value)
    # A list result is the window list `list_windows` answers -- a call whose
    # whole answer is that read, which is another thing from the `windows`
    # field above: each entry carries the key of the window it is, and a claim
    # on one of them stands on that read the way a `curve_stats` read does.
    if isinstance(result, list):
        for entry in result:
            if isinstance(entry, dict) and isinstance(entry.get('key'), str):
                keys.append(entry['key'])
    return set(keys)


def _changeClaimNear(text, start, end):
    """Whether an un-negated change claim sits within reach of the
    span [start, end) -- the sentence between the key and the verb is
    what "sur Plot1, j'ai ajouté la température" reads as."""
    mid = (start + end) / 2.0
    claims = []
    for token in _CHANGE_CLAIM_SUBSTRINGS:
        i = 0
        while True:
            i = text.find(token, i)
            if i < 0:
                break
            claims.append((i, i + len(token)))
            i += 1
    for m in _CHANGE_CLAIM_RE.finditer(text):
        claims.append((m.start(), m.end()))
    for claim_start, claim_end in claims:
        if min(abs(claim_start - mid), abs(claim_end - mid)) > 60:
            continue
        window = text[max(0, claim_start - 40):claim_end + 40]
        if any(neg in window for neg in _CLAIM_NEGATIONS) or \
                _CLAIM_NEGATION_RE.search(window):
            continue
        return True
    return False


def unperformedWorkOn(text, ground):
    """The figure keys the answer presents with a change claim -- a
    curve added, a transform applied, an axis moved -- that no call of
    the request stands behind.

    ``ground`` is the union of the keys a call of this request worked
    on (a draw into the figure, a curve transform, an axis move), read
    back (``curve_stats``, ``export_curve``), or closed. A claim near a
    grounded key stands; the rest is a claim of work the tools did not
    do -- and it is refused by name, re-anchored once to do the work or
    read it, refused again on a second claim. A refusal or a failure
    word near the claim is the honest report of the call that was
    refused, and it stands on whatever the figure is. A description
    word is not in the claim family on purpose: "Plot1 montre la
    pression" says a state, and the loop that says it is the one that
    read it, not one that invented it.
    """
    text = (text or '').lower()
    if not any(token in text for token in _CHANGE_CLAIM_SUBSTRINGS) and \
            not _CHANGE_CLAIM_RE.search(text):
        return set()
    ground_low = {k.lower() for k in (ground or set()) if k}
    found = set()
    for spelling, start, end in _figureKeyMentions(text, ground):
        if spelling.lower() in ground_low:
            continue
        if _changeClaimNear(text, start, end):
            found.add(spelling)
    return found
