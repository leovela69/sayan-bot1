# -*- coding: utf-8 -*-
"""
NEXUS — Puente Bidireccional Entre Enjambres
Capa 2 (Puentes) — Conecta Sayan con Panteón.

Funciones:
- Distribuye conocimiento entre ambos enjambres
- Sincroniza datos de forma bidireccional
- Traduce formatos (Panteón usa su propio esquema)
- Mantiene un registro de qué se compartió
- Evita duplicados y loops de datos
"""
import time
import logging
from src.swarm.base_agent import BaseAgent
from src.swarm.bus.message_bus import Message

logger = logging.getLogger("sayan.nexus")


class Nexus(BaseAgent):
    """Puente de datos entre enjambres."""

    def __init__(self):
        super().__init__("NEXUS", layer=2, role="Puente Bidireccional")
        self.shared_knowledge = []
        self.sync_count = 0

    async def process_message(self, message: Message):
        action = message.action
        if action == "new_knowledge":
            return await self._distribute(message.payload)
        elif action == "sync_to_panteon":
            return await self._sync_to_panteon(message.payload)
        elif action == "sync_from_panteon":
            return await self._sync_from_panteon(message.payload)
        elif action == "execute_task":
            return await self._distribute(message.payload)
        elif action == "report_status":
            return self.status()

    async def _distribute(self, payload: dict) -> dict:
        """Distribuye conocimiento a los agentes apropiados."""
        knowledge = payload.get("knowledge", "")
        source = payload.get("source", "unknown")
        ktype = payload.get("type", "general")

        self.shared_knowledge.append({
            "source": source, "type": ktype,
            "content": knowledge[:300], "timestamp": time.time()
        })
        if len(self.shared_knowledge) > 200:
            self.shared_knowledge = self.shared_knowledge[-200:]
        self.sync_count += 1

        # Distribuir según tipo
        if ktype == "observation":
            await self.send("MIRROR", "learn_skill", {"skill_data": knowledge, "source": source})
            await self.send("ATLAS", "store", {"data": knowledge, "category": "panteon_observation"})
        elif ktype == "error":
            await self.send("KRONOS", "error_report", {"error": knowledge, "source": source})
        elif ktype == "evolution":
            await self.send("GENESIS", "propose_evolution", {"proposal": knowledge})

        return {"distributed": True, "sync_count": self.sync_count}

    async def _sync_to_panteon(self, payload: dict) -> dict:
        """Envía datos de Sayan al Panteón (requiere API/webhook del Panteón)."""
        # TODO: Implementar webhook al Panteón cuando esté configurado
        data = payload.get("data", "")
        logger.info(f"Sync to Panteón: {data[:100]}")
        return {"synced": True, "direction": "sayan→panteon"}

    async def _sync_from_panteon(self, payload: dict) -> dict:
        """Recibe datos del Panteón y los distribuye internamente."""
        data = payload.get("data", "")
        await self._distribute({"knowledge": data, "source": "panteon", "type": "sync"})
        return {"synced": True, "direction": "panteon→sayan"}


nexus = Nexus()
