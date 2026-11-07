#!/usr/bin/env bash
# IMASViz — WEST launcher (visible window), from sources.
#
# CeCILL-C open source license — CEA (France) and LECAD / University of
# Ljubljana (Slovenia). See License.txt at the repository root.
#
# On WEST the Python stack (PySide6, PyQtGraph, matplotlib, IMAS-Python)
# is pip-installed into a virtualenv at ~/.imasviz/venv; the IMAS core
# libraries come from `module load IMAS`.
#
# `module` is a shell function — never piped.
set -euo pipefail

# --- 1. python virtualenv ---------------------------------------------------
venv="${HOME}/.imasviz/venv"
if [ ! -d "$venv" ]; then
    python3 -m venv "$venv"
    source "$venv/bin/activate"
    python3 -m pip install --quiet --upgrade pip
    python3 -m pip install --quiet IMAS-Python PySide6 PyQtGraph matplotlib
fi
# Activate (always; the venv may already be loaded) and ensure packages.
source "$venv/bin/activate"
python3 -c "import imas" 2>/dev/null || \
    python3 -m pip install --quiet IMAS-Python PySide6 PyQtGraph matplotlib

# --- 2. modules (WEST core) --------------------------------------------------
module load IMAS

# --- 3. locate the repository -------------------------------------------------
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo"

# --- 4. environment (production) ----------------------------------------------
export VIZ_HOME="$repo"
export VIZ_PRODUCTION=1
export UDA_DISABLED=1
export TS_MAPPINGS_DIR="${TS_MAPPINGS_DIR:-$repo/ts_mapping_files}"
export IMAS_VIZ_VERSION="${IMAS_VIZ_VERSION:-local}"
export PYTHONPATH="$VIZ_HOME${PYTHONPATH:+:$PYTHONPATH}"

# --- 5. the visible window ----------------------------------------------------
exec python "$VIZ_HOME/imasviz/VizGUI/QtVIZ_GUI.py"
