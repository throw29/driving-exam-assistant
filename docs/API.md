# 驾考宝典智能查询助手 · 接口文档

> 版本：v1.0.0　｜　接口前缀：`/api/v1`　｜　协议：HTTP / JSON　｜　字符集：UTF-8

## 1. 基础信息

| 项目 | 说明 |
|---|---|
| 默认后端地址 | `http://127.0.0.1:8000` |
| 业务接口前缀 | `/api/v1` |
| 数据格式 | 请求与响应均为 `application/json`（文件上传为 `multipart/form-data`，文件下载为 `text/markdown`） |
| 在线文档 | Swagger UI：`http://127.0.0.1:8000/docs`；ReDoc：`http://127.0.0.1:8000/redoc`；OpenAPI：`http://127.0.0.1:8000/openapi.json` |
| 字符集 | UTF-8；Markdown 下载带 UTF-8 Content-Disposition 中文文件名 |
| 时间 | 默认时区 `Asia/Shanghai`，格式 `YYYY-MM-DD HH:mm:ss` |

### 1.1 统一响应结构

除文件下载接口外，所有接口（成功与失败）均返回：

```json
{
  "code": 0,
  "msg": "success",
  "data": {}
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | `0` 表示成功；非 0 为业务错误码（见第 2 节） |
| `msg` | string | 可直接展示给用户的中文提示 |
| `data` | any | 业务数据；错误时可能为 `null` 或包含错误详情 |

> 文件下载接口成功时直接返回 Markdown **二进制文件流**，不包裹 JSON；失败时仍返回上述 JSON 错误结构。

### 1.2 API-KEY 鉴权（对齐 Claude Code 规则）

所有 `/api/v1` 业务接口**必须**携带 API-KEY，无免鉴权业务接口。

支持两种请求头（与 Claude Code / Anthropic 客户端一致，同时存在时以 `Authorization` 为准）：

```http
Authorization: Bearer sk-dtk-local-2026-change-me
```

```http
x-api-key: sk-dtk-local-2026-change-me
```

校验规则：

1. 与后端配置的全局 API-KEY **完全一致**（默认读取 `DT_API_KEY`，未设置时兼容读取 `ANTHROPIC_API_KEY`）；
2. 使用 `hmac.compare_digest` 常量时间比较，防止时序攻击；
3. 缺失、格式错误（非 Bearer）或不匹配均返回 **HTTP 401** 与标准 JSON；
4. 401 响应带 `WWW-Authenticate: Bearer realm="driving-exam-assistant"`；
5. 前端所有 `fetch` 请求统一携带 `Authorization: Bearer {API_KEY}`。

401 示例：

```json
{
  "code": 401,
  "msg": "缺少 API-KEY。请在请求头携带 Authorization: Bearer <API_KEY> 或 x-api-key: <API_KEY>。",
  "data": null
}
```

> Swagger UI 可在右上角 **Authorize** 中填入 API-KEY 后直接调试。

### 1.3 跨域 CORS

- 默认 `DT_CORS_ORIGINS=*`，允许全部来源，便于 `file://` 直接打开前端；
- 已允许方法：`GET`、`POST`、`OPTIONS`；
- 已允许请求头：`Authorization`、`X-API-Key`、`Content-Type`、`Accept`、`Origin`；
- 已暴露响应头：`Content-Disposition`、`Content-Type`、`Content-Length`，保证浏览器能读取下载文件名；
- 预检请求由 CORS 中间件直接处理，不需要 API-KEY；
- 生产环境建议改为具体域名，例如 `DT_CORS_ORIGINS=http://127.0.0.1:5500,https://exam.example.com`。

## 2. 错误码

