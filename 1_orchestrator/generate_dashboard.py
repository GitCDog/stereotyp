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

pie_posted    = posted_done
pie_ready     = video_done - posted_done
pie_incomplete = total - video_done

# Reihenfolge-Daten laden – beide Formate ("0182" und "182") als Keys
nr_to_stereotyp = {}
for r in data:
    raw = r.get("nr", "").strip()
    name = r.get("stereotyp", "").strip()
    nr_to_stereotyp[raw] = name
    try:
        nr_to_stereotyp[str(int(raw))] = name  # ohne führende Null
    except ValueError:
        pass
reihenfolge_nrs = []
reihenfolge_path = Path("1_input/0_reihenfolge.txt")
if reihenfolge_path.exists():
    reihenfolge_nrs = [l.strip() for l in reihenfolge_path.read_text(encoding="utf-8").splitlines() if l.strip()]

# Lookup: normalisierte nr → Position (1-basiert)
reihenfolge_pos = {}
for i, rq_nr in enumerate(reihenfolge_nrs, 1):
    reihenfolge_pos[rq_nr] = i
    try:
        reihenfolge_pos[str(int(rq_nr))] = i   # ohne führende Null
        reihenfolge_pos[f"{int(rq_nr):04d}"] = i  # mit führender Null
    except ValueError:
        pass

reihenfolge_rows_html = ""
if reihenfolge_nrs:
    for i, nr in enumerate(reihenfolge_nrs, 1):
        name = nr_to_stereotyp.get(nr, nr_to_stereotyp.get(nr.lstrip("0"), "—"))
        reihenfolge_rows_html += f'<tr><td class="rq-pos">{i}</td><td class="rq-nr">#{nr}</td><td class="rq-name">{name}</td></tr>\n'
else:
    reihenfolge_rows_html = '<tr><td colspan="3" class="rq-empty">Reihenfolge ist leer</td></tr>'

# nr→stereotyp als JSON für JS-Lookup
import json as _json
nr_lookup_json = _json.dumps(nr_to_stereotyp)


def block(status):
    if status == "X":
        return '<span class="blk blk-green"></span>'
    return '<span class="blk blk-yellow"></span>'


