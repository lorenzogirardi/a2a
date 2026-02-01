"""
LangGraph Nodes - Individual processing functions for the graph.

Each node receives GraphState and returns updates to specific keys.
Nodes emit graph_update events for real-time vis.js visualization.
"""

from typing import Any, Optional
from langchain_core.runnables import RunnableConfig

from .state import GraphState


# Module-level references for dependency injection
_analyzer: Optional[Any] = None
_registry: Optional[Any] = None
_executor: Optional[Any] = None
_synthesizer: Optional[Any] = None


def set_analyzer(analyzer: Any) -> None:
    """Set the analyzer instance for nodes to use."""
    global _analyzer
    _analyzer = analyzer


def set_registry(registry: Any) -> None:
    """Set the registry instance for nodes to use."""
    global _registry
    _registry = registry


def set_executor(executor: Any) -> None:
    """Set the executor instance for nodes to use."""
    global _executor
    _executor = executor


def set_synthesizer(synthesizer: Any) -> None:
    """Set the synthesizer instance for nodes to use."""
    global _synthesizer
    _synthesizer = synthesizer


def get_analyzer() -> Any:
    """Get the analyzer instance."""
    return _analyzer


def get_registry() -> Any:
    """Get the registry instance."""
    return _registry


def get_executor() -> Any:
    """Get the executor instance."""
    return _executor


def get_synthesizer() -> Any:
    """Get the synthesizer instance."""
    return _synthesizer


def _get_stream_writer(config: RunnableConfig) -> Optional[Any]:
    """Extract stream writer from config if available."""
    configurable = config.get("configurable", {}) if config else {}
    return configurable.get("stream_writer")


def _emit_graph_update(
    config: RunnableConfig,
    action: str,
    node: Optional[dict] = None,
    edge: Optional[dict] = None
) -> None:
    """
    Emit a graph update event for vis.js visualization.

    Args:
        config: LangGraph config with stream_writer
        action: Action type (add_node, update_node, add_edge)
        node: Node data if action involves nodes
        edge: Edge data if action involves edges
    """
    writer = _get_stream_writer(config)
    if writer:
        event = {"type": "graph_update", "action": action}
        if node:
            event["node"] = node
        if edge:
            event["edge"] = edge
        writer(event)


async def analyze_node(state: GraphState, config: RunnableConfig) -> dict[str, Any]:
    """
    Analyze task to detect required capabilities.

    Emits graph updates:
    - add_node: "analyze" (running)
    - update_node: "analyze" (completed)
    - add_node: one per detected capability
    - add_edge: analyze -> each capability

    Args:
        state: Current graph state
        config: LangGraph config

    Returns:
        Dict with detected_capabilities, subtasks, status, dependencies
    """
    task_id = state["task_id"]
    task = state["original_task"]

    # Emit node start
    _emit_graph_update(config, "add_node", node={
        "id": "analyze",
        "label": "Analyzer",
        "state": "running",
        "type": "processor"
    })

    analyzer = get_analyzer()
    if not analyzer:
        _emit_graph_update(config, "update_node", node={
            "id": "analyze",
            "state": "failed"
        })
        return {
            "detected_capabilities": [],
            "subtasks": {},
            "dependencies": None,
            "status": "failed"
        }

    # Perform analysis
    analysis = await analyzer.analyze(task, task_id)

    # Emit node completion
    _emit_graph_update(config, "update_node", node={
        "id": "analyze",
        "state": "completed",
        "duration_ms": analysis.duration_ms
    })

    # Emit capability nodes and edges
    for cap in analysis.detected_capabilities:
        _emit_graph_update(config, "add_node", node={
            "id": f"cap_{cap}",
            "label": cap,
            "type": "capability",
            "state": "pending"
        })
        _emit_graph_update(config, "add_edge", edge={
            "from": "analyze",
            "to": f"cap_{cap}"
        })

    # Extract dependencies if present (from extended analysis)
    dependencies = getattr(analysis, 'dependencies', None)

    return {
        "detected_capabilities": analysis.detected_capabilities,
        "subtasks": analysis.subtasks,
        "dependencies": dependencies,
        "status": "analyzed"
    }


