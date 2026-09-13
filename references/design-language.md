# 设计语言与结构装置目录

做新主题时照这张表挑装置。**令牌决定"什么颜色"，装置决定"像什么"。** 一套主题挑
2–4 个装置、写够 ≥6 条规则 / ≥12 行，才越过了"换色"那条线。

## 一、五族视觉语言（35 套的分布）

### 1. 护眼纸墨（`care` 组 · 3 套）
`loki-ease` 纸墨·日 / `loki-ease-dark` 纸墨·夜 / `loki-moss` 雾苔

这一族**故意不华丽**，目标只有一个：让人能对着屏幕写三小时代码/文章。做法：
纸面相对亮度控制在 0.72–0.86（不用纯白）、正文对比 7–12:1（不追 21:1 极值，太硬）、
辅助小字 ≥4.5:1、行高 1.85、行宽 38rem（中文约 40 字）、正文衬线、**零纹理零噪点零动效**。
任何新做的"阅读主题"都必须先跟这三套对齐指标，否则不算护眼，只是浅色。

### 2. 贴纸波普（`art` 组主力）
`loki-pop` / `loki-die` / `loki-sticker` / `loki-nine` / `loki-egg` / `loki-guide` / `loki-manual` / `loki-wall`

2–3px 纯黑描边 + 右下硬投影（`box-shadow: 3px 3px 0`、不用模糊）+ 高饱和强调色。
圆角、白圈刀线、贴歪一点点是它的招牌。

### 3. 像素复古（`retro` 组）
`loki-8bit` / `pixel-arcade` / `loki-sandbox` / `loki-terminal` / `loki-neon` / `loki-vapor` / `loki-desk`

圆角归零、`image-rendering: pixelated`、等宽字体、扫描线/点阵底纹。老式桌面那套（`loki-desk`）
单独一条规矩：**立体感只给窗口部件**（标题栏、按钮斜角、输入框下沉），内容卡片一律平底细线。

### 4. 印刷刊物（`art` 组另一半）
`retro-poster` / `urban-collage` / `poster-stream` / `sky-cinema` / `loki-butter`

瑞士国际主义与活版报纸那一脉：圆角归零、纯黑框线、CSS 计数器编号（`01/02/03`）、
正文分栏（`column-width: 19rem`）、首字下沉、上下 double 粗线、全大写报头 + 拉宽字距。

### 5. 极简工具（`calm` 组）
`loki-atlas` / `loki-blueprint` / `loki-indigo` / `loki-wire` / `loki-navkit`

制图/仪器感：四角准星、网格底、等宽坐标标签、毛玻璃、细到 1px 的分割线。
`loki-wire`「线框稿」是这一族的极端形态——卡片是**未填充的虚线框**，整个界面像设计稿。

## 二、结构装置目录（可直接抄的配方）

### 卡片形状

| 装置 | 配方 | 用在 |
| --- | --- | --- |
| 圆角归零 | `--radius-panel: 0; --radius-control: 0;` | 包豪斯/像素/印刷族 |
| 贴纸圆边 + 白圈 | `border: 3px solid #fff; border-radius: 18px; outline: 1px dashed rgba(0,0,0,.38); outline-offset: 3px;` | `loki-sticker` `loki-die` `loki-wall`（实测带 3px 白边） |
| 模切刀线 | 上面那条 + `transform: rotate(-.3deg)`（奇偶项反向） | `loki-die` |
| 大圆角悬浮 | `--radius-panel: 22px;` + `--shadow-soft` 带一点扩散 | `loki-neon` |
| 直角 + 左上实心定位块 | `border-radius:0; border:2px solid #000;` + `::before{position:absolute;top:0;left:0;width:14px;height:14px;background:#d8232a}` | `loki-bauhaus` `loki-butter` |

### 边框与投影

| 装置 | 配方 | 用在 |
| --- | --- | --- |
| 粗墨线 + 硬投影 | `border: 2px solid var(--loki-ink); box-shadow: 3px 3px 0 var(--loki-ink);` | `loki-pop` 全族 |
| 双层描边 | 外层 3px 实色 + 内层 1px 细线（`outline-offset`） | `loki-8bit` `loki-sandbox` |
| 发丝线 | `border: 1px solid var(--border-subtle);` 且 `--shadow-*: none` | 极简工具族 |
| 顶端色条 | `border-top: 4px solid <accent>` | `loki-manual` `loki-nine` |
| 撕口 | `background-image: radial-gradient(circle at 0 50%, var(--bg-canvas) 6px, transparent 6px)` 左右各一 | `loki-ticket` |

### 角标与编号

| 装置 | 配方 | 用在 |
| --- | --- | --- |
| CSS 计数器编号 | `.page{counter-reset:c}` + 卡片 `counter-increment:c` + `::before{content:counter(c,decimal-leading-zero)}` | `loki-butter` `loki-console` `loki-guide` `loki-manual` `loki-sandbox` `retro-poster` |
| 四角准星 | 四个 `::before/::after` + `background: linear-gradient(...)` 画十字，11px | `loki-atlas` `loki-indigo` `loki-nine` `loki-egg`（这四个里有 `width: 11px`） |
| 左上编号方块 | `position:absolute;top:10px;left:12px;display:grid;place-items:center;width:20px;height:20px` | `loki-manual` `loki-sandbox` |
| 别针 | 卡片顶部中央一个 12px 圆点（`margin-left:-6px` 居中）+ 一点投影 | `loki-wall`（实测） |

