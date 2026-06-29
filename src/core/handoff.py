# -*- coding: utf-8 -*-
"""
HANDOFF SYSTEM — Self-Succession con Handoff Files estilo Antigravity.

Cuando una sesión/agente termina, genera un "handoff file" con TODO el contexto
para que el siguiente agente (o la siguiente sesión) pueda continuar sin perder nada.

Features:
- Handoff automático al cerrar sesión
- Contexto aislado por subagente
- Resumen de estado, decisiones, progreso
- Continuidad perfecta entre sesiones
- Exportable como JSON para otros sistemas
"""
import json
import os
import time
import logging
from typing import Dict, List, Optional
from config.settings import DATA_DIR

logger = logging.getLogger("sayan.handoff")

HANDOFF_DIR = os.path.join(DATA_DIR, "handoffs")
os.makedirs(HANDOFF_DIR, exist_ok=True)


class HandoffFile:
    """Un handoff file — snapshot completo del estado de un agente/sesión."""

    def __init__(self, agent_name: str, session_id: str = ""):
        self.id = f"hf_{agent_name}_{int(time.time())}"
        self.agent_name = agent_name
        self.session_id = session_id
        self.created_at = time.time()
        self.context = {}
        self.decisions = []
        self.progress = {}
        self.pending_tasks = []
        self.knowledge_gained = []
        self.recommendations = []
        self.state_snapshot = {}
        self.metadata = {}

    def add_context(self, key: str, value):
        """Añade contexto al handoff."""
        self.context[key] = value

    def add_decision(self, decision: str, reasoning: str = ""):
        """Registra una decisión tomada."""
        self.decisions.append({
            "decision": decision,
            "reasoning": reasoning,
            "timestamp": time.time()
        })

    def add_progress(self, task: str, status: str, details: str = ""):
        """Registra progreso en una tarea."""
        self.progress[task] = {
            "status": status,  # completed, in_progress, blocked, skipped
            "details": details,
            "timestamp": time.time()
        }

    def add_pending_task(self, task: str, priority: str = "normal", context: str = ""):
        """Añade tarea pendiente para el siguiente."""
        self.pending_tasks.append({
            "task": task,
            "priority": priority,
            "context": context,
            "added_at": time.time()
        })

    def add_knowledge(self, knowledge: str, category: str = "general"):
        """Añade conocimiento aprendido durante la sesión."""
        self.knowledge_gained.append({
            "knowledge": knowledge,
            "category": category,
            "timestamp": time.time()
        })

    def add_recommendation(self, recommendation: str, urgency: str = "normal"):
        """Añade recomendación para el siguiente agente/sesión."""
        self.recommendations.append({
            "recommendation": recommendation,
            "urgency": urgency,
            "timestamp": time.time()
        })

    def set_state_snapshot(self, state: Dict):
        """Snapshot del estado actual del sistema."""
        self.state_snapshot = state

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "agent_name": self.agent_name,
            "session_id": self.session_id,
            "created_at": self.created_at,
            "context": self.context,
            "decisions": self.decisions,
            "progress": self.progress,
            "pending_tasks": self.pending_tasks,
            "knowledge_gained": self.knowledge_gained,
            "recommendations": self.recommendations,
            "state_snapshot": self.state_snapshot,
            "metadata": self.metadata
        }

    def to_summary(self) -> str:
        """Genera resumen legible del handoff."""
        lines = [
            f"HANDOFF — {self.agent_name}",
            f"Sesión: {self.session_id}",
            f"Fecha: {time.strftime('%Y-%m-%d %H:%M', time.localtime(self.created_at))}",
            ""
        ]

        if self.decisions:
            lines.append(f"DECISIONES ({len(self.decisions)}):")
            for d in self.decisions[-5:]:
                lines.append(f"  • {d['decision']}")
            lines.append("")

        if self.progress:
            lines.append("PROGRESO:")
            for task, info in self.progress.items():
                lines.append(f"  [{info['status']}] {task}")
            lines.append("")

        if self.pending_tasks:
            lines.append(f"PENDIENTE ({len(self.pending_tasks)}):")
            for t in self.pending_tasks:
                lines.append(f"  [{t['priority']}] {t['task']}")
            lines.append("")

        if self.recommendations:
            lines.append("RECOMENDACIONES:")
            for r in self.recommendations:
                lines.append(f"  → {r['recommendation']}")
            lines.append("")

        if self.knowledge_gained:
            lines.append(f"CONOCIMIENTO NUEVO ({len(self.knowledge_gained)}):")
            for k in self.knowledge_gained[-5:]:
                lines.append(f"  [{k['category']}] {k['knowledge'][:80]}")

        return "\n".join(lines)


