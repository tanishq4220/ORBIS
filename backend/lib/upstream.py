"""Bounded public-only requests with DNS pinning and original TLS SNI."""
import asyncio
import ipaddress
import json
import socket
import ssl
from urllib.parse import urlsplit

import httpcore
from fastapi import HTTPException


async def validate_origin(raw: str) -> tuple[str, str]:
    try:
        p = urlsplit(raw.strip())
        if p.scheme not in {"http", "https"} or not p.hostname or p.username or p.password:
            raise ValueError("Use a credential-free HTTP or HTTPS URL")
        if p.path.rstrip("/") not in {"", "/api"} or p.query or p.fragment:
            raise ValueError("Use the backend origin, optionally ending in /api")
        port = p.port or (443 if p.scheme == "https" else 80)
        if port not in {80, 443}:
            raise ValueError("Public backend must use port 80 or 443; expose local servers through a tunnel")
        host = p.hostname.rstrip(".").encode("idna").decode()
        records = await asyncio.wait_for(asyncio.to_thread(socket.getaddrinfo, host, port, 0, socket.SOCK_STREAM), 5)
        ips = {ipaddress.ip_address(r[4][0]) for r in records}
        if not ips or any(not ip.is_global or ip.is_multicast or ip.is_reserved for ip in ips):
            raise ValueError("Private, loopback and reserved addresses are not allowed. Use the hosted local mode or a public tunnel.")
        ip = sorted(ips, key=lambda i: (i.version, str(i)))[0]
        authority = f"[{host}]" if ":" in host else host
        return f"{p.scheme}://{authority}:{port}", str(ip)
    except (ValueError, OSError, TimeoutError) as exc:
        raise HTTPException(422, str(exc) or "Invalid backend origin") from exc


class PinnedBackend(httpcore.AsyncNetworkBackend):
    def __init__(self, ip: str):
        self.ip = ip
        self.inner = httpcore.AnyIOBackend()

    async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        return await self.inner.connect_tcp(self.ip, port, timeout, local_address, socket_options)


async def public_request(url: str, method: str, path: str, query: str = "", body: bytes = b"") -> tuple[int, bytes]:
    origin, ip = await validate_origin(url)
    if len(body) > 16384 or len(query) > 4096:
        raise HTTPException(413, "Request too large")
    target = f"{origin}/api/{path}" + (f"?{query}" if query else "")
    headers = {"Accept": "application/json", "Content-Type": "application/json", "ngrok-skip-browser-warning": "orbis"}
    try:
        async with asyncio.timeout(90):
            async with httpcore.AsyncConnectionPool(ssl_context=ssl.create_default_context(),
                    network_backend=PinnedBackend(ip), max_connections=2, retries=0) as pool:
                async with pool.stream(method, target, headers=headers, content=body or None,
                    extensions={"timeout": {"connect": 8, "read": 80, "write": 10, "pool": 5}}) as response:
                    if 300 <= response.status < 400:
                        raise HTTPException(502, "Backend redirect rejected; enter its final public URL")
                    chunks, size = [], 0
                    async for chunk in response.aiter_stream():
                        size += len(chunk)
                        if size > 16 * 1024 * 1024:
                            raise HTTPException(502, "Backend response exceeds 16 MB")
                        chunks.append(chunk)
                    payload = b"".join(chunks)
                    json.loads(payload)
                    return response.status, payload
    except (httpcore.NetworkError, httpcore.TimeoutException, httpcore.ProtocolError, TimeoutError, ValueError) as exc:
        raise HTTPException(502, "BACKEND OFFLINE — public ORBIS API unavailable or returned invalid JSON") from exc