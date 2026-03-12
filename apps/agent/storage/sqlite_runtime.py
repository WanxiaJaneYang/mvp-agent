from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from apps.agent.pipeline.identifiers import build_citation_id, build_pack_id


def runtime_db_path(*, base_dir: Path) -> Path:
    runtime_dir = base_dir / "artifacts" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return runtime_dir / "agent_runtime.sqlite3"


def ensure_runtime_db(*, base_dir: Path) -> Path:
    db_path = runtime_db_path(base_dir=base_dir)
    connection = sqlite3.connect(db_path)
    try:
        _initialize_schema(connection)
        connection.commit()
    finally:
        connection.close()
    return db_path


def persist_daily_brief_runtime(
    *,
    base_dir: Path,
    generated_at_utc: str,
    report_date: str,
    query_text: str,
    source_rows: Iterable[Mapping[str, Any]],
    documents: Iterable[Mapping[str, Any]],
    chunks: Iterable[Mapping[str, Any]],
    evidence_pack_items: Iterable[Mapping[str, Any]],
    evidence_pack_report: Mapping[str, Any],
    issue_map_rows: Iterable[Mapping[str, Any]],
    structured_claim_rows: Iterable[Mapping[str, Any]],
    citation_rows: Iterable[Mapping[str, Any]],
    synthesis_rows: Iterable[Mapping[str, Any]],
    bullet_citation_rows: Iterable[Mapping[str, Any]],
    run_row: Mapping[str, Any],
    budget_ledger_rows: Iterable[Mapping[str, Any]],
    relevance_flag_rows: Iterable[Mapping[str, Any]] = (),
) -> Path:
    db_path = ensure_runtime_db(base_dir=base_dir)
    connection = sqlite3.connect(db_path)
    try:
        connection.row_factory = sqlite3.Row

        source_rows_list = [dict(row) for row in source_rows]
        document_rows_list = [dict(row) for row in documents]
        chunk_rows_list = [dict(row) for row in chunks]
        evidence_pack_rows_list = [dict(row) for row in evidence_pack_items]
        issue_map_rows_list = [dict(row) for row in issue_map_rows]
        structured_claim_rows_list = [dict(row) for row in structured_claim_rows]
        citation_rows_list = [dict(row) for row in citation_rows]
        synthesis_rows_list = [dict(row) for row in synthesis_rows]
        bullet_citation_rows_list = [dict(row) for row in bullet_citation_rows]
        budget_ledger_rows_list = [dict(row) for row in budget_ledger_rows]
        relevance_flag_rows_list = [dict(row) for row in relevance_flag_rows]

        pack_id = build_pack_id(run_id=str(run_row["run_id"]), query_text=query_text)
        synthesis_id = str(synthesis_rows_list[0]["synthesis_id"]) if synthesis_rows_list else None
        _persist_run(connection, row=dict(run_row))
        _persist_sources(connection, rows=source_rows_list)
        _persist_documents(connection, rows=document_rows_list)
        _persist_chunks(connection, rows=chunk_rows_list)
        _persist_evidence_pack(
            connection,
            pack_id=pack_id,
            query_text=query_text,
            generated_at_utc=generated_at_utc,
            stats=evidence_pack_report.get("diversity_stats", {}),
        )
        _persist_evidence_pack_items(connection, pack_id=pack_id, rows=evidence_pack_rows_list)
        _persist_issue_maps(
            connection,
            run_id=str(run_row["run_id"]),
            generated_at_utc=generated_at_utc,
            rows=issue_map_rows_list,
        )
        _persist_structured_claims(
            connection,
            run_id=str(run_row["run_id"]),
            generated_at_utc=generated_at_utc,
            rows=structured_claim_rows_list,
        )
        persisted_citation_ids = _persist_citations(
            connection,
            rows=citation_rows_list,
            valid_doc_ids={str(row["doc_id"]) for row in document_rows_list},
            valid_chunk_ids={str(row["chunk_id"]) for row in chunk_rows_list},
        )
        _persist_synthesis(
            connection,
            rows=synthesis_rows_list,
            run_row=run_row,
            report_date=report_date,
            generated_at_utc=generated_at_utc,
            pack_id=pack_id,
        )
        _persist_bullet_citations(
            connection,
            rows=bullet_citation_rows_list,
            citation_id_map=persisted_citation_ids,
        )
        _persist_budget_ledger(connection, rows=budget_ledger_rows_list)
        _persist_relevance_flags(
            connection,
            synthesis_id=synthesis_id,
            rows=relevance_flag_rows_list,
        )
        connection.commit()
    finally:
        connection.close()
    return db_path


