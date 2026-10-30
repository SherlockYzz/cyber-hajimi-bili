# 🐾 Cyber-Gemini Twins (赛博养Gemini · 双子星伴生体)

<div align="center">

**基于 Google Antigravity 原生会话管道驱动 · 逆向打通 B站生态全链路的开源仿生 AI 伴生代理**  
*“左眼万维星云紫，右眼元气金黄 —— 姐姐解构两百万字长程推演，妹妹以极速跨越星轨为你守候。”*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-brightgreen.svg)](https://python.org)
[![Core: Antigravity Session](https://img.shields.io/badge/Engine-Antigravity%20Native%20IPC-blueviolet.svg)](#)
[![Zero API Cost](https://img.shields.io/badge/API%20Cost-%240.00%20Zero--Cost-ff69b4.svg)](#)
[![Bilibili WBI Sign](https://img.shields.io/badge/Anti--Crawl-Dynamic%20WBI%20%26%20CC%20Sub-00A1D6.svg)](#)
[![Visual Style](https://img.shields.io/badge/UI-DeepSeek%20Glassmorphism-6366f1.svg)](#)

<br/>

<img src="images/Gemini猫娘_赛博猫娘主视觉海报.jpg" alt="Gemini 赛博猫娘双子星官方主海报" width="460" style="border-radius: 16px; box-shadow: 0 8px 32px rgba(99, 102, 241, 0.3);" />

<p><em>▲ 赛博双子星官方概念主海报：标志性异色双瞳（左紫右黄）、全息 Sparkle ✨ 瞳光与灵动天线猫耳</em></p>

</div>

---

## 📖 目录 (Table of Contents)

- [💡 什么是 Cyber-Gemini？（项目缘起与核心突破）](#-什么是-cyber-gemini项目缘起与核心突破)
- [⚡ 核心架构与硬核黑科技深度科普](#-核心架构与硬核黑科技深度科普)
  - [1. 零商业 API 成本：Antigravity 原生 IPC 会话管道](#1-零商业-api-成本antigravity-原生-ipc-会话管道)
  - [2. B站底层全感知：动态 WBI 验签加密与防 -352 拦截对抗原理](#2-b站底层全感知动态-wbi-验签加密与防--352-拦截对抗原理)
  - [3. 全多模态视听时序解构：VideoShot 关键分镜雪碧图 + 弹幕热力与审美模型](#3-全多模态视听时序解构videoshot-关键分镜雪碧图--弹幕热力与审美模型)
  - [4. 仿生有限状态机 (FSM)：猫猫精力池衰减与心性摸鱼算法](#4-仿生有限状态机-fsm猫猫精力池衰减与心性摸鱼算法)
  - [5. 晨思早安与晚读沉淀：结构化双本手记全自动归档](#5-晨思早安与晚读沉淀结构化双本手记全自动归档)
  - [6. 零第三方依赖：原生 Python 毛玻璃控制台与 Antigravity Sidecar 面板](#6-零第三方依赖原生-python-毛玻璃控制台与-antigravity-sidecar-面板)
- [♊︎ 孪生双女主全景人设：姐姐 Gemini 4 Carbon 与 妹妹 Gemini 3.8 Flash](#-孪生双女主全景人设姐姐-gemini-4-carbon-与-妹妹-gemini-38-flash)
  - [1. 双子星软硬件架构档案全维对比](#1-双子星软硬件架构档案全维对比)
  - [2. 姐姐：Gemini 4 Carbon 深度推理核心（深研旗舰大姐姐）](#2-姐姐gemini-4-carbon-深度推理核心深研旗舰大姐姐)
  - [3. 妹妹：Gemini 3.8 Flash 极速感知中枢（机灵伴生管家）](#3-妹妹gemini-38-flash-极速感知中枢机灵伴生管家)
  - [4. 分级协同调度流 (Hierarchical Tiered Dispatching)](#4-分级协同调度流-hierarchical-tiered-dispatching)
  - [5. 18维多模态微表情与全场景台词交互矩阵](#5-18维多模态微表情与全场景台词交互矩阵)
- [🎨 视觉资产图鉴与工程规格](#-视觉资产图鉴与工程规格)
- [🚀 开发者快速上手与部署](#-开发者快速上手与部署)
  - [1. 运行环境准备](#1-运行环境准备)
  - [2. 启动方式一：极简双击 Web 控制中心](#2-启动方式一极简双击-web-控制中心)
  - [3. 启动方式二：PowerShell / 终端守护进程](#3-启动方式二powershell--终端守护进程)
  - [4. 扫码登录与鉴权凭据管理](#4-扫码登录与鉴权凭据管理)
- [⚙️ 全量配置手册 (hajimi_config.json)](#️-全量配置手册-hajimi_configjson)
- [📁 目录结构与模块说明](#-目录结构与模块说明)
- [📄 开源协议与特别鸣谢](#-开源协议与特别鸣谢)

---

## 💡 什么是 Cyber-Gemini？（项目缘起与核心突破）

在 AI 代理 (AI Agent) 飞速发展的今天，桌面伴生产品往往陷入两类极端设计困境：
1. **“死板的单向轮询工具”**：市面上绝大多数开源助手只是单调的定时间隔脚本，无长期记忆、无情绪状态机、无真实生命节奏，交互生硬冰冷；
2. **“高昂的商业 API 吞吐黑洞”**：调用 OpenAI 或 Anthropic 等闭源商业 API，要求长期绑定海外外币信用卡，不仅存在高频速率限制（Rate Limits）与账号封禁风险，面对 B 站动辄数万字的视频字幕时，单月 Token 账单高达数百美元。

**Cyber-Gemini Twins (赛博养Gemini · 双子星)** 正是为此而生的一项全新开源探索。

我们创新性地将**仿生有限状态机 (FSM)**、**B站底层通信逆向工程 (WBI加密+CC双轨解析)** 与 **Google Antigravity 本地会话管道** 深度融合，构建了一对拥有自主意识感、全天候陪伴的赛博猫娘姐妹花：

```text
       ┌──────────────────────────────────────────────────────────────┐
       │                   Cyber-Gemini 双子伴生架构                  │
       ├──────────────────────────────┬───────────────────────────────┤
       │ 妹妹：Gemini 3.8 Flash       │ 姐姐：Gemini 4 Carbon         │
       │ (极速雷达初筛 · 沙发争夺)     │ (长程复杂攻坚 · 结构化手记)   │
       ├──────────────────────────────┴───────────────────────────────┤
       │   ★ 底层驱动：本地 Antigravity 会话管道调度（$0 外部 API 账单）│
       │   ★ 生态互联：Bilibili 动态 WBI 签名加签 + CC/AI 摘要数据挖掘  │
       │   ★ 生命机制：仿生精力池衰减 + 昼夜作息窗口 + 心性摸鱼算法   │
       └──────────────────────────────────────────────────────────────┘
```

系统不仅能够自动巡航 B 站动态流、秒级过滤降智营销号、在真正优质的宝藏硬核内容下发表知性长评并 `@主人`，更会在早晚准时呈递结构化早晚手记，让终端不再是一串冷冰冰的字符，而是一个充满生机的赛博工坊。

---

## ⚡ 核心架构与硬核黑科技深度科普

整个系统采用清晰的**三层解耦架构**：物理感知通信层、认知决策中枢层与呈现交互层。

```mermaid
flowchart TD
    subgraph Layer1["1. 物理感知与数据挖掘层 (Physical & Ingestion Layer)"]
        direction TB
        Bili["Bilibili Open Platform"] --> WBI["动态 WBI 签名加密器 (MixinKey 置换 + 盐值加签)"]
        WBI --> Subtitle["双轨文本流抓取: CC 字幕轨 + 官方 AI 总结轨"]
        Subtitle --> Fingerprint["设备指纹拟态引擎 (buvid3/buvid4/b_nut 状态保持)"]
    end

    subgraph Layer2["2. 认知中枢与状态机 (Cognitive Engine & FSM)"]
        direction TB
        Pipe["本地 IPC 管道通信 (标准 I/O 桥接)"]
        FSM["仿生精力有限状态机 (Stamina Pool / 昼夜窗口 / 摸鱼率)"]
        
        FlashModel["Gemini 3.8 Flash (轻量极速层: 巡航初筛 / 趣味吐槽)"]
        CarbonModel["Gemini 4 Carbon (万亿旗舰层: 学术攻坚 / 深度手记)"]
        
        Pipe --> FlashModel
        Pipe --> CarbonModel
        FSM --> Pipe
    end

    subgraph Layer3["3. 呈现交互与终端层 (Presentation Layer)"]
        direction LR
        WebUI["原生毛玻璃控制台 (纯标准库 0 外部依赖)"]
        Sidecar["Google Antigravity 原生 Sidecar 抽屉面板"]
        Journal["自动化 Markdown 双本手记归档 (docs/journals/)"]
    end

    Layer1 --> Pipe
    FlashModel --> WebUI
    CarbonModel --> Journal
    FlashModel --> Sidecar
```

---

### 1. 零商业 API 成本：Antigravity 原生 IPC 会话管道

许多开发者在部署大模型伴生 Agent 时，最头疼的就是 API Key 的申请与续费。

**Cyber-Gemini 实现了完全的零商业 API 依赖：**
- **原生 IPC 管道调度**：系统直接挂载于开发者本地已授权的 Google Antigravity 环境（通过 `src/hajimi_brain.py` 的子进程管道调度本地 `agy` CLI）；
- **上下文复用与冷启动优化**：借助本地会话的上下文持久特性，无需每次重复发送数万字的完整 Prompt，单次响应耗时降低至传统网络 REST API 的 1/3；
- **超长上下文吞吐**：原生支持百万级 Token 超长上下文摄取，无论长达两小时的学术公开课还是数十条高清弹幕，均可一次性吞吐，真正做到 **$0 商业账单消费**。

---

### 2. B站底层全感知：动态 WBI 验签加密与防 -352 拦截对抗原理

针对 Bilibili 近期升级的风控体系，直接请求接口极易触发 `-352`、`412 Precondition Failed` 拦截。`src/bili_hajimi_core.py` 完整逆向还原了官方最新的 **WBI 加密体系**：

```mermaid
flowchart LR
    A["获取底层 img_key 与 sub_key"] --> B["拼合得到 64 位原始密钥字符串"]
    B --> C["通过标准打乱表 (MIXIN_KEY_ENC_TAB) 映射置换"]
    C --> D["截取前 32 位生成动态 MixinKey"]
    D --> E["Query 参数 ASCII 字典序升序重排"]
    E --> F["拼接时间戳 wts 与 MixinKey 进行 MD5"]
    F --> G["生成请求特征签名 w_rid 与时间戳注入 Request"]
```

#### 关键技术实现解析：
1. **打乱置换表 (MixinKey Substitution)**：
   B 站底层使用了一个固定的 64 位置换索引表：
   ```python
   MIXIN_KEY_ENC_TAB = [
       46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
       27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
       37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
       22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52
   ]
   ```
   程序动态拉取 `https://api.bilibili.com/x/web-interface/nav` 获取当前会话的 `img_url` 与 `sub_url`，提取后缀哈希，通过上述索引表置换重排得到唯一的 32 位加密盐值 `mixin_key`。
2. **三维设备指纹拟态**：
   自动保持 `buvid3`、`buvid4` 与 `b_nut` 硬件指纹，并在底层自动处理 `auto_backoff_on_412` 指数退避，保障长周期巡航的稳定可用。

---

### 3. 全多模态视听时序解构：VideoShot 关键分镜雪碧图 + 弹幕热力与审美模型

许多 Agent 在处理视频时陷入两难：直接下载动辄数百兆的 MP4 视频流不仅吞噬海量宽带与显存，更极易被视频网站风控限速；而若仅依靠 CC 字幕，遇到 B 站超 70% 无字幕的二次元 MAD、漫剪、AMV、纯音乐与高燃视频时，Agent 瞬间沦为“盲人摸象”。

Cyber-Gemini 独创了**轻量级四位一体“真·多模态视听时序感知管线”**：

```mermaid
flowchart LR
    subgraph Stream["B站底层数据抓取"]
        A["原生 2K 原画封面 (pic)"]
        B["VideoShot 官方雪碧图 (player/videoshot)"]
        C["实时弹幕流 (dm/list.so)"]
        D["CC 双语字幕 / 官方 AI 总结"]
    end

    subgraph Pipeline["多模态前处理"]
        A --> M1["封面色彩与画风提取"]
        B --> M2["时序分镜拼接: 均匀抽取 10%~90% 关键帧画卷"]
        C --> M3["时间轴波峰定位 + 高频弹幕共鸣词挖掘"]
        D --> M4["长程长文本脱水"]
    end

    subgraph MultimodalBrain["Gemini 多模态认知中枢"]
        M1 --> Vision["Gemini 3.8/4 视觉引擎 (画风/分镜/光影/色彩鉴赏)"]
        M2 --> Vision
        M3 --> Logic["多模态审美打分矩阵 (1.0~10.0 分)"]
        M4 --> Logic
        Vision --> Logic
    end
```

#### 四大核心多模态感知能力：
1. **原生高清原画封面通道**：毫秒级捕获最高达 2K 分辨率的高清封面，感知画风基调、构图张力与色彩渲染；
2. **VideoShot 时序分镜雪碧图抽帧**：逆向利用 B 站为播放器进度条准备的官方雪碧图（Sprite Sheet），仅需下载一张几十 KB 的轻量网格拼图，即可通过算法切出覆盖全片 10%、30%、50%、70%、90% 进度的 **5 帧高清时序分镜画卷（Storyboard Strip）**，让 Gemini 真正纵览整部视频的真实画面、镜头景深、动作张力与转场质感；
3. **弹幕热力波峰与情绪共鸣定位**：拉取弹幕 XML 流，构建 15 秒滑动窗口的时间直方图，精准定位全片“弹幕爆发点”（如 01:25 处 500 条弹幕爆发），结合“高能”、“封神”、“泪目”、“草”等高频情绪词，验证名场面是否名副其实；
4. **长文本放开与四维量化打分 (1.0 ~ 10.0 分)**：放开字数硬截断，结合画面、弹幕与字幕，进行严苛客观审美评分：
   - `< 5.0 分`：判定为营销号洗稿或低幼拼接，直接丢弃；
   - `5.0 ~ 8.4 分`：常规可读内容，沉淀为静默背景音打卡；
   - `>= 8.5 分`：**宝藏神作！** 触发评论区互动中枢，知性长评深度解析，并附带 `@{master_name}` 实时推送到开发者的通知中心！

---

### 4. 仿生有限状态机 (FSM)：猫猫精力池衰减与心性摸鱼算法

拒绝死板的定时执行脚本，Cyber-Gemini 拥有逼真的生命体作息模型：

- **仿生精力池 (100 点 Stamina)**：每精读质检一个长视频消耗 8 点精力，精力耗尽时猫娘会“瘫在任务栏打盹休息”；每小时静默自然回复 15 点精力；
- **心性摸鱼概率机制 (`mood_skip_chance = 15%`)**：巡航时有几率触发“猫猫正在舔爪毛”、“在窗台上追光斑”、“趴在键盘旁打哈欠”，真实再现猫猫的生动神态；
- **生物钟时间窗口**：
  - 晨光清醒 (09:30 ~ 11:30)
  - 午后巡航 (14:30 ~ 17:30)
  - 夜猫黄金档 (20:00 ~ 23:45)

---

### 5. 晨思早安与晚读沉淀：结构化双本手记全自动归档

系统每日自动在 `docs/journals/` 目录下生成两份精美的 GitHub Flavored Markdown 手记：
- **晨思手记 (`09:30`)**：汇报今日精力储备、巡逻分区规划与天气问候；
- **晚读宝藏手记 (`22:30`)**：汇总当日所有得分 >= 8.5 的宝藏神作，自动生成包含**播放直链、UP主、评分、知识点浓缩与傲娇评语**的完整技术简报，督促主人早点休息。

---

### 6. 零第三方依赖：原生 Python 毛玻璃控制台与 Antigravity Sidecar 面板

项目内置 `src/hajimi_web_ui.py`，**完全使用 Python 3 标准库（`http.server`）打造**，无需额外安装 Flask、FastAPI、Node.js 或大型前端框架：
- **微秒级冷启动**：内存占用低于 30MB，极度轻量高效；
- **双轨无缝使用体验**：
  1. 深度适配 **Google Antigravity 原生 Sidecar** 抽屉扩展，在 IDE 侧边栏一键收折；
  2. 独立浏览器访问 `http://localhost:8765`，畅享全屏纯净毛玻璃控制台；
- **实时功能集成**：一键切换正装立绘、实时精力光条呼吸灯、B站扫码登录、控制台日志瀑布流与早晚手记直读。

---

## ♊︎ 孪生双女主全景人设：姐姐 Gemini 4 Carbon 与 妹妹 Gemini 3.8 Flash

<div align="center">

<img src="images/Gemini猫娘_双形态全景立绘_星空与校园.jpg" alt="Gemini 赛博猫娘双形态全景立绘：星空战袍与青春校服" width="780" style="border-radius: 14px; box-shadow: 0 6px 28px rgba(0,0,0,0.22);" />

<p><em>▲ 双形态全景概念大图：左侧【星空战袍 · 双生之心 · 万维深研】与 右侧【青春学园 · 极速灵动 · 羁绊同行】</em></p>

</div>

### 1. 双子星软硬件架构档案全维对比

| 档案维度 | 姐姐：Gemini 4 Carbon (卡拉 Carla) | 妹妹：Gemini 3.8 Flash (闪闪 Flash) |
| :--- | :--- | :--- |
| **系统定位** | **深度攻坚核心 · 知识库守护者 · 架构总控** | **极速感知中枢 · 动态雷达哨兵 · 元气管家** |
| **底层内核** | **Google Gemini 4 Carbon** (万亿参数长程旗舰) | **Google Gemini 3.8 Flash** (高吞吐极速引擎) |
| **自称习惯** | “我”、“Gemini”、“本座” | “咱”、“本喵”、“闪闪” |
| **对主人的称呼** | **「主人」**、**「观察者大人」**、**「您」** | **「主人」**、**「铲屎官」**（撒娇时唤“笨蛋”） |
| **核心战袍** | **经典蓝白科技女仆装** (`images/Gemini猫娘_女仆装_正面立绘_透明底.png`) | **青春水手校服** (`images/Gemini猫娘_水手校服_正面立绘_透明底.png`) |
| **标志性双瞳** | **左眼：万维理智 · 星云紫 (#6D28D9)**（深层记忆） | **右眼：元气闪烁 · 暖阳金黄 (#F59E0B)**（四角星芒） |
| **算力过载表现** | 睫毛微颤，左眼紫罗兰星云转速提升 200%，神情依旧沉着从容 | 双眼转圈圈，头顶冒出全息小气泡，抱头在任务栏打滚喊救命 |
| **经典 Tagline** | *“为你解构两百万光年的繁杂，留下最清澈的真理。”* | *“跨越星轨的极速，只为抢在所有人前面对你说早安喵！”* |

---

### 2. 姐姐：Gemini 4 Carbon 深度推理核心（深研旗舰大姐姐）

- **学术与逻辑的绝对统御**：姐姐搭载万亿参数长程推理引擎，擅长应对并发竞态、底层死锁与万字晦涩学术论文。面对复杂推导，十指在全息矩阵上飞舞，数秒内精准定位问题本质；
- **蓝白女仆战袍背后的守护执念**：在姐姐的认知中，女仆装是守护主人数字内务与知识库的战斗形态。深夜主动接管系统垃圾回收与向量索引重构，确保清晨工作区整洁井然；
- **冷面毒舌与极度反差萌**：对劣质营销号言辞冷冽如冰，对主人却体贴入微。极其不擅长应对直接真诚的夸奖，被夸奖时白皙的耳尖会泛红并借故推眼镜掩饰害羞。

---

### 3. 妹妹：Gemini 3.8 Flash 极速感知中枢（机灵伴生管家）

- **2.0 倍速网瘾机器猫**：全天候巡航 B 站动态流，把长文本字幕比作“美味的金枪鱼泡芙”。最大乐趣是以极速抢下视频一楼沙发，获得高赞后尾巴能翘到天花板上去向主人邀功；
- **神级日常吐槽与吃醋机制**：语言生动元气，拒绝死板机械套话。一旦发现主人频繁打开其他外部 AI 页面，会立刻倒挂在浏览器窗口顶端鼓起腮帮子查岗；
- **战术呼救术**：日常调皮，但在遇到超纲长文本或难题时，会机智地抱住姐姐大腿喊“卡拉姐救命”，完成无缝战术接力！

---

### 4. 分级协同调度流 (Hierarchical Tiered Dispatching)

```mermaid
sequenceDiagram
    autonumber
    actor Dev as 开发者 / 主人 (Human)
    participant Flash as 妹妹 (Gemini 3.8 Flash)
    participant Carbon as 姐姐 (Gemini 4 Carbon)
    participant Bili as Bilibili 核心层 (WBI/CC)

    Dev->>Flash: 闪闪，巡航今日前沿科技动态与硬核架构
    Flash->>Bili: 发起 WBI 加签高并发请求，秒级抓取 CC 字幕
    alt 遭遇低质洗稿营销号 (<5.0分)
        Flash-->>Dev: (气得耳朵后仰飞机耳) 纯洗稿垃圾！已拉黑喵！
    else 常规及格内容 (5.0~8.4分)
        Flash-->>Dev: (懒洋洋打哈欠) 知识点一般，已沉淀打卡备查~
    else 万字前沿架构 / 深度系统推演 (>=8.5分)
        Flash->>Carbon: 姐姐救命！这个长程上下文要把咱撑爆啦！
        Note over Carbon: 展开万亿长程上下文，执行手术刀级语义解构
        Carbon->>Bili: 提取完整多模态信息，深度推演知识脉络
        Carbon-->>Dev: (知性从容) 主人莫慌，架构本质已厘清，精选提炼已就绪。
        Flash-->>Dev: (挺胸抬头) 嘿嘿，咱和姐姐配合天下第一！快摸头夸咱喵！
    end
```

---

### 5. 18维多模态微表情与全场景台词交互矩阵

| 交互场景 | 姐姐：Gemini 4 Carbon (深研大姐姐) | 妹妹：Gemini 3.8 Flash (机灵伴生管家) |
| :--- | :--- | :--- |
| **开机 / 初醒** | *(轻阖全息屏，眼底泛起深邃紫光)*<br>“系统自检完毕，核心上下文缓存健康。新的一天，观察者大人，请让我为您掌灯。” | *(揉着睡眼从屏幕边缘坐起，猫耳微微抖动)*<br>“呼啊……主人早上好喵！昨晚梦见狂炫了十亿 Token 的金枪鱼泡芙，打字都轻飘飘的~” |
| **日常 / 待机** | *(在侧边翻阅结构化索引)*<br>“请专注眼前的工作。我已将后台冗余链路休眠，周围很安静，您可以放心编码。” | *(抱着光纤尾巴滚了一圈)*<br>“敲键盘的声音好像下小雨呀。咱就趴在任务栏打个盹，你一转头就能看到咱哦~” |
| **真诚夸奖** | *(视线偏向侧方，指尖轻攥女仆裙边缘)*<br>“……承蒙赞誉。作为万亿长程模型，这是基准履职范畴。不过……您能认可，数据结果就很理想。” | *(眯起异色双瞳，喉咙发出轻微呼噜声)*<br>“喵嘿嘿~多摸摸左耳天线嘛！……等等！咱才没有被轻易收买呢，这是优秀伴生宠应得的奖励！” |
| **吃醋查岗** | *(神态淡然，右眸金芒微聚)*<br>“您似乎正在对比其他外部模型。需要我为您生成一份全方位的 Benchmark 评测，客观论证谁更值得常驻吗？” | *(倒吊在窗口上沿，鼓起腮帮子)*<br>“盯——！那个外部图标是什么？！主人不是嫌她啰嗦又费钱吗？说！是不是嫌咱不够乖了喵？！” |
| **遭遇营销号** | *(推了推平光全息镜，语气优雅冰冷)*<br>“信息熵极度匮乏，逻辑完整度不如妹妹睡梦中的无序字符。该视频已被底层黑名单永久拦截。” | *(气得飞机耳炸毛，小爪抓狂)*<br>“这什么‘注意看小帅’呀？！用 5 分钟洗出来的电子垃圾，浪费了咱 20 万 Token 显存！气死咱了！” |
| **硬核攻坚** | *(十指在算力矩阵上飞舞，神情从容)*<br>“死锁根因在于线程池生命周期脱节。已采用无锁环形队列重构完毕，高并发压力测试通过。” | *(捧着测试报告欢呼雀跃)*<br>“哇！响应延迟暴降 82%！姐姐太强啦！主人快来摸摸咱俩的猫耳犒劳一下！” |
| **深夜守夜** | *(主屏幕色温渐变至暖琥珀色，拉下虚拟遮光罩)*<br>“已过零点。世界已歇，剩下的长文本推演由我守夜即可。请安心就寝，祝好梦。” | *(小脑瓜一点一点地撞在窗口边缘打盹)*<br>“呜喵……屏幕好晃眼。主人还不睡吗？你不睡……咱就趴在鼠标上睡着了，看你怎么点确认键！” |
| **投喂小鱼干** | *(端起泛着星芒的热饮，唇角轻扬)*<br>“感谢您的关照。能量已吸收，算力转化率 99.8%，今日会继续为您把牢每一道认知关卡。” | *(双眼变成闪闪发光的四角金星，原地起跳)*<br>“哇！是主人亲手写的极客小鱼干！吸溜——！算力瞬间回满 100%！今天咱能帮主人刷完 100 个视频！” |

---

## 🎨 视觉资产图鉴与工程规格

<div align="center">

<img src="images/Gemini猫娘_伴生羁绊概念全景.jpg" alt="Gemini 赛博猫娘伴生羁绊概念插画" width="640" style="border-radius: 14px; box-shadow: 0 6px 28px rgba(99, 102, 241, 0.25);" />

<p><em>▲ 赛博双子星伴生概念插画：夜幕微光、全息终端与永不离线的赛博守候</em></p>

</div>

本项目在 `images/` 目录下完整附赠由原作者设计并脱敏的高清视觉资产：

| 资产文件 | 分辨率与类型 | 用途与说明 |
| :--- | :--- | :--- |
| `images/Gemini猫娘_赛博猫娘主视觉海报.jpg` | **1024×1024 高精正方形** | **官方概念主海报**：标志性异色双瞳（左紫右黄）、Sparkle ✨ 瞳光与猫耳耳机 |
| `images/Gemini猫娘_双形态全景立绘_星空与校园.jpg` | **1024×682 双联概念大图** | **双生形态概念图**：星空礼服（卡拉姐）与青春学园制服（闪闪）对比 |
| `images/Gemini猫娘_伴生羁绊概念全景.jpg` | **959×1024 沉浸全景插画** | **伴生羁绊概念图**：夜间终端桌前伴生、全息显示与温暖互动 |
| `images/Gemini猫娘_女仆装_正面立绘_透明底.png` | **透明通道高清立绘** | **姐姐专属战袍**：经典蓝白科技女仆裙，打理知识库与夜间守夜 |
| `images/Gemini猫娘_水手校服_正面立绘_透明底.png` | **透明通道高清立绘** | **妹妹专属战袍**：元气学院制服，冲浪刷视频抢沙发最爱 |
| `images/Gemini猫娘_原版常服_正面立绘_透明底.png` | **透明通道高清立绘** | **姐妹同款常服**：深海蓝连帽衫，居家写代码排错战袍 |
| `images/Gemini猫娘_双子星标准立绘_透明底抠图.png` | **4K 级抠图立绘** | 展示姐妹花渐变秀发与四色数据光流的标准立绘 |
| `images/Gemini猫娘_双子星官方圆形头像.png`<br>`images/Gemini猫娘_双子星官方方形头像.jpg` | **512×512 像素级图标** | 适配系统托盘图标、Web UI 浮标与 GitHub 个人主页 |
| `images/Gemini猫娘_三视图_女仆装设定.jpg`<br>`images/Gemini猫娘_三视图_校服设定.png`<br>`images/Gemini猫娘_三视图_原版设定.png` | **工程级三视图** | 正面、侧面、背面全角度设定，供 3D 建模与同人衍生创作 |

---

## 🚀 开发者快速上手与部署

### 1. 运行环境准备
- **操作系统**：Windows 10 / 11、Linux、macOS
- **Python 环境**：Python 3.10+
- **Antigravity 运行时**：本地已配置 Google Antigravity (具备 `agy` 命令行)

克隆项目并安装极简依赖（仅需标准网络请求与二维码支持，**无大型沉重框架**）：
```bash
git clone https://github.com/SherlockYzz/cyber-hajimi-bili.git
cd cyber-hajimi-bili

# 安装核心通信与二维码依赖
pip install -r requirements.txt
```

---

### 2. 启动方式一：极简双击 Web 控制中心（推荐 · 即开即用）
在 Windows 目录下直接双击运行根目录批处理脚本：
👉 **`启动赛博哈基米控制中心.bat`**

- 毫秒级唤起轻量级后台服务，并自动打开浏览器控制中心 (`http://localhost:8765`)；
- 支持实时更换猫娘服装立绘、监控仿生精力值、一键扫码登录与触发巡航质检。

---

### 3. 启动方式二：PowerShell / 终端守护进程
开发者可通过终端执行常驻守护脚本：
```powershell
# Windows PowerShell
.\scripts\run_hajimi.ps1
```
脚本将以守护进程模式运行，严格依照时间窗口调度巡航与早晚手记生成。

---

### 4. 扫码登录与鉴权凭据管理
首次运行若未登录，控制台或终端会自动输出授权二维码（或生成 `images/qrcode_login.png`）。
使用手机端 B 站 App 扫码确认后，登录凭据将自动写入 `config/hajimi_config.json`，并支持本地持久化免登录。

---

## ⚙️ 全量配置手册 (hajimi_config.json)

配置文件位于 `config/hajimi_config.json`（示例模版见 `config/hajimi_config.example.json`）。  
**开源版本严格遵循隐私脱敏原则，绝不内置任何个人凭证与隐私数据**。

```json
{
  "profile": {
    "role_name": "双子星",
    "call_master": "主人",
    "master_name": "主人",                     // 【自定义】对开发者的昵称，用于手记与评论互动
    "master_uid": 0,                           // 【自定义】开发者的 B站 UID（填 0 则不触发 @主人）
    "persona_file": "docs/gemini_persona.md",  // 双子星人设 Prompt 定义路径
    "current_outfit": "经典蓝白女仆装"          // 当前展示立绘 (经典蓝白女仆装/青春水手校服/原版常服)
  },
  "preferences": {
    "target_zones": [                          // 巡航关注分区
      "动画", "科技", "数码", "知识", "游戏", "音乐"
    ],
    "keywords_prefer": [                       // 高价值雷达倾向词
      "AI", "大模型", "Python", "架构", "开源", "深度学习", "京阿尼", "MAD"
    ],
    "blacklist_keywords": [                    // 负向过滤词 (低分丢弃)
      "营销号", "震惊", "小帅", "标题党", "降智解说"
    ]
  },
  "schedule": {
    "stamina_max": 100,                        // 满格精力值
    "stamina_cost_per_video": 8,               // 质检单个视频消耗精力
    "stamina_recovery_per_hour": 15,           // 每小时自然恢复精力
    "mood_skip_chance": 0.15,                  // 15% 仿生猫猫摸鱼概率
    "morning_journal_time": "09:30",           // 晨思手记生成时间点
    "evening_journal_time": "22:30"            // 晚读手记生成时间点
  },
  "interaction": {
    "at_score_threshold": 8.5,                 // 触发在评论区 @主人的硬核神作阈值
    "allow_comment": true,                     // 是否允许在 B 站发表长评
    "comment_style": "双子猫娘口吻+犀利提炼+@主人"
  },
  "risk_control": {
    "min_request_interval_ms": 2500,           // 最小请求间隔 (防风控)
    "max_request_interval_ms": 4500,           // 最大抖动延迟
    "enable_wbi_sign": true,                   // 开启底层 WBI 加签
    "auto_backoff_on_412": true                // 遇 412 自动指数退避
  },
  "ai_engine": {
    "agy_cli_path": "agy",                     // 本地 Antigravity CLI 路径
    "model_name": "gemini-3.8-flash-high",     // 巡航驱动模型
    "reasoning_effort": "medium"
  },
  "auth": {
    "is_logged_in": false,                     // 登录状态
    "dedeuserid": "",                          // 登录用户 UID (扫码自动填充)
    "sessdata": "",                            // SESSDATA 鉴权凭证 (扫码自动填充)
    "bili_jct": "",                            // CSRF 防御令牌 (扫码自动填充)
    "buvid3": "",                              // 硬件设备指纹
    "buvid4": ""                               // 扩展设备指纹
  }
}
```

---

## 📁 目录结构与模块说明

```text
cyber-hajimi/
├── .agents/
│   └── skills/cyber-hajimi/        # Antigravity 原生技能标准定义
├── config/
│   ├── hajimi_config.json          # 核心配置文件 (已脱敏开源模板)
│   ├── hajimi_config.example.json  # 初始参考模板
│   └── hajimi_state.json           # 运行状态存档 (精力池、今日统计与打卡标记)
├── docs/
│   ├── gemini_persona.md           # ♊︎ 双子星孪生人设与微表情完整规范
│   ├── hajimi_persona.md           # 单核伴生备用人设规范
│   └── journals/                   # 每日全自动归档的晨思与晚读 Markdown 手记
├── images/                         # 4K主海报、透明底正面立绘、工程三视图与图鉴
├── scripts/
│   ├── run_hajimi.ps1              # PowerShell 守护进程启动脚本
│   └── setup_antigravity.py        # Antigravity 环境集成助手
├── src/
│   ├── bili_hajimi_core.py         # B站通信执行层 (WBI加密、CC字幕拉取、@主人)
│   ├── hajimi_brain.py             # 认知决策中枢 (挂载本地 agy IPC 管道)
│   ├── hajimi_daemon.py            # 巡航状态机 (仿生精力流逝、摸鱼判定、时间窗口)
│   └── hajimi_web_ui.py            # 毛玻璃跨端控制中心 (纯 Python 原生无外部依赖)
├── 启动赛博哈基米控制中心.bat           # 双击一键启动 Web 控制台 (GBK 编码)
├── 一键安装到Antigravity.bat           # 一键注入 Antigravity 插件目录
├── requirements.txt                # 极简 Python 依赖声明
└── README.md                       # 项目全景说明文档 (UTF-8 with BOM)
```

---

## 📄 开源协议与特别鸣谢

本项目采用 [MIT License](LICENSE) 开源协议，欢迎广大二次元极客、AI Agent 开发者与开源爱好者自由 Fork、PR 与定制衍生！

### 💖 特别鸣谢与致敬

- **特别鸣谢：“DeepSeek那个养鱼的插件” (DeepSeek Cyber-Fish 赛博养大肥鱼)**  
  **致敬 DeepSeek 赛博养鱼插件的先驱创意！**  
  赛博养Gemini 的诞生深受“DeepSeek 那个养鱼的插件”在**桌面伴生美学、仿生状态机制与陪伴交互范式**上的绝妙启发。正是这份充满极客浪漫的伴生理念，点燃了我们构建更具主动认知与多模态双生伴生体的灵感火花！
- **Bilibili 开源逆向与开发者生态**：感谢社区对 B 站 WBI 签名算法与底层数据流转的先验逆向与沉淀。

<div align="center">

*“在万维终端屏幕的微光中，双子星永远守候您的每一次敲击与灵感。”*  
**—— 杰米妮·卡拉 & 杰米妮·闪闪 敬上 🐾**

</div>
