# 旅行助手

基于 LangGraph 多智能体与 RAG 的智能旅游助手系统。

项目将旅游规划、攻略问答、实时工具调用、用户私有知识库、多轮记忆和 Agent 执行轨迹组织成一个可本地运行、可 Docker 部署的 Agentic RAG 工程。

---

## 技术架构

```text
Vue 3 + Vite + Pinia + Element Plus
        |
        | HTTP / SSE
        v
FastAPI + Pydantic + JWT
        |
        | Agent 调度
        v
LangGraph / RouterAgent / RAGAgent / ToolAgent / PlannerAgent / CriticAgent
        |
        | 模型调用
        v
Qwen / DeepSeek / Local OpenAI-compatible endpoint
        |
        | 知识检索与记忆
        v
Chroma + BM25 + Redis + SQLite
```

**数据边界：**

| 组件 | 用途 | 默认位置 |
| --- | --- | --- |
| SQLite | 用户账号 | `storage/travel_assistant.db` |
| JWT | 识别当前用户身份 | — |
| Redis | 会话历史、用户画像、事实记忆、Agent 运行状态、工具缓存 | `redis://localhost:6379/0` |
| Chroma | 公共旅游攻略向量库 | `storage/chroma` |
| 用户私有 Chroma | 用户文件向量库 | `storage/user_kb/{user_id}` |
| BM25 | 关键词召回 | `storage/bm25` |
| Web Search | 实时开放时间、门票、政策、活动 | — |

---

## 快速启动

### 1. 准备配置

```powershell
Copy-Item .env.example .env
```

至少修改这三个字段：

```env
ADMIN_TOKEN=换成你自己的管理员口令
JWT_SECRET_KEY=换成一段足够长的随机字符串
DATABASE_URL=sqlite:///./storage/travel_assistant.db
```

真实演示建议再填写：

```env
DASHSCOPE_API_KEY=你的 DashScope API Key
TAVILY_API_KEY=你的 Tavily API Key
AMAP_KEY=你的高德 Key
QWEATHER_KEY=你的和风天气 Key
REDIS_URL=redis://localhost:6379/0
```

### 2. 启动 Redis

```powershell
docker run --name travelai-redis -p 6379:6379 -d redis:7-alpine
```

### 3. 启动后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端文档：`http://127.0.0.1:8000/docs`
健康检查：`http://127.0.0.1:8000/api/v1/health`

### 4. 启动前端

```powershell
cd frontend
npm install
npm run dev
```

前端地址：`http://localhost:5173`

### 5. Docker Compose 一键启动

```powershell
cd infra
docker compose up -d --build
```

Docker 中 `.env` 需要调整：

```env
DATABASE_URL=sqlite:////app/storage/travel_assistant.db
REDIS_URL=redis://redis:6379/0
```

---

## 页面路由

| 路由 | 页面 | 用途 |
| --- | --- | --- |
| `/login` | 登录 | 输入用户名和密码登录 |
| `/register` | 注册 | 创建本地用户账号 |
| `/dashboard` | 总览 | 系统能力、运行状态和演示入口 |
| `/agent` | Agent 工作台 | 对话、意图识别、工具调用和执行轨迹 |
| `/travel` | 旅行工作台 | 行程生成、网页增强规划、路线优化和预算估算 |
| `/knowledge` | 知识库工作台 | 公共知识库、我的文件、RAG 问答和知识库治理 |
| `/creation` | 创作工具 | 旅行文案、实时天气、POI 和网页搜索 |
| `/sessions` | 会话历史 | 查看历史会话消息 |
| `/profile` | 个人中心 | 账号信息和快捷入口 |

旧路由如 `/rag`、`/trip`、`/tools` 会重定向到新的工作台页面。

---

## 系统架构

### 总体分层

```text
用户
 |
 v
Vue 3 前端（登录、对话、上传、规划、执行轨迹展示）
 |
 v
FastAPI 后端（认证、统一响应、限流、文件校验、API 编排）
 |
 v
服务层（ChatService / RagService / AgentService / PlanService / MemoryService / UserKbService）
 |
 v
LangGraph Agent 层（RouterAgent / RAGAgent / ToolAgent / PlannerAgent / CriticAgent）
 |
 v
能力层（Qwen / DeepSeek / Local | Chroma / BM25 / Redis / SQLite | Weather / AMap POI / Web Search）
```

