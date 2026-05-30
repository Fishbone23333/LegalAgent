"""风险判定器 - 带 RAG 检索增强"""

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from agent.state import AgentState
from agent.llm_client import get_llm
from agent.prompts.core import RISK_CHECKER_PROMPT


def _parse_json_response(content: str) -> dict:
    """解析 LLM 返回的 JSON 内容"""
    content = re.sub(r'<think>[\s\S]*?</think>', '', content or '')
    content = content.strip()

    # 去掉 markdown 代码块
    if content.startswith('```json'):
        content = content[7:]
    elif content.startswith('```'):
        content = content[3:]
    if content.endswith('```'):
        content = content[:-3]
    content = content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    first_brace = content.find('{')
    last_brace = content.rfind('}')
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(content[first_brace:last_brace + 1])
        except json.JSONDecodeError:
            pass

    fixed = _fix_json_content(content)
    if fixed:
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass
    return {}


def _risk_rank(level: str) -> int:
    """返回风险等级排序权重。"""
    return {
        "critical": 4,
        "high": 3,
        "medium": 2,
        "low": 1,
    }.get(str(level or "").lower(), 0)


def _normalize_risks(value: Any) -> list[dict[str, str]]:
    """标准化 LLM 返回的风险点列表。"""
    if not isinstance(value, list):
        return []

    risks: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        level = str(item.get("risk_level", "low")).lower()
        if level not in {"low", "medium", "high", "critical"}:
            level = "low"
        risks.append({
            "clause": str(item.get("clause") or item.get("original_clause") or item.get("issue") or ""),
            "risk_level": level,
            "risk_type": str(item.get("risk_type") or item.get("type") or "合同风险"),
            "legal_basis": str(item.get("legal_basis") or "请结合具体条款核对相关法律规定。"),
            "recommendation": str(item.get("recommendation") or "建议签署前要求对方修改为更清晰、对等的表述。"),
            "severity_note": str(item.get("severity_note") or item.get("impact") or "该条款可能增加用户责任或维权难度。"),
        })
    return risks


def _normalize_action_plans(value: Any) -> list[str]:
    """标准化行动建议列表。"""
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _risk_text(state: AgentState) -> str:
    """拼接原文和结构化条款，供规则兜底扫描。"""
    parts = [state.get("raw_contract", "")]
    for seg in state.get("segments", []):
        if isinstance(seg, dict):
            parts.append(str(seg.get("title", "")))
            parts.append(str(seg.get("content", "")))
            parts.append(json.dumps(seg.get("key_items", {}), ensure_ascii=False))
    return "\n".join(part for part in parts if part)


def _compact_clause(text: str, max_len: int = 180) -> str:
    """压缩过长条款，避免兜底风险点占用过多页面空间。"""
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + "..."


def _find_clause(state: AgentState, pattern: str) -> str:
    """从结构化条款或原文中找到命中的片段。"""
    regex = re.compile(pattern, re.I)
    for seg in state.get("segments", []):
        if not isinstance(seg, dict):
            continue
        content = str(seg.get("content", ""))
        if regex.search(content):
            return _compact_clause(content)

    raw_text = state.get("raw_contract", "")
    match = regex.search(raw_text)
    if match:
        start = max(0, match.start() - 80)
        end = min(len(raw_text), match.end() + 120)
        return _compact_clause(raw_text[start:end])
    return ""


def _parse_number(text: str | None) -> float | None:
    """解析阿拉伯数字或常见中文数字。"""
    if not text:
        return None
    text = str(text).strip().replace(",", "")
    match = re.search(r"\d+(?:\.\d+)?", text)
    if match:
        value = float(match.group())
        if "万" in text:
            value *= 10000
        return value

    digits = {
        "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
        "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
    }
    text = text.replace("个", "").replace("月", "").replace("元", "")
    if text in digits:
        return float(digits[text])
    if text == "十":
        return 10.0
    if "十" in text:
        left, _, right = text.partition("十")
        tens = digits.get(left, 1) if left else 1
        ones = digits.get(right, 0) if right else 0
        return float(tens * 10 + ones)
    return None


def _extract_money(text: str, labels: list[str]) -> float | None:
    """提取指定标签附近的金额。"""
    label_pattern = "|".join(re.escape(label) for label in labels)
    pattern = re.compile(
        rf"(?:{label_pattern})[^0-9一二两三四五六七八九十万]{{0,30}}"
        rf"([0-9,]+(?:\.\d+)?|[一二两三四五六七八九十]+)\s*(万)?\s*元",
        re.I,
    )
    match = pattern.search(text)
    if not match:
        return None
    number_text = match.group(1) + (match.group(2) or "")
    return _parse_number(number_text)


