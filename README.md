# MaixCam 无线图传上位机

MaixCam 作为 HTTP 服务器推流，同一局域网内的电脑/手机浏览器打开网页即可无线观看 + 录制视频。

## 架构

```
MaixCam (Server)                    浏览器
┌──────────────────────┐           ┌──────────────┐
│ maixcam_server.py    │  MJPEG    │ http://ip:8000│
│ 摄像头 → JPEG → 推流  │─────────►│ 实时画面 + 录屏 │
│ 内嵌 HTML 上位机页面   │           │ Canvas 录制    │
└──────────────────────┘           └──────────────┘
```

## 使用方法

### 1. MaixCam 连接网络

MaixCam 连接手机热点或无线路由器 WiFi，获取局域网 IP。

### 2. 部署脚本

将 `maixcam_server.py` 部署到 MaixCam：

```bash
# 通过 ADB 或 MaixPy IDE 上传脚本到 MaixCam
# 或直接在 MaixCam 的 MaixPy 中运行
```

### 3. 启动推流

```python
python maixcam_server.py
```

启动后会打印访问地址：

```
MaixCam Server 已启动
  上位机:  http://192.168.x.x:8000
  视频流:  http://192.168.x.x:8000/stream
```

### 4. 浏览器观看

- **方式 A（推荐）**：浏览器直接访问 `http://192.168.x.x:8000`
  - 内置上位机页面，支持实时观看 + Canvas 录屏
  - 录制格式：WebM（VP8）
  - 支持多次录制，停止后自动下载

- **方式 B**：PC 打开 `index.html`，地址栏输入 `http://192.168.x.x:8000/stream`
  - 独立上位机，支持地址切换

## 可选工具

| 文件 | 用途 |
|------|------|
| `maixcam_server.py` | 主文件，部署到 MaixCam |
| `index.html` | 独立上位机页面（PC 打开，可切换流地址） |
| `recorder.py` | 代理服务器，支持 FFmpeg 无损 MP4 录制 |
| `maixcam_client/stream_simulator.py` | 模拟推流（测试用） |

### recorder.py（无损录制）

```bash
# PC 启动代理，拉 MaixCam 流并转发
python recorder.py --source http://192.168.x.x:8000/stream

# 浏览器 index.html 预设选「PC 代理」，录制时 FFmpeg 无损转 MP4
```

## 录制对比

| | MaixCam 内置 | recorder 代理 |
|---|---|---|
| 格式 | WebM (VP8) | MP4 (MJPEG 无损) |
| 画质 | Canvas 重绘 | 原始帧，无二次编码 |
| 部署 | 仅 MaixCam | PC + FFmpeg |

## 硬件要求

- MaixCAM / MaixCAM Pro / MaixCAM2
- MaixPy v4+

## 测试

PC 无 MaixCam 时可用模拟器测试：

```bash
# 终端 1：启动模拟推流
python maixcam_client/stream_simulator.py --port 8000

# 终端 2：浏览器打开 index.html → 输入 http://localhost:8000/stream
```