### 数据流：普通 Agent 对话

```text
用户输入 -> POST /api/v1/agent/chat -> JWT 解析 user_id
  -> ContextBuilder 拼装用户画像、事实记忆、会话摘要、最近消息
  -> RouterAgent 判断意图
  -> 按需调用 RAGAgent、ToolAgent、PlannerAgent
  -> CriticAgent 检查答案和计划
  -> 保存消息、压缩上下文、记录 run_id
  -> 返回答案、sources、tool_calls、steps
```

### 数据流：RAG 问答

```text
用户问题 -> POST /api/v1/rag/ask -> 读取 scope=global|personal|hybrid
  -> 公共 Chroma / 用户私有 Chroma 检索 -> BM25 关键词召回
  -> 合并去重和排序 -> Qwen 生成带引用答案
  -> 返回 answer、sources、score、scope
```

### 数据流：网页增强旅行规划

```text
用户填写目的地、天数、预算、偏好 -> POST /api/v1/plan/web-enhanced
  -> ContextBuilder 读取记忆 -> ToolAgent 调天气、POI、网页搜索
  -> RAGAgent 查询本地攻略 -> PlannerAgent 合成结构化行程
  -> CriticAgent 检查合理性 -> 返回计划、工具调用、网页证据、本地来源
```

### 工程边界

- 前端只负责展示和交互，不直接调用模型
- 后端负责鉴权、工具调用、RAG、Agent 编排和安全控制
- 公共知识库必须经过管理员 Token
- 用户私有知识库按 `user_id` 隔离
- 网页搜索只作为实时证据，不替代公共知识库
- Agent 之间不自由聊天，由 Router 或 Supervisor 控制调用顺序

---

## Agent 架构设计

### 设计原则

不要把每个工具都拆成独立 Agent。系统将旅游任务拆成 5 个边界清晰的核心 Agent，工具统一由 ToolAgent 管理。

### 核心 Agent

| Agent | 职责 | 输入 | 输出 |
| --- | --- | --- | --- |
| RouterAgent | 判断用户意图和需要哪些能力 | 当前问题、用户画像、会话摘要、最近消息 | intent、destination、days、need_rag、need_weather、need_search、need_plan |
| RAGAgent | 从知识库检索证据 | query、scope、destination | sources、scores、evidence |
| ToolAgent | 调用外部工具 | destination、date、keyword、intent | weather、poi、web_search、tool_calls |
| PlannerAgent | 生成结构化旅行计划 | 用户偏好、RAG 证据、网页证据、工具结果 | title、days、items、budget、tips |
| CriticAgent | 检查回答和计划质量 | 初版答案、计划、证据、用户约束 | verified、warnings、revision_suggestions |

可选 Agent：CopywritingAgent（旅行文案）、SupervisorAgent（统一调度）

### 执行流程

```text
用户请求 -> ContextBuilder -> RouterAgent
  -> RAGAgent（检索引擎）+ ToolAgent（工具调用）+ PlannerAgent（计划生成）
  -> CriticAgent（自检）-> AnswerComposer -> 前端展示答案、来源、工具调用和执行轨迹
```

### RouterAgent 示例

输入：`明天杭州适合去西湖吗？顺便帮我安排一天路线。`

```json
{
  "intent": "mixed",
  "destination": "杭州",
  "days": 1,
  "need_rag": true,
  "need_weather": true,
  "need_map": true,
  "need_search": true,
  "need_plan": true,
  "need_copywriting": false
}
```

### RAGAgent

只负责查证据，不负责编最终答案。支持三种范围：`global`（公共库）、`personal`（用户私有库）、`hybrid`（两者混合，默认推荐）。

### PlannerAgent

输出结构化行程：

```json
{
  "title": "杭州西湖一日游",
  "days": [{
    "day": 1,
    "theme": "西湖经典路线",
    "items": [{
      "time": "09:00",
      "place": "断桥残雪",
      "activity": "游览拍照",
      "duration": "1小时",
      "transport": "步行",
      "tips": "上午人相对少，适合拍照"
    }]
  }],
  "budget": { "food": 120, "transport": 50, "ticket": 80, "total": 250 }
}
```

