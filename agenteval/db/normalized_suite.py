"""Persist requirements, criteria, and test cases at suite freeze (SQLite v2)."""

import hashlib
import json
import sqlite3
from agenteval.core.manifest import AgentCapability, AgentCard
from agenteval.domain.models import (
    AcceptanceCriterionRecord,
    FrozenTestCaseRecord,
    RequirementRecord,
)
from agenteval.packs.audit_evidence import build_audit_evidence_payload, should_capture_audit_evidence
from agenteval.packs.enabled import enabled_domain_pack_ids
from agenteval.packs.scoring import score_criterion
from agenteval.packs.freeze_metadata import (
    persist_criterion_compliance_maps,
    persist_pack_freeze_metadata,
    resolve_enabled_pack_ids,
)
from agenteval.packs.protocol import RequirementDraft
from agenteval.packs.registry import load_domain_pack
from agenteval.planning.models import (
    AcceptanceCriterionSummary,
    CandidateTest,
    CriterionVerdictSummary,
    RequirementSummary,
    SuiteRequirementsResult,
    SuiteRunReport,
    TestCaseResult,
    TestPack,
)

DEFAULT_CRITERION_STABLE_ID = "observable-response"
EVIDENCE_KIND_HTTP = "http_observation"
CHECK_KIND_BLACKBOX = "blackbox_observable"


def v2_suite_tables_present(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'requirements'"
    ).fetchone()
    return row is not None


def v2_run_verdict_tables_present(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'criterion_verdicts'"
    ).fetchone()
    return row is not None


def _content_sha256(payload_json: str) -> str:
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def _delete_normalized_children(conn: sqlite3.Connection, suite_version_id: str) -> None:
    test_ids = [
        str(r[0])
        for r in conn.execute(
            "SELECT id FROM test_cases WHERE suite_version_id = ?",
            (suite_version_id,),
        ).fetchall()
    ]
    if test_ids:
        placeholders = ",".join("?" * len(test_ids))
        conn.execute(
            f"DELETE FROM test_case_criteria WHERE test_case_id IN ({placeholders})",
            test_ids,
        )
    conn.execute("DELETE FROM test_cases WHERE suite_version_id = ?", (suite_version_id,))
    req_ids = [
        str(r[0])
        for r in conn.execute(
            "SELECT id FROM requirements WHERE suite_version_id = ?",
            (suite_version_id,),
        ).fetchall()
    ]
    if req_ids:
        placeholders = ",".join("?" * len(req_ids))
        conn.execute(
            f"DELETE FROM acceptance_criteria WHERE requirement_id IN ({placeholders})",
            req_ids,
        )
    conn.execute("DELETE FROM requirements WHERE suite_version_id = ?", (suite_version_id,))
    conn.execute(
        "DELETE FROM suite_pack_selections WHERE suite_version_id = ?",
        (suite_version_id,),
    )


def build_requirements_and_criteria(
    suite_version_id: str,
    capabilities: list[AgentCapability],
) -> tuple[list[RequirementRecord], list[AcceptanceCriterionRecord], dict[str, str]]:
    """Return records and map stable requirement id → criterion row id."""
    requirements: list[RequirementRecord] = []
    criteria: list[AcceptanceCriterionRecord] = []
    cap_to_criterion: dict[str, str] = {}

    for cap in capabilities:
        stable = cap.requirement_id()
        req_id = f"{suite_version_id}:req:{stable}"
        requirements.append(
            RequirementRecord(
                id=req_id,
                suite_version_id=suite_version_id,
                stable_id=stable,
                statement=cap.description,
                source_kind="spec",
                review_status="approved",
            )
        )
        crit_id = f"{req_id}:crit:{DEFAULT_CRITERION_STABLE_ID}"
        criteria.append(
            AcceptanceCriterionRecord(
                id=crit_id,
                requirement_id=req_id,
                stable_id=DEFAULT_CRITERION_STABLE_ID,
                description=f"Observable HTTP behavior satisfies: {cap.description}",
                evidence_kind=EVIDENCE_KIND_HTTP,
                check_kind=CHECK_KIND_BLACKBOX,
                source_kind="extracted",
            )
        )
        cap_to_criterion[stable] = crit_id

    return requirements, criteria, cap_to_criterion


def collect_synthetic_test_data(pack_ids: list[str] | None) -> dict[str, object]:
    if not pack_ids:
        return {}
    merged: dict[str, object] = {}
    for pack_id in pack_ids:
        pack = load_domain_pack(pack_id)
        if pack is None:
            continue
        options = pack.contribute_options()
        chunk = pack.synthetic_test_data(options)
        if chunk:
            merged.update(chunk)
    return merged


