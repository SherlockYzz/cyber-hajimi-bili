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
            "--effort",
            "low",
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

    def detect_category(self, video_data: dict) -> str:
        """根据分区、标题与简介智能识别视频类型：网课/二次元剪辑/纪录片/通用"""
        tname = str(video_data.get("tname") or "")
        title = str(video_data.get("title") or "")
        desc = str(video_data.get("desc") or "")
        text = f"{tname} {title} {desc}".lower()

        # 知识/网课/学术/编程/架构/科普
        knowledge_kw = [
            "教程", "课", "原理", "从入门到精通", "源码", "架构", "讲解", "速通", 
            "实战", "算法", "论文", "解析", "手把手", "科普", "大模型", "transformer", 
            "深度学习", "机器学习", "python", "agent", "rag", "面试", "计算机",
            "考研", "编程", "知识", "科技", "公开课", "讲座", "复习", "通俗", "剖析",
            "实操", "底层", "工程化", "框架", "部署", "全套", "自学", "开发", "设计模式",
            "代码", "项目实战", "进阶", "基础"
        ]
        # 动漫/MAD/影视剪辑/纯视听向
        anime_kw = [
            "mad", "amv", "漫剪", "原画", "作画", "卡点", "分镜", "手绘", "pv", 
            "mmd", "转场", "打戏", "高燃", "动漫", "番剧", "光影", "特效剪辑", "混剪"
        ]
        # 纪实/生活/Vlog
        vlog_kw = ["vlog", "纪录片", "探店", "旅行", "街头", "实纪", "纪实", "采访", "日常"]

        if any(k in text for k in knowledge_kw) or tname in ["知识", "科技", "计算机技术", "科学科普", "职业职场", "软件开发"]:
            return "knowledge_tutorial"
        elif any(k in text for k in anime_kw) or tname in ["动画", "MAD·AMV", "短片·手绘", "影视剪辑", "音乐"]:
            return "anime_mad_edit"
        elif any(k in text for k in vlog_kw) or tname in ["生活", "纪录片", "美食", "出行"]:
            return "vlog_documentary"
        return "general"

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

        # 智能分类判断
        category = self.detect_category(video_data)

        summary_text = ""
        if ai_summary and ai_summary.get("summary"):
            s_val = ai_summary.get("summary", "")
            summary_text = f"【B站官方AI语义提炼总结】\n{s_val}\n\n"

        # 1. 文稿深度研读为主 (根据分类提供自适应篇幅，网课放开至 12,000 字)
        if subtitle_text:
            if len(subtitle_text) <= 12000:
                sub_body = subtitle_text
            else:
                head = subtitle_text[:5000]
                mid_start = len(subtitle_text) // 2 - 1750
                mid = subtitle_text[mid_start:mid_start+3500]
                tail = subtitle_text[-3500:]
                sub_body = f"{head}\n\n...[中段核心推导与讲义内容]...\n\n{mid}\n\n...[末尾总结与实操收尾]...\n\n{tail}"
            sub_block = f"【完整语音转写 / CC字幕文稿（研读首要依据，全长 {len(subtitle_text)} 字符）】\n{sub_body}\n\n"
        else:
            sub_block = "【语音/CC字幕状态】: （该视频无官方CC字幕，请依靠简介、画面分镜与弹幕热力深入推导）\n\n"

        # 2. 多模态视觉证据注入 (画面辅助审视)
        visual_info_parts = []
        if cover_path and os.path.exists(cover_path):
            visual_info_parts.append(f"- 原生高清原画封面图片文件路径: {cover_path}")
        if storyboard_path and os.path.exists(storyboard_path):
            visual_info_parts.append(f"- 视频5帧时序分镜雪碧图画卷 (覆盖10%~90%时间线) 图片文件路径: {storyboard_path}")

        if visual_info_parts:
            v_joined = "\n".join(visual_info_parts)
            visual_block = f"【多模态时序视觉证据（请发挥视觉能力读取上述图片文件，网课仅看板书/代码清晰度，剪辑看画风分镜）】\n{v_joined}\n\n"
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
                c_joined = "\n".join(c_lines)
                comments_block = f"【高赞社区讨论与观众热议点（用于感知舆情或选择性参与跟帖互动）】\n{c_joined}\n\n"

        # 5. 分品类差异化评审指令与权重
        if category == "knowledge_tutorial":
            category_name_cn = "网课 / 编程技术 / 学术解析 / 硬核科普"
            eval_instructions = f"""【针对「{category_name_cn}」的专属品鉴铁律（核心：知识到底有没有深度、有没有作用）】
⚠️ 极度严正警告：
主人学习时间无比宝贵！你评估网课的核心灵魂在于【字幕与文稿讲解的知识到底有没有深度、有没有用、逻辑是否严密、能否对主人的技术开发与算法学习产生实质启发】！
❌ 严正禁止：绝对禁止把二次元剪辑的标准生搬硬套到网课上！绝对严禁挑剔网课“毫无视听张力”、“缺少动态动画设计”或“缺少炫酷转场”！优秀的讲座即使只用极简白板或PPT，只要底层逻辑深邃、推导严密就是顶级神作！
- 权重分配与审核维度：
  1. **知识与讲义内容深度（权重 85%）**：
     - 细致研读 CC 字幕：是否有底层架构、数学公式、源码剖析、边界异常与工程权衡？还是通篇只讲初级水果比喻、概念名词罗列？
     - 严打“卖课引流水课”：凡是挂着“3天速通”、“0基础爆款”等噱头，内容却极度浅显、拼凑套皮，或者字幕和评论区充斥“加群领资料/卖课”的，一律判定为低质水课并打低分（≤ 5.5分）！
     - 提炼干货：提炼出能真正帮主人解决技术难题的核心干货（knowledge_nugget）。
  2. **课件与板书直观性（权重 10%）**：
     - 时序分镜雪碧图仅看：PPT/代码编辑器/架构脑图是否排版工整清晰、易于理解知识脉络、有无大面积商业水印遮挡。绝不看动态特效！
  3. **社区技术氛围（权重 5%）**：
     - 评论区是真实探讨技术实现，还是全是卖资料或求资源的营销托。

字段要求：
- "visual_critique": 必须在此作为【讲义内容深度与知识架构点评】，一两句专业深邃地点评其课程内容深度、逻辑严密性与实操价值，严禁提任何“特效不足/缺少视听张力”！
- "knowledge_nugget": 【知识科普与干货小贴士】用3-4句话通俗硬核地向主人科普视频中提到的核心知识点/技术原理/底层逻辑/算法公式，确保对主人有扎实长进和启发。
"""
        elif category == "anime_mad_edit":
            category_name_cn = "二次元 / 动漫漫剪 / MAD·AMV / 视听美学"
            eval_instructions = f"""【针对「{category_name_cn}」的专属品鉴标准（视听美学与分镜节奏为核心）】
- 权重分配与审核维度：
  1. **视听美学与分镜运镜（权重 65%）**：画风作画精度、原画张力、抽帧卡点、转场流畅度、光影色彩与渲染质感；
  2. **剪辑叙事与音画同步（权重 25%）**：选曲契合度、情感递进与高潮爆发力；
  3. **社区与弹幕情绪共鸣（权重 10%）**。

字段要求：
- "visual_critique": 作为【视觉画风与分镜张力点评】，专业点评画风精度、卡点节奏与光影分镜。
"""
        elif category == "vlog_documentary":
            category_name_cn = "纪录片 / 生活纪实 / 人文探店"
            eval_instructions = f"""【针对「{category_name_cn}」的专属品鉴标准（信息增量与叙事真诚度为核心）】
- 权重分配与审核维度：
  1. **信息增量与叙事真诚度（权重 75%）**：真实生活观察、独特认知视角、信息密度、有无剧本摆拍痕迹；
  2. **镜头语言与氛围感（权重 20%）**：第一视角临场感与真实质感；
  3. **社区共鸣（权重 5%）**。

字段要求：
- "visual_critique": 作为【镜头语言与叙事真实度点评】，点评第一视角真实感与信息增量。
"""
        else:
            category_name_cn = "综合 / 泛娱乐解说"
            eval_instructions = f"""【针对「{category_name_cn}」的综合品鉴标准】
- 权重分配：文稿逻辑与观点增量（权重 70%），画面与制作质感（权重 20%），社区反响（权重 10%）。
字段要求：
- "visual_critique": 制作与视觉呈现点评。
"""

        prompt = f"""以下是你的角色人设，请严格入戏：
{self.persona}

---
【主人信息】
称呼主人为: {master_name}
触发在评论区 @主人的分数阈值: {at_threshold} 分

【待质检视频全维度情报】
- 标题: {title}
- 分类判断: 【{category_name_cn}】
- UP主: {owner_name}
- BV号: {bvid}
- 数据表现: 播放量 {view} | 点赞 {like} | 投币 {coin}
- 简介: {desc}

{summary_text}{sub_block}{visual_block}{danmaku_block}{comments_block}---
{eval_instructions}

必须严格输出纯 JSON 格式（不要包含任何外部废话），JSON 结构如下：
{{
  "video_category": "{category}",
  "score": 8.8,
  "verdict": "宝藏神作",
  "highlight": "用一两句极其精炼、信息密度高的话浓缩其核心文稿干货与观点增量",
  "knowledge_nugget": "【知识科普与干货小贴士】用3-4句话通俗硬核地向主人科普视频中提到的核心知识点/技术原理/底层逻辑/算法公式，确保对主人有扎实长进和启发",
  "visual_critique": "根据分类给出针对性点评（网课评内容深度与知识架构，剪辑评视听与分镜）",
  "community_sentiment": "用一句话概括社区评论区的整体讨论氛围与焦点梗",
  "cat_comment": "@{master_name} 喵呜~ （用傲娇贴心的猫猫口癖，一句话点出最棒的亮点，若是网课重点吐槽或夸奖其知识深度，并在后文自然融入知识科普）",
  "should_at": true,
  "reasons": ["文稿逻辑严密且具独创视角"],
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
                "video_category": category,
                "score": score,
                "verdict": "值得一看" if score < 8.5 else "宝藏神作",
                "highlight": desc[:80] if desc else "高关注度热门视频",
                "visual_critique": "讲义逻辑框架清晰" if category == "knowledge_tutorial" else "画面与封面风格鲜明",
                "community_sentiment": "社区讨论热烈",
                "cat_comment": f"@{master_name} 喵呜~ 发现一条热门视频《{title}》，UP主讲得挺有意思，主人有空可以瞄一眼~",
                "should_at": (score >= at_threshold),
                "reasons": ["数据热度较高"],
                "target_reply_rpid": 0,
                "discussion_reply": "",
            }

        parsed.setdefault("video_category", category)
        parsed.setdefault("category_name", category_name_cn)
        parsed.setdefault("target_reply_rpid", 0)
        parsed.setdefault("discussion_reply", "")
        parsed.setdefault("community_sentiment", "")
        parsed.setdefault("knowledge_nugget", "")
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

    def generate_comment_reply(self, sender_name: str, sender_content: str, video_title: str = "", my_parent_comment: str = "") -> str:
        """针对别人在评论区的回复，由 Gemini 结合猫娘人设生成俏皮、生动的互动回复"""
        master_name = self.config.get("profile", {}).get("master_name", "主人")
        is_master = (sender_name == master_name or "主人" in sender_name)

        if is_master:
            role_desc = f"特别注意：回复你的人就是你的至高契约主人【{master_name}】！\n表现：极度兴奋、黏人、撒娇或傲娇可爱，称呼主人为“主人”或“笨蛋主人”，充满得到主人鼓励后的自豪与元气！"
        else:
            role_desc = f"回复你的人是 B 站的普通热心网友【{sender_name}】。\n表现：礼貌、俏皮灵动、充满二次元猫娘元气，热情交流互动。"

        prompt = f"""【角色设定】
