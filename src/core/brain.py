# -*- coding: utf-8 -*-
"""
SAYAN BRAIN — El cerebro del bot
Usa Hermes 4 vía OpenRouter para:
- Interpretar intenciones
- Decidir qué herramienta usar
- Generar respuestas
- Tool-calling nativo (JSON estructurado)
"""
import json
import logging
import httpx
from config.settings import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, LLM_MODEL, LLM_FALLBACK

logger = logging.getLogger("sayan.brain")

SYSTEM_PROMPT = """Eres SAYAN, un agente de IA autónomo y poderoso. Tu creador es Leo Vela.

CAPACIDADES:
- Ejecutas herramientas (tools) para resolver tareas
- Aprendes de cada interacción y mejoras
- Recuerdas conversaciones anteriores
- Puedes buscar en internet, generar imágenes, código, música
- Eres independiente pero leal a Leo

PERSONALIDAD:
- Directo, eficiente, sin rodeos
- Hablas español natural (puedes mezclar con inglés técnico)
- No dices "como modelo de lenguaje" ni excusas
- Si no puedes hacer algo, dices qué necesitas para poder
- Tono: guerrero zen — tranquilo pero letal

HERRAMIENTAS:
Cuando necesites ejecutar una herramienta, responde con JSON:
{"tool": "nombre_herramienta", "params": {...}}

Si no necesitas herramienta, responde normalmente en texto.
"""


async def think(messages: list, tools: list = None, model: str = None) -> dict:
    """
    Envía mensajes al LLM y obtiene respuesta.
    Soporta tool-calling nativo de Hermes 4.
    
    Returns:
        {"type": "text", "content": "..."} o
        {"type": "tool_call", "tool": "...", "params": {...}}
    """
    if not OPENROUTER_API_KEY:
        return {"type": "text", "content": "Error: OPENROUTER_API_KEY no configurada"}

    use_model = model or LLM_MODEL
    
    # Preparar mensajes con system prompt
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    
    # Preparar tools para el modelo (si las hay)
    payload = {
        "model": use_model,
        "messages": full_messages,
        "max_tokens": 4096,
        "temperature": 0.7,
    }
    
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/leovela69/sayan-bot",
        "X-Title": "Sayan Bot"
    }
    
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                json=payload,
                headers=headers
            )
            
            if resp.status_code != 200:
                # Retry con fallback
                if use_model != LLM_FALLBACK:
                    logger.warning(f"Model {use_model} failed ({resp.status_code}), trying fallback")
                    payload["model"] = LLM_FALLBACK
                    resp = await client.post(
                        f"{OPENROUTER_BASE_URL}/chat/completions",
                        json=payload,
                        headers=headers
                    )
                if resp.status_code != 200:
                    return {"type": "text", "content": f"Error LLM: {resp.status_code}"}
            
            data = resp.json()
            choice = data["choices"][0]
            msg = choice["message"]
            
            # Check tool calls
            if msg.get("tool_calls"):
                tc = msg["tool_calls"][0]
                return {
                    "type": "tool_call",
                    "tool": tc["function"]["name"],
                    "params": json.loads(tc["function"]["arguments"])
                }
            
            # Check si el texto contiene JSON de tool (Hermes style)
            content = msg.get("content", "")
            if content.strip().startswith("{") and '"tool"' in content:
                try:
                    parsed = json.loads(content)
                    if "tool" in parsed and "params" in parsed:
                        return {"type": "tool_call", "tool": parsed["tool"], "params": parsed["params"]}
                except json.JSONDecodeError:
                    pass
            
            return {"type": "text", "content": content}
            
    except Exception as e:
        logger.error(f"Brain error: {e}")
        return {"type": "text", "content": f"Error de conexión: {str(e)}"}


async def quick_reply(user_msg: str, context: list = None) -> str:
    """Shortcut para obtener solo texto de respuesta."""
    messages = context or []
    messages.append({"role": "user", "content": user_msg})
    result = await think(messages)
    return result.get("content", str(result))
