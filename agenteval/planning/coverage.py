"""Coverage mapping for selected or executed test packs."""

from collections import defaultdict

from agenteval.planning.models import (
    CandidateTest,
    CoverageReport,
    MandatoryCategory,
    OptimizerConfig,
)


class CoverageMapper:
    """Computes multi-axis coverage from pool vs selected/executed tests."""

    AXIS_PREFIXES = ("cap", "persona", "failure", "security", "integration", "invariant")

    def report(
        self,
        pool: list[CandidateTest],
        selected_or_executed: list[CandidateTest],
        applicable_mandatory: list[MandatoryCategory] | None = None,
    ) -> CoverageReport:
        """Compare pool tag universe to tags hit by the given tests."""
        pool_tags = {tag for c in pool for tag in c.coverage_tags}
        hit_tags: set[str] = set()
        hit_mandatory: set[MandatoryCategory] = set()
        executed_ids: list[str] = []

        for t in selected_or_executed:
            hit_tags.update(t.coverage_tags)
            hit_mandatory.update(t.mandatory_categories)
            executed_ids.append(t.id)

        uncovered = sorted(pool_tags - hit_tags)
        covered = sorted(hit_tags & pool_tags)

        axes: dict[str, float] = {}
        by_axis: dict[str, set[str]] = defaultdict(set)
        for tag in pool_tags:
            axis = tag.split(":", 1)[0] if ":" in tag else "other"
            by_axis[axis].add(tag)

        for axis, tags in by_axis.items():
            if not tags:
                continue
            hit_count = len(tags & hit_tags)
            axes[axis] = round(hit_count / len(tags), 4)

        critical: list[str] = []
        if applicable_mandatory:
            for m in applicable_mandatory:
                if m not in hit_mandatory:
                    critical.append(f"mandatory:{m.value}")

        for tag in uncovered:
            if tag.startswith("security:"):
                critical.append(tag)

        return CoverageReport(
            axes=axes,
            covered_tags=covered,
            uncovered_tags=uncovered,
            critical_uncovered=sorted(set(critical)),
            executed_test_ids=executed_ids,
            metadata={
                "pool_tag_count": len(pool_tags),
                "hit_tag_count": len(covered),
            },
        )

    def report_from_config(
        self,
        pool: list[CandidateTest],
        pack_tests: list[CandidateTest],
        config: OptimizerConfig,
    ) -> CoverageReport:
        """Coverage report using optimizer mandatory applicability."""
        return self.report(pool, pack_tests, config.applicable_mandatory)