def _add_rule_risk(
    risks: list[dict[str, str]],
    state: AgentState,
    pattern: str,
    risk_level: str,
    risk_type: str,
    legal_basis: str,
    recommendation: str,
    severity_note: str,
    clause: str = "",
) -> None:
    """向兜底风险列表追加一条命中规则。"""
    risks.append({
        "clause": clause or _find_clause(state, pattern) or risk_type,
        "risk_level": risk_level,
        "risk_type": risk_type,
        "legal_basis": legal_basis,
        "recommendation": recommendation,
        "severity_note": severity_note,
    })


def _rule_based_risks(state: AgentState) -> list[dict[str, str]]:
    """对明确高频风险做规则兜底，避免模型偶发漏判。"""
    contract_type = state.get("contract_type", "unknown")
    text = _risk_text(state)
    risks: list[dict[str, str]] = []

    if contract_type == "housing":
        rent = _extract_money(text, ["月租金", "每月租金", "租金", "房租"])
        deposit = _extract_money(text, ["押金", "保证金"])
        deposit_months = None
        pledge_match = re.search(r"押\s*([0-9一二两三四五六七八九十]+)\s*付", text)
        if pledge_match:
            deposit_months = _parse_number(pledge_match.group(1))
        elif rent and deposit:
            deposit_months = deposit / rent

        if deposit_months and deposit_months > 2:
            _add_rule_risk(
                risks, state, r"押金|保证金|押\s*[0-9一二两三四五六七八九十]\s*付",
                "high", "押金金额过高",
                "《民法典》第 587 条关于定金罚则及定金限额的规则可作为比例合理性参考。",
                "建议将押金调整为不超过两个月租金，并明确退还条件。",
                "押金过高会显著增加承租人资金占用和退租争议成本。",
            )

        early_quit = re.search(
            r"(提前退租|提前解除|退租)[^。；\n]{0,80}(赔偿|违约金|支付|扣除)[^。；\n]{0,40}"
            r"([0-9一二两三四五六七八九十]+)\s*(?:个)?月(?:租金|房租)",
            text,
        )
        if early_quit and (_parse_number(early_quit.group(3)) or 0) > 1:
            _add_rule_risk(
                risks, state, r"提前退租|提前解除|退租|违约金",
                "medium", "提前退租赔偿过高",
                "《民法典》第 585 条规定违约金过分高于损失的，可以请求适当减少。",
                "建议将提前退租违约责任限制为不超过一个月租金或按实际损失计算。",
                "过高违约金会限制正常退租，并可能导致押金被过度扣除。",
            )

        repair_pattern = (
            r"(家电|家具|设施|设备|维修)[^。；\n]{0,80}(全部|均|一切|所有|自行|自理)"
            r"[^。；\n]{0,40}(乙方|承租方|租客|租户)[^。；\n]{0,20}(承担|负责)"
            r"|((乙方|承租方|租客|租户)[^。；\n]{0,40}(承担|负责)[^。；\n]{0,40}"
            r"(全部|一切|所有)[^。；\n]{0,40}(家电|设施|设备|维修))"
        )
        if re.search(repair_pattern, text):
            _add_rule_risk(
                risks, state, repair_pattern,
                "medium", "维修责任过度转嫁",
                "《民法典》第 713 条规定出租人应当履行租赁物的维修义务，但当事人另有约定的除外。",
                "建议区分自然损耗、房屋主体及人为损坏责任，删除“全部由承租人承担”的表述。",
                "把全部维修责任交给承租人，会让自然损耗和房屋既有问题也由承租人买单。",
            )

        refund_days: float | None = None
        refund_pattern = (
            r"押金[^。；\n]{0,80}(退还|返还)[^。；\n]{0,60}?"
            r"([0-9一二两三四五六七八九十]+)\s*(?:个)?(工作日|日|天)"
            r"|([0-9一二两三四五六七八九十]+)\s*(?:个)?(工作日|日|天)"
            r"[^。；\n]{0,60}?(退还|返还)[^。；\n]{0,30}押金"
        )
        refund_match = re.search(refund_pattern, text)
        if refund_match:
            refund_days = _parse_number(refund_match.group(2) or refund_match.group(4))
        if refund_days and refund_days > 15:
            _add_rule_risk(
                risks, state, r"押金[^。；\n]{0,80}(退还|返还)|[0-9一二两三四五六七八九十]+\s*(?:个)?(工作日|日|天)[^。；\n]{0,60}(退还|返还)[^。；\n]{0,30}押金",
                "low", "押金退还周期过长",
                "押金退还期限虽主要依合同约定，但应遵循公平和诚实信用原则。",
                "建议约定退租验房并结清费用后 7-15 个工作日内退还押金。",
                "退还周期过长会拉长资金占用时间，也会增加追讨成本。",
            )

        deposit_deduct_pattern = (
            r"(无故|任意|单方|自行)[^。；\n]{0,20}(扣除|克扣|没收)[^。；\n]{0,20}押金"
            r"|押金[^。；\n]{0,30}(概不退还|不予退还|不退还)"
        )
        if re.search(deposit_deduct_pattern, text):
            _add_rule_risk(
                risks, state, deposit_deduct_pattern,
                "critical", "押金扣除条件不清或过严",
                "《民法典》第 587 条及公平原则要求扣款具有明确依据，不能任意扩大扣押范围。",
                "建议明确可扣款事项、举证责任、费用清单和剩余押金退还期限。",
                "押金扣除条件过宽会导致承租人退租时难以追回押金。",
            )

    if contract_type == "employment":
        social_pattern = (
            r"(自愿|同意|承诺)?[^。；\n]{0,30}(放弃|不缴纳|无需缴纳|不购买)[^。；\n]{0,20}"
            r"(社保|社会保险|公积金)|(社保|社会保险|公积金)[^。；\n]{0,20}"
            r"(放弃|不缴纳|无需缴纳)"
        )
        if re.search(social_pattern, text):
            _add_rule_risk(
                risks, state, social_pattern,
                "critical", "放弃社保或公积金约定",
                "《劳动法》第 72 条及社会保险相关规定要求依法参加社会保险。",
                "建议删除放弃社保/公积金表述，改为由用人单位依法足额缴纳。",
                "社保缴纳属于法定义务，不能通过员工承诺放弃来免除。",
            )

        probation_match = re.search(
            r"试用期[^。；\n]{0,30}([0-9一二两三四五六七八九十]+)\s*(年|个?月)",
            text,
        )
        if probation_match:
            number = _parse_number(probation_match.group(1)) or 0
            months = number * 12 if "年" in probation_match.group(2) else number
            if months > 6:
                _add_rule_risk(
                    risks, state, r"试用期",
                    "high", "试用期超过法定上限",
                    "《劳动合同法》第 19 条规定试用期最长不得超过六个月。",
                    "建议将试用期调整到法定上限以内，并与劳动合同期限匹配。",
                    "过长试用期会压低劳动者稳定性和权益保护。",
                )

        for seg in state.get("segments", []):
            content = str(seg.get("content", "")) if isinstance(seg, dict) else ""
            if "竞业" in content and not re.search(r"补偿|经济补偿|补偿金", content):
                _add_rule_risk(
                    risks, state, r"竞业",
                    "high", "竞业限制缺少补偿",
                    "《劳动合同法》第 23 条要求竞业限制期间按月给予劳动者经济补偿。",
                    "建议明确竞业限制范围、期限和按月经济补偿标准。",
                    "没有补偿的竞业限制会过度限制离职后的就业自由。",
                    clause=_compact_clause(content),
                )
                break

        overtime_pattern = (
            r"加班[^。；\n]{0,40}(无|不|不再|无需)[^。；\n]{0,20}(补偿|加班费|调休)"
            r"|加班费[^。；\n]{0,20}(包含|已含)[^。；\n]{0,20}(工资|薪资)"
        )
        if re.search(overtime_pattern, text):
            _add_rule_risk(
                risks, state, overtime_pattern,
                "medium", "加班补偿约定不明确或被排除",
                "《劳动法》第 44 条规定延长工作时间、休息日和法定节假日加班应支付相应报酬。",
                "建议明确加班审批、调休和加班费计算标准。",
                "排除加班补偿会增加后续主张加班费的举证难度。",
            )

        salary = _extract_money(text, ["月薪", "工资", "薪资", "基本工资"])
        penalty = _extract_money(text, ["违约金"])
        if salary and penalty and penalty > salary * 0.2:
            _add_rule_risk(
                risks, state, r"违约金|月薪|工资|薪资",
                "critical", "违约金金额明显过高",
                "《劳动合同法》第 22、23 条限制劳动合同中违约金适用范围和金额。",
                "建议删除不合法违约金，或限于培训服务期、竞业限制等法定场景并按实际损失计算。",
                "高额违约金可能不合法，也会压制劳动者正常离职权利。",
            )

    return risks


