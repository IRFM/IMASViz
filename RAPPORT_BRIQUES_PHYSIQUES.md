# Tour d'horizon — les quatre briques physiques

Synthèse du lot d'améliorations fonctionnelles construites pour les physiciens
des plasmas, au-dessus du cœur existant d'IMASViz. Date : 2026-11-21.
Branch : `worktree-brainstorming2`.

Les quatre priorités demandées sont toutes en place, committées, et vertes :

1. **Détection ELM / Sawtooth / transition L→H**
2. **FFT / spectre + cross-corrélation**
3. **Grandeurs dérivées** — `f_G` (Greenwald), `beta_N`, pression totale
4. **Tendance multi-jeux / campagne**

Chacune répond au même besoin physique — *voir ce que le cas dit, avec le
nombre que le cas donne* — et suit les mêmes règles de construction, décrites
une fois dans [l'architecture commune](#architecture-commune) puis résumées
brique par brique.

---

## Le principe à ne pas trahir

**Aucune brique ne fabrique un nombre.** Chaque méthode lit la feuille que le
cas garde (la même lecture qu'une figure de cette feuille ferait, via
`get_signal`) et répond le numéro *du cas*, nommé par son chemin, plus la
statistique qui en sort (moyenne, max, min). Une feuille que le cas ne tient
pas est **refusée par son nom** (`ValueError`), jamais remplacée par une valeur
plausible. Ce qui fait qu'une réponse n'est jamais à confondre avec un défaut
inventé : si un clic ou un appel ne produit rien, c'est que la feuille n'est
pas là, et le mot qui le dit est là où l'utilisateur le lit.

---

## Brique 1 — Détection d'événements (ELM · Sawtooth · L→H)

**Physique.** Trois lectures d'une série temporelle : une excursion vers le haut
(limitée par sa saillance, avec un plancher de valeur et un espacement minimal)
= un **ELM** ; la même lecture inversée, une chute = un **sawtooth** ; un
franchissement de seuil, un ou deux sens, avec une bande d'hystérésis = une
**transition L→H**. Plus la périodicité des événements.

Où le code :

| couche | où | fait |
|---|---|---|
| pure | `imaSViz/VizAnalysis/detect.py` | `peaks`, `transitions`, `period_stats`, `detect(kind, t, y, **params)` ; `kind ∈ elm / sawtooth / lh` (alias `e`, `saw`, `crash`, `l_h`, `transition`) |
| core | `imaSViz/VizAgent/core.py` | `detect_events`, `clear_event_marks`, `events_report` |
| GUI | `imaSViz/VizPlot/QVizEventMarks.py` — accroché à `QVizCurvePlot` | menu « Événements » du clic droit de la figure (3 types + « Retirer les marques »), marqueurs `InfiniteLine` sur la courbe vivante |
| rapport | `events_report` | HTML autonome sous `~/.imasviz/reports` |

Refus nommés : signal plat, trop court au moindre voisin, paramètre que le
type ne prend pas, espacement négatif, mode autre que `max`/`min`.

---

## Brique 2 — Spectre, bandes, cross-corrélation

**Physique.** Décomposer une série en ses fréquences : le spectre et ses
pics (fréquence, période, puissance, fraction de la puissance totale),
la puissance d'une bande `fmin..fmax`, et la **cross-corrélation** de deux
séries (le décalage qui maximise la corrélation, la fréquence/période commune
dominante). Le décalage est signé — série 2 qui *retarde* série 1 est lue
positif.

Où le code :

| couche | où | fait |
|---|---|---|
| pure | `imaSViz/VizAnalysis/spectra.py` | `spectrum(t, y, n_peaks)`, `band_power(t, y, fmin, fmax)`, `cross_correlation(t1, y1, t2, y2)` ; grilles de fréquences par `np.fft.rfftfreq` |
| core | `imaSViz/VizAgent/core.py` | `spectrum`, `cross_correlation`, `spectrum_report` |
| rapport | `spectrum_report` | HTML autonome : bandeau du spectre, pics, bande, corrélation |

Refus nommés : longueur inégale, série plate, bande nommée d'un seul bord
(`band_low` sans `band_high`, et l'inverse), série trop courte.

---

## Brique 3 — Grandeurs dérivées

**Physique.** Trois grandeurs qu'un cas *garde* et qu'une figure peut ne pas
dessiner : le **`f_G`** (fraction de Greenwald, `n_e / ((I_p/A)·1e20)`), le
**`beta_N`** (beta normalisé, lecture de la feuille `beta_normal`), et la
**pression totale** `p = n_e k_B T_e + n_i k_B T_i` (lecture de la feuille
totale que le cas a déjà sommée).

Où le code :

| couche | où | fait |
|---|---|---|
| pure | `imaSViz/VizAnalysis/spectra.py` | `greenwald_fraction(n_e, ip, area)` (formule point par point) |
| core | `imaSViz/VizAgent/core.py` | `greenwald`, `beta_normal`, `total_pressure` ; stats de courbe par `_scalarCurve` |

Refus nommés : série plate, longueurs inégales (« one length »), aucun élément
fini, `area == 0`. Pour `beta_N`/`total_pressure` : une feuille que le cas ne
tient pas est refusée par nom.

> Note sur `total_pressure` : on lit la feuille **totale** que le cas garde,
> on ne ré-invente pas la somme `e + i` — la feuille est ce que le cas a
> calculé, et c'est elle qui est citée dans la réponse.

---

## Brique 4 — Tendance / campagne

**Physique.** La **tendance d'une grandeur sur une série de jeux**, dans
l'ordre de la campagne : pente (moindres carrés sur l'index de shot),
premier→dernier, min/max *et le jeu d'où vient chacun*, direction
(montrant/montant/à plat). C'est la comparaison multi-shot qui manquait entre
les cas d'une même machine.

Où le code :

| couche | où | fait |
|---|---|---|
| pure | `imaSViz/VizAnalysis/trend.py` | `trend(values, labels)` — seul, sans numpy ; pente, extrêmes, direction |
| core | `imaSViz/VizAgent/core.py` | `campaign(cases, path, at=/which=, along, indices)`, `campaign_report` ; valeur par jeu via `_shotValue` (un index `at` **ou** un `which` — l'un des deux) |
| rapport | `campaign_report` | HTML autonome : table par jeu, la tendance, le tracé SVG des valeurs sur la campagne |

Refus nommés : campagne d'un seul jeu, jeu qui ne tient pas la feuille,
campagne à valeurs toutes égales (c'est une valeur, pas une tendance), `at`
**et** `which` ensemble, valeur nulle/nombre non fini/étiquette de longueur
différente.

---

## Architecture commune

Les quatre briques partagent la même découpe, à trois étages :

1. **Une couche pure** (`imaSViz/VizAnalysis/`) — numpy seule (ou rien), **pas
   de Qt, pas de IMAS**. Testée par des signaux synthétiques, sans cas : c'est
   ici que les règles de physicien sont piquées. C'est ce qui la rend réutilisable
   hors GUI et réutilisable par les autres surfaces.

2. **Le cœur** (`imaSViz/VizAgent/core.py`) — fait **une seule lecture**
   (`get_signal`, celle qu'une figure ferait) et demande la couche pure.
   Résultat : *ce qu'analyse la brique et ce que traça la figure sont la même
   lecture*. C'est aussi le seul endroit qui touche le cas, donc celui qui
   refuse par nom quand la feuille n'y est pas.

3. **Les surfaces et les rapports** — chaque brique s'expose aux **cinq
   surfaces** qui relient le cœur, et chaque brique *avec des nombres* donne
   un rapport HTML autonome sous `~/.imasviz/reports` (aucune requête externe,
   SVG/HTML en ligne).

### Surfaces par où les briques passent

| surface | comment elle porte les briques |
|---|---|
| **agent in-app** | les 11 outils dans la liste `TOOLS` (`imaSViz/VizAgent/tools.py`), résolus sur le cœur par `AgentLoop._dispatch` |
| **serveur MCP** | entrées explicites `@server.tool(name=...)` dans `mcp_server/tools.py`, chacune une `partial(core.<méthode>, …)` |
| **web** | `viz_web` lance le **même** `AgentLoop._dispatch` — tout outil de `TOOLS` y est appelable |
| **CLI** | `viz_cli` lit `TOOLS` génériquement et dispatche par le cœur |
| **gateway** | `viz_gateway` relaie le cœur (cf. `viz_gateway/USAGE.md`) |
| **GUI (menu)** | **Brique 1 seulement** a un menu de figure natif (« Événements »). Les autres arrivent à la figure par le cœur + rapports — il n'y a pas encore d'entrée native pour spectre/`f_G`/`beta_N`/pression/campagne |

### Liste des outils ajoutés (11)

`detect_events` · `clear_event_marks` · `events_report` · `spectrum` ·
`cross_correlation` · `spectrum_report` · `greenwald` · `beta_normal` ·
`total_pressure` · `campaign` · `campaign_report`

Chacun : `additionalProperties: False`, `required` posé, et le nom répond sur
le cœur (garde `test_116`) ; un paramètre hors schéma est refusé en nommant
l'intrus et les bons (`test_117`).

### Règle d'importation (défaut corrigé en cours de route)

Importer les fonctions du **sous-module** (`from imasviz.VizAnalysis.detect
import detect`), **pas** du paquet. Un import via le paquet peut retourner le
*module* au lieu de la fonction (un autre module qui importe le sous-module
ré-attache le lien du paquet) — c'est ce qui faisait `'module' object is not
callable` quand les fichiers de tests tournaient **ensemble** alors que chacun
passait seul. Corrigé (commit `12b1284`).

---

## Matrice de tests

**73 tests d'analyse** sur 8 fichiers, tous verts ; la suite combinée
(152–159 + gardes de contrat + import-sweep) passe à **224 passed**.

| test | brique | couvre |
|---|---|---|
| `test_152_event_detection_pure` (17) | 1 | la couche pure : les 3 types, plancher/saillance/espacement, période, refus |
| `test_153_event_detection_surface` (7) | 1 | le cœur : marquer/démarquer, le rapport |
| `test_154_event_detection_gui` (6) | 1 | la menu de figure, les marqueurs sur la courbe |
| `test_155_spectral_pure` (12) | 2 | spectre, bande, cross-corrélation (dont l'ordre du décalage) |
| `test_156_spectral_surface` (5) | 2 | le cœur : lecture de feuilles + rapport |
| `test_157_greenwald_fraction` (6) | 3 | la formule sur un triple connu + surface à 3 feuilles |
| `test_158_beta_and_pressure` (6) | 3 | `beta_N`, pression (cas réel) + refus d'une feuille absente |
| `test_159_campaign_trend` (14) | 4 | la tendance (synthétique) + 2 jeux réels + refus + rapport écrit |

Gardes transversales : `test_99_import_sweep` (l'ajout de modules est vu
comme +des ids, +2 xfail) · `test_116_tools_resolve_on_the_core` ·
`test_117_dispatch_refuses_unknown_parameters`.

### Exécuter

```bash
# depuis la racine du dépôt
cd /afs/eufus.eu/g2itmdev/user/g2lfleur/IMASViz/.qwen/worktrees/brainstorming2
module load PyQtGraph/0.13.7-intel-2023b
export VIZ_PRODUCTION=1 VIZ_HOME=$PWD QT_QPA_PLATFORM=offscreen
python3 -m pytest tests/test_15[2-9]*.py \
  tests/test_116_tools_resolve_on_the_core.py \
  tests/test_117_dispatch_refuses_unknown_parameters.py \
  tests/test_99_import_sweep.py -q
```

---

## Historique des commits (ordre posé)

```
49f8e73 feat(analysis): la tendance d'une grandeur sur une campagne de jeux
778c2c8 feat(analysis): beta_N et la pression totale d'un cas
12b1284 fix(analysis): importer les fonctions du sous-module, pas du paquet
92a24a2 feat(analysis): la fraction de Greenwald d'un cas
06e8b9a feat(analysis): le spectre et la cross-correlation d'une feuille, et le rapport
445774e feat(analysis): les faits spectraux d'une série, et de deux
72a4d37 feat(ui): la détection d'événements sur la figure de courbe
9d3c4ee feat(analysis): détecter, marquer et rapport des événements d'une figure
6f1fe1a feat(analysis): la couche pure qui détecte les événements d'une série
```

Un commit par surface visible, chacun vert, message écrit d'un tenant (pas de
`--amend`).

---

## Ce qui reste ouvert (à discuter, pas fait)

- **GUI : les briques 2–4 n'ont pas encore d'entrée native.** Brique 1 a son
  menu de figure ; les autres passent par agent/web/CLI/MCP + rapports. Une
  entrée « Spectre… / Campagne… / `f_G` » sur la figure du clic droit serait
  le pas suivant naturel, *à la même règle* (`QVizCurvePlot`, `weakref` sur le
  frame, refuser par nom ce que le cas ne tient pas).
- **Campagne : export en CSV/figure** (aujourd'hui le rapport HTML est le
  livrable ; `export_curve` existe déjà pour une figure).
- **Détection d'événements *sur une campagne*** (Brique 1 appliquée à la sortie
  de Brique 4 — ex. le taux de ELM sur une série de jeux).

Les chiffres cités ici (nombres de tests, noms de méthodes, chemins) sont ceux
vérifiés sur cet arbre au 2026-11-21 ; le code peut bouger, re-vérifier avant
de s'y fier.
