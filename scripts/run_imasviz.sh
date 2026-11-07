#!/usr/bin/env bash
# ImasViz — launcher for the gateway (this node), from sources.
#
# CeCILL-C open source license — CEA (France) and LECAD / University of
# Ljubljana (Slovenia). See License.txt at the repository root.
#
# Loads the module stack, sets the production environment, and opens the
# visual application (needs an X display). On this gateway the HLI is the
# **intel** one: the foss variant does not load its SciPy-bundle requirement
# here. `module` is a shell function — it is never piped, a pipe would run it
# in a subshell and lose the environment it sets.
set -euo pipefail

# --- 1. modules (intel stack) ---------------------------------------------
module load PySide6/6.6.2-GCCcore-13.2.0
module load IMAS-Python/2.3.0-intel-2023b
module load PyQtGraph/0.13.7-intel-2023b

# --- 2. locate the repository ---------------------------------------------
# The script lives in <repo>/scripts; the top-level package is <repo>/imasviz.
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo"

# --- 3. environment (production) ------------------------------------------
export VIZ_HOME="$repo"
export VIZ_PRODUCTION=1
export UDA_DISABLED=1
export TS_MAPPINGS_DIR="${TS_MAPPINGS_DIR:-$repo/ts_mapping_files}"
# The window title carries this; overridable from the environment.
export IMAS_VIZ_VERSION="${IMAS_VIZ_VERSION:-local}"
# Not forced: the code appends VIZ_HOME to sys.path itself, and replacing the
# PYTHONPATH the modules export would drop the PySide6/IMAS paths.
export PYTHONPATH="$VIZ_HOME${PYTHONPATH:+:$PYTHONPATH}"

# --- 4. the visible window --------------------------------------------------
exec python "$VIZ_HOME/imasviz/VizGUI/QtVIZ_GUI.py"
