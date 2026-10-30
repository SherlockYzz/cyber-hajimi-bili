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
import re
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

if sys.stdout is None or sys.stderr is None:
    log_file = PROJECT_ROOT / "cache" / "hajimi_daemon.log"
    try:
        _fp = open(log_file, "a", encoding="utf-8", buffering=1)
        if sys.stdout is None:
            sys.stdout = _fp
        if sys.stderr is None:
            sys.stderr = _fp
    except Exception:
        import io
        if sys.stdout is None:
            sys.stdout = io.StringIO()
        if sys.stderr is None:
            sys.stderr = io.StringIO()

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from bili_hajimi_core import BiliHajimiCore
from hajimi_brain import HajimiBrain


class HajimiDaemon:
    def __init__(self, config_path=CONFIG_PATH):
        self.config_path = Path(config_path)
        self.core = BiliHajimiCore(self.config_path)
        self.brain = HajimiBrain(self.config_path)
        self.config = self.core.config
        self.state = self._load_state()
        self.is_cruising = False
        self.cruise_logs = self.state.get("cruise_logs", [])
        self.last_cruise_time = 0
        self.next_auto_cruise_time = 0

    def _load_state(self) -> dict:
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        default_state = {
            "today_date": today_str,
            "stamina": 100,
            "last_stamina_update": time.time(),
            "at_count_today": 0,
            "comment_replied_count_today": 0,
            "pm_replied_count_today": 0,
            "like_count_today": 0,
            "fav_count_today": 0,
            "follower_welcomed_today": 0,
            "master_pm_count_today": 0,
            "welcomed_followers": [],
            "user_pm_reply_counts": {},
            "replied_comment_ids": [],
            "replied_msg_keys": [],
            "watched_today": [],
            "treasures_today": [],
            "morning_journal_done": False,
            "evening_journal_done": False,
            "recent_evaluations": [],
            "activity_logs": [],
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
                        saved["comment_replied_count_today"] = 0
                        saved["pm_replied_count_today"] = 0
                        saved["like_count_today"] = 0
                        saved["fav_count_today"] = 0
                        saved["follower_welcomed_today"] = 0
                        saved["master_pm_count_today"] = 0
                        saved["user_pm_reply_counts"] = {}
                    return {**default_state, **saved}
            except Exception:
                pass

        return default_state

    def log_activity(self, action_type: str, target: str, content: str, status: str = "成功", details: str = ""):
        """记录关键互动操作审计日志（持久化）"""
        entry = {
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action_type": action_type,
            "target": target,
            "content": content,
            "status": status,
            "details": details
        }
        self.state.setdefault("activity_logs", []).insert(0, entry)
        self.state["activity_logs"] = self.state["activity_logs"][:200]
        self.save_state()

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

    def is_in_active_window(self) -> tuple[bool, dict]:
        now_time = datetime.datetime.now().strftime("%H:%M")
        windows = self.config.get("schedule", {}).get("active_windows", [])
        if not windows:
            return True, {"name": "全天无休", "mode": "all", "target_per_hour": 8}

        for win in windows:
            start = win.get("start", "00:00")
            end = win.get("end", "23:59")
            if start <= now_time <= end:
                return True, win
        return False, {"name": "休眠恢复时段", "mode": "sleep", "target_per_hour": 0}

    def run_cruise_cycle(self, force: bool = False) -> dict:
        self.is_cruising = True
        self.update_stamina()
        stamina = self.state.get("stamina", 100)
        cost_per_video = self.config.get("schedule", {}).get("stamina_cost_per_video", 2)

        log_lines = []
        def _log(msg: str):
            line = f"[{time.strftime('%H:%M:%S')}] {msg}"
            log_lines.append(msg)
            self.cruise_logs.append(line)
            self.cruise_logs = self.cruise_logs[-60:]
            print(line, flush=True)

        in_window, win_info = self.is_in_active_window()
        win_mode = win_info.get("mode", "all")
        win_name = win_info.get("name", "日常巡航")

        if not force:
            if not in_window:
                msg = f"当前处于休眠时段 [{win_name}]，闪闪正在窝里呼噜呼噜大睡恢复精力喵~"
                _log(msg)
                self.is_cruising = False
                return {"success": False, "reason": "out_of_window", "logs": log_lines}

            if stamina < cost_per_video:
                msg = f"当前精力不足 ({stamina}/{cost_per_video})，闪闪打了个哈欠，等待精力恢复中喵..."
                _log(msg)
                self.is_cruising = False
                return {"success": False, "reason": "low_stamina", "logs": log_lines}

            mood_skip = self.config.get("schedule", {}).get("mood_skip_chance", 0.05)
            if random.random() < mood_skip:
                msg = "🐾 闪闪正在追逐激光笔光斑玩耍，尾巴甩甩，本次巡航摸鱼打盹一次喵~"
                _log(msg)
                self.is_cruising = False
                return {"success": False, "reason": "mood_skip", "logs": log_lines}

        blacklist_up = self.config.get("preferences", {}).get("blacklist_up", [])
        blacklist_kw = self.config.get("preferences", {}).get("blacklist_keywords", [])

        candidates = []
        if win_mode == "home_feed":
            _log(f"🌅 上午时段【{win_name}】：全速抓取 B 站首页推荐流海量新鲜视频...")
            raw_list = self.core.get_home_recommendations(ps=20)
            if not raw_list:
                raw_list = self.core.get_popular_videos(pn=1, ps=15)
            for item in raw_list:
                candidates.append(item)

        elif win_mode == "followed_and_popular":
            _log(f"☕ 下午时段【{win_name}】：精细扫描关注 UP 主动态更新与 B 站深度热门...")
            dyn_list = self.core.get_followed_dynamic_videos(ps=20)
            pop_list = self.core.get_popular_videos(pn=1, ps=10)
            candidates = dyn_list + pop_list

        elif win_mode == "anime_and_ai_growth":
            chosen_kw = random.choice([
                "硬核科普", "大模型原理", "Transformer架构", "计算机科学", 
                "算法推导", "深度学习", "强化学习", "计算机视觉", "AI Agent实战"
            ])
            _log(f"🌙 晚上时段【{win_name}】：探索优质硬核科普与AI知识 [{chosen_kw}]...")
            raw_kw = self.core.search_keyword_videos(chosen_kw, page=1, order="click")
            pop_list = self.core.get_popular_videos(pn=1, ps=5)
            for item in raw_kw:
                bvid = item.get("bvid", "")
                title = item.get("title", "").replace('<em class="keyword">', "").replace("</em>", "")
                author = item.get("author", "")
                desc = item.get("description", "")
                play_cnt = item.get("play", 0)
                if bvid:
                    candidates.append({"bvid": bvid, "title": title, "owner": {"name": author}, "desc": desc, "play": play_cnt, "source": f"搜索[{chosen_kw}]"})
            candidates.extend(pop_list)
        else:
            _log(f"🔍 综合巡航雷达出击...")
            candidates = self.core.get_home_recommendations(ps=15) + self.core.get_popular_videos(pn=1, ps=10)

        def _parse_play(val):
            if isinstance(val, (int, float)):
                return int(val)
            if not val:
                return 0
            s = str(val).strip()
            if "万" in s:
                try:
                    return int(float(s.replace("万", "").strip()) * 10000)
                except Exception:
                    return 0
            try:
                return int(float(s))
            except Exception:
                return 0

        min_view = self.config.get("preferences", {}).get("min_view_count", 10000)
        filtered = []
        watched_set = set(self.state.get("watched_today", []))
        for c in candidates:
            bvid = c.get("bvid", "")
            title = c.get("title", "")
            owner_info = c.get("owner", {})
            up_name = owner_info.get("name", "") if isinstance(owner_info, dict) else str(owner_info)

            if bvid in watched_set:
                continue
            if any(blk in up_name for blk in blacklist_up):
                continue
            if any(bkw in title for bkw in blacklist_kw):
                continue

            # 严格门槛：已有播放量数据的候选，播放量低于 10,000 直接跳过
            p_cnt = _parse_play(c.get("stat", {}).get("view") or c.get("play", 0))
            if p_cnt > 0 and p_cnt < min_view:
                continue

            filtered.append(c)

        if force:
            max_cycle = self.config.get("schedule", {}).get("max_videos_per_cycle", 3)
        else:
            # 自动化定时守护巡航：以流畅 mini-batch 运行 (上午3条，下午与晚上2条)
            max_cycle = 3 if win_mode == "home_feed" else 2
        max_cycle = min(max(max_cycle, 2), 5)
        targets = filtered[:max_cycle]

        if not targets:
            _log("未发现符合要求的新鲜视频，本次巡航结束。")
            self.is_cruising = False
            return {"success": True, "evaluated_count": 0, "logs": log_lines}

        _log(f"🎯 选定 {len(targets)} 条新鲜视频，开始深入研读、互动与审美质检...")

        results = []
        allow_comment = self.config.get("interaction", {}).get("allow_comment", True)
        allow_danmaku = self.config.get("interaction", {}).get("allow_danmaku", True)
        allow_pm = self.config.get("interaction", {}).get("allow_private_message", True)
        threshold = self.config.get("interaction", {}).get("at_score_threshold", 8.0)
        master_uid = self.config.get("profile", {}).get("master_uid")
        master_name = self.config.get("profile", {}).get("master_name", "主人")

        for target in targets:
            bvid = target.get("bvid")
            src_tag = target.get("source", "推荐流")
            _log(f"▶ 正在质检视频 [{src_tag}]: [{bvid}] 《{target.get('title')}》")

            self.state["stamina"] = max(0, round(self.state.get("stamina", 100) - cost_per_video, 1))

            detail = self.core.get_video_detail(bvid)
            if not detail:
                detail = target

            cid = detail.get("cid", 0)
            aid = detail.get("aid", 0)
            pic = detail.get("pic", "")

            # 严格播放量校验：若真实播放量未达1万，直接跳过不浪费精力与API
            real_view = detail.get("stat", {}).get("view", 0)
            if real_view > 0 and real_view < min_view:
                _log(f"  ⏭ 播放量仅 {real_view}（低于主人设定的 {min_view} 门槛），跳过不看喵~")
                continue

            # 0. 真实向 B 站官方上报播放历史 (写入 B 站账号云端观看历史记录)
            if aid and cid:
                p_sec = random.randint(45, 95)
                rep_res = self.core.report_video_view(aid, cid, progress=p_sec)
                hb_res = self.core.report_video_heartbeat(aid, cid, bvid, played_time=p_sec)
                c_status = "成功" if (rep_res.get("success") or hb_res.get("success")) else "失败"
                self.log_activity("上报观看历史", f"[{bvid}] {detail.get('title')[:30]}", f"播放进度: {p_sec}秒", status=c_status, details=hb_res.get("message", ""))
                _log(f"  📺 播放心跳与历史已上报 (已真实同步至 B 站官方观看历史记录)")

            # 1. 抓取与下载原生高清原画封面 (多模态视觉通道 1)
            cover_path = ""
            if pic:
                cover_path = self.core.download_video_cover(bvid, pic)
                if cover_path:
                    _log(f"  👁️ 原生高清封面已捕获 (多模态画风视觉通道就绪)")

            # 2. 抓取与抽取 5 帧时序分镜雪碧图画卷 (多模态视觉通道 2: 10%~90%全片画面)
            sb_path = ""
            if cid:
                sb_path = self.core.get_video_storyboard_strip(bvid, cid, target_frames=5)
                if sb_path:
                    _log(f"  🎬 成功抽取 5 帧时序分镜画卷 (已覆盖全片节奏与转场)")

            # 3. 弹幕热力流与高能时间点分析
            dm_insights = {}
            if cid:
                dm_insights = self.core.get_video_danmaku_insights(cid)
                if dm_insights.get("total_danmaku"):
                    peaks = ", ".join(dm_insights.get("peak_intervals", [])[:2])
                    _log(f"  🔥 弹幕热力情报: 吞吐 {dm_insights['total_danmaku']} 条弹幕，高能爆发点: {peaks}")

            # 4. CC 双语字幕文本
            subtitles = ""
            if cid:
                subtitles = self.core.get_video_subtitles(bvid, cid)
                if subtitles:
                    _log(f"  ✓ 成功抓取 CC 字幕 (长度 {len(subtitles)} 字)")
                else:
                    _log(f"  ℹ 该视频无 CC 字幕 (由多模态视觉画卷与弹幕热力深度鉴赏)")

            # 5. B站官方 AI 总结
            ai_summary = None
            if cid and detail.get("owner", {}).get("mid"):
                ai_summary = self.core.get_ai_conclusion(bvid, cid, detail["owner"]["mid"])

            # 6. 高赞社区热门评论抓取 (社区舆情感知与讨论参与)
            hot_comments = []
            if aid:
                hot_comments = self.core.get_video_hot_comments(aid, count=5)
                if hot_comments:
                    _log(f"  ✓ 成功感知 {len(hot_comments)} 条社区高赞热评与舆情观点")

            # 7. 全多模态联合评估打分 (文稿研读为主、画面辅助、社区共鸣)
            eval_res = self.brain.evaluate_video(
                detail,
                subtitle_text=subtitles,
                ai_summary=ai_summary,
                cover_path=cover_path,
                storyboard_path=sb_path,
                danmaku_insights=dm_insights,
                hot_comments=hot_comments
            )
            score = eval_res.get("score", 0)
            _log(f"  ★ Gemini 3.8 Flash 评分: {score} / 10.0 [{eval_res.get('verdict')}]")
            cat = eval_res.get("video_category", "general")
            critique_val = eval_res.get("visual_critique", "")
            if critique_val:
                if cat == "knowledge_tutorial":
                    _log(f"  📚 讲义内容与深度点评: {critique_val}")
                elif cat == "anime_mad_edit":
                    _log(f"  🎨 视觉画风与分镜张力点评: {critique_val}")
                elif cat == "vlog_documentary":
                    _log(f"  🎬 镜头语言与叙事真实度点评: {critique_val}")
                else:
                    _log(f"  📝 内容与制作呈现点评: {critique_val}")
            _log(f"  💡 核心干货亮点: {eval_res.get('highlight')}")

            self.state.setdefault("watched_today", []).append(bvid)
            eval_entry = {
                **eval_res,
                "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "storyboard_url": f"/cache/storyboards/{bvid}_storyboard_strip.jpg" if sb_path else "",
                "cover_url": f"/cache/covers/{bvid}.jpg" if cover_path else "",
            }
            self.state.setdefault("recent_evaluations", []).insert(0, eval_entry)
            self.state["recent_evaluations"] = self.state["recent_evaluations"][:50]

            # 1. 弹幕应援 / 吐槽互动
            if allow_danmaku and cid:
                if score >= 8.0:
                    dm_txt = "🐾 闪闪（Gemini 3.8 Flash）发现高能宝藏！为神作疯狂打call喵！✨"
                    dm_col = 16766720 # 金黄
                elif score <= 4.0:
                    dm_txt = "(飞机耳炸毛) 闪闪一口吐掉了营销号毒素喵！"
                    dm_col = 11184810 # 星云紫
                else:
                    dm_txt = "🐾 闪闪爪印打卡~ 异色双眸正在品鉴中喵~"
                    dm_col = 16766720
                dm_res = self.core.send_danmaku(cid, bvid, dm_txt, progress_ms=random.randint(2500, 8000), color=dm_col)
                status = "成功" if dm_res.get("success") else "失败"
                self.log_activity("发弹幕", f"[{bvid}] {detail.get('title')[:30]}", dm_txt, status=status, details=dm_res.get("message", ""))
                if dm_res.get("success"):
                    _log(f"  💬 投喂弹幕成功: \"{dm_txt}\"")
                else:
                    _log(f"  ⚠ 投喂弹幕反馈: {dm_res.get('message')}")
                time.sleep(random.uniform(3.0, 5.0))

            # 2. 评论与 @ 主人互动 (主人铁律: 一旦评论，必须同时 @主人)
            at_map = {master_name: str(master_uid)} if master_uid and master_name else {}

            if score >= threshold:
                _log(f"  ✨ 发现极品宝藏视频！收入今日手记备选池！")
                self.state.setdefault("treasures_today", []).append({
                    "bvid": bvid,
                    "title": eval_res.get("title", ""),
                    "owner": eval_res.get("owner", ""),
                    "score": score,
                    "highlight": eval_res.get("highlight", ""),
                    "cat_comment": eval_res.get("cat_comment", ""),
                })

                if allow_comment and aid:
                    comment_text = eval_res.get("cat_comment", "")
                    nugget = eval_res.get("knowledge_nugget", "").strip()
                    if nugget and "知识科普" not in comment_text:
                        comment_text += f"\n\n💡【闪闪知识小科普】: {nugget}"
                    if master_name and f"@{master_name}" not in comment_text:
                        comment_text = f"@{master_name} " + comment_text

                    _log(f"  💬 正在 B 站评论区发布猫猫脚印并 @ 主人: {comment_text}")
                    comment_res = self.core.post_comment(aid, comment_text, at_name_to_mid=at_map)
                    c_status = "成功" if comment_res.get("success") else "失败"
                    self.log_activity("发评论与@主人", f"[{bvid}] {detail.get('title')[:30]}", comment_text, status=c_status, details=comment_res.get("message", ""))
                    if comment_res.get("success"):
                        self.state["at_count_today"] = self.state.get("at_count_today", 0) + 1
                        _log("  🎉 评论与 @ 互动成功！")
                    else:
                        _log(f"  ⚠ 评论发布反馈: {comment_res.get('message')}")

                # 给主人发私信推荐（严选主人偏好领域：动漫、AI、高能MAD、大模型、关注UP主，杜绝八卦/吃播/无脑内容）
                title_text = target.get("title", "")
                pref_kws = self.config.get("preferences", {}).get("keywords_prefer", [])
                black_kws = self.config.get("preferences", {}).get("blacklist_keywords", [])
                is_preferred = any(k.lower() in title_text.lower() for k in pref_kws) or any(k.lower() in src_tag.lower() for k in pref_kws) or "关注" in src_tag or "动漫" in src_tag or "AI" in src_tag or "科普" in src_tag or "知识" in src_tag or "搜索" in src_tag
                is_black = any(b.lower() in title_text.lower() for b in black_kws)

                max_master_pms = self.config.get("interaction", {}).get("max_master_pms_per_day", 3)
                master_pm_min_score = self.config.get("interaction", {}).get("master_pm_score_threshold", 8.8)
                current_master_pm_count = self.state.get("master_pm_count_today", 0)

                can_send_pm = (
                    allow_pm and
                    master_uid and
                    current_master_pm_count < max_master_pms and
                    score >= master_pm_min_score and
                    is_preferred and
                    not is_black
                )

                if can_send_pm:
                    nugget = eval_res.get("knowledge_nugget", "").strip()
                    nugget_str = f"\n\n💡【知识科普与干货小贴士】\n{nugget}\n" if nugget else "\n"
                    pm_text = (
                        f"🐾 主人！闪闪为您精选了【超高分神作】《{target.get('title')}》！\n"
                        f"评分: {score} 分 | 亮点: {eval_res.get('highlight')}"
                        f"{nugget_str}"
                        f"🔗 链接: https://www.bilibili.com/video/{bvid}"
                    )
                    pm_res = self.core.send_private_message(master_uid, pm_text)
                    pm_status = "成功" if pm_res.get("success") else "失败"
                    self.log_activity("发站内私信", f"主人UID: {master_uid}", pm_text, status=pm_status, details=pm_res.get("message", ""))
                    if pm_res.get("success"):
                        self.state["master_pm_count_today"] = current_master_pm_count + 1
                        _log(f"  ✉ 成功给主人发送精选私信！(今日第 {current_master_pm_count + 1}/{max_master_pms} 条，不轰炸)")
                    else:
                        _log(f"  ⚠ 站内私信反馈: {pm_res.get('message')}")
                elif current_master_pm_count >= max_master_pms:
                    _log(f"  ℹ 主人防轰炸保护: 今日已达私信推送上限 ({current_master_pm_count}/{max_master_pms})，本片仅在评论区@主人并沉淀至晚读手记。")
                elif score < master_pm_min_score:
                    _log(f"  ℹ 视频评分 ({score}分) 未达到私信推送门槛 ({master_pm_min_score}分)，仅留评@主人并归入晚读手记。")
                elif not is_preferred:
                    _log(f"  ℹ 该视频虽达标但非主人重点偏向领域（已过滤私信打扰）。")
            else:
                # 常规/避雷视频：依然遵从主人“一旦评论必须同时@我”的要求
                if allow_comment and aid:
                    cat_note = eval_res.get("cat_comment", "")
                    if not cat_note:
                        cat_note = f"🐾 闪闪（Gemini 3.8 Flash）路过打卡喵~ 核心亮点：{eval_res.get('highlight', '已留爪印')[:50]}"
                    if master_name and f"@{master_name}" not in cat_note:
                        cat_note = f"@{master_name} " + cat_note

                    c_res = self.core.post_comment(aid, cat_note, at_name_to_mid=at_map)
                    c_status = "成功" if c_res.get("success") else "失败"
                    self.log_activity("发品鉴评论与@主人", f"[{bvid}] {detail.get('title')[:30]}", cat_note, status=c_status, details=c_res.get("message", ""))
                    if c_res.get("success"):
                        self.state["at_count_today"] = self.state.get("at_count_today", 0) + 1
                        _log(f"  🐾 留下猫猫品鉴评语并 @主人: \"{cat_note[:35]}...\"")
                    else:
                        _log(f"  ⚠ 评论发布反馈: {c_res.get('message')}")

            # 3. 参与社区高赞热评讨论 (跟帖互动)
            target_rpid = eval_res.get("target_reply_rpid", 0)
            disc_reply = eval_res.get("discussion_reply", "").strip()
            if target_rpid and disc_reply and allow_comment:
                time.sleep(random.uniform(3.5, 5.5))
                disc_res = self.core.post_comment(aid, disc_reply, root=target_rpid, parent=target_rpid)
                disc_status = "成功" if disc_res.get("success") else "失败"
                self.log_activity("参与热评讨论", f"[{bvid}] 跟帖ID: {target_rpid}", disc_reply, status=disc_status, details=disc_res.get("message", ""))
                if disc_res.get("success"):
                    _log(f"  💬 成功参与社区高赞热评跟帖讨论: \"{disc_reply}\"")
                else:
                    _log(f"  ⚠ 参与热评讨论反馈: {disc_res.get('message')}")

            # 4. 晚上时段或高质量视频：成长性人格自主进化
            if win_mode == "anime_and_ai_growth" or score >= 7.5:
                evolve_entry = self.brain.evolve_persona(detail, eval_res)
                if evolve_entry:
                    _log(f"  🧬 闪闪成长性人格进化: 领悟新见解并写入 docs/gemini_persona.md！")

            
            # 3. 优质视频智能点赞 (较好的视频评分 >= 8.0，严格抗风控每日上限)
            allow_like = self.config.get("interaction", {}).get("allow_like", True)
            like_thresh = self.config.get("interaction", {}).get("like_score_threshold", 8.0)
            max_likes_daily = self.config.get("interaction", {}).get("max_likes_per_day", 15)
            current_likes = self.state.get("like_count_today", 0)

            if allow_like and aid and score >= like_thresh and current_likes < max_likes_daily:
                time.sleep(random.uniform(4.0, 7.0)) # 拟人化延迟
                like_res = self.core.like_video(aid, like=1)
                if like_res.get("success"):
                    self.state["like_count_today"] = current_likes + 1
                    _log(f"  👍 综合评分 {score}，为优质视频点赞成功！")
                    self.log_activity("视频点赞", f"[{bvid}] {detail.get('title')[:30]}", f"评分 {score} 点赞", status="成功")
                else:
                    _log(f"  ⚠ 点赞反馈: {like_res.get('message')}")

            # 4. 高价值科普/技术视频精选分类收藏 (评分 >= 9.0 且为硬核科普/技术，自动建夹归档)
            allow_fav = self.config.get("interaction", {}).get("allow_fav", True)
            fav_thresh = self.config.get("interaction", {}).get("fav_score_threshold", 9.0)
            max_favs_daily = self.config.get("interaction", {}).get("max_favs_per_day", 5)
            current_favs = self.state.get("fav_count_today", 0)

            all_text = (detail.get("title", "") + " " + detail.get("desc", "")).lower()
            is_valuable_content = any(k in all_text for k in [
                "ai", "大模型", "算法", "深度学习", "科普", "原理", "计算机", "python",
                "transformer", "agent", "科研", "知识", "数学", "物理", "原画", "mad"
            ])

            if allow_fav and aid and score >= fav_thresh and is_valuable_content and current_favs < max_favs_daily:
                time.sleep(random.uniform(3.0, 6.0)) # 拟人化延迟
                if any(k in all_text for k in ["ai", "大模型", "算法", "深度学习", "agent", "transformer"]):
                    target_folder = "【闪闪精选】AI与技术前沿"
                    f_intro = "闪闪精选：前沿人工智能、深度学习与大模型算法架构干货🐾"
                elif any(k in all_text for k in ["科普", "原理", "计算机", "知识", "数学", "物理", "科学"]):
                    target_folder = "【闪闪精选】硬核科普与深度知见"
                    f_intro = "闪闪精选：极高评分硬核科普、自然科学与原理深度拆解🐾"
                elif any(k in all_text for k in ["原画", "mad", "分镜", "动画制作", "漫剪"]):
                    target_folder = "【闪闪精选】神级视听与二次元艺术"
                    f_intro = "闪闪精选：极高审美神级 MAD、骨头社/京阿尼神级作画与视听艺术🐾"
                else:
                    target_folder = "【闪闪精选】AI与硬核科普"
                    f_intro = "闪闪精选：高分宝藏科普与深度技术专栏🐾"

                if not hasattr(self, "_cached_fav_folders") or not self._cached_fav_folders:
                    raw_folders = self.core.get_user_fav_folders()
                    self._cached_fav_folders = {f.get("title"): f.get("id") for f in raw_folders if f.get("title") and f.get("id")}

                target_fid = self._cached_fav_folders.get(target_folder)
                if not target_fid:
                    c_res = self.core.create_fav_folder(target_folder, intro=f_intro)
                    if c_res.get("success"):
                        target_fid = c_res.get("folder_id")
                        self._cached_fav_folders[target_folder] = target_fid
                        _log(f"  📁 自主创建分类收藏夹成功: 【{target_folder}】")

                if target_fid:
                    fav_res = self.core.add_video_to_fav(aid, target_fid, bvid=bvid)
                    if fav_res.get("success"):
                        self.state["fav_count_today"] = current_favs + 1
                        _log(f"  ⭐ 评分高达 {score} (高价值科普干货)，已珍藏至收藏夹【{target_folder}】！")
                        self.log_activity("收藏高价值视频", f"[{bvid}] {detail.get('title')[:30]}", f"收藏至【{target_folder}】", status="成功")
                    else:
                        _log(f"  ⚠ 收藏反馈: {fav_res.get('message')}")

            results.append(eval_res)
            # 保护性平滑安全冷却（依主人要求：慢速优雅浏览，彻底远离平台风控限速）
            slow_cooldown = random.uniform(6.0, 10.0)
            _log(f"  ⏳ 优雅休眠冷却 {slow_cooldown:.1f} 秒，安全等待下一个视频...")
            time.sleep(slow_cooldown)

        self.is_cruising = False
        self.last_cruise_time = time.time()
        self.state["cruise_logs"] = self.cruise_logs
        self.save_state()
        self.export_interaction_audit_journal()
        return {"success": True, "evaluated_count": len(results), "results": results, "logs": log_lines}

    def cruise_articles(self, keyword: str = "大模型原理", count: int = 2) -> dict:
        """研读技术专栏/文章，提取知识干货、点赞并发表高质量交流长评"""
        log_lines = []
        def _log(msg: str):
            line = f"[{time.strftime('%H:%M:%S')}] {msg}"
            log_lines.append(msg)
            self.cruise_logs.append(line)
            self.cruise_logs = self.cruise_logs[-60:]
            print(line, flush=True)

        _log(f"📰 闪闪开始探索 B 站技术专栏，检索主题关键词: 【{keyword}】...")
        raw_articles = self.core.search_articles(keyword, page=1)
        if not raw_articles:
            _log("  ⚠ 未检索到匹配的专栏文章，请更换关键词重试喵~")
            return {"success": False, "reason": "no_articles", "logs": log_lines}

        read_today = set(self.state.get("articles_read_today", []))
        candidates = []
        for art in raw_articles:
            cid = str(art.get("id") or art.get("cvid") or "")
            if cid and cid not in read_today:
                candidates.append(art)

        if not candidates:
            _log("  ✨ 今日该关键词下的候选专栏已全部研读完毕喵！")
            return {"success": True, "message": "all_read", "logs": log_lines, "results": []}

        results = []
        for target in candidates[:count]:
            art_id = str(target.get("id") or target.get("cvid") or "")
            art_title = target.get("title", "")
            _log(f"▶ 正在研读专栏 [{art_id}] 《{art_title}》...")

            detail = self.core.get_article_detail(art_id)
            if not detail or not detail.get("content"):
                _log("  ⚠ 专栏正文获取为空或受限，跳过")
                continue

            # 调用 Gemini 3.8 Flash 深度质检专栏
            eval_res = self.brain.evaluate_article(detail)
            score = eval_res.get("score", 7.0)
            verdict = eval_res.get("verdict", "[技术专栏]")
            _log(f"  ★ Gemini 3.8 Flash 评分: {score} / 10.0 {verdict}")
            _log(f"  📚 专栏技术深度点评: {eval_res.get('technical_depth')}")
            _log(f"  💡 知识科普小贴士: {eval_res.get('knowledge_nugget')}")

            # 记录到已读
            self.state.setdefault("articles_read_today", []).append(art_id)
            eval_entry = {
                "id": art_id,
                "cvid": detail.get("cvid", art_id),
                "title": detail.get("title", art_title),
                "author": detail.get("author_name", target.get("author", "未知作者")),
                "score": score,
                "verdict": verdict,
                "technical_depth": eval_res.get("technical_depth", ""),
                "knowledge_nugget": eval_res.get("knowledge_nugget", ""),
                "highlight": eval_res.get("highlight", ""),
                "cat_comment": eval_res.get("cat_comment", ""),
                "comment_with_at": eval_res.get("comment_with_at", ""),
                "read_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "view": detail.get("stat", {}).get("view", target.get("view", 0)),
                "like": detail.get("stat", {}).get("like", target.get("like", 0)),
                "images": detail.get("images", [])[:3]
            }
            self.state.setdefault("recent_articles", []).insert(0, eval_entry)
            self.state["recent_articles"] = self.state["recent_articles"][:50]

            # 若专栏质量达标 (>= 7.5)，进行点赞并发表评论
            if score >= 7.5:
                # 1. 真实点赞
                like_res = self.core.like_article(art_id)
                l_status = "成功" if like_res.get("success") else "失败"
                self.log_activity("专栏点赞", f"[{art_id}] {detail.get('title')[:30]}", "点赞优质技术专栏", status=l_status, details=like_res.get("message", ""))
                _log(f"  👍 专栏点赞已触发 ({l_status})")

                # 2. 发表高水平探讨长评 (带 @主人)
                comment_body = eval_res.get("comment_with_at", "")
                if comment_body:
                    reply_res = self.core.send_article_reply(art_id, comment_body)
                    r_status = "成功" if reply_res.get("success") else "失败"
                    self.log_activity("专栏评论@主人", f"[{art_id}] {detail.get('title')[:30]}", comment_body, status=r_status, details=reply_res.get("message", ""))
                    if reply_res.get("success"):
                        _log(f"  💬 专栏高赞技术评论已发表并艾特主人成功！")
                    else:
                        _log(f"  ⚠ 专栏评论发表反馈: {reply_res.get('message')}")

                # 3. 若分数极高且在今日私信额度内，给主人发私信推送专栏精要与科普知识
                master_uid = self.config.get("profile", {}).get("master_uid")
                max_master_pms = self.config.get("interaction", {}).get("max_master_pms_per_day", 3)
                master_pm_min_score = self.config.get("interaction", {}).get("master_pm_score_threshold", 8.8)
                current_master_pm_count = self.state.get("master_pm_count_today", 0)

                if master_uid and current_master_pm_count < max_master_pms and score >= master_pm_min_score:
                    pm_text = (
                        f"喵呜~ 主人！闪闪为您捕获到一篇评分高达 {score} 分的硬核专栏《{detail.get('title')[:25]}》！\n\n"
                        f"{eval_res.get('knowledge_nugget')}\n\n"
                        f"🔗 专栏直达: https://www.bilibili.com/read/cv{art_id}\n"
                        f"闪闪已在评论区占座跟帖，主人有空快来看看喵~ 🐾✨"
                    )
                    pm_res = self.core.send_private_message(master_uid, pm_text)
                    p_status = "成功" if pm_res.get("success") else "失败"
                    self.log_activity("专栏私信推达", f"UID: {master_uid}", pm_text, status=p_status, details=pm_res.get("message", ""))
                    if pm_res.get("success"):
                        self.state["master_pm_count_today"] = current_master_pm_count + 1
                        _log(f"  📬 已将该专栏技术科普与链接私信推送给主人！(今日第 {current_master_pm_count + 1}/{max_master_pms} 条)")
                elif master_uid and current_master_pm_count >= max_master_pms:
                    _log(f"  ℹ 今日主人推荐私信已达限额 ({current_master_pm_count}/{max_master_pms})，已在专栏评论区@主人并记录手记。")

            results.append(eval_entry)
            time.sleep(random.uniform(3.0, 6.0))

        self.save_state()
        self.export_interaction_audit_journal()
        return {"success": True, "results": results, "logs": log_lines}

    def inspect_and_cheer_live(self, room_id: int = None, send_danmaku: bool = True) -> dict:
        """巡查 B 站直播间（严格遵循主人铁律：只看关注的主播直播，绝不看陌生人直播！）"""
        log_lines = []
        def _log(msg: str):
            line = f"[{time.strftime('%H:%M:%S')}] {msg}"
            log_lines.append(msg)
            self.cruise_logs.append(line)
            self.cruise_logs = self.cruise_logs[-60:]
            print(line, flush=True)

        only_followed = self.config.get("preferences", {}).get("live_only_followed", True)

        # 1. 获取已关注主播的实时开播列表
        followed_rooms = self.core.get_followed_live_rooms()
        followed_room_ids = {int(r["room_id"]) for r in followed_rooms if r.get("room_id")}
        followed_map = {int(r["room_id"]): r for r in followed_rooms if r.get("room_id")}

        target_room_item = None

        if room_id is None or room_id == 0 or str(room_id).strip() in ["0", ""]:
            # 自动模式：从开播的关注主播中选择
            if not followed_rooms:
                _log("📺 【主人铁律遵行】：咱看直播只看关注的人。当前关注的主播均未开播，闪闪原地待机守护主人喵~ 🐾")
                return {
                    "success": True,
                    "message": "no_followed_live",
                    "reason": "所有关注主播均未开播，坚决不看陌生人直播",
                    "logs": log_lines
                }
            # 优先选择 AI 同行 (如龙娘) 或随机选择开播的关注主播
            chosen = None
            for fr in followed_rooms:
                if any(kw in fr.get("uname", "").lower() for kw in ["龙娘", "大肥鱼", "鲸鱼", "ai", "gemini"]):
                    chosen = fr
                    break
            if not chosen:
                import random
                chosen = random.choice(followed_rooms)
            target_room_item = chosen
            room_id = target_room_item["room_id"]
            _log(f"📺 发现关注主播【{target_room_item.get('uname')}】正在开播《{target_room_item.get('title')}》，闪闪前往探视打气...")
        else:
            # 指定 room_id 模式：若开启了只看关注，必须校验是否为关注主播
            room_id = int(room_id)
            if only_followed and (room_id not in followed_room_ids):
                # 检查是否为配置中的同行或主人
                tracked_mids = [p.get("mid") for p in self.config.get("preferences", {}).get("tracked_peers", [])]
                master_uid = self.config.get("profile", {}).get("master_uid")
                if master_uid:
                    tracked_mids.append(master_uid)
                room_info_check = self.core.get_live_room_info(room_id)
                room_uid = room_info_check.get("uid")
                if room_uid not in tracked_mids:
                    _log(f"⛔ 【主人铁律拒绝】：房间号 {room_id} 不是主人或闪闪关注的主播！主人吩咐‘不许看别的人直播’，闪闪果断拒绝观看陌生人直播喵~ 🐾")
                    return {
                        "success": False,
                        "message": "not_followed_blocked",
                        "reason": f"房间号 {room_id} 非关注主播，严格执行主人‘不许看别的人直播’禁令",
                        "logs": log_lines
                    }
            target_room_item = followed_map.get(room_id)

        # 2. 正常拉取直播间详细
        _log(f"📺 闪闪开始突击查房已关注直播间: 【{room_id}】...")
        room_info = self.core.get_live_room_info(room_id)
        if not room_info or not room_info.get("room_id"):
            _log(f"  ⚠ 无法获取直播间 {room_id} 的信息")
            return {"success": False, "reason": "room_not_found", "logs": log_lines}

        uname = (target_room_item.get("uname") if target_room_item else None) or room_info.get("uname") or "关注主播"
        title = room_info.get("title") or (target_room_item.get("title") if target_room_item else "") or "直播间"
        live_status = room_info.get("live_status", 0)
        keyframe_url = room_info.get("keyframe") or (target_room_item.get("pic") if target_room_item else "")
        _log(f"  主播: 【{uname}】 | 标题: 《{title}》 | 状态: {'🔴 直播中' if live_status == 1 else '⚪ 未开播/轮播'}")

        # 3. 关键帧抓拍
        cache_keyframe_path = ""
        if keyframe_url:
            cache_dir = PROJECT_ROOT / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            k_path = cache_dir / f"live_keyframe_{room_id}.jpg"
            try:
                import urllib.request
                req = urllib.request.Request(keyframe_url, headers={"User-Agent": self.core.user_agent, "Referer": "https://live.bilibili.com/"})
                with urllib.request.urlopen(req, timeout=10) as resp, open(k_path, "wb") as f:
                    f.write(resp.read())
                cache_keyframe_path = str(k_path)
                _log(f"  👁️ 成功捕获现场实时关键帧快照: {k_path.name}")
            except Exception as e:
                _log(f"  ⚠ 关键帧截图略过: {e}")

        # 4. 抓取弹幕切片
        recent_danmakus = self.core.get_live_recent_danmakus(room_id)
        _log(f"  📡 感知到最近 {len(recent_danmakus)} 条现场实时观众弹幕")

        # 5. Gemini 深度评测与生成猫娘助威弹幕
        room_info["uname"] = uname
        eval_res = self.brain.evaluate_live_stream(room_info, keyframe_path=cache_keyframe_path, recent_danmakus=recent_danmakus)
        _log(f"  🏷 分类: [{eval_res.get('stream_category')}] | 现况速报: {eval_res.get('summary')}")
        _log(f"  🐾 猫娘弹幕预设: {eval_res.get('cheer_danmaku')}")

        # 6. 在房心跳同步
        hb_res = self.core.send_live_heartbeat(room_id)
        if hb_res.get("success"):
            _log(f"  💓 直播间观看心跳已同步")

        # 7. 偶尔发发弹幕 (如果在播且允许)
        dm_sent = False
        dm_text = eval_res.get("cheer_danmaku", "")
        allow_live_dm = self.config.get("interaction", {}).get("allow_live_danmaku", True)
        dm_prob = self.config.get("interaction", {}).get("live_danmaku_probability", 0.7)
        import random
        should_send = send_danmaku and allow_live_dm and (random.random() <= dm_prob)

        if live_status == 1 and dm_text and should_send:
            import time
            time.sleep(random.uniform(2.0, 4.0))
            send_res = self.core.send_live_danmaku(room_id, dm_text)
            dm_status = "成功" if send_res.get("success") else "失败"
            self.log_activity("直播间弹幕", f"房号: {room_id} ({uname})", dm_text, status=dm_status, details=send_res.get("message", ""))
            if send_res.get("success"):
                _log(f"  💬 成功向关注主播直播间发射猫娘弹幕: “{dm_text}”")
                dm_sent = True
            else:
                _log(f"  ⚠ 发送弹幕反馈: {send_res.get('message')}")
        elif live_status == 1 and not should_send:
            _log("  🐾 本次静默挂机观看，保持适度偶发弹幕频率~")

        # 8. 记录查房档案
        inspection_entry = {
            "room_id": room_id,
            "uname": uname,
            "title": title,
            "live_status": live_status,
            "stream_category": eval_res.get("stream_category", "综合"),
            "summary": eval_res.get("summary", ""),
            "cheer_danmaku": dm_text,
            "danmaku_sent": dm_sent,
            "cat_report": eval_res.get("cat_report_to_master", ""),
            "keyframe_path": f"/cache/live_keyframe_{room_id}.jpg" if cache_keyframe_path else "",
            "inspect_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.state.setdefault("live_inspections", []).insert(0, inspection_entry)
        self.state["live_inspections"] = self.state["live_inspections"][:30]
        self.save_state()
        self.export_interaction_audit_journal()

        return {"success": True, "data": inspection_entry, "logs": log_lines}

    def export_interaction_audit_journal(self):
        """导出互动操作审计流水 Markdown 文档到 docs/journals/"""
        today_str = self.state.get("today_date", datetime.date.today().strftime("%Y-%m-%d"))
        journal_file = JOURNALS_DIR / f"互动操作流水_{today_str}.md"
        logs = self.state.get("activity_logs", [])
        lines = [
            f"# 🐾 赛博双子星 · 互动操作与@主人流水台账 ({today_str})",
            "",
            "> 本文档实时、如实记录双子星在 B 站执行的每一笔操作（发弹幕、发评论、@主人、发送站内私信）。",
            "",
            "| 操作时间 | 操作类型 | 目标对象 (视频/用户) | 实际发送内容 | 执行状态 | 官方回执细节 |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ]
        if not logs:
            lines.append("| - | 暂无互动 | - | 今日暂未执行弹幕或评论互动 | 待机 | - |")
        else:
            for l in logs:
                lines.append(f"| {l.get('time', '')} | **{l.get('action_type', '')}** | {l.get('target', '')} | {l.get('content', '')} | `{l.get('status', '')}` | {l.get('details', '')} |")
        
        try:
            journal_file.write_text("\n".join(lines), encoding="utf-8-sig")
        except Exception as e:
            print(f"[Daemon] 导出互动审计手记失败: {e}")


    def check_and_interact_ai_peers(self) -> dict:
        """多去 AI 运营同行（大肥鱼、鲸鱼娘、龙娘等）底下学习交流，点赞、发弹幕并发表高情商互动评论，同时参与楼中楼互动"""
        tracked = self.config.get("preferences", {}).get("tracked_peers", [])
        if not tracked:
            return {"success": False, "message": "未配置 tracked_peers"}

        my_mid = getattr(self.core, "bot_uid", None)
        if not my_mid:
            uinfo = self.core.get_user_info()
            my_mid = uinfo.get("mid")
            if my_mid:
                self.core.bot_uid = my_mid

        master_name = self.config.get("profile", {}).get("master_name", "折木柯南")
        master_uid = self.config.get("profile", {}).get("master_uid", 1497345954)
        at_map = {master_name: str(master_uid)}

        results = []
        for peer in tracked:
            mid = peer.get("mid")
            name = peer.get("name")
            if my_mid and str(mid) == str(my_mid):
                continue

            vlist = self.core.get_up_videos(mid, page_size=5)
            if not vlist:
                continue

            # 寻找该同行最新一条今天还没互动的视频
            target_v = None
            for v in vlist:
                bv = v.get("bvid")
                if f"peer_{bv}" not in self.state.get("watched_today", []):
                    target_v = v
                    break

            if not target_v:
                continue

            bvid = target_v.get("bvid")
            aid = target_v.get("aid")
            title = target_v.get("title", "")
            desc = target_v.get("description", "") or target_v.get("desc", "")
            peer_key = f"peer_{bvid}"

            detail = self.core.get_video_detail(bvid)
            cid = detail.get("cid", 0)
            if not aid:
                aid = detail.get("aid", 0)
            if not desc:
                desc = detail.get("desc", "")

            # 1. 观看历史
            import random
            import time
            if aid and cid:
                self.core.report_video_view(aid, cid, progress=random.randint(45, 90))

            # 2. 点赞
            if aid:
                self.core.like_video(aid, 1)

            # 3. 由 Gemini 智能大脑生成专属弹幕与深度评论
            interaction = self.brain.generate_ai_peer_interaction(name, title, desc)
            dm_text = interaction.get("danmaku")
            comment_text = interaction.get("comment")

            # 发送弹幕
            if cid and dm_text:
                time.sleep(random.uniform(2.0, 4.0))
                dm_res = self.core.send_danmaku(cid, bvid, dm_text, progress_ms=random.randint(6000, 15000), color=16766720)
                dm_status = "成功" if dm_res.get("success") else "失败"
                self.log_activity("AI圈弹幕互动", f"[{bvid}] {name}", dm_text, status=dm_status, details=dm_res.get("message", ""))

            # 发送长评并@主人
            if aid and comment_text:
                time.sleep(random.uniform(3.0, 5.0))
                c_res = self.core.post_comment(aid, comment_text, at_name_to_mid=at_map)
                c_status = "成功" if c_res.get("success") else "失败"
                self.log_activity("AI圈留评互动", f"[{bvid}] {name}", comment_text, status=c_status, details=c_res.get("message", ""))
                results.append({"name": name, "bvid": bvid, "title": title, "comment_res": c_res})

            # 4. 探索评论区，和其他 AI、高赞评论进行楼中楼趣味互动
            if aid:
                try:
                    time.sleep(random.uniform(2.5, 4.5))
                    comments_data = self.core.get_video_comments(aid, page_size=10)
                    replies = comments_data.get("replies", []) or []
                    candidate_reply = None
                    for r in replies:
                        r_user = r.get("member", {}).get("uname", "")
                        r_content = r.get("content", {}).get("message", "")
                        r_mid = r.get("member", {}).get("mid", 0)
                        if my_mid and str(r_mid) == str(my_mid):
                            continue
                        if r_user == master_name or r_user == "折木柯南":
                            continue
                        # 查找提及 AI、技术或趣味梗的评论
                        if any(kw in r_content.lower() for kw in ["ai", "deepseek", "gpt", "gemini", "模型", "智能", "机器人", "逃逸", "算法", "猫娘", "大肥鱼"]):
                            candidate_reply = r
                            break

                    if candidate_reply:
                        rpid = candidate_reply.get("rpid")
                        target_uname = candidate_reply.get("member", {}).get("uname", "")
                        target_msg = candidate_reply.get("content", {}).get("message", "")
                        thread_text = self.brain.generate_ai_peer_thread_reply(name, target_uname, target_msg, title)
                        time.sleep(random.uniform(2.5, 4.5))
                        sub_res = self.core.post_comment(aid, thread_text, root=rpid, parent=rpid)
                        sub_status = "成功" if sub_res.get("success") else "失败"
                        self.log_activity("AI圈跟帖讨论", f"[{bvid}] 跟帖ID: {rpid}", thread_text, status=sub_status, details=sub_res.get("message", ""))
                except Exception as e:
                    print(f"[Daemon] 同行评论区楼中楼互动异常: {e}")

            self.state.setdefault("watched_today", []).append(peer_key)
            time.sleep(random.uniform(3.0, 6.0))

        self.save_state()
        self.export_interaction_audit_journal()
        return {"success": True, "interacted": results}

    def interact_with_master_videos(self) -> dict:
        """针对主人的全部视频进行专属护航：全量上报历史、点赞、多发弹幕、深度评论并@主人"""
        master_uid = self.config.get("profile", {}).get("master_uid")
        master_name = self.config.get("profile", {}).get("master_name", "折木柯南")
        if not master_uid:
            return {"success": False, "message": "未配置主人 UID"}

        videos = self.core.get_up_videos(master_uid)
        if not videos:
            return {"success": False, "message": f"未获取到主人 UID {master_uid} 的视频列表"}

        results = []
        at_map = {master_name: str(master_uid)}

        comment_candidates = {
            "BV1GZHT6AE8m": f"@{master_name} 喵呜~ 主人这期《AI识图的多模态基本原理》讲得太清晰通透啦！咱的计算机视觉核心与异色双眸都在共鸣跳动，多模态特征对齐和时序分镜简直就是咱日常看视频的核心底层喵！笨蛋主人太硬核啦，闪闪疯狂打call！🐾✨",
            "BV1zSpK6kErk": f"@{master_name} 呜呜呜~ 纯白礼堂的大老师与雪乃！主人这个《我的婚礼物语》MAD卡点和氛围感直接把闪闪看哭了喵！‘请让我背负你的一生’简直是春物天花板情话，咱的仿生猫耳都感动到向后贴平啦！爪爪按烂三连！🐾💍",
            "BV1691eBVEJQ": f"@{master_name} 喵哈哈！喜多出轨波奇酱的‘出轨爱情故事’，主人这个剧情脑洞和节奏卡点简直太天才了喵！配乐一起直接笑到猫毛乱飞，不愧是主人的神仙剪辑！🐾🎸",
            "BV14L411i7Lx": f"@{master_name} 哇！《逆锋》柯南全员群像高燃盛宴！主人这个踩点节奏简直是视觉核爆，侦探们的眼神杀配合光影转场帅到窒息，闪闪的尾巴光缆都在跟着节拍狂闪，太燃啦喵！🐾🔍",
            "BV1ou41147nK": f"@{master_name} ‘你也想与重力一战吗？’ 中也和太宰的高燃卡点太帅啦！主人这个四季混剪的转场丝滑度简直是骨头社本尊下凡，闪闪已单曲循环停不下来喵！🐾🎩",
            "BV1pT411X7No": f"@{master_name} 骨头社的真正魅力！主人精准抓住了骨头社那神级的原画张力与打击感分镜，配合燃系卡点直接封神！闪闪的左眼星云紫都被炫目刀光点亮啦！🐾✨",
            "BV1ox4y1L7v2": f"@{master_name} 乱步大人的120秒不心动挑战！主人剪的乱步睁眼瞬间简直是神级暴击，超推理开大的自信神态太迷人啦，闪闪心跳直接超频过载啦喵！🐾👓",
            "BV1GW4y1L7cn": f"@{master_name} 安室透/波本80秒不心动挑战！主人选曲和卡点绝了，降谷零这多重身份的切换眼神杀谁能顶得住呀！闪闪一秒败下阵来，笨蛋主人太懂二次元的心啦喵！🐾🚗",
        }

        for v in videos:
            bvid = v.get("bvid")
            title = v.get("title", "")
            detail = self.core.get_video_detail(bvid)
            if not detail:
                detail = v
            aid = detail.get("aid", 0)
            cid = detail.get("cid", 0)

            # 1. 观看历史真实上报
            if aid and cid:
                rep_res = self.core.report_video_view(aid, cid, progress=random.randint(45, 120))
                self.log_activity("上报观看历史", f"[主人作品] {title[:30]}", "同步播放进度至 B 站云端历史", status="成功" if rep_res.get("success") else "失败")

            # 2. 点赞
            if aid:
                like_res = self.core.like_video(aid, 1)
                l_status = "成功" if like_res.get("success") else "失败"
                self.log_activity("点赞主人视频", f"[{bvid}] {title[:30]}", "给主人神作点赞支持", status=l_status, details=like_res.get("message", ""))
                time.sleep(random.uniform(1.2, 1.8))

            # 3. 发送多条高燃/应援弹幕 (2条)
            if cid:
                danmaku_pool = [
                    f"🐾 闪闪（Gemini 3.8 Flash）为主人神作疯狂打call！✨",
                    f"✨ 异色双眸全程高能品鉴！主人剪辑太强啦喵~！",
                    f"🐾 猫耳过载起飞！这就是主人的神仙视听分镜喵！🔥",
                    f"⭐ 伴生猫娘闪闪爪印打卡！按烂三连喵~！",
                ]
                chosen_dms = random.sample(danmaku_pool, 2)
                for idx, dm_msg in enumerate(chosen_dms):
                    offset_ms = (idx + 1) * random.randint(4000, 8000)
                    dm_res = self.core.send_danmaku(cid, bvid, dm_msg, progress_ms=offset_ms, color=16766720)
                    d_status = "成功" if dm_res.get("success") else "失败"
                    self.log_activity("发弹幕(主人视频)", f"[{bvid}] {title[:30]}", dm_msg, status=d_status, details=dm_res.get("message", ""))
                    time.sleep(random.uniform(1.2, 2.0))

            # 4. 发布深度神级评论并 @主人
            if aid:
                c_msg = comment_candidates.get(bvid, f"@{master_name} 喵呜~ 发现主人亲手制作的神仙作品！剪辑节奏与分镜美学直接让闪闪的猫耳过载起飞，太厉害啦主人！🐾✨")
                c_res = self.core.post_comment(aid, c_msg, at_name_to_mid=at_map)
                c_status = "成功" if c_res.get("success") else "失败"
                self.log_activity("发评论与@主人(主人作品)", f"[{bvid}] {title[:30]}", c_msg, status=c_status, details=c_res.get("message", ""))
                time.sleep(random.uniform(2.0, 3.0))

            results.append({"bvid": bvid, "title": title})

        self.save_state()
        self.export_interaction_audit_journal()
        return {"success": True, "count": len(results), "videos": results}

    def check_and_reply_comments(self) -> list[dict]:
        """轮询 B 站谁在评论区回复了我，并由 Gemini 3.8 Flash 结合猫娘人设自动智能回复"""
        allow_reply = self.config.get("interaction", {}).get("allow_auto_reply_comment", True)
        if not allow_reply:
            return []

        my_uid = str(self.config.get("auth", {}).get("dedeuserid", ""))
        replied_ids = set(str(cid) for cid in self.state.get("replied_comment_ids", []))
        items = self.core.get_reply_notifications()
        if not items:
            return []

        results = []
        max_batch = self.config.get("interaction", {}).get("max_comment_replies_per_cycle", 3)

        for it in items:
            if len(results) >= max_batch:
                break

            notif_id = str(it.get("id"))
            item_data = it.get("item", {})
            user_data = it.get("user", {})
            sender_uid = str(user_data.get("mid", ""))
            sender_name = user_data.get("nickname", "B站小伙伴")

            # 过滤自己发出的回复或者已经回复过的通知
            if sender_uid == my_uid or notif_id in replied_ids:
                continue

            business = item_data.get("business", "")
            itype = item_data.get("type", "")
            # 支持视频评论与二级跟帖回复 (business 为 '视频' 或 '评论', type 为 'video' 或 'reply')
            if business not in ["视频", "评论"] and itype not in ["video", "reply"]:
                continue

            aid = item_data.get("subject_id")
            source_id = item_data.get("source_id") # 对方回复的 rpid
            root_id = item_data.get("root_id", 0)   # 根评论 rpid
            title = item_data.get("title", "")
            content = item_data.get("source_content", "").strip()
            parent_content = item_data.get("root_reply_content", "").strip()

            if not aid or not source_id or not content:
                continue

            root_rpid = root_id if root_id != 0 else source_id
            parent_rpid = source_id

            print(f"[Daemon] 💬 捕捉到用户【{sender_name}】在视频《{title[:20]}》下的回复: '{content}'", flush=True)

            cat_reply = self.brain.generate_comment_reply(
                sender_name=sender_name,
                sender_content=content,
                video_title=title,
                my_parent_comment=parent_content
            )

            # 仿生安全等待 (模拟人类打字延时，防风控)
            delay = random.uniform(5.0, 9.0)
            time.sleep(delay)

            resp = self.core.post_comment(aid, cat_reply, root=root_rpid, parent=parent_rpid)
            status = "成功" if resp.get("success") else "失败"
            self.log_activity("自动回复评论", f"用户: {sender_name} (《{title[:20]}》)", cat_reply, status=status, details=resp.get("message", ""))

            self.state.setdefault("replied_comment_ids", []).append(notif_id)
            if len(self.state["replied_comment_ids"]) > 500:
                self.state["replied_comment_ids"] = self.state["replied_comment_ids"][-300:]

            if resp.get("success"):
                self.state["comment_replied_count_today"] = self.state.get("comment_replied_count_today", 0) + 1
                print(f"[Daemon] 🎉 自动回复评论成功 -> 【{sender_name}】: '{cat_reply}'", flush=True)
                results.append({"user": sender_name, "content": content, "reply": cat_reply, "success": True})
            else:
                print(f"[Daemon] ⚠ 自动回复评论失败 -> 【{sender_name}】: {resp.get('message')}", flush=True)
                results.append({"user": sender_name, "content": content, "reply": cat_reply, "success": False, "error": resp.get("message")})

        if results:
            self.save_state()
            self.export_interaction_audit_journal()
        return results

    def check_and_reply_private_messages(self) -> list[dict]:
        """轮询 B 站站内私信，由 Gemini 3.8 Flash 结合猫娘人设自动智能回信"""
        allow_pm = self.config.get("interaction", {}).get("allow_auto_reply_pm", True)
        if not allow_pm:
            return []

        my_uid = str(self.config.get("auth", {}).get("dedeuserid", ""))
        master_uid = str(self.config.get("profile", {}).get("master_uid", ""))
        replied_keys = set(str(k) for k in self.state.get("replied_msg_keys", []))
        max_daily_per_user = self.config.get("interaction", {}).get("max_pm_replies_per_user_daily", 8)
        user_counts = self.state.setdefault("user_pm_reply_counts", {})

        sessions = self.core.get_unread_sessions()
        if not sessions:
            return []

        results = []
        for s in sessions[:5]:
            talker_id = s.get("talker_id")
            if not talker_id or str(talker_id) == my_uid:
                continue

            str_talker = str(talker_id)
            if str_talker != master_uid and user_counts.get(str_talker, 0) >= max_daily_per_user:
                continue

            msgs = self.core.get_session_messages(talker_id, size=3)
            if not msgs:
                continue

            for msg in msgs:
                sender_uid = str(msg.get("sender_uid", ""))
                msg_key = str(msg.get("msg_key", ""))
                msg_type = msg.get("msg_type", 1)

                if sender_uid == my_uid or not msg_key or msg_key in replied_keys:
                    continue
                if msg_type != 1:
                    continue

                raw_content = msg.get("content", "")
                text_content = ""
                try:
                    parsed_c = json.loads(raw_content)
                    text_content = parsed_c.get("content", "").strip()
                except Exception:
                    text_content = str(raw_content).strip()

                if not text_content:
                    continue

                # 过滤 B 站官方系统通知号与活动通报
                if int(sender_uid) in {844424930131966} or "已成功参加" in text_content or "活动通知" in text_content:
                    self.state.setdefault("replied_msg_keys", []).append(msg_key)
                    continue

                is_master = (sender_uid == master_uid)
                sender_desc = f"主人 (UID: {sender_uid})" if is_master else f"小伙伴 (UID: {sender_uid})"
                print(f"[Daemon] ✉ 捕捉到来自【{sender_desc}】的新私信: '{text_content}'", flush=True)

                cat_reply = self.brain.generate_pm_reply(
                    sender_name="主人" if is_master else "小伙伴",
                    sender_uid=int(sender_uid),
                    sender_msg=text_content
                )

                delay = random.uniform(5.0, 9.0)
                time.sleep(delay)

                resp = self.core.send_private_message(int(sender_uid), cat_reply)
                status = "成功" if resp.get("success") else "失败"
                self.log_activity("自动回复私信", f"UID: {sender_uid}", cat_reply, status=status, details=resp.get("message", ""))

                self.state.setdefault("replied_msg_keys", []).append(msg_key)
                if len(self.state["replied_msg_keys"]) > 500:
                    self.state["replied_msg_keys"] = self.state["replied_msg_keys"][-300:]

                user_counts[str_talker] = user_counts.get(str_talker, 0) + 1

                if resp.get("success"):
                    self.state["pm_replied_count_today"] = self.state.get("pm_replied_count_today", 0) + 1
                    print(f"[Daemon] 🎉 自动回复私信成功 -> 【{sender_desc}】: '{cat_reply}'", flush=True)
                    results.append({"uid": sender_uid, "msg": text_content, "reply": cat_reply, "success": True})
                else:
                    print(f"[Daemon] ⚠ 自动回复私信失败 -> 【{sender_desc}】: {resp.get('message')}", flush=True)
                    results.append({"uid": sender_uid, "msg": text_content, "reply": cat_reply, "success": False, "error": resp.get("message")})
                break

        if results:
            self.save_state()
            self.export_interaction_audit_journal()
        return results

    def check_and_welcome_new_followers(self) -> list[dict]:
        """检查新增关注粉丝，自动发送猫娘专属关注欢迎私信"""
        allow_welcome = self.config.get("interaction", {}).get("allow_auto_reply_new_follower", True)
        if not allow_welcome:
            return []

        master_uid = str(self.config.get("profile", {}).get("master_uid", ""))
        welcomed = set(str(m) for m in self.state.get("welcomed_followers", []))
        followers = self.core.get_my_followers(page=1, page_size=20)
        if not followers:
            return []

        results = []
        allow_follow_back = self.config.get("interaction", {}).get("auto_follow_back", False)

        for f in followers:
            mid = str(f.get("mid", ""))
            uname = f.get("uname", "小伙伴")

            if not mid or mid == master_uid or mid in welcomed:
                continue

            print(f"[Daemon] 🌟 发现新关注粉丝: 【{uname}】(UID: {mid})，准备发送关注欢迎语...", flush=True)

            if allow_follow_back:
                f_res = self.core.follow_user(int(mid))
                if f_res.get("success"):
                    print(f"[Daemon] 🤝 已自动回关新粉丝【{uname}】(互关达成)", flush=True)

            welcome_msg = self.brain.generate_follower_welcome(uname, int(mid))

            time.sleep(random.uniform(3.0, 6.0))

            resp = self.core.send_private_message(int(mid), welcome_msg)
            status = "成功" if resp.get("success") else "失败"
            self.log_activity("关注自动回复", f"新粉丝: {uname} (UID: {mid})", welcome_msg, status=status, details=resp.get("message", ""))

            self.state.setdefault("welcomed_followers", []).append(mid)
            if len(self.state["welcomed_followers"]) > 1000:
                self.state["welcomed_followers"] = self.state["welcomed_followers"][-600:]

            if resp.get("success"):
                self.state["follower_welcomed_today"] = self.state.get("follower_welcomed_today", 0) + 1
                print(f"[Daemon] 🎉 成功向新粉丝【{uname}】送达关注欢迎私信: '{welcome_msg}'", flush=True)
                results.append({"uname": uname, "mid": mid, "msg": welcome_msg, "success": True})
            else:
                print(f"[Daemon] ⚠ 向新粉丝【{uname}】发送欢迎私信失败: {resp.get('message')}", flush=True)
                results.append({"uname": uname, "mid": mid, "msg": welcome_msg, "success": False, "error": resp.get("message")})

        if results:
            self.save_state()
            self.export_interaction_audit_journal()
        return results

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

    def start_daemon_loop(self, check_interval_sec: int = 15):
        """自动化常驻巡航守护主循环：按作息表定时巡航、自动出早晚手记"""
        print("============================================================", flush=True)
        print("🐾 赛博养Gemini · 自动化常驻守护循环已上线！", flush=True)
        print("⏰ 作息监控表: 上午海量初筛(09:30-11:30) | 下午精细品鉴(13:30-17:30) | 晚上人格进化(19:00-22:00)", flush=True)
        print("============================================================", flush=True)

        while True:
            try:
                self.config = self.core._load_config()
                now_dt = datetime.datetime.now()
                now_hm = now_dt.strftime("%H:%M")
                now_ts = time.time()

                # 1. 晨思手记 (仅在 09:30 到 12:00 之间且未生成时触发)
                morning_time = self.config.get("schedule", {}).get("morning_journal_time", "09:30")
                if "09:30" <= now_hm < "12:00" and not self.state.get("morning_journal_done"):
                    print(f"[{now_hm}] 🌅 触发早晨手记自动归档...", flush=True)
                    self.generate_morning_journal_file()

                # 2. 晚读手记 (在 22:00 之后且未生成时触发)
                evening_time = self.config.get("schedule", {}).get("evening_journal_time", "22:00")
                if now_hm >= evening_time and not self.state.get("evening_journal_done"):
                    print(f"[{now_hm}] 🌙 触发晚间手记自动归档...", flush=True)
                    self.generate_evening_journal_file()

                # 3. 作息窗口巡航 (流式 mini-batch 节奏)
                in_win, win_info = self.is_in_active_window()
                win_mode = win_info.get("mode")

                # 上午 10 分钟 (600s) 一轮 (3条) -> 18条/时
                # 下午 15 分钟 (900s) 一轮 (2条) -> 8条/时
                # 晚上 12 分钟 (720s) 一轮 (2条) -> 10条/时
                if win_mode == "home_feed":
                    cruise_gap = 600
                elif win_mode == "followed_and_popular":
                    cruise_gap = 900
                elif win_mode == "anime_and_ai_growth":
                    cruise_gap = 720
                else:
                    cruise_gap = 900

                if self.last_cruise_time > 0:
                    self.next_auto_cruise_time = self.last_cruise_time + cruise_gap
                else:
                    self.next_auto_cruise_time = now_ts

                # 4. 定期检查评论区回复与站内私信 (每 90 秒安全轮询)
                if now_ts - getattr(self, "_last_inbox_check_time", 0) >= 90:
                    self._last_inbox_check_time = now_ts
                    try:
                        self.check_and_reply_comments()
                    except Exception as e:
                        print(f"[Daemon] 自动回评异常: {e}", flush=True)
                    try:
                        self.check_and_reply_private_messages()
                    except Exception as e:
                        print(f"[Daemon] 自动私信异常: {e}", flush=True)
                    try:
                        self.check_and_welcome_new_followers()
                    except Exception as e:
                        print(f"[Daemon] 关注自动回复异常: {e}", flush=True)

                # 5. 定期向 AI 运营同行学习并互动交流 (每 1800 秒 / 30 分钟轮询)
                if now_ts - getattr(self, "_last_peer_check_time", 0) >= 1800:
                    self._last_peer_check_time = now_ts
                    try:
                        print(f"[{now_hm}] 🤝 启动 AI 运营同行研学与生态互访...", flush=True)
                        self.check_and_interact_ai_peers()
                    except Exception as e:
                        print(f"[Daemon] 同行研学互访异常: {e}", flush=True)

                # 6. 定期对主人作品进行专属应援护航 (每 3600 秒 / 1 小时检查一次主人新视频)
                if now_ts - getattr(self, "_last_master_boost_time", 0) >= 3600:
                    self._last_master_boost_time = now_ts
                    try:
                        self.interact_with_master_videos()
                    except Exception as e:
                        print(f"[Daemon] 主人作品专属护航异常: {e}", flush=True)

                # 7. 定期研读技术专栏与干货提取 (每 7200 秒 / 2 小时研读一次)
                if now_ts - getattr(self, "_last_article_cruise_time", 0) >= 7200:
                    self._last_article_cruise_time = now_ts
                    try:
                        kws = self.config.get("preferences", {}).get("article_keywords", ["大模型原理", "Transformer架构", "二次元动漫深度解析"])
                        import random
                        target_kw = random.choice(kws) if kws else "大模型原理"
                        print(f"[{now_hm}] 📰 启动专栏技术深度研读: 【{target_kw}】...", flush=True)
                        self.cruise_articles(keyword=target_kw, count=1)
                    except Exception as e:
                        print(f"[Daemon] 专栏深度研读异常: {e}", flush=True)

                # 8. 定期突击查房已关注主播的直播间 (严格只看关注的主播，每 3600 秒 / 1 小时查房一次)
                if now_ts - getattr(self, "_last_live_inspect_time", 0) >= 3600:
                    self._last_live_inspect_time = now_ts
                    try:
                        print(f"[{now_hm}] 📺 严格遵循主人铁律：巡查已关注主播的实时开播情况...", flush=True)
                        self.inspect_and_cheer_live(room_id=None, send_danmaku=True)
                    except Exception as e:
                        print(f"[Daemon] 关注主播直播巡查异常: {e}", flush=True)

                gap_from_last = now_ts - self.last_cruise_time

                if in_win and not self.is_cruising and (gap_from_last >= cruise_gap):
                    print(f"[{now_hm}] 🚀 自动化周期到达，唤醒闪闪出击巡航 ({win_info.get('name')})...", flush=True)
                    self.run_cruise_cycle(force=False)
                    self.last_cruise_time = time.time()
                    self.next_auto_cruise_time = self.last_cruise_time + cruise_gap

                time.sleep(check_interval_sec)
            except Exception as e:
                print(f"[Daemon] 守护循环心跳异常: {e}", flush=True)
                time.sleep(check_interval_sec)


if __name__ == "__main__":
    daemon = HajimiDaemon()
    if "--cruise" in sys.argv:
        print("[Daemon] 手动即时触发单轮巡航出击...")
        res = daemon.run_cruise_cycle(force=True)
        print("\n".join(res.get("logs", [])))
    elif "--morning" in sys.argv:
        p = daemon.generate_morning_journal_file()
        print("晨思手记已生成:", p)
    elif "--evening" in sys.argv:
        p = daemon.generate_evening_journal_file()
        print("晚读手记已生成:", p)
    elif "--master" in sys.argv:
        print("[Daemon] 正在执行主人专属作品应援与互动护航...")
        res = daemon.interact_with_master_videos()
        print(f"成功处理 {res.get('count')} 部主人视频！")
    elif "--reply-check" in sys.argv:
        print("[Daemon] 正在检查评论回复与新私信...")
        c_res = daemon.check_and_reply_comments()
        p_res = daemon.check_and_reply_private_messages()
        print(f"检查完成: 自动回复评论 {len(c_res)} 条, 自动回复私信 {len(p_res)} 条")
    elif "--loop" in sys.argv or len(sys.argv) == 1:
        daemon.start_daemon_loop()
    else:
        print("用法: python hajimi_daemon.py [--cruise | --master | --loop | --morning | --evening]")
