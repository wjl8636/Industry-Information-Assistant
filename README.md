<div align="center">

# 行业信息助手 (Industry Information Assistant)

基于 AI Agent 的一站式行业研究与信息智能分析平台

支持**深度研究**、**智能问答**、**知识库 RAG**、**行业资讯/招投标监控**、**数据库 Text2SQL** 等能力，
帮助研究人员与分析师快速完成多行业的资料检索、信息聚合与深度分析报告生成。

</div>

---

## ✨ 功能特性

- **🧠 AI 深度研究**：基于 Multi-Agent 图谱编排的深度研究流程，支持搜索 → 多轮迭代 → 研究报告生成，全程流式输出（SSE），研究历史可随时恢复。
- **💬 智能问答**：基于 Qwen 大模型 + 联网检索的对话助手，支持流式回复、附件上传、多会话管理。
- **📚 知识库 RAG**：文档上传解析（PDF/Word 等，可选阿里云 DocMind），切片向量化（Milvus），实现基于本地知识库的精准检索增强问答。
- **📰 行业资讯监控**：内置定时任务自动采集行业新闻与招投标信息，并支持按行业维度查看与统计分析。
- **🗄️ 数据库智能查询（Text2SQL）**：通过自然语言直接查询行业结构化数据，自动生成 SQL 并返回结果。
- **📈 数据可视化**：内置 ECharts 图表生成，支撑研究报告中的可视化呈现。
- **🧠 长期记忆**：多轮对话中的用户长期记忆管理与沉淀。
- **🏭 多行业覆盖**：内置智慧交通、金融科技、医疗健康、能源电力等行业配置，关键词与检索策略可灵活扩展。
- **🔐 用户认证**：JWT 令牌认证 + 会话隔离。

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                         前端 (React 19)                      │
│  首页 / 对话 / 深度研究 / 知识库 / 资讯 / 招投标 / 数据库 / 记忆 │
└──────────────────────────┬──────────────────────────────────┘
                           │  HTTP / SSE
┌──────────────────────────▼──────────────────────────────────┐
│                      后端 (FastAPI)                          │
│  Auth · Chat · Research · Knowledge · News · Bidding        │
│  Memory · Database · Document · Attachment · Session        │
└───────┬──────────────┬──────────────┬──────────────┬────────┘
        │              │              │              │
        ▼              ▼              ▼              ▼
   PostgreSQL       Redis         Milvus+etcd      Elasticsearch
   (业务数据)       (缓存)         +MinIO(向量/对象)  (全文检索,可选)
