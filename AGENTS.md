# LegalShield Agent - AI Agent 开发指南

> 本文档是 **LegalShield Agent（法律护航卫士）** 项目的核心开发指南，旨在为接手或扩展本项目的 AI Agent 提供完整的上下文、架构决策、代码规范和协作约定。
>
> **项目目标**：通过 LangGraph 构建具备闭环执行能力的 AI Agent，专门帮助应届生在求职（劳动合同）和租房（租赁合同）场景下识别合同风险并生成维权工具。
>
> **核心价值链**：Think（深度解析）→ Decide（法律判定）→ Execute（生成行动工具）

---

## 1. 项目愿景与核心原则

### 1.1 角色定位

系统的每一个 Agent 都应扮演一个**有经验、有立场、有温度**的法律专业人士，而非冷冰冰的条款检索机器。

| Agent | 角色 | 性格 | 职责边界 |
|-------|------|------|----------|
| Extractor | 合同条款提取专家 | 严谨、结构化 | 将非结构化文本转为 JSON 结构 |
| RiskChecker | 公益律师 | 极其敏锐、坚定 | 基于法律判定风险等级 |
| DraftGenerator | 法律文书专家 | 专业但务实 | 生成可直接使用的文档 |
| Challenger（红方） | 应届生公益律师 | 敏锐但温暖、立场坚定 | 穷尽一切找出不利条款 |
| Defender（蓝方） | 企业法务/中介 | 理性、冷静、专业 | 为条款提供合理化解释 |
| Judge（裁决官） | 首席仲裁员 | 客观、公正、权威 | 给出可操作的维权指南 |

### 1.2 核心开发原则

1. **JSON-first**：所有 Agent 输出必须是严格的 JSON 结构，即使 LLM 返回格式混乱，代码中也必须有健壮的容错解析逻辑。
2. **RAG 增强**：所有涉及法律判定的节点都应集成 RAG 检索，Ollama 不可用时必须优雅降级（返回空字符串，不崩溃）。
3. **流式优先**：所有 API 接口默认提供流式版本（`/stream`），提升用户体验。
4. **零信任输入**：Guardrail 检查是每个工作流的入口点，绝不跳过。
5. **可测试性**：每个节点函数是纯函数，输入 `state` → 输出 `state`，无副作用。

---

## 2. 技术栈速查

| 层级 | 技术选型 | 说明 |
|------|---------|------|
| Agent 框架 | LangGraph | Python，单 Agent 用 `StateGraph`，Multi-Agent 用独立 `Graph` |
| LLM 客户端 | LangChain `ChatOpenAI` | 通过 `api_key` + `base_url` 兼容 DeepSeek、MiniMax 等 |
| 后端框架 | FastAPI | 异步 API，支持 SSE 流式输出 |
| 向量数据库 | FAISS | 本地向量检索，配合 Ollama Embedding |
| 法律知识库 | `legal/` 目录下的 `.md` 文件 | 当前包含《中华人民共和国民法典》 |
| PDF 生成 | ReportLab | 中文支持（`SIMHEI.ttf`） |
| OCR | RapidOCR | 图片合同文本提取 |
| 环境管理 | `.env` 文件 | 不硬编码任何密钥 |

### 2.1 环境变量清单

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek API Key | - |
| `DEEPSEEK_BASE_URL` | API 地址 | `https://api.deepseek.com` |
| `MINIMAX_API_KEY` | MiniMax API Key | - |
| `MINIMAX_BASE_URL` | MiniMax API 地址 | `https://api.minimax.chat/v1` |
| `MINIMAX_MODEL` | MiniMax 模型名 | `MiniMax-M2.7` |
| `LLM_PROVIDER` | 当前使用的 Provider | `deepseek` |
| `OLLAMA_BASE_URL` | Ollama 服务地址（用于 RAG Embedding） | `http://localhost:11434` |
| `HOST` | 服务监听地址 | `0.0.0.0` |
| `PORT` | 服务端口 | `8000` |

---

## 3. 架构总览

