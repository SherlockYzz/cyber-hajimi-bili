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
import subprocess
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "hajimi_config.json"
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
        self.agy_path = self.config.get("ai_engine", {}).get("agy_cli_path", r"C:\Users\Lenovo\.gemini\bin\agy.exe")
        self.model_name = self.config.get("ai_engine", {}).get("model_name", "gemini-3.8-flash-high")

    def _load_config(self) -> dict:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

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
            self.model_name,
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

    def evaluate_video(self, video_data: dict, subtitle_text: str = "", ai_summary: dict = None) -> dict:
        title = video_data.get("title", "")
        owner_name = video_data.get("owner", {}).get("name", "未知UP")
        desc = video_data.get("desc", "")[:500]
        stat = video_data.get("stat", {})
        view = stat.get("view", 0)
        like = stat.get("like", 0)
        coin = stat.get("coin", 0)
        bvid = video_data.get("bvid", "")

        master_name = self.config.get("profile", {}).get("master_name", "主人")
        at_threshold = self.config.get("interaction", {}).get("at_score_threshold", 8.5)

        summary_text = ""
        if ai_summary and ai_summary.get("summary"):
            summary_text = f"B站官方总结: {ai_summary.get('summary')}\n"

        sub_snippet = f"CC字幕精选片段: {subtitle_text[:1200]}" if subtitle_text else "（暂无CC字幕，仅参考简介与标题）"

        prompt = f"""
以下是你的角色人设，请严格入戏：
{self.persona}

---
【主人信息】
称呼主人为: {master_name}
触发在评论区 @主人的分数阈值: {at_threshold} 分

【待质检视频元数据】
- 标题: {title}
- UP主: {owner_name}
- BV号: {bvid}
- 数据: 播放量 {view} | 点赞 {like} | 投币 {coin}
- 简介: {desc}
{summary_text}- 字幕/内容概览: {sub_snippet}

---
【任务指令】
请以赛博猫猫哈基米的口吻与严苛的审美打分体系（1.0 ~ 10.0 分），评估此视频。
必须严格输出纯 JSON 格式（不要包含任何外部废话），JSON 结构如下：
{{
  "score": 8.8,
  "verdict": "宝藏神作",
  "highlight": "用一两句极其精炼、信息密度高的话浓缩其核心干货亮点",
  "cat_comment": "@{master_name} 喵呜~ （用傲娇贴心的猫猫口癖，一句话点出最棒的地方，建议主人快来看）",
  "should_at": true,
  "reasons": ["核心见解独到", "干货密度极高"]
}}
注意：
1. 只有 score >= {at_threshold} 时，should_at 才能为 true，否则必须为 false；
2. 如果是营销号洗稿、标题党、毫无干货，请给出 1.0~5.9 的低分并无情报废；
3. 输出必须是合法 JSON。
"""

        raw_output = self.call_gemini(prompt, timeout=40)
        parsed = self._parse_json_result(raw_output)

        if not parsed:
            score = 7.5
            if like > 10000 and coin > 3000:
                score = 8.6
            parsed = {
                "score": score,
                "verdict": "值得一看" if score < 8.5 else "宝藏神作",
                "highlight": desc[:80] if desc else "高关注度热门视频",
                "cat_comment": f"@{master_name} 喵呜~ 发现一条热门视频《{title}》，UP主讲得挺有意思，主人有空可以瞄一眼~",
                "should_at": (score >= at_threshold),
                "reasons": ["数据热度较高"],
            }

        parsed["bvid"] = bvid
        parsed["title"] = title
        parsed["owner"] = owner_name
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
