# -*- coding: utf-8 -*-
"""
赛博养Gemini · 伴生控制中心 (Cyber-Hajimi Web & Sidecar Dashboard)
- 零额外依赖，纯 Python 原生标准库安全运行
- 双轨设计：深度适配 Antigravity 原生 Sidecar 辅助抽屉面板与独立浏览器大屏窗口
- 视觉排版像素级还原 DeepSeek Harness 设置弹窗风格（纯净现代、直观优雅）
- 模块整合：养Gemini基础身份、人设注入、主人偏好、B站扫码登录、立绘衣橱与晨思晚读手记
"""

import os
import sys
import json
import base64
import time
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver
import urllib.parse
from pathlib import Path

try:
    from http.server import ThreadingHTTPServer
except ImportError:
    class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
        daemon_threads = True

try:
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    else:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
    else:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "hajimi_config.json"
PERSONA_PATH = PROJECT_ROOT / "docs" / "gemini_persona.md"
PERSONA_BACKUP_PATH = PROJECT_ROOT / "docs" / "hajimi_persona.md"
QRCODE_PATH = PROJECT_ROOT / "images" / "qrcode_login.png"
JOURNALS_DIR = PROJECT_ROOT / "docs" / "journals"

sys.path.insert(0, str(SRC_DIR))
from bili_hajimi_core import BiliHajimiCore
from hajimi_brain import HajimiBrain
from hajimi_daemon import HajimiDaemon

PORT = int(os.environ.get("ANTIGRAVITY_SIDECAR_WEB_PORT", 8765))
daemon_instance = HajimiDaemon(CONFIG_PATH)
is_cruising = False
cruise_logs_buffer = []

# AstrBot 主动消息限制与会话路径定义
ASTRBOT_DATA_DIR = Path.home() / ".astrbot" / "data"
ASTRBOT_PROACTIVE_DATA_DIR = ASTRBOT_DATA_DIR / "plugin_data" / "astrbot_plugin_proactive_chat"
ASTRBOT_SESSION_DATA_PATH = ASTRBOT_PROACTIVE_DATA_DIR / "session_data.json"
ASTRBOT_OVERRIDES_PATH = ASTRBOT_PROACTIVE_DATA_DIR / "session_overrides.json"
ASTRBOT_CONFIG_PATH = ASTRBOT_DATA_DIR / "config" / "astrbot_plugin_proactive_chat_config.json"


