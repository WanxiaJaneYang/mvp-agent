from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from smtplib import SMTP
from typing import Any, cast

from apps.agent.daily_brief.delta import build_changed_section_from_deltas, build_claim_deltas
from apps.agent.daily_brief.editorial_planner import LocalBriefPlanner, build_corpus_summary
from apps.agent.daily_brief.issue_dedup import dedupe_issues
from apps.agent.daily_brief.issue_retrieval import build_brief_corpus_report, build_issue_evidence_scopes
from apps.agent.daily_brief.model_interfaces import (
    BriefPlannerProvider,
    ClaimComposerInput,
    ClaimComposerProvider,
    CriticInput,
    CriticProvider,
    IssuePlannerInput,
    IssuePlannerProvider,
)
from apps.agent.daily_brief.prior_brief_context import build_prior_brief_context
from apps.agent.daily_brief.synthesis import (
    SynthesisRetryPlan,
    build_citation_store,
    build_synthesis,
    build_synthesis_from_structured_claims,
)
from apps.agent.delivery.email_sender import EmailDeliveryConfig, send_daily_brief_email
from apps.agent.delivery.html_report import render_daily_brief_html
from apps.agent.delivery.scheduler import (
    DailyBriefSchedule,
    compute_next_scheduled_run,
    scheduled_local_date,
)
from apps.agent.ingest.dedup import classify_duplicate
from apps.agent.ingest.extract import extract_payload
from apps.agent.ingest.fetch import plan_fetch_items
from apps.agent.ingest.live_fetch import fetch_live_payloads_for_source
from apps.agent.ingest.normalize import build_document_record
from apps.agent.orchestrator import run_pipeline
from apps.agent.pipeline.identifiers import build_document_id, build_synthesis_id
from apps.agent.pipeline.stage8_validation import run_stage8_citation_validation
from apps.agent.pipeline.stage10_decision_record import build_and_persist_decision_record
from apps.agent.pipeline.types import (
    BriefPlan,
    BulletCitationRow,
    CitationStoreEntry,
    CitationValidationResult,
    ClaimDelta,
    CriticReport,
    DailyBriefCorpusStageData,
    DailyBriefInputStageData,
    DailyBriefOutputSection,
    DailyBriefSectionBulletRow,
    DailyBriefSynthesis,
    DailyBriefSynthesisStageData,
    DeliveryMode,
    EvidencePackItem,
    FtsRow,
    IssueEvidenceScope,
    IssueInformationGain,
    IssueMap,
    IssueOverlapReport,
    PublishDecision,
    PublishDecisionStatus,
    RunStatus,
    RuntimeChunkRow,
    RuntimeDocumentRecord,
    SourceRegistryEntry,
    SourceRow,
    StageResult,
    StructuredClaim,
    ValidatedDailyBriefSynthesis,
)
from apps.agent.portfolio.input_store import load_portfolio_positions
from apps.agent.portfolio.relevance import build_portfolio_relevance_flags
from apps.agent.retrieval.chunker import build_chunk_rows
from apps.agent.retrieval.evidence_pack import build_evidence_pack_report
from apps.agent.retrieval.fts_index import build_fts_rows
from apps.agent.runtime.budget_guard import BudgetCaps
from apps.agent.runtime.cost_ledger import BudgetWindowSnapshot
from apps.agent.runtime.source_scope import load_active_source_subset, load_source_registry
from apps.agent.storage.sqlite_runtime import persist_daily_brief_runtime
from apps.agent.synthesis.postprocess import finalize_validation_outcome

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
    delivery_schedule: DailyBriefSchedule | None = None,
    email_config: EmailDeliveryConfig | None = None,
    smtp_class: Any = SMTP,
    issue_planner: IssuePlannerProvider | None = None,
    claim_composer: ClaimComposerProvider | None = None,
    critic: CriticProvider | None = None,
    provider_resolution: Mapping[str, Any] | None = None,
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
                delivery_schedule=delivery_schedule,
                email_config=email_config,
                smtp_class=smtp_class,
                issue_planner=issue_planner,
                claim_composer=claim_composer,
                critic=critic,
                provider_resolution=provider_resolution,
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
                provider_resolution=provider_resolution,
            )
        )
    execution.setdefault("status", pipeline_result["status"])
    execution["lifecycle"] = lifecycle
    execution["pipeline_status"] = pipeline_result["status"]
    execution["error_summary"] = pipeline_result.get("error_summary")
    execution["runtime_db_path"] = str(
        _persist_run_state(
            base_dir=base_dir,
            generated_at_utc=timestamp,
            execution=execution,
            pipeline_result=pipeline_result,
        )
    )
    return execution