| HTTP | code | 含义 | 典型场景 |
|---:|---:|---|---|
| 200 | 0 | 成功 | 正常返回 |
| 400 | 4001 | 业务参数不满足 | 题量超过题库可用数量、章节不存在、未选择题型 |
| 400 | 4002 | 题库解析失败 | 没有有效题目、题目数超过上限 |
| 400 | 4003 | 科目不支持所选题型 | 科目一选择多选题 |
| 400 | 4004 | 文件为空 / 编码不可识别 | 上传空文件、二进制内容 |
| 400 | 4005 | 无效题目编号 | 提交阅卷时题目 ID 不属于该题库 |
| 401 | 401 | API-KEY 缺失或无效 | 未带请求头、key 错误 |
| 404 | 4040 | 试卷不存在或已过期 | 下载过期试卷 |
| 404 | 4041 | 题库不存在或已过期 | 提交阅卷时题库过期 |
| 404 | 4042 | 阅卷结果不存在或已过期 | 下载过期错题 |
| 404 | 404 | 接口不存在 | 地址错误 |
| 405 | 405 | 请求方法不允许 | GET 调用 POST 接口 |
| 413 | 4130 | 上传文件超过限制 | 文件大于 2 MB |
| 415 | 4150 | 文件类型不支持 | 上传 PDF / 图片伪装成 md |
| 422 | 422 | 请求参数校验失败 | 题量为 0、消息为空、答案 key 非 A-H |
| 500 | 500 | 服务器内部错误 | 未捕获异常（详情只写服务端日志） |

参数校验失败示例：

```json
{
  "code": 422,
  "msg": "请求参数校验失败：Input should be greater than or equal to 1",
  "data": {
    "errors": [
      {
        "field": "body.question_count",
        "message": "Input should be greater than or equal to 1",
        "type": "greater_than_equal"
      }
    ]
  }
}
```

## 3. 接口总览

| # | 方法 | 路径 | 功能 | 鉴权 |
|---|---|---|---|---|
| 1 | GET | `/api/v1/health` | 健康检查（同时验证 KEY） | 是 |
| 2 | GET | `/api/v1/exams/meta` | 科目 / 题型 / 章节 / 题库量元信息 | 是 |
| 3 | POST | `/api/v1/exams/generate` | 一键生成试卷 | 是 |
| 4 | GET | `/api/v1/exams/{exam_id}` | 查询已生成试卷详情 | 是 |
| 5 | GET | `/api/v1/exams/{exam_id}/preview` | Markdown + HTML 排版预览 | 是 |
| 6 | GET | `/api/v1/exams/{exam_id}/download` | 下载 Markdown 试卷文件流 | 是 |
| 7 | GET | `/api/v1/chat/suggestions` | 知识分类、热门问题、能力介绍 | 是 |
| 8 | POST | `/api/v1/chat` | 驾考知识问答（多轮上下文） | 是 |
| 9 | POST | `/api/v1/questions/upload` | 上传 txt / md 题库并解析 | 是 |
| 10 | POST | `/api/v1/grading/submit` | 提交作答并自动阅卷 | 是 |
| 11 | GET | `/api/v1/grading/{result_id}` | 查询阅卷结果 | 是 |
| 12 | GET | `/api/v1/grading/{result_id}/wrong-answers/download` | 下载错题集 Markdown | 是 |

---

## 4. 接口详情

### 4.1 健康检查

`GET /api/v1/health`

用于检查服务状态、验证 API-KEY、查看题库加载数量与临时存储统计。

**请求头**

```http
Authorization: Bearer sk-dtk-local-2026-change-me
```

**请求参数**：无

**成功响应**

```json
{
  "code": 0,
  "msg": "服务正常",
  "data": {
    "status": "ok",
    "name": "驾考宝典智能查询助手",
    "version": "1.0.0",
    "time": "2026-10-21 11:52:00",
    "timezone": "Asia/Shanghai",
    "auth": "verified",
    "key_tail": "e-me",
    "bank": {
      "subjects": 2,
      "questions": 92
    },
    "storage": {
      "exams": { "files": 1, "ttl_hours": 24.0 },
      "papers": { "files": 1, "ttl_hours": 24.0 },
      "results": { "files": 1, "ttl_hours": 72.0 }
    }
  }
}
```

