"""OpenAPI 3.0 / Swagger schema introspector for HTTP REST agents."""

from typing import Any

from agenteval.introspect.models import IntrospectedTool


class OpenAPIIntrospector:
    """Extracts callable operations and parameters from OpenAPI specifications."""

    def extract_tools(self, spec: dict[str, Any]) -> list[IntrospectedTool]:
        """Convert OpenAPI path operations into normalized IntrospectedTool objects."""
        paths = spec.get("paths", {})
        discovered: list[IntrospectedTool] = []

        for path_str, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            for method, operation in path_item.items():
                if method.lower() not in {"get", "post", "put", "delete", "patch"}:
                    continue
                if not isinstance(operation, dict):
                    continue

                operation_id = (
                    operation.get("operationId")
                    or f"{method.lower()}_{path_str.strip('/').replace('/', '_')}"
                )
                summary = operation.get("summary") or operation.get("description")

                parameters: dict[str, Any] = {}
                required_args: list[str] = []

                # Path/Query/Header parameters
                for param in operation.get("parameters", []):
                    if not isinstance(param, dict):
                        continue
                    p_name = param.get("name")
                    if not p_name:
                        continue
                    parameters[p_name] = param.get("schema", {})
                    if param.get("required"):
                        required_args.append(p_name)

                # Request body properties (JSON)
                request_body = operation.get("requestBody", {})
                if isinstance(request_body, dict):
                    content = request_body.get("content", {})
                    app_json = content.get("application/json", {})
                    schema = app_json.get("schema", {})
                    props = schema.get("properties", {})
                    for prop_name, prop_def in props.items():
                        parameters[prop_name] = prop_def
                    for req_name in schema.get("required", []):
                        if req_name not in required_args:
                            required_args.append(req_name)

                discovered.append(
                    IntrospectedTool(
                        name=operation_id,
                        description=summary,
                        parameters=parameters,
                        required_args=required_args,
                    )
                )

        return discovered
