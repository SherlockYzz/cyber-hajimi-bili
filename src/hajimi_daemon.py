# -*- coding: utf-8 -*-
"""
赛博哈基米 (Cyber-Hajimi) - 巡航调度与仿生作息守护引擎
- 仿生精力系统（自然流逝、休息恢复、看视频消耗）
- 心情概率摸鱼机制（猫猫理毛、打瞌睡、玩玩具跳过巡航）
- 智能分区巡航、关键词定向追踪与垃圾营销号黑名单过滤
- 评论区精准 @ 主人与频次风控限制
- 每日晨思与晚读手记自动归档（docs/journals/）
"""

import os
import sys
import json
import time
import random
import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "hajimi_config.json"
STATE_PATH = PROJECT_ROOT / "config" / "hajimi_state.json"
JOURNALS_DIR = PROJECT_ROOT / "docs" / "journals"

JOURNALS_DIR.mkdir(parents=True, exist_ok=True)

from bili_hajimi_core import BiliHajimiCore
from hajimi_brain import HajimiBrain


class HajimiDaemon:
    def __init__(self, config_path=CONFIG_PATH):
        self.config_path = Path(config_path)
        self.core = BiliHajimiCore(self.config_path)
        self.brain = HajimiBrain(self.config_path)
        self.config = self.core.config
        self.state = self._load_state()

    def _load_state(self) -> dict:
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        default_state = {
            "today_date": today_str,
            "stamina": 100,
            "last_stamina_update": time.time(),
            "at_count_today": 0,
            "watched_today": [],
            "treasures_today": [],
            "morning_journal_done": False,
            "evening_journal_done": False,
            "recent_evaluations": [],
            "cruise_logs": [],
        }

        if STATE_PATH.exists():
            try:
                with open(STATE_PATH, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    if saved.get("today_date") != today_str:
                        saved["today_date"] = today_str
                        saved["at_count_today"] = 0
                        saved["watched_today"] = []
                        saved["treasures_today"] = []
                        saved["morning_journal_done"] = False
                        saved["evening_journal_done"] = False
                    return {**default_state, **saved}
            except Exception:
                pass

        return default_state

    def save_state(self):
        try:
            with open(STATE_PATH, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Daemon] 保存运行状态失败: {e}")

    def update_stamina(self):
        now = time.time()
        elapsed_hours = (now - self.state.get("last_stamina_update", now)) / 3600.0
        max_stamina = self.config.get("schedule", {}).get("stamina_max", 100)
        recovery_rate = self.config.get("schedule", {}).get("stamina_recovery_per_hour", 15)

        current = self.state.get("stamina", 100)
        recovered = elapsed_hours * recovery_rate
        new_stamina = min(max_stamina, current + recovered)

        self.state["stamina"] = round(new_stamina, 1)
        self.state["last_stamina_update"] = now
        self.save_state()

    def is_in_active_window(self) -> tuple[bool, str]:
        now_time = datetime.datetime.now().strftime("%H:%M")
        windows = self.config.get("schedule", {}).get("active_windows", [])
        if not windows:
            return True, "全天无休"

        for win in windows:
            start = win.get("start", "00:00")
            end = win.get("end", "23:59")
            if start <= now_time <= end:
                return True, win.get("name", "活跃窗口")
        return False, "休息窗口"

    def run_cruise_cycle(self, force: bool = False) -> dict:
        self.update_stamina()
        stamina = self.state.get("stamina", 100)
        cost_per_video = self.config.get("schedule", {}).get("stamina_cost_per_video", 8)

        log_lines = []

        if not force:
            in_window, win_name = self.is_in_active_window()
            if not in_window:
                msg = f"当前处于休眠时段，哈基米正在窝里呼噜大睡，不打扰主人~"
                log_lines.append(msg)
                return {"success": False, "reason": "out_of_window", "logs": log_lines}

            if stamina < cost_per_video:
                msg = f"当前精力不足 ({stamina}/{cost_per_video})，哈基米打了个哈欠，等待精力恢复中..."
                log_lines.append(msg)
                return {"success": False, "reason": "low_stamina", "logs": log_lines}

            mood_skip = self.config.get("schedule", {}).get("mood_skip_chance", 0.15)
            if random.random() < mood_skip:
                msg = "🐾 哈基米正在追逐激光笔玩耍，尾巴甩甩，本次巡航摸鱼打盹一次喵~"
                log_lines.append(msg)
                return {"success": False, "reason": "mood_skip", "logs": log_lines}

        keywords = self.config.get("preferences", {}).get("keywords_prefer", ["AI", "大模型", "极客"])
        blacklist_up = self.config.get("preferences", {}).get("blacklist_up", [])
        blacklist_kw = self.config.get("preferences", {}).get("blacklist_keywords", [])

        is_search = random.random() < 0.7
        candidates = []

        if is_search and keywords:
            chosen_kw = random.choice(keywords)
            log_lines.append(f"🔍 启动关键词定向雷达: [{chosen_kw}]")
            raw_list = self.core.search_keyword_videos(chosen_kw, page=1, order="pubdate")
            for item in raw_list:
                bvid = item.get("bvid", "")
                title = item.get("title", "").replace('<em class="keyword">', "").replace("</em>", "")
                author = item.get("author", "")
                desc = item.get("description", "")
                if bvid:
                    candidates.append({"bvid": bvid, "title": title, "owner": {"name": author}, "desc": desc})
        else:
            log_lines.append(f"🔥 扫描 B 站综合热门前沿...")
            raw_list = self.core.get_popular_videos(pn=1, ps=15)
            for item in raw_list:
                candidates.append({
                    "bvid": item.get("bvid", ""),
                    "title": item.get("title", ""),
                    "owner": item.get("owner", {}),
                    "desc": item.get("desc", ""),
                })

        filtered = []
        watched_set = set(self.state.get("watched_today", []))
        for c in candidates:
            bvid = c.get("bvid", "")
            title = c.get("title", "")
            up_name = c.get("owner", {}).get("name", "")

            if bvid in watched_set:
                continue
            if any(blk in up_name for blk in blacklist_up):
                continue
            if any(bkw in title for bkw in blacklist_kw):
                continue
            filtered.append(c)

        max_cycle = self.config.get("schedule", {}).get("max_videos_per_cycle", 4)
        targets = filtered[:max_cycle]

        if not targets:
            log_lines.append("未发现符合要求的新鲜视频，本次巡航结束。")
            return {"success": True, "evaluated_count": 0, "logs": log_lines}

        log_lines.append(f"🎯 选定 {len(targets)} 条新鲜视频，开始深入研读与审美质检...")

        results = []
        for target in targets:
            bvid = target.get("bvid")
            log_lines.append(f"\n▶ 正在质检视频: [{bvid}] 《{target.get('title')}》")

            self.state["stamina"] = max(0, round(self.state.get("stamina", 100) - cost_per_video, 1))

            detail = self.core.get_video_detail(bvid)
            if not detail:
                detail = target

            cid = detail.get("cid", 0)
            aid = detail.get("aid", 0)
            subtitles = ""
            if cid:
                subtitles = self.core.get_video_subtitles(bvid, cid)
                if subtitles:
                    log_lines.append(f"  ✓ 成功抓取 CC 字幕 (长度 {len(subtitles)} 字)")

            ai_summary = None
            if cid and detail.get("owner", {}).get("mid"):
                ai_summary = self.core.get_ai_conclusion(bvid, cid, detail["owner"]["mid"])

            eval_res = self.brain.evaluate_video(detail, subtitle_text=subtitles, ai_summary=ai_summary)
            score = eval_res.get("score", 0)
            log_lines.append(f"  ★ Gemini 3.8 Flash 评分: {score} / 10.0 [{eval_res.get('verdict')}]")
            log_lines.append(f"  💡 核心干货亮点: {eval_res.get('highlight')}")

            self.state.setdefault("watched_today", []).append(bvid)
            self.state.setdefault("recent_evaluations", []).insert(0, {
                **eval_res,
                "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
            self.state["recent_evaluations"] = self.state["recent_evaluations"][:50]

            threshold = self.config.get("interaction", {}).get("at_score_threshold", 8.5)
            if score >= threshold:
                log_lines.append(f"  ✨ 发现极品宝藏视频！收入今日晚读手记备选池！")
                self.state.setdefault("treasures_today", []).append({
                    "bvid": bvid,
                    "title": eval_res.get("title", ""),
                    "owner": eval_res.get("owner", ""),
                    "score": score,
                    "highlight": eval_res.get("highlight", ""),
                    "cat_comment": eval_res.get("cat_comment", ""),
                })

                max_at = self.config.get("schedule", {}).get("max_at_per_day", 3)
                curr_at = self.state.get("at_count_today", 0)
                allow_comment = self.config.get("interaction", {}).get("allow_comment", True)

                if allow_comment and curr_at < max_at and eval_res.get("should_at") and aid:
                    comment_text = eval_res.get("cat_comment", "")
                    log_lines.append(f"  💬 正在 B 站评论区发布猫猫脚印并 @ 主人: {comment_text}")
                    comment_res = self.core.post_comment(aid, comment_text)
                    if comment_res.get("success"):
                        self.state["at_count_today"] = curr_at + 1
                        log_lines.append("  🎉 评论与 @ 互动成功！")
                    else:
                        log_lines.append(f"  ⚠ 评论发布反馈: {comment_res.get('message')}")

            results.append(eval_res)

        self.save_state()
        return {"success": True, "evaluated_count": len(results), "results": results, "logs": log_lines}

    def generate_morning_journal_file(self) -> str:
        self.update_stamina()
        stamina = int(self.state.get("stamina", 100))
        zones = self.config.get("preferences", {}).get("target_zones", [])
        content = self.brain.generate_morning_journal(stamina, zones)

        today_tag = datetime.date.today().strftime("%Y%m%d")
        file_name = f"哈基米手记_{today_tag}_早.md"
        target_path = JOURNALS_DIR / file_name

        try:
            with open(target_path, "w", encoding="utf-8-sig") as f:
                f.write(content)
            self.state["morning_journal_done"] = True
            self.save_state()
            print(f"[Daemon] 晨思手记已生成: {target_path}")
            return str(target_path)
        except Exception as e:
            print(f"[Daemon] 生成晨思手记失败: {e}")
            return ""

    def generate_evening_journal_file(self) -> str:
        self.update_stamina()
        stamina = int(self.state.get("stamina", 100))
        treasures = self.state.get("treasures_today", [])
        content = self.brain.generate_evening_journal(stamina, treasures)

        today_tag = datetime.date.today().strftime("%Y%m%d")
        file_name = f"哈基米手记_{today_tag}_晚.md"
        target_path = JOURNALS_DIR / file_name

        try:
            with open(target_path, "w", encoding="utf-8-sig") as f:
                f.write(content)
            self.state["evening_journal_done"] = True
            self.save_state()
            print(f"[Daemon] 晚读手记已生成: {target_path}")
            return str(target_path)
        except Exception as e:
            print(f"[Daemon] 生成晚读手记失败: {e}")
            return ""


if __name__ == "__main__":
    print("[Daemon] 初始化赛博养Gemini巡航守护引擎...")
    daemon = HajimiDaemon()
    print(f"[Daemon] 当前精力值: {daemon.state.get('stamina')}/100 | 今日已 @: {daemon.state.get('at_count_today')} 次")
