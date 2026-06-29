# SAYAN BOT

Bot autónomo independiente con framework Hermes Agent.
Aprende de cada interacción y mejora con el tiempo.

## Estructura

```
sayan-bot/
├── main.py                 ← Entry point
├── config/settings.py      ← Configuración
├── src/
│   ├── core/
│   │   ├── brain.py        ← LLM (Hermes 4 via OpenRouter)
│   │   └── router.py       ← Orquestador mensaje→tools→respuesta
│   ├── tools/
│   │   ├── registry.py     ← Sistema auto-registrante
│   │   └── builtin/        ← Tools incluidas
│   │       ├── web_search   ← Búsqueda internet
│   │       ├── image_gen    ← Generación de imágenes
│   │       ├── code_exec    ← Ejecutar Python
│   │       ├── datetime     ← Fecha/hora
│   │       └── reminder     ← Recordatorios
│   ├── memory/
│   │   └── store.py        ← Memoria persistente
│   ├── skills/             ← Skills auto-aprendidos
│   └── platforms/
│       └── telegram.py     ← Bot Telegram
├── data/                   ← Datos persistentes
├── .env.example            ← Variables de entorno
├── requirements.txt
└── Dockerfile
```

## Deploy en Render

1. Crea repo en GitHub
2. Conecta con Render (New Web Service)
3. Environment: Docker
4. Añade variables de entorno (ver .env.example)
5. Deploy

## Comandos

- `/start` — Inicio
- `/tools` — Ver herramientas
- `/reset` — Borrar memoria
- `/status` — Estado del bot
- O simplemente escríbele lo que necesites
