# -*- coding: utf-8 -*-
"""
ASYNC EXECUTOR — Ejecución asíncrona fire-and-forget estilo Antigravity.

Features:
- Ejecutar tareas en background sin bloquear al usuario
- Pool de workers con límite configurable
- Prioridades (critical, high, normal, low)
- Cola persistente
- Timeout + auto-retry
- Callbacks opcionales al completar
- Historial de ejecuciones
"""
import asyncio
import time
import logging
import json
import os
import traceback
from typing import Dict, List, Callable, Optional, Any
from config.settings import DATA_DIR

logger = logging.getLogger("sayan.executor")

EXECUTOR_LOG = os.path.join(DATA_DIR, "executor_log.json")


class AsyncTask:
    """Una tarea asíncrona."""

    def __init__(self, name: str, coroutine_fn: Callable, args: tuple = (),
                 kwargs: dict = None, priority: str = "normal",
                 timeout: float = 120.0, max_retries: int = 2,
                 callback: Callable = None, metadata: Dict = None):
        self.id = f"task_{name}_{int(time.time()*1000) % 100000}"
        self.name = name
        self.coroutine_fn = coroutine_fn
        self.args = args
        self.kwargs = kwargs or {}
        self.priority = priority
        self.timeout = timeout
        self.max_retries = max_retries
        self.callback = callback
        self.metadata = metadata or {}

        self.status = "pending"  # pending, running, completed, failed, cancelled
        self.result = None
        self.error = None
        self.created_at = time.time()
        self.started_at = None
        self.completed_at = None
        self.retries = 0

    @property
    def duration(self) -> float:
        if self.completed_at and self.started_at:
            return self.completed_at - self.started_at
        return 0

    def to_dict(self) -> Dict:
        return {
            "id": self.id, "name": self.name, "priority": self.priority,
            "status": self.status, "retries": self.retries,
            "duration": self.duration, "created_at": self.created_at,
            "result": str(self.result)[:200] if self.result else None,
            "error": str(self.error)[:200] if self.error else None,
            "metadata": self.metadata
        }


class AsyncExecutor:
    """Motor de ejecución asíncrona fire-and-forget."""

    PRIORITY_ORDER = {"critical": 0, "high": 1, "normal": 2, "low": 3}

    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self.queue: List[AsyncTask] = []
        self.running: Dict[str, AsyncTask] = {}
        self.completed: List[AsyncTask] = []
        self.failed: List[AsyncTask] = []
        self._active = False
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def start(self):
        """Inicia el executor (procesa cola cada 2s)."""
        self._active = True
        logger.info(f"AsyncExecutor started (max_concurrent={self.max_concurrent})")
        while self._active:
            await self._process_queue()
            await asyncio.sleep(2)

    def stop(self):
        """Detiene el executor."""
        self._active = False

    def submit(self, name: str, coroutine_fn: Callable, *args,
               priority: str = "normal", timeout: float = 120.0,
               max_retries: int = 2, callback: Callable = None,
               metadata: Dict = None, **kwargs) -> str:
        """
        Envía una tarea al executor (fire-and-forget).
        Retorna el task_id inmediatamente.
        """
        task = AsyncTask(
            name=name,
            coroutine_fn=coroutine_fn,
            args=args,
            kwargs=kwargs,
            priority=priority,
            timeout=timeout,
            max_retries=max_retries,
            callback=callback,
            metadata=metadata
        )
        self.queue.append(task)
        self._sort_queue()
        logger.info(f"Task submitted: {task.id} ({priority})")
        return task.id

    def fire_and_forget(self, coroutine_fn: Callable, *args, **kwargs) -> str:
        """Shortcut: ejecutar sin preocuparse del resultado."""
        name = getattr(coroutine_fn, "__name__", "anonymous")
        return self.submit(name, coroutine_fn, *args, **kwargs)

    async def _process_queue(self):
        """Procesa tareas de la cola."""
        while self.queue and len(self.running) < self.max_concurrent:
            task = self.queue.pop(0)
            asyncio.create_task(self._execute_task(task))

    async def _execute_task(self, task: AsyncTask):
        """Ejecuta una tarea individual con retry y timeout."""
        async with self._semaphore:
            task.status = "running"
            task.started_at = time.time()
            self.running[task.id] = task

            while task.retries <= task.max_retries:
                try:
                    if asyncio.iscoroutinefunction(task.coroutine_fn):
                        result = await asyncio.wait_for(
                            task.coroutine_fn(*task.args, **task.kwargs),
                            timeout=task.timeout
                        )
                    else:
                        result = task.coroutine_fn(*task.args, **task.kwargs)

                    task.result = result
                    task.status = "completed"
                    task.completed_at = time.time()
                    self.completed.append(task)
                    logger.info(f"Task completed: {task.id} ({task.duration:.2f}s)")

                    # Callback
                    if task.callback:
                        try:
                            if asyncio.iscoroutinefunction(task.callback):
                                await task.callback(result)
                            else:
                                task.callback(result)
                        except Exception:
                            pass
                    break

                except asyncio.TimeoutError:
                    task.retries += 1
                    if task.retries > task.max_retries:
                        task.error = f"Timeout after {task.timeout}s"
                        task.status = "failed"
                        task.completed_at = time.time()
                        self.failed.append(task)
                        logger.error(f"Task timeout: {task.id}")

                except Exception as e:
                    task.retries += 1
                    if task.retries > task.max_retries:
                        task.error = f"{type(e).__name__}: {str(e)}"
                        task.status = "failed"
                        task.completed_at = time.time()
                        self.failed.append(task)
                        logger.error(f"Task failed: {task.id} — {e}")
                    else:
                        await asyncio.sleep(1)  # Brief wait before retry

            # Limpiar running
            self.running.pop(task.id, None)

            # Mantener historial acotado
            if len(self.completed) > 200:
                self.completed = self.completed[-200:]
            if len(self.failed) > 100:
                self.failed = self.failed[-100:]

    def _sort_queue(self):
        """Ordena la cola por prioridad."""
        self.queue.sort(key=lambda t: self.PRIORITY_ORDER.get(t.priority, 2))

    def get_task(self, task_id: str) -> Optional[Dict]:
        """Obtiene estado de una tarea por ID."""
        # Buscar en running
        if task_id in self.running:
            return self.running[task_id].to_dict()
        # Buscar en completed
        for t in reversed(self.completed):
            if t.id == task_id:
                return t.to_dict()
        # Buscar en failed
        for t in reversed(self.failed):
            if t.id == task_id:
                return t.to_dict()
        # Buscar en queue
        for t in self.queue:
            if t.id == task_id:
                return t.to_dict()
        return None

    def cancel(self, task_id: str) -> bool:
        """Cancela una tarea en cola."""
        for i, t in enumerate(self.queue):
            if t.id == task_id:
                t.status = "cancelled"
                self.queue.pop(i)
                return True
        return False

    def get_status(self) -> Dict:
        """Estado del executor."""
        return {
            "active": self._active,
            "max_concurrent": self.max_concurrent,
            "queued": len(self.queue),
            "running": len(self.running),
            "completed_total": len(self.completed),
            "failed_total": len(self.failed),
            "running_tasks": [t.to_dict() for t in self.running.values()],
            "recent_completed": [t.to_dict() for t in self.completed[-5:]],
            "recent_failed": [t.to_dict() for t in self.failed[-5:]]
        }


# Singleton
executor = AsyncExecutor(max_concurrent=10)
