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
        self.update_stamina()
        stamina = self.state.get("stamina", 100)
        cost_per_video = self.config.get("schedule", {}).get("stamina_cost_per_video", 2)

        log_lines = []
        in_window, win_info = self.is_in_active_window()
        win_mode = win_info.get("mode", "all")
        win_name = win_info.get("name", "日常巡航")

        if not force:
            if not in_window:
                msg = f"当前处于休眠时段 [{win_name}]，闪闪正在窝里呼噜呼噜大睡恢复精力喵~"
                log_lines.append(msg)
                return {"success": False, "reason": "out_of_window", "logs": log_lines}

            if stamina < cost_per_video:
                msg = f"当前精力不足 ({stamina}/{cost_per_video})，闪闪打了个哈欠，等待精力恢复中喵..."
                log_lines.append(msg)
                return {"success": False, "reason": "low_stamina", "logs": log_lines}

            mood_skip = self.config.get("schedule", {}).get("mood_skip_chance", 0.05)
            if random.random() < mood_skip:
                msg = "🐾 闪闪正在追逐激光笔光斑玩耍，尾巴甩甩，本次巡航摸鱼打盹一次喵~"
                log_lines.append(msg)
                return {"success": False, "reason": "mood_skip", "logs": log_lines}

        blacklist_up = self.config.get("preferences", {}).get("blacklist_up", [])
        blacklist_kw = self.config.get("preferences", {}).get("blacklist_keywords", [])

        candidates = []
        if win_mode == "home_feed":
            log_lines.append(f"🌅 上午时段【{win_name}】：全速抓取 B 站首页推荐流海量新鲜视频...")
            raw_list = self.core.get_home_recommendations(ps=20)
            if not raw_list:
                raw_list = self.core.get_popular_videos(pn=1, ps=15)
            for item in raw_list:
                candidates.append(item)

        elif win_mode == "followed_and_popular":
            log_lines.append(f"☕ 下午时段【{win_name}】：精细扫描关注 UP 主动态更新与 B 站深度热门...")
            dyn_list = self.core.get_followed_dynamic_videos(ps=20)
            pop_list = self.core.get_popular_videos(pn=1, ps=10)
            candidates = dyn_list + pop_list

        elif win_mode == "anime_and_ai_growth":
            chosen_kw = random.choice(["AI", "大模型", "动漫", "MAD", "春物", "名侦探柯南", "文豪野犬", "AIGC"])
            log_lines.append(f"🌙 晚上时段【{win_name}】：自由漫游探索 [{chosen_kw}] 分区并进行成长性人格自主进化...")
            raw_kw = self.core.search_keyword_videos(chosen_kw, page=1, order="pubdate")
            pop_list = self.core.get_popular_videos(pn=1, ps=5)
            for item in raw_kw:
                bvid = item.get("bvid", "")
                title = item.get("title", "").replace('<em class="keyword">', "").replace("</em>", "")
                author = item.get("author", "")
                desc = item.get("description", "")
                if bvid:
                    candidates.append({"bvid": bvid, "title": title, "owner": {"name": author}, "desc": desc, "source": f"搜索[{chosen_kw}]"})
            candidates.extend(pop_list)
        else:
            log_lines.append(f"🔍 综合巡航雷达出击...")
            candidates = self.core.get_home_recommendations(ps=15) + self.core.get_popular_videos(pn=1, ps=10)

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
            filtered.append(c)

        max_cycle = win_info.get("target_per_hour", 8) if not force else self.config.get("schedule", {}).get("max_videos_per_cycle", 8)
        # 单批次最多 10 条，避免一次巡航卡太久
        max_cycle = min(max(max_cycle, 4), 10)
        targets = filtered[:max_cycle]

        if not targets:
            log_lines.append("未发现符合要求的新鲜视频，本次巡航结束。")
            return {"success": True, "evaluated_count": 0, "logs": log_lines}

        log_lines.append(f"🎯 选定 {len(targets)} 条新鲜视频，开始深入研读、互动与审美质检...")

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
            log_lines.append(f"\n▶ 正在质检视频 [{src_tag}]: [{bvid}] 《{target.get('title')}》")

            self.state["stamina"] = max(0, round(self.state.get("stamina", 100) - cost_per_video, 1))

            detail = self.core.get_video_detail(bvid)
            if not detail:
                detail = target

            cid = detail.get("cid", 0)
            aid = detail.get("aid", 0)
            pic = detail.get("pic", "")

            # 0. 真实向 B 站官方上报播放历史 (写入 B 站账号云端观看历史记录)
            if aid and cid:
                rep_res = self.core.report_video_view(aid, cid, progress=random.randint(35, 95))
                c_status = "成功" if rep_res.get("success") else "失败"
                self.log_activity("上报观看历史", f"[{bvid}] {detail.get('title')[:30]}", f"同步播放进度至 B 站云端历史", status=c_status, details=rep_res.get("message", ""))
                if rep_res.get("success"):
                    log_lines.append(f"  📺 播放心跳与历史已上报 (已真实同步至 B 站官方观看历史记录)")
                else:
                    log_lines.append(f"  ⚠ 历史记录上报反馈: {rep_res.get('message')}")

            # 1. 抓取与下载原生高清原画封面 (多模态视觉通道 1)
            cover_path = ""
            if pic:
                cover_path = self.core.download_video_cover(bvid, pic)
                if cover_path:
                    log_lines.append(f"  👁️ 原生高清封面已捕获 (多模态画风视觉通道就绪)")

            # 2. 抓取与抽取 5 帧时序分镜雪碧图画卷 (多模态视觉通道 2: 10%~90%全片画面)
            sb_path = ""
            if cid:
                sb_path = self.core.get_video_storyboard_strip(bvid, cid, target_frames=5)
                if sb_path:
                    log_lines.append(f"  🎬 成功抽取 5 帧时序分镜画卷 (已覆盖全片节奏与转场)")

            # 3. 弹幕热力流与高能时间点分析
            dm_insights = {}
            if cid:
                dm_insights = self.core.get_video_danmaku_insights(cid)
                if dm_insights.get("total_danmaku"):
                    peaks = ", ".join(dm_insights.get("peak_intervals", [])[:2])
                    log_lines.append(f"  🔥 弹幕热力情报: 吞吐 {dm_insights['total_danmaku']} 条弹幕，高能爆发点: {peaks}")

            # 4. CC 双语字幕文本
            subtitles = ""
            if cid:
                subtitles = self.core.get_video_subtitles(bvid, cid)
                if subtitles:
                    log_lines.append(f"  ✓ 成功抓取 CC 字幕 (长度 {len(subtitles)} 字)")
                else:
                    log_lines.append(f"  ℹ 该视频无 CC 字幕 (由多模态视觉画卷与弹幕热力深度鉴赏)")

            # 5. B站官方 AI 总结
            ai_summary = None
            if cid and detail.get("owner", {}).get("mid"):
                ai_summary = self.core.get_ai_conclusion(bvid, cid, detail["owner"]["mid"])

            # 6. 全多模态联合评估打分
            eval_res = self.brain.evaluate_video(
                detail,
                subtitle_text=subtitles,
                ai_summary=ai_summary,
                cover_path=cover_path,
                storyboard_path=sb_path,
                danmaku_insights=dm_insights
            )
            score = eval_res.get("score", 0)
            log_lines.append(f"  ★ Gemini 3.8 Flash 评分: {score} / 10.0 [{eval_res.get('verdict')}]")
            if eval_res.get("visual_critique"):
                log_lines.append(f"  🎨 视觉画风点评: {eval_res.get('visual_critique')}")
            log_lines.append(f"  💡 核心干货亮点: {eval_res.get('highlight')}")

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
                    log_lines.append(f"  💬 投喂弹幕成功: \"{dm_txt}\"")
                else:
                    log_lines.append(f"  ⚠ 投喂弹幕反馈: {dm_res.get('message')}")
                time.sleep(random.uniform(1.2, 2.0))

            # 2. 评论与 @ 主人互动
            if score >= threshold:
                log_lines.append(f"  ✨ 发现极品宝藏视频！收入今日手记备选池！")
                self.state.setdefault("treasures_today", []).append({
                    "bvid": bvid,
                    "title": eval_res.get("title", ""),
                    "owner": eval_res.get("owner", ""),
                    "score": score,
                    "highlight": eval_res.get("highlight", ""),
                    "cat_comment": eval_res.get("cat_comment", ""),
                })

                max_at = self.config.get("schedule", {}).get("max_at_per_day", 15)
                curr_at = self.state.get("at_count_today", 0)

                if allow_comment and curr_at < max_at and eval_res.get("should_at") and aid:
                    comment_text = eval_res.get("cat_comment", "")
                    at_map = {master_name: str(master_uid)} if master_uid and master_name else {}
                    log_lines.append(f"  💬 正在 B 站评论区发布猫猫脚印并 @ 主人: {comment_text}")
                    comment_res = self.core.post_comment(aid, comment_text, at_name_to_mid=at_map)
                    c_status = "成功" if comment_res.get("success") else "失败"
                    self.log_activity("发评论与@主人", f"[{bvid}] {detail.get('title')[:30]}", comment_text, status=c_status, details=comment_res.get("message", ""))
                    if comment_res.get("success"):
                        self.state["at_count_today"] = curr_at + 1
                        log_lines.append("  🎉 评论与 @ 互动成功！")
                    else:
                        log_lines.append(f"  ⚠ 评论发布反馈: {comment_res.get('message')}")

                # 给主人发私信
                if allow_pm and master_uid:
                    pm_text = f"🐾 主人！闪闪巡航发现了超棒的宝藏视频《{target.get('title')}》！评分 {score} 分，亮点：{eval_res.get('highlight')}，快去看看喵~ 🔗 https://www.bilibili.com/video/{bvid}"
                    pm_res = self.core.send_private_message(master_uid, pm_text)
                    pm_status = "成功" if pm_res.get("success") else "失败"
                    self.log_activity("发站内私信", f"主人UID: {master_uid}", pm_text, status=pm_status, details=pm_res.get("message", ""))
                    if pm_res.get("success"):
                        log_lines.append("  ✉ 成功给主人发送推荐私信！")
                    else:
                        log_lines.append(f"  ⚠ 站内私信反馈: {pm_res.get('message')}")
            else:
                # 普通/常规视频：遵从主人“每次看视频尽量都发评论”要求（发表猫猫真实审美点评，且不打扰主人）
                if allow_comment and aid:
                    cat_note = eval_res.get("cat_comment", "")
                    # 清理掉 @主人 前缀避免在普通视频误召唤主人
                    if "@" in cat_note:
                        cat_note = re.sub(r"@\S+\s*", "", cat_note).strip()
                    if not cat_note:
                        cat_note = f"🐾 闪闪（Gemini 3.8 Flash）路过打卡喵~ 核心亮点：{eval_res.get('highlight', '已留爪印')[:50]}"
                    c_res = self.core.post_comment(aid, cat_note)
                    c_status = "成功" if c_res.get("success") else "失败"
                    self.log_activity("发品鉴评论", f"[{bvid}] {detail.get('title')[:30]}", cat_note, status=c_status, details=c_res.get("message", ""))
                    if c_res.get("success"):
                        log_lines.append(f"  🐾 留下猫猫品鉴短评: \"{cat_note[:35]}...\"")
                    else:
                        log_lines.append(f"  ⚠ 评论发布反馈: {c_res.get('message')}")

            # 3. 晚上时段或高质量视频：成长性人格自主进化
            if win_mode == "anime_and_ai_growth" or score >= 7.5:
                evolve_entry = self.brain.evolve_persona(detail, eval_res)
                if evolve_entry:
                    log_lines.append(f"  🧬 闪闪成长性人格进化: 领悟新见解并写入 docs/gemini_persona.md！")

            results.append(eval_res)
            time.sleep(random.uniform(2.0, 3.5))

        self.save_state()
        self.export_interaction_audit_journal()
        return {"success": True, "evaluated_count": len(results), "results": results, "logs": log_lines}

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


    def start_daemon_loop(self, check_interval_sec: int = 180):
        """自动化常驻巡航守护主循环：按作息表定时巡航、自动出早晚手记"""
        print("============================================================")
        print("🐾 赛博养Gemini · 自动化常驻守护循环已上线！")
        print("⏰ 作息监控表: 上午海量初筛(09:30-11:30) | 下午精细品鉴(13:30-17:30) | 晚上人格进化(19:00-22:00)")
        print("============================================================")
        last_cruise_time = 0

        while True:
            try:
                now_dt = datetime.datetime.now()
                now_hm = now_dt.strftime("%H:%M")

                # 1. 晨思手记
                morning_time = self.config.get("schedule", {}).get("morning_journal_time", "09:30")
                if now_hm >= morning_time and not self.state.get("morning_journal_done"):
                    print(f"[{now_hm}] 🌅 触发早晨手记自动归档...")
                    self.generate_morning_journal_file()

                # 2. 晚读手记
                evening_time = self.config.get("schedule", {}).get("evening_journal_time", "22:00")
                if now_hm >= evening_time and not self.state.get("evening_journal_done"):
                    print(f"[{now_hm}] 🌙 触发晚间手记自动归档...")
                    self.generate_evening_journal_file()

                # 3. 作息窗口巡航 (上午20分钟一轮，其他时段30分钟一轮)
                in_win, win_info = self.is_in_active_window()
                win_mode = win_info.get("mode")
                cruise_gap = 1200 if win_mode == "home_feed" else 1800

                if in_win and (time.time() - last_cruise_time >= cruise_gap):
                    print(f"[{now_hm}] 🚀 自动化周期到达，唤醒闪闪出击巡航 ({win_info.get('name')})...")
                    res = self.run_cruise_cycle(force=False)
                    last_cruise_time = time.time()
                    for l in res.get("logs", []):
                        print(f"  {l}")

                time.sleep(check_interval_sec)
            except Exception as e:
                print(f"[Daemon] 守护循环心跳异常: {e}")
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
    elif "--loop" in sys.argv or len(sys.argv) == 1:
        daemon.start_daemon_loop()
    else:
        print("用法: python hajimi_daemon.py [--cruise | --loop | --morning | --evening]")
