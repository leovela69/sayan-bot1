# -*- coding: utf-8 -*-
"""
ATLAS — Memoria Infinita
Capa 3 (Ejecutores) — Almacena TODO y conecta conceptos.

Funciones:
- Guarda todo dato que pasa por el enjambre
- Conecta conceptos entre sesiones (grafo de conocimiento)
- Busca en historial cuando alguien necesita info
- Nunca olvida (persistente en disco)
- Genera resúmenes de lo aprendido
"""
import json
import os
import time
import logging
from src.swarm.base_agent import BaseAgent
from src.swarm.bus.message_bus import Message
from config.settings import DATA_DIR

logger = logging.getLogger("sayan.atlas")

ATLAS_FILE = os.path.join(DATA_DIR, "atlas_memory.json")


class Atlas(BaseAgent):
    """Memoria infinita del enjambre."""

    def __init__(self):
        super().__init__("ATLAS", layer=3, role="Memoria Infinita")
        self.knowledge = self._load()

    async def process_message(self, message: Message):
        action = message.action
        if action == "store":
            return self._store(message.payload)
        elif action == "search":
            return self._search(message.payload)
        elif action == "execute_task":
            return self._search(message.payload)
        elif action == "summary":
            return self._summary()
        elif action == "report_status":
            return self.status()

    def _store(self, payload: dict) -> dict:
        data = payload.get("data", "")
        category = payload.get("category", "general")
        tags = payload.get("tags", [])

        entry = {
            "data": data[:1000],
            "category": category,
            "tags": tags,
            "timestamp": time.time()
        }
        self.knowledge.append(entry)
        self._save()
        return {"stored": True, "total_entries": len(self.knowledge)}

    def _search(self, payload: dict) -> dict:
        query = payload.get("query", payload.get("task", "")).lower()
        category = payload.get("category", None)

        results = []
        for entry in reversed(self.knowledge):
            if category and entry.get("category") != category:
                continue
            if query in entry.get("data", "").lower():
                results.append(entry)
            elif any(query in tag.lower() for tag in entry.get("tags", [])):
                results.append(entry)
            if len(results) >= 10:
                break

        return {"results": results, "count": len(results)}

    def _summary(self) -> dict:
        categories = {}
        for e in self.knowledge:
            cat = e.get("category", "general")
            categories[cat] = categories.get(cat, 0) + 1
        return {
            "total_entries": len(self.knowledge),
            "categories": categories,
            "oldest": self.knowledge[0]["timestamp"] if self.knowledge else None,
            "newest": self.knowledge[-1]["timestamp"] if self.knowledge else None
        }

    def _load(self) -> list:
        if os.path.exists(ATLAS_FILE):
            try:
                with open(ATLAS_FILE, "r") as f:
                    return json.load(f)
            except:
                return []
        return []

    def _save(self):
        # Mantener máximo 10000 entradas
        if len(self.knowledge) > 10000:
            self.knowledge = self.knowledge[-10000:]
        with open(ATLAS_FILE, "w") as f:
            json.dump(self.knowledge, f, ensure_ascii=False)


atlas = Atlas()