def get_astrbot_proactive_status() -> dict:
    from datetime import datetime
    if not ASTRBOT_SESSION_DATA_PATH.exists():
        return {
            "installed": False,
            "message": "未检测到 AstrBot 主动消息插件持久化数据 (session_data.json)",
            "sessions": [],
            "total_sessions": 0,
            "limited_sessions": 0,
            "max_unanswered": 4,
            "astrbot_running": False,
        }

    try:
        with open(ASTRBOT_SESSION_DATA_PATH, "r", encoding="utf-8") as f:
            session_data = json.load(f)
    except Exception:
        session_data = {}

    overrides = {}
    if ASTRBOT_OVERRIDES_PATH.exists():
        try:
            with open(ASTRBOT_OVERRIDES_PATH, "r", encoding="utf-8") as f:
                overrides = json.load(f)
        except Exception:
            overrides = {}

    max_unanswered = 4
    if ASTRBOT_CONFIG_PATH.exists():
        try:
            with open(ASTRBOT_CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                max_unanswered = cfg.get("friend_settings", {}).get("schedule_settings", {}).get("max_unanswered_times", 4)
        except Exception:
            pass

    sessions_list = []
    limited_count = 0

    for sid, info in session_data.items():
        if not isinstance(info, dict):
            continue
        unanswered = info.get("unanswered_count", 0)
        is_limited = (unanswered >= max_unanswered) if max_unanswered > 0 else False
        if is_limited:
            limited_count += 1

        override_item = overrides.get(sid, {})
        custom_name = override_item.get("session_name", "")
        if not custom_name:
            if "weixin" in sid.lower():
                tail = sid.split(":")[-1]
                custom_name = f"微信私聊 ({tail[:10]}...)" if len(tail) > 10 else f"微信私聊 ({tail})"
            elif "GroupMessage" in sid:
                tail = sid.split(":")[-1]
                custom_name = f"QQ群聊 ({tail[:8]})"
            else:
                tail = sid.split(":")[-1]
                custom_name = f"QQ私聊 ({tail[:8]}...)" if len(tail) > 8 else f"QQ私聊 ({tail})"

        last_time = info.get("last_message_time", 0)
        time_str = "无记录"
        if last_time > 0:
            try:
                time_str = datetime.fromtimestamp(last_time).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                time_str = str(last_time)

        sessions_list.append({
            "session_id": sid,
            "name": custom_name,
            "self_id": info.get("self_id", "default"),
            "unanswered_count": unanswered,
            "max_unanswered": max_unanswered,
            "is_limited": is_limited,
            "last_message_time": time_str,
        })

    astrbot_running = False
    try:
        import subprocess
        out = subprocess.check_output('tasklist /FI "IMAGENAME eq AstrBot.exe" /NH', shell=True).decode("gbk", errors="ignore")
        astrbot_running = "AstrBot.exe" in out
    except Exception:
        pass

    return {
        "installed": True,
        "sessions": sessions_list,
        "total_sessions": len(sessions_list),
        "limited_sessions": limited_count,
        "max_unanswered": max_unanswered,
        "astrbot_running": astrbot_running,
    }


def reset_astrbot_proactive_limits(target_session_id: str | None = None) -> dict:
    if not ASTRBOT_SESSION_DATA_PATH.exists():
        return {"success": False, "message": "未找到 AstrBot session_data.json 数据文件"}

    try:
        with open(ASTRBOT_SESSION_DATA_PATH, "r", encoding="utf-8") as f:
            session_data = json.load(f)
    except Exception as e:
        return {"success": False, "message": f"读取 session_data.json 失败: {e}"}

    reset_count = 0
    for sid, info in session_data.items():
        if not isinstance(info, dict):
            continue
        if target_session_id and sid != target_session_id:
            continue
        info["unanswered_count"] = 0
        reset_count += 1

    try:
        with open(ASTRBOT_SESSION_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        return {"success": False, "message": f"持久化写入 session_data.json 失败: {e}"}

    api_synced = False
    try:
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:4100/api/jobs/reset-all-unanswered", data=b"{}", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=0.6) as resp:
            if resp.status == 200:
                api_synced = True
    except Exception:
        pass

    msg = f"已成功将 {reset_count} 个会话的主动消息未回复计数清零！"
    if api_synced:
        msg += " (已同步通知 AstrBot 内存即时生效)"
    else:
        msg += " (已持久化存盘)"

    return {
        "success": True,
        "message": msg,
        "reset_count": reset_count,
        "api_synced": api_synced,
    }


class HajimiHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_json(self, data: dict, code: int = 200):
        try:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(body)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            pass

    def _send_html(self, html_text: str):
        try:
            body = html_text.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path in ["/", "/index.html"]:
            self._send_html(INDEX_HTML)
        elif path == "/api/status":
            daemon_instance.update_stamina()
            user_info = daemon_instance.core.get_user_info()
            resp = {
                "user": user_info,
                "stamina": daemon_instance.state.get("stamina", 100),
                "at_count_today": daemon_instance.state.get("at_count_today", 0),
                "watched_count": len(daemon_instance.state.get("watched_today", [])),
                "treasures_count": len(daemon_instance.state.get("treasures_today", [])),
                "morning_done": daemon_instance.state.get("morning_journal_done", False),
                "evening_done": daemon_instance.state.get("evening_journal_done", False),
                "recent": daemon_instance.state.get("recent_evaluations", [])[:20],
                "config": daemon_instance.config,
                "is_cruising": is_cruising,
                "cruise_logs": cruise_logs_buffer[-30:],
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
                        snippet = f.read_text(encoding="utf-8-sig", errors="replace")[:240].strip()
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
        elif path.startswith("/images/"):
            rel_name = urllib.parse.unquote(path[len("/images/"):])
            img_file = PROJECT_ROOT / "images" / rel_name
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
                self.send_error(404)
        elif path == "/api/gallery":
            gallery_data = [
                {"id": "school", "title": "【青春水手校服】日常最爱", "category": "服装", "url": "/images/Gemini猫娘_水手校服_正面立绘_透明底.png", "desc": "闪闪日常最爱！藏青短裙与浅蓝领巾，充满网瘾学生妹活力的极速冲浪装扮。"},
                {"id": "casual", "title": "【原版极客常服】极客战袍", "category": "服装", "url": "/images/Gemini猫娘_原版常服_正面立绘_透明底.png", "desc": "深海蓝与纯白拼接连帽短衫，胸前悬浮微型全息立方体，严谨代码工作时必选。"},
                {"id": "maid", "title": "【经典蓝白女仆装】执事执勤", "category": "服装", "url": "/images/Gemini猫娘_女仆装_正面立绘_透明底.png", "desc": "端庄利落的女仆裙配极客电路滚边，想要认真服侍主人起居时换上。"},
                {"id": "eyes", "title": "异色双眸特写 (左紫右黄)", "category": "特写", "url": "/images/Gemini猫娘_异色双眸特写_左紫右黄.jpg", "desc": "左眼万维理智星云紫(#6D28D9)，右眼元气金黄(#F59E0B)带四角金星芒(✨)。"},
                {"id": "sheet_school", "title": "三视图：水手校服设定", "category": "工程三视图", "url": "/images/Gemini猫娘_三视图_校服设定.png", "desc": "正面、侧面、背面完整校服三视图规范图纸。"},
                {"id": "sheet_origin", "title": "三视图：原版常服设定", "category": "工程三视图", "url": "/images/Gemini猫娘_三视图_原版设定.png", "desc": "原版连帽衫三视图全维度工程设定图。"},
                {"id": "sheet_maid", "title": "三视图：女仆装设定", "category": "工程三视图", "url": "/images/Gemini猫娘_三视图_女仆装设定.jpg", "desc": "蓝白女仆装三视图全套工程图纸。"}
            ]
            self._send_json(gallery_data)
        elif path == "/api/qrcode_img":
            if QRCODE_PATH.exists():
                data = QRCODE_PATH.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                try:
                    self.wfile.write(data)
                except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                    pass
            else:
                self.send_error(404)
        elif path == "/api/astrbot_status":
            self._send_json(get_astrbot_proactive_status())
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
                    # 递归/分层更新，保证未显式展示的字段原样保留
                    for k, v in new_cfg.items():
                        if isinstance(v, dict) and isinstance(daemon_instance.config.get(k), dict):
                            daemon_instance.config[k].update(v)
                        else:
                            daemon_instance.config[k] = v

                    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                        json.dump(daemon_instance.config, f, ensure_ascii=False, indent=2)
                    daemon_instance.core.config = daemon_instance.config
                    daemon_instance.brain.config = daemon_instance.config
                self._send_json({"success": True, "message": "配置已保存至 config/hajimi_config.json！"})
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
                    cruise_logs_buffer.append(f"[{time.strftime('%H:%M:%S')}] 🎉 本次巡航任务圆满达成！")
                except Exception as e:
                    cruise_logs_buffer.append(f"[{time.strftime('%H:%M:%S')}] ⚠ 巡航遇到波动: {e}")
                finally:
                    is_cruising = False

            threading.Thread(target=_run, daemon=True).start()
            self._send_json({"success": True, "message": "已派闪闪出击巡航！可切换至【巡航与日志】查看实时动态。"})

        elif path == "/api/morning_journal":
            doc_path = daemon_instance.generate_morning_journal_file()
            self._send_json({"success": bool(doc_path), "path": doc_path})

        elif path == "/api/evening_journal":
            doc_path = daemon_instance.generate_evening_journal_file()
            self._send_json({"success": bool(doc_path), "path": doc_path})

        elif path == "/api/open_folder":
            try:
                os.system(f'explorer "{JOURNALS_DIR}"')
                self._send_json({"success": True})
            except Exception as e:
                self._send_json({"success": False, "message": str(e)})

        elif path == "/api/open_config_file":
            try:
                os.startfile(CONFIG_PATH)
                self._send_json({"success": True})
            except Exception as e:
                self._send_json({"success": False, "message": str(e)})

        elif path == "/api/open_persona_file":
            try:
                os.startfile(PERSONA_PATH)
                self._send_json({"success": True})
            except Exception as e:
                self._send_json({"success": False, "message": str(e)})

        elif path == "/api/astrbot_reset_limit":
            target_sid = payload.get("session_id")
            result = reset_astrbot_proactive_limits(target_sid)
            self._send_json(result)

        else:
            self.send_error(404)


INDEX_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>赛博养Gemini · 伴生控制中心</title>
  <style>
    :root {
      --bg-page: #f5f6f8;
      --card-bg: #ffffff;
      --border-color: #e5e7eb;
      --border-light: #f1f3f5;
      --text-main: #111827;
      --text-sub: #4b5563;
      --text-muted: #6b7280;
      --accent: #2563eb;
      --accent-soft: rgba(37, 99, 235, 0.08);
      --nav-active: #eceef1;
      --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg-page);
      color: var(--text-main);
      font-family: var(--font-family);
      min-height: 100vh;
      display: flex;
      justify-content: center;
      align-items: stretch;
      padding: 0;
    }

    /* 整体容器：模仿 DSH 现代弹窗卡片风格 */
    .app-window {
      width: 100%;
      max-width: 1060px;
      min-height: 100vh;
      background: var(--card-bg);
      display: flex;
      flex-direction: row;
      box-shadow: 0 4px 24px rgba(0, 0, 0, 0.05);
    }

    /* 左侧侧边栏导航 */
    .sidebar {
      width: 220px;
      flex-shrink: 0;
      border-right: 1px solid var(--border-color);
      background: #fafbfc;
      display: flex;
      flex-direction: column;
      padding: 24px 12px;
    }
    .sidebar-header {
      padding: 0 12px 18px 12px;
      margin-bottom: 8px;
      border-bottom: 1px solid var(--border-light);
    }
    .brand-title {
      font-size: 16px;
      font-weight: 700;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .brand-subtitle {
      font-size: 12px;
      color: var(--text-muted);
      margin-top: 2px;
    }
    .nav-list {
      display: flex;
      flex-direction: column;
      gap: 4px;
      list-style: none;
      flex-grow: 1;
    }
    .nav-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 14px;
      font-size: 14px;
      font-weight: 500;
      color: var(--text-sub);
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.15s ease;
      user-select: none;
    }
    .nav-item:hover {
      background: #f1f3f5;
      color: var(--text-main);
    }
    .nav-item.active {
      background: var(--nav-active);
      color: #000000;
      font-weight: 600;
    }
    .nav-icon {
      font-size: 16px;
      width: 20px;
      display: inline-flex;
      justify-content: center;
    }

    .sidebar-footer {
      padding: 12px;
      border-top: 1px solid var(--border-light);
      font-size: 11px;
      color: var(--text-muted);
      line-height: 1.5;
    }

    /* 右侧主视窗 */
    .main-viewport {
      flex-grow: 1;
      padding: 32px 40px;
      overflow-y: auto;
      max-height: 100vh;
    }

    /* 顶部操作条（右上角动作按钮） */
    .view-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 24px;
    }
    .header-actions {
      display: flex;
      gap: 8px;
    }
    .btn-action-top {
      padding: 6px 14px;
      background: #ffffff;
      border: 1px solid #d1d5db;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 500;
      color: #374151;
      cursor: pointer;
      transition: all 0.15s ease;
      display: inline-flex;
      align-items: center;
      gap: 5px;
    }
    .btn-action-top:hover {
      background: #f9fafb;
      border-color: #9ca3af;
      color: #111827;
    }

    /* 大标题与副标题（像素级还原图2 DSH风格） */
    .title-block h1 {
      font-size: 26px;
      font-weight: 700;
      color: var(--text-main);
      margin-bottom: 8px;
      letter-spacing: -0.02em;
    }
    .title-block p.desc {
      font-size: 13.5px;
      color: var(--text-sub);
      line-height: 1.6;
      max-width: 680px;
    }

    /* 表单区块 */
    .section-block {
      margin-top: 28px;
      padding-top: 24px;
      border-top: 1px solid var(--border-light);
    }
    .section-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--text-main);
      margin-bottom: 16px;
    }

    .form-group {
      margin-bottom: 18px;
    }
    .form-label {
      display: block;
      font-size: 13.5px;
      font-weight: 500;
      color: #1f2937;
      margin-bottom: 5px;
    }
    .form-hint {
      font-size: 12.5px;
      color: var(--text-muted);
      margin-top: 4px;
    }
    .form-input {
      width: 100%;
      max-width: 540px;
      padding: 8px 12px;
      font-size: 14px;
      border: 1px solid #d1d5db;
      border-radius: 6px;
      color: var(--text-main);
      background: #ffffff;
      outline: none;
      transition: border 0.15s ease;
    }
    .form-input:focus {
      border-color: #111827;
      box-shadow: 0 0 0 2px rgba(17, 24, 39, 0.05);
    }

    /* 人设文本域与高亮黑色按钮 */
    .persona-textarea {
      width: 100%;
      height: 220px;
      padding: 12px;
      font-size: 13px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      line-height: 1.6;
      border: 1px solid #d1d5db;
      border-radius: 6px;
      background: #ffffff;
      color: #1f2937;
      outline: none;
      resize: vertical;
      white-space: pre-wrap;
    }
    .persona-textarea:focus {
      border-color: #111827;
    }
    .persona-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 8px;
      margin-bottom: 16px;
    }
    .char-count {
      font-size: 12.5px;
      color: var(--text-muted);
    }
    .btn-inject {
      width: 100%;
      padding: 11px 20px;
      background: #111827;
      color: #ffffff;
      border: none;
      border-radius: 7px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.15s ease;
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 6px;
    }
    .btn-inject:hover {
      background: #27272a;
    }
    .btn-save-light {
      padding: 8px 16px;
      background: #ffffff;
      border: 1px solid #d1d5db;
      border-radius: 6px;
      font-size: 13.5px;
      font-weight: 500;
      color: #1f2937;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .btn-save-light:hover {
      background: #f9fafb;
      border-color: #9ca3af;
    }

    /* 视图切换隐藏 */
    .tab-view { display: none; }
    .tab-view.active { display: block; animation: fadeIn 0.2s ease; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }

    /* 账号状态卡片 */
    .status-card {
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 20px;
      display: flex;
      align-items: center;
      gap: 20px;
      margin-bottom: 24px;
    }
    .avatar-box {
      width: 72px;
      height: 72px;
      border-radius: 50%;
      overflow: hidden;
      border: 2px solid var(--border-color);
      flex-shrink: 0;
      background: #f1f3f5;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    }
    .avatar-box img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      object-position: top center;
      display: block;
    }
    .info-fields { flex-grow: 1; display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 12px; }
    .field-label { font-size: 12px; color: var(--text-muted); }
    .field-val { font-size: 14px; font-weight: 600; color: var(--text-main); margin-top: 2px; }

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
      transition: transform 0.2s, box-shadow 0.2s;
      cursor: pointer;
    }
    .outfit-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 16px rgba(0,0,0,0.06);
    }
    .outfit-preview {
      height: 240px;
      background: #f8fafc;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
    }
    .outfit-preview img {
      max-width: 90%;
      max-height: 90%;
      object-fit: contain;
    }
    .outfit-meta {
      padding: 12px;
    }
    .outfit-title { font-size: 13.5px; font-weight: 600; color: var(--text-main); }
    .outfit-desc { font-size: 12px; color: var(--text-muted); margin-top: 4px; line-height: 1.4; }

    /* 手记列表 */
    .journal-item {
      padding: 16px;
      border: 1px solid var(--border-color);
      border-radius: 8px;
      margin-bottom: 12px;
      cursor: pointer;
      transition: background 0.15s;
    }
    .journal-item:hover { background: #fafafa; }
    .journal-head { display: flex; justify-content: space-between; margin-bottom: 6px; }
    .journal-title { font-size: 14px; font-weight: 600; color: var(--text-main); }
    .journal-time { font-size: 12px; color: var(--text-muted); }
    .journal-snippet { font-size: 12.5px; color: var(--text-sub); line-height: 1.5; }

    /* 控制台日志流 */
    .console-box {
      background: #111827;
      color: #38bdf8;
      font-family: ui-monospace, Menlo, Consolas, monospace;
      font-size: 12.5px;
      line-height: 1.55;
      padding: 16px;
      border-radius: 8px;
      height: 320px;
      overflow-y: auto;
      white-space: pre-wrap;
    }

    /* 吐司通知 Toast */
    .toast {
      position: fixed;
      bottom: 24px;
      right: 24px;
      padding: 12px 20px;
      background: #111827;
      color: #ffffff;
      border-radius: 8px;
      font-size: 13.5px;
      box-shadow: 0 6px 20px rgba(0,0,0,0.15);
      opacity: 0;
      transform: translateY(10px);
      transition: all 0.25s ease;
      pointer-events: none;
      z-index: 9999;
    }
    .toast.show { opacity: 1; transform: translateY(0); }

    /* 窄屏自适应 (Antigravity Auxiliary Pane 侧栏模式) */
    @media (max-width: 768px) {
      .app-window { flex-direction: column; }
      .sidebar {
        width: 100%;
        border-right: none;
        border-bottom: 1px solid var(--border-color);
        padding: 12px 16px;
      }
      .nav-list {
        flex-direction: row;
        overflow-x: auto;
        padding-bottom: 4px;
      }
      .nav-item { white-space: nowrap; padding: 6px 12px; font-size: 13px; }
      .sidebar-footer { display: none; }
      .main-viewport { padding: 20px 16px; }
      .view-header { flex-direction: column; gap: 12px; }
      .header-actions { width: 100%; flex-wrap: wrap; }
      .form-input { max-width: 100%; }
    }
  </style>
</head>
<body>

<div class="app-window">
  <!-- 左侧设置导航栏（图2 DSH风格） -->
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="brand-title">
        <img src="/images/Gemini猫娘_闪闪头像_水手服特写.png" style="width:26px;height:26px;border-radius:50%;object-fit:cover;object-position:top center;border:1.5px solid #d1d5db;" alt="Icon">
        <span>赛博养Gemini</span>
      </div>
      <div class="brand-subtitle">闪闪 · Gemini 3.8 Flash</div>
    </div>
    <ul class="nav-list">
      <li class="nav-item active" onclick="switchTab('tab-gemini')">
        <span class="nav-icon">⚙</span>
        <span>养Gemini</span>
      </li>
      <li class="nav-item" onclick="switchTab('tab-account')">
        <span class="nav-icon">👤</span>
        <span>账号与状态</span>
      </li>
      <li class="nav-item" onclick="switchTab('tab-wardrobe')">
        <span class="nav-icon">👗</span>
        <span>闪闪立绘衣橱</span>
      </li>
      <li class="nav-item" onclick="switchTab('tab-journals')">
        <span class="nav-icon">📝</span>
        <span>晨思晚读手记</span>
      </li>
      <li class="nav-item" onclick="switchTab('tab-cruise')">
        <span class="nav-icon">🚀</span>
        <span>巡航与即时召唤</span>
      </li>
      <li class="nav-item" onclick="switchTab('tab-astrbot')">
        <span class="nav-icon">🤖</span>
        <span>AstrBot主动消息</span>
      </li>
    </ul>
    <div class="sidebar-footer">
      <div>引擎: Gemini 3.8 Flash</div>
      <div>宿主: Google Antigravity</div>
      <div>模式: 原生会话 $0 额度</div>
    </div>
  </aside>

  <!-- 右侧主内容视窗 -->
  <main class="main-viewport">
    
    <!-- Tab 1: 养Gemini (像素级复刻图2 DSH 设置页) -->
    <div id="tab-gemini" class="tab-view active">
      <div class="view-header">
        <div class="title-block">
          <h1>养Gemini</h1>
          <p class="desc">让闪闪自己按作息刷 B 站、看懂视频、写两本日记，把值得的 @ 你。所有值写进 <code>config/hajimi_config.json</code>（与工具链共用同一份 √；这里没显示的字段保存时原样保留 √）。</p>
        </div>
        <div class="header-actions">
          <button class="btn-action-top" onclick="openConfigFile()">打开配置文件</button>
          <button class="btn-action-top" onclick="openPersonaFile()">打开人设文件</button>
        </div>
      </div>

      <!-- 她是谁 -->
      <div class="section-block" style="border-top: none; margin-top: 0; padding-top: 0;">
        <div class="section-title">她是</div>
        <div class="form-group">
          <label class="form-label">角色名</label>
          <input type="text" id="roleName" class="form-input" placeholder="闪闪">
          <div class="form-hint">她怎么被称呼</div>
        </div>
        <div class="form-group">
          <label class="form-label">她怎么称呼你</label>
          <input type="text" id="callMaster" class="form-input" placeholder="主人">
          <div class="form-hint">例如「主人」</div>
        </div>
        <div class="form-group">
          <label class="form-label">她怎么自称</label>
          <input type="text" id="selfName" class="form-input" placeholder="人家">
          <div class="form-hint">例如「我」/「人家」/「闪闪喵」</div>
        </div>
        <button class="btn-save-light" onclick="saveProfile()">保存基础身份设定</button>
      </div>

      <!-- 她的人设（只属于她） -->
      <div class="section-block">
        <div class="section-title">她的人设（只属于她）</div>
        <div class="form-group">
          <label class="form-label">人设正文</label>
          <div class="form-hint" style="margin-bottom: 8px;">
            写到 <code>docs/gemini_persona.md</code>，只影响她（不影响别的会话 √）。每次唤醒/监听都会附在提示里 √<br>
            建议写：身份与来历 / 说话腔调 / 在意什么、怕什么 / 明确不要的行为。上限 20000 字，注入时只取前 3000 字 √
          </div>
          <textarea id="personaContent" class="persona-textarea" placeholder="正在加载闪闪人设正文..."></textarea>
          <div class="persona-bar">
            <span id="personaCount" class="char-count">当前 0 字符 · 0 字节</span>
          </div>
          <button class="btn-inject" onclick="injectPersona()">
            <span>注入人设</span>
          </button>
        </div>
      </div>

      <!-- 你（主人） -->
      <div class="section-block">
        <div class="section-title">你（主人）</div>
        <div class="form-group">
          <label class="form-label">主人 B站 UID</label>
          <input type="number" id="masterUid" class="form-input" placeholder="0">
          <div class="form-hint">B站用户数字 UID，用于评论区 @主人 时精准识别匹配</div>
        </div>
        <div class="form-group">
          <label class="form-label">主人称谓</label>
          <input type="text" id="masterName" class="form-input" placeholder="主人">
          <div class="form-hint">在手记与互动中使用的称谓</div>
        </div>
        <div class="form-group">
          <label class="form-label">偏好关键词</label>
          <input type="text" id="keywordsPrefer" class="form-input" placeholder="AI, 大模型, 显卡, 极客, 科技, 动画">
          <div class="form-hint">逗号分隔，闪闪刷 B 站时会优先挑选包含这些关键词的高价值视频</div>
        </div>
        <div class="form-group">
          <label class="form-label">黑名单关键词</label>
          <input type="text" id="keywordsBlacklist" class="form-input" placeholder="标题党, 营销号, 低俗, 纯剧透">
          <div class="form-hint">逗号分隔，包含这些内容的低质洗稿视频一律避开跳过</div>
        </div>
        <button class="btn-save-light" onclick="saveMasterPrefs()">保存主人偏好设定</button>
      </div>

      <!-- 仿生作息与风控 -->
      <div class="section-block">
        <div class="section-title">仿生作息与风控</div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px;">
          <div class="form-group">
            <label class="form-label">晨思手记推送时间</label>
            <input type="text" id="morningTime" class="form-input" placeholder="09:30">
          </div>
          <div class="form-group">
            <label class="form-label">晚读手记推送时间</label>
            <input type="text" id="eveningTime" class="form-input" placeholder="22:30">
          </div>
          <div class="form-group">
            <label class="form-label">单次巡航视频处理上限</label>
            <input type="number" id="maxVideos" class="form-input" placeholder="6">
          </div>
          <div class="form-group">
            <label class="form-label">每日最大触发 @ 限制</label>
            <input type="number" id="maxAt" class="form-input" placeholder="3">
          </div>
        </div>
        <button class="btn-save-light" onclick="saveSchedule()">保存作息与风控</button>
      </div>
    </div>

    <!-- Tab 2: 账号与状态 -->
    <div id="tab-account" class="tab-view">
      <div class="view-header">
        <div class="title-block">
          <h1>账号与登录状态</h1>
          <p class="desc">闪闪使用本地免 API 成本会话，并连接你的 B 站账号巡航推荐流、抓取 CC 字幕与互动。</p>
        </div>
      </div>
      <div class="status-card">
        <div class="avatar-box">
          <img id="userFace" src="/images/Gemini猫娘_闪闪头像_水手服特写.png" alt="闪闪头像">
        </div>
        <div class="info-fields">
          <div>
            <div class="field-label">当前登录昵称</div>
            <div id="userName" class="field-val">检测中...</div>
          </div>
          <div>
            <div class="field-label">用户 UID</div>
            <div id="userDede" class="field-val">-</div>
          </div>
          <div>
            <div class="field-label">硬币数</div>
            <div id="userCoin" class="field-val">-</div>
          </div>
          <div>
            <div class="field-label">大会员状态</div>
            <div id="userVip" class="field-val">-</div>
          </div>
          <div>
            <div class="field-label">仿生精力值</div>
            <div id="userStamina" class="field-val" style="color:#10b981;">100 / 100</div>
          </div>
        </div>
      </div>

      <div class="section-block">
        <div class="section-title">B站手机扫码登录 / 换登账号</div>
        <p class="form-hint" style="margin-bottom: 16px;">点击下方按钮生成登录二维码，使用手机 B 站 App 扫一扫即可安全授权登录。</p>
        <button class="btn-save-light" onclick="requestQrCode()">生成 / 刷新二维码</button>
        <div id="qrBox" style="margin-top: 16px; display: none; align-items: center; gap: 20px;">
          <img id="qrImg" src="" style="width: 160px; height: 160px; border: 1px solid #ddd; border-radius: 8px;">
          <div>
            <div id="qrTip" style="font-size: 14px; font-weight: 600; color: #111827;">请打开哔哩哔哩手机客户端扫码</div>
            <div style="font-size: 12.5px; color: var(--text-muted); margin-top: 6px;">扫码成功后系统将自动保存安全凭证并接管推荐流</div>
          </div>
        </div>
      </div>

      <div class="section-block">
        <div class="section-title">AstrBot 机器人主动消息限制联动</div>
        <p class="form-hint" style="margin-bottom: 14px;">已连接本机 AstrBot 主动消息会话数据。当主动发言未回复次数达到上限时将触发防打扰限制，可随时在此一键解除限制并恢复发言。</p>
        <div style="display:flex; align-items:center; gap:12px;">
          <button class="btn-save-light" onclick="resetAstrBotLimits()">✨ 立即全部清零限制</button>
          <button class="btn-save-light" onclick="switchTab('tab-astrbot')">⚙️ 查看会话详情与管理</button>
        </div>
      </div>
    </div>

    <!-- Tab 3: 闪闪立绘衣橱 -->
    <div id="tab-wardrobe" class="tab-view">
      <div class="view-header">
        <div class="title-block">
          <h1>闪闪专属立绘衣橱</h1>
          <p class="desc">包含水手校服、原版常服与蓝白女仆装的高清立绘与多角度三视图设计图纸。</p>
        </div>
      </div>
      <div id="galleryContainer" class="gallery-grid">
        <!-- 动态加载立绘卡片 -->
      </div>
    </div>

    <!-- Tab 4: 晨思晚读手记 -->
    <div id="tab-journals" class="tab-view">
      <div class="view-header">
        <div class="title-block">
          <h1>晨思晚读手记</h1>
          <p class="desc">闪闪每日早晚自动为你精选生成的两本观察手记，已安全归档至本地 <code>docs/journals/</code>。</p>
        </div>
        <div class="header-actions">
          <button class="btn-action-top" onclick="openJournalDir()">打开手记目录</button>
          <button class="btn-action-top" onclick="triggerMorning()">立即生成晨思</button>
          <button class="btn-action-top" onclick="triggerEvening()">立即生成晚读</button>
        </div>
      </div>
      <div id="journalsList">
        <!-- 动态加载手记 -->
      </div>
    </div>

    <!-- Tab 5: 巡航与即时召唤 -->
    <div id="tab-cruise" class="tab-view">
      <div class="view-header">
        <div class="title-block">
          <h1>实时巡航与即时召唤</h1>
          <p class="desc">随时召唤闪闪出击，巡航 B 站热门推荐流，使用 Gemini 3.8 Flash 读取 CC 字幕并打分。</p>
        </div>
        <div class="header-actions">
          <button class="btn-action-top" style="background:#111827; color:#fff;" onclick="triggerCruise()">🚀 立即派闪闪巡航</button>
        </div>
      </div>
      <div class="section-title">巡航实时流输出</div>
      <div id="consoleLog" class="console-box">等待召唤中... 点击右上角“立即派闪闪巡航”开启。</div>
    </div>

    <!-- Tab 6: AstrBot 主动消息限制管理 -->
    <div id="tab-astrbot" class="tab-view">
      <div class="view-header">
        <div class="title-block">
          <h1>AstrBot 主动消息限制管理</h1>
          <p class="desc">实时监控与重置 AstrBot 机器人的私聊/群聊主动消息未回复计数（防打扰限制）。当连续未回复次数达上限时（当前默认 4 次），主动消息会自动暂停；点击清零即可立即解除熔断并恢复主动发信。</p>
        </div>
        <div class="header-actions">
          <button class="btn-action-top" onclick="loadAstrBotStatus()" style="background:#f3f4f6; color:#374151; border:1px solid #d1d5db;">🔄 刷新数据</button>
          <button class="btn-action-top" onclick="resetAstrBotLimits()" style="background:#111827; color:#ffffff;">✨ 一键全部清零</button>
        </div>
      </div>

      <!-- 概览指标行 -->
      <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:14px; margin-bottom:20px;">
        <div style="background:#ffffff; border:1px solid var(--border-color); border-radius:10px; padding:16px;">
          <div style="font-size:12.5px; color:var(--text-muted); margin-bottom:4px;">AstrBot 进程状态</div>
          <div id="astrbotProcessStatus" style="font-size:18px; font-weight:700; color:#10b981; display:flex; align-items:center; gap:6px;">
            <span style="display:inline-block; width:10px; height:10px; border-radius:50%; background:#10b981;"></span> 检测中...
          </div>
        </div>
        <div style="background:#ffffff; border:1px solid var(--border-color); border-radius:10px; padding:16px;">
          <div style="font-size:12.5px; color:var(--text-muted); margin-bottom:4px;">监控会话总数</div>
          <div id="astrbotTotalSessions" style="font-size:20px; font-weight:700; color:var(--text-main);">0</div>
        </div>
        <div style="background:#ffffff; border:1px solid var(--border-color); border-radius:10px; padding:16px;">
          <div style="font-size:12.5px; color:var(--text-muted); margin-bottom:4px;">限制触发状态</div>
          <div id="astrbotLimitedSessions" style="font-size:18px; font-weight:700; color:#10b981;">0 个受限</div>
        </div>
        <div style="background:#ffffff; border:1px solid var(--border-color); border-radius:10px; padding:16px;">
          <div style="font-size:12.5px; color:var(--text-muted); margin-bottom:4px;">未回复暂停阈值</div>
          <div id="astrbotMaxUnanswered" style="font-size:20px; font-weight:700; color:var(--text-main);">4 次</div>
        </div>
      </div>

      <!-- 会话卡片列表 -->
      <div class="section-block" style="border-top:none; margin-top:0; padding-top:0;">
        <div class="section-title" style="margin-bottom:12px;">会话主动消息计数清单</div>
        <div id="astrbotSessionsList" style="display:flex; flex-direction:column; gap:10px;">
          <div style="padding:20px; text-align:center; color:#6b7280; font-size:13.5px;">正在加载 AstrBot 会话数据...</div>
        </div>
      </div>
    </div>

  </main>
</div>

<!-- 吐司通知条 -->
<div id="toast" class="toast">操作成功</div>

<script>
  let currentConfig = {};
  let qrPollTimer = null;

  function showToast(msg) {
    const t = document.getElementById('toast');
    t.innerText = msg;
    t.classList.add('show');
    setTimeout(() => { t.classList.remove('show'); }, 3000);
  }

  function switchTab(tabId) {
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-view').forEach(el => el.classList.remove('active'));
    
    // 高亮菜单
    const items = document.querySelectorAll('.nav-item');
    if (tabId === 'tab-gemini') items[0].classList.add('active');
    else if (tabId === 'tab-account') items[1].classList.add('active');
    else if (tabId === 'tab-wardrobe') items[2].classList.add('active');
    else if (tabId === 'tab-journals') items[3].classList.add('active');
    else if (tabId === 'tab-cruise') items[4].classList.add('active');
    else if (tabId === 'tab-astrbot') items[5].classList.add('active');

    const target = document.getElementById(tabId);
    if (target) target.classList.add('active');

    if (tabId === 'tab-wardrobe') loadGallery();
    if (tabId === 'tab-journals') loadJournals();
    if (tabId === 'tab-astrbot') loadAstrBotStatus();
  }

  // 计算字符与字节
  const personaTextarea = document.getElementById('personaContent');
  personaTextarea.addEventListener('input', () => {
    updateCharCount(personaTextarea.value);
  });

  function updateCharCount(text) {
    const chars = text.length;
    const bytes = new TextEncoder().encode(text).length;
    document.getElementById('personaCount').innerText = `当前 ${chars.toLocaleString()} 字符 · ${bytes.toLocaleString()} 字节`;
  }

  // 加载系统状态与配置
  async function loadStatus() {
    try {
      const res = await fetch('/api/status');
      const data = await res.json();
      currentConfig = data.config || {};

      // 填充她是
      const prof = currentConfig.profile || {};
      document.getElementById('roleName').value = prof.role_name || '闪闪';
      document.getElementById('callMaster').value = prof.call_master || '主人';
      document.getElementById('selfName').value = prof.self_name || '人家';

      // 填充你（主人）
      document.getElementById('masterUid').value = prof.master_uid || 0;
      document.getElementById('masterName').value = prof.master_name || '主人';
      const prefs = currentConfig.preferences || {};
      document.getElementById('keywordsPrefer').value = (prefs.keywords_prefer || []).join(', ');
      document.getElementById('keywordsBlacklist').value = (prefs.blacklist_keywords || []).join(', ');

      // 填充作息
      const sched = currentConfig.schedule || {};
      document.getElementById('morningTime').value = sched.morning_journal_time || '09:30';
      document.getElementById('eveningTime').value = sched.evening_journal_time || '22:30';
      document.getElementById('maxVideos').value = sched.max_videos_per_cycle || 6;
      document.getElementById('maxAt').value = sched.max_at_per_day || 3;

      // 账号卡片
      const user = data.user || {};
      if (user.is_login) {
        document.getElementById('userName').innerText = user.uname || '已授权用户';
        document.getElementById('userDede').innerText = user.mid || '-';
        document.getElementById('userCoin').innerText = (user.money !== undefined) ? user.money : '正常';
        document.getElementById('userVip').innerText = user.vip_type ? '年度大会员 ✨' : '正式会员';
        if (user.face) document.getElementById('userFace').src = user.face;
      } else {
        document.getElementById('userName').innerText = '未登录 (免登录访客模式)';
        document.getElementById('userDede').innerText = '访客 WBI';
        document.getElementById('userCoin').innerText = '-';
        document.getElementById('userVip').innerText = '免登录冲浪';
        document.getElementById('userFace').src = '/images/Gemini猫娘_闪闪头像_水手服特写.png';
      }
      document.getElementById('userStamina').innerText = `${data.stamina || 100} / 100`;

      // 巡航日志
      if (data.cruise_logs && data.cruise_logs.length > 0) {
        document.getElementById('consoleLog').innerText = data.cruise_logs.join('\n');
      }
    } catch(e) {
      console.error(e);
    }
  }

  // 加载人设正文
  async function loadPersona() {
    try {
      const res = await fetch('/api/persona');
      const data = await res.json();
      const txt = data.persona || '';
      personaTextarea.value = txt;
      updateCharCount(txt);
    } catch(e) {
      console.error(e);
    }
  }

  // 保存身份
  async function saveProfile() {
    const role_name = document.getElementById('roleName').value.trim();
    const call_master = document.getElementById('callMaster').value.trim();
    const self_name = document.getElementById('selfName').value.trim();
    const payload = {
      config: {
        profile: { role_name, call_master, self_name }
      }
    };
    const res = await fetch('/api/save_config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const d = await res.json();
    showToast(d.message || '基础身份保存成功！');
  }

  // 注入人设
  async function injectPersona() {
    const txt = personaTextarea.value;
    const res = await fetch('/api/save_persona', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ persona: txt })
    });
    const d = await res.json();
    showToast(d.message || '人设已成功注入 docs/gemini_persona.md！');
  }

  // 保存主人偏好
  async function saveMasterPrefs() {
    const master_uid = parseInt(document.getElementById('masterUid').value) || 0;
    const master_name = document.getElementById('masterName').value.trim();
    const kw_prefer = document.getElementById('keywordsPrefer').value.split(',').map(s => s.trim()).filter(Boolean);
    const kw_black = document.getElementById('keywordsBlacklist').value.split(',').map(s => s.trim()).filter(Boolean);

    const payload = {
      config: {
        profile: { master_uid, master_name },
        preferences: { keywords_prefer: kw_prefer, blacklist_keywords: kw_black }
      }
    };
    const res = await fetch('/api/save_config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const d = await res.json();
    showToast(d.message || '主人偏好保存成功！');
  }

  // 保存作息
  async function saveSchedule() {
    const morning = document.getElementById('morningTime').value.trim();
    const evening = document.getElementById('eveningTime').value.trim();
    const maxVideos = parseInt(document.getElementById('maxVideos').value) || 6;
    const maxAt = parseInt(document.getElementById('maxAt').value) || 3;

    const payload = {
      config: {
        schedule: {
          morning_journal_time: morning,
          evening_journal_time: evening,
          max_videos_per_cycle: maxVideos,
          max_at_per_day: maxAt
        }
      }
    };
    const res = await fetch('/api/save_config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const d = await res.json();
    showToast(d.message || '作息风控已更新！');
  }

  // 快捷打开本地文件
  async function openConfigFile() {
    const res = await fetch('/api/open_config_file', { method: 'POST' });
    showToast('已调起系统编辑器打开 config/hajimi_config.json');
  }
  async function openPersonaFile() {
    const res = await fetch('/api/open_persona_file', { method: 'POST' });
    showToast('已调起系统编辑器打开 docs/gemini_persona.md');
  }
  async function openJournalDir() {
    await fetch('/api/open_folder', { method: 'POST' });
    showToast('已在资源管理器中打开手记目录');
  }

  // 二维码扫码
  async function requestQrCode() {
    const box = document.getElementById('qrBox');
    const tip = document.getElementById('qrTip');
    tip.innerText = '正在向 B 站申请安全登录二维码...';
    box.style.display = 'flex';

    const res = await fetch('/api/qrcode');
    const d = await res.json();
    if (d.url && d.qrcode_key) {
      if (d.img_b64) document.getElementById('qrImg').src = d.img_b64;
      else document.getElementById('qrImg').src = `/api/qrcode_img?t=${Date.now()}`;
      tip.innerText = '请打开哔哩哔哩手机客户端扫码';
      if (qrPollTimer) clearInterval(qrPollTimer);
      qrPollTimer = setInterval(async () => {
        const pRes = await fetch(`/api/poll_login?key=${d.qrcode_key}`);
        const pData = await pRes.json();
        if (pData.code === 0) {
          clearInterval(qrPollTimer);
          tip.innerText = '🎉 授权登录成功！';
          showToast('B站登录成功！已接管推荐流与专属互动权限');
          loadStatus();
        } else if (pData.code === 86038) {
          clearInterval(qrPollTimer);
          tip.innerText = '二维码已失效，请重新生成';
        }
      }, 2500);
    }
  }

  // 加载立绘图鉴
  async function loadGallery() {
    const cont = document.getElementById('galleryContainer');
    if (cont.children.length > 0) return;
    try {
      const res = await fetch('/api/gallery');
      const list = await res.json();
      cont.innerHTML = list.map(item => `
        <div class="outfit-card" onclick="window.open('${item.url}', '_blank')">
          <div class="outfit-preview">
            <img src="${item.url}" alt="${item.title}" loading="lazy">
          </div>
          <div class="outfit-meta">
            <div class="outfit-title">${item.title}</div>
            <div class="outfit-desc">${item.desc}</div>
          </div>
        </div>
      `).join('');
    } catch(e) {
      console.error(e);
    }
  }

  // 加载手记
  async function loadJournals() {
    const cont = document.getElementById('journalsList');
    try {
      const res = await fetch('/api/journals');
      const data = await res.json();
      if (!data.journals || data.journals.length === 0) {
        cont.innerHTML = '<div style="padding:20px; color:var(--text-muted);">暂无已归档手记，可点击右上角“立即生成晨思/晚读”或等待作息定时写入。</div>';
        return;
      }
      cont.innerHTML = data.journals.map(j => `
        <div class="journal-item" onclick="openJournalDir()">
          <div class="journal-head">
            <div class="journal-title">📄 ${j.filename}</div>
            <div class="journal-time">${j.mtime} · ${(j.size / 1024).toFixed(1)} KB</div>
          </div>
          <div class="journal-snippet">${j.snippet}...</div>
        </div>
      `).join('');
    } catch(e) {
      console.error(e);
    }
  }

  // 触发巡航与手记
  async function triggerCruise() {
    showToast('已唤醒闪闪出击巡航！请在下方控制台观察动态');
    await fetch('/api/cruise', { method: 'POST' });
    pollCruiseLogs();
  }
  async function triggerMorning() {
    showToast('闪闪正在撰写《晨思手记》...');
    const res = await fetch('/api/morning_journal', { method: 'POST' });
    const d = await res.json();
    if (d.success) { showToast('《晨思手记》撰写完成并已归档！'); loadJournals(); }
  }
  async function triggerEvening() {
    showToast('闪闪正在撰写《晚读手记》...');
    const res = await fetch('/api/evening_journal', { method: 'POST' });
    const d = await res.json();
    if (d.success) { showToast('《晚读手记》撰写完成并已归档！'); loadJournals(); }
  }

  function pollCruiseLogs() {
    const t = setInterval(async () => {
      const res = await fetch('/api/status');
      const d = await res.json();
      if (d.cruise_logs && d.cruise_logs.length > 0) {
        const consoleEl = document.getElementById('consoleLog');
        consoleEl.innerText = d.cruise_logs.join('\n');
        consoleEl.scrollTop = consoleEl.scrollHeight;
      }
      if (!d.is_cruising) clearInterval(t);
    }, 2000);
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  async function loadAstrBotStatus() {
    try {
      const res = await fetch('/api/astrbot_status');
      const data = await res.json();
      if (!data.installed) {
        document.getElementById('astrbotSessionsList').innerHTML = `<div style="padding:20px; text-align:center; color:#6b7280; font-size:13.5px;">${data.message}</div>`;
        return;
      }
      document.getElementById('astrbotTotalSessions').textContent = data.total_sessions;
      document.getElementById('astrbotMaxUnanswered').textContent = data.max_unanswered + ' 次';

      const limitedEl = document.getElementById('astrbotLimitedSessions');
      if (data.limited_sessions > 0) {
        limitedEl.innerHTML = `<span style="color:#ef4444;">${data.limited_sessions} 个已暂停</span>`;
      } else {
        limitedEl.innerHTML = `<span style="color:#10b981;">全部畅聊中 (0 受限)</span>`;
      }

      const procEl = document.getElementById('astrbotProcessStatus');
      if (data.astrbot_running) {
        procEl.innerHTML = `<span style="display:inline-block; width:9px; height:9px; border-radius:50%; background:#10b981;"></span> 运行中`;
      } else {
        procEl.innerHTML = `<span style="display:inline-block; width:9px; height:9px; border-radius:50%; background:#9ca3af;"></span> 离线 / 待启动`;
      }

      const container = document.getElementById('astrbotSessionsList');
      if (!data.sessions || data.sessions.length === 0) {
        container.innerHTML = `<div style="padding:20px; text-align:center; color:#6b7280; font-size:13.5px;">暂无会话数据</div>`;
        return;
      }

      container.innerHTML = data.sessions.map(s => {
        const isLimited = s.is_limited;
        const count = s.unanswered_count;
        const max = s.max_unanswered;
        const statusBadge = isLimited 
          ? `<span style="background:#fee2e2; color:#b91c1c; font-size:11.5px; font-weight:600; padding:2px 8px; border-radius:999px;">已达上限 (${count}/${max}) 熔断中</span>`
          : (count > 0 
            ? `<span style="background:#fef3c7; color:#b45309; font-size:11.5px; font-weight:600; padding:2px 8px; border-radius:999px;">待回复 (${count}/${max})</span>`
            : `<span style="background:#d1fae5; color:#065f46; font-size:11.5px; font-weight:600; padding:2px 8px; border-radius:999px;">正常畅聊 (0/${max})</span>`);

        return `
          <div style="background:#ffffff; border:1px solid ${isLimited ? '#fca5a5' : 'var(--border-color)'}; border-radius:9px; padding:14px 18px; display:flex; align-items:center; justify-content:space-between; gap:12px;">
            <div style="flex:1; min-width:0;">
              <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px; flex-wrap:wrap;">
                <span style="font-weight:600; font-size:14px; color:var(--text-main);">${escapeHtml(s.name)}</span>
                ${statusBadge}
              </div>
              <div style="font-size:12px; color:var(--text-muted); font-family:monospace; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                ${escapeHtml(s.session_id)}
              </div>
              <div style="font-size:12px; color:var(--text-muted); margin-top:2px;">
                最近活动: ${escapeHtml(s.last_message_time)} ｜ 平台账号: ${escapeHtml(s.self_id)}
              </div>
            </div>
            <button class="btn-save-light" style="padding:6px 14px; font-size:12.5px; flex-shrink:0;" onclick="resetAstrBotLimits('${escapeHtml(s.session_id)}')">清零此会话</button>
          </div>
        `;
      }).join('');
    } catch (err) {
      showToast('获取 AstrBot 状态失败: ' + err.message);
    }
  }

  async function resetAstrBotLimits(sessionId = null) {
    try {
      showToast('正在重置主动消息未回复计数...');
      const res = await fetch('/api/astrbot_reset_limit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId })
      });
      const result = await res.json();
      if (result.success) {
        showToast(result.message);
        await loadAstrBotStatus();
      } else {
        showToast('清零失败: ' + result.message);
      }
    } catch (err) {
      showToast('请求异常: ' + err.message);
    }
  }

  // 初始化
  window.addEventListener('DOMContentLoaded', () => {
    loadStatus();
    loadPersona();
    loadAstrBotStatus();
  });
</script>

</body>
</html>
"""


def run_server():
    server_address = ("0.0.0.0", PORT)
    httpd = ThreadingHTTPServer(server_address, HajimiHandler)
    httpd.daemon_threads = True
    print(f"============================================================")
    print(f"🐾 赛博养Gemini · 伴生控制中心已启动 (多线程高并发模式)！")
    print(f"🔗 本地 Web 访问入口: http://127.0.0.1:{PORT}/")
    print(f"🔗 Sidecar 辅助抽屉入口: sidecar://cyber-hajimi/panel/")
    print(f"============================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] 控制中心已停止。")


if __name__ == "__main__":
    if "--no-browser" not in sys.argv and not os.environ.get("ANTIGRAVITY_SIDECAR_WEB_PORT"):
        threading.Thread(target=lambda: (time.sleep(1.2), webbrowser.open(f"http://127.0.0.1:{PORT}/")), daemon=True).start()
    run_server()
