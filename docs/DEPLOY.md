# 部署与使用教程

## 1. 项目架构

```text
┌────────────────────────────┐        HTTP / JSON        ┌────────────────────────────┐
│  前端（纯静态）             │  Authorization: Bearer    │  后端（FastAPI）            │
│  frontend/index.html       │ ────────────────────────► │  /api/v1/*                 │
│  原生 HTML + CSS + JS       │                           │  API-KEY 鉴权               │
│  试卷 / 问答 / 阅卷三个 Tab │ ◄──────────────────────── │  统一 {code,msg,data}      │
└────────────────────────────┘   Markdown / JSON 响应     │  内置题库 + 知识库          │
                                                          │  .data 临时存储             │
                                                          └────────────────────────────┘
```

- 前端与后端**完全分离**：前端为纯静态文件，可 `file://` 直接打开，也可由 Nginx / Python 静态服务器托管；后端不托管前端页面。
- 后端依赖由 **uv** 统一管理（`pyproject.toml` + `uv.lock`），禁止使用 pip 直接安装。
- 数据默认保存在 `backend/.data`，无需数据库即可运行。

## 2. 环境要求

| 组件 | 版本 / 说明 |
|---|---|
| Python | 3.13+（uv 可自动安装） |
| uv | 0.8+（项目使用 0.11 开发验证；官方安装脚本即可） |
| 浏览器 | Chrome / Edge / Firefox 等现代浏览器（桌面端） |
| 操作系统 | Windows 10+ / Linux / macOS 均可 |

### 2.1 安装 uv

**Windows PowerShell：**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS / Linux：**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

安装后新开终端确认：

```bash
uv --version
```

> 如果 PowerShell 提示禁止运行脚本，可使用 `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`，或直接使用 `.bat` 启动脚本。

## 3. 项目初始化（uv 标准流程）

本项目已使用 uv 完成初始化，正常情况下只需同步依赖。若需要从零复现同样的工程结构，可执行：

```bash
# 1. 创建后端项目（本项目已执行）
uv init backend --app --name driving-exam-assistant --python 3.13

cd backend

# 2. 安装运行依赖（本项目已执行）
uv add fastapi "uvicorn[standard]" markdown filetype pydantic python-multipart python-dotenv tzdata

# 3. 安装开发依赖（pytest / httpx）
uv add --dev pytest httpx

# 4. 同步环境（按 uv.lock 创建 .venv）
uv sync

# 5. 启动
uv run serve
# 等价于：
# uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

说明：

- `markdown` 即 **Python-Markdown** 的官方 PyPI 发行名，`import markdown` 使用，用于把试卷 Markdown 渲染为 HTML 预览。
- CORS 由 FastAPI 内置的 `fastapi.middleware.cors.CORSMiddleware`（Starlette）提供，无需额外第三方包。
- 项目不允许也不需要使用 `pip install`；所有依赖、虚拟环境、脚本都由 uv 管理。

## 4. 快速启动

### 4.1 一键启动后端（推荐）

Windows：

```powershell
# 在项目根目录
.\start-backend.ps1
```

或双击 `start-backend.bat`；Linux / macOS：

```bash
chmod +x start-backend.sh
./start-backend.sh
```

脚本会自动：

1. 检查 uv；
2. 若不存在 `backend/.env`，从 `.env.example` 复制；
3. 执行 `uv sync`；
4. 执行 `uv run serve` 启动在 `http://127.0.0.1:8000`。

启动成功后可访问：

- API 根路径（无页面）：`http://127.0.0.1:8000/api/v1/health`（需 API-KEY）
- Swagger 文档：`http://127.0.0.1:8000/docs`
- ReDoc：`http://127.0.0.1:8000/redoc`

### 4.2 手动启动后端

```bash
cd backend
cp .env.example .env          # Windows: copy .env.example .env
# 编辑 .env，修改 DT_API_KEY
uv sync
uv run serve
```

开发热重载：

```bash
# 在 backend/.env 中设置 DT_RELOAD=true，或直接执行：
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 4.3 启动前端

**方式 A：直接打开（最简）**

双击 `frontend/index.html`，或浏览器打开：

```text
file:///E:/workspace/frontend/index.html
```

后端 CORS 默认允许全部来源，`file://`（Origin: null）可以直接请求 `http://127.0.0.1:8000`。

**方式 B：静态 HTTP 服务**

```powershell
# Windows（会自动优先使用 python，其次使用 uv 环境中的 python）
.\start-frontend.ps1
# 或
.\start-frontend.bat
```

```bash
# Linux / macOS
./start-frontend.sh
```

访问 `http://127.0.0.1:5500`。

**方式 C：一键启动两个窗口（Windows）**

```powershell
.\start-all.ps1
```

会分别打开后端、前端 PowerShell 窗口，并打开浏览器。

## 5. API-KEY 配置（必须前后端一致）

### 5.1 后端配置

编辑 `backend/.env`：

