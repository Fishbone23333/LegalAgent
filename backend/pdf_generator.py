"""
合同红蓝对抗辩论报告 PDF 生成模块
"""
import io
import os
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ─── 注册中文字体 ──────────────────────────────────────
# 尝试多个常见中文字体，找第一个存在的
_CN_FONT = None
_FONT_CANDIDATES = [
    ("SimHei",       "C:\\Windows\\Fonts\\SimHei.ttf"),
    ("MicrosoftYaHei","C:\\Windows\\Fonts\\msyh.ttc"),
    ("SimSun",       "C:\\Windows\\Fonts\\simsun.ttc"),
    ("KaiTi",        "C:\\Windows\\Fonts\\simkai.ttf"),
]
for _name, _path in _FONT_CANDIDATES:
    if os.path.exists(_path):
        try:
            pdfmetrics.registerFont(TTFont(_name, _path))
            _CN_FONT = _name
            break
        except Exception:
            pass

# 回退到 Helvetica（无中文字体时不会崩溃，只是中文显示为方块）
FONT_NORMAL = _CN_FONT or "Helvetica"
FONT_BOLD   = _CN_FONT or "Helvetica-Bold"


# ─── 颜色常量 ────────────────────────────────────────────
CLR_RED_BG      = colors.HexColor("#FFCDD2")  # 浅红 → 稍深
CLR_RED_ACCENT  = colors.HexColor("#C62828")  # 深红强调
CLR_BLUE_BG     = colors.HexColor("#BBDEFB")  # 浅蓝 → 稍深
CLR_BLUE_ACCENT = colors.HexColor("#1565C0")  # 深蓝强调
CLR_GOLD_BG     = colors.HexColor("#FFE082")  # 浅黄 → 稍深
CLR_GOLD_ACCENT = colors.HexColor("#E65100")  # 深橙强调
CLR_GREEN_BG    = colors.HexColor("#C8E6C9")  # 浅绿 → 稍深
CLR_GREEN_ACCENT= colors.HexColor("#2E7D32")  # 深绿强调
CLR_GRAY_BG     = colors.HexColor("#F5F5F5")
CLR_GRAY_BORDER = colors.HexColor("#E0E0E0")
CLR_TEXT_DARK   = colors.HexColor("#212121")
CLR_TEXT_MEDIUM = colors.HexColor("#555555")
CLR_TEXT_LIGHT  = colors.HexColor("#757575")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()

    def ps(name: str, parent: str = "Normal", **kw) -> ParagraphStyle:
        return ParagraphStyle(name, parent=base[parent], **kw)

    return {
        "doc_title":   ps("doc_title",   fontSize=20, leading=26,
                           textColor=CLR_TEXT_DARK, spaceAfter=4,
                           fontName=FONT_BOLD, alignment=1),
        "doc_subtitle":ps("doc_subtitle",fontSize=11, leading=16,
                           textColor=CLR_TEXT_MEDIUM, spaceAfter=2,
                           fontName=FONT_NORMAL, alignment=1),
        "section_hdr": ps("section_hdr", fontSize=13, leading=18,
                           textColor=CLR_TEXT_DARK,
                           fontName=FONT_BOLD, spaceAfter=6),
        "subsection":  ps("subsection",  fontSize=11, leading=16,
                           textColor=CLR_TEXT_DARK,
                           fontName=FONT_BOLD, spaceAfter=4),
        "body":        ps("body",        fontSize=10, leading=15,
                           textColor=CLR_TEXT_DARK, spaceAfter=4,
                           fontName=FONT_NORMAL),
        "body_sm":     ps("body_sm",     fontSize=9,  leading=13,
                           textColor=CLR_TEXT_MEDIUM, spaceAfter=2,
                           fontName=FONT_NORMAL),
        "badge":       ps("badge",        fontSize=9,  leading=12,
                           textColor=CLR_TEXT_DARK,
                           fontName=FONT_BOLD),
        "footer":      ps("footer",      fontSize=8,  leading=12,
                           textColor=CLR_TEXT_LIGHT, alignment=1,
                           fontName=FONT_NORMAL),
        "verdict":     ps("verdict",     fontSize=11, leading=17,
                           textColor=CLR_TEXT_DARK, spaceAfter=6,
                           fontName=FONT_NORMAL),
        "list_item":   ps("list_item",   fontSize=10, leading=15,
                           textColor=CLR_TEXT_DARK, leftIndent=12, spaceAfter=3,
                           fontName=FONT_NORMAL),
    }


