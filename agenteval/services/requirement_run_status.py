"""FR-B-17 / FR-B-23 rollups from SQLite criterion verdicts."""

import sqlite3

from pydantic import BaseModel, ConfigDict, Field

_STATUS_ORDER = {"failing": 0, "unverifiable": 1, "untested": 2, "proven": 3}


class RequirementRunStatusRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stable_id: str
    statement: str
    status: str
    source_kind: str


class ComplianceControlRunRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    control_key: str
    title: str
    status: str
    requirement_stable_ids: list[str] = Field(default_factory=list)


class AssuranceSignoffContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirements: list[RequirementRunStatusRow] = Field(default_factory=list)
    controls: list[ComplianceControlRunRow] = Field(default_factory=list)


def _worst_status(statuses: list[str]) -> str:
    if not statuses:
        return "untested"
    return min(statuses, key=lambda s: _STATUS_ORDER.get(s, 99))


def _criterion_status(verdict: str | None) -> str:
    if verdict is None:
        return "untested"
    if verdict == "PASS":
        return "proven"
    if verdict == "FAIL":
        return "failing"
    return "unverifiable"


def build_assurance_signoff_context(
    conn: sqlite3.Connection,
    suite_version_id: str,
    run_id: str,
) -> AssuranceSignoffContext | None:
    req_rows = conn.execute(
        """
        SELECT id, stable_id, statement, source_kind
        FROM requirements
        WHERE suite_version_id = ?
        ORDER BY stable_id
        """,
        (suite_version_id,),
    ).fetchall()
    if not req_rows:
        return None

    verdict_by_criterion: dict[str, str] = {}
    for row in conn.execute(
        """
        SELECT cv.criterion_id, cv.verdict
        FROM criterion_verdicts cv
        JOIN case_executions ce ON ce.id = cv.case_execution_id
        WHERE ce.run_id = ?
        """,
        (run_id,),
    ).fetchall():
        cid = str(row["criterion_id"])
        verdict_by_criterion[cid] = str(row["verdict"])

    requirement_rows: list[RequirementRunStatusRow] = []
    for req in req_rows:
        req_id = str(req["id"])
        crit_ids = [
            str(r["id"])
            for r in conn.execute(
                "SELECT id FROM acceptance_criteria WHERE requirement_id = ?",
                (req_id,),
            ).fetchall()
        ]
        statuses = [
            _criterion_status(verdict_by_criterion.get(cid)) for cid in crit_ids
        ]
        requirement_rows.append(
            RequirementRunStatusRow(
                stable_id=str(req["stable_id"]),
                statement=str(req["statement"]),
                status=_worst_status(statuses),
                source_kind=str(req["source_kind"]),
            )
        )

    control_rows: list[ComplianceControlRunRow] = []
    pack_ids = [
        str(r["pack_id"])
        for r in conn.execute(
            "SELECT pack_id FROM suite_pack_selections WHERE suite_version_id = ?",
            (suite_version_id,),
        ).fetchall()
    ]
    if pack_ids:
        placeholders = ",".join("?" * len(pack_ids))
        controls = conn.execute(
            f"""
            SELECT id, control_key, title
            FROM compliance_controls
            WHERE pack_id IN ({placeholders})
            ORDER BY control_key
            """,
            pack_ids,
        ).fetchall()
        for ctrl in controls:
            control_id = str(ctrl["id"])
            crit_ids = [
                str(r["criterion_id"])
                for r in conn.execute(
                    "SELECT criterion_id FROM criterion_compliance_map WHERE control_id = ?",
                    (control_id,),
                ).fetchall()
            ]
            statuses = [
                _criterion_status(verdict_by_criterion.get(cid)) for cid in crit_ids
            ]
            req_stables = [
                str(r["stable_id"])
                for r in conn.execute(
                    """
                    SELECT r.stable_id
                    FROM requirements r
                    JOIN acceptance_criteria ac ON ac.requirement_id = r.id
                    JOIN criterion_compliance_map m ON m.criterion_id = ac.id
                    WHERE m.control_id = ?
                    """,
                    (control_id,),
                ).fetchall()
            ]
            control_rows.append(
                ComplianceControlRunRow(
                    control_key=str(ctrl["control_key"]),
                    title=str(ctrl["title"]),
                    status=_worst_status(statuses),
                    requirement_stable_ids=req_stables,
                )
            )

    return AssuranceSignoffContext(requirements=requirement_rows, controls=control_rows)
