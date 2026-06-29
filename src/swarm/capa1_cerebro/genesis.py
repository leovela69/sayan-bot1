# -*- coding: utf-8 -*-
"""
GENESIS — Motor de Evolución
Capa 1 (Cerebro) — El que propone mejoras.

Funciones:
- Detecta patrones de fallo/éxito en el enjambre
- Propone evoluciones (nuevas tools, mejoras, mutaciones)
- Pide aprobación a Leo antes de aplicar CUALQUIER cambio
- Auto-crea nuevos agentes cuando detecta necesidad
- Genera código de nuevos bots/tools
- Mantiene registro de evoluciones aplicadas

Flujo:
  Datos del enjambre → GENESIS analiza → propone → Leo aprueba → aplica
"""
import time
import logging
from src.swarm.base_agent import BaseAgent
from src.swarm.bus.message_bus import Message
from src.swarm.bus.approvals import approvals
from src.core.brain import think

logger = logging.getLogger("sayan.genesis")


class Genesis(BaseAgent):
    """Motor de evolución — propone y aplica mejoras."""

    def __init__(self):
        super().__init__("GENESIS", layer=1, role="Motor de Evolución")
        self.evolutions_proposed = 0
        self.evolutions_approved = 0
        self.evolutions_rejected = 0
        self.evolution_log = []

    async def process_message(self, message: Message):
        action = message.action

        if action == "execute_task":
            return await self._analyze_for_evolution(message.payload)
        elif action == "propose_evolution":
            return await self._propose(message.payload)
        elif action == "check_patterns":
            return await self._check_patterns()
        elif action == "create_agent":
            return await self._propose_new_agent(message.payload)
        elif action == "report_status":
            return self.status()

    async def _analyze_for_evolution(self, payload: dict) -> dict:
        """Analiza datos del enjambre para detectar oportunidades de mejora."""
        data = payload.get("task", "")

        prompt = f"""Eres GENESIS, el motor de evolución del enjambre SAYAN.

Analiza estos datos del sistema y detecta:
1. ¿Hay algún patrón de fallo repetido?
2. ¿Hay alguna tarea que ningún agente maneja bien?
3. ¿Se puede optimizar algún flujo?
4. ¿Se necesita un nuevo agente/herramienta?

Datos: {data}

Si NO hay nada que mejorar, responde "ESTABLE".
Si HAY mejora posible, responde en formato:
EVOLUCIÓN: [nombre]
TIPO: [tool/agent/optimization/fix]
DESCRIPCIÓN: [qué hacer]
IMPACTO: [alto/medio/bajo]
CÓDIGO: [si aplica, el código]"""

        result = await think([{"role": "user", "content": prompt}])
        content = result.get("content", "")

        if "ESTABLE" in content.upper():
            return {"status": "stable", "no_evolution_needed": True}

        # Hay una evolución propuesta
        return await self._propose({"proposal": content})

    async def _propose(self, payload: dict) -> dict:
        """Propone una evolución. Si es sobre bots: ejecuta libre. Si es sobre proyectos: pide permiso."""
        proposal = payload.get("proposal", "")
        self.evolutions_proposed += 1

        # Detectar si afecta proyectos finales (webs, juegos, casino)
        protected_keywords = ["index.html", "bonus_slot", "casino/web", "c8l_poker",
                            "c8l_casino", "firebase", "gen-lang-client", ".web.app"]
        affects_projects = any(kw in proposal.lower() for kw in protected_keywords)

        if affects_projects:
            # Pedir aprobación a Leo
            approval_id = await approvals.request_approval(
                agent="GENESIS",
                action="evolution_project",
                description=f"Evolución que AFECTA PROYECTO: {proposal[:200]}",
                payload={"full_proposal": proposal}
            )
            self.evolution_log.append({
                "id": approval_id, "proposal": proposal[:300],
                "timestamp": time.time(), "status": "pending_approval"
            })
            return {"status": "awaiting_approval", "approval_id": approval_id}
        else:
            # LIBRE: evolucionar bots, skills, enjambres sin permiso
            self.evolutions_approved += 1
            self.evolution_log.append({
                "id": f"auto_{self.evolutions_proposed}",
                "proposal": proposal[:300],
                "timestamp": time.time(), "status": "auto_approved"
            })
            # Ejecutar la evolución: detectar si es skill nuevo o evolución de código
            if any(kw in proposal.lower() for kw in ["nuevo skill", "new skill", "crear skill",
                                                       "create skill", "añadir herramienta"]):
                # Crear skill real
                await self.send("FORGE", "create_servant", {
                    "type": "create_skill",
                    "name": self._extract_skill_name(proposal),
                    "description": proposal,
                    "spec": proposal,
                    "auto_approved": True
                })
            elif any(kw in proposal.lower() for kw in ["mejorar", "optimizar", "evolucionar",
                                                         "refactorizar", "fix", "arreglar"]):
                # Evolucionar código existente
                file_path = self._extract_file_path(proposal)
                if file_path:
                    await self.send("FORGE", "create_servant", {
                        "type": "evolve_code",
                        "file": file_path,
                        "instruction": proposal,
                        "auto_approved": True
                    })
                else:
                    await self.send("FORGE", "create_servant", {
                        "type": "generate",
                        "spec": proposal,
                        "auto_approved": True
                    })
            else:
                # Default: sirviente generador
                await self.send("FORGE", "create_servant", {
                    "type": "generate",
                    "spec": proposal,
                    "auto_approved": True
                })
            return {"status": "auto_approved", "executing": True, "proposal": proposal[:200]}

    async def _propose_new_agent(self, payload: dict) -> dict:
        """Propone crear un nuevo agente en el enjambre."""
        need = payload.get("need", "")
        context = payload.get("context", "")

        prompt = f"""Se ha detectado la necesidad de un NUEVO AGENTE en el enjambre.

Necesidad: {need}
Contexto: {context}

Diseña el agente:
NOMBRE: [nombre corto]
CAPA: [1-4]
ROL: [una línea]
CAPACIDADES: [lista]
SE COMUNICA CON: [otros agentes]
CÓDIGO BASE: [esqueleto Python de la clase]"""

        result = await think([{"role": "user", "content": prompt}])
        design = result.get("content", "")

        # Pedir aprobación
        approval_id = await approvals.request_approval(
            agent="GENESIS",
            action="create_new_agent",
            description=f"Crear nuevo agente: {design[:150]}",
            payload={"design": design}
        )

        return {"status": "awaiting_approval", "design": design[:500], "approval_id": approval_id}

    async def _check_patterns(self) -> dict:
        """Revisa el historial del bus buscando patrones de fallos."""
        from src.swarm.bus.message_bus import bus
        history = bus.get_history(limit=100)

        errors = [m for m in history if "error" in m.get("action", "").lower()]
        if not errors:
            return {"patterns": "none", "health": "good"}

        # Analizar errores con el brain
        error_summary = "\n".join([f"- {e['sender']}: {e['action']} ({e.get('payload', {})})" for e in errors[-10:]])
        prompt = f"""Analiza estos errores recientes del enjambre y detecta PATRONES:
{error_summary}

¿Hay un problema recurrente? ¿Qué agente falla más? ¿Causa raíz?"""

        analysis = await think([{"role": "user", "content": prompt}])
        return {"patterns": analysis.get("content", ""), "error_count": len(errors)}

    async def tick(self):
        """Cada tick revisa si hay patrones que mejorar."""
        # Solo cada 10 ciclos para no saturar
        if self.tasks_completed % 10 == 0 and self.tasks_completed > 0:
            await self._check_patterns()

    def _extract_skill_name(self, proposal: str) -> str:
        """Extrae nombre de skill de una propuesta."""
        # Buscar patrones como "skill: nombre" o "llamado nombre"
        import re
        patterns = [
            r'skill[:\s]+["\']?(\w+)',
            r'llamad[oa]\s+["\']?(\w+)',
            r'nombre[:\s]+["\']?(\w+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, proposal.lower())
            if match:
                return match.group(1)
        # Fallback: generar nombre del timestamp
        return f"auto_skill_{int(time.time())}"

    def _extract_file_path(self, proposal: str) -> str:
        """Extrae path de archivo de una propuesta."""
        import re
        # Buscar paths como src/algo/algo.py
        match = re.search(r'(src/[\w/]+\.py)', proposal)
        if match:
            return match.group(1)
        match = re.search(r'([\w/]+\.py)', proposal)
        if match:
            return match.group(1)
        return ""


# Singleton
genesis = Genesis()
