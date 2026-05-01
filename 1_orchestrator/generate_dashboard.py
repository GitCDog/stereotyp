#!/usr/bin/env python3
"""Generiert dashboard.html für das Stereotypen-Projekt."""

import csv
from pathlib import Path

with open("1_input/1_input_file.txt", encoding="utf-8") as f:
    data = [r for r in csv.DictReader(f) if r.get("nr", "").strip()]

total = len(data)
story_done  = sum(1 for r in data if r.get("status_story")  == "X")
caption_done = sum(1 for r in data if r.get("status_caption") == "X")
audio_done  = sum(1 for r in data if r.get("status_audio")  == "X")
pic_done    = sum(1 for r in data if r.get("status_pic")    == "X")
video_done  = sum(1 for r in data if r.get("status_video")  == "X")
posted_done = sum(1 for r in data if r.get("insta_post")    == "X")

steps = story_done + caption_done + audio_done + pic_done + video_done
percent = round((steps / (total * 5)) * 100) if total else 0


def ck(status): return "✓" if status == "X" else "○"
def col(status): return "color: #28a745;" if status == "X" else "color: #ccc;"


rows_html = ""
for row in data:
    nr        = row.get("nr", "")
    stereo    = row.get("stereotyp", "")
    sec       = row.get("seconds", "")
    insta     = row.get("insta_post", "")
    insta_cls = "active" if insta == "X" else ""
    insta_lbl = "✓ Gepostet" if insta == "X" else "Post"
    vid_done  = row.get("status_video", "") == "X"

    rows_html += f"""                <tr>
                    <td class="num">{nr}</td>
                    <td class="name">{stereo}</td>
                    <td class="status-cell" style="{col(row.get('status_story',''))}">{ck(row.get('status_story',''))}</td>
                    <td class="status-cell" style="{col(row.get('status_caption',''))}">{ck(row.get('status_caption',''))}</td>
                    <td class="status-cell" style="{col(row.get('status_audio',''))}">{ck(row.get('status_audio',''))}</td>
                    <td class="center">{sec}</td>
                    <td class="status-cell" style="{col(row.get('status_pic',''))}">{ck(row.get('status_pic',''))}</td>
                    <td class="status-cell" style="{col(row.get('status_video',''))}">{ck(row.get('status_video',''))}</td>
                    <td class="center">
                        <button class="insta-btn {insta_cls}" data-nr="{nr}" onclick="togglePost(this)" {"" if vid_done else "disabled"}>{insta_lbl}</button>
                    </td>
                </tr>
"""

