import re
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit, urlunsplit

from flask import current_app
from sqlalchemy import or_

from db import db
from models import PotholeResearchRun, PotholeResearchSource, utcnow
from services.ollama_client import OllamaClient, OllamaError
from services.page_fetcher import FetchError, SafePageFetcher
from services.research_target import (
    build_research_key,
    build_target,
    normalize_key,
    normalize_text,
    road_aliases,
    road_match_aliases,
)
from services.search_provider import SearchError, SearXNGProvider

ROAD_CONTEXT_TERMS = (
    "road",
    "rd",
    "street",
    "st",
    "lane",
    "marg",
    "highway",
    "path",
    "bypass",
    "avenue",
)
WORK_TERMS = (
    "contractor",
    "awarded",
    "award",
    "tender",
    "work order",
    "budget work",
    "village roads",
    "improvements",
    "agreement",
    "executed",
    "maintenance",
    "resurfacing",
    "repair",
    "bidder",
    "selected",
    "sanction",
    "estimate",
    "road work",
)
GENERIC_NAME_TOKENS = {
    "ltd",
    "limited",
    "pvt",
    "private",
    "company",
    "co",
    "contractor",
    "and",
    "the",
}
SECONDARY_DOMAINS = {
    "thehindu.com",
    "indianexpress.com",
    "mathrubhumi.com",
    "manoramaonline.com",
    "onmanorama.com",
    "newindianexpress.com",
    "deccanherald.com",
    "timesofindia.indiatimes.com",
    "ndtv.com",
}
NO_MATCH_REASON = "No source-backed road work record found."
TENDER_AGGREGATOR_DOMAINS = {
    "gittigo.com",
    "tendershark.com",
    "tenderdetail.com",
    "indiantenders.in",
    "tenderimpulse.com",
    "tendersontime.com",
    "firsttender.com",
    "asiantender.com",
    "infralens.in",
}


def _quote_term(value):
    return '"' + normalize_text(value).replace('"', "") + '"'


def _official_domains(target):
    state_key = normalize_key(target.state)
    if state_key == "kerala":
        return [
            "kerala.gov.in",
            "pwd.kerala.gov.in",
            "etenders.kerala.gov.in",
            "gov.in",
        ]
    return ["gov.in", "nic.in"]


def generate_queries(target, max_queries=12):
    aliases = road_aliases(target)
    if not aliases:
        return []
    road = _quote_term(aliases[0])
    base = _quote_term(aliases[1]) if len(aliases) > 1 else road
    locality = _quote_term(target.locality) if target.locality else ""
    district = _quote_term(target.district) if target.district else ""
    state = _quote_term(target.state) if target.state else ""
    municipality = (
        _quote_term(target.municipality) if target.municipality else ""
    )
    authority = _quote_term(target.authority) if target.authority else ""
    place = " ".join(part for part in (locality, district, state) if part)
    queries = [
        "{0} {1} contractor".format(road, place).strip(),
        "{0} {1} tender".format(road, place).strip(),
        "{0} {1} road work".format(road, place).strip(),
    ]
    if base and base != road and locality:
        queries.append("{0} {1} tender".format(base, locality).strip())
    for domain in _official_domains(target):
        queries.append(
            "site:{0} {1} {2}".format(domain, road, locality or district).strip()
        )
    if target.pincode:
        queries.append(
            "{0} {1} tender".format(road, target.pincode).strip()
        )
    if municipality:
        queries.append(
            "{0} {1} tender".format(road, municipality).strip()
        )
    if authority:
        queries.append("{0} {1} work".format(road, authority).strip())
    if district:
        queries.append(
            "{0} {1} government tender".format(road, district).strip()
        )
    if state:
        queries.append("{0} {1} PWD tender".format(road, state).strip())
    queries.append(
        "site:gov.in {0} {1} contractor".format(road, locality or district).strip()
    )
    seen = set()
    result = []
    for query in queries:
        key = normalize_key(query)
        if key and key not in seen:
            seen.add(key)
            result.append(query)
        if len(result) >= max_queries:
            break
    return result

def _domain_of(url):
    try:
        host = (urlsplit(url).hostname or "").lower().rstrip(".")
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


