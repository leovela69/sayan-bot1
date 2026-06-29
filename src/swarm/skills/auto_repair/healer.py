# -*- coding: utf-8 -*-
"""
AUTO-HEALER v1.0 — Sistema de auto-reparación REAL
Funciona con la infraestructura actual del enjambre.

5 CAPAS:
1. MONITOREO: Detecta fallos en tiempo real
2. DIAGNÓSTICO: Identifica la causa raíz
3. REPARACIÓN: Aplica la solución automática
4. VERIFICACIÓN: Confirma que funciona
5. REGISTRO: Documenta todo para aprendizaje
"""
import os
import sys
import gc
import time
import asyncio
import logging
import json
import traceback
from datetime import datetime
from typing import Dict, List
from enum import Enum

logger = logging.getLogger("sayan.healer")

# ============ CONFIG ============

class HealerConfig:
    CHECK_INTERVAL = 30          # segundos entre chequeos
    MAX_MEMORY_MB = 500          # MB máximo del proceso
    MAX_ERROR_RATE = 5           # errores por minuto antes de actuar
    MAX_RESTART_ATTEMPTS = 3
    COOLDOWN_SECONDS = 60


class RepairAction(Enum):
    NONE = "none"
    CLEAR_MEMORY = "clear_memory"
    RESTART_AGENT = "restart_agent"
    SWITCH_MODEL = "switch_model"
    RECONNECT = "reconnect"
    NOTIFY_OWNER = "notify_owner"


# ============ HEALER ============

