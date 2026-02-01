#!/usr/bin/env python3
"""
Demo: LLM Agent with Claude API

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python examples/llm_demo.py

Or:
    ANTHROPIC_API_KEY="sk-ant-..." python examples/llm_demo.py
"""

import asyncio
import os
import sys

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage import MemoryStorage
from agents.llm_agent import LLMAgent, ToolUsingLLMAgent
from auth.permissions import user_context


async def demo_basic_llm():
    """Demo: Basic LLM Agent (no tools)."""
    print("\n" + "=" * 60)
    print("Demo 1: Basic LLM Agent")
    print("=" * 60)

    storage = MemoryStorage()
    agent = LLMAgent(
        agent_id="assistant",
        storage=storage,
        system_prompt="Sei un assistente conciso. Rispondi in italiano in massimo 2 frasi."
    )

    ctx = user_context("demo_user")

    # Test conversation
    questions = [
        "Ciao! Come ti chiami?",
        "Qual è la capitale della Francia?",
    ]

    for q in questions:
        print(f"\n👤 User: {q}")
        response = await agent.receive_message(ctx=ctx, content=q, sender_id="demo_user")
        print(f"🤖 Agent: {response.content}")
        if response.metadata.get("usage"):
            usage = response.metadata["usage"]
            print(f"   (tokens: {usage['input_tokens']} in, {usage['output_tokens']} out)")


async def demo_tool_agent():
    """Demo: LLM Agent with Tools."""
    print("\n" + "=" * 60)
    print("Demo 2: Tool-Using LLM Agent")
    print("=" * 60)

    storage = MemoryStorage()
    agent = ToolUsingLLMAgent(
        agent_id="calculator",
        storage=storage,
        system_prompt="Sei un assistente con accesso a una calcolatrice. Usa il tool 'calculate' per fare calcoli."
    )

    # Add calculator tool
    def calculate(params: dict) -> str:
        expression = params.get("expression", "")
        try:
            # Safe eval for simple math
            allowed = set("0123456789+-*/.() ")
            if all(c in allowed for c in expression):
                result = eval(expression)
                return f"Il risultato di {expression} è {result}"
            return "Espressione non valida"
        except Exception as e:
            return f"Errore: {e}"

    agent.add_tool(
        name="calculate",
        description="Esegue calcoli matematici. Input: espressione matematica come stringa.",
        input_schema={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Espressione matematica, es: '2 + 2' o '(10 * 5) / 2'"
                }
            },
            "required": ["expression"]
        },
        handler=calculate
    )

    ctx = user_context("demo_user")

    # Test with calculation
    questions = [
        "Quanto fa 15 * 7?",
        "Se ho 100 euro e spendo 37.50, quanto mi resta?",
    ]

    for q in questions:
        print(f"\n👤 User: {q}")
        response = await agent.receive_message(ctx=ctx, content=q, sender_id="demo_user")
        print(f"🤖 Agent: {response.content}")

        # Show tool calls if any
        tool_calls = response.metadata.get("tool_calls", [])
        if tool_calls:
            print(f"   🔧 Tools used: {[t['tool'] for t in tool_calls]}")


async def demo_research_llm():
    """Demo: LLM Agent that uses research."""
    print("\n" + "=" * 60)
    print("Demo 3: Research-Capable LLM Agent")
    print("=" * 60)

    from agents.research import OrchestratorAgent

    storage = MemoryStorage()

    # Create research orchestrator
    research_orchestrator = OrchestratorAgent(storage)

    # Create LLM agent with research tool
    agent = ToolUsingLLMAgent(
        agent_id="researcher",
        storage=storage,
        system_prompt="Sei un assistente di ricerca. Usa il tool 'search' per cercare informazioni."
    )

    # Add research tool
    async def search(params: dict) -> str:
        query = params.get("query", "")
        result = await research_orchestrator.research(query)
        return result.summary

    agent.add_tool(
        name="search",
        description="Cerca informazioni su un argomento.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Query di ricerca"}
            },
            "required": ["query"]
        },
        handler=search
    )

    ctx = user_context("demo_user")

    print(f"\n👤 User: Cerca informazioni su FastAPI")
    response = await agent.receive_message(
        ctx=ctx,
        content="Cerca informazioni su FastAPI",
        sender_id="demo_user"
    )
    print(f"🤖 Agent: {response.content}")

    tool_calls = response.metadata.get("tool_calls", [])
    if tool_calls:
        print(f"   🔧 Tools used: {[t['tool'] for t in tool_calls]}")


async def main():
    # Check API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY non impostata!")
        print()
        print("Imposta la chiave API:")
        print("  export ANTHROPIC_API_KEY='sk-ant-...'")
        print()
        print("Poi esegui:")
        print("  python examples/llm_demo.py")
        sys.exit(1)

    print("🚀 A2A LLM Agent Demo")
    print("Using Claude API...")

    try:
        await demo_basic_llm()
        await demo_tool_agent()
        await demo_research_llm()

        print("\n" + "=" * 60)
        print("✅ Demo completata!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Errore: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
