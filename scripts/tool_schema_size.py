# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C
# open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted
# upon downloading the software and/or exercising any of the rights granted
# under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""What the agent's tool vocabulary costs on the wire, measured.

The loop sends its whole tool list on **every** turn of an ask
(``AgentLoop`` calls ``chat(messages, tools=TOOLS)`` inside its turn
loop), so the schemas are a fixed cost multiplied by the turn budget --
not a one-off at the start of a session. Reducing the number of names is
only one of the two levers: the descriptions are close to half the
payload, and they are prose, not plumbing. This script says which part
of the payload is which, tool by tool and group by group, so a proposed
merge can be quoted as a number instead of a feeling.

It reads the vocabulary off its **source**, not by importing it:
``imasviz.VizAgent.tools`` sits behind a package ``__init__`` that pulls
Qt and the IMAS HLI. A measurement that needs the module stack loaded is a
measurement nobody re-runs.

There is **one** vocabulary to read. Since T6 ``mcp_server/tools.py``
builds its tools by walking ``TOOLS``, so its names, its descriptions and
its parameter notes are these entries and cannot be measured beside them;
what is read there is the residue -- a tool declared by hand, which is the
shape the drift took before that pass, and which ``test_177`` refuses.
``test_174`` asks that the residue stays empty.

The last line of the loop face is the same vocabulary spelled as the
table's **offers** rather than as its tools. That used to be a projection
-- what a merge still to come would cost. ``test_175`` refuses an offer the
faces answer nowhere, so there is no merge left to imagine and the line
answers the present: it must equal the payload to the character, and
``test_174`` pins that equality. A line that used to read "-6.2 %" was not
a saving; it was this script forgetting to count the names of its own
parameters.

    python3 scripts/tool_schema_size.py
    python3 scripts/tool_schema_size.py --json /tmp/tools.json
    python3 scripts/tool_schema_size.py --baseline /tmp/tools.json

