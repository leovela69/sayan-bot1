# -*- coding: utf-8 -*-
"""
DAEMON — Ejecución 24/7
Capa 3 (Ejecutores) — Tareas programadas que nunca paran.

Funciones:
- Cron jobs del enjambre (cada N minutos/horas)
- Sincronización periódica con Panteón
- Health checks automáticos
- Limpieza de memoria/logs
- Publicaciones programadas
- Cualquier tarea recurrente
"""
import time
import asyncio
import logging
from src.swarm.base_agent import BaseAgent
from src.swarm.bus.message_bus import Message

logger = logging.getLogger("sayan.daemon")


class CronJob:
    """Una tarea programada."""
    def __init__(self, name: str, interval: int, target: str, action: str, payload: dict = None):
        self.name = name
        self.interval = interval  # segundos
        self.target = target
        self.action = action
        self.payload = payload or {}
        self.last_run = 0
        self.run_count = 0

    def is_due(self) -> bool:
        return time.time() - self.last_run >= self.interval

    def mark_run(self):
        self.last_run = time.time()
        self.run_count += 1


class Daemon(BaseAgent):
    """Ejecutor de tareas programadas 24/7."""

    def __init__(self):
        super().__init__("DAEMON", layer=3, role="Cron 24/7")
        self.jobs = self._default_jobs()

    def _default_jobs(self) -> list:
        return [
            CronJob("health_check", 60, "KRONOS", "health_check"),
            CronJob("sync_panteon", 300, "ORACULO", "observe_panteon", {"target": "general"}),
            CronJob("check_patterns", 600, "GENESIS", "check_patterns"),
            CronJob("sentinel_scan", 120, "SENTINEL", "scan", {"target": "swarm"}),
            CronJob("atlas_summary", 1800, "ATLAS", "summary"),
        ]

    async def process_message(self, message: Message):
        action = message.action
        if action == "add_job":
            return self._add_job(message.payload)
        elif action == "list_jobs":
            return self._list_jobs()
        elif action == "remove_job":
            return self._remove_job(message.payload)
        elif action == "execute_task":
            return self._list_jobs()
        elif action == "report_status":
            return self.status()

    async def tick(self):
        """Tick — ejecuta jobs pendientes."""
        for job in self.jobs:
            if job.is_due():
                try:
                    await self.send(job.target, job.action, job.payload)
                    job.mark_run()
                except Exception as e:
                    self.logger.error(f"Cron job {job.name} failed: {e}")

    def _add_job(self, payload: dict) -> dict:
        name = payload.get("name", f"job_{len(self.jobs)}")
        job = CronJob(
            name=name,
            interval=payload.get("interval", 300),
            target=payload.get("target", "KRONOS"),
            action=payload.get("action", "task_request"),
            payload=payload.get("payload", {})
        )
        self.jobs.append(job)
        return {"added": True, "job": name, "total_jobs": len(self.jobs)}

    def _remove_job(self, payload: dict) -> dict:
        name = payload.get("name", "")
        self.jobs = [j for j in self.jobs if j.name != name]
        return {"removed": True, "name": name}

    def _list_jobs(self) -> dict:
        return {
            "jobs": [
                {"name": j.name, "interval": j.interval, "target": j.target,
                 "action": j.action, "runs": j.run_count,
                 "next_in": max(0, int(j.interval - (time.time() - j.last_run)))}
                for j in self.jobs
            ]
        }


daemon = Daemon()
