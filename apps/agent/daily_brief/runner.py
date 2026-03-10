from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from apps.agent.delivery.html_report import render_daily_brief_html
from apps.agent.ingest.dedup import classify_duplicate
from apps.agent.ingest.extract import extract_payload
from apps.agent.ingest.fetch import plan_fetch_items
from apps.agent.ingest.live_fetch import fetch_live_payloads_for_source
from apps.agent.ingest.normalize import build_document_record
from apps.agent.orchestrator import run_pipeline
from apps.agent.pipeline.stage10_decision_record import build_and_persist_decision_record
from apps.agent.pipeline.stage8_validation import run_stage8_citation_validation
from apps.agent.pipeline.types import (
    DAILY_BRIEF_OUTPUT_SECTIONS,
    BulletCitationRow,
    CitationValidationResult,
    DailyBriefSectionBulletRow,
    DailyBriefSynthesis,
    DailyBriefCorpusStageData,
    DailyBriefInputStageData,
    DailyBriefSynthesisStageData,
    EvidencePackItem,
    FtsRow,
    RuntimeChunkRow,
    RuntimeDocumentRecord,
    RunStatus,
    SourceRegistryEntry,
    SourceRow,
    StageResult,
)
from apps.agent.retrieval.chunker import build_chunk_rows
from apps.agent.retrieval.evidence_pack import build_evidence_pack_report
from apps.agent.retrieval.fts_index import build_fts_rows
from apps.agent.runtime.budget_guard import BudgetCaps
from apps.agent.runtime.cost_ledger import BudgetWindowSnapshot
from apps.agent.runtime.source_scope import load_active_source_subset
from apps.agent.runtime.source_scope import load_source_registry
from apps.agent.synthesis.postprocess import finalize_validation_outcome
from apps.agent.daily_brief.synthesis import (
    SynthesisRetryPlan,
    build_changed_section,
    build_citation_store,
    build_synthesis,
)


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FIXTURE_PATH = ROOT / "artifacts" / "runtime" / "daily_brief_fixture_payloads.json"
MAX_VALIDATION_RETRIES = 1
MAX_VALIDATION_ATTEMPTS = MAX_VALIDATION_RETRIES + 1
STOPWORDS = {
    "a",
    "and",
    "as",
    "at",
    "for",
    "from",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
    "slower",
}


def load_active_fixture_payloads(*, fixture_path: Path | None = None) -> dict[str, list[dict[str, Any]]]:
    path = fixture_path or DEFAULT_FIXTURE_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    active_sources = load_active_source_subset()

    filtered: dict[str, list[dict[str, Any]]] = {}
    for source in active_sources:
        source_id = str(source["id"])
        source_payloads = payload.get(source_id, [])
        filtered[source_id] = [dict(item) for item in source_payloads]
    return filtered


def build_daily_brief_query(*, documents: Iterable[Mapping[str, Any]], max_terms: int = 4) -> str:
    counts: Counter[str] = Counter()
    for document in documents:
        text = " ".join(
            str(document.get(field, ""))
            for field in ("title", "rss_snippet", "body_text")
            if document.get(field)
        )
        counts.update(_tokenize(text))

    ranked_terms = [
        term
        for term, _count in counts.most_common()
        if term not in STOPWORDS and len(term) > 2
    ]
    return " ".join(ranked_terms[:max_terms])


def _tokenize(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.lower())


