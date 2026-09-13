# 已装套组：35 套（契约前缀 `loki-`）

> 来自 **Loki 外观套组工坊（loki-theme-kit）** —— 作者 Loki · 可自由使用与改造。

## 你需要做的三件事

1. 引样式（在你的全局 CSS 或入口里加一行）：

   ```css
   @import "./loki-themes/index.css";   /* 路径按你实际放置位置改 */
   ```

2. 在页面根元素上给主题名：`<html data-theme="loki-sticker">`。切换就是改这个属性，
   存哪都行（localStorage / 用户设置 / Cookie）；可选主题的清单看 `themes.json`。

3. 给你 App 里的元素挂契约类名。本次装进来的套组会用到：

   - `.loki-loki-avatar`
   - `.loki-loki-brand-mark`
   - `.loki-loki-brand-name`
   - `.loki-loki-brand-sub`
   - `.loki-loki-bubble-assistant`
   - `.loki-loki-bubble-user`
   - `.loki-loki-button-primary`
   - `.loki-loki-button-secondary`
   - `.loki-loki-chat-canvas`
   - `.loki-loki-chat-sidebar`
   - `.loki-loki-chat-stream`
   - `.loki-loki-code-block`
   - `.loki-loki-composer`
   - `.loki-loki-composer-meta`
   - `.loki-loki-context-panel`
   - `.loki-loki-conversation-item`
   - `.loki-loki-conversation-item-active`
   - `.loki-loki-drawer`
   - `.loki-loki-empty-hero`
   - `.loki-loki-header-sticker`
   - `.loki-loki-input`
   - `.loki-loki-mascot-frame`
   - `.loki-loki-nav-group`
   - `.loki-loki-nav-group-dot`
   - `.loki-loki-nav-group-label`
   - `.loki-loki-nav-icon`
   - `.loki-loki-nav-item`
   - `.loki-loki-nav-item-active`
   - `.loki-loki-page`
   - `.loki-loki-paper`
   - `.loki-loki-sidebar`
   - `.loki-loki-sidebar-head`
   - `.loki-loki-sticker`
   - `.loki-loki-sticker-title`
   - `.loki-loki-surface`
   - `.loki-loki-surface-strong`
   - `.loki-loki-table`
   - `.loki-loki-theme-swatch`
   - `.loki-loki-theme-swatch-active`
   - `.loki-loki-tint-danger`
   - `.loki-loki-tint-success`
   - `.loki-loki-tint-warning`
   - `.loki-loki-workbench`
   - `.loki-loki-workbench-toolbar`

完整契约表见 `references/host-contract.md`。**少挂哪几个，就少几处主题效果，不会报错。**

## 切换器（可以直接抄）

已一并装进本目录：

- `theme-switcher.js`   原生 JS（造 DOM，无依赖）
- `theme-switcher.tsx`  React / Next.js 版
- `theme-switcher.css`  切换器样式（只用主题令牌，自己也会跟着变）
- `theme-switcher-flash-guard.html`  放在 `<head>` 最前面的防闪白片段

两个坑已经在文件注释里写明白了：localStorage 不能在 useState 初值里读（hydration
mismatch）；收起的面板要 `display:none`，否则它仍然占布局、会把侧栏挤出去。

## 演示页

`demo.html` 是一个**参考宿主**：只用契约类名 + 令牌搭出侧栏/卡片/按钮/输入区，
浏览器直接打开就能切主题看效果（`host-base.css` 就是"宿主那一半"的最小实现，
可以照着搬进你自己的样式）。

## 关于图片和 IP

套组**零图片依赖**：这些槽位：--deco-a、--deco-b、--deco-c、--deco-d 默认 `none`，想挂自己的装饰就覆盖它。

```css
:root[data-theme="loki-8bit"] { --deco-a: url("/your/cloud.png"); }
```

**套组不含任何人的 IP 形象。** 你自己的品牌头像放你自己的位置，别指望套组带它来。
