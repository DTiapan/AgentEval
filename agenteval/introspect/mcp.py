"""MCP (Model Context Protocol) tool discovery and schema extractor."""

from typing import Any

from agenteval.introspect.models import IntrospectedTool


class MCPIntrospector:
    """Extracts standardized IntrospectedTool catalogs from MCP responses."""

    def extract_tools(self, tools_list_response: dict[str, Any]) -> list[IntrospectedTool]:
        """Parse raw response from MCP tools/list method into normalized tools."""
        raw_tools = tools_list_response.get("tools", [])
        discovered: list[IntrospectedTool] = []

        for item in raw_tools:
            name = item.get("name", "")
            description = item.get("description")
            input_schema = item.get("inputSchema", {})
            properties = input_schema.get("properties", {})
            required = input_schema.get("required", [])

            discovered.append(
                IntrospectedTool(
                    name=name,
                    description=description,
                    parameters=properties,
                    required_args=required,
                )
            )

        return discovered
