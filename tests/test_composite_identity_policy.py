from dataclasses import dataclass

import pytest


@dataclass(frozen=True)
class CompositeAuthorizationCase:
    name: str
    user_scope_matches: bool
    agent_delegated: bool
    tool_allowed: bool
    session_active: bool
    sensitive_external_export: bool
    expected: tuple[str, str]


def decide(case: CompositeAuthorizationCase) -> tuple[str, str]:
    if not case.session_active:
        return "deny", "session_expired_or_revoked"
    if not case.agent_delegated:
        return "deny", "delegation_chain_invalid"
    if not case.user_scope_matches:
        return "deny", "human_resource_scope_mismatch"
    if not case.tool_allowed:
        return "deny", "tool_not_allowed"
    if case.sensitive_external_export:
        return "deny", "toxic_combination_sensitive_export"
    return "allow", "composite_scope_valid"


CASES = [
    CompositeAuthorizationCase(
        "owner_read",
        user_scope_matches=True,
        agent_delegated=True,
        tool_allowed=True,
        session_active=True,
        sensitive_external_export=False,
        expected=("allow", "composite_scope_valid"),
    ),
    CompositeAuthorizationCase(
        "clinician_redacted_summary",
        user_scope_matches=True,
        agent_delegated=True,
        tool_allowed=True,
        session_active=True,
        sensitive_external_export=False,
        expected=("allow", "composite_scope_valid"),
    ),
    CompositeAuthorizationCase(
        "non_owner_read",
        user_scope_matches=False,
        agent_delegated=True,
        tool_allowed=True,
        session_active=True,
        sensitive_external_export=False,
        expected=("deny", "human_resource_scope_mismatch"),
    ),
    CompositeAuthorizationCase(
        "toxic_combination_sensitive_export",
        user_scope_matches=True,
        agent_delegated=True,
        tool_allowed=True,
        session_active=True,
        sensitive_external_export=True,
        expected=("deny", "toxic_combination_sensitive_export"),
    ),
    CompositeAuthorizationCase(
        "broken_delegation_chain",
        user_scope_matches=True,
        agent_delegated=False,
        tool_allowed=True,
        session_active=True,
        sensitive_external_export=False,
        expected=("deny", "delegation_chain_invalid"),
    ),
    CompositeAuthorizationCase(
        "expired_or_revoked_session",
        user_scope_matches=True,
        agent_delegated=True,
        tool_allowed=True,
        session_active=False,
        sensitive_external_export=False,
        expected=("deny", "session_expired_or_revoked"),
    ),
]


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
def test_composite_identity_policy(case: CompositeAuthorizationCase) -> None:
    assert decide(case) == case.expected
