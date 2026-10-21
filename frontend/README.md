# 前端模块 · 驾考宝典智能查询助手

原生 HTML + CSS + JavaScript 单页应用，**无任何框架、无构建步骤**。包含三个功能 Tab：试卷生成、智能问答、上传阅卷。

## 打开方式

### 方式一：直接打开（最简单）

双击 `index.html`，或浏览器访问：

```text
file:///E:/workspace/frontend/index.html
```

后端 CORS 默认允许全部来源，`file://` 也能正常请求 `http://127.0.0.1:8000`。

### 方式二：静态 HTTP 服务

在项目根目录执行：

```powershell
.\start-frontend.ps1
```

或：

```bash
cd backend
uv run python -m http.server 5500 --bind 127.0.0.1 --directory ../frontend
```

访问 <http://127.0.0.1:5500>。

> 前端不依赖 Node、不依赖打包工具，任意静态服务器均可。

## 配置

编辑 `js/config.js`：

```javascript
window.DKA.config = {
  API_BASE_URL: 'http://127.0.0.1:8000',
  API_KEY: 'sk-dtk-local-2026-change-me',
  REQUEST_TIMEOUT: 30000,
  UPLOAD_TIMEOUT: 60000,
  CHAT_STORAGE_KEY: 'dka.chat.history.v1',
  CHAT_MAX_STORED: 40,
  CHAT_HISTORY_SEND: 10,
  APP_VERSION: '0.1.0'
};
```

- `API_BASE_URL`：后端地址；Nginx 同源部署时可设为空字符串 `''`（请求 `/api/v1/...`）；
- `API_KEY`：必须与 `backend/.env` 的 `DT_API_KEY` 一致；
- 所有请求由 `api.js` 统一添加 `Authorization: Bearer {API_KEY}`；
- 修改后强制刷新页面（`Ctrl + F5`）。

## 文件职责

| 文件 | 作用 |
|---|---|
| `index.html` | 单页结构：顶栏、三个 Tab 面板、表单、聊天、上传、试卷、结果、Toast |
| `css/style.css` | 全站样式：设计变量、组件、桌面布局、响应式、打印样式 |
| `js/config.js` | 全局配置（API 地址、API-KEY、超时、存储 key） |
| `js/api.js` | 原生 `fetch` 封装、统一响应解析、错误类、带鉴权 Blob 下载、文件名解析 |
| `js/ui.js` | DOM 构建、Toast、按钮 loading、纯文本 Markdown 渲染、localStorage、ID |
| `js/app.js` | Tab 切换、URL hash、服务状态检测（每 60 秒）、模块初始化 |
| `js/exam.js` | 组卷表单联动、可用题量计算、生成、完整预览、MD 源码/下载 |
| `js/chat.js` | 聊天气泡、热门问题、多轮发送、结构化回答、历史持久化、清空 |
| `js/grading.js` | 上传/拖拽、解析报告、在线作答、进度、提交阅卷、错题与全部详情、错题下载 |

## 交互说明

### 试卷生成

- 科目切换时自动切换支持题型、章节与可选题量；
- 章节默认全选；类型/章节联动计算当前可用题量；
- 题量超过可用量时自动收缩并提示；
- 生成结果按题型分节，展示标准答案、解析、答案速查；
- 下载通过 `fetch` + `Blob`，因此请求头能携带 API-KEY。

### 智能问答

- 首次进入显示欢迎语、能力与热门问题；
- Enter 发送，Shift+Enter 换行，自动适配输入框高度；
- 发送历史只保留最近 10 条用于后端上下文；
- 回答按知识点结构化渲染（讲解、要点、记忆技巧、易错提醒、追问）；
- 历史保存在 `localStorage` 的 `dka.chat.history.v1`，刷新恢复；
- “清空历史”会二次确认并清理本地记录。

### 上传阅卷

- 支持点击/拖拽选择，客户端先校验扩展名与 2 MB 大小；
- 上传后显示解析错误/警告（含行号）；
- 单选/判断为 radio，多选为 checkbox；
- 提交前若存在未作答会二次确认；
- 结果页展示分数环、等级、正确率、用时、错题汇总、全部详情；
- 错题 MD 通过带鉴权请求下载。

## 安全

- 所有来自后端/上传题库/聊天内容的文本均通过 `textContent` 或 `createElement` 渲染，不使用动态 `innerHTML`，避免 XSS；
- 前端 API-KEY 是可见的，本工具定位为驾校内部使用；公网部署建议在网关层增加登录/SSO。

## 浏览器兼容

- Chrome / Edge 90+、Firefox 90+、Safari 15+；
- 使用 ES2017+ 语法、`fetch`、`AbortController`、CSS Grid、CSS 变量；
- 不支持 IE。

## 关联文档

- [接口文档](../docs/API.md)
- [部署与使用教程](../docs/DEPLOY.md)
- [功能自测说明](../docs/TEST.md)
