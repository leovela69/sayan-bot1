# -*- coding: utf-8 -*-
"""
SKILLS MANAGER — Progressive Disclosure estilo Antigravity.

Sistema de skills modulares que se desbloquean progresivamente:
- Nivel 1: Skills básicos (siempre disponibles)
- Nivel 2: Skills intermedios (se desbloquean con uso)
- Nivel 3: Skills avanzados (requieren cierto score/confianza)
- Nivel 4: Skills experimentales (auto-generados por el sistema)

Features:
- Hot-loading de skills (sin reiniciar)
- Skills como plugins (archivos .py independientes)
- Catálogo con descripciones
- Métricas por skill (uso, éxito, tiempo)
- Auto-disable si un skill falla mucho
- Skills aprendidos de interacciones
"""
import os
import json
import time
import logging
import importlib
import importlib.util
from typing import Dict, List, Optional, Callable, Any
from config.settings import SKILLS_DIR, DATA_DIR

logger = logging.getLogger("sayan.skills")

SKILLS_REGISTRY_FILE = os.path.join(DATA_DIR, "skills_registry.json")
os.makedirs(SKILLS_DIR, exist_ok=True)


class Skill:
    """Un skill individual."""

    def __init__(self, name: str, description: str, level: int = 1,
                 handler: Callable = None, category: str = "general"):
        self.name = name
        self.description = description
        self.level = level  # 1-4
        self.category = category
        self.handler = handler
        self.enabled = True
        self.locked = level > 1  # Niveles > 1 empiezan bloqueados

        # Métricas
        self.uses = 0
        self.successes = 0
        self.failures = 0
        self.total_time = 0
        self.last_used = 0
        self.created_at = time.time()

    @property
    def success_rate(self) -> float:
        if self.uses == 0:
            return 1.0
        return self.successes / self.uses

    @property
    def avg_time(self) -> float:
        if self.uses == 0:
            return 0
        return self.total_time / self.uses

    async def execute(self, *args, **kwargs) -> Any:
        """Ejecuta el skill."""
        if not self.enabled:
            raise RuntimeError(f"Skill '{self.name}' está deshabilitado")
        if self.locked:
            raise RuntimeError(f"Skill '{self.name}' está bloqueado (nivel {self.level})")

        self.uses += 1
        self.last_used = time.time()
        start = time.time()

        try:
            if self.handler:
                import asyncio
                if asyncio.iscoroutinefunction(self.handler):
                    result = await self.handler(*args, **kwargs)
                else:
                    result = self.handler(*args, **kwargs)
                self.successes += 1
                self.total_time += time.time() - start
                return result
            else:
                raise RuntimeError(f"Skill '{self.name}' no tiene handler")
        except Exception as e:
            self.failures += 1
            self.total_time += time.time() - start

            # Auto-disable si falla mucho
            if self.uses >= 5 and self.success_rate < 0.3:
                self.enabled = False
                logger.warning(f"Skill '{self.name}' auto-disabled (success rate: {self.success_rate:.0%})")

            raise

    def to_dict(self) -> Dict:
        return {
            "name": self.name, "description": self.description,
            "level": self.level, "category": self.category,
            "enabled": self.enabled, "locked": self.locked,
            "uses": self.uses, "successes": self.successes,
            "failures": self.failures, "success_rate": round(self.success_rate, 2),
            "avg_time": round(self.avg_time, 3), "last_used": self.last_used
        }


