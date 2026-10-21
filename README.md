# 驾考宝典智能查询助手

> 驾校内部业务工具：**一键生成驾考试卷并下载 Markdown**、**对话式查询驾考知识点**、**上传自定义题库自动阅卷评分**。
>
> 原生前端（HTML + CSS + JavaScript）+ Python FastAPI 后端，前后端严格分离，uv 全流程管理依赖，开箱即用。

**版本**：v0.1.0　｜　**内置题库**：92 题（科目一 52 / 科目四 40）　｜　**知识库**：40 个结构化知识点　｜　**接口**：12 个 RESTful API

## 目录

- [界面预览](#界面预览)
- [1. 项目解决什么问题](#1-项目解决什么问题)
- [2. 主要功能](#2-主要功能)
  - [2.1 一键生成试卷与 Markdown 下载](#21-一键生成驾考试卷与-markdown-下载)
  - [2.2 对话式知识问答](#22-对话式驾考知识点智能查询)
  - [2.3 上传自定义题库与自动阅卷评分](#23-上传自定义题库与自动阅卷评分)
  - [2.4 鉴权、跨域与工程能力](#24-鉴权跨域与工程能力)
- [3. 安装方法](#3-安装方法)
  - [3.1 环境要求](#31-环境要求)
  - [3.2 安装 uv](#32-安装-uv)
  - [3.3 安装后端依赖](#33-安装后端依赖)
  - [3.4 配置 API-KEY](#34-配置-api-key)
  - [3.5 前端安装说明](#35-前端安装说明)
  - [3.6 安装验证](#36-安装验证)
- [4. 使用方法](#4-使用方法)
  - [4.1 启动后端](#41-启动后端)
  - [4.2 启动前端](#42-启动前端)
  - [4.3 生成并下载试卷](#43-功能一生成并下载试卷)
  - [4.4 查询驾考知识点](#44-功能二查询驾考知识点)
  - [4.5 上传题库并自动阅卷](#45-功能三上传题库并自动阅卷)
  - [4.6 通过 API 使用](#46-通过-api-使用)
  - [4.7 数据与限制](#47-数据与限制)
- [5. 输入输出示例](#5-输入输出示例)
  - [5.0 统一约定](#50-统一约定)
  - [5.1 生成试卷](#51-生成试卷)
  - [5.2 驾考知识问答](#52-驾考知识问答)
  - [5.3 上传、作答与阅卷](#53-上传题库在线作答与自动阅卷)
  - [5.4 鉴权失败](#54-鉴权失败示例)
- [技术栈](#技术栈)
- [目录结构](#目录结构)
- [API 一览](#api-一览)
- [测试与验收](#测试与验收)
- [文档索引](#文档索引)
- [设计说明](#设计说明)
- [安全提示](#安全提示)
- [常见问题](#常见问题)

> 点击目录条目可直接跳转到对应章节；下方截图均来自真实运行界面。

## 界面预览

| 一键生成试卷 + MD 下载 | 对话式知识问答 |
|:---:|:---:|
| ![试卷生成](docs/screenshots/exam.png) | ![智能问答](docs/screenshots/chat.png) |
| 组卷参数、完整预览、答案速查、MD 下载 | 多轮追问、结构化知识点、历史记录恢复 |
| **上传题库 · 在线作答** | **自动阅卷 · 错题汇总** |
| ![在线作答](docs/screenshots/grading-paper.png) | ![阅卷结果](docs/screenshots/grading-result.png) |
| 上传解析、在线作答、进度跟踪 | 得分/正确率、错题解析、错题 MD |

## 1. 项目解决什么问题

驾校学员、教练和教务人员日常会在三件事上反复消耗时间：

| 真实痛点 | 本项目的解决方式 | 对应功能 |
|---|---|---|
| 出模拟卷要手工翻教材、复制题目、排版答案，不同教练出的卷子格式不统一 | 选择科目、题量、题型、章节，后端从内置题库自动抽题并按题型分节，页面预览后一键下载规范 Markdown 试卷 | 试卷生成 |
| 学员问“闯红灯扣几分”“坡道起步怎么不熄火”，教材检索慢，通用 AI 又可能编造法规 | 内置 40 个结构化驾考知识点，本地检索并输出讲解、要点、记忆技巧、易错提醒；非驾考问题明确拒答 | 智能问答 |
| 教练手头的 txt/md 题库只能人工对答案、算分、整理错题 | 上传 txt/md 题库自动解析，学员在线作答，系统立即判分、计算正确率、汇总错题并导出错题 Markdown | 上传阅卷 |
| 内部工具需要权限控制，部署又不想引入数据库和外部模型 | 所有业务接口统一 API-KEY 鉴权；本地 JSON 文件存储 + TTL；无需数据库，uv 一条命令启动 | 鉴权与工程能力 |

目标用户是**驾校学员、教练、教务人员**。项目不依赖外部大模型或在线服务，知识点和题目均可本地维护，适合内网或单机部署。

## 2. 主要功能

### 2.1 一键生成驾考试卷与 Markdown 下载

- 自定义**科目一 / 科目四**、**题目数量**、**题型（单选 / 判断 / 多选）**、**章节知识点**；
- 后端按筛选条件抽题（默认随机，可关闭乱序），自动按题型分节、计算建议用时与分值，满分 100 分、90 分合格；
- 每题包含题干、选项、标准答案、解析；页面完整预览，并附答案速查表；
- **一键下载 `.md`**：规范排版（标题、说明、章节、题号、选项、标准答案、解析、答案速查表），浏览器直出文件流；
- 额外支持下载**空白卷**（无答案、带答题卡）与查看 / 复制 Markdown 源码。

### 2.2 对话式驾考知识点智能查询

- 左右气泡聊天界面，支持**多轮连续对话**与上下文追问（如“那要罚多少钱”）；
- 内置 40 个结构化知识点，覆盖交通信号、标志标线、让行规则、扣分处罚、驾驶证业务、安全行车、科目二/三、事故应急、文明驾驶；
- 检索链路：关键词加权 → 同义词归一（红绿灯→信号灯、扣分→记分、刹车→制动等）→ 标题/分类匹配 → 字符二元组相似度 → 上下文拼接；
- 结构化回答包含**知识点讲解、要点、记忆技巧、易错提醒、相关追问**；
- 聊天记录保存在浏览器 `localStorage`，**刷新页面自动恢复**，支持一键清空；
- 非驾考问题友好拒答；驾考相关但库中未收录时明确提示，不编造答案。

### 2.3 上传自定义题库与自动阅卷评分

- 支持上传 `.txt` / `.md`，使用 `filetype` 校验真实文件类型，限制 2 MB / 300 题；
- 自动解析题号、题型、章节、题干、选项、标准答案、解析，兼容多种写法，错误行返回**行号与原因**；
- **标准答案仅保存在服务端**，上传响应不下发答案，避免前端直接看到答案；
- 在线作答：单选/判断 radio、多选 checkbox，实时显示作答进度与未答题数；
- 提交后立即计算**总分、正确率**，区分正确/错误，标注及格线与等级；
- 错题单独汇总，标注**你的答案、正确答案、解析**，支持**导出错题集 `.md`**；
- 支持查看全部题目详情、重新作答、上传新题库。

### 2.4 鉴权、跨域与工程能力

- 所有 `/api/v1` 业务接口强制 API-KEY：支持 `Authorization: Bearer <KEY>` 与 `x-api-key: <KEY>`，常量时间比较，失败返回 401；
- 统一 JSON 响应 `{code, msg, data}`，统一异常捕获；
- CORS 可配置，`file://` 直接打开前端也能调用后端；
- 前端仅原生 HTML/CSS/JS，无框架、无构建步骤；后端使用 uv、FastAPI、Pydantic v2；
- 提供 50 项后端自动化测试、端到端 UI 验证、完整 API 文档与部署文档。

## 3. 安装方法

### 3.1 环境要求

| 组件 | 要求 |
|---|---|
| 操作系统 | Windows 10+ / Linux / macOS |
| Python | 3.13+（uv 可自动安装） |
| uv | 0.11+（项目使用 0.11.14 验证） |
| 浏览器 | Chrome / Edge / Firefox 等现代桌面浏览器 |

> 前端不需要 Node.js、npm 或打包工具；运行时只需要浏览器。

### 3.2 安装 uv

Windows PowerShell：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

macOS / Linux：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

安装后重新打开终端，确认：

```bash
uv --version
```

### 3.3 安装后端依赖

项目已经完成 `uv init` 与 `uv add`，依赖版本锁定在 `backend/uv.lock`，无需再初始化：

```bash
cd backend
uv sync
```

`uv sync` 会创建/复用 `backend/.venv`、安装 FastAPI、Uvicorn、Pydantic、Python-Markdown、filetype、python-multipart、tzdata 等依赖，并安装 `serve` 入口脚本。

如需从零复现工程结构：

```bash
uv init backend --app --name driving-exam-assistant --python 3.13
cd backend
uv add fastapi "uvicorn[standard]" markdown filetype pydantic python-multipart python-dotenv tzdata
uv add --dev pytest httpx
uv sync
```

> `markdown` 即 Python-Markdown 的官方 PyPI 发行名；CORS 使用 FastAPI / Starlette 内置的 `CORSMiddleware`，无需额外包。项目禁止使用 pip 直接管理依赖。

### 3.4 配置 API-KEY

后端：

```bash
cd backend
cp .env.example .env        # Windows PowerShell: Copy-Item .env.example .env
```

编辑 `backend/.env`：

```dotenv
DT_API_KEY=sk-dtk-local-2026-change-me
```

前端编辑 `frontend/js/config.js`：

```javascript
window.DKA.config = {
  API_BASE_URL: 'http://127.0.0.1:8000',
  API_KEY: 'sk-dtk-local-2026-change-me',
  // ...
};
```

默认 key 仅供本地演示；对外部署前务必改成足够随机的字符串，并重启后端、强制刷新前端。

### 3.5 前端安装说明

前端是纯静态文件，**无需安装**：

- 直接双击 `frontend/index.html`；或
- 使用项目脚本启动静态服务器（推荐）：`.\start-frontend.ps1`；或
- 使用任意静态服务器 / Nginx 托管 `frontend/` 目录。

### 3.6 安装验证

启动后端后访问健康检查（需 API-KEY），或直接运行测试：

```bash
cd backend
uv run pytest
# 预期：50 passed
```

## 4. 使用方法

### 4.1 启动后端

Windows 项目根目录：

```powershell
.\start-backend.ps1
```

若 PowerShell 执行策略受限，可双击 / 执行：

```powershell
.\start-backend.bat
```

手动启动：

```bash
cd backend
uv run serve
```

启动后：

- 后端：<http://127.0.0.1:8000>
- Swagger：<http://127.0.0.1:8000/docs>（右上角 **Authorize** 填入 API-KEY）
- 健康检查：<http://127.0.0.1:8000/api/v1/health>（需请求头）

### 4.2 启动前端

**方式 A：直接打开**

双击 `frontend/index.html`，浏览器地址形如 `file:///.../frontend/index.html`。

**方式 B：静态 HTTP 服务（推荐）**

```powershell
.\start-frontend.ps1
```

访问 <http://127.0.0.1:5500>。

**方式 C：Windows 一键启动**

```powershell
.\start-all.ps1
```

会分别打开后端与前端窗口，并打开浏览器。

### 4.3 功能一：生成并下载试卷

1. 打开页面默认进入「试卷生成」；
2. 选择科目（科目一 / 科目四）；
3. 输入题目数量，或点击 10 / 20 / 30 / 50 / 全部；
4. 勾选题型（科目一支持单选、判断；科目四支持单选、判断、多选）；
5. 勾选章节知识点（默认全选，可全选/清空）；
6. 点击「一键生成试卷」；
7. 在右侧预览题干、选项、标准答案、解析与答案速查表；
8. 点击「下载 MD 试卷」导出 `.md`；点击「空白卷」导出无答案版本；点击「查看 MD 源码」查看/复制 Markdown。

### 4.4 功能二：查询驾考知识点

1. 切换到「智能问答」；
2. 在输入框输入问题，按 Enter 发送（Shift + Enter 换行）；
3. 查看左侧/右侧气泡中的结构化回答：讲解、要点、记忆技巧、易错提醒与追问建议；
4. 可继续追问（如先问“闯红灯扣几分”，再问“那要罚多少钱”）；
5. 刷新页面后聊天记录自动恢复；点击「清空历史」可清除本地记录。

### 4.5 功能三：上传题库并自动阅卷

1. 切换到「上传阅卷」；
2. 拖拽或选择 `.txt` / `.md` 题库（最大 2 MB，最多 300 题）；
3. 点击「上传并解析」，系统自动拆分题目与标准答案；
4. 在作答页完成单选、判断、多选，右侧显示作答进度；
5. 点击「提交阅卷」，立即查看得分、正确率、正确/错误题数；
6. 在错题汇总中查看你的答案、正确答案与解析；点击「下载错题 MD」导出；
7. 可「重新作答」或「上传新题库」。

题库格式示例：

```text
1. 【单选】机动车遇红灯时应当如何通行？
A. 在停止线以外停车等待
B. 加速通过
C. 减速通过
D. 鸣笛通过
答案：A
解析：红灯亮时应在停止线以外停车等待。

2. 【判断】黄灯亮时，已经越过停止线的车辆可以继续通行。
答案：正确
```

题号支持 `1.` / `1、` / `第1题` / `（1）`；题型支持 `【单选】` `【多选】` `【判断】`，也可省略由系统推断；判断题可省略选项。

### 4.6 通过 API 使用

所有 `/api/v1` 接口都需要 API-KEY。最小示例：

```bash
curl -s http://127.0.0.1:8000/api/v1/health \
  -H "Authorization: Bearer sk-dtk-local-2026-change-me"
```

文件下载接口成功时返回 Markdown 二进制流，因此需使用 `curl -o` 或前端 `fetch` + Blob；失败时仍返回标准 JSON 错误。完整接口清单与 curl 见 [docs/API.md](docs/API.md)。

### 4.7 数据与限制

- 生成试卷默认保留 24 小时，上传题库 24 小时，阅卷结果 72 小时；
- 聊天历史只保存在本机浏览器，不落服务端；
- 内置题库规模：科目一 52 题、科目四 40 题；请求题量不得超过当前筛选可用题量；
- 上传文件仅支持 UTF-8 / GBK 编码的 `.txt` / `.md`。

## 5. 输入输出示例

### 5.0 统一约定

**鉴权请求头（二选一）：**

```http
Authorization: Bearer sk-dtk-local-2026-change-me
```

```http
x-api-key: sk-dtk-local-2026-change-me
```

**JSON 接口统一响应：**

```json
{
  "code": 0,
  "msg": "success",
  "data": {}
}
```

`code=0` 表示成功，非 0 表示业务错误。文件下载成功时直接返回 Markdown 文件流，不包 JSON。

### 5.1 生成试卷

**输入（API 请求体）：**

```json
{
  "subject": "subject1",
  "question_count": 5,
  "question_types": ["single", "judge"],
  "chapters": ["交通法规与信号"],
  "shuffle": true
}
```

**输出（节选，题量与题型以实际抽题结果为准）：**

```json
{
  "code": 0,
  "msg": "试卷生成成功",
  "data": {
    "exam_id": "exam_20261021120000_ab12cd34",
    "title": "科目一 · 驾考模拟试卷",
    "subject": {
      "key": "subject1",
      "name": "科目一",
      "full_name": "科目一 · 道路交通安全法律、法规和相关知识"
    },
    "question_count": 5,
    "total_score": 100,
    "pass_score": 90,
    "duration_minutes": 5,
    "type_counts": { "single": 4, "judge": 1, "multiple": 0 },
    "covered_chapters": ["交通法规与信号"],
    "questions": [
      {
        "id": "s1-001",
        "number": 1,
        "type": "single",
        "type_name": "单选题",
        "chapter": "交通法规与信号",
        "stem": "前方交通信号灯为红灯时，机动车应当如何通行？",
        "options": [
          { "key": "A", "text": "在停止线以外停车等待" },
          { "key": "B", "text": "减速后直接通过" }
        ],
        "answer": ["A"],
        "explanation": "红灯亮时，禁止车辆通行，应当在停止线以外停车等待。",
        "score": 20.0
      }
    ],
    "md_filename": "科目一_驾考模拟试卷_exam_20261021120000_ab12cd34.md",
    "markdown": "# 科目一 · 驾考模拟试卷（含答案解析）\n..."
  }
}
```

**Markdown 下载：**

```bash
curl -L "http://127.0.0.1:8000/api/v1/exams/exam_20261021120000_ab12cd34/download" \
  -H "Authorization: Bearer sk-dtk-local-2026-change-me" \
  -o 科目一_驾考模拟试卷.md
```

下载文件内容示例：

```markdown
# 科目一 · 驾考模拟试卷（含答案解析）

> 试卷编号：exam_20261021120000_ab12cd34
> 题目数量：5 题　总分：100 分　合格线：90 分　建议用时：5 分钟

## 一、单选题（共 4 题，每题 20 分）

### 第 1 题

> 章节：交通法规与信号

前方交通信号灯为红灯时，机动车应当如何通行？

- **A.** 在停止线以外停车等待
- **B.** 减速后直接通过

**标准答案：** A

**解析：** 红灯亮时，禁止车辆通行，应当在停止线以外停车等待。
```

**前端效果：** 页面展示完整试卷与答案速查表；点击「下载 MD 试卷」得到上述 `.md` 文件；点击「空白卷」得到无答案、带答题卡的版本。

### 5.2 驾考知识问答

**输入（支持多轮上下文）：**

```json
{
  "message": "那要罚多少钱",
  "history": [
    { "role": "user", "content": "闯红灯扣几分？" },
    { "role": "assistant", "content": "闯红灯一次记 6 分。" }
  ],
  "session_id": "chat_demo_001"
}
```

**输出（节选）：**

```json
{
  "code": 0,
  "msg": "回答成功",
  "data": {
    "matched": true,
    "intent": "knowledge",
    "session_id": "chat_demo_001",
    "question": "那要罚多少钱",
    "context_used": true,
    "matched_keywords": ["闯红灯", "红灯", "闯红灯扣几分"],
    "topics": [
      {
        "id": "kb-red-light",
        "category": "交通信号与标志",
        "title": "闯红灯的记分与处罚",
        "summary": "驾驶机动车违反道路交通信号灯通行（俗称闯红灯），一次记 6 分，并依法处以罚款。",
        "points": [
          "处罚：一次记 6 分，通常并处 200 元罚款，具体金额以当地规定为准。",
          "红灯右转：若设有右转箭头红灯或“禁止右转”标志，必须停车等待。"
        ],
        "memory_tip": "“红灯停、绿灯行、黄灯亮了等一等”；闯红灯＝6 分。",
        "pitfalls": [
          "黄灯亮时已经越过停止线的车辆可以继续通行，不算闯红灯。"
        ],
        "suggested_questions": ["红灯时右转算闯红灯吗？", "黄灯亮时还能不能走？"]
      }
    ],
    "suggestions": ["红灯时右转算闯红灯吗？", "黄灯亮时还能不能走？"],
    "reply_markdown": "> 已结合上一轮对话理解你的问题。\n\n### 闯红灯的记分与处罚\n..."
  }
}
```

**未命中示例：**

```json
{
  "code": 0,
  "msg": "回答成功",
  "data": {
    "matched": false,
    "intent": "out_of_scope",
    "question": "今天天气怎么样？",
    "topics": [],
    "reply_markdown": "抱歉，我是驾考知识助手，只能回答与驾考相关的问题……",
    "suggestions": ["闯红灯扣几分？", "高速公路最低限速是多少？"]
  }
}
```

**前端效果：** 用户问题显示在右侧气泡，助手回答显示在左侧；多轮追问会自动带入上一轮上下文。

### 5.3 上传题库、在线作答与自动阅卷

**输入文件 `traffic_bank.md`：**

```markdown
# 交通法规练习题库

## 第一章 交通法规与信号

1. 【单选】机动车遇红灯时应当如何通行？
A. 在停止线以外停车等待
B. 加速通过
C. 减速通过
D. 鸣笛通过
答案：A
解析：红灯亮时应在停止线以外停车等待。
```

**上传解析输出（节选，答案不会下发给前端）：**

```json
{
  "code": 0,
  "msg": "题库解析成功",
  "data": {
    "paper_id": "paper_20261021120000_ab12cd34",
    "filename": "traffic_bank.md",
    "title": "交通法规练习题库",
    "question_count": 1,
    "type_counts": { "single": 1, "judge": 0, "multiple": 0 },
    "chapters": ["交通法规与信号"],
    "total_score": 100,
    "pass_score": 90,
    "questions": [
      {
        "id": "q001",
        "number": 1,
        "type": "single",
        "type_name": "单选题",
        "chapter": "交通法规与信号",
        "stem": "机动车遇红灯时应当如何通行？",
        "options": [
          { "key": "A", "text": "在停止线以外停车等待" },
          { "key": "B", "text": "加速通过" }
        ],
        "has_explanation": true
      }
    ],
    "parse_report": { "errors": [], "warnings": [], "chapters": ["交通法规与信号"] }
  }
}
```

**提交作答输入：**

```json
{
  "paper_id": "paper_20261021120000_ab12cd34",
  "answers": [
    { "question_id": "q001", "answer": ["A"] }
  ],
  "duration_seconds": 30
}
```

**全部正确时的输出（节选）：**

```json
{
  "code": 0,
  "msg": "阅卷完成",
  "data": {
    "result_id": "result_20261021120000_ef56ab78",
    "score": 100.0,
    "full_score": 100,
    "accuracy": 100.0,
    "pass_score": 90,
    "passed": true,
    "grade": "优秀",
    "total_questions": 1,
    "correct_count": 1,
    "wrong_count": 0,
    "answered_count": 1,
    "unanswered_count": 0,
    "duration_text": "30 秒",
    "wrong_questions": []
  }
}
```

**答错时的输出（节选）：**

```json
{
  "code": 0,
  "msg": "阅卷完成",
  "data": {
    "score": 0.0,
    "accuracy": 0.0,
    "passed": false,
    "grade": "不合格",
    "correct_count": 0,
    "wrong_count": 1,
    "wrong_questions": [
      {
        "number": 1,
        "type_name": "单选题",
        "chapter": "交通法规与信号",
        "stem": "机动车遇红灯时应当如何通行？",
        "user_answer": ["B"],
        "user_answer_text": "B（加速通过）",
        "correct_answer": ["A"],
        "correct_answer_text": "A（在停止线以外停车等待）",
        "explanation": "红灯亮时应在停止线以外停车等待。"
      }
    ]
  }
}
```

**错题 Markdown 下载内容示例：**

```markdown
# 错题集 · 交通法规练习题库

## 错题汇总

| 错题序号 | 原题号 | 题型 | 章节 | 你的答案 | 正确答案 |
|:--:|:--:|---|---|:--:|:--:|
| 1 | 1 | 单选题 | 交通法规与信号 | B | A |

## 错题详解

### 错题 1（原题第 1 题 · 单选题）

**你的答案：** B

**正确答案：** A

**解析：** 红灯亮时应在停止线以外停车等待。
```

**前端效果：** 上传后进入在线作答页；提交后展示分数环、正确率、错题汇总与全部题目详情；点击「下载错题 MD」得到上述文件。

### 5.4 鉴权失败示例

```bash
curl -i http://127.0.0.1:8000/api/v1/health
```

```json
{
  "code": 401,
  "msg": "缺少 API-KEY。请在请求头携带 Authorization: Bearer <API_KEY> 或 x-api-key: <API_KEY>。",
  "data": null
}
```

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | 原生 HTML5 + CSS3 + JavaScript（ES2017+），无 Vue / React / uni-app 等框架；原生 `fetch` |
| 后端 | Python 3.13 + FastAPI + Uvicorn，RESTful API |
| 依赖管理 | **uv**（`uv init` / `uv add` / `uv sync` / `uv run`）；`pyproject.toml` + `uv.lock` |
| 参数校验 | Pydantic v2 |
| Markdown | Python-Markdown（PyPI 发行名 `Markdown`，`import markdown`） |
| 文件类型 | `filetype`（魔数校验） |
| 上传解析 | `python-multipart` |
| 跨域 | FastAPI / Starlette 内置 `CORSMiddleware` |
| 鉴权 | 固定 API-KEY，`Authorization: Bearer` + `x-api-key` 双支持，常量时间比较，对齐 Claude Code 使用方式 |
| 存储 | 本地 JSON 文件 + 原子写 + TTL（无需数据库） |
| 测试 | pytest + httpx（后端 50 项）；Edge + Playwright（前端端到端验证） |

## 目录结构

```text
E:\workspace
├── README.md                        # 本文件：问题、功能、安装、使用、示例、目录
├── .gitignore                       # 忽略 .env、虚拟环境、运行时数据、测试产物
├── .gitattributes                   # Git 行尾统一：sh=LF、bat/ps1=CRLF、图片=二进制
├── start-backend.ps1                # Windows：启动后端（委托 backend/scripts/start.ps1）
├── start-backend.bat                # Windows 批处理：启动后端
├── start-backend.sh                 # Linux / macOS：启动后端
├── start-frontend.ps1               # Windows：以静态 HTTP 服务启动前端（5500 端口）
├── start-frontend.bat               # Windows 批处理：启动前端
├── start-frontend.sh                # Linux / macOS：启动前端
├── start-all.ps1                    # Windows：同时打开后端 + 前端窗口并启动浏览器
├── samples/
│   ├── sample_bank.md               # 示例题库（Markdown，10 题，覆盖单选/判断/多选）
│   └── sample_bank.txt              # 示例题库（txt，5 题，可用于上传测试）
│
├── backend/                         # ================= 后端模块 =================
│   ├── pyproject.toml               # uv 项目定义、依赖、serve 脚本、pytest 配置
│   ├── uv.lock                      # uv 锁定依赖版本（可复现安装）
│   ├── .python-version              # Python 3.13
│   ├── .env.example                 # 环境变量模板（API-KEY、CORS、TTL、上传限制等）
│   ├── README.md                    # 后端模块说明
│   ├── scripts/
│   │   ├── start.ps1                # 后端启动脚本（Windows PowerShell）
│   │   ├── start.bat                # 后端启动脚本（Windows CMD）
│   │   └── start.sh                 # 后端启动脚本（Linux / macOS）
│   ├── app/
│   │   ├── __init__.py              # 应用包与版本号
│   │   ├── main.py                  # FastAPI 入口：CORS、路由挂载、全局异常、启动预热、uv run serve
│   │   ├── config.py                # 全局配置（.env 读取、API-KEY、时区、TTL、上传限制）
│   │   ├── errors.py                # BusinessError / ApiKeyError 业务异常
│   │   ├── responses.py             # 统一 {code,msg,data} 响应构造
│   │   ├── security.py              # API-KEY 提取与常量时间校验（Bearer / x-api-key）
│   │   ├── models.py                # Pydantic 请求模型与参数校验（科目/题型/答案/历史消息）
│   │   ├── normalization.py         # 科目/题型/章节归一化常量与函数
│   │   ├── utils.py                 # 时间、ID、文件名、Content-Disposition、时长格式化
│   │   ├── storage.py               # 线程安全 JSON 文件存储（原子写 + TTL 清理）
│   │   ├── deps.py                  # 试卷 / 题库 / 阅卷结果三个存储实例
│   │   ├── data/
│   │   │   ├── subjects.json        # 科目、章节、支持题型、标准卷题量配置
│   │   │   ├── questions_subject1.json # 科目一内置题库（52 题，含答案与解析）
│   │   │   ├── questions_subject4.json # 科目四内置题库（40 题，含多选）
│   │   │   └── knowledge_base.json  # 40 个结构化驾考知识点 + 8 个分类 + 热门问题
│   │   ├── routers/
│   │   │   ├── __init__.py          # 路由包
│   │   │   ├── system.py            # GET /health 健康检查
│   │   │   ├── exams.py             # 组卷元信息、生成、详情、MD 预览、MD 下载
│   │   │   ├── chat.py              # 聊天问答、问答初始化信息
│   │   │   ├── questions.py         # 题库文件上传解析
│   │   │   └── grading.py           # 提交阅卷、查询结果、错题 MD 下载
│   │   └── services/
│   │       ├── __init__.py          # 服务包
│   │       ├── bank.py              # 题库加载、校验、按条件筛选、元信息统计
│   │       ├── exam_service.py      # 组卷算法、分值计算、试卷落盘、下载数据
│   │       ├── markdown_service.py  # 试卷/错题 Markdown 渲染、MD→HTML、预览样式
│   │       ├── chat_service.py      # 知识库检索、同义词归一、上下文、意图识别
│   │       ├── parser_service.py    # txt/md 题库解析、文件类型/编码校验、答案隐藏
│   │       └── grading_service.py   # 逐题判分、总分/正确率、错题汇总、错题 MD
│   └── tests/
│       ├── conftest.py              # 测试隔离数据目录、TestClient、固定测试 key
│       ├── test_auth.py             # 鉴权 / CORS / 统一错误（11 项）
│       ├── test_exams.py            # 组卷 / 筛选 / 预览 / MD 下载（16 项）
│       ├── test_chat.py             # 知识命中 / 上下文 / 越界拒答（8 项）
│       └── test_grading.py          # 上传解析 / 自动阅卷 / 错题导出（15 项）
│
├── frontend/                        # ================= 前端模块 =================
│   ├── index.html                   # 单页应用：导航 + 三个功能 Tab 的完整 DOM 结构
│   ├── README.md                    # 前端模块说明
│   ├── css/
│   │   └── style.css                # 全站样式：设计变量、布局、组件、响应式、打印
│   ├── js/
│   │   ├── config.js                # 前端配置：API 地址、API-KEY、存储 key
│   │   ├── api.js                   # fetch 封装：鉴权头、统一响应、错误、Blob 下载
│   │   ├── ui.js                    # DOM 构建、Toast、按钮状态、纯文本 Markdown 渲染、storage
│   │   ├── app.js                   # 应用入口：Tab 切换、服务状态检测、模块初始化
│   │   ├── exam.js                  # 功能一：组卷表单、预览、MD 源码、下载
│   │   ├── chat.js                  # 功能二：聊天 UI、历史恢复、结构化回答、多轮
│   │   └── grading.js               # 功能三：上传、作答、进度、阅卷结果、错题导出
│   └── samples/
│       ├── sample_bank.md           # 前端可直接下载的示例题库（与根 samples 一致）
│       └── sample_bank.txt          # 前端示例题库
│
├── docs/                            # ================= 文档 =================
│   ├── API.md                       # 完整接口文档：鉴权、错误码、12 个接口示例、curl
│   ├── DEPLOY.md                    # 部署与使用教程：uv 安装、初始化、配置、Nginx、systemd
│   ├── TEST.md                      # 功能自测说明：50 项自动化 + UI 端到端 + 手工验收清单
│   └── screenshots/
│       ├── exam.png                 # 试卷生成界面截图
│       ├── chat.png                 # 智能问答界面截图
│       ├── grading-paper.png        # 在线作答界面截图
│       └── grading-result.png       # 阅卷结果界面截图
│
└── backend/.data/                   # 运行时生成（不提交）：exams / papers / results
```

## API 一览

| 方法 | 路径 | 功能 |
|---|---|---|
| GET | `/api/v1/health` | 健康检查（同时校验 API-KEY） |
| GET | `/api/v1/exams/meta` | 科目 / 题型 / 章节 / 题库量 |
| POST | `/api/v1/exams/generate` | 一键生成试卷 |
| GET | `/api/v1/exams/{exam_id}` | 试卷详情 |
| GET | `/api/v1/exams/{exam_id}/preview` | Markdown + HTML 预览 |
| GET | `/api/v1/exams/{exam_id}/download` | 下载 MD（`include_answers=false` 为空白卷） |
| GET | `/api/v1/chat/suggestions` | 知识分类 / 热门问题 / 能力介绍 |
| POST | `/api/v1/chat` | 驾考知识问答（多轮上下文） |
| POST | `/api/v1/questions/upload` | 上传 txt / md 题库并解析 |
| POST | `/api/v1/grading/submit` | 提交作答自动阅卷 |
| GET | `/api/v1/grading/{result_id}` | 查询阅卷结果 |
| GET | `/api/v1/grading/{result_id}/wrong-answers/download` | 导出错题 MD |

- 所有 JSON 接口统一返回 `{code, msg, data}`；文件下载接口成功时返回二进制流，失败仍返回 JSON；
- 所有 `/api/v1` 接口都必须携带 `Authorization: Bearer <API_KEY>` 或 `x-api-key: <API_KEY>`；
- 详细入参、出参、错误码与 curl 示例见 **[docs/API.md](docs/API.md)**。

## 测试与验收

```bash
cd backend
uv run pytest
```

实际结果：

```text
50 passed
```

- 后端覆盖鉴权、CORS、组卷、筛选、MD 下载、空白卷、问答命中、多轮上下文、越界拒答、上传解析、满分/错题阅卷、错题 MD 等；
- 前端已使用 Edge + Playwright 对真实页面与真实后端完成端到端验证：生成→预览→下载、问答→追问→刷新恢复、上传→作答→100/80 分→错题导出→全部详情；
- 逐条验收清单见 **[docs/TEST.md](docs/TEST.md)**。

## 文档索引

| 文档 | 内容 |
|---|---|
| [docs/API.md](docs/API.md) | 接口总览、API-KEY 规则、统一响应、错误码、12 个接口的入参/出参/curl |
| [docs/DEPLOY.md](docs/DEPLOY.md) | uv 安装、项目初始化、前后端启动、API-KEY 修改、Nginx、systemd、备份与排错 |
| [docs/TEST.md](docs/TEST.md) | 自动化测试结果、UI 端到端结果、逐条功能验收清单、边界测试、已知限制 |
| [backend/README.md](backend/README.md) | 后端目录、启动、测试、数据与算法说明 |
| [frontend/README.md](frontend/README.md) | 前端打开方式、配置、模块职责、交互与本地存储 |

## 设计说明

### 为什么问答不接大模型？

本项目定位为**驾校内部工具**，要求可控、可离线、无额外成本。问答采用本地结构化知识库检索：

- 40 个知识点均有明确的讲解、要点、记忆技巧、易错提醒，避免大模型幻觉；
- 同义词归一 + 关键词加权 + 字符相似度 + 上下文拼接，覆盖常见问法；
- 非驾考问题直接拒答，未收录问题明确提示；
- 后续可在 `knowledge_base.json` 持续扩充，无需改代码。

### 鉴权如何对齐 Claude Code？

- 与 Claude Code / Anthropic SDK 相同的两种传参方式：`Authorization: Bearer` 与 `x-api-key`；
- 请求头精确匹配、`hmac.compare_digest` 常量时间比较、401 带 `WWW-Authenticate`；
- 支持 `ANTHROPIC_API_KEY` 作为 `DT_API_KEY` 未设置时的兼容回退；
- 所有 `/api/v1` 业务路由统一挂载鉴权依赖，无遗漏；文件下载也必须带 key。

### 数据存储

- 生成试卷、上传题库、阅卷结果使用本地 JSON 文件存储，原子写，TTL 过期清理；
- 聊天历史保存在浏览器，不落到服务端；
- 无需数据库即可完整运行；多实例/高并发场景可替换为 Redis/PostgreSQL/对象存储。

## 安全提示

1. 本项目为**内部业务工具**，前端固定 API-KEY 对使用者可见；公网部署请在 Nginx / 网关增加 SSO、Basic Auth 或 IP 白名单；
2. 对外部署必须修改默认 API-KEY；
3. 已做文件扩展名、真实类型（`filetype`）、大小、题量限制；所有动态文本使用 `textContent` 渲染，避免 XSS；
4. 题库与知识库依据公开驾考资料整理，具体处罚与记分以当地交管部门最新规定为准。

## 常见问题

| 问题 | 解决 |
|---|---|
| 页面右上角「后端未连接」 | 确认后端已启动；检查 `config.js` 的 `API_BASE_URL` |
| 「API-KEY 无效」 | 前后端 key 一致；重启后端；`Ctrl+F5` 刷新 |
| 生成时提示题量不足 | 当前筛选可用题量不足，减少题量或放宽章节/题型 |
| 上传被拒绝 | 只支持 UTF-8/GBK 的 `.txt`/`.md`，≤2 MB，格式参照示例题库 |
| 下载无反应 | 查看 toast 提示；试卷默认 24 小时过期，重新生成 |
| uv 命令不存在 | 重新安装 uv 并打开新终端；Windows 也可使用 `.bat` 脚本 |

---

↑ [返回目录](#目录)

**驾考宝典智能查询助手 · 驾校内部业务工具 · 仅供教学练习使用**