def persist_alert_record(
    *,
    base_dir: Path,
    row: Mapping[str, Any],
) -> Path:
    db_path = ensure_runtime_db(base_dir=base_dir)
    connection = sqlite3.connect(db_path)
    try:
        _persist_alerts(connection, rows=[dict(row)])
        connection.commit()
    finally:
        connection.close()
    return db_path


def _initialize_schema(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = ON")
    statements = (
        """
        CREATE TABLE IF NOT EXISTS sources (
          source_id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          base_url TEXT NOT NULL,
          source_type TEXT NOT NULL,
          credibility_tier INTEGER NOT NULL,
          paywall_policy TEXT NOT NULL,
          fetch_interval TEXT NOT NULL,
          tags_json TEXT NOT NULL,
          enabled INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS documents (
          doc_id TEXT PRIMARY KEY,
          source_id TEXT NOT NULL REFERENCES sources(source_id),
          publisher TEXT NOT NULL,
          canonical_url TEXT NOT NULL,
          title TEXT,
          author TEXT,
          language TEXT,
          doc_type TEXT,
          published_at TEXT,
          fetched_at TEXT NOT NULL,
          paywall_policy TEXT NOT NULL,
          metadata_only INTEGER NOT NULL,
          rss_snippet TEXT,
          body_text TEXT,
          content_hash TEXT NOT NULL,
          ingestion_run_id TEXT REFERENCES runs(run_id),
          status TEXT NOT NULL DEFAULT 'active',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          UNIQUE(canonical_url),
          UNIQUE(content_hash)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS chunks (
          chunk_id TEXT PRIMARY KEY,
          doc_id TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
          chunk_index INTEGER NOT NULL,
          text TEXT NOT NULL,
          token_count INTEGER,
          char_start INTEGER,
          char_end INTEGER,
          embedding_model TEXT,
          embedding_vector BLOB,
          created_at TEXT NOT NULL,
          UNIQUE(doc_id, chunk_index)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS evidence_packs (
          pack_id TEXT PRIMARY KEY,
          purpose TEXT NOT NULL,
          query_text TEXT NOT NULL,
          generated_at TEXT NOT NULL,
          unique_publishers INTEGER NOT NULL,
          tier_1_pct REAL NOT NULL,
          tier_2_pct REAL NOT NULL,
          tier_3_pct REAL NOT NULL,
          tier_4_pct REAL NOT NULL,
          max_publisher_pct REAL NOT NULL,
          created_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS evidence_pack_items (
          pack_id TEXT NOT NULL REFERENCES evidence_packs(pack_id) ON DELETE CASCADE,
          chunk_id TEXT NOT NULL REFERENCES chunks(chunk_id),
          source_id TEXT NOT NULL REFERENCES sources(source_id),
          publisher TEXT NOT NULL,
          credibility_tier INTEGER NOT NULL,
          retrieval_score REAL NOT NULL,
          semantic_score REAL,
          recency_score REAL,
          credibility_score REAL,
          rank_in_pack INTEGER NOT NULL,
          PRIMARY KEY (pack_id, chunk_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS syntheses (
          synthesis_id TEXT PRIMARY KEY,
          kind TEXT NOT NULL,
          run_id TEXT REFERENCES runs(run_id),
          pack_id TEXT REFERENCES evidence_packs(pack_id),
          scheduled_for_local_date TEXT,
          generated_at TEXT NOT NULL,
          validation_passed INTEGER NOT NULL,
          removed_bullets_count INTEGER NOT NULL DEFAULT 0,
          retry_count INTEGER NOT NULL DEFAULT 0,
          status TEXT NOT NULL,
          created_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS issue_maps (
          run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
          issue_id TEXT NOT NULL,
          issue_question TEXT NOT NULL,
          thesis_hint TEXT NOT NULL,
          supporting_evidence_ids_json TEXT NOT NULL,
          opposing_evidence_ids_json TEXT NOT NULL,
          minority_evidence_ids_json TEXT NOT NULL,
          watch_evidence_ids_json TEXT NOT NULL,
          generated_at TEXT NOT NULL,
          PRIMARY KEY (run_id, issue_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS structured_claims (
          run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
          claim_id TEXT NOT NULL,
          issue_id TEXT NOT NULL,
          claim_kind TEXT NOT NULL,
          claim_text TEXT NOT NULL,
          supporting_citation_ids_json TEXT NOT NULL,
          opposing_citation_ids_json TEXT NOT NULL,
          confidence TEXT NOT NULL,
          novelty_vs_prior_brief TEXT NOT NULL,
          why_it_matters TEXT NOT NULL,
          generated_at TEXT NOT NULL,
          PRIMARY KEY (run_id, claim_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS synthesis_bullets (
          synthesis_id TEXT NOT NULL REFERENCES syntheses(synthesis_id) ON DELETE CASCADE,
          section TEXT NOT NULL,
          bullet_index INTEGER NOT NULL,
          text TEXT NOT NULL,
          claim_span_count INTEGER NOT NULL DEFAULT 1,
          is_abstain INTEGER NOT NULL DEFAULT 0,
          confidence_label TEXT,
          PRIMARY KEY (synthesis_id, section, bullet_index)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS citations (
          citation_id TEXT PRIMARY KEY,
          source_id TEXT NOT NULL REFERENCES sources(source_id),
          publisher TEXT NOT NULL,
          doc_id TEXT NOT NULL REFERENCES documents(doc_id),
          chunk_id TEXT REFERENCES chunks(chunk_id),
          url TEXT NOT NULL,
          title TEXT,
          published_at TEXT,
          fetched_at TEXT,
          quote_start INTEGER,
          quote_end INTEGER,
          quote_text TEXT,
          snippet_text TEXT,
          created_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS bullet_citations (
          synthesis_id TEXT NOT NULL,
          section TEXT NOT NULL,
          bullet_index INTEGER NOT NULL,
          claim_span_index INTEGER NOT NULL DEFAULT 0,
          citation_id TEXT NOT NULL REFERENCES citations(citation_id) ON DELETE CASCADE,
          PRIMARY KEY (synthesis_id, section, bullet_index, claim_span_index, citation_id),
          FOREIGN KEY (synthesis_id, section, bullet_index)
            REFERENCES synthesis_bullets(synthesis_id, section, bullet_index)
            ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS runs (
          run_id TEXT PRIMARY KEY,
          run_type TEXT NOT NULL,
          started_at TEXT NOT NULL,
          ended_at TEXT,
          status TEXT NOT NULL,
          docs_fetched INTEGER NOT NULL DEFAULT 0,
          docs_ingested INTEGER NOT NULL DEFAULT 0,
          chunks_indexed INTEGER NOT NULL DEFAULT 0,
          tool_calls INTEGER NOT NULL DEFAULT 0,
          pages_fetched INTEGER NOT NULL DEFAULT 0,
          model_input_tokens INTEGER NOT NULL DEFAULT 0,
          model_output_tokens INTEGER NOT NULL DEFAULT 0,
          estimated_cost_usd REAL NOT NULL DEFAULT 0,
          error_summary TEXT,
          created_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS budget_ledger (
          ledger_id TEXT PRIMARY KEY,
          run_id TEXT REFERENCES runs(run_id),
          recorded_at TEXT NOT NULL,
          window_type TEXT NOT NULL,
          window_start TEXT NOT NULL,
          window_end TEXT NOT NULL,
          cost_usd REAL NOT NULL,
          cap_usd REAL NOT NULL,
          exceeded INTEGER NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS portfolio_positions (
          position_id TEXT PRIMARY KEY,
          ticker TEXT NOT NULL,
          weight_pct REAL NOT NULL,
          asset_type TEXT DEFAULT 'equity',
          notes TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          UNIQUE(ticker)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS relevance_flags (
          relevance_id TEXT PRIMARY KEY,
          synthesis_id TEXT NOT NULL REFERENCES syntheses(synthesis_id) ON DELETE CASCADE,
          ticker TEXT NOT NULL,
          relevance_score REAL NOT NULL,
          risk_flag TEXT NOT NULL,
          rationale TEXT,
          created_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS alerts (
          alert_id TEXT PRIMARY KEY,
          run_id TEXT NOT NULL,
          category TEXT NOT NULL,
          title TEXT NOT NULL,
          summary TEXT NOT NULL,
          action TEXT NOT NULL,
          delivery_status TEXT NOT NULL,
          score_total REAL NOT NULL,
          score_importance REAL NOT NULL,
          score_evidence REAL NOT NULL,
          score_confidence REAL NOT NULL,
          score_relevance REAL NOT NULL,
          score_noise_risk REAL NOT NULL,
          triggered_at TEXT NOT NULL,
          delivered_email_at TEXT,
          delivered_local_page_at TEXT,
          bundle_for_daily_brief INTEGER NOT NULL DEFAULT 0,
          suppression_reason TEXT,
          failure_reason TEXT,
          html_path TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
        """,
    )
    for statement in statements:
        connection.execute(statement)


def _persist_sources(connection: sqlite3.Connection, *, rows: list[dict[str, Any]]) -> None:
    connection.executemany(
        """
        INSERT INTO sources (
          source_id, name, base_url, source_type, credibility_tier, paywall_policy,
          fetch_interval, tags_json, enabled, created_at, updated_at
        ) VALUES (
          :source_id, :name, :base_url, :source_type, :credibility_tier, :paywall_policy,
          :fetch_interval, :tags_json, :enabled, :created_at, :updated_at
        )
        ON CONFLICT(source_id) DO UPDATE SET
          name=excluded.name,
          base_url=excluded.base_url,
          source_type=excluded.source_type,
          credibility_tier=excluded.credibility_tier,
          paywall_policy=excluded.paywall_policy,
          fetch_interval=excluded.fetch_interval,
          tags_json=excluded.tags_json,
          enabled=excluded.enabled,
          updated_at=excluded.updated_at
        """,
        rows,
    )


def _persist_documents(connection: sqlite3.Connection, *, rows: list[dict[str, Any]]) -> None:
    connection.executemany(
        """
        INSERT INTO documents (
          doc_id, source_id, publisher, canonical_url, title, author, language, doc_type,
          published_at, fetched_at, paywall_policy, metadata_only, rss_snippet, body_text,
          content_hash, ingestion_run_id, status, created_at, updated_at
        ) VALUES (
          :doc_id, :source_id, :publisher, :canonical_url, :title, :author, :language, :doc_type,
          :published_at, :fetched_at, :paywall_policy, :metadata_only, :rss_snippet, :body_text,
          :content_hash, :ingestion_run_id, :status, :created_at, :updated_at
        )
        ON CONFLICT(doc_id) DO UPDATE SET
          source_id=excluded.source_id,
          publisher=excluded.publisher,
          canonical_url=excluded.canonical_url,
          title=excluded.title,
          author=excluded.author,
          language=excluded.language,
          doc_type=excluded.doc_type,
          published_at=excluded.published_at,
          fetched_at=excluded.fetched_at,
          paywall_policy=excluded.paywall_policy,
          metadata_only=excluded.metadata_only,
          rss_snippet=excluded.rss_snippet,
          body_text=excluded.body_text,
          content_hash=excluded.content_hash,
          ingestion_run_id=excluded.ingestion_run_id,
          status=excluded.status,
          updated_at=excluded.updated_at
        """,
        rows,
    )


def _persist_chunks(connection: sqlite3.Connection, *, rows: list[dict[str, Any]]) -> None:
    connection.executemany(
        """
        INSERT INTO chunks (
          chunk_id, doc_id, chunk_index, text, token_count, char_start, char_end,
          embedding_model, embedding_vector, created_at
        ) VALUES (
          :chunk_id, :doc_id, :chunk_index, :text, :token_count, :char_start, :char_end,
          NULL, NULL, :created_at
        )
        ON CONFLICT(chunk_id) DO UPDATE SET
          doc_id=excluded.doc_id,
          chunk_index=excluded.chunk_index,
          text=excluded.text,
          token_count=excluded.token_count,
          char_start=excluded.char_start,
          char_end=excluded.char_end,
          created_at=excluded.created_at
        """,
        rows,
    )


def _persist_evidence_pack(
    connection: sqlite3.Connection,
    *,
    pack_id: str,
    query_text: str,
    generated_at_utc: str,
    stats: Mapping[str, Any],
) -> None:
    connection.execute(
        """
        INSERT INTO evidence_packs (
          pack_id, purpose, query_text, generated_at, unique_publishers,
          tier_1_pct, tier_2_pct, tier_3_pct, tier_4_pct, max_publisher_pct, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(pack_id) DO UPDATE SET
          query_text=excluded.query_text,
          generated_at=excluded.generated_at,
          unique_publishers=excluded.unique_publishers,
          tier_1_pct=excluded.tier_1_pct,
          tier_2_pct=excluded.tier_2_pct,
          tier_3_pct=excluded.tier_3_pct,
          tier_4_pct=excluded.tier_4_pct,
          max_publisher_pct=excluded.max_publisher_pct
        """,
        (
            pack_id,
            "daily_brief",
            query_text,
            generated_at_utc,
            int(stats.get("unique_publishers", 0)),
            float(stats.get("tier_1_pct", 0.0)),
            float(stats.get("tier_2_pct", 0.0)),
            float(stats.get("tier_3_pct", 0.0)),
            float(stats.get("tier_4_pct", 0.0)),
            float(stats.get("max_publisher_pct", 0.0)),
            generated_at_utc,
        ),
    )


def _persist_evidence_pack_items(
    connection: sqlite3.Connection,
    *,
    pack_id: str,
    rows: list[dict[str, Any]],
) -> None:
    connection.execute("DELETE FROM evidence_pack_items WHERE pack_id = ?", (pack_id,))
    for row in rows:
        connection.execute(
            """
            INSERT INTO evidence_pack_items (
              pack_id, chunk_id, source_id, publisher, credibility_tier, retrieval_score,
              semantic_score, recency_score, credibility_score, rank_in_pack
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pack_id,
                row["chunk_id"],
                row["source_id"],
                row["publisher"],
                row["credibility_tier"],
                row["retrieval_score"],
                row.get("semantic_score"),
                row.get("recency_score"),
                row.get("credibility_score"),
                row["rank_in_pack"],
            ),
        )


def _persist_citations(
    connection: sqlite3.Connection,
    *,
    rows: list[dict[str, Any]],
    valid_doc_ids: set[str],
    valid_chunk_ids: set[str],
) -> dict[str, str]:
    persisted_ids: dict[str, str] = {}
    for row in rows:
        doc_id = str(row["doc_id"])
        chunk_id = str(row["chunk_id"])
        if doc_id not in valid_doc_ids or chunk_id not in valid_chunk_ids:
            continue
        persisted_id = build_citation_id(
            source_id=str(row["source_id"]),
            doc_id=doc_id,
            chunk_id=chunk_id,
            url=str(row["url"]),
        )
        persisted_ids[str(row["citation_id"])] = persisted_id
        connection.execute(
            """
            INSERT INTO citations (
              citation_id, source_id, publisher, doc_id, chunk_id, url, title, published_at,
              fetched_at, quote_start, quote_end, quote_text, snippet_text, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?, ?)
            ON CONFLICT(citation_id) DO UPDATE SET
              source_id=excluded.source_id,
              publisher=excluded.publisher,
              doc_id=excluded.doc_id,
              chunk_id=excluded.chunk_id,
              url=excluded.url,
              title=excluded.title,
              published_at=excluded.published_at,
              fetched_at=excluded.fetched_at,
              quote_text=excluded.quote_text,
              snippet_text=excluded.snippet_text
            """,
            (
                persisted_id,
                row["source_id"],
                row["publisher"],
                doc_id,
                chunk_id,
                row["url"],
                row.get("title"),
                row.get("published_at"),
                row.get("fetched_at"),
                row.get("quote_text"),
                row.get("snippet_text"),
                row.get("fetched_at") or row.get("published_at") or "",
            ),
        )
    return persisted_ids


def _persist_synthesis(
    connection: sqlite3.Connection,
    *,
    rows: list[dict[str, Any]],
    run_row: Mapping[str, Any],
    report_date: str,
    generated_at_utc: str,
    pack_id: str,
) -> None:
    if not rows:
        return

    synthesis_id = str(rows[0]["synthesis_id"])
    removed_bullets = 0
    retry_count = 0
    validation_passed = 1 if str(run_row["status"]) == "ok" else 0
    connection.execute(
        """
        INSERT INTO syntheses (
          synthesis_id, kind, run_id, pack_id, scheduled_for_local_date, generated_at,
          validation_passed, removed_bullets_count, retry_count, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(synthesis_id) DO UPDATE SET
          run_id=excluded.run_id,
          pack_id=excluded.pack_id,
          scheduled_for_local_date=excluded.scheduled_for_local_date,
          generated_at=excluded.generated_at,
          validation_passed=excluded.validation_passed,
          removed_bullets_count=excluded.removed_bullets_count,
          retry_count=excluded.retry_count,
          status=excluded.status
        """,
        (
            synthesis_id,
            "daily_brief",
            run_row["run_id"],
            pack_id,
            report_date,
            generated_at_utc,
            validation_passed,
            removed_bullets,
            retry_count,
            run_row["status"],
            generated_at_utc,
        ),
    )
    connection.executemany(
        """
        INSERT INTO synthesis_bullets (
          synthesis_id, section, bullet_index, text, claim_span_count, is_abstain, confidence_label
        ) VALUES (
          :synthesis_id, :section, :bullet_index, :text, :claim_span_count, :is_abstain, :confidence_label
        )
        ON CONFLICT(synthesis_id, section, bullet_index) DO UPDATE SET
          text=excluded.text,
          claim_span_count=excluded.claim_span_count,
          is_abstain=excluded.is_abstain,
          confidence_label=excluded.confidence_label
        """,
        rows,
    )


def _persist_issue_maps(
    connection: sqlite3.Connection,
    *,
    run_id: str,
    generated_at_utc: str,
    rows: list[dict[str, Any]],
) -> None:
    connection.execute("DELETE FROM issue_maps WHERE run_id = ?", (run_id,))
    if not rows:
        return
    payload_rows = [
        {
            "run_id": run_id,
            "issue_id": str(row["issue_id"]),
            "issue_question": str(row.get("issue_question") or ""),
            "thesis_hint": str(row.get("thesis_hint") or ""),
            "supporting_evidence_ids_json": json.dumps(list(row.get("supporting_evidence_ids", []))),
            "opposing_evidence_ids_json": json.dumps(list(row.get("opposing_evidence_ids", []))),
            "minority_evidence_ids_json": json.dumps(list(row.get("minority_evidence_ids", []))),
            "watch_evidence_ids_json": json.dumps(list(row.get("watch_evidence_ids", []))),
            "generated_at": generated_at_utc,
        }
        for row in rows
    ]
    connection.executemany(
        """
        INSERT INTO issue_maps (
          run_id, issue_id, issue_question, thesis_hint,
          supporting_evidence_ids_json, opposing_evidence_ids_json,
          minority_evidence_ids_json, watch_evidence_ids_json, generated_at
        ) VALUES (
          :run_id, :issue_id, :issue_question, :thesis_hint,
          :supporting_evidence_ids_json, :opposing_evidence_ids_json,
          :minority_evidence_ids_json, :watch_evidence_ids_json, :generated_at
        )
        ON CONFLICT(run_id, issue_id) DO UPDATE SET
          issue_question=excluded.issue_question,
          thesis_hint=excluded.thesis_hint,
          supporting_evidence_ids_json=excluded.supporting_evidence_ids_json,
          opposing_evidence_ids_json=excluded.opposing_evidence_ids_json,
          minority_evidence_ids_json=excluded.minority_evidence_ids_json,
          watch_evidence_ids_json=excluded.watch_evidence_ids_json,
          generated_at=excluded.generated_at
        """,
        payload_rows,
    )


def _persist_structured_claims(
    connection: sqlite3.Connection,
    *,
    run_id: str,
    generated_at_utc: str,
    rows: list[dict[str, Any]],
) -> None:
    connection.execute("DELETE FROM structured_claims WHERE run_id = ?", (run_id,))
    if not rows:
        return
    payload_rows = [
        {
            "run_id": run_id,
            "claim_id": str(row["claim_id"]),
            "issue_id": str(row.get("issue_id") or ""),
            "claim_kind": str(row.get("claim_kind") or ""),
            "claim_text": str(row.get("claim_text") or ""),
            "supporting_citation_ids_json": json.dumps(list(row.get("supporting_citation_ids", []))),
            "opposing_citation_ids_json": json.dumps(list(row.get("opposing_citation_ids", []))),
            "confidence": str(row.get("confidence") or ""),
            "novelty_vs_prior_brief": str(row.get("novelty_vs_prior_brief") or "unknown"),
            "why_it_matters": str(row.get("why_it_matters") or ""),
            "generated_at": generated_at_utc,
        }
        for row in rows
    ]
    connection.executemany(
        """
        INSERT INTO structured_claims (
          run_id, claim_id, issue_id, claim_kind, claim_text,
          supporting_citation_ids_json, opposing_citation_ids_json,
          confidence, novelty_vs_prior_brief, why_it_matters, generated_at
        ) VALUES (
          :run_id, :claim_id, :issue_id, :claim_kind, :claim_text,
          :supporting_citation_ids_json, :opposing_citation_ids_json,
          :confidence, :novelty_vs_prior_brief, :why_it_matters, :generated_at
        )
        ON CONFLICT(run_id, claim_id) DO UPDATE SET
          issue_id=excluded.issue_id,
          claim_kind=excluded.claim_kind,
          claim_text=excluded.claim_text,
          supporting_citation_ids_json=excluded.supporting_citation_ids_json,
          opposing_citation_ids_json=excluded.opposing_citation_ids_json,
          confidence=excluded.confidence,
          novelty_vs_prior_brief=excluded.novelty_vs_prior_brief,
          why_it_matters=excluded.why_it_matters,
          generated_at=excluded.generated_at
        """,
        payload_rows,
    )


def _persist_bullet_citations(
    connection: sqlite3.Connection,
    *,
    rows: list[dict[str, Any]],
    citation_id_map: Mapping[str, str],
) -> None:
    for row in rows:
        persisted_citation_id = citation_id_map.get(str(row["citation_id"]))
        if persisted_citation_id is None:
            continue
        connection.execute(
            """
            INSERT OR REPLACE INTO bullet_citations (
              synthesis_id, section, bullet_index, claim_span_index, citation_id
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                row["synthesis_id"],
                row["section"],
                row["bullet_index"],
                row["claim_span_index"],
                persisted_citation_id,
            ),
        )


def _persist_run(connection: sqlite3.Connection, *, row: dict[str, Any]) -> None:
    connection.execute(
        """
        INSERT INTO runs (
          run_id, run_type, started_at, ended_at, status, docs_fetched, docs_ingested,
          chunks_indexed, tool_calls, pages_fetched, model_input_tokens, model_output_tokens,
          estimated_cost_usd, error_summary, created_at
        ) VALUES (
          :run_id, :run_type, :started_at, :ended_at, :status, :docs_fetched, :docs_ingested,
          :chunks_indexed, :tool_calls, :pages_fetched, :model_input_tokens, :model_output_tokens,
          :estimated_cost_usd, :error_summary, :created_at
        )
        ON CONFLICT(run_id) DO UPDATE SET
          ended_at=excluded.ended_at,
          status=excluded.status,
          docs_fetched=excluded.docs_fetched,
          docs_ingested=excluded.docs_ingested,
          chunks_indexed=excluded.chunks_indexed,
          tool_calls=excluded.tool_calls,
          pages_fetched=excluded.pages_fetched,
          model_input_tokens=excluded.model_input_tokens,
          model_output_tokens=excluded.model_output_tokens,
          estimated_cost_usd=excluded.estimated_cost_usd,
          error_summary=excluded.error_summary
        """,
        row,
    )


def _persist_budget_ledger(connection: sqlite3.Connection, *, rows: list[dict[str, Any]]) -> None:
    connection.executemany(
        """
        INSERT INTO budget_ledger (
          ledger_id, run_id, recorded_at, window_type, window_start, window_end, cost_usd, cap_usd, exceeded
        ) VALUES (
          :ledger_id, :run_id, :recorded_at, :window_type, :window_start, :window_end, :cost_usd, :cap_usd, :exceeded
        )
        ON CONFLICT(ledger_id) DO UPDATE SET
          cost_usd=excluded.cost_usd,
          cap_usd=excluded.cap_usd,
          exceeded=excluded.exceeded
        """,
        rows,
    )


def _persist_relevance_flags(
    connection: sqlite3.Connection,
    *,
    synthesis_id: str | None,
    rows: list[dict[str, Any]],
) -> None:
    if synthesis_id is not None:
        connection.execute("DELETE FROM relevance_flags WHERE synthesis_id = ?", (synthesis_id,))
    if not rows:
        return
    connection.executemany(
        """
        INSERT INTO relevance_flags (
          relevance_id, synthesis_id, ticker, relevance_score, risk_flag, rationale, created_at
        ) VALUES (
          :relevance_id, :synthesis_id, :ticker, :relevance_score, :risk_flag, :rationale, :created_at
        )
        ON CONFLICT(relevance_id) DO UPDATE SET
          ticker=excluded.ticker,
          relevance_score=excluded.relevance_score,
          risk_flag=excluded.risk_flag,
          rationale=excluded.rationale,
          created_at=excluded.created_at
        """,
        rows,
    )


def _persist_alerts(connection: sqlite3.Connection, *, rows: list[dict[str, Any]]) -> None:
    connection.executemany(
        """
        INSERT INTO alerts (
          alert_id, run_id, category, title, summary, action, delivery_status,
          score_total, score_importance, score_evidence, score_confidence,
          score_relevance, score_noise_risk, triggered_at, delivered_email_at,
          delivered_local_page_at, bundle_for_daily_brief, suppression_reason,
          failure_reason, html_path, created_at, updated_at
        ) VALUES (
          :alert_id, :run_id, :category, :title, :summary, :action, :delivery_status,
          :score_total, :score_importance, :score_evidence, :score_confidence,
          :score_relevance, :score_noise_risk, :triggered_at, :delivered_email_at,
          :delivered_local_page_at, :bundle_for_daily_brief, :suppression_reason,
          :failure_reason, :html_path, :created_at, :updated_at
        )
        ON CONFLICT(alert_id) DO UPDATE SET
          run_id=excluded.run_id,
          category=excluded.category,
          title=excluded.title,
          summary=excluded.summary,
          action=excluded.action,
          delivery_status=excluded.delivery_status,
          score_total=excluded.score_total,
          score_importance=excluded.score_importance,
          score_evidence=excluded.score_evidence,
          score_confidence=excluded.score_confidence,
          score_relevance=excluded.score_relevance,
          score_noise_risk=excluded.score_noise_risk,
          triggered_at=excluded.triggered_at,
          delivered_email_at=excluded.delivered_email_at,
          delivered_local_page_at=excluded.delivered_local_page_at,
          bundle_for_daily_brief=excluded.bundle_for_daily_brief,
          suppression_reason=excluded.suppression_reason,
          failure_reason=excluded.failure_reason,
          html_path=excluded.html_path,
          updated_at=excluded.updated_at
        """,
        rows,
    )