def collect_pack_requirement_drafts(
    pack_ids: list[str] | None = None,
) -> list[RequirementDraft]:
    """Merge mandatory requirements from enabled domain packs."""
    ids = pack_ids if pack_ids is not None else enabled_domain_pack_ids()
    drafts: list[RequirementDraft] = []
    seen: set[str] = set()
    for pack_id in ids:
        pack = load_domain_pack(pack_id)
        if pack is None:
            continue
        options = pack.contribute_options()
        for draft in pack.mandatory_requirements(options):
            if draft.stable_id in seen:
                continue
            seen.add(draft.stable_id)
            drafts.append(draft)
    return drafts


def append_pack_requirements_and_criteria(
    suite_version_id: str,
    drafts: list[RequirementDraft],
    *,
    requirements: list[RequirementRecord],
    criteria: list[AcceptanceCriterionRecord],
) -> None:
    """Extend in-memory requirement/criterion lists with pack-sourced rows."""
    for draft in drafts:
        req_id = f"{suite_version_id}:req:{draft.stable_id}"
        requirements.append(
            RequirementRecord(
                id=req_id,
                suite_version_id=suite_version_id,
                stable_id=draft.stable_id,
                statement=draft.statement,
                source_kind="pack",
                source_pack_name=draft.pack_name,
                review_status="approved",
            )
        )
        crit_id = f"{req_id}:crit:{draft.criterion_stable_id}"
        criteria.append(
            AcceptanceCriterionRecord(
                id=crit_id,
                requirement_id=req_id,
                stable_id=draft.criterion_stable_id,
                description=f"Pack criterion: {draft.statement}",
                evidence_kind=draft.evidence_kind,
                check_kind=draft.check_kind,
                source_kind="pack",
                source_pack_name=draft.pack_name,
            )
        )


def build_frozen_test_cases(
    suite_version_id: str,
    tests: list[CandidateTest],
    cap_to_criterion: dict[str, str],
    *,
    pack_ids: list[str] | None = None,
    extra_criterion_ids: list[str] | None = None,
) -> list[FrozenTestCaseRecord]:
    synthetic = collect_synthetic_test_data(pack_ids)
    records: list[FrozenTestCaseRecord] = []
    for test in tests:
        test_row_id = f"{suite_version_id}:tc:{test.id}"
        persona = json.dumps({"persona_id": test.persona_id})
        inputs = json.dumps(
            {
                "user_prompt": test.user_prompt,
                "expected_behavior": test.expected_behavior,
            }
        )
        test_data_obj: dict[str, object] = {
            "user_prompt": test.user_prompt,
            "expected_behavior": test.expected_behavior,
            "frozen": True,
        }
        if synthetic:
            test_data_obj.update(synthetic)
        test_data = json.dumps(test_data_obj)
        crit_id = cap_to_criterion.get(test.capability_id)
        criterion_ids = [crit_id] if crit_id else []
        if extra_criterion_ids:
            criterion_ids = list(dict.fromkeys([*criterion_ids, *extra_criterion_ids]))
        records.append(
            FrozenTestCaseRecord(
                id=test_row_id,
                suite_version_id=suite_version_id,
                stable_id=test.id,
                title=test.name,
                persona_json=persona,
                inputs_json=inputs,
                test_data_json=test_data,
                criterion_ids=criterion_ids,
            )
        )
    return records


def capabilities_from_pack_tests(tests: list[CandidateTest]) -> list[AgentCapability]:
    """Fallback when AgentCard JSON was not stored."""
    by_cap: dict[str, AgentCapability] = {}
    for test in tests:
        if test.capability_id in by_cap:
            continue
        label = test.name.split(":", 1)[0].strip() or test.capability_id
        cap = AgentCapability(name=label, description=label, stable_id=test.capability_id)
        by_cap[test.capability_id] = cap
    return list(by_cap.values())


def parse_agent_card(agent_card_json: str | None, pack: TestPack) -> list[AgentCapability]:
    if agent_card_json:
        card = AgentCard.model_validate_json(agent_card_json)
        if card.capabilities:
            return card.capabilities
    return capabilities_from_pack_tests(pack.tests)


