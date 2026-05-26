"""OCR 合同图片识别模块

使用 RapidOCR（本地 OnnxRuntime OCR）从合同图片中提取文本内容。
支持 jpg/png/webp/bmp/tiff 格式。无需 API Key，完全本地运行。
"""

import os
import json
import re
from io import BytesIO
from typing import Optional

from PIL import Image


# ─────────────────────────────────────────────
# 图片预处理
# ─────────────────────────────────────────────

def validate_image(file_bytes: bytes) -> tuple[bool, str]:
    """验证图片格式和大小"""
    max_size_mb = 10
    if len(file_bytes) > max_size_mb * 1024 * 1024:
        return False, f"图片大小不能超过 {max_size_mb}MB"

    allowed = {"JPEG", "PNG", "WEBP", "BMP", "TIFF"}
    try:
        img = Image.open(BytesIO(file_bytes))
        if img.format not in allowed:
            return False, f"不支持的图片格式: {img.format}，仅支持 {', '.join(allowed)}"
        return True, ""
    except Exception as e:
        return False, f"无法识别图片格式：{str(e)}"


def compress_image(file_bytes: bytes, max_dim: int = 2048) -> bytes:
    """压缩图片，防止超大图片导致 OCR 失败"""
    try:
        img = Image.open(BytesIO(file_bytes))
        w, h = img.size
        if max(w, h) <= max_dim:
            return file_bytes

        ratio = max_dim / max(w, h)
        new_w, new_h = int(w * ratio), int(h * ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        buf = BytesIO()
        fmt = img.format or "JPEG"
        img.save(buf, format=fmt, quality=85)
        return buf.getvalue()
    except Exception:
        return file_bytes


# ─────────────────────────────────────────────
# RapidOCR 初始化（延迟加载，首次调用时初始化）
# ─────────────────────────────────────────────

_rapid_ocr = None


def _get_rapid_ocr():
    """获取 RapidOCR 实例（单例，延迟初始化）"""
    global _rapid_ocr
    if _rapid_ocr is None:
        from rapidocr_onnxruntime import RapidOCR
        _rapid_ocr = RapidOCR()
    return _rapid_ocr


def _detect_contract_type(text: str) -> str:
    """根据文本内容判断合同类型"""
    text_lower = text.lower()
    employment_keywords = ["劳动合同", "甲方", "乙方", "用人单位", "劳动者", "月薪", "工资", "试用期", "社保", "劳动合同法", "职位", "岗位"]
    housing_keywords = ["租赁合同", "出租人", "承租人", "租金", "押金", "房屋", "租赁", "房东", "中介", "月租", "物业费", "租房"]

    employment_score = sum(1 for kw in employment_keywords if kw in text_lower)
    housing_score = sum(1 for kw in housing_keywords if kw in text_lower)

    if employment_score > housing_score:
        return "employment"
    elif housing_score > employment_score:
        return "housing"
    else:
        return "unknown"


# ─────────────────────────────────────────────
# OCR 核心逻辑
# ─────────────────────────────────────────────

def extract_contract_text_from_image(file_bytes: bytes) -> dict:
    """
    提取合同文本（同步版本）。

    Args:
        file_bytes: 图片二进制数据

    Returns:
        {
            "success": bool,
            "contract_type": str,
            "full_text": str,
            "confidence": float,
            "warning": str,
            "error": str
        }
    """
    # 验证
    ok, err = validate_image(file_bytes)
    if not ok:
        return {"success": False, "contract_type": "", "full_text": "", "confidence": 0.0, "warning": "", "error": err}

    # 压缩
    compressed = compress_image(file_bytes)

    try:
        ocr = _get_rapid_ocr()
        result, elapsed = ocr(compressed)

        if not result or len(result) == 0:
            return {
                "success": False,
                "contract_type": "unknown",
                "full_text": "",
                "confidence": 0.0,
                "warning": "未在图片中识别到文字",
                "error": "图片中未识别到有效文字"
            }

        # 合并所有识别结果
        lines = []
        total_confidence = 0.0
        for item in result:
            # RapidOCR 返回格式: [box, text, confidence]
            text = item[1].strip()
            if text:
                lines.append(text)
                total_confidence += item[2]  # confidence

        full_text = "\n".join(lines)
        avg_confidence = total_confidence / len(result) if result else 0.0

        if not full_text or len(full_text.strip()) < 10:
            return {
                "success": False,
                "contract_type": "unknown",
                "full_text": "",
                "confidence": avg_confidence,
                "warning": "识别出的文字过少，可能图片质量较差",
                "error": "图片中未识别到有效合同文本"
            }

        contract_type = _detect_contract_type(full_text)

        return {
            "success": True,
            "contract_type": contract_type,
            "full_text": full_text,
            "confidence": avg_confidence,
            "warning": "",
            "error": ""
        }

    except Exception as e:
        return {
            "success": False,
            "contract_type": "",
            "full_text": "",
            "confidence": 0.0,
            "warning": "",
            "error": f"OCR 处理失败：{str(e)}"
        }


# ─────────────────────────────────────────────
# 流式 OCR
# ─────────────────────────────────────────────

async def stream_ocr(file_bytes: bytes):
    """
    流式 OCR：逐步输出识别进度。
    """
    # Step 1: 验证
    ok, err = validate_image(file_bytes)
    if not ok:
        yield {"type": "step", "step": "validating", "status": "error", "message": err, "progress": 0.1}
        return

    yield {"type": "step", "step": "validating", "status": "done", "message": "图片格式验证通过", "progress": 0.15}

    # Step 2: 压缩
    compressed = compress_image(file_bytes)
    yield {"type": "step", "step": "compressing", "status": "done", "message": "图片预处理完成", "progress": 0.2}

    # Step 3: OCR 识别
    yield {"type": "step", "step": "ocr", "status": "running", "message": "RapidOCR 正在识别合同文字...", "progress": 0.3}

    # 同步调用 RapidOCR（已有 asyncio 兼容）
    import asyncio
    result = await asyncio.to_thread(extract_contract_text_from_image, compressed)

    if not result["success"]:
        yield {
            "type": "step", "step": "ocr", "status": "error",
            "message": result.get("error", "识别失败"),
            "progress": 1.0
        }
        return

    text_preview = result["full_text"][:100] + "..." if len(result["full_text"]) > 100 else result["full_text"]
    yield {
        "type": "step", "step": "ocr", "status": "done",
        "message": f"文本提取完成（{len(result['full_text'])}字符），正在启动分析...",
        "progress": 0.7,
        "text_preview": text_preview,
        "contract_type": result["contract_type"],
        "confidence": result["confidence"],
    }

    # Step 4: Guardrail 检查
    yield {"type": "step", "step": "guardrail", "status": "running", "message": "正在验证合同内容...", "progress": 0.8}
    from agent.guardrail import guardrail_check
    is_contract, reason = guardrail_check(result["full_text"])

    if not is_contract:
        yield {
            "type": "step", "step": "guardrail", "status": "error",
            "message": f"合同验证未通过：{reason}",
            "progress": 1.0,
            "full_text": result["full_text"],
        }
        return

    yield {
        "type": "step", "step": "guardrail", "status": "done",
        "message": "合同内容验证通过",
        "progress": 0.9,
        "full_text": result["full_text"],
        "contract_type": result["contract_type"],
        "confidence": result["confidence"],
        "warning": result.get("warning", ""),
    }

    # 完成
    yield {
        "type": "result",
        "step": "complete",
        "status": "done",
        "message": "图片识别完成",
        "progress": 1.0,
        "full_text": result["full_text"],
        "contract_type": result["contract_type"],
        "confidence": result["confidence"],
        "warning": result.get("warning", ""),
    }
