"""Tests for the autouse outbound-network guard in ``conftest.py``.

The guard is the reason a unit test can no longer stall on a real HTTPS
request (CI run 30755522961). It only pays for itself if it keeps blocking
what leaves the machine and keeps allowing what does not, so both halves are
pinned here -- a guard that quietly starts rejecting loopback would break the
tests that stand up a local relay / OAuth-callback server.
"""

from __future__ import annotations

import socket
import threading
from contextlib import contextmanager

import anyio
import pytest
from conftest import OutboundNetworkBlocked, _is_local_host


@contextmanager
def _listener():
    """A loopback listener that accepts one connection and closes it."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)

    def _accept() -> None:
        try:
            conn, _ = server.accept()
            conn.close()
        except OSError:
            pass

    thread = threading.Thread(target=_accept, daemon=True)
    thread.start()
    try:
        yield server.getsockname()[1]
    finally:
        server.close()
        thread.join(timeout=5)


class TestBlocksOutbound:
    def test_getaddrinfo_of_a_remote_name_is_blocked(self):
        with pytest.raises(OutboundNetworkBlocked) as exc:
            socket.getaddrinfo("api.jina.ai", 443)
        assert "api.jina.ai" in str(exc.value)

    def test_connect_to_a_remote_address_is_blocked(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            with pytest.raises(OutboundNetworkBlocked) as exc:
                sock.connect(("140.82.121.4", 443))
        assert "140.82.121.4" in str(exc.value)

    def test_message_names_the_host_and_how_to_fix_it(self):
        with pytest.raises(OutboundNetworkBlocked) as exc:
            socket.getaddrinfo("oauth2.googleapis.com", 443)
        message = str(exc.value)
        assert "oauth2.googleapis.com:443" in message
        assert "patch(" in message
        assert "integration" in message


class TestAllowsLoopback:
    @pytest.mark.parametrize(
        "host",
        [
            "127.0.0.1",
            "127.0.0.53",
            "::1",
            "localhost",
            b"127.0.0.1",
            b"localhost",
            None,
            "",
        ],
    )
    def test_local_hosts_classify_as_local(self, host):
        assert _is_local_host(host) is True

    @pytest.mark.parametrize("host", ["api.jina.ai", "8.8.8.8", b"api.jina.ai"])
    def test_remote_hosts_classify_as_remote(self, host):
        assert _is_local_host(host) is False

    def test_sync_connect_to_loopback_succeeds(self):
        with _listener() as port:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(("127.0.0.1", port))

    async def test_async_connect_to_loopback_succeeds(self):
        """anyio ASCII-encodes a hostname before resolving it.

        ``str(b"localhost")`` is ``"b'localhost'"``, so a guard that stringifies
        instead of decoding blocks every async loopback client that connects by
        name -- which is what httpx and the relay tests do -- while still
        looking correct against the IP literals above.
        """
        with _listener() as port:
            stream = await anyio.connect_tcp("localhost", port)
            await stream.aclose()
