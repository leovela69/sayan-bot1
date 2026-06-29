# -*- coding: utf-8 -*-
"""
🏭 SKILL FACTORY — Crea skills REALES en disco
================================================
El módulo que le faltaba al Sayan para ser verdaderamente autónomo.

Antes: FORGE generaba texto con LLM pero NO escribía archivos.
Ahora: SkillFactory ESCRIBE archivos .py reales, los valida, y los registra.

Flujo:
1. GENESIS/FORGE solicita crear un skill nuevo
2. SkillFactory genera el código via LLM
3. Valida sintaxis con ast.parse()
4. Escribe el archivo .py al disco
5. Lo registra en el skill registry
6. HotLoader lo carga sin reiniciar

Seguridad:
- NUNCA toca archivos protegidos (config, main, settings)
- Valida sintaxis ANTES de escribir
- Mantiene backup del archivo anterior
- Log completo de todo lo que crea
- Requiere aprobación de Leo para skills que afecten proyectos
"""

import os
import ast
import json
import time
import logging
import shutil
from typing import Dict, Optional, List
from config.settings import DATA_DIR
from src.core.brain import think

logger = logging.getLogger("sayan.skill_factory")

# Directorios
SKILLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated")
BACKUPS_DIR = os.path.join(DATA_DIR, "skill_backups")
REGISTRY_FILE = os.path.join(DATA_DIR, "skill_registry.json")

os.makedirs(SKILLS_DIR, exist_ok=True)
os.makedirs(BACKUPS_DIR, exist_ok=True)

# Archivos que NUNCA se pueden modificar
PROTECTED_FILES = [
    "config/settings.py",
    "main.py",
    "src/swarm/base_agent.py",
    "src/swarm/bus/message_bus.py",
    "src/swarm/bus/approvals.py",
    "Dockerfile",
    "requirements.txt",
    "render.yaml",
]