def _merge_risks(model_risks: list[dict[str, str]], fallback_risks: list[dict[str, str]]) -> list[dict[str, str]]:
    """合并模型风险和规则兜底风险，按严重程度排序。"""
    merged: list[dict[str, str]] = []
    seen: set[str] = set()
    for risk in [*model_risks, *fallback_risks]:
        key = f"{risk.get('risk_type', '')}|{risk.get('clause', '')[:60]}"
        broad_key = str(risk.get("risk_type", ""))
        if key in seen or broad_key in seen:
            continue
        seen.add(key)
        seen.add(broad_key)
        merged.append(risk)
    return sorted(merged, key=lambda item: _risk_rank(item.get("risk_level", "")), reverse=True)


def _fallback_action_plans(risks: list[dict[str, str]]) -> list[str]:
    """在模型没有给出行动建议时，根据风险点生成简短行动项。"""
    return [
        risk["recommendation"]
        for risk in sorted(risks, key=lambda item: _risk_rank(item.get("risk_level", "")), reverse=True)
        if risk.get("recommendation")
    ][:3]


def _fix_json_content(content: str) -> str | None:
    """尝试修复不完整的 JSON 内容"""
    lines = content.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('//') or stripped.startswith('#'):
            continue
        cleaned_lines.append(line)
    content = '\n'.join(cleaned_lines)

    start = content.find('{"')
    end = content.rfind('"}') + 2
    if start == -1 or end == -1:
        start = content.find('{')
        end = content.rfind('}') + 1
    if start != -1 and end > start:
        return content[start:end]
    return None


