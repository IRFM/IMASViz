# Mode d'emploi — `viz_gateway`

Le mode d'emploi de la couche multi-user d'IMASViz. Court : pour lancer vite.
La doctrine (pourquoi, les refus, la limite v1, la route d'UDS v2) est dans le
`README.md` du même dossier.

## Ce que c'est

Un navigateur, plus d'un user à la fois. Chaque user est un **token**, chaque
token répond sur une **instance `viz_web`** de son user — soit lancée ici par la
gateway (user *local*, isolée par son `HOME`), soit pointant sur une URL
d'enregistrement (user *remote*). La gateway elle-même n'a aucun widget : c'est
un proxy HTTP et un superviseur de processus.

```
[user A — browser]      [user B — browser]
     | Bearer TA                 | Bearer TB
     v                           v
   +---------------------------------------------+
   |  python3 -m viz_gateway                     |
   |  token -> user -> backend (local|remote)    |
   |  proxy SSE + JSON                           |
   +---------------------------------------------+
     | Bearer TA                 | Bearer TB
     v                           v
[viz_web (HOME=alice)]   [viz_web (HOME=bob)]
```

## 1. Prérequis

La gateway **hérite** l'environnement du shell qui la lance — les enfants que
elle démarre (`python3 -m viz_web`) reçoivent le même. Charge donc la pile HLI
**avant** :

```bash
module load ach-modules
module load PySide6/6.6.2-GCCcore-13.2.0
module load IMAS-Python/2.3.0-…       # la variante que ce node tient
module load PyQtGraph/0.13.7-…
export VIZ_HOME=$PWD
export VIZ_PRODUCTION=1                  # ou 0 pour un mode test
```

La **mémoire** est plus serrée que les ports : chaque user local ≈ 150–300 Mo +
un thread Qt. Sur ce node, c'est la RAM qui limite le `--max-users` utile, bien
avant l'épuisement des ports.

## 2. Lancer la gateway

```bash
python3 -m viz_gateway \
    --port 8760 \
    --max-users 20 \
    --idle-timeout 1800 \
    --users-dir ~/.imasviz/gateway
```

Options (défaut dans la parenthèse) :

| Flag | Défaut | Rôle |
|------|--------|------|
| `--host` | `127.0.0.1` | interface où la gateway écoute |
| `--port` | `8760` | port de **la gateway** (les backends locaux reçoivent leur port par le kernel) |
| `--users-dir` | `~/.imasviz/gateway` | dossier qui tient `users.json` et les `homes/` des users locaux |
| `--max-users` | `20` | nombre d'instances vivantes au maximum |
| `--idle-timeout` | `1800` (s) | temps d'inactivité avant que le pool tue une instance |

Le **reap** court en arrière-plan toutes les 30 s : le pool demande de lui les
users inactifs plus de `--idle-timeout`, les stoppe, libère le port. Un user qui
revient plus tard redémarre une nouvelle instance derrière son token, sans que
le caller le sache.

## 3. Inscrire un user

Un user est une ligne dans `~/.imasviz/gateway/users.json`. Le token est
généré. Deux formes — choisir.

### Local (la gateway lance l'instance)

```python
from viz_gateway.userstore import UserStore
store = UserStore('~/.imasviz/gateway')
token_alice = store.issue('alice', 'local')
# Le HOME est créé sous ~/.imasviz/gateway/homes/alice
```

Résultat dans `users.json` :

```json
{
  "alice": {
    "token": "gXk…24c",
    "kind":  "local",
    "home":  "~/.imasviz/gateway/homes/alice",
    "url":   null
  }
}
```

`$HOME` = `/…/homes/alice` → les rapports, préférences et *shots* de l'instance
vont dans `/…/homes/alice/.imasviz/`, pas dans le `$HOME` de la gateway.
C'est l'isolation d'état.

### Remote (la gateway proxy vers une URL)

```python
store.issue('bob', 'remote', url='https://viz.example:8770/')
```

Résultat :

```json
{
  "bob": {
    "token": "…24c",
    "kind":  "remote",
    "home":  null,
    "url":   "https://viz.example:8770/"
  }
}
```

La gateway ne démarrerait rien pour `bob` : tout transite vers l'URL, y
compris le flux SSE de `/api/agent`. La topologie **hybride** est juste une
ligne JSON.

## 4. Brancher un navigateur

Ouvrir `http://127.0.0.1:8760`. Pour que la gateway reconnaisse le user, il
faut lui donner son token. Deux façons :

- **Header** `Authorization: Bearer <token>` (typique pour un script ou une
  API).
- **Cookie** `imasviz_token=<token>` (typique pour un navigateur).

Puis, depuis l'app, tout est transité dans l'ordre : la page, `list_cases`,
`open_case`, le flux `POST /api/agent`, les gestures d'outils.

Exemple en `curl` :

```bash
TOKEN=$(python3 -c "import json,os;print(json.load(open(os.path.expanduser('~/.imasviz/gateway/users.json')))['alice']['token'])")

# 1. List what's open (empty at start)
curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8760/api/tool \
    -X POST -H 'content-type: application/json' \
    -d '{"name":"list_cases","args":{}}'

# 2. Open a case (adjust the URI to the one you mean)
curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8760/api/tool \
    -X POST -H 'content-type: application/json' \
    -d '{"name":"open_case","args":{"uri":"imas:hdf5?path=/…/west/3/54924/0","dd_version":"3.35.0"}}'

# 3. Ask the agent for a line about it
curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8760/api/agent \
    -X POST -H 'content-type: application/json' \
    -d '{"prompt":"How many figures do I have open?"}' \
    --no-buffer
```

## 5. Les refus — comment les lire

Tous viennent **à la fois** de l'application (l'instance `viz_web`) et de la
gateway (catalog / pool). En lisant le texte, tu trouves ce qui t'empêche.