rows_html = ""
for row in data:
    nr        = row.get("nr", "")
    stereo    = row.get("stereotyp", "")
    sec       = row.get("seconds", "")
    insta     = row.get("insta_post", "")
    yt        = row.get("youtube_post", "")
    insta_cls = "active" if insta == "X" else ""
    insta_lbl = "✓ Gepostet" if insta == "X" else "Post"
    vid_done  = row.get("status_video", "") == "X"
    audio_ok  = row.get("status_audio", "") == "X"
    pic_ok    = row.get("status_pic", "") == "X"
    if insta == "X":
        row_cls = ' class="row-posted"'
    elif vid_done:
        row_cls = ' class="row-ready"'
    elif not audio_ok or not pic_ok or not vid_done:
        row_cls = ' class="row-incomplete"'
    else:
        row_cls = ""
    rq_pos    = reihenfolge_pos.get(nr, reihenfolge_pos.get(str(int(nr)) if nr.isdigit() else nr, None))

    rows_html += f"""                <tr{row_cls}>
                    <td class="num">{nr}</td>
                    <td class="name">{stereo} <span class="eye-btn" data-nr="{nr}" onmouseenter="showStory(this)" onmouseleave="hideStory()">👁</span></td>
                    <td class="status-cell">{block(row.get('status_story',''))}</td>
                    <td class="status-cell">{block(row.get('status_caption',''))}</td>
                    <td class="status-cell">{block(row.get('status_audio',''))}</td>
                    <td class="center">{sec}</td>
                    <td class="status-cell">{block(row.get('status_pic',''))}</td>
                    <td class="status-cell">{block(row.get('status_video',''))}</td>
                    <td class="status-cell">{block(yt)}</td>
                    <td class="center" style="white-space:nowrap;">
                        <button class="insta-btn {insta_cls}" data-nr="{nr}" onclick="togglePost(this)" {"" if vid_done else "disabled"}>{insta_lbl}</button>
                        <button class="queue-btn" data-nr="{nr}" onclick="openQueueModal(this)" title="In Reihenfolge einreihen">☰</button>
                    </td>
                    <td class="center rq-col" data-nr="{nr}">{f'<span class="rq-badge">{rq_pos}</span>' if rq_pos else ''}</td>
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
            margin-bottom: 10px;
        }}
        .btn-group {{ display: flex; gap: 8px; flex-wrap: wrap; }}
        .btn-row {{ margin-bottom: 8px; }}
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
        .log-list {{
            margin-top: 10px;
            max-height: 200px;
            overflow-y: auto;
            font-size: 12px;
            font-family: monospace;
            background: #fff;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 6px 10px;
            display: none;
        }}
        .log-list.visible {{ display: block; }}
        .log-list div {{ padding: 2px 0; border-bottom: 1px solid #f0f0f0; }}
        .log-list div:last-child {{ border-bottom: none; }}
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
        .status-cell {{ text-align: center; width: 35px; }}
        .blk {{ display: inline-block; width: 16px; height: 16px; border-radius: 3px; vertical-align: middle; }}
        .blk-green {{ background: #28a745; }}
        .blk-yellow {{ background: #ffc107; }}
        tr.row-posted {{ background: #1a4d2e; color: #c8f5d8; }}
        tr.row-posted:hover {{ background: #245c38; }}
        tr.row-posted td {{ color: #c8f5d8; }}
        tr.row-ready {{ background: #d4f5e2; }}
        tr.row-ready:hover {{ background: #baefd1; }}
        tr.row-incomplete {{ background: #fff8d6; }}
        tr.row-incomplete:hover {{ background: #fff0a0; }}
        .pie-section {{
            display: flex;
            align-items: center;
            gap: 24px;
            background: white;
            padding: 18px 24px;
            border-radius: 10px;
            margin-bottom: 16px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            flex-wrap: wrap;
        }}
        .pie-legend {{ display: flex; flex-direction: column; gap: 10px; }}
        .legend-item {{ display: flex; align-items: center; gap: 10px; font-size: 14px; font-weight: 600; }}
        .legend-dot {{ width: 16px; height: 16px; border-radius: 3px; flex-shrink: 0; }}
        .center {{ text-align: center; }}
        .insta-btn {{
            background: #e9ecef; border: none; padding: 5px 11px;
            border-radius: 4px; cursor: pointer; font-weight: bold;
            color: #666; transition: all 0.2s;
        }}
        .insta-btn:hover {{ background: #dee2e6; }}
        .insta-btn.active {{ background: #28a745; color: white; }}
        .insta-btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}
        .rq-col {{ width: 48px; }}
        .rq-badge {{
            display: inline-block;
            background: #e8120a; color: white;
            font-size: 11px; font-weight: 700;
            border-radius: 10px; padding: 2px 7px;
            min-width: 22px; text-align: center;
        }}
        ::-webkit-scrollbar {{ width: 8px; }}
        ::-webkit-scrollbar-track {{ background: #f1f1f1; }}
        ::-webkit-scrollbar-thumb {{ background: #e8120a; border-radius: 4px; }}
        .new-story-card {{
            background: #fff8f8;
            border: 2px solid #e8120a;
            border-radius: 10px;
            padding: 16px 18px;
            margin-top: 14px;
        }}
        .new-story-card h3 {{
            font-size: 14px; font-weight: 700; color: #e8120a;
            margin-bottom: 12px;
        }}
        .new-story-fields {{
            display: flex; gap: 10px; flex-wrap: wrap; align-items: flex-end;
        }}
        .new-story-field {{
            display: flex; flex-direction: column; gap: 4px; flex: 1; min-width: 160px;
        }}
        .new-story-field label {{
            font-size: 11px; font-weight: 700; color: #555; text-transform: uppercase; letter-spacing: 0.5px;
        }}
        .new-story-field input {{
            padding: 9px 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
            width: 100%;
        }}
        .new-story-field input:focus {{
            outline: none; border-color: #e8120a; box-shadow: 0 0 0 2px rgba(232,18,10,0.15);
        }}
        .new-story-submit {{
            background: #e8120a; color: white; border: none;
            padding: 9px 22px; border-radius: 6px; cursor: pointer;
            font-size: 14px; font-weight: 700; white-space: nowrap;
            align-self: flex-end;
        }}
        .new-story-submit:hover {{ background: #c00e08; }}
        .new-story-submit:disabled {{ background: #aaa; cursor: not-allowed; }}
        .new-story-field select {{
            padding: 9px 12px; border: 1px solid #ddd; border-radius: 6px;
            font-size: 14px; width: 100%; background: white;
        }}
        .new-story-field select:focus {{
            outline: none; border-color: #e8120a;
        }}
        .pos-custom {{ display: none; margin-top: 6px; }}
        .pos-custom input {{
            padding: 7px 10px; border: 1px solid #ddd; border-radius: 6px;
            font-size: 13px; width: 100%;
        }}
        .queue-btn {{
            background: #f0f0f0; border: 1px solid #ddd; padding: 3px 8px;
            border-radius: 4px; cursor: pointer; font-size: 11px; font-weight: 600;
            color: #555; white-space: nowrap;
        }}
        .queue-btn:hover {{ background: #e8120a; color: white; border-color: #e8120a; }}
        .queue-btn.in-queue {{ background: #28a745; color: white; border-color: #28a745; }}
        .eye-btn {{
            cursor: pointer; font-size: 12px; opacity: 0.35;
            margin-left: 5px; user-select: none;
            transition: opacity 0.15s;
        }}
        .eye-btn:hover {{ opacity: 1; }}
        #story-tooltip {{
            display: none; position: fixed; z-index: 9999;
            background: #1a1a1a; color: #f0f0f0;
            border: 1px solid #444; border-radius: 8px;
            padding: 12px 15px; max-width: 420px;
            font-size: 13px; line-height: 1.55;
            box-shadow: 0 6px 24px rgba(0,0,0,0.45);
            white-space: pre-wrap; pointer-events: none;
        }}
        .queue-modal {{
            display: none; position: fixed; top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0,0,0,0.5); z-index: 2000;
            justify-content: center; align-items: center;
        }}
        .queue-modal.visible {{ display: flex; }}
        .queue-inner {{
            background: white; border-radius: 12px; padding: 24px 28px;
            max-width: 360px; width: 90%;
            box-shadow: 0 8px 32px rgba(0,0,0,0.25);
        }}
        .queue-inner h3 {{ font-size: 15px; margin-bottom: 14px; color: #111; }}
        .queue-options {{ display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px; }}
        .queue-opt {{
            padding: 10px 14px; border: 2px solid #ddd; border-radius: 8px;
            cursor: pointer; font-size: 13px; font-weight: 600; color: #333;
            display: flex; align-items: center; gap: 8px;
        }}
        .queue-opt:hover {{ border-color: #e8120a; color: #e8120a; }}
        .queue-opt.remove {{ border-color: #dc3545; color: #dc3545; }}
        .queue-opt.remove:hover {{ background: #dc3545; color: white; }}
        .queue-pos-row {{ display: flex; gap: 8px; align-items: center; }}
        .queue-pos-row input {{
            flex: 1; padding: 9px 12px; border: 2px solid #ddd; border-radius: 8px;
            font-size: 14px;
        }}
        .queue-pos-row input:focus {{ outline: none; border-color: #e8120a; }}
        .queue-pos-btn {{
            background: #e8120a; color: white; border: none;
            padding: 9px 16px; border-radius: 8px; cursor: pointer;
            font-size: 13px; font-weight: 700;
        }}
        .queue-cancel {{
            background: none; border: none; color: #888; cursor: pointer;
            font-size: 12px; margin-top: 8px; width: 100%; text-align: center;
        }}
        .reihenfolge-card {{
            background: #fff8f8;
            border: 1px solid #f0c0c0;
            border-radius: 10px;
            padding: 14px 16px;
            margin-top: 14px;
        }}
        .reihenfolge-card h3 {{
            font-size: 13px; font-weight: 700; color: #c00;
            margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;
        }}
        .reihenfolge-card.saved {{
            border-color: #28a745;
            background: #f0fff4;
            transition: all 0.3s;
        }}
        .reihenfolge-table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
        .reihenfolge-table td {{ padding: 5px 8px; border-bottom: 1px solid #f0e0e0; }}
        .reihenfolge-table tr:last-child td {{ border-bottom: none; }}
        .rq-pos {{ width: 28px; font-weight: 700; color: #e8120a; text-align: center; }}
        .rq-nr {{ width: 40px; color: #999; text-align: center; }}
        .rq-name {{ font-weight: 500; color: #222; }}
        .rq-empty {{ color: #aaa; font-style: italic; font-size: 12px; padding: 6px 0; }}
        @media (max-width: 600px) {{
            .new-story-fields {{ flex-direction: column; }}
            .new-story-submit {{ width: 100%; padding: 12px; font-size: 16px; }}
            .new-story-field input, .new-story-field select {{ font-size: 16px; }}
        }}
        .server-status {{
            display: flex; align-items: center; gap: 8px;
            font-size: 12px; color: #555;
            background: #f0f0f0; border-radius: 20px;
            padding: 5px 12px; white-space: nowrap;
        }}
        .server-dot {{
            width: 8px; height: 8px; border-radius: 50%;
            background: #ccc; flex-shrink: 0;
        }}
        .server-dot.online {{ background: #28a745; box-shadow: 0 0 6px #28a745; }}
        .server-dot.offline {{ background: #dc3545; }}
        .summary-modal {{
            display: none; position: fixed; top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0,0,0,0.55); z-index: 1000;
            justify-content: center; align-items: center;
        }}
        .summary-modal.visible {{ display: flex; }}
        .summary-inner {{
            background: white; border-radius: 12px; padding: 28px 32px;
            max-width: 480px; width: 90%; max-height: 80vh; overflow-y: auto;
            box-shadow: 0 8px 32px rgba(0,0,0,0.25);
        }}
        .summary-inner h3 {{ margin-bottom: 14px; color: #111; font-size: 17px; }}
        .summary-list {{ font-size: 13px; margin-bottom: 20px; }}
        .summary-list div {{ padding: 4px 0; border-bottom: 1px solid #f0f0f0; }}
        .summary-list div:last-child {{ border-bottom: none; }}
        .summary-ok {{
            background: #e8120a; color: white; border: none;
            padding: 11px 0; border-radius: 6px; cursor: pointer;
            font-weight: bold; font-size: 14px; width: 100%;
        }}
        .summary-ok:hover {{ background: #c00e08; }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>
            <span>🇩🇪 Stereotypen Dashboard</span>
            <div style="display:flex;align-items:center;gap:10px;">
                <div class="server-status" id="serverStatus">
                    <span class="server-dot" id="serverDot"></span>
                    <span id="serverText">Verbinde...</span>
                </div>
                <button onclick="restartServer()" id="restartBtn" style="background:#333;color:white;border:none;padding:5px 12px;border-radius:20px;cursor:pointer;font-size:12px;font-weight:600;">↺ Neustart</button>
            </div>
        </h1>
        <div class="btn-group btn-row">
            <button class="action-btn disabled" id="storyBtn"   onclick="showInput('story')">✍️ Story generieren</button>
            <button class="action-btn disabled" id="captionBtn" onclick="showInput('caption')">💬 Caption generieren</button>
            <button class="action-btn disabled" id="picBtn"     onclick="showInput('picture')">🖼️ Bild generieren</button>
        </div>
        <div class="btn-group btn-row">
            <button class="action-btn" id="refreshBtn"    onclick="doRefresh()">🔄 Refresh</button>
            <button class="action-btn" id="audioBtn"    onclick="showInput('audio')">🎵 Audio generieren</button>
            <button class="action-btn" id="audioPicBtn" onclick="runDirect('audio-pic')">🎵 Audio für alle Pics</button>
            <button class="action-btn" id="videoBtn"    onclick="showInput('video')">🎬 Video erstellen</button>
            <button class="action-btn" id="playwrightBtn" onclick="showInput('playwright')">🤖 Bilder-Playwright</button>
            <button class="action-btn" id="postBtn"     onclick="runDirect('post')">📤 Instagram Post</button>
        </div>

        <div class="pie-section">
            <canvas id="statusPie" width="160" height="160"></canvas>
            <div class="pie-legend">
                <div class="legend-item">
                    <span class="legend-dot" style="background:#1a4d2e"></span>
                    Gepostet: {pie_posted}
                </div>
                <div class="legend-item">
                    <span class="legend-dot" style="background:#22c55e"></span>
                    Bereit zum Posten: {pie_ready}
                </div>
                <div class="legend-item">
                    <span class="legend-dot" style="background:#fbbf24"></span>
                    Unvollständig: {pie_incomplete}
                </div>
            </div>
        </div>

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

        <div class="new-story-card">
            <h3>✍️ Neue Story erstellen</h3>
            <div class="new-story-fields">
                <div class="new-story-field">
                    <label>Stereotyp *</label>
                    <input type="text" id="newStereotyp" placeholder="z.B. Der Sparfuchs"
                           onkeydown="if(event.key==='Enter') createStory()">
                </div>
                <div class="new-story-field">
                    <label>Stichworte (optional)</label>
                    <input type="text" id="newStichworte" placeholder="z.B. Sonderangebot, Coupons, Kassenzettel"
                           onkeydown="if(event.key==='Enter') createStory()">
                </div>
                <div class="new-story-field" style="flex:0;min-width:150px;">
                    <label>Reihenfolge</label>
                    <select id="newPosition" onchange="toggleCustomPos()">
                        <option value="">Nicht einreihen</option>
                        <option value="start">Anfang</option>
                        <option value="end">Ende</option>
                        <option value="custom">Position...</option>
                    </select>
                    <div class="pos-custom" id="posCustomDiv">
                        <input type="number" id="newPositionNr" min="1" placeholder="z.B. 3">
                    </div>
                </div>
                <button class="new-story-submit" id="createStoryBtn" onclick="createStory()">Generieren</button>
            </div>
        </div>

        <div class="reihenfolge-card">
            <h3>
                <span>📋 Posting-Reihenfolge</span>
                <span id="rqCount" style="font-size:11px;color:#888;font-weight:400;">{len(reihenfolge_nrs)} Stories</span>
            </h3>
            <table class="reihenfolge-table" id="reihenfolgeTable">
                {reihenfolge_rows_html}
            </table>
        </div>

        <div class="pic-input" id="actionInputDiv">
            <label id="actionLabel"></label>
            <input type="text" id="actionInput" placeholder="z.B. 5 | 1-10 | 100_01 | leer = alle ausstehenden"
                   onkeydown="if(event.key==='Enter') startAction()">
            <button onclick="startAction()">Starten</button>
        </div>

        <div class="log-box" id="logBox">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                <strong id="logTitle">Verarbeitung...</strong>
                <button id="abortBtn" onclick="abortTask()" style="background:#dc3545;color:white;border:none;padding:5px 14px;border-radius:4px;cursor:pointer;font-weight:bold;font-size:12px;">⏹ Abbrechen</button>
            </div>
            <div class="log-progress">
                <div class="log-fill" id="logFill" style="width:0%">0%</div>
            </div>
            <div class="log-msg" id="logMsg">Starte...</div>
            <div class="log-list" id="logList"></div>
        </div>
    </div>

    <div class="queue-modal" id="queueModal" onclick="closeQueueModal()">
        <div class="queue-inner" onclick="event.stopPropagation()">
            <h3 id="queueModalTitle">☰ Reihenfolge</h3>
            <div class="queue-options">
                <div class="queue-opt" onclick="setQueue('start')">⬆️ An den Anfang</div>
                <div class="queue-opt" onclick="setQueue('end')">⬇️ Ans Ende</div>
                <div class="queue-pos-row">
                    <input type="number" id="queuePosInput" min="1" placeholder="Position (z.B. 2)">
                    <button class="queue-pos-btn" onclick="setQueue('pos')">Einfügen</button>
                </div>
                <div class="queue-opt remove" id="queueRemoveBtn" onclick="setQueue('remove')">✕ Aus Reihenfolge entfernen</div>
            </div>
            <button class="queue-cancel" onclick="closeQueueModal()">Abbrechen</button>
        </div>
    </div>

    <div class="summary-modal" id="summaryModal" onclick="closeSummary()">
        <div class="summary-inner" onclick="event.stopPropagation()">
            <h3>✅ Refresh abgeschlossen</h3>
            <div class="summary-list" id="summaryList"></div>
            <button class="summary-ok" onclick="closeSummary()">OK</button>
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
                        <th title="YouTube Short">YT</th>
                        <th title="Instagram">Post</th>
                        <th title="Posting-Reihenfolge">Reihenf.</th>
                    </tr>
                </thead>
                <tbody>
{rows_html}                </tbody>
            </table>
        </div>
    </div>
</div>

<script>
    (function() {{
        var canvas = document.getElementById('statusPie');
        if (!canvas) return;
        var ctx = canvas.getContext('2d');
        var data = [
            {{ v: {pie_posted},     c: '#1a4d2e' }},
            {{ v: {pie_ready},      c: '#22c55e' }},
            {{ v: {pie_incomplete}, c: '#fbbf24' }}
        ];
        var total = data.reduce(function(s, d) {{ return s + d.v; }}, 0);
        if (total === 0) return;
        var start = -Math.PI / 2;
        var cx = 80, cy = 80, r = 72;
        data.forEach(function(d) {{
            if (d.v === 0) return;
            var angle = (d.v / total) * 2 * Math.PI;
            ctx.beginPath();
            ctx.moveTo(cx, cy);
            ctx.arc(cx, cy, r, start, start + angle);
            ctx.closePath();
            ctx.fillStyle = d.c;
            ctx.fill();
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 2;
            ctx.stroke();
            start += angle;
        }});
    }})();

    const ACTIONS = {{
        'story':      {{ btn: 'storyBtn',      api: '/api/generate-story',              label: '✍️ Story generieren'      }},
        'caption':    {{ btn: 'captionBtn',    api: '/api/generate-caption',            label: '💬 Caption generieren'    }},
        'picture':    {{ btn: 'picBtn',        api: '/api/generate-picture',            label: '🖼️ Bild generieren'      }},
        'audio':      {{ btn: 'audioBtn',      api: '/api/generate-audio',              label: '🎵 Audio generieren'      }},
        'playwright': {{ btn: 'playwrightBtn', api: '/api/generate-pictures-playwright', label: '🤖 Bilder-Playwright'     }},
        'audio-pic': {{ btn: 'audioPicBtn', api: '/api/generate-audio-for-pics', label: '🎵 Audio für alle Pics'  }},
        'video':   {{ btn: 'videoBtn',   api: '/api/generate-video',   label: '🎬 Video erstellen'   }},
        'post':    {{ btn: 'postBtn',    api: '/api/instagram-post',      label: '📤 Instagram Post'    }},
    }};

    let _pendingAction = null;
    let _pollInterval = null;
    let _activeBtn = null;
    let _isRefresh = false;

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
        _activeBtn = btn;
        btn.classList.add('running');
        btn.disabled = true;
        const abortBtn = document.getElementById('abortBtn');
        abortBtn.disabled = false;
        abortBtn.textContent = '⏹ Abbrechen';
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
        if (btn) {{ btn.classList.remove('running'); btn.disabled = false; }}
        document.getElementById('logBox').classList.remove('visible');
        _activeBtn = null;
    }}

    function updateLogList(lines) {{
        const el = document.getElementById('logList');
        if (!lines || lines.length === 0) {{ el.classList.remove('visible'); return; }}
        el.classList.add('visible');
        el.innerHTML = lines.map(l => `<div>${{l}}</div>`).join('');
        el.scrollTop = el.scrollHeight;
    }}

    function pollProgress(btn, label) {{
        if (_pollInterval) clearInterval(_pollInterval);
        let pct = 5;
        _pollInterval = setInterval(async () => {{
            try {{
                const resp = await fetch('/api/progress');
                const data = await resp.json();
                setLog(data.percent || pct, data.message || '...');
                updateLogList(data.log);
                if (data.status === 'complete' || data.status === 'error' || data.status === 'idle') {{
                    clearInterval(_pollInterval);
                    _pollInterval = null;
                    if (data.status === 'complete' && _isRefresh) {{
                        _isRefresh = false;
                        resetBtn(btn, label);
                        showSummary(data.log, data.message);
                    }} else if (data.status === 'complete') {{
                        setLog(100, 'Fertig! Lade Dashboard neu...');
                        setTimeout(() => {{ updateLogList([]); location.reload(); }}, 1500);
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

    function showSummary(log, msg) {{
        const el = document.getElementById('summaryList');
        const items = (log && log.length) ? log : [msg || 'Refresh abgeschlossen.'];
        el.innerHTML = items.map(l => `<div>${{l}}</div>`).join('');
        document.getElementById('summaryModal').classList.add('visible');
        document.getElementById('logBox').classList.remove('visible');
    }}

    function closeSummary(e) {{
        document.getElementById('summaryModal').classList.remove('visible');
        location.reload();
    }}

    async function abortTask() {{
        const btn = document.getElementById('abortBtn');
        btn.textContent = '⏳...';
        btn.disabled = true;
        try {{
            await fetch('/api/abort', {{ method: 'POST' }});
        }} catch(e) {{}}
        if (_pollInterval) {{ clearInterval(_pollInterval); _pollInterval = null; }}
        resetBtn(_activeBtn, '');
    }}

    async function doRefresh() {{
        _isRefresh = true;
        const btn = document.getElementById('refreshBtn');
        _activeBtn = btn;
        btn.textContent = '⏳ Refresh...';
        btn.classList.add('running');
        btn.disabled = true;
        const abortBtn = document.getElementById('abortBtn');
        abortBtn.disabled = false;
        abortBtn.textContent = '⏹ Abbrechen';
        document.getElementById('logBox').classList.add('visible');
        document.getElementById('logTitle').textContent = '🔄 Refresh';
        setLog(5, 'Starte...');
        try {{
            const resp = await fetch('/api/refresh', {{ method: 'POST' }});
            if (resp.ok) pollProgress(btn, '🔄 Refresh');
            else {{ btn.textContent = '🔄 Refresh'; resetBtn(btn, ''); location.reload(); }}
        }} catch(e) {{ btn.textContent = '🔄 Refresh'; resetBtn(btn, ''); location.reload(); }}
    }}

    async function restartServer() {{
        const btn = document.getElementById('restartBtn');
        btn.textContent = '⏳ Neustart...';
        btn.disabled = true;
        try {{
            await fetch('/api/restart', {{ method: 'POST' }});
        }} catch(e) {{}}
        setTimeout(() => location.reload(), 4000);
    }}

    async function updateServerStatus() {{
        const dot = document.getElementById('serverDot');
        const txt = document.getElementById('serverText');
        try {{
            const resp = await fetch('/api/status');
            const data = await resp.json();
            dot.className = 'server-dot online';
            txt.textContent = `Server online · gestartet ${{data.started}} · Laufzeit ${{data.uptime}}`;
        }} catch(e) {{
            dot.className = 'server-dot offline';
            txt.textContent = 'Server offline';
        }}
    }}
    updateServerStatus();
    setInterval(updateServerStatus, 30000);

    const NR_LOOKUP = {nr_lookup_json};
    let _queueNr = null;
    let _currentReihenfolge = [];

    async function loadReihenfolge() {{
        try {{
            const r = await fetch('/api/reihenfolge');
            const d = await r.json();
            _currentReihenfolge = d.reihenfolge || [];
        }} catch(e) {{ _currentReihenfolge = []; }}
    }}

    async function refreshQueueDisplay() {{
        await loadReihenfolge();
        const table = document.getElementById('reihenfolgeTable');
        const count = document.getElementById('rqCount');
        if (!_currentReihenfolge.length) {{
            table.innerHTML = '<tr><td colspan="3" class="rq-empty">Reihenfolge ist leer</td></tr>';
            count.textContent = '0 Stories';
            return;
        }}
        count.textContent = _currentReihenfolge.length + ' Stories';
        table.innerHTML = _currentReihenfolge.map((nr, i) => {{
            const name = NR_LOOKUP[nr] || NR_LOOKUP[String(parseInt(nr))] || '—';
            return `<tr><td class="rq-pos">${{i+1}}</td><td class="rq-nr">#${{nr}}</td><td class="rq-name">${{name}}</td></tr>`;
        }}).join('');
        // Reihenfolge-Spalte in der Tabelle aktualisieren
        document.querySelectorAll('.rq-col').forEach(td => {{
            const nr = td.getAttribute('data-nr');
            const pos = _currentReihenfolge.indexOf(nr) + 1 ||
                        _currentReihenfolge.indexOf(String(parseInt(nr))) + 1 ||
                        _currentReihenfolge.indexOf(nr.padStart(4,'0')) + 1;
            td.innerHTML = pos ? `<span class="rq-badge">${{pos}}</span>` : '';
        }});
    }}

    function toggleCustomPos() {{
        const sel = document.getElementById('newPosition');
        const div = document.getElementById('posCustomDiv');
        div.style.display = sel.value === 'custom' ? 'block' : 'none';
    }}

    async function openQueueModal(btn) {{
        _queueNr = btn.getAttribute('data-nr');
        await loadReihenfolge();
        const inQueue = _currentReihenfolge.some(n => parseInt(n, 10) === parseInt(_queueNr, 10));

        if (!inQueue) {{
            const r = await fetch('/api/cloudinary-check?nr=' + _queueNr);
            const d = await r.json();
            if (!d.exists) {{
                alert('Story #' + _queueNr + ' hat noch kein Video auf Cloudinary.\\nErst Video generieren und hochladen!');
                _queueNr = null;
                return;
            }}
        }}

        document.getElementById('queueModalTitle').textContent =
            '☰ Reihenfolge – #' + _queueNr + (inQueue ? ' (aktuell in Queue)' : '');
        document.getElementById('queueRemoveBtn').style.display = inQueue ? 'flex' : 'none';
        document.getElementById('queuePosInput').value = '';
        document.getElementById('queueModal').classList.add('visible');
    }}

    function closeQueueModal() {{
        document.getElementById('queueModal').classList.remove('visible');
        _queueNr = null;
    }}

    async function setQueue(action) {{
        if (!_queueNr) return;
        let position;
        if (action === 'start') position = 'start';
        else if (action === 'end') position = 'end';
        else if (action === 'remove') {{
            await fetch('/api/reihenfolge/remove', {{
                method: 'POST', headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{nr: _queueNr}})
            }});
            closeQueueModal();
            document.querySelectorAll('.queue-btn[data-nr="' + _queueNr + '"]')
                .forEach(b => b.classList.remove('in-queue'));
            await refreshQueueDisplay();
            flashSaved('Entfernt');
            return;
        }} else {{
            const val = document.getElementById('queuePosInput').value.trim();
            if (!val) {{ document.getElementById('queuePosInput').focus(); return; }}
            position = val;
        }}
        await fetch('/api/reihenfolge', {{
            method: 'POST', headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{nr: _queueNr, position}})
        }});
        closeQueueModal();
        document.querySelectorAll('.queue-btn[data-nr="' + _queueNr + '"]')
            .forEach(b => b.classList.add('in-queue'));
        await refreshQueueDisplay();
        flashSaved('Gespeichert');
    }}

    function flashSaved(msg) {{
        const card = document.querySelector('.reihenfolge-card');
        const count = document.getElementById('rqCount');
        card.classList.add('saved');
        const prev = count.textContent;
        count.innerHTML = '<span style="color:#28a745;font-weight:700;">✓ ' + msg + '</span>';
        setTimeout(() => {{
            card.classList.remove('saved');
            count.textContent = _currentReihenfolge.length + ' Stories';
        }}, 1800);
    }}

    async function createStory() {{
        const stereotyp = document.getElementById('newStereotyp').value.trim();
        const stichworte = document.getElementById('newStichworte').value.trim();
        if (!stereotyp) {{
            document.getElementById('newStereotyp').focus();
            return;
        }}
        const btn = document.getElementById('createStoryBtn');
        btn.disabled = true;
        btn.textContent = '⏳...';
        _activeBtn = null;
        document.getElementById('logBox').classList.add('visible');
        document.getElementById('logTitle').textContent = '✍️ Story generieren: ' + stereotyp;
        setLog(5, 'Starte...');
        try {{
            let position = document.getElementById('newPosition').value;
        if (position === 'custom') {{
            position = document.getElementById('newPositionNr').value.trim() || '';
        }}
        const resp = await fetch('/api/create-story', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{stereotyp, stichworte, position}})
            }});
            if (resp.ok) {{
                pollProgress(btn, '✍️ Story generieren');
                _activeBtn = btn;
            }} else {{
                const err = await resp.json();
                alert('Fehler: ' + (err.error || 'Unbekannter Fehler'));
                btn.disabled = false;
                btn.textContent = 'Generieren';
            }}
        }} catch(e) {{
            btn.disabled = false;
            btn.textContent = 'Generieren';
        }}
    }}

    const _storyCache = {{}};
    const _tooltip = document.createElement('div');
    _tooltip.id = 'story-tooltip';
    document.body.appendChild(_tooltip);

    async function showStory(eye) {{
        const nr = eye.getAttribute('data-nr');
        if (!_storyCache[nr]) {{
            const r = await fetch('/api/story-text?nr=' + nr);
            const d = await r.json();
            _storyCache[nr] = d.text || '(kein Text vorhanden)';
        }}
        _tooltip.textContent = _storyCache[nr];
        _tooltip.style.display = 'block';
        document.addEventListener('mousemove', _moveTooltip);
    }}

    function hideStory() {{
        _tooltip.style.display = 'none';
        document.removeEventListener('mousemove', _moveTooltip);
    }}

    function _moveTooltip(e) {{
        const gap = 14;
        let x = e.clientX + gap;
        let y = e.clientY + gap;
        if (x + 440 > window.innerWidth) x = e.clientX - 440 - gap;
        if (y + _tooltip.offsetHeight > window.innerHeight) y = e.clientY - _tooltip.offsetHeight - gap;
        _tooltip.style.left = x + 'px';
        _tooltip.style.top  = y + 'px';
    }}

    async function togglePost(btn) {{
        const nr = btn.getAttribute('data-nr');
        if (btn.classList.contains('active')) {{
            if (!confirm(`Story #${{nr}} als NICHT gepostet markieren?`)) return;
            btn.disabled = true;
            btn.textContent = '...';
            try {{
                const resp = await fetch('/api/unmark-posted', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{nr}})
                }});
                if (resp.ok) {{
                    btn.classList.remove('active');
                    btn.textContent = 'Post';
                    btn.disabled = false;
                    const row = btn.closest('tr');
                    if (row) {{ row.className = 'row-ready'; }}
                }} else {{
                    btn.textContent = '✓ Gepostet';
                    btn.disabled = false;
                }}
            }} catch(e) {{
                btn.textContent = '✓ Gepostet';
                btn.disabled = false;
            }}
            return;
        }}
        if (!confirm(`Story #${{nr}} als gepostet markieren?`)) return;
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
                const row = btn.closest('tr');
                if (row) {{ row.className = 'row-posted'; }}
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
