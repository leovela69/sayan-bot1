# -*- coding: utf-8 -*-
"""
KRONOS — Coordinador Supremo del Enjambre Sayan
Capa 1 (Cerebro) — Nodo central.

Funciones:
- Recibe TODA solicitud y decide quién la ejecuta
- Monitorea salud de todos los agentes (heartbeat)
- Detecta fallos y ordena reparación
- Coordina flujo entre capas (1→2→3→4)
- Reporta estado a Leo bajo demanda
- Escala tareas: si un agente no puede, pasa al siguiente

Flujo:
  Mensaje → KRONOS → analiza → delega → monitorea → reporta
"""
import time
import logging
import asyncio
from src.swarm.base_agent import BaseAgent
from src.swarm.bus.message_bus import bus, Message
from src.core.brain import think

logger = logging.getLogger("sayan.kronos")


class Kronos(BaseAgent):
    """El coordinador supremo del enjambre."""

    def __init__(self):
        super().__init__("KRONOS", layer=1, role="Coordinador Supremo")
        self.agents_status = {}
        self.cycle_count = 0
        self.last_cycle = time.time()

    async def process_message(self, message: Message):
        """Procesa mensajes dirigidos a Kronos."""
        action = message.action

        if action == "status_report":
            # Un agente reporta su estado
            self.agents_status[message.sender] = message.payload
            return {"ok": True}

        elif action == "task_request":
            # Alguien pide que se ejecute una tarea
            return await self._delegate_task(message)

        elif action == "error_report":
            # Un agente reporta un error
            return await self._handle_error(message)

        elif action == "health_check":
            return self._get_swarm_health()

        elif action == "cycle":
            # Ciclo periódico de coordinación
            return await self._run_cycle()

    async def _delegate_task(self, message: Message):
        """Analiza una tarea y la delega al agente correcto."""
        task = message.payload.get("task", "")
        context = message.payload.get("context", "")

        # Usar el brain para decidir a quién delegar
        decision_prompt = f"""Tarea recibida: {task}
Contexto: {context}
Agentes disponibles y sus roles:
- CORTEX: razonamiento profundo, análisis complejo
- GENESIS: proponer evoluciones y mejoras
- ORACULO: observar al Panteón, extraer datos
- NEXUS: conectar enjambres, transferir datos
- MIRROR: replicar habilidades del Panteón
- ATLAS: memoria infinita, buscar en historial
- SENTINEL: detección proactiva, oportunidades
- DAEMON: tareas programadas, cron
- FORGE: crear sirvientes para tareas pesadas

¿A quién debo delegar esta tarea? Responde SOLO el nombre del agente."""

        result = await think([{"role": "user", "content": decision_prompt}])
        target_agent = result.get("content", "CORTEX").strip().upper()

        # Validar que el agente existe
        valid_agents = ["CORTEX", "GENESIS", "ORACULO", "NEXUS", "MIRROR",
                       "ATLAS", "SENTINEL", "DAEMON", "FORGE"]
        if target_agent not in valid_agents:
            target_agent = "CORTEX"  # fallback

        # Delegar
        await self.send(target_agent, "execute_task", {
            "task": task,
            "context": context,
            "delegated_by": "KRONOS",
            "original_sender": message.sender
        })

        self.logger.info(f"Task delegated to {target_agent}: {task[:50]}")
        return {"delegated_to": target_agent}

    async def _handle_error(self, message: Message):
        """Maneja errores reportados por agentes."""
        error_agent = message.sender
        error_info = message.payload

        self.logger.warning(f"Error from {error_agent}: {error_info}")

        # Ordenar a FORGE crear un sirviente reparador
        await self.send("FORGE", "create_servant", {
            "type": "repair",
            "target_agent": error_agent,
            "error": error_info,
            "priority": "high"
        })

        return {"action": "repair_ordered", "target": error_agent}

    async def _run_cycle(self):
        """Ciclo de coordinación — se ejecuta cada N segundos."""
        self.cycle_count += 1
        self.last_cycle = time.time()

        # 1. Pedir estado a todos
        await self.broadcast("report_status", {"cycle": self.cycle_count})

        # 2. Verificar agentes muertos
        dead_agents = []
        for name, status in self.agents_status.items():
            if time.time() - status.get("last_heartbeat", 0) > 300:  # 5 min sin responder
                dead_agents.append(name)

        # 3. Intentar reactivar muertos
        for dead in dead_agents:
            await self.send("FORGE", "create_servant", {
                "type": "revive",
                "target_agent": dead,
                "priority": "critical"
            })

        return {
            "cycle": self.cycle_count,
            "agents_alive": len(self.agents_status) - len(dead_agents),
            "agents_dead": dead_agents
        }

    def _get_swarm_health(self) -> dict:
        """Estado de salud del enjambre completo."""
        return {
            "coordinator": "KRONOS",
            "cycle_count": self.cycle_count,
            "last_cycle": self.last_cycle,
            "agents": self.agents_status,
            "bus_history_size": len(bus._history),
            "overall_status": "healthy" if not any(
                time.time() - s.get("last_heartbeat", 0) > 300
                for s in self.agents_status.values()
            ) else "degraded"
        }


# Singleton
kronos = Kronos()
