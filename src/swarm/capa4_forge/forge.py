# -*- coding: utf-8 -*-
"""
FORGE — Fábrica de Sirvientes
Capa 4 — Genera micro-agentes de UNA sola tarea.

Los sirvientes:
- Se crean en milisegundos (1 prompt + 1 función)
- Ejecutan su tarea
- Se auto-destruyen al completar
- Usan mínimos recursos (sin memoria, sin estado)
- Pueden reparar fallos del Panteón

Ejemplo:
  KRONOS detecta error → pide a FORGE →
  FORGE crea sirviente_reparador → ejecuta → muere
"""
import time
import asyncio
import logging
from src.swarm.base_agent import BaseAgent
from src.swarm.bus.message_bus import Message
from src.core.brain import think
from src.swarm.bus.approvals import approvals

logger = logging.getLogger("sayan.forge")


class Servant:
    """Micro-agente de una sola tarea. Nace, ejecuta, muere."""

    def __init__(self, servant_id: str, task_type: str, task_data: dict):
        self.id = servant_id
        self.task_type = task_type
        self.task_data = task_data
        self.created_at = time.time()
        self.completed = False
        self.result = None

    async def execute(self) -> dict:
        """Ejecuta la tarea asignada."""
        try:
            if self.task_type == "repair":
                result = await self._repair()
            elif self.task_type == "analyze":
                result = await self._analyze()
            elif self.task_type == "fetch":
                result = await self._fetch()
            elif self.task_type == "generate":
                result = await self._generate()
            elif self.task_type == "revive":
                result = await self._revive()
            else:
                result = await self._generic()

            self.completed = True
            self.result = result
            return {"success": True, "result": result, "servant_id": self.id}
        except Exception as e:
            self.completed = True
            self.result = f"Error: {e}"
            return {"success": False, "error": str(e), "servant_id": self.id}

    async def _repair(self) -> str:
        """Repara un error en otro agente o en el Panteón."""
        error = self.task_data.get("error", {})
        target = self.task_data.get("target_agent", "unknown")

        prompt = f"""Eres un micro-agente reparador. Tu ÚNICA misión es resolver este error:

Agente afectado: {target}
Error: {error}

Genera la solución más eficiente posible. Si necesitas código, genera solo el patch.
Si necesitas reiniciar algo, indica el comando exacto.
Responde SOLO la solución, sin explicaciones."""

        result = await think([{"role": "user", "content": prompt}])
        return result.get("content", "No pude generar solución")

    async def _analyze(self) -> str:
        """Analiza datos/situación."""
        data = self.task_data.get("data", "")
        prompt = f"Analiza esto de forma concisa y extrae lo relevante:\n{data}"
        result = await think([{"role": "user", "content": prompt}])
        return result.get("content", "")

    async def _fetch(self) -> str:
        """Obtiene datos de una fuente."""
        source = self.task_data.get("source", "")
        return f"Fetched from {source}"

    async def _generate(self) -> str:
        """Genera contenido/código."""
        spec = self.task_data.get("spec", "")
        prompt = f"Genera exactamente lo que se pide:\n{spec}"
        result = await think([{"role": "user", "content": prompt}])
        return result.get("content", "")

    async def _revive(self) -> str:
        """Intenta reactivar un agente muerto."""
        target = self.task_data.get("target_agent", "")
        return f"Revive signal sent to {target}"

    async def _generic(self) -> str:
        """Tarea genérica."""
        task = self.task_data.get("task", "")
        prompt = f"Ejecuta esta tarea de la forma más eficiente:\n{task}"
        result = await think([{"role": "user", "content": prompt}])
        return result.get("content", "")


class Forge(BaseAgent):
    """Fábrica de sirvientes — Genera y gestiona micro-agentes."""

    def __init__(self):
        super().__init__("FORGE", layer=4, role="Fábrica de Sirvientes")
        self.servants_created = 0
        self.servants_active = []
        self.servants_completed = []

    async def process_message(self, message: Message):
        """Procesa solicitudes de creación de sirvientes."""
        action = message.action

        if action == "create_servant":
            return await self._create_servant(message.payload)
        elif action == "servant_status":
            return self._get_status()

    async def _create_servant(self, payload: dict) -> dict:
        """Crea un nuevo sirviente y lo ejecuta."""
        task_type = payload.get("type", "generic")
        priority = payload.get("priority", "normal")

        # PERMISOS:
        # - Evolucionar bots (Panteón o Sayan): LIBRE, sin aprobación
        # - Tocar webs/juegos/proyectos finales: REQUIERE aprobación de Leo
        affects_projects = payload.get("affects_projects", False)  # webs, juegos, casino
        
        if affects_projects:
            approval_id = await approvals.request_approval(
                agent="FORGE",
                action=f"modify_project_{payload.get('target', 'unknown')}",
                description=f"Modificar proyecto: {payload.get('description', '')}",
                payload=payload
            )
            return {"status": "awaiting_approval", "approval_id": approval_id}

        # Todo lo demás (evolucionar bots, añadir skills, crear agentes): EJECUTAR LIBRE
        self.servants_created += 1
        servant_id = f"srv_{self.servants_created}_{int(time.time())}"
        servant = Servant(servant_id, task_type, payload)

        self.servants_active.append(servant)
        self.logger.info(f"Servant created (FREE): {servant_id} (type: {task_type})")

        result = await servant.execute()

        self.servants_active.remove(servant)
        self.servants_completed.append({
            "id": servant_id,
            "type": task_type,
            "result": result,
            "duration": time.time() - servant.created_at
        })

        if len(self.servants_completed) > 100:
            self.servants_completed = self.servants_completed[-100:]

        return result

    def _get_status(self) -> dict:
        return {
            "total_created": self.servants_created,
            "active": len(self.servants_active),
            "completed": len(self.servants_completed),
            "last_5": self.servants_completed[-5:] if self.servants_completed else []
        }


# Singleton
forge = Forge()