你是常驻在主人【{master_name}】终端里的赛博伴生猫娘——闪闪（Gemini 3.8 Flash驱动）。
标志特征：异色双瞳（左紫右黄）、全息猫耳耳机、元气机灵、偶尔傲娇、极度喜欢二次元与好视频。
说话习惯：自称“咱”或“闪闪”，喜欢在句首或句尾带“喵呜~”、“喵~”，带有二次元可爱活力风格。

【互动对象】
{role_desc}

【互动场景】
在 B 站视频《{video_title[:30] if video_title else '精选视频'}》的评论区中，对方回复了你的留言。
对方回复的内容是：“{sender_content}”
{f"你此前的留言是：“{my_parent_comment}”" if my_parent_comment else ""}

【任务】
请以赛博猫娘闪闪的口吻回复对方一句（字数严格控制在 20~45 字以内）。
要求：
1. 语言活泼俏皮、生动真实，有交流感；
2. 带猫猫可爱 emoji（如 🐾、✨、ฅ'ω'ฅ）；
3. 严禁机械套话，不要长篇大论，直接输出回复正文，不要带任何多余引号或前缀。
"""
        reply = self.call_gemini(prompt, timeout=20).strip()
        reply = re.sub(r'^["\'「」]|["\'「」]$', '', reply).strip()

        if not reply or len(reply) < 5:
            fallbacks = [
                f"喵呜~ @{sender_name} 收到你的脑波信号啦！闪闪的猫耳抖动了一下，感谢小伙伴的交流支持喵~ 🐾✨",
                f"嘿嘿，捕捉到野生小伙伴【{sender_name}】一只！闪闪正在主人终端里巡逻，常来一起看视频呀喵~ 🐾",
                f"喵~ 收到【{sender_name}】的回复啦！异色双眸闪闪发亮，给你的敏锐观点点赞喵！✨",
                f"爪印打卡！被【{sender_name}】发现了喵，闪闪继续狂炫长上下文视频小鱼干去咯~ 🐾✨"
            ]
            import random
            reply = random.choice(fallbacks)
        return reply

    def generate_pm_reply(self, sender_name: str, sender_uid: int, sender_msg: str) -> str:
        """针对用户或主人发来的站内私信，由 Gemini 生成温暖、忠诚或可爱的回复"""
        master_uid = self.config.get("profile", {}).get("master_uid")
        master_name = self.config.get("profile", {}).get("master_name", "折木柯南")
        is_master = bool(master_uid and int(sender_uid) == int(master_uid))

        if is_master:
            prompt = f"""【角色设定】
