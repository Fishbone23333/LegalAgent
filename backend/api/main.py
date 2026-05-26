"""FastAPI 主应用"""
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import io
import json
from urllib.parse import quote
from typing import AsyncGenerator

from agent import run_analysis, legal_agent_graph, guardrail_check, run_debate, debate_graph
from agent.debate_streaming import run_streaming_debate
from agent.prompts import SYSTEM_PROMPT
from agent.ocr import extract_contract_text_from_image, stream_ocr
from pdf_generator import build_debate_pdf

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "frontend"

app = FastAPI(
    title="LegalShield Agent API",
    description="AI法律护航卫士 - 合同风险分析API",
    version="1.0.0",
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境请限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def state_to_response(state) -> dict:
    """将AgentState转换为响应模型"""
    return {
        "success": state.get("is_valid_contract", False) and not state.get("error_message"),
        "contract_type": state.get("contract_type", "unknown"),
        "is_valid_contract": state.get("is_valid_contract", False),
        "segments": state.get("segments", []),
        "risks": state.get("risks", []),
        "action_plans": state.get("action_plans", []),
        "final_documents": state.get("final_documents", {}),
        "error_message": state.get("error_message", "")
    }


async def stream_agent_updates(
    raw_contract: str,
    user_id: str
) -> AsyncGenerator[str, None]:
    """流式执行Agent并产出中间状态"""
    
    # 步骤1：验证输入
    yield json.dumps({
        "type": "step",
        "step": "validating",
        "status": "running",
        "message": "正在验证合同文本...",
        "progress": 0.1
    }, ensure_ascii=False)
    await asyncio.sleep(0.3)
    
    is_contract, reason = guardrail_check(raw_contract)
    
    if not is_contract:
        yield json.dumps({
            "type": "step",
            "step": "rejected",
            "status": "error",
            "message": f"文本验证未通过：{reason}",
            "progress": 1.0
        }, ensure_ascii=False)
        return
    
    yield json.dumps({
        "type": "step",
        "step": "validated",
        "status": "done",
        "message": "合同文本验证通过",
        "progress": 0.15
    }, ensure_ascii=False)
    
    # 准备初始状态
    initial_state = {
        "raw_contract": raw_contract,
        "contract_type": "employment",
        "user_id": user_id,
        "segments": [],
        "risks": [],
        "action_plans": [],
        "final_documents": {},
        "current_step": "initial",
        "error_message": "",
        "is_valid_contract": True
    }
    
    # 步骤2：提取条款
    yield json.dumps({
        "type": "step",
        "step": "extracting",
        "status": "running",
        "message": "正在解析合同条款...",
        "progress": 0.2
    }, ensure_ascii=False)
    
    # 使用graph.stream获取中间状态
    async for event in legal_agent_graph.astream(initial_state):
        step_name = list(event.keys())[0] if event else "unknown"
        state = event.get(step_name, {})
        
        if step_name == "extractor":
            yield json.dumps({
                "type": "step",
                "step": "extracting",
                "status": "done",
                "message": f"条款解析完成，识别为{state.get('contract_type', 'unknown')}合同",
                "progress": 0.4,
                "contract_type": state.get("contract_type")
            }, ensure_ascii=False)
            await asyncio.sleep(0.2)
        
        elif step_name == "risk_checker":
            risk_count = len(state.get("risks", []))
            yield json.dumps({
                "type": "step",
                "step": "analyzing_risks",
                "status": "done",
                "message": f"风险分析完成，发现 {risk_count} 个风险点",
                "progress": 0.7,
                "risk_count": risk_count,
                "risks_preview": [
                    {"clause": r.get("clause", "")[:50], "risk_level": r.get("risk_level")}
                    for r in state.get("risks", [])[:3]
                ]
            }, ensure_ascii=False)
            await asyncio.sleep(0.2)
        
        elif step_name == "draft_generator":
            yield json.dumps({
                "type": "step",
                "step": "generating_documents",
                "status": "done",
                "message": "法律文书生成完成",
                "progress": 0.9
            }, ensure_ascii=False)
            await asyncio.sleep(0.2)
    
    # 最终结果
    yield json.dumps({
        "type": "result",
        "step": "complete",
        "status": "done",
        "message": "分析完成",
        "progress": 1.0
    }, ensure_ascii=False)


@app.post("/analyze")
async def analyze_contract(request: dict):
    """
    分析合同文本
    
    - **text**: 合同全文（最少20字符）
    - **user_id**: 用户标识（可选）
    
    返回完整的合同分析结果，包括风险点和法律建议。
    """
    try:
        text = request.get("text", "")
        user_id = request.get("user_id", "anonymous")
        
        # 验证输入
        if len(text.strip()) < 20:
            raise HTTPException(
                status_code=400,
                detail="合同文本过短，请提供完整的合同内容。"
            )
        
        # 执行分析
        result = run_analysis(text, user_id)
        response = state_to_response(result)
        
        if not response["success"] and response["error_message"]:
            raise HTTPException(
                status_code=400,
                detail=response["error_message"]
            )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"分析过程出错：{str(e)}"
        )


