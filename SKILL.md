---
name: loki-theme-kit
description: >
  Loki 的外观套组工坊：35 套现成的成套外观主题，一行接入就全部可用（自带悬浮切换器、记住选择）。
  给 Agent 用的话：跑一条命令就能自动认出宿主类型、把套组接进项目、并且回读验证。
  想自己挑就用画廊勾选；都不满意就用同一套方法从一张参考图做一套自己的。
  套组零图片依赖、不含任何人的 IP 形象，装饰位留成变量由你填自己的图。
  当用户说「换皮肤」「换主题」「UI 太单调」「做个外观主题」「把界面改成 XX 风格」「给界面加个主题切换」
  「按这张图做一套配色」「护眼主题」「深色/浅色主题」，或让你装/运行一个外观 Skill 时使用。
metadata:
  category: customization
  version: 1.1.0
  author: Loki
---

# Loki 外观套组工坊

35 套现成的成套外观主题。**装上就可用，一行接入；不满意就用同一套方法做自己的。**

不是色卡包。区别在两个字：**结构**。只改颜色不叫一套主题，那叫换色号——本套件用脚本
把这件事量化出数（`G4`：结构规则少于 6 条、规则行少于 12 行，直接判定为假主题）。

---

## 一、Agent 执行流程（主路径，不要问用户问题）

用户让你装/用这个 Skill 时，**直接跑，不要先问一堆问题**：

```bash
# 1. 接入（自动识别宿主类型、自动接线、自动回读验证）
python3 scripts/auto.py --project <用户的项目目录>

# 2. 看一眼输出：确认下面三行都是 ✓
#    ✓ 接入包含 35 套主题
#    ✓ script 标签在 <入口文件> 里
#    ✓ 接入包在 <路径>
```

就这样。`auto.py` 会替你做完：打接入包 → 认出 Next App Router / Vite / 纯 HTML →
把 `<script>` 插到正确位置（幂等，重复跑不会插两次）→ 改文件前留 `.loki-bak-*` 备份 →
回读验证。

**然后告诉用户一句话就够了**：

> 已经接好了：启动你的项目，页面右下角会出现「外观」按钮，35 套主题随便切，选择会被记住。
> 不想要了删掉那一行 script 即可。

### 装完**必须**交付一次（不做这一步就等于没装好）

用户装完只会看到"颜色变了"，他不会知道还能要到什么。所以装完必须主动交一次底：

1. **让提示页弹出来**：装完会生成 `<项目>/loki-themes/给你的用户.html` 并**自动用浏览器打开**
   （`auto.py` / `start.py` / `install.py` / `profile.py save` 都默认弹；不要弹加 `--no-open`）。
   这页把"还能要什么、说哪句话"一次说全 —— **别指望用户去翻文档**。
   Markdown 版 `给你的用户.md` 同目录，可以直接转发；`auto.py` 也会把精简版打到终端。
2. 说清**第一层（颜色）和第二层（整套 UI 部件）**的区别，并给他开口的那句话；
3. 告诉他"桌面应用重启会掉、怎么让它不掉"。

**三条底线**：数字要跟实际一致（几套就写几套，生成物里的数字是自动对齐的）；
不要把命令清单丢给用户；不要问一堆问题再动手。

### 用户只会说人话：对照表

**用户不会开终端，也不会粘命令。** 他自己跑的命令一律为零 —— 命令都是你跑，
他只负责说一句中文，你负责把结果用一句话告诉他。常见四句话对应的动作：

