# -*- coding: utf-8 -*-
"""
TOOL: Image Generation — Genera imágenes con IA (Pollinations, gratis)
"""
import httpx


async def generate_image(prompt: str, style: str = "realistic") -> str:
    """Genera una imagen con IA. Devuelve URL de la imagen."""
    try:
        # Pollinations.ai — 100% gratis, sin API key
        encoded_prompt = prompt.replace(" ", "%20")
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&model=flux"
        
        # Verificar que la URL funciona
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.head(url)
            if resp.status_code < 400:
                return f"IMAGEN_URL:{url}"
        
        return f"Error: no se pudo generar la imagen"
    except Exception as e:
        return f"Error generando imagen: {str(e)}"


def register_tools(registry):
    registry.register(
        name="generate_image",
        description="Genera una imagen con IA desde un prompt de texto. Usa cuando pidan crear, dibujar, diseñar o generar una imagen.",
        parameters={
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Descripción de la imagen a generar (en inglés funciona mejor)"},
                "style": {"type": "string", "description": "Estilo: realistic, anime, art, pixel (default: realistic)"}
            },
            "required": ["prompt"]
        },
        handler=generate_image
    )