def _retrieve_legal_provisions(state: AgentState, top_k: int = 5) -> str:
    """
    根据合同条款内容，从法律知识库检索相关法条。
    若 RAG 模块未初始化（Ollama 未运行），返回空字符串。
    """
    try:
        from rag.legal_kb import get_legal_kb
        kb = get_legal_kb()
        kb.initialize()
    except Exception:
        return ""

    contract_type = state.get("contract_type", "unknown")
    segments = state.get("segments", [])

    if not segments:
        return ""

    # 从条款内容中构造检索 query
    # 取前 3 个条款的 title + content 组合作为检索 query
    query_parts = []
    for seg in segments[:3]:
        title = seg.get("title", "")
        content = seg.get("content", "")[:200]
        if title:
            query_parts.append(f"{title} {content}")
        else:
            query_parts.append(content[:200])
    query = " | ".join(query_parts)

    try:
        provisions_text = kb.search_as_text(
            query=query,
            top_k=top_k,
            mode="hybrid",
            contract_type=contract_type if contract_type != "unknown" else None,
        )
        return provisions_text
    except Exception:
        return ""


def risk_checker_node(state: AgentState) -> AgentState:
    """节点B: 风险判定器（RAG 增强版）"""
    contract_type = state.get("contract_type", "unknown")
    segments = state.get("segments", [])

    if contract_type == "unknown" or not segments:
        return {
            **state,
            "risks": [],
            "action_plans": [],
            "current_step": "risk_checker_done",
            "error_message": "",
        }

    try:
        llm = get_llm(temperature=0.1)
        segments_text = json.dumps(segments, ensure_ascii=False, indent=2)

        # RAG: 检索相关法律条文
        provisions = _retrieve_legal_provisions(state, top_k=5)

        # 构建提示词
        user_content = f"合同类型：{contract_type}\n\n"
        if provisions and provisions != "未找到相关法律条文。":
            user_content += f"【相关法律条文】（以下条文仅供参考，最终判定请结合具体条款）\n{provisions}\n\n"
        user_content += f"条款内容：\n{segments_text}\n\n请进行风险判定。"

        messages = [
            SystemMessage(content=RISK_CHECKER_PROMPT),
            HumanMessage(content=user_content),
        ]

        response = llm.invoke(messages)
        result = _parse_json_response(response.content)
        risks = _merge_risks(
            _normalize_risks(result.get("risks", [])),
            _rule_based_risks(state),
        )
        action_plans = _normalize_action_plans(result.get("action_plans", []))
        if not action_plans and risks:
            action_plans = _fallback_action_plans(risks)

        return {
            **state,
            "risks": risks,
            "action_plans": action_plans,
            "current_step": "risk_checker_done",
            "error_message": "",
        }

    except Exception as e:
        return {
            **state,
            "risks": [],
            "action_plans": [],
            "current_step": "risk_checker_done",
            "error_message": f"风险分析出错：{str(e)}",
        }
