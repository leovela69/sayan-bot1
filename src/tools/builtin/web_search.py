# -*- coding: utf-8 -*-
"""
TOOL: Web Search — Busca información en internet
"""
import httpx


async def search_web(query: str, num_results: int = 5) -> str:
    """Busca en internet usando DuckDuckGo (gratis, sin API key)."""
    try:
        url = "https://api.duckduckgo.com/"
        params = {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            data = resp.json()
        
        results = []
        # Abstract
        if data.get("Abstract"):
            results.append(f"Resumen: {data['Abstract']}")
        # Related topics
        for topic in data.get("RelatedTopics", [])[:num_results]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(topic["Text"])
        
        if not results:
            # Fallback: use instant answer
            if data.get("Answer"):
                return f"Respuesta: {data['Answer']}"
            return f"No encontré resultados para: {query}"
        
        return "\n".join(results[:num_results])
    except Exception as e:
        return f"Error buscando: {str(e)}"


def register_tools(registry):
    registry.register(
        name="web_search",
        description="Busca información en internet. Usa cuando necesites datos actuales, noticias, o información que no tienes.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Qué buscar"},
                "num_results": {"type": "integer", "description": "Cantidad de resultados (default 5)"}
            },
            "required": ["query"]
        },
        handler=search_web
    )