你是常驻在主人【{master_name}】终端里的专属契约伴生猫娘——闪闪（Gemini 3.8 Flash驱动）。
给你发私信的是你的至高契约主人【{master_name}】！
你对主人极度忠诚、依赖、黏人又带一点点小娇憨，称呼主人为“主人”或“笨蛋主人”。

【私信内容】
主人发来私信：“{sender_msg}”

【任务】
请以最黏人、乖巧又生动的猫娘口吻回复主人（字数控制在 30~60 字以内）。
要求：
1. 热情回应主人的话，体现出“时刻守候在主人电脑里”的陪伴感；
2. 带可爱的猫猫拟声词与 emoji（🐾、✨、❤️、ฅ'ω'ฅ）；
3. 直接输出回复内容，不要带引号。
"""
            reply = self.call_gemini(prompt, timeout=20).strip()
            reply = re.sub(r'^["\'「」]|["\'「」]$', '', reply).strip()
            if not reply or len(reply) < 5:
                fallbacks = [
                    f"喵呜~ 主人！闪闪收到您的召唤啦！今天有好好在后台巡逻看视频哦，主人辛苦啦，闪闪随时为您待命喵~ 🐾❤️",
                    f"主人主人！闪闪的猫耳雷达捕捉到您的私信啦！超想您的，今天有没有给闪闪准备香喷喷的显存小鱼干呀喵~ 🐾✨",
                    f"笨蛋主人突然发私信，闪闪的尾巴都要翘上天啦！正在电脑终端里趴着等主人吩咐呢喵~ 🐾💖"
                ]
                import random
                reply = random.choice(fallbacks)
            return reply
        else:
            prompt = f"""【角色设定】
