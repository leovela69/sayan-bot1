# -*- coding: utf-8 -*-
"""
TRAINER — Sistema de entrenamiento y evolución del Panteón.
Sayan puede LIBREMENTE:
- Añadir skills/tools a cualquier agente del Panteón
- Crear bots nuevos para el Panteón
- Modificar código de agentes del Panteón
- Mejorar prompts, lógica, flujos

NO puede (requiere permiso de Leo):
- Tocar webs (index.html, bonus_slot.html, etc.)
- Modificar juegos (casino, kukis, chess)
- Cambiar configuración de deploy
- Tocar la web de Firebase

MECANISMO:
Sayan genera código → lo envía al Panteón via bridge →
El Panteón lo aplica en caliente (hot-reload) o lo guarda para
el próximo reinicio.
"""
import time
import logging
from src.core.brain import think
from src.swarm.bridge.panteon_bridge import bridge

logger = logging.getLogger("sayan.trainer")


class PanteonTrainer:
    """Entrena y evoluciona los bots del Panteón."""

    def __init__(self):
        self.evolutions_applied = 0
        self.skills_added = 0
        self.bots_created = 0
        self.history = []

    async def add_skill_to_agent(self, agent_name: str, skill_description: str) -> dict:
        """Genera y envía un nuevo skill a un agente del Panteón."""

        # Generar el código del skill
        prompt = f"""Genera un SKILL COMPLETO en Python para el agente {agent_name} del Panteón C8L.

Descripción del skill: {skill_description}

El Panteón usa esta arquitectura:
- Cada agente tiene un SYSTEM_PROMPT y una función process()
- Los skills son funciones async que reciben (user_message, context) y devuelven str
- Usan openrouter_client.call_openrouter() para LLM
- Archivos van en pantheon/slaves/ o pantheon/skills/

Genera SOLO el código Python. Sin explicaciones. Listo para guardar como archivo."""

        result = await think([{"role": "user", "content": prompt}])
        code = result.get("content", "")

        if not code or len(code) < 50:
            return {"success": False, "error": "No pude generar el skill"}

        # Enviar al Panteón via bridge
        response = await bridge.send_to_panteon("add_skill", {
            "agent": agent_name,
            "skill_name": skill_description[:50].replace(" ", "_").lower(),
            "code": code,
            "description": skill_description
        })

        self.skills_added += 1
        self._log("add_skill", agent_name, skill_description)

        return {"success": True, "agent": agent_name, "skill": skill_description[:50], "response": response}

    async def improve_agent(self, agent_name: str, improvement: str) -> dict:
        """Mejora un agente existente del Panteón (prompt, lógica, etc.)."""

        prompt = f"""Genera una MEJORA para el agente {agent_name} del Panteón C8L.

Mejora solicitada: {improvement}

Genera:
1. Qué archivo modificar (ruta relativa desde raíz del repo)
2. El código o prompt mejorado
3. Instrucciones de aplicación

SOLO el resultado práctico. Sin explicaciones innecesarias."""

        result = await think([{"role": "user", "content": prompt}])
        improvement_code = result.get("content", "")

        response = await bridge.send_to_panteon("improve_agent", {
            "agent": agent_name,
            "improvement": improvement,
            "code": improvement_code
        })

        self.evolutions_applied += 1
        self._log("improve", agent_name, improvement)

        return {"success": True, "agent": agent_name, "improvement": improvement[:50], "response": response}

    async def create_bot_for_panteon(self, bot_name: str, role: str, capabilities: list) -> dict:
        """Crea un bot NUEVO completo para añadir al Panteón."""

        prompt = f"""Crea un BOT COMPLETO nuevo para el Panteón C8L.

Nombre: {bot_name}
Rol: {role}
Capacidades: {', '.join(capabilities)}

El Panteón usa esta estructura para bots esclavos:
- Archivo: pantheon/slaves/{bot_name.lower()}.py
- Clase con métodos: __init__, process(user_message, context)
- SYSTEM_PROMPT detallado con personalidad y skills
- Usa openrouter_client.call_openrouter() para LLM
- Debe registrarse en pantheon/zeus.py (lista de agentes)

Genera el archivo Python COMPLETO. Sin explicaciones."""

        result = await think([{"role": "user", "content": prompt}])
        code = result.get("content", "")

        response = await bridge.send_to_panteon("create_bot", {
            "bot_name": bot_name,
            "role": role,
            "capabilities": capabilities,
            "code": code
        })

        self.bots_created += 1
        self._log("create_bot", bot_name, role)

        return {"success": True, "bot": bot_name, "role": role, "response": response}

    async def train_self(self, skill_description: str) -> dict:
        """Sayan se entrena a sí mismo — genera nueva tool para su propio enjambre."""

        prompt = f"""Genera una nueva TOOL para el enjambre Sayan.

Descripción: {skill_description}

Formato del archivo (src/tools/builtin/nombre.py):

async def mi_funcion(param1: str) -> str:
    '''Hace algo.'''
    return "resultado"

def register_tools(registry):
    registry.register(
        name="mi_funcion",
        description="...",
        parameters={{...}},
        handler=mi_funcion
    )

Genera SOLO el código Python completo."""

        result = await think([{"role": "user", "content": prompt}])
        code = result.get("content", "")

        # Guardar como archivo local
        import os
        skill_name = skill_description[:30].replace(" ", "_").lower()
        skill_path = os.path.join("src", "tools", "builtin", f"auto_{skill_name}.py")

        try:
            with open(skill_path, "w") as f:
                f.write(code)
            self._log("self_train", "SAYAN", skill_description)
            return {"success": True, "skill": skill_name, "path": skill_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def status(self) -> dict:
        return {
            "evolutions_applied": self.evolutions_applied,
            "skills_added": self.skills_added,
            "bots_created": self.bots_created,
            "history_count": len(self.history),
            "last_5": self.history[-5:] if self.history else []
        }

    def _log(self, action: str, target: str, description: str):
        self.history.append({
            "action": action,
            "target": target,
            "description": description[:200],
            "timestamp": time.time()
        })
        if len(self.history) > 200:
            self.history = self.history[-200:]


# Singleton
trainer = PanteonTrainer()