def _tier_for_domain(domain):
    if not domain:
        return 4
    if (
        domain == "gov.in"
        or domain.endswith(".gov.in")
        or domain == "nic.in"
        or domain.endswith(".nic.in")
        or domain == "gov"
        or domain.endswith(".gov")
    ):
        return 1
    if domain.endswith(".ac.in") or domain.endswith(".edu.in") or domain.endswith(".res.in"):
        return 2
    if domain in SECONDARY_DOMAINS or any(
        domain.endswith("." + candidate) for candidate in SECONDARY_DOMAINS
    ):
        return 3
    if domain in TENDER_AGGREGATOR_DOMAINS or any(
        domain.endswith("." + candidate) for candidate in TENDER_AGGREGATOR_DOMAINS
    ):
        return 3
    return 4


def normalize_url(url):
    try:
        parsed = urlsplit((url or "").strip())
    except ValueError:
        return ""
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return ""
    host = parsed.hostname.lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), host, path, parsed.query, ""))


def _dedupe_candidates(hits, target):
    candidates = []
    seen = set()
    for hit in hits:
        url = normalize_url(hit.url)
        if not url or url in seen:
            continue
        seen.add(url)
        domain = _domain_of(url)
        candidates.append(
            {
                "hit": hit,
                "url": url,
                "domain": domain,
                "tier": _tier_for_domain(domain),
            }
        )

    def rank_key(item):
        hit = item["hit"]
        text = "{0} {1}".format(hit.title, hit.snippet)
        road = _road_name_mentioned(text, target)
        work = _has_work_term(text)
        location = _has_strong_location(text, target)
        if road and work and location:
            relevance = 0
        elif road and work:
            relevance = 1
        elif road and location:
            relevance = 2
        elif road:
            relevance = 3
        else:
            relevance = 4
        return (relevance, item["tier"], hit.rank, -hit.score)

    candidates.sort(key=rank_key)
    return candidates


def _contains(text, phrase):
    normalized_phrase = normalize_key(phrase)
    if not normalized_phrase:
        return False
    return normalized_phrase in normalize_key(text)


def _is_tender_aggregator(domain):
    return bool(
        domain
        and (
            domain in TENDER_AGGREGATOR_DOMAINS
            or any(
                domain.endswith("." + candidate)
                for candidate in TENDER_AGGREGATOR_DOMAINS
            )
        )
    )


def _road_name_mentioned(text, target):
    normalized_text = normalize_key(text)
    if not normalized_text:
        return False
    full = normalize_key(target.road_name)
    if full and full in normalized_text:
        return True
    return any(
        normalize_key(alias) in normalized_text
        for alias in road_match_aliases(target)
        if normalize_key(alias)
    )


def _has_road_context(text):
    padded = " {0} ".format(normalize_key(text))
    return any(" {0} ".format(term) in padded for term in ROAD_CONTEXT_TERMS)


def _has_strong_location(text, target):
    normalized_text = normalize_key(text)
    if not normalized_text:
        return False
    for value in (
        target.locality,
        target.district,
        target.pincode,
        target.municipality,
        target.administrative_area,
        target.suburb,
    ):
        token = normalize_key(value)
        if token and token in normalized_text:
            return True
    return False


def _road_mentioned(text, target):
    normalized_text = normalize_key(text)
    if not normalized_text:
        return False
    if not _has_strong_location(text, target):
        return False
    full = normalize_key(target.road_name)
    if full and full in normalized_text:
        return True
    if not _has_road_context(text):
        return False
    return any(
        normalize_key(alias) in normalized_text
        for alias in road_match_aliases(target)
        if normalize_key(alias)
    )


def _authority_mentioned(text, authority):
    normalized_text = normalize_key(text)
    normalized_authority = normalize_key(authority)
    if not normalized_text or not normalized_authority:
        return False
    if normalized_authority in normalized_text:
        return True
    generic = {
        "public",
        "works",
        "department",
        "government",
        "state",
        "kerala",
        "india",
        "the",
        "and",
    }
    tokens = [
        token
        for token in normalized_authority.split()
        if len(token) > 2 and token not in generic
    ]
    if not tokens:
        return False
    text_tokens = set(normalized_text.split())
    return any(token in text_tokens for token in tokens)


