# 套组文件格式

每套主题是一个目录，里面只有两个文件。这是本套件的最小单位，也是能"发出去"的原因：
**一套主题 = 一段 CSS + 一张身份卡，没有图片、没有脚本、没有依赖。**

```text
sets/loki-die/
├── theme.css     这一套的全部 CSS（令牌块 + 该套专属规则）
└── meta.json     身份卡：机器和人都能读的那部分
```

## theme.css

两类东西，用同一个选择器开头：

```css
/* ① 令牌块：变量。必须有那 7 个必备令牌（check.py 的 G1 会查） */
:root[data-theme="loki-die"] {
  --bg-canvas: #f6f1e6;
  --text-primary: #2a211c;
  --accent-copper: #b04a33;
  --accent-ink: #fffdf8;
  /* … 31–37 个 */
  --deco-a: none;           /* 装饰槽位，默认不给图 */
}

/* ② 专属规则：这套主题的结构件（决定它"像什么"，不是"什么颜色"） */
:root[data-theme="loki-die"] .loki-surface-strong {
  border: 3px solid #fff;
  border-radius: 18px;
  outline: 1px dashed rgba(28, 20, 16, .38);
  outline-offset: 3px;
}
```

`data-theme="loki-die"` 就是这套的 id。id 只出现在这个属性里——**换成别的名字不影响
任何规则**，所以宿主想改叫 `my-theme` 只需要全局替换这个字符串。

## meta.json

```json
{
  "id": "loki-die",
  "label": "模切贴纸",
  "group": "art",                        // care / art / retro / calm
  "accent": "#b04a33",
  "surface": "#f7f2e8",
  "tokens": 35,
  "rules": 11,
  "rule_lines": 40,
  "host_hooks": ["loki-nav-item", "loki-surface-strong", "..."],   // 这套会碰哪些契约钩子
  "deco_slots": ["--deco-a"],            // 装饰槽位（图片由使用者自己提供）
  "source_board": "loki红熊猫音乐贴纸页",  // 来源板：这套是从哪来的
  "recommended": false
}
```

`host_hooks` 是**自动算出来的**（扫 theme.css 里的类名），不是手写的——所以它不会说谎：
它列的就是这套主题真正会作用到的钩子。

## index.json / sources.json

- `index.json`：35 套的汇总（id/名字/分组/令牌数/规则数/钩子/槽位/是否推荐），
  画廊和安装器都读它。
- `sources.json`：id → 来源板。做新主题时照这个格式记来源，别省——半年后你会感谢自己。

## 加一套新套组

```bash
python3 scripts/new-theme.py --id my-x --label "我的X" --group art --palette 参考图.png
# 写完结构件后：
python3 scripts/check.py --only my-x        # 六道门
python3 scripts/gallery.py                  # 画廊重新生成
```

新套组目录放进来就自动被索引（`index.json` 由 `extract.py` 重生成，或手工补一条）。
