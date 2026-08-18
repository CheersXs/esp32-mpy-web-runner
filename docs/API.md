# HTTP / WebSocket API 接口文档

本文档描述 ESP32 MPY Web Runner 的 REST API 与 WebSocket 协议（S3 / C3 一致）。
基础路径：`http://<板子IP>:80`（C3 见 OLED，S3 见网页控制台）。

## 通用约定

- **响应**：成功返回 JSON 对象；错误返回 `{"error": "说明"}` + 非 2xx 状态码
  （`400` 参数错 / `401` 未登录 / `403` 密码错 / `404` 不存在 / `413` 超限）。
- **鉴权**：`config.json` 的 `auth.enabled=false`（默认）时无需登录；开启后：
  - 普通 API：请求头 `X-Auth-Token: <token>`，或 Cookie `token=<token>`
    （登录接口 `Set-Cookie` 自动下发）。
  - WebSocket：URL 查询参数 `?token=<token>`。
  - token 有效期 7 天，登出即失效。
- **传输限制**：
  - 上传请求体（PUT/POST）上限 **1MB**（`web.py` 覆写 `Request.max_content_length`）。
    其中 **≤16KB** 的请求体读入内存（`request.body`）；**>16KB** 留在
    `request.stream` 由服务端流式写盘（内存安全）。
  - **C3 并发限制**：后端同时最多处理 **3 个请求**，超限直接关闭连接（客户端
    fetch 报网络错误），保护 C3 的 lwIP 缓冲；S3 不限。
  - 大响应（C3）：单次响应实测 ~9KB 才稳定，大文件一律分片（见文件读取/保存）。

## 鉴权

| 方法 | 路径 | 请求体 | 响应 |
|---|---|---|---|
| POST | `/api/login` | `{"password": "..."}` | `{"ok":true,"token":"..."}`（`auth.enabled=false` 时返回空 token） |
| POST | `/api/logout` | — | `{"ok":true}`（同时清 Cookie） |

## 程序管理（程序 = `/programs/*.py`）

| 方法 | 路径 | 请求体 | 说明 |
|---|---|---|---|
| GET | `/api/programs` | — | 列表：`{"programs":[{"name","type","status","error"}]}`；`type`=`async`/`sync`，`status`=`stopped`/`running`/`error`/`finished` |
| POST | `/api/programs` | `{"name","code"?,"template"?}` | 新建；无 `code` 时按 `template`（`async`/`sync`）生成模板 |
| GET | `/api/programs/<name>` | — | `{"name","type","code"}` |
| PUT | `/api/programs/<name>` | `{"code"}` | 保存；返回 `{"ok":true,"type"}` |
| DELETE | `/api/programs/<name>` | — | 删除（运行中拒绝） |
| POST | `/api/programs/<name>/rename` | `{"name"}` | 重命名（运行中拒绝） |
| POST | `/api/programs/<name>/start` | — | 启动；返回 `{"ok","message","type"}` |
| POST | `/api/programs/<name>/stop` | — | 停止（同步脚本为协作式停止信号） |
| POST | `/api/programs/<name>/restart` | `{"code"}?` | 保存（可选）→ 停止 → 启动 |

- 程序名仅 `A-Za-z0-9_`。类型判定：首行 `#type:async` / `#type:sync` 强制指定，
  否则含 `async def main` 判为异步，其余按同步脚本在线程运行。

## 文件系统（文件管理器 / 远程更新）

所有路径为设备绝对路径（`/lib/web.py`、`/www/...`），统一归一化，
拒绝 `..` 逃逸根目录。**危险文件**（`/main.py` `/boot.py` `/c3_config.py`
`/config.json` 及 `/lib`、`/www` 下）删除/重命名需 `force=1`。

### 目录列表
```
GET /api/fs/list?path=/lib
→ {"path":"/lib","entries":[{"name","dir":bool,"size"}], "free":<字节>, "dangerous":bool}
```

