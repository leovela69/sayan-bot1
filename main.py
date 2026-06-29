# -*- coding: utf-8 -*-
"""
SAYAN BOT — Entry point
@Sayanyin_Bot — Bot autónomo independiente con enjambre de 10 agentes
+ Módulos Antigravity (Artifacts, Slash, Executor, Handoff, Auditor, Skills, MCP, Hooks)
"""
import sys
import os
import logging
import asyncio

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
    """Arranca el bot de Telegram + el circuito del enjambre + módulos Antigravity."""
    print("=" * 60)
    print("  SAYAN BOT v2.0 — Enjambre Autónomo + Antigravity")
    print("  10 agentes | 4 capas | 8 módulos Antigravity")
    print("=" * 60)

    # ===== MÓDULOS ANTIGRAVITY =====
    # Artifact Store (se auto-carga)
    from src.core.artifact import artifact_store
    artifact_store.start_session("boot")
    artifact_store.create("log", {"event": "boot", "version": "2.0"}, agent="SYSTEM", tags=["boot"])
    print("  ✓ Artifacts — Trazabilidad activa")

    # Slash Commands Engine
    from src.core.slash_commands import slash_engine
    print(f"  ✓ Slash Commands — {len(slash_engine.commands)} comandos")

    # Async Executor
    from src.core.async_executor import executor
    executor_task = asyncio.create_task(executor.start())
    print("  ✓ Async Executor — Fire-and-forget activo")

    # Handoff Manager
    from src.core.handoff import handoff_manager
    handoff_manager.start_handoff("SYSTEM", "boot")
    print(f"  ✓ Handoff System — Continuidad activa")

    # Auditor
    from src.core.auditor import auditor
    print("  ✓ Auditor — Anti-cheating activo")

    # Skills Manager
    from src.skills.manager import skills_manager
    print(f"  ✓ Skills Manager — {len(skills_manager.skills)} skills (trust: {skills_manager.trust_score})")

    # MCP Integration
    from src.core.mcp_integration import mcp
    print(f"  ✓ MCP Integration — {len(mcp.servers)} servidores")

    # Hooks Engine
    from src.core.hooks import hooks
    print(f"  ✓ Hooks Engine — {len(hooks.get_hooks())} hooks")

    # Cron Engine
    from src.core.cron_system import cron_engine
    cron_task = asyncio.create_task(cron_engine.start())
    print("  ✓ Cron Engine — Tareas programadas")

    print("=" * 60)

    # ===== ENJAMBRE =====
    # El circuito corre como tarea async en background
    circuit_task = asyncio.create_task(run_circuit(interval=30))

    # Auto-Healer corre en paralelo
    from src.swarm.skills.auto_repair.healer import healer
    healer_task = asyncio.create_task(healer.start())

    # API server para el puente con el Panteón
    from src.swarm.bridge.api_server import start_api_server
    api_runner = await start_api_server()

    # ===== TELEGRAM BOT =====
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

    # --- Comandos base ---
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("tools", cmd_tools))
    app.add_handler(CommandHandler("status", cmd_status))

    # --- Comandos del enjambre ---
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

    # --- Comandos Antigravity ---
    from src.platforms.antigravity_commands import (
        cmd_goal, cmd_schedule, cmd_reelme, cmd_artifacts,
        cmd_team_exec, cmd_memory_search, cmd_evolve,
        cmd_audit, cmd_skills, cmd_executor, cmd_handoff,
        cmd_mcp, cmd_hooks
    )
    app.add_handler(CommandHandler("goal", cmd_goal))
    app.add_handler(CommandHandler("schedule", cmd_schedule))
    app.add_handler(CommandHandler("reelme", cmd_reelme))
    app.add_handler(CommandHandler("artifacts", cmd_artifacts))
    app.add_handler(CommandHandler("team", cmd_team_exec))
    app.add_handler(CommandHandler("memory", cmd_memory_search))
    app.add_handler(CommandHandler("evolve", cmd_evolve))
    app.add_handler(CommandHandler("audit", cmd_audit))
    app.add_handler(CommandHandler("skills", cmd_skills))
    app.add_handler(CommandHandler("executor", cmd_executor))
    app.add_handler(CommandHandler("handoff", cmd_handoff))
    app.add_handler(CommandHandler("mcp", cmd_mcp))
    app.add_handler(CommandHandler("hooks", cmd_hooks))

    # --- Mensajes normales (con integración slash) ---
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("\nBot Telegram + Enjambre + Antigravity arrancando...")
    print(f"Comandos activos: {len(app.handlers[0])} handlers")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    # Artifact de boot completado
    artifact_store.create("milestone", {
        "event": "boot_complete",
        "handlers": len(app.handlers[0]),
        "modules": ["artifacts", "slash", "executor", "handoff", "auditor", "skills", "mcp", "hooks"]
    }, agent="SYSTEM", tags=["boot", "milestone"])

    # Mantener vivo
    try:
        await circuit_task
    except asyncio.CancelledError:
        pass
    finally:
        # Handoff de cierre
        handoff_manager.get_active("SYSTEM").add_knowledge("Sistema cerrado correctamente", "system")
        handoff_manager.finalize("SYSTEM")
        executor.stop()
        cron_engine.stop()
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
