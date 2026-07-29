# MaixCam 无线图传

MaixCam 作为 HTTP 服务器推流，同一局域网下的电脑/手机浏览器即可无线观看 + 录制视频。

## 使用方法

### 1. 获取 MaixCam IP 地址

MaixCam 连接手机热点或 WiFi 后，在 MaixCam 终端查看 IP：

```python
import network
wlan = network.WLAN(network.STA_IF)
print(wlan.ifconfig()[0])   # 例如 192.168.1.100
```

### 2. 启动推流

将 `maixcam_server.py` 部署到 MaixCam 并运行：

```python
python maixcam_server.py
```

### 3. 浏览器打开

PC 用 Edge 或 Chrome 浏览器访问：

```
http://192.168.x.x:8000
```

打开即可看到实时画面，点击「开始录制」保存视频，停止后自动下载 WebM 文件。

## 录屏

内置 Canvas + MediaRecorder 录屏，同源无跨域问题。

- 录制格式：WebM（VP8）
- 支持多次录制
- 下载到浏览器默认下载目录