| 用户说 | 你做 | 结果 |
| --- | --- | --- |
| 「帮我换个皮肤 / 装个主题」 | `auto.py --project <他的项目>`（能改源码的）；改不了源码的桌面 App 走 `inject-cdp.py` + 适配器 | **只拿到颜色** —— 必须主动说清楚（见下面「两层」）| 
| 「颜色我有了，但侧栏/卡片/气泡这些 UI 部件也要跟着变」 | 走**结构件适配**：`probe.py` 出候选 → 定稿 `adapters/<宿主>/binding.json` → `adapt.py --triage --apply` → `--verify` → `--install`；完事 `profile.py save` 存档案 | 那套主题的**结构件真正落到他的界面上**（覆盖率有数）|
| 「我只要这几套，其余不要」 | `profile.py sets --name <档案> --only a,b,c` 然后 `profile.py restore --name <档案>`（源码型宿主：`auto.py --sets a,b,c`）| 其余套组从他的 Agent 上**走掉** |
| 「把外观恢复回来」（重启/升级之后） | `profile.py restore --name <档案>` | 自动重认失效角色→重新注入→回读报告 |
| 「这套我不要了」 | `profile.py drop --name <档案>` + 让他重载宿主（注入型的重启就没了）| 干净卸除 |
| 「我想自己新做一套」（给图或说风格） | `palette.py 图` 量色 → `new-theme.py --id … --palette 图` 起骨架 → 写 ≥6 条结构规则 → `check.py --only <id>` → `bundle.py --all --out <项目>/loki-themes` | 他自己的一套，能立刻用上 |
| 「就用这套，改一改」（沿用） | 复制 `sets/<id>` → 改 `meta.json` 的 `id`/`label` → 改 `theme.css` → `check.py --only <新id>` | 变成他自己的，原套不动 |
| 「把别人的主题搬进来」 | 放进 `sets/` + 补 `meta.json` + `bundle.py` 重新打包 | 并入，可切可选 |
| 「我不想每次都叫你，**打开就有**」 | `profile.py autostart`（装一个常驻守护）| 宿主一起来外观就自己回来了 |

### 必须说清楚的两层（诚实用语，照抄）

装完第一遍，只能给到**第一层**。要主动告诉用户，不要等他发现：

> 已经装好了，30 多套主题可以换。先说清楚：**这一步只换了配色和基本的字体圆角**。
> 具体到侧栏、卡片、气泡、代码块这些 UI 部件要不要跟着变成套主题的样子，是**另一层**，
> 得针对你的界面单独适配一遍。你要是想要，跟我说一句「**连 UI 部件也一起变**」，我来做。

做完第二层，也要告诉他代价（不要藏）：

> 这一层的效果是**按你的界面量身调的**，已经存成档案了。你的应用一升级，界面结构可能变，
> 那时候跟我说一句「**把外观恢复回来**」就行。

### 别让用户粘命令；但你要知道为什么不是你自己启动就行

你自己跑命令没问题，因为你在他机器上。但**两件事不要代他做**：

1. **不要静默改他的应用/项目**：源码型宿主改文件前必须留备份（`auto.py` 已内置）；
   要装开机自启的注入器、要重启他的宿主应用 —— **先问，得到中文同意再动**。
2. **不要为了好看卸掉他自己已有的皮肤**：宿主自带的皮肤系统要**共存 + 让位**，不要抢。

---

### 分情况

| 用户说 | 你做 |
| --- | --- |
| 「给我的 App 加个好看的外观」（默认） | `auto.py --project <目录>`（35 套全带） |
| 「只要几套 / 文件小一点」 | `auto.py --project <目录> --sets recommended`（10 套）或 `--sets loki-ease,loki-pop` |
| 「先看看有哪些」 | `python3 scripts/gallery.py && open previews/gallery.html`（勾选后导出清单） |
| 「不要悬浮按钮，只上主题」 | 加 `--no-switcher` |
| 「先别改我文件」 | 加 `--dry-run`（只打印会做什么） |
| 「自动的不好使 / 宿主很特殊」 | 用下面第二节的深度接入，或手工加一行 `<script src="…/loki-themes.js"></script>` |
| 「宿主是打包好的桌面 App，改不了源码」 | 走 CDP 注入：`bundle.py --adapter <宿主>` + `inject-cdp.py`，见 `adapters/README.md` |
| 「这 35 套都不喜欢，我想自己做」 | 走第四节 |