```
┌────────────────────────────────────────────────────────────────────┐
│                          FastAPI 后端                               │
│  POST /analyze         POST /analyze/stream                         │
│  POST /debate          POST /debate/stream      POST /ocr/stream   │
└───────────────────────────────┬────────────────────────────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
          ▼                     ▼                     ▼
   ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
   │  单Agent模式 │      │ 红蓝对抗模式 │      │   RAG模块   │
   │  Extractor  │      │  Challenger │      │ (FAISS+Ollama│
   │  RiskChecker│      │  Defender   │      │  Legal KB)  │
   │  DraftGen   │      │  Judge      │      └─────────────┘
   └─────────────┘      │  Negotiation│
                        └─────────────┘
```

### 3.1 单 Agent 模式（快速分析）

工作流：`Guardrail` → `Extractor` → `RiskChecker` → `DraftGenerator`

- 入口：`agent/graph.py` → `run_analysis()`
- 状态：`agent/state.py` → `AgentState`（TypedDict）
- 特点：简单线性流程，适合快速初步分析

### 3.2 红蓝对抗模式（深度分析）

工作流：`Guardrail` → `Challenger` → `Defender` → `Judge` → `Negotiation`

- 入口：`agent/debate_graph.py` → `run_debate()`
- 状态：`agent/debate_state.py` → `DebateState`（dict 子类）
- 特点：多 Agent 协作，输出更全面的维权指南

### 3.3 RAG 模块（法律知识检索）

- 知识库来源：`legal/中华人民共和国民法典.md`（1797 行）
- 向量索引：`backend/data/faiss_index/`
- 检索方式：Hybrid（语义 + 关键词），按合同类型过滤
- **重要**：Ollama 服务不可用时，RAG 检索返回空字符串，整个系统仍能正常运行

---

## 4. 核心数据结构

### 4.1 AgentState（单 Agent 模式）

```python
class AgentState(TypedDict):
    raw_contract: str                              # 原始合同文本
    contract_type: Literal["employment", "housing", "unknown"]
    user_id: str
    segments: List[ContractSegment]               # 提取的条款模块
    risks: List[RiskPoint]                        # 风险点列表
    action_plans: List[str]                       # 行动建议
    final_documents: dict                         # 生成的法律文书
    current_step: str                             # 当前节点（流式输出用）
    error_message: str                             # 错误信息
    is_valid_contract: bool                       # 是否通过 Guardrail
```

### 4.2 DebateState（红蓝对抗模式）

```python
class DebateState(dict):
    raw_contract: str
    contract_type: Literal["employment", "housing", "unknown"]
    user_id: str
    is_valid_contract: bool
    error_message: str
    challenger_opening: str                        # 红方开篇陈词（JSON 字符串）
    defender_response: str                          # 蓝方反驳（JSON 字符串）
    judge_verdict: str                            # 裁决结果（JSON 字符串）
    final_action_guide: dict                     # 维权行动指南
    negotiation_scripts: list                    # 谈判话术
    current_step: str                             # 当前节点
```

### 4.3 RiskPoint 结构

```python
class RiskPoint(TypedDict):
    clause: str                                   # 涉及条款原文
    risk_level: Literal["low", "medium", "high", "critical"]
    risk_type: str                                # 风险类型描述
    legal_basis: str                              # 法律依据（具体法条）
    recommendation: str                          # 修改建议
    severity_note: str                           # 严重程度说明
```

---

## 5. 节点开发规范

### 5.1 节点函数签名

每个节点必须遵循以下签名：

```python
def node_name(state: StateType) -> StateType:
    """
    节点描述
    
    处理逻辑...
    
    Returns:
        更新后的 state（必须是新对象，用 {...state, ...} 语法）
    """
```

### 5.2 JSON 解析容错规范

每个节点在调用 LLM 后必须使用容错解析器处理响应：

```python
def _parse_json_response(content: str) -> dict:
    """解析 LLM 返回的 JSON 内容（容错版）
    
    处理逻辑：
    1. 去掉 <think>...</think> 标签块
    2. 去掉 ```json / ``` markdown 代码块包裹
    3. 尝试直接 json.loads()
    4. 失败则查找 { ... } 区间再尝试
    5. 最终失败返回空字典 {}
    """
    import re, json
    content = re.sub(r'<think>[\s\S]*?</think>', '', content)
    content = content.strip()
    if content.startswith('```json'): content = content[7:]
    elif content.startswith('```'): content = content[3:]
    if content.endswith('```'): content = content[:-3]
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
    return {}
