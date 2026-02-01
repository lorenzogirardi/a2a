"""
Sistema di Permessi - Controlla cosa può fare ogni caller.

CONCETTO CHIAVE: Quando qualcuno chiama un agente, dobbiamo sapere:
1. CHI sta chiamando (identità)
2. COSA può fare (permessi)
3. QUALI dati può vedere (scope)

Questo modulo implementa un sistema semplice ma estendibile.
"""

from enum import Enum
from typing import Callable, Any
from functools import wraps
from pydantic import BaseModel


class Role(str, Enum):
    """Ruoli disponibili nel sistema."""
    ADMIN = "admin"       # Può fare tutto
    USER = "user"         # Può interagire normalmente
    GUEST = "guest"       # Solo lettura
    AGENT = "agent"       # Un altro agente (fiducia intermedia)


class Permission(str, Enum):
    """Permessi granulari."""
    READ_MESSAGES = "read_messages"
    SEND_MESSAGES = "send_messages"
    MODIFY_STATE = "modify_state"
    READ_STATE = "read_state"
    CREATE_CONVERSATION = "create_conversation"
    DELETE_CONVERSATION = "delete_conversation"
    MANAGE_AGENTS = "manage_agents"


# Mapping ruolo -> permessi
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.ADMIN: set(Permission),  # Tutti i permessi
    Role.USER: {
        Permission.READ_MESSAGES,
        Permission.SEND_MESSAGES,
        Permission.READ_STATE,
        Permission.CREATE_CONVERSATION,
    },
    Role.GUEST: {
        Permission.READ_MESSAGES,
        Permission.READ_STATE,
    },
    Role.AGENT: {
        Permission.READ_MESSAGES,
        Permission.SEND_MESSAGES,
        Permission.MODIFY_STATE,
        Permission.READ_STATE,
        Permission.CREATE_CONVERSATION,
    },
}


class CallerContext(BaseModel):
    """
    Contesto di chi sta facendo la chiamata.

    Questo oggetto viene passato ad ogni operazione per verificare i permessi.
    """
    caller_id: str                    # ID univoco del caller
    role: Role = Role.GUEST           # Ruolo del caller
    custom_permissions: set[str] = set()  # Permessi extra oltre al ruolo
    metadata: dict = {}               # Info aggiuntive (IP, timestamp, etc.)

    def has_permission(self, permission: Permission) -> bool:
        """Verifica se il caller ha un determinato permesso."""
        # Admin ha sempre tutti i permessi
        if self.role == Role.ADMIN:
            return True

        # Controlla permessi del ruolo
        role_perms = ROLE_PERMISSIONS.get(self.role, set())
        if permission in role_perms:
            return True

        # Controlla permessi custom
        return permission.value in self.custom_permissions

    def get_all_permissions(self) -> set[Permission]:
        """Ritorna tutti i permessi del caller."""
        base_perms = ROLE_PERMISSIONS.get(self.role, set())
        custom = {Permission(p) for p in self.custom_permissions if p in Permission._value2member_map_}
        return base_perms | custom


class PermissionDenied(Exception):
    """Eccezione quando un'operazione non è permessa."""
    def __init__(self, caller_id: str, permission: Permission, operation: str):
        self.caller_id = caller_id
        self.permission = permission
        self.operation = operation
        super().__init__(
            f"Caller '{caller_id}' non ha il permesso '{permission.value}' "
            f"per l'operazione '{operation}'"
        )


def requires_permission(permission: Permission):
    """
    Decorator per proteggere metodi con controllo permessi.

    Uso:
        @requires_permission(Permission.SEND_MESSAGES)
        async def send_message(self, ctx: CallerContext, message: str):
            ...

    Il metodo deve avere CallerContext come primo argomento (dopo self).
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Trova il CallerContext negli argomenti
            ctx = None
            for arg in args:
                if isinstance(arg, CallerContext):
                    ctx = arg
                    break

            if ctx is None:
                ctx = kwargs.get('ctx') or kwargs.get('caller_context')

            if ctx is None:
                raise ValueError(
                    f"Metodo {func.__name__} richiede CallerContext ma non è stato fornito"
                )

            # Verifica permesso
            if not ctx.has_permission(permission):
                raise PermissionDenied(ctx.caller_id, permission, func.__name__)

            # Log dell'operazione (utile per audit)
            print(f"[Auth] {ctx.caller_id} ({ctx.role.value}) -> {func.__name__}")

            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Utility per creare contesti comuni
def admin_context(caller_id: str = "admin") -> CallerContext:
    """Crea un contesto admin per testing/setup."""
    return CallerContext(caller_id=caller_id, role=Role.ADMIN)


def user_context(caller_id: str) -> CallerContext:
    """Crea un contesto utente normale."""
    return CallerContext(caller_id=caller_id, role=Role.USER)


def agent_context(agent_id: str) -> CallerContext:
    """Crea un contesto per un agente che chiama un altro agente."""
    return CallerContext(caller_id=agent_id, role=Role.AGENT)


def guest_context(caller_id: str = "anonymous") -> CallerContext:
    """Crea un contesto guest (solo lettura)."""
    return CallerContext(caller_id=caller_id, role=Role.GUEST)
