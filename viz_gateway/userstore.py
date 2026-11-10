# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The token to user to backend catalog, and the refusal when a token is unknown.

A user is a name that holds a token and one backend: either `local`, in which
case the pool of this very gateway spawns the instance it isolates by giving it
its own HOME, or `remote`, in which case the name of that backend is an
`https://` URL this gateway reaches by name and spawns nothing. The file is a
plain `users.json`:

    {
      "alice": { "token": "...", "kind": "local",  "home": "..." },
      "bob":   { "token": "...", "kind": "remote", "url": "https://..." }
    }

A token no user holds is refused **by name**: the answer names the token that
came in and every user the file holds, so the caller sees exactly what it does
and does not hold -- the one the code and the manual keep saying rather than a
silence the user has to guess at.
"""

import json
import os
import secrets


class UserStore:
    """The `users.json` of one gateway, and the asks made of it.

    `dirName` is the directory the `users.json` sits in (expanded against
    $HOME for the defaults). A catalog of empty is not a catalogue and it does
    not refuse: an unknown token is a named refusal either way, and the list it
    names is the empty one.
    """

    def __init__(self, dirName):
        self.dirName = os.path.abspath(os.path.expanduser(dirName))
        self.path = os.path.join(self.dirName, 'users.json')

    # ------------------------------------------------------------ read / write

    def load(self):
        """The catalog as a plain dict, or the empty one while it does not exist.

        A file that is not an object (a bare list, a string) is refused by name:
        it is the state of a catalog someone edited by hand and broke, and a
        lookup through it would answer a token for a user it does not hold.
        """
        if not os.path.exists(self.path):
            return {}
        with open(self.path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            raise ValueError(
                'users.json is not an object of users: the file at %s answers '
                '%r.' % (self.path, type(raw).__name__))
        return raw

    def save(self, mapping):
        """Write the catalog back, one file under a directory it creates if absent."""
        os.makedirs(self.dirName, exist_ok=True)
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, indent=2, sort_keys=True, ensure_ascii=False)
            f.write('\n')

    # ------------------------------------------------------------------- asks

    def users(self):
        """The user names the catalog holds, in the order the file spells them."""
        return list(self.load())

    def userCount(self):
        return len(self.load())

    def issue(self, user, kind, home=None, url=None):
        """One user, a fresh token, and the backend it holds, written to disk.

        A `local` user gets a HOME to isolate under (the one this gateway gives
        it: under its own directory, one folder per user) and no URL; a
        `remote` user gets a URL and no HOME. The two are refused by name when
        they are not -- a kind that is not `local` or `remote`, a remote user
        without a URL, a name the catalog already holds. Returns the token.
        """
        if user in self.load():
            raise ValueError(
                'a user by that name is already in the catalog: "%s" -- '
                'rename this one, or drop the existing entry first.' % user)
        if kind not in ('local', 'remote'):
            raise ValueError(
                'a user is either "local" (spawned by this gateway, isolated '
                'by its own HOME) or "remote" (answered by its https URL); %r '
                'is neither.' % kind)
        entry = {'token': secrets.token_urlsafe(24), 'kind': kind}
        if kind == 'local':
            if not home:
                home = os.path.join(self.dirName, 'homes', user)
            entry['home'] = home
            entry['url'] = None
        else:
            if not url:
                raise ValueError(
                    '%s needs its URL: name the https:// endpoint it '
                    'answers.' % user)
            entry['url'] = url
            entry['home'] = None
        mapping = self.load()
        mapping[user] = entry
        self.save(mapping)
        return entry['token']

    def entryFor(self, token):
        """The (user, entry) a token holds, or a named refusal.

        An absent or blank token, and a token no user holds, are both refused
        by name: the first for what it is, the second naming the token that
        came in and every user the catalog holds. A token is a string, and it
        is compared to the file's, never to a different shape.
        """
        if token is None or not str(token).strip():
            raise ValueError(
                'no token: one is named in `Authorization: Bearer <token>` (or '
                'the `imasviz_token` cookie), and this request carried none.')
        token = str(token).strip()
        mapping = self.load()
        for user in sorted(mapping):
            if mapping[user].get('token') == token:
                return user, mapping[user]
        held = ', '.join('"%s"' % one for one in sorted(mapping))
        raise ValueError(
            'unknown token: %r is held by none of the %d user(s) in %s %s.'
            % (token, len(mapping), 'namely ' if mapping else '', held))
