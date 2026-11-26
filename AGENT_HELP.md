# M'adresser à l'agent pour tracer des signaux multi-axes

Ce fichier est le guide côté utilisateur : **quoi dire à l'agent** pour tracer un
signal le long des différents axes de son tenseur, et en particulier les quantités
dont la coordonnée n'est **pas** le temps (les profils de pression de `equilibrium`).
Il couvre aussi les trois questions récurrentes : comment fonctionnent les traces de
slices, la superposition de profils, et ce que fait (et ne fait pas) la face MCP.

Tout ce qui est affirmé ici est soit vérifié dans le code de la surface
(`imasviz/VizAgent/`, `mcp_server/`, `viz_web/`), soit épinglé par un test nommé
(`test_115`, `test_119`, `test_122`, `test_124`, `test_125`, `test_132`, `test_133`,
`test_134`, `test_135`, `test_136`). Les valeurs mesurées sont celles du cas de
référence **WEST 54924 run 0**, occurrence 0.

**Une chose sur la forme de ce fichier :** il écrit les appels comme on les **offre à
un modèle**, pas comme ils s'écrivent en Python dans le core. Un groupe d'outils
répond **un nom** et un mot qui dit lequel (`mode`, `action`, `operation`, `scope`,
`quantity`) ; les anciens noms du core (`plot_one`, `plot_slice`, `load_ids`,
`focus_window`, …) restent des gestes du core et des **valeurs** légales de ce mot,
mais ne sont plus ce qu'on appelle. `test_178` refuse que cette fiche demande à un
lecteur d'appeler un nom qui n'est plus sur le fil.

---

## 1. En une minute : la seule règle à retenir

Une quantité ne se trace **pas** « au hasard ». On lui adresse **un axe à étaler** et
on **fixe** les autres par leur index. C'est la paire qui s'appelle partout de la même
manière :

- `along` — **l'axe dont la courbe s'étale** : l'horloge (`"time"`), ou une coordonnée
  de la feuille (ex. `"psi"`). On le laisse vide pour avoir l'horloge quand la quantité
  en porte une.
- `indices` — **les autres axes, un index chacun**, nommés par le nom de l'axe :
  une array of structures (`time_slice`, `profiles_1d`, `ion`, …) **ou** la coordonnée
  de la feuille (`psi`, …). Une entrée par array de structures imbriquée.

`get_signal` (lire les valeurs) et `plot(mode="single")` (tracer la courbe)
**partagent ce même schéma**, sur **le même core** (`McpGuiCore`). C'est pour ça que la
figure qu'un spectateur voit et les nombres qu'un lecteur rapporte sont **le même
élément** du même array — et pas deux éléments qui se ressemblent. (C'est le défaut
que `test_124` censure : il a fallu que le nombre que le lecteur nomme et l'élément
que le slider tient soient le même.)

Donc : « trace la pression à `psi=50` » → `along` = l'horloge (la pression y est tenue
par une `time_slice`), `indices = { "psi": 50 }`.

---

## 2. Le vocabulaire du tenseur

- **Occurrence** — une version d'un IDS que le cas porte (`equilibrium` occurrence 0).
  C'est ce que `manage_idss(action="declared")`, `manage_idss(action="filled")` et
  `manage_idss(action="load", occurrence=…)` nomment.
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
  compatibilité : `along_time` (`plot`), `as_function_of_time` / `coordinate_index` /
  `time_index` (`get_signal`). Le schéma unifié (`along`/`indices`) les remplace ;
  on les laisse marcher, on ne les recommande pas.

---

## 3. Les trois façons de demander un tracage

### 3.1 Le long du temps

