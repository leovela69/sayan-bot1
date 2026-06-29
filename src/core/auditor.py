# -*- coding: utf-8 -*-
"""
AUDITOR — Sistema de Auditoría Anti-Cheating estilo Antigravity.

Verifica que los agentes no "hagan trampa":
- No inventen resultados sin ejecutar
- No salten pasos del pipeline
- No generen outputs inconsistentes
- No repitan respuestas cacheadas como si fueran nuevas
- No ignoren errores silenciosamente

Features:
- Verificación de autenticidad de outputs
- Análisis estático de coherencia
- Detección de respuestas fabricadas
- Scoring de confianza (0-100)
- Historial de auditorías
- Alertas al owner si hay cheating
"""
import json
import time
import logging
import hashlib
import os
from typing import Dict, List, Optional, Any
from config.settings import DATA_DIR

logger = logging.getLogger("sayan.auditor")

AUDIT_DIR = os.path.join(DATA_DIR, "audits")
os.makedirs(AUDIT_DIR, exist_ok=True)


class AuditResult:
    """Resultado de una auditoría."""

    def __init__(self, agent: str, action: str):
        self.id = f"audit_{int(time.time()*1000) % 100000}"
        self.agent = agent
        self.action = action
        self.timestamp = time.time()
        self.checks: List[Dict] = []
        self.score = 100  # Empieza perfecto, se penaliza
        self.verdict = "PENDING"  # CLEAN, SUSPICIOUS, CHEATING
        self.flags: List[str] = []

    def add_check(self, name: str, passed: bool, details: str = "", penalty: int = 0):
        """Añade un check a la auditoría."""
        self.checks.append({
            "name": name, "passed": passed,
            "details": details, "penalty": penalty
        })
        if not passed:
            self.score -= penalty
            self.flags.append(f"{name}: {details}")

    def finalize(self):
        """Calcula veredicto final."""
        if self.score >= 80:
            self.verdict = "CLEAN"
        elif self.score >= 50:
            self.verdict = "SUSPICIOUS"
        else:
            self.verdict = "CHEATING"

    def to_dict(self) -> Dict:
        return {
            "id": self.id, "agent": self.agent, "action": self.action,
            "timestamp": self.timestamp, "checks": self.checks,
            "score": self.score, "verdict": self.verdict, "flags": self.flags
        }


