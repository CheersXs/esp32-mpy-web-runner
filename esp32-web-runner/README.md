# ESP32 Web Runner

在 ESP32-S3 (N16R8) 上运行的 **网页版编程 / 程序管理** 系统：
整页前端存在板子 flash 上，浏览器访问即得到一个 **Web IDE** —— 可以新建、编辑、保存、启动、停止、
删除、重命名多个 MicroPython 程序，并实时看到它们运行时的 print 输出。

## 功能

- 📁 **程序管理**：列表、新建、删除、重命名、复制、下载、导入（网页里直接传文件）
- ⌨️ **网页编程**：CodeMirror 编辑器（Python 语法高亮 / 自动缩进 / 括号配对 / 自动补全），Ctrl+S 保存
- ▶️ **开关程序**：异步程序可随时停止；同步脚本在线程里跑，互不阻塞网页
- 📟 **实时控制台**：WebSocket 把程序 print 输出实时推送到网页
- 🌐 **网络**：AP+STA 双模式（有路由器连路由器，没有就自建热点 `ESP32-S3`，访问 `192.168.4.1`）
- ⚙️ **设置**：网页里配置 WiFi / 热点 / 可选访问密码 / 开机自启动
- 🛡 **看门狗**：程序把系统锁死时自动重启恢复

## 文件结构

```
esp32-web-runner/
├── boot.py                # 开机初始化（加载路径）
├── main.py                # 启动服务器 + 调度器 + 看门狗
├── lib/
│   ├── config.py          # WiFi/热点/密码/自启动 配置存取
│   ├── console.py         # 全局控制台（接管 print 输出）
│   ├── net.py             # AP+STA 网络
│   ├── runner.py          # 程序管理器（异步任务 + 线程同步脚本）
│   ├── uvm.py             # 用户程序内 import 的辅助库
│   ├── web.py             # microdot 路由 / REST API / WebSocket
│   └── microdot/          # 第三方零依赖 web 框架（已内置，无需联网安装）
├── www/                   # 网页前端（存 flash）
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   └── cm/                # CodeMirror 编辑器
├── programs/examples/     # 示例程序（上传后变成板上可操作的"程序"）
└── tools/
    ├── upload.py          # 一键上传到板子
    └── smoke_test.py      # PC 端冒烟测试（无需板子）
```

## 安装 / 上传

1. 安装上传工具（只需一次）：

   ```
   pip install mpremote
   ```

2. 用 USB 线把 ESP32-S3 接到电脑，然后在项目目录执行：

   ```
   python tools/upload.py            # 自动找串口
   python tools/upload.py --port COM7   # 或指定串口
   ```

   脚本会建立目录、上传所有文件、把根目录旧的 `led.py` 挪进 `programs/`（这样它
   也变成网页里可管理的程序），然后软复位板子。

   > 不想动 `led.py` 的话：`python tools/upload.py --no-examples`

3. 上电后，打开浏览器：

   - 板子开了热点 `ESP32-S3`：连上后访问 `http://192.168.4.1`
   - 连上家里路由器：`http://<板子IP>`（在网页控制台/串口能看到）

   打不开就先看串口（Thonny/`mpremote repl`），里面有启动日志。

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
| 改完 WiFi 后连不上 | 网页设置保存即生效；改错 SSID 会重连失败，仍可用热点入口修复 |
| 想彻底恢复 | `esptool --port COMx erase_flash`，重新烧录 MicroPython 再上传 |

## 限制说明

- 浏览器必须与板子在同一局域网（或连它的热点）。
- 程序运行在同一个 Python 解释器里：**阻塞型死循环**（无任何 `await`/`sleep`）会拖垮整个
  系统，看门狗会重启兜底——所以长任务请写成异步或至少带上 `uvm.sleep_ms`。
- 控制台是共享日志流（所有程序 + 系统日志混在一起），未按程序分组。

## 开发 / 测试

不插板子也能验证核心逻辑：

```
python tools/smoke_test.py     # PC 上跑 REST API + 调度器全流程，全部通过
```