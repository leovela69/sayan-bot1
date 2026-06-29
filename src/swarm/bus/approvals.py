# -*- coding: utf-8 -*-
"""
APPROVAL SYSTEM — Sistema de aprobación de Leo.
Cuando un agente propone una evolución/cambio, Leo debe aprobar.
Le llega por Telegram y responde SI/NO.
"""
import json
import os
import time
import logging
from config.settings import DATA_DIR, OWNER_ID

logger = logging.getLogger("sayan.approvals")

APPROVALS_FILE = os.path.join(DATA_DIR, "pending_approvals.json")


class ApprovalRequest:
    def __init__(self, agent: str, action: str, description: str, payload: dict = None):
        self.id = f"apr_{int(time.time()*1000)}"
        self.agent = agent
        self.action = action
        self.description = description
        self.payload = payload or {}
        self.status = "pending"  # pending, approved, rejected
        self.created_at = time.time()
        self.resolved_at = None

    def to_dict(self):
        return {
            "id": self.id, "agent": self.agent, "action": self.action,
            "description": self.description, "payload": self.payload,
            "status": self.status, "created_at": self.created_at,
            "resolved_at": self.resolved_at
        }


class ApprovalSystem:
    """Gestiona aprobaciones pendientes de Leo."""

    def __init__(self):
        self._pending = self._load()
        self._notify_callback = None

    def set_notify_callback(self, callback):
        """Registra función para notificar a Leo (via Telegram)."""
        self._notify_callback = callback

    async def request_approval(self, agent: str, action: str, description: str, payload: dict = None) -> str:
        """
        Un agente solicita aprobación a Leo.
        Devuelve el ID de la solicitud.
        """
        req = ApprovalRequest(agent, action, description, payload)
        self._pending.append(req.to_dict())
        self._save()

        # Notificar a Leo
        if self._notify_callback:
            msg = (
                f"APROBACIÓN PENDIENTE\n"
                f"Agente: {agent}\n"
                f"Acción: {action}\n"
                f"Descripción: {description}\n\n"
                f"Responde: /aprobar {req.id} o /rechazar {req.id}"
            )
            try:
                await self._notify_callback(OWNER_ID, msg)
            except Exception as e:
                logger.error(f"Error notifying owner: {e}")

        logger.info(f"Approval requested: {req.id} from {agent}")
        return req.id

    def approve(self, request_id: str) -> bool:
        """Leo aprueba una solicitud."""
        for req in self._pending:
            if req["id"] == request_id and req["status"] == "pending":
                req["status"] = "approved"
                req["resolved_at"] = time.time()
                self._save()
                logger.info(f"Approved: {request_id}")
                return True
        return False

    def reject(self, request_id: str) -> bool:
        """Leo rechaza una solicitud."""
        for req in self._pending:
            if req["id"] == request_id and req["status"] == "pending":
                req["status"] = "rejected"
                req["resolved_at"] = time.time()
                self._save()
                logger.info(f"Rejected: {request_id}")
                return True
        return False

    def is_approved(self, request_id: str) -> bool:
        """Verifica si una solicitud fue aprobada."""
        for req in self._pending:
            if req["id"] == request_id:
                return req["status"] == "approved"
        return False

    def get_pending(self) -> list:
        """Devuelve solicitudes pendientes."""
        return [r for r in self._pending if r["status"] == "pending"]

    def _load(self) -> list:
        if os.path.exists(APPROVALS_FILE):
            try:
                with open(APPROVALS_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save(self):
        with open(APPROVALS_FILE, "w") as f:
            json.dump(self._pending, f, ensure_ascii=False, indent=2)


# Singleton
approvals = ApprovalSystem()
