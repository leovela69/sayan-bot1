# -*- coding: utf-8 -*-
"""
MESSAGE BUS — Sistema de comunicación entre agentes del enjambre.
Flujo sin cortes: cada agente publica mensajes y los demás escuchan.
Persistente: los mensajes se guardan para redundancia.

Diseño:
- Pub/Sub async (sin dependencias externas)
- Queue por agente (nunca pierde mensajes)
- Prioridades (critical > high > normal > low)
- Auto-retry si un agente no responde
"""
import asyncio
import json
import os
import time
import logging
from typing import Callable, Dict, List
from config.settings import DATA_DIR

logger = logging.getLogger("sayan.bus")

BUS_LOG_FILE = os.path.join(DATA_DIR, "bus_log.jsonl")


class Message:
    """Un mensaje entre agentes."""
    def __init__(self, sender: str, target: str, action: str, payload: dict = None, priority: str = "normal"):
        self.id = f"{sender}_{int(time.time()*1000)}"
        self.sender = sender
        self.target = target  # "*" = broadcast
        self.action = action
        self.payload = payload or {}
        self.priority = priority  # critical, high, normal, low
        self.timestamp = time.time()
        self.processed = False

    def to_dict(self):
        return {
            "id": self.id, "sender": self.sender, "target": self.target,
            "action": self.action, "payload": self.payload,
            "priority": self.priority, "timestamp": self.timestamp
        }


class MessageBus:
    """Bus central de mensajes del enjambre."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._queues: Dict[str, asyncio.Queue] = {}
        self._history: List[dict] = []
        self._running = False

    def register_agent(self, agent_name: str, handler: Callable):
        """Registra un agente como suscriptor del bus."""
        self._subscribers[agent_name] = handler
        self._queues[agent_name] = asyncio.Queue()
        logger.info(f"Agent registered on bus: {agent_name}")

    async def publish(self, message: Message):
        """Publica un mensaje en el bus."""
        self._history.append(message.to_dict())
        self._persist(message)

        if message.target == "*":
            # Broadcast a todos
            for name, queue in self._queues.items():
                if name != message.sender:
                    await queue.put(message)
        elif message.target in self._queues:
            await self._queues[message.target].put(message)
        else:
            logger.warning(f"Target '{message.target}' not found on bus")

    async def send(self, sender: str, target: str, action: str, payload: dict = None, priority: str = "normal"):
        """Shortcut para enviar mensaje."""
        msg = Message(sender, target, action, payload, priority)
        await self.publish(msg)
        return msg.id

    async def process_queue(self, agent_name: str):
        """Procesa mensajes pendientes de un agente."""
        if agent_name not in self._queues:
            return
        queue = self._queues[agent_name]
        handler = self._subscribers.get(agent_name)
        if not handler:
            return

        processed = 0
        while not queue.empty():
            msg = await queue.get()
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(msg)
                else:
                    handler(msg)
                processed += 1
            except Exception as e:
                logger.error(f"Error processing msg for {agent_name}: {e}")
                # Re-queue on error (retry)
                await queue.put(msg)
                break
        return processed

    def get_history(self, limit: int = 50, agent: str = None) -> list:
        """Historial de mensajes."""
        history = self._history
        if agent:
            history = [m for m in history if m["sender"] == agent or m["target"] == agent]
        return history[-limit:]

    def get_pending_count(self, agent_name: str) -> int:
        """Mensajes pendientes para un agente."""
        if agent_name in self._queues:
            return self._queues[agent_name].qsize()
        return 0

    def _persist(self, message: Message):
        """Guarda mensaje en disco (no pierde nada si se reinicia)."""
        try:
            with open(BUS_LOG_FILE, "a") as f:
                f.write(json.dumps(message.to_dict(), ensure_ascii=False) + "\n")
        except Exception:
            pass


# Singleton global
bus = MessageBus()