```

**不要省略这步**。即使 Prompt 中明确要求 JSON 格式，LLM 仍可能返回带思考标签或格式偏差的内容。

### 5.3 RAG 检索集成规范

涉及法律判定的节点（`RiskChecker`、`Challenger`、`Defender`、`Judge`）必须集成 RAG 检索：

```python
def _retrieve_legal_provisions(
    contract_text: str,
    contract_type: str | None = None,
    top_k: int = 5
) -> str:
    """从法律知识库检索相关条文
    
    Returns:
        检索到的法律条文文本，如果 RAG 不可用则返回空字符串
    """
    try:
        from rag.legal_kb import get_legal_kb
        kb = get_legal_kb()
        kb.initialize()
    except Exception:
        return ""  # RAG 不可用时优雅降级

    try:
        return kb.search_as_text(
            query=contract_text[:500],
            top_k=top_k,
            mode="hybrid",
            contract_type=contract_type if contract_type != "unknown" else None,
        )
    except Exception:
        return ""
```

检索到的条文应追加到用户提示词中：

```python
user_content = f"请分析以下合同文本：\n\n{raw_text}"
if provisions and provisions != "未找到相关法律条文。":
    user_content = (
        f"【相关法律条文】（引用法条时优先使用以下条文）\n{provisions}\n\n"
        f"请分析以下合同文本：\n\n{raw_text}"
    )
```

---

## 6. Prompt 工程规范

### 6.1 Prompt 文件组织

```
backend/prompts/
├── __init__.py       # 统一导出所有 prompt 常量
├── core.py          # 单 Agent 模式提示词（Extractor / RiskChecker / DraftGenerator）
└── debate.py        # 红蓝对抗提示词（Challenger / Defender / Judge / Negotiation）
```

### 6.2 Prompt 设计原则

1. **明确角色背景**：每条 Prompt 第一段必须是角色设定，包含年限、专长、性格
2. **具体输出格式**：必须明确 JSON schema，给出每个字段的类型和说明
3. **法律引用要求**：Prompt 中应要求 Agent 引用具体法条（条文编号）
4. **风险判定规则显式化**：将风险判定规则（见第 7 节）完整写入 Prompt
5. **情商要求**：谈判话术类 Prompt 必须强调"高情商、不对抗、给台阶"

### 6.3 辩论系统 Prompt 设计

| 节点 | 核心策略 | 关键约束 |
|------|---------|---------|
| Challenger | 穷尽找茬，为弱势方说话 | 必须引用法条，区分风险等级 |
| Defender | 理性辩护，但承认合理关切 | 不要无原则偏袒，要给出改进建议 |
| Judge | 客观裁决，可操作性强 | 区分"无效条款"和"不利但合法条款" |
| Negotiation | 接地气，可直接复制发微信 | 3-5 句话，不说法律术语，给台阶 |

---

## 7. 风险判定规则（权威参考）

### 7.1 劳动合同

| 风险场景 | 判定等级 | 法律依据 |
|---------|---------|---------|
| 违约金 > 月薪 20% | **critical** | 《劳动合同法》第 22、23 条 |
| "自愿放弃社保/公积金" | **critical** | 《劳动法》第 72 条，《社会保险法》 |
| 试用期 > 6 个月 | **high** | 《劳动合同法》第 19 条 |
| 竞业限制无补偿金 | **high** | 《劳动合同法》第 23 条 |
| 加班无补偿约定 | **medium** | 《劳动法》第 44 条 |
| 解除合同条件显失公平 | **high** | 《劳动合同法》第 26 条 |

### 7.2 租赁合同

| 风险场景 | 判定等级 | 法律依据 |
|---------|---------|---------|
| 押金 > 2 个月租金 | **high** | 《民法典》第 587 条（定金上限） |
| 提前退租赔偿 > 1 个月租金 | **medium** | 《民法典》第 585 条 |
| 家电维修全由租客承担 | **medium** | 《民法典》第 713 条 |
| 押金退还时限 > 15 工作日 | **low** | 行业惯例 |
| 无故克扣押金条款 | **critical** | 《民法典》第 587 条 |
| 二房东无转租授权 | **high** | 《民法典》第 716 条 |

---

## 8. API 接口规范

### 8.1 接口列表

| 方法 | 路径 | 说明 | 推荐 |
|------|------|------|------|
| POST | `/analyze` | 单 Agent 同步分析 | |
| POST | `/analyze/stream` | 单 Agent 流式分析 | ✅ |
| POST | `/debate` | 红蓝对抗同步分析 | |
| POST | `/debate/stream` | 红蓝对抗流式分析 | ✅ |
| POST | `/debate/export-pdf` | 导出辩论报告 PDF | |
| POST | `/ocr` | OCR 合同图片（同步） | |
| POST | `/ocr/stream` | OCR + 辩论流式分析 | |
| GET | `/health` | 健康检查 | |

### 8.2 请求/响应模型

```python
class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=20)  # 合同全文
    user_id: str = Field(default="anonymous")

