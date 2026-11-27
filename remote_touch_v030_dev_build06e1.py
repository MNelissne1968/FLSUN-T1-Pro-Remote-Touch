#!/usr/bin/env python3

"""
FLSUN T1 Pro Remote Touch
Version: 0.3.0
Mode: Interactive framebuffer viewer

Resolution: 480 x 272
Pixel format: BGRA 32-bit
Framebuffer: /dev/fb0

No external Python dependencies.
No modification of the original FLSUN TUI.
"""

import os
import urllib.request
import urllib.parse
import argparse
import secrets
import threading
import time
import json
import struct
import zlib
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

WIDTH = 480
HEIGHT = 272
STRIDE = 1920
FRAMEBUFFER = "/dev/fb0"

HOST = "127.0.0.1"
PORT = 8765
DEMO = False
API_KEY = secrets.token_hex(32)
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

    if DEMO:
        rows = b"".join(b"\x00" + b"".join(bytes((25 + x//8, 45 + y//4, 80)) for x in range(WIDTH)) for y in range(HEIGHT))
        return (b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", struct.pack("!2I5B", WIDTH, HEIGHT, 8, 2, 0, 0, 0)) + png_chunk(b"IDAT", zlib.compress(rows, 1)) + png_chunk(b"IEND", b""))
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
<title>FLSUN T1 Pro Remote Touch V0.3.0</title>

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
    image-rendering:auto;
    cursor:default;
    user-select:none;
    -webkit-user-drag:none;
}
#screen[data-quality="original"] { image-rendering:pixelated; }
#screen[data-quality="enhanced"] { image-rendering:auto; filter:url(#display-sharpen); }
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

body.light { background:#eef2f6; color:#202833; }
body.light #status, body.light #feedback { color:#17665c; }
.toolbar { display:flex; flex-wrap:wrap; justify-content:center; align-items:center; gap:10px; }
select { padding:8px; border-radius:6px; background:#26313c; color:#e5e9ef; border:1px solid #56636f; }
body.light select, body.light button { background:#fff; color:#202833; border-color:#aab7c4; }
button:disabled { opacity:.45; cursor:not-allowed; }
button:focus-visible, select:focus-visible { outline:2px solid #00c8bd; outline-offset:3px; }
#diagnostics { display:flex; flex-wrap:wrap; justify-content:center; gap:12px; margin:12px auto; font-size:13px; }
#diagnostics span { border:1px solid #56636f; border-radius:6px; padding:7px 12px; }
@media(max-width:600px) { body { margin:15px 8px; } h1 { font-size:21px; } button { padding:9px 12px; } .toolbar { gap:6px; } }

#viewport:fullscreen { width:100%; height:100%; background:#000; display:flex; align-items:center; justify-content:center; }
#viewport:fullscreen #screen { width:auto; height:auto; max-width:100%; max-height:100%; object-fit:contain; }

#workspace {display:flex; align-items:flex-start; justify-content:center; gap:18px; flex-wrap:wrap;}
#touchpane {min-width:0; max-width:100%; flex:0 1 auto;}
#dashboard {flex:1 1 440px; max-width:960px; min-width:0; text-align:left;}
#dashboard[hidden], #touchpane[hidden] {display:none;}
.panel {background:#232c36; border:1px solid #56636f; border-radius:10px; padding:14px; margin-bottom:12px;}
body.light .panel {background:white; border-color:#b8c2cc;}
.metrics {display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:10px;}
.metrics .panel {margin:0;}
.metric {font-size:23px; font-weight:bold; margin:8px 0;}
small {opacity:.8;}
progress {width:100%; accent-color:#00a99d;}
#history {width:100%; height:auto; display:block;}
#preview {border:1px dashed #8795a3; padding:25px; text-align:center; border-radius:8px;}

* {box-sizing:border-box;}
#workspace {width:100%; max-width:1800px; margin:auto; display:grid; grid-template-columns:minmax(0,1fr);}
#workspace[data-view="combined"] {grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);}
#touchpane,#dashboard {width:100%; min-width:0; max-width:100%;}
#dashboard {overflow-wrap:anywhere;}
#workspace[data-view="touch"] #touchpane {justify-self:center;}
#workspace[data-view="dashboard"] #dashboard {max-width:1200px; justify-self:center;}
.metrics {grid-template-columns:repeat(2,minmax(0,1fr)); margin-bottom:10px;}
.panel {padding:12px; margin-bottom:10px; text-align:left;}
.panel p {margin:8px 0;}
.metric {font-size:clamp(17px,1.5vw,23px);}
.heat .metric {color:#f59e42;} .cool .metric {color:#00b9ae;}
body.light .heat .metric {color:#a34b00;} body.light .cool .metric {color:#08756e;}
.xyz {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;}
.jobhead {display:flex;gap:12px;align-items:center;}
#preview {flex:0 0 90px;padding:8px;font-size:12px;}
.primary {font-size:26px;font-weight:bold;}
#historypanel {margin-top:12px;}
#curves {display:flex;flex-wrap:wrap;gap:8px;font-size:13px;margin:8px 0;}
@media(max-width:950px){#workspace[data-view="combined"] {grid-template-columns:minmax(0,1fr);}}
</style>
</head>

<body>

<h1>FLSUN T1 Pro Remote Touch</h1>
<div class="subtitle">
    Version 0.3.0 | Virtual Touch Bridge (DEV Build 06E1)
</div>

<div class="toolbar">
<label>View <select id="view"><option value="touch">Touchscreen</option><option value="combined">Combined</option><option value="dashboard">Dashboard</option></select></label>
    <button id="toggle" disabled>Enable Demo Touch</button>
    <button disabled title="Server blocks all POST requests">Live Touch locked</button>
    <button id="fullscreen">⛶ Fullscreen</button>
    <button id="snapshot">▣ Screenshot</button>
    <label>Size <select id="size"><option value="480">480 px</option><option value="720">720 px</option><option value="960">960 px</option><option value="1440">1440 px</option></select></label>
    <label>Image quality <select id="quality"><option value="original">Original</option><option value="smooth">Smooth</option><option value="enhanced">Enhanced</option></select></label>
    <label>Refresh <select id="fps"><option value="1">1 FPS</option><option value="2">2 FPS</option></select></label>
    <button id="theme">◐ Light / Dark</button>
</div>

<svg width="0" height="0" aria-hidden="true" style="position:absolute"><defs><filter id="display-sharpen" color-interpolation-filters="sRGB"><feConvolveMatrix order="3" kernelMatrix="0 -0.12 0 -0.12 1.48 -0.12 0 -0.12 0" preserveAlpha="true" edgeMode="duplicate"/></filter></defs></svg>
<div id="workspace"><section id="touchpane"><div id="viewport">
    <img id="screen" alt="Printer touchscreen"
         draggable="false">
    <div id="marker"></div>
</div>

<div id="status">Connecting...</div>
<div id="diagnostics"><span id="actualfps">Actual FPS: —</span><span id="lastseen">Last frame: —</span><span id="retry">Connecting</span></div>
<div id="safety" class="panel">Safety check pending — physical touch locked</div><div id="feedback">Read Only — Live Touch locked</div><div class="panel"><strong>Touch Event Log — simulation only</strong><p><button id="authprobe">Test Live eligibility (no physical touch)</button></p><div id="eventlog" aria-live="polite"></div></div>

</section>
<section id="dashboard" hidden><div id="moonstatus" class="panel">DEMO · recorded data</div>
<div class="panel"><div class="jobhead"><div id="preview">300 × 300<br>Preview placeholder</div><div><strong>DEMO · Recorded printer snapshot</strong><p>Light Bottom.gcode · PRINTING (recorded)</p></div></div>
<div class="primary">25%</div><label>Display progress</label><progress value="25" max="100"></progress>
<label>G-code file progress: 11.31%</label><progress value="11.31" max="100"></progress>
<p>Elapsed: 1h 26m 03s · Slicer estimate: 5h 26m 15s</p><small>Estimated remaining: 4h 02m 40s (slicer estimate minus recorded print duration; not a prediction)</small></div>
<div class="metrics" id="metrics"></div><div class="panel"><strong>Toolhead position · mm</strong><div class="xyz"><div>X<div class="metric">7.17</div></div><div>Y<div class="metric">−2.59</div></div><div>Z<div class="metric">3.09</div></div></div></div><div class="panel" id="historypanel"><strong>Temperature history · simulated</strong><div id="curves"></div><svg id="history" viewBox="0 0 440 180" role="img" aria-label="Simulated temperature history"></svg><small>Dashed: heater targets · sample index, not verified time interval</small></div>

<div class="panel"><strong>Filament · 27.18%</strong><progress value="27.18" max="100"></progress><p>17.23 / 63.39 m · Estimated used weight: 51.38 g</p><p>SunLu High Speed PLA+ · PLA</p></div>
<div class="panel"><strong>Print metadata</strong><p>FlsunSlicer 3.0.0.20 · 983 layers · 177.1 mm height</p><p>Layer: 0.2 mm · Nozzle: 0.4 mm · Estimated total: 189.05 g</p></div>
</section></div>
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

const apiKey = "__API_KEY__";
function eventLog(message){const e=document.createElement("div");e.textContent=new Date().toLocaleTimeString("nl-NL",{hour12:false})+" | "+message;const log=document.getElementById("eventlog");log.prepend(e);while(log.children.length>20)log.lastChild.remove();}
async function api(path,data){const r=await fetch(path,{method:"POST",headers:{"Content-Type":"application/json","X-Simulation-Key":apiKey},body:JSON.stringify(data),signal:AbortSignal.timeout(8000)});const j=await r.json();eventLog((r.ok?"PASS ":"DENIED ")+j.reason);return j;}
document.getElementById("authprobe").onclick=async()=>{try{await api("/api/eligibility",{});}catch(e){eventLog("ERROR eligibility unavailable");}};
let enabled = false;
let connected = false;
let busy = false;
let lastFrame = 0;
let started = 0;
let frameTimer = null;
let retryAt = 0;
let frameTimes = [];
const demo = __DEMO__;
const actualfps = document.getElementById("actualfps");
const lastseen = document.getElementById("lastseen");
const retry = document.getElementById("retry");
function diagnostics() {
    const now=Date.now();
    frameTimes=frameTimes.filter(t=>now-t<=5000);
    const rate=frameTimes.length>1 ? (frameTimes.length-1)*1000/(frameTimes[frameTimes.length-1]-frameTimes[0]) : 0;
    actualfps.textContent="Actual FPS: "+(connected && rate>0 ? rate.toFixed(1):"—");
    lastseen.textContent="Last frame: "+(lastFrame?new Date(lastFrame).toLocaleTimeString("nl-NL",{hour12:false}):"—");
    retry.textContent=retryAt ? "Retry in "+Math.max(0,Math.ceil((retryAt-now)/1000))+" s" : connected ? "Receiving frames" : "Connecting";
}
setInterval(diagnostics,250);
const size = document.getElementById("size");
const fps = document.getElementById("fps");
const viewport = document.getElementById("viewport");
function pref(key, fallback) { try { return localStorage.getItem("flsun022."+key) || fallback; } catch(e) { return fallback; } }
function save(key,value) { try { localStorage.setItem("flsun022."+key,value); } catch(e) {} }
const quality=document.getElementById("quality");
quality.value=pref("quality","smooth");
if(!quality.value) quality.value="smooth";
function applyQuality(){screen.dataset.quality=quality.value;save("quality",quality.value);}
quality.onchange=applyQuality; applyQuality();
size.value = pref("size","960");
if (!size.value) size.value="960";
fps.value = pref("fps","2");
if (!fps.value) fps.value="2";
viewport.style.width=size.value+"px";
document.body.classList.toggle("light",pref("theme","dark")==="light");
size.onchange=()=>{ viewport.style.width=size.value+"px"; save("size",size.value); };
fps.onchange=()=>save("fps",fps.value);
document.getElementById("theme").onclick=()=>{ const light=document.body.classList.toggle("light"); save("theme",light?"light":"dark"); };
document.getElementById("fullscreen").onclick=async()=>{ try { if(document.fullscreenElement) await document.exitFullscreen(); else await viewport.requestFullscreen(); } catch(e) { feedback.textContent="Fullscreen unavailable"; } };
document.getElementById("snapshot").onclick=()=>{ if(!connected || Date.now()-lastFrame>2000) { feedback.textContent="No fresh image"; return; } const canvas=document.createElement("canvas"); canvas.width=480; canvas.height=272; canvas.getContext("2d").drawImage(screen,0,0,480,272); canvas.toBlob(blob=>{ if(!blob)return; const url=URL.createObjectURL(blob); const a=document.createElement("a"); a.href=url; a.download="FLSUN-"+new Date().toISOString().replace(/[:.]/g,"-")+".png"; a.click(); setTimeout(()=>URL.revokeObjectURL(url),1000); },"image/png"); };
setInterval(()=>{ if(connected && Date.now()-lastFrame>2000) { connected=false; enabled=false; marker.style.display="none"; updateStatus(); feedback.textContent="Waiting for a fresh frame"; } },500);

function updateStatus() {
    status.textContent = connected
        ? (enabled ? "DEMO TOUCH - simulation only" : demo ? "DEMO - Read-only" : "LIVE - Read-only")
        : "Connection interrupted";

    status.style.color = connected
        ? "#00c8bd" : "#ff6666";

    toggle.textContent = enabled
        ? "Disable Demo Touch"
        : "Enable Demo Touch";

    toggle.disabled = !connected || document.getElementById("view").value === "dashboard";
    toggle.classList.toggle("active", enabled);
    screen.style.cursor = enabled
        ? "crosshair" : "default";
}

toggle.onclick = function() {
    if (!connected || Date.now()-lastFrame>2000) return;
    if (!enabled && !confirm(
        "Enable simulated touch? No commands will be sent to the printer."
    )) return;

    enabled = !enabled;
    feedback.textContent = enabled
        ? "Demo Touch enabled — no commands sent"
        : "Read Only — Live Touch locked";

    updateStatus();
};

function refreshScreen() {
    retryAt = 0;
    started = Date.now();
    screen.src = "/screen.png?t=" + started;
}

screen.onload = function() {
    connected = true;
    lastFrame = Date.now();
    frameTimes.push(lastFrame);
    diagnostics();
    updateStatus();

    setTimeout(refreshScreen,
        Math.max(0, 1000/Number(fps.value)-(Date.now()-started)));
};

screen.onerror = function() {
    connected = false;
    enabled = false;
    marker.style.display="none";
    updateStatus();
    frameTimes=[];
    retryAt=Date.now()+3000;
    feedback.textContent="Connection lost — touch disabled";
    diagnostics();
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

    const scale=Math.min(r.width/480,r.height/272);
    const w=480*scale,h=272*scale;
    const left=r.left+(r.width-w)/2,top=r.top+(r.height-h)/2;
    const x = Math.floor(
        (e.clientX-left)*480/w
    );

    const y = Math.floor(
        (e.clientY-top)*272/h
    );

    if (x<0 || x>=480 || y<0 || y>=272) return;

    busy = true;

    const vr=viewport.getBoundingClientRect();
    marker.style.left = (e.clientX-vr.left)+"px";
    marker.style.top = (e.clientY-vr.top)+"px";
    marker.style.display = "block";

    feedback.textContent = "SIMULATED ONLY: X="+x+" Y="+y+" — nothing sent";
    try {const a=await api("/api/demo/authorize",{});if(a.token && enabled && connected && Date.now()-lastFrame<=2000){await api("/api/demo/submit",{token:a.token,x,y});}}catch(e){eventLog("ERROR simulation API unavailable");}finally{setTimeout(()=>{marker.style.display="none";busy=false;},600);}

});

const view=document.getElementById("view");
view.value=pref("view","combined"); if(!view.value)view.value="combined";
function applyView(){document.getElementById("workspace").dataset.view=view.value; const graph=document.getElementById("historypanel"); if(view.value==="combined")document.getElementById("touchpane").appendChild(graph); else document.getElementById("dashboard").appendChild(graph);const touch=view.value!=="dashboard"; document.getElementById("touchpane").hidden=!touch; document.getElementById("dashboard").hidden=view.value==="touch"; for(const id of ["fullscreen","snapshot","size","fps","quality"])document.getElementById(id).disabled=!touch; if(!touch){enabled=false;marker.style.display="none";feedback.textContent="Read Only — dashboard view";} updateStatus();save("view",view.value);}
view.onchange=applyView; applyView();
const values=[["Nozzle","224.19 °C","Target 225 °C"],["Heatbed","59.56 °C","Target 60 °C"],["ARM processor","60.2 °C","Peak 61.5 °C"],["MCU","49.76 °C","Peak 50.77 °C"],["Live velocity","120 mm/s","Speed factor 100%"],["Cooling fan","60%","Configured maximum 60%"],["Filament","Detected","Sensor enabled"],["Box light","ON","Recorded status"]];
for(const [name,value,note] of values){const card=document.createElement("div");card.className="panel "+(["Nozzle","Heatbed"].includes(name)?"heat":"cool");for(const [tag,txt,cls] of [["small",name,""],["div",value,"metric"],["small",note,""]]){const e=document.createElement(tag);e.textContent=txt;e.className=cls;card.appendChild(e);}document.getElementById("metrics").appendChild(card);}
const svg=document.getElementById("history");
function shape(tag,attrs,txt){const e=document.createElementNS("http://www.w3.org/2000/svg",tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);if(txt)e.textContent=txt;svg.appendChild(e);}
const yy=t=>155-t/250*140;
const series=[["Nozzle",225,"#e99136",1.8,true],["Bed",60,"#00a99d",.6,true],["CPU",60.2,"#a78bfa",.5,false],["MCU",49.76,"#60a5fa",.4,false]];
const controls=document.getElementById("curves");
for(const [name,target,color,amp,heater] of series){const label=document.createElement("label");const input=document.createElement("input");input.type="checkbox";input.checked=heater;input.dataset.sensor=name;input.onchange=drawHistory;label.append(input,document.createTextNode(name));label.style.color=color;controls.appendChild(label);}
function drawHistory(){svg.replaceChildren();for(const t of [0,50,100,150,200,250]){shape("line",{x1:35,x2:430,y1:yy(t),y2:yy(t),stroke:"#8795a3","stroke-opacity":.3});shape("text",{x:0,y:yy(t)+4,fill:"currentColor","font-size":10},t+"°");}
for(const [name,target,color,amp,heater] of series){if(!controls.querySelector('input[data-sensor="'+name+'"]').checked)continue;if(heater)shape("line",{x1:35,x2:430,y1:yy(target),y2:yy(target),stroke:color,"stroke-dasharray":"4 4"});const pts=Array.from({length:120},(_,i)=>(35+i*395/119)+","+yy(target+amp*Math.sin(i*.67)+amp*.3*Math.cos(i*1.9))).join(" ");shape("polyline",{points:pts,fill:"none",stroke:color,"stroke-width":1.6});}}
drawHistory();

if(!demo){
const dash=document.getElementById("dashboard"), panels=dash.querySelectorAll(":scope > .panel"), job=panels[1], xyz=dash.querySelector(".xyz"), filament=Array.from(panels).find(p=>p.textContent.startsWith("Filament")), metaPanel=Array.from(panels).find(p=>p.textContent.startsWith("Print metadata"));
const ms=document.getElementById("moonstatus"); let metadata=null, filename=null, history=null, lastStatus=null;
const fmt=(v,d=1)=>typeof v==="number"&&Number.isFinite(v)?v.toFixed(d):"—";
const duration=v=>typeof v==="number"?Math.floor(v/3600)+"h "+Math.floor(v%3600/60)+"m "+Math.floor(v%60)+"s":"—";
const pct=v=>typeof v==="number"?fmt(v*100,1)+"%":"—";
async function get(path){const r=await fetch(path,{cache:"no-store"});if(!r.ok)throw Error(r.status);const j=await r.json();if(!j.result)throw Error("Missing result");return j.result;}
function line(parent,tag,txt){const e=document.createElement(tag);e.textContent=txt;parent.appendChild(e);return e;}
function bar(parent,v){const e=document.createElement("progress");e.max=1;if(typeof v==="number")e.value=Math.max(0,Math.min(1,v));parent.appendChild(e);}
function render(t){const p=t.print_stats||{}, e=t.extruder||{}, b=t.heater_bed||{}, cpu=t["temperature_sensor Armv7 mcu"]||{}, mcu=t["temperature_sensor mcu_temp"]||{}, f=t.fan||{}, g=t.gcode_move||{}, motion=t.motion_report||{}, fs=t["filament_switch_sensor filament_sensor"]||{};const m=metadata||{};
job.replaceChildren();const head=line(job,"div","");head.className="jobhead";const preview=line(head,"div","Preview unavailable");preview.id="preview";const thumb=(m.thumbnails||[]).slice().sort((a,b)=>b.width-a.width)[0];if(thumb&&thumb.relative_path){const img=document.createElement("img");img.style.width="100%";img.alt="Print preview";img.src="/thumbnail?name="+encodeURIComponent((filename.includes("/")?filename.slice(0,filename.lastIndexOf("/")+1):"")+thumb.relative_path);preview.replaceChildren(img);}line(head,"strong",(p.filename||"No file")+" · "+(p.state||"Unknown"));line(job,"div",pct(t.display_status?.progress)).className="primary";line(job,"small","Display progress");bar(job,t.display_status?.progress);line(job,"p","G-code file progress: "+pct(t.virtual_sdcard?.progress));bar(job,t.virtual_sdcard?.progress);line(job,"p","Elapsed: "+duration(p.total_duration)+" · Slicer estimate: "+duration(m.estimated_time));line(job,"small","Remaining (slicer estimate minus print duration): "+duration(typeof m.estimated_time==="number"&&typeof p.print_duration==="number"?Math.max(0,m.estimated_time-p.print_duration):null));
const rows=[[fmt(e.temperature,2)+" °C","Target "+fmt(e.target)+" °C"],[fmt(b.temperature,2)+" °C","Target "+fmt(b.target)+" °C"],[fmt(cpu.temperature)+" °C","Peak "+fmt(cpu.measured_max_temp)],[fmt(mcu.temperature)+" °C","Peak "+fmt(mcu.measured_max_temp)],[fmt(motion.live_velocity)+" mm/s","Speed factor "+pct(g.speed_factor)],[pct(f.speed),"Configured maximum "+pct(f.max_power)],[fs.filament_detected===true?"Detected":fs.filament_detected===false?"Not detected":"—",fs.enabled?"Sensor enabled":"Sensor inactive/unknown"],[t.box_light?.value===1?"ON":t.box_light?.value===0?"OFF":"—","Reported status"]];
Array.from(document.getElementById("metrics").children).forEach((c,i)=>{c.children[1].textContent=rows[i][0];c.children[2].textContent=rows[i][1];});xyz.querySelectorAll(".metric").forEach((x,i)=>x.textContent=fmt(motion.live_position?.[i],2));filament.replaceChildren();const ratio=m.filament_total>0&&typeof p.filament_used==="number"?p.filament_used/m.filament_total:null;line(filament,"strong","Filament · "+pct(ratio));bar(filament,ratio);line(filament,"p",fmt(p.filament_used/1000,2)+" / "+fmt(m.filament_total/1000,2)+" m");line(filament,"p",m.filament_name||"Material unavailable");metaPanel.replaceChildren();line(metaPanel,"strong","Print metadata");line(metaPanel,"p",[m.slicer,m.slicer_version,m.layer_count?m.layer_count+" layers":null].filter(Boolean).join(" · ")||"Metadata unavailable");line(metaPanel,"p","Layer: "+fmt(m.layer_height,2)+" mm · Nozzle: "+fmt(m.nozzle_diameter)+" mm · Estimated total: "+fmt(m.filament_weight_total,2)+" g");}
function clearLive(){render({});}
clearLive();ms.textContent="Moonraker: connecting";
const hp=document.getElementById("historypanel");hp.querySelector("strong").textContent="Temperature history · connecting";svg.setAttribute("aria-label","Live temperature history");
const keys={Nozzle:"extruder",Bed:"heater_bed",CPU:"temperature_sensor Armv7 mcu",MCU:"temperature_sensor mcu_temp"};
drawHistory=function(){svg.replaceChildren();if(!history)return;const max=Math.max(250,...Object.values(history).flatMap(s=>s.temperatures||[]).filter(Number.isFinite));const y=v=>155-v/max*140;for(let i=0;i<=5;i++){const t=max*i/5;shape("line",{x1:35,x2:430,y1:y(t),y2:y(t),stroke:"#8795a3","stroke-opacity":.3});shape("text",{x:0,y:y(t)+4,fill:"currentColor","font-size":10},Math.round(t)+"°");}for(const [name,,color] of series){if(!controls.querySelector('input[data-sensor="'+name+'"]').checked)continue;const sensor=history[keys[name]]||{};for(const field of ["temperatures","targets"]){const arr=sensor[field]||[];if(arr.length<2)continue;const points=arr.map((v,i)=>Number.isFinite(v)?(35+i*395/(arr.length-1))+","+y(v):null).filter(Boolean).join(" ");shape("polyline",{points,fill:"none",stroke:color,"stroke-width":1.5,"stroke-dasharray":field==="targets"?"4 4":"none"});}}};
controls.querySelectorAll("input").forEach(i=>i.onchange=drawHistory);drawHistory();
async function poll(){try{const r=await get("/telemetry");if(!r.status)throw Error("No status");lastStatus=r.status;const next=r.status.print_stats?.filename||"";if(next!==filename){filename=next;metadata=null;}ms.textContent="Moonraker ONLINE · "+new Date().toLocaleTimeString("en-GB");render(r.status);}catch(e){ms.textContent="Moonraker OFFLINE · retrying";lastStatus=null;metadata=null;enabled=false;updateStatus();clearLive();}finally{setTimeout(poll,2000);}}
async function pollMeta(){const name=filename;if(name&&lastStatus&&!metadata){try{const m=await get("/metadata?name="+encodeURIComponent(name));if(filename===name&&lastStatus){metadata=m;render(lastStatus);}}catch(e){}}setTimeout(pollMeta,5000);}
async function pollHistory(){try{history=await get("/history");hp.querySelector("strong").textContent="Temperature history · "+new Date().toLocaleTimeString("en-GB");}catch(e){history=null;hp.querySelector("strong").textContent="Temperature history · OFFLINE";}drawHistory();setTimeout(pollHistory,10000);}
poll();pollMeta();pollHistory();
}

updateStatus();
refreshScreen();
async function safetyPoll(){
 const el=document.getElementById("safety");
 try {const r=await fetch("/safety",{cache:"no-store",signal:AbortSignal.timeout(5000)});if(!r.ok)throw Error();const j=await r.json();el.textContent="Safety: "+j.reason+" | Physical touch locked (06E1)";}
 catch(e){el.textContent="Safety: status unavailable | Physical touch locked (06E1)";}
 finally{setTimeout(safetyPoll,3000);}
}
safetyPoll();
</script>
</body>
</html>
"""


def upstream(url):
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url, timeout=4) as r:
        data = r.read(4000000)
        return data

OBJECTS = "extruder&heater_bed&print_stats&virtual_sdcard&display_status&gcode_move&motion_report&fan&filament_switch_sensor%20filament_sensor&box_light&temperature_sensor%20Armv7%20mcu&temperature_sensor%20mcu_temp"
BASE = "http://127.0.0.1:7126"


def safety_check(status, ready=True):
    """Conservative eligibility only; never authorizes physical touch."""
    import math
    try:
        if ready is not True:
            return False, "Klipper not ready"
        state = status["print_stats"]["state"]
        if state not in ("standby", "complete", "cancelled"):
            return False, "Print state: " + str(state)
        if status["pause_resume"]["is_paused"] is not False or status["virtual_sdcard"]["is_active"] is not False:
            return False, "Print active or paused"
        for name in ("extruder", "heater_bed"):
            for key in ("target", "temperature", "power"):
                v = status[name][key]
                if type(v) not in (int, float) or not math.isfinite(v) or v < 0:
                    return False, "Invalid heater data"
            if status[name]["target"] != 0 or status[name]["power"] != 0:
                return False, "Heater active: " + name
            if status[name]["temperature"] > 40:
                return False, "Cooling down: " + name
        v = status["motion_report"]["live_velocity"]
        if type(v) not in (int,float) or not math.isfinite(v) or v != 0:
            return False, "Motion active or unknown"
        return True, "Idle and cool — eligibility only"
    except (KeyError, TypeError, ValueError):
        return False, "Incomplete printer status"


def safety_status():
    if DEMO:
        return False, "Offline demo"
    try:
        started = time.monotonic()
        info = json.loads(upstream(BASE + "/server/info"))["result"]
        status = json.loads(upstream(BASE + "/printer/objects/query?print_stats&pause_resume&virtual_sdcard&extruder&heater_bed&motion_report"))["result"]["status"]
        if time.monotonic() - started > 3:
            return False, "Status request too slow"
        return safety_check(status, info.get("klippy_connected") is True and info.get("klippy_state") == "ready")
    except Exception:
        return False, "Moonraker unavailable or invalid status"



class TouchAuthorization:
    """One-use, short-lived authorization for a simulated request only."""
    def __init__(self, check, clock=time.monotonic):
        self.check, self.clock = check, clock
        self.token = None
        self.deadline = 0
        self.lock = threading.Lock()

    def authorize(self):
        with self.lock:
            self.token = None
            ok, reason = self.check()
            if not ok:
                return None, reason
            self.token = secrets.token_hex(32)
            self.deadline = self.clock() + 3
            return self.token, "Simulation authorized"

    def submit(self, token, x, y):
        with self.lock:
            expected, self.token = self.token, None
            if not expected or not isinstance(token, str) or not secrets.compare_digest(expected.encode(), token.encode("utf-8", errors="replace")) or self.clock() >= self.deadline:
                return False, "Authorization invalid or expired"
            if type(x) is not int or type(y) is not int or not (0 <= x < WIDTH and 0 <= y < HEIGHT):
                return False, "Invalid coordinates"
            ok, reason = self.check()
            if not ok or self.clock() >= self.deadline:
                return False, reason if not ok else "Authorization expired"
            return True, "SIMULATION ONLY: %d,%d" % (x,y)


def authorization_self_test():
    now = [0]
    state = [True]
    a = TouchAuthorization(lambda: (state[0], "Mock status"), lambda: now[0])
    def verify(name, condition):
        if not condition:
            raise RuntimeError(name)
        print("PASS", name)
    verify("No authorization", not a.submit(None, 1, 1)[0])
    token, _ = a.authorize()
    verify("Valid simulated touch", a.submit(token, 240, 136)[0])
    verify("Replay blocked", not a.submit(token, 240, 136)[0])
    token, _ = a.authorize()
    verify("Wrong token", not a.submit("wrong", 1, 1)[0])
    for x,y in [(-1,0),(480,0),(0,272),(True,0),(1.5,0)]:
        token, _ = a.authorize()
        verify("Invalid coordinates %r,%r" % (x,y), not a.submit(token,x,y)[0])
    token, _ = a.authorize()
    now[0] += 3
    verify("Expired token", not a.submit(token,1,1)[0])
    token, _ = a.authorize()
    state[0] = False
    verify("Status changed before touch", not a.submit(token,1,1)[0])
    verify("Unsafe authorization denied", a.authorize()[0] is None)
    state[0] = True
    verify("Recovery requires new authorization", not a.submit(token,1,1)[0])


# Demo authorization is intentionally independent of printer safety: no hardware action exists.
DEMO_AUTH = TouchAuthorization(lambda: (True, "Demo only"))
LIVE_AUTH = TouchAuthorization(safety_status)

class RemoteTouchHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.headers.get("Host") not in ("localhost:%d" % self.server.server_port, "127.0.0.1:%d" % self.server.server_port):
            return self.send_error(403)

        path = self.path.split("?")[0]

        if path == "/":

            data = HTML.replace("__DEMO__", "true" if DEMO else "false").replace("__API_KEY__", API_KEY)
            if DEMO:
                data = data.replace("Virtual Touch Bridge (DEV Build 06E1)", "OFFLINE DEMO — Interactive Simulation — no printer connection")
            data = data.encode("utf-8")

            self.send_response(200)
            self.send_header(
                "Content-Type", "text/html; charset=utf-8"
            )
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", len(data))
            self.end_headers()
            self.wfile.write(data)

        elif path == "/safety":
            eligible, reason = safety_status()
            data = json.dumps({"eligible": eligible, "reason": reason, "physical_touch": False}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        elif path in ("/telemetry", "/history", "/metadata", "/thumbnail") and not DEMO:
            try:
                if path == "/telemetry":
                    url = BASE + "/printer/objects/query?" + OBJECTS
                elif path == "/history":
                    url = BASE + "/server/temperature_store"
                else:
                    q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                    name = q.get("name", [""])[0]
                    if not name or ".." in name.split("/") or name.startswith("/") or "\\" in name:
                        raise ValueError("Invalid filename")
                    if path == "/metadata":
                        url = BASE + "/server/files/metadata?" + urllib.parse.urlencode({"filename":name})
                    else:
                        if not name.lower().endswith(".png"):
                            raise ValueError("Invalid thumbnail")
                        url = BASE + "/server/files/gcodes/" + urllib.parse.quote(name, safe="/")
                data = upstream(url)
                self.send_response(200)
                self.send_header("Content-Type", "image/png" if path == "/thumbnail" else "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception:
                self.send_error(502, "Upstream unavailable")
        elif path == "/screen.png":

            try:
                data = capture_screen() if DEMO else upstream("http://127.0.0.1:8765/screen.png")

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
        def reply(code, reason, **extra):
            data = json.dumps(dict(reason=reason, **extra)).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        port = self.server.server_port
        if self.headers.get("Host") not in ("localhost:%d" % port, "127.0.0.1:%d" % port) or self.headers.get("Origin") not in ("http://localhost:%d" % port, "http://127.0.0.1:%d" % port) or not secrets.compare_digest(self.headers.get("X-Simulation-Key", "").encode("utf-8"), API_KEY.encode()):
            return reply(403, "Unauthorized request")
        if self.path not in ("/api/demo/authorize", "/api/demo/submit", "/api/eligibility"):
            return reply(403, "Physical touch locked")
        try:
            self.connection.settimeout(3)
            if self.headers.get("Transfer-Encoding") or len(self.headers.get_all("Content-Length", [])) != 1:
                raise ValueError()
            n = int(self.headers.get("Content-Length", "0"))
            if not 1 <= n <= 512 or self.headers.get("Content-Type") != "application/json":
                raise ValueError()
            raw = self.rfile.read(n)
            if len(raw) != n: raise ValueError()
            body = json.loads(raw)
            if not isinstance(body, dict): raise ValueError()
        except (ValueError, TypeError, OSError):
            return reply(400, "Invalid request")
        if self.path == "/api/eligibility":
            token, reason = LIVE_AUTH.authorize()
            # Never expose a live authorization token in this build.
            return reply(200 if token else 403, reason + " | physical touch locked")
        if self.path == "/api/demo/authorize":
            token, reason = DEMO_AUTH.authorize()
            return reply(200, reason, token=token)
        ok, reason = DEMO_AUTH.submit(body.get("token"), body.get("x"), body.get("y"))
        print(time.strftime("%H:%M:%S"), "PASS" if ok else "DENIED", reason, flush=True)
        return reply(200 if ok else 403, reason)

    def log_message(self, format, *args):
        pass


def api_test():
    import http.client
    from concurrent.futures import ThreadPoolExecutor
    global DEMO
    DEMO = True
    server = ThreadingHTTPServer((HOST, 0), RemoteTouchHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_port
    def req(path, body=None, key=API_KEY, origin=None, host=None, method="POST"):
        c = http.client.HTTPConnection(HOST, port, timeout=6)
        headers = {"Origin": origin or "http://127.0.0.1:%d" % port, "X-Simulation-Key": key, "Content-Type":"application/json"}
        if host: headers["Host"] = host
        try:
            c.request(method, path, body=json.dumps(body) if not isinstance(body, bytes) else body, headers=headers)
            r=c.getresponse(); raw=r.read()
            try: data=json.loads(raw)
            except ValueError: data={}
            return r.status,data
        finally: c.close()
    def verify(name, condition):
        if not condition: raise RuntimeError(name)
        print("PASS",name)
    def token(): return req("/api/demo/authorize",{})[1]["token"]
    def submit(t,x=240,y=136): return req("/api/demo/submit",dict(token=t,x=x,y=y))[0]
    try:
        verify("Missing authorization",submit(None)==403)
        verify("Wrong API key",req("/api/demo/authorize",{},key="wrong")[0]==403)
        verify("Foreign origin",req("/api/demo/authorize",{},origin="http://example.invalid")[0]==403)
        verify("Foreign host GET",req("/",method="GET",host="example.invalid")[0]==403)
        t=token(); verify("Valid simulation",submit(t)==200)
        verify("Replay blocked",submit(t)==403)
        verify("Unicode token rejected",submit("é")==403)
        verify("Invalid coordinates",submit(token(),480,0)==403)
        verify("Malformed JSON",req("/api/demo/submit",b"{")[0]==400)
        verify("Non-object JSON",req("/api/demo/submit",[])[0]==400)
        verify("Oversized request",req("/api/demo/submit",b"x"*513)[0]==400)
        verify("Unknown endpoint",req("/api/unknown",{})[0]==403)
        verify("Physical touch locked",req("/touch",{})[0]==403)
        verify("Offline eligibility denied",req("/api/eligibility",{})[0]==403)
        t=token(); time.sleep(3.1); verify("Expired token",submit(t)==403)
        t=token()
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(lambda _:submit(t),range(4)))
        verify("Concurrent replay blocked",sorted(results)==[200,403,403,403])
        verify("Recovery requires new token",submit(token())==200)
        print("API TEST COMPLETE: 17/17")
    finally:
        server.shutdown(); server.server_close(); thread.join()


class VirtualTouchBridge:
    """Offline-only bridge. Destination is an owned ephemeral mock server."""
    def __init__(self, server, check):
        self.server = server
        self.auth = TouchAuthorization(check)
        self.armed = False
        self.lock = threading.Lock()

    def arm(self):
        with self.lock:
            self.armed = True

    def authorize(self):
        with self.lock:
            return self.auth.authorize()[0] if self.armed else None

    def submit(self, token, x, y):
        import http.client
        with self.lock:
            if not self.armed:
                return False
            ok, _ = self.auth.submit(token, x, y)
            if not ok:
                self.armed = False
                return False
            c = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=0.4)
            try:
                c.request('POST', '/touch', json.dumps({'x':x,'y':y}), {
                    'Content-Type':'application/json', 'X-Touch-Token':self.server.mock_token,
                    'Origin':'http://127.0.0.1:%d' % self.server.server_port})
                r = c.getresponse()
                if r.status == 200 and r.read(3) == b'OK':
                    return True
            except (OSError, http.client.HTTPException):
                pass
            finally:
                c.close()
            self.armed = False
            return False


def bridge_test():
    import socket
    from concurrent.futures import ThreadPoolExecutor
    class MockHandler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_POST(self):
            s = self.server
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            valid = (self.path == '/touch' and self.headers.get('X-Touch-Token') == s.expected_token
                     and self.headers.get('Origin') == 'http://127.0.0.1:%d' % s.server_port)
            if valid:
                s.events.append((data['x'],data['y']))
            if s.mode == 'timeout': time.sleep(0.8)
            if s.mode == 'disconnect':
                self.connection.shutdown(socket.SHUT_RDWR)
                return
            body = b'BAD' if s.mode == 'bad' else b'OK'
            try:
                self.send_response(200 if valid and s.mode != 'reject' else 403)
                self.send_header('Content-Length',str(len(body)))
                self.end_headers(); self.wfile.write(body)
            except OSError: pass
    s = ThreadingHTTPServer(('127.0.0.1',0),MockHandler)
    s.mock_token = s.expected_token = secrets.token_hex(32)
    s.events=[]; s.mode='normal'
    t=threading.Thread(target=s.serve_forever,daemon=True); t.start()
    state=[True]; b=VirtualTouchBridge(s,lambda:(state[0],'Mock safety status'))
    count=0
    def verify(name, ok):
        nonlocal count
        if not ok: raise RuntimeError(name)
        count+=1; print('PASS',name)
    def fresh(): b.arm(); return b.authorize()
    try:
        verify('Initially locked',b.authorize() is None)
        verify('Coordinate transfer',b.submit(fresh(),240,136) and s.events==[(240,136)])
        token=fresh(); verify('One-use token',b.submit(token,0,0) and not b.submit(token,0,0) and len(s.events)==2)
        verify('Replay locks bridge',b.authorize() is None)
        verify('Wrong authorization',not b.submit('wrong',1,1))
        token=fresh(); verify('Invalid coordinates',not b.submit(token,480,0) and len(s.events)==2)
        token=fresh(); state[0]=False; verify('State changed before submit',not b.submit(token,1,1) and len(s.events)==2)
        verify('Unsafe authorization denied',fresh() is None); state[0]=True
        token=fresh(); b.auth.deadline=0; verify('Expired authorization',not b.submit(token,1,1))
        s.expected_token='rotated'; verify('Legacy token rejected',not b.submit(fresh(),1,1) and len(s.events)==2); s.expected_token=s.mock_token
        for mode in ('reject','bad','timeout','disconnect'):
            s.mode=mode; before=len(s.events)
            verify(mode+' locks without retry',not b.submit(fresh(),1,1) and not b.armed and len(s.events)==before+1)
        s.mode='normal'; verify('Recovery remains locked',b.authorize() is None)
        token=fresh(); before=len(s.events)
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(lambda _:b.submit(token,479,271),range(4)))
        verify('Concurrent replay blocked',sum(results)==1 and len(s.events)==before+1)
        verify('Explicit rearm recovers',b.submit(fresh(),1,1))
    finally:
        s.shutdown(); s.server_close(); t.join()
    verify('Stopped mock server fails closed',not b.submit(fresh(),1,1) and not b.armed)
    print('BRIDGE TEST COMPLETE: %d/18' % count)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="Offline simulated framebuffer; real touch blocked")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--api-test", action="store_true")
    parser.add_argument("--bridge-test", action="store_true")
    args = parser.parse_args()
    if args.bridge_test:
        if args.live or args.demo or args.self_test or args.api_test: parser.error("Use --bridge-test alone")
        bridge_test()
        raise SystemExit(0)
    if args.api_test:
        if args.live or args.demo or args.self_test: parser.error("Use --api-test alone")
        api_test()
        raise SystemExit(0)
    if args.self_test:
        import copy
        base = {"print_stats":{"state":"standby"}, "pause_resume":{"is_paused":False}, "virtual_sdcard":{"is_active":False}, "extruder":{"target":0,"temperature":25,"power":0}, "heater_bed":{"target":0,"temperature":25,"power":0}, "motion_report":{"live_velocity":0}}
        cases = [("Idle", None, None, None, True), ("Printing","print_stats","state","printing",False), ("Paused","pause_resume","is_paused",True,False), ("Active SD","virtual_sdcard","is_active",True,False), ("Target","extruder","target",225,False), ("Power","heater_bed","power",0.1,False), ("Hot","extruder","temperature",41,False), ("Motion","motion_report","live_velocity",1,False), ("Unknown","print_stats","state","unknown",False), ("Invalid","heater_bed","temperature",float("nan"),False)]
        for name,obj,key,val,expected in cases:
            data=copy.deepcopy(base)
            if obj: data[obj][key]=val
            assert safety_check(data)[0] is expected, name
            print("PASS",name)
        assert not safety_check({})[0]
        assert not safety_check(base,False)[0]
        print("PASS Missing status; PASS Klipper not ready")
        authorization_self_test()
        return_code = 0
        raise SystemExit(return_code)
    if args.demo == args.live:
        parser.error("Choose --demo or --live")
    DEMO = args.demo
    PORT = 8766
    server = ThreadingHTTPServer(
        (HOST, PORT),
        RemoteTouchHandler
    )

    print("=" * 48)
    print("FLSUN T1 Pro Remote Touch V0.3.0")
    print("Mode:", "OFFLINE DEMO" if DEMO else "LIVE MONITORING", "- simulated touch only; simulation API only; physical touch blocked")
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
