"""Combine requirements ingest + optional endpoint probe (North Star E1+E2)."""

from pathlib import Path

from agenteval.core.manifest import AgentCard
from agenteval.ingest.endpoint_probe import EndpointProber, EndpointProbeResult
from agenteval.ingest.requirements import RequirementsIngestor
from agenteval.planning.bootstrap import SuiteBootstrap
from agenteval.targets import TargetConnectionProfile


class AgentBootstrap:
    """Build AgentCard and fingerprint from customer inputs."""

    @classmethod
    def from_prd(
        cls,
        prd_path: Path,
        *,
        agent_id: str | None = None,
        endpoint_url: str | None = None,
        probe_endpoint: bool = True,
        headers: dict[str, str] | None = None,
        connection_profile: TargetConnectionProfile | None = None,
    ) -> tuple[AgentCard, str, EndpointProbeResult | None]:
        card = RequirementsIngestor.from_file(prd_path, agent_id=agent_id)
        fingerprint = SuiteBootstrap.fingerprint_prd(prd_path)
        probe_result: EndpointProbeResult | None = None

        target_url = (
            connection_profile.endpoint_url
            if connection_profile and connection_profile.endpoint_url
            else endpoint_url
        )

        if target_url and probe_endpoint:
            with EndpointProber() as prober:
                probe_result = prober.probe(
                    target_url,
                    headers=headers,
                    profile=connection_profile,
                )
                card = EndpointProber.merge_tools(card, probe_result)
                eff_headers = (
                    connection_profile.resolve_headers() if connection_profile else headers
                )
                openapi_tools = prober.try_fetch_openapi_tools(target_url, headers=eff_headers)
                if openapi_tools:
                    extra = EndpointProbeResult(
                        endpoint_url=target_url,
                        reachable=probe_result.reachable,
                        inferred_tool_names=openapi_tools,
                    )
                    card = EndpointProber.merge_tools(card, extra)

        return card, fingerprint, probe_result

    @classmethod
    def from_text(
        cls,
        prd_text: str,
        *,
        agent_id: str,
        endpoint_url: str | None = None,
        probe_endpoint: bool = True,
        headers: dict[str, str] | None = None,
        connection_profile: TargetConnectionProfile | None = None,
    ) -> tuple[AgentCard, str, EndpointProbeResult | None]:
        card = RequirementsIngestor.from_text(prd_text, agent_id=agent_id)
        fingerprint = RequirementsIngestor.fingerprint_text(prd_text)
        probe_result: EndpointProbeResult | None = None

        target_url = (
            connection_profile.endpoint_url
            if connection_profile and connection_profile.endpoint_url
            else endpoint_url
        )

        if target_url and probe_endpoint:
            with EndpointProber() as prober:
                probe_result = prober.probe(
                    target_url,
                    headers=headers,
                    profile=connection_profile,
                )
                card = EndpointProber.merge_tools(card, probe_result)
                eff_headers = (
                    connection_profile.resolve_headers() if connection_profile else headers
                )
                openapi_tools = prober.try_fetch_openapi_tools(target_url, headers=eff_headers)
                if openapi_tools:
                    extra = EndpointProbeResult(
                        endpoint_url=target_url,
                        reachable=probe_result.reachable,
                        inferred_tool_names=openapi_tools,
                    )
                    card = EndpointProber.merge_tools(card, extra)

        return card, fingerprint, probe_result
