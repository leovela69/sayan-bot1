# -*- coding: utf-8 -*-
"""
SWARM COMMANDS — Comandos de Telegram para controlar el enjambre.
Solo el OWNER puede usar estos comandos.
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from config.settings import OWNER_ID

logger = logging.getLogger("sayan.commands")


def owner_only(func):
    """Decorator: solo Leo puede usar este comando."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != OWNER_ID:
            await update.message.reply_text("Sin permiso.")
            return
        return await func(update, context)
    return wrapper


@owner_only
async def cmd_swarm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/swarm — Estado general del enjambre."""
    from src.swarm.circuit import get_circuit_status
    status = get_circuit_status()

    txt = f"SAYAN SWARM\n"
    txt += f"Agentes: {status['total_agents']}\n"
    txt += f"Mensajes bus: {status['bus_total_messages']}\n\n"

    for layer_name, agents in status["layers"].items():
        txt += f"{layer_name.upper()}:\n"
        for name in agents:
            a = status["agents"].get(name, {})
            tasks = a.get("tasks_completed", 0)
            errors = a.get("errors", 0)
            txt += f"  {name}: {tasks} tareas, {errors} errores\n"
        txt += "\n"

    await update.message.reply_text(txt)


@owner_only
async def cmd_aprobar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/aprobar ID — Aprueba una evolución."""
    from src.swarm.bus.approvals import approvals
    args = context.args
    if not args:
        await update.message.reply_text("Uso: /aprobar <ID>")
        return

    req_id = args[0]
    if approvals.approve(req_id):
        await update.message.reply_text(f"APROBADO: {req_id}")
    else:
        await update.message.reply_text(f"No encontrado o ya resuelto: {req_id}")


@owner_only
async def cmd_rechazar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/rechazar ID — Rechaza una evolución."""
    from src.swarm.bus.approvals import approvals
    args = context.args
    if not args:
        await update.message.reply_text("Uso: /rechazar <ID>")
        return

    req_id = args[0]
    if approvals.reject(req_id):
        await update.message.reply_text(f"RECHAZADO: {req_id}")
    else:
        await update.message.reply_text(f"No encontrado o ya resuelto: {req_id}")


@owner_only
async def cmd_evoluciones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/evoluciones — Lista evoluciones pendientes."""
    from src.swarm.bus.approvals import approvals
    pending = approvals.get_pending()

    if not pending:
        await update.message.reply_text("Sin evoluciones pendientes.")
        return

    txt = f"EVOLUCIONES PENDIENTES ({len(pending)}):\n\n"
    for req in pending[-10:]:
        txt += f"ID: {req['id']}\n"
        txt += f"Agente: {req['agent']}\n"
        txt += f"Acción: {req['description'][:80]}\n"
        txt += f"/aprobar {req['id']} | /rechazar {req['id']}\n\n"

    await update.message.reply_text(txt[:4000])


@owner_only
async def cmd_agentes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/agentes — Lista todos los agentes y su estado."""
    from src.swarm.circuit import ACTIVE_AGENTS

    txt = "AGENTES DEL ENJAMBRE:\n\n"
    for name, agent in ACTIVE_AGENTS.items():
        s = agent.status()
        txt += f"L{s['layer']} | {name:10} | {s['role']}\n"
        txt += f"     Tareas: {s['tasks_completed']} | Errores: {s['errors']}\n\n"

    await update.message.reply_text(txt[:4000])


@owner_only
async def cmd_forge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/forge — Estado de la fábrica de sirvientes."""
    from src.swarm.capa4_forge.forge import forge
    from src.swarm.bus.message_bus import Message

    status = forge._get_status()
    txt = f"FORGE — Fábrica de Sirvientes\n\n"
    txt += f"Creados total: {status['total_created']}\n"
    txt += f"Activos ahora: {status['active']}\n"
    txt += f"Completados: {status['completed']}\n\n"

    if status['last_5']:
        txt += "Últimos 5:\n"
        for s in status['last_5']:
            txt += f"  {s['id']}: {s['type']} ({s['duration']:.1f}s)\n"

    await update.message.reply_text(txt)


@owner_only
async def cmd_atlas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/atlas [búsqueda] — Busca en memoria infinita."""
    from src.swarm.capa3_ejecutores.atlas import atlas
    from src.swarm.bus.message_bus import Message

    args = context.args
    if not args:
        # Mostrar resumen
        summary = atlas._summary()
        txt = f"ATLAS — Memoria Infinita\n\n"
        txt += f"Entradas: {summary['total_entries']}\n"
        txt += f"Categorías: {summary['categories']}\n"
        await update.message.reply_text(txt)
        return

    # Buscar
    query = " ".join(args)
    results = atlas._search({"query": query})
    if results["count"] == 0:
        await update.message.reply_text(f"Sin resultados para: {query}")
        return

    txt = f"ATLAS — Resultados para '{query}':\n\n"
    for r in results["results"][:5]:
        txt += f"[{r['category']}] {r['data'][:100]}\n\n"

    await update.message.reply_text(txt[:4000])



@owner_only
async def cmd_healer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/healer — Estado del auto-reparador."""
    from src.swarm.skills.auto_repair.healer import healer

    args = context.args
    if args and args[0] == "check":
        # Forzar chequeo
        health = healer._check_health()
        issues = healer._diagnose(health)
        txt = f"HEALTH CHECK FORZADO:\n\n"
        txt += f"Memoria: {health['memory_mb']:.0f} MB\n"
        txt += f"Errores/min: {health['error_rate']}\n"
        txt += f"Bus: {'OK' if health['bus_alive'] else 'MUERTO'}\n"
        txt += f"Brain: {'OK' if health['brain_alive'] else 'MUERTO'}\n"
        txt += f"Agentes: {'OK' if health['agents_alive'] else 'PROBLEMAS'}\n\n"
        if issues:
            txt += f"PROBLEMAS ({len(issues)}):\n"
            for i in issues:
                txt += f"  - {i['type']} ({i.get('severity', '?')})\n"
        else:
            txt += "Sin problemas detectados."
        await update.message.reply_text(txt)
        return

    status = healer.get_status()
    txt = f"AUTO-HEALER\n\n"
    txt += f"Estado: {'ACTIVO' if status['running'] else 'INACTIVO'}\n"
    txt += f"Errores/min: {status['errors_last_minute']}\n"
    txt += f"Reparaciones totales: {status['total_repairs']}\n\n"

    if status['last_5_repairs']:
        txt += "Últimas reparaciones:\n"
        for r in status['last_5_repairs']:
            txt += f"  {r['issue']['type']} → {r['action']} → {'OK' if r['verified'] else 'FAIL'}\n"

    txt += f"\n/healer check — Forzar chequeo"
    await update.message.reply_text(txt)