| Code | Motif (extrait du texte) |
|------|--------------------------|
| `401` | `no token` — la route n'a vu ni Bearer ni cookie |
| `401` | `unknown token : « … » is held by none of the N user(s)` — **nomme** le token reçu **et** les users que `users.json` tient |
| `503` | `the pool is full: N instance(s) are live and its budget is M` — arrêter un user, ou monter `--max-users` |
| `500` | le backend a répondu ce qu'il dit — ex. `no shot view` (le cas n'est pas ouvert), `Not enough data loaded` (le cas chargé n'a pas assez de signal pour le choix) |
| `500` | `no open case of the IDS: <name>` ou `no loaded occurrence of it` — le core de **l'instance** le dit, pas la gateway |

Un token d'un user qu'on a oublié dans `users.json` est `unknown` — la gateway
ne le « répare » pas. `UserStore(issue=…)` pour en remettre, pas de `sed` sur
le fichier.

## 6. Diagnostiquer une instance qui ne vient pas

La gateway attend `/api/health` sur l'instance qu'elle démarre et refuse par le
nom le refus qu'elle reçoit. C'est le diagnostic le plus utile : le texte
nomme le **port** et le `HOME` de l'instance, et son **code de sortie** si celle-ci
est morte.

```bash
# Lancer en log verbose (le log de la gateway)
python3 -m viz_gateway --port 8760 --idle-timeout 60 --max-users 2 2>&1 | less

# Depuis un autre terminal, forcer l'issue d'un user local pour lire le refus
TOK=$(python3 -c "import json,os;print(json.load(open(os.path.expanduser('~/.imasviz/gateway/users.json')))['alice']['token'])")
curl -s -H "Authorization: Bearer $TOK" http://127.0.0.1:8760/api/health
```

Causes typiques, toutes nommées dans le texte :

- **le processus enfant ne démarre pas** → `died before it was ready, answered
  N` (N = code de sortie). Causes habituelles : `VIZ_HOME` absent dans
  l'environnement, `VIZ_PRODUCTION` manquant, `IMAS_VERSION` non exporté.
  Revoir la section *Prérequis*.
- **le processus démarre mais ne répond pas** → `did not answer /api/health
  within 90 s`. C'est un `Qt_QPA_PLATFORM` manquant, un backend à
  `127.0.0.1:PORT` qui ne tient pas, ou une dépendance manquante (PySide6,
  starlette, uvicorn, httpx).
- **l'isolation par `HOME` casse l'import** → le child ne voit plus
  `starlette`. Ce `fix(gateway)` corrige en repopulant `PYTHONPATH` depuis
  l'`sys.path` du parent (tous les chemins non sous `HOME` de l'enfant).
