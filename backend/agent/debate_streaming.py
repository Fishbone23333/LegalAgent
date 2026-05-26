"""流式辩论 Multi-Agent 工作流

使用异步生成器实现 token 级别的实时流式输出。
每个 Agent 的 LLM 调用使用 astream() 逐 token 推送到前端。
"""
import asyncio, json, re
from langgraph.graph import StateGraph, END
from agent.debate_state import DebateState
from agent.debate_nodes import challenger_node, defender_node, judge_node
from agent.guardrail import guardrail_check
from agent.llm_client import get_llm


def _parse_json(content: str) -> dict:
    """解析LLM返回的JSON响应"""
    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
    for prefix in ['```json\n', '```json', '```\n', '```']:
        if content.startswith(prefix):
            content = content[len(prefix):]
    if content.endswith('```'):
        content = content[:-3]
    content = content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        first_brace = content.find('{')
        last_brace = content.rfind('}')
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            try:
                return json.loads(content[first_brace:last_brace + 1])
            except json.JSONDecodeError:
                pass
    return {}


async def run_streaming_debate(raw_contract: str, user_id: str = "anonymous"):
    """
    异步生成器：流式运行红蓝对抗辩论。
    每个 token 实时 yield 到 SSE 流中。

    事件类型：
      type=start   — Agent 开始，content 为引导语
      type=token  — Agent 输出 token，content 为片段
      type=done   — Agent 完成，data 包含完整数据
      type=error  — 出错
      type=complete — 全部完成
    """
    # ── Guardrail ──────────────────────────────────────────
    is_contract, reason = guardrail_check(raw_contract)
    if not is_contract:
        yield {"type": "error", "agent": "system", "content": f"文本验证未通过：{reason}"}
        return

    # 状态由各阶段逐步构建
    challenger_opening = ""
    defender_response = ""
    judge_verdict = ""
    final_action_guide = {}
    contract_type = "unknown"

    # ══════════════════════════════════════════════════════
    #  Agent 1：Challenger 红方（应届生公益律师）
    # ══════════════════════════════════════════════════════
    yield {"type": "start", "agent": "challenger",
           "content": "🔴 红方律师正在审阅合同，寻找所有对你不利的条款...\n\n"}

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from agent.prompts.debate import CHALLENGER_PROMPT

        llm = get_llm(temperature=0.1)
        messages = [
            SystemMessage(content=CHALLENGER_PROMPT),
            HumanMessage(content=f"请分析以下合同文本：\n\n{raw_contract}"),
        ]

        full = ""
        async for token in llm.astream(messages):
            token_text = token.content if hasattr(token, 'content') else str(token)
            full += token_text
            yield {"type": "token", "agent": "challenger", "content": token_text}

        result = _parse_json(full)
        contract_type = result.get("contract_type", "unknown")
        challenger_opening = json.dumps({
            "risk_points": result.get("risk_points", []),
            "opening_statement": result.get("opening_statement", ""),
        }, ensure_ascii=False)

        yield {"type": "done", "agent": "challenger",
               "data": {"challenger_opening": challenger_opening,
                        "contract_type": contract_type}}

    except Exception as e:
        yield {"type": "error", "agent": "challenger",
               "content": f"红方分析出错：{str(e)}"}
        return

    # ══════════════════════════════════════════════════════
    #  Agent 2：Defender 蓝方（企业法务/中介）
    # ══════════════════════════════════════════════════════
    yield {"type": "start", "agent": "defender",
           "content": "\n\n🔵 蓝方法务收到质疑，逐条反驳中...\n\n"}

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from agent.prompts.debate import DEFENDER_PROMPT

        llm = get_llm(temperature=0.2)
        messages = [
            SystemMessage(content=DEFENDER_PROMPT),
            HumanMessage(content=f"红方（Challenger）对合同的质疑内容如下：\n\n{challenger_opening}\n\n请给出你的辩护和反驳。"),
        ]

        full = ""
        async for token in llm.astream(messages):
            token_text = token.content if hasattr(token, 'content') else str(token)
            full += token_text
            yield {"type": "token", "agent": "defender", "content": token_text}

        result = _parse_json(full)
        defender_response = json.dumps({
            "responses": result.get("responses", []),
            "overall_stance": result.get("overall_stance", ""),
        }, ensure_ascii=False)

        yield {"type": "done", "agent": "defender",
               "data": {"defender_response": defender_response}}

    except Exception as e:
        yield {"type": "error", "agent": "defender",
               "content": f"蓝方分析出错：{str(e)}"}
        return

    # ══════════════════════════════════════════════════════
    #  Agent 3：Judge 裁决官（首席仲裁员）
    # ══════════════════════════════════════════════════════
    yield {"type": "start", "agent": "judge",
           "content": "\n\n🟡 裁决官正在综合双方意见，撰写《维权行动指南》...\n\n"}

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from agent.prompts.debate import JUDGE_PROMPT

        llm = get_llm(temperature=0.1)
        debate_record = (
            f"【红方（Challenger）开篇陈词】\n{challenger_opening}\n\n"
            f"【蓝方（Defender）辩护与反驳】\n{defender_response}"
        )
        messages = [
            SystemMessage(content=JUDGE_PROMPT),
            HumanMessage(content=f"请根据以下红蓝双方辩论记录，做出客观裁决：\n\n{debate_record}"),
        ]

        full = ""
        async for token in llm.astream(messages):
            token_text = token.content if hasattr(token, 'content') else str(token)
            full += token_text
            yield {"type": "token", "agent": "judge", "content": token_text}

        result = _parse_json(full)
        judge_verdict = json.dumps({
            "verdict_summary": result.get("verdict_summary", ""),
            "void_clauses": result.get("void_clauses", []),
            "unfair_but_legal": result.get("unfair_but_legal", []),
        }, ensure_ascii=False)
        final_action_guide = {
            "action_plan": result.get("action_plan", {}),
            "evidence_checklist": result.get("evidence_checklist", []),
        }

        yield {"type": "done", "agent": "judge",
               "data": {
                   "judge_verdict": judge_verdict,
                   "final_action_guide": final_action_guide,
                   "contract_type": contract_type,
                   "challenger_opening": challenger_opening,
                   "defender_response": defender_response,
               }}

    except Exception as e:
        yield {"type": "error", "agent": "judge",
               "content": f"裁决出错：{str(e)}"}
        return

    # ══════════════════════════════════════════════════════
    #  Agent 4：Negotiation 谈判话术生成
    # ══════════════════════════════════════════════════════
    yield {"type": "start", "agent": "negotiation",
           "content": "\n\n💬 正在根据风险点生成逐条谈判话术...\n\n"}

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from agent.prompts.debate import NEGOTIATION_PROMPT

        llm = get_llm(temperature=0.5)
        challenger_data = json.loads(challenger_opening) if challenger_opening else {}
        risk_points = challenger_data.get("risk_points", [])

        if not risk_points:
            negotiation_scripts = []
        else:
            risk_summary_lines = []
            for i, rp in enumerate(risk_points):
                risk_summary_lines.append(
                    f"风险点{i+1}：{rp.get('clause','')}（等级：{rp.get('risk_level','')}）\n"
                    f"  影响：{rp.get('impact','')}\n"
                    f"  说明：{rp.get('severity_note','')}"
                )
            risk_summary = "\n\n".join(risk_summary_lines)
            contract_label = "租房合同" if contract_type == "housing" else "劳动合同"

            messages = [
                SystemMessage(content=NEGOTIATION_PROMPT),
                HumanMessage(
                    content=f"合同类型：{contract_label}\n\n发现的风险点如下：\n\n{risk_summary}\n\n请为每个风险点生成一条谈判话术："
                ),
            ]

            full = ""
            async for token in llm.astream(messages):
                token_text = token.content if hasattr(token, 'content') else str(token)
                full += token_text
                yield {"type": "token", "agent": "negotiation", "content": token_text}

            result = _parse_json(full)
            negotiation_scripts = result.get("scripts", [])

            for script in negotiation_scripts:
                idx = script.get("risk_index", -1)
                if idx >= 0 and idx < len(risk_points) and not script.get("clause"):
                    script["clause"] = risk_points[idx].get("clause", "")

        yield {"type": "done", "agent": "negotiation",
               "data": {"negotiation_scripts": negotiation_scripts}}

    except Exception as e:
        yield {"type": "error", "agent": "negotiation",
               "content": f"谈判话术生成出错：{str(e)}"}
        negotiation_scripts = []

    # 完成
    yield {"type": "complete", "agent": "system",
           "content": "\n\n✅ 辩论完成！正在整理结果...",
           "data": {
               "success": True,
               "contract_type": contract_type,
               "is_valid_contract": True,
               "challenger_opening": challenger_opening,
               "defender_response": defender_response,
               "judge_verdict": judge_verdict,
               "final_action_guide": final_action_guide,
               "negotiation_scripts": negotiation_scripts,
               "error_message": "",
           }}
