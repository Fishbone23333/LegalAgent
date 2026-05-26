# LegalShield Agent - 法律护航卫士

AI Agent 开发指南项目，专门帮助应届生解决求职（劳动合同）和租房（租赁合同）场景下的法律问题。

## 项目特性

- **Think**: 深度解析合同条款，提取关键权责
- **Decide**: 基于现行法律（劳动法、民法典）判定潜在风险
- **Execute**: 自动生成法律交涉文案、修订建议或标准的维权存证文档

## 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                      Web 前端 (HTML/CSS/JS)               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │  首页（模式   │  │  分析页    │  │  辩论/结果页 │   │
│  │  选择）      │  │           │  │             │   │
│  └─────────────┘  └─────────────┘  └─────────────┘   │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP/SSE
┌────────────────────────┴────────────────────────────────┐
│                   FastAPI 后端                            │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ /analyze   │  │ /debate      │  │ Guardrail    │    │
│  │ (单Agent)  │  │ (Multi-Agent)│  │ 输入验证     │    │
│  └────────────┘  └──────────────┘  └──────────────┘    │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────┐
│            LangGraph Agent / Multi-Agent 系统             │
│                                                        │
│  单Agent模式:                                          │
│  Extractor ──▶ RiskChecker ──▶ DraftGenerator         │
│                                                        │
│  红蓝对抗模式 (Multi-Agent):                           │
│  Challenger ──▶ Defender ──▶ Judge ──▶ 维权行动指南    │
│  (红方律师)    (蓝方法务)  (裁决官)                    │
└─────────────────────────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────┐
│                    LLM (MiniMax M2.7)                  │
└─────────────────────────────────────────────────────────┘
```

## 项目结构

```
LegalAgent/
├── backend/                    # Python 后端
│   ├── agent/                  # Agent 核心逻辑
│   │   ├── state.py           # 单Agent状态定义
│   │   ├── debate_state.py    # 红蓝对抗状态定义
│   │   ├── graph.py           # 单Agent工作流
│   │   ├── debate_graph.py    # 红蓝对抗工作流
│   │   ├── extractor.py       # 提取器节点
│   │   ├── risk_checker.py    # 风险判定节点
│   │   ├── draft_generator.py # 文书生成节点
│   │   ├── guardrail.py       # 输入验证
│   │   └── debate_nodes/       # 红蓝对抗节点
│   │       ├── challenger.py  # 红方节点
│   │       ├── defender.py    # 蓝方节点
│   │       └── judge.py       # 裁决官节点
│   ├── api/                    # FastAPI 接口
│   │   ├── main.py            # 主应用
│   │   └── models.py          # 请求/响应模型
│   ├── prompts/                # 单Agent提示词
│   │   └── debate.py          # 红蓝对抗提示词
│   └── main.py                # 入口
├── frontend/                   # Web 前端
│   ├── index.html              # 主页面（快速分析 + 红蓝对抗）
│   └── css/
│       └── styles.css          # 样式
└── README.md
│   │   └── core.py            # 核心提示词
│   ├── requirements.txt       # 依赖
│   └── main.py                # 入口
│
└── frontend/                   # Flutter 前端
    └── lib/
        ├── main.dart           # 入口
        ├── screens/            # 页面
        │   ├── home_screen.dart
        │   ├── analyze_screen.dart
        │   └── results_screen.dart
        ├── widgets/            # 组件
        │   ├── analysis_progress.dart
        │   ├── contract_input.dart
        │   ├── risk_card.dart
        │   └── document_card.dart
        ├── models/             # 数据模型
        ├── services/           # 服务
        └── theme/              # 主题
```

## 快速开始

### 1. 后端启动

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 API Key

# 启动服务
python main.py
# 或使用 uvicorn
uvicorn main:app --reload --port 8000
```

### 2. 前端启动（Web 版本）

Web 前端是一个纯 HTML/CSS/JS 文件，无需安装任何依赖，直接用浏览器打开即可。

```bash
# 方式一：直接在浏览器打开
open frontend/index.html

# 方式二：使用任意静态服务器
cd frontend && python -m http.server 3000
# 然后访问 http://localhost:3000
```

> 注意：Web 前端默认连接 `http://localhost:8000`，请确保后端已启动。
>
> **前端模式选择**：打开页面后，可在首页选择「快速分析」（单Agent）或「红蓝对抗」（Multi-Agent）模式。

## 技术架构

## API 接口

### POST /analyze
同步分析合同（单Agent）

```json
{ "text": "合同全文...", "user_id": "xxx" }
```

### POST /analyze/stream
流式分析合同（单Agent，推荐）

返回 Server-Sent Events 流，包含中间处理状态。

### POST /debate
红蓝对抗辩论分析（Multi-Agent，同步）

触发红方→蓝方→裁决官三轮辩论，返回完整辩论记录和维权行动指南。

```json
{ "text": "合同全文...", "user_id": "xxx" }
```

### POST /debate/stream
红蓝对抗辩论分析（Multi-Agent，流式，推荐）

逐步展示红方挑刺 → 蓝方反驳 → 裁决官定论的全过程。

### GET /health
健康检查

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| DEEPSEEK_API_KEY | DeepSeek API Key | - |
| DEEPSEEK_BASE_URL | API 地址 | https://api.deepseek.com |
| HOST | 服务监听地址 | 0.0.0.0 |
| PORT | 服务端口 | 8000 |

## 风险判定规则

### 劳动合同
- 违约金 > 月薪的20% → **致命风险**
- "自愿放弃社保/公积金" → **致命风险**（违法条款）
- 试用期 > 6个月 → **高风险**
- 竞业限制无补偿金 → **高风险**

### 租房合同
- 押金 > 2个月租金 → **高风险**
- 提前退租赔偿 > 1个月租金 → **中风险**
- 无故克扣押金条款 → **致命风险**

## 生成的法律文书

1. **《合同修订建议表》** - 红线批注版，清晰对比原文与修订
2. **《交涉话术模版》** - 高情商谈判版本，专业但不对抗
3. **《维权证据清单》** - 需要收集的证据和获取方式

## License

MIT