def persist_normalized_suite(
    conn: sqlite3.Connection,
    suite_version_id: str,
    pack: TestPack,
    *,
    agent_card_json: str | None = None,
) -> None:
    """Write requirements, acceptance criteria, test cases, and links for one freeze."""
    if not v2_suite_tables_present(conn):
        return

    capabilities = parse_agent_card(agent_card_json, pack)
    if not capabilities and not pack.tests:
        return

    _delete_normalized_children(conn, suite_version_id)

    requirements, criteria, cap_to_criterion = build_requirements_and_criteria(
        suite_version_id, capabilities
    )
    enabled_ids = resolve_enabled_pack_ids()
    pack_name_to_id = persist_pack_freeze_metadata(conn, suite_version_id, enabled_ids)

    pack_drafts = collect_pack_requirement_drafts(enabled_ids)
    append_pack_requirements_and_criteria(
        suite_version_id,
        pack_drafts,
        requirements=requirements,
        criteria=criteria,
    )
    pack_criterion_ids = [c.id for c in criteria if c.source_kind == "pack"]
    test_cases = build_frozen_test_cases(
        suite_version_id,
        pack.tests,
        cap_to_criterion,
        pack_ids=enabled_ids,
        extra_criterion_ids=pack_criterion_ids,
    )

    for req in requirements:
        source_pack_id = (
            pack_name_to_id.get(req.source_pack_name)
            if req.source_kind == "pack" and req.source_pack_name
            else None
        )
        conn.execute(
            """
            INSERT INTO requirements (
                id, suite_version_id, stable_id, statement,
                source_kind, source_pack_id, review_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                req.id,
                req.suite_version_id,
                req.stable_id,
                req.statement,
                req.source_kind,
                source_pack_id,
                req.review_status,
            ),
        )

    for crit in criteria:
        source_pack_id = (
            pack_name_to_id.get(crit.source_pack_name)
            if crit.source_kind == "pack" and crit.source_pack_name
            else None
        )
        conn.execute(
            """
            INSERT INTO acceptance_criteria (
                id, requirement_id, stable_id, description,
                evidence_kind, check_kind, source_kind, source_pack_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                crit.id,
                crit.requirement_id,
                crit.stable_id,
                crit.description,
                crit.evidence_kind,
                crit.check_kind,
                crit.source_kind,
                source_pack_id,
            ),
        )

    persist_criterion_compliance_maps(conn, enabled_ids, requirements, criteria)

    for tc in test_cases:
        conn.execute(
            """
            INSERT INTO test_cases (
                id, suite_version_id, stable_id, title,
                persona_json, inputs_json, test_data_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tc.id,
                tc.suite_version_id,
                tc.stable_id,
                tc.title,
                tc.persona_json,
                tc.inputs_json,
                tc.test_data_json,
            ),
        )
        for criterion_id in tc.criterion_ids:
            conn.execute(
                """
                INSERT INTO test_case_criteria (test_case_id, criterion_id)
                VALUES (?, ?)
                """,
                (tc.id, criterion_id),
            )


def load_requirements_for_suite(
    conn: sqlite3.Connection, suite_version_id: str
) -> list[RequirementRecord]:
    rows = conn.execute(
        """
        SELECT id, suite_version_id, stable_id, statement, source_kind, review_status
        FROM requirements
        WHERE suite_version_id = ?
        ORDER BY stable_id
        """,
        (suite_version_id,),
    ).fetchall()
    return [
        RequirementRecord(
            id=str(r["id"]),
            suite_version_id=str(r["suite_version_id"]),
            stable_id=str(r["stable_id"]),
            statement=str(r["statement"]),
            source_kind=str(r["source_kind"]),
            review_status=str(r["review_status"]),
        )
        for r in rows
    ]


def load_test_cases_for_suite(
    conn: sqlite3.Connection, suite_version_id: str
) -> list[FrozenTestCaseRecord]:
    rows = conn.execute(
        """
        SELECT id, suite_version_id, stable_id, title,
               persona_json, inputs_json, test_data_json
        FROM test_cases
        WHERE suite_version_id = ?
        ORDER BY stable_id
        """,
        (suite_version_id,),
    ).fetchall()
    records: list[FrozenTestCaseRecord] = []
    for r in rows:
        tc_id = str(r["id"])
        crit_rows = conn.execute(
            "SELECT criterion_id FROM test_case_criteria WHERE test_case_id = ?",
            (tc_id,),
        ).fetchall()
        records.append(
            FrozenTestCaseRecord(
                id=tc_id,
                suite_version_id=str(r["suite_version_id"]),
                stable_id=str(r["stable_id"]),
                title=str(r["title"]),
                persona_json=str(r["persona_json"]),
                inputs_json=str(r["inputs_json"]),
                test_data_json=str(r["test_data_json"]),
                criterion_ids=[str(c["criterion_id"]) for c in crit_rows],
            )
        )
    return records


def _delete_run_normalized(conn: sqlite3.Connection, run_id: str) -> None:
    conn.execute("DELETE FROM case_executions WHERE run_id = ?", (run_id,))


def persist_run_evidence_and_verdicts(
    conn: sqlite3.Connection,
    run_id: str,
    suite_version_id: str,
    results: list[TestCaseResult],
    *,
    captured_at: str,
) -> None:
    """
    Write case_executions, evidence_items, and criterion_verdicts for a run.

    Writes HTTP observation evidence for every case; optional audit_log evidence when
    ``AGENTEVAL_AUDIT_LOG_DB_PATH`` is set and domain packs are enabled. Pack check kinds
    are scored via ``agenteval.pack_checks``; blackbox criteria mirror the test verdict.
    """
    if not v2_run_verdict_tables_present(conn):
        return

    _delete_run_normalized(conn, run_id)

    for result in results:
        tc_row = conn.execute(
            """
            SELECT id, test_data_json FROM test_cases
            WHERE suite_version_id = ? AND stable_id = ?
            """,
            (suite_version_id, result.test_id),
        ).fetchone()
        if tc_row is None:
            continue

        test_case_row_id = str(tc_row["id"])
        case_execution_id = f"{run_id}:ce:{result.test_id}"

        conn.execute(
            """
            INSERT INTO case_executions (
                id, run_id, test_case_id, verdict_rollup,
                rationale, observation_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                case_execution_id,
                run_id,
                test_case_row_id,
                result.verdict,
                result.rationale,
                result.observation.model_dump_json(),
            ),
        )

        payload_json = result.observation.model_dump_json()
        evidence_id = f"{case_execution_id}:ev:http"
        conn.execute(
            """
            INSERT INTO evidence_items (
                id, case_execution_id, connector_id, kind,
                payload_json, content_sha256, captured_at
            ) VALUES (?, ?, NULL, 'http_observation', ?, ?, ?)
            """,
            (
                evidence_id,
                case_execution_id,
                payload_json,
                _content_sha256(payload_json),
                captured_at,
            ),
        )

        evidence_for_scoring: list[dict[str, str]] = [
            {
                "id": evidence_id,
                "kind": "http_observation",
                "payload_json": payload_json,
            }
        ]

        if should_capture_audit_evidence():
            test_data = json.loads(str(tc_row["test_data_json"] or "{}"))
            audit_payload = build_audit_evidence_payload(test_data)
            if audit_payload is not None:
                audit_evidence_id = f"{case_execution_id}:ev:audit"
                conn.execute(
                    """
                    INSERT INTO evidence_items (
                        id, case_execution_id, connector_id, kind,
                        payload_json, content_sha256, captured_at
                    ) VALUES (?, ?, NULL, 'audit_log', ?, ?, ?)
                    """,
                    (
                        audit_evidence_id,
                        case_execution_id,
                        audit_payload,
                        _content_sha256(audit_payload),
                        captured_at,
                    ),
                )
                evidence_for_scoring.append(
                    {
                        "id": audit_evidence_id,
                        "kind": "audit_log",
                        "payload_json": audit_payload,
                    }
                )

        crit_rows = conn.execute(
            """
            SELECT criterion_id FROM test_case_criteria
            WHERE test_case_id = ?
            """,
            (test_case_row_id,),
        ).fetchall()

        for crit_row in crit_rows:
            criterion_id = str(crit_row["criterion_id"])
            crit_meta = conn.execute(
                """
                SELECT stable_id, description, check_kind
                FROM acceptance_criteria
                WHERE id = ?
                """,
                (criterion_id,),
            ).fetchone()
            if crit_meta is None:
                continue

            scored = score_criterion(
                check_kind=str(crit_meta["check_kind"]),
                test_verdict=result.verdict,
                test_rationale=result.rationale,
                criterion_stable_id=str(crit_meta["stable_id"]),
                criterion_description=str(crit_meta["description"]),
                evidence_items=evidence_for_scoring,
            )
            verdict_id = f"{case_execution_id}:cv:{criterion_id}"
            conn.execute(
                """
                INSERT INTO criterion_verdicts (
                    id, case_execution_id, criterion_id, verdict,
                    verdict_tier, rationale
                ) VALUES (?, ?, ?, ?, 'deterministic', ?)
                """,
                (
                    verdict_id,
                    case_execution_id,
                    criterion_id,
                    scored.verdict,
                    scored.rationale,
                ),
            )
            for ev_id in scored.evidence_item_ids:
                conn.execute(
                    """
                    INSERT INTO criterion_verdict_evidence (verdict_id, evidence_item_id)
                    VALUES (?, ?)
                    """,
                    (verdict_id, ev_id),
                )


