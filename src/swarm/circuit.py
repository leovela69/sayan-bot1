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
from src.swarm.bus.message_bus import bus, Message

logger = logging.getLogger("sayan.circuit")

# Import todos los agentes
from src.swarm.capa1_cerebro.kronos import kronos
from src.swarm.capa1_cerebro.cortex import cortex
from src.swarm.capa1_cerebro.genesis import genesis
from src.swarm.capa2_puentes.oraculo import oraculo
from src.swarm.capa2_puentes.nexus import nexus
from src.swarm.capa2_puentes.mirror import mirror
from src.swarm.capa3_ejecutores.atlas import atlas
from src.swarm.capa3_ejecutores.sentinel import sentinel
from src.swarm.capa3_ejecutores.daemon import daemon
from src.swarm.capa4_forge.forge import forge

# Todos los agentes activos
ACTIVE_AGENTS = {
    # Capa 1 — Cerebro
    "KRONOS": kronos,
    "CORTEX": cortex,
    "GENESIS": genesis,
    # Capa 2 — Puentes
    "ORACULO": oraculo,
    "NEXUS": nexus,
    "MIRROR": mirror,
    # Capa 3 — Ejecutores
    "ATLAS": atlas,
    "SENTINEL": sentinel,
    "DAEMON": daemon,
    # Capa 4 — Fábrica
    "FORGE": forge,
}


async def run_circuit(interval: int = 30):
    """
    Bucle principal del circuito.
    Cada 'interval' segundos:
    1. DAEMON ejecuta cron jobs
    2. Procesa mensajes pendientes de cada agente
    3. SENTINEL escanea proactivamente
    4. KRONOS corre ciclo de coordinación
    """
    logger.info(f"=== SAYAN CIRCUIT ONLINE === {len(ACTIVE_AGENTS)} agents")
    for name, agent in ACTIVE_AGENTS.items():
        logger.info(f"  L{agent.layer} | {name:10} | {agent.role}")

    while True:
        try:
            # 1. DAEMON tick (cron jobs)
            await daemon.tick()

            # 2. Procesar mensajes pendientes
            for name in list(ACTIVE_AGENTS.keys()):
                await bus.process_queue(name)

            # 3. SENTINEL tick (proactivo)
            await sentinel.tick()

            # 4. Ciclo de KRONOS
            cycle_msg = Message("CIRCUIT", "KRONOS", "cycle", {"timestamp": time.time()})
            await kronos.process_message(cycle_msg)

        except Exception as e:
            logger.error(f"Circuit error: {e}")

        await asyncio.sleep(interval)


def register_agent(name: str, agent):
    """Registra un nuevo agente dinámicamente."""
    ACTIVE_AGENTS[name] = agent
    logger.info(f"Agent {name} added to circuit ({len(ACTIVE_AGENTS)} total)")


def get_circuit_status() -> dict:
    """Estado completo del circuito."""
    return {
        "total_agents": len(ACTIVE_AGENTS),
        "layers": {
            "1_cerebro": ["KRONOS", "CORTEX", "GENESIS"],
            "2_puentes": ["ORACULO", "NEXUS", "MIRROR"],
            "3_ejecutores": ["ATLAS", "SENTINEL", "DAEMON"],
            "4_forge": ["FORGE"]
        },
        "agents": {name: agent.status() for name, agent in ACTIVE_AGENTS.items()},
        "bus_total_messages": len(bus._history)
    }
