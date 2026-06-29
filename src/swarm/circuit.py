# -*- coding: utf-8 -*-
"""
CIRCUIT — Orquestador del circuito completo.
Ejecuta el ciclo de vida del enjambre:
1. Inicia todos los agentes
2. Corre el bus de mensajes
3. Ejecuta ticks periódicos
4. Mantiene el flujo Capa1→2→3→4 sin cortes
"""
import asyncio
import logging
import time
from src.swarm.bus.message_bus import bus
from src.swarm.capa1_cerebro.kronos import kronos
from src.swarm.capa4_forge.forge import forge

logger = logging.getLogger("sayan.circuit")

# Agentes activos (se irán añadiendo conforme se creen)
ACTIVE_AGENTS = {
    "KRONOS": kronos,
    "FORGE": forge,
}


async def run_circuit(interval: int = 30):
    """
    Bucle principal del circuito.
    Cada 'interval' segundos:
    1. Procesa mensajes pendientes de cada agente
    2. Ejecuta tick() de cada agente
    3. KRONOS corre su ciclo de coordinación
    """
    logger.info(f"Circuit started — {len(ACTIVE_AGENTS)} agents active")
    logger.info(f"Agents: {list(ACTIVE_AGENTS.keys())}")

    while True:
        try:
            # Procesar mensajes pendientes
            for name in list(ACTIVE_AGENTS.keys()):
                await bus.process_queue(name)

            # Tick de cada agente
            for name, agent in ACTIVE_AGENTS.items():
                try:
                    await agent.tick()
                except Exception as e:
                    logger.error(f"Tick error for {name}: {e}")

            # Ciclo de Kronos (coordinación)
            await kronos.process_message(
                __import__('src.swarm.bus.message_bus', fromlist=['Message']).Message(
                    "CIRCUIT", "KRONOS", "cycle", {"timestamp": time.time()}
                )
            )

        except Exception as e:
            logger.error(f"Circuit error: {e}")

        await asyncio.sleep(interval)


def register_agent(name: str, agent):
    """Registra un nuevo agente en el circuito."""
    ACTIVE_AGENTS[name] = agent
    logger.info(f"Agent {name} added to circuit ({len(ACTIVE_AGENTS)} total)")


def get_circuit_status() -> dict:
    """Estado del circuito completo."""
    return {
        "agents_count": len(ACTIVE_AGENTS),
        "agents": {name: agent.status() for name, agent in ACTIVE_AGENTS.items()},
        "bus_pending": {name: bus.get_pending_count(name) for name in ACTIVE_AGENTS},
        "uptime": time.time()
    }
