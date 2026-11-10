# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""One loopback port per spawned instance, chosen by the kernel.

The port is asked of the kernel by binding `0` and reading back the one it
handed out -- never counted out of a reserved range, so there is no collision
and no bookkeeping to keep in sync. The socket is closed before it is returned,
so the answer is a number, not a live descriptor: the caller binds that number
itself (or passes it to the child).
"""

import socket


def freePort(host='127.0.0.1'):
    """A port `host` will take right now that nobody else holds.

    A port a caller later does not reach -- because the child did not bind it
    in time -- is a named refusal at the caller, not a port collision here.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, 0))
        return sock.getsockname()[1]
