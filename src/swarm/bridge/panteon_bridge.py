# -*- coding: utf-8 -*-
"""
PANTEON BRIDGE — Conexión real con el Panteón (c8l-bot-server)
Permite comunicación bidireccional entre enjambres.

MODO: HTTP API
- Sayan tiene un endpoint /api/bridge/receive (recibe datos del Panteón)
- Sayan llama al endpoint del Panteón para enviar datos
- Ambos se autentican con un BRIDGE_SECRET compartido

Si no hay conexión directa (no están en el mismo servidor):
- Usa GitHub como intermediario (lee/escribe archivos en un repo compartido)
- O Firebase Realtime DB como canal de mensajes
"""
import os
import json
import time
import logging
import httpx
from config.settings import DATA_DIR

logger = logging.getLogger("sayan.bridge")

# Configuración del puente
BRIDGE_SECRET = os.environ.get("BRIDGE_SECRET", "c8l_sayan_bridge_2026")
PANTEON_URL = os.environ.get("PANTEON_API_URL", "")  # URL del Panteón en Render

# Archivo local para mensajes pendientes (si no hay conexión directa)
BRIDGE_INBOX = os.path.join(DATA_DIR, "bridge_inbox.json")
BRIDGE_OUTBOX = os.path.join(DATA_DIR, "bridge_outbox.json")


class PanteonBridge:
    """Puente de comunicación con el Panteón."""

    def __init__(self):
        self.connected = False
        self.messages_sent = 0
        self.messages_received = 0
        self.last_sync = 0

    async def send_to_panteon(self, message_type: str, data: dict) -> dict:
        """Envía datos al Panteón."""
        payload = {
            "from": "sayan",
            "type": message_type,
            "data": data,
            "timestamp": time.time(),
            "secret": BRIDGE_SECRET
        }

        # Si hay URL del Panteón, enviar por HTTP
        if PANTEON_URL:
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.post(
                        f"{PANTEON_URL}/api/bridge/receive",
                        json=payload
                    )
                    if resp.status_code == 200:
                        self.messages_sent += 1
                        self.connected = True
                        return {"sent": True, "response": resp.json()}
            except Exception as e:
                logger.warning(f"HTTP bridge failed: {e}")
                self.connected = False

        # Fallback: guardar en outbox local
        outbox = self._load_file(BRIDGE_OUTBOX)
        outbox.append(payload)
        if len(outbox) > 100:
            outbox = outbox[-100:]
        self._save_file(BRIDGE_OUTBOX, outbox)
        self.messages_sent += 1

        return {"sent": True, "method": "outbox", "pending": len(outbox)}

    def receive_from_panteon(self, payload: dict) -> dict:
        """Recibe datos del Panteón (llamado por el endpoint HTTP)."""
        # Verificar secreto
        if payload.get("secret") != BRIDGE_SECRET:
            return {"error": "unauthorized"}

        # Guardar en inbox
        inbox = self._load_file(BRIDGE_INBOX)
        inbox.append({
            "type": payload.get("type", "unknown"),
            "data": payload.get("data", {}),
            "timestamp": time.time(),
            "from": payload.get("from", "panteon")
        })
        if len(inbox) > 100:
            inbox = inbox[-100:]
        self._save_file(BRIDGE_INBOX, inbox)
        self.messages_received += 1
        self.last_sync = time.time()
        self.connected = True

        return {"received": True, "inbox_size": len(inbox)}

    def get_inbox(self, limit: int = 10) -> list:
        """Lee mensajes recibidos del Panteón."""
        inbox = self._load_file(BRIDGE_INBOX)
        return inbox[-limit:]

    def clear_inbox(self):
        """Limpia inbox después de procesar."""
        self._save_file(BRIDGE_INBOX, [])

    def get_outbox(self, limit: int = 10) -> list:
        """Lee mensajes pendientes de enviar."""
        outbox = self._load_file(BRIDGE_OUTBOX)
        return outbox[-limit:]

    def status(self) -> dict:
        return {
            "connected": self.connected,
            "panteon_url": PANTEON_URL or "(no configurada)",
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "last_sync": self.last_sync,
            "inbox_size": len(self._load_file(BRIDGE_INBOX)),
            "outbox_size": len(self._load_file(BRIDGE_OUTBOX))
        }

    def _load_file(self, path: str) -> list:
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except:
                return []
        return []

    def _save_file(self, path: str, data: list):
        with open(path, "w") as f:
            json.dump(data, f, ensure_ascii=False)


# Singleton
bridge = PanteonBridge()
