# 装饰槽位（asset slots）

## 一条硬规则

**套组不携带任何人的图片。** 没有头像、没有吉祥物、没有道具素材。要图的地方全部是
CSS 变量，默认 `none`——**缺图不会破版，只是少一个装饰**。

## 槽位长什么样

套组里凡是原作者挂了私有素材的地方，都已经被改写成变量：

```css
:root[data-theme="loki-ticket"] {
  /* 装饰槽位：原作者在这里挂的是自己的素材（/loki-stickers/pixel-ticket.png），
     本套组不含该文件。想挂自己的装饰就覆盖这个变量。 */
  --deco-a: none;
  --deco-b: none;
}
:root[data-theme="loki-ticket"] .loki-empty-hero {
  background-image: var(--deco-a), var(--deco-b);
  background-position: right 26px top 22px, right 22px bottom 20px;
  background-size: 44px, 46px;
  image-rendering: pixelated;
}
```

几何（位置、尺寸、像素锐化）是**主题的一部分**，保留；图本身是**你的**，留空。

## 怎么填自己的图

```css
/* 放在你引主题之后，覆盖即可 */
:root[data-theme="loki-ticket"] {
  --deco-a: url("/my/icon-ticket.png");
  --deco-b: url("/my/icon-map.png");
}
```

三条注意：

1. **`--deco-x` 是按套组独立编号的**（`--deco-a`…），不同套组里的 a/b 指的是不同东西。
   所以覆盖要写成 `:root[data-theme="<id>"] { --deco-a: … }` 这种带主题名的形式。
2. **尺寸和位置是主题定的**，你的图最好透明底、比例接近。`background-size` 用的固定
   px，图太窄会被拉变形——想改尺寸就在自己的覆盖规则里一起写 `background-size`。
3. **不想要装饰就别管它。** 默认 `none` 就是最终状态，不需要"删掉那段 CSS"。

## 哪些套组有槽位

```bash
python3 - <<'PY'
import json, pathlib
for d in sorted(pathlib.Path("sets").iterdir()):
    m = d / "meta.json"
    if not m.exists(): continue
    meta = json.loads(m.read_text())
    if meta.get("deco_slots"):
        print(d.name, meta["label"], meta["deco_slots"])
PY
```

35 套里只有 3 套有槽位（`loki-ticket` 票根+地图、`loki-8bit` 云/环行星/金币/木箱、
`loki-neon` 黑胶+音符）——其余 32 套是零装饰的纯 CSS 主题。

## 宿主自己的品牌形象放哪

**不放在套组里，也不放在套组的槽位上。** 放宿主自己的位置（头像位、品牌位），
套组不去装饰它。这是本套件第一条铁律：换外观只换壳，不碰任何人的角色形象。
