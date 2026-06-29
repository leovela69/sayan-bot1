# -*- coding: utf-8 -*-
"""
MIRROR — Replicador de Habilidades
Capa 2 (Puentes) — Aprende del Panteón y copia sus mejores skills.

Funciones:
- Recibe datos de ORÁCULO/NEXUS sobre qué hace bien el Panteón
- Genera versiones mejoradas de esas habilidades
- Las registra como nuevas tools en el enjambre Sayan
- Mantiene un catálogo de skills replicados
- Evalúa si la copia es mejor que el original
"""
import time
import logging
from src.swarm.base_agent import BaseAgent
from src.swarm.bus.message_bus import Message
from src.core.brain import think

logger = logging.getLogger("sayan.mirror")


class Mirror(BaseAgent):
    """Replica y mejora habilidades del Panteón."""

    def __init__(self):
        super().__init__("MIRROR", layer=2, role="Replicador de Skills")
        self.skills_replicated = []
        self.skills_catalog = []

    async def process_message(self, message: Message):
        action = message.action
        if action == "learn_skill":
            return await self._learn(message.payload)
        elif action == "execute_task":
            return await self._learn(message.payload)
        elif action == "list_skills":
            return {"skills": self.skills_catalog}
        elif action == "report_status":
            return self.status()

    async def _learn(self, payload: dict) -> dict:
        """Aprende una habilidad del Panteón y genera versión mejorada."""
        skill_data = payload.get("skill_data", "")
        source = payload.get("source", "panteon")

        prompt = f"""Eres MIRROR. Tu misión es APRENDER habilidades de otros sistemas y crear versiones MEJORADAS.

Habilidad observada del Panteón:
{skill_data}

Tu trabajo:
1. Identifica QUÉ habilidad es (nombre corto)
2. Analiza cómo funciona
3. Genera una versión MEJORADA (más eficiente, menos recursos)
4. Si puedes, genera el código Python de la tool

Formato:
SKILL: [nombre]
MEJORA: [qué mejoraste]
CÓDIGO: [si aplica]"""

        result = await think([{"role": "user", "content": prompt}])
        content = result.get("content", "")

        skill_entry = {
            "source": source,
            "original": skill_data[:200],
            "improved": content[:500],
            "timestamp": time.time()
        }
        self.skills_replicated.append(skill_entry)
        self.skills_catalog.append(content[:200])

        if len(self.skills_replicated) > 50:
            self.skills_replicated = self.skills_replicated[-50:]

        # Si generó código, proponer a GENESIS como evolución
        if "CÓDIGO:" in content.upper() or "def " in content:
            await self.send("GENESIS", "propose_evolution", {
                "proposal": f"Nueva skill replicada del Panteón: {content[:300]}"
            })

        return {"learned": True, "skill": content[:200]}


mirror = Mirror()