async def discover_node(state: GraphState, config: RunnableConfig) -> dict[str, Any]:
    """
    Discover agents for each detected capability.

    Emits graph updates:
    - add_node: "discover" (running)
    - update_node: each capability (with matched agents)
    - add_node: one per matched agent
    - add_edge: capability -> agent

    Args:
        state: Current graph state
        config: LangGraph config

    Returns:
        Dict with matches and updated status
    """
    capabilities = state["detected_capabilities"]
    task_id = state["task_id"]

    # Emit node start
    _emit_graph_update(config, "add_node", node={
        "id": "discover",
        "label": "Discovery",
        "state": "running",
        "type": "processor"
    })
    _emit_graph_update(config, "add_edge", edge={
        "from": "analyze",
        "to": "discover"
    })

    registry = get_registry()
    if not registry:
        _emit_graph_update(config, "update_node", node={
            "id": "discover",
            "state": "failed"
        })
        return {
            "matches": [],
            "status": "failed"
        }

    matches = []
    for capability in capabilities:
        agents = registry.find_by_capability(capability)
        agent_ids = [a.id for a in agents]

        match = {
            "capability": capability,
            "agent_ids": agent_ids,
            "matched": len(agent_ids) > 0
        }
        matches.append(match)

        # Update capability node state
        _emit_graph_update(config, "update_node", node={
            "id": f"cap_{capability}",
            "state": "matched" if agent_ids else "unmatched",
            "agents": agent_ids
        })

        # Add agent nodes and edges
        for agent in agents:
            _emit_graph_update(config, "add_node", node={
                "id": f"agent_{agent.id}",
                "label": agent.name,
                "type": "agent",
                "state": "pending"
            })
            _emit_graph_update(config, "add_edge", edge={
                "from": f"cap_{capability}",
                "to": f"agent_{agent.id}"
            })

    # Emit discover completion
    _emit_graph_update(config, "update_node", node={
        "id": "discover",
        "state": "completed"
    })

    return {
        "matches": matches,
        "status": "discovered"
    }


async def execute_node(state: GraphState, config: RunnableConfig) -> dict[str, Any]:
    """
    Execute subtasks on matched agents.

    Supports dependencies between capabilities:
    - If dependencies defined, runs in topological order
    - Otherwise, runs all in parallel

    Emits graph updates:
    - add_node: "execute" (running)
    - update_node: each agent (running -> completed/failed)
    - add_edge: execute -> agent

    Args:
        state: Current graph state
        config: LangGraph config

    Returns:
        Dict with executions list and updated status
    """
    matches = state["matches"]
    subtasks = state["subtasks"]
    task_id = state["task_id"]
    dependencies = state.get("dependencies")

    # Emit node start
    _emit_graph_update(config, "add_node", node={
        "id": "execute",
        "label": "Executor",
        "state": "running",
        "type": "processor"
    })
    _emit_graph_update(config, "add_edge", edge={
        "from": "discover",
        "to": "execute"
    })

    executor = get_executor()
    if not executor:
        _emit_graph_update(config, "update_node", node={
            "id": "execute",
            "state": "failed"
        })
        return {
            "executions": [],
            "status": "failed"
        }

    # Convert matches to the format executor expects
    from agents.router.models import CapabilityMatch
    capability_matches = [
        CapabilityMatch(
            capability=m["capability"],
            agent_ids=m["agent_ids"],
            matched=m["matched"]
        )
        for m in matches
    ]

    # Check if we have dependencies
    if dependencies and hasattr(executor, 'execute_with_dependencies'):
        # Execute with dependency ordering
        executions = await executor.execute_with_dependencies(
            matches=capability_matches,
            subtasks=subtasks,
            task_id=task_id,
            dependencies=dependencies
        )
    else:
        # Execute all (parallel by default)
        executions = await executor.execute_all(
            matches=capability_matches,
            subtasks=subtasks,
            task_id=task_id
        )

    # Convert to dict format and emit updates
    execution_dicts = []
    for exec_result in executions:
        exec_dict = {
            "agent_id": exec_result.agent_id,
            "agent_name": exec_result.agent_name,
            "capability": exec_result.capability,
            "input_text": exec_result.input_text,
            "output_text": exec_result.output_text,
            "duration_ms": exec_result.duration_ms,
            "success": exec_result.success,
            "error": exec_result.error,
            "tokens": exec_result.tokens
        }
        execution_dicts.append(exec_dict)

        # Update agent node
        _emit_graph_update(config, "update_node", node={
            "id": f"agent_{exec_result.agent_id}",
            "state": "completed" if exec_result.success else "failed",
            "duration_ms": exec_result.duration_ms
        })

    # Emit execute completion
    _emit_graph_update(config, "update_node", node={
        "id": "execute",
        "state": "completed"
    })

    # Determine final output if only one execution
    successful = [e for e in execution_dicts if e.get("success")]
    final_output = ""
    if len(successful) == 1:
        final_output = successful[0]["output_text"]

    return {
        "executions": execution_dicts,
        "final_output": final_output,
        "status": "executed"
    }


