# 宿主契约（host contract）

套组是 CSS，但它得知道"该装饰谁"。这份契约就是那层约定：**你的 App 里挂上这些类名，
35 套主题就能直接作用上去**；少挂几个不会报错，只是少几处效果。

类名前缀默认 `loki-`（作者的项目名）。想换成自己的前缀：

```bash
python3 scripts/install.py --only <套组> --prefix th- --out ./my-themes
# 生成的选择器变成 .th-surface / .th-nav-item …，语义完全一样
```

## 核心层（缺了主题就基本没效果）

| 契约类名 | 挂在哪 | 它是什么 | 被多少套主题用到 |
| --- | --- | --- | --- |
| `.loki-surface-strong` | 主卡片 / 面板 | 最"重"的容器，主题辨识度主要靠它 | 31 / 35 |
| `.loki-button-primary` | 主按钮 | 主操作按钮 | 31 / 35 |
| `.loki-nav-item` | 侧栏每一个导航项 | 导航条目 | 30 / 35 |
| `.loki-sidebar` | 侧栏根节点 | 整条侧栏（很多主题会单独给它配色） | 30 / 35 |
| `.loki-nav-item-active` | 当前所在的导航项 | 激活态 | 30 / 35 |
| `.loki-paper` | 消息 / 内容纸片 | 一"张"内容 | 28 / 35 |
| `.loki-surface` | 普通容器 | 比 strong 轻一档的卡片 | 26 / 35 |
| `.loki-composer` | 输入区外壳 | 底部输入框那一条 | 25 / 35 |
| `.loki-button-secondary` | 次按钮 | 次要操作 | 23 / 35 |
| `.loki-chat-stream` | 内容滚动区 | 消息流所在的滚动容器 | 22 / 35 |

## 识别层（决定这套主题长得像什么）

| 契约类名 | 挂在哪 | 它是什么 |
| --- | --- | --- |
| `.loki-header-sticker` | 页面标题旁的道具位 | 装饰槽（图片由你用 `--deco-*` 或直接放 `<img>`） |
| `.loki-nav-group-label` | 侧栏分组标题 | 「工作台 / 知识 / 简报 / 系统」这类分组名 |
| `.loki-nav-group-dot` | 分组标题前的小点 | 分组色标 |
| `.loki-nav-icon` | 导航项里的图标容器 | 图标底座 |
| `.loki-empty-hero` | 空状态大卡 | 没有内容时的欢迎区 |
| `.loki-bubble-user` / `.loki-bubble-assistant` | 两种气泡 | 你说的话 / 系统说的话 |
| `.loki-conversation-item` / `-active` | 会话列表项 | 左侧会话列表 |
| `.loki-workbench-toolbar` | 工具条 | 页面顶部工具条 |
| `.loki-context-panel` | 侧边信息面板 | 右侧上下文面板 |
| `.loki-input` | 输入控件 | 文本框本体 |
| `.loki-page` | 页面根节点 | 页面级容器（做编号/计数器时用） |
| `.loki-sticker-title` / `.loki-sticker` | 标题 / 贴纸 | 贴纸语言专用（见 design-language） |
| `.loki-tint-success` / `-warning` / `-danger` | 提示条 | 三色语义提示块 |
| `.loki-code-block` | 代码块 | 代码区域 |
| `.loki-theme-swatch` / `-active` | 主题选择器的色卡 | 只在做切换器时用到 |

完整清单（44 个钩子）在 `sets/index.json` 的 `host_hooks` 字段里，每套主题用了哪几个
写在它自己的 `meta.json` 里。

## 令牌契约（主题真正的地基）

一套主题必须提供这些 CSS 变量（`scripts/check.py` 的 G1 会检查缺没缺）：

| 令牌 | 用途 |
| --- | --- |
| `--bg-canvas` | 页面最底层的底 |
| `--bg-surface` | 卡片面 |
| `--bg-elevated` / `--bg-paper` / `--bg-canvas-soft` | 更亮的面 / 纸片 / 次底 |
| `--bg-metal` | 侧栏（或"金属件"）的底 |
| `--text-primary` / `--text-secondary` / `--text-muted` | 正文 / 次要 / 辅助小字，三档对比度分别有门槛 |
| `--accent-copper` / `--accent-copper-deep` | 强调色及其深一档 |
| `--accent-ink` | **压在强调色上的文字色**（按钮字色，最容易被忽略、最容易翻车） |
| `--border-subtle` / `--border-active` | 细边框 / 激活边框 |
| `--state-running` / `-success` / `-warning` / `-danger` | 四种状态色 |
| `--radius-panel` / `--radius-control` | 圆角（这是"结构件"的第一根杠杆） |
| `--shadow-soft` / `--shadow-panel` | 投影 |
| `--font-display` / `--display-weight` / `--display-spacing` | 标题字体 / 字重 / 字距 |
| `--sidebar-*` | 侧栏前景/悬停/激活/分割线的独立一套 |
| `--nav-tone-*` | 导航分组各自的色（不给就跟随强调色） |
| `--canvas-texture` `--canvas-noise` `--canvas-ambient` `--canvas-mark` `--surface-highlight` `--surface-glow` | 材质层：纹理/噪点/环境光/水印/高光。**护眼套组必须全是 `none`** |

## 把一个已有 App 接上契约（三步）

1. **挂类名**：在你现有组件上补契约类名，不动原有样式。比如
   `<div class="my-card loki-surface-strong">`、`<a class="my-nav loki-nav-item">`。
   只补不加效果也没关系——不装主题时它们是空钩子。
2. **放主题名**：`document.documentElement.dataset.theme = id`。
3. **引样式**：`@import "./my-themes/index.css";`。

三步做完，`data-theme` 一换，整套外观就换了。你的 App 原有的类名和样式一律不动。

## 为什么不做成"自动适配任意 App"

因为做不到诚实。CSS 主题要么作用于**已知的钩子**，要么就得靠 `!important` 去硬砸
别人的样式——后者在真实项目里是灾难（改坏别人布局、升级即碎）。契约这一层看起来多
了一步，但它换来的是：**主题永远只作用于你允许它碰的地方**，出事范围可控、可回滚。