class Auditor:
    """Sistema de auditoría anti-cheating."""

    def __init__(self):
        self.audit_history: List[AuditResult] = []
        self.response_hashes: Dict[str, List[str]] = {}  # agent → hashes
        self.execution_log: Dict[str, List[Dict]] = {}  # agent → acciones
        self.alerts: List[Dict] = []

    def audit_response(self, agent: str, action: str, input_data: Any,
                       output_data: Any, execution_time: float = 0,
                       tool_calls: List[str] = None) -> AuditResult:
        """
        Audita una respuesta de un agente.
        Verifica autenticidad, coherencia, y no-fabricación.
        """
        audit = AuditResult(agent, action)

        # CHECK 1: Tiempo de ejecución realista
        self._check_execution_time(audit, action, execution_time)

        # CHECK 2: Output no vacío
        self._check_non_empty(audit, output_data)

        # CHECK 3: No repetición (anti-cache cheat)
        self._check_no_repetition(audit, agent, output_data)

        # CHECK 4: Coherencia input/output
        self._check_coherence(audit, input_data, output_data)

        # CHECK 5: Tools usadas si eran necesarias
        self._check_tool_usage(audit, action, tool_calls)

        # CHECK 6: No contenido genérico/template
        self._check_not_generic(audit, output_data)

        # Finalizar
        audit.finalize()

        # Guardar
        self.audit_history.append(audit)
        if len(self.audit_history) > 500:
            self.audit_history = self.audit_history[-500:]

        # Registrar ejecución
        if agent not in self.execution_log:
            self.execution_log[agent] = []
        self.execution_log[agent].append({
            "action": action, "time": time.time(),
            "score": audit.score, "verdict": audit.verdict
        })

        # Alertar si hay cheating
        if audit.verdict == "CHEATING":
            self._raise_alert(audit)

        logger.info(f"Audit {audit.id}: {agent}/{action} → {audit.verdict} (score={audit.score})")
        return audit

    def _check_execution_time(self, audit: AuditResult, action: str, exec_time: float):
        """Si tardó 0ms, probablemente no ejecutó nada."""
        if exec_time < 0.01 and action not in ["read", "get", "status"]:
            audit.add_check(
                "execution_time", False,
                f"Demasiado rápido ({exec_time:.4f}s) para '{action}'",
                penalty=20
            )
        else:
            audit.add_check("execution_time", True, f"{exec_time:.2f}s")

    def _check_non_empty(self, audit: AuditResult, output: Any):
        """Output no debe ser vacío/nulo."""
        if output is None or output == "" or output == {} or output == []:
            audit.add_check("non_empty", False, "Output vacío", penalty=30)
        else:
            audit.add_check("non_empty", True)

    def _check_no_repetition(self, audit: AuditResult, agent: str, output: Any):
        """Detecta si el output es idéntico a uno anterior (respuesta cacheada)."""
        output_str = json.dumps(output, ensure_ascii=False) if not isinstance(output, str) else output
        output_hash = hashlib.md5(output_str.encode()).hexdigest()

        if agent not in self.response_hashes:
            self.response_hashes[agent] = []

        recent_hashes = self.response_hashes[agent][-20:]
        if output_hash in recent_hashes:
            audit.add_check(
                "no_repetition", False,
                "Output idéntico a uno previo (posible cache)",
                penalty=25
            )
        else:
            audit.add_check("no_repetition", True)

        self.response_hashes[agent].append(output_hash)
        if len(self.response_hashes[agent]) > 100:
            self.response_hashes[agent] = self.response_hashes[agent][-100:]

    def _check_coherence(self, audit: AuditResult, input_data: Any, output_data: Any):
        """Verifica coherencia básica entre input y output."""
        input_str = str(input_data).lower() if input_data else ""
        output_str = str(output_data).lower() if output_data else ""

        # Si el input pide algo específico, el output debe mencionarlo
        if len(input_str) > 20 and len(output_str) > 20:
            # Extraer palabras clave del input
            keywords = [w for w in input_str.split() if len(w) > 4][:5]
            if keywords:
                matches = sum(1 for k in keywords if k in output_str)
                relevance = matches / len(keywords)
                if relevance < 0.1 and len(output_str) > 50:
                    audit.add_check(
                        "coherence", False,
                        f"Baja relevancia input/output ({relevance:.0%})",
                        penalty=15
                    )
                else:
                    audit.add_check("coherence", True, f"Relevancia: {relevance:.0%}")
            else:
                audit.add_check("coherence", True, "Input corto, skip")
        else:
            audit.add_check("coherence", True, "Datos insuficientes")

    def _check_tool_usage(self, audit: AuditResult, action: str, tool_calls: List[str] = None):
        """Si la acción requería tools y no se usaron, es sospechoso."""
        tool_required_actions = ["search", "generate", "execute", "analyze", "fetch"]
        needs_tool = any(t in action.lower() for t in tool_required_actions)

        if needs_tool and (not tool_calls or len(tool_calls) == 0):
            audit.add_check(
                "tool_usage", False,
                f"Acción '{action}' probablemente requería tools pero no se usaron",
                penalty=15
            )
        else:
            audit.add_check("tool_usage", True)

    def _check_not_generic(self, audit: AuditResult, output: Any):
        """Detecta respuestas genéricas/template."""
        output_str = str(output).lower()
        generic_phrases = [
            "como modelo de lenguaje",
            "no puedo hacer eso",
            "lo siento, no tengo",
            "aquí tienes un ejemplo genérico",
            "lorem ipsum"
        ]
        for phrase in generic_phrases:
            if phrase in output_str:
                audit.add_check(
                    "not_generic", False,
                    f"Contiene frase genérica: '{phrase}'",
                    penalty=20
                )
                return
        audit.add_check("not_generic", True)

    def _raise_alert(self, audit: AuditResult):
        """Genera alerta de cheating."""
        alert = {
            "audit_id": audit.id,
            "agent": audit.agent,
            "action": audit.action,
            "score": audit.score,
            "flags": audit.flags,
            "timestamp": time.time()
        }
        self.alerts.append(alert)
        logger.warning(f"CHEATING ALERT: {audit.agent} — score {audit.score} — {audit.flags}")

    def get_agent_score(self, agent: str) -> Dict:
        """Score acumulado de un agente."""
        agent_audits = [a for a in self.audit_history if a.agent == agent]
        if not agent_audits:
            return {"agent": agent, "score": 100, "audits": 0, "verdict": "NO_DATA"}

        avg_score = sum(a.score for a in agent_audits) / len(agent_audits)
        verdicts = {"CLEAN": 0, "SUSPICIOUS": 0, "CHEATING": 0}
        for a in agent_audits:
            verdicts[a.verdict] = verdicts.get(a.verdict, 0) + 1

        return {
            "agent": agent,
            "average_score": round(avg_score, 1),
            "total_audits": len(agent_audits),
            "verdicts": verdicts,
            "alerts": len([al for al in self.alerts if al["agent"] == agent]),
            "trust_level": "HIGH" if avg_score >= 80 else "MEDIUM" if avg_score >= 50 else "LOW"
        }

    def get_status(self) -> Dict:
        """Estado general del auditor."""
        return {
            "total_audits": len(self.audit_history),
            "total_alerts": len(self.alerts),
            "agents_audited": list(set(a.agent for a in self.audit_history)),
            "recent_alerts": self.alerts[-5:],
            "recent_audits": [a.to_dict() for a in self.audit_history[-5:]]
        }


# Singleton
auditor = Auditor()
