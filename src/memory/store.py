# -*- coding: utf-8 -*-
"""
MEMORY STORE — Memoria persistente por usuario
Guarda conversaciones, aprende patrones, recuerda contexto.
"""
import json
import os
import time
import logging
from config.settings import MEMORY_DIR

logger = logging.getLogger("sayan.memory")


class MemoryStore:
    """Memoria persistente. Guarda y recupera contexto por usuario."""
    
    def __init__(self):
        self._cache = {}
    
    def save_message(self, user_id: int, role: str, content: str, username: str = ""):
        """Guarda un mensaje en la memoria del usuario."""
        user_file = self._user_file(user_id)
        history = self._load(user_file)
        
        history.append({
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "username": username
        })
        
        # Mantener máximo 200 mensajes por usuario
        if len(history) > 200:
            history = history[-200:]
        
        self._save(user_file, history)
    
    def get_context(self, user_id: int, limit: int = 10) -> list:
        """Recupera los últimos N mensajes como contexto para el LLM."""
        user_file = self._user_file(user_id)
        history = self._load(user_file)
        recent = history[-limit:] if history else []
        return [{"role": m["role"], "content": m["content"]} for m in recent]
    
    def get_full_history(self, user_id: int) -> list:
        """Devuelve todo el historial de un usuario."""
        return self._load(self._user_file(user_id))
    
    def clear(self, user_id: int):
        """Borra la memoria de un usuario."""
        user_file = self._user_file(user_id)
        self._save(user_file, [])
        logger.info(f"Memory cleared for user {user_id}")
    
    def save_learning(self, user_id: int, topic: str, lesson: str):
        """Guarda un aprendizaje específico (el bot aprende algo nuevo)."""
        learn_file = os.path.join(MEMORY_DIR, "learnings.json")
        learnings = self._load(learn_file) if os.path.exists(learn_file) else []
        learnings.append({
            "user_id": user_id,
            "topic": topic,
            "lesson": lesson,
            "timestamp": time.time()
        })
        self._save(learn_file, learnings)
    
    def get_learnings(self, topic: str = None) -> list:
        """Recupera aprendizajes (todos o por tema)."""
        learn_file = os.path.join(MEMORY_DIR, "learnings.json")
        if not os.path.exists(learn_file):
            return []
        learnings = self._load(learn_file)
        if topic:
            return [l for l in learnings if topic.lower() in l.get("topic", "").lower()]
        return learnings
    
    def _user_file(self, user_id: int) -> str:
        return os.path.join(MEMORY_DIR, f"user_{user_id}.json")
    
    def _load(self, filepath: str) -> list:
        if filepath in self._cache:
            return self._cache[filepath]
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                self._cache[filepath] = data
                return data
            except Exception:
                return []
        return []
    
    def _save(self, filepath: str, data):
        self._cache[filepath] = data
        with open(filepath, "w") as f:
            json.dump(data, f, ensure_ascii=False)