**curl**

```bash
curl -s http://127.0.0.1:8000/api/v1/health \
  -H "Authorization: Bearer sk-dtk-local-2026-change-me"
```

---

### 4.2 获取组卷元信息

`GET /api/v1/exams/meta`

返回科目、各科目支持题型、章节及每章题量、总题量等，用于前端渲染筛选表单。

**成功响应（节选）**

```json
{
  "code": 0,
  "msg": "获取成功",
  "data": {
    "subjects": [
      {
        "key": "subject1",
        "name": "科目一",
        "full_name": "科目一 · 道路交通安全法律、法规和相关知识",
        "description": "道路交通安全法律、法规和规章，交通信号、标志、标线，安全行车与文明驾驶常识。",
        "duration_minutes": 45,
        "exam_question_count": 100,
        "pass_score": 90,
        "supported_types": [
          { "key": "single", "name": "单选题" },
          { "key": "judge", "name": "判断题" }
        ],
        "type_counts": { "single": 31, "judge": 21, "multiple": 0 },
        "total": 52,
        "chapters": [
          {
            "name": "交通法规与信号",
            "total": 12,
            "counts": { "single": 7, "judge": 5, "multiple": 0 }
          }
        ]
      },
      {
        "key": "subject4",
        "name": "科目四",
        "supported_types": [
          { "key": "single", "name": "单选题" },
          { "key": "judge", "name": "判断题" },
          { "key": "multiple", "name": "多选题" }
        ],
        "total": 40
      }
    ],
    "total_questions": 92,
    "question_types": [
      { "key": "single", "name": "单选题" },
      { "key": "judge", "name": "判断题" },
      { "key": "multiple", "name": "多选题" }
    ],
    "limits": {
      "max_question_count": 200,
      "max_upload_mb": 2,
      "max_upload_questions": 300
    },
    "pass_score": 90
  }
}
```

---

### 4.3 一键生成试卷

`POST /api/v1/exams/generate`

根据科目、题量、题型、章节从内置题库中随机抽题，按题型分节，满分 100 分，返回完整题目、答案、解析与 Markdown 文本。

**请求头**

```http
Authorization: Bearer sk-dtk-local-2026-change-me
Content-Type: application/json
```

**请求体**

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `subject` | string | 否 | `subject1` | `subject1` / `subject4`，兼容 `科目一` / `科目四` |
| `question_count` | int | 否 | `20` | 题目数量，1-200；不得超过当前筛选可用题量 |
| `question_types` | string[] | 否 | 科目全部支持题型 | `single` 单选、`judge` 判断、`multiple` 多选；也接受中文题型名 |
| `chapters` | string[] | 否 | 全部章节 | 章节名数组；空数组或 `["全部"]` 表示不限 |
| `shuffle` | bool | 否 | `true` | 是否随机打乱题目顺序 |

**请求示例**

```json
{
  "subject": "subject4",
  "question_count": 10,
  "question_types": ["single", "multiple"],
  "chapters": ["安全文明驾驶常识", "紧急情况处置"],
  "shuffle": true
}
```

**成功响应（节选，题目数组只展示 1 题）**

