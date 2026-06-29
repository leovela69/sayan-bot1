# -*- coding: utf-8 -*-
"""
🧬 CODE EVOLVER — Evoluciona código existente del bot
======================================================
GENESIS propone mejoras → CodeEvolver las implementa de verdad.

Flujo:
1. Recibe propuesta de evolución (de GENESIS o FORGE)
2. Lee el archivo actual
3. Genera la versión mejorada con LLM
4. Valida con ast.parse()
5. Hace backup del original
6. Escribe la versión nueva
7. (Opcional) Push a GitHub para redeploy

Seguridad:
- Archivos protegidos: NUNCA se tocan
- Siempre backup antes de escribir
- Validación AST obligatoria
- Max 3 evoluciones por hora (rate limit)
- Log de todo lo que modifica
"""

import os
import ast
import json
import time
import shutil
import logging
from typing import Dict, Optional, List
from config.settings import DATA_DIR
from src.core.brain import think

logger = logging.getLogger("sayan.code_evolver")


# Directorios
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
BACKUPS_DIR = os.path.join(DATA_DIR, "code_backups")
EVOLUTION_LOG = os.path.join(DATA_DIR, "evolution_log.json")

os.makedirs(BACKUPS_DIR, exist_ok=True)

# Archivos protegidos — NUNCA se modifican
PROTECTED_FILES = [
    "config/settings.py",
    "main.py",
    "Dockerfile",
    "requirements.txt",
    "render.yaml",
    ".env",
    ".env.example",
]

# Rate limiting
MAX_EVOLUTIONS_PER_HOUR = 3



