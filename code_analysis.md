# Analyse du code — IMASViz

**Date :** 2026-11-28 — **Branche :** `feature/tensor-plot-core` — **HEAD :** `863425bf`
**Périmètre :** `imasviz/`, `mcp_server/`, `viz_cli/`, `viz_web/`, `viz_gateway/`, `tests/`, `scripts/` — lecture seule, aucun fichier modifié.

## 1. État d'ensemble

| Métrique | Valeur |
| --- | --- |
| Fichiers `.py` (sans `__pycache__`) | **396** |
| Lignes de code | **~53 800** |
| Fichiers de test | **194** (`tests/`, hors `support/`) |
| Doc Sphinx | 149 fichiers |
| CI / linter / packaging | **aucun** (pas de `.github/`, pas de `setup.py`/`pyproject`) |
| TODO/FIXME | 10 seulement |

L'architecture a mûri : lecture unifiée via l'axe-model (`QVizAxesSpec`, `QVizTensorDataAccess`), figures récentes (`QVizCurvePlot`, `QVizImagePlot`, `QVizTablePlot`, `QVizStackedPlot`, `QVizPreviewPlot`), plugins déclaratifs avec scope, 5 faces sur un seul noyau (`McpGuiCore`) — in-app, MCP (`mcp_server/`), CLI (`viz_cli/`), web (`viz_web/`), gateway (`viz_gateway/`). Les faces partagent les mêmes tables (`TOOLS` partagé entre `VizAgent/tools.py` et `mcp_server/tools.py`). Le ledger `LEGACY_REPLACEMENT.md` (T0–T45) est à jour : le widget legacy `QVizPlotWidget`, les `QVizTablePlotView`/`QVizStackedPlotView`/`QVizMultiPlotWindow` et `QVizViewLoadingStrategy` sont supprimés (T22, T7, T12).

**Vérifié à l'introspection, pas au credo** : `issues.md` (traceback `No module named 'imas.ids_data_type'`, chemin `/home/ITER/fleuryl/IMASViz/.../QVizTimeSliceSelection.py`, daté 2026-10-23) est un artefact **stale** — le fichier du working tree est déjà corrigé (ligne 37 : `from imasviz.VizDataAccess.QVizAccessLayerHLI import IDSDataType`). Et contrairement à ce qu'on pourrait penser, `imasviz/VizAgent/core_plots.py:474` qui fait `import imas.ids_defs as _id` **ne pose pas de problème** : introspecté sur `IMAS-Python/2.3.0-intel-2023b`, `imas.ids_defs` existe et porte `LINEAR_INTERP`/`PREVIOUS_INTERP`/`CLOSEST_INTERP` (l'idiom `eval/exec` était dans le module generated-HLI, pas dans l'HLI moderne).

## 2. Code mort vérifié (présent, jamais atteint hors worktrees)

**a) Plugins non enregistrés / non atteignables** — tous dans `imasviz/VizPlugins/`, tous exclus du registre de `VizPlugin.py` (commentés) et tous parlant le contrat abrogaté (`execute(vizAPI, pluginEntry)` + `getEntries`/`isEnabled`) :

| Fichier | État |
| --- | --- |
| `viz_tofu/viz_tofu_plugin.py` | Enregistré en commentaire ; importe `tofu` hors repo |
| `viz_example_plugin/viz_example_plugin.py` | En commentaire ; consommateur unique = `VizExamples/test_plugin.py` (aussi abrogé) |
| `viz_simple_plot_example/simplePlotPluginExample.py` | En commentaire ; **dossier sans `__init__.py`** — importable à peine |
| `viz_gkdb/` | **`__init__.py` vide**, aucune classe |
| `test_imas_viz_plugin.py` | Démo exécutable : `import imas_viz_plugins.equilibriumcharts` — package inexistant depuis longtemps |

**b) Modules jamais importés** :

- `imasviz/Viz_DataSelection_API.py` — classe morte, sans aucun consommateur
- `imasviz/VizDataSource/QVizToreSupraDataSource.py` — jamais instantié ; le seul lecteur de `ts_mapping_files/` (10 XML) + `TS_MAPPINGS_DIR` — tout ce dossier est du poids mort
- `imasviz/VizDataSource/QvizIMASPublicDataSource.py` — classe définie, jamais instanciée
- `imasviz/VizGUI/VizWidgets/QVizTableOfIDSs.py` — consommé uniquement par `tests/test_11_table_of_IDDs.py` (test unique, fonction unique)

**c) `viz_tofu` et `viz_example_plugin`** sont aussi les seuls fichiers de `VizPlugins/` à importer `tofu`/`imas_viz_plugins` — la frontière du registre n'est pas protégée.

## 3. Imports morts vérifiés par grep (fichiers, lignes)