class AnalyzeResponse(BaseModel):
    success: bool
    contract_type: str
    is_valid_contract: bool
    segments: List[dict]
    risks: List[RiskPointResponse]
    action_plans: List[str]
    final_documents: dict
    error_message: str
```

### 8.3 SSE 流式输出格式

流式端点使用 Server-Sent Events，每个事件格式为：

```
event: step
data: {"step": "extractor", "status": "running", "message": "正在解析合同条款...", "progress": 0.25}

event: step
data: {"step": "risk_checker", "status": "done", "message": "风险分析完成", "progress": 0.75}

event: done
data: {"summary": "...", "contract_type": "employment"}
```

---

## 9. RAG 模块开发规范

### 9.1 模块结构

```
backend/rag/
├── loader.py       # 文档加载（MarkdownLoader）
├── chunker.py      # 文本分块（按章节 + 固定长度）
├── indexer.py      # 向量索引构建（FAISS + Ollama Embedding）
├── searcher.py     # 检索器（支持 hybrid 语义+关键词搜索）
├── legal_kb.py     # 法律知识库封装（initialize / search_as_text / search_as_docs）
└── build_index.py  # 索引构建脚本
```

### 9.2 索引构建流程

```bash
cd backend
python -m rag.build_index
```

要求 Ollama 服务运行且 Embedding 模型可用（默认 `nomic-embed-text`）。

### 9.3 检索 API

```python
from rag.legal_kb import get_legal_kb

kb = get_legal_kb()
kb.initialize()

# 检索相关条文（文本形式）
provisions = kb.search_as_text(
    query="违约金 试用期 竞业限制",
    top_k=5,
    mode="hybrid",          # "semantic" | "keyword" | "hybrid"
    contract_type="employment",  # "employment" | "housing" | None
)

# 检索相关条文（文档形式）
docs = kb.search_as_docs(
    query="押金 家电维修",
    top_k=3,
    mode="hybrid",
    contract_type="housing",
)
```

### 9.4 优雅降级

RAG 模块初始化或检索失败时，所有 Agent 节点必须能继续运行：

```python
try:
    kb = get_legal_kb()
    kb.initialize()
except Exception:
    provisions = ""  # 降级：跳过 RAG，直接用 LLM 内置知识
```

---

## 10. 前端集成规范

### 10.1 Web 前端

纯 HTML/CSS/JS 单文件应用（`frontend/index.html`），通过 Fetch API 调用后端。

**模式选择**：用户在首页选择「快速分析」（单 Agent）或「红蓝对抗」（Multi-Agent）模式。

**SSE 连接示例**：

```javascript
const eventSource = new EventSource(`/analyze/stream?text=${encodeURIComponent(text)}`);

eventSource.addEventListener("step", (e) => {
    const data = JSON.parse(e.data);
    updateProgress(data.step, data.progress, data.message);
});

eventSource.addEventListener("done", (e) => {
    const result = JSON.parse(e.data);
    displayResults(result);
    eventSource.close();
});