@app.post("/analyze/stream")
async def analyze_contract_stream(request: dict):
    """
    流式分析合同文本
    
    返回Server-Sent Events流，包含中间处理状态。
    """
    try:
        text = request.get("text", "")
        user_id = request.get("user_id", "anonymous")
        
        if len(text.strip()) < 20:
            raise HTTPException(
                status_code=400,
                detail="合同文本过短"
            )
        
        return StreamingResponse(
            stream_agent_updates(text, user_id),
            media_type="application/x-ndjson",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ═══════════════════════════════════════════════════════
#  红蓝对抗辩论 API（Multi-Agent）
# ═══════════════════════════════════════════════════════

def debate_state_to_response(state) -> dict:
    """将DebateState转换为响应模型"""
    return {
        "success": state.get("is_valid_contract", False) and not state.get("error_message"),
        "contract_type": state.get("contract_type", "unknown"),
        "is_valid_contract": state.get("is_valid_contract", False),
        "challenger_opening": state.get("challenger_opening", ""),
        "defender_response": state.get("defender_response", ""),
        "judge_verdict": state.get("judge_verdict", ""),
        "final_action_guide": state.get("final_action_guide", {}),
        "negotiation_scripts": state.get("negotiation_scripts", []),
        "error_message": state.get("error_message", ""),
    }


async def stream_debate_updates(
    raw_contract: str,
    user_id: str,
) -> AsyncGenerator[str, None]:
    """流式执行红蓝对抗辩论流程"""
    yield json.dumps({
        "type": "step", "step": "validating",
        "status": "running", "message": "正在验证合同文本...",
        "progress": 0.05
    }, ensure_ascii=False)
    await asyncio.sleep(0.3)

    is_contract, reason = guardrail_check(raw_contract)
    if not is_contract:
        yield json.dumps({
            "type": "step", "step": "rejected",
            "status": "error", "message": f"文本验证未通过：{reason}",
            "progress": 1.0
        }, ensure_ascii=False)
        return

    yield json.dumps({
        "type": "step", "step": "validated",
        "status": "done", "message": "合同文本验证通过，开始辩论...",
        "progress": 0.1
    }, ensure_ascii=False)

    # 构建初始状态
    initial_state = {
        "raw_contract": raw_contract,
        "contract_type": "employment",
        "user_id": user_id,
        "is_valid_contract": True,
        "error_message": "",
        "challenger_opening": "",
        "defender_response": "",
        "judge_verdict": "",
        "final_action_guide": {},
        "negotiation_scripts": [],
        "current_step": "initial",
    }

    # Challenger 阶段
    yield json.dumps({
        "type": "step", "step": "challenger",
        "status": "running", "message": "红方（应届生律师）正在挑刺...",
        "progress": 0.2
    }, ensure_ascii=False)

    async for event in debate_graph.astream(initial_state):
        step_name = list(event.keys())[0] if event else "unknown"
        state = event.get(step_name, {})

        if step_name == "challenger":
            yield json.dumps({
                "type": "step", "step": "challenger",
                "status": "done",
                "message": "红方完成，开篇陈词已生成",
                "progress": 0.4,
            }, ensure_ascii=False)
            await asyncio.sleep(0.2)

        elif step_name == "defender":
            challenger_data = state.get("challenger_opening", "")
            try:
                challenger_json = json.loads(challenger_data) if challenger_data else {}
                risk_count = len(challenger_json.get("risk_points", []))
                opening_snippet = challenger_json.get("opening_statement", "")[:80]
            except Exception:
                risk_count = 0
                opening_snippet = ""

            yield json.dumps({
                "type": "step", "step": "defender",
                "status": "done",
                "message": f"蓝方（企业法务）反驳完成，发现 {risk_count} 个风险点",
                "progress": 0.65,
                "challenger_snippet": opening_snippet,
            }, ensure_ascii=False)
            await asyncio.sleep(0.2)

        elif step_name == "judge":
            yield json.dumps({
                "type": "step", "step": "judge",
                "status": "done",
                "message": "裁决官完成，维权行动指南已生成",
                "progress": 0.88
            }, ensure_ascii=False)
            await asyncio.sleep(0.2)

        elif step_name == "negotiation":
            yield json.dumps({
                "type": "step", "step": "negotiation",
                "status": "done",
                "message": "逐条谈判话术已生成",
                "progress": 0.96
            }, ensure_ascii=False)
            await asyncio.sleep(0.2)

    # 最终结果
    yield json.dumps({
        "type": "result",
        "step": "complete",
        "status": "done",
        "message": "红蓝对抗辩论完成",
        "progress": 1.0
    }, ensure_ascii=False)


@app.post("/debate")
async def debate_contract(request: dict):
    """
    红蓝对抗辩论分析（同步）

    - **text**: 合同全文（最少20字符）
    - **user_id**: 用户标识（可选）
    """
    try:
        text = request.get("text", "")
        user_id = request.get("user_id", "anonymous")

        if len(text.strip()) < 20:
            raise HTTPException(
                status_code=400,
                detail="合同文本过短，请提供完整的合同内容。"
            )

        result = run_debate(text, user_id)
        response = debate_state_to_response(result)

        if not response["success"] and response["error_message"]:
            raise HTTPException(status_code=400, detail=response["error_message"])

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"辩论分析出错：{str(e)}")


