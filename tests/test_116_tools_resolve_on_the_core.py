# Copyright holders : Commissariat à l'Energie Atomique et aux Energies
# Alternatives (CEA), France; and Laboratory for Engineering Design - LECAD,
# University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C
# open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted
# upon downloading the software and/or exercising any of the rights granted
# under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""Every tool the loop offers the LLM must resolve to a method on the core.

The ``TOOLS`` list in ``imasviz.VizAgent.tools`` is what the in-app loop
offers the LLM: each entry carries the name it may call. ``AgentLoop._dispatch``
(``imasviz/VizAgent/agent.py``) then runs ``getattr(self.core, name)`` on the
concrete core, so a name in ``TOOLS`` that no core method answers is a tool
the LLM is offered that can never be answered -- the call returns the refusal
"not a gesture of this session", which the LLM cannot correct, because the
name it used is right and the target is not.

The ``get_screenshot`` / ``screenshot`` drift behind the user's 2026-11-07
viz_cli test is exactly this: the loop's tool list says ``get_screenshot``,
the core answered ``screenshot`` only, and the loop refused the call by name.
The MCP surface (``mcp_server/tools.py``) never hit it, because it maps each
tool to an *explicit* core call (tool ``get_screenshot`` -> ``core.screenshot``
); that is a naming layer, not a dispatch-by-name, so it is deliberately not
pinned here.

This test pins the one invariant that matters: every name in the loop's
``TOOLS`` must be a callable on the core the loop dispatches against.
"""

import pytest

from mcp_server.core import McpGuiCore


@pytest.fixture(scope='module')
def core_class(qapp):
    """The concrete core class the loop dispatches against."""
    import imasviz.VizAgent.core as core_module
    return core_module.McpGuiCore


def test_every_toolname_in_tools_resolves_on_the_core(core_class):
    """A tool the LLM may call must be a method the core can answer.

    ``AgentLoop._dispatch`` refuses by name a tool whose name no core
    method carries; this test is the guard that such a name is not in the
    tool list in the first place, so the refusal is never the answer the
    LLM gets.
    """
    from imasviz.VizAgent.tools import TOOLS
    unresolved = []
    for tool in TOOLS:
        name = tool['function']['name']
        method = getattr(core_class, name, None)
        if method is None or not callable(method):
            unresolved.append(name)
    assert not unresolved, (
        'TOOLS offers tools the core cannot answer: %s. Either add the '
        'method to McpGuiCore, or remove the entry from TOOLS.'
        % unresolved)


def test_get_screenshot_delegates_to_screenshot(qapp):
    """Not just the name, but the call: ``AgentLoop._dispatch`` resolves the
    tool name on the core and runs it -- the path that refused
    ``get_screenshot`` before the core answered the name. On the real class
    the alias must hand off to ``screenshot``, so both names return the
    same gesture for the same window."""
    class _Core(McpGuiCore):
        def __init__(self):
            pass  # no app needed: screenshot is stubbed, not rendered

        def screenshot(self, window='app'):
            return ('png:%s' % window).encode()

    core = _Core()
    assert core.get_screenshot(window='Plot1') == b'png:Plot1', \
        'get_screenshot must answer the same gesture as screenshot'
    assert core.get_screenshot('Plot1') == core.screenshot('Plot1')


def test_get_screenshot_answers(qapp):
    """The drift named in the docstring, pinned on its own: the loop's
    tool list offers ``get_screenshot``; the core must answer that name and
    keep the underlying ``screenshot`` available too."""
    core = McpGuiCore.__new__(McpGuiCore)
    assert callable(getattr(core, 'get_screenshot', None)), \
        'get_screenshot is not a method of McpGuiCore; the loop refuses ' \
        'every call to it by name'
    assert callable(getattr(core, 'screenshot', None)), \
        'screenshot is the underlying method; it must remain available'