class AutoHealer:
    """Sistema de auto-reparación del enjambre Sayan."""

    def __init__(self):
        self.running = False
        self.errors_log: List[Dict] = []
        self.repairs_log: List[Dict] = []
        self.error_count_per_minute = 0
        self.last_error_reset = time.time()
        self.restart_attempts: Dict[str, int] = {}
        self.notify_callback = None

    def set_notify(self, callback):
        """Registra callback para notificar a Leo."""
        self.notify_callback = callback

    async def start(self):
        """Inicia el ciclo de monitoreo."""
        self.running = True
        logger.info("Auto-Healer ONLINE — Monitoreando cada 30s")

        while self.running:
            try:
                await self._check_cycle()
            except Exception as e:
                logger.error(f"Healer cycle error: {e}")
            await asyncio.sleep(HealerConfig.CHECK_INTERVAL)

    async def _check_cycle(self):
        """Un ciclo completo de monitoreo."""
        # 1. MONITOREO
        health = self._check_health()

        # 2. DIAGNÓSTICO
        issues = self._diagnose(health)

        # 3. REPARACIÓN
        for issue in issues:
            action = self._determine_action(issue)
            if action != RepairAction.NONE:
                result = await self._repair(issue, action)
                # 4. VERIFICACIÓN
                verified = self._verify_repair(issue, result)
                # 5. REGISTRO
                self._log_repair(issue, action, result, verified)

        # Reset error counter cada minuto
        if time.time() - self.last_error_reset > 60:
            self.error_count_per_minute = 0
            self.last_error_reset = time.time()

    def _check_health(self) -> Dict:
        """Chequeo de salud del sistema."""
        import resource
        process_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # MB

        health = {
            "timestamp": time.time(),
            "memory_mb": process_memory,
            "error_rate": self.error_count_per_minute,
            "bus_alive": True,
            "brain_alive": True,
            "agents_alive": True,
        }

        # Verificar bus
        try:
            from src.swarm.bus.message_bus import bus
            health["bus_pending"] = sum(q.qsize() for q in bus._queues.values())
            health["bus_alive"] = True
        except Exception:
            health["bus_alive"] = False

        # Verificar brain (LLM)
        try:
            from config.settings import OPENROUTER_API_KEY
            health["brain_alive"] = bool(OPENROUTER_API_KEY)
        except Exception:
            health["brain_alive"] = False

        # Verificar agentes
        try:
            from src.swarm.circuit import ACTIVE_AGENTS
            dead = [n for n, a in ACTIVE_AGENTS.items() if a.errors > 10]
            health["agents_alive"] = len(dead) == 0
            health["dead_agents"] = dead
        except Exception:
            health["agents_alive"] = False

        return health

    def _diagnose(self, health: Dict) -> List[Dict]:
        """Identifica problemas a partir del health check."""
        issues = []

        if health["memory_mb"] > HealerConfig.MAX_MEMORY_MB:
            issues.append({
                "type": "high_memory",
                "severity": "warning",
                "value": health["memory_mb"],
                "threshold": HealerConfig.MAX_MEMORY_MB
            })

        if health["error_rate"] > HealerConfig.MAX_ERROR_RATE:
            issues.append({
                "type": "high_error_rate",
                "severity": "critical",
                "value": health["error_rate"],
                "threshold": HealerConfig.MAX_ERROR_RATE
            })

        if not health["bus_alive"]:
            issues.append({"type": "bus_dead", "severity": "critical"})

        if not health["brain_alive"]:
            issues.append({"type": "brain_dead", "severity": "critical"})

        if not health["agents_alive"]:
            issues.append({
                "type": "agents_dead",
                "severity": "warning",
                "dead": health.get("dead_agents", [])
            })

        if health.get("bus_pending", 0) > 50:
            issues.append({
                "type": "bus_overloaded",
                "severity": "warning",
                "pending": health["bus_pending"]
            })

        return issues

    def _determine_action(self, issue: Dict) -> RepairAction:
        """Decide qué acción tomar."""
        itype = issue["type"]

        if itype == "high_memory":
            return RepairAction.CLEAR_MEMORY
        elif itype == "high_error_rate":
            return RepairAction.NOTIFY_OWNER
        elif itype == "bus_dead":
            return RepairAction.RECONNECT
        elif itype == "brain_dead":
            return RepairAction.SWITCH_MODEL
        elif itype == "agents_dead":
            return RepairAction.RESTART_AGENT
        elif itype == "bus_overloaded":
            return RepairAction.CLEAR_MEMORY

        return RepairAction.NONE

    async def _repair(self, issue: Dict, action: RepairAction) -> Dict:
        """Ejecuta la reparación."""
        logger.info(f"Repairing: {issue['type']} with {action.value}")

        try:
            if action == RepairAction.CLEAR_MEMORY:
                gc.collect()
                return {"success": True, "freed": "garbage collected"}

            elif action == RepairAction.RESTART_AGENT:
                dead = issue.get("dead", [])
                for agent_name in dead:
                    try:
                        from src.swarm.circuit import ACTIVE_AGENTS
                        if agent_name in ACTIVE_AGENTS:
                            ACTIVE_AGENTS[agent_name].errors = 0
                            ACTIVE_AGENTS[agent_name].active = True
                    except Exception:
                        pass
                return {"success": True, "restarted": dead}

            elif action == RepairAction.SWITCH_MODEL:
                from config.settings import LLM_FALLBACK
                os.environ["LLM_MODEL"] = LLM_FALLBACK
                return {"success": True, "switched_to": LLM_FALLBACK}

            elif action == RepairAction.RECONNECT:
                from src.swarm.bus.message_bus import bus
                # Re-init queues
                for name in list(bus._queues.keys()):
                    if bus._queues[name].qsize() > 20:
                        bus._queues[name] = asyncio.Queue()
                return {"success": True, "reconnected": True}

            elif action == RepairAction.NOTIFY_OWNER:
                if self.notify_callback:
                    msg = f"ALERTA: {issue['type']} — {issue.get('value', 'N/A')}"
                    await self.notify_callback(msg)
                return {"success": True, "notified": True}

        except Exception as e:
            return {"success": False, "error": str(e)}

        return {"success": False, "error": "unknown action"}

    def _verify_repair(self, issue: Dict, result: Dict) -> bool:
        """Verifica que la reparación funcionó."""
        if not result.get("success"):
            return False
        # Re-check rápido
        health = self._check_health()
        new_issues = self._diagnose(health)
        return not any(i["type"] == issue["type"] for i in new_issues)

    def _log_repair(self, issue: Dict, action: RepairAction, result: Dict, verified: bool):
        """Registra la reparación para aprendizaje."""
        entry = {
            "timestamp": time.time(),
            "issue": issue,
            "action": action.value,
            "result": result,
            "verified": verified
        }
        self.repairs_log.append(entry)
        if len(self.repairs_log) > 100:
            self.repairs_log = self.repairs_log[-100:]

        level = "INFO" if verified else "WARNING"
        logger.log(
            logging.INFO if verified else logging.WARNING,
            f"Repair: {issue['type']} → {action.value} → {'OK' if verified else 'FAILED'}"
        )

    def report_error(self, error: Exception, context: str = ""):
        """Llamado externamente cuando ocurre un error."""
        self.error_count_per_minute += 1
        self.errors_log.append({
            "error": str(error),
            "traceback": traceback.format_exc(),
            "context": context,
            "timestamp": time.time()
        })
        if len(self.errors_log) > 200:
            self.errors_log = self.errors_log[-200:]

    def get_status(self) -> Dict:
        """Estado actual del healer."""
        return {
            "running": self.running,
            "errors_last_minute": self.error_count_per_minute,
            "total_repairs": len(self.repairs_log),
            "last_5_repairs": self.repairs_log[-5:],
            "health": self._check_health()
        }

    def stop(self):
        self.running = False


# Singleton
healer = AutoHealer()