### CriticAgent

检查项：是否遗漏用户偏好、是否超预算、景点是否太远、是否忽略天气、是否缺少来源、是否编造实时政策、行程是否过紧。

### Agent 状态记录

每次 Agent 执行生成 `run_id`，通过 `GET /api/v1/agent/runs/{run_id}` 可查看完整执行轨迹（Router 结果、调用了哪些 Agent、工具调用、耗时、RAG 来源、Critic 结果）。Redis Key：`travelai:agent:run:{run_id}`。

### 为什么这是 Agentic RAG

| | 传统 RAG | 本项目 |
| --- | --- | --- |
| 流程 | 问题 -> 检索 -> 拼 prompt -> 回答 | 意图路由 -> 多 Agent 协作 -> 自检 -> 可解释输出 |
| 工具 | 无 | 天气、POI、网页搜索 |
| 输出 | 纯文本 | 结构化行程 + 引用 + 预算 |
| 记忆 | 无 | 分层记忆 + 上下文压缩 |
| 可见性 | 黑盒 | 执行轨迹可视化 |

---

## 知识库体系

### 三层知识来源

| 来源 | 作用 | 适合内容 | 风险 |
| --- | --- | --- | --- |
| 公共知识库 | 全站共享的旅游攻略底座 | 城市攻略、景点介绍、经典路线、注意事项 | 内容过期后影响所有用户 |
| 用户私有知识库 | 当前用户自己的文件和攻略 | 用户收藏的攻略、自己写的计划、个人资料 | 只对当前用户有效 |
| 网页搜索 | 补充实时信息 | 最新开放时间、门票政策、临时闭园、节假日活动 | 网页质量不稳定 |

核心原则：公共库负责稳定可复用的攻略，用户私有库负责个人文件，网页搜索负责实时变化信息。用户上传的文件不会自动进入公共库，必须经过管理员治理流程审核。

### RAG 检索范围（scope）

| scope | 检索范围 | 适合场景 |
| --- | --- | --- |
| `global` | 只查公共知识库 | 城市介绍、通用注意事项 |
| `personal` | 只查用户私有知识库 | 自己上传的 PDF、Markdown、TXT |
| `hybrid` | 同时查公共库和用户私有库 | 默认推荐，兼顾通用知识和个人资料 |

### 优先级规则

- **稳定攻略问题**（如"西湖一日游怎么安排"）：用户私有库 -> 公共库 -> 必要时网页搜索补充
- **实时政策问题**（如"明天西湖有没有交通管制"）：网页搜索 -> 工具查询 -> 公共库作为背景参考
- **用户文件问题**（如"根据我上传的攻略整理路线"）：用户私有库 -> 公共库补充 -> PlannerAgent 生成

### 新攻略进入项目

- **个人使用**：知识库工作台 -> 我的文件 -> 上传文件或登记文字攻略（只对当前用户可见）
- **公共沉淀**：知识库工作台 -> 攻略治理 -> 填写管理员 Token -> 登记攻略 -> 审核后合并公共库（影响所有用户）

---

## 认证、记忆与上下文

### 身份识别

项目使用完整 JWT 登录注册，不使用浏览器临时 session_id。

`user_id`（来自 JWT，稳定）vs `session_id`（前端生成，代表一次会话）vs `run_id`（后端生成，代表单次 Agent 执行）。同一用户可创建多个 session，共享用户画像但聊天消息互不混淆。

### Redis Key 设计

| Key | 作用 |
| --- | --- |
| `travelai:user:{user_id}:profile` | 长期用户画像（预算偏好、旅行节奏、饮食偏好） |
| `travelai:user:{user_id}:facts` | 长期事实记忆（"喜欢自然风光，不喜欢购物"） |
| `travelai:user:{user_id}:sessions` | 当前用户的会话列表 |
| `travelai:session:{user_id}:{session_id}:messages` | 某个会话的最近消息 |
| `travelai:session:{user_id}:{session_id}:summary` | 某个会话的压缩摘要 |
| `travelai:agent:run:{run_id}` | Agent 执行轨迹、工具调用和中间状态 |
| `tool:weather:{city}:{date}` | 天气工具缓存 |
| `tool:poi:{city}:{keyword}` | POI 工具缓存 |
| `rag:cache:{query_hash}` | RAG 检索结果缓存 |

