# -*- coding: utf-8 -*-
"""
SAYAN ROUTER — Orquesta el flujo: mensaje → brain → tools → respuesta
Integrado con módulos Antigravity: Slash Commands, Auditor, Artifacts, Hooks.
"""
import time
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
    1. Check si es slash command → delegar
    2. Hook before_response
    3. Carga contexto de memoria
    4. Envía al brain con tools disponibles
    5. Si brain pide tool → ejecuta → audita → envía resultado al brain
    6. Hook after_response
    7. Guarda en memoria + artifact
    8. Devuelve respuesta final
    """
    # 0. Slash commands
    from src.core.slash_commands import slash_engine
    if slash_engine.is_slash_command(text):
        return await slash_engine.execute(text, user_id)

    # 1. Hook: before_response
    from src.core.hooks import hooks
    hook_data = await hooks.trigger("on_message", {
        "user_id": user_id, "text": text, "username": username
    })

    # 2. Cargar contexto (incluye handoff context si existe)
    context = memory.get_context(user_id, limit=10)

    # Inyectar continuation context del handoff si existe
    from src.core.handoff import handoff_manager
    continuation = handoff_manager.get_continuation_context(f"user_{user_id}")
    if continuation:
        context = [{"role": "system", "content": continuation}] + context

    # 3. Pensar
    messages = context + [{"role": "user", "content": text}]
    tool_schemas = tools.get_schemas()

    # Añadir MCP tools si hay
    from src.core.mcp_integration import mcp
    mcp_schemas = mcp.get_tool_schemas()
    if mcp_schemas:
        tool_schemas = tool_schemas + mcp_schemas

    start_time = time.time()
    result = await think(messages, tools=tool_schemas)

    # 4. Si pide tool, ejecutar + auditar
    from src.core.auditor import auditor
    max_tool_loops = 5
    loops = 0
    tool_calls_made = []

    while result["type"] == "tool_call" and loops < max_tool_loops:
        loops += 1
        tool_name = result["tool"]
        tool_params = result["params"]

        logger.info(f"Executing tool: {tool_name}({tool_params})")
        tool_calls_made.append(tool_name)

        # Check si es MCP tool
        if tool_name.startswith("mcp_"):
            real_name = tool_name[4:]  # quitar prefijo mcp_
            tool_result = await mcp.call_tool(real_name, tool_params)
            tool_result = str(tool_result.get("result", tool_result.get("error", "no result")))
        else:
            tool_result = await tools.execute(tool_name, tool_params)

        # Hook: after_tool
        await hooks.trigger("after_tool", {
            "tool": tool_name, "params": tool_params, "result": str(tool_result)[:200]
        })

        # Enviar resultado al brain para que formule respuesta
        messages.append({"role": "assistant", "content": f"[Tool: {tool_name}] Ejecutado"})
        messages.append({"role": "user", "content": f"Resultado de {tool_name}: {tool_result}"})
        result = await think(messages, tools=tool_schemas)

    # 5. Respuesta final
    response = result.get("content", "No pude procesar tu mensaje.")
    execution_time = time.time() - start_time

    # 6. Auditar la respuesta
    audit_result = auditor.audit_response(
        agent="BRAIN",
        action="respond",
        input_data=text,
        output_data=response,
        execution_time=execution_time,
        tool_calls=tool_calls_made
    )

    # 7. Hook: after_response
    await hooks.trigger("after_response", {
        "user_id": user_id, "text": text, "response": response[:200],
        "audit_score": audit_result.score, "tools_used": tool_calls_made
    })

    # 8. Guardar en memoria
    memory.save_message(user_id, "user", text, username=username)
    memory.save_message(user_id, "assistant", response)

    # 9. Artifact de la interacción
    from src.core.artifact import artifact_store
    artifact_store.create("log", {
        "user_id": user_id, "input": text[:100],
        "response": response[:100], "tools": tool_calls_made,
        "audit_score": audit_result.score,
        "duration": round(execution_time, 2)
    }, agent="ROUTER", tags=["interaction", f"user_{user_id}"])

    return response
