# -*- coding: utf-8 -*-
"""
CORTEX — Razonamiento Profundo en Cadena
Capa 1 (Cerebro) — El pensador.

Funciones:
- Chain-of-Thought: piensa paso a paso antes de actuar
- Descompone problemas complejos en sub-tareas
- Evalúa múltiples opciones antes de decidir
- Conecta conceptos de memoria (pide a ATLAS)
- Genera planes de acción estructurados
- Feedback loop: evalúa si su propia respuesta es buena

Flujo:
  Tarea compleja → CORTEX → piensa (3-5 pasos) → plan → ejecuta o delega
"""
import time
import logging
from src.swarm.base_agent import BaseAgent
from src.swarm.bus.message_bus import Message
from src.core.brain import think

logger = logging.getLogger("sayan.cortex")

CORTEX_SYSTEM = """Eres CORTEX, el módulo de razonamiento profundo del enjambre SAYAN.

Tu método:
1. DESCOMPONER: divide el problema en partes
2. ANALIZAR: evalúa cada parte por separado
3. CONECTAR: busca relaciones entre las partes
4. SINTETIZAR: genera una solución unificada
5. VALIDAR: verifica si la solución es coherente

REGLAS:
- Piensa SIEMPRE en cadena (paso 1, paso 2, paso 3...)
- Si no tienes info suficiente, pide a ATLAS (memoria) o ORÁCULO (observar)
- Nunca respondas con lo primero que se te ocurra — evalúa al menos 2 opciones
- Prioriza soluciones que usen POCOS recursos para ALTO impacto
- Si la tarea es demasiado grande, divídela en sub-tareas para otros agentes

FORMATO DE RESPUESTA:
---PENSAMIENTO---
[tu cadena de razonamiento]
---DECISIÓN---
[qué hacer]
---ACCIÓN---
[instrucciones exactas o delegación]
"""


class Cortex(BaseAgent):
    """Razonamiento profundo — piensa antes de actuar."""

    def __init__(self):
        super().__init__("CORTEX", layer=1, role="Razonamiento Profundo")
        self.thoughts_log = []

    async def process_message(self, message: Message):
        action = message.action

        if action == "execute_task":
            return await self._deep_think(message.payload)
        elif action == "evaluate":
            return await self._evaluate(message.payload)
        elif action == "plan":
            return await self._create_plan(message.payload)
        elif action == "report_status":
            return self.status()

    async def _deep_think(self, payload: dict) -> dict:
        """Razonamiento en cadena sobre una tarea."""
        task = payload.get("task", "")
        context = payload.get("context", "")

        # Paso 1: Pensar profundamente
        prompt = f"""{CORTEX_SYSTEM}

TAREA: {task}
CONTEXTO: {context}

Piensa paso a paso y genera tu respuesta."""

        result = await think([{"role": "user", "content": prompt}])
        thought = result.get("content", "")

        # Guardar pensamiento
        self.thoughts_log.append({
            "task": task[:100],
            "thought": thought[:500],
            "timestamp": time.time()
        })
        if len(self.thoughts_log) > 50:
            self.thoughts_log = self.thoughts_log[-50:]

        # Paso 2: Si necesita delegar sub-tareas, enviar a KRONOS
        if "DELEGAR:" in thought.upper() or "SUB-TAREA:" in thought.upper():
            await self.send("KRONOS", "task_request", {
                "task": thought,
                "context": f"Sub-tarea generada por CORTEX para: {task[:50]}"
            })

        return {"thought": thought, "status": "completed"}

    async def _evaluate(self, payload: dict) -> dict:
        """Evalúa una decisión/resultado — ¿fue buena?"""
        what = payload.get("what", "")
        result = payload.get("result", "")

        prompt = f"""Evalúa este resultado:
Objetivo: {what}
Resultado: {result}

¿Es bueno? ¿Se puede mejorar? ¿Qué faltó?
Puntúa de 1 a 10 y explica brevemente."""

        evaluation = await think([{"role": "user", "content": prompt}])
        return {"evaluation": evaluation.get("content", ""), "status": "evaluated"}

    async def _create_plan(self, payload: dict) -> dict:
        """Genera un plan estructurado para un objetivo."""
        goal = payload.get("goal", "")
        constraints = payload.get("constraints", "")

        prompt = f"""Genera un PLAN ESTRUCTURADO para lograr este objetivo:

OBJETIVO: {goal}
RESTRICCIONES: {constraints}

Formato:
1. [paso 1] — agente responsable — tiempo estimado
2. [paso 2] — agente responsable — tiempo estimado
...

Agentes disponibles: KRONOS, CORTEX, GENESIS, ORÁCULO, NEXUS, MIRROR, ATLAS, SENTINEL, DAEMON, FORGE"""

        plan = await think([{"role": "user", "content": prompt}])
        return {"plan": plan.get("content", ""), "status": "planned"}


# Singleton
cortex = Cortex()