### 分层记忆

| 层级 | 内容 | 进入上下文方式 |
| --- | --- | --- |
| 用户画像 | 预算、旅行风格、同行人、偏好和禁忌 | 优先进入 |
| 事实记忆 | 用户明确说过的稳定事实 | MemoryCompressor 抽取，精简进入 |
| 会话摘要 | 旧消息压缩后的摘要 | 替代大量旧消息 |
| 最近消息 | 当前会话最后几轮原始对话 | 按 token 预算裁剪 |

### 上下文预算

| 字段 | 说明 | 默认值 |
| --- | --- | --- |
| `MAX_CONTEXT_TOKENS` | 单次请求允许拼装的最大上下文 | 12000 |
| `RECENT_HISTORY_TOKENS` | 最近消息最多占用多少 token | 3000 |
| `MEMORY_SUMMARY_TOKENS` | 会话摘要最多占用多少 token | 1500 |
| `RAG_CONTEXT_TOKENS` | 本地知识库证据最多占用多少 token | 4000 |
| `WEB_CONTEXT_TOKENS` | 网页搜索证据最多占用多少 token | 2500 |
| `COMPRESSION_TRIGGER_TOKENS` | 会话历史超过多少 token 后触发压缩 | 8000 |

当会话历史超过 `COMPRESSION_TRIGGER_TOKENS` 时，MemoryCompressor 自动：保留最近消息、把旧消息压缩为会话摘要、从旧消息中抽取用户偏好和事实记忆。

### 用户隔离

所有聊天历史、私有知识库、偏好、事实和摘要必须带 `user_id`。用户 A 上传的文件只能用户 A 在 personal 或 hybrid 模式下检索到。

---

## 完整配置参考

### 必填项

| 字段 | 用途 | 示例 |
| --- | --- | --- |
| `ADMIN_TOKEN` | 管理员接口和知识库管理页面使用 | `travelai-admin-2026` |
| `JWT_SECRET_KEY` | JWT 签名密钥 | 建议 32 位以上随机字符串 |
| `DATABASE_URL` | SQLite 数据库地址 | `sqlite:///./storage/travel_assistant.db` |

### 推荐填写

| 字段 | 用途 | 不填的影响 |
| --- | --- | --- |
| `DASHSCOPE_API_KEY` | Qwen 模型调用 | 真实 AI 回复不可用，走兜底逻辑 |
| `REDIS_URL` | 缓存和记忆 | 多轮记忆、缓存、Agent 状态受限 |
| `TAVILY_API_KEY` | 网页搜索 | 网页搜索和增强规划无法获取实时结果 |
| `AMAP_KEY` | 附近 POI、地图 | 地图和 POI 能力不可用 |
| `QWEATHER_KEY` | 和风天气 | 天气工具不可用 |

填写优先级：`DASHSCOPE_API_KEY` > `REDIS_URL` > `TAVILY_API_KEY` > `AMAP_KEY` > `QWEATHER_KEY`

### 模型配置

| 字段 | 用途 | 默认值 |
| --- | --- | --- |
| `DEFAULT_PROVIDER` | 默认模型提供方 | `qwen` |
| `QWEN_CHAT_MODEL` | 主聊天和 RAG 回答 | `qwen3.6-plus` |
| `QWEN_FAST_MODEL` | Router、摘要、轻量任务 | `qwen3.6-flash` |
| `QWEN_REASONING_MODEL` | 复杂规划和复核 | `qwen3.6-max-preview` |
| `QWEN_EMBEDDING_MODEL` | RAG 向量化 | `text-embedding-v4` |
| `QWEN_RERANK_MODEL` | RAG 重排 | `qwen3-rerank` |
| `DEEPSEEK_API_KEY` | DeepSeek 备用模型 | — |
| `LOCAL_OPENAI_BASE_URL` | 本地 OpenAI-compatible endpoint | — |

推荐策略：RouterAgent 用快速模型，RAGAgent 用平衡模型，PlannerAgent 和 CriticAgent 优先用推理能力更强的模型。

### RAG 和上下文配置

