# -*- coding: utf-8 -*-
"""
AGENT TEAM — Sistema de subagentes dinámicos estilo Antigravity.

ROLES:
- SENTINEL: Estructura intención, supervisa
- ORCHESTRATOR: Descompone en hitos, despacha workers
- WORKER: Ejecuta tareas (hasta 5 en paralelo)
- REVIEWER: Revisa resultados independientemente
- CRITIC: Stress-testing y pruebas adversariales
- AUDITOR: Verificación final de autenticidad
"""
import asyncio
import time
import logging
from typing import List, Dict
from src.core.brain import think

logger = logging.getLogger("sayan.team")


class SubAgent:
    """Base para subagentes del equipo."""
    def __init__(self, role: str, prompt: str):
        self.role = role
        self.prompt = prompt
        self.result = None

    async def execute(self, task: str, context: str = "") -> Dict:
        messages = [{"role": "user", "content": f"{self.prompt}\n\nTAREA: {task}\nCONTEXTO: {context}"}]
        result = await think(messages)
        self.result = result.get("content", "")
        return {"role": self.role, "output": self.result, "timestamp": time.time()}


class AgentTeam:
    """Equipo dinámico de agentes estilo Antigravity."""

    def __init__(self):
        self.max_workers = 5
        self.history = []

    async def execute_teamwork(self, task: str) -> Dict:
        """Ejecuta un equipo completo en paralelo."""
        start = time.time()

        # 1. SENTINEL: estructura la intención
        sentinel = SubAgent("SENTINEL",
            "Eres el Sentinel. Analiza la intención del usuario y estructúrala "
            "en un formato claro: OBJETIVO, REQUISITOS, RESTRICCIONES, CRITERIO DE ÉXITO.")
        intent = await sentinel.execute(task)

        # 2. ORCHESTRATOR: descompone en hitos
        orchestrator = SubAgent("ORCHESTRATOR",
            "Eres el Orchestrator. Descompón este objetivo en máximo 5 hitos "
            "ejecutables en paralelo. Formato: HITO 1: ..., HITO 2: ..., etc.")
        plan = await orchestrator.execute(task, intent["output"])

        # Parsear hitos
        milestones = self._parse_milestones(plan["output"])

        # 3. WORKERS: ejecutan en paralelo
        workers = []
        for i, milestone in enumerate(milestones[:self.max_workers]):
            worker = SubAgent(f"WORKER_{i+1}",
                f"Eres Worker #{i+1}. Ejecuta SOLO este hito de forma concreta y eficiente. "
                "Genera el resultado final, no explicaciones.")
            workers.append(worker.execute(milestone, plan["output"]))

        worker_results = await asyncio.gather(*workers)

        # 4. REVIEWER: revisa
        reviewer = SubAgent("REVIEWER",
            "Eres el Reviewer. Revisa estos resultados y señala: "
            "CORRECTO, MEJORABLE, o INCORRECTO para cada uno. Sé breve.")
        combined = "\n".join([f"Worker {r['role']}: {r['output'][:200]}" for r in worker_results])
        review = await reviewer.execute(combined, intent["output"])

        # 5. AUDITOR: verificación final
        auditor = SubAgent("AUDITOR",
            "Eres el Auditor. Verifica que el resultado CUMPLE el objetivo original. "
            "Responde: APROBADO o RECHAZADO con razón.")
        audit = await auditor.execute(review["output"], intent["output"])

        result = {
            "task": task,
            "intent": intent["output"][:200],
            "plan": plan["output"][:300],
            "workers": len(worker_results),
            "review": review["output"][:200],
            "audit": audit["output"][:200],
            "duration": time.time() - start,
            "timestamp": time.time()
        }
        self.history.append(result)
        if len(self.history) > 50:
            self.history = self.history[-50:]

        return result

    def _parse_milestones(self, plan_text: str) -> List[str]:
        """Extrae hitos del plan del orchestrator."""
        lines = plan_text.split("\n")
        milestones = []
        for line in lines:
            line = line.strip()
            if line and any(line.startswith(p) for p in ["HITO", "1.", "2.", "3.", "4.", "5.", "-", "*"]):
                milestones.append(line)
        if not milestones:
            milestones = [plan_text]
        return milestones[:5]


# Singleton
team = AgentTeam()
