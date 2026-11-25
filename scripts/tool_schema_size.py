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

It reads the two faces off their **source**, not by importing them:
``imasviz.VizAgent.tools`` sits behind a package ``__init__`` that pulls
Qt and the IMAS HLI, and ``mcp_server.tools`` imports the MCP SDK. A
measurement that needs the module stack loaded is a measurement nobody
re-runs.

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

# What one tool costs before a word of its own: the OpenAI-shape envelope
# the schema is wrapped in. Measured, not guessed -- see `_plumbing`.
def _plumbing():
    return len(_json({
        'type': 'function',
        'function': {
            'name': '',
            'description': '',
            'parameters': {'type': 'object', 'properties': {},
                           'required': [], 'additionalProperties': False},
        },
    }))


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


def _mcpFace(path):
    """The tools the MCP face declares, and the prose each one carries.

    FastMCP builds that face's schema from the decorated function: its
    description is the docstring and its parameters come from the
    signature. So the docstring lengths and the signature lengths are what
    that face sends, and the count is what its client is offered.
    """
    tree = ast.parse(open(path, encoding='utf-8').read())
    tools = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            names = [kw.value.value for kw in decorator.keywords
                     if kw.arg == 'name']
            if not names:
                continue
            doc = ast.get_docstring(node) or ''
            arguments = [a.arg for a in node.args.args
                         if a.arg not in ('self', 'ctx')]
            tools.append({'name': names[0],
                          'docstringChars': len(doc),
                          'docstringWords': _words(doc),
                          'signatureChars': len(ast.unparse(node.args)),
                          'parameters': arguments})
    return tools


def measure(loopSource=LOOP_SOURCE, mcpSource=MCP_SOURCE):
    """Every number the report prints, in one dictionary."""
    tools, families, instructions = _sourceConstants(
        loopSource, ['TOOLS', 'FAMILIES', 'SYSTEM_INSTRUCTIONS'])

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

    # The projection: the vocabulary spelled as the table's OFFERS, which
    # is what a merged group is actually offered as -- "the drawing" is
    # `plot(mode=...)` AND `get_signal`, not one name. The members'
    # descriptions are kept verbatim (a merge that drops what a tool
    # answers is not a merge, it is a loss), and one block per parameter
    # name -- the longest, which is the one worth keeping -- plus the
    # discriminant's own block, which a merge ADDS: `mode` is a parameter
    # no member had. So the saving is the plumbing and the duplicated
    # blocks and nothing else: the prose is untouched, which is the point
    # of printing it separately.
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
            # members' schemas and keeps their prose verbatim.
            if offerName in schemaOf:
                sources = [schemaOf[offerName]]
                prose = [descriptions[offerName]]
            else:
                sources = [schemaOf[m] for m in names if m in schemaOf]
                prose = [descriptions[m] for m in names if m in descriptions]
            props = {}
            required = set()
            for schema in sources:
                for name, block in schema.get('properties', {}).items():
                    if len(_json(block)) > len(_json(props.get(name, {}))):
                        props[name] = block
                required.update(schema.get('required', []))
            if discriminator:
                props[discriminator] = {
                    'type': 'string',
                    'enum': [action for action, _member in actions]}
                required.add(discriminator)
            merged += plumbing
            merged += sum(len(_json(text)) - 2 for text in prose)
            merged += sum(len(_json(b)) for b in props.values())
            merged += len(_json(sorted(required)))

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

    mcp = _mcpFace(mcpSource)
    loopNames = {t['function']['name'] for t in tools}
    mcpNames = {t['name'] for t in mcp}

    return {
        'tools': len(tools),
        'payloadChars': len(payload),
        'payloadTokens': int(len(payload) / CHARS_PER_TOKEN),
        'descriptionChars': sum(len(d) for d in descriptions.values()),
        'descriptionWords': sum(_words(d) for d in descriptions.values()),
        'parameterChars': parameterChars,
        'distinctParameters': len(blocks),
        'repeatedParameterChars': repeated,
        'plumbingCharsPerTool': plumbing,
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
        'mcpTools': len(mcp),
        'mcpDocstringChars': sum(t['docstringChars'] for t in mcp),
        'mcpSignatureChars': sum(t['signatureChars'] for t in mcp),
        'mcpOnly': sorted(mcpNames - loopNames),
        'loopOnly': sorted(loopNames - mcpNames),
    }


def _delta(current, baseline):
    lines = []
    for key in ('tools', 'payloadChars', 'payloadTokens', 'descriptionChars',
                'repeatedParameterChars', 'projectedTools', 'mcpTools'):
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
    print('  plumbing     : %d chars per tool before a word of its own'
          % m['plumbingCharsPerTool'])
    print('  instructions : %s chars (once per turn, beside the schemas)'
          % format(m['systemInstructionsChars'], ','))
    print('  the MCP face declares %d tools (%s chars of docstring, %s of '
          'signature)' % (m['mcpTools'],
                          format(m['mcpDocstringChars'], ','),
                          format(m['mcpSignatureChars'], ',')))
    if m['mcpOnly'] or m['loopOnly']:
        print('  the two faces are NOT the same list: %d named only by the '
              'MCP face, %d only by the loop' % (len(m['mcpOnly']),
                                                 len(m['loopOnly'])))
        for label, names in (('mcp only', m['mcpOnly']),
                             ('loop only', m['loopOnly'])):
            if names:
                print('    %s: %s' % (label, ', '.join(names)))
    print('  projected on the %d offers of those %d groups (a merged group '
          'answers one name with a discriminant, the rest answer themselves;'
          ' descriptions kept, one block per parameter): %d tools, %s chars '
          '(~%d tokens, %+.1f%%)'
          % (m['projectedTools'], m['groups'], m['projectedTools'],
             format(m['projectedPayloadChars'], ','),
             m['projectedPayloadTokens'],
             100.0 * (m['projectedPayloadChars'] - m['payloadChars'])
             / m['payloadChars']))
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
