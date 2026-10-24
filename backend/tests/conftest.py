"""
Shared pytest setup for the backend.

RIBIF depends on paid services (Gemini/Vertex, Serper, Bing, Supabase,
Presenton, SMTP/IMAP). The suite must never reach them, so every socket
connection or DNS lookup outside localhost raises instead of going out.
Service-dependent code is tested by mocking its single client function.
"""

import socket
import sys
from pathlib import Path

import dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Modules call load_dotenv() at import; never let the suite read real keys
dotenv.load_dotenv = lambda *args, **kwargs: False

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
_real_connect = socket.socket.connect
_real_getaddrinfo = socket.getaddrinfo


class NetworkBlocked(OSError):
    pass


def _guarded_connect(self, address):
    if isinstance(address, tuple) and address[0] not in LOCAL_HOSTS:
        raise NetworkBlocked(f"tests may not open network connections: {address}")
    return _real_connect(self, address)


def _guarded_getaddrinfo(host, *args, **kwargs):
    if host is not None and host not in LOCAL_HOSTS:
        raise NetworkBlocked(f"tests may not resolve external hosts: {host}")
    return _real_getaddrinfo(host, *args, **kwargs)


socket.socket.connect = _guarded_connect
socket.getaddrinfo = _guarded_getaddrinfo
