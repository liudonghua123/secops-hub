"""NVD API 2.0 fetcher.

Public docs: https://nvd.nist.gov/developers/vulnerabilities
Rate limit without API key: 5 requests / 30 seconds — we do a single request
per sync (7-day window) which is comfortably within limits.
Set NVD_API_KEY env var for higher limits.
"""
import os

import httpx
from sqlalchemy.orm import Session

from .common import cvss_to_severity, iso_days_ago, upsert_intel, upsert_vulnerability

NVD_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"


def _extract_cvss(cve: dict) -> float:
    metrics = cve.get("metrics", {})
    for key in ("cvssMetricV40", "cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        items = metrics.get(key) or []
        if items:
            return float(items[0]["cvssData"].get("baseScore", 0.0))
    return 0.0


def _extract_keywords(cve: dict) -> str:
    """Product/vendor keywords for asset fingerprint matching.

    Priority: CNA-provided `affected` list (current NVD format, from the CVE.org
    schema) > legacy CPE `configurations`.
    """
    products: list = []

    for a in cve.get("affected") or []:
        # NVD puts CNA product data either flat on the item or nested in
        # affectedData (observed in production API responses).
        for sub in a.get("affectedData") or [a]:
            vendor = (sub.get("vendor") or "").strip()
            product = (sub.get("product") or "").strip()
            for word in (vendor, product):
                if word and word not in ("*", "-"):
                    products.append(word.lower())
            for pkg in sub.get("packages") or []:
                for name in pkg.get("names") or []:
                    if name and name not in ("*", "-"):
                        products.append(name.lower())

    if not products:
        for conf in cve.get("configurations") or []:
            for node in conf.get("nodes", []):
                for match in node.get("cpeMatch", []):
                    parts = match.get("criteria", "").split(":")
                    if len(parts) >= 5 and parts[2] in ("a", "h", "o"):
                        products.append(parts[4].lower())
                    if len(products) >= 6:
                        break

    return ",".join(list(dict.fromkeys(products))[:6])


def _cve_to_record(cve_entry: dict) -> dict:
    cve = cve_entry.get("cve", {})
    cve_id = cve.get("id", "")
    desc = ""
    for d in cve.get("descriptions", []):
        if d.get("lang") == "en":
            desc = d.get("value", "")
            break
    score = _extract_cvss(cve)
    keywords = _extract_keywords(cve)
    weak = score <= 0 or not keywords
    return {
        "cve_id": cve_id,
        "title": f"{cve_id} {desc[:60]}",
        "severity": cvss_to_severity(score),
        "cvss": score,
        "source": "NVD",
        "description": desc[:2000],
        "affected_keywords": keywords,
        "poc_available": False,
        "exploited_in_wild": bool(cve.get("cisaExploitAdd")),
        "fix_suggestion": "",
        "published_at": (cve.get("published") or "")[:10],
    }


def sync_nvd(db: Session, days: int = 7, max_results: int = 200) -> dict:
    """Fetch CVEs published/modified within the last N days."""
    headers = {}
    if os.environ.get("NVD_API_KEY"):
        headers["apiKey"] = os.environ["NVD_API_KEY"]
    params = {
        "pubStartDate": iso_days_ago(days),
        "pubEndDate": iso_days_ago(0),
        "resultsPerPage": min(max_results, 2000),
    }
    try:
        resp = httpx.get(NVD_API, params=params, headers=headers, timeout=60)
        resp.raise_for_status()
        payload = resp.json()
    except httpx.HTTPError as exc:
        return {"ok": False, "error": f"NVD request failed: {exc}"}

    stats = {"add": 0, "update": 0, "same": 0, "skip": 0}
    intel_added = 0
    total = payload.get("totalResults", 0)
    for entry in payload.get("vulnerabilities", [])[:max_results]:
        rec = _cve_to_record(entry)
        rec["_internal"] = True
        action = upsert_vulnerability(db, {k: v for k, v in rec.items() if not k.startswith("_")})
        stats[action] += 1
        if action == "add" and rec["severity"] in ("严重", "高危"):
            added = upsert_intel(
                db, "NVD",
                f"NVD 收录 {rec['cve_id']}（{rec['severity']} CVSS {rec['cvss']}）",
                f"https://nvd.nist.gov/vuln/detail/{rec['cve_id']}",
                rec["description"][:300], rec["severity"], rec["cve_id"], rec["published_at"])
            if added:
                intel_added += 1
    db.commit()
    return {
        "ok": True, "source": "NVD", "total_available": total,
        "fetched": sum(stats.values()), **stats,
        "intel_created": intel_added,
    }