def _name_mentioned(text, name):
    normalized_text = normalize_key(text)
    normalized_name = normalize_key(name)
    if not normalized_name:
        return False
    if normalized_name in normalized_text:
        return True
    tokens = [
        token
        for token in normalized_name.split()
        if len(token) > 2 and token not in GENERIC_NAME_TOKENS
    ]
    if not tokens:
        return False
    if len(tokens) == 1:
        return tokens[0] in normalized_text.split()
    return all(token in normalized_text.split() for token in tokens)


def _has_work_term(text):
    lowered = normalize_text(text).casefold()
    return any(term in lowered for term in WORK_TERMS)


def _focus_text(text, target, max_chars):
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if not lines:
        return ""
    selected = []
    for index, line in enumerate(lines):
        if _road_name_mentioned(line, target):
            start = max(0, index - 3)
            end = min(len(lines), index + 5)
            selected.extend(lines[start:end])
    if not selected:
        selected = [line for line in lines if _has_work_term(line)][:30]
    if not selected:
        selected = lines[:40]
    output = []
    seen = set()
    total = 0
    for line in selected:
        key = line.casefold()
        if key in seen:
            continue
        seen.add(key)
        if total + len(line) + 1 > max_chars:
            break
        output.append(line)
        total += len(line) + 1
    return "\n".join(output)[:max_chars]


def _supporting_quote(text, target, contractor):
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if contractor:
        for line in lines:
            if _road_mentioned(line, target) and _name_mentioned(line, contractor):
                return normalize_text(line)[:1000]
    for line in lines:
        if _road_mentioned(line, target) and _has_work_term(line):
            return normalize_text(line)[:1000]
    return None


def validate_model_result(result, target, source_entries):
    no_match = {
        "match": False,
        "confidence": "none",
        "contractor": None,
        "work_title": None,
        "authority": None,
        "tender_number": None,
        "work_reference": None,
        "source_url": None,
        "source_title": None,
        "evidence": None,
        "reason": "No source-backed contractor or work record connection was established.",
    }
    if not result.get("match"):
        reason = normalize_text(result.get("reason"))
        no_match["reason"] = (
            reason[:512]
            if reason
            else "No source-backed contractor or work record connection was found."
        )
        return no_match

    sources_by_id = {source["id"]: source for source in source_entries}
    source = sources_by_id.get(normalize_text(result.get("source_id")))
    if source is None:
        no_match["reason"] = "The model did not cite a supplied source."
        return no_match

    source_text = source["text"]
    contractor = normalize_text(result.get("contractor"))
    if contractor and not _name_mentioned(source_text, contractor):
        contractor = ""

    evidence = normalize_text(result.get("evidence"))
    if not evidence or normalize_key(evidence) not in normalize_key(source_text):
        evidence = _supporting_quote(source_text, target, contractor)
    if not evidence:
        no_match["reason"] = "The cited source does not contain a supporting quote."
        return no_match

    road_in_evidence = _road_mentioned(evidence, target)
    contractor_in_evidence = bool(
        contractor and _name_mentioned(evidence, contractor)
    )
    work_term_in_evidence = _has_work_term(evidence)
    tier = source["tier"]
    if not road_in_evidence:
        no_match["reason"] = "The supporting quote does not name the target road."
        return no_match
    if tier >= 4:
        no_match["reason"] = "Only a general website mentioned this connection."
        return no_match
    if not contractor_in_evidence:
        contractor = ""
    if not contractor and not work_term_in_evidence:
        no_match["reason"] = "The supporting quote does not describe a work or tender record."
        return no_match

    aggregator = _is_tender_aggregator(_domain_of(source["url"]))
    if tier == 3:
        if contractor_in_evidence and work_term_in_evidence:
            confidence = "medium"
            reason = (
                "A tender aggregator links the road and contractor; verify on the official portal."
                if aggregator
                else "A reputable secondary source links the road and contractor; review the original record."
            )
        elif work_term_in_evidence:
            confidence = "medium"
            reason = (
                "A tender aggregator lists a related work record; verify on the official portal."
                if aggregator
                else "A secondary source lists a related work record; verify the original record."
            )
        else:
            no_match["reason"] = "The secondary source does not explicitly connect the road and contractor."
            return no_match
    elif contractor_in_evidence and work_term_in_evidence:
        confidence = "high"
        reason = "An explicit road and contractor connection was found in a government or official source."
    elif contractor_in_evidence:
        confidence = "medium"
        reason = "The road and contractor appear together, but the work connection needs review."
    else:
        confidence = "medium"
        reason = (
            "A public tender or work record names the road but does not identify a contractor."
        )

    tender_number = normalize_text(result.get("tender_number"))
    work_reference = normalize_text(result.get("work_reference"))
    if tender_number and not _contains(source_text, tender_number):
        tender_number = ""
    if work_reference and not _contains(source_text, work_reference):
        work_reference = ""
    work_title = normalize_text(result.get("work_title"))
    authority = normalize_text(result.get("authority"))
    if authority and not _authority_mentioned(source_text, authority):
        authority = ""
    return {
        "match": True,
        "confidence": confidence,
        "contractor": contractor[:255] or None,
        "work_title": work_title[:512] or None,
        "authority": authority[:255] or None,
        "tender_number": tender_number[:128] or None,
        "work_reference": work_reference[:128] or None,
        "source_url": source["url"][:1024],
        "source_title": (source["title"] or source["url"])[:512],
        "evidence": evidence[:1000],
        "reason": reason[:512],
    }


