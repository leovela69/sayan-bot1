# -*- coding: utf-8 -*-
"""
BASE AGENT — Clase base para todos los agentes del enjambre.
Cada agente hereda de aquí y obtiene:
- Conexión al bus de mensajes
- Sistema de logs
- Memoria propia
- Heartbeat (vivo/muerto)
- Comunicación con otros agentes
"""
import time
import logging
import asyncio
from src.swarm.bus.message_bus import bus, Message


class BaseAgent:
    """Clase base para agentes del enjambre Sayan."""

    def __init__(self, name: str, layer: int, role: str):
        self.name = name
        self.layer = layer  # 1=cerebro, 2=puente, 3=ejecutor, 4=forge
        self.role = role
        self.active = True
        self.last_heartbeat = time.time()
        self.tasks_completed = 0
        self.errors = 0
        self.logger = logging.getLogger(f"sayan.{name.lower()}")

        # Registrar en el bus
        bus.register_agent(name, self._handle_message)
        self.logger.info(f"{name} initialized (Layer {layer}: {role})")

    async def _handle_message(self, message: Message):
        """Handler interno del bus. Delega al método process_message."""
        self.last_heartbeat = time.time()
        try:
            result = await self.process_message(message)
            self.tasks_completed += 1
            return result
        except Exception as e:
            self.errors += 1
            self.logger.error(f"Error processing message: {e}")
            raise

    async def process_message(self, message: Message):
        """Override en cada agente — procesa un mensaje del bus."""
        raise NotImplementedError(f"{self.name} must implement process_message")

    async def send(self, target: str, action: str, payload: dict = None, priority: str = "normal"):
        """Enviar mensaje a otro agente via bus."""
        return await bus.send(self.name, target, action, payload, priority)

    async def broadcast(self, action: str, payload: dict = None, priority: str = "normal"):
        """Enviar a todos los agentes."""
        return await bus.send(self.name, "*", action, payload, priority)

    def status(self) -> dict:
        """Estado actual del agente."""
        return {
            "name": self.name,
            "layer": self.layer,
            "role": self.role,
            "active": self.active,
            "uptime": time.time() - self.last_heartbeat,
            "tasks_completed": self.tasks_completed,
            "errors": self.errors,
            "pending_messages": bus.get_pending_count(self.name)
        }

    async def tick(self):
        """Ciclo de vida — se ejecuta periódicamente. Override para lógica proactiva."""
        pass
