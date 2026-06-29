# -*- coding: utf-8 -*-
"""
ANTIGRAVITY COMMANDS — Comandos de Telegram para los módulos Antigravity.

Nuevos comandos:
- /goal <tarea>       → Ejecución autónoma
- /schedule <tarea>   → Programar tarea recurrente
- /reelme <pregunta>  → Clarificación antes de ejecutar
- /artifacts          → Ver feed de artifacts
- /team <tarea>       → Ejecutar con equipo de agentes
- /memory <query>     → Buscar en memoria
- /evolve             → Forzar ciclo de evolución
- /audit              → Estado del auditor
- /skills             → Skills disponibles
- /executor           → Estado del async executor
- /handoff            → Estado de handoffs
- /mcp               → Estado de integraciones MCP
- /hooks             → Estado de hooks
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from config.settings import OWNER_ID

logger = logging.getLogger("sayan.antigravity_cmds")


def owner_only(func):
    """Decorator: solo Leo puede usar estos comandos."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != OWNER_ID:
            await update.message.reply_text("Sin permiso.")
            return
        return await func(update, context)
    return wrapper


async def cmd_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/goal — Ejecución autónoma sin confirmación."""
    from src.core.slash_commands import slash_engine
    args_text = " ".join(context.args) if context.args else ""
    if not args_text:
        await update.message.reply_text("Uso: /goal <describe qué quieres lograr>")
        return

    await update.message.reply_text(f"Ejecutando goal autónomo...\nTarea: {args_text}")
    await update.message.chat.send_action("typing")

    result = await slash_engine.execute(f"/goal {args_text}", update.effective_user.id)
    # Dividir si es largo
    if len(result) > 4000:
        for i in range(0, len(result), 4000):
            await update.message.reply_text(result[i:i+4000])
    else:
        await update.message.reply_text(result)


async def cmd_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/schedule — Programar tarea recurrente."""
    from src.core.slash_commands import slash_engine
    args_text = " ".join(context.args) if context.args else ""
    result = await slash_engine.execute(f"/schedule {args_text}", update.effective_user.id)
    await update.message.reply_text(result)


async def cmd_reelme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/reelme — Modo clarificación."""
    from src.core.slash_commands import slash_engine
    args_text = " ".join(context.args) if context.args else ""
    if not args_text:
        await update.message.reply_text("Uso: /reelme <lo que quieres hacer>")
        return

    await update.message.chat.send_action("typing")
    result = await slash_engine.execute(f"/reelme {args_text}", update.effective_user.id)
    await update.message.reply_text(result)


async def cmd_artifacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/artifacts — Ver feed de artifacts."""
    from src.core.slash_commands import slash_engine
    args_text = " ".join(context.args) if context.args else ""
    result = await slash_engine.execute(f"/artifacts {args_text}", update.effective_user.id)
    await update.message.reply_text(result)


async def cmd_team_exec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/team — Ejecutar tarea con equipo completo de agentes."""
    from src.core.slash_commands import slash_engine
    args_text = " ".join(context.args) if context.args else ""
    if not args_text:
        await update.message.reply_text("Uso: /team <tarea compleja>")
        return

    await update.message.reply_text(f"Desplegando equipo de agentes...\nTarea: {args_text}")
    await update.message.chat.send_action("typing")

    result = await slash_engine.execute(f"/team {args_text}", update.effective_user.id)
    if len(result) > 4000:
        for i in range(0, len(result), 4000):
            await update.message.reply_text(result[i:i+4000])
    else:
        await update.message.reply_text(result)


async def cmd_memory_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/memory — Buscar en memoria colectiva."""
    from src.core.slash_commands import slash_engine
    args_text = " ".join(context.args) if context.args else ""
    result = await slash_engine.execute(f"/memory {args_text}", update.effective_user.id)
    await update.message.reply_text(result)


async def cmd_evolve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/evolve — Forzar ciclo de evolución."""
    from src.core.slash_commands import slash_engine
    args_text = " ".join(context.args) if context.args else ""
    result = await slash_engine.execute(f"/evolve {args_text}", update.effective_user.id)
    await update.message.reply_text(result)


@owner_only
async def cmd_audit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/audit — Estado del auditor anti-cheating."""
    from src.core.auditor import auditor

    args = context.args
    if args and args[0] == "agent":
        # /audit agent <nombre>
        agent_name = args[1] if len(args) > 1 else ""
        if agent_name:
            score = auditor.get_agent_score(agent_name)
            txt = (
                f"AUDITOR — Agente: {agent_name}\n\n"
                f"Score promedio: {score['average_score']}\n"
                f"Auditorías: {score['total_audits']}\n"
                f"Nivel confianza: {score['trust_level']}\n"
                f"Alertas: {score['alerts']}\n"
                f"Veredictos: {score['verdicts']}"
            )
        else:
            txt = "Uso: /audit agent <nombre>"
        await update.message.reply_text(txt)
        return

    status = auditor.get_status()
    txt = (
        f"AUDITOR ANTI-CHEATING\n\n"
        f"Auditorías totales: {status['total_audits']}\n"
        f"Alertas totales: {status['total_alerts']}\n"
        f"Agentes auditados: {len(status['agents_audited'])}\n\n"
    )

    if status['recent_alerts']:
        txt += "Alertas recientes:\n"
        for a in status['recent_alerts'][-3:]:
            txt += f"  {a['agent']}: score {a['score']} — {a['flags'][:50]}\n"
        txt += "\n"

    if status['recent_audits']:
        txt += "Últimas auditorías:\n"
        for a in status['recent_audits'][-5:]:
            txt += f"  [{a['verdict']}] {a['agent']}/{a['action']} (score={a['score']})\n"

    txt += "\nUso: /audit agent <nombre>"
    await update.message.reply_text(txt[:4000])