def load_suite_requirements_result(
    conn: sqlite3.Connection,
    agent_id: str,
    suite_version_id: str,
    suite_version: int,
) -> SuiteRequirementsResult | None:
    if not v2_suite_tables_present(conn):
        return None
    req_rows = conn.execute(
        """
        SELECT id, stable_id, statement, source_kind, review_status
        FROM requirements
        WHERE suite_version_id = ?
        ORDER BY stable_id
        """,
        (suite_version_id,),
    ).fetchall()
    if not req_rows:
        return None

    summaries: list[RequirementSummary] = []
    for req in req_rows:
        req_id = str(req["id"])
        crit_rows = conn.execute(
            """
            SELECT id, stable_id, description, evidence_kind, check_kind
            FROM acceptance_criteria
            WHERE requirement_id = ?
            ORDER BY stable_id
            """,
            (req_id,),
        ).fetchall()
        summaries.append(
            RequirementSummary(
                stable_id=str(req["stable_id"]),
                statement=str(req["statement"]),
                source_kind=str(req["source_kind"]),
                review_status=str(req["review_status"]),
                criteria=[
                    AcceptanceCriterionSummary(
                        id=str(c["id"]),
                        stable_id=str(c["stable_id"]),
                        description=str(c["description"]),
                        evidence_kind=str(c["evidence_kind"]),
                        check_kind=str(c["check_kind"]),
                    )
                    for c in crit_rows
                ],
            )
        )
    return SuiteRequirementsResult(
        agent_id=agent_id,
        suite_version=suite_version,
        requirements=summaries,
    )


