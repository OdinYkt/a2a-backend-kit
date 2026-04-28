"""AgentCard builders shared by A2A backend adapters."""
# pyright: reportMissingImports=false

from __future__ import annotations

from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill


PROTOCOL_VERSION = "1.0"
TEXT_MIME_TYPE = "text/plain"


def build_text_agent_card(
    *,
    name: str,
    description: str,
    version: str,
    public_url: str,
    jsonrpc_url: str | None = None,
    include_rest: bool = True,
    skill_id: str,
    skill_name: str,
    skill_description: str,
    skill_tags: tuple[str, ...] = ("a2a",),
    streaming: bool,
) -> AgentCard:
    """Build a text-only A2A v1 AgentCard with JSON-RPC and REST interfaces."""

    normalized_url = public_url.rstrip("/")
    normalized_jsonrpc_url = (jsonrpc_url or normalized_url).rstrip("/")
    card = AgentCard(
        name=name,
        description=description,
        version=version,
    )
    card.capabilities.CopyFrom(
        AgentCapabilities(
            streaming=streaming,
            push_notifications=False,
            extended_agent_card=False,
        )
    )
    card.default_input_modes.append(TEXT_MIME_TYPE)
    card.default_output_modes.append(TEXT_MIME_TYPE)
    card.skills.append(
        AgentSkill(
            id=skill_id,
            name=skill_name,
            description=skill_description,
            tags=list(skill_tags),
        )
    )
    card.supported_interfaces.append(
        AgentInterface(
            url=normalized_jsonrpc_url,
            protocol_binding="JSONRPC",
            protocol_version=PROTOCOL_VERSION,
        )
    )
    if include_rest:
        card.supported_interfaces.append(
            AgentInterface(
                url=normalized_url,
                protocol_binding="REST",
                protocol_version=PROTOCOL_VERSION,
            )
        )
    return card
