# -*- coding: utf-8 -*-
"""
SAYAN BOT — Entry point
@Sayanyin_Bot — Bot autónomo independiente con enjambre de 10 agentes
"""
import sys
import os
import logging
import asyncio
import threading

# Setup path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

from src.platforms.telegram import run_telegram_bot
from src.swarm.circuit import run_circuit


async def main():
    """Arranca el bot de Telegram + el circuito del enjambre en paralelo."""
    print("=" * 50)
    print("  SAYAN BOT v1.0 — Enjambre Autónomo")
    print("  10 agentes | 4 capas | Circuito cerrado")
    print("=" * 50)

    # El circuito corre como tarea async en background
    circuit_task = asyncio.create_task(run_circuit(interval=30))

    # Auto-Healer corre en paralelo
    from src.swarm.skills.auto_repair.healer import healer
    healer_task = asyncio.create_task(healer.start())

    # API server para el puente con el Panteón
    from src.swarm.bridge.api_server import start_api_server
    api_runner = await start_api_server()

    # El bot de Telegram corre en el hilo principal
    from config.settings import TELEGRAM_BOT_TOKEN
    if not TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN no configurado")
        return

    from telegram.ext import Application, CommandHandler, MessageHandler, filters
    from src.platforms.telegram import (
        cmd_start, cmd_reset, cmd_tools, cmd_status,
        handle_message
    )

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Comandos base
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("tools", cmd_tools))
    app.add_handler(CommandHandler("status", cmd_status))

    # Comandos del enjambre
    from src.platforms.swarm_commands import (
        cmd_swarm, cmd_aprobar, cmd_rechazar, cmd_evoluciones,
        cmd_agentes, cmd_forge, cmd_atlas, cmd_healer
    )
    app.add_handler(CommandHandler("swarm", cmd_swarm))
    app.add_handler(CommandHandler("aprobar", cmd_aprobar))
    app.add_handler(CommandHandler("rechazar", cmd_rechazar))
    app.add_handler(CommandHandler("evoluciones", cmd_evoluciones))
    app.add_handler(CommandHandler("agentes", cmd_agentes))
    app.add_handler(CommandHandler("forge", cmd_forge))
    app.add_handler(CommandHandler("atlas", cmd_atlas))
    app.add_handler(CommandHandler("healer", cmd_healer))

    # Mensajes normales
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot Telegram + Circuito arrancando...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    # Mantener vivo
    try:
        await circuit_task
    except asyncio.CancelledError:
        pass
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