def load_criterion_verdict_summaries(
    conn: sqlite3.Connection, run_id: str
) -> list[CriterionVerdictSummary]:
    if not v2_run_verdict_tables_present(conn):
        return []
    rows = conn.execute(
        """
        SELECT cv.id AS verdict_id, cv.criterion_id, cv.verdict, cv.verdict_tier,
               cv.rationale, ac.stable_id AS criterion_stable_id,
               r.stable_id AS requirement_stable_id, tc.stable_id AS test_id
        FROM criterion_verdicts cv
        JOIN case_executions ce ON ce.id = cv.case_execution_id
        JOIN acceptance_criteria ac ON ac.id = cv.criterion_id
        JOIN requirements r ON r.id = ac.requirement_id
        JOIN test_cases tc ON tc.id = ce.test_case_id
        WHERE ce.run_id = ?
        ORDER BY r.stable_id, tc.stable_id
        """,
        (run_id,),
    ).fetchall()
    summaries: list[CriterionVerdictSummary] = []
    for row in rows:
        verdict_id = str(row["verdict_id"])
        evidence_ids = [
            str(er["evidence_item_id"])
            for er in conn.execute(
                """
                SELECT evidence_item_id FROM criterion_verdict_evidence
                WHERE verdict_id = ?
                """,
                (verdict_id,),
            ).fetchall()
        ]
        summaries.append(
            CriterionVerdictSummary(
                criterion_id=str(row["criterion_id"]),
                requirement_stable_id=str(row["requirement_stable_id"]),
                criterion_stable_id=str(row["criterion_stable_id"]),
                test_id=str(row["test_id"]),
                verdict=str(row["verdict"]),
                verdict_tier=str(row["verdict_tier"]),
                rationale=str(row["rationale"] or ""),
                evidence_item_ids=evidence_ids,
            )
        )
    return summaries


def enrich_run_report(conn: sqlite3.Connection, report: SuiteRunReport) -> SuiteRunReport:
    verdicts = load_criterion_verdict_summaries(conn, report.run_id)
    if not verdicts:
        return report
    return report.model_copy(update={"criterion_verdicts": verdicts})


def count_criterion_verdicts_for_run(conn: sqlite3.Connection, run_id: str) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS n
        FROM criterion_verdicts cv
        JOIN case_executions ce ON ce.id = cv.case_execution_id
        WHERE ce.run_id = ?
        """,
        (run_id,),
    ).fetchone()
    return int(row["n"]) if row is not None else 0