```dotenv
DT_API_KEY=sk-dtk-your-own-secret-2026
```

- 未创建 `.env` 时，后端使用内置默认值 `sk-dtk-local-2026-change-me`，只适合本地演示；
- 也可使用环境变量直接覆盖，例如 Docker / systemd / 云平台；
- 兼容 Claude Code 的 `ANTHROPIC_API_KEY`：未设置 `DT_API_KEY` 时会自动读取它作为校验 key；
- 修改后需**重启后端**。

### 5.2 前端配置

编辑 `frontend/js/config.js`：

```javascript
window.DKA.config = {
  API_BASE_URL: 'http://127.0.0.1:8000',
  API_KEY: 'sk-dtk-your-own-secret-2026',
  // ...
};
```

- `API_KEY` 必须与后端 `DT_API_KEY` 完全一致；
- 前端统一以 `Authorization: Bearer {API_KEY}` 请求头调用接口；
- 修改后刷新页面（必要时 `Ctrl + F5` 强制刷新，避免 `config.js` 缓存）。

### 5.3 鉴权验证

```bash
# 应返回 200 + code 0
curl -s http://127.0.0.1:8000/api/v1/health \
  -H "Authorization: Bearer sk-dtk-your-own-secret-2026"

# 使用 x-api-key 也可以
curl -s http://127.0.0.1:8000/api/v1/health \
  -H "x-api-key: sk-dtk-your-own-secret-2026"

# 不携带或 key 错误：401
curl -i http://127.0.0.1:8000/api/v1/health
```

## 6. 生产部署

### 6.1 后端（Linux + systemd 示例）

**上传代码到 `/opt/driving-exam-assistant`**，然后：

```bash
cd /opt/driving-exam-assistant/backend
cp .env.example .env
vi .env
# 必改：DT_API_KEY；生产建议：DT_CORS_ORIGINS=https://你的域名
uv sync --frozen
```

创建 systemd 服务 `/etc/systemd/system/driving-exam.service`：

```ini
[Unit]
Description=Driving Exam Assistant API
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/driving-exam-assistant/backend
EnvironmentFile=/opt/driving-exam-assistant/backend/.env
ExecStart=/usr/local/bin/uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=3
TimeoutStopSec=20

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now driving-exam
sudo systemctl status driving-exam
```

> 注意：`uv` 的实际路径以 `which uv` 为准；`WorkingDirectory` 必须指向 `backend`，否则相对路径 `.data` 会落到别处。若使用 workers > 1，各进程共享文件存储；当前存储为文件级原子写，适合中小规模内部工具，高并发建议后续替换为数据库/对象存储。

**Windows 生产部署**可使用 NSSM 注册服务：

```powershell
nssm install DrivingExamBackend "C:\Users\Administrator\.local\bin\uv.exe" "run serve"
nssm set DrivingExamBackend AppDirectory "E:\workspace\backend"
nssm set DrivingExamBackend AppStdout "E:\workspace\backend\logs\stdout.log"
nssm set DrivingExamBackend AppStderr "E:\workspace\backend\logs\stderr.log"
nssm start DrivingExamBackend
```

或使用「任务计划程序」设置开机启动并运行 `start-backend.bat`。

### 6.2 前端（Nginx 静态托管 + 反向代理）

将 `frontend/` 复制到 `/var/www/driving-exam/`，修改 `frontend/js/config.js`：

```javascript
API_BASE_URL: '',                  // 同源，走 Nginx /api 反向代理
API_KEY: 'sk-dtk-your-own-secret-2026'
```

Nginx 配置示例：

```nginx
server {
    listen 80;
    server_name exam.example.com;
    root /var/www/driving-exam;
    index index.html;

    # 静态前端
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 后端 API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
        client_max_body_size 4m;   # 上传题库限制 2 MB，预留余量
    }

    # API 文档（内网可保留，公网建议关闭或加访问控制）
    # location ~ ^/(docs|redoc|openapi.json) {
    #     proxy_pass http://127.0.0.1:8000;
    # }
}
```

生产建议：

- 启用 HTTPS（certbot / 云证书），否则 API-KEY 在浏览器与服务器之间明文传输；
- `DT_CORS_ORIGINS` 改为实际域名，避免任意站点调用；
- 按需关闭 `/docs`、`/redoc` 的公网访问，或加 Basic Auth / 内网 ACL；
- Nginx 增加上传大小与超时限制（与 `DT_MAX_UPLOAD_MB` 对齐）；
- 定期轮换 API-KEY，并同步修改前端 `config.js`。

### 6.3 反向代理同源模式注意事项

- `API_BASE_URL: ''` 时，前端请求 `/api/v1/...`，与页面同源，不受 CORS 限制；
- 后端仍会校验 `Authorization`，不能省略；
- 如前后端不同域（前端 `:5500`，后端 `:8000`），保持默认 `http://127.0.0.1:8000`，并把后端 `DT_CORS_ORIGINS` 设置为前端地址（或暂时 `*`）。

