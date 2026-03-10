from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from apps.agent.delivery.html_report import render_daily_brief_html
from apps.agent.ingest.dedup import classify_duplicate
from apps.agent.ingest.extract import extract_payload
from apps.agent.ingest.fetch import plan_fetch_items
from apps.agent.ingest.normalize import build_document_record
from apps.agent.orchestrator import run_pipeline
from apps.agent.pipeline.stage10_decision_record import build_and_persist_decision_record
from apps.agent.pipeline.stage8_validation import run_stage8_citation_validation
from apps.agent.pipeline.types import (
    DAILY_BRIEF_OUTPUT_SECTIONS,
    BulletCitationRow,
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
from apps.agent.retrieval.evidence_pack import build_evidence_pack
from apps.agent.retrieval.fts_index import build_fts_rows
from apps.agent.runtime.source_scope import load_active_source_subset
from apps.agent.runtime.source_scope import load_source_registry
from apps.agent.synthesis.postprocess import finalize_validation_outcome
from apps.agent.daily_brief.synthesis import build_citation_store, build_synthesis


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FIXTURE_PATH = ROOT / "artifacts" / "runtime" / "daily_brief_fixture_payloads.json"
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
    )
    execution.setdefault("status", "failed")
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
) -> dict[str, Any]:
    input_data = prepare_daily_brief_inputs(
        fixture_path=fixture_path,
        generated_at_utc=generated_at_utc,
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
    )
    report_date = generated_at_utc[:10]
    output_path = base_dir / "artifacts" / "daily" / report_date / "brief.html"
    render_daily_brief_html(
        output_path=output_path,
        report_date=report_date,
        run_id=run_id,
        synthesis=synthesis_data.final_result["synthesis"],
        citation_store=synthesis_data.stage8_result["citation_store"],
    )

    decision_record = build_and_persist_decision_record(
        base_dir=base_dir,
        run_id=run_id,
        run_type="daily_brief",
        stage8_status=synthesis_data.stage8_result["status"],
        synthesis=synthesis_data.final_result["synthesis"],
        removed_bullets=int(synthesis_data.stage8_result["report"]["removed_bullets"]),
        budget_snapshot=_budget_snapshot(),
        guardrail_checks=_guardrail_checks(
            stage8_result=synthesis_data.stage8_result,
            final_status=synthesis_data.final_result["status"],
        ),
        output_path=output_path,
        generated_at_utc=generated_at_utc,
    )

    artifact_dir = base_dir / "artifacts" / "runtime" / "daily_brief_runs" / report_date / run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
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
) -> DailyBriefInputStageData:
    registry = load_source_registry()
    active_sources = load_active_source_subset(registry=registry)
    fixture_payloads = load_active_fixture_payloads(fixture_path=fixture_path)
    planned_items = plan_fetch_items(sources=active_sources, candidate_payloads=fixture_payloads)
    if not planned_items:
        raise ValueError("No fixture payloads available for active sources")

    source_rows = [_build_source_row(source=source, generated_at_utc=generated_at_utc) for source in active_sources]
    return DailyBriefInputStageData(
        registry=registry,
        active_sources=active_sources,
        planned_items=planned_items,
        source_rows=source_rows,
    )


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
) -> DailyBriefSynthesisStageData:
    query_text = build_daily_brief_query(documents=stage_data.documents)
    evidence_pack_items = build_evidence_pack(fts_rows=stage_data.fts_rows, query_text=query_text, pack_size=30)
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
    synthesis = build_synthesis(
        evidence_items=evidence_pack_items,
        documents_by_id=documents_by_id,
        citation_store=citation_store,
    )

    validation_registry = _build_validation_registry(
        registry=registry,
        documents=stage_data.documents,
    )
    stage8_result = run_stage8_citation_validation(
        synthesis,
        citation_store,
        source_registry=validation_registry,
        available_source_ids={str(item["source_id"]) for item in evidence_pack_items},
    )
    final_result = finalize_validation_outcome(validation_result=stage8_result)
    synthesis_id = f"syn_{run_id}"
    return DailyBriefSynthesisStageData(
        query_text=query_text,
        evidence_pack_items=evidence_pack_items,
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


def _budget_snapshot() -> dict[str, Any]:
    return {
        "hourly_spend_usd": 0.0,
        "hourly_cap_usd": 0.10,
        "daily_spend_usd": 0.0,
        "daily_cap_usd": 3.0,
        "monthly_spend_usd": 0.0,
        "monthly_cap_usd": 100.0,
        "allowed": True,
    }


def _guardrail_checks(*, stage8_result: Mapping[str, Any], final_status: str) -> dict[str, Any]:
    citation_level = "pass"
    if stage8_result["status"] == "partial":
        citation_level = "warn"
    if stage8_result["status"] == "retry":
        citation_level = "fail"

    notes: list[str] = []
    if final_status == "abstained":
        notes.append("Daily brief downgraded to abstain after citation validation.")
    removed_bullets = int(stage8_result["report"]["removed_bullets"])
    if removed_bullets > 0:
        notes.append(f"{removed_bullets} bullet(s) were removed or downgraded during validation.")

    diversity_level = "warn" if final_status == "abstained" else "pass"

    return {
        "citation_check": citation_level,
        "paywall_check": "pass",
        "diversity_check": diversity_level,
        "budget_check": "pass",
        "notes": notes,
    }


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