```json
{
  "code": 0,
  "msg": "试卷生成成功",
  "data": {
    "exam_id": "exam_20261021115256_ea8c44f3",
    "title": "科目四 · 驾考模拟试卷",
    "subject": {
      "key": "subject4",
      "name": "科目四",
      "full_name": "科目四 · 安全文明驾驶常识"
    },
    "created_at": "2026-10-21 11:52:56",
    "created_at_display": "2026-10-21 11:52:56",
    "expires_at_display": "2026-10-22 11:52:56",
    "duration_minutes": 6,
    "total_score": 100,
    "pass_score": 90,
    "question_count": 10,
    "type_counts": { "single": 7, "judge": 0, "multiple": 3 },
    "types": ["single", "multiple"],
    "chapters_filter": ["安全文明驾驶常识", "紧急情况处置"],
    "covered_chapters": ["安全文明驾驶常识", "紧急情况处置"],
    "scope_text": "题型：单选题、多选题；章节：安全文明驾驶常识、紧急情况处置",
    "rules": [
      "本试卷共 10 题，满分 100 分，90 分及以上为合格。",
      "单选题、判断题只有一个正确答案；多选题须全部选对才计分，少选、多选、错选均不得分。"
    ],
    "questions": [
      {
        "id": "s4-001",
        "number": 1,
        "type": "single",
        "type_name": "单选题",
        "chapter": "安全文明驾驶常识",
        "stem": "驾驶机动车行经人行横道时，下列哪些做法是正确的？",
        "options": [
          { "key": "A", "text": "提前减速慢行" },
          { "key": "B", "text": "遇行人正在通过时停车让行" }
        ],
        "answer": ["A"],
        "answer_text": "A",
        "explanation": "行经人行横道应提前减速，遇行人通过时停车让行。",
        "score": 10
      }
    ],
    "sections": [
      {
        "type": "single",
        "type_name": "单选题",
        "count": 7,
        "from": 1,
        "to": 7
      }
    ],
    "markdown": "# 科目四 · 驾考模拟试卷（含答案解析）\n\n> 试卷编号：exam_20261021115256_ea8c44f3 ...",
    "md_filename": "科目四_驾考模拟试卷_exam_20261021115256_ea8c44f3.md"
  }
}
```

> 说明：`questions[].answer` 返回标准答案 key 数组；`score` 之和恒为 100（最后一题吸收舍入误差）。

**错误示例：题库数量不足**

```json
{
  "code": 4001,
  "msg": "当前筛选条件下只有 12 道可用试题，无法生成 20 题试卷。请减少题量或放宽题型 / 章节筛选（当前范围：全部章节）。",
  "data": {
    "requested": 20,
    "available": 12,
    "available_by_type": { "single": 8, "judge": 4 },
    "chapters": [],
    "types": ["single", "judge"]
  }
}
```

**curl**

```bash
curl -s http://127.0.0.1:8000/api/v1/exams/generate \
  -H "Authorization: Bearer sk-dtk-local-2026-change-me" \
  -H "Content-Type: application/json" \
  -d '{"subject":"subject1","question_count":10,"question_types":["single","judge"],"chapters":[]}'
```

---

### 4.4 查询已生成试卷

`GET /api/v1/exams/{exam_id}`

返回生成时保存的完整试卷数据（不含 `markdown` 字段），用于刷新或二次展示。

| 路径参数 | 类型 | 说明 |
|---|---|---|
| `exam_id` | string | 生成接口返回的试卷编号 |

- 找不到或超过 TTL（默认 24 小时）：HTTP 404，`code=4040`。

---

### 4.5 Markdown 排版预览

`GET /api/v1/exams/{exam_id}/preview`

使用 Python-Markdown 将试卷 Markdown 渲染为 HTML，便于前端 iframe / 预览。

**成功响应（节选）**

```json
{
  "code": 0,
  "msg": "预览生成成功",
  "data": {
    "exam_id": "exam_20261021115256_ea8c44f3",
    "filename": "科目一_驾考模拟试卷_exam_20261021115256_ea8c44f3.md",
    "markdown": "# 科目一 · 驾考模拟试卷（含答案解析）...",
    "html": "<!doctype html><html lang=\"zh-CN\">...<article>...</article></html>",
    "bytes": 6116
  }
}
```

---

### 4.6 下载 Markdown 试卷（文件流）

`GET /api/v1/exams/{exam_id}/download`

浏览器直接下载 `.md` 文件。前端使用带鉴权的 `fetch` 获取 Blob 后触发下载，因此请求头仍必须携带 API-KEY。

