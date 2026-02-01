"""
Run MCP Server - Avvia il server FastMCP per esporre gli agenti.

Uso:
    python run_mcp_server.py          # Avvia MCP server (stdio)
    python run_mcp_server.py --api    # Avvia FastAPI server (HTTP)
"""

import sys


def main():
    if "--api" in sys.argv:
        # Avvia FastAPI
        import uvicorn
        from protocol.api import app

        print("[API] Avvio server FastAPI su http://localhost:8000")
        print("[API] Docs disponibili su http://localhost:8000/docs")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        # Avvia MCP (default)
        from protocol.mcp_server import mcp, setup_default_agents

        setup_default_agents()
        print("[MCP] Avvio server MCP (stdio mode)")
        mcp.run()


if __name__ == "__main__":
    main()
