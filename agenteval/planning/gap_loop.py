"""B5 (full): gap-driven incremental pack extension (DR-010, AP-003)."""

from datetime import UTC, datetime

from agenteval.planning.coverage import CoverageMapper
from agenteval.planning.models import (
    CandidateTest,
    CoverageReport,
    MandatoryCategory,
    SuiteGapChangelog,
    SuiteGapLoopResult,
    SuiteManifest,
    TestPack,
)


def _candidate_hits_target(candidate: CandidateTest, target: str) -> bool:
    if target in candidate.coverage_tags:
        return True
    if target.startswith("mandatory:"):
        key = target.split(":", 1)[1]
        try:
            category = MandatoryCategory(key)
        except ValueError:
            return False
        return category in candidate.mandatory_categories
    return False


def _uncovered_targets(coverage: CoverageReport) -> set[str]:
    targets = set(coverage.uncovered_tags)
    targets.update(coverage.critical_uncovered)
    return targets


def _score_candidate(candidate: CandidateTest, targets: set[str]) -> int:
    return sum(1 for tag in targets if _candidate_hits_target(candidate, tag))


class SuiteGapExtender:
    """Append pool tests that close coverage gaps from the last executed pack."""

    def extend(
        self,
        *,
        agent_id: str,
        manifest: SuiteManifest,
        pool: list[CandidateTest],
        pack: TestPack,
        executed_tests: list[CandidateTest],
        triggered_by_run_id: str | None,
        max_pack_tests: int,
        max_add: int = 5,
    ) -> tuple[SuiteGapLoopResult, SuiteGapChangelog | None, TestPack | None]:
        mapper = CoverageMapper()
        coverage_before = mapper.report(pool, executed_tests)
        targets = _uncovered_targets(coverage_before)

        if not targets:
            after = mapper.report(pool, pack.tests)
            return (
                SuiteGapLoopResult(
                    agent_id=agent_id,
                    previous_version=manifest.version,
                    new_version=manifest.version,
                    triggered_by_run_id=triggered_by_run_id,
                    pack_size=len(pack.tests),
                    pool_size=len(pool),
                    coverage_before=coverage_before,
                    coverage_after=after,
                    noop=True,
                ),
                None,
                None,
            )

        selected_ids = {t.id for t in pack.tests}
        available = [c for c in pool if c.id not in selected_ids]
        added: list[CandidateTest] = []
        new_tests = list(pack.tests)

        while (
            len(added) < max_add
            and len(new_tests) < max_pack_tests
            and targets
            and available
        ):
            best: CandidateTest | None = None
            best_score = 0
            for candidate in available:
                score = _score_candidate(candidate, targets)
                if score > best_score:
                    best_score = score
                    best = candidate
            if best is None or best_score == 0:
                break
            new_tests.append(best)
            added.append(best)
            selected_ids.add(best.id)
            available = [c for c in available if c.id != best.id]
            targets = {
                tag
                for tag in targets
                if not _candidate_hits_target(best, tag)
            }

        if not added:
            after = mapper.report(pool, pack.tests)
            return (
                SuiteGapLoopResult(
                    agent_id=agent_id,
                    previous_version=manifest.version,
                    new_version=manifest.version,
                    triggered_by_run_id=triggered_by_run_id,
                    targeted_tags=sorted(_uncovered_targets(coverage_before)),
                    remaining_gaps=sorted(targets),
                    pack_size=len(pack.tests),
                    pool_size=len(pool),
                    coverage_before=coverage_before,
                    coverage_after=after,
                    noop=True,
                ),
                None,
                None,
            )

        new_version = manifest.version + 1
        new_pack = TestPack(
            agent_id=agent_id,
            version=new_version,
            tests=new_tests,
            candidate_count=len(pool),
            requirements_fingerprint=pack.requirements_fingerprint,
        )
        coverage_after = mapper.report(pool, new_tests)
        remaining = sorted(_uncovered_targets(coverage_after))

        result = SuiteGapLoopResult(
            agent_id=agent_id,
            previous_version=manifest.version,
            new_version=new_version,
            triggered_by_run_id=triggered_by_run_id,
            targeted_tags=sorted(_uncovered_targets(coverage_before)),
            added_test_ids=[t.id for t in added],
            remaining_gaps=remaining,
            pack_size=len(new_tests),
            pool_size=len(pool),
            coverage_before=coverage_before,
            coverage_after=coverage_after,
        )
        changelog = SuiteGapChangelog(
            suite_version=new_version,
            timestamp=datetime.now(UTC).isoformat(),
            triggered_by_run_id=triggered_by_run_id,
            targeted_tags=result.targeted_tags,
            added_test_ids=result.added_test_ids,
        )
        return result, changelog, new_pack
