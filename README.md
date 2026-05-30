# 小白合同避坑助手

面向应届生、毕业生和刚步入社会人群的合同风险识别工具。项目聚焦两类高频场景：入职签劳动合同、租房签租赁合同，帮助用户在签字前快速发现不公平、违法或容易引发争议的条款，并生成可执行的修改建议、谈判话术和 PDF 报告。

> 免责声明：本项目生成的风险分析、修改建议、谈判话术和对话内容仅供教育与参考使用，不构成正式法律意见。涉及仲裁、诉讼、重大金额或紧急期限时，请咨询持证律师或当地法律援助机构。

## 核心能力

- **快速分析**：通过 Extractor、RiskChecker、DraftGenerator 完成合同有效性检查、条款抽取、风险判定和修订建议生成。
- **红蓝对抗分析**：红方 Challenger 站在用户立场挖掘风险，蓝方 Defender 模拟对方律师/法务/房东代理人的反驳，裁决官 Judge 综合双方观点给出判断。
- **三 Agent 追问**：红蓝对抗结束后，可分别与红方、蓝方、裁决官继续对话。三位 Agent 各自保留页面内聊天历史，并根据原合同和本轮分析上下文回答。
- **OCR 识别**：支持上传合同图片或扫描件，识别后自动填入输入框，但不会自动开始风险分析，用户确认文本后再手动分析。
- **PDF 导出**：快速分析和红蓝对抗分析都支持导出 PDF 报告，报告包含原始合同文本和当前页面对应的分析结果。
- **RAG 增强**：可选接入 Ollama Embedding + FAISS 本地法律知识库；Ollama 不可用时优雅降级，不影响主流程。
- **前端状态隔离**：快速分析和红蓝对抗分析的输入、进度、结果相互独立，切换模式不会重置另一个模式的分析过程或结果。

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 后端 | FastAPI、Pydantic、StreamingResponse |
| Agent 工作流 | LangGraph |
| LLM 接入 | LangChain ChatOpenAI 兼容接口，支持 DeepSeek / MiniMax |
| RAG | FAISS、Ollama Embedding、本地 `legal/` 法律知识库 |
| OCR | RapidOCR |
| PDF | ReportLab |
| 前端 | 原生 HTML / CSS / JavaScript，主页面为 `frontend/analysis.html` |

## 项目结构

```text
LegalAgent/
├─ backend/
│  ├─ agent/
│  │  ├─ graph.py              # 快速分析工作流
│  │  ├─ debate_graph.py       # 红蓝对抗工作流
│  │  ├─ debate_chat.py        # 红蓝分析后的三 Agent 追问
│  │  ├─ debate_streaming.py   # 红蓝对抗流式输出
│  │  └─ debate_nodes/         # Challenger / Defender / Judge 节点
│  ├─ api/
│  │  └─ main.py               # FastAPI 路由
│  ├─ rag/                     # 法律知识库加载、分块、索引、检索
│  ├─ main.py                  # 后端启动入口
│  ├─ pdf_generator.py         # PDF 报告生成
│  └─ requirements.txt
├─ frontend/
│  ├─ index.html               # 首页
│  └─ analysis.html            # 分析工作台
├─ legal/                      # 本地法律知识库
├─ docs/
│  └─ dev-log.md               # 开发日志
├─ opendesign/                 # OpenDesign 导出文件
├─ AGENTS.md                   # AI Agent 开发指南
└─ README.md
```

## 快速开始

### 1. 安装后端依赖

```powershell
cd D:\pyproject\LegalAgent\backend
pip install -r requirements.txt
```

### 2. 配置环境变量

复制示例文件并填写 API Key：

```powershell
copy .env.example .env
```

常用配置：

```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash

MINIMAX_API_KEY=
MINIMAX_BASE_URL=https://api.minimax.chat/v1
MINIMAX_MODEL=MiniMax-M2.7

HOST=0.0.0.0
PORT=8000
```

安全提醒：

- 不要提交真实 `.env`。
- 仓库只保留 `.env.example`。
- 当前 `.gitignore` 已忽略 `.env`、`*.env`、`backend/.env` 和本地 Codex 临时目录 `.codex/`。

### 3. 启动后端

```powershell
cd D:\pyproject\LegalAgent\backend
python main.py
```

或：

```powershell
uvicorn main:app --reload --port 8000
```

启动后访问：

- 首页：`http://localhost:8000/`
- 分析工作台：`http://localhost:8000/analysis.html`
- 健康检查：`http://localhost:8000/health`

## API 概览

### 快速分析

