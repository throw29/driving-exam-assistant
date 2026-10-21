# 后端模块 · 驾考宝典智能查询助手

FastAPI + uv 实现的 RESTful 后端，提供试卷生成、Markdown 下载、驾考知识问答、自定义题库上传解析与自动阅卷。

## 快速启动

```bash
cd backend
copy .env.example .env          # Linux/macOS: cp .env.example .env
uv sync
uv run serve
```

默认地址：<http://127.0.0.1:8000>　｜　Swagger：<http://127.0.0.1:8000/docs>

也可以使用：

```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## 目录结构

```text
backend/
├── pyproject.toml          # uv 项目、依赖、serve 脚本、pytest 配置
├── uv.lock                 # 依赖锁定
├── .python-version         # 3.13
├── .env.example            # 环境变量模板
├── scripts/                # start.ps1 / start.bat / start.sh
├── app/
│   ├── main.py             # FastAPI 入口、CORS、异常处理、路由挂载、启动预热
│   ├── config.py           # 配置（.env、API-KEY、TTL、上传限制、时区）
│   ├── security.py         # API-KEY 校验（Bearer / x-api-key、常量时间比较）
│   ├── models.py           # Pydantic 请求模型
│   ├── errors.py           # 业务异常
│   ├── responses.py        # 统一响应
│   ├── storage.py          # JSON 文件存储（原子写 + TTL）
│   ├── deps.py             # 存储实例
│   ├── routers/            # system / exams / chat / questions / grading
│   ├── services/           # 业务服务（组卷、Markdown、检索、解析、阅卷）
│   └── data/               # 内置题库、知识库、科目配置
└── tests/                  # pytest 测试（50 项）
```

## 环境变量

复制 `.env.example` 为 `.env` 后修改。最关键的是：

```dotenv
DT_API_KEY=sk-dtk-your-own-secret
DT_CORS_ORIGINS=*
```

完整配置说明见 [../docs/DEPLOY.md](../docs/DEPLOY.md#7-配置项说明)。

## 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/health` | 健康检查 |
| GET | `/api/v1/exams/meta` | 组卷元信息 |
| POST | `/api/v1/exams/generate` | 生成试卷 |
| GET | `/api/v1/exams/{id}` | 试卷详情 |
| GET | `/api/v1/exams/{id}/preview` | Markdown → HTML 预览 |
| GET | `/api/v1/exams/{id}/download` | MD 文件流（可下载空白卷） |
| GET | `/api/v1/chat/suggestions` | 知识分类/热门问题 |
| POST | `/api/v1/chat` | 知识问答 |
| POST | `/api/v1/questions/upload` | 上传题库解析 |
| POST | `/api/v1/grading/submit` | 提交阅卷 |
| GET | `/api/v1/grading/{id}` | 查询阅卷结果 |
| GET | `/api/v1/grading/{id}/wrong-answers/download` | 错题 MD |

完整入参 / 出参 / 错误码 / curl 示例见 [../docs/API.md](../docs/API.md)。

## 业务说明

### 题库与组卷

- `app/data/subjects.json` 定义科目、章节、支持题型、标准卷题量；
- `questions_subject1.json` / `questions_subject4.json` 为内置题库，启动时校验：
  - 题号唯一、章节属于科目、题型被科目支持、答案在选项内、解析非空；
- 组卷按科目 + 题型 + 章节筛选后随机抽题，按题型分节；
- 100 分平均分配到每题（保留两位小数，最后一题吸收误差）；
- 建议用时按科目标准卷题量等比缩放，最少 5 分钟；
- 试卷保存到 `.data/exams/`，默认 24 小时过期。

### Markdown

`markdown_service.py` 输出：

- 标题、试卷编号/生成时间/题量/总分/合格线/建议用时/覆盖章节；
- 按题型分节（一、单选题；二、判断题；三、多选题）；
- 每题：章节标签、题干、选项、标准答案、解析；
- 答案速查表；空白卷带答题卡；
- 使用 Python-Markdown 渲染 HTML 预览（`/preview`）。

### 知识问答

不依赖外部大模型，`chat_service.py` 本地检索：

1. NFKC / 去标点 / 同义词归一；
2. 关键词命中加权（按关键词长度）；
3. 标题、分类匹配；
4. 字符二元组 Jaccard / 覆盖率相似度（过滤泛词）；
5. 当前问题匹配不足时，拼接上一轮用户问题（上下文追问）；
6. 命中返回结构化知识点；非驾考拒答；驾考未收录提示；
7. 知识库位于 `app/data/knowledge_base.json`，可继续扩充。

### 上传解析

- 只接受 `.txt` / `.md` / `.markdown`；
- `filetype` 魔数校验，拒绝 PDF / 图片 / docx 伪装；
- 支持 UTF-8 / GBK；
- 解析题号、题型标记、选项、标准答案、解析、章节；
- 标准答案与解析只存服务端，上传响应不下发；
- 错误行返回行号与原因；重复题干自动跳过并警告；
- 题库保存到 `.data/papers/`，默认 24 小时过期。

### 自动阅卷

- 单选题 / 判断题答案完全一致才得分；
- 多选题全部选对才得分（与真实驾考一致）；
- 未作答 0 分；
- 满分 100，90 分合格，95 分以上“优秀”；
- 返回全部题目详情、错题详情、总分、正确率、用时；
- 结果保存到 `.data/results/`，默认 72 小时；
- 错题 MD 包含汇总表、选项标注、你的答案、正确答案、解析。

### 存储

`storage.py` 使用线程锁 + 临时文件 + `os.replace` 原子写，读取时校验 TTL，写入时惰性清理过期文件。无需数据库。

## 测试

```bash
uv run pytest
# 50 passed
```

测试会使用独立的临时 `DT_DATA_DIR` 与测试 key，不会污染开发数据。

## 安全

- 所有 `/api/v1` 路由强制 API-KEY；
- 常量时间比较；
- CORS 可配置；
- 上传类型、大小、题量限制；
- 全局异常不向前端泄露堆栈；
- 详见 [../docs/DEPLOY.md](../docs/DEPLOY.md#10-安全与合规提示)。
