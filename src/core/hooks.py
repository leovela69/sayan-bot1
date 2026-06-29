# -*- coding: utf-8 -*-
"""
HOOKS SYSTEM — Sistema de hooks para personalización estilo Antigravity.

Permite inyectar comportamiento personalizado en puntos clave del pipeline
sin modificar el código base.

Hooks disponibles:
- before_response: antes de generar respuesta
- after_response: después de generar respuesta
- before_tool: antes de ejecutar una tool
- after_tool: después de ejecutar una tool
- on_error: cuando ocurre un error
- on_new_user: cuando un usuario nuevo interactúa
- on_skill_unlock: cuando se desbloquea un skill
- on_evolution: cuando el sistema evoluciona
- on_audit_alert: cuando el auditor detecta cheating
- on_handoff: cuando se genera un handoff
"""
import asyncio
import logging
import time
from typing import Dict, List, Callable, Any, Optional

logger = logging.getLogger("sayan.hooks")


HOOK_POINTS = [
    "before_response",
    "after_response",
    "before_tool",
    "after_tool",
    "on_error",
    "on_new_user",
    "on_skill_unlock",
    "on_evolution",
    "on_audit_alert",
    "on_handoff",
    "on_message",
    "on_command",
    "on_cron_tick",
    "on_agent_spawn",
    "on_agent_death",
]


class Hook:
    """Un hook individual."""

    def __init__(self, name: str, point: str, handler: Callable,
                 priority: int = 0, description: str = ""):
        self.name = name
        self.point = point
        self.handler = handler
        self.priority = priority  # Mayor = se ejecuta primero
        self.description = description
        self.enabled = True
        self.executions = 0
        self.errors = 0
        self.created_at = time.time()

    def to_dict(self) -> Dict:
        return {
            "name": self.name, "point": self.point,
            "priority": self.priority, "description": self.description,
            "enabled": self.enabled, "executions": self.executions,
            "errors": self.errors
        }


class HooksEngine:
    """Motor de hooks para personalización."""

    def __init__(self):
        self.hooks: Dict[str, List[Hook]] = {point: [] for point in HOOK_POINTS}
        self.execution_log: List[Dict] = []

    def register(self, name: str, point: str, handler: Callable,
                 priority: int = 0, description: str = "") -> Hook:
        """Registra un nuevo hook."""
        if point not in HOOK_POINTS:
            raise ValueError(f"Hook point '{point}' no válido. Válidos: {HOOK_POINTS}")

        hook = Hook(name, point, handler, priority, description)
        self.hooks[point].append(hook)
        # Ordenar por prioridad (mayor primero)
        self.hooks[point].sort(key=lambda h: h.priority, reverse=True)
        logger.info(f"Hook registered: {name} → {point} (priority={priority})")
        return hook

    def unregister(self, name: str, point: str = None) -> bool:
        """Elimina un hook por nombre."""
        removed = False
        points = [point] if point else HOOK_POINTS
        for p in points:
            self.hooks[p] = [h for h in self.hooks[p] if h.name != name]
            if len(self.hooks.get(p, [])) != len([h for h in self.hooks.get(p, [])]):
                removed = True
        return removed

    async def trigger(self, point: str, data: Dict = None, **kwargs) -> Dict:
        """
        Dispara todos los hooks de un punto.
        Los hooks pueden modificar 'data' (pipeline de transformación).
        """
        if point not in self.hooks:
            return data or {}

        active_hooks = [h for h in self.hooks[point] if h.enabled]
        if not active_hooks:
            return data or {}

        result_data = data or {}

        for hook in active_hooks:
            try:
                if asyncio.iscoroutinefunction(hook.handler):
                    hook_result = await hook.handler(result_data, **kwargs)
                else:
                    hook_result = hook.handler(result_data, **kwargs)

                # Si el hook devuelve algo, actualiza data
                if hook_result is not None and isinstance(hook_result, dict):
                    result_data.update(hook_result)

                hook.executions += 1

            except Exception as e:
                hook.errors += 1
                logger.error(f"Hook error ({hook.name}@{point}): {e}")

                # Auto-disable si falla mucho
                if hook.errors > 10 and hook.executions > 0:
                    error_rate = hook.errors / (hook.executions + hook.errors)
                    if error_rate > 0.5:
                        hook.enabled = False
                        logger.warning(f"Hook '{hook.name}' auto-disabled (error rate: {error_rate:.0%})")

        # Log
        self.execution_log.append({
            "point": point, "hooks_executed": len(active_hooks),
            "timestamp": time.time()
        })
        if len(self.execution_log) > 200:
            self.execution_log = self.execution_log[-200:]

        return result_data

    def get_hooks(self, point: str = None) -> List[Dict]:
        """Lista hooks registrados."""
        if point:
            return [h.to_dict() for h in self.hooks.get(point, [])]
        all_hooks = []
        for p, hooks in self.hooks.items():
            for h in hooks:
                all_hooks.append(h.to_dict())
        return all_hooks

    def enable(self, name: str) -> bool:
        """Habilita un hook."""
        for hooks in self.hooks.values():
            for h in hooks:
                if h.name == name:
                    h.enabled = True
                    return True
        return False

    def disable(self, name: str) -> bool:
        """Deshabilita un hook."""
        for hooks in self.hooks.values():
            for h in hooks:
                if h.name == name:
                    h.enabled = False
                    return True
        return False

    def get_status(self) -> Dict:
        """Estado del sistema de hooks."""
        return {
            "total_hooks": sum(len(hooks) for hooks in self.hooks.values()),
            "by_point": {p: len(hooks) for p, hooks in self.hooks.items() if hooks},
            "total_executions": sum(h.executions for hooks in self.hooks.values() for h in hooks),
            "total_errors": sum(h.errors for hooks in self.hooks.values() for h in hooks),
            "recent_triggers": self.execution_log[-10:]
        }


# Singleton
hooks = HooksEngine()