```

> Milvus 依赖 etcd 与 MinIO 组件，已在 `docker-compose.yml` 中一并编排。

---

## 🧰 技术栈

| 层级 | 技术 |
|------|------|
| **前端** | React 19 · TypeScript · Vite · Ant Design 5 · ECharts · React Router 6 · Valtio |
| **后端** | Python 3.10+ · FastAPI · SQLAlchemy 2 · Uvicorn/Gunicorn · APScheduler |
| **大模型** | 阿里云百炼（DashScope / Qwen）· OpenRouter（可选多模型网关） |
| **检索/向量** | Milvus 2.3 · llama-index · 百炼 Embedding / Rerank |
| **基础设施** | PostgreSQL 15 · Redis 7 · Elasticsearch 8 · MinIO · etcd |
| **部署** | Docker Compose · Shell 一键脚本 |

---

## 📁 目录结构

```
industry_information_assistant/
├── backend/                        # 后端服务 (FastAPI)
│   ├── app/
│   │   ├── app_main.py             # 入口文件 (FastAPI app)
│   │   ├── router/                 # API 路由 (auth/chat/research/news/knowledge...)
│   │   ├── service/                # 业务逻辑 (深度研究/检索/资讯采集/股票/Text2SQL...)
│   │   ├── core/                   # 核心 (数据库/Redis/安全/JWT)
│   │   ├── models/                 # SQLAlchemy 数据模型
│   │   ├── schemas/                # 请求/响应数据模型
│   │   └── config/                 # 行业与 LLM 配置
│   ├── requirements.txt            # Python 依赖
│   ├── .env.example                # 环境变量示例
│   └── Dockerfile                  # 后端镜像
├── frontend/                       # 前端服务 (React + Vite)
│   ├── src/
│   │   ├── pages/                  # 页面 (chat/research/knowledge/news/bidding...)
│   │   ├── components/             # 通用组件
│   │   ├── router/                 # 前端路由
│   │   ├── api/                    # 接口封装
│   │   └── assets/                 # 静态资源
│   ├── package.json
│   └── vite.config.ts
├── docker/init-db/                 # 数据库初始化脚本
├── docker-compose.yml              # 中间件一键编排
├── start-services.sh               # 服务一键管理脚本
└── data/                           # 示例数据/文档
```

---

## 🚀 快速开始

### 环境要求

| 依赖 | 版本要求 | 说明 |
|------|---------|------|
| Docker | 20.0+ | 运行 PostgreSQL、Redis、Milvus、Elasticsearch 等中间件 |
| Python | 3.10+ | 后端服务 |
| Node.js | 18+ | 前端构建 |

### 1. 启动基础服务（推荐使用脚本）

```bash
cd industry_information_assistant

# 方式 A: 使用一键启动脚本（推荐）
chmod +x start-services.sh
./start-services.sh start

# 方式 B: 使用 Docker Compose
docker compose up -d
```

验证服务状态：

```bash
./start-services.sh status          # 或 docker compose ps
```

预期运行的服务：

| 服务 | 容器名 | 端口 |
|------|--------|------|
| PostgreSQL | `industry_postgres` | `5432` |
| Redis | `industry_redis` | `6379` |
| Milvus | `industry_milvus` | `19530` |
| etcd | `industry_etcd` | `2379` |
| MinIO（Console） | `industry_minio` | `9000 / 9001`（admin/minioadmin） |
| Elasticsearch（可选） | `industry_elasticsearch` | `1200` |

### 2. 配置环境变量

```bash
cd backend
cp .env.example .env
```

**必填 API Key（其余配置已预置，通常无需修改）：**

```env
# 阿里云百炼 (LLM & Embedding) - 必填
DASHSCOPE_API_KEY=your-dashscope-api-key

# 搜索服务 - 必填
BOCHA_API_KEY=your-bocha-api-key

# JWT 密钥（生产环境务必修改为随机值）
JWT_SECRET_KEY=your-super-secret-key-change-in-production
```

### 3. 启动后端

```bash
cd backend

# 创建虚拟环境（推荐）
conda create -n deepresearch python=3.10
conda activate deepresearch

pip install -r requirements.txt

# 启动后端
python app/app_main.py
```

后端默认运行在 `http://localhost:8000`，接口文档见 `http://localhost:8000/docs`。

### 4. 启动前端

```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```

前端默认运行在 `http://localhost:5173/login`。

---

## ⚙️ 环境变量说明

### 必填配置

| 变量名 | 说明 | 申请地址 |
|--------|------|----------|
| `DASHSCOPE_API_KEY` | 阿里云百炼（LLM & Embedding） | https://bailian.console.aliyun.com/ |
| `BOCHA_API_KEY` | 博查搜索 API | https://open.bochaai.com/ |
| `POSTGRES_*` | PostgreSQL 连接配置 | Docker 已配置 |
| `REDIS_HOST/PORT` | Redis 连接配置 | Docker 已配置 |
| `MILVUS_HOST/PORT` | Milvus 向量数据库 | Docker 已配置 |
| `JWT_SECRET_KEY` | JWT 认证密钥 | 自定义 |

### 可选配置