**Query 参数**

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `include_answers` | bool | `true` | `false` 时下载空白卷（无答案与解析，附答题卡） |

**成功响应头**

```http
HTTP/1.1 200 OK
Content-Type: text/markdown; charset=utf-8
Content-Disposition: attachment; filename="dtk_exam_20261021115256_ea8c44f3.md"; filename*=UTF-8''%E7%A7%91%E7%9B%AE%E4%B8%80_...
Cache-Control: no-store
X-Content-Type-Options: nosniff
```

**Markdown 内容结构**

```markdown
# 科目一 · 驾考模拟试卷（含答案解析）

> 试卷编号：exam_...
> 生成时间：2026-10-21 11:52:56
> 题目数量：10 题　总分：100 分　合格线：90 分　建议用时：5 分钟
> 覆盖章节：交通法规与信号、...

## 试卷说明
- ...

## 一、单选题（共 7 题，每题 10 分）

### 第 1 题

> 章节：交通法规与信号

题干内容

- **A.** 选项一
- **B.** 选项二

**标准答案：** A

**解析：** ...

---

## 答案速查

| 题号 | 题型 | 章节 | 标准答案 |
|:--:|---|---|:--:|
| 1 | 单选题 | 交通法规与信号 | A |
```

**curl 下载**

```bash
curl -L http://127.0.0.1:8000/api/v1/exams/exam_xxx/download \
  -H "Authorization: Bearer sk-dtk-local-2026-change-me" \
  -o 驾考模拟试卷.md
```

**空白卷**

```bash
curl -L "http://127.0.0.1:8000/api/v1/exams/exam_xxx/download?include_answers=false" \
  -H "Authorization: Bearer sk-dtk-local-2026-change-me" \
  -o 驾考模拟试卷_空白卷.md
```

---

### 4.7 获取问答初始化信息

`GET /api/v1/chat/suggestions`

返回知识分类、热门问题、能力介绍和知识点总数，聊天页左侧栏使用。

**成功响应（节选）**

```json
{
  "code": 0,
  "msg": "获取成功",
  "data": {
    "version": "1.0.0",
    "categories": [
      { "key": "signals", "name": "交通信号与标志" },
      { "key": "rules", "name": "通行规则与让行" }
    ],
    "hot_questions": [
      "闯红灯扣几分？",
      "高速公路最低限速是多少？",
      "酒驾和醉驾有什么区别？"
    ],
    "capabilities": [
      "交通信号、标志标线的含义与记忆方法"
    ],
    "total_knowledge_points": 40
  }
}
```

---

### 4.8 驾考知识智能问答

`POST /api/v1/chat`

基于内置结构化知识库进行检索，返回讲解、要点、记忆技巧、易错提醒；支持传入历史对话实现多轮追问。仅回答驾考问题，未命中时明确提示。

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `message` | string | 是 | 用户提问，1-1000 字 |
| `history` | object[] | 否 | 历史消息，最多 30 条，格式 `{role, content}`；`role` 为 `user` / `assistant` |
| `session_id` | string | 否 | 会话标识，4-64 位字母、数字、下划线或短横线，原样回传 |

**请求示例**

```json
{
  "message": "那要罚多少钱",
  "history": [
    { "role": "user", "content": "闯红灯扣几分？" },
    { "role": "assistant", "content": "闯红灯一次记 6 分。" }
  ],
  "session_id": "chat_5f1c8e7a9b2d4c6e"
}
```

**命中知识点响应**

```json
{
  "code": 0,
  "msg": "回答成功",
  "data": {
    "matched": true,
    "intent": "knowledge",
    "session_id": "chat_5f1c8e7a9b2d4c6e",
    "question": "那要罚多少钱",
    "context_used": true,
    "matched_keywords": ["闯红灯", "红灯"],
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
    "related_topics": [
      { "id": "kb-yellow-light", "title": "黄灯通行规则" }
    ],
    "reply_markdown": "> 已结合上一轮对话理解你的问题。\n\n### 闯红灯的记分与处罚\n...",
    "suggestions": [
      "红灯时右转算闯红灯吗？",
      "黄灯亮时还能不能走？",
      "高速公路最低限速是多少？"
    ],
    "disclaimer": "回答内容仅供驾考学习参考，具体法规与处罚以当地交管部门最新规定为准。"
  }
}
```