def _section_banner(text: str, bg: colors.Color, text_color: colors.Color,
                     styles: dict) -> Table:
    """返回一行彩色的 section 标题 Banner."""
    cell = Paragraph(text, styles["section_hdr"])
    tbl = Table([[cell]], colWidths=[16.5 * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), bg),
        ("TOPPADDING",  (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",(0, 0), (-1, -1), 12),
        ("ROUNDEDCORNERS", [6]),
    ]))
    return tbl


def _card(content: list, bg: colors.Color = CLR_GRAY_BG,
          padding: float = 10) -> Table:
    """通用卡片容器."""
    tbl = Table([[content]], colWidths=[16.5 * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), bg),
        ("TOPPADDING",   (0, 0), (-1, -1), padding),
        ("BOTTOMPADDING",(0, 0), (-1, -1), padding),
        ("LEFTPADDING",  (0, 0), (-1, -1), padding),
        ("RIGHTPADDING", (0, 0), (-1, -1), padding),
        ("BOX",          (0, 0), (-1, -1), 0.5, CLR_GRAY_BORDER),
    ]))
    return tbl


def _badge(label: str, bg: colors.Color, styles: dict) -> Table:
    p = Paragraph(label, styles["badge"])
    tbl = Table([[p]], colWidths=[2.5 * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), bg),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ROUNDEDCORNERS", [3]),
    ]))
    return tbl


def _risk_badge(level: str, styles: dict) -> Table:
    mapping = {
        "critical": (CLR_RED_ACCENT,   CLR_RED_BG),
        "high":     (CLR_GOLD_ACCENT,  CLR_GOLD_BG),
        "medium":   (colors.HexColor("#E65100"), CLR_GOLD_BG),
        "low":      (CLR_GREEN_ACCENT, CLR_GREEN_BG),
    }
    labels = {
        "critical": "致命",
        "high":     "高危",
        "medium":   "中危",
        "low":      "低危",
    }
    accent, bg = mapping.get(level, (CLR_TEXT_LIGHT, CLR_GRAY_BG))
    label = labels.get(level, level)
    return _badge(label, bg, styles)


def _two_col_row(left: Any, right: Any) -> Table:
    """左右两列布局."""
    tbl = Table([[left, right]], colWidths=[8.1 * cm, 8.4 * cm])
    tbl.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING",   (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
        ("LINEAFTER",    (0, 0), (0, -1),  0.5, CLR_GRAY_BORDER),
    ]))
    return tbl


def _contract_label(contract_type: str) -> str:
    """返回合同类型的中文名称."""
    contract_type_map = {
        "employment": "劳动合同",
        "housing": "租赁合同",
        "unknown": "合同",
    }
    return contract_type_map.get(contract_type, "合同")


def _risk_rank(level: Any) -> int:
    """返回风险等级排序权重."""
    return {
        "critical": 4,
        "high": 3,
        "medium": 2,
        "low": 1,
    }.get(str(level or "").lower(), 0)


def _parse_json_field(value: Any) -> dict:
    """兼容解析 JSON 字符串或 dict 字段."""
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        import json as _json
        return _json.loads(value)
    except Exception:
        return {}


def _safe_multiline(text: Any) -> str:
    """转义多行文本并保留换行."""
    return _safe(text).replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br/>")


def _split_pdf_text(text: Any, max_chars: int = 700, max_lines: int = 18) -> list[str]:
    """将长文本切成可放进单页卡片的小块，避免 ReportLab 单元格过高."""
    normalized = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    chunks: list[str] = []
    current_lines: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current_lines, current_len
        chunk = "\n".join(current_lines).strip()
        if chunk:
            chunks.append(chunk)
        current_lines = []
        current_len = 0

    def append_line(line: str) -> None:
        nonlocal current_len
        line_len = len(line)
        if current_lines and (
            current_len + line_len > max_chars
            or len(current_lines) >= max_lines
        ):
            flush()
        current_lines.append(line)
        current_len += line_len

    for raw_line in normalized.split("\n"):
        line = raw_line.strip()
        if not line:
            if current_lines and len(current_lines) < max_lines:
                current_lines.append("")
            continue

        while len(line) > max_chars:
            append_line(line[:max_chars])
            flush()
            line = line[max_chars:]
        append_line(line)

    flush()
    return chunks


