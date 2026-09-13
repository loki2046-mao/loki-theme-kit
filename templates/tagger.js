/* 结构件挂钩器 —— 在宿主页面里跑，把宿主自己的元素认领成套组的契约钩子。
 *
 * 为什么需要它：套组的**颜色**靠令牌就能搬过去，但**结构件**（纸面纹理、贴纸圆边、
 * 撕口、计数器编号、扫描线、四角准星、气泡尾巴……）在 CSS 里是挂在 `.loki-*`
 * 这些语义钩子上的。普通宿主的 DOM 里没有这些钩子，所以结构件全都落空了。
 *
 * 这个脚本把缺的那一环补上：按 `binding.json`（角色 → 宿主里的选择器）给宿主的
 * 真实元素**加上**这些钩子类名。加完以后，35 套的结构层原封不动就能生效 ——
 * 不用为每个宿主重写 35 套主题，每个宿主只需要一份角色对照表。
 *
 * 三个设计约束：
 *   1. 幂等 —— 反复跑不会重复加、不会加错；
 *   2. 跟得上重渲染 —— 宿主是动态的（列表会重建），用 MutationObserver 补挂；
 *   3. **坏了自己会喊** —— 某个角色在宿主里一个元素都匹配不到时，往控制台警告，
 *      并把结果留在 `window.__LOKI_ROLE_REPORT__`，好让 `adapt.py --check` 拿到。
 *      宿主升级把 DOM 改了，就是靠这条发现的。
 *
 * 它只**加类名**，不动宿主的 DOM 结构、不写文件和存储。
 */
(function () {
  var CFG = window.__LOKI_ROLES__ || {};
  var ROLES = CFG.roles || {};
  var PREFIX = CFG.prefix || 'loki-';
  var SKIP = CFG.skip || '[data-loki-injected]';
  var DEBOUNCE = CFG.debounce || 200;
  var lastReport = null;

  function passes(el, spec) {
    if (typeof spec === 'string') return true;
    if (spec.within && !el.closest(spec.within)) return false;
    if (spec.has && !el.querySelector(spec.has)) return false;
    if (spec.not && el.closest(spec.not)) return false;
    var r = el.getBoundingClientRect();
    if (spec.min_h && r.height < spec.min_h) return false;
    if (spec.max_h && r.height > spec.max_h) return false;
    if (spec.min_w && r.width < spec.min_w) return false;
    if (spec.max_w && r.width > spec.max_w) return false;
    return true;
  }

  function apply() {
    var report = {}, dead = [], total = 0;
    for (var role in ROLES) {
      if (!Object.prototype.hasOwnProperty.call(ROLES, role)) continue;
      var spec = ROLES[role];
      var sel = typeof spec === 'string' ? spec : spec.selector;
      var cls = PREFIX + role;
      var nodes;
      try {
        nodes = document.querySelectorAll(sel);
      } catch (e) {
        report[role] = -1;
        dead.push(role + '(选择器无效)');
        continue;
      }
      var n = 0;
      for (var i = 0; i < nodes.length; i++) {
        var el = nodes[i];
        if (SKIP && el.closest(SKIP)) continue;
        if (!passes(el, spec)) continue;
        if (!el.classList.contains(cls)) el.classList.add(cls);
        el.setAttribute('data-loki-role', role);
        n++;
      }
      report[role] = n;
      total += n;
      if (n === 0) dead.push(role);
    }
    report.__total = total;
    window.__LOKI_ROLE_REPORT__ = report;
    lastReport = report;
    if (dead.length && window.console && console.warn) {
      console.warn('[loki-theme-kit] 这些角色在宿主里一个元素都没匹配到，结构件会落空：' + dead.join(', ') +
        '　→ 跑 `python3 scripts/adapt.py --host <宿主> --port <端口> --refresh` 重认一遍');
    }
    return report;
  }

  window.__LOKI_APPLY_ROLES__ = apply;
  apply();

  // 宿主是动态渲染的：列表重建、面板切换都会把类名冲掉，所以 DOM 一变就补挂。
  // 用 MutationObserver 而不是定时器轮询，闲着的时候不占 CPU。
  if (CFG.watch !== false && window.MutationObserver) {
    var timer = null;
    var mo = new MutationObserver(function () {
      if (timer) return;
      timer = setTimeout(function () { timer = null; apply(); }, DEBOUNCE);
    });
    mo.observe(document.documentElement, { childList: true, subtree: true });
    window.__LOKI_ROLE_OBSERVER__ = mo;
  }
})()
