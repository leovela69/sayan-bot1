# -*- coding: utf-8 -*-
"""
API SERVER — Endpoint HTTP para recibir datos del Panteón.
Corre en paralelo con el bot de Telegram.
"""
import asyncio
import json
import logging
from aiohttp import web
from config.settings import PORT
from src.swarm.bridge.panteon_bridge import bridge

logger = logging.getLogger("sayan.api")


async def handle_bridge_receive(request):
    """POST /api/bridge/receive — Recibe datos del Panteón."""
    try:
        payload = await request.json()
        result = bridge.receive_from_panteon(payload)

        # Notificar al enjambre que llegó data del Panteón
        from src.swarm.bus.message_bus import bus, Message
        msg = Message("BRIDGE", "NEXUS", "sync_from_panteon", {
            "data": json.dumps(payload.get("data", {}))
        })
        await bus.publish(msg)

        return web.json_response(result)
    except Exception as e:
        logger.error(f"Bridge receive error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def handle_bridge_status(request):
    """GET /api/bridge/status — Estado del puente."""
    return web.json_response(bridge.status())


async def handle_swarm_status(request):
    """GET /api/swarm/status — Estado del enjambre."""
    from src.swarm.circuit import get_circuit_status
    return web.json_response(get_circuit_status())


async def handle_health(request):
    """GET /health — Health check para Render."""
    return web.json_response({"status": "alive", "bot": "sayan"})


async def start_api_server():
    """Arranca el servidor HTTP."""
    app = web.Application()
    app.router.add_post("/api/bridge/receive", handle_bridge_receive)
    app.router.add_get("/api/bridge/status", handle_bridge_status)
    app.router.add_get("/api/swarm/status", handle_swarm_status)
    app.router.add_get("/health", handle_health)
    app.router.add_get("/", handle_health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"API Server running on port {PORT}")
    return runner
