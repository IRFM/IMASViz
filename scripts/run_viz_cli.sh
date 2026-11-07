#!/usr/bin/env bash
# ImasViz — launcher for the terminal client (viz_cli) on the gateway, from
# sources.
#
# CeCILL-C open source license — CEA (France) and LECAD / University of
# Ljubljana (Slovenia). See License.txt at the repository root.
#
# Loads the module stack and the production environment, then hands off to
# viz_cli. On this gateway the HLI is the **intel** one: the foss variant
# does not load its SciPy-bundle requirement here. `module` is a shell
# function — it is never piped, a pipe would run it in a subshell and lose
# the environment it sets.
#
#   scripts/run_viz_cli.sh                      # the REPL, offscreen
#   scripts/run_viz_cli.sh "trace le champ"     # one prompt, then exit
set -euo pipefail

# --- 1. modules (intel stack) ---------------------------------------------
module load PySide6/6.6.2-GCCcore-13.2.0
module load IMAS-Python/2.3.0-intel-2023b
module load PyQtGraph/0.13.7-intel-2023b

# --- 2. locate the repository ---------------------------------------------
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo"

# --- 3. environment (production) ------------------------------------------
export VIZ_HOME="$repo"
export VIZ_PRODUCTION=1
export UDA_DISABLED=1
export TS_MAPPINGS_DIR="${TS_MAPPINGS_DIR:-$repo/ts_mapping_files}"
export IMAS_VIZ_VERSION="${IMAS_VIZ_VERSION:-local}"
# Not forced: viz_cli appends VIZ_HOME itself; replacing the modules'
# PYTHONPATH would drop the PySide6/IMAS paths.
export PYTHONPATH="$VIZ_HOME${PYTHONPATH:+:$PYTHONPATH}"

# --- 4. the client — arguments (a prompt, flags) pass straight through -----
exec python3 -m viz_cli "$@"