class CodeEvolver:
    """Evoluciona código existente del bot de forma segura."""

    def __init__(self):
        self.log = self._load_log()
        self.evolutions_this_hour = 0
        self.hour_start = time.time()

    # ==================================================================
    # EVOLUCIONAR ARCHIVO
    # ==================================================================

    async def evolve_file(self, file_path: str, instruction: str,
                          auto_apply: bool = True) -> Dict:
        """
        Evoluciona un archivo existente con una instrucción.

        Args:
            file_path: Path relativo al repo (ej: src/swarm/capa1_cerebro/genesis.py)
            instruction: Qué mejorar/cambiar
            auto_apply: Si True, aplica automáticamente (si pasa validación)

        Returns:
            Dict con status, diff resumido, backup path
        """
        # Rate limit
        if not self._check_rate_limit():
            return {"status": "rate_limited",
                    "error": f"Max {MAX_EVOLUTIONS_PER_HOUR} evoluciones/hora"}

        # Verificar protección
        if self._is_protected(file_path):
            return {"status": "protected",
                    "error": f"Archivo protegido: {file_path}"}

        # Leer archivo actual
        full_path = os.path.join(REPO_ROOT, file_path)
        if not os.path.exists(full_path):
            return {"status": "error", "error": f"Archivo no existe: {file_path}"}

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                original_code = f.read()
        except Exception as e:
            return {"status": "error", "error": f"Error leyendo: {e}"}

        logger.info(f"🧬 Evolucionando: {file_path}")

        # Generar versión mejorada
        new_code = await self._generate_evolution(original_code, instruction, file_path)
        if not new_code:
            return {"status": "error", "error": "LLM no generó código"}

        # Validar
        validation = self._validate_code(new_code)
        if not validation["valid"]:
            return {"status": "invalid_code",
                    "error": f"Código generado inválido: {validation['error']}"}

        # Verificar que no es idéntico
        if new_code.strip() == original_code.strip():
            return {"status": "no_change", "message": "Código sin cambios"}

        if not auto_apply:
            return {
                "status": "preview",
                "original_lines": len(original_code.splitlines()),
                "new_lines": len(new_code.splitlines()),
                "instruction": instruction,
                "new_code_preview": new_code[:500],
            }

        # Backup
        backup_path = self._backup_file(full_path, file_path)

        # Aplicar
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_code)
            logger.info(f"✅ Evolución aplicada: {file_path}")
        except Exception as e:
            # Restaurar backup
            self._restore_backup(backup_path, full_path)
            return {"status": "error", "error": f"Error escribiendo: {e}"}

        # Registrar
        entry = {
            "file": file_path,
            "instruction": instruction,
            "timestamp": time.time(),
            "backup": backup_path,
            "original_lines": len(original_code.splitlines()),
            "new_lines": len(new_code.splitlines()),
        }
        self.log.append(entry)
        self._save_log()
        self.evolutions_this_hour += 1

        return {
            "status": "success",
            "file": file_path,
            "backup": backup_path,
            "lines_before": entry["original_lines"],
            "lines_after": entry["new_lines"],
        }


    # ==================================================================
    # ROLLBACK
    # ==================================================================

    def rollback_last(self) -> Dict:
        """Deshace la última evolución restaurando el backup."""
        if not self.log:
            return {"status": "error", "error": "No hay evoluciones para revertir"}

        last = self.log[-1]
        backup_path = last.get("backup")
        file_path = last.get("file")
        full_path = os.path.join(REPO_ROOT, file_path)

        if not backup_path or not os.path.exists(backup_path):
            return {"status": "error", "error": "Backup no encontrado"}

        try:
            shutil.copy2(backup_path, full_path)
            self.log.pop()
            self._save_log()
            logger.info(f"↩️ Rollback exitoso: {file_path}")
            return {"status": "success", "reverted": file_path}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ==================================================================
    # GENERAR EVOLUCIÓN CON LLM
    # ==================================================================

    async def _generate_evolution(self, original: str, instruction: str,
                                   file_path: str) -> Optional[str]:
        """Genera versión mejorada del código."""
        prompt = f"""Eres un ingeniero de software experto. Evoluciona este código Python.

ARCHIVO: {file_path}
INSTRUCCIÓN: {instruction}

CÓDIGO ACTUAL:
```python
{original}
```

REGLAS:
1. Retorna el archivo COMPLETO modificado (no solo el diff)
2. Mantén la estructura general y los imports
3. Aplica SOLO lo que pide la instrucción
4. No rompas funcionalidad existente
5. Mantén docstrings y comentarios relevantes
6. SOLO código Python, sin markdown, sin explicaciones
7. El resultado debe ser sintácticamente válido

Genera el código mejorado completo:"""

        result = await think([{"role": "user", "content": prompt}])
        content = result.get("content", "")

        # Limpiar markdown si hay
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:])
            if content.rstrip().endswith("```"):
                content = content.rstrip()[:-3]

        return content.strip() if content.strip() else None


    # ==================================================================
    # PUSH A GITHUB (opcional)
    # ==================================================================

    async def push_evolution(self, message: str = "auto: evolution") -> Dict:
        """Push cambios a GitHub (trigger redeploy en Render)."""
        import subprocess

        try:
            # git add + commit + push
            subprocess.run(["git", "add", "-A"], cwd=REPO_ROOT,
                          capture_output=True, timeout=10)
            subprocess.run(
                ["git", "commit", "-m", f"🧬 {message}"],
                cwd=REPO_ROOT, capture_output=True, timeout=10
            )
            result = subprocess.run(
                ["git", "push", "origin", "main"],
                cwd=REPO_ROOT, capture_output=True, timeout=30
            )
            if result.returncode == 0:
                logger.info(f"📤 Push exitoso: {message}")
                return {"status": "pushed", "message": message}
            else:
                error = result.stderr.decode()[:200]
                return {"status": "push_failed", "error": error}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ==================================================================
    # UTILIDADES
    # ==================================================================

    def _validate_code(self, code: str) -> Dict:
        """Valida sintaxis Python."""
        try:
            ast.parse(code)
            return {"valid": True}
        except SyntaxError as e:
            return {"valid": False, "error": f"Línea {e.lineno}: {e.msg}"}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def _is_protected(self, file_path: str) -> bool:
        """Verifica si el archivo está protegido."""
        for p in PROTECTED_FILES:
            if p in file_path:
                return True
        return False

    def _backup_file(self, full_path: str, rel_path: str) -> str:
        """Crea backup del archivo original."""
        timestamp = int(time.time())
        safe_name = rel_path.replace("/", "_").replace("\\", "_")
        backup_path = os.path.join(BACKUPS_DIR, f"{safe_name}.{timestamp}.bak")
        shutil.copy2(full_path, backup_path)
        return backup_path

    def _restore_backup(self, backup_path: str, target_path: str):
        """Restaura un backup."""
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, target_path)

    def _check_rate_limit(self) -> bool:
        """Verifica rate limit (max 3/hora)."""
        now = time.time()
        if now - self.hour_start > 3600:
            self.hour_start = now
            self.evolutions_this_hour = 0
        return self.evolutions_this_hour < MAX_EVOLUTIONS_PER_HOUR

    def _load_log(self) -> List:
        if os.path.exists(EVOLUTION_LOG):
            try:
                with open(EVOLUTION_LOG, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_log(self):
        # Mantener últimas 200
        if len(self.log) > 200:
            self.log = self.log[-200:]
        with open(EVOLUTION_LOG, "w") as f:
            json.dump(self.log, f, ensure_ascii=False, indent=2)

    def get_stats(self) -> Dict:
        return {
            "total_evolutions": len(self.log),
            "this_hour": self.evolutions_this_hour,
            "max_per_hour": MAX_EVOLUTIONS_PER_HOUR,
            "last_5": self.log[-5:] if self.log else [],
        }


# Singleton
code_evolver = CodeEvolver()
