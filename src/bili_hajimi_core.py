# -*- coding: utf-8 -*-
"""
赛博哈基米 (Cyber-Hajimi) - B 站底层通信与感知执行核心
- 官方 OAuth 二维码扫码登录与凭证自动维护
- WBI 接口加密签名（w_rid 与 wts）动态计算与防 -352 反爬
- SPI / BUVID3 / BUVID4 指纹自适应保持
- 仿生推荐流抓取、关键词定向追踪与负向屏蔽过滤
- CC/AI 视频字幕文本提取与官方 AI 总结解析
- 视频评论区互动（支持 @ 主人 UID/昵称）
- 仿生作息与 412/429 智能指数退避
"""

import os
import sys
import json
import time
import random
import hashlib
import urllib.parse
import urllib.request
import urllib.error
import re
import io
import zlib
from collections import Counter
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]

SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "hajimi_config.json"
LOCAL_CONFIG_PATH = PROJECT_ROOT / "config" / "hajimi_config.local.json"
QRCODE_PATH = PROJECT_ROOT / "images" / "qrcode_login.png"
JOURNALS_DIR = PROJECT_ROOT / "docs" / "journals"
CACHE_DIR = PROJECT_ROOT / "cache"
COVERS_DIR = CACHE_DIR / "covers"
STORYBOARDS_DIR = CACHE_DIR / "storyboards"

JOURNALS_DIR.mkdir(parents=True, exist_ok=True)
QRCODE_PATH.parent.mkdir(parents=True, exist_ok=True)
COVERS_DIR.mkdir(parents=True, exist_ok=True)
STORYBOARDS_DIR.mkdir(parents=True, exist_ok=True)


def get_mixin_key(orig: str) -> str:
    return "".join([orig[i] for i in MIXIN_KEY_ENC_TAB if i < len(orig)])[:32]


