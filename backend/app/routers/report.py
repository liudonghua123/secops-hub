"""Official vulnerability notification (通报) as Word documents."""
import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import require_role
from ..database import get_db, SessionLocal
from ..models import VulnEvent, Vulnerability
from ..routers.vulns import enrich

router = APIRouter(prefix="/api/report", tags=["report"])


def _set_cn(run, size=12, bold=False, font="仿宋"):
    run.font.name = font
    run.font.size = size
    run.font.bold = bold
    # east asian font requires rFonts patch
    from docx.oxml.ns import qn
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font)


def build_docx(vulns: list[dict], operator: str = "") -> bytes:
    """One docx containing one notification per vulnerability (page break separated)."""
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
    from docx.shared import Pt, Cm

    doc = Document()
    # page setup: A4, standard 公文 margins
    for section in doc.sections:
        section.page_width, section.page_height = Cm(21.0), Cm(29.7)
        section.top_margin = section.bottom_margin = Cm(3.7 - 1.2)
        section.left_margin, section.right_margin = Cm(2.8), Cm(2.6)

    now = datetime.now()
    today = f"{now.year}年{now.month:02d}月{now.day:02d}日"
    year = now.year
    for i, v in enumerate(vulns):
        assets = v.get("matched_assets") or []
        # title
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _set_cn(p.add_run("网络安全漏洞处置通报"), size=Pt(22), bold=True, font="方正小标宋简体")

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _set_cn(p.add_run(f"编号：SecOps-{year}-{v['id']:04d}"), size=Pt(12))

        doc.add_paragraph()
        lines = [
            f"各相关处室、运维单位：",
            "",
            f"经安全监测发现，我单位存在以下网络安全漏洞风险，现将有关情况通报如下，请按要求及时组织处置。",
            "",
        ]
        for line in lines:
            p = doc.add_paragraph()
            p.paragraph_format.first_line_indent = Pt(24)
            p.paragraph_format.line_spacing = 1.5
            _set_cn(p.add_run(line), size=Pt(14))

        # 漏洞情况
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.5
        _set_cn(p.add_run("一、漏洞基本情况"), size=Pt(14), bold=True, font="黑体")
        basic = [
            f"漏洞名称：{v['title']}",
            f"漏洞编号：{' / '.join(filter(None, [v.get('cve_id'), v.get('cnvd_id'), v.get('cnnvd_id')])) or '—'}",
            f"风险等级：{v['severity']}（CVSS {v.get('cvss') or 0}）",
            f"公开日期：{v.get('published_at') or '—'}",
            f"漏洞描述：{v.get('description') or '—'}",
            f"修复建议：{v.get('fix_suggestion') or '—'}",
            f"利用条件：{'已有公开 POC' + ('，已被在野利用' if v.get('exploited_in_wild') else '') if v.get('poc_available') else '暂无公开利用'}",
        ]
        for line in basic:
            p = doc.add_paragraph()
            p.paragraph_format.first_line_indent = Pt(24)
            p.paragraph_format.line_spacing = 1.5
            _set_cn(p.add_run(line), size=Pt(14))

        # 影响资产
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.5
        _set_cn(p.add_run("二、涉及资产"), size=Pt(14), bold=True, font="黑体")
        if assets:
            table = doc.add_table(rows=1, cols=4)
            table.style = "Table Grid"
            header = table.rows[0].cells
            for c, text in zip(header, ["资产名称", "地址/值", "责任部门", "重要性"]):
                c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                _set_cn(c.paragraphs[0].add_run(text), size=Pt(12), bold=True)
            for a in assets:
                cells = table.add_row().cells
                for c, text in zip(cells, [a.get("name", ""), a.get("value", ""),
                                           a.get("owner_dept", "") or "—", a.get("criticality", "")]):
                    _set_cn(c.paragraphs[0].add_run(str(text)), size=Pt(12))
        else:
            p = doc.add_paragraph()
            p.paragraph_format.first_line_indent = Pt(24)
            _set_cn(p.add_run("经指纹匹配，暂未发现单位资产受该漏洞影响，请持续关注。"), size=Pt(14))

        # 处置要求
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.5
        _set_cn(p.add_run("三、处置要求"), size=Pt(14), bold=True, font="黑体")
        for line in [
            f"1. 请于 {"3 个工作日" if v['severity'] in ("严重", "高危") else "5 个工作日"}内完成核查与整改，并在平台中回填处置状态。",
            "2. 严重、高危漏洞修复前，应采取临时缓解措施（限制访问来源、关闭相关功能、加强监测）。",
            "3. 处置过程中发现已被利用的迹象，请立即报告信息中心，并保留现场证据。",
            "4. 联系人：信息中心安全管理岗。",
        ]:
            p = doc.add_paragraph()
            p.paragraph_format.first_line_indent = Pt(24)
            p.paragraph_format.line_spacing = 1.5
            _set_cn(p.add_run(line), size=Pt(14))

        doc.add_paragraph()
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        _set_cn(p.add_run(f"信息中心\n{today}"), size=Pt(14))

        if i < len(vulns) - 1:
            doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()


class ReportBody(BaseModel):
    vuln_ids: list[int]


@router.post("/vuln-docx")
def vuln_report(body: ReportBody, db: Session = Depends(get_db),
                user: dict = Depends(require_role("analyst"))):
    """Generate official Word notification for one or more vulnerabilities."""
    vulns = []
    for vid in body.vuln_ids:
        v = db.get(Vulnerability, vid)
        if not v:
            raise HTTPException(404, f"漏洞 {vid} 不存在")
        vulns.append(enrich(v, db))
    if not vulns:
        raise HTTPException(400, "未选择漏洞")
    data = build_docx(vulns, operator=user["username"])
    for vid in body.vuln_ids:
        db.add(VulnEvent(vuln_id=vid, action="通报生成",
                         detail=f"生成处置通报（{len(vulns)} 项合并文档）", operator=user["username"]))
    db.commit()
    filename = (f"vuln_report_{len(vulns)}.docx" if len(vulns) > 1
                else f"vuln_report_{vulns[0]['cve_id'] or vulns[0]['cnvd_id'] or vulns[0]['id']}.docx")
    return StreamingResponse(io.BytesIO(data), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                             headers={"Content-Disposition": f"attachment; filename={filename}"})