def latest_research_run(pothole):
    target = build_target(pothole)
    key = build_research_key(target)
    query = PotholeResearchRun.query
    if key:
        query = query.filter(
            or_(
                PotholeResearchRun.canonical_pothole_id == pothole.id,
                PotholeResearchRun.research_key == key,
            )
        )
    else:
        query = query.filter(PotholeResearchRun.canonical_pothole_id == pothole.id)
    return query.order_by(
        PotholeResearchRun.created_at.desc(), PotholeResearchRun.id.desc()
    ).first()


def enqueue_research(pothole, force=False):
    if not current_app.config.get("RESEARCH_ENABLED"):
        return None
    target = build_target(pothole)
    key = build_research_key(target)
    if target is None or not key:
        return None

    active = (
        PotholeResearchRun.query.filter(
            PotholeResearchRun.status.in_(("pending", "running")),
            or_(
                PotholeResearchRun.canonical_pothole_id == pothole.id,
                PotholeResearchRun.research_key == key,
            ),
        )
        .order_by(PotholeResearchRun.created_at.desc())
        .first()
    )
    if active:
        return active

    now = datetime.now(timezone.utc)
    if not force:
        cache_days = current_app.config.get("RESEARCH_CACHE_DAYS", 30)
        completed = (
            PotholeResearchRun.query.filter(
                PotholeResearchRun.research_key == key,
                PotholeResearchRun.status == "completed",
                PotholeResearchRun.completed_at >= now - timedelta(days=cache_days),
            )
            .order_by(PotholeResearchRun.completed_at.desc())
            .first()
        )
        if completed:
            return completed
        retry_seconds = current_app.config.get("RESEARCH_FAILED_RETRY_SECONDS", 3600)
        failed = (
            PotholeResearchRun.query.filter(
                PotholeResearchRun.research_key == key,
                PotholeResearchRun.status == "failed",
                PotholeResearchRun.completed_at >= now - timedelta(seconds=retry_seconds),
            )
            .order_by(PotholeResearchRun.completed_at.desc())
            .first()
        )
        if failed:
            return failed

    run = PotholeResearchRun(
        canonical_pothole_id=pothole.id,
        research_key=key,
        status="pending",
        model=current_app.config.get("RESEARCH_MODEL", "qwen3:0.6b"),
    )
    db.session.add(run)
    db.session.commit()
    return run


def _complete_no_match(run, reason):
    run.status = "completed"
    run.match = False
    run.confidence = "none"
    run.reason = reason[:512]
    run.completed_at = utcnow()
    if run.started_at:
        started = run.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        run.total_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
    db.session.commit()


def _fail_run(run, code):
    run.status = "failed"
    run.error = code[:64]
    run.completed_at = utcnow()
    db.session.commit()


