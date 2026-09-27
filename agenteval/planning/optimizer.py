"""Test pack optimizer: mandatory security floor + greedy weighted set cover."""

from collections.abc import Callable

from agenteval.planning.models import (
    BudgetProjection,
    CandidateTest,
    MandatoryCategory,
    OptimizationResult,
    OptimizerConfig,
    PriorityTier,
    TestPack,
)


def _scoring_tags(tags: set[str]) -> set[str]:
    """Tags used for set-cover (persona diversity is not one test per persona tag)."""
    return {t for t in tags if not t.startswith("persona:")}


class TestPackOptimizer:
    """Selects a minimal high-value test pack from a candidate pool."""

    def optimize(
        self,
        agent_id: str,
        candidates: list[CandidateTest],
        config: OptimizerConfig,
        requirements_fingerprint: str = "",
        pack_version: int = 1,
    ) -> OptimizationResult:
        """Build a test pack up to max_tests honoring mandatory floors and optional tier filters."""
        if not candidates:
            pack = TestPack(
                agent_id=agent_id,
                version=pack_version,
                tests=[],
                candidate_count=0,
                requirements_fingerprint=requirements_fingerprint,
            )
            return OptimizationResult(
                pack=pack,
                mandatory_missing=list(config.applicable_mandatory),
            )

        # 0. Filter by max allowed priority tier if requested
        if config.max_tier in (PriorityTier.P0_CRITICAL, "P0"):
            allowed_tiers = {PriorityTier.P0_CRITICAL}
        elif config.max_tier in (PriorityTier.P1_RECOMMENDED, "P1"):
            allowed_tiers = {PriorityTier.P0_CRITICAL, PriorityTier.P1_RECOMMENDED}
        else:
            allowed_tiers = {
                PriorityTier.P0_CRITICAL,
                PriorityTier.P1_RECOMMENDED,
                PriorityTier.P2_EXTENDED,
            }

        eligible_candidates = [c for c in candidates if c.priority_tier in allowed_tiers]

        selected: list[CandidateTest] = []
        selected_ids: set[str] = set()
        covered_tags: set[str] = set()
        covered_scoring: set[str] = set()
        covered_mandatory: set[MandatoryCategory] = set()

        def add(test: CandidateTest) -> None:
            if test.id in selected_ids:
                return
            selected.append(test)
            selected_ids.add(test.id)
            covered_tags.update(test.coverage_tags)
            covered_scoring.update(_scoring_tags(set(test.coverage_tags)))
            covered_mandatory.update(test.mandatory_categories)

        # 1. User-selected test cases (seeds from interactive UI)
        if config.selected_test_ids:
            wanted_ids = set(config.selected_test_ids)
            for c in eligible_candidates:
                if c.id in wanted_ids and len(selected) < config.max_tests:
                    add(c)

        # 2. Explicit mandatory flags
        for c in sorted(eligible_candidates, key=lambda t: t.id):
            if c.is_mandatory and len(selected) < config.max_tests:
                add(c)

        # 3. Mandatory category floor
        applicable = set(config.applicable_mandatory)
        self._fill_mandatory_gaps(
            eligible_candidates,
            selected_ids,
            add,
            applicable,
            covered_mandatory,
            max_tests=config.max_tests,
            current_count=lambda: len(selected),
        )

        # 4. Greedy weighted set cover on coverage tags
        while len(selected) < config.max_tests:
            best: CandidateTest | None = None
            best_score = 0.0
            for c in eligible_candidates:
                if c.id in selected_ids:
                    continue
                new_tags = _scoring_tags(set(c.coverage_tags)) - covered_scoring
                if not new_tags and not (applicable - covered_mandatory):
                    continue
                score = sum(config.tag_weights.get(t, 1.0) for t in new_tags) / c.execution_cost
                # Boost tests that also close mandatory gaps
                gap_m = set(c.mandatory_categories) & (applicable - covered_mandatory)
                score += len(gap_m) * 10.0
                if score > best_score:
                    best_score = score
                    best = c
            if best is None or best_score <= 0:
                break
            add(best)

        missing = sorted(applicable - covered_mandatory, key=lambda m: m.value)
        removed_as_redundant = max(0, len(eligible_candidates) - len(selected))

        pack = TestPack(
            agent_id=agent_id,
            version=pack_version,
            tests=selected,
            candidate_count=len(candidates),
            requirements_fingerprint=requirements_fingerprint,
        )
        return OptimizationResult(
            pack=pack,
            selected_ids=[t.id for t in selected],
            removed_as_redundant=removed_as_redundant,
            mandatory_satisfied=sorted(covered_mandatory, key=lambda m: m.value),
            mandatory_missing=missing,
            tags_covered=sorted(covered_tags),
        )

    @staticmethod
    def compute_marginal_coverage_curve(
        candidates: list[CandidateTest],
        applicable_mandatory: list[MandatoryCategory] | None = None,
    ) -> list[BudgetProjection]:
        """Calculate marginal requirement coverage, latency, and token cost curves for P0, P1, and P2 tiers."""
        if not candidates:
            return []

        applicable = set(applicable_mandatory or [])
        total_applicable = len(applicable)

        p0_tests = [c for c in candidates if c.priority_tier == PriorityTier.P0_CRITICAL]
        p1_tests = [c for c in candidates if c.priority_tier == PriorityTier.P1_RECOMMENDED]

        all_caps = {c.capability_id for c in candidates}
        total_caps = len(all_caps) if all_caps else 1

        # Tier P0 (Smoke)
        p0_caps = {c.capability_id for c in p0_tests}
        p0_mand = {m for c in p0_tests for m in c.mandatory_categories} & applicable
        p0_cap_ratio = len(p0_caps) / total_caps
        p0_mand_ratio = len(p0_mand) / total_applicable if total_applicable else 1.0
        p0_cov = round(min(100.0, (p0_cap_ratio * 40.0 + p0_mand_ratio * 60.0)), 1)
        p0_count = len(p0_tests)

        # Tier P1 (Standard = P0 + P1)
        p1_cum_tests = p0_tests + p1_tests
        p1_caps = {c.capability_id for c in p1_cum_tests}
        p1_mand = {m for c in p1_cum_tests for m in c.mandatory_categories} & applicable
        p1_cap_ratio = len(p1_caps) / total_caps
        p1_mand_ratio = len(p1_mand) / total_applicable if total_applicable else 1.0
        p1_cov = round(min(100.0, max(p0_cov, p1_cap_ratio * 70.0 + p1_mand_ratio * 30.0)), 1)
        p1_count = len(p1_cum_tests)

        # Tier P2 (Full Audit = P0 + P1 + P2)
        p2_cum_tests = candidates
        p2_mand = {m for c in p2_cum_tests for m in c.mandatory_categories} & applicable
        p2_cov = 100.0
        p2_count = len(candidates)

        return [
            BudgetProjection(
                tier=PriorityTier.P0_CRITICAL,
                label="Smoke (P0 Critical)",
                target_test_count=p0_count,
                projected_coverage_pct=p0_cov,
                estimated_latency_ms=round(p0_count * 450.0, 1),
                estimated_cost_usd=round(p0_count * 0.005, 3),
                mandatory_floors_covered=len(p0_mand),
                mandatory_floors_total=total_applicable,
            ),
            BudgetProjection(
                tier=PriorityTier.P1_RECOMMENDED,
                label="Standard (P0 + P1 Recommended)",
                target_test_count=p1_count,
                projected_coverage_pct=p1_cov,
                estimated_latency_ms=round(p1_count * 450.0, 1),
                estimated_cost_usd=round(p1_count * 0.005, 3),
                mandatory_floors_covered=len(p1_mand),
                mandatory_floors_total=total_applicable,
            ),
            BudgetProjection(
                tier=PriorityTier.P2_EXTENDED,
                label="Full Audit (All Tiers)",
                target_test_count=p2_count,
                projected_coverage_pct=p2_cov,
                estimated_latency_ms=round(p2_count * 450.0, 1),
                estimated_cost_usd=round(p2_count * 0.005, 3),
                mandatory_floors_covered=len(p2_mand),
                mandatory_floors_total=total_applicable,
            ),
        ]

    @staticmethod
    def _fill_mandatory_gaps(
        candidates: list[CandidateTest],
        selected_ids: set[str],
        add: Callable[[CandidateTest], None],
        applicable: set[MandatoryCategory],
        covered_mandatory: set[MandatoryCategory],
        max_tests: int,
        current_count: Callable[[], int],
    ) -> None:
        missing = applicable - covered_mandatory
        while missing and current_count() < max_tests:
            best: CandidateTest | None = None
            best_fill = 0
            for c in candidates:
                if c.id in selected_ids:
                    continue
                fill = set(c.mandatory_categories) & missing
                if len(fill) > best_fill:
                    best_fill = len(fill)
                    best = c
            if best is None:
                break
            add(best)
            missing = applicable - covered_mandatory
