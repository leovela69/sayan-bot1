# -*- coding: utf-8 -*-
"""
MCP INTEGRATION — Model Context Protocol para herramientas externas.

Permite a Sayan conectarse a servidores MCP para acceder a tools externas
sin necesidad de implementarlas directamente.

Features:
- Registro dinámico de servidores MCP
- Descubrimiento automático de tools
- Ejecución de tools MCP via JSON-RPC
- Fallback si el servidor MCP no responde
- Cache de schemas para evitar re-descubrimiento
- Métricas de uso por servidor
"""
import asyncio
import json
import time
import logging
import httpx
import os
from typing import Dict, List, Optional, Any
from config.settings import DATA_DIR

logger = logging.getLogger("sayan.mcp")

MCP_CONFIG_FILE = os.path.join(DATA_DIR, "mcp_servers.json")


class MCPServer:
    """Un servidor MCP conectado."""

    def __init__(self, name: str, url: str, description: str = "",
                 auth_token: str = "", timeout: float = 30.0):
        self.name = name
        self.url = url.rstrip("/")
        self.description = description
        self.auth_token = auth_token
        self.timeout = timeout
        self.active = True
        self.tools: List[Dict] = []
        self.last_discovery = 0
        self.call_count = 0
        self.error_count = 0
        self.last_error = ""

    async def discover_tools(self) -> List[Dict]:
        """Descubre herramientas disponibles en el servidor MCP."""
        try:
            headers = {"Content-Type": "application/json"}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"

            payload = {
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": int(time.time() * 1000),
                "params": {}
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.url}", json=payload, headers=headers)

                if resp.status_code == 200:
                    data = resp.json()
                    self.tools = data.get("result", {}).get("tools", [])
                    self.last_discovery = time.time()
                    logger.info(f"MCP '{self.name}': discovered {len(self.tools)} tools")
                    return self.tools
                else:
                    self.last_error = f"Discovery failed: HTTP {resp.status_code}"
                    logger.error(f"MCP '{self.name}' discovery error: {resp.status_code}")
                    return []

        except Exception as e:
            self.last_error = str(e)
            self.error_count += 1
            logger.error(f"MCP '{self.name}' discovery error: {e}")
            return []

    async def call_tool(self, tool_name: str, arguments: Dict = None) -> Dict:
        """Ejecuta una herramienta del servidor MCP."""
        try:
            headers = {"Content-Type": "application/json"}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"

            payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "id": int(time.time() * 1000),
                "params": {
                    "name": tool_name,
                    "arguments": arguments or {}
                }
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.url}", json=payload, headers=headers)
                self.call_count += 1

                if resp.status_code == 200:
                    data = resp.json()
                    if "error" in data:
                        self.error_count += 1
                        return {"error": data["error"], "success": False}
                    return {"result": data.get("result", {}), "success": True}
                else:
                    self.error_count += 1
                    self.last_error = f"Call failed: HTTP {resp.status_code}"
                    return {"error": f"HTTP {resp.status_code}", "success": False}

        except asyncio.TimeoutError:
            self.error_count += 1
            self.last_error = "Timeout"
            return {"error": "Timeout", "success": False}
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            return {"error": str(e), "success": False}

    def to_dict(self) -> Dict:
        return {
            "name": self.name, "url": self.url,
            "description": self.description,
            "active": self.active,
            "tools_count": len(self.tools),
            "call_count": self.call_count,
            "error_count": self.error_count,
            "last_discovery": self.last_discovery,
            "last_error": self.last_error
        }


