"""Persist pack rows and compliance mappings at suite freeze (FR-P-05)."""

import json
import sqlite3
from datetime import UTC, datetime

from agenteval.domain.models import AcceptanceCriterionRecord, RequirementRecord
from agenteval.packs.protocol import PackManifest
from agenteval.packs.registry import load_domain_pack


def pack_row_id(manifest: PackManifest) -> str:
    return f"{manifest.name}:{manifest.version}"


def control_row_id(pack_id: str, control_key: str) -> str:
    return f"{pack_id}:ctrl:{control_key}"


def persist_pack_freeze_metadata(
    conn: sqlite3.Connection,
    suite_version_id: str,
    pack_ids: list[str],
) -> dict[str, str]:
    """Upsert packs, suite_pack_selections, compliance_controls. Returns pack name → row id."""
    name_to_id: dict[str, str] = {}
    now = datetime.now(UTC).isoformat()

    for pack_id in pack_ids:
        pack = load_domain_pack(pack_id)
        if pack is None:
            continue
        manifest = pack.manifest
        row_id = pack_row_id(manifest)
        name_to_id[manifest.name] = row_id

        conn.execute(
            """
            INSERT INTO packs (id, name, version, manifest_json, installed_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                manifest_json = excluded.manifest_json,
                installed_at = excluded.installed_at
            """,
            (
                row_id,
                manifest.name,
                manifest.version,
                manifest.model_dump_json(),
                now,
            ),
        )

        options = pack.contribute_options()
        conn.execute(
            """
            INSERT INTO suite_pack_selections (suite_version_id, pack_id, options_json)
            VALUES (?, ?, ?)
            ON CONFLICT(suite_version_id, pack_id) DO UPDATE SET
                options_json = excluded.options_json
            """,
            (suite_version_id, row_id, json.dumps(options)),
        )

        for ctrl in pack.compliance_controls():
            conn.execute(
                """
                INSERT INTO compliance_controls (id, pack_id, control_key, title, framework)
                VALUES (?, ?, ?, ?, '')
                ON CONFLICT(pack_id, control_key) DO UPDATE SET
                    title = excluded.title
                """,
                (
                    control_row_id(row_id, ctrl.control_key),
                    row_id,
                    ctrl.control_key,
                    ctrl.title,
                ),
            )

    return name_to_id


def persist_criterion_compliance_maps(
    conn: sqlite3.Connection,
    pack_ids: list[str],
    requirements: list[RequirementRecord],
    criteria: list[AcceptanceCriterionRecord],
) -> None:
    """Link frozen criteria to compliance control rows declared by packs."""
    req_stable_to_crit: dict[str, str] = {}
    for crit in criteria:
        req = next((r for r in requirements if r.id == crit.requirement_id), None)
        if req is None:
            continue
        req_stable_to_crit[req.stable_id] = crit.id

    for pack_id in pack_ids:
        pack = load_domain_pack(pack_id)
        if pack is None:
            continue
        row_id = pack_row_id(pack.manifest)
        for ctrl in pack.compliance_controls():
            control_id = control_row_id(row_id, ctrl.control_key)
            for req_stable in ctrl.requirement_stable_ids:
                criterion_id = req_stable_to_crit.get(req_stable)
                if criterion_id is None:
                    continue
                conn.execute(
                    """
                    INSERT OR IGNORE INTO criterion_compliance_map (criterion_id, control_id)
                    VALUES (?, ?)
                    """,
                    (criterion_id, control_id),
                )
