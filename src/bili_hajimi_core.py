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
from pathlib import Path

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
QRCODE_PATH = PROJECT_ROOT / "images" / "qrcode_login.png"
JOURNALS_DIR = PROJECT_ROOT / "docs" / "journals"

JOURNALS_DIR.mkdir(parents=True, exist_ok=True)
QRCODE_PATH.parent.mkdir(parents=True, exist_ok=True)


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
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[Core] 读取配置失败: {e}")
        return {}

    def save_config(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
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

    def get_user_info(self) -> dict:
        resp = self._request("https://api.bilibili.com/x/web-interface/nav")
        if resp.get("code") == 0 and resp.get("data", {}).get("isLogin"):
            data = resp["data"]
            mid = data.get("mid", 0)
            uname = data.get("uname", "")

            # 若配置中尚未绑定主人 UID，自动同步绑定
            profile = self.config.setdefault("profile", {})
            if mid and (not profile.get("master_uid") or profile["master_uid"] == 0):
                profile["master_uid"] = mid
                profile["master_name"] = uname
                self.save_config()

            self.config["auth"]["is_logged_in"] = True
            return {
                "is_login": True,
                "mid": mid,
                "uname": uname,
                "vip": data.get("vipStatus", 0),
                "avatar": data.get("face", ""),
                "coins": data.get("money", 0),
            }
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

    # ==================== 评论与互动 ====================
    def post_comment(self, aid: int, message: str) -> dict:
        csrf = self.config.get("auth", {}).get("bili_jct", "")
        if not csrf:
            return {"success": False, "message": "未登录或缺少 csrf 凭证"}

        url = "https://api.bilibili.com/x/v2/reply/add"
        payload = {
            "type": 1,
            "oid": aid,
            "message": message,
            "csrf": csrf,
        }
        resp = self._request(url, method="POST", data=payload, headers={"Referer": f"https://www.bilibili.com/video/av{aid}"})
        if resp.get("code") == 0:
            return {"success": True, "message": "评论发布成功！", "data": resp.get("data")}
        else:
            return {"success": False, "message": resp.get("message", "发布失败"), "code": resp.get("code")}


if __name__ == "__main__":
    print("[Core] 正在初始化赛博养Gemini通信核心...")
    core = BiliHajimiCore()
    user = core.get_user_info()
    print(f"[Core] 登录状态: {'已登录' if user['is_login'] else '未登录'} | 用户名: {user['uname']}")
    vids = core.get_popular_videos(1, 2)
    print(f"[Core] 成功连接 B站，抓取到 {len(vids)} 条热门视频")