`auto.py` 找不到入口文件时会**明确报出来并给出手工那行代码**，不会假装成功（退出码 1）。

---

## 二、接入的两条路

| | 一行接入（默认） | 深度接入 |
| --- | --- | --- |
| 做什么 | 加一行 `<script>` | `@import` 一个 CSS + 给元素贴类名 |
| 效果 | 页面底色/文字/标题/链接/按钮/输入框 + 卡片等契约钩子 + 悬浮切换器 | 精确到卡片、侧栏、气泡、导航激活态… |
| 产出 | 1 个自包含 `loki-themes.js` | 每套一个 CSS + 切换器组件 + 参考宿主 |
| 命令 | `scripts/auto.py` / `scripts/bundle.py` | `scripts/install.py` |

一行接入产出的东西：
`<script src="./loki-themes/loki-themes.js"></script>`（放在 `<head>` 或 `<body>` 顶部）
→ 自带悬浮切换器、记住选择、删掉即还原。体积：35 套全带 **144 KB**，10 套 **54 KB**，
2 套 **22 KB**。

可选参数（写在 script 标签上）：`data-theme="loki-desk"`（首次用哪套）、
`data-switcher="off"`、`data-autotag="on"`（自动给常见元素贴契约类名，默认关）。

**深度接入**要人做三件事：`@import "./my-themes/index.css"` → `<html data-theme="…">` →
给元素挂契约类名。仅当用户要精确控制、或自动接入不适用时才走这条。

### 结构件怎么过（宿主的 DOM 里没有 `.loki-*` 钩子时）

先说清楚：**颜色和结构件是两层，过法不一样。**

- 颜色/圆角/字体/状态色 → 靠**令牌**接口，宿主是变量驱动的就全能过；
- 结构件（纸面纹理、贴纸圆边、撕口、计数器编号、扫描线、四角准星、气泡尾巴）
  → 挂在 `.loki-*` 语义钩子上，**普通宿主的 DOM 里没有这些钩子，会全部落空**。

落空了别去改 35 套主题（那是 35 遍），也别人肉一处处调：**给宿主的真实元素挂上钩子**。
每个宿主只需要一份角色对照表 `adapters/<宿主>/binding.json`。

```bash
python3 scripts/probe.py --port 9333 --dump /tmp/host-dom.json   # ① 盘点宿主，出角色候选
# ② 核一遍候选，定稿写进 adapters/<宿主>/binding.json（认不出的宁可不写）
python3 scripts/adapt.py --host <宿主> --port 9333 --check        # ③ 逐条实测匹配到几个
python3 scripts/adapt.py --host <宿主> --port 9333 --triage --apply  # ④ 隔离测试：哪个钩子会弄坏排版
python3 scripts/adapt.py --host <宿主> --port 9333 --verify       # ⑤ 结构件到了多少 + 硬数字
python3 scripts/adapt.py --host <宿主> --port 9333 --install --css <套组 css>   # ⑥ 挂上
```

**宿主升级之后**（用户只需要记这一条）：

```bash
python3 scripts/adapt.py --host <宿主> --port 9333 --refresh --apply
```

重新盘点 → 给失效的角色找新位置并实测 → 写回对照表（旧的存 `.json.bak`，留 `refresh_log`）。
不用等用户发现：`tagger.js` 里某个角色匹配不到元素时会往宿主控制台喊一句并说明跑 `--refresh`。

判定标准是算出来的：**整页有多少元素被改动、有没有元素被隐藏、哪个钩子接管了
`display/position/溢出`**。自动撤下的只有硬伤（藏元素 / 溢出改 hidden / 整页 >60% 尺寸大变）；
其余按「要人看一眼」列出来。撤下不是失败 —— 那个装饰位在这个宿主上是空的，
其它套不受影响。细节和真实数字见 `references/host-binding.md`。

