# M'adresser à l'agent pour tracer des signaux multi-axes

Ce fichier est le guide côté utilisateur : **quoi dire à l'agent** pour tracer un
signal le long des différents axes de son tenseur, et en particulier les quantités
dont la coordonnée n'est **pas** le temps (les profils de pression de `equilibrium`).
Il couvre aussi les trois questions récurrentes : comment fonctionnent les traces de
slices, la superposition de profils, et ce que fait (et ne fait pas) la surface MCP.

Tout ce qui est affirmé ici est soit vérifié dans le code de la surface
(`imasviz/VizAgent/`, `mcp_server/`, `viz_web/`), soit épinglé par un test nommé
(`test_124`, `test_125`, `test_132`, `test_119`, `test_133`). Les valeurs mesurées
sont celles du cas de référence **WEST 54924 run 0**, occurrence 0.

---

## 1. En une minute : la seule règle à retenir

Une quantité ne se trace **pas** « au hasard ». On lui adresse **un axe à étaler** et
on **fixe** les autres par leur index. C'est la paire qui s'appelle partout de la même
manière :

- `along` — **l'axe dont la courbe s'étale** : l'horloge (`"time"`), ou une coordonnée
  de la feuille (ex. `"psi"`). L'agent le laisse vide pour avoir l'horloge quand la
  quantité en porte une.
- `indices` — **les autres axes, un index chacun**, nommés par le nom de l'axe :
  une array of structures (`time_slice`, `profiles_1d`, `ion`, …) **ou** la coordonnée
  de la feuille (`psi`, …). Une entrée par array de structures imbriquée.

`get_signal` (lire les valeurs) et `plot_one` (tracer la courbe) **partagent ce même
schéma**, sur **le même core** (`McpGuiCore`). C'est pour ça que la figure qu'un
spectateur voit et les nombres qu'un lecteur rapporte sont **le même élément** du même
array — et pas deux éléments qui se ressemblent. (C'est le défaut que `test_124`
censure : il a fallu que le nombre que le lecteur nomme et l'élément que le slider
tient soient le même.)

Donc : « trace la pression à `psi=50` » → `along` = l'horloge (la pression y est tenue
par une `time_slice`), `indices = { "psi": 50 }`.

---

## 2. Le vocabulaire du tenseur

- **Occurrence** — une version d'un IDS que le cas porte (`equilibrium` occurrence 0).
  C'est ce que `list_idss`, `list_case_idss` et `load_ids(occurrence=…)` nomment.
- **Élément** — un membre d'une *array of structures*. `magnetics.bpol_probe[3]` est
  une sonde, **pas** la 3ᵉ version de `magnetics`. Les deux mots sont distincts et
  s'écrivent distinctement dans un refus.
- **Axe** — soit une array of structures (`time_slice`, `profiles_1d`, `ion`, …), soit
  la coordonnée d'une feuille (`psi`, …), soit une dimension non bornée du dictionnaire
  (elle s'identifie par son rang). C'est **ça** qu'on nomme dans `along`/`indices`.
- **`along` vs `indices`** — un seul est l'axe étalé (`along`), tous les autres sont
  fixés (`indices`, un index chacun). On ne fixe **pas** l'axe qu'on étale : un index
  sur l'axe même est un refus qu'on nomme.
- **Legacy vs schéma unifié** — les anciennes moitiés existent encore, pour la
  compatibilité : `along_time` (`plot_one`), `as_function_of_time` / `coordinate_index`
  / `time_index` (`get_signal`). Le schéma unifié (`along`/`indices`) les remplace ;
  on les laisse marcher, on les ne recommande pas.

---

## 3. Les trois façons de demander un tracage

### 3.1 Le long du temps

Le cas porte la quantité par une `time_slice` (ou une horloge homogène) :
```text
"trace la pression le long du temps, à psi = 50"
```
→ `plot_one(uri, path, along=null, indices={"psi": 50})` (`along=null` = l'horloge
quand la quantité en porte une). C'est le mode par défaut d'une courbe « pression le
long du temps ».

### 3.2 Le long d'une coordonnée qui n'est pas le temps

La feuille a une coordonnée (`psi`) :
```text
"trace la pression en fonction de psi"
```
→ `plot_one(uri, path, along="psi")` **et** `get_signal(uri, path, along="psi")`.
L'agent s'adresse à l'axe par son **nom** ; c'est le resolver (`axesAddressing` /
`QVizAxesSpec`) qui décide quelle abscisse on tient, et qui refuse (en nommant les
axes) un mot qu'aucun axe ne répond.

Sur `equilibrium.time_slice[0].profiles_1d.pressure`, c'est **la même moitié** pour
le tracer et pour le lire : `along="psi"` donne une courbe de **101 échantillons**
dont `x` court sur la coordonnée de la feuille (x≈-7,97…-7,78), **pas** les **49**
échantillons / ~16,4 s qu'on obtient le long du temps. Avant la correction ce même
appel était refusé *après* qu'une figure vide avait été ouverte (un « Plot2 » qui
restait dans `figureframes`, sa clé consommée, la figure suivante numérotée au-dessus
du trou) — `test_134` l'épingle ; aujourd'hui `along="psi"` se trace comme
il se lit.