**未命中 / 越界响应**

```json
{
  "code": 0,
  "msg": "回答成功",
  "data": {
    "matched": false,
    "intent": "out_of_scope",
    "session_id": "chat_xxx",
    "question": "今天天气怎么样？",
    "context_used": false,
    "matched_keywords": [],
    "topics": [],
    "related_topics": [],
    "suggestions": ["闯红灯扣几分？", "高速公路最低限速是多少？"],
    "disclaimer": "回答内容仅供驾考学习参考，具体法规与处罚以当地交管部门最新规定为准。",
    "reply_markdown": "抱歉，我是驾考知识助手，只能回答与驾考相关的问题……"
  }
}
```

`intent` 取值：`knowledge`（命中知识库）、`greeting`（问候）、`thanks`（感谢）、`help`（能力介绍）、`knowledge_miss`（驾考相关但知识库未收录）、`out_of_scope`（非驾考问题）。

**curl**

```bash
curl -s http://127.0.0.1:8000/api/v1/chat \
  -H "Authorization: Bearer sk-dtk-local-2026-change-me" \
  -H "Content-Type: application/json" \
  -d '{"message":"闯红灯扣几分？","history":[],"session_id":"chat_demo_001"}'
```

---

### 4.9 上传并解析自定义题库

`POST /api/v1/questions/upload`

`multipart/form-data` 上传 `.txt` / `.md`（最大 2 MB，最多 300 题）。服务端自动拆分题号、题干、选项、标准答案与解析，并做文件真实类型校验（`filetype`）。

**请求头**

```http
Authorization: Bearer sk-dtk-local-2026-change-me
Content-Type: multipart/form-data; boundary=...
```

**表单字段**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `file` | file | 是 | `.txt` / `.md` / `.markdown`，UTF-8 或 GBK 编码，最大 2 MB |

**支持的题库格式**

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
解析：已越过停止线的车辆可以继续通行。
```

- 题号：`1.` / `1、` / `第1题` / `（1）` / `### 第 1 题`
- 题型：`【单选】`、`【多选】`、`【判断】`、`（单选题）`、`题型：单选`，可省略由系统推断
- 选项：`A.` / `A、` / `- **A.**`；支持一行多个选项
- 答案：`答案：A`、`正确答案：A、C`、`【答案】B`、`答案：正确`
- 解析：`解析：...`、`【解析】...`
- 章节：Markdown 标题或 `第X章 ...`
- 判断题可省略选项，系统自动补全“正确 / 错误”

**成功响应（节选）**

```json
{
  "code": 0,
  "msg": "题库解析成功",
  "data": {
    "paper_id": "paper_20261021115259_ab12cd34",
    "filename": "sample_bank.md",
    "title": "科目一 自定义练习题库",
    "uploaded_at": "2026-10-21 11:52:59",
    "expires_at_display": "2026-10-22 11:52:59",
    "question_count": 10,
    "type_counts": { "single": 5, "judge": 3, "multiple": 2 },
    "chapters": ["交通法规与信号", "安全行车"],
    "total_score": 100,
    "pass_score": 90,
    "questions": [
      {
        "id": "q001",
        "number": 1,
        "source_number": 1,
        "type": "single",
        "type_name": "单选题",
        "chapter": "交通法规与信号",
        "stem": "机动车遇交通信号灯为红灯时，应当如何通行？",
        "options": [
          { "key": "A", "text": "在停止线以外停车等待" },
          { "key": "B", "text": "加速通过路口" }
        ],
        "has_explanation": true
      }
    ],
    "parse_report": {
      "errors": [],
      "warnings": [],
      "chapters": ["交通法规与信号", "安全行车"],
      "source_lines": 80
    }
  }
}
```

