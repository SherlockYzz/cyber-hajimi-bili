# -*- coding: utf-8 -*-
"""
赛博哈基米 (Cyber-Hajimi) - 毛玻璃跨端控制中心 (Web UI & Sidecar)
- 零第三方依赖：纯 Python 3 原生 http.server 驱动
- 像素级还原 DeepSeek 纯净毛玻璃极客质感与 Antigravity 原生 Sidecar 抽屉规范
- 全景可视化看过的视频、5帧时序分镜雪碧图画卷与多模态画风审美
- 全透明互动操作审计流水：发弹幕、发评论、@主人、发私信记录实时持久化查阅
- 站内信与@互动中枢：一键私信互通测试、B站@通知监听与私信会话管理
"""

import os
import sys
import json
import time
import base64
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import threading

SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "hajimi_config.json"
LOCAL_CONFIG_PATH = PROJECT_ROOT / "config" / "hajimi_config.local.json"
QRCODE_PATH = PROJECT_ROOT / "images" / "qrcode_login.png"
JOURNALS_DIR = PROJECT_ROOT / "docs" / "journals"
CACHE_DIR = PROJECT_ROOT / "cache"
PERSONA_PATH = PROJECT_ROOT / "docs" / "gemini_persona.md"
PERSONA_BACKUP_PATH = PROJECT_ROOT / "docs" / "hajimi_persona.md"

JOURNALS_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

from bili_hajimi_core import BiliHajimiCore
from hajimi_brain import HajimiBrain
from hajimi_daemon import HajimiDaemon

daemon_instance = HajimiDaemon(CONFIG_PATH)
is_cruising = False
cruise_logs_buffer = []


class HajimiWebHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_json(self, data: dict, code: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            pass

    def _send_html(self, html_str: str, code: int = 200):
        body = html_str.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Connection", "close")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/":
            self._send_html(get_dashboard_html())
        elif path == "/api/status":
            user_info = daemon_instance.core.get_user_info()
            in_win, win_info = daemon_instance.is_in_active_window()
            resp = {
                "user": user_info,
                "current_window": win_info,
                "in_window": in_win,
                "stamina": daemon_instance.state.get("stamina", 100),
                "at_count_today": daemon_instance.state.get("at_count_today", 0),
                "watched_count": len(daemon_instance.state.get("watched_today", [])),
                "treasures_count": len(daemon_instance.state.get("treasures_today", [])),
                "morning_done": daemon_instance.state.get("morning_journal_done", False),
                "evening_done": daemon_instance.state.get("evening_journal_done", False),
                "recent": daemon_instance.state.get("recent_evaluations", [])[:80],
                "activity_logs": daemon_instance.state.get("activity_logs", [])[:150],
                "config": daemon_instance.config,
                "is_cruising": is_cruising,
                "cruise_logs": cruise_logs_buffer[-40:],
            }
            self._send_json(resp)
        elif path == "/api/qrcode":
            qr_res = daemon_instance.core.generate_login_qr()
            img_b64 = ""
            if QRCODE_PATH.exists():
                try:
                    with open(QRCODE_PATH, "rb") as f:
                        img_b64 = "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")
                except Exception:
                    pass
            qr_res["img_b64"] = img_b64
            self._send_json(qr_res)
        elif path == "/api/poll_login":
            qrcode_key = query.get("key", [""])[0]
            poll_res = daemon_instance.core.poll_login_status(qrcode_key)
            self._send_json(poll_res)
        elif path == "/api/persona":
            content = ""
            target_file = PERSONA_PATH if PERSONA_PATH.exists() else PERSONA_BACKUP_PATH
            if target_file.exists():
                try:
                    content = target_file.read_text(encoding="utf-8-sig")
                except Exception:
                    content = target_file.read_text(encoding="utf-8", errors="replace")
            self._send_json({"persona": content})
        elif path == "/api/journals":
            journals = []
            if JOURNALS_DIR.exists():
                for f in sorted(JOURNALS_DIR.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True):
                    try:
                        mtime_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(f.stat().st_mtime))
                        snippet = f.read_text(encoding="utf-8-sig", errors="replace")[:300].strip()
                        journals.append({
                            "filename": f.name,
                            "path": str(f),
                            "mtime": mtime_str,
                            "size": f.stat().st_size,
                            "snippet": snippet
                        })
                    except Exception:
                        pass
            self._send_json({"journals": journals})
        elif path == "/api/journal_detail":
            filename = query.get("filename", [""])[0]
            content = ""
            if filename:
                safe_name = Path(filename).name
                target = JOURNALS_DIR / safe_name
                if target.exists() and target.is_file():
                    content = target.read_text(encoding="utf-8-sig", errors="replace")
            self._send_json({"content": content})
        elif path == "/api/at_notifications":
            items = daemon_instance.core.get_at_notifications()
            self._send_json({"success": True, "items": items})
        elif path == "/api/sessions":
            sessions = daemon_instance.core.get_unread_sessions()
            self._send_json({"success": True, "sessions": sessions})
        elif path.startswith("/images/") or path.startswith("/cache/"):
            is_cache = path.startswith("/cache/")
            prefix_len = len("/cache/") if is_cache else len("/images/")
            base_folder = PROJECT_ROOT / "cache" if is_cache else PROJECT_ROOT / "images"
            rel_name = urllib.parse.unquote(path[prefix_len:])
            img_file = base_folder / rel_name
            if img_file.exists() and img_file.is_file():
                suffix = img_file.suffix.lower()
                mime = "image/png" if suffix == ".png" else ("image/jpeg" if suffix in [".jpg", ".jpeg"] else "application/octet-stream")
                data = img_file.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Connection", "close")
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                try:
                    self.wfile.write(data)
                except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                    pass
            else:
                self.send_error(404, "File not found")
        else:
            self.send_error(404)

    def do_POST(self):
        global is_cruising, cruise_logs_buffer
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_len = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            payload = json.loads(post_body)
        except Exception:
            payload = {}

        if path == "/api/save_config":
            try:
                new_cfg = payload.get("config", {})
                if new_cfg:
                    for k, v in new_cfg.items():
                        if isinstance(v, dict) and isinstance(daemon_instance.config.get(k), dict):
                            daemon_instance.config[k].update(v)
                        else:
                            daemon_instance.config[k] = v

                    daemon_instance.core.config = daemon_instance.config
                    daemon_instance.brain.config = daemon_instance.config
                    daemon_instance.core.save_config()
                self._send_json({"success": True, "message": "配置已成功保存并即时生效！"})
            except Exception as e:
                self._send_json({"success": False, "message": str(e)}, 500)

        elif path == "/api/save_persona":
            try:
                persona_txt = payload.get("persona", "")
                with open(PERSONA_PATH, "w", encoding="utf-8-sig") as f:
                    f.write(persona_txt)
                if PERSONA_BACKUP_PATH.exists():
                    with open(PERSONA_BACKUP_PATH, "w", encoding="utf-8-sig") as f:
                        f.write(persona_txt)
                daemon_instance.brain.persona = persona_txt
                self._send_json({"success": True, "message": "人设正文已成功注入 docs/gemini_persona.md！下次唤醒立即生效 √"})
            except Exception as e:
                self._send_json({"success": False, "message": str(e)}, 500)

        elif path == "/api/cruise":
            if is_cruising:
                self._send_json({"success": False, "message": "闪闪正在巡航冲浪中，请稍候喵..."})
                return

            def _run():
                global is_cruising, cruise_logs_buffer
                is_cruising = True
                cruise_logs_buffer.append(f"[{time.strftime('%H:%M:%S')}] 🚀 主人发起即时召唤，闪闪全速出击巡航！")
                try:
                    res = daemon_instance.run_cruise_cycle(force=True)
                    for l in res.get("logs", []):
                        cruise_logs_buffer.append(f"[{time.strftime('%H:%M:%S')}] {l}")
                    cruise_logs_buffer.append(f"[{time.strftime('%H:%M:%S')}] 🎉 本次巡航任务圆满达成！已同步更新工作记录与审计流水。")
                except Exception as e:
                    cruise_logs_buffer.append(f"[{time.strftime('%H:%M:%S')}] ⚠ 巡航遇到波动: {e}")
                finally:
                    is_cruising = False

            t = threading.Thread(target=_run, daemon=True)
            t.start()
            self._send_json({"success": True, "message": "已成功唤起闪闪！全速巡航中..."})

        elif path == "/api/send_pm":
            target_uid = payload.get("receiver_uid") or daemon_instance.config.get("profile", {}).get("master_uid")
            content = payload.get("content") or "🐾 主人！这是闪闪来自控制中心的站内私信测试喵~ ✨"
            if not target_uid:
                self._send_json({"success": False, "message": "未配置主人 UID，请在设置中先填写主人 UID！"})
                return

            res = daemon_instance.core.send_private_message(int(target_uid), content)
            status = "成功" if res.get("success") else "失败"
            daemon_instance.log_activity("发站内私信(测试)", f"主人UID: {target_uid}", content, status=status, details=res.get("message", ""))
            self._send_json(res)

        elif path == "/api/morning_journal":
            path_file = daemon_instance.generate_morning_journal_file()
            daemon_instance.log_activity("生成手记", "晨思早安手记", f"归档文件: {Path(path_file).name}", status="成功")
            self._send_json({"success": True, "message": f"晨思手记已生成: {path_file}"})

        elif path == "/api/evening_journal":
            path_file = daemon_instance.generate_evening_journal_file()
            daemon_instance.log_activity("生成手记", "晚读宝藏手记", f"归档文件: {Path(path_file).name}", status="成功")
            self._send_json({"success": True, "message": f"晚读手记已生成: {path_file}"})

        elif path == "/api/clear_audit":
            daemon_instance.state["activity_logs"] = []
            daemon_instance.save_state()
            self._send_json({"success": True, "message": "审计流水已清空！"})

        else:
            self.send_error(404)