### 3.3 Un slice à un instant donné

Une 1D-profile tenue par une `time_slice` :
```text
"la pression du slice le plus proche de 35 s"        → plot_slice(uri, leaf, time=35)
"la pression du slice le plus proche"                 → plot_slice(…, interpolation="closest")
"l'interpolation linéaire à 35 s"                     → plot_slice(…, interpolation="linear")
```
`plot_slice` lit la valeur **par la couche d'accès** (`DBEntry.get_slice`) — pas un
lerp maison. `plot_one(time=…, time_interp=…)` fait la même chose, mais ouvre la figure
au lieu de donner le nombre : c'est la même moitié. `time` et le schéma unifié
(`along`/`indices`) sont **refusés ensemble**, ce sont des lectures inverses.

---

## 4. Le cas concret : le profil de pression de `equilibrium`

Le nœud s'adresse en trois moitiés : `equilibrium` (l'IDS) · `time_slice[0]` (l'array
of structures) · `profiles_1d.pressure` (la feuille, la coordonnée `psi`). C'est une
quantité **tenue par la `time_slice`** — elle court donc par défaut le long du temps —
et elle a une coordonnée, `psi`.

### 4.1 L'ordre du tour

```text
open_case(uri="imas:hdf5?path=/…/west/3/54924/0")
list_idss(uri)                      # ou list_case_idss, la liste plus courte
load_ids(uri, ids_name="equilibrium", occurrence=0)
search_nodes(uri, query="pressure") # le chemin exact, les 3 façons de l'écrire
```

### 4.2 Les deux moitiés, sur la même figure

`get_signal` **et** `plot_one` s'adressent à la paire `along`/`indices` comme tout le
reste, et donnent **le même élément** :

```python
# Lire : la pression le long du temps, à psi = 0 / 10 / 50
get_signal(uri, "equilibrium.time_slice[0].profiles_1d.pressure",
           along=None, indices={"psi": 0})
get_signal(uri, "equilibrium.time_slice[0].profiles_1d.pressure",
           along=None, indices={"psi": 10})
get_signal(uri, "equilibrium.time_slice[0].profiles_1d.pressure",
           along=None, indices={"psi": 50})
```
Chacun répond une courbe (49 échantillons = le nombre de `time_slice` du cas), pas une
valeur unique. Le pic décroît strictement de l'axe vers la bordure :

| `psi` | pic (Pa)  | ce que le lecteur rapporte |
| ----- | --------- | --------------------------- |
| 0     | ≈ 50 317  | la plus haute               |
| 10    | ≈ 41 096  | strictement en dessous      |
| 50    | ≈ 13 196  | la plus basse               |

Ces trois nombres sont épinglés par `test_132` (tolérance 5 %), et le mode **ne les
invente pas** : le mode ne peut pas répondre à un nombre qu'il n'a pas lu. (C'est le
contresens que `tests/test_115` verrouille : une figure et un tableau de valeurs sans
aucun outil appelé ce tour-là est refusée, re-ancrée sur `get_signal` / `plot_one`,
et refusée encore si elle se répète.)