> **安全设计**：上传响应中的题目**不包含** `answer` 与 `explanation`，标准答案仅保存于服务端，提交阅卷后才返回，避免前端直接看到答案。

**解析失败示例**

```json
{
  "code": 4002,
  "msg": "未能从文件中解析出有效题目。请检查题库格式：每题需有题号、题干、至少两个选项（判断题除外）和标准答案。",
  "data": {
    "errors": [
      { "line": 3, "source_number": 1, "reason": "缺少标准答案（支持“答案：A”或“答案：正确”）" }
    ],
    "warnings": [],
    "format_example": "1. 【单选】机动车遇红灯时应当？\nA. 停车等待\n..."
  }
}
```

**curl**

```bash
curl -s http://127.0.0.1:8000/api/v1/questions/upload \
  -H "Authorization: Bearer sk-dtk-local-2026-change-me" \
  -F "file=@samples/sample_bank.md"
```

---

### 4.10 提交作答并自动阅卷

`POST /api/v1/grading/submit`

接收题库 `paper_id` 与每道题的选项答案，自动逐题判分，返回总分、正确率、及格结果、全部题目详情与错题详情。

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `paper_id` | string | 是 | 上传解析接口返回的题库 ID |
| `answers` | object[] | 是 | 每题作答，元素为 `{question_id, answer}`；未作答可不传或传空数组 |
| `answers[].question_id` | string | 是 | 题目 ID，如 `q001` |
| `answers[].answer` | string[] | 是 | 选项 key 数组，如 `["A"]`、`["A","C"]`；只能 A-H |
| `duration_seconds` | int | 否 | 作答耗时（秒），0-86400 |

**请求示例**

```json
{
  "paper_id": "paper_20261021115259_ab12cd34",
  "answers": [
    { "question_id": "q001", "answer": ["A"] },
    { "question_id": "q002", "answer": ["B"] },
    { "question_id": "q003", "answer": ["A", "B", "D"] }
  ],
  "duration_seconds": 305
}
```

**成功响应（节选）**

```json
{
  "code": 0,
  "msg": "阅卷完成",
  "data": {
    "result_id": "result_20261021115301_ef56ab78",
    "paper_id": "paper_20261021115259_ab12cd34",
    "paper_name": "科目一 自定义练习题库",
    "filename": "sample_bank.md",
    "submitted_at": "2026-10-21 11:53:01",
    "submitted_at_display": "2026-10-21 11:53:01",
    "score": 100,
    "full_score": 100,
    "accuracy": 100.0,
    "pass_score": 90,
    "passed": true,
    "grade": "优秀",
    "total_questions": 10,
    "answered_count": 10,
    "unanswered_count": 0,
    "correct_count": 10,
    "wrong_count": 0,
    "duration_seconds": 305,
    "duration_text": "5 分 5 秒",
    "type_counts": { "single": 5, "judge": 3, "multiple": 2 },
    "chapters": ["交通法规与信号", "安全行车"],
    "details": [
      {
        "id": "q001",
        "number": 1,
        "source_number": 1,
        "type": "single",
        "type_name": "单选题",
        "chapter": "交通法规与信号",
        "stem": "机动车遇交通信号灯为红灯时，应当如何通行？",
        "options": [
          { "key": "A", "text": "在停止线以外停车等待" }
        ],
        "user_answer": ["A"],
        "user_answer_text": "A（在停止线以外停车等待）",
        "correct_answer": ["A"],
        "correct_answer_text": "A（在停止线以外停车等待）",
        "is_correct": true,
        "explanation": "红灯亮时禁止车辆通行……",
        "score_awarded": 10,
        "score_total": 10
      }
    ],
    "wrong_questions": [],
    "disclaimer": "阅卷结果由系统按标准答案自动判定，仅供练习参考。"
  }
}
```