### 分组与前置符号

| 装置 | 配方 | 用在 |
| --- | --- | --- |
| 彩色分组标签 | `.nav-group-label{background:var(--nav-tone-*);color:#fff;border-radius:999px}` | `loki-pop` `loki-sticker` |
| 数字编号前缀 | `::before{content:"01 "}` （分组内计数） | `loki-butter` `loki-console` |
| 终端符号 | 消息 `>`、用户 `$`、文件树 `\|--`、分组 `// LABEL` | `loki-terminal` |
| 点阵标记 | 分组标题前 3×3 或九点阵 | `loki-nine` `loki-egg` |
| 等宽大写 | `font-family:var(--font-mono);text-transform:uppercase;letter-spacing:.18em` | `loki-atlas` `loki-bauhaus` `loki-blueprint` `loki-butter` `loki-manual` `loki-terminal` `loki-ticket` `loki-wire` `urban-collage`（实测大写+拉宽字距） |

### 激活态

| 装置 | 配方 | 用在 |
| --- | --- | --- |
| 实心块 | `background:var(--text-primary);color:var(--bg-surface)` | `loki-wire` `loki-pop` |
| 左侧粗条 | `box-shadow: inset 3px 0 0 var(--accent-copper)` | `loki-manual` `loki-wall` |
| 下划线标签页 | `border-bottom: 3px solid` + 无底色 | 当前 35 套无使用者（配方留着） |
| 折角 | 右上角三角 `clip-path` / `border-width` 技巧 | `loki-rose` |
| 荧光笔 | 背景做成一条高亮带（`linear-gradient(transparent 55%, <accent> 55%)`） | `sky-cinema`（实测 `transparent 55%`） |

### 内容区与侧栏

| 装置 | 配方 | 用在 |
| --- | --- | --- |
| 均衡器条 | `repeating-linear-gradient(90deg, <accent> 0 3px, transparent 3px 10px)` + `background-size: 100% 14px` + `repeat-x` | `loki-sticker`（实测 `transparent 3px 10px`） |
| 会话竖线 | `.chat-stream{border-left:2px solid rgba(...) }` + 每段节点圆点 | `loki-wall` `pixel-arcade`（实测） |
| 界格线 | `repeating-linear-gradient(0deg, ... 3rem)` 竖格 | 水墨类（已删，配方留着） |
| 扫描线 + 暗角 | `repeating-linear-gradient` 细横线 + `radial-gradient` 边缘压暗 | `loki-terminal`（全套 10 处伪元素，装置最密的一套） |
| 侧栏换色 | `.loki-sidebar{background:var(--bg-metal)}` + `--sidebar-text` 单独一套 | `loki-rose`（唯一浅粉侧栏）、`loki-mint` |
| 窄柱居中 | `main > div{max-width:50rem;margin:0 auto}` | `loki-indigo` `loki-butter`（实测 `max-width: 50rem`） |

### 字体与字距

| 装置 | 配方 | 用在 |
| --- | --- | --- |
| 标题换家族 | `--font-display: "Marker Felt","Kaiti SC",cursive` | `loki-mint` `loki-wall` |
| 折角/异形 | `clip-path` 切角 | `loki-egg`（35 套里唯一用 `clip-path` 的） |
| 等宽大写 | `--font-display: "SF Mono","Menlo",monospace` + `letter-spacing: .16em` | `loki-wire` `loki-terminal` |
| 首字下沉 | `.paper > p:first-of-type::first-letter{float:left;font-size:3.2em;line-height:.9}` | 当前 35 套无使用者（配方留着；原先用它的活版报纸套组已删） |
| 斜体铬字 | `font-style:italic; text-shadow: 0 0 8px <accent>, 2px 2px 0 <ink>` | `loki-vapor` |

## 三、做一套新主题：推荐组合方式

一个不会翻车的组合法：**从五族里选一族定基调 → 从装置目录挑 2–4 个 → 换令牌 → 过门**。

| 你想要的 | 建议组合 |
| --- | --- |
| 长时间写代码/写字 | 护眼纸墨族基调 + 顶部色条 + 左侧粗条激活态（别碰纹理和动效） |
| 可爱/轻松 | 贴纸波普族 + 贴纸圆边 + 彩色分组标签 + 圆点别针 |
| 硬核/机能 | 像素复古族 + 圆角归零 + 等宽大写 + 扫描线 |
| 文艺/杂志感 | 印刷刊物族 + 计数器编号 + 首字下沉 + 全大写报头 |
| 冷静/专业 | 极简工具族 + 发丝线 + 四角准星 + 等宽标签 |

**别一次上五个装置。**35 套里最耐看的几套（`loki-ease`、`loki-desk`、`loki-nine`）
结构件都在 8–17 条之间，而堆到 40 条的那几套（`sky-cinema`、`urban-collage`）
是"特定心情才想开"的类型——两类都需要，但要清楚自己在做哪一类。