做完之后**存一次档案**（`profile.py save`），以后不管是重启、升级还是换机器，
用户说一句「把外观恢复回来」，你跑 `profile.py restore` 就够了 ——
它会先清掉自己上一轮塞进去的东西（含旧一代的观察器与面板条目），再重新注入，
并且**先检查角色还认不认得**，变了就自动重认一遍。

### 开机自动恢复（用户不想每次都叫你）

改不了源码的宿主重启就掉，所以除了「叫一句 restore」，还可以装一个**常驻守护**：

```bash
python3 scripts/profile.py autostart              # 装（LaunchAgent，登录自启、常驻）
python3 scripts/profile.py autostart --status     # 看状态 + 最近日志
python3 scripts/profile.py autostart --off        # 卸掉（配置移到废纸篓，可恢复）
```

它每 5 秒巡检一次：宿主起来了、端口在、页面里没有我们的外观 → 自动注入回去。
三条纪律写在 `scripts/daemon.py` 顶上，最重要的一条是**不抢宿主自己的皮肤系统**：

- 用户现在选的是宿主自带的皮肤、而宿主那套样式还没进页面 → **等它先注**（我们抢先把
  标记打上，宿主自己的守护就会让位，用户反而会看到一套没有样式的皮肤）；
- 用户选的是我们的套组 → 注入，并把套组注册进宿主自己的外观面板；
- 清单改小、把用户当前选的那套剪掉了 → 自动回落到清单里的第一套（不然界面会掉样式）。

**改完 `daemon.py` 的代码要重启守护才生效**：`launchctl kickstart -k gui/$(id -u)/com.loki.theme-kit.restore`
（改的是磁盘上的文件，跑着的那份还是旧代码 —— 真踩过：修了 bug 却没反应，白等一轮。）

---

## 三、三条铁律

1. **不碰宿主的 IP 形象和品牌图。** 换外观只换壳，不重画角色、不替换品牌位、不生成
   "第二个吉祥物"。装饰件只有两个来源：宿主自己的，或使用者自己提供的。没有就留空。
   **35 套里没有任何图片文件。**
2. **"看着挺多、其实只是换色"必须被脚本检出。** 每套都要过 `scripts/check.py` 的 G4。
3. **可读性是硬门槛。** 正文/底 ≥ 7:1、辅助小字 ≥ 4.5:1、强调色上文字 ≥ 4.5:1。

另外：**改用户文件前先备份**（`auto.py` 已内置 `.loki-bak-*`），**幂等**（重复跑不出错，
不重复插标签）。改完必须回读验证，不要只看命令退出码。

---

## 四、用户想自己做一套主题时

顺序别换（这是从 35 套里磨出来的顺序）：

```bash
python3 scripts/palette.py 参考图.png        # ① 量色：别肉眼取，肉眼会漏掉面积最大的底
python3 scripts/new-theme.py --id my-x --label "我的X" --group art --palette 参考图.png   # ② 骨架
# ③ 写结构件：从 references/design-language.md 挑 2–4 个装置写进 theme.css（≥6 条规则/≥12 行）
python3 scripts/check.py --only my-x         # ④ 过六道门
python3 scripts/bundle.py --all --out <项目>/loki-themes   # ⑤ 重打接入包，新套组自动进包
```

**最容易走错的是第 ③ 步**：新手会一口气改 30 个颜色然后以为做了一套主题，G4 会拦下来。
辨识度来自形状，不来自色号。

---

## 五、目录