def _append_raw_contract_section(story: list, raw_contract: str, styles: dict) -> None:
    """向 PDF story 追加原始合同文本."""
    if not raw_contract:
        return
    story.append(_section_banner("原始合同文本", CLR_GRAY_BG, CLR_TEXT_DARK, styles))
    story.append(Spacer(1, 8))
    for chunk in _split_pdf_text(raw_contract):
        story.append(_card([
            Paragraph(_safe_multiline(chunk), styles["body_sm"]),
        ], bg=colors.white, padding=9))
        story.append(Spacer(1, 5))
    story.append(Spacer(1, 14))


def _append_footer(story: list, styles: dict) -> None:
    """向 PDF story 追加统一免责声明页脚."""
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=CLR_GRAY_BORDER))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "本报告由 AI 自动生成，仅供教育和参考使用，不构成正式法律意见。"
        "如有争议请咨询持证律师。",
        styles["footer"]))


def build_analysis_pdf(analysis_result: dict) -> bytes:
    """
    根据快速分析结果 dict 生成 PDF，返回 PDF 字节数据。

    analysis_result 字段结构（与 /analyze 接口一致）：
        raw_contract: str
        contract_type: str
        risks: list
        action_plans: list
    """
    S = _styles()
    contract_label = _contract_label(analysis_result.get("contract_type", "unknown"))
    raw_contract = analysis_result.get("raw_contract") or analysis_result.get("text") or ""
    risks = sorted(
        analysis_result.get("risks") or [],
        key=lambda risk: _risk_rank(risk.get("risk_level")),
        reverse=True,
    )
    action_plans = analysis_result.get("action_plans") or []
    now_str = datetime.now().strftime("%Y年%m月%d日 %H:%M")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=2 * cm,
        encodings=['utf-8'],
    )

    story: list = []
    story.append(Paragraph(f"{contract_label}快速分析报告", S["doc_title"]))
    story.append(Paragraph(f"生成时间：{now_str}  |  LegalShield 法律护航卫士", S["doc_subtitle"]))
    story.append(HRFlowable(width="100%", thickness=2, color=CLR_BLUE_ACCENT, spaceAfter=14))

    _append_raw_contract_section(story, raw_contract, S)

    story.append(_section_banner("合同类型", CLR_BLUE_BG, CLR_BLUE_ACCENT, S))
    story.append(Spacer(1, 8))
    story.append(_card([
        Paragraph(f"<b>识别结果：</b>{_safe(contract_label)}", S["body"]),
        Paragraph(f"<b>风险点数量：</b>{len(risks)}", S["body_sm"]),
    ], bg=CLR_BLUE_BG, padding=8))
    story.append(Spacer(1, 14))

    story.append(_section_banner("风险点汇总", CLR_RED_BG, CLR_RED_ACCENT, S))
    story.append(Spacer(1, 8))
    if risks:
        for risk in risks:
            level = risk.get("risk_level", "low")
            risk_type = risk.get("risk_type", "风险条款")
            clause = risk.get("clause", "")
            basis = risk.get("legal_basis", "")
            recommendation = risk.get("recommendation", "")
            severity_note = risk.get("severity_note", "")

            rows = [[_risk_badge(level, S), Paragraph(f"<b>{_safe(risk_type)}</b>", S["body"])]]
            inner = Table(rows, colWidths=[2 * cm, 13.7 * cm])
            inner.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING",  (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING",   (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
            ]))
            card_content = [inner]
            if clause:
                card_content.append(Paragraph(f"<font color='#C62828'><b>涉及条款：</b></font>{_safe(clause)}", S["body_sm"]))
            if basis:
                card_content.append(Paragraph(f"<font color='#1565C0'><b>法律依据：</b></font>{_safe(basis)}", S["body_sm"]))
            if recommendation:
                card_content.append(Paragraph(f"<b>处理建议：</b>{_safe(recommendation)}", S["body_sm"]))
            if severity_note:
                card_content.append(Paragraph(f"<b>严重程度：</b>{_safe(severity_note)}", S["body_sm"]))
            story.append(KeepTogether(_card(card_content, bg=CLR_GRAY_BG)))
            story.append(Spacer(1, 6))
    else:
        story.append(_card([
            Paragraph("未发现明显风险点。仍建议在签署前核对主体、期限、金额、解除条件和附件材料。", S["body"]),
        ], bg=CLR_GRAY_BG, padding=8))
    story.append(Spacer(1, 14))

    story.append(_section_banner("行动优先级", CLR_GREEN_BG, CLR_GREEN_ACCENT, S))
    story.append(Spacer(1, 8))
    if action_plans:
        for idx, item in enumerate(action_plans, 1):
            story.append(_card([
                Paragraph(f"<b>{idx}. </b>{_safe(item)}", S["body"]),
            ], bg=CLR_GREEN_BG, padding=8))
            story.append(Spacer(1, 4))
    else:
        story.append(_card([
            Paragraph("暂无行动建议。", S["body"]),
        ], bg=CLR_GREEN_BG, padding=8))

    _append_footer(story, S)
    doc.build(story)
    return buf.getvalue()


