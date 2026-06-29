# -*- coding: utf-8 -*-
"""
SENTINEL — Detección Proactiva
Capa 3 (Ejecutores) — Detecta oportunidades y actúa sin que le pidan.

Funciones:
- Monitorea el estado del enjambre continuamente
- Detecta oportunidades de mejora
- Actúa proactivamente (sugiere tareas a KRONOS)
- Vigila el Panteón via ORÁCULO
- Genera alertas cuando algo no va bien
- Propone acciones preventivas
"""
import time
import logging
from src.swarm.base_agent import BaseAgent
from src.swarm.bus.message_bus import Message, bus

logger = logging.getLogger("sayan.sentinel")


class Sentinel(BaseAgent):
    """Vigía proactivo del enjambre."""

    def __init__(self):
        super().__init__("SENTINEL", layer=3, role="Detección Proactiva")
        self.alerts = []
        self.opportunities = []

    async def process_message(self, message: Message):
        action = message.action
        if action == "execute_task":
            return await self._scan(message.payload)
        elif action == "scan":
            return await self._scan(message.payload)
        elif action == "get_alerts":
            return {"alerts": self.alerts[-20:]}
        elif action == "report_status":
            return self.status()

    async def tick(self):
        """Tick proactivo — escanea el bus buscando problemas."""
        history = bus.get_history(limit=20)
        error_msgs = [m for m in history if "error" in m.get("action", "").lower()]

        if len(error_msgs) >= 3:
            # Muchos errores recientes → alerta
            alert = {
                "type": "high_error_rate",
                "count": len(error_msgs),
                "timestamp": time.time(),
                "msg": f"{len(error_msgs)} errores en últimos 20 mensajes"
            }
            self.alerts.append(alert)
            await self.send("KRONOS", "error_report", {
                "error": alert, "source": "SENTINEL proactive scan"
            })

    async def _scan(self, payload: dict) -> dict:
        """Escaneo manual del sistema."""
        target = payload.get("target", "swarm")

        # Revisar pendientes del bus
        pending = {name: bus.get_pending_count(name) for name in bus._queues}
        overloaded = [name for name, count in pending.items() if count > 10]

        if overloaded:
            opp = {
                "type": "overloaded_agents",
                "agents": overloaded,
                "timestamp": time.time(),
                "suggestion": "FORGE debería crear sirvientes para ayudar"
            }
            self.opportunities.append(opp)
            await self.send("KRONOS", "task_request", {
                "task": f"Agentes sobrecargados: {overloaded}. Sugerir FORGE.",
                "context": "Detectado por SENTINEL"
            })

        return {
            "scanned": True,
            "overloaded": overloaded,
            "alerts_total": len(self.alerts),
            "pending_queues": pending
        }


sentinel = Sentinel()