def run_daily_brief(
    *,
    base_dir: Path,
    run_id: str = "run_daily_live",
    generated_at_utc: str | None = None,
    budget_preflight: Mapping[str, Any] | None = None,
    delivery_schedule: DailyBriefSchedule | None = None,
    email_config: EmailDeliveryConfig | None = None,
    smtp_class: Any = SMTP,
    issue_planner: IssuePlannerProvider | None = None,
    claim_composer: ClaimComposerProvider | None = None,
    critic: CriticProvider | None = None,
    provider_resolution: Mapping[str, Any] | None = None,
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
                delivery_schedule=delivery_schedule,
                email_config=email_config,
                smtp_class=smtp_class,
                issue_planner=issue_planner,
                claim_composer=claim_composer,
                critic=critic,
                provider_resolution=provider_resolution,
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
                provider_resolution=provider_resolution,
            )
        )
    execution.setdefault("status", pipeline_result["status"])
    execution["lifecycle"] = lifecycle
    execution["pipeline_status"] = pipeline_result["status"]
    execution["error_summary"] = pipeline_result.get("error_summary")
    execution["runtime_db_path"] = str(
        _persist_run_state(
            base_dir=base_dir,
            generated_at_utc=timestamp,
            execution=execution,
            pipeline_result=pipeline_result,
        )
    )
    return execution