- **un user qui revient après un reap** → l'ancienne instance est morte. La
  gateway redémarre une nouvelle, sur un nouveau port. L'ancienne session
  (cas, figures, sélection) **n'est pas restaurée** : c'est l'effet voulu
  d'une re-apparition de user après idle. Voir *Limites et v2* ci-dessous.

## 7. Les limits de la v1, et la route d'UDS (v2)

Le socket **local** écoute sur `127.0.0.1` : ce loopback est partagé sur la
machine. Un autre compte local peut **techniquement** rejoindre ce port
(danger : un autre compte local peut faire de la proxying pour lui-même).
Le token est un contrôle d'accès au **contenu** — pas au socket.

Fermer ce gap se fait par **Unix Domain Socket** :

- `viz_web/run.py` ajouterait un `--uds /chemin/sock` ; `uvicorn.Config` prend
  l'option `uds=`.
- Le client `httpx` du proxy ferait `httpx.AsyncClient(
  base_url="http+x://gateway", transport=httpx.AsyncHTTPTransport(
  unix_socket="/chemin/sock"))`.
- Le `users.json` d'un user *local* tiendrait le `uds` au lieu du `port`.

Le code du proxy serait inchangé — seul le **transport** entre gateway et
backend changerait, pas les routes. Les refus de pool et de token sont
inchangés.

## 8. Les tests

```bash
# Les 4 fichiers viz_gateway (26 tests, dont 1 vrai) :
python3 -m pytest tests/test_127_gateway_token.py \
                  tests/test_128_gateway_proxy_streams.py \
                  tests/test_129_gateway_pool.py \
                  tests/test_130_gateway_two_real_users_are_isolated.py \
                  -q -p no:cacheprovider
```

La `test_130` est la vrai-épreuve : elle **démarrerait** deux `python3 -m
viz_web` offscreen réels (un par user), et prouerait l'isolation par un cas
que A ouvre et que B ne voit pas.

- `test_127` — le catalog token, refus par le nom.
- `test_128` — le proxy, cont un stub uvicorn réel sur un vrai socket : le
  flux SSE de bout-en-bout.
- `test_129` — le pool : un instance et un port par user, le budget, le
  reaping. Clock injectée, spawn injectée.
- `test_130` — deux vrais `viz_web`, deux `HOME`, un cas ouvert par A, invisible
  à B. `@pytest.mark.case`, skip si l'HLI est manquant.

## 9. FAQ — « comment le dire à un collègue »

**Q : je démarre, ma gateway, ça marche, mais mon collègue ne voit pas ma page.**
A : un token. Vérifier que sa ligne est dans `~/.imasviz/gateway/users.json`,
puis qu'il a bien son token dans le navigateur (header **ou** cookie, l'un
des deux).

**Q : combien de users sur ce node ? **
A : le `--max-users` que vous mettez, mais la **mémoire** est plus serrée.
Chaque user local ≈ 250 Mo. Ce node tient ≈ N users simultanés.

**Q : un user idle, il est killé ? **
A : oui, après `--idle-timeout`. Son process est arrêté, son port libéré, son
budget rendu. Son **token** est toujours valable : la prochaine demande redémarre
une instance derrière — mais l'ancienne session (cas, figures, sélection) est
perdue. Si c'est un problème, le garder actif (un heartbeat `/api/health` de
temps en temps) ou pousser `--idle-timeout`.

**Q : deux users sur la même instance, pour comparer ? **
A : non. Deux users, deux instances, deux `Viz_API` — l'isolation par
processus est le modèle. Pour un *comparatif* (de deux cas dans *une*
fenêtre), c'est le **Stacked Plot View** dans `viz_web`/`viz_gui` d'un seul
user, pas ici.

**Q : une page qui arrive mais un cas qui dit « nothing selected » ? **
A : ce *cas* n'est pas ouvert *dans cette instance*. Vérifier qu'elle est bien
ouverte (l'app elle le dit) — la gateway ne cache pas le refus de l'instance.