@owner_only
async def cmd_skills(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/skills — Skills disponibles y estado."""
    from src.skills.manager import skills_manager

    args = context.args
    if args and args[0] == "unlock":
        skills_manager.unlock_all()
        await update.message.reply_text("Todos los skills desbloqueados (modo admin).")
        return

    status = skills_manager.get_status()
    txt = (
        f"SKILLS MANAGER\n\n"
        f"Total skills: {status['total_skills']}\n"
        f"Usos totales: {status['total_uses']}\n"
        f"Trust score: {status['trust_score']}\n\n"
        f"Por nivel:\n"
    )
    for lvl in range(1, 5):
        total = status['by_level'].get(lvl, 0)
        unlocked = status['unlocked_by_level'].get(lvl, 0)
        txt += f"  L{lvl}: {unlocked}/{total} desbloqueados\n"

    txt += f"\nCategorías: {status['categories']}\n"

    if status['top_used']:
        txt += "\nMás usados:\n"
        for s in status['top_used'][:5]:
            txt += f"  {s['name']}: {s['uses']} usos ({s['success_rate']*100:.0f}%)\n"

    txt += "\n/skills unlock — Desbloquear todos"
    await update.message.reply_text(txt[:4000])


@owner_only
async def cmd_executor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/executor — Estado del async executor."""
    from src.core.async_executor import executor

    status = executor.get_status()
    txt = (
        f"ASYNC EXECUTOR\n\n"
        f"Estado: {'ACTIVO' if status['active'] else 'INACTIVO'}\n"
        f"Concurrencia max: {status['max_concurrent']}\n"
        f"En cola: {status['queued']}\n"
        f"Ejecutando: {status['running']}\n"
        f"Completadas: {status['completed_total']}\n"
        f"Fallidas: {status['failed_total']}\n"
    )

    if status['running_tasks']:
        txt += "\nEjecutando ahora:\n"
        for t in status['running_tasks']:
            txt += f"  {t['name']} ({t['priority']})\n"

    if status['recent_completed']:
        txt += "\nRecientes completadas:\n"
        for t in status['recent_completed']:
            txt += f"  {t['name']} ({t['duration']:.1f}s)\n"

    if status['recent_failed']:
        txt += "\nRecientes fallidas:\n"
        for t in status['recent_failed']:
            txt += f"  {t['name']}: {t['error'][:50]}\n"

    await update.message.reply_text(txt[:4000])


@owner_only
async def cmd_handoff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/handoff — Estado de handoffs."""
    from src.core.handoff import handoff_manager

    status = handoff_manager.get_status()
    txt = (
        f"HANDOFF SYSTEM\n\n"
        f"Handoffs activos: {status['active_handoffs']}\n"
        f"Historial total: {status['total_history']}\n"
        f"Agentes con handoff: {status['agents_with_handoffs']}\n"
    )

    if status['last_5']:
        txt += "\nÚltimos handoffs:\n"
        for h in status['last_5']:
            txt += (
                f"  {h['agent']} — {h['decisions']} decisiones, "
                f"{h['pending_tasks']} pendientes, {h['knowledge']} conocimiento\n"
            )

    await update.message.reply_text(txt[:4000])


@owner_only
async def cmd_mcp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/mcp — Estado de integraciones MCP."""
    from src.core.mcp_integration import mcp

    args = context.args
    if args and args[0] == "discover":
        await update.message.reply_text("Descubriendo tools MCP...")
        results = await mcp.discover_all()
        txt = "MCP DISCOVERY\n\n"
        for name, tools in results.items():
            txt += f"  {name}: {len(tools)} tools\n"
            for t in tools[:3]:
                txt += f"    - {t.get('name', '?')}: {t.get('description', '')[:50]}\n"
        await update.message.reply_text(txt[:4000])
        return

    if args and args[0] == "add":
        # /mcp add <name> <url>
        if len(args) >= 3:
            name = args[1]
            url = args[2]
            mcp.register_server(name, url)
            await update.message.reply_text(f"Servidor MCP registrado: {name} ({url})")
        else:
            await update.message.reply_text("Uso: /mcp add <name> <url>")
        return

    status = mcp.get_status()
    txt = (
        f"MCP INTEGRATION\n\n"
        f"Servidores: {status['total_servers']}\n"
        f"Activos: {status['active_servers']}\n"
        f"Tools disponibles: {status['total_tools']}\n"
    )

    if status['servers']:
        txt += "\nServidores:\n"
        for name, s in status['servers'].items():
            txt += f"  {name}: {s['tools_count']} tools, {s['call_count']} calls\n"

    txt += "\n/mcp discover — Descubrir tools\n/mcp add <name> <url> — Añadir servidor"
    await update.message.reply_text(txt[:4000])


@owner_only
async def cmd_hooks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/hooks — Estado de hooks."""
    from src.core.hooks import hooks

    status = hooks.get_status()
    txt = (
        f"HOOKS SYSTEM\n\n"
        f"Total hooks: {status['total_hooks']}\n"
        f"Ejecuciones: {status['total_executions']}\n"
        f"Errores: {status['total_errors']}\n"
    )

    if status['by_point']:
        txt += "\nPor punto:\n"
        for point, count in status['by_point'].items():
            txt += f"  {point}: {count} hooks\n"

    await update.message.reply_text(txt[:4000])
