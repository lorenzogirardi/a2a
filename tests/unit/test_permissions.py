"""Unit tests for permission system."""

import pytest

from auth import (
    Role,
    Permission,
    CallerContext,
    PermissionDenied,
    requires_permission,
    admin_context,
    user_context,
    guest_context,
    agent_context,
    ROLE_PERMISSIONS,
)


class TestCallerContext:
    """Tests for CallerContext."""

    def test_create_context(self):
        """Should create a context with default values."""
        ctx = CallerContext(caller_id="test")

        assert ctx.caller_id == "test"
        assert ctx.role == Role.GUEST
        assert ctx.custom_permissions == set()

    def test_admin_has_all_permissions(self):
        """Admin should have all permissions."""
        ctx = admin_context("admin")

        for perm in Permission:
            assert ctx.has_permission(perm) is True

    def test_user_permissions(self):
        """User should have limited permissions."""
        ctx = user_context("user")

        assert ctx.has_permission(Permission.READ_MESSAGES) is True
        assert ctx.has_permission(Permission.SEND_MESSAGES) is True
        assert ctx.has_permission(Permission.READ_STATE) is True
        assert ctx.has_permission(Permission.MANAGE_AGENTS) is False

    def test_guest_permissions(self):
        """Guest should have read-only permissions."""
        ctx = guest_context("guest")

        assert ctx.has_permission(Permission.READ_MESSAGES) is True
        assert ctx.has_permission(Permission.READ_STATE) is True
        assert ctx.has_permission(Permission.SEND_MESSAGES) is False
        assert ctx.has_permission(Permission.MODIFY_STATE) is False

    def test_agent_permissions(self):
        """Agent context should have agent-to-agent permissions."""
        ctx = agent_context("agent-1")

        assert ctx.has_permission(Permission.SEND_MESSAGES) is True
        assert ctx.has_permission(Permission.MODIFY_STATE) is True
        assert ctx.has_permission(Permission.MANAGE_AGENTS) is False

    def test_custom_permissions(self):
        """Should support custom permissions."""
        ctx = CallerContext(
            caller_id="custom",
            role=Role.GUEST,
            custom_permissions={"send_messages"}
        )

        # Has custom permission
        assert ctx.has_permission(Permission.SEND_MESSAGES) is True
        # Still doesn't have non-custom permission not in role
        assert ctx.has_permission(Permission.MODIFY_STATE) is False

    def test_get_all_permissions(self):
        """Should return all permissions for a context."""
        ctx = user_context("user")
        perms = ctx.get_all_permissions()

        assert Permission.READ_MESSAGES in perms
        assert Permission.SEND_MESSAGES in perms
        assert Permission.MANAGE_AGENTS not in perms


class TestRolePermissions:
    """Tests for role-permission mapping."""

    def test_admin_role_has_all(self):
        """Admin role should have all permissions."""
        admin_perms = ROLE_PERMISSIONS[Role.ADMIN]
        assert admin_perms == set(Permission)

    def test_guest_role_is_limited(self):
        """Guest role should only have read permissions."""
        guest_perms = ROLE_PERMISSIONS[Role.GUEST]

        assert Permission.READ_MESSAGES in guest_perms
        assert Permission.READ_STATE in guest_perms
        assert len(guest_perms) == 2


class TestRequiresPermissionDecorator:
    """Tests for @requires_permission decorator."""

    @pytest.mark.asyncio
    async def test_allows_with_permission(self):
        """Should allow call when permission is present."""

        @requires_permission(Permission.SEND_MESSAGES)
        async def protected_func(ctx: CallerContext, value: str) -> str:
            return f"success: {value}"

        ctx = user_context("user")
        result = await protected_func(ctx, "test")

        assert result == "success: test"

    @pytest.mark.asyncio
    async def test_denies_without_permission(self):
        """Should raise PermissionDenied when permission is missing."""

        @requires_permission(Permission.MANAGE_AGENTS)
        async def admin_only(ctx: CallerContext) -> str:
            return "secret"

        ctx = user_context("user")

        with pytest.raises(PermissionDenied) as exc_info:
            await admin_only(ctx)

        assert exc_info.value.caller_id == "user"
        assert exc_info.value.permission == Permission.MANAGE_AGENTS

    @pytest.mark.asyncio
    async def test_works_with_kwargs(self):
        """Should find context in kwargs."""

        @requires_permission(Permission.READ_STATE)
        async def read_state(ctx: CallerContext) -> str:
            return "state"

        ctx = guest_context("guest")
        result = await read_state(ctx=ctx)

        assert result == "state"

    @pytest.mark.asyncio
    async def test_raises_without_context(self):
        """Should raise ValueError if no context provided."""

        @requires_permission(Permission.READ_STATE)
        async def no_context() -> str:
            return "oops"

        with pytest.raises(ValueError):
            await no_context()


class TestPermissionDenied:
    """Tests for PermissionDenied exception."""

    def test_exception_message(self):
        """Should have informative message."""
        exc = PermissionDenied("user123", Permission.MANAGE_AGENTS, "delete_agent")

        assert "user123" in str(exc)
        assert "manage_agents" in str(exc)
        assert "delete_agent" in str(exc)

    def test_exception_attributes(self):
        """Should store relevant attributes."""
        exc = PermissionDenied("user", Permission.SEND_MESSAGES, "send")

        assert exc.caller_id == "user"
        assert exc.permission == Permission.SEND_MESSAGES
        assert exc.operation == "send"