class HandoffManager:
    """Gestor de handoff files."""

    def __init__(self):
        self.active_handoffs: Dict[str, HandoffFile] = {}
        self.history: List[Dict] = []
        self._load_history()

    def _load_history(self):
        """Carga historial de handoffs."""
        history_file = os.path.join(HANDOFF_DIR, "history.json")
        if os.path.exists(history_file):
            try:
                with open(history_file, "r") as f:
                    self.history = json.load(f)
            except Exception:
                self.history = []

    def _save_history(self):
        """Persiste historial."""
        history_file = os.path.join(HANDOFF_DIR, "history.json")
        try:
            with open(history_file, "w") as f:
                json.dump(self.history[-100:], f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving handoff history: {e}")

    def start_handoff(self, agent_name: str, session_id: str = "") -> HandoffFile:
        """Inicia un nuevo handoff file para un agente."""
        hf = HandoffFile(agent_name, session_id)
        self.active_handoffs[agent_name] = hf
        logger.info(f"Handoff started: {agent_name} ({hf.id})")
        return hf

    def get_active(self, agent_name: str) -> Optional[HandoffFile]:
        """Obtiene el handoff activo de un agente."""
        return self.active_handoffs.get(agent_name)

    def finalize(self, agent_name: str, state_snapshot: Dict = None) -> Optional[HandoffFile]:
        """
        Finaliza un handoff y lo persiste.
        El siguiente agente/sesión podrá cargar este contexto.
        """
        hf = self.active_handoffs.pop(agent_name, None)
        if not hf:
            return None

        if state_snapshot:
            hf.set_state_snapshot(state_snapshot)

        # Persistir
        hf_file = os.path.join(HANDOFF_DIR, f"{hf.id}.json")
        try:
            with open(hf_file, "w") as f:
                json.dump(hf.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving handoff: {e}")

        # Registrar en historial
        self.history.append({
            "id": hf.id,
            "agent": agent_name,
            "session_id": hf.session_id,
            "timestamp": time.time(),
            "decisions": len(hf.decisions),
            "pending_tasks": len(hf.pending_tasks),
            "knowledge": len(hf.knowledge_gained)
        })
        self._save_history()

        logger.info(f"Handoff finalized: {hf.id}")
        return hf

    def load_latest(self, agent_name: str) -> Optional[Dict]:
        """
        Carga el último handoff de un agente para continuidad.
        """
        # Buscar en historial
        agent_handoffs = [h for h in self.history if h["agent"] == agent_name]
        if not agent_handoffs:
            return None

        latest = agent_handoffs[-1]
        hf_file = os.path.join(HANDOFF_DIR, f"{latest['id']}.json")

        if os.path.exists(hf_file):
            try:
                with open(hf_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return latest

    def get_continuation_context(self, agent_name: str) -> str:
        """
        Genera contexto de continuación para inyectar en el prompt del siguiente agente.
        """
        data = self.load_latest(agent_name)
        if not data:
            return ""

        lines = [
            f"[CONTEXTO DE CONTINUACIÓN — {agent_name}]",
            f"Última sesión: {data.get('session_id', 'N/A')}",
        ]

        # Decisiones recientes
        decisions = data.get("decisions", [])
        if decisions:
            lines.append("\nDecisiones previas:")
            for d in decisions[-3:]:
                lines.append(f"  • {d['decision']}")

        # Tareas pendientes
        pending = data.get("pending_tasks", [])
        if pending:
            lines.append("\nPendiente:")
            for t in pending:
                lines.append(f"  [{t['priority']}] {t['task']}")

        # Conocimiento
        knowledge = data.get("knowledge_gained", [])
        if knowledge:
            lines.append("\nConocimiento adquirido:")
            for k in knowledge[-3:]:
                lines.append(f"  • {k['knowledge'][:60]}")

        lines.append("[FIN CONTEXTO]")
        return "\n".join(lines)

    def get_status(self) -> Dict:
        """Estado del sistema de handoffs."""
        return {
            "active_handoffs": len(self.active_handoffs),
            "total_history": len(self.history),
            "agents_with_handoffs": list(set(h["agent"] for h in self.history)),
            "last_5": self.history[-5:]
        }


# Singleton
handoff_manager = HandoffManager()