| Fichier | Import mort |
| --- | --- |
| `VizDataSource/QVizIMASDataSource.py:17` | `QVizGlobalValues`, `QVizPreferences` |
| `VizDataSource/QVizToreSupraDataSource.py:13` | `Thread`, `RLock` (module mort, voir §2) |
| `VizPlugins/QVizPluginCatalog.py:40` | `import shiboken6` |
| `VizPlugins/viz_equi/equilibriumcharts.py:39-40` | `QDockWidget`, `QApplication`, `QTreeWidget`, `QTreeWidgetItem`, `QGridLayout` |
| `VizGUI/QtVIZ_GUI.py:13,18,20,349` | `partial`, `QTableView`, `Path`, `import imas` (ligne 349, dans `OpenDataSourceFromTab2` — jamais utilisé) |
| `VizGUI/VizGUICommands/VizMenusManagement/QVizMainMenuController.py:12,14` | `QApplication`, `GlobalIcons` (utilisés seulement dans un commentaire ligne 171) |
| `VizGUI/VizGUICommands/VizMenusManagement/QVizSignalHandling.py:11,15` | `re`, `QVizPreferences` |
| `VizGUI/VizGUICommands/VizOpenViews/QVizOpenShotView.py:10,13,23` | `os`, `QVizGlobalValues`, `QVizIMASDataSource` (in-function, jamais utilisé même dans la fonction) |
| `VizGUI/VizGUICommands/VizSession/QVizRestoreSession.py:50` | `CURVE` |
| `VizGUI/VizTreeView/QVizDataTreeView.py:12,20` | `numpy as np`, `QVizGlobalValues`, `getWindowSize` (seulement dans un commentaire ligne 958) |
| `VizGUI/VizTreeView/QVizDataTreeViewBuilder.py:12` | `Thread`, `Condition` |
| `VizGUI/VizWidgets/QVizIMASdbBrowserWidget.py:18-19` | `threading`, `Thread`, `Condition` |
| `VizUtils/QVizGlobalOperations.py:17` | `numpy as np` |
| `Viz_API.py:12` | `import sys` |
| `viz_gateway/run.py:29` | `import time` |
| `viz_web/run.py:35` | `import sys` |
| `viz_web/web_session.py:632` | `LLMClient` (import intra-fonction, non utilisé) |

⚠️ Aucun n'est silencieux à l'exécution (importés mais jamais référencés), mais c'est du bruit qui fausse les lectures des dépendances. Le scan AST a aussi flagué `VizUtils/__init__.py` — ce sont les **re-exports** volontaires (surface publique), à ignorer.

## 4. Points de vigilance

- **`Viz_API.py`** — 1 760 lignes, 94 méthodes : c'est le cœur de la session, structuré mais volumineux. Une découpe par cluster (comme `VizAgent/core_*.py`) serait un chantier à part.
- **`.qwen/` non git-ignoré** — `git status` affiche 68 worktrees (`.qwen/worktrees/`, **2,3 Go**) + 76 Mo de probes (`.qwen/tmp/probe_*.py`) à chaque fois. Ce sont des fichiers locaux du user (non touchés), mais `.gitignore` ne les exclut pas — chaque commit doit multiplier les `git add` explicites.
- **`QtVIZ_GUI.py:702`** — `sys.exit(app.exec())` au niveau module (le `QApplication` est construit au niveau module, ce qui force le `sys.argv` offscreen avant import — documenté, mais c'est un piège déjà connu).
- **`scripts/tool_schema_size.py:143`** — fait `exec(code, namespace)` sur du code compilé depuis l'AST de `VizAgent/tools.py`. Techniquement correct mais c'est un `exec` hors du repo de production — un outil de dev, pas un livrable.
- **`VizGUICommands/VizMenusManagement/QVizMainMenuController.py`** — garde-corps historique (`menuAddPublicDB`, `menuAddSpecificUserDB`) dont l'entrée est toujours câblée au pop-up de la start panel, mais peu de tests la protègent (test_50/test_75).
- **Suite de tests** — 194 fichiers, ~18 min, 2254 ids ; **pas de CI**. Aucun verdict qualité automatique. Les 5 fichiers racine `issues.md`, `Modelfile`, `prompt_gemini`, `Inkling-2-Mini-UD-Q4_K_XL.gguf`, `module av IMAS` sont des fichiers locaux du user (non touchés).

## 5. En résumé

- **Sain** : lecture unifiée, figures récentes, plugins déclaratifs, faces MCP/CLI/web/gateway sur un noyau unique, ledger T0–T45 à jour, zéro `eval/exec` exécutable, 10 TODOs.
- **Mort** : 4 plugins non enregistrés (dont un sans `__init__.py`) + 1 démo cassée, 4 modules jamais importés, `ts_mapping_files/` + `TS_MAPPINGS_DIR` (dead Tore-Supra), `Viz_DataSelection_API`, ~20 imports morts.
- **Point d'attention** : `Viz_API.py` (1 760 l./94 méth.), `.qwen/` non ignoré (2,3 Go de worktrees), zéro CI.