def execute_research_run(run_id):
    run = db.session.get(PotholeResearchRun, run_id)
    if run is None:
        return
    if run.status == "completed":
        return
    run.status = "running"
    run.started_at = utcnow()
    db.session.commit()

    pothole = run.pothole
    target = build_target(pothole) if pothole else None
    if target is None:
        _complete_no_match(run, "Insufficient location metadata for research.")
        return

    config = current_app.config
    started = time.monotonic()
    deadline = started + config.get("RESEARCH_MAX_DURATION_SECONDS", 180)
    max_queries = config.get("RESEARCH_MAX_QUERIES", 12)
    max_fetches = config.get("RESEARCH_MAX_FETCHES", 5)
    queries = generate_queries(target, max_queries)
    search_engine_url = (
        config.get("SEARCH_ENGINE_URL")
        or config.get("SEARXNG_URL")
        or "http://searxng:8080"
    )
    search_provider = SearXNGProvider(
        search_engine_url,
        config.get("RESEARCH_USER_AGENT", "RoadSenseResearch/1.0"),
        timeout=config.get("SEARXNG_TIMEOUT_SECONDS", 15),
        results_per_query=config.get("SEARXNG_RESULTS_PER_QUERY", 5),
        engines=config.get("SEARXNG_ENGINES", "yep"),
    )
    fetcher = SafePageFetcher(
        config.get("RESEARCH_USER_AGENT", "RoadSenseResearch/1.0"),
        allowed_ports=config.get("RESEARCH_ALLOWED_PORTS") or {80, 443},
        max_html_bytes=config.get("RESEARCH_MAX_HTML_BYTES", 3000000),
        max_pdf_bytes=config.get("RESEARCH_MAX_PDF_BYTES", 8000000),
    )
    ollama = OllamaClient(
        config.get("OLLAMA_URL", "http://ollama:11434"),
        config.get("RESEARCH_MODEL", "qwen3:0.6b"),
        timeout=config.get("RESEARCH_OLLAMA_TIMEOUT_SECONDS", 120),
        num_ctx=config.get("RESEARCH_OLLAMA_NUM_CTX", 4096),
        num_predict=config.get("RESEARCH_OLLAMA_NUM_PREDICT", 512),
    )

    run.query_count = len(queries)
    run.queries_json = []
    db.session.commit()
    current_app.logger.info(
        "RESEARCH start run=%s pothole=%s road=%r locality=%r district=%r "
        "pincode=%r queries=%s",
        run.id,
        target.public_id,
        target.road_name,
        target.locality,
        target.district,
        target.pincode,
        len(queries),
    )

    hits = []
    query_log = []
    search_errors = 0
    search_started = time.monotonic()
    for index, query in enumerate(queries):
        if time.monotonic() >= deadline:
            break
        try:
            found = search_provider.search(query)
            hits.extend(found)
            query_log.append({"query": query, "result_count": len(found)})
            current_app.logger.info(
                "SEARCH query=%r results=%s", query, len(found)
            )
        except SearchError as exc:
            search_errors += 1
            query_log.append({"query": query, "result_count": 0, "error": exc.code})
            current_app.logger.warning(
                "SEARCH query=%r failed=%s", query, exc.code
            )
        if index < len(queries) - 1:
            time.sleep(config.get("RESEARCH_SEARCH_DELAY_SECONDS", 0.8))
    run.search_ms = int((time.monotonic() - search_started) * 1000)
    run.queries_json = query_log
    db.session.commit()
    current_app.logger.info(
        "SEARCH RESULTS run=%s hits=%s errors=%s", run.id, len(hits), search_errors
    )

    if not hits:
        if search_errors == len(queries):
            _fail_run(run, "search_failed")
        else:
            _complete_no_match(run, NO_MATCH_REASON)
        return

    candidates = _dedupe_candidates(hits, target)
    run.result_count = len(candidates)
    db.session.commit()
    authoritative = [item for item in candidates if item["tier"] <= 3]
    if not authoritative:
        _complete_no_match(run, NO_MATCH_REASON)
        return

    fetch_started = time.monotonic()
    fetched = []
    fetch_errors = 0
    for item in authoritative[:max_fetches]:
        if time.monotonic() >= deadline:
            break
        hit = item["hit"]
        source_row = PotholeResearchSource(
            run_id=run.id,
            search_query=hit.query,
            rank=hit.rank,
            title=hit.title,
            url=hit.url,
            domain=item["domain"],
            tier=item["tier"],
            snippet=hit.snippet,
            fetch_status="pending",
        )
        db.session.add(source_row)
        db.session.flush()
        try:
            page = fetcher.fetch(hit.url)
        except FetchError as exc:
            fetch_errors += 1
            source_row.fetch_status = "failed"
            source_row.error = exc.code[:64]
            db.session.commit()
            time.sleep(config.get("RESEARCH_FETCH_DELAY_SECONDS", 1.2))
            continue
        source_row.fetched = True
        source_row.fetch_status = "ok"
        source_row.retrieved_at = utcnow()
        source_row.url = page.url[:1024]
        source_row.domain = _domain_of(page.url)
        source_row.tier = _tier_for_domain(source_row.domain)
        source_row.title = (page.title or hit.title)[:512]
        source_row.text_chars = len(page.text)
        current_app.logger.info(
            "FETCH ok run=%s source=%s domain=%s chars=%s",
            run.id,
            source_row.id,
            source_row.domain,
            source_row.text_chars,
        )
        text = "\n".join(
            part
            for part in (hit.title, hit.snippet, page.title, page.text)
            if part
        )
        fetched.append(
            {
                "id": "S{0}".format(len(fetched) + 1),
                "title": source_row.title,
                "url": page.url,
                "tier": source_row.tier,
                "text": text,
                "row": source_row,
            }
        )
        db.session.commit()
        if len(fetched) >= max_fetches:
            break
        time.sleep(config.get("RESEARCH_FETCH_DELAY_SECONDS", 1.2))

    run.fetch_ms = int((time.monotonic() - fetch_started) * 1000)
    run.fetched_source_count = len(fetched)
    db.session.commit()
    if not fetched:
        _fail_run(run, "fetch_failed")
        return

    relevant = [item for item in fetched if _road_mentioned(item["text"], target)]
    current_app.logger.info(
        "MATCH sources run=%s fetched=%s relevant=%s",
        run.id,
        len(fetched),
        len(relevant),
    )
    if not relevant:
        _complete_no_match(run, NO_MATCH_REASON)
        return

    relevant.sort(
        key=lambda item: (
            0 if _has_work_term(item["text"]) else 1,
            item["tier"],
            -len(item["text"]),
        )
    )
    selected = relevant[:3]
    for item in selected:
        item["row"].selected = True
    db.session.commit()
    run.selected_source_count = len(selected)
    db.session.commit()

    prompt_sources = []
    remaining_context = config.get("RESEARCH_MAX_CONTEXT_CHARS", 9000)
    max_source_chars = config.get("RESEARCH_MAX_SOURCE_CHARS", 3000)
    for item in selected:
        budget = min(max_source_chars, remaining_context)
        if budget <= 200:
            break
        excerpt = _focus_text(item["text"], target, budget)
        prompt_sources.append(
            {
                "id": item["id"],
                "title": item["title"],
                "url": item["url"],
                "tier": item["tier"],
                "text": excerpt,
            }
        )
        remaining_context -= len(excerpt)
    if not prompt_sources:
        _complete_no_match(run, NO_MATCH_REASON)
        return

    if time.monotonic() >= deadline:
        _fail_run(run, "time_budget_exceeded")
        return

    current_app.logger.info(
        "OLLAMA extract run=%s model=%s sources=%s",
        run.id,
        config.get("RESEARCH_MODEL", "qwen3:0.6b"),
        len(prompt_sources),
    )
    ollama_started = time.monotonic()
    try:
        result = ollama.extract(target, prompt_sources)
    except OllamaError as exc:
        run.ollama_ms = int((time.monotonic() - ollama_started) * 1000)
        _fail_run(run, exc.code)
        return
    run.ollama_ms = int((time.monotonic() - ollama_started) * 1000)

    validated = validate_model_result(result, target, prompt_sources)
    run.match = validated["match"]
    run.confidence = validated["confidence"]
    run.contractor = validated["contractor"]
    run.work_title = validated["work_title"]
    run.authority = validated["authority"]
    run.tender_number = validated["tender_number"]
    run.work_reference = validated["work_reference"]
    run.source_url = validated["source_url"]
    run.source_title = validated["source_title"]
    run.evidence = validated["evidence"]
    run.reason = validated["reason"]
    run.status = "completed"
    run.completed_at = utcnow()
    run.total_ms = int((time.monotonic() - started) * 1000)
    db.session.commit()

    current_app.logger.info(
        "FINAL run=%s pothole=%s match=%s confidence=%s contractor=%s "
        "authority=%s source=%s",
        run.id,
        target.public_id,
        run.match,
        run.confidence,
        bool(run.contractor),
        run.authority,
        run.source_url,
    )
