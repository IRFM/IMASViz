# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""One line at a time, with the arrows -- without readline.

The C module behind the standard library's `readline` is not built in
this node's Python (measured: `readline` is the pure-Python fallback
with no `_rl` behind it, so there is no arrows, no history file and no
completion to ask of it). The line editor the client needs is instead
a small one on `termios` and `select`:

* printable input in UTF-8, backspace and delete;
* left and right, home and end (`Ctrl+A` / `Ctrl+E` as well);
* up and down on the `History` the client holds, the walk surviving
  from one line to the next the way the shell's does: up walks the
  entries from the newest to the oldest (and keeps the oldest), down
  gives back the line the walk left and leaves the walk;
* tab completion for the one candidate that holds the line's prefix;
* `Ctrl+C` the `KeyboardInterrupt` the rest of the stack already
  handles; `Ctrl+D` on an empty line the leave, on a line a delete at
  the cursor, the way the shells do it;
* on a stdin that is not a terminal -- a scripted run, a pipe -- plain
  `input` takes the line instead, and nothing here is in the way.

What the editor draws is one clear, one write, one optional cursor step
back, so a redraw leaves no half line behind; a stdout that is not a
terminal (the test's stand-in) keeps the same text, the escapes in it
harmless there.
"""

import os
import select
import sys

try:
    import termios
    import tty
except ImportError:           # a node without termios: the fallback stands
    termios = None
    tty = None


# The history walk, held the way the shell holds its own: it survives
# from one `readLine` to the next, so an up arrow on the line after the
# one that walked keeps walking where the walk was. `hidx` is the
# entry the walk stands on (`len - 1` the newest, `0` the oldest),
# `saving` the line the walk left behind, which a down arrow gives back.
_WALK = {'hidx': None, 'saving': None}


def _stdinFd():
    """The file descriptor the line is read from.

    `sys.stdin` is the object a wrapper or a test's stand-in points it
    at; when it gives no descriptor -- a test's stand-in answers
    exactly that -- the terminal the process's own fd 0 is pointed at
    stands in, which is where `os.dup2` and the terminals put one.
    """
    try:
        return sys.stdin.fileno()
    except (OSError, ValueError, AttributeError):
        return 0


def _usableTerminal():
    try:
        fd = _stdinFd()
        if termios is None or not os.isatty(fd):
            return False
        termios.tcgetattr(fd)
        return True
    except (OSError, ValueError, TypeError):
        return False


def _decodeChunk(pending, chunk):
    """The complete characters the bytes hold, and the bytes not yet done.

    One French character is three bytes and a read may split it: the old
    tail plus the new bytes are cut at the last complete character, and
    the rest stays pending. A byte no code point holds is dropped,
    because it is not a line either.
    """
    data = pending + chunk
    for cut in range(len(data), 0, -1):
        try:
            return data[:cut].decode('utf-8'), data[cut:]
        except UnicodeDecodeError:
            continue
    return '', b''


def _move(buf, pos, delta):
    return max(0, min(pos + delta, len(buf)))


def _render(prompt, buf, pos, out):
    text = ''.join(buf)
    out.write('\r\x1b[2K')
    out.write(prompt + text)
    if pos < len(text):
        out.write('\x1b[%dD' % (len(text) - pos))
    try:
        out.flush()
    except (OSError, ValueError):
        pass


_TERMINAL_CODES = ('A', 'B', 'C', 'D', 'F', 'H')


def _escapeFromRest(rest):
    """The arrow code the characters after an ESC spell, and how many of
    them it took. A bare ESC takes none and changes nothing.

    One read commonly holds an arrow's whole sequence behind the ESC it
    began with, so the sequence is parsed out of the characters already
    read, and only an ESC left alone in the read asks the terminal for
    the rest -- which is why the two helpers sit next to each other."""
    if len(rest) >= 2 and rest[0] == '[':
        second = rest[1]
        if second.isdigit() and len(rest) >= 3 and rest[2] == '~':
            return '\x1b[' + second + '~', 3
        if second in _TERMINAL_CODES:
            return '\x1b[' + second, 2
    if len(rest) >= 2 and rest[0] == 'O' and rest[1] in _TERMINAL_CODES:
        return '\x1bO' + rest[1], 2
    return '\x1b', 0


def _escapeFromFd(fd, head):
    """An ESC with no characters left in the read: the terminal may still
    be spelling its arrow. Ask for the rest, with a silence of 30 ms for
    the answer that no rest is on its way -- a bare ESC then."""
    keys = head
    for _ in range(3):
        ready, _, _ = select.select([fd], [], [], 0.03)
        if not ready:
            break
        byte = os.read(fd, 1)
        if not byte:
            break
        keys += byte.decode('ascii', 'ignore')
        if keys.endswith(_TERMINAL_CODES + ('~',)):
            break
    return keys


def readLine(prompt, history=None, candidates=None):
    """One line from the keyboard, edited the way a shell edits its own.

    Returns the line, `None` for the leave (`Ctrl+D` on an empty line,
    or an end-of-file on the pipe), and raises `KeyboardInterrupt` for
    `Ctrl+C`. `history` is the `History` the up and down arrows walk;
    `candidates` the word list tab completes against."""
    if not _usableTerminal():
        try:
            return input(prompt)
        except EOFError:
            return None

    fd = _stdinFd()
    out = sys.stdout
    old = termios.tcgetattr(fd)
    # The history walk the shell holds, across the lines: up from the
    # current line keeps walking where the last readLine left it, and
    # only a new line the user edits resets it to what it holds.
    state = {'buf': [], 'pos': 0,
             'saving': _WALK['saving'], 'hidx': _WALK['hidx']}
    pending = b''
    # What the line discipline already held for this fd: the mode change
    # to raw below takes the canonical line buffer with it, so the bytes
    # are pulled out first (a prompt the user typed in advance; the test
    # that puts its keys on the pty before the call). Zero cost in the
    # usual case, where nothing is queued.
    priming = ''
    ready, _, _ = select.select([fd], [], [], 0.0)
    if ready:
        priming, _ = _decodeChunk(b'', os.read(fd, 4096))
    try:
        tty.setraw(fd)
        while True:
            _render(prompt, state['buf'], state['pos'], out)
            if priming:
                text = priming
                priming = ''
            else:
                ready, _, _ = select.select([fd], [], [], None)
                chunk = os.read(fd, 64) if ready else b''
                if not chunk:
                    return None
                text, pending = _decodeChunk(pending, chunk)
            chars = list(text)
            idx = 0
            while idx < len(chars):
                char = chars[idx]
                if ord(char) == 0x1B:
                    rest = ''.join(chars[idx + 1:])
                    if rest:
                        key, used = _escapeFromRest(rest)
                        idx += 1 + used
                    else:
                        key = _escapeFromFd(fd, '\x1b')
                    _escapeKey(key, state, history)
                    continue
                _key(char, state, candidates)
                idx += 1
                if state.pop('left', False):
                    out.write('\n')
                    return None
                if state.pop('done', False):
                    out.write('\n')
                    return ''.join(state['buf'])
    finally:
        # The walk is the line editor's, not the call's: whatever the
        # line that ends here stood on, the next one starts there.
        _WALK['hidx'] = state['hidx']
        _WALK['saving'] = state['saving']
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _key(char, state, candidates):
    """One simple key, on the state the line editor holds."""
    buf, pos = state['buf'], state['pos']
    code = ord(char)
    if code in (0x03, 0x02):
        raise KeyboardInterrupt
    if code == 0x04:                         # Ctrl+D: delete, or leave
        if buf:
            del buf[pos]
            state['pos'] = min(pos, len(buf))
        else:
            state['left'] = True
            state['done'] = True
            state['pos'] = 0
        return
    if code in (0x0A, 0x0D):
        state['done'] = True
        return
    if code in (0x7F, 0x08):                 # Backspace
        if pos > 0:
            del buf[pos - 1]
            state['pos'] = pos - 1
        return
    if code == 0x01:                         # Ctrl+A: home
        state['pos'] = 0
        return
    if code == 0x05:                         # Ctrl+E: end
        state['pos'] = len(buf)
        return
    if code == 0x09:                         # Tab: the one completion it holds
        if candidates:
            line = ''.join(buf)
            hold = [c for c in candidates if c.startswith(line)]
            if len(hold) == 1:
                state['buf'] = list(hold[0])
                state['pos'] = len(state['buf'])
        return
    if code < 0x20:
        return                               # another control: it is not a line
    buf.insert(pos, char)
    state['pos'] = pos + 1


def _escapeKey(key, state, history):
    """The arrow and home/end codes, on the state the editor holds.

    The codes a terminal no one here spells -- a bare ESC among them --
    are answered by doing nothing, which is the answer the line gives."""
    buf, pos = state['buf'], state['pos']
    entries = history.entries if history is not None else []
    hidx = state['hidx']

    if key == '\x1b[A' and entries:
        if hidx is None:
            state['saving'] = ''.join(buf)
            hidx = len(entries) - 1
        elif hidx > 0:
            hidx -= 1
        state['buf'] = list(entries[hidx])
        state['pos'] = len(state['buf'])
        state['hidx'] = hidx
        return

    if key == '\x1b[B':
        if hidx is None:
            return                   # already on the saved line: it holds
        # Down leaves the walk: the line the one that began it stood on
        # is the current one again, wherever the walk is.
        state['hidx'] = None
        state['buf'] = list(state['saving'] or '')
        state['pos'] = len(state['buf'])
        return

    if key == '\x1b[C':
        state['pos'] = _move(buf, pos, 1)
        return
    if key == '\x1b[D':
        state['pos'] = _move(buf, pos, -1)
        return
    if key in ('\x1b[H', '\x1b[1~', '\x1b[7~'):
        state['pos'] = 0
        return
    if key in ('\x1b[F', '\x1b[4~', '\x1b[8~'):
        state['pos'] = len(buf)
        return
    if key == '\x1b[3~':                     # Delete at the cursor
        if buf:
            del state['buf'][pos]
        return