```text
loki-theme-kit/
├── SKILL.md                        ← 你在这里
├── README.md                       给人看的 30 秒说明
├── sets/                           35 套主题（每套 theme.css + meta.json）
│   ├── README.md                       套组文件格式
│   └── index.json / sources.json       索引 / 来源板
├── references/
│   ├── quickstart.md               5 分钟白话版（给人看，含名词对照表）
│   ├── host-contract.md            契约：44 个钩子 + 完整令牌表
│   ├── after-install.md            ★装完要交给用户的那段话 + 用户能要什么（单一来源）
│   ├── host-binding.md             ★结构件怎么过到别人家：角色绑定 + 隔离测试 + 跟着升级
│   ├── design-language.md          五族视觉语言 + 22 个结构装置配方
│   ├── quality-gates.md            六道门的阈值与理由
│   ├── asset-slots.md              装饰位机制（不含任何人的图）
│   ├── eyecare-rationale.md        护眼主题为什么是这些数
│   └── troubleshooting.md          10 个真实踩过的坑
├── scripts/
│   ├── auto.py                     ★Agent 主入口：无人值守接入 + 回读验证
│   ├── welcome.py                  ★装完自动弹给用户看的那一页（从 after-install.md 渲染）
│   ├── profile.py                  ★外观档案：存一次，重启/升级后一句话拿回来；autostart 装常驻守护
│   ├── daemon.py                   常驻守护：宿主一起来就把外观注回去（开机自动恢复）
│   ├── probe.py                    ★盘点别人的宿主，出结构件角色候选（草案）
│   ├── adapt.py                    ★结构件适配：check / triage / verify / render / install / refresh
│   ├── collect-dom.js              盘点器（在宿主页面里跑，只抓事实不下判断）
│   ├── inject-cdp.py               改不了源码的宿主：从外面注入（Electron/Chromium）
│   ├── start.py                    交互向导（给人用；默认也是一行接入）
│   ├── bundle.py                   打一行接入包
│   ├── install.py                  深度接入
│   ├── check.py                    六道质量门（有退出码）
│   ├── palette.py                  一张图 → 主色 + 令牌映射建议
│   ├── new-theme.py                新主题脚手架
│   ├── gallery.py                  预览画廊（搜索/分组/勾选/导出清单）
│   └── extract.py                  从混在一起的宿主 CSS 反抽套组
├── adapters/                       ★宿主适配器（把我们的令牌接到宿主的令牌上）
│   ├── README.md                       适配器怎么写 + Cola 实战结论与三个真问题
│   └── cola/adapter.json + extra.css + binding.json
│                                       Cola（Electron）：令牌映射 + 结构件的角色对照表
├── templates/                      主题模板 + 切换器 + tagger.js + 参考宿主 + 接入包三层
└── previews/
    ├── gallery.html                画廊
    ├── dropin/index.html           一行接入的示例页（本身零样式）
    └── demo/demo.html              深度接入的参考宿主
```

---

## 六、质检

```bash
python3 scripts/check.py     # 六道门；当前 35/35 通过；退出码 0=全过
```

六道门：令牌完整（G1）、正文/辅助对比度（G2）、强调色上文字对比度（G3）、
结构件数量防伪（G4）、护眼专项：禁纯白/禁纹理/禁动效（G5）、零素材依赖（G6）。
脚本管确定性，眼睛管布局与手感（导航有没有被挤出去、长段落累不累）——
见 `references/troubleshooting.md` 的自查清单。两者都做才算交付。

---

## 七、署名与边界

作者是 **Loki**，署名出现在技能名 `loki-theme-kit`、front matter、35 套主题的 id 前缀
`loki-`、画廊与演示页页脚、以及生成到别人项目里的 `README.md` 顶部。

- 35 套来自作者自己的桌面应用，**真实跑过**（不是概念图）；`meta.json` 里有结构件数量与
  实测对比度，`sources.json` 里有来源板。
- **不含作者的 IP 形象，也不含作者的像素装饰道具**：原素材位置已变成 `--deco-a: none`
  之类的槽位（只保留位置与尺寸），想挂什么由使用者决定。
- 别人想换成自己的标记：`--prefix th-` 换类名前缀；署名行在生成的 README 里单独一行。