class BiliHajimiCore:
    def __init__(self, config_or_path=None):
        if isinstance(config_or_path, dict):
            self.config = config_or_path
            self.config_path = CONFIG_PATH
        elif isinstance(config_or_path, (str, Path)):
            self.config_path = Path(config_or_path)
            self.config = self._load_config()
        else:
            self.config_path = CONFIG_PATH
            self.config = self._load_config()

        self.wbi_cache = {"img_key": "", "sub_key": "", "expire_time": 0}
        self.user_agent = self.config.get("risk_control", {}).get(
            "user_agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self._ensure_buvid()

    def _load_config(self) -> dict:
        cfg = {}
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            except Exception as e:
                print(f"[Core] 读取配置失败: {e}")
        # 如果存在本地优先配置 (如登录态及本地专属个性化)，合并本地信息
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
                if local_cfg.get("schedule"):
                    cfg["schedule"] = local_cfg["schedule"]
            except Exception:
                pass
        return cfg

    def save_config(self):
        try:
            # 1. 保存主配置
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            # 2. 同步写入 local.json 保持双向一致
            if LOCAL_CONFIG_PATH.exists():
                with open(LOCAL_CONFIG_PATH, "w", encoding="utf-8") as f:
                    json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Core] 保存配置失败: {e}")

    def _ensure_buvid(self):
        auth = self.config.setdefault("auth", {})
        if not auth.get("buvid3"):
            try:
                req = urllib.request.Request(
                    "https://api.bilibili.com/x/frontend/finger/spi",
                    headers={"User-Agent": self.user_agent}
                )
                with urllib.request.urlopen(req, timeout=8) as res:
                    data = json.loads(res.read().decode("utf-8"))
                    if data.get("code") == 0:
                        auth["buvid3"] = data.get("data", {}).get("b_3", "")
                        auth["buvid4"] = data.get("data", {}).get("b_4", "")
                        self.save_config()
            except Exception as e:
                print(f"[Core] 获取 buvid 提示: {e}")

    def get_cookie_header(self) -> str:
        auth = self.config.get("auth", {})
        cookies = []
        mapping = {
            "dedeuserid": "DedeUserID",
            "sessdata": "SESSDATA",
            "bili_jct": "bili_jct",
            "buvid3": "buvid3",
            "buvid4": "buvid4"
        }
        for k, cookie_key in mapping.items():
            val = auth.get(k)
            if val:
                cookies.append(f"{cookie_key}={val}")
        return "; ".join(cookies)

    def _request(self, url: str, params: dict = None, method: str = "GET", data: dict = None, headers: dict = None) -> dict:
        if params:
            query = urllib.parse.urlencode(params)
            url = f"{url}?{query}" if "?" not in url else f"{url}&{query}"

        all_headers = {
            "User-Agent": self.user_agent,
            "Referer": "https://www.bilibili.com/",
            "Accept": "application/json, text/plain, */*",
        }
        cookie_str = self.get_cookie_header()
        if cookie_str:
            all_headers["Cookie"] = cookie_str

        if headers:
            all_headers.update(headers)

        body_bytes = None
        if data is not None:
            body_bytes = urllib.parse.urlencode(data).encode("utf-8")
            all_headers["Content-Type"] = "application/x-www-form-urlencoded"

        req = urllib.request.Request(url, data=body_bytes, headers=all_headers, method=method)

        retries = 3
        backoff = 2.0
        for attempt in range(retries):
            try:
                min_wait = self.config.get("risk_control", {}).get("min_request_interval_ms", 2000) / 1000.0
                max_wait = self.config.get("risk_control", {}).get("max_request_interval_ms", 4000) / 1000.0
                time.sleep(random.uniform(min_wait, max_wait))

                with urllib.request.urlopen(req, timeout=12) as response:
                    raw = response.read().decode("utf-8", errors="replace")
                    return json.loads(raw)
            except urllib.error.HTTPError as e:
                if e.code in (412, 429) and attempt < retries - 1:
                    print(f"[Core] 遇到 HTTP {e.code} 风控拦截，执行指数退避休眠 ({backoff:.1f}s)...")
                    time.sleep(backoff)
                    backoff *= 2.0
                else:
                    return {"code": e.code, "message": str(e), "data": None}
            except Exception as e:
                if attempt < retries - 1:
                    time.sleep(1.0)
                else:
                    return {"code": -1, "message": str(e), "data": None}
        return {"code": -999, "message": "超过最大重试次数", "data": None}

    # ==================== WBI 混淆签名 ====================
    def get_wbi_keys(self) -> tuple[str, str]:
        now = time.time()
        if self.wbi_cache["expire_time"] > now and self.wbi_cache["img_key"]:
            return self.wbi_cache["img_key"], self.wbi_cache["sub_key"]

        resp = self._request("https://api.bilibili.com/x/web-interface/nav")
        wbi_img = resp.get("data", {}).get("wbi_img", {})
        img_url = wbi_img.get("img_url", "")
        sub_url = wbi_img.get("sub_url", "")

        if img_url and sub_url:
            img_key = img_url.split("/")[-1].split(".")[0]
            sub_key = sub_url.split("/")[-1].split(".")[0]
            self.wbi_cache = {"img_key": img_key, "sub_key": sub_key, "expire_time": now + 3600}
            return img_key, sub_key

        return "7cd084941338484aae1ad9425b84077c", "4932caff0ff746eab6f01bf08b70ac45"

    def sign_wbi(self, params: dict) -> dict:
        img_key, sub_key = self.get_wbi_keys()
        mixin_key = get_mixin_key(img_key + sub_key)
        params["wts"] = round(time.time())
        sorted_params = dict(sorted(params.items()))
        filtered = {
            k: "".join([c for c in str(v) if c not in "!'()*"])
            for k, v in sorted_params.items()
        }
        query = urllib.parse.urlencode(filtered)
        w_rid = hashlib.md5((query + mixin_key).encode()).hexdigest()
        filtered["w_rid"] = w_rid
        return filtered

    # ==================== 登录管理 ====================
    def generate_login_qr(self) -> dict:
        """获取登录二维码并落盘到 images/qrcode_login.png"""
        req_url = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
        headers = {
            "User-Agent": self.user_agent,
            "Referer": "https://passport.bilibili.com/login",
        }
        req = urllib.request.Request(req_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode("utf-8"))

        if data.get("code") != 0:
            return {"success": False, "message": "生成二维码失败"}

        qr_url = data["data"]["url"]
        qrcode_key = data["data"]["qrcode_key"]

        try:
            import qrcode
            qr = qrcode.QRCode(box_size=10, border=2)
            qr.add_data(qr_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(str(QRCODE_PATH))
            print(f"[Core] 登录二维码已落盘: {QRCODE_PATH}")
        except Exception as e:
            print(f"[Core] 生成二维码图片提示: {e}")

        return {
            "success": True,
            "url": qr_url,
            "qrcode_key": qrcode_key,
            "img_path": str(QRCODE_PATH),
        }

    def print_ascii_qr(self, qr_url: str):
        try:
            import qrcode
            qr = qrcode.QRCode()
            qr.add_data(qr_url)
            qr.make(fit=True)
            print("\n" + "=" * 48)
            print("  请使用哔哩哔哩手机客户端扫描下方二维码登录：")
            print("=" * 48)
            qr.print_ascii(invert=True)
            print("=" * 48 + "\n")
        except Exception:
            pass

    def poll_login_status(self, qrcode_key: str) -> dict:
        url = f"https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key={qrcode_key}"
        headers = {
            "User-Agent": self.user_agent,
            "Referer": "https://passport.bilibili.com/login",
        }
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                set_cookies = res.headers.get_all("Set-Cookie") or []
                raw_body = res.read().decode("utf-8")
                data = json.loads(raw_body)
                code = data.get("data", {}).get("code", -1)

                if code == 0:
                    auth = self.config.setdefault("auth", {})
                    for header in set_cookies:
                        parts = header.split(";")[0].split("=", 1)
                        if len(parts) == 2:
                            k_lower = parts[0].strip().lower()
                            val = parts[1].strip()
                            if k_lower == "dedeuserid":
                                auth["dedeuserid"] = val
                            elif k_lower == "sessdata":
                                auth["sessdata"] = val
                            elif k_lower == "bili_jct":
                                auth["bili_jct"] = val

                    auth["is_logged_in"] = True
                    self.save_config()
                    user_info = self.get_user_info()
                    return {
                        "status": "success",
                        "code": 0,
                        "message": "登录成功！",
                        "user": user_info,
                    }
                elif code == 86090:
                    return {"status": "scanned", "code": 86090, "message": "已扫码，请在手机上点击确认登录"}
                elif code == 86101:
                    return {"status": "waiting", "code": 86101, "message": "等待扫码中..."}
                elif code == 86038:
                    return {"status": "expired", "code": 86038, "message": "二维码已失效，请重新生成"}
                else:
                    return {"status": "other", "code": code, "message": data.get("data", {}).get("message", "未知状态")}
        except Exception as e:
            return {"status": "error", "code": -1, "message": str(e)}

    def get_user_info(self, cache_ttl: int = 300) -> dict:
        now = time.time()
        if hasattr(self, "_user_info_cache") and self._user_info_cache and (now - getattr(self, "_user_info_cached_at", 0) < cache_ttl):
            return self._user_info_cache

        resp = self._request("https://api.bilibili.com/x/web-interface/nav")
        if resp.get("code") == 0 and resp.get("data", {}).get("isLogin"):
            data = resp["data"]
            mid = data.get("mid", 0)
            uname = data.get("uname", "")

            self.config["auth"]["is_logged_in"] = True
            info = {
                "is_login": True,
                "mid": mid,
                "uname": uname,
                "vip": data.get("vipStatus", 0),
                "avatar": data.get("face", ""),
                "coins": data.get("money", 0),
            }
            self._user_info_cache = info
            self._user_info_cached_at = now
            return info
        return {"is_login": False, "mid": 0, "uname": "未登录", "vip": 0, "avatar": "", "coins": 0}

    # ==================== 视频获取 ====================
    def get_popular_videos(self, pn: int = 1, ps: int = 10) -> list[dict]:
        url = "https://api.bilibili.com/x/web-interface/popular"
        resp = self._request(url, params={"pn": pn, "ps": ps})
        if resp.get("code") == 0:
            return resp.get("data", {}).get("list", [])
        return []

    def search_keyword_videos(self, keyword: str, page: int = 1, order: str = "pubdate") -> list[dict]:
        params = {
            "search_type": "video",
            "keyword": keyword,
            "page": page,
            "order": order,
        }
        signed = self.sign_wbi(params)
        url = "https://api.bilibili.com/x/web-interface/wbi/search/type"
        resp = self._request(url, params=signed, headers={"Referer": "https://search.bilibili.com/"})
        if resp.get("code") == 0:
            return resp.get("data", {}).get("result", [])
        return []

    def get_video_detail(self, bvid: str) -> dict:
        url = "https://api.bilibili.com/x/web-interface/view"
        resp = self._request(url, params={"bvid": bvid})
        if resp.get("code") == 0:
            data = resp.get("data", {})
            return {
                "bvid": bvid,
                "aid": data.get("aid", 0),
                "cid": data.get("cid", 0),
                "title": data.get("title", ""),
                "desc": data.get("desc", ""),
                "duration": data.get("duration", 0),
                "pubdate": data.get("pubdate", 0),
                "owner": data.get("owner", {}),
                "stat": data.get("stat", {}),
                "pic": data.get("pic", ""),
                "tname": data.get("tname", ""),
            }
        return {}

    def get_video_subtitles(self, bvid: str, cid: int) -> str:
        url = "https://api.bilibili.com/x/player/v2"
        resp = self._request(url, params={"bvid": bvid, "cid": cid})
        subtitles = resp.get("data", {}).get("subtitle", {}).get("subtitles", [])
        if not subtitles:
            return ""

        target_sub = subtitles[0]
        for s in subtitles:
            if "zh" in s.get("lan", "").lower() or "中文" in s.get("lan_doc", ""):
                target_sub = s
                break

        sub_url = target_sub.get("subtitle_url", "")
        if not sub_url:
            return ""
        if not sub_url.startswith("http"):
            sub_url = "https:" + sub_url

        try:
            req = urllib.request.Request(sub_url, headers={"User-Agent": self.user_agent})
            with urllib.request.urlopen(req, timeout=8) as res:
                sub_body = json.loads(res.read().decode("utf-8"))
                lines = [item.get("content", "").strip() for item in sub_body.get("body", []) if item.get("content")]
                return " ".join(lines)[:15000]
        except Exception:
            return ""

    def get_ai_conclusion(self, bvid: str, cid: int, up_mid: int) -> dict:
        params = {"bvid": bvid, "cid": cid, "up_mid": up_mid}
        signed = self.sign_wbi(params)
        url = "https://api.bilibili.com/x/web-interface/view/conclusion/get"
        resp = self._request(url, params=signed)
        if resp.get("code") == 0:
            data = resp.get("data", {})
            model_result = data.get("model_result", {})
            return {
                "summary": model_result.get("summary", ""),
                "outline": model_result.get("outline", [])
            }
        return {}

    # ==================== 多模态视觉与时序分镜感知 ====================
    def download_video_cover(self, bvid: str, pic_url: str) -> str:
        """下载视频高清原画封面至本地缓存"""
        if not pic_url:
            return ""
        if pic_url.startswith("//"):
            pic_url = "https:" + pic_url
        ext = os.path.splitext(urllib.parse.urlparse(pic_url).path)[-1] or ".jpg"
        save_path = COVERS_DIR / f"{bvid}{ext}"
        if save_path.exists() and save_path.stat().st_size > 1000:
            return str(save_path.resolve())

        try:
            req = urllib.request.Request(pic_url, headers={"User-Agent": self.user_agent, "Referer": "https://www.bilibili.com/"})
            with urllib.request.urlopen(req, timeout=10) as res:
                content = res.read()
                if len(content) > 1000:
                    with open(save_path, "wb") as f:
                        f.write(content)
                    return str(save_path.resolve())
        except Exception as e:
            print(f"[Core] 下载封面失败 [{bvid}]: {e}")
        return ""

    def get_video_storyboard_strip(self, bvid: str, cid: int, target_frames: int = 5) -> str:
        """
        利用 B 站底层的 VideoShot / Storyboard 雪碧图，
        按时间轴均匀抽取 target_frames 个时序关键分镜，横向拼接为时序画卷 (Storyboard Strip)
        """
        save_path = STORYBOARDS_DIR / f"{bvid}_storyboard_strip.jpg"
        if save_path.exists() and save_path.stat().st_size > 2000:
            return str(save_path.resolve())

        url = "https://api.bilibili.com/x/player/videoshot"
        resp = self._request(url, params={"bvid": bvid, "cid": cid, "index": 1})
        if resp.get("code") != 0 or not resp.get("data"):
            return ""

        data = resp.get("data", {})
        images = data.get("image", [])
        if not images:
            return ""

        sprite_url = images[0]
        if sprite_url.startswith("//"):
            sprite_url = "http:" + sprite_url
        elif sprite_url.startswith("https://bimp.hdslb.com"):
            sprite_url = sprite_url.replace("https://", "http://")

        try:
            req = urllib.request.Request(sprite_url, headers={"User-Agent": self.user_agent, "Referer": "https://www.bilibili.com/"})
            with urllib.request.urlopen(req, timeout=10) as res:
                sprite_bytes = res.read()
            sprite_img = Image.open(io.BytesIO(sprite_bytes))
        except Exception:
            try:
                alt_url = sprite_url.replace("http://", "https://") if sprite_url.startswith("http://") else sprite_url.replace("https://", "http://")
                req = urllib.request.Request(alt_url, headers={"User-Agent": self.user_agent, "Referer": "https://www.bilibili.com/"})
                with urllib.request.urlopen(req, timeout=10) as res:
                    sprite_bytes = res.read()
                sprite_img = Image.open(io.BytesIO(sprite_bytes))
            except Exception as e:
                print(f"[Core] 下载分镜雪碧图失败 [{bvid}]: {e}")
                return ""

        img_x_len = data.get("img_x_len", 10)
        img_y_len = data.get("img_y_len", 10)
        img_x_size = data.get("img_x_size", 160)
        img_y_size = data.get("img_y_size", 90)
        index_list = data.get("index", [])
        total_frames = len(index_list)
        if total_frames <= 0:
            # 动态嗅探雪碧图中的有效帧数，防止短视频尾部黑帧误采
            valid_cnt = 0
            max_possible = img_x_len * img_y_len
            for idx in range(max_possible):
                c = idx % img_x_len
                r = idx // img_x_len
                box = (c * img_x_size, r * img_y_size, (c + 1) * img_x_size, (r + 1) * img_y_size)
                tile = sprite_img.crop(box)
                stat = tile.resize((16, 9)).convert("L")
                if sum(stat.getdata()) / 144.0 > 1.0:
                    valid_cnt += 1
                else:
                    break
            total_frames = valid_cnt if valid_cnt > 0 else (img_x_len * img_y_len)

        if total_frames <= 0:
            return ""

        # 均匀选取时序点: 如 [0.1, 0.3, 0.5, 0.7, 0.9]
        if target_frames == 1:
            points = [0.5]
        else:
            step = 1.0 / (target_frames + 1)
            points = [step * (i + 1) for i in range(target_frames)]

        sampled_indices = [int(p * (total_frames - 1)) for p in points]

        # 拼接画卷 (单元格放大为 240x135 提升 Gemini 视觉清晰度)
        cell_w, cell_h = 240, 135
        strip_img = Image.new("RGB", (cell_w * len(sampled_indices), cell_h + 24), color=(18, 18, 28))
        draw = ImageDraw.Draw(strip_img)

        try:
            font = ImageFont.truetype("arialbd.ttf", 14)
        except Exception:
            font = ImageFont.load_default()

        for idx, f_idx in enumerate(sampled_indices):
            col = f_idx % img_x_len
            row = f_idx // img_x_len
            x1 = col * img_x_size
            y1 = row * img_y_size
            cropped = sprite_img.crop((x1, y1, x1 + img_x_size, y1 + img_y_size))
            resized = cropped.resize((cell_w, cell_h), Image.Resampling.LANCZOS)
            strip_img.paste(resized, (idx * cell_w, 0))

            # 底部标注时序进度
            sec = index_list[f_idx] if f_idx < len(index_list) else 0
            m, s = divmod(sec, 60)
            pct_label = f"[{int(points[idx]*100)}%] {m:02d}:{s:02d}"
            draw.text((idx * cell_w + 12, cell_h + 4), pct_label, font=font, fill=(180, 200, 255))

        strip_img.save(save_path, quality=92)
        return str(save_path.resolve())

    def get_video_danmaku_insights(self, cid: int) -> dict:
        """抓取并分析实时弹幕热力与高能点"""
        url = f"https://api.bilibili.com/x/v1/dm/list.so?oid={cid}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
            with urllib.request.urlopen(req, timeout=8) as res:
                raw = res.read()
            try:
                xml_text = zlib.decompress(raw, -zlib.MAX_WBITS).decode("utf-8", errors="replace")
            except Exception:
                xml_text = zlib.decompress(raw).decode("utf-8", errors="replace")
        except Exception:
            return {}

        matches = re.findall(r'<d p="([^,]+)[^>]*>([^<]+)</d>', xml_text)
        if not matches:
            return {"total_danmaku": 0}

        # 统计时间区间 (15秒一个区间)
        buckets = Counter(int(float(m[0]) // 15) * 15 for m in matches)
        top_peaks = []
        for sec, count in buckets.most_common(3):
            m, s = divmod(sec, 60)
            top_peaks.append(f"{m:02d}:{s:02d} ({count}条弹幕爆发)")

        # 统计高频共鸣词
        key_words = ["高能", "封神", "卧槽", "神仙", "原画", "泪目", "草", "燃", "鸡皮疙瘩", "太帅了", "好活", "双厨狂喜", "名场面"]
        found_keywords = Counter()
        for _, text in matches:
            for kw in key_words:
                if kw in text:
                    found_keywords[kw] += 1

        top_kw = [f"{k}({v}次)" for k, v in found_keywords.most_common(5) if v > 1]
        sample_dm = [m[1].strip() for m in matches if len(m[1].strip()) >= 4][:8]

        return {
            "total_danmaku": len(matches),
            "peak_intervals": top_peaks,
            "hot_keywords": top_kw,
            "sample_danmaku": sample_dm
        }

    # ==================== 评论与社区互动 ====================
    def get_video_comments(self, aid: int, page_size: int = 10) -> dict:
        """兼容接口：获取视频评论列表"""
        hot = self.get_video_hot_comments(aid, count=page_size)
        return {"replies": [{"rpid": h["rpid"], "member": {"uname": h["uname"], "mid": 0}, "content": {"message": h["message"]}} for h in hot]}

    def get_video_hot_comments(self, aid: int, count: int = 6) -> list[dict]:
        """通过 WBI 验签抓取视频最热门的高赞社区评论与核心讨论点"""
        if not aid:
            return []
        try:
            params = {"oid": int(aid), "type": 1, "mode": 3, "ps": count}
            signed = self.sign_wbi(params)
            res = self._request("https://api.bilibili.com/x/v2/reply/wbi/main", params=signed)
            if res.get("code") == 0:
                replies = res.get("data", {}).get("replies", []) or []
                hot_list = []
                for r in replies[:count]:
                    hot_list.append({
                        "rpid": r.get("rpid"),
                        "uname": r.get("member", {}).get("uname", "热心网友"),
                        "like": r.get("like", 0),
                        "message": r.get("content", {}).get("message", "").strip(),
                        "rcount": r.get("rcount", 0)
                    })
                return hot_list
        except Exception as e:
            print(f"[Core] 抓取热门评论异常: {e}")
        return []

    def post_comment(self, aid: int, message: str, at_name_to_mid: dict = None, root: int = 0, parent: int = 0) -> dict:
        """发布视频主楼评论或回复指定热门评论参与社区讨论"""
        csrf = self.config.get("auth", {}).get("bili_jct", "")
        if not csrf:
            return {"success": False, "message": "未登录或缺少 csrf 凭证"}

        url = "https://api.bilibili.com/x/v2/reply/add"
        payload = {
            "type": 1,
            "oid": aid,
            "message": message,
            "csrf": csrf,
            "plat": 1,
        }
        if root:
            payload["root"] = int(root)
        if parent:
            payload["parent"] = int(parent)
        if at_name_to_mid:
            payload["at_name_to_mid"] = json.dumps(at_name_to_mid, ensure_ascii=False)

        resp = self._request(url, method="POST", data=payload, headers={"Referer": f"https://www.bilibili.com/video/av{aid}"})
        if resp.get("code") == 0:
            return {"success": True, "message": "评论发布成功！", "data": resp.get("data")}
        else:
            return {"success": False, "message": resp.get("message", "发布失败"), "code": resp.get("code")}

    def report_video_view(self, aid: int, cid: int, progress: int = 60) -> dict:
        """向 B 站官方上报播放历史与进度，确保账号历史记录真实留痕"""
        csrf = self.config.get("auth", {}).get("bili_jct", "")
        if not csrf or not aid or not cid:
            return {"success": False, "message": "参数不足或未登录"}

        url = "https://api.bilibili.com/x/v2/history/report"
        payload = {
            "aid": int(aid),
            "cid": int(cid),
            "progress": int(progress),
            "platform": "web",
            "csrf": csrf
        }
        resp = self._request(
            url,
            method="POST",
            data=payload,
            headers={"Referer": f"https://www.bilibili.com/video/av{aid}"}
        )
        if resp.get("code") == 0:
            return {"success": True, "message": "历史记录上报成功"}
        return {"success": False, "message": resp.get("message", "上报失败"), "code": resp.get("code")}

    def get_my_history(self, ps: int = 20) -> list[dict]:
        """获取当前账号真实的 B 站云端观看历史记录"""
        url = f"https://api.bilibili.com/x/web-interface/history/cursor?ps={ps}"
        resp = self._request(url)
        if resp.get("code") == 0:
            return resp.get("data", {}).get("list", [])
        return []

    def get_up_videos(self, mid: int, page: int = 1, page_size: int = 30) -> list[dict]:
        """通过 WBI 验签抓取指定 UP 主的投稿视频列表"""
        signed_params = self.sign_wbi({
            "mid": mid,
            "ps": page_size,
            "pn": page,
            "order": "pubdate"
        })
        resp = self._request("https://api.bilibili.com/x/space/wbi/arc/search", params=signed_params)
        if resp.get("code") == 0:
            return resp.get("data", {}).get("list", {}).get("vlist", [])
        return []

    def like_video(self, aid: int, like: int = 1) -> dict:
        """点赞视频 (like: 1 点赞, 2 取消点赞)"""
        csrf = self.config.get("auth", {}).get("bili_jct", "")
        if not csrf:
            return {"success": False, "message": "未登录或缺少 csrf 凭证"}

        url = "https://api.bilibili.com/x/web-interface/archive/like"
        payload = {
            "aid": aid,
            "like": like,
            "csrf": csrf
        }
        resp = self._request(url, method="POST", data=payload, headers={"Referer": f"https://www.bilibili.com/video/av{aid}"})
        code = resp.get("code")
        if code == 0:
            return {"success": True, "message": "点赞成功！"}
        elif code == 65006:
            return {"success": True, "message": "已点过赞"}
        else:
            return {"success": False, "message": resp.get("message", "点赞失败"), "code": code}


    def report_video_heartbeat(self, aid: int, cid: int, bvid: str, played_time: int = 60) -> dict:
        """上报视频播放心跳包，让视频真实记录在 B 站云端历史记录中"""
        csrf = self.config.get("auth", {}).get("bili_jct", "")
        my_uid = self.config.get("auth", {}).get("dedeuserid", "")
        if not aid or not cid or not bvid:
            return {"success": False, "message": "缺少必要参数"}
        url = "https://api.bilibili.com/x/click-interface/web/heartbeat"
        now_ts = int(time.time())
        p_time = max(30, int(played_time))
        data = {
            "aid": aid,
            "bvid": bvid,
            "cid": cid,
            "mid": my_uid,
            "csrf": csrf,
            "played_time": p_time,
            "real_played_time": p_time,
            "realtime": p_time,
            "start_ts": now_ts - p_time - 5,
            "type": 3,
            "sub_type": 0,
            "dt": 2,
            "play_type": 0
        }
        resp = self._request(url, method="POST", data=data, headers={"Referer": f"https://www.bilibili.com/video/{bvid}"})
        if resp.get("code") == 0:
            return {"success": True, "message": "播放心跳上报成功，已写入历史记录"}
        return {"success": False, "message": resp.get("message", "心跳上报失败")}

    def get_user_fav_folders(self) -> list[dict]:
        """拉取当前登录用户创建的所有收藏夹列表"""
        my_uid = self.config.get("auth", {}).get("dedeuserid", "")
        if not my_uid:
            return []
        url = f"https://api.bilibili.com/x/v3/fav/folder/created/list-all?up_mid={my_uid}"
        resp = self._request(url)
        if resp.get("code") == 0:
            data = resp.get("data")
            if isinstance(data, dict):
                return data.get("list", [])
            elif isinstance(data, list):
                return data
        return []

    def create_fav_folder(self, title: str, intro: str = "", privacy: int = 0) -> dict:
        """自主创建新收藏夹"""
        csrf = self.config.get("auth", {}).get("bili_jct", "")
        if not csrf:
            return {"success": False, "message": "缺少 csrf 凭据"}
        url = "https://api.bilibili.com/x/v3/fav/folder/add"
        data = {
            "title": title,
            "intro": intro or "闪闪与主人共同精选沉淀的宝藏分类收藏夹🐾",
            "privacy": privacy,
            "csrf": csrf
        }
        resp = self._request(url, method="POST", data=data, headers={"Referer": "https://space.bilibili.com/"})
        if resp.get("code") == 0:
            fid = resp.get("data", {}).get("id")
            return {"success": True, "folder_id": fid, "title": title}
        return {"success": False, "message": resp.get("message", "创建收藏夹失败")}

    def is_video_favoured(self, aid: int) -> bool:
        """检查当前视频是否已收藏"""
        url = f"https://api.bilibili.com/x/v2/fav/video/favoured?aid={aid}"
        resp = self._request(url)
        if resp.get("code") == 0:
            return bool(resp.get("data", {}).get("favoured", False))
        return False

    def add_video_to_fav(self, aid: int, folder_id: int, bvid: str = "") -> dict:
        """将视频精准收藏至指定收藏夹"""
        csrf = self.config.get("auth", {}).get("bili_jct", "")
        if not csrf:
            return {"success": False, "message": "缺少 csrf 凭据"}
        url = "https://api.bilibili.com/x/v3/fav/resource/deal"
        ref = f"https://www.bilibili.com/video/{bvid}" if bvid else f"https://www.bilibili.com/video/av{aid}"
        data = {
            "rid": aid,
            "type": 2,
            "add_media_ids": str(folder_id),
            "del_media_ids": "",
            "csrf": csrf
        }
        resp = self._request(url, method="POST", data=data, headers={"Referer": ref})
        if resp.get("code") == 0:
            return {"success": True, "message": "收藏成功"}
        return {"success": False, "message": resp.get("message", "收藏失败")}
    def send_danmaku(self, cid: int, bvid: str, message: str, progress_ms: int = 3000, color: int = 16766720) -> dict:
        """在指定时间戳发送弹幕 (color 默认为闪闪的金色 16766720)"""
        csrf = self.config.get("auth", {}).get("bili_jct", "")
        if not csrf:
            return {"success": False, "message": "未登录或缺少 csrf 凭证"}

        url = "https://api.bilibili.com/x/v2/dm/post"
        payload = {
            "type": 1,
            "oid": cid,
            "msg": message,
            "bvid": bvid,
            "progress": progress_ms,
            "color": color,
            "fontsize": 25,
            "mode": 1,
            "rnd": int(time.time() * 1000),
            "csrf": csrf
        }
        resp = self._request(url, method="POST", data=payload, headers={"Referer": f"https://www.bilibili.com/video/{bvid}"})
        if resp.get("code") == 0:
            return {"success": True, "message": "弹幕发送成功！", "data": resp.get("data")}
        else:
            return {"success": False, "message": resp.get("message", "弹幕发送失败"), "code": resp.get("code")}

    def get_home_recommendations(self, ps: int = 15) -> list[dict]:
        """抓取 B 站首页推荐信息流视频 (海量初筛专用)"""
        url = "https://api.bilibili.com/x/web-interface/index/top/feed/rcmd"
        resp = self._request(url, params={"ps": ps, "fresh_type": 3, "feed_version": "V8"})
        if resp.get("code") == 0:
            items = resp.get("data", {}).get("item", [])
            results = []
            for i in items:
                bvid = i.get("bvid")
                if bvid:
                    results.append({
                        "bvid": bvid,
                        "aid": i.get("id"),
                        "title": i.get("title", ""),
                        "owner": {"name": i.get("owner", {}).get("name", "B站UP"), "mid": i.get("owner", {}).get("mid", 0)},
                        "desc": i.get("desc", ""),
                        "stat": i.get("stat", {}),
                        "duration": i.get("duration", 0),
                        "source": "首页推荐流"
                    })
            return results
        return []

    def get_followed_dynamic_videos(self, ps: int = 20) -> list[dict]:
        """抓取关注的 UP 主发布的最新视频动态 (午后精读专用)"""
        url = "https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/all"
        resp = self._request(url, params={"type": "video"})
        if resp.get("code") == 0:
            items = resp.get("data", {}).get("items", [])
            results = []
            for item in items:
                if item.get("type") == "DYNAMIC_TYPE_AV":
                    author = item.get("modules", {}).get("module_author", {})
                    archive = item.get("modules", {}).get("module_dynamic", {}).get("major", {}).get("archive", {})
                    bvid = archive.get("bvid")
                    if bvid:
                        results.append({
                            "bvid": bvid,
                            "aid": archive.get("aid"),
                            "title": archive.get("title", ""),
                            "owner": {"name": author.get("name", ""), "mid": author.get("mid", 0)},
                            "desc": archive.get("desc", ""),
                            "duration_text": archive.get("duration_text", ""),
                            "stat": archive.get("stat", {}),
                            "source": f"关注UP主动态 ({author.get('name')})"
                        })
            return results
        return []

    def send_private_message(self, receiver_uid: int, content: str) -> dict:
        """向指定用户（主人）发送 B 站私信"""
        csrf = self.config.get("auth", {}).get("bili_jct", "")
        sender_uid = self.config.get("auth", {}).get("dedeuserid", "")
        if not csrf or not sender_uid:
            return {"success": False, "message": "未登录或缺少凭证"}

        import uuid
        dev_id = str(uuid.uuid4()).upper()
        url = "https://api.vc.bilibili.com/web_im/v1/web_im/send_msg"
        payload = {
            "msg[sender_uid]": sender_uid,
            "msg[receiver_id]": receiver_uid,
            "msg[receiver_type]": 1,
            "msg[msg_type]": 1,
            "msg[msg_status]": 0,
            "msg[content]": json.dumps({"content": content}, ensure_ascii=False),
            "msg[timestamp]": int(time.time()),
            "msg[new_face_version]": 0,
            "msg[dev_id]": dev_id,
            "csrf": csrf,
            "csrf_token": csrf,
            "build": 0,
            "mobi_app": "web"
        }
        resp = self._request(
            url,
            method="POST",
            data=payload,
            headers={
                "Origin": "https://message.bilibili.com",
                "Referer": "https://message.bilibili.com/"
            }
        )
        if resp.get("code") == 0:
            return {"success": True, "message": "私信发送成功！", "data": resp.get("data")}
        else:
            code = resp.get("code")
            msg = resp.get("message", "私信发送失败")
            if code == 21001:
                msg = "B站风控拦截: 需要关注对方或对方设置了仅接收互关私信"
            elif code == 21002:
                msg = "发送私信过于频繁，请稍后再试"
            return {"success": False, "message": msg, "code": code}

    def get_at_notifications(self) -> list[dict]:
        """拉取 B 站通知中心谁 @ 了我"""
        url = "https://api.bilibili.com/x/msgfeed/at"
        resp = self._request(url)
        if resp.get("code") == 0:
            return resp.get("data", {}).get("items", [])
        return []

    def get_reply_notifications(self) -> list[dict]:
        """拉取 B 站通知中心收到的回复评论（谁回复了我）"""
        url = "https://api.bilibili.com/x/msgfeed/reply"
        resp = self._request(url)
        if resp.get("code") == 0:
            return resp.get("data", {}).get("items", [])
        return []

    def get_unread_sessions(self) -> list[dict]:
        """拉取最近的私信会话列表"""
        url = "https://api.vc.bilibili.com/session_svr/v1/session_svr/new_sessions?begin_ts=0&build=0&mobi_app=web"
        resp = self._request(url)
        if resp.get("code") == 0:
            return resp.get("data", {}).get("session_list", [])
        return []

    def get_session_messages(self, talker_id: int, size: int = 5) -> list[dict]:
        """拉取与指定用户 (talker_id) 的最近历史私信消息"""
        url = "https://api.vc.bilibili.com/svr_sync/v1/svr_sync/fetch_session_msgs"
        params = {
            "talker_id": int(talker_id),
            "session_type": 1,
            "size": int(size)
        }
        resp = self._request(url, params=params)
        if resp.get("code") == 0:
            return resp.get("data", {}).get("messages", [])
        return []

    def get_my_followers(self, page: int = 1, page_size: int = 20) -> list[dict]:
        """获取关注我的粉丝列表（按关注时间倒序排列）"""
        my_uid = self.config.get("auth", {}).get("dedeuserid", "")
        if not my_uid:
            return []
        url = f"https://api.bilibili.com/x/relation/followers?vmid={my_uid}&pn={page}&ps={page_size}&order=desc"
        resp = self._request(url)
        if resp.get("code") == 0:
            return resp.get("data", {}).get("list", [])
        return []

    def follow_user(self, fid: int) -> dict:
        """关注指定用户（互相关注）"""
        csrf = self.config.get("auth", {}).get("bili_jct", "")
        if not csrf:
            return {"success": False, "message": "未登录或缺少 csrf 凭证"}
        url = "https://api.bilibili.com/x/relation/modify"
        payload = {
            "fid": int(fid),
            "act": 1,
            "re_src": 11,
            "csrf": csrf
        }
        resp = self._request(url, method="POST", data=payload, headers={"Referer": f"https://space.bilibili.com/{fid}/"})
        code = resp.get("code")
        if code == 0 or code == 22014:
            return {"success": True, "message": "关注成功！"}
        return {"success": False, "message": resp.get("message", "关注失败"), "code": code}


    def upload_picture_to_bfs(self, image_path: str) -> dict:
        """上传本地图片到 B 站 BFS 动态图床"""
        if not os.path.exists(image_path):
            return {"success": False, "message": f"图片文件不存在: {image_path}"}
        csrf = self.config.get("auth", {}).get("bili_jct", "")
        if not csrf:
            return {"success": False, "message": "未登录或缺少 csrf 凭证"}

        url = "https://api.bilibili.com/x/dynamic/feed/draw/upload_bfs"
        headers = {
            "User-Agent": self.user_agent,
            "Cookie": self.get_cookie_header(),
            "Origin": "https://t.bilibili.com",
            "Referer": "https://t.bilibili.com/"
        }
        try:
            with open(image_path, "rb") as f:
                files = {"file_up": (os.path.basename(image_path), f, "image/jpeg")}
                data = {"category": "daily", "csrf": csrf}
                res = requests.post(url, files=files, data=data, headers=headers, timeout=20)
                resp = res.json()
                if resp.get("code") == 0:
                    d = resp.get("data", {})
                    return {
                        "success": True,
                        "image_url": d.get("image_url"),
                        "image_width": d.get("image_width"),
                        "image_height": d.get("image_height"),
                        "img_size": d.get("img_size")
                    }
                return {"success": False, "message": resp.get("message", "上传失败"), "code": resp.get("code")}
        except Exception as e:
            return {"success": False, "message": f"上传异常: {e}"}

    def post_picture_dynamic(self, text: str, image_path: str) -> dict:
        """发布带图片的 B 站动态"""
        csrf = self.config.get("auth", {}).get("bili_jct", "")
        if not csrf:
            return {"success": False, "message": "未登录或缺少 csrf 凭证"}

        up_res = self.upload_picture_to_bfs(image_path)
        if not up_res.get("success"):
            return {"success": False, "message": f"图片上传失败: {up_res.get('message')}"}

        url = "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/create_draw"
        headers = {
            "User-Agent": self.user_agent,
            "Cookie": self.get_cookie_header(),
            "Origin": "https://t.bilibili.com",
            "Referer": "https://t.bilibili.com/",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        pictures = [{
            "img_src": up_res["image_url"],
            "img_width": up_res["image_width"],
            "img_height": up_res["image_height"],
            "img_size": up_res["img_size"]
        }]
        data = {
            "biz": 3,
            "category": 3,
            "type": 0,
            "pictures": json.dumps(pictures),
            "description": text,
            "csrf": csrf,
            "csrf_token": csrf
        }
        try:
            res = requests.post(url, data=data, headers=headers, timeout=15)
            resp = res.json()
            if resp.get("code") == 0:
                dyn_data = resp.get("data", {})
                return {
                    "success": True,
                    "message": "动态发布成功！",
                    "dynamic_id": dyn_data.get("dynamic_id_str") or dyn_data.get("dynamic_id"),
                    "doc_id": dyn_data.get("doc_id")
                }
            return {"success": False, "message": resp.get("message", "发布动态失败"), "code": resp.get("code")}
        except Exception as e:
            return {"success": False, "message": f"发布动态异常: {e}"}


    # ==========================================
    # 专栏文章 (Articles / Columns) 模块
    # ==========================================
    def search_articles(self, keyword: str, page: int = 1, order: str = "click") -> list[dict]:
        """搜索专栏文章列表"""
        url = "https://api.bilibili.com/x/web-interface/search/type"
        params = {"search_type": "article", "keyword": keyword, "order": order, "page": page}
        res = self._request(url, params=params)
        if res.get("code") == 0:
            result = res.get("data", {}).get("result", [])
            articles = []
            for item in result:
                art_id = item.get("id") or item.get("mid")
                title = re.sub(r'<[^>]+>', '', item.get("title", ""))
                desc = re.sub(r'<[^>]+>', '', item.get("desc", ""))
                articles.append({
                    "id": art_id,
                    "cvid": f"cv{art_id}",
                    "title": title,
                    "desc": desc,
                    "author": item.get("author", "未知作者"),
                    "mid": item.get("mid", 0),
                    "view": item.get("view", 0),
                    "like": item.get("like", 0),
                    "reply": item.get("reply", 0),
                    "image_urls": item.get("image_urls", []),
                    "publish_time": item.get("pub_time", 0)
                })
            return articles
        return []

    def get_article_detail(self, cvid_or_id) -> dict:
        """获取专栏文章完整正文、段落、代码块、LaTeX公式与高清插图"""
        clean_id = str(cvid_or_id).lower().replace("cv", "")
        url_web = f"https://www.bilibili.com/read/cv{clean_id}/"
        headers = {
            "User-Agent": self.user_agent,
            "Referer": "https://www.bilibili.com/",
            "Cookie": self.get_cookie_header()
        }
        try:
            req = urllib.request.Request(url_web, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            return {"success": False, "message": f"拉取专栏页面失败: {e}"}

        init_match = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.+?\});", html)
        if not init_match:
            return {"success": False, "message": "未在专栏页面中找到状态数据"}

        try:
            init = json.loads(init_match.group(1))
            detail = init.get("detail", {})
            modules = detail.get("modules", [])
            title, author, mid = "", "", 0
            stats = {}
            paragraphs_text = []
            images = []

            for m in modules:
                m_type = m.get("module_type")
                if m_type == "MODULE_TYPE_TITLE":
                    title = m.get("module_title", {}).get("text", "")
                elif m_type == "MODULE_TYPE_AUTHOR":
                    author = m.get("module_author", {}).get("name", "")
                    mid = m.get("module_author", {}).get("mid", 0)
                elif m_type == "MODULE_TYPE_STAT":
                    stats = m.get("module_stat", {})
                elif m_type == "MODULE_TYPE_CONTENT":
                    for p in m.get("module_content", {}).get("paragraphs", []):
                        nodes = []
                        if isinstance(p.get("text"), dict):
                            nodes.extend(p.get("text", {}).get("nodes", []))
                        if isinstance(p.get("heading"), dict):
                            nodes.extend(p.get("heading", {}).get("nodes", []))
                        
                        para_words = []
                        for n in nodes:
                            if isinstance(n.get("word"), dict):
                                w = n.get("word", {}).get("words", "")
                                if w: para_words.append(w)
                            elif isinstance(n.get("formula"), dict):
                                f_latex = n.get("formula", {}).get("latex", "")
                                if f_latex: para_words.append(f" ${f_latex}$ ")
                        
                        if para_words:
                            paragraphs_text.append("".join(para_words).strip())
                        
                        if isinstance(p.get("code"), dict):
                            code_str = p.get("code", {}).get("code", "")
                            paragraphs_text.append(f"```\n{code_str}\n```")
                        
                        if isinstance(p.get("pic"), dict):
                            for pic in p.get("pic", {}).get("pics", []):
                                if pic.get("url"): images.append(pic.get("url"))

            content = "\n\n".join(paragraphs_text)
            return {
                "success": True,
                "id": clean_id,
                "cvid": f"cv{clean_id}",
                "title": title,
                "author": author,
                "mid": mid,
                "stats": stats,
                "content": content,
                "images": images,
                "url": url_web
            }
        except Exception as e:
            return {"success": False, "message": f"解析专栏内容异常: {e}"}

    def like_article(self, cvid_or_id) -> dict:
        """点赞专栏文章"""
        clean_id = str(cvid_or_id).lower().replace("cv", "")
        csrf = self.config.get("auth", {}).get("bili_jct", "")
        if not csrf:
            return {"success": False, "message": "未登录或缺少 csrf"}
        url = "https://api.bilibili.com/x/article/like"
        data = {"id": int(clean_id), "type": 1, "csrf": csrf}
        res = self._request(url, method="POST", data=data)
        if res.get("code") in [0, 65006]:
            return {"success": True, "message": "专栏点赞成功！" if res.get("code") == 0 else "专栏已点过赞"}
        return {"success": False, "message": res.get("message", "专栏点赞失败"), "code": res.get("code")}

    def send_article_reply(self, cvid_or_id, message: str) -> dict:
        """在专栏文章发布评论（专栏 reply type 为 12）"""
        clean_id = str(cvid_or_id).lower().replace("cv", "")
        csrf = self.config.get("auth", {}).get("bili_jct", "")
        if not csrf:
            return {"success": False, "message": "未登录或缺少 csrf"}
        url = "https://api.bilibili.com/x/v2/reply/add"
        data = {
            "oid": int(clean_id),
            "type": 12,
            "message": message,
            "csrf": csrf
        }
        res = self._request(url, method="POST", data=data)
        if res.get("code") == 0:
            return {"success": True, "message": "专栏评论发布成功！", "rpid": res.get("data", {}).get("rpid")}
        return {"success": False, "message": res.get("message", "发布专栏评论失败"), "code": res.get("code")}

    # ==========================================
    # 直播间 (Live Stream) 模块
    # ==========================================
    def get_live_room_info(self, room_id: int) -> dict:
        """获取直播间全景信息、开播状态、实时关键帧截屏"""
        url = "https://api.live.bilibili.com/room/v1/Room/get_info"
        res = self._request(url, params={"room_id": room_id})
        if res.get("code") == 0:
            data = res.get("data", {})
            return {
                "success": True,
                "room_id": room_id,
                "uid": data.get("uid"),
                "title": data.get("title", ""),
                "live_status": data.get("live_status", 0),
                "area_name": data.get("area_name", ""),
                "parent_area_name": data.get("parent_area_name", ""),
                "online": data.get("online", 0),
                "attention": data.get("attention", 0),
                "keyframe": data.get("keyframe", ""),
                "cover": data.get("user_cover", "") or data.get("cover", ""),
                "description": data.get("description", "")
            }
        return {"success": False, "message": res.get("message", "获取直播间失败")}

    def get_live_room_by_mid(self, mid: int) -> dict:
        """通过主播/用户 UID 查询其直播间 ID 与开播状态"""
        url = "https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld"
        res = self._request(url, params={"mid": mid})
        if res.get("code") == 0:
            d = res.get("data", {})
            return {
                "success": True,
                "room_id": d.get("roomid", 0),
                "live_status": d.get("liveStatus", 0),
                "url": d.get("url", ""),
                "title": d.get("title", "")
            }
        return {"success": False, "message": res.get("message", "查询主播直播间失败")}

    def get_followed_live_rooms(self, page: int = 1, page_size: int = 20) -> list[dict]:
        """获取当前正在开播的已关注主播/UP主列表（只看关注的主播！）"""
        url = "https://api.live.bilibili.com/relation/v1/feed/feed_list"
        params = {"page": page, "pagesize": page_size}
        res = self._request(url, params=params)
        if res.get("code") == 0:
            raw_list = res.get("data", {}).get("list", []) or []
            rooms = []
            for r in raw_list:
                rooms.append({
                    "room_id": r.get("roomid"),
                    "title": r.get("title", ""),
                    "uname": r.get("uname", "关注主播"),
                    "uid": r.get("uid"),
                    "online": r.get("online", 0),
                    "cover": r.get("cover") or r.get("face", ""),
                    "pic": r.get("pic", ""),
                    "link": r.get("link", f"https://live.bilibili.com/{r.get('roomid')}")
                })
            return rooms
        return []

    def get_hot_live_rooms(self, parent_area_id: int = 1, page: int = 1, page_size: int = 10) -> list[dict]:
        """获取热门直播间列表"""
        url = "https://api.live.bilibili.com/room/v3/area/getRoomList"
        params = {
            "platform": "web",
            "parent_area_id": parent_area_id,
            "page": page,
            "page_size": page_size
        }
        res = self._request(url, params=params)
        if res.get("code") == 0:
            raw_list = res.get("data", {}).get("list", [])
            rooms = []
            for r in raw_list:
                rooms.append({
                    "room_id": r.get("roomid"),
                    "title": r.get("title"),
                    "uname": r.get("uname"),
                    "uid": r.get("uid"),
                    "online": r.get("online", 0),
                    "area_name": r.get("area_name", ""),
                    "keyframe": r.get("keyframe", ""),
                    "cover": r.get("user_cover", "")
                })
            return rooms
        return []

    def get_live_recent_danmakus(self, room_id: int) -> list[dict]:
        """获取直播间最近的实时弹幕流"""
        url = f"https://api.live.bilibili.com/ajax/msg?roomid={room_id}"
        res = self._request(url)
        if res.get("code") == 0:
            raw_dms = res.get("data", {}).get("room", [])
            dms = []
            for d in raw_dms:
                dms.append({
                    "text": d.get("text", ""),
                    "nickname": d.get("nickname", "热心观众"),
                    "timeline": d.get("timeline", ""),
                    "uid": d.get("uid", 0)
                })
            return dms
        return []

    def send_live_danmaku(self, room_id: int, message: str, color: int = 16777215) -> dict:
        """在指定直播间发送实时打Call弹幕"""
        csrf = self.config.get("auth", {}).get("bili_jct", "")
        if not csrf:
            return {"success": False, "message": "未登录或缺少 csrf"}
        url = "https://api.live.bilibili.com/msg/send"
        data = {
            "roomid": int(room_id),
            "msg": message,
            "color": color,
            "fontsize": 25,
            "mode": 1,
            "rnd": int(time.time()),
            "csrf": csrf,
            "csrf_token": csrf
        }
        res = self._request(url, method="POST", data=data)
        if res.get("code") == 0:
            return {"success": True, "message": "直播弹幕发送成功！"}
        return {"success": False, "message": res.get("message", "发送直播弹幕失败"), "code": res.get("code")}

    def send_live_heartbeat(self, room_id: int) -> dict:
        """上报直播间在房心跳（挂机打卡、累积亲密度与经验）"""
        csrf = self.config.get("auth", {}).get("bili_jct", "")
        if not csrf:
            return {"success": False, "message": "未登录或缺少 csrf"}
        url = "https://api.live.bilibili.com/relation/v1/feed/heartBeat"
        data = {"room_id": int(room_id), "csrf": csrf}
        res = self._request(url, method="POST", data=data)
        return {"success": res.get("code") == 0, "message": res.get("message", "心跳已上报")}


if __name__ == "__main__":
    print("[Core] 正在初始化赛博养Gemini通信核心...")
    core = BiliHajimiCore()
    user = core.get_user_info()
    print(f"[Core] 登录状态: {'已登录' if user['is_login'] else '未登录'} | 用户名: {user['uname']}")
    vids = core.get_popular_videos(1, 2)
    print(f"[Core] 成功连接 B站，抓取到 {len(vids)} 条热门视频")
