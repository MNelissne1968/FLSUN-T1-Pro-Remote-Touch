#!/usr/bin/env python3

"""
FLSUN T1 Pro Remote Touch
Version: 0.2.1
Mode: Interactive framebuffer viewer

Resolution: 480 x 272
Pixel format: BGRA 32-bit
Framebuffer: /dev/fb0

No external Python dependencies.
No modification of the original FLSUN TUI.
"""

import os
import time
import json
import secrets
import struct
import zlib
from http.server import HTTPServer, BaseHTTPRequestHandler

WIDTH = 480
HEIGHT = 272
STRIDE = 1920
FRAMEBUFFER = "/dev/fb0"

HOST = "127.0.0.1"
PORT = 8765
TOKEN = secrets.token_hex(32)
DEVICE = "/dev/input/event1"


def send_touch(x, y):

    with open("/etc/pointercal") as f:
        a,b,c,d,e,f0,s = map(int,f.read().split()[:7])

    det = a*e-b*d

    u = x*s-c
    v = y*s-f0

    rx = round((e*u-b*v)/det)
    ry = round((a*v-d*u)/det)

    if not (-5 <= rx <= 270 and -21 <= ry <= 491):
        raise ValueError("Outside calibrated touch range")

    fd = os.open(DEVICE, os.O_WRONLY)

    def event(t,c,v):
        os.write(fd,struct.pack("@llHHi",0,0,t,c,v))

    try:
        event(3,47,0)
        event(3,57,100)
        event(3,53,rx)
        event(3,54,ry)
        event(3,48,8)
        event(0,0,0)

        time.sleep(0.15)

    finally:
        try:
            event(3,47,0)
            event(3,48,0)
            event(3,57,-1)
            event(0,0,0)
        finally:
            os.close(fd)

    print("Touch: screen",x,y,"raw",rx,ry)



def png_chunk(tag, data):
    return (
        struct.pack("!I", len(data))
        + tag
        + data
        + struct.pack(
            "!I", zlib.crc32(tag + data) & 0xffffffff
        )
    )


def capture_screen():

    with open(FRAMEBUFFER, "rb") as fb:
        raw = fb.read(STRIDE * HEIGHT)

    if len(raw) != STRIDE * HEIGHT:
        raise RuntimeError("Invalid framebuffer size")

    rows = bytearray()

    for y in range(HEIGHT):

        start = y * STRIDE
        line = raw[start:start + WIDTH * 4]

        rgb = bytearray(WIDTH * 3)

        rgb[0::3] = line[2::4]
        rgb[1::3] = line[1::4]
        rgb[2::3] = line[0::4]

        rows.append(0)
        rows.extend(rgb)

    png = b"\x89PNG\r\n\x1a\n"

    png += png_chunk(
        b"IHDR",
        struct.pack(
            "!2I5B",
            WIDTH, HEIGHT, 8, 2, 0, 0, 0
        )
    )

    png += png_chunk(
        b"IDAT",
        zlib.compress(bytes(rows), 1)
    )

    png += png_chunk(b"IEND", b"")

    return png


HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport"
      content="width=device-width, initial-scale=1">
<title>FLSUN T1 Pro Remote Touch V0.2.1</title>

<style>
body {
    background:#14191f;
    color:#e5e9ef;
    font-family:Arial,sans-serif;
    text-align:center;
    margin:30px 15px;
}
h1 {
    font-size:26px;
    margin-bottom:8px;
}
.subtitle {
    color:#8b98a5;
    margin-bottom:20px;
}
.toolbar {
    margin:20px 0;
}
button {
    background:#303b45;
    color:white;
    border:1px solid #56636f;
    border-radius:6px;
    padding:12px 24px;
    font-size:15px;
    cursor:pointer;
}
button.active {
    background:#087e64;
    border-color:#00dba7;
}
#viewport {
    position:relative;
    display:inline-block;
    width:960px;
    max-width:100%;
    overflow:hidden;
    border-radius:8px;
    box-shadow:0 8px 35px #0008;
}
#screen {
    display:block;
    width:100%;
    height:auto;
    image-rendering:pixelated;
    cursor:default;
    user-select:none;
    -webkit-user-drag:none;
}
#marker {
    display:none;
    position:absolute;
    width:24px;
    height:24px;
    border:2px solid #00ffb3;
    border-radius:50%;
    transform:translate(-50%,-50%);
    pointer-events:none;
}
#status {
    margin-top:20px;
    color:#00c8bd;
}
#feedback {
    min-height:20px;
    margin-top:12px;
    color:#aab7c4;
}
.footer {
    color:#8b98a5;
    font-size:13px;
    margin-top:25px;
}
</style>
</head>

<body>

<h1>FLSUN T1 Pro Remote Touch</h1>
<div class="subtitle">
    Version 0.2.1 | Interactive Edition
</div>

<div class="toolbar">
    <button id="toggle">Enable Touch Control</button>
</div>

<div id="viewport">
    <img id="screen" alt="Printer touchscreen"
         draggable="false">
    <div id="marker"></div>
</div>

<div id="status">Connecting...</div>
<div id="feedback">Touch control disabled</div>

<div class="footer">
    Original FLSUN touchscreen |
    480 x 272 | Local SSH connection
</div>

