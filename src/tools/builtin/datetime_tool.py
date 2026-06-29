# -*- coding: utf-8 -*-
"""
TOOL: DateTime — Fecha y hora actual
"""
from datetime import datetime


def get_datetime(timezone: str = "Europe/Madrid") -> str:
    """Devuelve fecha y hora actual."""
    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo(timezone))
    except Exception:
        now = datetime.now()
    return now.strftime("%A %d de %B de %Y, %H:%M:%S")


def register_tools(registry):
    registry.register(
        name="get_datetime",
        description="Obtiene la fecha y hora actual. Usa cuando pregunten qué hora es o qué día es.",
        parameters={
            "type": "object",
            "properties": {
                "timezone": {"type": "string", "description": "Zona horaria (default Europe/Madrid)"}
            }
        },
        handler=get_datetime
    )
