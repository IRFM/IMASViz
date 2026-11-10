# `viz_gateway` — IMASViz à plusieurs users à la fois

La couche multi-utilisateur d'IMASViz. Elle **entoure** les instances
`viz_web` existantes pour qu'elles répondent *plus d'un user à la fois*, sans
les modifier : `imasviz/`, `viz_web/`, `viz_cli/` et `mcp_server/` ne bougent
pas.

## Pour quoi ça sert

Aujourd'hui une instance `viz_web` répond **un** user : une `QApplication`,
une `QVizMainWindow` offscreen, une `Viz_API`, et un `QVizDBEntryRegistry`
global au processus. Deux users dans le même processus seraient deux souris sur
le même écran — avec les cas de l'un visibles de l'autre.

`viz_gateway` pose le modèle inverse : **une instance par user**, chacune
isolée par son processus et son `HOME`. La gateway elle-même n'a **aucun**
widget : c'est un proxy HTTP et un superviseur de processus.

| User  | Backend            | Isolation                                        |
|-------|--------------------|--------------------------------------------------|
| local | `python3 -m viz_web` lancé ici, sur `127.0.0.1:<port>` | un `HOME` → un `$HOME/.imasviz`, une `Viz_API` |
| remote| une `https://` URL enregistrée                            | le backend a son process et sa config ailleurs   |

## Comment on l'utilise

1. **Lancer la gateway.** Depuis un shell qui a *déjà* `module load`é la pile
   HLI (les enfants héritent cet environnement et ne changent que `HOME`) :

   ```bash
   module load IMAS-Python/2.3.0-…        # la pile que le user utilise
   export VIZ_HOME=$PWD
   export VIZ_PRODUCTION=1
   python3 -m viz_gateway --port 8760 --max-users 20 --idle-timeout 1800
   ```

2. **Inscrire un user** (le token est généré et son backend choisi).
   Le fichier `~/.imasviz/gateway/users.json` tient la table
   (`token → user → backend`). L'inscription peut être scriptée :

   ```python
   from viz_gateway.userstore import UserStore
   UserStore('~/.imasviz/gateway').issue(
       'alice', 'local')                                # → son token
   UserStore('~/.imasviz/gateway').issue(
       'bob', 'remote', url='https://viz.example:8770') # → son token
   ```

3. **Pointer le navigateur** sur `http://127.0.0.1:8760` avec le token du
   user (header `Authorization: Bearer <token>` ou cookie `imasviz_token`),
   et tout le reste est transité : la page, `/api/agent` (le flux SSE arrive
   comme il est écrit), et `/api/tool` (les gestures raw).

## Les refus sont nommés

* **pas de token** → `401` : « no token : … »
* **token inconnu**  → `401` : « unknown token : « … » is held by none of the
  N user(s) in … » (on nomme le token reçu **et** les users que le fichier tient)
* **pool plein**     → `503` : « the pool is full : N instance(s) are live and
  its budget is M »
* **instance qui ne vient pas** → `ValueError` nommant son port, son `HOME`,
  et (si elle est morte) son code de sortie

## Le budget

`--max-users` (défaut 20) est le nombre d'instances **vivantes** au maximum,
et `--idle-timeout` (défaut 1800 s) le temps d'inactivité avant qu'une
instance soit reaped (son port libéré, son budget rendu). Le token reste
valable : la prochaine demande redémarre une instance derrière, sans que le
caller le sache.

Le vrai coût par user est le **processus Qt** (≈ 150–300 Mo + un thread Qt) —
**pas** le port. Sur un node, c'est la mémoire qui limite le nombre de
users simultanés, bien avant l'épuisement des ports (≈ 35 k disponibles).

## La limite multi-comptes (et la route d'UDS)

En v1, les backends locaux écoutent sur `127.0.0.1:<port>` : un autre **compte
local** sur la même machine peut techniquement joindre ce port (le loopback est
partagé). C'est la limite connue de la v1 — le token est un contrôle d'accès au
*contenu*, pas au *socket*.

La route d'UDS (v2) ferme ce gap : chaque backend local écoute sur un
**socket Unix** isolé par ses permissions (le client `httpx` y pointe, le port
disparaît). C'est une option à brancher : `viz_web/run.py` ajouterait un
`--uds PATH`, et le client httpx du proxy ferait `transport=AsyncHTTPTransport
(unix_socket=…)`. Le token y répondrait de la même façon.

## Les dépendances

`starlette` (le proxy), `uvicorn` (le loop d'événements du proxy et du
superviseur), `httpx` (le proxy lui-même) — toutes trois déjà importables
ici. La Qt et l'IMAS HLI sont dans les **processus fils**, pas dans la gateway
: le pool les porte, un par user.

## Tests

* `tests/test_127_gateway_token.py` — le catalogue des users, le refus du
  token par le nom.
* `tests/test_128_gateway_proxy_streams.py` — le proxy, contre un vrai
  backend stub uvicorn sur un vrai socket : le flux SSE, le refus des deux
  formes de token.
* `tests/test_129_gateway_pool.py` — le pool : un instance et un port par
  user, le budget, le reaping.
* `tests/test_130_gateway_two_real_users_are_isolated.py` (`@pytest.mark.case`)
  — **deux vraies** instances `viz_web` lancées par le spawner réel,
  l'une qui ouvre le cas de référence, l'autre qui ne le voit pas.
