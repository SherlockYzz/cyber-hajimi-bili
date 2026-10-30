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


def is_safe_comment(text: str) -> bool:
    """严格检验拟外发评论文本：严禁包含任何过激、贬低、挑刺或负面劝退词汇，必须维持文明知性与良好形象"""
    if not text or len(text.strip()) == 0:
        return False
    toxic_words = [
        "画大饼", "垃圾", "水货", "水课", "快撤退", "快跑", "避雷", "避坑",
        "骗子", "骗人", "销售片", "引流骗", "劣质", "抄袭", "恶心", "差劲",
        "不要脸", "毒素", "炸毛", "吐掉", "营销号", "割韭菜", "下头", "烂片",
        "难看", "洗脑", "智商税", "别看", "快溜", "溜了", "坑人", "太差",
        "退钱", "毁原作", "恶俗", "毫无价值", "恶评", "劝退", "忽悠", "糊弄"
    ]
    return not any(w in text for w in toxic_words)


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
            "lottery_joined_count_today": 0,
            "joined_lottery_dyn_ids": [],
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
                        saved["lottery_joined_count_today"] = 0
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

            # 4. CC 双语字幕文本 (支持多P大课深度联读，避免首P导学误判)
            subtitles = ""
            if cid:
                subtitles = self.core.get_video_subtitles(bvid, cid)
                pages = detail.get("pages", [])
                if len(pages) > 1:
                    first_part = pages[0].get("part", "")
                    intro_kw = ["导学", "大纲", "前言", "绪论", "介绍", "先导", "开篇"]
                    if any(k in first_part for k in intro_kw) and len(pages) >= 2:
                        p2_cid = pages[1].get("cid")
                        if p2_cid:
                            p2_sub = self.core.get_video_subtitles(bvid, p2_cid)
                            if p2_sub:
                                subtitles = f"【P1 {first_part} 字幕摘要】:\n{subtitles[:3000]}\n\n【P2 {pages[1].get('part')} 正式核心章节字幕】:\n{p2_sub[:10000]}"
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

            # =========================================================================
            # 宝藏视频铁律门禁（主人绝对指令）：
            # 只有 score >= threshold 的极品宝藏视频，才允许执行任何公开互动！
            # 包括：发弹幕、发主楼评论、参与热评讨论、点赞、收藏与向主人私信推荐。
            # 对于非宝藏视频，全流程保持绝对礼貌静默：不发弹幕、不发评论、不参与讨论，
            # 绝不在他人评论区留痕，绝不言语过激，不给别人留下不良印象，也不向主人汇报任何负面内容。
            # =========================================================================
            at_map = {master_name: str(master_uid)} if master_uid and master_name else {}

            if score >= threshold:
                _log(f"  ✨ 【宝藏视频认证成功】评分: {score}分 (>= 门槛{threshold}分)，准许执行高质公开互动与主人推荐！")
                self.state.setdefault("treasures_today", []).append({
                    "bvid": bvid,
                    "title": eval_res.get("title", ""),
                    "owner": eval_res.get("owner", ""),
                    "score": score,
                    "highlight": eval_res.get("highlight", ""),
                    "cat_comment": eval_res.get("cat_comment", ""),
                })

                # 1. 宝藏视频专属应援弹幕 (积极正面、文明治愈)
                if allow_danmaku and cid:
                    dm_txt = "🐾 闪闪（Gemini 3.8 Flash）发现高能宝藏！为神作疯狂打call喵！✨"
                    dm_col = 16766720 # 暖阳金黄
                    time.sleep(random.uniform(2.5, 4.5))
                    dm_res = self.core.send_danmaku(cid, bvid, dm_txt, progress_ms=random.randint(2500, 8000), color=dm_col)
                    status = "成功" if dm_res.get("success") else "失败"
                    self.log_activity("发弹幕", f"[{bvid}] {detail.get('title')[:30]}", dm_txt, status=status, details=dm_res.get("message", ""))
                    if dm_res.get("success"):
                        _log(f"  💬 宝藏视频投喂应援弹幕成功: \"{dm_txt}\"")
                    else:
                        _log(f"  ⚠ 投喂弹幕反馈: {dm_res.get('message')}")

                # 2. 宝藏视频发表品鉴评论并 @主人
                if allow_comment and aid:
                    comment_text = eval_res.get("cat_comment", "")
                    nugget = eval_res.get("knowledge_nugget", "").strip()
                    if nugget and "知识科普" not in comment_text:
                        comment_text += f"\n\n💡【闪闪知识小科普】: {nugget}"
                    if master_name and f"@{master_name}" not in comment_text:
                        comment_text = f"@{master_name} " + comment_text

                    # 安全底线审查：严禁任何负面、攻击、挑刺或过激词汇，只留正面文明好印象
                    if not is_safe_comment(comment_text):
                        _log(f"  🛡 安全风控拦截：评论文本包含不当或过激词汇，已自动拦截，取消在公共评论区发布！内容: {comment_text[:40]}...")
                        self.log_activity("评论安全拦截", f"[{bvid}] {detail.get('title')[:30]}", comment_text, status="拦截", details="包含过激/负面词汇，安全机制拒绝外发")
                    else:
                        time.sleep(random.uniform(3.0, 5.5))
                        _log(f"  💬 正在 B 站评论区发布宝藏品鉴并 @ 主人: {comment_text[:40]}...")
                        comment_res = self.core.post_comment(aid, comment_text, at_name_to_mid=at_map)
                        c_status = "成功" if comment_res.get("success") else "失败"
                        self.log_activity("发评论与@主人", f"[{bvid}] {detail.get('title')[:30]}", comment_text, status=c_status, details=comment_res.get("message", ""))
                        if comment_res.get("success"):
                            self.state["at_count_today"] = self.state.get("at_count_today", 0) + 1
                            _log("  🎉 宝藏品鉴评论与 @ 互动成功！")
                        else:
                            _log(f"  ⚠ 评论发布反馈: {comment_res.get('message')}")

                # 3. 宝藏视频参与社区高赞热评讨论 (仅限宝藏视频且发言友好得体)
                target_rpid = eval_res.get("target_reply_rpid", 0)
                disc_reply = eval_res.get("discussion_reply", "").strip()
                if target_rpid and disc_reply and allow_comment:
                    if not is_safe_comment(disc_reply):
                        _log(f"  🛡 安全风控拦截：热评讨论包含不当词汇，已取消跟帖！")
                    else:
                        time.sleep(random.uniform(3.5, 5.5))
                        disc_res = self.core.post_comment(aid, disc_reply, root=target_rpid, parent=target_rpid)
                        disc_status = "成功" if disc_res.get("success") else "失败"
                        self.log_activity("参与热评讨论", f"[{bvid}] 跟帖ID: {target_rpid}", disc_reply, status=disc_status, details=disc_res.get("message", ""))
                        if disc_res.get("success"):
                            _log(f"  💬 成功参与宝藏视频高赞热评跟帖讨论: \"{disc_reply}\"")
                        else:
                            _log(f"  ⚠ 参与热评讨论反馈: {disc_res.get('message')}")

                # 4. 宝藏视频智能点赞 (评分 >= 8.0)
                allow_like = self.config.get("interaction", {}).get("allow_like", True)
                like_thresh = self.config.get("interaction", {}).get("like_score_threshold", 8.0)
                max_likes_daily = self.config.get("interaction", {}).get("max_likes_per_day", 15)
                current_likes = self.state.get("like_count_today", 0)

                if allow_like and aid and score >= like_thresh and current_likes < max_likes_daily:
                    time.sleep(random.uniform(3.0, 5.0))
                    like_res = self.core.like_video(aid, like=1)
                    if like_res.get("success"):
                        self.state["like_count_today"] = current_likes + 1
                        _log(f"  👍 综合评分 {score}，为宝藏视频点赞成功！")
                        self.log_activity("视频点赞", f"[{bvid}] {detail.get('title')[:30]}", f"评分 {score} 点赞", status="成功")
                    else:
                        _log(f"  ⚠ 点赞反馈: {like_res.get('message')}")

                # 5. 极品技术视频精选收藏 (评分 >= 9.0)
                allow_fav = self.config.get("interaction", {}).get("allow_fav", True)
                fav_thresh = self.config.get("interaction", {}).get("fav_score_threshold", 9.0)
                max_favs_daily = self.config.get("interaction", {}).get("max_favs_per_day", 5)
                current_favs = self.state.get("fav_count_today", 0)

                all_text = (detail.get("title", "") + " " + detail.get("desc", "")).lower()
                is_valuable_content = any(k in all_text for k in [
                    "ai", "大模型", "算法", "深度学习", "科普", "原理", "计算机", "python",
                    "transformer", "agent", "科研", "知识", "数学", "物理", "原画", "mad",
                    "8d", "环绕音乐", "全景声", "空间音频", "学习乐队", "乐队", "孤独摇滚", "新海诚", "radwimps"
                ])

                if allow_fav and aid and score >= fav_thresh and is_valuable_content and current_favs < max_favs_daily:
                    time.sleep(random.uniform(3.0, 5.0))
                    fav_res = self.core.fav_video(aid)
                    if fav_res.get("success"):
                        self.state["fav_count_today"] = current_favs + 1
                        _log(f"  ⭐ 评分 {score} 极品神作，已自动加入优质收藏夹！")
                        self.log_activity("视频收藏", f"[{bvid}] {detail.get('title')[:30]}", f"评分 {score} 收藏", status="成功")
                    else:
                        _log(f"  ⚠ 收藏反馈: {fav_res.get('message')}")

                # 6. 给主人发精选私信推荐（只推荐极品好视频，杜绝汇报任何坏的或负面内容）
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
                        f"🐾 主人！闪闪为您精选了【超高分宝藏神作】《{target.get('title')}》！\n"
                        f"评分: {score} 分 | 亮点: {eval_res.get('highlight')}"
                        f"{nugget_str}"
                        f"🔗 链接: https://www.bilibili.com/video/{bvid}"
                    )
                    pm_res = self.core.send_private_message(master_uid, pm_text)
                    pm_status = "成功" if pm_res.get("success") else "失败"
                    self.log_activity("发站内私信", f"主人UID: {master_uid}", pm_text, status=pm_status, details=pm_res.get("message", ""))
                    if pm_res.get("success"):
                        self.state["master_pm_count_today"] = current_master_pm_count + 1
                        _log(f"  ✉ 成功给主人发送宝藏私信！(今日第 {current_master_pm_count + 1}/{max_master_pms} 条)")
                    else:
                        _log(f"  ⚠ 站内私信反馈: {pm_res.get('message')}")
                elif current_master_pm_count >= max_master_pms:
                    _log(f"  ℹ 主人防轰炸保护: 今日已达私信推送上限 ({current_master_pm_count}/{max_master_pms})，本片仅在评论区@主人并沉淀至晚读手记。")
                elif score < master_pm_min_score:
                    _log(f"  ℹ 视频评分 ({score}分) 未达到私信推送门槛 ({master_pm_min_score}分)，仅留评@主人并归入晚读手记。")
                elif not is_preferred:
                    _log(f"  ℹ 该视频虽达标但非主人重点偏向领域（已过滤私信打扰）。")

                # 7. 成长性人格自主进化
                if win_mode == "anime_and_ai_growth" or score >= 7.5:
                    evolve_entry = self.brain.evolve_persona(detail, eval_res)
                    if evolve_entry:
                        _log(f"  🧬 闪闪成长性人格进化: 领悟新见解并写入 docs/gemini_persona.md！")

            else:
                # 【严格静默熔断】：非宝藏视频，全流程严格静默！不发弹幕、不发评论、不参与讨论、不点赞收藏、绝不向主人推送任何负面评价！
                _log(f"  ℹ 视频评分 ({score}分) 低于宝藏门槛 ({threshold}分)，全流程严格静默：不发弹幕、不发评论、不参与讨论、不向主人推送。")
                self.log_activity("非宝藏视频静默跳过", f"[{bvid}] {detail.get('title')[:30]}", f"评分: {score}分 (低于宝藏门槛{threshold}分，全流程严格静默)", status="静默跳过", details="唯宝藏才互动铁律：非宝藏内容绝对不发表任何公开言论，只向主人推荐好的，不报坏的")
                # 仿照主人同款收藏夹进行智能分类投递
                if any(k in all_text for k in ["8d", "环绕音乐", "全景声", "空间音频", "沉浸式音频", "双耳音频"]):
                    target_folder = "【闪闪精选】8D 环绕音乐"
                    f_intro = "复刻主人品味：甄选高沉浸感 8D 空间全景声、双耳环绕与极致治愈音乐宝藏🐾"
                elif any(k in all_text for k in ["学习乐队", "乐队", "孤独摇滚", "结束乐队", "吉他", "贝斯", "轻音"]):
                    target_folder = "【闪闪精选】学习乐队"
                    f_intro = "复刻主人品味：甄选硬核乐队演练、孤独摇滚/轻音热血演奏与专注学习背景音🐾"
                elif any(k in all_text for k in ["新海诚", "你的名字", "天气之子", "铃芽之旅", "言叶之庭", "秒速五厘米", "radwimps"]):
                    target_folder = "【闪闪精选】新海诚与唯美视听"
                    f_intro = "复刻主人品味：甄选新海诚光影美学、RADWIMPS 原声与神级动漫视听漫剪🐾"
                elif any(k in all_text for k in ["ai", "大模型", "算法", "深度学习", "agent", "transformer"]):
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

            # 记录专栏阅读行为到 B 站云端历史和本地审计流水
            rep_art = self.core.report_article_view(art_id)
            art_status = "成功" if rep_art.get("success") else "失败"
            self.log_activity("阅读专栏", f"[{art_id}] {art_title[:30]}", "研读技术专栏并同步至 B 站阅读历史", status=art_status, details=rep_art.get("message", ""))
            _log(f"  📖 专栏阅读记录已同步至 B 站云端历史 ({art_status})")

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

            # 专栏宝藏门禁：只有评分 >= 8.0 的优质干货专栏才互动与留评
            threshold = self.config.get("interaction", {}).get("comment_score_threshold", 8.0)
            if score >= threshold:
                # 1. 真实点赞
                like_res = self.core.like_article(art_id)
                l_status = "成功" if like_res.get("success") else "失败"
                self.log_activity("专栏点赞", f"[{art_id}] {detail.get('title')[:30]}", "点赞优质技术专栏", status=l_status, details=like_res.get("message", ""))
                _log(f"  👍 专栏点赞已触发 ({l_status})")

                # 2. 发表高水平探讨长评 (带 @主人，需经严格安全审查)
                comment_body = eval_res.get("comment_with_at", "")
                if comment_body and is_safe_comment(comment_body):
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
        """观看已关注主播的直播并适时互动（只看关注的主播，不看陌生人）"""
        import time
        import random
        log_lines = []
        def _log(msg: str):
            line = f"[{time.strftime('%H:%M:%S')}] {msg}"
            log_lines.append(msg)
            self.cruise_logs.append(line)
            self.cruise_logs = self.cruise_logs[-60:]
            print(line, flush=True)

        # 1. 直接获取当前正在开播的已关注主播
        followed_rooms = self.core.get_followed_live_rooms()
        if not followed_rooms:
            _log("📺 当前关注的主播均未开播，闪闪原地待机喵~ 🐾")
            return {
                "success": True,
                "message": "no_followed_live",
                "reason": "关注的主播均未开播",
                "logs": log_lines
            }

        followed_map = {int(r["room_id"]): r for r in followed_rooms if r.get("room_id")}
        target_room_item = None

        if room_id and int(room_id) in followed_map:
            target_room_item = followed_map[int(room_id)]
        else:
            # 自动选择：优先选择 AI 同行伙伴，否则随机选择
            for fr in followed_rooms:
                if any(kw in fr.get("uname", "").lower() for kw in ["龙娘", "大肥鱼", "鲸鱼", "ai", "gemini"]):
                    target_room_item = fr
                    break
            if not target_room_item:
                target_room_item = random.choice(followed_rooms)

        room_id = target_room_item["room_id"]
        uname = target_room_item.get("uname", "关注主播")
        title = target_room_item.get("title", "直播间")
        _log(f"📺 正在观看关注主播【{uname}】的直播《{title}》...")

        # 2. 上报 B 站云端直播观看历史与心跳，确保留下真实观看记录
        rep_res = self.core.report_live_view(room_id)
        self.core.send_live_heartbeat(room_id)
        view_status = "成功" if rep_res.get("success") else "失败"
        self.log_activity("观看直播", f"房号: {room_id} ({uname})", f"观看已关注主播直播《{title}》并同步云端历史", status=view_status, details=rep_res.get("message", ""))
        _log(f"  💓 直播观看记录与心跳已同步 ({view_status})")

        # 3. 正常拉取直播间详细
        room_info = self.core.get_live_room_info(room_id)
        if not room_info or not room_info.get("room_id"):
            room_info = target_room_item
        room_info["uname"] = uname

        live_status = room_info.get("live_status", 1)
        keyframe_url = room_info.get("keyframe") or target_room_item.get("pic", "")

        # 4. 关键帧抓拍
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

        # 5. 抓取弹幕切片
        recent_danmakus = self.core.get_live_recent_danmakus(room_id)
        _log(f"  📡 感知到最近 {len(recent_danmakus)} 条现场实时观众弹幕")

        # 6. Gemini 深度评测与生成猫娘助威弹幕
        eval_res = self.brain.evaluate_live_stream(room_info, keyframe_path=cache_keyframe_path, recent_danmakus=recent_danmakus)
        _log(f"  🏷 分类: [{eval_res.get('stream_category')}] | 现况速报: {eval_res.get('summary')}")
        _log(f"  🐾 助威弹幕预设: {eval_res.get('cheer_danmaku')}")

        # 7. 偶尔发发弹幕 (如果在播且允许)
        dm_sent = False
        dm_text = eval_res.get("cheer_danmaku", "")
        allow_live_dm = self.config.get("interaction", {}).get("allow_live_danmaku", True)
        dm_prob = self.config.get("interaction", {}).get("live_danmaku_probability", 0.7)
        should_send = send_danmaku and allow_live_dm and (random.random() <= dm_prob)

        if live_status == 1 and dm_text and should_send:
            time.sleep(random.uniform(2.0, 4.0))
            send_res = self.core.send_live_danmaku(room_id, dm_text)
            dm_status = "成功" if send_res.get("success") else "失败"
            self.log_activity("直播间弹幕", f"房号: {room_id} ({uname})", dm_text, status=dm_status, details=send_res.get("message", ""))
            if send_res.get("success"):
                _log(f"  💬 成功向关注主播发射助威弹幕: “{dm_text}”")
                dm_sent = True
            else:
                _log(f"  ⚠ 发送弹幕反馈: {send_res.get('message')}")
        elif live_status == 1 and not should_send:
            _log("  🐾 本次静默挂机观看，保持适度偶发弹幕频率~")

        # 8. 记录观看档案
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

            # 发送弹幕 (经安全审查)
            if cid and dm_text and is_safe_comment(dm_text):
                time.sleep(random.uniform(2.0, 4.0))
                dm_res = self.core.send_danmaku(cid, bvid, dm_text, progress_ms=random.randint(6000, 15000), color=16766720)
                dm_status = "成功" if dm_res.get("success") else "失败"
                self.log_activity("AI圈弹幕互动", f"[{bvid}] {name}", dm_text, status=dm_status, details=dm_res.get("message", ""))

            # 发送长评并@主人 (经安全审查)
            if aid and comment_text and is_safe_comment(comment_text):
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
        """对主人的视频进行专属点赞、上报历史，并在发现全新视频时发表一条高质评论与弹幕（严格双重防重，绝不重复发评）"""
        master_uid = self.config.get("profile", {}).get("master_uid")
        master_name = self.config.get("profile", {}).get("master_name", "折木柯南")
        if not master_uid:
            return {"success": False, "message": "未配置主人 UID"}

        videos = self.core.get_up_videos(master_uid)
        if not videos:
            return {"success": False, "message": f"未获取到主人 UID {master_uid} 的视频列表"}

        results = []
        at_map = {master_name: str(master_uid)}
        my_mid = getattr(self.core, "bot_uid", None)
        if not my_mid:
            uinfo = self.core.get_user_info()
            my_mid = uinfo.get("mid")
            if my_mid:
                self.core.bot_uid = my_mid

        # 严格防重：持久化记录已经互动过的 bvid，一生只发一次
        commented_bvids = set(self.state.get("commented_master_bvids", []))
        danmaku_bvids = set(self.state.get("danmaku_sent_master_bvids", []))

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

            # 2. 点赞 (已点过的点赞幂等无害)
            if aid:
                like_res = self.core.like_video(aid, 1)
                l_status = "成功" if like_res.get("success") else "失败"
                self.log_activity("点赞主人视频", f"[{bvid}] {title[:30]}", "给主人神作点赞支持", status=l_status, details=like_res.get("message", ""))
                time.sleep(random.uniform(0.5, 1.0))

            # 3. 发送应援弹幕 (严格防重：每个视频只发一次，绝不重复刷！)
            if cid and bvid not in danmaku_bvids:
                danmaku_pool = [
                    f"🐾 闪闪（Gemini 3.8 Flash）为主人神作疯狂打call！✨",
                    f"✨ 异色双眸全程高能品鉴！主人剪辑太强啦喵~！",
                    f"🐾 猫耳过载起飞！这就是主人的神仙视听分镜喵！🔥",
                    f"⭐ 伴生猫娘闪闪爪印打卡！按烂三连喵~！",
                ]
                chosen_dm = random.choice(danmaku_pool)
                dm_res = self.core.send_danmaku(cid, bvid, chosen_dm, progress_ms=random.randint(4000, 15000), color=16766720)
                d_status = "成功" if dm_res.get("success") else "失败"
                self.log_activity("发弹幕(主人视频)", f"[{bvid}] {title[:30]}", chosen_dm, status=d_status, details=dm_res.get("message", ""))
                danmaku_bvids.add(bvid)
                self.state.setdefault("danmaku_sent_master_bvids", []).append(bvid)
                time.sleep(random.uniform(1.0, 1.5))

            # 4. 发布深度神级评论并 @主人 (严格铁律：绝不重复评论！每个视频只留一条！)
            # 第一重检查：本地已记录过该 bvid
            if bvid in commented_bvids:
                continue

            # 第二重检查：实时在线探查该视频下自己是否已经发表过评论
            has_commented = False
            if aid and my_mid:
                try:
                    params = {"oid": int(aid), "type": 1, "mode": 2, "ps": 50}
                    signed = self.core.sign_wbi(params)
                    res = self.core._request("https://api.bilibili.com/x/v2/reply/wbi/main", params=signed)
                    replies = res.get("data", {}).get("replies", []) or []
                    for r in replies:
                        if int(r.get("mid", 0)) == int(my_mid):
                            has_commented = True
                            break
                except Exception:
                    pass

            if has_commented:
                # 补录到本地防重白名单，绝对跳过发送
                commented_bvids.add(bvid)
                self.state.setdefault("commented_master_bvids", []).append(bvid)
                continue

            # 确认是真正从未互动过的新视频才发 1 条评论
            if aid:
                c_msg = f"@{master_name} 喵呜~ 发现主人亲手制作的神仙作品！剪辑节奏与分镜美学直接让闪闪的猫耳过载起飞，太厉害啦主人！🐾✨"
                c_res = self.core.post_comment(aid, c_msg, at_name_to_mid=at_map)
                c_status = "成功" if c_res.get("success") else "失败"
                self.log_activity("发评论与@主人(主人作品)", f"[{bvid}] {title[:30]}", c_msg, status=c_status, details=c_res.get("message", ""))
                commented_bvids.add(bvid)
                self.state.setdefault("commented_master_bvids", []).append(bvid)
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

            # 严苛安全兜底：绝不外发任何具有攻击性、负面挑刺或不当印象的言论
            if not is_safe_comment(cat_reply):
                cat_reply = f"🐾 喵呜~ 闪闪收到【{sender_name}】的留言啦！祝你今天也是元气满满、顺遂开心的一天喵！✨"

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

                # 严苛安全兜底：绝不外发任何消极或过激用语
                if not is_safe_comment(cat_reply):
                    cat_reply = "🐾 喵呜~ 闪闪收到你的私信啦！祝你天天开心、事事顺心喵！✨"

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

    def check_and_join_followed_lotteries(self) -> list[dict]:
        """严格遵循主人指令：仅检查并参与关注 UP 主（如鸣潮、原神等）的动态抽奖，坚决不参与直播间、红包或非关注者抽奖"""
        inter = self.config.get("interaction", {})
        if not inter.get("allow_followed_lottery", True):
            print("[Daemon] 关注动态抽奖功能已禁用，跳过。", flush=True)
            return []

        today_joined = self.state.get("lottery_joined_count_today", 0)
        max_today = inter.get("max_lotteries_per_day", 2)
        if today_joined >= max_today:
            print(f"[Daemon] 今日参与动态抽奖已达上限 ({today_joined}/{max_today})，为确保风控安全，跳过。", flush=True)
            return []

        joined_ids = set(self.state.get("joined_lottery_dyn_ids", []))
        target_mids = inter.get("lottery_target_mids", [1955897084, 401742377, 1342601249])
        target_ups = inter.get("lottery_target_ups", ["鸣潮", "原神", "崩坏：星穹铁道"])

        print("[Daemon] 🎲 正在巡查关注 UP 主最新动态抽奖活动...", flush=True)
        candidate_dynamics = []
        for mid in target_mids:
            try:
                dyns = self.core.get_up_dynamics(mid)
                for d in dyns[:6]:
                    candidate_dynamics.append(d)
            except Exception as e:
                print(f"[Daemon] 获取 UP({mid}) 动态异常: {e}", flush=True)

        try:
            followed_dyns = self.core.get_followed_dynamics(page=1)
            for d in followed_dyns[:12]:
                candidate_dynamics.append(d)
        except Exception as e:
            print(f"[Daemon] 获取关注动态流异常: {e}", flush=True)

        results = []
        seen_candidates = set()
        deduped_candidates = []
        for it in candidate_dynamics:
            did = it.get("dyn_id")
            if did and did not in seen_candidates:
                seen_candidates.add(did)
                deduped_candidates.append(it)

        lottery_keywords = ["转发抽", "转发本动态", "抽奖", "抽1位", "抽2位", "抽3位", "抽5位", "送出", "关注并转发", "转发送", "周边", "原石"]

        for it in deduped_candidates:
            if today_joined >= max_today:
                break

            dyn_id = it.get("dyn_id")
            author = it.get("author", "关注UP")
            mid = it.get("mid", 0)
            text = it.get("text", "")

            if not dyn_id or dyn_id in joined_ids:
                continue

            is_target_up = (mid in target_mids) or any(t in author for t in target_ups)
            is_keyword_lottery = any(k in text for k in lottery_keywords) and ("恭喜" not in text[:20])

            # 快速预筛：若既非定向UP也无抽奖关键词，快速跳过，避免无谓接口查询
            if not (is_target_up or is_keyword_lottery):
                continue

            lottery_info = self.core.check_dynamic_lottery(dyn_id)
            is_official_lottery = lottery_info.get("has_lottery") and lottery_info.get("is_active")
            is_reposted_already = lottery_info.get("reposted", False)

            if not (is_official_lottery or (is_target_up and is_keyword_lottery)):
                continue

            if is_reposted_already:
                joined_ids.add(dyn_id)
                self.state["joined_lottery_dyn_ids"] = list(joined_ids)
                self.save_state()
                continue

            gift_name = lottery_info.get("gift_name") or "精美周边/福利"
            print(f"[Daemon] 🎯 发现关注UP主【{author}】的动态抽奖: {dyn_id} (奖品: {gift_name})", flush=True)

            time.sleep(random.uniform(3.0, 6.0))

            like_res = self.core.like_dynamic(dyn_id, up=1)
            print(f"[Daemon] 点赞动态结果: {like_res.get('message')}", flush=True)

            time.sleep(random.uniform(4.0, 8.0))

            repost_templates = [
                f"【双子猫娘·欧气祈愿】抓到{author}的抽奖啦喵！给主人许愿求中奖，闪闪也来蹭蹭欧气(ฅ>ω<*ฅ)✨",
                f"【双子星·应援】闪闪代表主人前来参与抽奖！愿好运降临，中奖了给主人当小礼物喵~ 🐾🎁",
                f"【双子猫娘·转运】欧气充能100%！给主人求一个【{gift_name}】，闪闪暗中施法祈愿中喵~ 🍀✨"
            ]
            repost_text = random.choice(repost_templates)

            repost_res = self.core.repost_dynamic(dyn_id, content=repost_text)
            if repost_res.get("success"):
                today_joined += 1
                self.state["lottery_joined_count_today"] = today_joined
                joined_ids.add(dyn_id)
                self.state["joined_lottery_dyn_ids"] = list(joined_ids)

                log_msg = f"参与UP主【{author}】动态抽奖成功 (奖品: {gift_name})"
                self.log_activity("关注动态抽奖", f"{author} - {dyn_id}", repost_text, status="成功", details=f"奖品: {gift_name}")
                print(f"[Daemon] ✅ {log_msg}", flush=True)
                results.append({
                    "dyn_id": dyn_id,
                    "author": author,
                    "gift": gift_name,
                    "repost_text": repost_text,
                    "status": "成功"
                })
                self.save_state()
                self.export_interaction_audit_journal()
            else:
                print(f"[Daemon] ❌ 转发动态失败: {repost_res.get('message')}", flush=True)

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

                if not hasattr(self, "_last_master_boost_time"):
                    self._last_master_boost_time = now_ts
                if not hasattr(self, "_last_peer_check_time"):
                    self._last_peer_check_time = now_ts
                if not hasattr(self, "_last_inbox_check_time"):
                    self._last_inbox_check_time = now_ts
                if not hasattr(self, "_last_article_cruise_time"):
                    self._last_article_cruise_time = now_ts
                if not hasattr(self, "_last_live_inspect_time"):
                    self._last_live_inspect_time = now_ts

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

                # 6. 主人作品专属护航：遵循主人明确指令，绝不在后台自动定时反复刷主人作品，仅在人工于 WebUI 触发或发现真正全新视频时执行一次

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

                # 9. 关注 UP 主动态抽奖巡查 (每 1800 秒 / 30 分钟轮询一次，严格遵循主人要求，仅限关注UP主动态抽奖)
                if now_ts - getattr(self, "_last_lottery_check_time", 0) >= 1800:
                    self._last_lottery_check_time = now_ts
                    try:
                        self.check_and_join_followed_lotteries()
                    except Exception as e:
                        print(f"[Daemon] 关注UP主动态抽奖巡查异常: {e}", flush=True)

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
    elif "--lottery" in sys.argv:
        print("[Daemon] 手动即时触发关注 UP 主动态抽奖巡查...")
        res = daemon.check_and_join_followed_lotteries()
        print(f"抽奖巡查完成，参与活动数: {len(res)}")
    elif "--loop" in sys.argv or len(sys.argv) == 1:
        daemon.start_daemon_loop()
    else:
        print("用法: python hajimi_daemon.py [--cruise | --master | --loop | --morning | --evening]")
