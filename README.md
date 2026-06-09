# 📖 Draft-Beat-Novel — AI 故事创作流水线

> 把你的故事想法变成完整小说——AI 辅助的四级流水线：**草稿 → 节拍 → 章节 → 大纲**

面向**非专业写作者**（有想法但不知道怎么写的人），纯本地部署，每一步都由你掌控。

---

## 🚀 快速开始

```bash
# 1. 进入项目
cd ~/hermes_workspace/story_tool

# 2. 安装依赖（Hermes 环境下已预装）
pip install fastapi uvicorn requests

# 3. 配置 API 密钥（写入 .env 或环境变量）
export DEEPSEEK_API_KEY="sk-your-key"

# 4. 启动服务
python3 web_app.py

# 5. 打开浏览器 → http://localhost:8888
```

### 使用 Hermes 启动脚本

```bash
# 自动加载 .env 中的 API 密钥
bash start_server.sh
```

### 环境变量

| 变量 | 用途 |
|:-----|:-----|
| `DEEPSEEK_API_KEY` | DeepSeek V4 Flash（默认后端） |
| `ZHIPU_API_KEY` / `GLM_API_KEY` | 智谱 API（备选后端，改 `llm.py` 中的 `API_BASE`） |

---

## ✨ 功能

### 📥 四级流水线

| 层级 | 作用 | AI 工具 |
|:----|:-----|:--------|
| **草稿箱** | 自由写作，记录原始想法 | 续写 · 脑暴 · 提炼 · 改写 |
| **节拍板** | 规划故事结构（支持父子层级） | 节奏分析 · 逻辑检查 · 补充节拍 |
| **章节** | 正文创作与阶段流转 | 续写/导演/脑暴/检查 + 3 种润色 |
| **大纲** | 全局视角 + 时间线 | 故事弧线分析 · 一致性检查 |

**关键交互**：每一步你可以**勾选**哪些内容进入下一步，AI 不会擅自决定。

### 🎭 角色管理
- 圆圈布局关系图谱（⭐ 主角 / 🔹 配角 / 💀 反派）
- 角色档案编辑 + 关系编辑器
- 创建故事时 AI 自动识别角色

### ✍️ 章节写作
- **4 种模式**：续写、导演（给指令）、脑暴（建议方向）、检查（批评分析）
- **3 种润色**：画面感、感人、紧张
- **阶段流**：📝 草稿 → 👀 初稿 → 🔧 修改 → ✅ 审核 → 📖 发布
- AI 生成计时器（秒级显示，避免假死感）

### 🔍 搜索与筛选
- 作品列表：标题搜索、体裁筛选、6 种排序
- ⭐ 焦点机制（焦点作品优先排序）
- ⚙️ 设置面板（焦点开关 · 信息统计）
- ✅ 批量删除

---

## 🏗️ 项目架构

```
story_tool/
├── web_app.py                 # FastAPI 入口（4 行）
├── framework.py               # 数据模型（DraftItem / Beat / Chapter / Character...）
├── comprehension.py           # AI 理解层（提取 → 确认 → 构建框架）
├── llm.py                     # LLM API 调用封装（requests）
├── models.py                  # Pydantic 请求/响应模型
│
├── routes/                    # API 路由（FastAPI）
│   ├── story.py               #   故事 CRUD + 焦点/设置
│   ├── drafts.py              #   草稿箱
│   ├── beats.py               #   节拍板
│   ├── chapters.py            #   章节管理
│   ├── outline.py             #   大纲
│   ├── characters.py          #   角色与关系图谱
│   ├── writing.py             #   写作（续写/导演/脑暴/检查）
│   └── ai_panel.py            #   通用 AI 面板（各层级分析工具）
│
├── services/
│   ├── storage.py             # JSON 文件持久化
│   └── context.py             # AI 上下文构建器
│
├── frontend/
│   └── index.html             # 单页 Web UI（纯 HTML/CSS/JS，零构建工具）
│
├── tests/                     # pytest 测试套件（93 个测试）
│   ├── conftest.py            #   共享 Fixtures
│   ├── test_framework.py      #   数据模型
│   ├── test_storage.py        #   持久化
│   ├── test_context.py        #   AI 上下文
│   └── test_routes.py         #   API 端点
│
├── start_server.sh            # 启动脚本（自动加载 .env）
├── stories/                   # 用户故事数据（JSON，.gitignore）
└── design_v3.svg              # 架构图
```

### 核心设计原则

```
Raw Ideas ──→ Comprehension Layer ──→ Story Framework ──→ Generation
    ↑               ↓      ↑                  ↓              ↓
    └── Refine ──────┘      └── Cards ◄────────┘      ◄── Polish
```

- **理解层**：AI 从不猜测，模糊点一定问用户确认
- **框架层**：一个知识库（角色 + 节拍 + 章节 + 大纲），所有模式共享
- **生成层**：多种模式读写同一个框架，切换模式不损失进度

---

## 🧪 测试

```bash
# 运行全部测试（93 个，覆盖框架/存储/上下文/路由）
cd ~/hermes_workspace/story_tool
python3 -m pytest tests/ -v

# 仅测试特定模块
python3 -m pytest tests/test_routes.py -v
```

测试创建的作品自动标记体裁为「测试」，可通过体裁筛选 + 批量删除清理。

---

## 🔧 开发指南

### 添加新功能

```
┌─ 后端 ─────────────────────────┐
│ routes/xxx.py    ← 新增路由文件   │
│ models.py        ← 新增 Pydantic  │
│ framework.py     ← 新增数据字段   │
└─────────────────────────────────┘
        ↓
┌─ 前端 ─────────────────────────┐
│ frontend/index.html            │
│   ← 新增 CSS / HTML / JS       │
└─────────────────────────────────┘
        ↓
┌─ 测试 ─────────────────────────┐
│ tests/test_xxx.py  ← 加测试    │
└─────────────────────────────────┘
```

### 数据流示例

```
用户勾选草稿 → POST /beats/generate → AI 分析草稿 + 已有节拍 → 返回 JSON
    ↓
用户勾选节拍 → POST /chapters/generate → AI 生成正文 → 自动提取摘要
    ↓
POST /outline/update → 从章节自动重建大纲
```

### 关键文件速查

| 文件 | 做什么 |
|:-----|:-------|
| `framework.py` | 所有数据类定义——改数据模型先改这里 |
| `comprehension.py` | AI 理解原始想法——提取角色/事件/问题 |
| `services/storage.py` | 读写 `stories/*.json`——改持久化逻辑在这里 |
| `services/context.py` | 构建 AI prompt 上下文——控制给 LLM 看什么 |
| `routes/ai_panel.py` | 通用 AI 面板——新增层级工具在这里注册 |
| `llm.py` | LLM 调用封装——换模型/改参数在这里 |

---

## 🛠️ 技术栈

| 层 | 技术 |
|:---|:-----|
| 后端 | Python 3.10+ · FastAPI · Uvicorn · Pydantic |
| 前端 | 纯 HTML / CSS / Vanilla JS · 无构建工具 · 单文件 |
| 数据 | JSON 文件（`stories/` 目录） · 无数据库依赖 |
| AI | DeepSeek V4 Flash / 智谱 GLM · REST API via `requests` |
| 测试 | pytest · in-memory fixtures · 93 tests |
| 硬件 | 支持低配置（Celeron J1900 / 4GB RAM / 无 GPU） |

---

## 📝 License

MIT
