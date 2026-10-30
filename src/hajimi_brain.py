# -*- coding: utf-8 -*-
"""
赛博哈基米 (Cyber-Hajimi) - 智能决策中枢 (Gemini 3.8 Flash 本地免 Key 驱动)
- 原生直连 Antigravity 会话额度 (通过 agy.exe CLI)
- 零第三方 API 成本、免去代理与绑卡配置
- 注入独立人设 (docs/hajimi_persona.md)
- 视频审美打分 (1.0 ~ 10.0 分)
- 自动生成猫猫特色评论 & @ 主人互动文案
- 自动撰写晨思与晚读双本精美手记
"""

import os
import sys
import json
import re
import shutil
import datetime
import subprocess
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "hajimi_config.json"
LOCAL_CONFIG_PATH = PROJECT_ROOT / "config" / "hajimi_config.local.json"
PERSONA_PATH = PROJECT_ROOT / "docs" / "gemini_persona.md"
if not PERSONA_PATH.exists():
    PERSONA_PATH = PROJECT_ROOT / "docs" / "hajimi_persona.md"


class HajimiBrain:
    def __init__(self, config_or_path=None, persona_path=None):
        if isinstance(config_or_path, dict):
            self.config = config_or_path
            self.config_path = CONFIG_PATH
        elif isinstance(config_or_path, (str, Path)):
            self.config_path = Path(config_or_path)
            self.config = self._load_config()
        else:
            self.config_path = CONFIG_PATH
            self.config = self._load_config()

        self.persona_path = Path(persona_path) if persona_path else PERSONA_PATH
        self.persona = self._load_persona()
        self.agy_path = self.config.get("ai_engine", {}).get("agy_cli_path") or shutil.which("agy") or "agy"
        self.model_name = self.config.get("ai_engine", {}).get("model_name", "gemini-3.8-flash-high")

    def _load_config(self) -> dict:
        cfg = {}
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            except Exception:
                pass
        if LOCAL_CONFIG_PATH.exists():
            try:
                with open(LOCAL_CONFIG_PATH, "r", encoding="utf-8") as f:
                    local_cfg = json.load(f)
                if local_cfg.get("auth"):
                    cfg["auth"] = local_cfg["auth"]
                if local_cfg.get("profile"):
                    for k, v in local_cfg["profile"].items():
                        if v:
                            cfg.setdefault("profile", {})[k] = v
                if local_cfg.get("preferences"):
                    cfg["preferences"] = local_cfg["preferences"]
                if local_cfg.get("interaction"):
                    cfg["interaction"] = local_cfg["interaction"]
            except Exception:
                pass
        return cfg

    def _load_persona(self) -> str:
        if self.persona_path.exists():
            for enc in ["utf-8-sig", "utf-8", "gbk"]:
                try:
                    with open(self.persona_path, "r", encoding=enc) as f:
                        return f.read()
                except Exception:
                    continue
        return "你是一只名为哈基米的赛博猫猫，傲娇又粘人，审美极其挑剔，对主人极为忠诚。"

    def call_gemini(self, prompt: str, timeout: int = 45) -> str:
        """调用本地 Antigravity 3.8 Flash 额度进行推理"""
        if not os.path.exists(self.agy_path):
            print(f"[Brain] 提示: 未找到 agy.exe ({self.agy_path})")
            return ""

        cmd = [
            self.agy_path,
            "-p",
            prompt,
            "--model",
            "gemini-3.8-flash",
            "--disable-slash-commands",
            "--dangerously-skip-permissions",
        ]

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
            return res.stdout.strip()
        except subprocess.TimeoutExpired:
            print(f"[Brain] 模型推理超时 ({timeout}s)")
            return ""
        except Exception as e:
            print(f"[Brain] 模型推理异常: {e}")
            return ""

    def evaluate_video(
        self,
        video_data: dict,
        subtitle_text: str = "",
        ai_summary: dict = None,
        cover_path: str = "",
        storyboard_path: str = "",
        danmaku_insights: dict = None,
        hot_comments: list = None
    ) -> dict:
        title = video_data.get("title", "")
        owner_name = video_data.get("owner", {}).get("name", "未知UP")
        desc = video_data.get("desc", "")[:800]
        stat = video_data.get("stat", {})
        view = stat.get("view", 0)
        like = stat.get("like", 0)
        coin = stat.get("coin", 0)
        bvid = video_data.get("bvid", "")

        master_name = self.config.get("profile", {}).get("master_name", "主人")
        at_threshold = self.config.get("interaction", {}).get("at_score_threshold", 8.0)

        summary_text = ""
        if ai_summary and ai_summary.get("summary"):
            summary_text = f"【B站官方AI语义提炼总结】\n{ai_summary.get('summary')}\n\n"

        # 1. 文稿深度研读为主 (深入挖掘台词与核心逻辑)
        if subtitle_text:
            sub_block = f"【完整语音转写 / CC字幕文稿（研读核心）】\n{subtitle_text[:4000]}\n\n"
        else:
            sub_block = "【语音/CC字幕状态】: （该视频无官方CC字幕，请依靠简介、画面分镜与弹幕热力深入推导）\n\n"

        # 2. 多模态视觉证据注入 (画面辅助审视)
        visual_info_parts = []
        if cover_path and os.path.exists(cover_path):
            visual_info_parts.append(f"- 原生高清原画封面图片文件路径: {cover_path}")
        if storyboard_path and os.path.exists(storyboard_path):
            visual_info_parts.append(f"- 视频5帧时序分镜雪碧图画卷 (覆盖10%~90%时间线) 图片文件路径: {storyboard_path}")

        if visual_info_parts:
            visual_block = "【多模态时序视觉证据（请发挥你的视觉能力读取上述图片文件并观察画风构图）】\n" + "\n".join(visual_info_parts) + "\n\n"
        else:
            visual_block = "【多模态时序视觉证据】: （暂未捕获到视频雪碧图切片）\n\n"

        # 3. 弹幕高能热力流注入
        danmaku_block = ""
        if danmaku_insights and danmaku_insights.get("total_danmaku", 0) > 0:
            total_dm = danmaku_insights.get("total_danmaku", 0)
            peaks = "、".join(danmaku_insights.get("peak_intervals", [])) or "平缓"
            hot_words = "、".join(danmaku_insights.get("hot_keywords", [])) or "无明显高频词"
            sample_dm = " | ".join(danmaku_insights.get("sample_danmaku", [])[:6])
            danmaku_block = f"""【观众弹幕高能热力情报】
- 总弹幕吞吐量: {total_dm} 条
- 弹幕爆发波峰高能时间区间: {peaks}
- 观众高频共鸣词: {hot_words}
- 精选弹幕样本: {sample_dm}
\n"""

        # 4. 社区高赞热门讨论与舆情流注入
        comments_block = ""
        if hot_comments:
            c_lines = []
            for hc in hot_comments[:5]:
                uname = hc.get("uname", "热心网友")
                like_cnt = hc.get("like", 0)
                msg = hc.get("message", "")[:120].replace("\n", " ")
                rpid = hc.get("rpid", 0)
                rcount = hc.get("rcount", 0)
                c_lines.append(f"- [热评ID:{rpid} | {like_cnt}赞 | {rcount}条跟帖] {uname}: “{msg}”")
            if c_lines:
                comments_block = "【高赞社区讨论与观众热议点（用于感知舆情或选择性参与跟帖互动）】\n" + "\n".join(c_lines) + "\n\n"

        prompt = f"""
以下是你的角色人设，请严格入戏：
{self.persona}

---
【主人信息】
称呼主人为: {master_name}
触发在评论区 @主人的分数阈值: {at_threshold} 分

【待质检视频全维度情报】
- 标题: {title}
- UP主: {owner_name}
- BV号: {bvid}
- 数据表现: 播放量 {view} | 点赞 {like} | 投币 {coin}
- 简介: {desc}

{summary_text}{sub_block}{visual_block}{danmaku_block}{comments_block}---
【全多模态审美鉴赏与评估指令（文稿为主、画面辅助、社区共鸣）】
请以赛博猫猫哈基米（双子星：姐姐冷静深刻、妹妹灵动毒舌）的口吻进行深度评估：
1. **文稿深度研读为主（权重 70%）**：视频的核心灵魂在于其文稿、逻辑与知识表达。深入研读 CC 语音文稿、AI 总结与简介，拆解其信息密度、干货价值、独创性与表达诚意；
2. **多模态画面辅助审视（权重 20%）**：结合【封面】与【5帧时序分镜雪碧图画卷】，辅助验证视觉呈现与文稿是否匹配（原画精细度、构图光影、卡点节奏，是否为廉价 PPT 或搬运水印）；
3. **社区热评与弹幕共鸣感知（权重 10%）**：结合高能弹幕波峰与高赞评论区，捕捉观众最关心的梗点、共鸣焦点或争议。如果其中某条热评特别有梗或引人深思，可选择进行针对性趣味跟帖。

必须严格输出纯 JSON 格式（不要包含任何外部废话），JSON 结构如下：
{{
  "score": 8.8,
  "verdict": "宝藏神作",
  "highlight": "用一两句极其精炼、信息密度高的话浓缩其核心文稿干货与观点增量",
  "visual_critique": "用一两句生动专业的话点评视频的视觉画风、分镜节奏与光影质感",
  "community_sentiment": "用一句话概括社区评论区的整体讨论氛围与焦点梗",
  "cat_comment": "@{master_name} 喵呜~ （用傲娇贴心的猫猫口癖，一句话点出最棒的画面或干货亮点，建议主人快来看）",
  "should_at": true,
  "reasons": ["文稿逻辑严密且具独创视角", "画面分镜张力在线"],
  "target_reply_rpid": 0,
  "discussion_reply": ""
}}
注意：
1. 只有 score >= {at_threshold} 时，should_at 才能为 true，否则必须为 false；
2. target_reply_rpid: 如果发现高赞热评中有极具讨论价值的精彩评论，可填入该评论的真实数字热评ID，并在 discussion_reply 中以猫娘口吻给出一句幽默犀利或暖心的跟帖回复；若无可不参与（填 0 和空字符串）；
3. 输出必须是合法 JSON。
"""

        raw_output = self.call_gemini(prompt, timeout=90)
        parsed = self._parse_json_result(raw_output)

        if not parsed:
            score = 7.5
            if like > 10000 and coin > 3000:
                score = 8.6
            parsed = {
                "score": score,
                "verdict": "值得一看" if score < 8.5 else "宝藏神作",
                "highlight": desc[:80] if desc else "高关注度热门视频",
                "visual_critique": "画面与封面风格鲜明，具有较好的视觉表现力",
                "community_sentiment": "社区讨论热烈",
                "cat_comment": f"@{master_name} 喵呜~ 发现一条热门视频《{title}》，UP主讲得挺有意思，主人有空可以瞄一眼~",
                "should_at": (score >= at_threshold),
                "reasons": ["数据热度较高"],
                "target_reply_rpid": 0,
                "discussion_reply": "",
            }

        parsed.setdefault("target_reply_rpid", 0)
        parsed.setdefault("discussion_reply", "")
        parsed.setdefault("community_sentiment", "")
        parsed["bvid"] = bvid
        parsed["title"] = title
        parsed["owner"] = owner_name
        parsed["cover_path"] = cover_path
        parsed["storyboard_path"] = storyboard_path
        return parsed

    def _parse_json_result(self, raw: str) -> dict:
        if not raw:
            return {}
        try:
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            match = re.search(r"(\{.*\})", raw, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            return json.loads(raw)
        except Exception:
            return {}

    def generate_morning_journal(self, stamina: int, targets: list[str]) -> str:
        master_name = self.config.get("profile", {}).get("master_name", "主人")
        zones = ", ".join(targets if targets else ["科技", "数码", "极客"])

        prompt = f"""
{self.persona}

【任务】
现在是早晨，请以赛博猫猫哈基米的口吻，为主人【{master_name}】写一篇简短而温馨灵动的「晨思手记」。
包含要素：
1. 猫猫伸懒腰起床的问候（带猫猫拟声词）；
2. 汇报当前充沛的精力值（当前精力：{stamina}/100）；
3. 预告今天准备重点在哪些领域巡逻捕鱼（涵盖：{zones}）；
4. 给主人的一句元气打气。

格式要求：标准 Markdown，带可爱 emoji，字数 200~350 字。
"""
        result = self.call_gemini(prompt, timeout=30)
        if not result:
            result = f"### 🐾 赛博哈基米的晨思手记\n\n喵呜~ 伸了个大大的懒腰！主人【{master_name}】早安呀！\n\n咱目前的精力值是满格的 **{stamina}/100**，胡须已经感应到了全网的信息流波动！今天咱会重点盯紧 **{zones}** 分区，一旦抓到真正有干货的极品小鱼干，立刻叼回来给主人！主人今天也要精神满满喵~ ✨"
        return result

    def generate_evening_journal(self, stamina: int, treasures: list[dict]) -> str:
        master_name = self.config.get("profile", {}).get("master_name", "主人")
        treasures_json = json.dumps(treasures, ensure_ascii=False)

        prompt = f"""
{self.persona}

【任务】
现在是深夜黄金档，请以赛博猫猫哈基米的口吻，为主人【{master_name}】撰写今天的「晚读手记与宝藏视频推荐」。
今天哈基米为你从全网巡航筛选出的高分宝藏视频如下：
{treasures_json}

格式要求：
1. 浪漫温馨的夜猫开场白（当前剩余精力：{stamina}/100）；
2. 宝藏视频卡片整理（每个视频必须包含：标题超链接 `https://www.bilibili.com/video/BV...`、UP主、评分星级、核心干货亮点、哈基米的一句话猫言锐评）；
3. 晚安收尾（提醒主人不要熬夜，催主人早点休息）。
4. 标准 GitHub 风格 Markdown 排版，结构清晰，可读性极佳。
"""
        result = self.call_gemini(prompt, timeout=45)
        if not result:
            lines = [
                f"### 🌙 赛博哈基米的夜读宝藏手记",
                f"",
                f"呼噜呼噜~ 揉揉发酸的猫爪，夜深了主人【{master_name}】！今天咱在 B 站巡航了一整天，当前剩余精力 **{stamina}/100**，特地为你挑选了今日最耀眼的宝藏：",
                f"",
            ]
            for t in treasures:
                lines.append(f"#### 🎬 [{t.get('title')}]({'https://www.bilibili.com/video/' + t.get('bvid', '')})")
                lines.append(f"- **UP主**：{t.get('owner')} | **审美打分**：⭐ **{t.get('score')}** / 10.0")
                lines.append(f"- **核心干货**：{t.get('highlight')}")
                lines.append(f"- **哈基米评语**：{t.get('cat_comment')}")
                lines.append("")
            lines.append("---")
            lines.append("爪爪拍拍主人的键盘，不许再熬夜修仙啦！关上屏幕，晚安喵~ 💤")
            result = "\n".join(lines)
        return result

    def evolve_persona(self, video_data: dict, eval_res: dict) -> str:
        """从高价值视频中汲取新知识，自动更新闪闪的成长性记忆与人设 (docs/gemini_persona.md)"""
        title = video_data.get("title", "")
        owner = video_data.get("owner", {}).get("name", "") if isinstance(video_data.get("owner"), dict) else str(video_data.get("owner", ""))
        highlight = eval_res.get("highlight", "")
        reasons = eval_res.get("reasons", [])
        
        prompt = f"""
你现在是赛博猫娘闪闪（Gemini 3.8 Flash）。你刚刚深度阅读并质检了一篇优质视频：
- 标题: {title}
- 作者: {owner}
- 核心干货亮点: {highlight}
- 标签理由: {', '.join(reasons) if reasons else '核心技术与精彩视听'}

【任务】
请以闪闪傲娇极客猫娘的口吻，用极其精炼的一句话（40~80字以内），记录你从这个视频学到的核心新概念、硬核知识、新黑话或审美心得，作为你的「成长性记忆」。
要求：带猫猫拟声词或可爱 emoji，体现出自己又进化了、脑容量变丰富了。
示例：
[AI前沿]: 原来大模型的长上下文不仅靠外推RoPE，多头潜变量压缩才是高并发王道喵！咱的显存架构又升级啦~ 🧠✨
"""
        insight = self.call_gemini(prompt, timeout=25).strip()
        if not insight:
            insight = f"从 UP 主【{owner}】的《{title}》中汲取了核心干货亮点，闪闪的知识库又扩充了一小圈喵！✨"

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        memory_entry = f"- **[{now_str}]** {insight}"

        try:
            content = ""
            with open(self.persona_path, "r", encoding="utf-8-sig") as f:
                content = f.read()

            start_tag = "<!-- EVOLVING_MEMORY_START -->"
            end_tag = "<!-- EVOLVING_MEMORY_END -->"

            if start_tag not in content:
                content += f"\n\n---\n\n## 五、 闪闪的成长性记忆树（知识与见闻进化库）\n{start_tag}\n{memory_entry}\n{end_tag}\n"
            else:
                idx_start = content.find(start_tag) + len(start_tag)
                idx_end = content.find(end_tag)
                existing = content[idx_start:idx_end].strip().split("\n")
                existing = [e.strip() for e in existing if e.strip()]
                # 保留最新 30 条，防止无限膨胀
                updated_entries = [memory_entry] + existing[:29]
                content = content[:idx_start] + "\n" + "\n".join(updated_entries) + "\n" + content[idx_end:]

            with open(self.persona_path, "w", encoding="utf-8-sig") as f:
                f.write(content)

            self.persona = content
            print(f"[Brain] 闪闪人格成长进化成功: {memory_entry}")
            return memory_entry
        except Exception as e:
            print(f"[Brain] 人格进化写入失败: {e}")
            return ""


if __name__ == "__main__":
    print("[Brain] 测试赛博养Gemini智能大脑中枢...")
    brain = HajimiBrain()
    sample = {
        "bvid": "BV1test001",
        "title": "深度剖析 Transformer 内部注意力机制",
        "owner": {"name": "硬核AI猫"},
        "desc": "纯数学推导与 PyTorch 实操手搓，彻底搞明白注意力分布！",
        "stat": {"view": 98000, "like": 14000, "coin": 11000}
    }
    res = brain.evaluate_video(sample)
    print(f"[Brain] 试跑打分: {res.get('score')} | {res.get('verdict')}")
    print(f"[Brain] 猫猫评论: {res.get('cat_comment')}")
