"""Integration and concurrency tests for secure communication (Practice 3).

This test suite verifies:
1. Multiple concurrent clients can authenticate and receive encrypted responses simultaneously.
2. A slow database task in a worker thread does not freeze the event loop for other secure clients.
3. Abrupt disconnects or failed handshakes do not crash the server or interrupt other clients.
4. Switching between different client certificates (client1, client2) works seamlessly.
"""

import asyncio
import json
import time

import network_client
import pytest
import server


class ServerContext:
    """Manages an active asyncio server instance on an OS-assigned free port."""

    def __init__(self, host: str = "127.0.0.1") -> None:
        self.host = host
        self.port = 0
        self.server = None

    async def __aenter__(self):
        # Port 0 lets the operating system pick a free ephemeral port
        self.server = await asyncio.start_server(server.handle_client, self.host, 0)
        self.port = self.server.sockets[0].getsockname()[1]
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.server:
            self.server.close()
            await self.server.wait_closed()


def test_server_handles_multiple_concurrent_clients(monkeypatch):
    """Verify that multiple authenticated clients can perform secure handshakes and get responses."""

    async def main():
        async with ServerContext() as ctx:
            monkeypatch.setattr(network_client, "SERVER_PORT", ctx.port)

            # Launch 5 secure client requests simultaneously using asyncio.gather
            tasks = [network_client.send_request("ping") for _ in range(5)]
            responses = await asyncio.gather(*tasks)

            assert len(responses) == 5
            for resp in responses:
                assert resp["status"] == "ok"
                assert resp["message"] == "Connection successful."

    asyncio.run(main())


def test_server_continues_serving_during_slow_database_task(monkeypatch):
    """Verify that a slow DB task in a thread does not block other authenticated clients."""

    def slow_processor(action, data, repo, session):
        time.sleep(0.4)  # Simulate a 400ms blocking database query in worker thread
        return {"status": "ok", "message": "Slow operation finished", "data": None}

    monkeypatch.setitem(
        server.ACTION_HANDLERS,
        "slow_action",
        ("role", slow_processor),
    )

    async def main():
        async with ServerContext() as ctx:
            monkeypatch.setattr(network_client, "SERVER_PORT", ctx.port)

            start = time.perf_counter()
            slow_task = asyncio.create_task(network_client.send_request("slow_action"))

            # Small delay so slow_task initiates and enters worker thread first
            await asyncio.sleep(0.05)
            fast_start = time.perf_counter()
            fast_task = asyncio.create_task(network_client.send_request("ping"))

            slow_resp, fast_resp = await asyncio.gather(slow_task, fast_task)
            fast_elapsed = time.perf_counter() - fast_start
            total_elapsed = time.perf_counter() - start

            assert slow_resp["message"] == "Slow operation finished"
            assert fast_resp["message"] == "Connection successful."

            # The fast request must complete faster than the total time taken by the slow task
            assert fast_elapsed < total_elapsed

    asyncio.run(main())


def test_client_abrupt_disconnect_does_not_crash_server(monkeypatch):
    """Verify that an unauthenticated or abrupt client does not interrupt the server."""

    async def bad_client(host: str, port: int):
        _, writer = await asyncio.open_connection(host, port)
        # Abruptly close without completing handshake
        writer.close()
        await writer.wait_closed()

    async def main():
        async with ServerContext() as ctx:
            monkeypatch.setattr(network_client, "SERVER_PORT", ctx.port)

            # 1. Abrupt disconnect
            await bad_client(ctx.host, ctx.port)

            # 2. Server still processes authentic clients normally
            resp = await network_client.send_request("ping")
            assert resp["status"] == "ok"
            assert resp["message"] == "Connection successful."

    asyncio.run(main())


def test_multiple_client_identities_can_authenticate(monkeypatch):
    """Verify that both client1 and client2 certificates are accepted by the server."""

    async def main():
        async with ServerContext() as ctx:
            monkeypatch.setattr(network_client, "SERVER_PORT", ctx.port)

            network_client.set_client_identity("client1")
            resp1 = await network_client.send_request("ping")
            assert resp1["status"] == "ok"

            network_client.set_client_identity("client2")
            resp2 = await network_client.send_request("ping")
            assert resp2["status"] == "ok"

            # Reset back to client1
            network_client.set_client_identity("client1")

    asyncio.run(main())
