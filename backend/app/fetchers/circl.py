"""CIRCL CVE feed fetcher (backup real-time source, no key required).

Endpoint: https://cve.circl.lu/api/last — the 30 most recently published CVEs.
Useful when NVD is unreachable or rate-limited from the unit network.
"""
import httpx
from sqlalchemy.orm import Session

from .common import cvss_to_severity, upsert_vulnerability

CIRCL_LAST = "https://cve.circl.lu/api/last"


def _extract_keywords(item: dict) -> str:
    """Product names from CPE strings (cpe23 preferred, 2.2 fallback)."""
    products: list = []
    for cpe in item.get("vulnerable_product_cpe23") or item.get("vulnerable_product") or []:
        parts = cpe.split(":")
        # cpe23: cpe:2.3:part:vendor:product  ->  product = parts[4]
        # cpe2.2: cpe:part:vendor:product     ->  product = parts[3]
        idx = 4 if len(parts) > 4 and parts[1] == "2.3" else 3
        if len(parts) > idx and parts[idx] and parts[idx] not in ("*", "-"):
            products.append(parts[idx])
        if len(products) >= 6:
            break
    return ",".join(dict.fromkeys(products))


def sync_circl(db: Session, max_results: int = 30) -> dict:
    try:
        resp = httpx.get(CIRCL_LAST, timeout=120)
        resp.raise_for_status()
        items = resp.json()
    except httpx.HTTPError as exc:
        return {"ok": False, "error": f"CIRCL request failed: {exc}"}

    stats = {"add": 0, "update": 0, "same": 0, "skip": 0}
    for item in (items if isinstance(items, list) else [])[:max_results]:
        if not isinstance(item, dict):
            stats["skip"] += 1
            continue
        cve_id = str(item.get("id") or item.get("cve_id") or item.get("cve") or "")
        if not cve_id.upper().startswith("CVE-"):
            stats["skip"] += 1
            continue
        score = float(item.get("cvss") or item.get("cvss3") or 0.0)
        rec = {
            "cve_id": cve_id,
            "title": f"{cve_id} {(item.get('summary') or '')[:60]}",
            "severity": cvss_to_severity(score),
            "cvss": score,
            "source": "CIRCL",
            "description": (item.get("summary") or "")[:2000],
            "affected_keywords": _extract_keywords(item),
            "published_at": (item.get("Published") or "")[:10],
        }
        stats[upsert_vulnerability(db, rec)] += 1
    db.commit()
    return {"ok": True, "source": "CIRCL", "fetched": sum(stats.values()), **stats}