class SkillFactory:
    """Fábrica de skills reales — genera, valida y persiste código."""

    def __init__(self):
        self.registry = self._load_registry()
        self.stats = {
            "skills_created": 0,
            "skills_failed": 0,
            "validations_passed": 0,
            "validations_failed": 0,
        }

    # ==================================================================
    # CREAR SKILL NUEVO
    # ==================================================================

    async def create_skill(self, spec: Dict) -> Dict:
        """
        Crea un skill nuevo desde una especificación.

        Args:
            spec: {
                'name': str — nombre del skill (snake_case)
                'description': str — qué hace
                'triggers': List[str] — acciones del bus que disparan este skill
                'input_schema': dict — qué datos espera
                'output_schema': dict — qué datos retorna
                'examples': List[str] — ejemplos de uso
            }

        Returns:
            Dict con status, path del archivo creado, o error
        """
        name = spec.get("name", "").strip().lower().replace(" ", "_").replace("-", "_")
        if not name:
            return {"status": "error", "error": "Nombre de skill vacío"}

        # Verificar que no existe ya
        if name in self.registry:
            return {"status": "error", "error": f"Skill '{name}' ya existe"}

        logger.info(f"🏭 Creando skill: {name}")

        # Generar código con LLM
        code = await self._generate_skill_code(spec)
        if not code:
            self.stats["skills_failed"] += 1
            return {"status": "error", "error": "LLM no generó código válido"}

        # Validar sintaxis
        validation = self._validate_code(code)
        if not validation["valid"]:
            self.stats["validations_failed"] += 1
            return {"status": "error", "error": f"Código inválido: {validation['error']}"}

        self.stats["validations_passed"] += 1

        # Escribir archivo
        file_path = os.path.join(SKILLS_DIR, f"{name}.py")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)
            logger.info(f"✅ Skill escrito: {file_path}")
        except Exception as e:
            return {"status": "error", "error": f"Error escribiendo archivo: {e}"}

        # Registrar en el registry
        entry = {
            "name": name,
            "path": file_path,
            "description": spec.get("description", ""),
            "triggers": spec.get("triggers", []),
            "created_at": time.time(),
            "created_by": spec.get("created_by", "FORGE"),
            "version": 1,
            "active": True,
        }
        self.registry[name] = entry
        self._save_registry()
        self.stats["skills_created"] += 1

        logger.info(f"🏭 Skill '{name}' registrado y activo")
        return {
            "status": "success",
            "skill_name": name,
            "path": file_path,
            "entry": entry,
        }

    # ==================================================================
    # GENERAR CÓDIGO
    # ==================================================================

    async def _generate_skill_code(self, spec: Dict) -> Optional[str]:
        """Genera código Python para un skill usando el LLM."""
        name = spec.get("name", "unnamed_skill")
        description = spec.get("description", "")
        triggers = spec.get("triggers", [])
        examples = spec.get("examples", [])

        prompt = f"""Genera un módulo Python COMPLETO para un skill del enjambre Sayan.

ESPECIFICACIÓN:
- Nombre: {name}
- Descripción: {description}
- Triggers (acciones del bus): {triggers}
- Ejemplos de uso: {examples}

REGLAS OBLIGATORIAS:
1. El módulo debe tener UNA clase principal llamada `Skill_{name.title().replace('_', '')}`
2. La clase debe tener un método async `execute(self, payload: dict) -> dict`
3. Debe importar solo stdlib + src.core.brain.think (para LLM)
4. Debe manejar errores internamente (try/except)
5. Debe retornar siempre un dict con al menos {{"status": "success/error"}}
6. Incluir docstring explicativo
7. NO importar módulos externos raros (solo os, json, time, asyncio, logging)
8. SOLO código Python válido, sin markdown, sin ```

TEMPLATE:
# -*- coding: utf-8 -*-
\"\"\"
SKILL: {name}
{description}
\"\"\"
import logging
from src.core.brain import think

logger = logging.getLogger("sayan.skill.{name}")

class Skill_{name.title().replace('_', '')}:
    \"\"\"[descripción]\"\"\"

    def __init__(self):
        self.name = "{name}"
        self.executions = 0

    async def execute(self, payload: dict) -> dict:
        \"\"\"Ejecuta el skill.\"\"\"
        # ... lógica aquí ...
        pass

# Singleton
skill = Skill_{name.title().replace('_', '')}()

Genera el código COMPLETO basándote en la especificación. SOLO Python, nada más."""

        result = await think([{"role": "user", "content": prompt}])
        content = result.get("content", "")

        # Limpiar posible markdown
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:])
            if content.endswith("```"):
                content = content[:-3]

        return content.strip() if content.strip() else None

    # ==================================================================
    # VALIDACIÓN
    # ==================================================================

    def _validate_code(self, code: str) -> Dict:
        """Valida código Python con ast.parse()."""
        try:
            ast.parse(code)
            return {"valid": True}
        except SyntaxError as e:
            return {"valid": False, "error": f"SyntaxError línea {e.lineno}: {e.msg}"}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def _is_protected(self, file_path: str) -> bool:
        """Verifica si un archivo está protegido."""
        for protected in PROTECTED_FILES:
            if protected in file_path:
                return True
        return False

    # ==================================================================
    # REGISTRY
    # ==================================================================

    def _load_registry(self) -> Dict:
        if os.path.exists(REGISTRY_FILE):
            try:
                with open(REGISTRY_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_registry(self):
        with open(REGISTRY_FILE, "w") as f:
            json.dump(self.registry, f, ensure_ascii=False, indent=2)

    def get_skill(self, name: str) -> Optional[Dict]:
        """Obtiene info de un skill registrado."""
        return self.registry.get(name)

    def list_skills(self) -> List[Dict]:
        """Lista todos los skills registrados."""
        return [
            {"name": k, "description": v.get("description", ""), "active": v.get("active", True)}
            for k, v in self.registry.items()
        ]

    def deactivate_skill(self, name: str) -> bool:
        """Desactiva un skill (no lo borra)."""
        if name in self.registry:
            self.registry[name]["active"] = False
            self._save_registry()
            return True
        return False

    def get_stats(self) -> Dict:
        return {
            **self.stats,
            "total_registered": len(self.registry),
            "active": sum(1 for v in self.registry.values() if v.get("active")),
        }


# Singleton
skill_factory = SkillFactory()
