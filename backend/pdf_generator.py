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


# ─── 主生成函数 ───────────────────────────────────────────

def build_debate_pdf(debate_result: dict) -> bytes:
    """
    根据辩论结果 dict 生成 PDF，返回 PDF 字节数据。

    debate_result 字段结构（与 /debate 接口一致）：
        contract_type: str
        challenger_opening: str  (JSON)
        defender_response:  str  (JSON)
        judge_verdict:       str (JSON)
        final_action_guide:   dict
        negotiation_scripts: list
    """
    import json as _json

    S = _styles()

    # ── 解析 JSON 字段 ───────────────────────────────────
    challenger_data = {}
    try:
        challenger_data = _json.loads(debate_result.get("challenger_opening") or "{}")
    except Exception:
        pass

    judge_data = {}
    try:
        judge_data = _json.loads(debate_result.get("judge_verdict") or "{}")
    except Exception:
        pass

    action_guide = debate_result.get("final_action_guide") or {}
    contract_type_map = {
        "employment": "劳动合同",
        "housing":    "租赁合同",
        "unknown":    "合同",
    }
    contract_label = contract_type_map.get(
        debate_result.get("contract_type", "unknown"), "合同"
    )
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
    story.append(Paragraph(f"{contract_label}修改意见书", S["doc_title"]))
    story.append(Paragraph(f"生成时间：{now_str}  |  LegalShield 法律护航卫士", S["doc_subtitle"]))
    story.append(HRFlowable(width="100%", thickness=2, color=CLR_BLUE_ACCENT, spaceAfter=14))

    # ══ 发现的风险点 ════════════════════════════════════════
    risk_points = challenger_data.get("risk_points") or []
    if risk_points:
        story.append(_section_banner(
            "发现的风险点", CLR_RED_BG, CLR_RED_ACCENT, S))
        story.append(Spacer(1, 8))
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
        story.append(Spacer(1, 14))

    # ══ 认定为无效的条款 ═════════════════════════════════════
    void_clauses = judge_data.get("void_clauses") or []
    if void_clauses:
        story.append(_section_banner(
            "认定为无效的条款", CLR_RED_BG, CLR_RED_ACCENT, S))
        story.append(Spacer(1, 8))
        for vc in void_clauses:
            content = [
                Paragraph(f"<b>{_safe(vc.get('clause', ''))}</b>", S["body"]),
                Paragraph(f"<b>原因：</b>{_safe(vc.get('reason', ''))}", S["body_sm"]),
                Paragraph(f"<b>法律依据：</b>{_safe(vc.get('legal_basis', ''))}", S["body_sm"]),
                Paragraph(f"<b>维权行动：</b>{_safe(vc.get('action', ''))}", S["body_sm"]),
            ]
            story.append(KeepTogether(_card(content, bg=CLR_RED_BG)))
            story.append(Spacer(1, 6))
        story.append(Spacer(1, 14))

    # ══ 对当事人不利但暂不违法的条款 ═════════════════════════
    unfair_clauses = judge_data.get("unfair_but_legal") or []
    if unfair_clauses:
        story.append(_section_banner(
            "对当事人不利但暂不违法的条款", CLR_GOLD_BG, CLR_GOLD_ACCENT, S))
        story.append(Spacer(1, 8))
        for uc in unfair_clauses:
            content = [
                Table(
                    [[_risk_badge(uc.get("risk_level", "medium"), S),
                      Paragraph(f"<b>{_safe(uc.get('clause', ''))}</b>", S["body"])]],
                    colWidths=[2 * cm, 13.7 * cm]
                ),
                Paragraph(f"<b>谈判争取：</b>{_safe(uc.get('negotiation_point', ''))}", S["body_sm"]),
                Paragraph(f"<b>自我保护：</b>{_safe(uc.get('fallback', ''))}", S["body_sm"]),
            ]
            story.append(KeepTogether(_card(content, bg=CLR_GOLD_BG)))
            story.append(Spacer(1, 6))
        story.append(Spacer(1, 14))

    # ══ 逐条谈判话术 ═════════════════════════════════════════
    negotiation_scripts = debate_result.get("negotiation_scripts") or []
    if negotiation_scripts:
        story.append(Spacer(1, 8))
        story.append(_section_banner(
            "💬 逐条谈判话术", CLR_BLUE_BG, CLR_BLUE_ACCENT, S))
        story.append(Spacer(1, 8))
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
        story.append(Spacer(1, 14))

    # 维权行动指南
    action_plan = action_guide.get("action_plan") or {}
    if action_plan:
        story.append(Spacer(1, 8))
        story.append(_section_banner(
            "维权行动指南", CLR_GREEN_BG, CLR_GREEN_ACCENT, S))
        story.append(Spacer(1, 8))
        for phase_key, phase_label in [
            ("immediate",   "立即行动"),
            ("short_term", "短期措施"),
            ("if_dispute", "发生纠纷时"),
        ]:
            items = action_plan.get(phase_key) or []
            if not items:
                continue
            phase_rows = [[
                Paragraph(f"<b>{phase_label}</b>", S["body"]),
            ]]
            for idx, item in enumerate(items, 1):
                phase_rows.append([
                    Paragraph(f"  {idx}. {_safe(item)}", S["list_item"])
                ])
            story.append(_card(phase_rows, bg=CLR_GREEN_BG, padding=8))
            story.append(Spacer(1, 4))

    # 维权证据清单
    evidence_list = action_guide.get("evidence_checklist") or []
    if evidence_list:
        story.append(Spacer(1, 8))
        story.append(_section_banner(
            "维权证据清单", CLR_BLUE_BG, CLR_BLUE_ACCENT, S))
        story.append(Spacer(1, 8))
        for ev in evidence_list:
            content = [
                Paragraph(f"<b>证据名称：</b>{_safe(ev.get('evidence', ''))}", S["body"]),
                Paragraph(f"<b>获取方式：</b>{_safe(ev.get('how_to_collect', ''))}", S["body_sm"]),
            ]
            story.append(KeepTogether(_card(content, bg=CLR_GRAY_BG)))
            story.append(Spacer(1, 4))

    # ══ 页脚说明 ══════════════════════════════════════════
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=CLR_GRAY_BORDER))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "本修改意见书由 AI 自动生成，仅供参考，不构成正式法律意见。"
        "如有争议请咨询持证律师。",
        S["footer"]))

    # ── 构建 PDF ───────────────────────────────────────
    doc.build(story)
    return buf.getvalue()


def _safe(text: str) -> str:
    """转义 XML 特殊字符，防止 ReportLab 报错."""
    if not text:
        return ""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;"))
