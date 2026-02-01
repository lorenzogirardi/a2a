"""
Run MCP Server - Avvia il server MCP per esporre gli agenti.

Uso:
    python run_mcp_server.py

Il server sara' accessibile tramite stdio (per Claude Desktop)
o puo' essere esteso per SSE/HTTP.
"""

import asyncio

from storage import MemoryStorage
from agents import EchoAgent, CounterAgent, CalculatorAgent, RouterAgent
from protocol import AgentMCPServer


async def main():
    """Avvia il server MCP con gli agenti configurati."""

    # Storage condiviso
    storage = MemoryStorage()

    # Crea gli agenti
    echo = EchoAgent("echo", storage)
    counter = CounterAgent("counter", storage)
    calculator = CalculatorAgent("calculator", storage)

    # Router che smista ai vari agenti
    router = RouterAgent("router", storage)
    router.add_route("calcola", calculator)
    router.add_route("ripeti", echo)
    router.add_route("conta", counter)

    # Crea e configura il server MCP
    server = AgentMCPServer(storage)
    server.register_agent(echo)
    server.register_agent(counter)
    server.register_agent(calculator)
    server.register_agent(router)

    # Avvia
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