## 7. 配置项说明

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `DT_API_KEY` | `sk-dtk-local-2026-change-me` | 全局 API-KEY，必须与前端一致 |
| `ANTHROPIC_API_KEY` | 无 | `DT_API_KEY` 未设置时的兼容回退 |
| `DT_HOST` | `127.0.0.1` | 监听地址；对外提供服务可改 `0.0.0.0` |
| `DT_PORT` | `8000` | 监听端口 |
| `DT_RELOAD` | `false` | 是否热重载（开发用） |
| `DT_CORS_ORIGINS` | `*` | 允许的来源，逗号分隔；`*` 为全部 |
| `DT_DATA_DIR` | `backend/.data` | 试卷 / 题库 / 阅卷结果存储目录 |
| `DT_EXAM_TTL_HOURS` | `24` | 生成试卷保留时长 |
| `DT_PAPER_TTL_HOURS` | `24` | 上传题库保留时长 |
| `DT_RESULT_TTL_HOURS` | `72` | 阅卷结果保留时长 |
| `DT_MAX_UPLOAD_MB` | `2` | 上传文件大小上限 |
| `DT_MAX_UPLOAD_QUESTIONS` | `300` | 单次上传题目数量上限 |
| `DT_TIMEZONE` | `Asia/Shanghai` | 时间与时区 |
| `DT_PASS_SCORE` | `90` | 合格分数线 |

> 前端试卷题目上限由题库元信息 `limits.max_question_count` 提供；内置题库科目一 52 题、科目四 40 题，因此实际可生成题量受当前筛选条件限制。

## 8. 数据备份与清理

```text
backend/.data/
├── exams/      # 生成的试卷 JSON
├── papers/     # 上传解析后的题库（含标准答案）
└── results/    # 阅卷结果 JSON
```

- 备份：直接备份 `backend/.data` 目录即可（或配置 `DT_DATA_DIR` 到持久化盘）；
- 清理：停止服务后删除对应目录，重启会自动重建；过期数据也会在写入时自动惰性清理；
- 安全：`papers` 目录包含标准答案，注意目录权限；
- 临时数据不包含用户账号等敏感个人信息，但聊天记录保存在浏览器 `localStorage`，可通过「清空历史」删除。

## 9. 常见问题排查

| 现象 | 原因 | 解决 |
|---|---|---|
| 页面右上角「后端未连接」 | 后端未启动 / 地址错误 / 端口被占用 | 启动后端；检查 `frontend/js/config.js` 的 `API_BASE_URL`；`netstat -ano | findstr :8000` |
| 页面右上角「API-KEY 无效」 | 前后端 key 不一致 | 修改 `backend/.env` 后重启；同步修改 `config.js` 并强制刷新 |
| 浏览器控制台 CORS 报错 | 后端未启动 / CORS 配置限制 | 确认 CORS 中间件已启用；`DT_CORS_ORIGINS=*` 或加入前端来源 |
| 上传提示「文件真实类型不是纯文本」 | 文件是 PDF / 图片 / docx 伪装扩展名 | 另存为真正的 UTF-8 `.txt` / `.md` |
| 上传解析 0 题 | 格式不符合要求 | 对照 `samples/sample_bank.md`，检查题号、选项、`答案：X` |
| 生成试卷提示题量不足 | 筛选后可用题量少于请求题量 | 减少题量、增加题型或放宽章节 |
| 下载没有反应 | API-KEY 失效 / 试卷过期 | 查看 toast 错误；重新生成试卷后下载 |
| `uv: command not found` | 未安装或未加入 PATH | 重新执行 uv 安装脚本，或使用绝对路径 |
| PowerShell 禁止运行脚本 | 执行策略限制 | 使用 `.bat`，或 `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| 时间显示不是北京时间 | 时区未生效（Windows 缺 tzdata） | 项目已依赖 `tzdata`；检查 `DT_TIMEZONE` |

## 10. 安全与合规提示

1. **前端 API-KEY 是可见的**：本工具定位为驾校内部业务工具，固定 key 方案适合内网/受控环境；公网部署建议在 Nginx / API 网关层再加一层身份认证（如 SSO、Basic Auth、IP 白名单），不要把固定 key 当作公网用户级鉴权。
2. **修改默认 key**：任何对外部署必须修改 `sk-dtk-local-2026-change-me`。
3. **上传文件防护**：已限制扩展名、真实文件类型（filetype）、大小、题目数量，并对所有动态内容使用 `textContent` 渲染，避免 XSS；仍建议在网关层限制上传频率。
4. **法规内容免责声明**：题库与知识库依据公开驾考资料整理，具体处罚金额、记分标准以当地交管部门最新规定为准；产品内已展示免责声明。
5. **删除敏感数据**：定期清理 `backend/.data` 中过期题库与结果；不要把 `.env` 提交到代码仓库（已在 `.gitignore` 中忽略）。
