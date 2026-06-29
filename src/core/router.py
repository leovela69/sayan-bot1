# -*- coding: utf-8 -*-
"""
SAYAN ROUTER — Orquesta el flujo: mensaje → brain → tools → respuesta
"""
import logging
from src.core.brain import think
from src.tools.registry import ToolRegistry
from src.memory.store import MemoryStore

logger = logging.getLogger("sayan.router")

memory = MemoryStore()
tools = ToolRegistry()


async def process_message(user_id: int, text: str, username: str = "") -> str:
    """
    Procesa un mensaje del usuario:
    1. Carga contexto de memoria
    2. Envía al brain con tools disponibles
    3. Si brain pide tool → ejecuta → envía resultado al brain
    4. Guarda en memoria
    5. Devuelve respuesta final
    """
    # 1. Cargar contexto
    context = memory.get_context(user_id, limit=10)
    
    # 2. Pensar
    messages = context + [{"role": "user", "content": text}]
    tool_schemas = tools.get_schemas()
    
    result = await think(messages, tools=tool_schemas)
    
    # 3. Si pide tool, ejecutar
    max_tool_loops = 5
    loops = 0
    while result["type"] == "tool_call" and loops < max_tool_loops:
        loops += 1
        tool_name = result["tool"]
        tool_params = result["params"]
        
        logger.info(f"Executing tool: {tool_name}({tool_params})")
        tool_result = await tools.execute(tool_name, tool_params)
        
        # Enviar resultado al brain para que formule respuesta
        messages.append({"role": "assistant", "content": f"[Tool: {tool_name}] Ejecutado"})
        messages.append({"role": "user", "content": f"Resultado de {tool_name}: {tool_result}"})
        result = await think(messages, tools=tool_schemas)
    
    # 4. Respuesta final
    response = result.get("content", "No pude procesar tu mensaje.")
    
    # 5. Guardar en memoria
    memory.save_message(user_id, "user", text, username=username)
    memory.save_message(user_id, "assistant", response)
    
    return response