| 变量名 | 说明 | 申请地址 |
|--------|------|----------|
| `DOCMIND_ACCESS_KEY_ID/SECRET` | 阿里云 DocMind 文档解析 | https://help.aliyun.com/zh/ram/user-guide/create-an-accesskey-pair |
| `SERPER_API_KEY` | Serper 搜索 API | https://serper.dev/ |
| `JUHE_STOCK_API_KEY` | 聚合数据 - 股票行情 | https://www.juhe.cn/docs/api/id/21 |
| `BID_APP_KEY/SECRET/CODE` | 阿里云市场 - 招投标信息 | https://market.aliyun.com/ |
| `OPENROUTER_API_KEY` | OpenRouter 多模型网关 | https://openrouter.ai/ |

---

## 🛠️ 服务管理

使用 `start-services.sh` 一键管理中间件：

```bash
./start-services.sh start      # 启动所有服务
./start-services.sh status     # 查看服务状态
./start-services.sh logs       # 查看日志（可指定服务，如 logs postgres）
./start-services.sh restart    # 重启服务
./start-services.sh stop       # 停止服务
./start-services.sh clean      # 清理所有数据（危险操作！）
```

或使用 Docker Compose：

```bash
docker compose up -d
docker compose ps
docker compose logs -f
docker compose down
docker compose down -v        # 停止并删除数据卷（危险！）
```

---

## 🔌 接口示例

**文档上传（构建本地知识库）**

```bash
cd backend
curl -X POST "http://localhost:8000/documents/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@./test/test_doc.pdf"
```

**深度研究（流式）**

```bash
curl -N -X POST "http://localhost:8000/research/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "安责险在矿山行业的应用现状、主要挑战以及改进建议有哪些？",
    "max_iterations": 2
  }'
```

**会话问答（流式）**

```bash
# 创建会话
curl -s -X POST http://localhost:8000/chat/session

# 问答（SSE 流式）
curl -N -X POST http://localhost:8000/chat/completion \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"session_id": "<SESSION_ID>", "question": "智慧交通行业最新政策有哪些？"}'
```

---

## ❓ 常见问题

**Q: Docker 容器启动失败？**

```bash
./start-services.sh status     # 查看服务状态
./start-services.sh logs       # 查看日志定位问题
./start-services.sh restart    # 重启所有容器
```

**Q: 后端连接数据库失败？**

1. 检查 Docker 服务是否已启动：`./start-services.sh start`
2. 核对 `.env` 中 `POSTGRES_*` 配置是否与 Docker Compose 一致
3. 若本机端口被占用，调整 `docker-compose.yml` 中的端口映射

**Q: 前端 `npm install` 报错？**

```bash
npm install --legacy-peer-deps       # 解决依赖冲突
# 或清除缓存后重试
rm -rf node_modules package-lock.json
npm install --legacy-peer-deps
```

**Q: 研究历史无法恢复右侧面板数据？**

执行数据库迁移后重启后端：

```sql
ALTER TABLE research_checkpoints ADD COLUMN IF NOT EXISTS ui_state_json JSONB;
ALTER TABLE research_checkpoints ADD COLUMN IF NOT EXISTS final_report TEXT;
```

---

## 🧭 常见部署说明

- **数据库自动建表**：首次启动后端时会自动创建数据表，一般无需手动初始化。
- **本地 PostgreSQL（不推荐新手）**：可手动安装 PostgreSQL 后，将 `.env` 指向本地实例，并注释掉 `docker-compose.yml` 中的 `postgres` 服务。
- **生产部署**：请务必修改 `JWT_SECRET_KEY` 为随机密钥，并收紧 CORS 白名单。

---

## 📄 许可证

本项目源代码版权归 **深圳市深维智见教育科技有限公司** 所有。未经授权，禁止转售或仿制。

> 依赖的外部服务（阿里云百炼、博查、OpenRouter 等）均有各自的许可与计费条款，请在使用前查阅对应平台文档。