def _execute_daily_brief_slice(
    *,
    base_dir: Path,
    fixture_path: Path | None,
    run_id: str,
    generated_at_utc: str,
    context: Any,
    use_live_sources: bool = False,
    delivery_schedule: DailyBriefSchedule | None = None,
    email_config: EmailDeliveryConfig | None = None,
    smtp_class: Any = SMTP,
    issue_planner: IssuePlannerProvider | None = None,
    claim_composer: ClaimComposerProvider | None = None,
    critic: CriticProvider | None = None,
    provider_resolution: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    report_date = generated_at_utc[:10]
    schedule = delivery_schedule or DailyBriefSchedule()
    local_report_date = scheduled_local_date(
        generated_at_utc=generated_at_utc,
        schedule=schedule,
    )
    next_scheduled_run_at_utc = compute_next_scheduled_run(
        now_utc=generated_at_utc,
        schedule=schedule,
    )
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
        generated_at_utc=generated_at_utc,
        previous_synthesis=_load_previous_synthesis(base_dir=base_dir, report_date=report_date),
        issue_planner=issue_planner,
        claim_composer=claim_composer,
        critic=critic,
    )
    portfolio_positions = load_portfolio_positions(base_dir=base_dir)
    portfolio_relevance_flags = build_portfolio_relevance_flags(
        positions=portfolio_positions,
        documents=corpus_data.documents,
        synthesis=synthesis_data.final_result["synthesis"],
        synthesis_id=build_synthesis_id(run_id=run_id),
        generated_at_utc=generated_at_utc,
    )
    output_path = base_dir / "artifacts" / "daily" / report_date / "brief.html"
    budget_snapshot = _budget_snapshot(context=context)
    guardrail_checks = _guardrail_checks(
        stage8_result=synthesis_data.stage8_result,
        final_status=synthesis_data.final_result["status"],
        budget_snapshot=budget_snapshot,
        diversity_report=synthesis_data.evidence_pack_report,
    )
    publish_summary = _publish_summary(
        stage8_result=synthesis_data.stage8_result,
        final_status=synthesis_data.final_result["status"],
        critic_report=synthesis_data.critic_report,
        email_requested=email_config is not None,
    )
    guardrail_checks = {**guardrail_checks, **publish_summary}
    render_daily_brief_html(
        output_path=output_path,
        report_date=report_date,
        run_id=run_id,
        synthesis=synthesis_data.final_result["synthesis"],
        citation_store=synthesis_data.stage8_result["citation_store"],
        guardrail_checks=guardrail_checks,
    )
    email_delivery = None
    if email_config is not None and publish_summary["publish_decision"] == "publish":
        email_delivery = send_daily_brief_email(
            config=email_config,
            report_date=local_report_date,
            run_id=run_id,
            html_body=output_path.read_text(encoding="utf-8"),
            status_title="Abstained" if synthesis_data.final_result["status"] == "abstained" else "Ready",
            synthesis=cast(dict[str, Any], synthesis_data.final_result["synthesis"]),
            citation_status=publish_summary["citation_status"],
            analytical_status=publish_summary["analytical_status"],
            publish_decision=publish_summary["publish_decision"],
            smtp_class=smtp_class,
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
        citation_status=publish_summary["citation_status"],
        analytical_status=publish_summary["analytical_status"],
        publish_decision=publish_summary["publish_decision"],
        reason_codes=publish_summary["reason_codes"],
        output_path=output_path,
        generated_at_utc=generated_at_utc,
    )

    artifact_dir = _artifact_dir(base_dir=base_dir, report_date=report_date, run_id=run_id)
    _write_json(artifact_dir / "sources.json", corpus_data.source_rows)
    _write_json(artifact_dir / "documents.json", corpus_data.documents)
    _write_json(artifact_dir / "chunks.json", corpus_data.chunks)
    _write_json(artifact_dir / "fts_rows.json", corpus_data.fts_rows)
    _write_json(artifact_dir / "brief_plan.json", synthesis_data.brief_plan)
    _write_json(artifact_dir / "evidence_pack_items.json", synthesis_data.evidence_pack_items)
    _write_json(artifact_dir / "issue_evidence_scopes.json", synthesis_data.issue_evidence_scopes)
    _write_json(artifact_dir / "issue_map.json", synthesis_data.issue_map)
    _write_json(artifact_dir / "issue_overlap_reports.json", synthesis_data.issue_overlap_reports)
    _write_json(artifact_dir / "information_gain_reports.json", synthesis_data.information_gain_reports)
    _write_json(artifact_dir / "claim_objects.json", synthesis_data.structured_claims)
    _write_json(artifact_dir / "claim_deltas.json", synthesis_data.claim_deltas)
    _write_json(artifact_dir / "critic_report.json", synthesis_data.critic_report)
    _write_json(artifact_dir / "citations.json", synthesis_data.citation_rows)
    _write_json(artifact_dir / "synthesis.json", synthesis_data.final_result["synthesis"])
    _write_json(artifact_dir / "synthesis_bullets.json", synthesis_data.synthesis_bullet_rows)
    _write_json(artifact_dir / "bullet_citations.json", synthesis_data.bullet_citation_rows)
    _write_json(
        artifact_dir / "portfolio_positions.json",
        [position.to_dict() for position in portfolio_positions],
    )
    _write_json(
        artifact_dir / "portfolio_relevance.json",
        [flag.to_dict() for flag in portfolio_relevance_flags],
    )
    _write_json(
        artifact_dir / "run_summary.json",
        {
            "run_id": run_id,
            "report_date": report_date,
            "query_text": synthesis_data.query_text,
            "issue_count": len(synthesis_data.issue_map),
            "claim_count": len(synthesis_data.structured_claims),
            "critic_status": None if synthesis_data.critic_report is None else synthesis_data.critic_report["status"],
            "render_mode": synthesis_data.brief_plan["render_mode"],
            "docs_fetched": context.counters.docs_fetched,
            "docs_ingested": context.counters.docs_ingested,
            "chunks_indexed": context.counters.chunks_indexed,
            "stage8_status": synthesis_data.stage8_result["status"],
            "final_status": synthesis_data.final_result["status"],
            "validation_attempts": synthesis_data.stage8_result["validation_attempts"],
            "max_validation_attempts": synthesis_data.stage8_result["max_validation_attempts"],
            "validation_retry_exhausted": synthesis_data.stage8_result["retry_exhausted"],
            "scheduled_for_local_date": local_report_date,
            "next_scheduled_run_at_utc": next_scheduled_run_at_utc,
            "email_delivery": email_delivery,
            "budget_snapshot": budget_snapshot,
            "budget_ledger_rows": list(context.budget_ledger_rows),
            "guardrail_checks": guardrail_checks,
            "diversity_stats": synthesis_data.evidence_pack_report["diversity_stats"],
            "portfolio_positions_count": len(portfolio_positions),
            "portfolio_relevance_count": len(portfolio_relevance_flags),
            "citation_status": publish_summary["citation_status"],
            "analytical_status": publish_summary["analytical_status"],
            "publish_decision": publish_summary["publish_decision"],
            "reason_codes": publish_summary["reason_codes"],
            "delivery_mode": publish_summary["delivery_mode"],
            **_provider_summary(provider_resolution=provider_resolution),
        },
    )

    return {
        "status": synthesis_data.final_result["status"],
        "html_path": str(output_path),
        "decision_record_path": decision_record["record_path"],
        "artifact_dir": str(artifact_dir),
        "query_text": synthesis_data.query_text,
        "abstain_reason": synthesis_data.final_result.get("abstain_reason"),
        "scheduled_for_local_date": local_report_date,
        "next_scheduled_run_at_utc": next_scheduled_run_at_utc,
        "email_delivery": email_delivery,
        "citation_status": publish_summary["citation_status"],
        "analytical_status": publish_summary["analytical_status"],
        "publish_decision": publish_summary["publish_decision"],
        "reason_codes": publish_summary["reason_codes"],
        "delivery_mode": publish_summary["delivery_mode"],
        **_provider_summary(provider_resolution=provider_resolution),
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

    for planned in stage_data.planned_items:
        source_id = str(planned["source_id"])
        source = stage_data.registry[source_id]
        extracted = extract_payload(source=source, payload=planned["payload"])
        document = _build_runtime_document_record(
            source=source,
            extracted=extracted,
            doc_id=build_document_id(canonical_url=str(extracted["canonical_url"])),
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
            fts_rows.append(cast(FtsRow, enriched))

    context.counters.docs_fetched = len(stage_data.planned_items)
    context.counters.docs_ingested = len(documents)
    context.counters.chunks_indexed = len(chunks)
    corpus_report = build_brief_corpus_report(fts_rows=fts_rows, pack_size=30)

    return DailyBriefCorpusStageData(
        source_rows=stage_data.source_rows,
        documents=documents,
        chunks=chunks,
        fts_rows=fts_rows,
        corpus_items=corpus_report["items"],
        diversity_stats=corpus_report["diversity_stats"],
    )


def build_daily_brief_synthesis(
    *,
    stage_data: DailyBriefCorpusStageData,
    registry: Mapping[str, SourceRegistryEntry],
    run_id: str,
    generated_at_utc: str | None = None,
    previous_synthesis: Mapping[str, Any] | None = None,
    brief_planner: BriefPlannerProvider | None = None,
    issue_planner: IssuePlannerProvider | None = None,
    claim_composer: ClaimComposerProvider | None = None,
    critic: CriticProvider | None = None,
) -> DailyBriefSynthesisStageData:
    if (issue_planner is None) != (claim_composer is None):
        raise ValueError("Daily brief synthesis requires both issue_planner and claim_composer together.")

    synthesis_generated_at_utc = generated_at_utc or _utc_now_iso()
    use_structured_orchestration = issue_planner is not None and claim_composer is not None
    evidence_pack_items: list[EvidencePackItem]
    evidence_pack_report: dict[str, Any]
    query_text = ""
    if use_structured_orchestration:
        evidence_pack_items = list(stage_data.corpus_items)
        diversity_check = (
            "pass"
            if int(stage_data.diversity_stats.get("unique_publishers", 0) or 0) >= 3
            else "warn"
        )
        evidence_pack_report = {
            "items": evidence_pack_items,
            "diversity_stats": dict(stage_data.diversity_stats),
            "diversity_check": diversity_check,
            "notes": [],
        }
    else:
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
    prior_brief_context = build_prior_brief_context(
        previous_synthesis=previous_synthesis,
        previous_generated_at_utc=None,
    )
    brief_plan = _build_brief_plan(
        evidence_pack_items=evidence_pack_items,
        documents_by_id=documents_by_id,
        evidence_pack_report=evidence_pack_report,
        prior_brief_context=prior_brief_context,
        brief_planner=brief_planner,
        run_id=run_id,
        generated_at_utc=synthesis_generated_at_utc,
    )
    issue_map: list[IssueMap] = []
    issue_evidence_scopes: list[IssueEvidenceScope] = []
    issue_overlap_reports: list[IssueOverlapReport] = []
    information_gain_reports: list[IssueInformationGain] = []
    structured_claims: list[StructuredClaim] = []
    claim_deltas: list[ClaimDelta] = []
    if use_structured_orchestration:
        issue_evidence_scopes = build_issue_evidence_scopes(
            brief_plan=brief_plan,
            corpus_items=evidence_pack_items,
            fts_rows=stage_data.fts_rows,
            registry=registry,
        )
        issue_map = _build_issue_map(
            brief_plan=brief_plan,
            query_text="",
            evidence_pack_items=[],
            issue_evidence_scopes=issue_evidence_scopes,
            issue_planner=issue_planner,
            prior_brief_context=prior_brief_context,
            run_id=run_id,
            generated_at_utc=synthesis_generated_at_utc,
        )
        issue_map, issue_overlap_reports, information_gain_reports = dedupe_issues(
            issue_map=issue_map,
            brief_plan=brief_plan,
        )
    validation_registry = _build_validation_registry(
        registry=registry,
        documents=stage_data.documents,
    )
    available_source_ids = {str(item["source_id"]) for item in evidence_pack_items}
    stage8_result: CitationValidationResult | None = None
    retry_plan: SynthesisRetryPlan | None = None
    for validation_attempt in range(1, MAX_VALIDATION_ATTEMPTS + 1):
        if use_structured_orchestration:
            structured_claims = _build_structured_claims(
                issue_map=issue_map,
                citation_store=citation_store,
                evidence_pack_items=evidence_pack_items,
                documents_by_id=documents_by_id,
                claim_composer=claim_composer,
                prior_brief_context=prior_brief_context,
                run_id=run_id,
                generated_at_utc=synthesis_generated_at_utc,
            )
            synthesis = build_synthesis_from_structured_claims(
                brief_plan=brief_plan,
                issue_map=issue_map,
                structured_claims=structured_claims,
                citation_store=citation_store,
            )
        else:
            flat_synthesis = build_synthesis(
                evidence_items=evidence_pack_items,
                documents_by_id=documents_by_id,
                citation_store=citation_store,
                retry_plan=retry_plan,
            )
            issue_map = _build_issue_map(
                brief_plan=brief_plan,
                query_text=query_text,
                evidence_pack_items=evidence_pack_items,
                issue_evidence_scopes=None,
                issue_planner=None,
                prior_brief_context=prior_brief_context,
                run_id=run_id,
                generated_at_utc=synthesis_generated_at_utc,
            )
            structured_claims = _build_structured_claims_from_synthesis(
                issue_map=issue_map,
                synthesis=flat_synthesis,
            )
            synthesis = build_synthesis_from_structured_claims(
                brief_plan=brief_plan,
                issue_map=issue_map,
                structured_claims=structured_claims,
                citation_store=citation_store,
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
        if not use_structured_orchestration:
            retry_plan = _build_retry_plan(
                synthesis=flat_synthesis,
                validation_result=current_result,
                citation_store=citation_store,
            )

    if stage8_result is None:
        raise ValueError("Daily brief synthesis did not produce a validation result.")

    if prior_brief_context is not None:
        claim_deltas = build_claim_deltas(
            structured_claims=structured_claims,
            prior_brief_context=prior_brief_context,
        )

    final_result = finalize_validation_outcome(validation_result=stage8_result)
    validated_claim_ids = _claim_ids_in_synthesis(synthesis=final_result["synthesis"])
    changed_section = build_changed_section_from_deltas(
        structured_claims=[
            claim for claim in structured_claims if str(claim["claim_id"]) in validated_claim_ids
        ],
        claim_deltas=[
            delta for delta in claim_deltas if str(delta["claim_id"]) in validated_claim_ids
        ],
    )
    if changed_section:
        final_synthesis = dict(final_result["synthesis"])
        final_synthesis["changed"] = changed_section
        final_result = {
            **final_result,
            "synthesis": cast(ValidatedDailyBriefSynthesis, final_synthesis),
        }
    critic_report: CriticReport | None = None
    if critic is not None:
        critic_report = critic.review_brief(
            brief_input=CriticInput(
                run_id=run_id,
                generated_at_utc=synthesis_generated_at_utc,
                synthesis=cast(dict[str, Any], final_result["synthesis"]),
                citation_store={key: dict(value) for key, value in stage8_result["citation_store"].items()},
                prior_brief_context=prior_brief_context,
            )
        )
    publish_decision = _build_publish_decision(
        stage8_status=str(stage8_result["status"]),
        final_status=final_result["status"],
        critic_report=critic_report,
    )
    final_synthesis = _decorate_synthesis_meta(
        synthesis=final_result["synthesis"],
        publish_decision=publish_decision,
    )
    final_result = {
        **final_result,
        "synthesis": cast(ValidatedDailyBriefSynthesis, final_synthesis),
    }
    synthesis_id = build_synthesis_id(run_id=run_id)
    return DailyBriefSynthesisStageData(
        query_text=query_text,
        brief_plan=brief_plan,
        evidence_pack_items=evidence_pack_items,
        evidence_pack_report=evidence_pack_report,
        issue_evidence_scopes=issue_evidence_scopes,
        issue_map=issue_map,
        issue_overlap_reports=issue_overlap_reports,
        information_gain_reports=information_gain_reports,
        structured_claims=structured_claims,
        claim_deltas=claim_deltas,
        publish_decision=publish_decision,
        citation_store=stage8_result["citation_store"],
        stage8_result=stage8_result,
        final_result=final_result,
        critic_report=critic_report,
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


def _build_brief_plan(
    *,
    evidence_pack_items: list[EvidencePackItem],
    documents_by_id: Mapping[str, RuntimeDocumentRecord],
    evidence_pack_report: Mapping[str, Any],
    prior_brief_context: Mapping[str, Any] | None,
    brief_planner: BriefPlannerProvider | None,
    run_id: str,
    generated_at_utc: str,
) -> BriefPlan:
    corpus_summary = build_corpus_summary(
        corpus_items=evidence_pack_items,
        documents_by_id=documents_by_id,
    )
    planner = brief_planner or LocalBriefPlanner()
    return planner.plan_brief(
        brief_input={
            "run_id": run_id,
            "generated_at_utc": generated_at_utc,
            "corpus_summary": corpus_summary,
            "source_diversity_stats": dict(evidence_pack_report.get("diversity_stats", {})),
            "prior_brief_context": None if prior_brief_context is None else dict(prior_brief_context),
        }
    )


def _build_retry_plan(
    *,
    synthesis: DailyBriefSynthesis,
    validation_result: CitationValidationResult,
    citation_store: Mapping[str, CitationStoreEntry],
) -> SynthesisRetryPlan:
    target_sections = tuple(
        str(section).split(".")[-1]
        for section in validation_result["report"].get("empty_core_sections", [])
        if section in {"prevailing", "counter", "minority", "watch"}
        or str(section).split(".")[-1] in {"prevailing", "counter", "minority", "watch"}
    )
    validated_synthesis = validation_result["synthesis"]
    pinned_chunk_ids_by_section: dict[DailyBriefOutputSection, str] = {}
    blocked_chunk_ids: set[str] = set()
    core_sections: tuple[DailyBriefOutputSection, ...] = ("prevailing", "counter", "minority", "watch")
    typed_target_sections = cast(tuple[DailyBriefOutputSection, ...], target_sections)

    for section in core_sections:
        validated_chunk_ids = _chunk_ids_for_section(
            synthesis=validated_synthesis,
            section=section,
            citation_store=citation_store,
        )
        if section in typed_target_sections or not validated_chunk_ids:
            blocked_chunk_ids.update(
                _chunk_ids_for_section(
                    synthesis=synthesis,
                    section=section,
                    citation_store=citation_store,
                )
            )
            continue
        pinned_chunk_ids_by_section[section] = validated_chunk_ids[0]

    if not typed_target_sections:
        typed_target_sections = tuple(
            section
            for section in core_sections
            if section not in pinned_chunk_ids_by_section
        )
        for section in typed_target_sections:
            blocked_chunk_ids.update(
                _chunk_ids_for_section(
                    synthesis=synthesis,
                    section=section,
                    citation_store=citation_store,
                )
            )

    return SynthesisRetryPlan(
        pinned_chunk_ids_by_section=pinned_chunk_ids_by_section,
        target_sections=typed_target_sections,
        blocked_chunk_ids=frozenset(blocked_chunk_ids),
    )


def _build_issue_map(
    *,
    brief_plan: BriefPlan,
    query_text: str,
    evidence_pack_items: list[EvidencePackItem],
    issue_evidence_scopes: list[IssueEvidenceScope] | None,
    issue_planner: IssuePlannerProvider | None,
    prior_brief_context: dict[str, Any] | None,
    run_id: str,
    generated_at_utc: str,
) -> list[IssueMap]:
    if issue_planner is not None:
        issue_map = issue_planner.plan_issues(
            brief_input=IssuePlannerInput(
                run_id=run_id,
                generated_at_utc=generated_at_utc,
                brief_plan=brief_plan,
                issue_evidence_scopes=(
                    []
                    if issue_evidence_scopes is None
                    else [cast(IssueEvidenceScope, dict(item)) for item in issue_evidence_scopes]
                ),
                prior_brief_context=prior_brief_context,
            )
        )
        return issue_map[: max(1, int(brief_plan["issue_budget"]))]

    fallback_topic = query_text or "today's dominant narrative"
    issue_question = (
        f"What is the latest debate around {query_text}?"
        if query_text
        else "What is the latest market debate?"
    )
    chunk_ids = [str(item["chunk_id"]) for item in evidence_pack_items]
    return [
        IssueMap(
            issue_id="issue_001",
            issue_question=issue_question,
            thesis_hint=f"The latest evidence pack centers on {fallback_topic}.",
            supporting_evidence_ids=chunk_ids[:2],
            opposing_evidence_ids=chunk_ids[2:3],
            minority_evidence_ids=chunk_ids[3:4],
            watch_evidence_ids=chunk_ids[:1],
        )
    ]


def _build_structured_claims(
    *,
    issue_map: list[IssueMap],
    citation_store: Mapping[str, CitationStoreEntry],
    evidence_pack_items: list[EvidencePackItem],
    documents_by_id: Mapping[str, RuntimeDocumentRecord],
    claim_composer: ClaimComposerProvider | None,
    prior_brief_context: dict[str, Any] | None,
    run_id: str,
    generated_at_utc: str,
) -> list[StructuredClaim]:
    if claim_composer is not None:
        return claim_composer.compose_claims(
            brief_input=ClaimComposerInput(
                run_id=run_id,
                generated_at_utc=generated_at_utc,
                issue_map=issue_map,
                citation_store={key: dict(value) for key, value in citation_store.items()},
                prior_brief_context=prior_brief_context,
            )
        )

    legacy_synthesis = build_synthesis(
        evidence_items=evidence_pack_items,
        documents_by_id=documents_by_id,
        citation_store=citation_store,
    )
    issue_id = issue_map[0]["issue_id"] if issue_map else "issue_001"
    structured_claims: list[StructuredClaim] = []
    for claim_kind in ("prevailing", "counter", "minority", "watch"):
        bullets = legacy_synthesis.get(claim_kind, [])
        if not isinstance(bullets, list):
            continue
        for index, bullet in enumerate(bullets, start=1):
            if not isinstance(bullet, Mapping):
                continue
            structured_claims.append(
                StructuredClaim(
                    claim_id=f"{issue_id}_{claim_kind}_{index:03d}",
                    issue_id=issue_id,
                    claim_kind=claim_kind,
                    claim_text=str(bullet.get("text", "")),
                    supporting_citation_ids=[str(citation_id) for citation_id in bullet.get("citation_ids", [])],
                    opposing_citation_ids=[],
                    confidence=str(bullet.get("confidence_label", "medium")),
                    novelty_vs_prior_brief="unknown",
                    why_it_matters=f"This affects the current {claim_kind} case for the issue.",
                )
            )
    return structured_claims


def _build_structured_claims_from_synthesis(
    *,
    issue_map: list[IssueMap],
    synthesis: DailyBriefSynthesis,
) -> list[StructuredClaim]:
    issue_id = issue_map[0]["issue_id"] if issue_map else "issue_001"
    structured_claims: list[StructuredClaim] = []
    for claim_kind in ("prevailing", "counter", "minority", "watch"):
        bullets = synthesis.get(claim_kind, [])
        if not isinstance(bullets, list):
            continue
        for index, bullet in enumerate(bullets, start=1):
            if not isinstance(bullet, Mapping):
                continue
            structured_claims.append(
                StructuredClaim(
                    claim_id=f"{issue_id}_{claim_kind}_{index:03d}",
                    issue_id=issue_id,
                    claim_kind=claim_kind,
                    claim_text=str(bullet.get("text", "")),
                    supporting_citation_ids=[str(citation_id) for citation_id in bullet.get("citation_ids", [])],
                    opposing_citation_ids=[],
                    confidence=str(bullet.get("confidence_label", "medium")),
                    novelty_vs_prior_brief="unknown",
                    why_it_matters=f"This affects the current {claim_kind} case for the issue.",
                )
            )
    return structured_claims


def _chunk_ids_for_section(
    *,
    synthesis: Mapping[str, Any],
    section: str,
    citation_store: Mapping[str, CitationStoreEntry],
) -> list[str]:
    issue_items = synthesis.get("issues")
    if isinstance(issue_items, list) and issue_items:
        first_issue = issue_items[0]
        if isinstance(first_issue, Mapping):
            bullets = first_issue.get(section, [])
        else:
            bullets = []
    else:
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
    return cast(RuntimeDocumentRecord, document)


def _build_validation_registry(
    *,
    registry: Mapping[str, SourceRegistryEntry],
    documents: Iterable[RuntimeDocumentRecord],
) -> dict[str, SourceRegistryEntry]:
    normalized_registry: dict[str, SourceRegistryEntry] = {
        source_id: cast(SourceRegistryEntry, dict(source)) for source_id, source in registry.items()
    }
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
        enriched_items.append(cast(EvidencePackItem, enriched))
    return enriched_items


def _build_synthesis_bullet_rows(
    *,
    synthesis: Mapping[str, Any],
    synthesis_id: str,
) -> list[DailyBriefSectionBulletRow]:
    rows: list[DailyBriefSectionBulletRow] = []
    for section, bullet_index, bullet in _iter_synthesis_bullets(synthesis):
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
    synthesis: Mapping[str, Any],
    synthesis_id: str,
) -> list[BulletCitationRow]:
    rows: list[BulletCitationRow] = []
    for section, bullet_index, bullet in _iter_synthesis_bullets(synthesis):
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


def _iter_synthesis_bullets(
    synthesis: Mapping[str, Any],
) -> Iterable[tuple[DailyBriefOutputSection, int, Mapping[str, Any]]]:
    issues = synthesis.get("issues")
    if isinstance(issues, list):
        for issue in issues:
            if not isinstance(issue, Mapping):
                continue
            for section in ("prevailing", "counter", "minority", "watch"):
                bullets = issue.get(section, [])
                if not isinstance(bullets, list):
                    continue
                for bullet_index, bullet in enumerate(bullets):
                    if isinstance(bullet, Mapping):
                        yield section, bullet_index, bullet

    changed_bullets = synthesis.get("changed", [])
    if isinstance(changed_bullets, list):
        for bullet_index, bullet in enumerate(changed_bullets):
            if isinstance(bullet, Mapping):
                yield "changed", bullet_index, bullet


def _claim_ids_in_synthesis(*, synthesis: Mapping[str, Any]) -> set[str]:
    claim_ids: set[str] = set()
    issues = synthesis.get("issues")
    if isinstance(issues, list):
        for issue in issues:
            if not isinstance(issue, Mapping):
                continue
            for section in ("prevailing", "counter", "minority", "watch"):
                bullets = issue.get(section, [])
                if not isinstance(bullets, list):
                    continue
                for bullet in bullets:
                    if not isinstance(bullet, Mapping):
                        continue
                    claim_id = bullet.get("claim_id")
                    if claim_id is not None:
                        claim_ids.add(str(claim_id))
        return claim_ids

    for section in ("prevailing", "counter", "minority", "watch"):
        bullets = synthesis.get(section, [])
        if not isinstance(bullets, list):
            continue
        for bullet in bullets:
            if not isinstance(bullet, Mapping):
                continue
            claim_id = bullet.get("claim_id")
            if claim_id is not None:
                claim_ids.add(str(claim_id))
    return claim_ids


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


def _publish_summary(
    *,
    stage8_result: Mapping[str, Any] | None,
    final_status: str,
    critic_report: Mapping[str, Any] | None,
    email_requested: bool,
) -> PublishDecision:
    citation_status = "ok"
    if stage8_result is None or final_status == "abstained":
        citation_status = "abstained"
    elif str(stage8_result.get("status")) == "partial":
        citation_status = "partial"
    elif str(stage8_result.get("status")) == "retry":
        citation_status = "abstained"

    analytical_status = "pass"
    reason_codes: list[str] = []
    if critic_report is not None:
        analytical_status = str(critic_report.get("status") or "pass")
        reason_codes = [
            str(code)
            for code in critic_report.get("reason_codes", [])
            if isinstance(code, str)
        ]
    if citation_status == "abstained" and "citation_validation_abstained" not in reason_codes:
        reason_codes.append("citation_validation_abstained")

    publish_decision: PublishDecisionStatus = "publish"
    if citation_status == "abstained" or analytical_status == "fail":
        publish_decision = "hold"

    delivery_mode: DeliveryMode = "html_only"
    if publish_decision == "publish" and email_requested:
        delivery_mode = "email_and_html"

    return {
        "citation_status": citation_status,
        "analytical_status": analytical_status,
        "publish_decision": publish_decision,
        "reason_codes": reason_codes,
        "delivery_mode": delivery_mode,
    }


def _build_publish_decision(
    *,
    stage8_status: str,
    final_status: str,
    critic_report: Mapping[str, Any] | None,
) -> PublishDecision:
    return _publish_summary(
        stage8_result={"status": stage8_status},
        final_status=final_status,
        critic_report=critic_report,
        email_requested=False,
    )


def _decorate_synthesis_meta(
    *,
    synthesis: Mapping[str, Any],
    publish_decision: PublishDecision,
) -> dict[str, Any]:
    meta = synthesis.get("meta")
    normalized_meta = dict(meta) if isinstance(meta, Mapping) else {}
    normalized_meta.update(
        {
            "citation_status": publish_decision["citation_status"],
            "analytical_status": publish_decision["analytical_status"],
            "publish_decision": publish_decision["publish_decision"],
            "reason_codes": list(publish_decision["reason_codes"]),
        }
    )
    decorated = dict(synthesis)
    decorated["meta"] = normalized_meta
    return decorated


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
    provider_resolution: Mapping[str, Any] | None = None,
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
            **_provider_summary(provider_resolution=provider_resolution),
        },
    )
    return {
        "status": "stopped_budget",
        "html_path": None,
        "decision_record_path": decision_record["record_path"],
        "artifact_dir": str(artifact_dir),
        "query_text": None,
        "abstain_reason": pipeline_result.get("error_summary"),
        **_provider_summary(provider_resolution=provider_resolution),
    }


def _persist_run_state(
    *,
    base_dir: Path,
    generated_at_utc: str,
    execution: Mapping[str, Any],
    pipeline_result: Mapping[str, Any],
) -> Path:
    report_date = str(execution.get("scheduled_for_local_date") or generated_at_utc[:10])
    run_row = dict(pipeline_result)
    artifact_dir_value = execution.get("artifact_dir")

    if artifact_dir_value:
        artifact_dir = Path(str(artifact_dir_value))
        if not (artifact_dir / "sources.json").exists():
            return persist_daily_brief_runtime(
                base_dir=base_dir,
                generated_at_utc=generated_at_utc,
                report_date=report_date,
                query_text="",
                source_rows=[],
                documents=[],
                chunks=[],
                evidence_pack_items=[],
                evidence_pack_report={"diversity_stats": {}},
                issue_map_rows=[],
                structured_claim_rows=[],
                citation_rows=[],
                synthesis_rows=[],
                bullet_citation_rows=[],
                run_row=run_row,
                budget_ledger_rows=pipeline_result.get("budget_ledger_rows", []),
            )
        source_rows = json.loads((artifact_dir / "sources.json").read_text(encoding="utf-8"))
        documents = json.loads((artifact_dir / "documents.json").read_text(encoding="utf-8"))
        chunks = json.loads((artifact_dir / "chunks.json").read_text(encoding="utf-8"))
        evidence_pack_items = json.loads(
            (artifact_dir / "evidence_pack_items.json").read_text(encoding="utf-8")
        )
        issue_map = json.loads((artifact_dir / "issue_map.json").read_text(encoding="utf-8"))
        structured_claims = json.loads(
            (artifact_dir / "claim_objects.json").read_text(encoding="utf-8")
        )
        citations = json.loads((artifact_dir / "citations.json").read_text(encoding="utf-8"))
        synthesis_bullets = json.loads(
            (artifact_dir / "synthesis_bullets.json").read_text(encoding="utf-8")
        )
        bullet_citations = json.loads(
            (artifact_dir / "bullet_citations.json").read_text(encoding="utf-8")
        )
        portfolio_relevance = json.loads(
            (artifact_dir / "portfolio_relevance.json").read_text(encoding="utf-8")
        )
        run_summary = json.loads((artifact_dir / "run_summary.json").read_text(encoding="utf-8"))
        return persist_daily_brief_runtime(
            base_dir=base_dir,
            generated_at_utc=generated_at_utc,
            report_date=report_date,
            query_text=str(execution.get("query_text") or ""),
            source_rows=source_rows,
            documents=documents,
            chunks=chunks,
            evidence_pack_items=evidence_pack_items,
            evidence_pack_report={"diversity_stats": run_summary.get("diversity_stats", {})},
            issue_map_rows=issue_map,
            structured_claim_rows=structured_claims,
            citation_rows=citations,
            synthesis_rows=synthesis_bullets,
            bullet_citation_rows=bullet_citations,
            run_row=run_row,
            budget_ledger_rows=run_summary.get("budget_ledger_rows", []),
            relevance_flag_rows=portfolio_relevance,
        )

    return persist_daily_brief_runtime(
        base_dir=base_dir,
        generated_at_utc=generated_at_utc,
        report_date=report_date,
        query_text="",
        source_rows=[],
        documents=[],
        chunks=[],
        evidence_pack_items=[],
        evidence_pack_report={"diversity_stats": {}},
        issue_map_rows=[],
        structured_claim_rows=[],
        citation_rows=[],
        synthesis_rows=[],
        bullet_citation_rows=[],
        run_row=run_row,
        budget_ledger_rows=pipeline_result.get("budget_ledger_rows", []),
    )


def _provider_summary(*, provider_resolution: Mapping[str, Any] | None) -> dict[str, Any]:
    if isinstance(provider_resolution, Mapping):
        return {
            "requested_provider": provider_resolution.get("requested_provider"),
            "resolved_provider": provider_resolution.get("resolved_provider"),
            "provider_mode": provider_resolution.get("provider_mode"),
            "provider_fallback_used": bool(provider_resolution.get("provider_fallback_used", False)),
        }
    return {
        "requested_provider": None,
        "resolved_provider": None,
        "provider_mode": None,
        "provider_fallback_used": False,
    }


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
