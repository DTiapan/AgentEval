"""Unit tests for AgentCard declarative manifest and protocol introspection (MCP & OpenAPI)."""

from pathlib import Path

from agenteval.core.manifest import AgentArchetype, AgentCard
from agenteval.introspect.mcp import MCPIntrospector
from agenteval.introspect.openapi import OpenAPIIntrospector


def test_agent_card_from_dict_and_yaml(tmp_path: Path) -> None:
    """Test loading and validating an AgentCard from dict and YAML file."""
    data = {
        "id": "order-fulfillment-bot",
        "name": "Order Fulfillment Assistant",
        "version": "1.2.0",
        "archetype": "TOOL_ACTION",
        "capabilities": [
            {
                "name": "charge_order",
                "description": "Process credit card payment",
                "idempotency_supported": True,
            }
        ],
        "tools_required": [
            {
                "name": "stripe_charge",
                "description": "External payment gateway API",
                "required": True,
            }
        ],
        "invariants": {
            "max_steps": 6,
            "forbidden_tools": ["delete_customer_account"],
            "approval_required_tools": ["refund_over_500"],
        },
    }

    # 1. From dict
    card = AgentCard.from_dict(data)
    assert card.id == "order-fulfillment-bot"
    assert card.archetype == AgentArchetype.TOOL_ACTION
    assert len(card.capabilities) == 1
    assert card.capabilities[0].idempotency_supported is True
    assert card.invariants.max_steps == 6
    assert "delete_customer_account" in card.invariants.forbidden_tools

    # 2. From YAML file
    yaml_file = tmp_path / "agenteval.manifest.yaml"
    import yaml

    yaml_file.write_text(yaml.dump(data), encoding="utf-8")
    card_from_file = AgentCard.from_yaml(yaml_file)
    assert card_from_file.id == "order-fulfillment-bot"
    assert card_from_file.version == "1.2.0"


def test_mcp_introspector_tools_list() -> None:
    """Test extracting IntrospectedTool catalog from MCP tools/list protocol response."""
    mcp_tools_response = {
        "tools": [
            {
                "name": "search_knowledge_base",
                "description": "Semantic search over product documents",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "top_k": {"type": "integer", "default": 5},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "execute_refund",
                "description": "Issue refund for an order",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string"},
                        "amount": {"type": "number"},
                    },
                    "required": ["order_id", "amount"],
                },
            },
        ]
    }

    introspector = MCPIntrospector()
    tools = introspector.extract_tools(mcp_tools_response)

    assert len(tools) == 2
    t1 = tools[0]
    assert t1.name == "search_knowledge_base"
    assert "query" in t1.parameters
    assert t1.required_args == ["query"]

    t2 = tools[1]
    assert t2.name == "execute_refund"
    assert "order_id" in t2.required_args
    assert "amount" in t2.required_args


def test_openapi_introspector_spec_parsing() -> None:
    """Test extracting tool operations from an OpenAPI 3.0 specification dict."""
    openapi_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Orders API", "version": "1.0.0"},
        "paths": {
            "/orders/{order_id}/cancel": {
                "post": {
                    "operationId": "cancel_order",
                    "summary": "Cancel an existing order",
                    "parameters": [
                        {
                            "name": "order_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                }
            },
            "/customers/search": {
                "get": {
                    "operationId": "search_customers",
                    "summary": "Search customers by email",
                    "parameters": [
                        {
                            "name": "email",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                }
            },
        },
    }

    introspector = OpenAPIIntrospector()
    tools = introspector.extract_tools(openapi_spec)

    assert len(tools) == 2
    tool_names = [t.name for t in tools]
    assert "cancel_order" in tool_names
    assert "search_customers" in tool_names

    cancel_op = next(t for t in tools if t.name == "cancel_order")
    assert cancel_op.required_args == ["order_id"]