html = f'''<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stereotypen Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #e8120a 0%, #000 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        .header {{
            background: white;
            padding: 25px 30px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.15);
        }}
        h1 {{
            color: #111;
            font-size: 26px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
            margin-bottom: 20px;
        }}
        .btn-group {{ display: flex; gap: 8px; flex-wrap: wrap; }}
        .action-btn {{
            background: #e8120a;
            color: white;
            border: none;
            padding: 9px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 600;
            transition: all 0.2s;
        }}
        .action-btn:hover {{ background: #c00e08; transform: scale(1.04); }}
        .action-btn:active {{ transform: scale(0.97); }}
        .action-btn.running {{ opacity: 0.65; cursor: not-allowed; }}
        .action-btn.disabled {{ background: #888; color: #ccc; cursor: not-allowed; }}
        .action-btn.disabled:hover {{ background: #888; transform: none; }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 12px;
            margin-bottom: 20px;
        }}
        .stat-box {{
            background: #f8f9fa;
            padding: 14px;
            border-radius: 8px;
            border-left: 4px solid #e8120a;
        }}
        .stat-box h3 {{ font-size: 10px; color: #666; text-transform: uppercase; font-weight: 700; margin-bottom: 6px; }}
        .stat-box .val {{ font-size: 26px; font-weight: bold; color: #28a745; }}
        .progress-section {{ margin-bottom: 5px; }}
        .progress-bar {{
            background: #e9ecef;
            border-radius: 4px;
            height: 28px;
            overflow: hidden;
            margin-top: 8px;
        }}
        .progress-fill {{
            background: linear-gradient(90deg, #28a745, #20c997);
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            width: {percent}%;
            min-width: {percent}%;
            transition: width 0.4s;
        }}
        .log-box {{
            display: none;
            margin-top: 15px;
            padding: 12px;
            background: #f8f9fa;
            border-radius: 6px;
            font-size: 13px;
        }}
        .log-box.visible {{ display: block; }}
        .log-progress {{
            background: #e9ecef;
            border-radius: 4px;
            height: 24px;
            overflow: hidden;
            margin: 8px 0;
        }}
        .log-fill {{
            background: linear-gradient(90deg, #e8120a, #000);
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            transition: width 0.3s;
        }}
        .log-msg {{ font-size: 12px; color: #555; text-align: center; }}
        .pic-input {{
            display: none;
            margin-top: 12px;
            padding: 12px;
            background: #f8f9fa;
            border-radius: 6px;
        }}
        .pic-input label {{ display: block; font-weight: 600; margin-bottom: 8px; }}
        .pic-input input {{
            padding: 7px; border: 1px solid #ddd; border-radius: 4px;
            font-size: 14px; width: 160px;
        }}
        .pic-input button {{
            margin-left: 8px; padding: 7px 14px;
            background: #e8120a; color: white; border: none;
            border-radius: 4px; cursor: pointer; font-weight: bold;
        }}
        .table-container {{
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow: hidden;
            height: 700px;
            display: flex;
            flex-direction: column;
        }}
        .table-scroll {{ overflow-y: auto; flex: 1; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
        thead {{ background: #e8120a; color: white; position: sticky; top: 0; z-index: 10; }}
        th {{ padding: 11px 8px; text-align: left; font-weight: 600; white-space: nowrap; }}
        td {{ padding: 9px 8px; border-bottom: 1px solid #eee; }}
        tr:hover {{ background: #fff5f5; }}
        .num {{ font-weight: bold; color: #e8120a; width: 35px; text-align: center; }}
        .name {{ min-width: 220px; font-weight: 500; }}
        .status-cell {{ text-align: center; width: 35px; font-size: 17px; font-weight: bold; }}
        .center {{ text-align: center; }}
        .insta-btn {{
            background: #e9ecef; border: none; padding: 5px 11px;
            border-radius: 4px; cursor: pointer; font-weight: bold;
            color: #666; transition: all 0.2s;
        }}
        .insta-btn:hover {{ background: #dee2e6; }}
        .insta-btn.active {{ background: #28a745; color: white; }}
        .insta-btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}
        ::-webkit-scrollbar {{ width: 8px; }}
        ::-webkit-scrollbar-track {{ background: #f1f1f1; }}
        ::-webkit-scrollbar-thumb {{ background: #e8120a; border-radius: 4px; }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>
            <span>🇩🇪 Stereotypen Dashboard</span>
            <div class="btn-group">
                <button class="action-btn disabled" id="storyBtn"   onclick="showInput('story')">✍️ Story generieren</button>
                <button class="action-btn disabled" id="captionBtn" onclick="showInput('caption')">💬 Caption generieren</button>
                <button class="action-btn disabled" id="picBtn"     onclick="showInput('picture')">🖼️ Bild generieren</button>
                <button class="action-btn" id="audioBtn"   onclick="showInput('audio')">🎵 Audio generieren</button>
                <button class="action-btn" id="videoBtn"   onclick="showInput('video')">🎬 Video erstellen</button>
                <button class="action-btn" id="postBtn"    onclick="runDirect('post')">📤 Instagram Post</button>
                <button class="action-btn" id="gptBtn"     onclick="runDirect('gpt')">📝 GPT Prompts</button>
                <button class="action-btn" id="refreshBtn" onclick="doRefresh()">🔄 Refresh</button>
            </div>
        </h1>

        <div class="stats">
            <div class="stat-box"><h3>Gesamt</h3><div class="val">{total}</div></div>
            <div class="stat-box"><h3>Story ✓</h3><div class="val">{story_done}</div></div>
            <div class="stat-box"><h3>Caption ✓</h3><div class="val">{caption_done}</div></div>
            <div class="stat-box"><h3>Audio ✓</h3><div class="val">{audio_done}</div></div>
            <div class="stat-box"><h3>Bild ✓</h3><div class="val">{pic_done}</div></div>
            <div class="stat-box"><h3>Video ✓</h3><div class="val">{video_done}</div></div>
            <div class="stat-box"><h3>Gepostet ✓</h3><div class="val">{posted_done}</div></div>
        </div>

        <div class="progress-section">
            <strong>Gesamtfortschritt ({percent}%)</strong>
            <div class="progress-bar">
                <div class="progress-fill">{percent}%</div>
            </div>
        </div>

        <div class="pic-input" id="actionInputDiv">
            <label id="actionLabel"></label>
            <input type="text" id="actionInput" placeholder="z.B. 5 | 1-10 | 100_01 | leer = alle ausstehenden"
                   onkeydown="if(event.key==='Enter') startAction()">
            <button onclick="startAction()">Starten</button>
        </div>

        <div class="log-box" id="logBox">
            <strong id="logTitle">Verarbeitung...</strong>
            <div class="log-progress">
                <div class="log-fill" id="logFill" style="width:0%">0%</div>
            </div>
            <div class="log-msg" id="logMsg">Starte...</div>
        </div>
    </div>

    <div class="table-container">
        <div class="table-scroll">
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Stereotyp</th>
                        <th title="Story-Text">Text</th>
                        <th title="Caption">Caption</th>
                        <th title="Audio">Audio</th>
                        <th>Sek.</th>
                        <th title="Bild">Bild</th>
                        <th title="Video">Video</th>
                        <th title="Instagram">Post</th>
                    </tr>
                </thead>
                <tbody>
{rows_html}                </tbody>
            </table>
        </div>
    </div>
</div>

<script>
    const ACTIONS = {{
        'story':   {{ btn: 'storyBtn',   api: '/api/generate-story',   label: '✍️ Story generieren'  }},
        'caption': {{ btn: 'captionBtn', api: '/api/generate-caption', label: '💬 Caption generieren' }},
        'picture': {{ btn: 'picBtn',     api: '/api/generate-picture', label: '🖼️ Bild generieren'   }},
        'audio':   {{ btn: 'audioBtn',   api: '/api/generate-audio',   label: '🎵 Audio generieren'  }},
        'video':   {{ btn: 'videoBtn',   api: '/api/generate-video',   label: '🎬 Video erstellen'   }},
        'post':    {{ btn: 'postBtn',    api: '/api/instagram-post',      label: '📤 Instagram Post'    }},
        'gpt':     {{ btn: 'gptBtn',     api: '/api/generate-gpt-prompt', label: '📝 GPT Prompts'        }},
    }};

    let _pendingAction = null;

    function showInput(type) {{
        const div = document.getElementById('actionInputDiv');
        if (_pendingAction === type && div.style.display === 'block') {{
            div.style.display = 'none';
            _pendingAction = null;
            return;
        }}
        _pendingAction = type;
        document.getElementById('actionLabel').textContent =
            ACTIONS[type].label + ' – Nummer oder Bereich (leer = alle ausstehenden):';
        document.getElementById('actionInput').value = '';
        div.style.display = 'block';
        document.getElementById('actionInput').focus();
    }}

    async function startAction() {{
        if (!_pendingAction) return;
        const type = _pendingAction;
        const cfg = ACTIONS[type];
        const val = document.getElementById('actionInput').value.trim();
        document.getElementById('actionInputDiv').style.display = 'none';
        _pendingAction = null;
        await _launch(cfg, val);
    }}

    async function runDirect(type) {{
        await _launch(ACTIONS[type], '');
    }}

    async function _launch(cfg, val) {{
        const btn = document.getElementById(cfg.btn);
        btn.classList.add('running');
        btn.disabled = true;
        document.getElementById('logBox').classList.add('visible');
        document.getElementById('logTitle').textContent = cfg.label;
        setLog(5, val ? `Starte für ${{val}}...` : 'Starte...');
        try {{
            const resp = await fetch(cfg.api, {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{story: val}})
            }});
            if (resp.ok) pollProgress(btn, cfg.label);
            else resetBtn(btn, cfg.label);
        }} catch(e) {{
            resetBtn(btn, cfg.label);
        }}
    }}

    function setLog(pct, msg) {{
        document.getElementById('logFill').style.width = pct + '%';
        document.getElementById('logFill').textContent = pct + '%';
        document.getElementById('logMsg').textContent = msg;
    }}

    function resetBtn(btn, label) {{
        btn.classList.remove('running');
        btn.disabled = false;
        document.getElementById('logBox').classList.remove('visible');
    }}

    function pollProgress(btn, label) {{
        let pct = 5;
        const interval = setInterval(async () => {{
            try {{
                const resp = await fetch('/api/progress');
                const data = await resp.json();
                setLog(data.percent || pct, data.message || '...');
                if (data.status === 'complete' || data.status === 'error') {{
                    clearInterval(interval);
                    if (data.status === 'complete') {{
                        setLog(100, 'Fertig! Lade Dashboard neu...');
                        setTimeout(() => location.reload(), 1500);
                    }} else {{
                        resetBtn(btn, label);
                    }}
                }} else {{
                    pct = Math.min(pct + 10, 90);
                }}
            }} catch(e) {{
                pct = Math.min(pct + 5, 90);
                setLog(pct, 'Verarbeitung läuft...');
            }}
        }}, 2000);
    }}

    async function doRefresh() {{
        const btn = document.getElementById('refreshBtn');
        btn.textContent = '⏳ Scanne...';
        btn.disabled = true;
        try {{ await fetch('/api/refresh', {{ method: 'POST' }}); }} catch(e) {{}}
        location.reload();
    }}

    async function togglePost(btn) {{
        if (btn.classList.contains('active')) return;
        const nr = btn.getAttribute('data-nr');
        btn.disabled = true;
        btn.textContent = '...';
        try {{
            const resp = await fetch('/api/mark-posted', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{nr}})
            }});
            if (resp.ok) {{
                btn.classList.add('active');
                btn.textContent = '✓ Gepostet';
            }} else {{
                btn.textContent = 'Fehler';
                setTimeout(() => {{ btn.textContent = 'Post'; btn.disabled = false; }}, 2000);
            }}
        }} catch(e) {{
            btn.textContent = 'Fehler';
            setTimeout(() => {{ btn.textContent = 'Post'; btn.disabled = false; }}, 2000);
        }}
    }}
</script>
</body>
</html>'''

Path("dashboard.html").write_text(html, encoding="utf-8")
print(f"[+] dashboard.html generiert")
print(f"[+] Story: {story_done}/{total} | Audio: {audio_done}/{total} | Bild: {pic_done}/{total} | Video: {video_done}/{total} | Gepostet: {posted_done}/{total}")
print(f"[+] Fortschritt: {percent}%")