def run_fixture_daily_brief(
    *,
    base_dir: Path,
    fixture_path: Path | None = None,
    run_id: str = "run_daily_fixture",
    generated_at_utc: str | None = None,
    budget_preflight: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    lifecycle: list[dict[str, Any]] = []
    execution: dict[str, Any] = {}
    timestamp = generated_at_utc or _utc_now_iso()

    def stage(context: Any) -> StageResult:
        try:
            result = _execute_daily_brief_slice(
                base_dir=base_dir,
                fixture_path=fixture_path,
                run_id=run_id,
                generated_at_utc=timestamp,
                context=context,
            )
        except Exception as exc:
            execution["status"] = "failed"
            execution["error_summary"] = str(exc)
            return StageResult(status=RunStatus.FAILED, error_summary=str(exc))

        execution.update(result)
        if result["status"] == "ok":
            return StageResult(status=RunStatus.OK)
        return StageResult(
            status=RunStatus.PARTIAL,
            error_summary=result.get("abstain_reason") or result["status"],
        )

    pipeline_result = run_pipeline(
        run_id=run_id,
        run_type="daily_brief",
        stages=[stage],
        recorder=lifecycle.append,
        budget_preflight=budget_preflight or _default_budget_preflight(generated_at_utc=timestamp),
    )
    if pipeline_result["status"] == "stopped_budget" and not execution:
        execution.update(
            _persist_budget_stop_outputs(
                base_dir=base_dir,
                run_id=run_id,
                generated_at_utc=timestamp,
                pipeline_result=pipeline_result,
            )
        )
    execution.setdefault("status", pipeline_result["status"])
    execution["lifecycle"] = lifecycle
    execution["pipeline_status"] = pipeline_result["status"]
    execution["error_summary"] = pipeline_result.get("error_summary")
    return execution


def run_daily_brief(
    *,
    base_dir: Path,
    run_id: str = "run_daily_live",
    generated_at_utc: str | None = None,
    budget_preflight: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    lifecycle: list[dict[str, Any]] = []
    execution: dict[str, Any] = {}
    timestamp = generated_at_utc or _utc_now_iso()

    def stage(context: Any) -> StageResult:
        try:
            result = _execute_daily_brief_slice(
                base_dir=base_dir,
                fixture_path=None,
                run_id=run_id,
                generated_at_utc=timestamp,
                context=context,
                use_live_sources=True,
            )
        except Exception as exc:
            execution["status"] = "failed"
            execution["error_summary"] = str(exc)
            return StageResult(status=RunStatus.FAILED, error_summary=str(exc))

        execution.update(result)
        if result["status"] == "ok":
            return StageResult(status=RunStatus.OK)
        return StageResult(
            status=RunStatus.PARTIAL,
            error_summary=result.get("abstain_reason") or result["status"],
        )

    pipeline_result = run_pipeline(
        run_id=run_id,
        run_type="daily_brief",
        stages=[stage],
        recorder=lifecycle.append,
        budget_preflight=budget_preflight or _default_budget_preflight(generated_at_utc=timestamp),
    )
    if pipeline_result["status"] == "stopped_budget" and not execution:
        execution.update(
            _persist_budget_stop_outputs(
                base_dir=base_dir,
                run_id=run_id,
                generated_at_utc=timestamp,
                pipeline_result=pipeline_result,
            )
        )
    execution.setdefault("status", pipeline_result["status"])
    execution["lifecycle"] = lifecycle
    execution["pipeline_status"] = pipeline_result["status"]
    execution["error_summary"] = pipeline_result.get("error_summary")
    return execution


def _execute_daily_brief_slice(
    *,
    base_dir: Path,
    fixture_path: Path | None,
    run_id: str,
    generated_at_utc: str,
    context: Any,
    use_live_sources: bool = False,
) -> dict[str, Any]:
    report_date = generated_at_utc[:10]
    input_data = prepare_daily_brief_inputs(
        fixture_path=fixture_path,
        generated_at_utc=generated_at_utc,
        use_live_sources=use_live_sources,
    )
    corpus_data = build_daily_brief_corpus(
        stage_data=input_data,
        run_id=run_id,
        context=context,
    )
    synthesis_data = build_daily_brief_synthesis(
        stage_data=corpus_data,
        registry=input_data.registry,
        run_id=run_id,
        previous_synthesis=_load_previous_synthesis(base_dir=base_dir, report_date=report_date),
    )
    output_path = base_dir / "artifacts" / "daily" / report_date / "brief.html"
    budget_snapshot = _budget_snapshot(context=context)
    guardrail_checks = _guardrail_checks(
        stage8_result=synthesis_data.stage8_result,
        final_status=synthesis_data.final_result["status"],
        budget_snapshot=budget_snapshot,
        diversity_report=synthesis_data.evidence_pack_report,
    )
    render_daily_brief_html(
        output_path=output_path,
        report_date=report_date,
        run_id=run_id,
        synthesis=synthesis_data.final_result["synthesis"],
        citation_store=synthesis_data.stage8_result["citation_store"],
        guardrail_checks=guardrail_checks,
    )

    decision_record = build_and_persist_decision_record(
        base_dir=base_dir,
        run_id=run_id,
        run_type="daily_brief",
        stage8_status=synthesis_data.stage8_result["status"],
        synthesis=synthesis_data.final_result["synthesis"],
        removed_bullets=int(synthesis_data.stage8_result["report"]["removed_bullets"]),
        budget_snapshot=budget_snapshot,
        guardrail_checks=guardrail_checks,
        output_path=output_path,
        generated_at_utc=generated_at_utc,
    )

    artifact_dir = _artifact_dir(base_dir=base_dir, report_date=report_date, run_id=run_id)
    _write_json(artifact_dir / "sources.json", corpus_data.source_rows)
    _write_json(artifact_dir / "documents.json", corpus_data.documents)
    _write_json(artifact_dir / "chunks.json", corpus_data.chunks)
    _write_json(artifact_dir / "fts_rows.json", corpus_data.fts_rows)
    _write_json(artifact_dir / "evidence_pack_items.json", synthesis_data.evidence_pack_items)
    _write_json(artifact_dir / "citations.json", synthesis_data.citation_rows)
    _write_json(artifact_dir / "synthesis.json", synthesis_data.final_result["synthesis"])
    _write_json(artifact_dir / "synthesis_bullets.json", synthesis_data.synthesis_bullet_rows)
    _write_json(artifact_dir / "bullet_citations.json", synthesis_data.bullet_citation_rows)
    _write_json(
        artifact_dir / "run_summary.json",
        {
            "run_id": run_id,
            "report_date": report_date,
            "query_text": synthesis_data.query_text,
            "docs_fetched": context.counters.docs_fetched,
            "docs_ingested": context.counters.docs_ingested,
            "chunks_indexed": context.counters.chunks_indexed,
            "stage8_status": synthesis_data.stage8_result["status"],
            "final_status": synthesis_data.final_result["status"],
            "validation_attempts": synthesis_data.stage8_result["validation_attempts"],
            "max_validation_attempts": synthesis_data.stage8_result["max_validation_attempts"],
            "validation_retry_exhausted": synthesis_data.stage8_result["retry_exhausted"],
            "budget_snapshot": budget_snapshot,
            "budget_ledger_rows": list(context.budget_ledger_rows),
            "guardrail_checks": guardrail_checks,
            "diversity_stats": synthesis_data.evidence_pack_report["diversity_stats"],
        },
    )

    return {
        "status": synthesis_data.final_result["status"],
        "html_path": str(output_path),
        "decision_record_path": decision_record["record_path"],
        "artifact_dir": str(artifact_dir),
        "query_text": synthesis_data.query_text,
        "abstain_reason": synthesis_data.final_result.get("abstain_reason"),
    }


def prepare_daily_brief_inputs(
    *,
    fixture_path: Path | None = None,
    generated_at_utc: str,
    use_live_sources: bool = False,
) -> DailyBriefInputStageData:
    registry = load_source_registry()
    active_sources = load_active_source_subset(registry=registry)
    candidate_payloads = (
        load_active_live_payloads(active_sources=active_sources, fetched_at_utc=generated_at_utc)
        if use_live_sources
        else load_active_fixture_payloads(fixture_path=fixture_path)
    )
    planned_items = plan_fetch_items(sources=active_sources, candidate_payloads=candidate_payloads)
    if not planned_items:
        if use_live_sources:
            raise ValueError("No live payloads available for active sources")
        raise ValueError("No fixture payloads available for active sources")

    source_rows = [_build_source_row(source=source, generated_at_utc=generated_at_utc) for source in active_sources]
    return DailyBriefInputStageData(
        registry=registry,
        active_sources=active_sources,
        planned_items=planned_items,
        source_rows=source_rows,
    )


def load_active_live_payloads(
    *,
    active_sources: Iterable[SourceRegistryEntry],
    fetched_at_utc: str,
) -> dict[str, list[dict[str, Any]]]:
    payloads: dict[str, list[dict[str, Any]]] = {}
    for source in active_sources:
        source_id = str(source["id"])
        try:
            payloads[source_id] = fetch_live_payloads_for_source(
                source=source,
                fetched_at_utc=fetched_at_utc,
            )
        except Exception:
            # Keep the live slice usable when one active source is blocked or drifts.
            payloads[source_id] = []
    return payloads


def build_daily_brief_corpus(
    *,
    stage_data: DailyBriefInputStageData,
    run_id: str,
    context: Any,
) -> DailyBriefCorpusStageData:
    documents: list[RuntimeDocumentRecord] = []
    chunks: list[RuntimeChunkRow] = []
    fts_rows: list[FtsRow] = []

    for index, planned in enumerate(stage_data.planned_items, start=1):
        source_id = str(planned["source_id"])
        source = stage_data.registry[source_id]
        extracted = extract_payload(source=source, payload=planned["payload"])
        document = _build_runtime_document_record(
            source=source,
            extracted=extracted,
            doc_id=f"doc_{index:03d}",
            run_id=run_id,
        )

        duplicate = classify_duplicate(candidate=document, existing_documents=documents)
        if duplicate["is_duplicate"]:
            continue

        documents.append(document)
        doc_chunks = build_chunk_rows(document=document)
        chunks.extend(doc_chunks)
        for row in build_fts_rows(document=document, chunk_rows=doc_chunks):
            enriched = dict(row)
            enriched["credibility_tier"] = document["credibility_tier"]
            fts_rows.append(enriched)

    context.counters.docs_fetched = len(stage_data.planned_items)
    context.counters.docs_ingested = len(documents)
    context.counters.chunks_indexed = len(chunks)

    return DailyBriefCorpusStageData(
        source_rows=stage_data.source_rows,
        documents=documents,
        chunks=chunks,
        fts_rows=fts_rows,
    )


def build_daily_brief_synthesis(
    *,
    stage_data: DailyBriefCorpusStageData,
    registry: Mapping[str, SourceRegistryEntry],
    run_id: str,
    previous_synthesis: Mapping[str, Any] | None = None,
) -> DailyBriefSynthesisStageData:
    query_text = build_daily_brief_query(documents=stage_data.documents)
    evidence_pack_report = build_evidence_pack_report(
        fts_rows=stage_data.fts_rows,
        query_text=query_text,
        pack_size=30,
    )
    evidence_pack_items = evidence_pack_report["items"]
    evidence_pack_items = _attach_doc_ids(
        evidence_pack_items=evidence_pack_items,
        fts_rows=stage_data.fts_rows,
    )

    documents_by_id = {str(document["doc_id"]): document for document in stage_data.documents}
    chunks_by_id = {str(chunk["chunk_id"]): chunk for chunk in stage_data.chunks}
    citation_store = build_citation_store(
        evidence_items=evidence_pack_items,
        documents_by_id=documents_by_id,
        chunks_by_id=chunks_by_id,
    )
    validation_registry = _build_validation_registry(
        registry=registry,
        documents=stage_data.documents,
    )
    available_source_ids = {str(item["source_id"]) for item in evidence_pack_items}
    stage8_result: CitationValidationResult | None = None
    retry_plan: SynthesisRetryPlan | None = None
    for validation_attempt in range(1, MAX_VALIDATION_ATTEMPTS + 1):
        synthesis = build_synthesis(
            evidence_items=evidence_pack_items,
            documents_by_id=documents_by_id,
            citation_store=citation_store,
            retry_plan=retry_plan,
        )
        current_result = run_stage8_citation_validation(
            synthesis,
            citation_store,
            source_registry=validation_registry,
            available_source_ids=available_source_ids,
        )
        retry_exhausted = (
            current_result["status"] == "retry"
            and validation_attempt >= MAX_VALIDATION_ATTEMPTS
        )
        stage8_result = {
            **current_result,
            "validation_attempts": validation_attempt,
            "max_validation_attempts": MAX_VALIDATION_ATTEMPTS,
            "retry_exhausted": retry_exhausted,
        }
        if current_result["status"] != "retry" or retry_exhausted:
            break
        retry_plan = _build_retry_plan(
            synthesis=synthesis,
            validation_result=current_result,
            citation_store=citation_store,
        )

    if stage8_result is None:
        raise ValueError("Daily brief synthesis did not produce a validation result.")

    final_result = finalize_validation_outcome(validation_result=stage8_result)
    changed_section = build_changed_section(
        current_synthesis=final_result["synthesis"],
        previous_synthesis=previous_synthesis,
    )
    if changed_section:
        final_synthesis = dict(final_result["synthesis"])
        final_synthesis["changed"] = changed_section
        final_result = {
            **final_result,
            "synthesis": final_synthesis,
        }
    synthesis_id = f"syn_{run_id}"
    return DailyBriefSynthesisStageData(
        query_text=query_text,
        evidence_pack_items=evidence_pack_items,
        evidence_pack_report=evidence_pack_report,
        citation_store=stage8_result["citation_store"],
        stage8_result=stage8_result,
        final_result=final_result,
        citation_rows=list(stage8_result["citation_store"].values()),
        synthesis_bullet_rows=_build_synthesis_bullet_rows(
            synthesis=final_result["synthesis"],
            synthesis_id=synthesis_id,
        ),
        bullet_citation_rows=_build_bullet_citation_rows(
            synthesis=final_result["synthesis"],
            synthesis_id=synthesis_id,
        ),
    )


def _build_retry_plan(
    *,
    synthesis: DailyBriefSynthesis,
    validation_result: CitationValidationResult,
    citation_store: Mapping[str, Mapping[str, Any]],
) -> SynthesisRetryPlan:
    target_sections = tuple(
        section
        for section in validation_result["report"].get("empty_core_sections", [])
        if section in {"prevailing", "counter", "minority", "watch"}
    )
    validated_synthesis = validation_result["synthesis"]
    pinned_chunk_ids_by_section: dict[str, str] = {}
    blocked_chunk_ids: set[str] = set()

    for section in ("prevailing", "counter", "minority", "watch"):
        validated_chunk_ids = _chunk_ids_for_section(
            synthesis=validated_synthesis,
            section=section,
            citation_store=citation_store,
        )
        if section in target_sections or not validated_chunk_ids:
            blocked_chunk_ids.update(
                _chunk_ids_for_section(
                    synthesis=synthesis,
                    section=section,
                    citation_store=citation_store,
                )
            )
            continue
        pinned_chunk_ids_by_section[section] = validated_chunk_ids[0]

    if not target_sections:
        target_sections = tuple(
            section
            for section in ("prevailing", "counter", "minority", "watch")
            if section not in pinned_chunk_ids_by_section
        )
        for section in target_sections:
            blocked_chunk_ids.update(
                _chunk_ids_for_section(
                    synthesis=synthesis,
                    section=section,
                    citation_store=citation_store,
                )
            )

    return SynthesisRetryPlan(
        pinned_chunk_ids_by_section=pinned_chunk_ids_by_section,
        target_sections=target_sections,
        blocked_chunk_ids=frozenset(blocked_chunk_ids),
    )


def _chunk_ids_for_section(
    *,
    synthesis: Mapping[str, Any],
    section: str,
    citation_store: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    bullets = synthesis.get(section, [])
    if not isinstance(bullets, list):
        return []

    chunk_ids: list[str] = []
    for bullet in bullets:
        if not isinstance(bullet, Mapping):
            continue
        citation_ids = bullet.get("citation_ids", [])
        if not isinstance(citation_ids, list):
            continue
        for citation_id in citation_ids:
            citation = citation_store.get(str(citation_id))
            if isinstance(citation, Mapping) and citation.get("chunk_id") is not None:
                chunk_ids.append(str(citation["chunk_id"]))
    return chunk_ids


def _build_source_row(*, source: SourceRegistryEntry, generated_at_utc: str) -> SourceRow:
    return {
        "source_id": source["id"],
        "name": source["name"],
        "base_url": source["url"],
        "source_type": source["type"],
        "credibility_tier": source["credibility_tier"],
        "paywall_policy": source["paywall_policy"],
        "fetch_interval": source["fetch_interval"],
        "tags_json": json.dumps(list(source.get("tags", []))),
        "enabled": 1,
        "created_at": generated_at_utc,
        "updated_at": generated_at_utc,
    }


def _build_runtime_document_record(
    *,
    source: Mapping[str, Any],
    extracted: Mapping[str, Any],
    doc_id: str,
    run_id: str,
) -> RuntimeDocumentRecord:
    document = build_document_record(source=source, extracted=extracted)
    document["doc_id"] = doc_id
    document["credibility_tier"] = source["credibility_tier"]
    document["ingestion_run_id"] = run_id
    return document


def _build_validation_registry(
    *,
    registry: Mapping[str, SourceRegistryEntry],
    documents: Iterable[RuntimeDocumentRecord],
) -> dict[str, SourceRegistryEntry]:
    normalized_registry = {source_id: dict(source) for source_id, source in registry.items()}
    for document in documents:
        source_id = str(document["source_id"])
        source_meta = normalized_registry.get(source_id)
        if source_meta is None:
            continue
        canonical_url = document.get("canonical_url")
        if canonical_url:
            source_meta["base_url"] = canonical_url
    return normalized_registry


def _attach_doc_ids(
    *,
    evidence_pack_items: Iterable[Mapping[str, Any]],
    fts_rows: Iterable[FtsRow],
) -> list[EvidencePackItem]:
    doc_ids_by_chunk_id = {str(row["chunk_id"]): row["doc_id"] for row in fts_rows}
    enriched_items: list[EvidencePackItem] = []
    for item in evidence_pack_items:
        enriched = dict(item)
        enriched["doc_id"] = doc_ids_by_chunk_id[str(item["chunk_id"])]
        enriched_items.append(enriched)
    return enriched_items


def _build_synthesis_bullet_rows(
    *,
    synthesis: DailyBriefSynthesis,
    synthesis_id: str,
) -> list[DailyBriefSectionBulletRow]:
    rows: list[DailyBriefSectionBulletRow] = []
    for section in DAILY_BRIEF_OUTPUT_SECTIONS:
        bullets = synthesis.get(section, [])
        if not isinstance(bullets, list):
            continue
        for bullet_index, bullet in enumerate(bullets):
            if not isinstance(bullet, Mapping):
                continue
            rows.append(
                {
                    "synthesis_id": synthesis_id,
                    "section": section,
                    "bullet_index": bullet_index,
                    "text": str(bullet.get("text", "")),
                    "claim_span_count": 1,
                    "is_abstain": int("Insufficient evidence" in str(bullet.get("text", ""))),
                    "confidence_label": bullet.get("confidence_label"),
                }
            )
    return rows


def _build_bullet_citation_rows(
    *,
    synthesis: DailyBriefSynthesis,
    synthesis_id: str,
) -> list[BulletCitationRow]:
    rows: list[BulletCitationRow] = []
    for section in DAILY_BRIEF_OUTPUT_SECTIONS:
        bullets = synthesis.get(section, [])
        if not isinstance(bullets, list):
            continue
        for bullet_index, bullet in enumerate(bullets):
            if not isinstance(bullet, Mapping):
                continue
            for citation_id in bullet.get("citation_ids", []):
                rows.append(
                    {
                        "synthesis_id": synthesis_id,
                        "section": section,
                        "bullet_index": bullet_index,
                        "claim_span_index": 0,
                        "citation_id": str(citation_id),
                    }
                )
    return rows


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _budget_snapshot(*, context: Any) -> dict[str, Any]:
    snapshot = getattr(context, "budget_snapshot", None)
    if isinstance(snapshot, Mapping):
        return dict(snapshot)
    return {
        "hourly_spend_usd": 0.0,
        "hourly_cap_usd": 0.10,
        "daily_spend_usd": 0.0,
        "daily_cap_usd": 3.0,
        "monthly_spend_usd": 0.0,
        "monthly_cap_usd": 100.0,
        "allowed": True,
    }


def _guardrail_checks(
    *,
    stage8_result: Mapping[str, Any] | None,
    final_status: str,
    budget_snapshot: Mapping[str, Any],
    diversity_report: Mapping[str, Any] | None,
) -> dict[str, Any]:
    citation_level = "warn" if stage8_result is None else "pass"
    if stage8_result is not None and stage8_result["status"] == "partial":
        citation_level = "warn"
    if stage8_result is not None and stage8_result["status"] == "retry":
        citation_level = "fail"

    notes: list[str] = []
    if stage8_result is None:
        notes.append("Citation validation did not run because budget preflight stopped the run.")
    if final_status == "abstained":
        notes.append("Daily brief downgraded to abstain after citation validation.")
    validation_attempts = 0
    if stage8_result is not None:
        validation_attempts = int(stage8_result.get("validation_attempts", 1))
    if validation_attempts > 1:
        notes.append(f"Citation validation required {validation_attempts} synthesis attempt(s).")
    removed_bullets = 0
    if stage8_result is not None:
        removed_bullets = int(stage8_result["report"]["removed_bullets"])
    if removed_bullets > 0:
        notes.append(f"{removed_bullets} bullet(s) were removed or downgraded during validation.")
    budget_allowed = bool(budget_snapshot.get("allowed", True))
    if not budget_allowed:
        notes.append("Budget preflight blocked the run before delivery work started.")

    diversity_level = "warn"
    if isinstance(diversity_report, Mapping):
        diversity_level = str(diversity_report.get("diversity_check", "warn"))
        for note in diversity_report.get("notes", []):
            if isinstance(note, str):
                notes.append(note)
    elif not budget_allowed:
        notes.append("Diversity check did not run because budget preflight stopped the run.")

    return {
        "citation_check": citation_level,
        "paywall_check": "pass",
        "diversity_check": diversity_level,
        "budget_check": "pass" if budget_allowed else "fail",
        "notes": notes,
    }


def _default_budget_preflight(*, generated_at_utc: str) -> dict[str, Any]:
    date_prefix = generated_at_utc[:10]
    month_prefix = generated_at_utc[:7]
    return {
        "hourly_spend_usd": 0.0,
        "daily_spend_usd": 0.0,
        "monthly_spend_usd": 0.0,
        "next_estimated_cost_usd": 0.0,
        "caps": BudgetCaps(),
        "windows": {
            "hourly": BudgetWindowSnapshot(
                window_start=f"{date_prefix}T00:00:00Z",
                window_end=f"{date_prefix}T00:59:59Z",
                cost_usd=0.0,
            ),
            "daily": BudgetWindowSnapshot(
                window_start=f"{date_prefix}T00:00:00Z",
                window_end=f"{date_prefix}T23:59:59Z",
                cost_usd=0.0,
            ),
            "monthly": BudgetWindowSnapshot(
                window_start=f"{month_prefix}-01T00:00:00Z",
                window_end=f"{month_prefix}-31T23:59:59Z",
                cost_usd=0.0,
            ),
        },
    }


def _artifact_dir(*, base_dir: Path, report_date: str, run_id: str) -> Path:
    artifact_dir = base_dir / "artifacts" / "runtime" / "daily_brief_runs" / report_date / run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    return artifact_dir


def _load_previous_synthesis(*, base_dir: Path, report_date: str) -> dict[str, Any] | None:
    current_date = datetime.fromisoformat(report_date).date()
    previous_date = (current_date - timedelta(days=1)).isoformat()
    prior_dir = base_dir / "artifacts" / "runtime" / "daily_brief_runs" / previous_date
    if not prior_dir.exists():
        return None

    candidate_paths = sorted(prior_dir.glob("*/synthesis.json"))
    if not candidate_paths:
        return None

    return json.loads(candidate_paths[-1].read_text(encoding="utf-8"))


def _persist_budget_stop_outputs(
    *,
    base_dir: Path,
    run_id: str,
    generated_at_utc: str,
    pipeline_result: Mapping[str, Any],
) -> dict[str, Any]:
    report_date = generated_at_utc[:10]
    artifact_dir = _artifact_dir(base_dir=base_dir, report_date=report_date, run_id=run_id)
    budget_snapshot = dict(pipeline_result.get("budget_snapshot", {}))
    guardrail_checks = _guardrail_checks(
        stage8_result=None,
        final_status="stopped_budget",
        budget_snapshot=budget_snapshot,
        diversity_report=None,
    )
    decision_record = build_and_persist_decision_record(
        base_dir=base_dir,
        run_id=run_id,
        run_type="daily_brief",
        stage8_status="failed",
        synthesis={},
        removed_bullets=0,
        budget_snapshot=budget_snapshot,
        guardrail_checks=guardrail_checks,
        output_path=None,
        generated_at_utc=generated_at_utc,
    )
    _write_json(
        artifact_dir / "run_summary.json",
        {
            "run_id": run_id,
            "report_date": report_date,
            "query_text": None,
            "docs_fetched": 0,
            "docs_ingested": 0,
            "chunks_indexed": 0,
            "stage8_status": None,
            "final_status": "stopped_budget",
            "budget_snapshot": budget_snapshot,
            "budget_ledger_rows": list(pipeline_result.get("budget_ledger_rows", [])),
            "guardrail_checks": guardrail_checks,
            "diversity_stats": {},
        },
    )
    return {
        "status": "stopped_budget",
        "html_path": None,
        "decision_record_path": decision_record["record_path"],
        "artifact_dir": str(artifact_dir),
        "query_text": None,
        "abstain_reason": pipeline_result.get("error_summary"),
    }


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
