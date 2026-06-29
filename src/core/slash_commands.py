# -*- coding: utf-8 -*-
"""
SLASH COMMANDS — Sistema de comandos avanzados estilo Antigravity.

Comandos:
- /goal <tarea>       → Ejecución autónoma sin confirmación
- /schedule <tarea>   → Programar tarea recurrente
- /reelme <pregunta>  → Clarificación antes de ejecutar
- /artifacts          → Ver feed de artifacts
- /team <tarea>       → Ejecutar con equipo completo de agentes
- /memory <query>     → Buscar en memoria colectiva
- /evolve             → Forzar ciclo de evolución
"""
import asyncio
import logging
import time
import re
from typing import Dict, Optional, Tuple
from src.core.brain import think, quick_reply
from src.core.agent_team import team
from src.core.artifact import artifact_store
from src.core.cron_system import cron_engine

logger = logging.getLogger("sayan.slash")


class SlashCommandEngine:
    """Motor de slash commands estilo Antigravity."""

    def __init__(self):
        self.commands = {
            "/goal": self._cmd_goal,
            "/schedule": self._cmd_schedule,
            "/reelme": self._cmd_reelme,
            "/artifacts": self._cmd_artifacts,
            "/team": self._cmd_team,
            "/memory": self._cmd_memory,
            "/evolve": self._cmd_evolve,
            "/cancel": self._cmd_cancel,
        }
        self.active_goals = []
        self.scheduled_count = 0

    def is_slash_command(self, text: str) -> bool:
        """Detecta si un mensaje es un slash command."""
        return text.strip().startswith("/") and text.split()[0].lower() in self.commands

    def parse_command(self, text: str) -> Tuple[str, str]:
        """Separa comando de argumentos."""
        parts = text.strip().split(None, 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        return cmd, args

    async def execute(self, text: str, user_id: int = 0) -> str:
        """Ejecuta un slash command."""
        cmd, args = self.parse_command(text)
        handler = self.commands.get(cmd)
        if handler:
            try:
                result = await handler(args, user_id)
                # Registrar artifact
                artifact_store.create("log", {
                    "command": cmd, "args": args, "result": result[:200]
                }, agent="SLASH_ENGINE", tags=["command", cmd[1:]])
                return result
            except Exception as e:
                logger.error(f"Slash command error ({cmd}): {e}")
                return f"Error ejecutando {cmd}: {str(e)}"
        return f"Comando desconocido: {cmd}"

    async def _cmd_goal(self, args: str, user_id: int) -> str:
        """
        /goal — Ejecución autónoma. El agente resuelve sin pedir confirmación.
        Despliega el equipo completo de subagentes.
        """
        if not args:
            return "Uso: /goal <describe qué quieres lograr>"

        # Registrar goal
        goal_id = f"goal_{int(time.time())}"
        self.active_goals.append({
            "id": goal_id, "task": args, "status": "running",
            "started": time.time(), "user_id": user_id
        })

        # Crear artifact de plan
        artifact_store.create("plan", {
            "goal": args, "goal_id": goal_id, "mode": "autonomous"
        }, agent="GOAL_ENGINE", tags=["goal", "autonomous"])

        # Ejecutar con equipo completo
        try:
            result = await team.execute_teamwork(args)
            # Marcar completado
            for g in self.active_goals:
                if g["id"] == goal_id:
                    g["status"] = "completed"
                    g["duration"] = time.time() - g["started"]

            # Artifact de milestone
            artifact_store.create("milestone", {
                "goal_id": goal_id, "task": args,
                "duration": result.get("duration", 0),
                "workers": result.get("workers", 0),
                "audit": result.get("audit", "N/A")
            }, agent="GOAL_ENGINE", tags=["milestone", "completed"])

            summary = (
                f"GOAL COMPLETADO\n\n"
                f"Tarea: {args}\n"
                f"Duración: {result.get('duration', 0):.1f}s\n"
                f"Workers usados: {result.get('workers', 0)}\n"
                f"Auditoría: {result.get('audit', 'N/A')[:100]}\n\n"
                f"Resultado:\n{result.get('review', '')[:500]}"
            )
            return summary
        except Exception as e:
            for g in self.active_goals:
                if g["id"] == goal_id:
                    g["status"] = "failed"
            return f"Goal fallido: {str(e)}"

    async def _cmd_schedule(self, args: str, user_id: int) -> str:
        """
        /schedule — Programa tarea recurrente.
        Formato: /schedule cada <N> <min|h|s> <tarea>
        Ejemplo: /schedule cada 30 min revisar estado del build
        """
        if not args:
            return (
                "Uso: /schedule cada <N> <min|h|s> <tarea>\n"
                "Ejemplo: /schedule cada 30 min revisar builds\n"
                "         /schedule cada 2 h generar reporte"
            )

        # Parsear intervalo
        pattern = r"cada\s+(\d+)\s+(min|h|s|hora|minuto|segundo)s?\s+(.+)"
        match = re.search(pattern, args, re.IGNORECASE)

        if not match:
            # Intentar formato simple
            interval = 300  # 5 min por defecto
            task_desc = args
        else:
            num = int(match.group(1))
            unit = match.group(2).lower()
            task_desc = match.group(3)

            multipliers = {"s": 1, "segundo": 1, "min": 60, "minuto": 60, "h": 3600, "hora": 3600}
            interval = num * multipliers.get(unit, 60)

        self.scheduled_count += 1
        task_name = f"scheduled_{self.scheduled_count}"

        # Handler: ejecutar la tarea con quick_reply
        async def scheduled_handler():
            return await quick_reply(f"Ejecuta esta tarea programada: {task_desc}")

        cron_engine.add_task(
            name=task_name,
            interval=interval,
            handler=scheduled_handler,
            description=task_desc,
            priority="normal"
        )

        artifact_store.create("task_list", {
            "scheduled": task_name, "interval": interval,
            "description": task_desc
        }, agent="SCHEDULER", tags=["schedule", "cron"])

        return (
            f"TAREA PROGRAMADA\n\n"
            f"ID: {task_name}\n"
            f"Cada: {interval}s ({interval//60} min)\n"
            f"Tarea: {task_desc}\n\n"
            f"Cancelar: /cancel {task_name}"
        )

    async def _cmd_reelme(self, args: str, user_id: int) -> str:
        """
        /reelme — Modo clarificación. El bot pregunta antes de actuar.
        """
        if not args:
            return "Uso: /reelme <lo que quieres hacer>\nEl bot preguntará antes de ejecutar."

        # Generar preguntas de clarificación
        prompt = (
            f"El usuario quiere: {args}\n\n"
            f"Genera 3-5 preguntas de clarificación para entender mejor lo que necesita. "
            f"Sé conciso y práctico. Formato:\n"
            f"1. Pregunta\n2. Pregunta\netc."
        )
        questions = await quick_reply(prompt)

        artifact_store.create("decision", {
            "mode": "reelme", "query": args, "questions": questions
        }, agent="REELME", tags=["clarification"])

        return f"CLARIFICACIÓN NECESARIA\n\nSobre: {args}\n\n{questions}"

    async def _cmd_artifacts(self, args: str, user_id: int) -> str:
        """
        /artifacts — Ver feed de artifacts recientes.
        """
        if args:
            # Buscar
            results = artifact_store.search(args, limit=5)
            if not results:
                return f"Sin artifacts para: {args}"
            txt = f"ARTIFACTS — Búsqueda: '{args}'\n\n"
            for a in results:
                txt += f"[{a['type']}] {a['agent']} — {str(a['data'])[:80]}\n"
            return txt

        # Feed reciente
        feed = artifact_store.get_feed(limit=10)
        if not feed:
            return "Sin artifacts todavía."

        stats = artifact_store.get_stats()
        txt = f"ARTIFACT FEED ({stats['total_artifacts']} total)\n\n"
        for a in feed:
            data_preview = str(a['data'])[:60]
            txt += f"[{a['type']}] {a['agent']}: {data_preview}\n"
        return txt

    async def _cmd_team(self, args: str, user_id: int) -> str:
        """
        /team — Ejecutar tarea con equipo completo (Sentinel→Orchestrator→Workers→Reviewer→Auditor).
        """
        if not args:
            return "Uso: /team <tarea compleja>"

        result = await team.execute_teamwork(args)
        return (
            f"TEAMWORK COMPLETADO\n\n"
            f"Intención: {result.get('intent', '')[:150]}\n\n"
            f"Plan: {result.get('plan', '')[:200]}\n\n"
            f"Workers: {result.get('workers', 0)}\n"
            f"Review: {result.get('review', '')[:150]}\n"
            f"Auditoría: {result.get('audit', '')[:150]}\n"
            f"Duración: {result.get('duration', 0):.1f}s"
        )

    async def _cmd_memory(self, args: str, user_id: int) -> str:
        """
        /memory — Buscar en artifacts y memoria.
        """
        if not args:
            stats = artifact_store.get_stats()
            return (
                f"MEMORIA DEL SISTEMA\n\n"
                f"Artifacts: {stats['total_artifacts']}\n"
                f"Sesiones: {stats['sessions']}\n"
                f"Por tipo: {stats['by_type']}\n\n"
                f"Uso: /memory <buscar algo>"
            )

        results = artifact_store.search(args, limit=5)
        if not results:
            return f"Sin resultados para: {args}"

        txt = f"MEMORIA — '{args}':\n\n"
        for r in results:
            txt += f"[{r['type']}] {r['agent']}: {str(r['data'])[:100]}\n\n"
        return txt

    async def _cmd_evolve(self, args: str, user_id: int) -> str:
        """
        /evolve — Forzar ciclo de evolución del sistema.
        """
        artifact_store.create("evolution", {
            "trigger": "manual", "user_id": user_id, "args": args
        }, agent="EVOLUTION", tags=["evolve", "manual"])

        # Análisis rápido del estado
        cron_status = cron_engine.get_status()
        team_history = len(team.history)

        return (
            f"CICLO DE EVOLUCIÓN\n\n"
            f"Crons activos: {cron_status['active_tasks']}\n"
            f"Teamworks completados: {team_history}\n"
            f"Artifacts totales: {artifact_store.get_stats()['total_artifacts']}\n\n"
            f"Sistema en constante evolución."
        )

    async def _cmd_cancel(self, args: str, user_id: int) -> str:
        """
        /cancel — Cancela una tarea programada.
        """
        if not args:
            return "Uso: /cancel <task_name>"

        if cron_engine.remove_task(args.strip()):
            return f"Tarea cancelada: {args}"
        return f"No encontrada: {args}"


# Singleton
slash_engine = SlashCommandEngine()