### 读取（分片契约，前端大文件编辑按此循环）
```
GET /api/fs/read?path=/lib/big.py&offset=0&limit=8192
→ {
    "path","size",                 # 文件总大小
    "text",                        # 本次 UTF-8 文本（服务端回退到字符边界，不切破多字节）
    "offset",                      # 下一次续读的起始字节偏移（= 本次实际结束位置）
    "limit","done":bool            # done=true 表示已到文件末尾
  }
```
- 首片（`offset=0`）额外返回 `name` 与 `dangerous`。
- 单次 `limit` 上限 = `config.fs_edit_max()`（C3 256KB / S3 512KB）；超限返回 413，
  前端按 8KB/段循环读取拼接。
- 客户端逻辑：`offset` 始终取上一响应返回的 `offset`，直到 `done`。

### 下载
```
GET /api/fs/file?path=/lib/hello.py
→ 200, Content-Type: application/octet-stream, Content-Disposition: attachment
```

### 上传 / 分片保存（契约）
```
# 整文件（≤16KB 一次 PUT，body 读内存）
PUT /api/fs/file?path=/programs/x.py        body=<bytes>

# 大文件分片：严格顺序 PUT，每片追加到 .tmp，最后一片提交
PUT /api/fs/file?path=/programs/big.py&append=0&final=0   body=<首片 8KB>
PUT /api/fs/file?path=/programs/big.py&append=1&final=0   body=<中间片>
PUT /api/fs/file?path=/programs/big.py&append=1&final=1   body=<末片>  → 提交为正式文件
```
- `append=0` 首片开 `.tmp` 覆盖；`append=1` 追加；`final=1` 提交（临时文件 +
  rename 原子替换）。**只要带 `append` 参数就按分片路径处理**。
- 不传 `append` 且 body >16KB 时服务端自动从 `request.stream` 流式写盘（内存安全）。
- 成功返回 `{"ok":true,"path","dangerous"}`。

### 目录 / 重命名 / 删除
```
POST /api/fs/mkdir?path=/lib/newdir            → {"ok":true}
POST /api/fs/rename   body={"from","to","force"?}
POST /api/fs/delete?path=/xxx&force=1&recursive=1
```
- `delete` 目录需 `recursive=1`；危险文件需 `force=1`。

## 状态 / 配置 / 系统

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/status` | `{"programs":[...], "sys":{"mem_free","filesystem":{"total","free"},"net":{"ap_ip","sta_ip","sta_connected"},"version","app_version"}}` |
| GET | `/api/config` | `{"wifi":{"ssid"},"ap":{"enabled","ssid"},"auth":{"enabled"},"autostart":[...]}` |
| POST | `/api/config` | 同构子集；保存后自动重配网络 |
| POST | `/api/reboot` | 立即软复位（200ms 后 `machine.reset()`） |
| GET | `/api/scan` | WiFi 扫描：`{"networks":[{"ssid","rssi","auth"}]}` |

## WebSocket 实时控制台

`GET /ws?token=<token>`（鉴权关闭时可省 token）。帧为 JSON 文本。

**服务器 → 客户端**
| type | 字段 | 说明 |
|---|---|---|
| `console` | `line` | 控制台日志行（连接即回放历史） |
| `console` | `action:"cleared"` | 已清空控制台 |
| `pong` | — | 响应 ping |

**客户端 → 服务器**
| type | 字段 | 说明 |
|---|---|---|
| `ping` | — | 保活，服务器回 `pong` |
| `clear` | — | 清空控制台缓冲 |

## 页面 / 静态资源

- `GET /` → `index.html`；`GET /<path>` → 静态文件（`/www`、`/cm`）。
- **C3 内联页**：只服务 `/www/index.html`（单连接页面，`build_inline.py` 生成）。
- **CodeMirror 分片**：`/cm/cm-partK.js`（K=0..7）。服务端存在同名 `.gz` 即返回
  `Content-Encoding: gzip`（浏览器自动解压）；前端按序 fetch、片间 600ms 间隔、
  拼接后全局 `eval`。加载失败自动降级为 textarea（页面不崩）。