Tracer ces trois profils ensemble, sur **une seule** figure :
```python
# 1ᵉʳ appel : ouvre la figure (elle reçoit une cle)
first = plot_one(uri, "equilibrium.time_slice[0].profiles_1d.pressure",
                 along=None, indices={"psi": 0})
# 2ᵉ / 3ᵉ : on empile sur la cle du 1ᵉʳ
plot_one(uri, "equilibrium.time_slice[0].profiles_1d.pressure",
         along=None, indices={"psi": 10}, into_figure_key=first["figure"])
plot_one(uri, "equilibrium.time_slice[0].profiles_1d.pressure",
         along=None, indices={"psi": 50}, into_figure_key=first["figure"])
```
Trois courbes sur une figure (`frame.curveCount() == 3`), et non une figure par slice
ni une courbe trois fois.

---

## 5. Les traces de slices, comment ça marche

Un **slice** est un membre de la `time_slice` — la « trace de slice » d'une feuille
c'est la même feuille au sein d'une array of structures, lue à un instant donné. Il
n'y a pas de confusion avec l'occurrence (c'est une **version** de l'IDS), et pas de
confusion avec l'élément d'une *sonde* / d'une *boucle* (c'est un **membre** d'un
autre array).

Ce que l'agent et le core savent sur les slices :

- `load_ids(uri, ids, occ, slices="first"|"all")` — le chargement garde une `time_slice`
  (`"first"`, le défaut) ou toutes (`"all"`). C'est la moitié « que de slices » avant
  qu'on demande quoi que ce soit.
- `plot_slice(uri, leaf, time, occurrence=0, interpolation="linear"|"closest"|"previous",
  into_figure_key=None)` — une 1D-profile à un instant, **par la couche d'accès**
  (`DBEntry.get_slice`). Le temps en dehors de la portée du cas répond le `time_slice`
  le plus proche, et l'adresse répond `time_requested` **et** `time_slice_time` à côté
  (les deux, pas une valeur qui ressemble).
- `plot_one(…, time=…, time_interp=…)` — la même valeur, mais la figure qu'elle ouvre
  a un **slider de slice** (`sliceControls`) — c'est ce qu'on voit comme « traces de
  slices » à l'écran. `time` fixe le slice ; `time_interp=true` interpole entre les
  deux qui bornent.
- Le refus **`time` vs `along`/`indices`** est posé d'avance : une lecture l'une,
  l'autre la lecture inverse, et on ne demande pas les deux.
- `frame.sliceControls` — le slider de la `QVizCurvePlot` ouverte, qui répond les
  indices que la figure tient. C'est celui que l'utilisateur bouge à la souris, et
  celui que `test_124` et `test_132` consultent pour prouver que la figure **s'ouvre
  à l'index demandé** et non à l'index 0 que le tree portait.

En une phrase : un slice = **une feuille parmi une array of structures**, lue par son
index ; pas une version, pas l'élément d'une *sonde*. Les trois moitiés sont séparées,
et le core les refuse (en nommant) si on les mélange.

---

## 6. La superposition de profils, de façon robuste

Deux manières, et c'est tout. Les deux passent par le **même** schéma, la même figure,
le même core — donc la figure qu'un dessin montre et le nombre qu'une lecture rapporte
ne divergent pas.

### 6.1 `into_figure_key` — empiler sur la figure déjà ouverte

