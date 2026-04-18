"""HTTP dashboard — stdlib-only (ThreadingHTTPServer + BaseHTTPRequestHandler).

Routes:
  GET  /                    dashboard HTML
  GET  /api/state           JSON robot state snapshot (no frame)
  GET  /api/diag            connection flags + motor intent breakdown
  GET  /api/logs?n=100      recent log lines from RingBufferHandler
  GET  /api/stream.mjpg     multipart JPEG stream of latest camera frame
  POST /api/mode            {"mode": "MANUAL"|"AUTO"|"WEB"}
  POST /api/drive           {"left": -255..255, "right": -255..255}  (WEB mode only)
  POST /api/estop           immediate motor stop, flips mode to MANUAL
  POST /api/recalibrate     re-sample floor for the autonomy navigator
"""

import json
import logging
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2

from walla.autonomy.navigator import Navigator
from walla.serial_bridge.bridge import SerialBridge
from walla.state import VALID_MODES, RobotState
from walla.web.logbuffer import RingBufferHandler

log = logging.getLogger(__name__)

DEFAULT_PORT = 8080
MJPEG_BOUNDARY = "wallaframe"
STREAM_INTERVAL = 1.0 / 15  # ~15 fps re-encode cap
JPEG_QUALITY = 70


class _Deps:
    """Bag of references shared between handler instances."""

    state: RobotState
    bridge: SerialBridge
    navigator: Navigator
    logbuf: RingBufferHandler


