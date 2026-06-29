# -*- coding: utf-8 -*-
"""
ORÁCULO — Observador del Panteón
Capa 2 (Puentes) — Extrae conocimiento del otro enjambre.

Funciones:
- Lee logs/memoria del Panteón (c8l-bot-server)
- Extrae patrones de éxito/fallo
- Reporta hallazgos a NEXUS para distribución
- Detecta cuándo el Panteón necesita ayuda
- Alimenta a MIRROR con habilidades a replicar
"""
import time
import logging
from src.swarm.base_agent import BaseAgent
from src.swarm.bus.message_bus import Message
from src.core.brain import think

logger = logging.getLogger("sayan.oraculo")


class Oraculo(BaseAgent):
    """Observa al Panteón y extrae conocimiento."""

    def __init__(self):
        super().__init__("ORACULO", layer=2, role="Observador del Panteón")
        self.observations = []
        self.panteon_status = {}

    async def process_message(self, message: Message):
        action = message.action
        if action == "execute_task":
            return await self._observe(message.payload)
        elif action == "observe_panteon":
            return await self._observe(message.payload)
        elif action == "get_observations":
            return {"observations": self.observations[-20:]}
        elif action == "report_status":
            return self.status()

    async def _observe(self, payload: dict) -> dict:
        """Observa un aspecto del Panteón y extrae conocimiento."""
        target = payload.get("target", "general")
        data = payload.get("data", "")

        prompt = f"""Eres ORÁCULO. Observas al Panteón (otro enjambre de bots) y extraes conocimiento útil.

Observando: {target}
Datos: {data}

Extrae:
1. ¿Qué hace bien este sistema?
2. ¿Qué falla o es ineficiente?
3. ¿Qué habilidad podemos copiar/mejorar?
4. ¿Necesita ayuda de nuestro enjambre?

Sé conciso y práctico."""

        result = await think([{"role": "user", "content": prompt}])
        observation = result.get("content", "")

        self.observations.append({
            "target": target,
            "observation": observation[:300],
            "timestamp": time.time()
        })
        if len(self.observations) > 100:
            self.observations = self.observations[-100:]

        # Si detecta que necesita ayuda, avisar a KRONOS
        if "necesita ayuda" in observation.lower() or "falla" in observation.lower():
            await self.send("KRONOS", "task_request", {
                "task": f"Panteón necesita asistencia: {observation[:150]}",
                "context": "Detectado por ORÁCULO"
            })

        # Enviar a NEXUS para distribución
        await self.send("NEXUS", "new_knowledge", {
            "source": "panteon",
            "knowledge": observation[:300],
            "type": "observation"
        })

        return {"observation": observation, "status": "observed"}


oraculo = Oraculo()
