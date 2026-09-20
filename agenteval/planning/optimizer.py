"""Test pack optimizer: mandatory security floor + greedy weighted set cover."""

from collections.abc import Callable

from agenteval.planning.models import (
    CandidateTest,
    MandatoryCategory,
    OptimizationResult,
    OptimizerConfig,
    TestPack,
)


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
        """Build a test pack up to max_tests honoring mandatory floors."""
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

        selected: list[CandidateTest] = []
        selected_ids: set[str] = set()
        covered_tags: set[str] = set()
        covered_mandatory: set[MandatoryCategory] = set()

        def add(test: CandidateTest) -> None:
            if test.id in selected_ids:
                return
            selected.append(test)
            selected_ids.add(test.id)
            covered_tags.update(test.coverage_tags)
            covered_mandatory.update(test.mandatory_categories)

        # 1. Explicit mandatory flags
        for c in sorted(candidates, key=lambda t: t.id):
            if c.is_mandatory:
                add(c)

        # 2. Mandatory category floor
        applicable = set(config.applicable_mandatory)
        self._fill_mandatory_gaps(candidates, selected_ids, add, applicable, covered_mandatory)

        # 3. Greedy weighted set cover on coverage tags
        while len(selected) < config.max_tests:
            best: CandidateTest | None = None
            best_score = 0.0
            for c in candidates:
                if c.id in selected_ids:
                    continue
                new_tags = set(c.coverage_tags) - covered_tags
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
        removed_as_redundant = max(0, len(candidates) - len(selected))

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
    def _fill_mandatory_gaps(
        candidates: list[CandidateTest],
        selected_ids: set[str],
        add: Callable[[CandidateTest], None],
        applicable: set[MandatoryCategory],
        covered_mandatory: set[MandatoryCategory],
    ) -> None:
        missing = applicable - covered_mandatory
        while missing:
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
