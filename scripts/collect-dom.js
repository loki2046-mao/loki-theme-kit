/* 宿主界面盘点器 —— 在页面里跑，把「谁长什么样、在哪儿、重复不重复」抓回来。
 *
 * 为什么需要它：套组的颜色靠令牌就能搬过去，但结构件（纸面、贴纸圆边、撕口、
 * 计数器编号、扫描线……）挂在 `.loki-*` 这些语义钩子上。普通宿主的 DOM 里
 * 没有这些钩子，所以要先**认出来**宿主里哪个元素扮演哪个角色，
 * 再由 tagger 把钩子挂上去。这个文件负责「认」的那一半：只抓事实，不下判断。
 *
 * 用法（通过 probe.py 调用）：
 *     python3 scripts/probe.py --port 9333
 */
(function () {
  var MAX = 2600;
  var vw = window.innerWidth, vh = window.innerHeight;
  var out = [], dropped = 0;

  function norm(s) { return (s || '').replace(/\s+/g, ' ').trim(); }
  function short(s, n) { s = norm(s); return s.length > n ? s.slice(0, n) : s; }
  function visibleScreen(r) { return r.bottom > 0 && r.right > 0 && r.top < vh && r.left < vw; }

  // 跳过我们自己注入的东西，别把自己的 UI 当成宿主 UI 盘点进去
  var SKIP = '#loki-theme-kit-switcher, [data-loki-injected], .loki-switcher-root';

  // 沿祖先链找第一个不透明背景 —— 「这个元素坐在什么颜色的底上」
  function effBg(el) {
    var n = el;
    while (n && n.nodeType === 1) {
      var c = window.getComputedStyle(n).backgroundColor;
      if (c && c.indexOf('rgba(0, 0, 0, 0)') !== 0 && c.indexOf('transparent') !== 0) {
        var m = c.match(/[\d.]+/g);
        if (!m || m.length < 4 || parseFloat(m[3]) > 0.7) return c;
      }
      n = n.parentElement;
    }
    return 'rgb(255, 255, 255)';
  }

  // 完整路径（从 body 起，不截断）。截断过的路径看着像选择器，拿去 querySelectorAll
  // 会从根上解释错 —— 这是真踩过的坑，所以宁可长一点也要写全。
  function pathOf(el) {
    var parts = [], n = el, guard = 0;
    while (n && n.nodeType === 1 && n !== document.documentElement && guard++ < 40) {
      var p = n.tagName.toLowerCase(), par = n.parentElement;
      if (par && par.nodeType === 1) {
        var same = [], kids = par.children;
        for (var i = 0; i < kids.length; i++) if (kids[i].tagName === n.tagName) same.push(kids[i]);
        if (same.length > 1) p += ':nth-of-type(' + (same.indexOf(n) + 1) + ')';
      }
      parts.unshift(p);
      n = par;
    }
    return parts.join('>');
  }

  function selOf(el) {
    if (el.id && /^[A-Za-z][\w-]*$/.test(el.id)) return '#' + el.id;
    var cls = [], list = el.classList;
    for (var i = 0; i < list.length && cls.length < 3; i++) {
      var c = list[i];
      if (c.length > 40 || /[^\w-]/.test(c)) continue;
      cls.push('.' + c);
    }
    if (cls.length) return el.tagName.toLowerCase() + cls.join('');
    return pathOf(el);
  }

  var all = document.querySelectorAll('body *');
  for (var k = 0; k < all.length; k++) {
    var el = all[k];
    if (out.length >= MAX) { dropped++; continue; }
    if (el.closest(SKIP)) continue;
    var r = el.getBoundingClientRect();
    if (r.width < 6 || r.height < 6) continue;
    var cs = window.getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0') continue;

    var cls2 = [], cl = el.classList;
    for (var j = 0; j < cl.length && cls2.length < 8; j++) cls2.push(cl[j]);
    var sig = el.tagName.toLowerCase() + '|' + cls2.slice().sort().join('');

    // 同签名兄弟有几个 —— 重复出现的多半是「列表项 / 导航项 / 消息」
    var sib = 0, sameSig = 0, par = el.parentElement;
    if (par) {
      var kids2 = par.children;
      for (var m = 0; m < kids2.length; m++) {
        var c2 = kids2[m];
        if (c2 === el) sib = sm(kids2, m);
        var cc = [], ccl = c2.classList;
        for (var q = 0; q < ccl.length && cc.length < 8; q++) cc.push(ccl[q]);
        if (c2.tagName.toLowerCase() + '|' + cc.slice().sort().join('') === sig) sameSig++;
      }
    }
    function sm(list, idx) {
      var n = 0;
      for (var a = 0; a <= idx; a++) if (list[a].tagName === el.tagName) n++;
      return n;
    }

    var depth = 0, p2 = el.parentElement;
    while (p2 && depth < 99) { depth++; p2 = p2.parentElement; }

    var own = 0, ch = el.childNodes;
    for (var t = 0; t < ch.length; t++) if (ch[t].nodeType === 3) own += norm(ch[t].nodeValue).length;

    out.push({
      i: out.length,
      tag: el.tagName.toLowerCase(),
      id: el.id || '',
      cls: cls2.join(' '),
      role: el.getAttribute('role') || '',
      aria: el.getAttribute('aria-label') || '',
      path: pathOf(el),
      sel: selOf(el),
      sig: sig,
      d: depth,
      r: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)],
      vis: visibleScreen(r) ? 1 : 0,
      bg: cs.backgroundColor,
      pbg: effBg(el.parentElement || el),
      fg: cs.color,
      bdc: cs.borderTopColor,
      bdw: cs.borderTopWidth,
      rad: cs.borderTopLeftRadius,
      fs: cs.fontSize,
      fw: cs.fontWeight,
      ff: (cs.fontFamily || '').split(',')[0].replace(/["']/g, ''),
      sh: cs.boxShadow !== 'none' ? 1 : 0,
      ovf: cs.overflowY,
      pos: cs.position,
      cur: cs.cursor,
      txt: short(el.textContent, 60),
      own: own,
      kids: el.children.length,
      sib: sib,
      same: sameSig,
      se: el.scrollHeight > el.clientHeight + 4 ? 1 : 0
    });
  }

  var html = document.documentElement;
  return {
    url: location.href,
    title: document.title,
    viewport: [vw, vh],
    dpr: window.devicePixelRatio,
    dark: window.matchMedia('(prefers-color-scheme: dark)').matches,
    htmlCls: html.className || '',
    htmlAttrs: (function () {
      var o = {}, a = html.attributes;
      for (var i = 0; i < a.length; i++) if (a[i].name.indexOf('data-') === 0) o[a[i].name] = a[i].value;
      return o;
    })(),
    total: all.length,
    dropped: dropped,
    elements: out
  };
})()