- `POST /analyze`：同步快速分析。
- `POST /analyze/stream`：流式返回 Guardrail、Extractor、RiskChecker、DraftGenerator 进度。
- `POST /analyze/export-pdf`：导出快速分析 PDF。

请求示例：

```json
{
  "text": "合同全文...",
  "user_id": "anonymous"
}
```

### 红蓝对抗

- `POST /debate`：同步红蓝对抗分析。
- `POST /debate/stream`：NDJSON 流式输出红方、蓝方、裁决官生成过程。
- `POST /debate/chat/stream`：红蓝对抗结束后，分别向红方、蓝方或裁决官追问。
- `POST /debate/export-pdf`：导出红蓝对抗 PDF。

追问请求示例：

```json
{
  "agent": "challenger",
  "question": "我应该优先和对方谈哪一条？",
  "context": {
    "raw_contract": "原始合同全文...",
    "contract_type": "housing",
    "challenger_opening": "...",
    "defender_response": "...",
    "judge_verdict": "...",
    "final_action_guide": {},
    "negotiation_scripts": []
  },
  "history": [
    { "role": "user", "content": "上一轮问题" },
    { "role": "assistant", "content": "上一轮回答" }
  ]
}
```

追问接口返回 NDJSON：

```json
{"type":"token","content":"..."}
{"type":"done"}
```

### OCR

- `POST /ocr`：同步 OCR 识别。
- `POST /ocr/stream`：流式 OCR 识别，前端显示识别进度并将结果填入输入框。

OCR 完成后不会自动开始风险分析，用户需要检查文本后再点击分析按钮。

## 前端工作流

1. 打开 `analysis.html`。
2. 选择“快速分析”或“红蓝对抗分析”。
3. 输入合同文本，或上传图片进行 OCR。
4. OCR 完成后检查识别文本，再手动开始分析。
5. 查看风险点、合同修订建议、谈判话术和三方观点。
6. 红蓝对抗完成后，可在三张 Agent 总结卡片下方继续向红方、蓝方或裁决官追问。
7. 分析完成后可下载 PDF 报告。

## RAG 法律知识库

RAG 是可选增强能力。没有启动 Ollama 或没有构建索引时，系统会跳过检索并继续调用 LLM 分析。

安装本地 embedding 模型：

```powershell
ollama pull nomic-embed-text
```

构建索引：

```powershell
cd D:\pyproject\LegalAgent\backend
python -m rag.build_index
```

相关环境变量：

```env
LEGAL_EMBEDDING_MODEL=nomic-embed-text
LEGAL_EMBEDDING_BASE_URL=http://localhost:11434
LEGAL_SEARCH_MODE=hybrid
```

## 风险判定参考

### 劳动合同

- 放弃社保/公积金：`critical`
- 违约金明显高于合理比例：`critical`
- 试用期超过 6 个月：`high`
- 竞业限制无补偿：`high`
- 加班无补偿或加班费约定不清：`medium`

### 租赁合同

- 无故克扣或不退押金：`critical`
- 押金超过 2 个月租金：`high`
- 提前退租赔偿超过 1 个月租金：`medium`
- 家电、设施维修责任全部转嫁给租客：`medium`
- 押金退还周期超过 15 个工作日：`low`

## PDF 报告内容

快速分析 PDF：

- 原始合同文本
- 合同类型
- 风险点汇总
- 行动优先级
- 合同修订建议

红蓝对抗 PDF：

- 原始合同文本
- 红方 / 蓝方 / 裁决官总结
- 风险点汇总
- 合同修订建议
- 谈判话术

长合同文本会被拆分为多个可分页文本块，避免 ReportLab 在单个 Table 单元格中触发 `Flowable too large`。

## 常见问题

### 前端无法连接后端

确认后端已启动在 `http://localhost:8000`，并访问 `/health` 检查服务状态。

### RAG 检索为空

确认 Ollama 已启动、`nomic-embed-text` 已安装，并已执行 `python -m rag.build_index`。如果没有配置 RAG，系统仍可运行，只是不会追加本地法条检索结果。

### PDF 中文乱码

确认 Windows 字体目录存在 `SimHei.ttf`、`msyh.ttc` 或 `simsun.ttc`。`pdf_generator.py` 会按候选字体自动注册中文字体。

### GitHub 推送前如何避免泄露密钥

执行：

```powershell
git status --short
git ls-files | Select-String -Pattern '(^|/|\\)\.env$|\.env\.'
```

确认真实 `.env` 没有出现在 Git 跟踪或暂存列表里。

## 开发日志

开发过程记录在：

```text
docs/dev-log.md
```

## License

MIT