def _build_debate_revision_suggestions(void_clauses: list, unfair_clauses: list) -> list[dict[str, str]]:
    """从裁决结果中整理统一的合同修订建议."""
    suggestions: list[dict[str, str]] = []
    for item in void_clauses:
        suggestions.append({
            "original_clause": item.get("clause") or item.get("issue") or "无效风险条款",
            "suggested_revision": item.get("action") or item.get("revision") or "建议删除该条款，或改为符合法律强制性规定的表述。",
            "reason": item.get("reason") or item.get("legal_basis") or "该条款可能违反强制性规定或明显加重用户责任。",
        })
    for item in unfair_clauses:
        suggestions.append({
            "original_clause": item.get("clause") or item.get("issue") or "不利但可谈判条款",
            "suggested_revision": item.get("negotiation_point") or item.get("action") or "建议改为更清晰、对等、可执行的表述。",
            "reason": item.get("reason") or item.get("legal_basis") or "该条款未必当然无效，但对用户明显不利，建议签署前争取调整。",
        })
    return [
        item for item in suggestions
        if item.get("original_clause") or item.get("suggested_revision") or item.get("reason")
    ]


# ─── 主生成函数 ───────────────────────────────────────────

def build_debate_pdf(debate_result: dict) -> bytes:
    """
    根据辩论结果 dict 生成 PDF，返回 PDF 字节数据。

    debate_result 字段结构（与 /debate 接口一致）：
        contract_type: str
        challenger_opening: str  (JSON)
        defender_response:  str  (JSON)
        judge_verdict:       str (JSON)
        negotiation_scripts: list
    """
    S = _styles()

    # ── 解析 JSON 字段 ───────────────────────────────────
    challenger_data = _parse_json_field(debate_result.get("challenger_opening"))
    defender_data = _parse_json_field(debate_result.get("defender_response"))
    judge_data = _parse_json_field(debate_result.get("judge_verdict"))

    contract_label = _contract_label(debate_result.get("contract_type", "unknown"))
    raw_contract = debate_result.get("raw_contract") or debate_result.get("text") or ""
    now_str = datetime.now().strftime("%Y年%m月%d日 %H:%M")

    # ── 准备 A4 文档 ────────────────────────────────────
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=2 * cm,
        encodings=['utf-8'],
    )

    story: list = []

    # ══ 封面标题 ══════════════════════════════════════════
    story.append(Paragraph(f"{contract_label}红蓝对抗分析报告", S["doc_title"]))
    story.append(Paragraph(f"生成时间：{now_str}  |  LegalShield 法律护航卫士", S["doc_subtitle"]))
    story.append(HRFlowable(width="100%", thickness=2, color=CLR_BLUE_ACCENT, spaceAfter=14))

    _append_raw_contract_section(story, raw_contract, S)

    # ══ 红方 / 蓝方 / 裁决官总结 ═════════════════════════════
    responses = defender_data.get("responses") or []
    first_response = responses[0] if responses and isinstance(responses[0], dict) else {}
    summary_rows = [
        ("红方 Challenger", challenger_data.get("opening_statement") or "暂无红方总结。", CLR_RED_BG),
        ("蓝方 Defender", defender_data.get("overall_stance") or first_response.get("justification") or "暂无蓝方总结。", CLR_BLUE_BG),
        ("裁决官 Judge", judge_data.get("verdict_summary") or "暂无裁决官总结。", CLR_GOLD_BG),
    ]
    story.append(_section_banner("红方 / 蓝方 / 裁决官总结", CLR_BLUE_BG, CLR_BLUE_ACCENT, S))
    story.append(Spacer(1, 8))
    for title, summary, bg in summary_rows:
        story.append(_card([
            Paragraph(f"<b>{_safe(title)}</b>", S["body"]),
            Paragraph(_safe_multiline(summary), S["body_sm"]),
        ], bg=bg, padding=8))
        story.append(Spacer(1, 6))
    story.append(Spacer(1, 8))

    # ══ 发现的风险点 ════════════════════════════════════════
    risk_points = sorted(
        challenger_data.get("risk_points") or [],
        key=lambda risk: _risk_rank(risk.get("risk_level")),
        reverse=True,
    )
    story.append(_section_banner(
        "发现的风险点", CLR_RED_BG, CLR_RED_ACCENT, S))
    story.append(Spacer(1, 8))
    if risk_points:
        for rp in risk_points:
            level  = rp.get("risk_level", "low")
            impact = rp.get("impact", "")
            clause = rp.get("clause", "")
            basis  = rp.get("legal_basis", "")
            note   = rp.get("severity_note", "")

            rows = [[_risk_badge(level, S),
                     Paragraph(f"<b>{impact}</b>", S["body"])]]
            inner = Table(rows, colWidths=[2 * cm, 13.7 * cm])
            inner.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING",  (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING",   (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
            ]))
            card_content = [inner]
            if clause:
                card_content.append(Paragraph(f"<font color='#C62828'><b>涉及条款：</b></font>{_safe(clause)}", S["body_sm"]))
            if basis:
                card_content.append(Paragraph(f"<font color='#1565C0'><b>法律依据：</b></font>{_safe(basis)}", S["body_sm"]))
            if note:
                card_content.append(Paragraph(f"<font color='#E65100'><b>严重程度：</b></font>{_safe(note)}", S["body_sm"]))
            story.append(KeepTogether(_card(card_content, bg=CLR_GRAY_BG)))
            story.append(Spacer(1, 6))
    else:
        story.append(_card([
            Paragraph("未发现明确风险点。", S["body"]),
        ], bg=CLR_GRAY_BG, padding=8))
    story.append(Spacer(1, 14))

    # ══ 合同修订建议 ════════════════════════════════════════
    void_clauses = judge_data.get("void_clauses") or []
    unfair_clauses = judge_data.get("unfair_but_legal") or []
    revision_suggestions = _build_debate_revision_suggestions(void_clauses, unfair_clauses)
    story.append(_section_banner(
        "合同修订建议", CLR_GREEN_BG, CLR_GREEN_ACCENT, S))
    story.append(Spacer(1, 8))
    if revision_suggestions:
        for item in revision_suggestions:
            content = [
                Paragraph(f"<b>原文：</b>{_safe(item.get('original_clause', ''))}", S["body_sm"]),
                Paragraph(f"<b>建议：</b>{_safe(item.get('suggested_revision', ''))}", S["body_sm"]),
                Paragraph(f"<b>理由：</b>{_safe(item.get('reason', ''))}", S["body_sm"]),
            ]
            story.append(KeepTogether(_card(content, bg=CLR_GREEN_BG)))
            story.append(Spacer(1, 6))
    else:
        story.append(_card([
            Paragraph("暂无合同修订建议。", S["body"]),
        ], bg=CLR_GREEN_BG, padding=8))
    story.append(Spacer(1, 14))

    # ══ 逐条谈判话术 ═════════════════════════════════════════
    negotiation_scripts = debate_result.get("negotiation_scripts") or []
    story.append(Spacer(1, 8))
    story.append(_section_banner(
        "逐条谈判话术", CLR_BLUE_BG, CLR_BLUE_ACCENT, S))
    story.append(Spacer(1, 8))
    if negotiation_scripts:
        for i, script in enumerate(negotiation_scripts):
            clause = script.get("clause", "")
            text  = script.get("script", "")
            card_content = []
            if clause:
                card_content.append(Paragraph(
                    f"<b>对应条款：</b><font color='#555555'>{_safe(clause)}</font>",
                    S["body_sm"]))
            card_content.append(Paragraph(_safe(text), S["body"]))
            story.append(KeepTogether(_card(card_content, bg=CLR_BLUE_BG)))
            story.append(Spacer(1, 6))
    else:
        story.append(_card([
            Paragraph("暂未生成谈判话术。", S["body"]),
        ], bg=CLR_BLUE_BG, padding=8))
    story.append(Spacer(1, 14))

    _append_footer(story, S)

    # ── 构建 PDF ───────────────────────────────────────
    doc.build(story)
    return buf.getvalue()


def _safe(text: Any) -> str:
    """转义 XML 特殊字符，防止 ReportLab 报错."""
    if text is None:
        return ""
    text = str(text)
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;"))
