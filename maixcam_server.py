"""
MaixCam Server — HTTP 视频流服务 + 内置录屏上位机

部署到 MaixCam。启动后浏览器访问 http://<ip>:8000 即可观看 + 录制。

用法:
    python maixcam_server.py
"""

from maix import camera, time, app, http, image

# ── 配置 ──
PORT = 8000
WIDTH = 640
HEIGHT = 480

# ── 内嵌上位机页面（同源，支持 Canvas 录屏）───────────────

HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MaixCam 上位机</title>
<style>
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    :root{
        --bg:#0d0d12;--surface:#14141c;--border:#2a2a36;
        --accent:#00c8ff;--text:#dcdce0;--dim:#8888a0;
        --green:#3deb6b;--red:#ff4444;
    }
    body{
        background:var(--bg);color:var(--text);
        font-family:'Segoe UI',system-ui,-apple-system,sans-serif;
        display:flex;flex-direction:column;
        align-items:center;justify-content:center;
        min-height:100vh;
        user-select:none;-webkit-user-select:none;
    }
    .container{
        display:flex;flex-direction:column;align-items:center;
        width:100%;max-width:900px;padding:0 16px;
    }
    .header{
        padding:14px 4px;display:flex;align-items:center;gap:14px;
        width:100%;justify-content:space-between;
    }
    .title{font-size:17px;font-weight:600;color:var(--accent);letter-spacing:.4px;}
    .status{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--dim);}
    .dot{width:9px;height:9px;border-radius:50%;background:var(--red);transition:background .3s;}
    .dot.live{background:var(--green);animation:pulse 2.5s infinite;}
    @keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(61,235,107,.45)}50%{box-shadow:0 0 0 10px rgba(61,235,107,0)}}

    .recbar{
        width:100%;display:flex;align-items:center;gap:10px;
        padding:6px 0;font-size:12px;color:var(--dim);
    }
    .recbar .rec-dot{width:10px;height:10px;border-radius:50%;background:var(--dim);}
    .recbar .rec-dot.active{background:var(--red);animation:recPulse 1s infinite;}
    @keyframes recPulse{0%,100%{opacity:1}50%{opacity:.3}}
    .recbar button{
        background:var(--surface);border:1px solid var(--border);
        border-radius:5px;padding:6px 14px;color:var(--text);
        font-size:12px;cursor:pointer;transition:border-color .2s;
    }
    .recbar button:hover{border-color:var(--accent);}
    .recbar button.rec-start{border-color:var(--red);color:var(--red);}
    .recbar button.rec-start:hover{background:var(--red);color:#fff;}
    .recbar button.rec-stop{border-color:#ff8c3a;color:#ff8c3a;}
    .recbar button.rec-stop:hover{background:#ff8c3a;color:#000;}

    .info{display:flex;gap:16px;font-size:12px;color:var(--dim);padding:4px 0;width:100%;}
    .info span{color:var(--text);font-weight:500;}

    .viewer{
        position:relative;width:100%;
        background:var(--surface);border:1px solid var(--border);
        border-radius:10px;overflow:hidden;
        box-shadow:0 8px 32px rgba(0,0,0,.5);
        aspect-ratio:""" + str(WIDTH) + "/" + str(HEIGHT) + """";
    }
    .viewer img{display:block;width:100%;height:100%;object-fit:contain;}
    .viewer canvas{position:absolute;top:0;left:0;width:100%;height:100%;object-fit:contain;display:none;}

    .hint{padding:10px;font-size:12px;color:#555;text-align:center;letter-spacing:.3px;}
    .hint span{color:var(--accent);}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <span class="title">⬤ MaixCam 上位机</span>
        <div class="status">
            <div class="dot" id="dot"></div>
            <span id="statusText">等待推流…</span>
        </div>
    </div>

    <div class="recbar">
        <div class="rec-dot" id="recDot"></div>
        <span id="recLabel">未录制</span>
        <span id="recDur" style="display:none">00:00</span>
        <span style="flex:1"></span>
        <button class="rec-start" id="btnRecStart">● 开始录制</button>
        <button class="rec-stop" id="btnRecStop" style="display:none">■ 停止录制</button>
    </div>

    <div class="info">
        <div>分辨率: <span>""" + str(WIDTH) + "x" + str(HEIGHT) + """</span></div>
        <div>录制格式: <span>WebM</span></div>
    </div>

    <div class="viewer" id="viewer">
        <img id="stream" alt="MJPEG Stream"
             onload="onFrame()" onerror="onErr()">
        <canvas id="canvas"></canvas>
    </div>
    <div class="hint">双击画面 <span>切换全屏</span> · 点击 <span>开始录制</span> 录屏</div>
</div>
<script>
    const img     = document.getElementById('stream');
    const canvas  = document.getElementById('canvas');
    const ctx     = canvas.getContext('2d');
    const dot     = document.getElementById('dot');
    const st      = document.getElementById('statusText');
    const viewer  = document.getElementById('viewer');
    const recDot  = document.getElementById('recDot');
    const recLabel= document.getElementById('recLabel');
    const recDur  = document.getElementById('recDur');
    const btnStart= document.getElementById('btnRecStart');
    const btnStop = document.getElementById('btnRecStop');

    //页面加载完后再连流，避免浏览器加载圈不停
    window.addEventListener('load', function() {
        setTimeout(function() { img.src = '/stream'; }, 100);
    });

    // ── 录制状态 ──
    let recording = false;
    let recorder = null;
    let recStream = null;
    let recChunks = [];
    let recStartTime = null;
    let drawLoop = null;

    function updateRecUI() {
        if (recording) {
            recDot.classList.add('active');
            recLabel.textContent = '录制中';
            recDur.style.display = '';
            btnStart.style.display = 'none';
            btnStop.style.display = '';
        } else {
            recDot.classList.remove('active');
            recLabel.textContent = '未录制';
            recDur.style.display = 'none';
            btnStart.style.display = '';
            btnStop.style.display = 'none';
        }
    }

    // ── 开始录制 ──
    btnStart.addEventListener('click', function() {
        if (recording) return;

        canvas.width = img.naturalWidth || """ + str(WIDTH) + """;
        canvas.height = img.naturalHeight || """ + str(HEIGHT) + """;
        canvas.style.display = 'block';
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        lastFrameTime = Date.now();  // 录制期间用 drawLoop 维持心跳

        drawLoop = setInterval(function() {
            if (img.complete && img.naturalWidth > 0) {
                ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                lastFrameTime = Date.now();  // 每帧都更新，绝不断流误判
            }
        }, 33);

        recStream = canvas.captureStream(30);
        var mime = 'video/webm; codecs=vp8';
        if (!MediaRecorder.isTypeSupported(mime)) mime = 'video/webm';
        recorder = new MediaRecorder(recStream, { mimeType: mime, videoBitsPerSecond: 2500000 });
        recChunks = [];

        recorder.ondataavailable = function(e) {
            if (e.data && e.data.size > 0) recChunks.push(e.data);
        };
        recorder.onstop = function() {
            var blob = new Blob(recChunks, { type: mime });
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            var ts = new Date().toISOString().replace(/[:.]/g,'-').slice(0,19);
            a.href = url; a.download = 'record_' + ts + '.webm';
            document.body.appendChild(a); a.click(); document.body.removeChild(a);
            URL.revokeObjectURL(url);
        };

        recorder.start(1000);
        recording = true;
        recStartTime = Date.now();
        updateRecUI();
    });

    // ── 停止录制 ──
    btnStop.addEventListener('click', function() {
        if (!recording) return;
        recording = false;
        if (drawLoop) { clearInterval(drawLoop); drawLoop = null; }
        if (recorder && recorder.state === 'recording') recorder.stop();
        if (recStream) {
            recStream.getTracks().forEach(function(t) { t.stop(); });
            recStream = null;
        }
        canvas.style.display = 'none';
        // 录制期间 img 一直在加载帧，onFrame 持续触发，状态无需改动
        updateRecUI();
    });

    // 录制计时
    setInterval(function() {
        if (!recording || !recStartTime) return;
        var s = Math.floor((Date.now() - recStartTime) / 1000);
        var m = Math.floor(s / 60); s = s % 60;
        recDur.textContent = (m < 10 ? '0' + m : m) + ':' + (s < 10 ? '0' + s : s);
    }, 500);

    // ── 流状态追踪（基于帧时间戳，不靠 flag 切换）──
    let lastFrameTime = 0;
    let retryTimer = null;

    function onFrame() {
        lastFrameTime = Date.now();
        if (!dot.classList.contains('live')) {
            dot.className = 'dot live';
            st.textContent = '推流中';
        }
    }

    function onErr() {
        dot.className = 'dot';
        st.textContent = '等待推流…';
        scheduleRetry();
    }

    function scheduleRetry() {
        if (retryTimer) return;
        retryTimer = setTimeout(function() {
            retryTimer = null;
            img.src = '/stream?' + Date.now();
        }, 2000);
    }

    // 断流检测：超过 10 秒没有新帧/绘制则判定为断流
    setInterval(function() {
        if (lastFrameTime > 0 && Date.now() - lastFrameTime > 10000) {
            if (dot.classList.contains('live')) {
                dot.className = 'dot';
                st.textContent = '重新连接…';
                scheduleRetry();
            }
        }
    }, 2000);

    // 双击全屏
    viewer.addEventListener('dblclick', function() {
        if (document.fullscreenElement) document.exitFullscreen();
        else if (viewer.requestFullscreen) viewer.requestFullscreen();
    });
</script>
</body>
</html>"""

# ── 启动服务 ──

cam = camera.Camera(WIDTH, HEIGHT, image.Format.FMT_YVU420SP)

stream = http.JpegStreamer(port=PORT)
stream.set_html(HTML)
stream.start()

print(f"\nMaixCam Server 已启动")
print(f"  上位机:  http://{stream.host()}:{stream.port()}")
print(f"  视频流:  http://{stream.host()}:{stream.port()}/stream")
print(f"  包含录屏功能，浏览器打开即可使用\n")

while not app.need_exit():
    img = cam.read()
    stream.write(img.to_jpeg())