Le cas porte la quantité par une `time_slice` (ou une horloge homogène) :
```text
"trace la pression le long du temps, à psi = 50"
```
→ `plot(mode="single", uri=…, path=…, along=null, indices={"psi": 50})`
(`along=null` = l'horloge quand la quantité en porte une). C'est le mode par défaut
d'une courbe « pression le long du temps ».

### 3.2 Le long d'une coordonnée qui n'est pas le temps

La feuille a une coordonnée (`psi`) :
```text
"trace la pression en fonction de psi"
```
→ `plot(mode="single", uri=…, path=…, along="psi")` **et**
`get_signal(uri=…, path=…, along="psi")`.
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
"la pression du slice le plus proche de 35 s"   → plot(mode="slice", …, time=35)
"la pression du slice le plus proche"           → plot(mode="slice", …, interpolation="closest")
"l'interpolation linéaire à 35 s"               → plot(mode="slice", …, interpolation="linear")
```
Le mode « slice » lit la valeur **par la couche d'accès** (`DBEntry.get_slice`) — pas
un lerp maison. `plot(mode="single", time=…, time_interp=…)` fait la même chose, mais
ouvre la figure au lieu de donner le nombre : c'est la même moitié. `time` et le
schéma unifié (`along`/`indices`) sont **refusés ensemble**, ce sont des lectures
inverses.

---

## 4. Le cas concret : le profil de pression de `equilibrium`

Le nœud s'adresse en trois moitiés : `equilibrium` (l'IDS) · `time_slice[0]` (l'array
of structures) · `profiles_1d.pressure` (la feuille, la coordonnée `psi`). C'est une
quantité **tenue par la `time_slice`** — elle court donc par défaut le long du temps —
et elle a une coordonnée, `psi`.

### 4.1 L'ordre du tour

```text
manage_case(action="open", uri="imas:hdf5?path=/…/west/3/54924/0")
manage_idss(action="filled", uri=…)          # ou "declared", la liste longue
manage_idss(action="load", uri=…, ids_name="equilibrium", occurrence=0)
inspect_tree(action="search", uri=…, query="pressure")   # le chemin exact, ses 3 écritures
```

### 4.2 Les deux moitiés, sur la même figure

`get_signal` **et** `plot` s'adressent à la paire `along`/`indices` comme tout le
reste, et donnent **le même élément** :

```python
# Lire : la pression le long du temps, à psi = 0 / 10 / 50
get_signal(uri=uri, path="equilibrium.time_slice[0].profiles_1d.pressure",
           along=None, indices={"psi": 0})
get_signal(uri=uri, path="equilibrium.time_slice[0].profiles_1d.pressure",
           along=None, indices={"psi": 10})
get_signal(uri=uri, path="equilibrium.time_slice[0].profiles_1d.pressure",
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
invente pas** : il ne peut pas répondre à un nombre qu'il n'a pas lu. (C'est le
contresens que `test_115` verrouille : une figure et un tableau de valeurs sans aucun
outil appelé ce tour-là sont refusés, re-ancrés sur `get_signal` / `plot`, et refusés
encore si la réponse se répète.)

Tracer ces trois profils ensemble, sur **une seule** figure :
```python
# 1ᵉʳ appel : ouvre la figure (elle reçoit une cle)
first = plot(mode="single", uri=uri,
             path="equilibrium.time_slice[0].profiles_1d.pressure",
             along=None, indices={"psi": 0})
# 2ᵉ / 3ᵉ : on empile sur la cle du 1ᵉʳ
plot(mode="single", uri=uri,
     path="equilibrium.time_slice[0].profiles_1d.pressure",
     along=None, indices={"psi": 10}, into_figure_key=first["figure"])
plot(mode="single", uri=uri,
     path="equilibrium.time_slice[0].profiles_1d.pressure",
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

- `manage_idss(action="load", uri=…, ids_name=…, occurrence=…,
  slices="first"|"all")` — le chargement garde une `time_slice` (`"first"`, le défaut)
  ou toutes (`"all"`). C'est la moitié « que de slices » avant qu'on demande quoi que
  ce soit.
- `plot(mode="slice", uri=…, path=…, time=…, occurrence=0,
  interpolation="linear"|"closest"|"previous")` — une 1D-profile à un instant, **par
  la couche d'accès** (`DBEntry.get_slice`). Le temps en dehors de la portée du cas
  répond le `time_slice` le plus proche, et l'adresse répond `time_requested` **et**
  `time_slice_time` à côté (les deux, pas une valeur qui ressemble).
- `plot(mode="single", time=…, time_interp=…)` — la même valeur, mais la figure
  qu'elle ouvre a un **slider de slice** (`sliceControls`) — c'est ce qu'on voit comme
  « traces de slices » à l'écran. `time` fixe le slice ; `time_interp=true` interpole
  entre les deux qui bornent.
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

Le premier `plot(mode="single")` **ouvre** la figure et reçoit une cle (`Plot1`). Les
suivants empilent sur cette cle. C'est le mode « sur la même figure ». Ce n'est **pas**
un défaut de la face MCP : c'est la **même** règle pour les clients MCP, pour l'agent
embarqué, pour le web (`viz_web`), pour le CLI.

Les indices **des autres** arrays de structures ne sont **pas** à cet usage : empiler
deux `bpol_probe` (2 et 10) sur une figure, c'est deux **chemins** de deux feuilles de
deux éléments, pas deux indices d'une même feuille. Le mode refuse
`indices = { "bpol_probe": … }` parce que la famille est déjà fixée sur une sonde par
le chemin. Deux familles différentes (2 sondes, puis 2 boucles) → **deux** figures, pas
quatre dans une ; c'est l'absence d'`into_figure_key` qui fait que la deuxième ouvre
une deuxième figure.

**N indices d'une même feuille, une figure** — le cas « `psi=75, 80, 85, 25` » :
c'est le premier `plot(mode="single")` qui **ouvre** la figure et qui garde le curseur
(un curseur à balayage) ; les suivants, en empilant sur la même figure, sont des
**éléments distincts** de la même feuille et sont **gelés** sur leur index nommé.
Chaque courbe répond à son index, pas à la position du curseur (le curseur n'est
plus touché quand on empile — sinon toutes les courbes répondraient à la dernière
valeur posée, et c'est le bug « 4 courbes identiques » que le core ne doit plus
produire. Épinglé par `test_132`). Empiler des indices d'une **autre** famille
(`bpol_probe[7]`, pas `bpol_probe`) reste refusé : la famille est fixée par le
chemin, ce n'est pas un curseur. (Épinglé par `test_134`, la moitié refus.)

### 6.2 `manage_selection(action="select")` puis `plot(mode="selection")`

Une sélection, une figure ; c'est le mode « d'abord choisir, puis tracer ». Utile
quand la superposition est le produit d'une **sélection** plutôt que la chaîne d'un
tracage.

### 6.3 Ce qu'une superposition **n'est pas**

Une superposition est une figure **qu'un outil d'ouverture a ouverte** et qu'un autre
appel a alimentée. Un nom de figure sans un seul outil d'ouverture ce tour-là est une
**invention** : le mode refuse la réponse et renomme les appels qu'il devait faire
(`manage_idss`, `get_signal`, `plot`). C'est l'équivalent du « Plot4 » qui n'a jamais
existé : le mode a tracé `psi=0/50/10` sur des figures `Plot1/2/3` distinctes, et ce
n'est **pas** la même figure `Plot4` qu'il a ensuite nommée comme si elle existait.

### 6.4 Fermer est une **demande**, pas une action

Les trois gestes qui effacent du bookkeeping — `manage_window(action="close")` (une
figure), `manage_case(action="close")` (un cas et ses figures qui ne servent que lui),
`manage_session(action="new")` (tout) — sont **demandés, pas pris** (la garde est dans
`agent.py::_dispatch`, épinglée par `test_135`) : le modèle ne les pose que si **ton
message du tour** le demande — « ferme Plot5 », « close the figure », « referme le
cas », « nouvelle session », « reset », « nettoie la session »… (français et anglais,
les deux sont lus). S'il les pose sur un tour qui ne les demande pas, c'est un refus
nommé, l'outil ne s'exécute **pas**, et la figure / le cas / la session restent debout
— la réponse dit alors expressément que rien n'a été fermé. C'est la voie par laquelle
une figure présentait « puis disparaissait » sans que tu aies demandé à fermer quoi
que ce soit : le mode fermait, la figure n'était plus dans
`manage_window(action="list")`, et le modèle le constatait sans l'avoir demandé. Si le
refus te semble trop large sur un mot que tu emploies naturellement (« close to 10% »,
« refresh »…), dis-le : la liste des mots qui comptent (`agent.py::_CLOSURE_WORDS`,
FR/EN) se règle en conséquence.

---

## 7. « Après quelques tours, les captures ne s'affichent plus »

Deux causes se sont mêlées dans le cas du field : il y avait **un vrai défaut** du
core (un refus coûtait une fenêtre vide et un numéro — corrigé, plus bas), et **le
mental model** de la face web (une figure est un fait par tour). Ce que `viz_web`
fait, et ce qu'il faut lui demander pour avoir des images :

- **Une cause réelle est corrigée et épinglée par `test_134`.** Avant, « pressure en
  fonction de psi » sur `equilibrium.time_slice[0]…` était **refusé** *après* qu'une
  figure vide avait été ouverte : `manage_window(action="list")` nommait cette figure
  `visible`, sa cle était consommée (la figure suivante était numérotée au-dessus du
  trou), puis le collecteur la recueillait (« released from the bookkeeping ») — d'où
  « Plot2/Plot3 créées puis disparues ». Maintenant, `along="psi"` sur un membre
  désigné par son chemin **se trace** (101 échantillons, x sur la coordonnée de la
  feuille), un refus ne coûte **ni** fenêtre **ni** numéro, et `get_signal` avec la
  même adresse répond la même courbe — la figure qu'on *voit* et le nombre qu'on *lit*
  sont le même élément.
- **Montrer une figure est une commande de l'utilisateur, pas l'agent.** L'agent trace
  ce qu'on lui demande ; la figure est une fenêtre de la session, dans le menu
  *Windows*, et **montrer** (apporter au premier plan, remonter) et **dimensionner**
  sont les gestes de l'utilisateur dans ce menu. « *montre-moi `Plot1`* » / « *ramène
  `Plot1` devant* » / « *je ne vois pas la figure* » → `manage_window(action="focus")`,
  qui montre ou ramène **à la taille que la fenêtre porte déjà** — pixels nommés (« *en
  grand* », `width` / `height`) seulement quand on les nomme. Une figure tracée ou
  simplement nommée dans la réponse n'est **ni montrée ni dimensionnée** de sa propre
  initiative : c'est le *Windows* menu qui y répond. Épinglé par `test_136` dans le
  prompt (`tools.py`, l'instruction du même mot + la description du mode) et le
  garde-fou inverse de `test_122` (un focus sans pixels ne change pas la taille).
  `get_screenshot` reste la capture PNG **explicite** (« donne-moi une capture de
  `Plot1` », « montre-moi l'interface ») ; quand la fenêtre répond petite et qu'on
  demande une image lisible, le focus avec les pixels nommés, puis la capture.
- **Une figure est capturée dans le tour qui la trace — ou la déplace —** et dans
  celui qui **demande** de la voir. `viz_web/web_session.py` (`_finishTurn`) et le REPL
  (`viz_cli/session.py`) sauvent les figures que le tour **ajoute** à la session, celles
  que ses gestes **déplacent** (`transform_curve` et ses sœurs posent le `figure_key`,
  lu en demande de capture par `captureAsk`), et les fenêtres **explicitement**
  demandées (`get_screenshot`, le focus d'un « montre-moi ») — les images d'un tour ne
  sont pas répétées dans le tour suivant. C'est voulu : un tour qui ne trace pas ni ne
  déplace (mots uniquement, refus) ne laisse pas de PNG, et une figure que la réponse
  **nomme seulement** n'est ré-capturée **nulle part** : la mention n'est pas un
  montrage, et son PNG est déjà dans le dossier du tour qui l'a tracée.
- **Un tour d'empilement redessine sur une figure déjà ouverte.** Son delta « nouvelles
  figures » est **vide** : `plot(mode="single", …, into_figure_key=Plot1)` ne change
  pas la liste des figures, et le code le sait — `web_session.py` porte même le
  commentaire « je ne vois plus les autres figures ». Si le tour n'a **pas** demandé
  non plus d'image (pas de capture dans le prompt), la page n'affiche rien pour ce
  tour, alors que la figure est bien là.
- **La re-capture se demande par le nom de la figure.** Dans le prompt : « montre-moi
  la figure `Plot1` » → `manage_window(action="focus", window="Plot1")` (la bring
  forward) ; ou « prends une capture de `Plot1` » → `get_screenshot(window="Plot1")`
  (la sauve). Le bouton *Screenshot* sur une carte de la galerie fait exactement ça.
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

1. **Dessiner ET demander la figure dans le même prompt** — « trace la pression à
   `psi=0`/`10`/`50` sur une même figure, et donne-moi la capture » → `plot` puis
   `get_screenshot` dans le même tour → le tour a une image, et le groupe arrive
   ouvert.
2. **Re-capturer une figure déjà tracée en la nommant** — « montre-moi `Plot1` » →
   le focus. La figure est là, mais c'est le tour qui doit **demander** l'image pour
   que la page la prenne.

---

## 8. La face MCP, ce qu'elle fait (et ce que le core partage)

« Doit-on revoir les outils MCP ? » — **oui, et c'est fait.** La face MCP standalone
est `python -m mcp_server`, `mcp_server/tools.py` (FastMCP). C'est une **troisième**
face sur le **même** core, en plus de l'agent embarqué et du web (`viz_web`) ; elle a
été la seule des trois à **ne pas porter** la paire `along`/`indices` sur le tracage et
la lecture (et à ne pas avoir le mode « slice »). C'est ça qui explique que le client
MCP échouait sur les signaux multi-axes pendant que l'agent embarqué, lui, les portait
déjà.

Ce qui est vrai **maintenant**, et épinglé :

- Le core est **un** : `imasviz/VizAgent/core.py` (`McpGuiCore`), ré-exporté par
  `mcp_server/core.py`. Ses gestes de tracage et de lecture (`plot_one`, `get_signal`)
  prennent `along`, `indices`, `time`, `time_interp` ; le geste du slice répond par
  `DBEntry.get_slice` ; celui du focus bring-forward, à la taille que la fenêtre porte
  déjà (les pixels nommés quand on les nomme).
- La face MCP standalone **porte** la paire parce qu'elle ne l'écrit plus elle-même :
  elle **génère** ses outils en parcourant `TOOLS` — une déclaration assemblée par
  entrée de la table, signature, type, énumération et note du paramètre compris (T6,
  2026-11-26 : un fichier de 1 185 lignes est devenu 360). Un mot ajouté sur la face
  de la boucle est donc sur le socket à la construction suivante du serveur, sans qu'on
  ait rien à retenir. Le garde-fou est `test_177` : il lit `list_tools()` et refuse un
  nom, une note, un type ou une description que ce fichier inventerait ; `test_133`
  demande à la table les mots de l'adressage (`along`, `indices`), qui sont maintenant
  leur seule écriture.
- L'agent embarqué et le web **partagent** le même schéma : la boucle envoie `TOOLS`
  de `imasviz/VizAgent/tools.py`, qui a déjà `along`/`indices` (`test_125` l'épingle),
  et un appel reçu du web passe par la **même** couture `resolveCall` + les mêmes
  `TOOL_PARAMETERS` / `ACTION_PARAMETERS` que le tour de la boucle, donc le POST
  `/api/tool` **porte** la paire — `test_119` l'épingle côté interface.
- Un groupe d'outils répond **un nom** et son discriminant, sur les deux faces à la
  fois : `plot(mode=…)`, `manage_idss(action=…)`, `manage_window(action=…)`, etc. Il
  n'y a plus d'entaille entre les deux : ce que la boucle offre est ce que le socket
  offre.

Une dernière chose qui tient à la même face : **`get_screenshot` refuse quand une
figure n'existe pas** — le geste de capture résout la fenêtre nommée avant de peindre.
« Plot4 » dans une demande de capture, sans qu'un seul tracage l'ait ouverte
ce tour-là, est refusé **par le nom de la figure** — pas rendu, pas inventé. Les refus
**n'ont pas de figure** — c'est la réponse du core, pas sa faute.

---

## 9. Dictionnaire de phrases prêtes

| Je veux …                              | Dis à l'agent                                   | Ça répond                                    |
| -------------------------------------- | ----------------------------------------------- | -------------------------------------------- |
| la pression le long du temps, à `psi` | « trace `equilibrium.time_slice[0].profiles_1d.pressure` à `psi=50` » | `plot(mode="single", along=null, indices={"psi":50})` |
| la pression en fonction de `psi`       | « trace la pression en fonction de `psi` »      | `plot(mode="single", along="psi")`            |
| 3 `psi` sur une même figure            | « trace `psi=0/10/50` sur **une même** figure » | `plot(mode="single")` × 3, `into_figure_key` sur 2 |
| 2 sondes, puis 2 boucles               | « trace `bpol_probe` 2 et 10, puis `flux_loop` 2 et 10 » | **deux** figures                             |
| un slice à un instant                  | « la pression du slice à 35 s »                 | `plot(mode="slice", time=35)`                |
| la valeur exacte à `psi=50`            | « lis la pression à `psi=50` »                  | `get_signal(along=null, indices={"psi":50})` |
| une capture de `Plot1`                 | « montre-moi `Plot1` » / « capture de `Plot1` » | focus / `get_screenshot(window="Plot1")`     |
