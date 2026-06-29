# -*- coding: utf-8 -*-
"""
TOOL: Code Executor — Ejecuta código Python de forma segura
"""
import sys
import io
import traceback


def execute_python(code: str) -> str:
    """Ejecuta código Python y devuelve el output."""
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    
    try:
        exec(code, {"__builtins__": __builtins__})
        output = sys.stdout.getvalue()
        errors = sys.stderr.getvalue()
        result = output if output else "(sin output)"
        if errors:
            result += f"\nSTDERR: {errors}"
        return result[:3000]  # Limitar output
    except Exception:
        return f"Error:\n{traceback.format_exc()}"[:2000]
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr


def register_tools(registry):
    registry.register(
        name="execute_python",
        description="Ejecuta código Python. Usa para cálculos, procesamiento de datos, o demostrar algo con código.",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Código Python a ejecutar"}
            },
            "required": ["code"]
        },
        handler=execute_python
    )