The token figure is an order of magnitude, never a count: the model this
application talks to is a local GGUF, whose byte-pair encoding this node
holds no tokenizer for. ``CHARS_PER_TOKEN`` is the usual English ratio;
the character counts it is derived from are exact, and a delta in
characters is a delta worth quoting even where the token estimate is not.
"""

import argparse
import ast
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOOP_SOURCE = os.path.join(REPO, 'imasviz', 'VizAgent', 'tools.py')
MCP_SOURCE = os.path.join(REPO, 'mcp_server', 'tools.py')

# Chars per token, for the order-of-magnitude figure only. See the module
# docstring: the exact numbers this script reports are characters.
CHARS_PER_TOKEN = 4.0

# The OpenAI-shape envelope one tool travels in, filled or empty. `_json`
# of the empty one is what a tool costs before a word of its own.
def _envelope(name, description, properties, required):
    """One tool as the endpoint sends it, filled or empty.

    The projection is measured through this and never by adding its parts,
    because a sum over ``properties.values()`` drops every parameter NAME:
    that is 16 of the 39 characters the old arithmetic was off by on
    ``manage_case``, and 1 825 over the whole payload. The envelope is what
    travels, so measuring it cannot be off by a piece of the shape it
    describes.

    ``required`` is the list, or ``None`` for a schema that carries no such
    key at all -- which two of this vocabulary's tools do (``get_screenshot``,
    ``get_logs``: nothing is mandatory about a screen or a log). Inventing an
    empty one there writes 14 characters the wire never sends.
    """
    parameters = {'type': 'object', 'properties': properties,
                  'additionalProperties': False}
    if required is not None:
        parameters['required'] = required
    return {
        'type': 'function',
        'function': {'name': name, 'description': description,
                     'parameters': parameters},
    }


def _plumbing():
    return len(_json(_envelope('', '', {}, [])))


def _json(value):
    """The compact wire form: what an HTTP client puts in the body."""
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def _words(text):
    return len(text.split())


def _sourceConstants(path, literalNames):
    """The module-level values of ``literalNames``, without importing.

    ``TOOLS`` is built by calls to the module's own ``_tool`` helper, so it
    is not a literal the ``ast`` alone can read: the helper's definition is
    compiled along with the assignment and run in an empty namespace. The
    names listed in ``literalNames`` are read that way; anything the module
    does beyond that (importing Qt, importing the SDK) is never reached.
    """
    tree = ast.parse(open(path, encoding='utf-8').read())
    wanted = set(literalNames)
    body = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == '_tool':
            body.append(node)
        elif (isinstance(node, ast.Assign)
              and any(getattr(t, 'id', None) in wanted for t in node.targets)):
            body.append(node)
    found = set()
    for node in body:
        if isinstance(node, ast.Assign):
            found.update(t.id for t in node.targets if isinstance(t, ast.Name))
    missing = wanted - found
    if missing:
        raise SystemExit('%s holds no %s' % (path, ', '.join(sorted(missing))))
    namespace = {}
    code = compile(ast.Module(body=body, type_ignores=tree.type_ignores),
                   path, 'exec')
    exec(code, namespace)
    return [namespace[name] for name in literalNames]


def _handWrittenTools(path):
    """The tools ``mcp_server/tools.py`` declares for itself.

    Since T6 the honest answer is an empty list: that file walks ``TOOLS``
    and assembles one tool per entry, so its name list, its descriptions
    and its parameter notes ARE these entries -- there is nothing beside
    the table to weigh. What is read here is the residue: a ``server.tool``
    call naming a tool with a literal, in either shape (a decorator or the
    registration line the generator uses). One of those coming back is a
    second spelling of one gesture, which is how the two faces drifted
    apart before the pass that merged them, and it is refused by
    ``test_177`` -- this script only prints the count, so that a number
    quoted from it says what it is measuring.
    """
    tree = ast.parse(open(path, encoding='utf-8').read())
    spelled = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if not (isinstance(function, ast.Attribute)
                and function.attr == 'tool'):
            continue
        for keyword in node.keywords:
            if keyword.arg == 'name' and isinstance(keyword.value,
                                                    ast.Constant) \
                    and isinstance(keyword.value.value, str):
                spelled.append(keyword.value.value)
    return spelled


def measure(loopSource=LOOP_SOURCE, mcpSource=MCP_SOURCE):
    """Every number the report prints, in one dictionary."""
    tools, families, instructions, shared = _sourceConstants(
        loopSource, ['TOOLS', 'FAMILIES', 'SYSTEM_INSTRUCTIONS',
                     'SHARED_NOTES'])

    payload = _json(tools)
    descriptions = {t['function']['name']: t['function']['description']
                    for t in tools}
    sizes = {t['function']['name']: len(_json(t)) for t in tools}

    # One block per parameter name, with the cost of its repetitions: the
    # same word (`along`, `scope`, `figure_key`) spelled out again in every
    # schema that takes it.
    blocks = {}
    for tool in tools:
        for name, block in tool['function']['parameters'].get(
                'properties', {}).items():
            blocks.setdefault(name, []).append(len(_json(block)))
    repeated = sum(sum(lengths) - max(lengths)
                   for lengths in blocks.values() if len(lengths) > 1)
    parameterChars = sum(max(lengths) for lengths in blocks.values()) \
        + repeated

    # The prose of the notes alone, told apart from the plumbing of the
    # block that carries it (a name, a type, the `description` key): the
    # half a shorter wording reduces, and the half of the parameter cost
    # that no wording can touch.
    notes = [block.get('description')
             for tool in tools
             for block in tool['function']['parameters'].get(
                 'properties', {}).values()]
    noteChars = sum(len(note) for note in notes if note)
    noteWords = sum(_words(note) for note in notes if note)
    silentParameters = sum(1 for note in notes if not note)

    # The spelling to compare: the vocabulary as the table's OFFERS, which
    # is what a merged group is actually offered as -- "the drawing" is
    # `plot(mode=...)` AND `get_signal`, not one name. The members'
    # descriptions are kept verbatim (a merge that drops what a tool
    # answers is not a merge, it is a loss), one block per parameter name --
    # the longest, which is the one worth keeping -- plus the discriminant's
    # own block, which a merge ADDS: `mode` is a parameter no member had.
    # The prose is therefore untouched by a merge, which is the point of
    # printing it separately above.
    #
    # It is measured as one envelope per offer, never as a sum of parts,
    # and `test_175` is why that matters here: every offer the table spells
    # is an offer the faces answer, so there is no pending merge left to
    # imagine -- this answers the present, and `projectedPayloadChars ==
    # payloadChars` is the reading that says so. An offer still to come
    # would be the union of its members' schemas and would keep their prose
    # verbatim; that branch is arithmetic too, it just has no ground truth
    # to be checked against until it is built.
    plumbing = _plumbing()
    schemaOf = {t['function']['name']: t['function']['parameters']
                for t in tools}
    merged = 0
    offered = 0
    for _label, members, offers in families:
        spelled = list(offers) if offers else [
            (name, None, ()) for name in members]
        for offerName, discriminator, actions in spelled:
            offered += 1
            names = [member for _action, member in actions] or [offerName]
            # An offer already on the wire carries its own schema and its
            # own prose; an offer still to come is the union of its
            # members'.
            if offerName in schemaOf:
                sources = [schemaOf[offerName]]
                prose = [descriptions[offerName]]
            else:
                sources = [schemaOf[m] for m in names if m in schemaOf]
                prose = [descriptions[m] for m in names if m in descriptions]
            props = {}
            required = set()
            hasRequired = any('required' in schema for schema in sources)
            for schema in sources:
                for name, block in schema.get('properties', {}).items():
                    if len(_json(block)) > len(_json(props.get(name, {}))):
                        props[name] = block
                required.update(schema.get('required', []))
            if discriminator and discriminator not in props:
                props[discriminator] = {
                    'type': 'string',
                    'enum': [action for action, _member in actions]}
                required.add(discriminator)
                hasRequired = True
            merged += len(_json(_envelope(offerName, '\n'.join(prose),
                                          props,
                                          sorted(required) if hasRequired
                                          else None)))
    # The projection is spelled as a list too, because that is what a turn
    # carries: the brackets around the envelopes and the comma between them,
    # or the two halves of the comparison are not the same shape.
    merged += offered + 1

    # What a group costs TODAY is the sum of the schemas it has on the wire
    # today: its members while they are still offered one by one, or its
    # offer once the merge is done. A merged member is in no schema any
    # more, so it counts for nothing here -- which is the point: the
    # reports group's cost moved from three tools to one.
    def offeredToday(members, offers):
        names = [name for name in members if name in sizes]
        names += [offer[0] for offer in (offers or ()) if offer[0] in sizes]
        return names

    groups = [{'label': label, 'members': list(members),
               'offers': len(offers) if offers else len(members),
               'currentChars': sum(sizes[name]
                                   for name in offeredToday(members, offers))}
              for label, members, offers in families]

    # One vocabulary, two faces. The endpoint's tool list IS this list --
    # it walks the table -- so the only thing to read in that file is
    # whether a tool escaped the generation and answers its own name again.
    hand = _handWrittenTools(mcpSource)

    return {
        'tools': len(tools),
        'payloadChars': len(payload),
        'payloadTokens': int(len(payload) / CHARS_PER_TOKEN),
        'descriptionChars': sum(len(d) for d in descriptions.values()),
        'descriptionWords': sum(_words(d) for d in descriptions.values()),
        'parameterChars': parameterChars,
        'distinctParameters': len(blocks),
        'repeatedParameterChars': repeated,
        'parameterNoteChars': noteChars,
        'parameterNoteWords': noteWords,
        'silentParameters': silentParameters,
        'sharedParameterWords': len(shared),
        'plumbingCharsPerTool': plumbing,
        'plumbingCharsWithoutRequired': len(
            _json(_envelope('', '', {}, None))),
        'toolsWithoutRequiredList': sum(
            1 for t in tools if 'required' not in t['function']
            ['parameters']),
        'systemInstructionsChars': len(instructions),
        'groups': len(families),
        'projectedTools': offered,
        'projectedPayloadChars': merged,
        'projectedPayloadTokens': int(merged / CHARS_PER_TOKEN),
        'asciiEscapeChars': len(_json(tools)) - len(
            json.dumps(tools, ensure_ascii=True, separators=(',', ':'))),
        'largest': sorted(((sizes[n], n) for n in sizes), reverse=True)[:10],
        'perTool': sizes,
        'groupBreakdown': groups,
        # The face the socket answers with: the same 23 entries, the same
        # descriptions, the same notes -- the payload of a ``tools/list``
        # round-trip, which is a one-off for a client and not a cost per
        # turn. What is counted here is what escaped the generation.
        'mcpTools': len(tools),
        'mcpProseChars': sum(len(d) for d in descriptions.values()),
        'mcpHandWritten': sorted(hand),
    }


def _delta(current, baseline):
    lines = []
    for key in ('tools', 'payloadChars', 'payloadTokens', 'descriptionChars',
                'parameterNoteChars', 'repeatedParameterChars',
                'projectedTools', 'mcpTools'):
        before, after = baseline.get(key), current.get(key)
        if isinstance(before, int) and isinstance(after, int):
            sign = after - before
            lines.append('  %-24s %8d -> %8d  %+d'
                         % (key, before, after, sign))
    return lines


def report(m):
    print('the loop face -- %s' % os.path.relpath(LOOP_SOURCE, REPO))
    print('  %d tools offered, %s chars on every turn of an ask '
          '(~%d tokens)' % (m['tools'], format(m['payloadChars'], ','),
                            m['payloadTokens']))
    print('  descriptions : %s chars (%.1f%% of the payload, %s words)'
          % (format(m['descriptionChars'], ','),
             100.0 * m['descriptionChars'] / m['payloadChars'],
             format(m['descriptionWords'], ',')))
    print('  parameters   : %s chars, of which %s are the same block '
          'recopied (%d distinct names)'
          % (format(m['parameterChars'], ','),
             format(m['repeatedParameterChars'], ','),
             m['distinctParameters']))
    print('  notes        : %s chars / %s words of that, %d blocks carrying '
          'no note, %d shared words spelled once'
          % (format(m['parameterNoteChars'], ','),
             format(m['parameterNoteWords'], ','),
             m['silentParameters'], m['sharedParameterWords']))
    print('  plumbing     : %d chars per tool before a word of its own'
          ' (%d for the %d that carry no required list)'
          % (m['plumbingCharsPerTool'], m['plumbingCharsWithoutRequired'],
             m['toolsWithoutRequiredList']))
    print('  instructions : %s chars (once per turn, beside the schemas)'
          % format(m['systemInstructionsChars'], ','))
    print('  the MCP face is generated from these %d entries: same names, '
          'same %s chars of description, same notes (test_177 pins that on '
          'list_tools); %d declared by hand in mcp_server/tools.py'
          % (m['mcpTools'], format(m['mcpProseChars'], ','),
             len(m['mcpHandWritten'])))
    if m['mcpHandWritten']:
        print('    declared by hand, and therefore spelled twice: %s'
              % ', '.join(m['mcpHandWritten']))
    print('  spelled as the %d offers of those %d groups (a merged group '
          'answers one name with a discriminant, the rest answer themselves;'
          ' descriptions kept, one block per parameter): %d tools, %s chars '
          '(~%d tokens, %+.1f%% -- test_175 leaves no merge to project, so '
          'these are the same %s characters read two ways)'
          % (m['projectedTools'], m['groups'], m['projectedTools'],
             format(m['projectedPayloadChars'], ','),
             m['projectedPayloadTokens'],
             100.0 * (m['projectedPayloadChars'] - m['payloadChars'])
             / m['payloadChars'], format(m['payloadChars'], ',')))
    print('\nthe %d biggest tools' % len(m['largest']))
    for size, name in m['largest']:
        print('  %-26s %5d chars' % (name, size))
    print('\nthe groups, by what they cost today')
    for group in sorted(m['groupBreakdown'],
                        key=lambda g: -g['currentChars']):
        print('  %-38s %2d tools -> %2d offered  %6d chars'
              % (group['label'], len(group['members']), group['offers'],
                 group['currentChars']))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--json', metavar='PATH',
                        help='write these metrics as JSON')
    parser.add_argument('--baseline', metavar='PATH',
                        help='print the delta against a JSON written earlier')
    args = parser.parse_args(argv)

    current = measure()
    report(current)
    if args.baseline:
        with open(args.baseline, encoding='utf-8') as handle:
            baseline = json.load(handle)
        print('\ndelta against %s' % args.baseline)
        for line in _delta(current, baseline):
            print(line)
    if args.json:
        with open(args.json, 'w', encoding='utf-8') as handle:
            json.dump(current, handle, indent=2, ensure_ascii=False)
        print('\nmetrics written to %s' % args.json)
    return 0


if __name__ == '__main__':
    sys.exit(main())
