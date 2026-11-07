#!/usr/bin/env bash
# IMASViz — ITER HPC launcher (terminal client), from sources.
#
# CeCILL-C open source license — CEA (France) and LECAD / University of
# Ljubljana (Slovenia). See License.txt at the repository root.
#
#   scripts/iter/run_viz_cli.sh               # the REPL, offscreen
#   scripts/iter/run_viz_cli.sh "traces …"    # one prompt, then exit
#
# `module` is a shell function — never piped.
set -euo pipefail

# --- 1. modules (ITER HPC stack) -------------------------------------------
module load IMAS-Core
module load IMAS-Python
module load PyQtGraph
module load matplotlib

# --- 2. locate the repository -----------------------------------------------
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo"

# --- 3. environment (production) --------------------------------------------
export VIZ_HOME="$repo"
export VIZ_PRODUCTION=1
export UDA_DISABLED=1
export TS_MAPPINGS_DIR="${TS_MAPPINGS_DIR:-$repo/ts_mapping_files}"
export IMAS_VIZ_VERSION="${IMAS_VIZ_VERSION:-local}"
export PYTHONPATH="$VIZ_HOME${PYTHONPATH:+:$PYTHONPATH}"

# --- 4. the client — arguments pass straight through -------------------------
exec python3 -m viz_cli "$@"