**判分规则**

- 满分 100，按题目数量平均分配（保留两位小数，最后一题吸收误差）；
- 单选 / 判断：选项完全一致才得分；
- 多选：必须全部选对才得分，少选、多选、错选均不得分；
- 未作答按 0 分处理；
- 90 分及以上为合格，95 分及以上评定为“优秀”。

**错误示例：无效题目编号**

```json
{
  "code": 4005,
  "msg": "提交的数据包含无效题目编号，请刷新页面后重新作答。",
  "data": { "invalid_question_ids": ["q999"] }
}
```

**curl**

```bash
curl -s http://127.0.0.1:8000/api/v1/grading/submit \
  -H "Authorization: Bearer sk-dtk-local-2026-change-me" \
  -H "Content-Type: application/json" \
  -d '{"paper_id":"paper_xxx","answers":[{"question_id":"q001","answer":["A"]}],"duration_seconds":120}'
```

---

### 4.11 查询阅卷结果

`GET /api/v1/grading/{result_id}`

返回与 4.10 相同的完整结果（含 `details` / `wrong_questions`）。

- 不存在或超过 TTL（默认 72 小时）：HTTP 404，`code=4042`。

---

### 4.12 下载错题集 Markdown

`GET /api/v1/grading/{result_id}/wrong-answers/download`

将与 4.10 对应阅卷结果的错题导出为 `.md` 文件流，包含错题汇总表、你的答案、正确答案、选项标注与解析。若全部答对，文件内容为“全部正确”的鼓励提示。

**成功响应头**

```http
HTTP/1.1 200 OK
Content-Type: text/markdown; charset=utf-8
Content-Disposition: attachment; filename="wrong_answers_result_xxx.md"; filename*=UTF-8''%E9%94%99%E9%A2%98%E9%9B%86_...
Cache-Control: no-store
```

**错题 Markdown 结构**

```markdown
# 错题集 · 科目一 自定义练习题库

> 阅卷编号：result_xxx
> 成绩：80 / 100 分　正确率：80%　正确 8 题 / 错误 2 题

## 错题汇总

| 错题序号 | 原题号 | 题型 | 章节 | 你的答案 | 正确答案 |
|:--:|:--:|---|---|:--:|:--:|
| 1 | 1 | 单选题 | 交通法规与信号 | B | A |

## 错题详解

### 错题 1（原题第 1 题 · 单选题）

> 章节：交通法规与信号

题干内容

- **A.** 在停止线以外停车等待（正确答案）
- **B.** 加速通过（你的选择）

**你的答案：** B

**正确答案：** A

**解析：** 红灯亮时禁止车辆通行……
```

**curl**

```bash
curl -L http://127.0.0.1:8000/api/v1/grading/result_xxx/wrong-answers/download \
  -H "Authorization: Bearer sk-dtk-local-2026-change-me" \
  -o 错题集.md
```

## 5. 数据生命周期

| 数据 | 存储位置 | 默认 TTL | 说明 |
|---|---|---|---|
| 生成试卷 | `backend/.data/exams/*.json` | 24 小时 | 支持下载、预览、详情查询 |
| 上传题库 | `backend/.data/papers/*.json` | 24 小时 | 标准答案仅存服务端 |
| 阅卷结果 | `backend/.data/results/*.json` | 72 小时 | 支持错题导出 |
| 聊天历史 | 浏览器 `localStorage` | 永久（用户可清空） | 不落服务端，后端仅用 `history` 理解上下文 |
| 内置题库 / 知识库 | `backend/app/data/*.json` | 随代码发布 | 只读 |

过期文件由服务端在写入时惰性清理；重启不会丢失未过期数据。生产环境可配置 `DT_EXAM_TTL_HOURS`、`DT_PAPER_TTL_HOURS`、`DT_RESULT_TTL_HOURS`。
