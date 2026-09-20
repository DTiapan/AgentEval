"""Combine requirements ingest + optional endpoint probe (North Star E1+E2)."""

from pathlib import Path

from agenteval.core.manifest import AgentCard
from agenteval.ingest.endpoint_probe import EndpointProber, EndpointProbeResult
from agenteval.ingest.requirements import RequirementsIngestor
from agenteval.planning.bootstrap import SuiteBootstrap


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
    ) -> tuple[AgentCard, str, EndpointProbeResult | None]:
        card = RequirementsIngestor.from_file(prd_path, agent_id=agent_id)
        fingerprint = SuiteBootstrap.fingerprint_prd(prd_path)
        probe_result: EndpointProbeResult | None = None

        if endpoint_url and probe_endpoint:
            prober = EndpointProber()
            probe_result = prober.probe(endpoint_url)
            card = EndpointProber.merge_tools(card, probe_result)
            openapi_tools = prober.try_fetch_openapi_tools(endpoint_url)
            if openapi_tools:
                extra = EndpointProbeResult(
                    endpoint_url=endpoint_url,
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
    ) -> tuple[AgentCard, str, EndpointProbeResult | None]:
        card = RequirementsIngestor.from_text(prd_text, agent_id=agent_id)
        fingerprint = RequirementsIngestor.fingerprint_text(prd_text)
        probe_result: EndpointProbeResult | None = None

        if endpoint_url and probe_endpoint:
            prober = EndpointProber()
            probe_result = prober.probe(endpoint_url)
            card = EndpointProber.merge_tools(card, probe_result)
            openapi_tools = prober.try_fetch_openapi_tools(endpoint_url)
            if openapi_tools:
                extra = EndpointProbeResult(
                    endpoint_url=endpoint_url,
                    reachable=probe_result.reachable,
                    inferred_tool_names=openapi_tools,
                )
                card = EndpointProber.merge_tools(card, extra)

        return card, fingerprint, probe_result
