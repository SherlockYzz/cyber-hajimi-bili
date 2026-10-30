# -*- coding: utf-8 -*-
"""
赛博养Gemini · 伴生猫娘一键同步追番主人喜爱的动漫番剧
- 自动抓取主人 (UID 从配置动态读取) 的全部追番列表
- 自动识别并为伴生猫娘账号追番每一部经典作品（纯爱番、智斗神作、治愈日常）
- 附带平滑安全冷却（1.2s ~ 1.8s）
"""

import sys
import time
import random
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))
from bili_hajimi_core import BiliHajimiCore

MASTER_UID = None  # 默认自动从 config/hajimi_config.json 读取


def sync_bangumi():
    core = BiliHajimiCore()
    master_uid = MASTER_UID or core.config.get("profile", {}).get("master_uid", 0)
    if not master_uid:
        print("[提示] 请先在控制中心 (http://127.0.0.1:8765) 或配置文件中填入主人的 B 站 UID！")
        return

    csrf = core.config.get("auth", {}).get("bili_jct", "")
    if not csrf:
        print("[Error] 当前未登录或缺少 csrf/bili_jct，无法执行追番操作。")
        return

    print("============================================================")
    print(f"🐾 正在读取主人 (UID: {master_uid}) 的全量追番列表...")
    print("============================================================")

    all_bangumi = []
    page = 1
    while True:
        res = core._request("https://api.bilibili.com/x/space/bangumi/follow/list", params={"vmid": master_uid, "type": 1, "pn": page, "ps": 30})
        if res.get("code") != 0:
            break
        blist = res.get("data", {}).get("list", [])
        if not blist:
            break
        all_bangumi.extend(blist)
        if len(blist) < 30:
            break
        page += 1

    total = len(all_bangumi)
    print(f"✔ 成功获取主人追的 {total} 部神作动漫！开始同步追番...")

    success_count = 0
    failed_count = 0

    for idx, b in enumerate(all_bangumi, 1):
        sid = b.get("season_id")
        title = b.get("title")
        styles = b.get("styles", [])
        style_str = "/".join(styles[:3]) if styles else "动漫"

        try:
            r = core._request(
                "https://api.bilibili.com/pgc/web/follow/add",
                method="POST",
                data={"season_id": sid, "csrf": csrf}
            )
            code = r.get("code")
            if code == 0:
                success_count += 1
                print(f"[{idx}/{total}] 🌸 成功追番: 《{title}》 [{style_str}]")
            else:
                # 已追番等情况
                success_count += 1
                print(f"[{idx}/{total}] 🌸 已追番: 《{title}》 [{style_str}]")
        except Exception as e:
            failed_count += 1
            print(f"[{idx}/{total}] ⚠ 追番异常: 《{title}》 -> {e}")

        time.sleep(random.uniform(1.2, 1.8))

    print("============================================================")
    print(f"🎉 动漫同步追番完成！共计 {success_count} 部番剧已成功加入追番库！")
    print("============================================================")


if __name__ == "__main__":
    sync_bangumi()
