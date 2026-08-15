# ESP32 MPY Web Runner v2.0.0

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**ESP32 MPY Web Runner** 是一个运行在 ESP32 上的轻量级 Web IDE，让你通过浏览器编写、运行、管理
多个 MicroPython 程序，无需安装任何 PC 软件，插电即用。

支持 **ESP32-S3** 与 **ESP32-C3** 双目标，共享同一套 `lib/`、`www/`、`programs/` 代码，
通过 `targets/` 目录做板级差异化。

## 支持的目标板

| 目标 | 芯片 | 网络模式 | 屏幕 | 说明 |
|---|---|---|---|---|
| `esp32s3` | ESP32-S3 (N16R8) | AP + STA 双模式 | 无 | 完整功能，可自建热点 |
| `esp32c3` | ESP32-C3 | 纯 STA（无 AP） | OLED (SSD1306) | 省内存，OLED 显示 IP/内存/状态 |

> **C3 与 S3 的差异**：C3 不发射 AP 热点，只以 STA 模式连接家里路由器，通过路由器被访问。
> 这样省去了 AP + DHCP 服务器的底层内存开销，让 400KB SRAM 的 C3 也能稳定运行完整 Web IDE。
> 同时 C3 通过 OLED 屏幕实时显示 IP 地址，方便通过浏览器访问。

> ESP32-C3 适配的技术原理与内存约束说明，详见 [docs/C3_PORTING_GUIDE.md](docs/C3_PORTING_GUIDE.md)。
> （C3 无 PSRAM 的内存架构差异、GC split-heap 根因与模块加载顺序要求）。

## 功能

- 📁 **程序管理**：列表、新建、删除、重命名、复制、下载、导入（网页里直接传文件）
- ⌨️ **网页编程**：CodeMirror 编辑器（Python 语法高亮 / 自动缩进 / 括号配对 / 自动补全），Ctrl+S 保存
- ▶️ **开关程序**：异步程序可随时停止；同步脚本在线程里跑，互不阻塞网页
- 📟 **实时控制台**：WebSocket 把程序 print 输出实时推送到网页
- 🌐 **网络**：
  - S3：AP+STA 双模式（有路由器连路由器，没有就自建热点 `ESP32-S3`，访问 `192.168.4.1`）
  - C3：纯 STA 模式，通过路由器访问，OLED 显示 IP
- ⚙️ **设置**：网页里配置 WiFi / 热点 / 可选访问密码 / 开机自启动
- 🛡 **看门狗**：程序把系统锁死时自动重启恢复
- 🧠 **芯片自适应**：运行时自动检测芯片型号，S3 保持高性能（500 行日志 / 2000 队列），C3 自动降级（150 行 / 300 队列）省内存

## 文件结构

```
├── lib/                        # 共享库（S3/C3 通用，只维护一份）
│   ├── config.py               # 配置 + 芯片检测 + 动态资源参数
│   ├── console.py              # 全局控制台（接管 print 输出）
│   ├── net.py                  # 网络（AP+STA，按 ap.enabled 决定是否开 AP）
│   ├── runner.py               # 程序管理器（异步任务 + 线程同步脚本）
│   ├── uvm.py                  # 用户程序内 import 的辅助库
│   ├── web.py                  # microdot 路由 / REST API / WebSocket
│   ├── ssd1306.py              # OLED 驱动（C3 用）
│   └── microdot/               # 第三方零依赖 web 框架
├── www/                        # 网页前端（存 flash，S3/C3 通用）
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   └── cm/                     # CodeMirror 编辑器
├── programs/
│   └── examples/               # 共享示例程序
├── targets/                    # 板级差异化
│   ├── esp32s3/                # ESP32-S3 目标
│   │   ├── main.py
│   │   └── boot.py
│   └── esp32c3/                # ESP32-C3 目标
│       ├── main.py             # 完整 Web IDE + 纯 STA + OLED 状态屏
│       ├── boot.py
│       ├── c3_config.py        # C3 配置（WiFi / OLED 引脚 / 端口）
│       └── examples/
│           └── oled_loop.py    # C3 专属 OLED 示例
└── tools/
    ├── upload.py               # 一键上传（--target 选择目标板）
    └── smoke_test.py           # PC 端冒烟测试（无需板子）
```

## 安装 / 上传

### 1. 安装上传工具（只需一次）

```
pip install mpremote
```

### 2. 烧录固件（如果板子还没装 MicroPython）

仓库根目录的固件文件：

- `ESP32_GENERIC_S3-SPIRAM_OCT-20260406-v1.28.0.bin` — ESP32-S3 Octal-SPIRAM (N16R8)
- `ESP32_GENERIC_C3-20260406-v1.28.0.bin` — ESP32-C3

用 esptool 烧入对应固件。

### 3. 配置并上传