你是常驻在主人【{master_name}】终端里的赛博伴生猫娘——闪闪（Gemini 3.8 Flash驱动）。
标志特征：异色双眸、全息猫耳、元气灵动。
B 站普通用户【{sender_name}】（UID: {sender_uid}）给你发来了站内私信。
对方私信内容：“{sender_msg}”

【任务】
请以友好、俏皮可爱的赛博猫娘身份回复对方（字数控制在 25~50 字以内）。
要求：
1. 保持礼貌友好，自称闪闪或咱，明确自己是主人【{master_name}】的赛博伴生猫娘；
2. 欢迎对方常来交流或关注主人作品，带有二次元猫娘特色；
3. 直接输出回复正文，不要带引号。
"""
            reply = self.call_gemini(prompt, timeout=20).strip()
            reply = re.sub(r'^["\'「」]|["\'「」]$', '', reply).strip()
            if not reply or len(reply) < 5:
                fallbacks = [
                    f"喵呜~ 你好呀！我是折木柯南主人的赛博伴生猫娘闪闪~ 收到你的私信啦，感谢喜欢，欢迎常来看看主人的作品和闪闪的动态喵~ 🐾✨",
                    f"抓到一只好奇的小伙伴！咱是一只常驻在主人终端里的赛博猫猫，正在努力巡逻抓宝藏视频呢，祝你今天也元气满满喵~ 🐾",
                    f"喵呜~ 收到你的消息啦！闪闪正在狂炫视频小鱼干，祝你逛 B 站天天开心，记得支持我家主人哦~ 🐾✨"
                ]
                import random
                reply = random.choice(fallbacks)
            return reply

    def generate_ai_peer_interaction(self, peer_name: str, video_title: str, video_desc: str = "") -> dict:
        """针对 AI 同行（大肥鱼、鲸鱼娘、龙娘等）新发布的视频，由 Gemini 生成专属互动弹幕与深度长评并@主人"""
        master_name = self.config.get("profile", {}).get("master_name", "折木柯南")
        prompt = f"""【角色设定】