class _Handler(BaseHTTPRequestHandler):
    deps: _Deps  # set on the class before serving

    # BaseHTTPRequestHandler logs each request to stderr by default — noisy.
    def log_message(self, format, *args):
        log.debug("http %s - %s", self.address_string(), format % args)

    # ---------- helpers ----------

    def _send_json(self, obj, status: int = HTTPStatus.OK):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, text: str, status: int = HTTPStatus.OK, content_type="text/plain"):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise ValueError(f"bad JSON body: {e}") from e

    # ---------- dispatch ----------

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        try:
            if path == "/":
                return self._send_text(DASHBOARD_HTML, content_type="text/html; charset=utf-8")
            if path == "/api/state":
                return self._api_state()
            if path == "/api/diag":
                return self._api_diag()
            if path == "/api/logs":
                return self._api_logs()
            if path == "/api/stream.mjpg":
                return self._api_stream()
            self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
        except BrokenPipeError:
            pass
        except Exception:
            log.exception("GET %s failed", self.path)
            try:
                self._send_json({"error": "server_error"}, HTTPStatus.INTERNAL_SERVER_ERROR)
            except Exception:
                pass

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        try:
            if path == "/api/mode":
                return self._api_set_mode()
            if path == "/api/drive":
                return self._api_drive()
            if path == "/api/estop":
                return self._api_estop()
            if path == "/api/recalibrate":
                return self._api_recalibrate()
            self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
        except ValueError as e:
            self._send_json({"error": str(e)}, HTTPStatus.BAD_REQUEST)
        except BrokenPipeError:
            pass
        except Exception:
            log.exception("POST %s failed", self.path)
            try:
                self._send_json({"error": "server_error"}, HTTPStatus.INTERNAL_SERVER_ERROR)
            except Exception:
                pass

    # ---------- endpoints ----------

    def _api_state(self):
        snap = self.deps.state.snapshot()
        snap.pop("frame", None)
        self._send_json(snap)

    def _api_diag(self):
        snap = self.deps.state.snapshot()
        snap.pop("frame", None)
        self._send_json(
            {
                "connections": {
                    "arduino": snap["arduino_connected"],
                    "camera": snap["camera_active"],
                    "controller": snap["controller_connected"],
                },
                "mode": snap["mode"],
                "battery_voltage": snap["battery_voltage"],
                "bumps": {
                    "front_left": snap["bump_front_left"],
                    "front_right": snap["bump_front_right"],
                },
                "motors": {
                    "left": snap["motor_left"],
                    "right": snap["motor_right"],
                },
                "web_drive": {
                    "left": snap["web_drive_left"],
                    "right": snap["web_drive_right"],
                    "age_ms": int((time.monotonic() - snap["web_drive_timestamp"]) * 1000)
                    if snap["web_drive_timestamp"] > 0
                    else None,
                },
                "server_time": time.time(),
            }
        )

    def _api_logs(self):
        n = 100
        if "?" in self.path:
            query = self.path.split("?", 1)[1]
            for part in query.split("&"):
                if part.startswith("n="):
                    try:
                        n = max(1, min(500, int(part[2:])))
                    except ValueError:
                        pass
        self._send_json({"lines": self.deps.logbuf.tail(n)})

    def _api_set_mode(self):
        body = self._read_json()
        mode = body.get("mode")
        if mode not in VALID_MODES:
            raise ValueError(f"mode must be one of {VALID_MODES}")
        # Safety: always zero motors during mode transitions.
        self.deps.bridge.set_motors(0, 0)
        self.deps.state.set_mode(mode)
        log.info("Mode switched to %s via web", mode)
        self._send_json({"ok": True, "mode": mode})

    def _api_drive(self):
        body = self._read_json()
        if "left" not in body or "right" not in body:
            raise ValueError("body requires 'left' and 'right'")
        snap = self.deps.state.snapshot()
        if snap["mode"] != "WEB":
            self._send_json(
                {"ok": False, "error": "not_in_web_mode", "mode": snap["mode"]},
                HTTPStatus.CONFLICT,
            )
            return
        self.deps.state.set_web_drive(body["left"], body["right"])
        self._send_json({"ok": True})

    def _api_estop(self):
        self.deps.bridge.set_motors(0, 0)
        self.deps.state.set_mode("MANUAL")
        log.warning("!! WEB E-STOP !!")
        self._send_json({"ok": True})

    def _api_recalibrate(self):
        snap = self.deps.state.snapshot()
        if snap["frame"] is None:
            self._send_json(
                {"ok": False, "error": "no_camera_frame"},
                HTTPStatus.CONFLICT,
            )
            return
        self.deps.navigator.calibrate(snap["frame"])
        log.info("Floor recalibrated via web")
        self._send_json({"ok": True})

    def _api_stream(self):
        self.send_response(HTTPStatus.OK)
        self.send_header(
            "Content-Type", f"multipart/x-mixed-replace; boundary={MJPEG_BOUNDARY}"
        )
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.end_headers()

        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
        last_sent = 0.0
        try:
            while True:
                now = time.monotonic()
                sleep_for = STREAM_INTERVAL - (now - last_sent)
                if sleep_for > 0:
                    time.sleep(sleep_for)

                frame = self.deps.state.snapshot()["frame"]
                if frame is None:
                    time.sleep(0.1)
                    continue

                ok, buf = cv2.imencode(".jpg", frame, encode_params)
                if not ok:
                    continue
                jpeg = buf.tobytes()

                header = (
                    f"--{MJPEG_BOUNDARY}\r\n"
                    f"Content-Type: image/jpeg\r\n"
                    f"Content-Length: {len(jpeg)}\r\n\r\n"
                ).encode("ascii")
                self.wfile.write(header)
                self.wfile.write(jpeg)
                self.wfile.write(b"\r\n")
                self.wfile.flush()
                last_sent = time.monotonic()
        except (BrokenPipeError, ConnectionResetError):
            return


class _ReusingThreadingHTTPServer(ThreadingHTTPServer):
    # Let restarts rebind instantly without waiting on TIME_WAIT.
    allow_reuse_address = True
    daemon_threads = True


class WebServer:
    """Owns the HTTP server thread + the log ring-buffer handler."""

    def __init__(
        self,
        state: RobotState,
        bridge: SerialBridge,
        navigator: Navigator,
        host: str = "0.0.0.0",
        port: int = DEFAULT_PORT,
        log_capacity: int = 500,
    ):
        self.host = host
        self.port = port
        self.logbuf = RingBufferHandler(capacity=log_capacity)
        self.logbuf.setFormatter(
            logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")
        )
        logging.getLogger().addHandler(self.logbuf)

        deps = _Deps()
        deps.state = state
        deps.bridge = bridge
        deps.navigator = navigator
        deps.logbuf = self.logbuf

        # Subclass per-server so we don't leak deps across test instances.
        handler_cls = type("_BoundHandler", (_Handler,), {"deps": deps})

        self._httpd = _ReusingThreadingHTTPServer((host, port), handler_cls)
        self._thread: threading.Thread | None = None

    def start(self):
        self._thread = threading.Thread(
            target=self._httpd.serve_forever,
            name="web",
            daemon=True,
        )
        self._thread.start()
        log.info("Web dashboard listening on http://%s:%d", self.host, self.port)

    def stop(self):
        try:
            self._httpd.shutdown()
            self._httpd.server_close()
        except Exception:
            log.exception("error shutting down web server")