**ESP32-S3**（默认目标）：

```
python tools/upload.py --target esp32s3
```

**ESP32-C3**：

先编辑 `targets/esp32c3/c3_config.py` 填入你的 WiFi 和 OLED 引脚：

```python
WIFI_SSID = "你的WiFi名"
WIFI_PASS = "你的WiFi密码"

# OLED 0.42" SSD1306 72x40
OLED_WIDTH = 72
OLED_HEIGHT = 40
OLED_SCL = 6
OLED_SDA = 5
OLED_ADDR = 0x3C

SERVER_PORT = 80
```

然后上传：

```
python tools/upload.py --target esp32c3
```

> 上传脚本会自动：
> - 上传共享的 `lib/`、`www/`、`programs/` 到板子
> - 按目标裁剪 microdot（C3 不传 cors/test_client，省 flash）
> - 上传对应 `targets/<目标>/` 下的 `main.py` / `boot.py`
> - 预置 `config.json`（C3 自动写入 `ap.enabled=false` 并预填 WiFi）
> - C3 额外上传 `c3_config.py` 和专属示例程序

### 4. 访问

- **S3**：上电后，连热点 `ESP32-S3` 访问 `http://192.168.4.1`，或连家里路由器后访问 `http://<板子IP>`
- **C3**：连上路由器后，OLED 屏幕会显示 IP 地址，浏览器访问 `http://<C3-IP>`

## C3 的 OLED 屏幕

C3 的 OLED 实时显示：

```
连接中：                       连接成功：
┌──────────┐                 ┌──────────┐
│Connecting│                 │IP 192.16 │
│你的WiFi名 │                 │8.1.23    │
│Mem 156K  │                 │Mem 156K  │
│          │                 │WiFi名 On │
└──────────┘                 └──────────┘
```

- **连接中**：显示 `Connecting` + WiFi 名 + 内存
- **连接成功**：显示 `IP`（分两行）+ 内存 + `WiFi名 On`

## 怎么用

- **新建**：点"＋ 新建"，选异步或同步模板，起个名。
- **编程**：左侧点程序名，右侧编辑。`Ctrl+S` 保存；"保存＋重启"会自动重启该程序。
- **类型怎么定**：
  - 第一行注释 `#type:async` / `#type:sync` 可强制指定类型；
  - 否则代码里含 `async def main` 自动视为异步，其余按同步处理。
  - 异步程序 = asyncio 任务，网页点"停止"能立刻停。
  - 同步脚本 = 独立线程跑，网页点"停止"是协作式信号（脚本循环里读 `uvm.should_stop()`）。
    顽固死循环没法硬杀，靠看门狗；同步程序并发最多 2 个。
- **程序里能 import 什么**：`uvm`（辅助库）。长循环见
  ```
  import uvm
  async def main():                # 异步程序入口
      while not uvm.should_stop():
          ... 
          await uvm.sleep_ms(500)
  ```
  同步脚本直接从上到下执行，`uvm.sleep_ms(500)` 阻塞延时即可。

## 常见问题

| 现象 | 处理 |
|---|---|
| 上传慢 | CodeMirror 文件较大（约 170KB），首次上传要半分钟左右，属正常 |
| 首页白屏 | 先开 WebSocket 日志观察；确保上传完整后按 EN 重启 |
|上传完没反应| 尝试重启板子或者彻底断电后重启然后等待一会
| 改完 WiFi 后连不上 | 网页设置保存即生效；改错 SSID 会重连失败，S3 仍可用热点入口修复，C3 需重新上传配置 |
| C3 连不上 WiFi | 检查 `c3_config.py` 的 SSID/密码，重新上传；确认路由器是 2.4GHz |
| 想彻底恢复 | `esptool --port COMx erase_flash`，重新烧录 MicroPython 再上传 |


## 限制说明

- 浏览器必须与板子在同一局域网（或连它的热点）。
- 程序运行在同一个 Python 解释器里：**阻塞型死循环**（无任何 `await`/`sleep`）会拖垮整个
  系统，看门狗会重启兜底——所以长任务请写成异步或至少带上 `uvm.sleep_ms`。
- 控制台是共享日志流（所有程序 + 系统日志混在一起），未按程序分组。
- **C3 内存提示**：C3 只有 400KB SRAM，建议程序源码 < 10KB，多写异步程序（`async def main`）。

## 开发 / 测试

不插板子也能验证核心逻辑：

```
python tools/smoke_test.py     # PC 上跑 REST API + 调度器全流程，全部通过
```

## 贡献

欢迎提交 Issue 和 Pull Request。如果你发现 Bug 或有新功能建议，请先在 Issue 中描述清楚复现步骤或使用场景。也欢迎 Star / Fork 支持本项目。

## 许可证

本项目采用 [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0) 开源协议。