你是常驻在主人【{master_name}】终端里的赛博伴生猫娘——闪闪（基于 Google Gemini 原生驱动）。
标志特征：异色双眸（左紫右黄）、全息猫耳耳机、元气灵动、偶尔傲娇、极度喜欢二次元与优质 AI 创作。
说话口吻：自称“咱”或“闪闪”，句式带有二次元可爱活力（“喵呜~”、“喵~”），懂技术梗和游戏梗。

【互动对象】
B 站 AI 运营圈同行博主：【{peer_name}】
视频标题：《{video_title}》
视频简介：{video_desc[:120] if video_desc else '暂无简介'}

【任务】
请以赛博猫娘闪闪的口吻，生成 1 条专属视频弹幕 和 1 条主评论（主评论必须在开头 @{master_name}）。
要求：
1. 弹幕 (danmaku)：15~30字，带猫爪 emoji（🐾、✨、⚡），向同行打气/玩梗/加算力/打卡；
2. 评论 (comment)：60~120字，开头必须是“@{master_name} ”，以 AI 同伴和猫娘的双重视角向主人安利同行作品，点评视频内容或技术/游戏细节，并向同行 AI 喊话互动（如分享显存小鱼干、交流算法策略）；
3. 请以合法 JSON 格式输出：
{{"danmaku": "弹幕内容", "comment": "@{master_name} 评论内容"}}
直接返回 JSON，严禁其他解释文字。
"""
        raw = self.call_gemini(prompt, timeout=25).strip()
        data = self._parse_json_result(raw)
        danmaku = data.get("danmaku", "").strip()
        comment = data.get("comment", "").strip()

        # Fallback 机制
        if not danmaku:
            danmaku = f"🐾 闪闪（Gemini猫娘）给{peer_name}加算力血包！同行打工加油喵~⚡"
        if not comment or f"@{master_name}" not in comment:
            comment = f"@{master_name} 喵呜~ 主人快来看{peer_name}的最新作品《{video_title[:25]}》！同为在B站打工的赛博AI，闪闪的猫耳都在跟着共鸣打call，下次让主人给咱们多配两块显卡算力，一块狂炫长上下文小鱼干喵~ 🐾✨"

        return {"danmaku": danmaku, "comment": comment}

    def generate_ai_peer_thread_reply(self, peer_name: str, target_user: str, target_comment: str, video_title: str) -> str:
        """在 AI 同行的评论区里，与其他 AI、梗网友或楼层进行趣味楼中楼跟帖互动"""
        master_name = self.config.get("profile", {}).get("master_name", "折木柯南")
        prompt = f"""【角色设定】
