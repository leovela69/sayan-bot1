# -*- coding: utf-8 -*-
"""
CRON SYSTEM — Sistema de tareas programadas avanzado estilo Antigravity.

Features:
- Tareas recurrentes con intervalos flexibles
- Fire-and-forget (ejecuta sin bloquear)
- Historial de ejecuciones
- Auto-retry en fallos
- Prioridades
- Cancelación dinámica
"""
import asyncio
import time
import logging
import json
import os
from typing import Dict, List, Callable
from config.settings import DATA_DIR

logger = logging.getLogger("sayan.cron")

CRON_FILE = os.path.join(DATA_DIR, "cron_tasks.json")


class CronTask:
    def __init__(self, name: str, interval: int, handler: Callable = None,
                 description: str = "", priority: str = "normal", max_retries: int = 2):
        self.name = name
        self.interval = interval  # segundos
        self.handler = handler
        self.description = description
        self.priority = priority
        self.max_retries = max_retries
        self.last_run = 0
        self.run_count = 0
        self.fail_count = 0
        self.active = True
        self.last_result = None

    def is_due(self) -> bool:
        return self.active and (time.time() - self.last_run >= self.interval)

    def to_dict(self) -> Dict:
        return {
            "name": self.name, "interval": self.interval,
            "description": self.description, "priority": self.priority,
            "active": self.active, "run_count": self.run_count,
            "fail_count": self.fail_count, "last_run": self.last_run
        }


class CronEngine:
    """Motor de crons avanzado."""

    def __init__(self):
        self.tasks: Dict[str, CronTask] = {}
        self.running = False
        self.execution_log: List[Dict] = []

    def add_task(self, name: str, interval: int, handler: Callable = None,
                 description: str = "", priority: str = "normal") -> CronTask:
        """Añade una tarea programada."""
        task = CronTask(name, interval, handler, description, priority)
        self.tasks[name] = task
        logger.info(f"Cron added: {name} (every {interval}s)")
        return task

    def remove_task(self, name: str) -> bool:
        if name in self.tasks:
            del self.tasks[name]
            return True
        return False

    def pause_task(self, name: str) -> bool:
        if name in self.tasks:
            self.tasks[name].active = False
            return True
        return False

    def resume_task(self, name: str) -> bool:
        if name in self.tasks:
            self.tasks[name].active = True
            return True
        return False

    async def start(self):
        """Inicia el engine de crons."""
        self.running = True
        logger.info(f"Cron Engine started — {len(self.tasks)} tasks")

        while self.running:
            for name, task in list(self.tasks.items()):
                if task.is_due():
                    asyncio.create_task(self._execute_task(task))
            await asyncio.sleep(10)

    async def _execute_task(self, task: CronTask):
        """Ejecuta una tarea (fire-and-forget)."""
        task.last_run = time.time()
        task.run_count += 1

        retries = 0
        while retries <= task.max_retries:
            try:
                if task.handler:
                    if asyncio.iscoroutinefunction(task.handler):
                        result = await task.handler()
                    else:
                        result = task.handler()
                    task.last_result = result
                    self._log_execution(task, "success", result)
                    return
                else:
                    self._log_execution(task, "no_handler")
                    return
            except Exception as e:
                retries += 1
                if retries > task.max_retries:
                    task.fail_count += 1
                    self._log_execution(task, "failed", str(e))
                    logger.error(f"Cron {task.name} failed after {retries} retries: {e}")
                else:
                    await asyncio.sleep(2)

    def _log_execution(self, task: CronTask, status: str, result=None):
        self.execution_log.append({
            "task": task.name, "status": status,
            "result": str(result)[:200] if result else None,
            "timestamp": time.time()
        })
        if len(self.execution_log) > 200:
            self.execution_log = self.execution_log[-200:]

    def get_status(self) -> Dict:
        return {
            "running": self.running,
            "total_tasks": len(self.tasks),
            "active_tasks": sum(1 for t in self.tasks.values() if t.active),
            "tasks": {n: t.to_dict() for n, t in self.tasks.items()},
            "last_executions": self.execution_log[-10:]
        }

    def stop(self):
        self.running = False


# Singleton
cron_engine = CronEngine()