def get_dashboard_html() -> str:
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>赛博养Gemini · 全息监控与伴生中枢</title>
  <style>
    :root {
      --bg-color: #f7f9fc;
      --sidebar-bg: #f1f4f9;
      --text-main: #1f2937;
      --text-sub: #4b5563;
      --text-muted: #6b7280;
      --border-color: #e5e7eb;
      --accent: #6366f1;
      --accent-hover: #4f46e5;
      --accent-light: #eef2ff;
      --card-bg: #ffffff;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: var(--bg-color);
      color: var(--text-main);
      height: 100vh;
      overflow: hidden;
      display: flex;
    }

    .app-window {
      display: flex;
      width: 100vw;
      height: 100vh;
      background: #ffffff;
    }

    /* 左侧侧边栏 */
    .sidebar {
      width: 250px;
      min-width: 250px;
      background: var(--sidebar-bg);
      border-right: 1px solid var(--border-color);
      display: flex;
      flex-direction: column;
      padding: 16px 10px;
    }
    .brand-title {
      font-size: 15px;
      font-weight: 700;
      color: #111827;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .brand-subtitle {
      font-size: 12px;
      color: var(--text-muted);
      margin-top: 3px;
      margin-left: 34px;
    }
    .nav-list {
      list-style: none;
      margin-top: 20px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .nav-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 9px 12px;
      border-radius: 8px;
      font-size: 13.5px;
      font-weight: 500;
      color: #4b5563;
      cursor: pointer;
      transition: all 0.15s ease;
      user-select: none;
    }
    .nav-item:hover {
      background: #e5e9f0;
      color: #111827;
    }
    .nav-item.active {
      background: #e0e7ff;
      color: var(--accent);
      font-weight: 600;
    }
    .nav-icon { font-size: 16px; width: 20px; text-align: center; }

    .sidebar-footer {
      margin-top: auto;
      padding: 12px;
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: 8px;
      font-size: 11.5px;
      color: var(--text-muted);
      line-height: 1.6;
    }

    /* 右侧主视窗 */
    .main-viewport {
      flex: 1;
      height: 100vh;
      overflow-y: auto;
      padding: 24px 32px;
      background: #ffffff;
    }
    .tab-view { display: none; }
    .tab-view.active { display: block; }

    /* 顶部全局统计状态条 */
    .top-stats-bar {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px;
      margin-bottom: 24px;
    }
    .stat-pill {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      padding: 12px 16px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .stat-label { font-size: 12px; color: var(--text-muted); font-weight: 500; }
    .stat-val { font-size: 20px; font-weight: 700; color: #0f172a; }

    .view-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 20px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border-color);
    }
    .title-block h1 { font-size: 20px; font-weight: 700; color: #111827; }
    .title-block .desc { font-size: 13px; color: var(--text-muted); margin-top: 4px; }
    .header-actions { display: flex; gap: 8px; }

    .btn-action {
      background: #ffffff;
      border: 1px solid #d1d5db;
      padding: 7px 14px;
      border-radius: 7px;
      font-size: 13px;
      font-weight: 500;
      color: #374151;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s;
    }
    .btn-action:hover {
      background: #f3f4f6;
      border-color: #9ca3af;
    }
    .btn-primary {
      background: var(--accent);
      color: #ffffff;
      border-color: var(--accent);
    }
    .btn-primary:hover {
      background: var(--accent-hover);
      border-color: var(--accent-hover);
    }

    /* 视频质检卡片流 */
    .eval-card {
      border: 1px solid #e5e7eb;
      border-radius: 12px;
      padding: 18px;
      margin-bottom: 18px;
      background: #ffffff;
      box-shadow: 0 1px 3px rgba(0,0,0,0.03);
      transition: transform 0.15s, box-shadow 0.15s;
    }
    .eval-card:hover {
      box-shadow: 0 6px 20px rgba(0,0,0,0.06);
    }
    .eval-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
    }
    .eval-title {
      font-size: 15px;
      font-weight: 600;
      color: #111827;
      text-decoration: none;
    }
    .eval-title:hover {
      color: var(--accent);
      text-decoration: underline;
    }
    .score-badge {
      padding: 4px 12px;
      border-radius: 20px;
      font-size: 12.5px;
      font-weight: 700;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }
    .score-badge.high { background: #ecfdf5; color: #059669; border: 1px solid #a7f3d0; }
    .score-badge.mid { background: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe; }
    .score-badge.low { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }

    .eval-meta { font-size: 12.5px; color: var(--text-muted); margin-bottom: 10px; }

    .eval-visual-strip {
      margin: 12px 0;
      border-radius: 8px;
      overflow: hidden;
      border: 1px solid #e2e8f0;
      background: #0f172a;
      position: relative;
    }
    .eval-visual-strip img {
      width: 100%;
      height: auto;
      display: block;
      cursor: pointer;
    }
    .strip-hint {
      position: absolute;
      bottom: 4px;
      right: 8px;
      background: rgba(0,0,0,0.65);
      color: #fff;
      font-size: 10px;
      padding: 2px 6px;
      border-radius: 4px;
      pointer-events: none;
    }

    .eval-visual-critique {
      background: #f0fdf4;
      border-left: 3px solid #10b981;
      padding: 10px 14px;
      border-radius: 0 6px 6px 0;
      margin-top: 8px;
      font-size: 13px;
      color: #065f46;
      line-height: 1.5;
    }
    .eval-highlight {
      background: #f8fafc;
      border-left: 3px solid #3b82f6;
      padding: 10px 14px;
      border-radius: 0 6px 6px 0;
      margin-top: 8px;
      font-size: 13px;
      color: #1e3a8a;
      line-height: 1.5;
    }
    .eval-cat-comment {
      background: #fdf2f8;
      border-left: 3px solid #ec4899;
      padding: 10px 14px;
      border-radius: 0 6px 6px 0;
      margin-top: 8px;
      font-size: 13px;
      color: #9d174d;
      line-height: 1.5;
    }

    /* 审计流水表格 */
    .audit-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      margin-top: 14px;
    }
    .audit-table th, .audit-table td {
      padding: 12px 14px;
      text-align: left;
      border-bottom: 1px solid #e5e7eb;
    }
    .audit-table th {
      background: #f8fafc;
      font-weight: 600;
      color: #475569;
    }
    .audit-badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 11.5px;
      font-weight: 600;
    }
    .badge-comment { background: #e0e7ff; color: #4338ca; }
    .badge-danmaku { background: #fef3c7; color: #b45309; }
    .badge-pm { background: #fce7f3; color: #be185d; }
    .badge-vision { background: #dcfce7; color: #15803d; }
    .badge-success { background: #d1fae5; color: #047857; }
    .badge-fail { background: #fee2e2; color: #b91c1c; }

    /* 站内信互动测试面板 */
    .pm-box {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 20px;
    }
    .form-group { margin-bottom: 14px; }
    .form-group label { display: block; font-size: 13px; font-weight: 600; color: #374151; margin-bottom: 6px; }
    .form-control {
      width: 100%;
      padding: 9px 12px;
      border: 1px solid #d1d5db;
      border-radius: 7px;
      font-size: 13.5px;
      outline: none;
    }
    .form-control:focus { border-color: var(--accent); }

    .notice-card {
      background: #fffbeb;
      border: 1px solid #fef3c7;
      border-radius: 8px;
      padding: 12px 16px;
      font-size: 12.5px;
      color: #92400e;
      line-height: 1.6;
      margin-top: 12px;
    }

    /* 控制台日志流 */
    .console-box {
      background: #111827;
      color: #38bdf8;
      font-family: ui-monospace, Menlo, Consolas, monospace;
      font-size: 12.5px;
      line-height: 1.55;
      padding: 16px;
      border-radius: 8px;
      height: 380px;
      overflow-y: auto;
      white-space: pre-wrap;
      word-break: break-all;
    }

    /* 吐司通知条 */
    .toast {
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #111827;
      color: #ffffff;
      padding: 10px 20px;
      border-radius: 8px;
      font-size: 13.5px;
      box-shadow: 0 10px 25px rgba(0,0,0,0.2);
      transform: translateY(100px);
      opacity: 0;
      transition: all 0.25s ease;
      z-index: 9999;
    }
    .toast.show { transform: translateY(0); opacity: 1; }

    /* 立绘衣橱网格 */
    .gallery-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 18px;
      margin-top: 16px;
    }
    .outfit-card {
      border: 1px solid var(--border-color);
      border-radius: 10px;
      overflow: hidden;
      background: #ffffff;
      cursor: pointer;
    }
    .outfit-preview {
      height: 240px;
      background: #f8fafc;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .outfit-preview img {
      max-width: 90%;
      max-height: 90%;
      object-fit: contain;
    }
    .outfit-meta { padding: 12px; }
    .outfit-title { font-size: 13.5px; font-weight: 600; color: var(--text-main); }
    .outfit-desc { font-size: 12px; color: var(--text-muted); margin-top: 4px; }
  </style>
</head>
<body>

<div class="app-window">
  <!-- 左侧导航 -->
  <aside class="sidebar">
    <div class="brand-title">
      <img src="/images/Gemini猫娘_双子星官方圆形头像.png" style="width:28px;height:28px;border-radius:50%;" alt="Icon">
      <span>赛博养Gemini · 双子星</span>
    </div>
    <div class="brand-subtitle">全息监控与伴生中枢</div>

    <ul class="nav-list">
      <li class="nav-item active" onclick="switchTab('tab-videos')">
        <span class="nav-icon">📺</span>
        <span>视频与工作记录</span>
      </li>
      <li class="nav-item" onclick="switchTab('tab-audit')">
        <span class="nav-icon">📜</span>
        <span>互动操作审计</span>
      </li>
      <li class="nav-item" onclick="switchTab('tab-messages')">
        <span class="nav-icon">💬</span>
        <span>站内信与@互动测试</span>
      </li>
      <li class="nav-item" onclick="switchTab('tab-cruise')">
        <span class="nav-icon">🚀</span>
        <span>巡航与即时召唤</span>
      </li>
      <li class="nav-item" onclick="switchTab('tab-journals')">
        <span class="nav-icon">📝</span>
        <span>晨思晚读与手记</span>
      </li>
      <li class="nav-item" onclick="switchTab('tab-wardrobe')">
        <span class="nav-icon">👗</span>
        <span>立绘衣橱</span>
      </li>
      <li class="nav-item" onclick="switchTab('tab-gemini')">
        <span class="nav-icon">⚙</span>
        <span>系统与人设配置</span>
      </li>
    </ul>

    <div class="sidebar-footer">
      <div>🧠 驱动内核: Gemini 3.8 Flash</div>
      <div>⚡ 多模态: VideoShot 5帧雪碧图</div>
      <div>🐾 状态: 持久化自动归档开启</div>
    </div>
  </aside>

  <!-- 主视窗 -->
  <main class="main-viewport">
    
    <!-- 全局状态顶栏 -->
    <div class="top-stats-bar">
      <div class="stat-pill">
        <span class="stat-label">今日已看视频</span>
        <span id="statWatched" class="stat-val">0</span>
      </div>
      <div class="stat-pill">
        <span class="stat-label">今日宝藏神作</span>
        <span id="statTreasures" class="stat-val" style="color:#059669;">0</span>
      </div>
      <div class="stat-pill">
        <span class="stat-label">今日互动与 @ 次数</span>
        <span id="statInteractions" class="stat-val" style="color:#4f46e5;">0</span>
      </div>
      <div class="stat-pill">
        <span class="stat-label">仿生精力池</span>
        <span id="statStamina" class="stat-val" style="color:#ea580c;">100 / 100</span>
      </div>
    </div>

    <!-- Tab 1: 视频质检画卷 (默认显示，解决痛点 1) -->
    <div id="tab-videos" class="tab-view active">
      <div class="view-header">
        <div class="title-block">
          <h1>📺 视频与工作记录画卷</h1>
          <p class="desc">实时持久化呈现猫娘读过的所有视频：5帧时序分镜雪碧图、多模态画风点评、干货浓缩与操作状态（刷新重进绝不丢失）。</p>
        </div>
        <div class="header-actions">
          <button class="btn-action" onclick="loadStatus()">🔄 刷新列表</button>
          <button class="btn-action btn-primary" onclick="triggerCruise()">🚀 立即派闪闪出击巡航</button>
        </div>
      </div>
      <div id="videoListContainer">
        <!-- 动态加载视频卡片 -->
        <div style="padding:40px; text-align:center; color:#9ca3af;">正在加载历史视频记录...</div>
      </div>
    </div>

    <!-- Tab 2: 互动操作审计台账 (解决痛点 2) -->
    <div id="tab-audit" class="tab-view">
      <div class="view-header">
        <div class="title-block">
          <h1>📜 互动操作与@主人流水审计</h1>
          <p class="desc">全透明如实记录双子星在 B 站执行的所有真实操作：何时发了弹幕、在哪个视频评论区说了什么、带了什么 @，回执状态全追踪。</p>
        </div>
        <div class="header-actions">
          <button class="btn-action" onclick="loadStatus()">🔄 刷新流水</button>
          <button class="btn-action" onclick="clearAuditLogs()">清空流水</button>
        </div>
      </div>
      <table class="audit-table">
        <thead>
          <tr>
            <th style="width:140px;">操作时间</th>
            <th style="width:120px;">类型</th>
            <th>目标对象 (视频/用户)</th>
            <th>实际发送内容</th>
            <th style="width:90px;">状态</th>
            <th>官方回执细节</th>
          </tr>
        </thead>
        <tbody id="auditTableBody">
          <!-- 动态加载审计行 -->
        </tbody>
      </table>
    </div>

    <!-- Tab 3: 站内信与@互动测试 (解决痛点 3) -->
    <div id="tab-messages" class="tab-view">
      <div class="view-header">
        <div class="title-block">
          <h1>💬 站内信与@互动中枢</h1>
          <p class="desc">解决站内信连通性与“谁 @ 了我”通知监听：支持一键向主人测试发送私信、查看会话历史与防拦截指引。</p>
        </div>
        <div class="header-actions">
          <button class="btn-action" onclick="refreshMessages()">🔄 刷新通知与私信</button>
        </div>
      </div>

      <!-- 发送私信测试 -->
      <div class="pm-box">
        <h3 style="font-size:15px; margin-bottom:12px; color:#111827;">✉️ 向主人 B 站账号发送一条测试私信</h3>
        <div class="form-group">
          <label>接收者 B站 UID (主人的 UID):</label>
          <input type="number" id="testPmUid" class="form-control" style="max-width:300px;" placeholder="例如: 12345678">
        </div>
        <div class="form-group">
          <label>私信内容:</label>
          <input type="text" id="testPmText" class="form-control" value="🐾 主人在吗喵？这是赛博猫娘来自控制中心的连通性测试！收到请摸头~ ✨">
        </div>
        <button class="btn-action btn-primary" onclick="sendTestPm()">🚀 立即发送私信测试</button>
        <span id="pmSendStatus" style="margin-left:12px; font-size:13px; font-weight:600;"></span>

        <div class="notice-card">
          <strong>💡 为什么你之前没收到私信？（B站官方风控防拦截指南）：</strong><br>
          1. <strong>未互相关注拦截</strong>：B 站官方默认开启了“仅接收互关好友私信”或“折叠未关注人消息”。如果猫娘机器人账号与你的账号<strong>互不关注</strong>，发送的私信会直接被塞进“未关注人消息”折叠盒，甚至被 B 站拦截阻断！请务必确保双方在 B 站<strong>互相关注</strong>！<br>
          2. <strong>阈值触发机制</strong>：系统默认仅在质检到 &ge; 8.5 分的宝藏视频时才会向主人推送私信推荐。您可以在此处随时手动点击测试验证连通性！
        </div>
      </div>

      <!-- 谁 @ 了我 -->
      <div class="pm-box" style="margin-top:20px;">
        <h3 style="font-size:15px; margin-bottom:12px; color:#111827;">🔔 B站通知中心：谁在视频/评论区 @ 了我？</h3>
        <div id="atNotificationsList" style="font-size:13px; color:#4b5563;">
          点击上方“刷新通知与私信”拉取 B 站谁 @ 了猫娘...
        </div>
      </div>

      <!-- 私信会话列表 -->
      <div class="pm-box" style="margin-top:20px;">
        <h3 style="font-size:15px; margin-bottom:12px; color:#111827;">📫 最近的私信会话列表</h3>
        <div id="sessionsList" style="font-size:13px; color:#4b5563;">
          正在同步私信会话...
        </div>
      </div>
    </div>

    <!-- Tab 4: 巡航与即时召唤 -->
    <div id="tab-cruise" class="tab-view">
      <div class="view-header">
        <div class="title-block">
          <h1>🚀 巡航与即时召唤</h1>
          <p class="desc">实时召唤双子星巡航 B 站动态流，查看底层控制台实时瀑布流日志。</p>
        </div>
        <div class="header-actions">
          <button class="btn-action btn-primary" onclick="triggerCruise()">🚀 立即派闪闪巡航</button>
        </div>
      </div>
      <div class="console-box" id="consoleLog">等待召唤中... 点击右上角“立即派闪闪巡航”开启。</div>
    </div>

    <!-- Tab 5: 晨思晚读手记 -->
    <div id="tab-journals" class="tab-view">
      <div class="view-header">
        <div class="title-block">
          <h1>📝 晨思晚读手记与流水台账</h1>
          <p class="desc">包含每日自动归档的晨思手记、晚读宝藏手记以及《互动操作审计流水》。</p>
        </div>
        <div class="header-actions">
          <button class="btn-action" onclick="triggerMorning()">生成今日晨思</button>
          <button class="btn-action" onclick="triggerEvening()">生成今日晚读</button>
        </div>
      </div>
      <div id="journalsList">
        <!-- 动态加载手记 -->
      </div>
    </div>

    <!-- Tab 6: 立绘衣橱 -->
    <div id="tab-wardrobe" class="tab-view">
      <div class="view-header">
        <div class="title-block">
          <h1>👗 双子星专属立绘衣橱</h1>
          <p class="desc">包含水手校服、经典蓝白女仆装与原版常服的高清正面透明立绘与三视图设定。</p>
        </div>
      </div>
      <div id="galleryContainer" class="gallery-grid"></div>
    </div>

    <!-- Tab 7: 系统与人设配置 -->
    <div id="tab-gemini" class="tab-view">
      <div class="view-header">
        <div class="title-block">
          <h1>⚙️ 系统参数与主人配置</h1>
          <p class="desc">设置伴生猫娘身份、对主人的称呼、主人 UID（用于评论区 @ 与发私信）、巡航关注分区与偏向词。</p>
        </div>
        <div class="header-actions">
          <button class="btn-action btn-primary" onclick="saveFullConfig()">💾 保存配置</button>
        </div>
      </div>
      <div class="pm-box">
        <div class="form-group">
          <label>伴生猫娘角色名 (默认: 闪闪):</label>
          <input type="text" id="cfgRoleName" class="form-control" style="max-width:300px;" placeholder="例如: 闪闪">
        </div>
        <div class="form-group">
          <label>猫娘自称 (例如: 我、人家、咱、闪闪):</label>
          <input type="text" id="cfgSelfName" class="form-control" style="max-width:300px;" placeholder="例如: 我">
        </div>
        <div class="form-group">
          <label>对主人的尊称 (例如: 主人、笨蛋主人、观察者大人):</label>
          <input type="text" id="cfgCallMaster" class="form-control" style="max-width:300px;" placeholder="例如: 主人">
        </div>
        <div class="form-group">
          <label>主人的 B站 UID (必填，用于在评论区精准 @主人 及发送私信):</label>
          <input type="number" id="cfgMasterUid" class="form-control" style="max-width:300px;" placeholder="例如: 12345678">
        </div>
        <div class="form-group">
          <label>主人自定义昵称 (用于日志与手记输出):</label>
          <input type="text" id="cfgMasterName" class="form-control" style="max-width:300px;" placeholder="例如: 主人">
        </div>
        <div class="form-group">
          <label>触发在评论区 @主人的硬核神作分数阈值 (默认 8.0):</label>
          <input type="number" step="0.1" id="cfgAtThreshold" class="form-control" style="max-width:300px;">
        </div>
        <div class="form-group">
          <label>雷达重点倾向词 (英文或中文逗号隔开):</label>
          <input type="text" id="cfgKeywordsPrefer" class="form-control">
        </div>
        <div class="form-group">
          <label>负向屏蔽词 (营销号/洗稿过滤，英文或中文逗号隔开):</label>
          <input type="text" id="cfgKeywordsBlacklist" class="form-control">
        </div>
      </div>
    </div>

  </main>
</div>

<div id="toast" class="toast">操作成功</div>

<script>
  let currentConfig = {};

  function showToast(msg) {
    const t = document.getElementById('toast');
    t.innerText = msg;
    t.classList.add('show');
    setTimeout(() => { t.classList.remove('show'); }, 3000);
  }

  function switchTab(tabId) {
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-view').forEach(el => el.classList.remove('active'));

    const items = document.querySelectorAll('.nav-item');
    if (tabId === 'tab-videos') items[0].classList.add('active');
    else if (tabId === 'tab-audit') items[1].classList.add('active');
    else if (tabId === 'tab-messages') { items[2].classList.add('active'); refreshMessages(); }
    else if (tabId === 'tab-cruise') items[3].classList.add('active');
    else if (tabId === 'tab-journals') { items[4].classList.add('active'); loadJournals(); }
    else if (tabId === 'tab-wardrobe') { items[5].classList.add('active'); loadGallery(); }
    else if (tabId === 'tab-gemini') items[6].classList.add('active');

    const target = document.getElementById(tabId);
    if (target) target.classList.add('active');
  }

  async function loadStatus() {
    try {
      const res = await fetch('/api/status');
      const data = await res.json();
      currentConfig = data.config || {};

      // 顶部指标
      document.getElementById('statWatched').innerText = data.watched_count || (data.recent ? data.recent.length : 0);
      document.getElementById('statTreasures').innerText = data.treasures_count || 0;
      document.getElementById('statInteractions').innerText = (data.activity_logs ? data.activity_logs.length : 0) + ' 笔操作';
      document.getElementById('statStamina').innerText = `${Math.round(data.stamina || 100)} / 100`;

      // 填充设置项 (若用户当前焦点正在输入框内，不覆写以避免打字被打断)
      const isEditingConfig = document.activeElement && document.activeElement.closest && document.activeElement.closest('.pm-box');
      if (!isEditingConfig) {
        const prof = currentConfig.profile || {};
        const elRole = document.getElementById('cfgRoleName');
        if (elRole) elRole.value = prof.role_name || '闪闪';
        const elSelf = document.getElementById('cfgSelfName');
        if (elSelf) elSelf.value = prof.self_name || '我';
        const elCall = document.getElementById('cfgCallMaster');
        if (elCall) elCall.value = prof.call_master || '主人';
        const elUid = document.getElementById('cfgMasterUid');
        if (elUid) elUid.value = prof.master_uid || '';
        const elName = document.getElementById('cfgMasterName');
        if (elName) elName.value = prof.master_name || '主人';

        const pmUidEl = document.getElementById('testPmUid');
        if (pmUidEl && !pmUidEl.value) {
          pmUidEl.value = prof.master_uid || '';
        }

        const inter = currentConfig.interaction || {};
        const elThresh = document.getElementById('cfgAtThreshold');
        if (elThresh) elThresh.value = inter.at_score_threshold || 8.0;

        const prefs = currentConfig.preferences || {};
        const elPref = document.getElementById('cfgKeywordsPrefer');
        if (elPref) elPref.value = (prefs.keywords_prefer || []).join(', ');
        const elBlack = document.getElementById('cfgKeywordsBlacklist');
        if (elBlack) elBlack.value = (prefs.blacklist_keywords || []).join(', ');
      }

      // 渲染视频卡片流 (解决痛点 1)
      renderVideoCards(data.recent || []);

      // 渲染互动审计台账 (解决痛点 2)
      renderAuditTable(data.activity_logs || []);

      // 巡航日志
      if (data.cruise_logs && data.cruise_logs.length > 0) {
        document.getElementById('consoleLog').innerText = data.cruise_logs.join('\\n');
      }
    } catch(e) {
      console.error(e);
    }
  }

  function renderVideoCards(videos) {
    const cont = document.getElementById('videoListContainer');
    if (!videos || videos.length === 0) {
      cont.innerHTML = '<div style="padding:40px; text-align:center; color:#9ca3af;">今日暂无质检视频记录，点击右上角“立即派闪闪出击巡航”开始探索！</div>';
      return;
    }

    cont.innerHTML = videos.map(item => {
      const score = item.score || 0;
      let badgeClass = 'mid';
      if (score >= 8.5) badgeClass = 'high';
      else if (score <= 5.0) badgeClass = 'low';

      const sbUrl = item.storyboard_url || (item.bvid ? `/cache/storyboards/${item.bvid}_storyboard_strip.jpg` : '');
      const stripHtml = sbUrl ? `
        <div class="eval-visual-strip" title="点击可在新标签页查看5帧时序全景画卷">
          <a href="${sbUrl}" target="_blank"><img src="${sbUrl}" loading="lazy" onerror="this.parentElement.parentElement.style.display='none'"></a>
          <div class="strip-hint">5帧时序分镜雪碧图画卷 (覆盖10%~90%全片节奏) 🔍 点击放大</div>
        </div>
      ` : '';

      const visualCritiqueHtml = item.visual_critique ? `
        <div class="eval-visual-critique"><strong>🎨 视觉画风与分镜点评:</strong> ${item.visual_critique}</div>
      ` : '';

      const highlightHtml = item.highlight ? `
        <div class="eval-highlight"><strong>💡 核心干货亮点:</strong> ${item.highlight}</div>
      ` : '';

      const catCommentHtml = item.cat_comment ? `
        <div class="eval-cat-comment"><strong>🐾 猫娘品鉴评语:</strong> ${item.cat_comment}</div>
      ` : '';

      return `
        <div class="eval-card">
          <div class="eval-header">
            <a class="eval-title" href="https://www.bilibili.com/video/${item.bvid}" target="_blank">
              📺 《${item.title || item.bvid}》 🔗
            </a>
            <span class="score-badge ${badgeClass}">★ ${score} 分 [${item.verdict || '品鉴完毕'}]</span>
          </div>
          <div class="eval-meta">
            <span>UP主: <strong>${item.owner || '未知'}</strong></span> · 
            <span>质检时间: ${item.time || '-'}</span> · 
            <span>BV号: <code>${item.bvid}</code></span>
            ${item.should_at ? ' · <span style="color:#059669; font-weight:700;">★ 已触发 @主人</span>' : ''}
          </div>
          ${stripHtml}
          ${visualCritiqueHtml}
          ${highlightHtml}
          ${catCommentHtml}
        </div>
      `;
    }).join('');
  }

  function renderAuditTable(logs) {
    const tbody = document.getElementById('auditTableBody');
    if (!logs || logs.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:24px; color:#9ca3af;">暂无互动操作审计流水</td></tr>';
      return;
    }

    tbody.innerHTML = logs.map(l => {
      let typeBadge = 'badge-comment';
      if (l.action_type.includes('弹幕')) typeBadge = 'badge-danmaku';
      else if (l.action_type.includes('私信')) typeBadge = 'badge-pm';
      else if (l.action_type.includes('抽帧')) typeBadge = 'badge-vision';

      const statusBadge = (l.status === '成功') ? 'badge-success' : 'badge-fail';
      return `
        <tr>
          <td><code style="font-size:12px;">${l.time}</code></td>
          <td><span class="audit-badge ${typeBadge}">${l.action_type}</span></td>
          <td><strong>${l.target || '-'}</strong></td>
          <td style="max-width:340px; word-break:break-all;">${l.content || '-'}</td>
          <td><span class="audit-badge ${statusBadge}">${l.status}</span></td>
          <td style="font-size:12px; color:#6b7280;">${l.details || '-'}</td>
        </tr>
      `;
    }).join('');
  }

  async function sendTestPm() {
    const uid = document.getElementById('testPmUid').value;
    const content = document.getElementById('testPmText').value;
    const statusSpan = document.getElementById('pmSendStatus');

    if (!uid) {
      showToast('请先输入主人的 UID！');
      return;
    }

    statusSpan.style.color = '#4b5563';
    statusSpan.innerText = '正在发送私信...';

    try {
      const res = await fetch('/api/send_pm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ receiver_uid: parseInt(uid), content })
      });
      const data = await res.json();
      if (data.success) {
        statusSpan.style.color = '#059669';
        statusSpan.innerText = '🎉 发送成功！请检查 B 站私信箱！';
        showToast('私信已发送成功！');
      } else {
        statusSpan.style.color = '#dc2626';
        statusSpan.innerText = `⚠ 失败: ${data.message} (错误码: ${data.code || '-'})`;
        showToast('发送失败: ' + data.message);
      }
      loadStatus();
    } catch(e) {
      statusSpan.style.color = '#dc2626';
      statusSpan.innerText = '网络异常: ' + e;
    }
  }

  async function refreshMessages() {
    // 1. 获取 @我的消息
    try {
      const atRes = await fetch('/api/at_notifications');
      const atData = await atRes.json();
      const atCont = document.getElementById('atNotificationsList');
      if (atData.items && atData.items.length > 0) {
        atCont.innerHTML = atData.items.map(it => `
          <div style="padding:10px; border-bottom:1px solid #e5e7eb;">
            <strong>${it.user ? it.user.nickname : '用户'}</strong> 在 <code>${it.item ? it.item.subject_id : '动态/视频'}</code> 中 @ 了猫娘:
            <div style="background:#f1f5f9; padding:6px 10px; border-radius:4px; margin-top:4px;">${it.item ? it.item.source_content : '-'}</div>
          </div>
        `).join('');
      } else {
        atCont.innerHTML = '<div style="color:#9ca3af; padding:8px 0;">目前暂无未读的 @我的通知（如果在 B 站评论区 @ 猫娘账号，这里即可捕获！）。</div>';
      }
    } catch(e) {}

    // 2. 获取私信会话
    try {
      const sRes = await fetch('/api/sessions');
      const sData = await sRes.json();
      const sCont = document.getElementById('sessionsList');
      if (sData.sessions && sData.sessions.length > 0) {
        sCont.innerHTML = sData.sessions.map(s => {
          let lastMsgTxt = '-';
          try {
            const parsed = JSON.parse(s.last_msg.content);
            lastMsgTxt = parsed.content || JSON.stringify(parsed);
          } catch(e) {
            lastMsgTxt = s.last_msg ? s.last_msg.content : '-';
          }
          return `
            <div style="padding:10px; border-bottom:1px solid #e5e7eb; display:flex; justify-content:space-between; align-items:center;">
              <div>
                <strong>会话对象 UID: ${s.talker_id}</strong>
                <div style="font-size:12.5px; color:#4b5563; margin-top:3px;">最新消息: ${lastMsgTxt}</div>
              </div>
              <span style="font-size:11.5px; color:#9ca3af;">会话状态活跃</span>
            </div>
          `;
        }).join('');
      } else {
        sCont.innerHTML = '<div style="color:#9ca3af; padding:8px 0;">暂无私信会话记录。</div>';
      }
    } catch(e) {}
  }

  async function triggerCruise() {
    showToast('🚀 正在召唤闪闪出击巡航...');
    try {
      const res = await fetch('/api/cruise', { method: 'POST' });
      const data = await res.json();
      showToast(data.message);
      switchTab('tab-cruise');
      setTimeout(loadStatus, 4000);
    } catch(e) {
      showToast('调用失败: ' + e);
    }
  }

  async function triggerMorning() {
    showToast('正在生成晨思手记...');
    const res = await fetch('/api/morning_journal', { method: 'POST' });
    const data = await res.json();
    showToast(data.message);
    loadJournals();
  }

  async function triggerEvening() {
    showToast('正在生成晚读手记...');
    const res = await fetch('/api/evening_journal', { method: 'POST' });
    const data = await res.json();
    showToast(data.message);
    loadJournals();
  }

  async function clearAuditLogs() {
    if (!confirm('确定清空当前全部互动操作审计流水吗？')) return;
    await fetch('/api/clear_audit', { method: 'POST' });
    showToast('审计流水已清空');
    loadStatus();
  }

  async function saveFullConfig() {
    const roleName = (document.getElementById('cfgRoleName')?.value || '闪闪').trim();
    const selfName = (document.getElementById('cfgSelfName')?.value || '我').trim();
    const callMaster = (document.getElementById('cfgCallMaster')?.value || '主人').trim();
    const uid = parseInt(document.getElementById('cfgMasterUid').value) || 0;
    const name = (document.getElementById('cfgMasterName').value || '主人').trim();
    const atThresh = parseFloat(document.getElementById('cfgAtThreshold').value) || 8.0;
    const prefStr = document.getElementById('cfgKeywordsPrefer').value;
    const blStr = document.getElementById('cfgKeywordsBlacklist').value;

    const payload = {
      config: {
        profile: {
          role_name: roleName,
          self_name: selfName,
          call_master: callMaster,
          master_uid: uid,
          master_name: name
        },
        interaction: { at_score_threshold: atThresh },
        preferences: {
          keywords_prefer: prefStr.split(/[,，]/).map(s => s.trim()).filter(Boolean),
          blacklist_keywords: blStr.split(/[,，]/).map(s => s.trim()).filter(Boolean)
        }
      }
    };

    try {
      const res = await fetch('/api/save_config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      showToast(data.message || '配置已成功保存并即时生效！');
      loadStatus();
    } catch(e) {
      showToast('保存失败: ' + e);
    }
  }

  async function loadJournals() {
    try {
      const res = await fetch('/api/journals');
      const data = await res.json();
      const cont = document.getElementById('journalsList');
      if (!data.journals || data.journals.length === 0) {
        cont.innerHTML = '<div style="color:#9ca3af; padding:20px;">暂无归档手记</div>';
        return;
      }
      cont.innerHTML = data.journals.map(j => `
        <div class="eval-card" style="padding:14px 18px;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <strong>📄 ${j.filename}</strong>
            <span style="font-size:12px; color:#6b7280;">${j.mtime}</span>
          </div>
          <div style="font-size:12.5px; color:#4b5563; margin-top:8px; line-height:1.5;">${j.snippet}...</div>
        </div>
      `).join('');
    } catch(e) {}
  }

  async function loadGallery() {
    const list = [
      { name: "Gemini猫娘_双形态全景立绘_星空与校园.jpg", title: "双形态全景概念大图", desc: "星空战袍与青春校园对比" },
      { name: "Gemini猫娘_赛博猫娘主视觉海报.jpg", title: "官方概念主海报", desc: "标志性异色双瞳与猫耳耳机" },
      { name: "Gemini猫娘_伴生羁绊概念全景.jpg", title: "伴生羁绊概念插画", desc: "夜间终端桌前赛博守候" },
      { name: "Gemini猫娘_女仆装_正面立绘_透明底.png", title: "经典蓝白科技女仆装", desc: "姐姐卡拉深研守护战袍" },
      { name: "Gemini猫娘_水手校服_正面立绘_透明底.png", title: "青春水手校服", desc: "妹妹闪闪冲浪常驻战袍" },
      { name: "Gemini猫娘_原版常服_正面立绘_透明底.png", title: "深海蓝极客连帽衫", desc: "居家写代码排错常服" }
    ];
    document.getElementById('galleryContainer').innerHTML = list.map(item => `
      <div class="outfit-card">
        <div class="outfit-preview">
          <img src="/images/${item.name}" alt="${item.title}">
        </div>
        <div class="outfit-meta">
          <div class="outfit-title">${item.title}</div>
          <div class="outfit-desc">${item.desc}</div>
        </div>
      </div>
    `).join('');
  }

  // 初始加载与定时轮询
  loadStatus();
  setInterval(loadStatus, 5000);
</script>
</body>
</html>
"""


def run_server(port=8765):
    server_address = ("", port)
    httpd = HTTPServer(server_address, HajimiWebHandler)
    print(f"\n=======================================================")
    print(f"🐾 赛博养Gemini · 全息监控与伴生中枢已启动！")
    print(f"👉 独立浏览器大屏访问: http://localhost:{port}")
    print(f"👉 Antigravity Sidecar: 深度适配原生抽屉视窗")
    print(f"=======================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[WebUI] 控制台服务已安全停止。")


if __name__ == "__main__":
    port = 8765
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run_server(port)
