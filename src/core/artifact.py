# -*- coding: utf-8 -*-
"""
ARTIFACT SYSTEM — Sistema de Artifacts estilo Antigravity.

Trazabilidad completa de todas las acciones, outputs y decisiones
de cada agente. Como el sidebar de Antigravity pero con persistencia.

Features:
- Artifacts tipados (plan, code, image, report, task_list, architecture)
- Feed cronológico
- Relaciones padre-hijo (sesiones → artifacts)
- Exportable a JSON
- Búsqueda por tipo, agente, sesión
"""
import uuid
import time
import json
import os
import logging
from typing import Dict, List, Optional, Any
from config.settings import DATA_DIR

logger = logging.getLogger("sayan.artifacts")

ARTIFACTS_DIR = os.path.join(DATA_DIR, "artifacts")
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

ARTIFACT_TYPES = [
    "plan",                  # Plan de ejecución
    "walkthrough",           # Guía paso a paso
    "implementation_plan",   # Plan de implementación técnica
    "task_list",             # Lista de tareas
    "architecture_diagram",  # Diagrama de arquitectura
    "code",                  # Fragmento de código generado
    "report",               # Reporte de análisis
    "decision",             # Decisión tomada con justificación
    "image",                # Imagen generada/referenciada
    "log",                  # Log de ejecución
    "error",                # Error capturado con contexto
    "milestone",            # Hito completado
    "evolution",            # Evolución de un agente
    "skill_learned",        # Skill aprendido
]


class Artifact:
    """Un artifact individual — unidad de trazabilidad."""

    def __init__(self, artifact_type: str, data: Any, agent: str = "SYSTEM",
                 session_id: str = None, parent_id: str = None, metadata: Dict = None):
        self.id = str(uuid.uuid4())[:12]
        self.type = artifact_type if artifact_type in ARTIFACT_TYPES else "log"
        self.data = data
        self.agent = agent
        self.session_id = session_id or "global"
        self.parent_id = parent_id
        self.metadata = metadata or {}
        self.timestamp = time.time()
        self.tags = []

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type,
            "data": self.data if isinstance(self.data, (str, dict, list)) else str(self.data),
            "agent": self.agent,
            "session_id": self.session_id,
            "parent_id": self.parent_id,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "tags": self.tags
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "Artifact":
        a = cls(d["type"], d["data"], d.get("agent", "SYSTEM"),
                d.get("session_id"), d.get("parent_id"), d.get("metadata", {}))
        a.id = d["id"]
        a.timestamp = d.get("timestamp", time.time())
        a.tags = d.get("tags", [])
        return a


class ArtifactStore:
    """Almacén de artifacts con persistencia y búsqueda."""

    def __init__(self):
        self.artifacts: List[Artifact] = []
        self.sessions: Dict[str, Dict] = {}
        self._current_session: str = str(uuid.uuid4())[:8]
        self._load()

    def _load(self):
        """Carga artifacts del disco."""
        store_file = os.path.join(ARTIFACTS_DIR, "store.json")
        if os.path.exists(store_file):
            try:
                with open(store_file, "r") as f:
                    data = json.load(f)
                self.artifacts = [Artifact.from_dict(d) for d in data.get("artifacts", [])]
                self.sessions = data.get("sessions", {})
                logger.info(f"Loaded {len(self.artifacts)} artifacts")
            except Exception as e:
                logger.error(f"Error loading artifacts: {e}")

    def _save(self):
        """Persiste artifacts a disco."""
        store_file = os.path.join(ARTIFACTS_DIR, "store.json")
        try:
            data = {
                "artifacts": [a.to_dict() for a in self.artifacts[-500:]],
                "sessions": self.sessions
            }
            with open(store_file, "w") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving artifacts: {e}")

    def create(self, artifact_type: str, data: Any, agent: str = "SYSTEM",
               parent_id: str = None, metadata: Dict = None, tags: List[str] = None) -> Artifact:
        """Crea un nuevo artifact y lo persiste."""
        artifact = Artifact(
            artifact_type=artifact_type,
            data=data,
            agent=agent,
            session_id=self._current_session,
            parent_id=parent_id,
            metadata=metadata
        )
        if tags:
            artifact.tags = tags

        self.artifacts.append(artifact)
        self._save()
        logger.info(f"Artifact created: [{artifact.type}] by {artifact.agent} ({artifact.id})")
        return artifact

    def get(self, artifact_id: str) -> Optional[Artifact]:
        """Obtiene un artifact por ID."""
        for a in self.artifacts:
            if a.id == artifact_id:
                return a
        return None

    def get_feed(self, limit: int = 20, artifact_type: str = None,
                 agent: str = None, session_id: str = None) -> List[Dict]:
        """Feed de artifacts con filtros opcionales."""
        filtered = self.artifacts
        if artifact_type:
            filtered = [a for a in filtered if a.type == artifact_type]
        if agent:
            filtered = [a for a in filtered if a.agent == agent]
        if session_id:
            filtered = [a for a in filtered if a.session_id == session_id]

        return [a.to_dict() for a in sorted(filtered, key=lambda x: x.timestamp, reverse=True)[:limit]]

    def get_by_parent(self, parent_id: str) -> List[Dict]:
        """Obtiene artifacts hijos de un parent."""
        return [a.to_dict() for a in self.artifacts if a.parent_id == parent_id]

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Búsqueda simple por contenido."""
        query_lower = query.lower()
        results = []
        for a in reversed(self.artifacts):
            data_str = json.dumps(a.data, ensure_ascii=False).lower() if not isinstance(a.data, str) else a.data.lower()
            if query_lower in data_str or query_lower in " ".join(a.tags):
                results.append(a.to_dict())
                if len(results) >= limit:
                    break
        return results

    def start_session(self, name: str = "") -> str:
        """Inicia una nueva sesión de artifacts."""
        self._current_session = str(uuid.uuid4())[:8]
        self.sessions[self._current_session] = {
            "name": name or f"session_{self._current_session}",
            "started": time.time(),
            "artifacts_count": 0
        }
        return self._current_session

    def get_stats(self) -> Dict:
        """Estadísticas del almacén."""
        type_counts = {}
        agent_counts = {}
        for a in self.artifacts:
            type_counts[a.type] = type_counts.get(a.type, 0) + 1
            agent_counts[a.agent] = agent_counts.get(a.agent, 0) + 1

        return {
            "total_artifacts": len(self.artifacts),
            "sessions": len(self.sessions),
            "current_session": self._current_session,
            "by_type": type_counts,
            "by_agent": agent_counts
        }


# Singleton
artifact_store = ArtifactStore()