async def synthesize_node(state: GraphState, config: RunnableConfig) -> dict[str, Any]:
    """
    Synthesize multiple execution outputs into coherent response.

    Only called if should_synthesize returns "synthesize".

    Emits graph updates:
    - add_node: "synthesize" (running)
    - add_edge: each successful agent -> synthesize
    - update_node: "synthesize" (completed)

    Args:
        state: Current graph state
        config: LangGraph config

    Returns:
        Dict with synthesis and final_output
    """
    executions = state["executions"]
    original_task = state["original_task"]
    task_id = state["task_id"]

    # Emit node start
    _emit_graph_update(config, "add_node", node={
        "id": "synthesize",
        "label": "Synthesizer",
        "state": "running",
        "type": "processor"
    })

    # Add edges from successful agents to synthesize
    successful = [e for e in executions if e.get("success")]
    for exec_result in successful:
        _emit_graph_update(config, "add_edge", edge={
            "from": f"agent_{exec_result['agent_id']}",
            "to": "synthesize"
        })

    synthesizer = get_synthesizer()
    if not synthesizer:
        _emit_graph_update(config, "update_node", node={
            "id": "synthesize",
            "state": "failed"
        })
        return {
            "synthesis": None,
            "final_output": "Synthesis failed: no synthesizer available",
            "status": "failed"
        }

    # Convert dicts back to ExecutionResult for synthesizer
    from agents.router.models import ExecutionResult
    execution_results = [
        ExecutionResult(
            agent_id=e["agent_id"],
            agent_name=e["agent_name"],
            capability=e["capability"],
            input_text=e["input_text"],
            output_text=e["output_text"],
            duration_ms=e["duration_ms"],
            success=e["success"],
            error=e.get("error"),
            tokens=e.get("tokens", {"input": 0, "output": 0})
        )
        for e in successful
    ]

    # Perform synthesis
    synthesis_result = await synthesizer.synthesize(
        original_task=original_task,
        executions=execution_results,
        task_id=task_id
    )

    # Emit synthesize completion
    _emit_graph_update(config, "update_node", node={
        "id": "synthesize",
        "state": "completed",
        "duration_ms": synthesis_result["duration_ms"]
    })

    return {
        "synthesis": synthesis_result,
        "final_output": synthesis_result["synthesized_output"],
        "status": "completed"
    }


def should_synthesize(state: GraphState) -> str:
    """
    Conditional edge function: determine if synthesis is needed.

    Synthesis is needed when:
    - 2 or more successful executions exist

    Args:
        state: Current graph state

    Returns:
        "synthesize" if synthesis needed, "end" otherwise
    """
    executions = state.get("executions", [])
    successful = [e for e in executions if e.get("success")]

    if len(successful) > 1:
        return "synthesize"
    return "end"
