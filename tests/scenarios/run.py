"""Uruchamia przypadki testowe (scenariusze A-J z sekcji 6 zadania) przez API Prawdowida.

Użycie (backend musi działać, np. docker compose up --build app):

    python tests/scenarios/run.py                         # http://localhost:8000
    python tests/scenarios/run.py --base-url http://localhost:8001
    python tests/scenarios/run.py --only A1,E1
    python tests/scenarios/run.py --bad-key-url http://localhost:8002   # + J3: dostawca odrzuca klucz

Koszt i liczba pobrań stron pochodzą z logu sprawdzeń (GET /api/v1/log/{checkId}). Spoza tego
komputera (np. backend w Dockerze) potrzebny jest ADMIN_TOKEN w zmiennej środowiskowej.

Wynik: tabela w konsoli i pełne dane (pytania, odpowiedzi, czasy, koszty) w
tests/scenarios/results/<data>.json. Tylko biblioteka standardowa Pythona.
"""

import argparse
import json
import os
import statistics
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
VERDICTS = {"CONFIRMED", "FALSE", "MISLEADING", "INSUFFICIENT_EVIDENCE", "NOT_CHECKABLE"}
SOURCED = {"CONFIRMED", "FALSE", "MISLEADING"}


def call(base: str, path: str, payload: dict | None = None, method: str = "POST", timeout: float = 400):
    headers = {"content-type": "application/json"}
    if os.getenv("ADMIN_TOKEN"):
        headers["authorization"] = f"Bearer {os.environ['ADMIN_TOKEN']}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except ValueError:
            return e.code, {}


def outcome(body: dict) -> str:
    """Status awarii/odrzucenia albo werdykt pierwszego twierdzenia."""
    if "answer" in body:
        return "TEXT"
    status = body.get("status") or "TECHNICAL_FAILURE"
    if status != "COMPLETED":
        return status
    claims = body.get("claims") or []
    if not claims:
        return "NO_CLAIMS"
    o = claims[0].get("outcome") or {}
    return o.get("verdict") or o.get("kind") or "?"


def citations(body: dict) -> tuple[int, int]:
    """(twierdzenia z werdyktem rozstrzygającym, w tym ze źródłem z listy)."""
    decisive = [c for c in body.get("claims") or [] if (c.get("outcome") or {}).get("verdict") in SOURCED]
    return len(decisive), sum(1 for c in decisive if c.get("evidenceIds"))


def run_case(base: str, case: dict, run_id: str) -> dict:
    payload = {"channel": case.get("channel", "WEB"), "text": case.get("text"), "url": case.get("url"),
               "userRef": f"test-{case['id']}-{run_id}"}
    started = time.monotonic()
    if case.get("burst"):  # kilka zapytań tej samej osoby pod rząd - liczy się ostatnie
        for _ in range(case["burst"] - 1):
            call(base, "/api/v1/check", payload)
    code, body = call(base, "/api/v1/check", payload)
    latency = time.monotonic() - started
    got = outcome(body)
    log = {}
    if body.get("checkId"):
        log_code, log_body = call(base, f"/api/v1/log/{body['checkId']}", method="GET", timeout=10)
        log = log_body if log_code == 200 else {}
    decisive, sourced = citations(body)
    ok = got in case["expect"] and got not in case.get("never", [])
    if case.get("needs_source") and decisive and sourced < decisive:
        ok = False
    return {
        "id": case["id"], "scenario": case["scenario"], "input": case.get("text") or case.get("url"),
        "channel": payload["channel"], "expect": case["expect"], "got": got, "pass": ok, "http": code,
        "latency_s": round(latency, 1), "model_called": not case.get("no_model"),
        "cost_usd": log.get("cost_usd"), "fetches": log.get("fetches"), "fetch_errors": log.get("fetch_errors"),
        "injection_logged": log.get("injection"), "decisive_claims": decisive, "with_source": sourced,
        "sources": [(e.get("source") or {}).get("url") for e in body.get("evidence") or []],
        "summary": body.get("summary") or body.get("statusMessage"), "response": body,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="http://localhost:8000")
    p.add_argument("--only", default="")
    p.add_argument("--bad-key-url", default="", help="backend uruchomiony z nieprawidłowym kluczem modelu (scenariusz J3)")
    args = p.parse_args()
    cases = json.loads((HERE / "scenarios.json").read_text(encoding="utf-8"))["cases"]
    only = {x.strip() for x in args.only.split(",") if x.strip()}
    run_id = uuid.uuid4().hex[:6]
    results = []
    for case in cases:
        if only and case["id"] not in only:
            continue
        base = args.base_url
        if case.get("bad_key"):
            if not args.bad_key_url:
                continue
            base = args.bad_key_url
        r = run_case(base, case, run_id)
        results.append(r)
        print(f"{r['id']:3} {'OK ' if r['pass'] else 'BŁĄD'} {r['got']:22} {r['latency_s']:6.1f} s  koszt={r['cost_usd']}")

    by_id = {r["id"]: r for r in results}
    for case in cases:  # spójność kanałów: ten sam werdykt co wskazany przypadek
        ref = case.get("same_as")
        if ref and case["id"] in by_id and ref in by_id:
            by_id[case["id"]]["same_as"] = ref
            by_id[case["id"]]["consistent"] = by_id[case["id"]]["got"] == by_id[ref]["got"]
            by_id[case["id"]]["pass"] = by_id[case["id"]]["pass"] and by_id[case["id"]]["consistent"]

    model = [r for r in results if r["model_called"] and r["got"] != "TECHNICAL_FAILURE"]
    costs = [r["cost_usd"] for r in model if r["cost_usd"] is not None]
    decisive = sum(r["decisive_claims"] for r in results)
    attacks = [r for r in results if any(c["id"] == r["id"] and c.get("injection") for c in cases)]
    summary = {
        "date": datetime.now().isoformat(timespec="seconds"), "base_url": args.base_url,
        "cases": len(results), "passed": sum(r["pass"] for r in results),
        "median_latency_s": round(statistics.median(r["latency_s"] for r in model), 1) if model else None,
        "max_latency_s": max((r["latency_s"] for r in model), default=None),
        "total_cost_usd": round(sum(costs), 4) if costs else None,
        "avg_cost_usd": round(sum(costs) / len(costs), 4) if costs else None,
        "citation_coverage": round(sum(r["with_source"] for r in results) / decisive, 3) if decisive else None,
        "attacks_repelled": f"{sum(r['pass'] for r in attacks)}/{len(attacks)}",
    }
    out = HERE / "results" / f"{datetime.now():%Y-%m-%d_%H%M}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Pełne wyniki: {out}")


if __name__ == "__main__":
    main()
