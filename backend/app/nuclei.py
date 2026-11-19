"""Nuclei real engine integration.

Detection order: NUCLEI_PATH env > shutil.which('nuclei') > not available.
Execution: targets written to a temp file, `nuclei -l targets -json -silent -no-color`,
each JSONL line parsed into a Finding (severity mapped, template-id as poc_ref).
If nuclei is not installed the scan falls back to the simulated engine and the
status endpoint reports install instructions.
"""
import json
import os
import shutil
import subprocess
import tempfile

from .models import Finding

SEV_MAP = {"critical": "严重", "high": "高危", "medium": "中危", "low": "低危", "info": "低危", "unknown": "中危"}


def nuclei_path() -> str | None:
    return os.environ.get("NUCLEI_PATH") or shutil.which("nuclei")


def nuclei_status() -> dict:
    path = nuclei_path()
    if not path:
        return {
            "available": False,
            "note": "未检测到 nuclei。安装指引：go install -v github.com/projectdiscovery/nuclei/v2/cmd/nuclei@latest "
                    "或从 https://github.com/projectdiscovery/nuclei/releases 下载后设置 NUCLEI_PATH 环境变量。"
                    "未安装时扫描自动回退到模拟引擎。",
        }
    try:
        out = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=15)
        version = (out.stdout or out.stderr).strip().splitlines()[-1] if (out.stdout or out.stderr) else ""
    except Exception as exc:
        version = f"version check failed: {exc}"
    return {"available": True, "path": path, "version": version}


def run_nuclei(target_scope: str) -> list[dict]:
    """Run nuclei against comma/newline separated targets. Returns findings."""
    path = nuclei_path()
    if not path:
        return []
    targets = [t.strip() for t in target_scope.replace(",", "\n").splitlines() if t.strip()]
    if not targets:
        return []
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tf:
        tf.write("\n".join(targets))
        targets_file = tf.name
    findings: list[dict] = []
    try:
        proc = subprocess.run(
            [path, "-l", targets_file, "-json", "-silent", "-no-color",
             "-timeout", "8", "-retries", "1", "-rate-limit", "50"],
            capture_output=True, text=True, timeout=1800,
        )
        for line in (proc.stdout or "").splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            info = ev.get("info", {}) or {}
            sev = SEV_MAP.get(str(info.get("severity", "unknown")).lower(), "中危")
            ref = ev.get("template-id") or ev.get("templateID") or "nuclei"
            findings.append({
                "asset_value": ev.get("matched-at") or ev.get("host") or "",
                "vuln_title": info.get("name") or ref,
                "severity": sev,
                "poc_ref": ref,
                "evidence": f"[nuclei] matcher={ev.get('matcher-name', '')} type={ev.get('type', '')} url={ev.get('matched-at', '')}",
            })
    finally:
        try:
            os.unlink(targets_file)
        except OSError:
            pass
    return findings
