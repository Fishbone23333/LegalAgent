"""LLM 客户端 - 支持多种模型提供商"""
import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()


def get_llm(
    model: str = None,
    temperature: float = 0.1,
    provider: str = None
):
    """
    获取LLM客户端
    
    Args:
        model: 模型名称（可选）
        temperature: 温度参数
        provider: 提供商 ('deepseek' / 'minimax' / 'openai')
    """
    provider = provider or os.getenv("LLM_PROVIDER", "deepseek")
    
    if provider == "minimax":
        return _get_minimax_llm(model, temperature)
    elif provider == "deepseek":
        return _get_deepseek_llm(model, temperature)
    else:
        return _get_openai_llm(model, temperature)


def _get_deepseek_llm(model: str = None, temperature: float = 0.1):
    return ChatOpenAI(
        model=model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        temperature=temperature,
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )


def _get_minimax_llm(model: str = None, temperature: float = 0.1):
    """MiniMax LLM (OpenAI兼容格式) - 设置足够大的max_tokens防止截断"""
    return ChatOpenAI(
        model=model or os.getenv("MINIMAX_MODEL", "MiniMax-M2.7"),
        temperature=temperature,
        api_key=os.getenv("MINIMAX_API_KEY"),
        base_url=os.getenv("MINIMAX_BASE_URL", "https://api.minimax.chat/v1"),
        max_tokens=8192,  # 增大token限制，防止JSON截断
    )


def _get_openai_llm(model: str = None, temperature: float = 0.1):
    return ChatOpenAI(
        model=model or "gpt-4",
        temperature=temperature,
    )