La première `plot_one` **ouvre** la figure et reçoit une cle (`Plot1`). Les suivantes
empilent sur cette cle. C'est le mode « sur la même figure ». Ce n'est **pas** un
défaut de la surface MCP : c'est la **même** règle pour les clients MCP, pour l'agent
embarqué, pour le web (`viz_web`), pour le CLI. (La surface MCP standalone
`python -m mcp_server` portait déjà `into_figure_key` — c'est `along`/`indices` qui
manquait, et c'est corrigé, voir § 8.)

Les indices **des autres** arrays de structures ne sont **pas** à cet usage : empiler
deux `bpol_probe` (2 et 10) sur une figure, c'est deux **chemins** de deux feuilles
de deux éléments, pas deux indices d'une même feuille. Le mode refuse `indices = { "bpol_probe": … }`
parce que la famille est déjà fixée sur une sonde par le chemin. Deux familles
différentes (2 sondes, puis 2 boucles) → **deux** figures, pas quatre dans une ; c'est
l'absence de `into_figure_key` qui fait que la deuxième ouvre une deuxième figure.

### 6.2 `select_signals` + `plot_selection`

Une sélection, une figure ; c'est le mode « d'abord choisir, puis tracer ». Utile
quand la superposition est le produit d'une **sélection** plutôt que la chaîne d'un
tracage.

### 6.3 Ce qu'une superposition **n'est pas**

Une superposition est une figure **qu'un outil d'ouverture a ouverte** et qu'un autre
outil d'empilement a alimentée. Un nom de figure sans un seul outil d'ouverture ce
tour-là est une **invention** : le mode refuse la réponse et renomme les deux
outils (`list_case_idss`, `get_signal`, `plot_one`) que le mode doit appeler.
C'est l'équivalent du « Plot4 » qui n'a jamais existé : le mode a tracé
`psi=0/50/10` sur des figures `Plot1/2/3` distinctes, et ce n'est **pas** la même
figure `Plot4` qu'il a ensuite nommé comme si elle existait.

---

## 7. « Après quelques tours, les captures ne s'affichent plus »

Deux causes se sont mêlées dans le cas du field : il y avait **un vrai défaut**
du core (un refus coûtait une fenêtre vide et un numéro — corrigé, plus bas),
et **le mental model** de la surface web (une figure est un fait par tour).
Ce que `viz_web` fait, et ce qu'il faut lui demander pour avoir des images :

- **Une cause réelle est corrigée et épinglée par `test_134`.** Avant,
  « pressure en fonction de psi » sur `equilibrium.time_slice[0]…` était
  **refusé** *après* qu'une figure vide avait été ouverte : `list_windows`
  nommait cette figure `visible`, sa cle était consommée (la figure suivante
  était numérotée au-dessus du trou), puis le collecteur la recueillait
  (« released from the bookkeeping ») — d'où « Plot2/Plot3 créées puis
  disparues ». Maintenant, `along='psi'` sur un membre designé par son chemin
  **se trace** (101 échantillons, x sur la coordonnée de la feuille), un refus
  ne coûte **ni** fenêtre **ni** numéro, et `get_signal` avec la même adresse
  répond la même courbe — la figure qu'on *voit* et le nombre qu'on *lit*
  sont le même élément.
- **Une figure est capturée dans le tour qui la trace.** `viz_web/web_session.py`
  (`_finishTurn`) sauve les figures que le tour **ajoute** à la session — les images
  d'un tour ne sont pas répétées dans le tour suivant. C'est voulu : un tour qui ne
  trace pas (mots uniquement, refus, `get_screenshot` seul) ne laisse pas de PNG.
- **Un tour d'empilement redessine sur une figure déjà ouverte.** Son delta
  « nouvelles figures » est **vide** : `plot_one(…, into_figure_key=Plot1)` ne change
  pas la liste des figures, et le code le sait — `web_session.py` porte même le
  commentaire « je ne vois plus les autres figures ». Si le tour n'a **pas** demandé
  non plus d'image (pas de `get_screenshot` dans le prompt), la page n'affiche rien
  pour ce tour, alors que la figure est bien là.
- **La re-capture se demande par le nom de la figure.** Dans le prompt : « montre-moi
  la figure `Plot1` » → `focus_window(window="Plot1")` (la bring forward) ; ou
  « prends une capture de `Plot1` » → `get_screenshot(window="Plot1")` (la sauve).
  Le bouton *Screenshot* sur une carte de la galerie fait exactement ça.
- **Le groupe du tour arrive ouvert, les groupes passés se ferment.**
  `viz_web/static/index.html` (`turnGroup`) pose le groupe du tour ouvert, et les
  anciens en `<details>` fermé — c'est voulu, c'est le mode « nom + compteur, clic
  pour ouvrir ». Au **rechargement** de la page, `buildGallery()` rebâtît tous les
  groupes **fermés**, depuis `/api/turns` : les PNGs sont là (sur disque, dans le
  dossier du tour), les groupes sont fermés. Ce n'est pas qu'ils « se sont perdus »,
  c'est qu'ils sont **repliables**.
- **Au rechargement tout redevient fermé** : `buildGallery()` lit `/api/turns`
  (la liste, pas les images) et les images sont demandées à
  `/api/turns/{n}/shots/{name}` au moment où le groupe s'ouvre. Un groupe qui a
  `0 shot` est un tour d'empilement sans capture demandée, voir au-dessus.

L'ordre des actions côté utilisateur qui garantit une image par demande :

1. **Dessiner ET demander la figure dans le même prompt** — « trace la pression
   à `psi=0`/`10`/`50` sur une même figure, et donne-moi la capture » → `plot_one`
   puis `get_screenshot` dans le même tour → le tour a une image, et le groupe arrive
   ouvert.
2. **Re-capturer une figure déjà tracée en la nommant** — « montre-moi `Plot1` » →
   `focus_window`. La figure est là, mais c'est le tour qui doit **demander** l'image
   pour que la page la prenne.

---

## 8. La surface MCP, ce qu'elle fait (et ce que le core partage)

« Doit-on revoir les outils MCP ? » — **oui, et c'est fait.** La surface MCP
standalone est `python -m mcp_server`, `mcp_server/tools.py` (FastMCP). C'est une
**troisième** surface sur le **même** core, en plus de l'agent embarqué et du
web (`viz_web`), mais c'est la seule des trois qui **ne portait pas** la paire
`along`/`indices` sur `plot_one` / `get_signal` (et n'avait pas `plot_slice`). C'est
ça qui explique que le CLI MCP (l'entry la plus proche du « web_cli ») échouait sur
les signaux multi-axes pendant que l'agent embarqué, lui, les portait déjà.

Ce qui est vrai **maintenant**, et épinglé par `test_133` :

- Le core est **un** : `imasviz/VizAgent/core.py` (`McpGuiCore`), ré-exporté par
  `mcp_server/core.py`. `plot_one` (l.757) et `get_signal` (l.1275) ont `along`,
  `indices`, `time`, `time_interp` ; `plot_slice` (l.1026) répond par
  `DBEntry.get_slice` ; `focus_window` (l.1368) bring-forward à une taille lisible.
- La surface MCP standalone (`mcp_server/tools.py`) **porte** la paire, après
  l'alignement : `plot_one` prend `along_time / into_figure_key / along / indices /
  time / time_interp`, `get_signal` prend `as_function_of_time / coordinate_index /
  time_index / along / indices`, et `plot_slice` est là. `test_133` est le garde-fou
  source (le `@server.tool(name='plot_slice')` y est) : rouge avant, vert après.
- L'agent embarqué et le web **partagent** le même schéma — `agent.py:169` passe
  `tools=TOOLS` de `imasviz/VizAgent/tools.py`, qui a déjà `along`/`indices`, et
  `test_125` l'épingle ; `agent.py:441` valide les arguments de la surface web
  contre `TOOL_PARAMETERS` (du même `TOOLS`), donc le POST `/api/tool` **porte**
  la paire, et `test_119` la pinnote maintenant à l'interface.

Une dernière chose qui tient à la même surface : **`get_screenshot` refuse quand une
figure n'existe pas** (`core.py:2078` → `screenshot(self, 'app')` →
`_resolveWindow(window)`). « Plot4 » dans un prompt de capture, sans qu'un seul
`plot_one` l'ait ouverte ce tour-là, est refusé **le nom de la figure** — pas
rendu, pas inventé. Les refus **n'ont pas de figure** — c'est la réponse du core,
pas sa faute.

---

## 9. Dictionnaire de phrases prêtes

| Je veux …                              | Dis à l'agent                                   | Ça répond                                    |
| -------------------------------------- | ----------------------------------------------- | -------------------------------------------- |
| la pression le long du temps, à `psi` | « trace `equilibrium.time_slice[0].profiles_1d.pressure` à `psi=50` » | `plot_one(…, along=null, indices={"psi":50})` |
| la pression en fonction de `psi`       | « trace la pression en fonction de `psi` »      | `plot_one(…, along="psi")`                    |
| 3 `psi` sur une même figure            | « trace `psi=0/10/50` sur **une même** figure » | `plot_one` × 3, `into_figure_key` sur 2       |
| 2 sondes, puis 2 boucles               | « trace `bpol_probe` 2 et 10, puis `flux_loop` 2 et 10 » | **deux** figures                             |
| un slice à un instant                  | « la pression du slice à 35 s »                 | `plot_slice(…, time=35)`                     |
| la valeur exacte à `psi=50`            | « lis la pression à `psi=50` »                  | `get_signal(…, along=null, indices={"psi":50})` |
| une capture de `Plot1`                 | « montre-moi `Plot1` » / « capture de `Plot1` » | `focus_window` / `get_screenshot(window="Plot1")` |