@app.post("/debate/stream")
async def debate_contract_stream(request: dict):
    """
    红蓝对抗辩论分析（流式，推荐）

    返回 Server-Sent Events 流，逐 token 展示红方挑刺 → 蓝方反驳 → 裁决官定论。
    """
    try:
        text = request.get("text", "")
        user_id = request.get("user_id", "anonymous")

        if len(text.strip()) < 20:
            raise HTTPException(status_code=400, detail="合同文本过短")

        async def ndjson_stream():
            async for event in run_streaming_debate(text, user_id):
                yield json.dumps(event, ensure_ascii=False) + "\n"

        return StreamingResponse(
            ndjson_stream(),
            media_type="application/x-ndjson",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/debate/export-pdf")
async def export_debate_pdf(request: dict):
    """
    导出红蓝对抗辩论报告为 PDF（下载）

    将辩论结果生成为格式化的 PDF 文件返回。
    """
    from datetime import datetime

    try:
        result = request.get("result")
        if not result:
            raise HTTPException(status_code=400, detail="缺少辩论结果数据")

        pdf_bytes = build_debate_pdf(result)

        contract_type = result.get("contract_type", "unknown")
        type_map = {"employment": "劳动合同", "housing": "租赁合同", "unknown": "合同"}
        label = type_map.get(contract_type, "合同")
        now_str_ts = datetime.now().strftime("%Y%m%d%H%M")
        filename = f"{label}修改意见书_{now_str_ts}.pdf"
        filename_encoded = quote(filename)

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename_encoded}\"; filename*=UTF-8''{filename_encoded}",
                "Content-Length": str(len(pdf_bytes)),
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ocr")
async def ocr_contract_image(request: Request):
    """
    上传合同图片，AI 识别图片中的合同文本（同步）

    返回识别的合同文本，供后续分析使用。
    """
    try:
        body = await request.body()
        if not body:
            raise HTTPException(status_code=400, detail="请上传图片文件")

        result = await extract_contract_text_from_image(body)
        if not result["success"]:
            raise HTTPException(status_code=422, detail=result.get("error", "识别失败"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ocr/stream")
async def ocr_contract_image_stream(request: Request):
    """
    上传合同图片 → OCR 识别 → 直接进入红蓝对抗辩论。
    全程流式输出：OCR 进度 + 辩论进度在同一个 SSE 流里。

    前端传原始图片二进制（Content-Type: application/octet-stream 或 multipart/form-data）。
    """
    try:
        body = await request.body()
        if not body:
            raise HTTPException(status_code=400, detail="请上传图片文件")

        async def combined_stream():
            ocr_complete = False
            contract_text = ""
            async for ocr_event in stream_ocr(body):
                yield json.dumps(ocr_event, ensure_ascii=False) + "\n"
                if ocr_event.get("type") == "result":
                    contract_text = ocr_event.get("full_text", "")
                    ocr_complete = True
                    break
                # guardrail done 阶段也包含完整文本
                if ocr_event.get("step") == "guardrail" and ocr_event.get("status") == "done":
                    contract_text = ocr_event.get("full_text", "")
                    ocr_complete = True
                    break

            if ocr_complete and contract_text and len(contract_text) >= 20:
                from agent.debate_streaming import run_streaming_debate
                async for debate_event in run_streaming_debate(contract_text, "web-user-ocr"):
                    yield json.dumps(debate_event, ensure_ascii=False) + "\n"

        return StreamingResponse(
            combined_stream(),
            media_type="application/x-ndjson",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """健康检查"""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    provider = os.getenv("LLM_PROVIDER", "deepseek")
    model_env_map = {
        "deepseek": "DEEPSEEK_MODEL",
        "minimax": "MINIMAX_MODEL",
        "openai": "OPENAI_MODEL",
    }
    model = os.getenv(model_env_map.get(provider, "OPENAI_MODEL"), "unknown")
    return {
        "status": "healthy",
        "service": "LegalShield Agent",
        "provider": provider,
        "model": model
    }


@app.get("/")
async def root():
    """前端首页"""
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
