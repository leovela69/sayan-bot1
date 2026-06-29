# -*- coding: utf-8 -*-
"""
SAYAN BOT — Telegram Platform
Bot de Telegram con python-telegram-bot v20+ (async)
"""
import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)
from config.settings import TELEGRAM_BOT_TOKEN, OWNER_ID
from src.core.router import process_message

logger = logging.getLogger("sayan.telegram")



# ===== HANDLERS =====

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    user = update.effective_user
    await update.message.reply_text(
        f"Soy SAYAN. Tu agente autónomo.\n\n"
        f"Escríbeme lo que necesites. Sin comandos, sin límites.\n"
        f"Aprendo de cada conversación y mejoro.\n\n"
        f"/reset — Borrar mi memoria\n"
        f"/tools — Ver mis herramientas\n"
        f"/status — Mi estado actual"
    )


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Borra memoria del usuario."""
    from src.core.router import memory
    user_id = update.effective_user.id
    memory.clear(user_id)
    await update.message.reply_text("Memoria borrada. Empezamos de cero.")


async def cmd_tools(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista herramientas disponibles."""
    from src.core.router import tools
    tool_list = tools.list_tools()
    txt = "Mis herramientas:\n" + "\n".join(f"- {t}" for t in tool_list)
    await update.message.reply_text(txt)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Estado del bot."""
    from src.core.router import tools, memory
    await update.message.reply_text(
        f"SAYAN v1.0\n"
        f"Tools: {len(tools.list_tools())}\n"
        f"Estado: Operativo\n"
        f"Modelo: Hermes 4"
    )



async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa cualquier mensaje de texto."""
    if not update.message or not update.message.text:
        return
    
    user = update.effective_user
    text = update.message.text.strip()
    if not text:
        return
    
    # Indicar que está escribiendo
    await update.message.chat.send_action("typing")
    
    try:
        response = await process_message(
            user_id=user.id,
            text=text,
            username=user.username or user.first_name or ""
        )
        
        # Si la respuesta contiene URL de imagen, enviar foto
        if "IMAGEN_URL:" in response:
            url = response.split("IMAGEN_URL:")[1].strip()
            try:
                await update.message.reply_photo(url)
            except Exception:
                await update.message.reply_text(f"Imagen: {url}")
        else:
            # Dividir mensajes largos
            if len(response) > 4000:
                for i in range(0, len(response), 4000):
                    await update.message.reply_text(response[i:i+4000])
            else:
                await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await update.message.reply_text("Error procesando. Intenta de nuevo.")


def run_telegram_bot():
    """Inicia el bot de Telegram."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN no configurado")
        return
    
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Registrar handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("tools", cmd_tools))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info(f"SAYAN Bot starting... (@{app.bot.username if hasattr(app, 'bot') else 'Sayanyin_Bot'})")
    app.run_polling(drop_pending_updates=True)
