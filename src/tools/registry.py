# -*- coding: utf-8 -*-
"""
TOOL REGISTRY — Sistema auto-registrante de herramientas
Las tools se registran con un decorador y quedan disponibles para el brain.
"""
import logging
import importlib
import os
import asyncio

logger = logging.getLogger("sayan.tools")


class ToolRegistry:
    """Registro central de herramientas. Auto-descubre tools en src/tools/"""
    
    def __init__(self):
        self._tools = {}
        self._load_builtin_tools()
    
    def register(self, name: str, description: str, parameters: dict, handler):
        """Registra una herramienta."""
        self._tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "handler": handler
        }
        logger.info(f"Tool registered: {name}")
    
    def get_schemas(self) -> list:
        """Devuelve schemas OpenAI-compatible para el LLM."""
        schemas = []
        for name, tool in self._tools.items():
            schemas.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool["description"],
                    "parameters": tool["parameters"]
                }
            })
        return schemas
    
    async def execute(self, name: str, params: dict) -> str:
        """Ejecuta una herramienta por nombre."""
        if name not in self._tools:
            return f"Error: herramienta '{name}' no existe"
        
        handler = self._tools[name]["handler"]
        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**params)
            else:
                result = handler(**params)
            return str(result)
        except Exception as e:
            logger.error(f"Tool {name} error: {e}")
            return f"Error ejecutando {name}: {str(e)}"
    
    def list_tools(self) -> list:
        """Lista nombres de tools registradas."""
        return list(self._tools.keys())
    
    def _load_builtin_tools(self):
        """Auto-carga todas las tools en src/tools/builtin/"""
        builtin_dir = os.path.join(os.path.dirname(__file__), "builtin")
        if not os.path.exists(builtin_dir):
            os.makedirs(builtin_dir, exist_ok=True)
            return
        
        for filename in os.listdir(builtin_dir):
            if filename.endswith(".py") and not filename.startswith("_"):
                module_name = f"src.tools.builtin.{filename[:-3]}"
                try:
                    mod = importlib.import_module(module_name)
                    if hasattr(mod, "register_tools"):
                        mod.register_tools(self)
                except Exception as e:
                    logger.warning(f"Failed to load tool module {filename}: {e}")


# Decorador para registrar tools fácilmente
_global_registry = None

def tool(name: str, description: str, parameters: dict = None):
    """Decorador para registrar una función como herramienta."""
    def decorator(func):
        func._tool_meta = {
            "name": name,
            "description": description,
            "parameters": parameters or {"type": "object", "properties": {}}
        }
        return func
    return decorator
