# -*- coding: utf-8 -*-
"""
🔥 HOT LOADER — Carga módulos nuevos SIN reiniciar el bot
===========================================================
Permite que el Sayan cargue skills recién creados por SkillFactory
sin necesidad de hacer redeploy.

Funcionalidades:
- Importar módulo nuevo desde path
- Recargar módulo existente (importlib.reload)
- Registrar skill en el router de ejecución
- Descargar skill (unload)
- Listar skills cargados

Seguridad:
- Solo carga desde el directorio de skills generados
- Valida que el módulo tenga la estructura correcta
- Catch de errores en import (no crashea el bot)
"""

import os
import sys
import importlib
import importlib.util
import logging
import time
from typing import Dict, Optional, Callable, Any

logger = logging.getLogger("sayan.hot_loader")

# Directorio permitido para cargar skills
ALLOWED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated")
os.makedirs(ALLOWED_DIR, exist_ok=True)


class HotLoader:
    """Carga y descarga módulos Python dinámicamente."""

    def __init__(self):
        self.loaded_skills: Dict[str, Dict] = {}  # name → {module, instance, loaded_at}
        self._ensure_generated_package()

    def _ensure_generated_package(self):
        """Asegura que el directorio generated/ sea un paquete Python."""
        init_path = os.path.join(ALLOWED_DIR, "__init__.py")
        if not os.path.exists(init_path):
            with open(init_path, "w") as f:
                f.write("# Auto-generated skills package\n")

    # ==================================================================
    # CARGAR SKILL
    # ==================================================================

    def load_skill(self, skill_name: str) -> Dict:
        """
        Carga un skill desde el directorio de skills generados.

        Args:
            skill_name: Nombre del skill (sin .py)

        Returns:
            Dict con status y detalles
        """
        file_path = os.path.join(ALLOWED_DIR, f"{skill_name}.py")

        # Verificar que existe
        if not os.path.exists(file_path):
            return {"status": "error", "error": f"Archivo no encontrado: {file_path}"}

        # Verificar que está en directorio permitido
        real_path = os.path.realpath(file_path)
        if not real_path.startswith(os.path.realpath(ALLOWED_DIR)):
            return {"status": "error", "error": "Path fuera del directorio permitido"}

        # Si ya está cargado, recargar
        if skill_name in self.loaded_skills:
            return self.reload_skill(skill_name)

        # Importar dinámicamente
        try:
            module_name = f"src.swarm.skills.generated.{skill_name}"
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None:
                return {"status": "error", "error": "No se pudo crear spec del módulo"}

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Buscar la instancia singleton 'skill'
            instance = getattr(module, "skill", None)
            if instance is None:
                # Buscar cualquier clase que tenga 'execute'
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (hasattr(attr, "execute") and callable(getattr(attr, "execute", None))
                            and attr_name.startswith("Skill_")):
                        instance = attr()
                        break

            if instance is None:
                return {"status": "error", "error": "No se encontró instancia 'skill' ni clase Skill_*"}

            # Registrar
            self.loaded_skills[skill_name] = {
                "module": module,
                "instance": instance,
                "path": file_path,
                "loaded_at": time.time(),
                "reload_count": 0,
            }

            logger.info(f"🔥 Skill cargado: {skill_name}")
            return {"status": "success", "skill": skill_name, "instance": str(instance)}

        except Exception as e:
            logger.error(f"Error cargando skill {skill_name}: {e}")
            return {"status": "error", "error": str(e)}

    # ==================================================================
    # RECARGAR SKILL
    # ==================================================================

    def reload_skill(self, skill_name: str) -> Dict:
        """Recarga un skill ya cargado (después de modificación)."""
        if skill_name not in self.loaded_skills:
            return self.load_skill(skill_name)

        entry = self.loaded_skills[skill_name]
        module = entry["module"]

        try:
            importlib.reload(module)

            # Re-obtener instancia
            instance = getattr(module, "skill", None)
            if instance is None:
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if hasattr(attr, "execute") and attr_name.startswith("Skill_"):
                        instance = attr()
                        break

            entry["instance"] = instance
            entry["reload_count"] += 1
            entry["loaded_at"] = time.time()

            logger.info(f"🔄 Skill recargado: {skill_name} (reload #{entry['reload_count']})")
            return {"status": "success", "skill": skill_name, "reloaded": True}

        except Exception as e:
            logger.error(f"Error recargando skill {skill_name}: {e}")
            return {"status": "error", "error": str(e)}

    # ==================================================================
    # DESCARGAR SKILL
    # ==================================================================

    def unload_skill(self, skill_name: str) -> Dict:
        """Descarga un skill de memoria."""
        if skill_name not in self.loaded_skills:
            return {"status": "error", "error": f"Skill {skill_name} no está cargado"}

        entry = self.loaded_skills.pop(skill_name)
        module_name = f"src.swarm.skills.generated.{skill_name}"
        sys.modules.pop(module_name, None)

        logger.info(f"🗑️ Skill descargado: {skill_name}")
        return {"status": "success", "skill": skill_name, "unloaded": True}

    # ==================================================================
    # EJECUTAR SKILL
    # ==================================================================

    async def execute_skill(self, skill_name: str, payload: dict) -> Dict:
        """
        Ejecuta un skill cargado.

        Args:
            skill_name: Nombre del skill
            payload: Datos de entrada

        Returns:
            Resultado de la ejecución
        """
        if skill_name not in self.loaded_skills:
            # Intentar cargarlo primero
            load_result = self.load_skill(skill_name)
            if load_result["status"] != "success":
                return load_result

        entry = self.loaded_skills.get(skill_name)
        if not entry or not entry.get("instance"):
            return {"status": "error", "error": f"Skill {skill_name} sin instancia"}

        instance = entry["instance"]
        try:
            result = await instance.execute(payload)
            return result
        except Exception as e:
            logger.error(f"Error ejecutando skill {skill_name}: {e}")
            return {"status": "error", "error": str(e), "skill": skill_name}

    # ==================================================================
    # UTILIDADES
    # ==================================================================

    def list_loaded(self) -> list:
        """Lista skills actualmente cargados."""
        return [
            {
                "name": name,
                "loaded_at": info["loaded_at"],
                "reload_count": info["reload_count"],
            }
            for name, info in self.loaded_skills.items()
        ]

    def load_all_generated(self) -> Dict:
        """Carga todos los skills del directorio generated/."""
        results = {"loaded": [], "failed": []}

        for filename in os.listdir(ALLOWED_DIR):
            if filename.endswith(".py") and filename != "__init__.py":
                skill_name = filename[:-3]
                result = self.load_skill(skill_name)
                if result["status"] == "success":
                    results["loaded"].append(skill_name)
                else:
                    results["failed"].append({"name": skill_name, "error": result.get("error")})

        logger.info(f"🔥 Carga masiva: {len(results['loaded'])} OK, {len(results['failed'])} fallidos")
        return results

    def is_loaded(self, skill_name: str) -> bool:
        return skill_name in self.loaded_skills


# Singleton
hot_loader = HotLoader()
