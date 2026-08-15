# ESP32-C3 适配技术说明

> **文档状态说明**
> 
> 本文档记录的是 ESP32-C3 初步适配时遇到的核心问题与解决方案，作为技术快照留存。
> 部分结论（如 WDT 策略、探针和看门狗启用状态等）可能在后续版本中有所调整。
> 如需了解当前最新行为，请以 `targets/esp32c3/` 下的源码为准。
> 本文档只记录把本项目（原为 ESP32-S3 编写）移植到 ESP32-C3 的关键技术结论与修复方案。

## 背景（为什么）

- C3 无 PSRAM，只有 400KB 内部 SRAM；S3（N16R8）有 8MB PSRAM。
- C3 固件的内存架构与 S3 不同：MicroPython GC 堆默认 64KB、按需增长，大模块加载对内存的
  影响方式需要专门适配，不能直接照搬 S3 的加载方式。
- 直接复用 S3 完整代码后，症状：WiFi 显示已连接（OLED 正常、`isconnected()=True`），
  但网页打不开、ping 不通。

## 根因（原因）

**MicroPython C3 固件是 split-heap：GC 堆初始 64KB，导入大模块时的编译瞬态峰值会触发
split，直接从 ESP-IDF 堆抢占 64–100KB 连续内存，导致 WiFi 驱动 RX buffer（需连续 DMA
内存）分配失败 → 数据通路双向断流。**

机制链条：

1. 大模块（`web` → `microdot` 1412 行、`runner` 387 行）导入时的编译峰值（代码对象 +
   字典 + 字符串等临时对象）撑爆 64KB 初始堆。
2. GC 自动 split 新区域，每次 split 直接从 ESP-IDF 堆抢 **64–100KB 连续内存**。
3. ESP-IDF 堆被抢占后，WiFi 驱动的 **RX buffer 池分配失败**（需要连续 DMA 内存）。
4. 结果：驱动认为已关联（`status=1010`、`isconnected()=True`、DHCP 有 IP、TCP 握手 SYN
   能被 lwIP 层应答），但数据帧双向不再收发 —— "关联在、数据断"。

实测证据：在堆近满时初始化 WiFi 驱动直接报

```
E esp_netif_lwip: esp_netif_new_api: Failed to configure netif ...
E wifi: Expected to init 10 rx buffer, actual is 0
E wifi_init: Failed to deinit Wi-Fi driver (0x3001)
OSError: WiFi Out of Memory
```

## 瓶颈 / 阈值

判定指标：`micropython.mem_info(1)` 输出的 **GC 堆 total**。

| GC 堆 total | 数据通路 | 结论 |
|---|---|---|
| 64KB（无模块） | 正常 30/30 | 安全 |
| **128KB**（碎片 bytearray / 修复后全模块） | 正常 30/30 | **安全阈值** |
| **164KB**（全模块、坏顺序） | 断流 0-4/30 | **死亡阈值** |

- **阈值：GC 堆 ≤128KB 安全，≥164KB 完全断流**，之间是翻车窗口。
- 复现条件：全部应用模块导入后 GC total 顶到 164KB（触发了 100KB 大 split）。
- GC total 与**存活内存量无关**：纯内存水位（bytearray 模拟碎片）顶到 128KB 仍正常；
  是**最大模块导入时的编译瞬态峰值**把堆顶过线。
- split 大小由最大模块导入前的堆占用决定，阈值窗口极薄：
  - 预置占用 ≤4.5KB → `web` 导入只切 64KB split（128KB，活）
  - 预置占用 ≥8KB（如顶层多一个 `ssd1306`）→ 切 100KB split（164KB，死）

## 解决方案（怎么修）

### 1. 固定导入顺序 —— 最大模块最先

`web → runner → config → console`，让各模块编译峰值各自落在最新鲜的堆里，避免触发大 split。
**顺序不可乱**，改动后必须复测（重排序会立刻复发）。

### 2. 每个 import 后立即 `gc.collect()`

压降编译期瞬时峰值，防止前一个模块的编译垃圾累积进下一个模块的编译峰值。

### 3. `main.py` 拆分为"薄壳引导 + 应用模块"

`main.py` 只做三件事（保持极薄，~90 行）：

1. WiFi 驱动初始化 + 首次连接（**必须在任何重模块导入前**，驱动初始化需要连续内存 + 干净堆）
2. 按上面的顺序逐个导入 `web` / `runner` / `config` / `console`，每个之间 `gc.collect()`
3. `import c3_app; c3_app.run(STA)`

应用逻辑（OLED、数据探针、`_sta_task`、`_oled_task`、`create_app`、`asyncio.run`）全部移入
`targets/esp32c3/c3_app.py`，在 GC 堆已稳定（128KB）后才导入。

原因：

- **main.py 自身的代码对象也占预导入堆**：540 行代码约 7KB 常驻堆，把 `web` 导入前的
  预置占用从 4.5KB 顶到 12KB，把 split 从 64KB 顶成 100KB → 164KB 死态。
- 只有把逻辑移出 main.py、等堆稳定后再加载，才不挤占重模块的导入窗口。
- `ssd1306`（OLED 驱动）同样延迟到 `c3_app` 内部加载。

### 4. 其他 C3 必需适配

- **`STA.config(pm=0)` 关闭 modem-sleep**：C3 固件默认 `pm=1`，空闲约 15s 后把上行
  （板→AP）杀掉，下行正常但 TX 全丢 → 连上但入站永久等待。连接成功后立刻设置，
  重连后也要补设。
- **看门狗 WDT 在 C3 上移除**（S3 保留）：`machine.WDT` 与 mpremote 串口会话冲突
  （软重启/刷板时喂狗任务被杀 → 10s 后硬复位 → 重启循环，甚至中断上传写 flash）。
- **console 打补丁 `builtins.print` 而非 `os.dupterm`**：dupterm 是单流双向，接管后连
  REPL/mpremote 一起吞掉。
- **串口写永不阻塞**：headless（无主机读串口）时 USB-CDC FIFO 写满会堵死单线程主循环；
  需按字节预算截流 + 可写探测（`select`）跳过。

## 验证结果

- 修复后 boot 日志：GC 堆 total = **127936（128KB）**，`[web] listen :80` 正常。
- 长探针 **30/30**，同 boot 二次复测 26/30，新 boot 复测 30/30 —— 跨 boot 稳定。
- 完整页面（32KB）与 `/api/programs`、`/api/status`、`/api/config`、`/api/scan` 全部正常。
- 修复前：同一套代码 GC total 164KB，入站 0-4/30。