class SkillsManager:
    """Gestor de skills con progressive disclosure."""

    UNLOCK_THRESHOLDS = {
        2: {"total_uses": 20, "min_trust": 60},      # Nivel 2: 20 usos, trust 60+
        3: {"total_uses": 100, "min_trust": 75},     # Nivel 3: 100 usos, trust 75+
        4: {"total_uses": 500, "min_trust": 90},     # Nivel 4: 500 usos, trust 90+
    }

    def __init__(self):
        self.skills: Dict[str, Skill] = {}
        self.categories = ["general", "code", "research", "creative", "system", "learned"]
        self.total_uses = 0
        self.trust_score = 50  # Score de confianza del sistema (0-100)
        self._load_registry()
        self._register_builtin_skills()

    def _load_registry(self):
        """Carga registro de skills persistido."""
        if os.path.exists(SKILLS_REGISTRY_FILE):
            try:
                with open(SKILLS_REGISTRY_FILE, "r") as f:
                    data = json.load(f)
                self.total_uses = data.get("total_uses", 0)
                self.trust_score = data.get("trust_score", 50)
                logger.info(f"Skills registry loaded (trust: {self.trust_score})")
            except Exception:
                pass

    def _save_registry(self):
        """Persiste registro de skills."""
        try:
            data = {
                "total_uses": self.total_uses,
                "trust_score": self.trust_score,
                "skills": {n: s.to_dict() for n, s in self.skills.items()},
                "updated_at": time.time()
            }
            with open(SKILLS_REGISTRY_FILE, "w") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving skills registry: {e}")

    def _register_builtin_skills(self):
        """Registra skills built-in de nivel 1."""
        builtins = [
            ("respond", "Generar respuesta conversacional", 1, "general"),
            ("search_web", "Buscar información en internet", 1, "research"),
            ("generate_image", "Generar imágenes con IA", 1, "creative"),
            ("execute_code", "Ejecutar código Python", 1, "code"),
            ("remember", "Guardar en memoria", 1, "system"),
            ("analyze_data", "Analizar datos y estadísticas", 2, "research"),
            ("generate_report", "Generar reportes estructurados", 2, "general"),
            ("multi_search", "Búsqueda avanzada multi-fuente", 2, "research"),
            ("code_review", "Revisar y mejorar código", 2, "code"),
            ("create_agent", "Crear un subagente temporal", 3, "system"),
            ("modify_self", "Auto-modificar comportamiento", 3, "system"),
            ("deploy_code", "Desplegar código a producción", 3, "code"),
            ("train_model", "Entrenar modelo de ML", 4, "creative"),
            ("auto_evolve", "Auto-evolucionar arquitectura", 4, "system"),
        ]
        for name, desc, level, category in builtins:
            if name not in self.skills:
                self.skills[name] = Skill(name, desc, level, category=category)

    def register(self, name: str, description: str, handler: Callable,
                 level: int = 1, category: str = "general") -> Skill:
        """Registra un nuevo skill."""
        skill = Skill(name, description, level, handler, category)
        self.skills[name] = skill
        logger.info(f"Skill registered: {name} (L{level}, {category})")
        return skill

    async def execute(self, name: str, *args, **kwargs) -> Any:
        """Ejecuta un skill por nombre."""
        skill = self.skills.get(name)
        if not skill:
            raise ValueError(f"Skill no encontrado: {name}")

        # Check progressive disclosure
        self._check_unlock(skill)

        result = await skill.execute(*args, **kwargs)
        self.total_uses += 1

        # Actualizar trust
        self._update_trust(skill)
        self._save_registry()

        return result

    def _check_unlock(self, skill: Skill):
        """Verifica y desbloquea skills según progreso."""
        if not skill.locked:
            return

        threshold = self.UNLOCK_THRESHOLDS.get(skill.level, {})
        if (self.total_uses >= threshold.get("total_uses", 999999) and
                self.trust_score >= threshold.get("min_trust", 100)):
            skill.locked = False
            logger.info(f"SKILL UNLOCKED: {skill.name} (Level {skill.level})")

    def _update_trust(self, skill: Skill):
        """Actualiza trust score basado en uso exitoso."""
        if skill.success_rate > 0.8:
            self.trust_score = min(100, self.trust_score + 0.1)
        elif skill.success_rate < 0.3:
            self.trust_score = max(0, self.trust_score - 0.5)

    def learn_skill(self, name: str, description: str, code: str) -> Skill:
        """
        Aprende un nuevo skill de una interacción.
        Lo guarda como archivo .py en SKILLS_DIR.
        """
        # Guardar código del skill
        skill_file = os.path.join(SKILLS_DIR, f"{name}.py")
        try:
            with open(skill_file, "w") as f:
                f.write(f'"""{description}"""\n\n{code}')
            logger.info(f"Skill learned and saved: {name}")
        except Exception as e:
            logger.error(f"Error saving learned skill: {e}")

        # Registrar como nivel 4 (experimental)
        skill = Skill(name, description, level=4, category="learned")
        skill.locked = False  # Skills aprendidos se desbloquean inmediatamente
        self.skills[name] = skill
        self._save_registry()
        return skill

    def get_available(self, include_locked: bool = False) -> List[Dict]:
        """Skills disponibles (desbloqueados)."""
        skills = []
        for s in self.skills.values():
            if include_locked or (not s.locked and s.enabled):
                skills.append(s.to_dict())
        return sorted(skills, key=lambda x: (x["level"], x["name"]))

    def get_by_category(self, category: str) -> List[Dict]:
        """Skills por categoría."""
        return [s.to_dict() for s in self.skills.values()
                if s.category == category and not s.locked and s.enabled]

    def get_by_level(self, level: int) -> List[Dict]:
        """Skills por nivel."""
        return [s.to_dict() for s in self.skills.values() if s.level == level]

    def get_status(self) -> Dict:
        """Estado del sistema de skills."""
        levels = {1: 0, 2: 0, 3: 0, 4: 0}
        unlocked = {1: 0, 2: 0, 3: 0, 4: 0}
        for s in self.skills.values():
            levels[s.level] = levels.get(s.level, 0) + 1
            if not s.locked:
                unlocked[s.level] = unlocked.get(s.level, 0) + 1

        return {
            "total_skills": len(self.skills),
            "total_uses": self.total_uses,
            "trust_score": round(self.trust_score, 1),
            "by_level": levels,
            "unlocked_by_level": unlocked,
            "categories": {cat: len(self.get_by_category(cat)) for cat in self.categories},
            "top_used": sorted(
                [s.to_dict() for s in self.skills.values() if s.uses > 0],
                key=lambda x: x["uses"], reverse=True
            )[:5]
        }

    def unlock_all(self):
        """Desbloquea todos los skills (modo admin)."""
        for s in self.skills.values():
            s.locked = False
        logger.info("All skills unlocked (admin mode)")


# Singleton
skills_manager = SkillsManager()