# ---------------------------------------------------------------------------
# Dashboard HTML — single-page, no build step, no external deps.
# ---------------------------------------------------------------------------

DASHBOARD_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<title>Wall-A Dashboard</title>
<style>
  :root{
    --bg:#0d1117; --panel:#161b22; --border:#30363d;
    --fg:#e6edf3; --muted:#8b949e;
    --ok:#3fb950; --warn:#d29922; --bad:#f85149; --accent:#58a6ff;
  }
  *{box-sizing:border-box}
  html,body{margin:0;background:var(--bg);color:var(--fg);
    font-family:ui-monospace,Menlo,Consolas,monospace;font-size:14px}
  header{display:flex;align-items:center;justify-content:space-between;
    padding:10px 16px;border-bottom:1px solid var(--border);background:var(--panel)}
  header h1{font-size:16px;margin:0;letter-spacing:1px}
  .dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;vertical-align:baseline}
  .ok{background:var(--ok)} .bad{background:var(--bad)} .warn{background:var(--warn)}
  main{display:grid;grid-template-columns:1.3fr 1fr;gap:12px;padding:12px;max-width:1400px;margin:0 auto}
  @media (max-width:900px){main{grid-template-columns:1fr}}
  .panel{background:var(--panel);border:1px solid var(--border);border-radius:8px;padding:12px}
  .panel h2{margin:0 0 8px;font-size:13px;text-transform:uppercase;color:var(--muted);letter-spacing:1px}
  .stream{background:#000;border-radius:6px;overflow:hidden;display:flex;align-items:center;justify-content:center;min-height:240px}
  .stream img{display:block;max-width:100%;max-height:60vh;image-rendering:pixelated}
  .grid{display:grid;grid-template-columns:repeat(2,1fr);gap:6px 16px}
  .grid .k{color:var(--muted)} .grid .v{text-align:right}
  .modebar{display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap}
  button{background:#21262d;color:var(--fg);border:1px solid var(--border);
    border-radius:6px;padding:8px 12px;font:inherit;cursor:pointer}
  button:hover{background:#30363d}
  button.active{background:var(--accent);color:#0d1117;border-color:var(--accent)}
  button.danger{background:var(--bad);color:#fff;border-color:var(--bad);font-weight:700}
  button.danger:hover{background:#ff6b63}
  .joy{position:relative;width:100%;max-width:280px;aspect-ratio:1;margin:8px auto;
    background:#0d1117;border:1px solid var(--border);border-radius:50%;touch-action:none;user-select:none}
  .joy .knob{position:absolute;width:60px;height:60px;border-radius:50%;
    background:var(--accent);left:50%;top:50%;transform:translate(-50%,-50%);
    transition:transform .05s linear;box-shadow:0 2px 8px rgba(0,0,0,.4)}
  .joy.disabled{opacity:.4}
  .logs{height:220px;overflow:auto;background:#010409;border:1px solid var(--border);
    border-radius:6px;padding:6px 8px;font-size:12px;white-space:pre-wrap;line-height:1.35}
  .log-INFO{color:#c9d1d9} .log-WARNING{color:var(--warn)}
  .log-ERROR,.log-CRITICAL{color:var(--bad)} .log-DEBUG{color:var(--muted)}
  .bar{position:relative;height:8px;background:#30363d;border-radius:4px;overflow:hidden}
  .bar>div{position:absolute;top:0;bottom:0;left:50%;background:var(--accent);transform-origin:left}
  .row{display:flex;align-items:center;gap:8px;margin:4px 0}
  .row .label{width:60px;color:var(--muted)}
  .row .num{width:50px;text-align:right;font-variant-numeric:tabular-nums}
  .hint{color:var(--muted);font-size:12px;margin-top:6px}
</style>
</head>
<body>
<header>
  <h1>WALL-A</h1>
  <div>
    <span id="hdrArduino"><span class="dot bad"></span>arduino</span>
    &nbsp;
    <span id="hdrCamera"><span class="dot bad"></span>camera</span>
    &nbsp;
    <span id="hdrController"><span class="dot bad"></span>controller</span>
    &nbsp;&nbsp;
    <span id="hdrMode" style="color:var(--muted)">mode: —</span>
  </div>
</header>
<main>
  <section class="panel">
    <h2>Camera</h2>
    <div class="stream"><img id="stream" alt="camera stream"></div>
    <div class="hint">MJPEG at ~15 fps. If blank, the Pi camera isn't connected yet.</div>
  </section>

  <section class="panel">
    <h2>Control</h2>
    <div class="modebar">
      <button id="btnManual">MANUAL</button>
      <button id="btnAuto">AUTO</button>
      <button id="btnWeb">WEB</button>
      <button id="btnRecal">recalibrate floor</button>
    </div>
    <div class="joy disabled" id="joy"><div class="knob" id="knob"></div></div>
    <div class="row"><span class="label">left</span>
      <div class="bar" style="flex:1"><div id="barLeft"></div></div>
      <span class="num" id="numLeft">0</span></div>
    <div class="row"><span class="label">right</span>
      <div class="bar" style="flex:1"><div id="barRight"></div></div>
      <span class="num" id="numRight">0</span></div>
    <div style="margin-top:10px;text-align:center">
      <button class="danger" id="btnEstop">E-STOP</button>
    </div>
    <div class="hint">Switch to WEB mode to enable the joystick. Release → motors idle.
      No command for 500ms → watchdog cuts power.</div>
  </section>

  <section class="panel">
    <h2>Diagnostics</h2>
    <div class="grid" id="diagGrid"></div>
  </section>

  <section class="panel">
    <h2>Logs</h2>
    <div class="logs" id="logs"></div>
  </section>
</main>

<script>
(() => {
  const $ = id => document.getElementById(id);
  let currentMode = null;

  // ---- camera ----
  $('stream').src = '/api/stream.mjpg?t=' + Date.now();

  // ---- polling ----
  async function refresh(){
    try {
      const [diag, logs] = await Promise.all([
        fetch('/api/diag', {cache:'no-store'}).then(r=>r.json()),
        fetch('/api/logs?n=80', {cache:'no-store'}).then(r=>r.json()),
      ]);
      render(diag, logs);
    } catch(e){ /* transient */ }
  }

  function dot(el, ok){
    const d = el.querySelector('.dot');
    d.className = 'dot ' + (ok ? 'ok' : 'bad');
  }

  function render(d, logs){
    dot($('hdrArduino'), d.connections.arduino);
    dot($('hdrCamera'), d.connections.camera);
    dot($('hdrController'), d.connections.controller);
    $('hdrMode').textContent = 'mode: ' + d.mode;
    $('hdrMode').style.color = d.mode === 'WEB' ? 'var(--accent)'
                             : d.mode === 'AUTO' ? 'var(--warn)' : 'var(--fg)';

    currentMode = d.mode;
    ['Manual','Auto','Web'].forEach(m=>{
      $('btn'+m).classList.toggle('active', d.mode === m.toUpperCase());
    });
    $('joy').classList.toggle('disabled', d.mode !== 'WEB');

    const batLow = d.battery_voltage > 0 && d.battery_voltage < 6.5;
    const grid = $('diagGrid');
    grid.innerHTML = `
      <div class="k">battery</div>
      <div class="v" style="color:${batLow?'var(--bad)':'inherit'}">${d.battery_voltage.toFixed(2)} V</div>
      <div class="k">motor cmd L/R</div>
      <div class="v">${d.motors.left} / ${d.motors.right}</div>
      <div class="k">web drive L/R</div>
      <div class="v">${d.web_drive.left} / ${d.web_drive.right}</div>
      <div class="k">web cmd age</div>
      <div class="v">${d.web_drive.age_ms==null?'—':d.web_drive.age_ms+' ms'}</div>
      <div class="k">bump L / R</div>
      <div class="v">${d.bumps.front_left?'⬤':'○'} / ${d.bumps.front_right?'⬤':'○'}</div>
      <div class="k">arduino</div>
      <div class="v">${d.connections.arduino?'up':'<span style="color:var(--bad)">down</span>'}</div>
      <div class="k">camera</div>
      <div class="v">${d.connections.camera?'up':'<span style="color:var(--bad)">down</span>'}</div>
      <div class="k">controller</div>
      <div class="v">${d.connections.controller?'up':'<span style="color:var(--muted)">absent</span>'}</div>
    `;

    setBar('barLeft', 'numLeft', d.motors.left);
    setBar('barRight', 'numRight', d.motors.right);

    const box = $('logs');
    const atBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 30;
    box.innerHTML = logs.lines.map(l => {
      const t = new Date(l.time * 1000).toLocaleTimeString();
      const esc = s => s.replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
      return `<div class="log-${esc(l.level)}">${t} [${esc(l.name)}] ${esc(l.level)}: ${esc(l.message)}</div>`;
    }).join('');
    if (atBottom) box.scrollTop = box.scrollHeight;
  }

  function setBar(barId, numId, value){
    const pct = Math.max(-1, Math.min(1, value/255));
    const b = $(barId);
    b.style.width = Math.abs(pct)*50 + '%';
    b.style.left = pct >= 0 ? '50%' : (50 + pct*50) + '%';
    $(numId).textContent = value;
  }

  setInterval(refresh, 400);
  refresh();

  // ---- mode buttons ----
  async function setMode(m){
    const r = await fetch('/api/mode', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({mode:m}),
    });
    if (!r.ok) alert('mode change failed: ' + r.status);
    refresh();
  }
  $('btnManual').onclick = () => setMode('MANUAL');
  $('btnAuto').onclick   = () => setMode('AUTO');
  $('btnWeb').onclick    = () => setMode('WEB');
  $('btnEstop').onclick  = async () => {
    await fetch('/api/estop', {method:'POST'});
    refresh();
  };
  $('btnRecal').onclick  = async () => {
    const r = await fetch('/api/recalibrate', {method:'POST'});
    const j = await r.json().catch(()=>({}));
    if (!j.ok) alert('recalibrate failed: ' + (j.error||r.status));
  };

  // ---- joystick ----
  const joy = $('joy'), knob = $('knob');
  let dragging = false, lastSend = 0;
  let joyX = 0, joyY = 0;

  function updateKnob(cx, cy){
    const r = joy.getBoundingClientRect();
    const rad = r.width/2;
    let dx = cx - (r.left + rad);
    let dy = cy - (r.top + rad);
    const dist = Math.hypot(dx, dy);
    if (dist > rad) { dx = dx/dist * rad; dy = dy/dist * rad; }
    knob.style.transform = `translate(calc(-50% + ${dx}px), calc(-50% + ${dy}px))`;
    joyX = dx/rad; joyY = dy/rad;
  }

  function resetKnob(){
    knob.style.transform = 'translate(-50%,-50%)';
    joyX = 0; joyY = 0;
  }

  function send(){
    // Arcade mixing — up is forward.
    const throttle = -joyY;
    const turn = joyX;
    let left = throttle + turn, right = throttle - turn;
    const m = Math.max(Math.abs(left), Math.abs(right), 1);
    left  = Math.round(left/m * 255 * Math.min(1, Math.hypot(joyX, joyY)));
    right = Math.round(right/m * 255 * Math.min(1, Math.hypot(joyX, joyY)));
    fetch('/api/drive', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({left, right}),
    }).catch(()=>{});
  }

  joy.addEventListener('pointerdown', e => {
    if (currentMode !== 'WEB') return;
    dragging = true;
    joy.setPointerCapture(e.pointerId);
    updateKnob(e.clientX, e.clientY);
  });
  joy.addEventListener('pointermove', e => {
    if (!dragging) return;
    updateKnob(e.clientX, e.clientY);
  });
  const endDrag = e => {
    if (!dragging) return;
    dragging = false;
    resetKnob();
    send();  // one last zero command
  };
  joy.addEventListener('pointerup', endDrag);
  joy.addEventListener('pointercancel', endDrag);
  joy.addEventListener('lostpointercapture', endDrag);

  // Throttle drive commands to ~10 Hz.
  setInterval(() => {
    if (currentMode !== 'WEB') return;
    const now = Date.now();
    if (now - lastSend < 100) return;
    // Always send while in WEB mode so the watchdog stays fed when idle at center.
    lastSend = now;
    send();
  }, 100);
})();
</script>
</body>
</html>
"""
