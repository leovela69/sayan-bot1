# -*- coding: utf-8 -*-
"""
TOOL: Reminder — Programa recordatorios
"""
import json
import os
import time
from config.settings import DATA_DIR

REMINDERS_FILE = os.path.join(DATA_DIR, "reminders.json")


def set_reminder(text: str, minutes: int, user_id: int = 0) -> str:
    """Programa un recordatorio para X minutos."""
    reminders = _load_reminders()
    reminder = {
        "text": text,
        "trigger_at": time.time() + (minutes * 60),
        "user_id": user_id,
        "created_at": time.time()
    }
    reminders.append(reminder)
    _save_reminders(reminders)
    return f"Recordatorio programado: '{text}' en {minutes} minutos"


def list_reminders(user_id: int = 0) -> str:
    """Lista recordatorios pendientes."""
    reminders = _load_reminders()
    active = [r for r in reminders if r["trigger_at"] > time.time()]
    if not active:
        return "No hay recordatorios pendientes"
    lines = []
    for r in active:
        mins_left = int((r["trigger_at"] - time.time()) / 60)
        lines.append(f"- {r['text']} (en {mins_left} min)")
    return "\n".join(lines)


def _load_reminders():
    if os.path.exists(REMINDERS_FILE):
        with open(REMINDERS_FILE, "r") as f:
            return json.load(f)
    return []


def _save_reminders(data):
    with open(REMINDERS_FILE, "w") as f:
        json.dump(data, f)


def register_tools(registry):
    registry.register(
        name="set_reminder",
        description="Programa un recordatorio. Usa cuando pidan recordar algo en X minutos/horas.",
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Qué recordar"},
                "minutes": {"type": "integer", "description": "En cuántos minutos recordar"},
                "user_id": {"type": "integer", "description": "ID del usuario"}
            },
            "required": ["text", "minutes"]
        },
        handler=set_reminder
    )
    registry.register(
        name="list_reminders",
        description="Lista todos los recordatorios pendientes.",
        parameters={
            "type": "object",
            "properties": {
                "user_id": {"type": "integer", "description": "ID del usuario"}
            }
        },
        handler=list_reminders
    )
