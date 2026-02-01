"""
Run MCP Server - Avvia il server FastMCP per esporre gli agenti.

Uso:
    python run_mcp_server.py          # Avvia MCP server (stdio)
    python run_mcp_server.py --api    # Avvia FastAPI server (HTTP)

Env vars:
    HOST: Host to bind (default: 127.0.0.1)
    PORT: Port to bind (default: 8000)
"""

import os
import sys


def main():
    if "--api" in sys.argv:
        # Avvia FastAPI
        import uvicorn
        from protocol.api import app

        host = os.environ.get("HOST", "127.0.0.1")
        port = int(os.environ.get("PORT", "8000"))

        print(f"[API] Avvio server FastAPI su http://{host}:{port}")
        print(f"[API] Docs disponibili su http://{host}:{port}/docs")
        uvicorn.run(app, host=host, port=port)
    else:
        # Avvia MCP (default)
        from protocol.mcp_server import mcp, setup_default_agents

        setup_default_agents()
        print("[MCP] Avvio server MCP (stdio mode)")
        mcp.run()


if __name__ == "__main__":
    main()
