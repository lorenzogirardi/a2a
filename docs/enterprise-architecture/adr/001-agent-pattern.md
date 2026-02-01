# ADR-001: Agent Pattern

## Status

Accepted

## Context

We need a consistent pattern for all agents in the system that:
- Separates reasoning from execution
- Supports both simple and LLM-based agents
- Allows state persistence
- Integrates with the permission system

## Decision

Adopt the **Think-Act-Respond** pattern:

```python
class AgentBase:
    async def receive_message(ctx, content, sender_id):
        # 1. Build message
        # 2. Think (decide what to do)
        # 3. Act (execute actions)
        # 4. Save state
        # 5. Return response

    async def think(message) -> dict:
        # Returns: response, actions, state_updates

    async def act(actions) -> list:
        # Execute actions, return results
```

## Consequences

### Positive

- Clear separation of concerns
- Easy to implement simple agents (just override `think`)
- LLM agents can use same pattern with Claude API
- State management is automatic
- Testable in isolation

### Negative

- Two-phase (think/act) may be overkill for simple agents
- Async-only (no sync support)

## Alternatives Considered

1. **Single process() method**: Simpler but mixes concerns
2. **Event-driven**: More flexible but harder to understand
3. **Actor model**: Good for concurrency but adds complexity

## References

- `agents/base.py` - Base implementation
- `agents/simple_agent.py` - Simple agent examples
- `agents/llm_agent.py` - LLM agent with tool use
