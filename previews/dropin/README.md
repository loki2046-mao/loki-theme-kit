# 35 套外观主题（单文件接入包）

> 来自 **Loki 外观套组工坊（loki-theme-kit）** —— 作者 Loki · 可自由使用与改造。

## 怎么用：一行

把这一行加进你页面的 `<head>`：

```html
<script src="./loki-themes.js"></script>
```

完。你的页面立刻有外观主题，右下角会出现一个「外观」按钮，点开可以切
35 套，选择会被记住（换浏览器/清缓存才会重置）。

## 可选的参数（都写在那个 script 标签上）

```html
<!-- 首次打开用某套；之后以用户的选择为准 -->
<script src="./loki-themes.js" data-theme="loki-desk"></script>

<!-- 不显示悬浮按钮，只上主题（那就要自己切 data-theme） -->
<script src="./loki-themes.js" data-switcher="off"></script>

<!-- 自动给常见元素贴契约类名（默认关；开了效果更足，但会往你的 DOM 加 class） -->
<script src="./loki-themes.js" data-autotag="on"></script>
```

## 它做了什么 / 没做什么

**做**：注入一份样式表（页面底色／文字／标题字体／链接／按钮／输入框／选中色／滚动条，
以及你选的每一套主题）；把 `data-theme` 设到 `<html>`；放一个悬浮切换器；记住选择。

**没做**：不改你的布局（不动 margin/padding/宽高），不碰你的品牌形象和头像，
不删改你的任何文件。**不想要了就删掉那一行**——一切都回原样。

## 想要更深的接入（推荐给正式项目）

接入包给的是"立刻能看到变化"。要让主题作用到卡片、侧栏、气泡这些具体元素上，
用 `scripts/install.py` 那套：单独引每套 CSS + 给元素挂契约类名
（见 `references/host-contract.md`）。两者可以同时用：接入包负责"立刻好看"，
契约负责"精确控制"。

## 包含的套组

- 纸墨·日（loki-ease）
- 纸墨·夜（loki-ease-dark）
- 雾苔（loki-moss）
- 贴纸波普（loki-pop）
- 包豪斯（loki-bauhaus）
- 孟菲斯（loki-memphis）
- 创作台（loki-console）
- 九宫格（loki-nine）
- 导航件（loki-navkit）
- 模切贴纸（loki-die）
- 彩蛋（loki-egg）
- 沙盘（loki-sandbox）
- 线框稿（loki-wire）
- 音乐贴纸（loki-sticker）
- 现场手册（loki-manual）
- 留言墙（loki-wall）
- 入场指南（loki-guide）
- 薄荷手账（loki-mint）
- 黄油海报（loki-butter）
- 玫瑰纸片（loki-rose）
- 通行证票根（loki-ticket）
- 拼贴（urban-collage）
- 海报（retro-poster）
- 涂鸦（doodle-studio）
- 展流（poster-stream）
- 老式桌面（loki-desk）
- 蒸汽波（loki-vapor）
- 像素冒险（loki-8bit）
- 像素（pixel-arcade）
- 终端绿（loki-terminal）
- 霓虹电台（loki-neon）
- 蓝图（loki-blueprint）
- 导览图（loki-atlas）
- 靖蓝夜色（loki-indigo）
- 天空（sky-cinema）