class MCPIntegration:
    """Gestor de integraciones MCP."""

    def __init__(self):
        self.servers: Dict[str, MCPServer] = {}
        self.tool_registry: Dict[str, str] = {}  # tool_name → server_name
        self._load_config()

    def _load_config(self):
        """Carga configuración de servidores MCP."""
        if os.path.exists(MCP_CONFIG_FILE):
            try:
                with open(MCP_CONFIG_FILE, "r") as f:
                    config = json.load(f)
                for name, server_data in config.get("servers", {}).items():
                    self.register_server(
                        name=name,
                        url=server_data["url"],
                        description=server_data.get("description", ""),
                        auth_token=server_data.get("auth_token", "")
                    )
                logger.info(f"MCP config loaded: {len(self.servers)} servers")
            except Exception as e:
                logger.error(f"Error loading MCP config: {e}")

    def _save_config(self):
        """Persiste configuración."""
        try:
            config = {
                "servers": {
                    name: {
                        "url": s.url,
                        "description": s.description,
                        "auth_token": s.auth_token
                    }
                    for name, s in self.servers.items()
                }
            }
            with open(MCP_CONFIG_FILE, "w") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving MCP config: {e}")

    def register_server(self, name: str, url: str, description: str = "",
                        auth_token: str = "") -> MCPServer:
        """Registra un nuevo servidor MCP."""
        server = MCPServer(name, url, description, auth_token)
        self.servers[name] = server
        self._save_config()
        logger.info(f"MCP server registered: {name} ({url})")
        return server

    def remove_server(self, name: str) -> bool:
        """Elimina un servidor MCP."""
        if name in self.servers:
            # Limpiar tools del registro
            tools_to_remove = [t for t, s in self.tool_registry.items() if s == name]
            for t in tools_to_remove:
                del self.tool_registry[t]
            del self.servers[name]
            self._save_config()
            return True
        return False

    async def discover_all(self) -> Dict[str, List[Dict]]:
        """Descubre tools de todos los servidores registrados."""
        results = {}
        for name, server in self.servers.items():
            if server.active:
                tools = await server.discover_tools()
                results[name] = tools
                # Registrar tools
                for tool in tools:
                    tool_name = tool.get("name", "")
                    if tool_name:
                        self.tool_registry[tool_name] = name
        return results

    async def call_tool(self, tool_name: str, arguments: Dict = None) -> Dict:
        """
        Ejecuta una tool MCP por nombre.
        Busca automáticamente en qué servidor está.
        """
        server_name = self.tool_registry.get(tool_name)
        if not server_name:
            # Intentar re-discovery
            await self.discover_all()
            server_name = self.tool_registry.get(tool_name)
            if not server_name:
                return {"error": f"Tool '{tool_name}' not found in any MCP server", "success": False}

        server = self.servers.get(server_name)
        if not server or not server.active:
            return {"error": f"Server '{server_name}' not available", "success": False}

        return await server.call_tool(tool_name, arguments)

    def get_all_tools(self) -> List[Dict]:
        """Lista todas las tools disponibles de todos los servidores."""
        all_tools = []
        for name, server in self.servers.items():
            for tool in server.tools:
                all_tools.append({
                    "name": tool.get("name", ""),
                    "description": tool.get("description", ""),
                    "server": name,
                    "input_schema": tool.get("inputSchema", {})
                })
        return all_tools

    def get_tool_schemas(self) -> List[Dict]:
        """
        Retorna schemas en formato OpenAI function-calling
        para inyectar al brain.
        """
        schemas = []
        for tool in self.get_all_tools():
            schemas.append({
                "type": "function",
                "function": {
                    "name": f"mcp_{tool['name']}",
                    "description": f"[MCP:{tool['server']}] {tool['description']}",
                    "parameters": tool.get("input_schema", {"type": "object", "properties": {}})
                }
            })
        return schemas

    def get_status(self) -> Dict:
        """Estado de la integración MCP."""
        return {
            "total_servers": len(self.servers),
            "active_servers": sum(1 for s in self.servers.values() if s.active),
            "total_tools": len(self.tool_registry),
            "servers": {n: s.to_dict() for n, s in self.servers.items()},
            "tool_mapping": self.tool_registry
        }


# Singleton
mcp = MCPIntegration()
