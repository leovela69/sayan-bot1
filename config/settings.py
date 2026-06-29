# -*- coding: utf-8 -*-
"""
SAYAN BOT — Configuracion central
Todas las keys se leen de variables de entorno.
"""
import os

# Auto-cargar .env si existe
_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(_env_path):
    with open(_env_path, "r") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _val = _line.split("=", 1)
                _key = _key.strip()
                _val = _val.strip().strip('"').strip("'")
                if _key and _key not in os.environ:
                    os.environ[_key] = _val

# --- Telegram ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
BOT_NAME = os.environ.get("BOT_NAME", "Sayanyin_Bot")

# --- LLM (OpenRouter — Hermes 4 gratuito) ---
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# Hermes 4 14B (gratis, mejor tool-calling del mercado)
LLM_MODEL = os.environ.get("LLM_MODEL", "nousresearch/hermes-4-scout")
LLM_FALLBACK = os.environ.get("LLM_FALLBACK", "deepseek/deepseek-chat-v3-0324:free")

# --- Memoria ---
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
MEMORY_DIR = os.path.join(DATA_DIR, "memory")
SKILLS_DIR = os.path.join(DATA_DIR, "skills")
LOGS_DIR = os.path.join(DATA_DIR, "logs")

# --- Herramientas externas (opcionales) ---
SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# --- Server ---
PORT = int(os.environ.get("PORT", "8080"))

# Asegurar directorios
for d in [DATA_DIR, MEMORY_DIR, SKILLS_DIR, LOGS_DIR]:
    os.makedirs(d, exist_ok=True)