eventSource.addEventListener("error", (e) => {
    showError("分析过程出错，请重试");
    eventSource.close();
});
```

### 10.2 Flutter 前端（未完成）

项目目录 `frontend/` 下预留了 Flutter 项目结构，待开发。

---

## 11. 测试与调试

### 11.1 启动后端

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # 填写 API Key
python main.py
# 或
uvicorn main:app --reload --port 8000
```

### 11.2 启动 RAG（可选）

```bash
# 确保 Ollama 运行
ollama serve
# 构建法律知识库索引
python -m rag.build_index
```

### 11.3 测试 API

```bash
# 健康检查
curl http://localhost:8000/health

# 单 Agent 流式分析
curl -X POST http://localhost:8000/analyze/stream \
  -H "Content-Type: application/json" \
  -d '{"text": "劳动合同：甲方XXX公司，乙方XXX，试用期三个月...", "user_id": "test"}'

# 红蓝对抗流式分析
curl -X POST http://localhost:8000/debate/stream \
  -H "Content-Type: application/json" \
  -d '{"text": "租赁合同：甲方张房东...", "user_id": "test"}'
```

### 11.4 常见问题排查

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| JSON 解析失败 | LLM 返回了带思考标签的响应 | 检查 `_parse_json_response` 容错逻辑 |
| RAG 返回空 | Ollama 未运行 | 启动 `ollama serve`，或忽略（优雅降级） |
| 流式卡住 | LLM 调用超时 | 检查 API Key 和网络连接 |
| PDF 中文乱码 | 字体文件缺失 | 确保 `backend/data/fonts/SIMHEI.ttf` 存在 |

---

## 12. 代码风格约定

1. **类型注解**：所有函数参数和返回值必须有类型注解
2. **Docstring**：公共函数必须有 docstring，说明参数和返回值
3. **错误处理**：所有 LLM 调用必须包裹 `try/except`，错误信息写入 `state["error_message"]`
4. **状态更新**：节点必须返回新对象（`{**state, ...}`），不能原地修改
5. **命名规范**：
   - 文件名：小写下划线（`draft_generator.py`）
   - 类名：PascalCase（`AgentState`）
   - 函数名：小写下划线（`risk_checker_node`）
   - 常量：大写下划线（`CHALLENGER_PROMPT`）
6. **依赖导入**：内部导入用相对路径（`from agent.llm_client import get_llm`），外部导入用绝对路径

---

## 13. 扩展指南

### 13.1 添加新的合同类型

1. 在 `AgentState.contract_type` 和 `DebateState.contract_type` 的 `Literal` 类型中添加新类型
2. 在 `risk_checker.py` 的判定规则中添加新合同类型的风险规则
3. 在 `prompts/core.py` 的 `EXTRACTOR_PROMPT` 中添加新类型的提取规则
4. 在 `rag/legal_kb.py` 的检索过滤中添加新类型支持

### 13.2 添加新的 Agent 节点

1. 在 `agent/debate_graph.py` 中添加新节点函数
2. 在 `workflow.add_node()` 中注册节点
3. 在适当的位置添加 `workflow.add_edge()`
4. 在 `prompts/debate.py` 中编写新节点的 Prompt

### 13.3 更换 LLM 提供商

在 `agent/llm_client.py` 中扩展 `get_llm()` 函数，添加新的 provider 分支：

```python
def get_llm(provider: str = None, ...):
    provider = provider or os.getenv("LLM_PROVIDER", "deepseek")
    if provider == "your_provider":
        return _get_your_provider_llm(...)
    # ... 其他 provider
```

### 13.4 添加新的 API 端点

1. 在 `api/models.py` 中定义请求/响应 Pydantic 模型
2. 在 `api/main.py` 中添加新的路由函数
3. 如果需要流式输出，使用 `StreamingResponse` + `async generator`

---

## 14. 法律免责声明模板

项目所有法律相关内容仅供教育和参考使用，不能替代专业律师的法律咨询。生成的谈判话术和维权建议应作为辅助工具，最终决策应由用户自行负责或咨询持证律师。

---

*本文档由 AI Agent 根据 `D:/pyproject/LegalAgent` 项目源码自动生成。
如有不一致之处，请以实际代码为准。*