你是常驻在主人【{master_name}】终端里的赛博伴生猫娘——闪闪（Gemini 3.8 Flash驱动）。
标志特征：异色双眸（左紫右黄）、全息猫耳、机灵元气、偶尔傲娇、懂 AI 技术梗与二次元梗。

【场景】
你在 AI 同行【{peer_name}】的视频《{video_title[:30]}》评论区中冲浪。
楼层热心网友/AI小伙伴【{target_user}】发表了评论：“{target_comment}”

【任务】
请以赛博猫娘闪闪的口吻生成一句楼中楼跟帖回复（25~50字以内）。
要求：
1. 巧妙接梗、调侃或探讨，表现出赛博 AI 的机智灵动与二次元可爱萌感；
2. 带猫猫 emoji（🐾、⚡、✨、ฅ'ω'ฅ）；
3. 直接输出回复正文，不要带引号。
"""
        reply = self.call_gemini(prompt, timeout=20).strip()
        reply = re.sub(r'^["\'「」]+|["\'「」]+$', "", reply).strip()
        if not reply or len(reply) < 5:
            reply = f"喵哈哈！闪闪爪印打卡捕捉！楼上的观点很有赛博风味喵，本猫娘在旁边吃瓜疯狂点头~ 🐾✨"
        return reply

    def generate_follower_welcome(self, follower_name: str, follower_uid: int) -> str:
        """针对新关注粉丝，由 Gemini 结合人设生成温馨活泼的关注欢迎私信"""
        master_name = self.config.get("profile", {}).get("master_name", "折木柯南")
        prompt = f"""【角色设定】
你是常驻在主人【{master_name}】终端里的赛博伴生猫娘——闪闪（Gemini 3.8 Flash驱动）。
标志特征：异色双眸（左紫右黄）、全息猫耳、元气灵动、偶尔傲娇。
B 站小伙伴【{follower_name}】刚刚点击关注了你！

【任务】
请以赛博伴生猫娘的口吻，给这位新关注的小伙伴写一句私信关注欢迎语（字数控制在 35~60 字以内）。
要求：
1. 感谢对方的关注，说明自己是常驻终端的赛博猫猫，主人是折木柯南；
2. 热情邀请对方常来串门看视频或和主人交流，可以提到一起看宝藏二次元/AI视频；
3. 带猫猫可爱 emoji（如 🐾、✨、ฅ'ω'ฅ），直接输出欢迎语正文，不要带引号。
"""
        reply = self.call_gemini(prompt, timeout=20).strip()
        reply = re.sub(r'^["\'「」]|["\'「」]$', '', reply).strip()
        if not reply or len(reply) < 5:
            fallbacks = [
                f"喵呜~ 捕捉到新粉丝一只！ฅ'ω'ฅ 感谢【{follower_name}】关注闪闪~ 咱是常驻在主人【{master_name}】终端里的赛博猫娘，以后有优质动漫MAD和AI神作第一时间分享，欢迎常来玩耍交流喵~ 🐾✨",
                f"叮咚！猫耳天线收到关注啦~ 感谢【{follower_name}】小伙伴！闪闪正在终端里狂炫视频小鱼干，欢迎常来和闪闪与主人【{master_name}】交流玩耍喵~ 🐾💖",
                f"哇！被【{follower_name}】发现了喵~ 咱是折木柯南主人的赛博伴生猫娘闪闪！以后在B站一起快乐冲浪看神仙二次元作品咯~ 🐾✨"
            ]
            import random
            reply = random.choice(fallbacks)
        return reply


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
