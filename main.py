"""
Main - Demo interattiva del sistema multi-agente.

Esegui con: python main.py

Questo script dimostra:
1. Creazione di agenti
2. Storage e persistenza
3. Comunicazione tra agenti
4. Sistema di permessi
"""

import asyncio
from datetime import datetime

from storage import MemoryStorage
from agents import EchoAgent, CounterAgent, RouterAgent, CalculatorAgent
from auth import (
    admin_context,
    user_context,
    guest_context,
    PermissionDenied,
    Permission
)


async def demo_basic_agents():
    """Demo 1: Agenti base e storage."""
    print("\n" + "="*60)
    print("DEMO 1: Agenti Base e Storage")
    print("="*60)

    # Crea lo storage condiviso
    storage = MemoryStorage()

    # Crea gli agenti
    echo = EchoAgent("echo-1", storage)
    counter = CounterAgent("counter-1", storage)

    # Un utente invia messaggi
    ctx = user_context("mario")

    print("\n--- Mario invia messaggi ---")

    # Messaggio all'echo agent
    response = await echo.receive_message(
        ctx=ctx,
        content="Ciao, come va?",
        sender_id="mario"
    )
    print(f"Echo risponde: {response.content}")

    # Messaggi al counter agent
    for i in range(3):
        response = await counter.receive_message(
            ctx=ctx,
            content=f"Messaggio numero {i+1}",
            sender_id="mario"
        )
        print(f"Counter risponde: {response.content}")

    # Verifica lo stato salvato
    print("\n--- Stato degli agenti ---")
    echo_state = await echo.get_state(ctx)
    counter_state = await counter.get_state(ctx)
    print(f"Echo state: {echo_state}")
    print(f"Counter state: {counter_state}")


async def demo_agent_to_agent():
    """Demo 2: Comunicazione tra agenti."""
    print("\n" + "="*60)
    print("DEMO 2: Comunicazione Agent-to-Agent")
    print("="*60)

    storage = MemoryStorage()

    # Crea agenti specializzati
    calculator = CalculatorAgent("calc", storage)
    echo = EchoAgent("echo", storage)

    # Crea un router che smista i messaggi
    router = RouterAgent("router", storage)
    router.add_route("calcola", calculator)
    router.add_route("ripeti", echo)

    ctx = user_context("luigi")

    print("\n--- Luigi parla al Router ---")

    # Il router inoltra al calculator
    response = await router.receive_message(
        ctx=ctx,
        content="calcola 15 * 7",
        sender_id="luigi"
    )
    print(f"Router (via Calculator): La risposta e' nel log delle azioni")

    # Il router inoltra all'echo
    response = await router.receive_message(
        ctx=ctx,
        content="ripeti questo messaggio",
        sender_id="luigi"
    )
    print(f"Router risponde: {response.content}")

    # Messaggio senza route
    response = await router.receive_message(
        ctx=ctx,
        content="ciao!",
        sender_id="luigi"
    )
    print(f"Router risponde: {response.content}")


async def demo_permissions():
    """Demo 3: Sistema di permessi."""
    print("\n" + "="*60)
    print("DEMO 3: Sistema di Permessi")
    print("="*60)

    storage = MemoryStorage()
    echo = EchoAgent("echo-secure", storage)

    # Admin puo' fare tutto
    admin = admin_context("superuser")
    print("\n--- Admin invia messaggio ---")
    response = await echo.receive_message(
        ctx=admin,
        content="Messaggio admin",
        sender_id="superuser"
    )
    print(f"Risposta: {response.content}")

    # User puo' inviare messaggi
    user = user_context("normale")
    print("\n--- User invia messaggio ---")
    response = await echo.receive_message(
        ctx=user,
        content="Messaggio user",
        sender_id="normale"
    )
    print(f"Risposta: {response.content}")

    # Guest NON puo' inviare messaggi (solo lettura)
    guest = guest_context("visitatore")
    print("\n--- Guest prova a inviare messaggio ---")
    try:
        await echo.receive_message(
            ctx=guest,
            content="Messaggio guest",
            sender_id="visitatore"
        )
    except PermissionDenied as e:
        print(f"ACCESSO NEGATO: {e}")

    # Guest puo' leggere lo stato
    print("\n--- Guest legge lo stato ---")
    state = await echo.get_state(guest)
    print(f"Guest puo' vedere lo stato: {state}")