| 字段 | 默认值 | 说明 |
| --- | --- | --- |
| `CHUNK_SIZE` | 1000 | 文档切分长度 |
| `CHUNK_OVERLAP` | 180 | 文档切分重叠 |
| `DENSE_TOP_K` | 40 | 向量召回数量 |
| `BM25_TOP_K` | 40 | BM25 召回数量 |
| `RERANK_TOP_K` | 20 | 重排候选数量 |
| `FINAL_TOP_K` | 6 | 最终证据数量 |

### 本地 vs Docker 差异

```env
# 本地运行
DATABASE_URL=sqlite:///./storage/travel_assistant.db
REDIS_URL=redis://localhost:6379/0

# Docker Compose 运行
DATABASE_URL=sqlite:////app/storage/travel_assistant.db
REDIS_URL=redis://redis:6379/0
```

### 前端配置

`frontend/.env.local`（前后端分开部署时填写）：

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

---

## API 参考

所有 v1 接口前缀：`/api/v1`

### 认证

| 方法 | 路径 | 说明 | 状态 |
| --- | --- | --- | --- |
| POST | `/v1/auth/register` | 注册 | 已完成 |
| POST | `/v1/auth/login` | 登录，返回 JWT | 已完成 |
| GET | `/v1/auth/me` | 获取当前用户 | 已完成 |
| POST | `/v1/auth/logout` | 登出 | 已完成 |

### 对话与 Agent

| 方法 | 路径 | 说明 | 状态 |
| --- | --- | --- | --- |
| POST | `/v1/chat` | 普通聊天（支持 general/rag/agent 三种模式） | 已完成 |
| POST | `/v1/agent/chat` | Agent 对话，返回答案 + 意图 + 工具调用 + 来源 + 计划 + 记忆信息 | 已完成 |
| GET | `/v1/agent/runs/{run_id}` | 查询 Agent 执行轨迹 | 已完成 |

### RAG 问答

| 方法 | 路径 | 说明 | 状态 |
| --- | --- | --- | --- |
| POST | `/v1/rag/ask` | RAG 问答，支持 `scope=global\|personal\|hybrid` | 已完成 |
| POST | `/v1/rag/evaluate` | RAG 评测（来源数、引用、匹配预期来源、平均重排分） | 已完成 |

### 旅行规划

| 方法 | 路径 | 说明 | 状态 |
| --- | --- | --- | --- |
| POST | `/v1/plan/generate` | 生成旅行计划 | 已完成 |
| POST | `/v1/plan/web-enhanced` | 网页增强旅行计划（天气 + POI + 网页搜索 + RAG） | 已完成 |
| POST | `/v1/plan/optimize` | 旅行计划优化 | 已完成 |
| POST | `/v1/plan/budget` | 预算估算（纯计算，不调用 LLM） | 已完成 |
| POST | `/v1/plan/export` | 导出 Markdown 或 HTML | 已完成 |
| POST | `/v1/plan/route-nodes` | 解析地名为节点/边图 | 已完成 |
| POST | `/v1/plan/alternatives` | 生成替代方案（天气等突发情况） | 已完成 |

### 知识库管理

| 方法 | 路径 | 说明 | 权限 | 状态 |
| --- | --- | --- | --- | --- |
| GET | `/v1/kb/documents` | 查看公共知识库文档列表 | 登录用户 | 已完成 |
| POST | `/v1/kb/upload` | 上传公共 PDF | 管理员 | 已完成 |
| POST | `/v1/kb/reindex` | 重建公共知识库索引 | 管理员 | 已完成 |
| DELETE | `/v1/kb/documents/{doc_id}` | 删除公共文档 | 管理员 | 已完成 |
| GET | `/v1/kb/governance/records` | 查看治理记录 | 登录用户 | 已完成 |
| POST | `/v1/kb/governance/analyze` | 分析攻略质量（相似度检查） | 登录用户 | 已完成 |
| POST | `/v1/kb/governance/upload` | 上传待治理攻略文件 | 管理员 | 已完成 |
| POST | `/v1/kb/governance/register-text` | 登记公共文字攻略 | 管理员 | 已完成 |
| POST | `/v1/kb/governance/merge-plan` | 生成合并建议 | 登录用户 | 已完成 |

### 用户私有知识库