<script>
const screen = document.getElementById("screen");
const status = document.getElementById("status");
const toggle = document.getElementById("toggle");
const marker = document.getElementById("marker");
const feedback = document.getElementById("feedback");

let enabled = false;
let connected = false;
let busy = false;
let lastFrame = 0;
let started = 0;

function updateStatus() {
    status.textContent = connected
        ? (enabled ? "LIVE - Touch Control"
                   : "LIVE - Read-only")
        : "Connection interrupted";

    status.style.color = connected
        ? "#00c8bd" : "#ff6666";

    toggle.textContent = enabled
        ? "Disable Touch Control"
        : "Enable Touch Control";

    toggle.classList.toggle("active", enabled);
    screen.style.cursor = enabled
        ? "crosshair" : "default";
}

toggle.onclick = function() {
    if (!connected || busy) return;

    if (!enabled && !confirm(
        "Enable live printer touch control?"
    )) return;

    enabled = !enabled;
    feedback.textContent = enabled
        ? "Touch control enabled"
        : "Touch control disabled";

    updateStatus();
};

function refreshScreen() {
    started = Date.now();
    screen.src = "/screen.png?t=" + started;
}

screen.onload = function() {
    connected = true;
    lastFrame = Date.now();
    updateStatus();

    setTimeout(refreshScreen,
        Math.max(0, 500-(Date.now()-started)));
};

screen.onerror = function() {
    connected = false;
    enabled = false;
    updateStatus();
    setTimeout(refreshScreen,3000);
};

screen.addEventListener("click", async function(e) {

    if (!enabled || !connected || busy) return;

    if (Date.now()-lastFrame > 2000) {
        enabled = false;
        updateStatus();
        feedback.textContent = "Stale image - touch blocked";
        return;
    }

    const r = screen.getBoundingClientRect();

    const x = Math.floor(
        (e.clientX-r.left)*480/r.width
    );

    const y = Math.floor(
        (e.clientY-r.top)*272/r.height
    );

    if (x<0 || x>=480 || y<0 || y>=272) return;

    busy = true;

    marker.style.left = (x/480*100)+"%";
    marker.style.top = (y/272*100)+"%";
    marker.style.display = "block";

    try {
        const response = await fetch("/touch", {
            method:"POST",
            headers:{
                "Content-Type":"application/json",
                "X-Touch-Token":"__TOKEN__"
            },
            body:JSON.stringify({x:x,y:y})
        });

        if (!response.ok) {
            throw new Error(response.statusText);
        }

        feedback.textContent =
            "Touch sent: X="+x+" Y="+y;

    } catch(error) {
        enabled = false;
        updateStatus();
        feedback.textContent =
            "Touch blocked: "+error.message;
    } finally {
        setTimeout(function() {
            marker.style.display = "none";
            busy = false;
        },600);
    }
});

refreshScreen();
</script>
</body>
</html>
"""


class RemoteTouchHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        path = self.path.split("?")[0]

        if path == "/":

            data = HTML.replace("__TOKEN__", TOKEN).encode("utf-8")

            self.send_response(200)
            self.send_header(
                "Content-Type", "text/html; charset=utf-8"
            )
            self.send_header("Content-Length", len(data))
            self.end_headers()
            self.wfile.write(data)

        elif path == "/screen.png":

            try:
                data = capture_screen()

                self.send_response(200)
                self.send_header(
                    "Content-Type", "image/png"
                )
                self.send_header(
                    "Cache-Control", "no-store"
                )
                self.send_header(
                    "Content-Length", len(data)
                )
                self.end_headers()
                self.wfile.write(data)

            except (BrokenPipeError, ConnectionResetError):
                pass

            except Exception as error:
                print("Capture error:", error)
                self.send_error(500)

        else:
            self.send_error(404)

    def do_POST(self):

        if self.path != "/touch":
            self.send_error(404)
            return

        if self.headers.get("Origin") not in (
            "http://localhost:8765",
            "http://127.0.0.1:8765"
        ):
            self.send_error(403)
            return

        if self.headers.get("X-Touch-Token") != TOKEN:
            self.send_error(403)
            return

        try:
            length = int(self.headers.get("Content-Length",0))

            if not 1 <= length <= 256:
                raise ValueError("Invalid request size")

            data = json.loads(self.rfile.read(length))
            x = data["x"]
            y = data["y"]

            if type(x) is not int or type(y) is not int:
                raise ValueError("Invalid coordinates")

            if not (0 <= x < WIDTH and 0 <= y < HEIGHT):
                raise ValueError("Outside screen")

            send_touch(x,y)

        except (ValueError, KeyError, TypeError) as error:
            self.send_error(400,str(error))
            return

        except Exception as error:
            print("Touch error:",error)
            self.send_error(500,"Touch failed")
            return

        self.send_response(200)
        self.send_header("Content-Length","2")
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":

    server = HTTPServer(
        (HOST, PORT),
        RemoteTouchHandler
    )

    print("=" * 48)
    print("FLSUN T1 Pro Remote Touch V0.2.1")
    print("Mode: INTERACTIVE - default read-only")
    print("Framebuffer:", FRAMEBUFFER)
    print("Resolution: 480 x 272")
    print("Listening on:", HOST, PORT)
    print("Press CTRL+C to stop")
    print("=" * 48)

    try:
        server.serve_forever()

    except KeyboardInterrupt:
        print("\nRemote Touch stopped.")

    finally:
        server.server_close()