async def demo_calculator():
    """Demo 4: Calculator Agent."""
    print("\n" + "="*60)
    print("DEMO 4: Calculator Agent")
    print("="*60)

    storage = MemoryStorage()
    calc = CalculatorAgent("calc", storage)
    ctx = user_context("studente")

    operations = [
        "quanto fa 10 + 5?",
        "calcola 100 / 4",
        "dimmi 7 * 8",
        "errore: nessun numero qui"
    ]

    for op in operations:
        response = await calc.receive_message(
            ctx=ctx,
            content=op,
            sender_id="studente"
        )
        print(f"Input: '{op}'")
        print(f"Output: {response.content}\n")


async def demo_conversation_history():
    """Demo 5: Cronologia conversazioni."""
    print("\n" + "="*60)
    print("DEMO 5: Cronologia Conversazioni")
    print("="*60)

    storage = MemoryStorage()
    echo = EchoAgent("echo", storage)

    # Crea una conversazione
    conv_id = await storage.create_conversation(["alice", "echo"])

    ctx = user_context("alice")

    # Scambio di messaggi
    messages = ["Ciao!", "Come stai?", "Che tempo fa?"]
    for msg in messages:
        await echo.receive_message(
            ctx=ctx,
            content=msg,
            sender_id="alice",
            conversation_id=conv_id
        )

    # Recupera la cronologia
    print(f"\n--- Cronologia conversazione {conv_id} ---")
    history = await storage.get_messages(conv_id)
    for msg in history:
        direction = "->" if msg.sender == "alice" else "<-"
        print(f"  {direction} [{msg.sender}]: {msg.content}")

    # Mostra tutte le conversazioni
    print("\n--- Tutte le conversazioni ---")
    all_convs = storage.get_all_conversations()
    for cid, conv in all_convs.items():
        print(f"  {cid}: {conv.participants} ({len(conv.messages)} messaggi)")


async def interactive_mode():
    """Modalita' interattiva per testare gli agenti."""
    print("\n" + "="*60)
    print("MODALITA' INTERATTIVA")
    print("="*60)

    storage = MemoryStorage()

    # Setup agenti
    calculator = CalculatorAgent("calc", storage)
    echo = EchoAgent("echo", storage)
    counter = CounterAgent("counter", storage)

    router = RouterAgent("router", storage)
    router.add_route("calcola", calculator)
    router.add_route("ripeti", echo)
    router.add_route("conta", counter)

    ctx = user_context("interactive_user")

    print("\nAgenti disponibili:")
    print("  - 'calcola X + Y' -> Calculator")
    print("  - 'ripeti ...' -> Echo")
    print("  - 'conta ...' -> Counter")
    print("\nScrivi 'exit' per uscire.\n")

    while True:
        try:
            user_input = input("Tu: ").strip()
            if user_input.lower() == 'exit':
                print("Arrivederci!")
                break

            if not user_input:
                continue

            response = await router.receive_message(
                ctx=ctx,
                content=user_input,
                sender_id="interactive_user"
            )
            print(f"Agente: {response.content}\n")

        except KeyboardInterrupt:
            print("\nInterrotto.")
            break
        except Exception as e:
            print(f"Errore: {e}\n")


async def main():
    """Entry point principale."""
    print("="*60)
    print("  SISTEMA MULTI-AGENTE - DEMO")
    print("="*60)

    # Esegui tutte le demo
    await demo_basic_agents()
    await demo_agent_to_agent()
    await demo_permissions()
    await demo_calculator()
    await demo_conversation_history()

    # Chiedi se avviare modalita' interattiva
    print("\n" + "="*60)
    choice = input("Vuoi provare la modalita' interattiva? (s/n): ").strip().lower()
    if choice == 's':
        await interactive_mode()

    print("\nDemo completate!")


if __name__ == "__main__":
    asyncio.run(main())
