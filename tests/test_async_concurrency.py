"""Integration and concurrency tests for Practice 2 (AsyncIO).

This test suite verifies the core requirements of Practice 2:
1. The server accepts multiple simultaneous client connections.
2. The server handles client requests concurrently.
3. The server continues serving other clients while an operation (e.g. database query)
   is waiting in an asyncio.to_thread worker.
4. Abrupt client disconnections do not crash the server or interrupt other clients.
"""

import asyncio
import json
import time

import pytest
import server


class ServerContext:
    """Manages an active asyncio server instance on an OS-assigned free port."""

    def __init__(self, host: str = "127.0.0.1") -> None:
        self.host = host
        self.port = 0
        self.server = None

    async def __aenter__(self):
        # Port 0 instructs the operating system to allocate an available ephemeral port
        self.server = await asyncio.start_server(server.handle_client, self.host, 0)
        self.port = self.server.sockets[0].getsockname()[1]
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.server:
            self.server.close()
            await self.server.wait_closed()


async def client_ping(host: str, port: int) -> dict:
    """Simple client helper that connects, sends 'ping', and returns the parsed response."""
    reader, writer = await asyncio.open_connection(host, port)
    try:
        request = {"accion": "ping", "datos": {}}
        writer.write(json.dumps(request).encode("utf-8"))
        await writer.drain()
        writer.write_eof()

        response_bytes = await reader.read()
        return json.loads(response_bytes.decode("utf-8"))
    finally:
        writer.close()
        await writer.wait_closed()


def test_server_handles_multiple_concurrent_clients():
    """Verify that multiple clients can connect and receive responses simultaneously."""

    async def main():
        async with ServerContext() as ctx:
            # Launch 5 clients simultaneously using asyncio.gather
            tasks = [client_ping(ctx.host, ctx.port) for _ in range(5)]
            responses = await asyncio.gather(*tasks)

            assert len(responses) == 5
            for resp in responses:
                assert resp["status"] == "ok"
                assert resp["message"] == "Connection successful."

    asyncio.run(main())


def test_server_continues_serving_during_slow_database_task(monkeypatch):
    """Verify that a slow DB task running in asyncio.to_thread does not freeze the event loop.

    A slow request and a fast 'ping' request are started at the same time.
    The fast 'ping' request should complete well before the slow request finishes.
    """

    def slow_processor(action, data, repo, session):
        time.sleep(0.2)  # Simulate a 200ms blocking database query in worker thread
        return {"status": "ok", "message": "Slow operation finished", "data": None}

    # Register slow_processor in ACTION_HANDLERS
    monkeypatch.setitem(
        server.ACTION_HANDLERS,
        "slow_action",
        ("role", slow_processor),
    )

    async def slow_client(host: str, port: int) -> tuple[str, float]:
        start = time.perf_counter()
        reader, writer = await asyncio.open_connection(host, port)
        try:
            request = {"accion": "slow_action", "datos": {}}
            writer.write(json.dumps(request).encode("utf-8"))
            await writer.drain()
            writer.write_eof()

            data = await reader.read()
            elapsed = time.perf_counter() - start
            return json.loads(data.decode("utf-8"))["message"], elapsed
        finally:
            writer.close()
            await writer.wait_closed()

    async def fast_client(host: str, port: int) -> tuple[str, float]:
        # Small delay to ensure slow_client is dispatched first
        await asyncio.sleep(0.02)
        start = time.perf_counter()
        resp = await client_ping(host, port)
        elapsed = time.perf_counter() - start
        return resp["message"], elapsed

    async def main():
        async with ServerContext() as ctx:
            slow_task = asyncio.create_task(slow_client(ctx.host, ctx.port))
            fast_task = asyncio.create_task(fast_client(ctx.host, ctx.port))

            (slow_msg, slow_elapsed), (fast_msg, fast_elapsed) = await asyncio.gather(
                slow_task, fast_task
            )

            assert slow_msg == "Slow operation finished"
            assert fast_msg == "Connection successful."

            # The fast client must finish much faster than the slow client
            assert fast_elapsed < slow_elapsed
            assert fast_elapsed < 0.15  # Fast client was not blocked by 200ms sleep

    asyncio.run(main())


def test_client_abrupt_disconnect_does_not_crash_server():
    """Verify that an abrupt client disconnect does not prevent other clients from being served."""

    async def abrupt_client(host: str, port: int):
        _, writer = await asyncio.open_connection(host, port)
        # Abruptly close without completing the request
        writer.close()
        await writer.wait_closed()

    async def main():
        async with ServerContext() as ctx:
            # 1. Run abrupt client
            await abrupt_client(ctx.host, ctx.port)

            # 2. Immediately run a normal client to ensure server is still healthy
            resp = await client_ping(ctx.host, ctx.port)
            assert resp["status"] == "ok"
            assert resp["message"] == "Connection successful."

    asyncio.run(main())
