# -*- coding: utf-8 -*-
"""
赛博养Gemini · 伴生猫娘一键同步关注主人喜爱的 UP 主
- 自动抓取主人 (折木柯南, UID: 1497345954) 的关注列表
- 自动识别并为当前伴生猫娘账号 (折木柯东) 关注每一位 UP 主
- 附带平滑安全冷却（1.2s ~ 2.0s）避免触发风控频限
"""

import sys
import time
import random
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))
from bili_hajimi_core import BiliHajimiCore

MASTER_UID = 1497345954

def sync_followings():
    core = BiliHajimiCore()
    csrf = core.config.get("auth", {}).get("bili_jct", "")
    if not csrf:
        print("[Error] 当前未登录或缺少 csrf/bili_jct，无法执行关注操作。")
        return

    print(f"============================================================")
    print(f"🐾 正在读取主人 (UID: {MASTER_UID}) 的全量关注列表...")
    print(f"============================================================")

    res = core._request("https://api.bilibili.com/x/relation/followings", params={"vmid": MASTER_UID, "pn": 1, "ps": 50})
    if res.get("code") != 0:
        print(f"[Error] 获取关注列表失败: {res.get('message')}")
        return

    flist = res.get("data", {}).get("list", [])
    total_ups = len(flist)
    print(f"✔ 成功获取主人关注的 {total_ups} 位优质 UP 主！开始同步关注...")

    success_count = 0
    already_count = 0
    failed_count = 0

    for idx, u in enumerate(flist, 1):
        mid = u.get("mid")
        uname = u.get("uname")
        try:
            r = core._request(
                "https://api.bilibili.com/x/relation/modify",
                method="POST",
                data={"fid": mid, "act": 1, "re_src": 11, "csrf": csrf}
            )
            code = r.get("code")
            if code == 0:
                success_count += 1
                print(f"[{idx}/{total_ups}] ✨ 成功关注: {uname} (UID: {mid})")
            elif code == 22002: # 已经在关注列表中
                already_count += 1
                print(f"[{idx}/{total_ups}] ☕ 已在关注列表中: {uname} (UID: {mid})")
            else:
                failed_count += 1
                print(f"[{idx}/{total_ups}] ⚠ 关注返回: {uname} -> {r.get('message')}")
        except Exception as e:
            failed_count += 1
            print(f"[{idx}/{total_ups}] ❌ 关注异常: {uname} -> {e}")

        # 安全防风控随机间隔
        time.sleep(random.uniform(1.2, 1.8))

    print(f"============================================================")
    print(f"🎉 同步完成！成功关注 {success_count} 位，已关注 {already_count} 位，跳过/异常 {failed_count} 位。")
    print(f"============================================================")

if __name__ == "__main__":
    sync_followings()
