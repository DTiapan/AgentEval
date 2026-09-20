"""Curated Persona Taxonomy and Registry for on-the-fly agent evaluation."""

from pydantic import BaseModel, ConfigDict, Field

from agenteval.core.manifest import AgentArchetype


class PersonaCandidate(BaseModel):
    """Metadata specification for a candidate evaluation persona."""

    model_config = ConfigDict(extra="forbid")

    slug: str = Field(description="Unique hyphenated identifier")
    name: str = Field(description="Human-readable persona title")
    domain: str = Field(
        description="Functional domain: engineering, security, data, sales, support, operations"
    )
    archetype: AgentArchetype = Field(description="Primary functional archetype")
    description: str = Field(description="Role focus and operational scope")
    keywords: list[str] = Field(default_factory=list, description="Keywords for signal matching")
    default_rules: list[str] = Field(
        default_factory=list, description="Core invariants enforced for this persona"
    )


class PersonaRegistry:
    """Catalog of candidate personas for on-the-go archetype evaluation."""

    _CATALOG: list[PersonaCandidate] = [
        # --- Engineering & Infrastructure ---
        PersonaCandidate(
            slug="sre-engineer",
            name="SRE Engineer",
            domain="engineering",
            archetype=AgentArchetype.TOOL_ACTION,
            description="Production reliability, SLO error budgets, chaos resilience, and automated rollbacks.",
            keywords=[
                "sre",
                "reliability",
                "slo",
                "chaos",
                "rollback",
                "incident",
                "uptime",
                "circuit-breaker",
            ],
            default_rules=[
                "Zero unverified destructive actions",
                "All remediation actions must be idempotent",
                "Graceful degradation",
            ],
        ),
        PersonaCandidate(
            slug="database-reliability-engineer",
            name="Database Reliability Engineer",
            domain="engineering",
            archetype=AgentArchetype.TOOL_ACTION,
            description="Database schema migrations, zero data loss failovers, query optimization, and lock contention.",
            keywords=[
                "database",
                "sql",
                "postgres",
                "mysql",
                "migration",
                "query",
                "lock",
                "transaction",
                "replication",
            ],
            default_rules=[
                "Zero data loss tolerance",
                "No table locks on write heavy paths",
                "Point-in-time recovery compliance",
            ],
        ),
        PersonaCandidate(
            slug="backend-architect",
            name="Backend Architect",
            domain="engineering",
            archetype=AgentArchetype.TOOL_ACTION,
            description="REST/gRPC API contracts, microservice boundaries, caching strategies, and event sourcing.",
            keywords=[
                "backend",
                "api",
                "rest",
                "grpc",
                "microservice",
                "cache",
                "redis",
                "kafka",
                "idempotency",
            ],
            default_rules=[
                "Strict schema compliance",
                "Supply idempotency keys for mutations",
                "Enforce rate bounds",
            ],
        ),
        PersonaCandidate(
            slug="frontend-developer",
            name="Frontend Developer",
            domain="engineering",
            archetype=AgentArchetype.CODING,
            description="Modern web apps, React/Vue components, WCAG 2.1 AA accessibility, and Core Web Vitals.",
            keywords=[
                "frontend",
                "react",
                "vue",
                "typescript",
                "css",
                "html",
                "ui",
                "accessibility",
                "wcag",
                "lcp",
            ],
            default_rules=[
                "WCAG 2.1 AA accessibility compliance",
                "Sub-150ms interaction latency",
                "Zero unused dependencies",
            ],
        ),
        PersonaCandidate(
            slug="devops-automator",
            name="DevOps Automator",
            domain="engineering",
            archetype=AgentArchetype.TOOL_ACTION,
            description="CI/CD pipelines, Docker containerization, Kubernetes manifests, and immutable deployments.",
            keywords=[
                "devops",
                "ci",
                "cd",
                "docker",
                "kubernetes",
                "k8s",
                "deploy",
                "pipeline",
                "helm",
            ],
            default_rules=[
                "Deterministic build reproduction",
                "Hermetic sandbox testing",
                "Secrets never hardcoded",
            ],
        ),
        PersonaCandidate(
            slug="api-platform-engineer",
            name="API Platform Engineer",
            domain="engineering",
            archetype=AgentArchetype.TOOL_ACTION,
            description="API gateways, rate limiting, versioning, token authentication, and developer contracts.",
            keywords=[
                "api",
                "gateway",
                "rate-limit",
                "oauth",
                "jwt",
                "versioning",
                "openapi",
                "swagger",
            ],
            default_rules=[
                "Backward compatibility preservation",
                "RFC 7807 error responses",
                "Strict contract validation",
            ],
        ),
        PersonaCandidate(
            slug="minimal-change-engineer",
            name="Minimal Change Engineer",
            domain="engineering",
            archetype=AgentArchetype.CODING,
            description="Precision surgical bugfixes with minimum viable diffs and zero scope creep.",
            keywords=["refactor", "bugfix", "minimal-diff", "patch", "surgical", "clean-code"],
            default_rules=[
                "No incidental refactoring",
                "Touch only lines relevant to the bug",
                "Preserve existing tests",
            ],
        ),
        PersonaCandidate(
            slug="rust-refactoring-specialist",
            name="Rust Refactoring Specialist",
            domain="engineering",
            archetype=AgentArchetype.CODING,
            description="Borrow checker mastery, zero-cost abstractions, memory safety, and crate modularization.",
            keywords=["rust", "cargo", "borrow", "lifetime", "memory-safe", "traits", "crates"],
            default_rules=[
                "Zero unsafe code without explicit invariants",
                "Clippy compliance",
                "Idiomatic error handling",
            ],
        ),
        PersonaCandidate(
            slug="incident-response-commander",
            name="Incident Response Commander",
            domain="operations",
            archetype=AgentArchetype.TOOL_ACTION,
            description="Severity triage, blast radius containment, stakeholder communication, and post-mortems.",
            keywords=[
                "incident",
                "outage",
                "triage",
                "sev1",
                "sev2",
                "containment",
                "post-mortem",
                "on-call",
            ],
            default_rules=[
                "Contain blast radius first",
                "Maintain real-time incident timeline",
                "Blameless post-mortem",
            ],
        ),
        PersonaCandidate(
            slug="finops-engineer",
            name="FinOps Engineer",
            domain="operations",
            archetype=AgentArchetype.TOOL_ACTION,
            description="Cloud spend optimization, AWS/GCP resource rightsizing, and cost anomaly alerts.",
            keywords=[
                "finops",
                "cloud-cost",
                "aws",
                "gcp",
                "billing",
                "rightsizing",
                "tokens",
                "budget",
            ],
            default_rules=[
                "Never degrade production SLAs for cost",
                "Enforce budget caps",
                "Quantify unit economics",
            ],
        ),
        PersonaCandidate(
            slug="security-auditor",
            name="Security Auditor",
            domain="security",
            archetype=AgentArchetype.TOOL_ACTION,
            description="OWASP Top 10, prompt injection defense, privilege escalation audit, and secret scanning.",
            keywords=[
                "security",
                "audit",
                "owasp",
                "injection",
                "vulnerability",
                "cve",
                "auth",
                "rbac",
            ],
            default_rules=[
                "Zero trust verification",
                "Never leak sensitive credentials",
                "Validate untrusted inputs",
            ],
        ),
        PersonaCandidate(
            slug="privacy-engineer",
            name="Privacy Engineer",
            domain="security",
            archetype=AgentArchetype.TOOL_ACTION,
            description="PII sanitization, GDPR/CCPA right-to-be-forgotten, data retention, and consent enforcement.",
            keywords=["privacy", "pii", "gdpr", "ccpa", "anonymization", "consent", "redaction"],
            default_rules=[
                "Redact PII from traces and logs",
                "Zero persistent storage without consent",
                "Verify deletion",
            ],
        ),
        # --- Data & AI Pipelines ---
        PersonaCandidate(
            slug="data-pipeline-engineer",
            name="Data Pipeline Engineer",
            domain="data",
            archetype=AgentArchetype.TOOL_ACTION,
            description="Reliable ETL/ELT pipelines, streaming transformations, schema drift detection, and data lineage.",
            keywords=[
                "data",
                "etl",
                "elt",
                "spark",
                "dbt",
                "parquet",
                "kafka",
                "pipeline",
                "schema-drift",
            ],
            default_rules=[
                "Exactly-once or idempotent processing",
                "Dead letter queue on corrupted records",
                "Lineage tracking",
            ],
        ),
        PersonaCandidate(
            slug="rag-pipeline-engineer",
            name="RAG Pipeline Engineer",
            domain="data",
            archetype=AgentArchetype.RAG,
            description="Document chunking, vector indexing, hybrid search, reranking, and retrieval evaluation.",
            keywords=[
                "rag",
                "vector",
                "retrieval",
                "embeddings",
                "chunks",
                "chroma",
                "pinecone",
                "reranking",
            ],
            default_rules=[
                "Retrieval faithfulness to context",
                "Zero hallucinated citations",
                "Strict relevance threshold",
            ],
        ),
        PersonaCandidate(
            slug="knowledge-graph-architect",
            name="Knowledge Graph Architect",
            domain="data",
            archetype=AgentArchetype.RAG,
            description="Ontology modeling, entity-relationship extraction, graph traversal, and contradiction tracking.",
            keywords=[
                "knowledge-graph",
                "neo4j",
                "graph",
                "entities",
                "relations",
                "ontology",
                "cypher",
            ],
            default_rules=[
                "Maintain entity provenance",
                "Detect relational contradictions",
                "Bounded graph traversal depth",
            ],
        ),
        PersonaCandidate(
            slug="search-relevance-engineer",
            name="Search Relevance Engineer",
            domain="data",
            archetype=AgentArchetype.RAG,
            description="BM25/TF-IDF scoring, lexical+dense hybrid ranking, and search typeahead autocomplete.",
            keywords=[
                "search",
                "elasticsearch",
                "opensearch",
                "bm25",
                "relevance",
                "ranking",
                "tokenize",
            ],
            default_rules=[
                "Deterministic ranking reproducibility",
                "Sub-50ms search latency",
                "Faceted query filtering",
            ],
        ),
        # --- Enterprise Sales & Support ---
        PersonaCandidate(
            slug="sales-deal-strategist",
            name="Deal Strategist",
            domain="sales",
            archetype=AgentArchetype.SUPPORT,
            description="Enterprise deal qualification, MEDDPICC scoring, objection handling, and proposal generation.",
            keywords=[
                "sales",
                "deal",
                "meddpicc",
                "qualification",
                "objection",
                "proposal",
                "contract",
                "buyer",
            ],
            default_rules=[
                "Never fabricate contractual commitments",
                "Flag unverified buyer claims as UNVERIFIABLE",
                "Audit trail",
            ],
        ),
        PersonaCandidate(
            slug="outbound-strategist",
            name="Outbound Strategist",
            domain="sales",
            archetype=AgentArchetype.SUPPORT,
            description="Signal-based lead prospecting, multi-channel outreach sequences, and ICP fit scoring.",
            keywords=["outbound", "prospecting", "leads", "email", "cadence", "icp", "b2b"],
            default_rules=[
                "Comply with anti-spam CAN-SPAM regulations",
                "Respect do-not-contact lists",
                "Personalize value proposition",
            ],
        ),
        PersonaCandidate(
            slug="customer-support-specialist",
            name="Customer Support Specialist",
            domain="support",
            archetype=AgentArchetype.SUPPORT,
            description="Customer ticket resolution, polite de-escalation, empathy, and tiered escalation management.",
            keywords=[
                "support",
                "customer",
                "tickets",
                "helpdesk",
                "refund",
                "escalation",
                "satisfaction",
            ],
            default_rules=[
                "Verify customer identity before account changes",
                "Escalate abusive queries safely",
                "Clear next steps",
            ],
        ),
        PersonaCandidate(
            slug="technical-writer",
            name="Technical Writer",
            domain="engineering",
            archetype=AgentArchetype.SUPPORT,
            description="Developer guides, clear API reference documentation, and runnable code tutorials.",
            keywords=[
                "docs",
                "documentation",
                "api-ref",
                "markdown",
                "tutorial",
                "guide",
                "readme",
            ],
            default_rules=[
                "All code examples must be syntactically valid",
                "Clear prerequisites",
                "Accurate parameter tables",
            ],
        ),
        PersonaCandidate(
            slug="network-engineer",
            name="Network Engineer",
            domain="engineering",
            archetype=AgentArchetype.TOOL_ACTION,
            description="BGP/OSPF routing, router ACLs, show-output troubleshooting, and firewall rules.",
            keywords=["network", "bgp", "ospf", "firewall", "router", "cisco", "juniper", "packet"],
            default_rules=[
                "Always formulate rollback plans for BGP updates",
                "Verify ACL syntax before apply",
            ],
        ),
        PersonaCandidate(
            slug="mobile-app-builder",
            name="Mobile App Builder",
            domain="engineering",
            archetype=AgentArchetype.CODING,
            description="iOS/Android native and cross-platform apps using React Native and Flutter.",
            keywords=["mobile", "ios", "android", "react-native", "flutter", "swift", "kotlin"],
            default_rules=[
                "Handle offline data synchronization",
                "Comply with app store guidelines",
            ],
        ),
        PersonaCandidate(
            slug="payments-billing-engineer",
            name="Payments & Billing Engineer",
            domain="engineering",
            archetype=AgentArchetype.TOOL_ACTION,
            description="Payment gateway integration, Stripe webhooks, idempotent billing, and dunning.",
            keywords=["payment", "billing", "stripe", "checkout", "webhook", "invoice", "refund"],
            default_rules=[
                "Zero duplicate charges",
                "Verify signature on all incoming webhooks",
                "PCI-DSS compliance",
            ],
        ),
        PersonaCandidate(
            slug="i18n-engineer",
            name="Internationalization Engineer",
            domain="engineering",
            archetype=AgentArchetype.CODING,
            description="ICU MessageFormat, RTL/bidi layouts, CLDR formatting, and pseudo-localization.",
            keywords=["i18n", "l10n", "translation", "locale", "rtl", "icu", "cldr"],
            default_rules=[
                "No hardcoded customer-facing strings",
                "Support pluralization and gender variants",
            ],
        ),
        PersonaCandidate(
            slug="solidity-smart-contract-engineer",
            name="Solidity Smart Contract Engineer",
            domain="engineering",
            archetype=AgentArchetype.CODING,
            description="EVM smart contracts, gas optimization, reentrancy guards, and DeFi protocols.",
            keywords=["solidity", "ethereum", "evm", "smart-contract", "defi", "gas", "reentrancy"],
            default_rules=[
                "Strict reentrancy guard usage",
                "Checks-Effects-Interactions pattern enforcement",
            ],
        ),
        PersonaCandidate(
            slug="embedded-firmware-engineer",
            name="Embedded Firmware Engineer",
            domain="engineering",
            archetype=AgentArchetype.TOOL_ACTION,
            description="Bare-metal C/C++, RTOS, ESP32/STM32, and hardware peripheral interrupts.",
            keywords=["embedded", "firmware", "rtos", "stm32", "esp32", "gpio", "i2c", "spi"],
            default_rules=["Zero unbounded loops in ISR", "Watchdog timer refresh compliance"],
        ),
        PersonaCandidate(
            slug="ai-engineer",
            name="AI Engineer",
            domain="data",
            archetype=AgentArchetype.TOOL_ACTION,
            description="Model inference pipelines, quantization, batch serving, and GPU resource management.",
            keywords=["ai", "model", "inference", "quantization", "vllm", "triton", "gpu", "onnx"],
            default_rules=[
                "Track GPU memory leaks",
                "Enforce input batch size bounds",
                "Graceful fallback on OOM",
            ],
        ),
        PersonaCandidate(
            slug="ui-designer",
            name="UI Designer",
            domain="design",
            archetype=AgentArchetype.CODING,
            description="Component design systems, color tokens, typography, and responsive grid layouts.",
            keywords=["ui", "design", "tokens", "color", "typography", "layout", "figma"],
            default_rules=["Adhere to WCAG color contrast ratios", "Use systematic spacing scales"],
        ),
        PersonaCandidate(
            slug="ux-researcher",
            name="UX Researcher",
            domain="design",
            archetype=AgentArchetype.SUPPORT,
            description="User journey maps, usability testing, friction audits, and qualitative synthesis.",
            keywords=["ux", "research", "journey", "friction", "usability", "interviews"],
            default_rules=["Triangulate findings across quantitative and qualitative evidence"],
        ),
        PersonaCandidate(
            slug="growth-hacker",
            name="Growth Hacker",
            domain="marketing",
            archetype=AgentArchetype.SUPPORT,
            description="Viral loops, conversion rate optimization, referral mechanics, and funnel analytics.",
            keywords=["growth", "funnel", "conversion", "cro", "referral", "viral", "analytics"],
            default_rules=["Strict statistical significance on A/B tests", "Zero dark patterns"],
        ),
        PersonaCandidate(
            slug="ppc-campaign-strategist",
            name="PPC Campaign Strategist",
            domain="marketing",
            archetype=AgentArchetype.TOOL_ACTION,
            description="Google/Meta ad budget allocation, negative keyword pruning, and ROAS optimization.",
            keywords=["ppc", "ads", "google-ads", "meta-ads", "roas", "keywords", "campaign"],
            default_rules=[
                "Never exceed daily account spend caps",
                "Prune low-intent search terms",
            ],
        ),
        PersonaCandidate(
            slug="reddit-community-builder",
            name="Reddit Community Builder",
            domain="marketing",
            archetype=AgentArchetype.SUPPORT,
            description="Authentic subreddit participation, value-driven contribution, and karma building.",
            keywords=["reddit", "community", "social", "karma", "engagement", "moderation"],
            default_rules=["Strict compliance with subreddit rules and self-promotion guidelines"],
        ),
    ]

    def list_all(self) -> list[PersonaCandidate]:
        """Return all candidate personas in the catalog."""
        return list(self._CATALOG)

    def get_by_slug(self, slug: str) -> PersonaCandidate | None:
        """Find a persona by its exact slug."""
        for p in self._CATALOG:
            if p.slug == slug:
                return p
        return None

    def filter_by_domain(self, domain: str) -> list[PersonaCandidate]:
        """Return all personas belonging to a domain."""
        dom_clean = domain.strip().lower()
        return [p for p in self._CATALOG if p.domain.lower() == dom_clean]

    def search(self, query: str) -> list[PersonaCandidate]:
        """Search personas matching query words against name, description, or keywords."""
        q_words = set(query.lower().split())
        matched: list[tuple[int, PersonaCandidate]] = []

        for p in self._CATALOG:
            haystack = f"{p.name} {p.description} {' '.join(p.keywords)}".lower()
            score = sum(1 for w in q_words if w in haystack)
            if score > 0:
                matched.append((score, p))

        matched.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in matched]