| 方法 | 路径 | 说明 | 状态 |
| --- | --- | --- | --- |
| GET | `/v1/user-kb/documents` | 查看我的文件列表 | 已完成 |
| POST | `/v1/user-kb/upload` | 上传我的 PDF、Markdown、TXT | 已完成 |
| POST | `/v1/user-kb/register-text` | 登记我的文字攻略 | 已完成 |
| POST | `/v1/user-kb/reindex` | 重建我的私有索引 | 已完成 |
| DELETE | `/v1/user-kb/documents/{doc_id}` | 删除我的某个文档 | 已完成 |
| POST | `/v1/user-kb/query` | 只查询我的私有知识库 | 已完成 |

### 工具调用

| 方法 | 路径 | 说明 | 状态 |
| --- | --- | --- | --- |
| POST | `/v1/tools/weather` | 天气查询 | 已完成 |
| POST | `/v1/tools/nearby` | 附近 POI 搜索 | 已完成 |
| POST | `/v1/tools/web-search` | 网页搜索 | 已完成 |

### 历史与偏好

| 方法 | 路径 | 说明 | 状态 |
| --- | --- | --- | --- |
| GET | `/v1/history/{session_id}` | 获取会话历史 | 已完成 |
| DELETE | `/v1/history/{session_id}` | 删除会话历史 | 已完成 |
| GET | `/v1/preferences/me` | 获取用户偏好 | 已完成 |
| PUT | `/v1/preferences/me` | 更新用户偏好 | 已完成 |
| DELETE | `/v1/preferences/me` | 删除用户偏好 | 已完成 |
| POST | `/v1/preferences/merge` | 合并多个用户画像 | 已完成 |

### 其他

| 方法 | 路径 | 说明 | 状态 |
| --- | --- | --- | --- |
| GET | `/v1/health` | 健康检查（状态、数据集、Redis、Chroma） | 已完成 |
| GET | `/v1/models` | 返回可用模型列表 | 已完成 |
| POST | `/v1/copywriting/generate` | 生成旅行文案 | 已完成 |

### 旧版 API（`/api/*` 无版本前缀，仍可用）

| 方法 | 路径 | 说明 | 状态 |
| --- | --- | --- | --- |
| POST | `/chat/stream` | SSE 流式聊天 | 旧版可用 |
| POST | `/trips/plan/stream` | SSE 流式旅行规划 | 旧版可用 |
| POST | `/media/caption` | 图片描述 | 旧版可用 |
| POST | `/media/copywriting` | 旅行文案（旧版） | 旧版可用 |
| POST | `/media/tts` | 文字转语音 | 旧版可用 |
| POST | `/media/image` | 图片生成 | 旧版可用 |

---

## 部署结构

```text
Docker Compose:
  frontend (Vue, :5173)  <- 用户浏览器
  backend  (FastAPI, :8000) <- API
  redis    (:6379) <- 会话记忆和缓存

Chroma 使用本地持久化目录，挂载在后端容器的 /app/storage 下。
```

---

## 测试命令

```powershell
# 后端语法检查
python -m compileall -q backend/app

# 后端单元测试
pytest backend/tests -q -p no:cacheprovider

# 前端类型检查 + 构建
cd frontend
npm run build
```

---

## 简历描述

> 旅行助手：基于 LangGraph 多智能体与 RAG 的智能旅游助手系统
>
> 项目基于 Vue3 + FastAPI 实现前后端分离，使用 Qwen 系列模型作为主要推理底座，结合 LangGraph 构建 RouterAgent、RAGAgent、ToolAgent、PlannerAgent、CriticAgent 的可解释多智能体流程。系统使用 Chroma 构建公共旅游攻略库和用户私有知识库，结合 BM25、向量检索和证据引用实现 Agentic RAG；使用 Redis 保存多轮会话、用户画像、事实记忆、Agent 执行状态和工具缓存，并通过上下文压缩控制长对话 token 预算。项目支持网页搜索增强规划、天气和 POI 工具调用、知识库治理、用户文件问答和 Docker Compose 一键部署。

---

## 致谢

本项目灵感来源于 [yaosenJ/LvBanGPT](https://github.com/yaosenJ/LvBanGPT)，已基于 LangGraph + FastAPI + Vue3 全面重构为多智能体架构。
