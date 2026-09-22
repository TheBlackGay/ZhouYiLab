/* state-sync.js — 排盘参数 URL 同步（周乙实验室 ZhouYiLab）。
 *
 * 以经典 <script>（非 defer）放在各排盘页脚本之前，保证在页面 defer 脚本
 * （部分页面会 requestSubmit 自动排盘）执行前完成表单水合：
 * 1) 载入：location.search → 表单控件（含表单外隐藏输出，如 *-utc-offset/*-lat）；
 * 2) 联动：仅对 radio/checkbox/select 派发 change（date/number/text 不派发，
 *    避免 qimen 年命字段等触发额外提交）；DCL 时重新断言值（place-picker 等
 *    可能在 defer 初始化时覆盖隐藏字段/尚未填充的 select）。
 * 3) 变更：表单 change/input 防抖写回 URL（history.replaceState，不产生历史条目）。
 * 4) 注入「复制排盘链接」按钮与 role=status 反馈。
 * 5) 错误重试：为 [role="alert"] 注入 .error-retry 兄弟按钮，随错误可见性显示。
 *
 * 已知取舍：分享链接会携带「具体问题/问题描述」文本（仅用户主动复制才分享）；
 * 出生地点搜索框显示不恢复，但隐藏坐标字段已恢复，排盘结果正确。
 */
(function () {
  'use strict';

  var form = null;
  var forms = document.querySelectorAll('form');
  for (var i = 0; i < forms.length; i += 1) {
    if (forms[i].querySelector('.primary-action')) { form = forms[i]; break; }
  }
  if (!form) return;

  var params = new URLSearchParams(location.search);
  var MAX_URL = 2600;

  /* 需要水合的控件：表单内所有有 id/name 的可输入元素 + 表单外带 id 的隐藏输入 */
  function fields() {
    var out = [];
    Array.prototype.forEach.call(form.elements, function (el) {
      if (!el.id && !el.name) return;
      if (el.type === 'submit' || el.type === 'button' || el.type === 'image') return;
      out.push(el);
    });
    Array.prototype.forEach.call(document.querySelectorAll('body > input[type="hidden"][id], main > input[type="hidden"][id], aside input[type="hidden"][id]'), function (el) {
      if (out.indexOf(el) === -1) out.push(el);
    });
    return out;
  }

  function keyOf(el) { return el.type === 'radio' ? (el.name || el.id) : (el.id || el.name); }

  function serialize() {
    var out = new URLSearchParams();
    var seenRadio = {};
    fields().forEach(function (el) {
      if (el.type === 'radio') {
        var k = keyOf(el);
        if (el.checked && !seenRadio[k]) { seenRadio[k] = true; out.set(k, el.value); }
        return;
      }
      if (el.type === 'checkbox') { out.set(keyOf(el), el.checked ? '1' : '0'); return; }
      if (el.value !== '') out.set(keyOf(el), el.value);
    });
    return out;
  }

  function writeUrl(force) {
    var qs = serialize().toString();
    var next = qs ? location.pathname + '?' + qs : location.pathname;
    if (next.length > MAX_URL) return;
    if (force || next !== location.pathname + location.search) {
      history.replaceState(null, '', next);
    }
  }

  /* 值写入（不派发事件）。返回被水合的控件集合 */
  var hydrated = [];
  function applyValues() {
    params.forEach(function (value, key) {
      var radio = form.elements[key];
      if (radio && radio.length !== undefined && radio[0] && radio[0].type === 'radio') {
        for (var j = 0; j < radio.length; j += 1) {
          if (radio[j].value === value && !radio[j].checked) { radio[j].checked = true; hydrated.push(radio[j]); }
        }
        return;
      }
      var el = document.getElementById(key);
      if (!el) return;
      if (el.type === 'checkbox') {
        var want = value === '1' || value === 'true';
        if (el.checked !== want) { el.checked = want; hydrated.push(el); }
        return;
      }
      if (el.value !== value) {
        try { el.value = value; hydrated.push(el); } catch (err) { /* 非法日期值忽略 */ }
      }
    });
  }
  applyValues();

  /* DCL：重新断言（select options 可能刚被填充、隐藏输出可能被组件覆盖），
   * 再联动 radio/checkbox/select */
  function redispatch() {
    if (!params.size) return;
    applyValues();
    var fired = {};
    hydrated.forEach(function (el) {
      if (el.type === 'radio' || el.type === 'checkbox' || el.tagName === 'SELECT') {
        var k = (el.type === 'radio' ? 'r' : '') + (el.name || el.id) + ':' + (el.type === 'radio' ? '' : el.value);
        if (fired[k]) return;
        fired[k] = true;
        el.dispatchEvent(new Event('change', { bubbles: true }));
      }
    });
    /* 不自动排盘的页面：代用户提交一次，使分享链接打开即是结果 */
    var AUTO = { '/': 1, '/index.html': 1, '/bazi.html': 1, '/bazi': 1, '/qimen.html': 1, '/qimen': 1 };
    if (!AUTO[location.pathname] && typeof form.requestSubmit === 'function') {
      form.requestSubmit();
    }
  }

  /* 复制排盘链接 */
  function injectCopyAction() {
    var submit = form.querySelector('.primary-action');
    if (!submit || submit.parentNode !== form) return;
    var row = document.createElement('div');
    row.className = 'link-copy-row';
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'secondary-action link-copy';
    btn.textContent = '复制排盘链接';
    var status = document.createElement('p');
    status.className = 'link-copy-status';
    status.setAttribute('role', 'status');
    row.appendChild(btn);
    row.appendChild(status);
    submit.insertAdjacentElement('afterend', row);
    btn.addEventListener('click', function () {
      writeUrl(true);
      var url = location.href;
      function done(ok) { status.textContent = ok ? '链接已复制，可直接分享本次排盘' : '复制失败，请从地址栏复制'; }
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(url).then(function () { done(true); }, function () { done(fallback(url)); });
      } else { done(fallback(url)); }
    });
    function fallback(text) {
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', 'readonly');
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      var ok = false;
      try { ok = document.execCommand('copy'); } catch (err) { ok = false; }
      document.body.removeChild(ta);
      return ok;
    }
  }

  /* 错误重试：role=alert 显示时在身后挂出 .error-retry */
  function injectRetry() {
    document.querySelectorAll('[role="alert"][id]').forEach(function (node) {
      if (!node.closest('form') && node.id.indexOf('error') === -1) return;
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'error-retry';
      btn.textContent = '重试';
      btn.hidden = true;
      btn.addEventListener('click', function () {
        btn.hidden = true;
        form.requestSubmit();
      });
      node.insertAdjacentElement('afterend', btn);
      var sync = function () { btn.hidden = !!node.hidden; };
      sync();
      new MutationObserver(sync).observe(node, { attributes: true, attributeFilter: ['hidden'] });
    });
  }

  function onFormActivity() {
    if (typeof window.__zylUrlSyncTimer === 'number') clearTimeout(window.__zylUrlSyncTimer);
    window.__zylUrlSyncTimer = setTimeout(function () { writeUrl(false); }, 250);
  }
  form.addEventListener('change', onFormActivity);
  form.addEventListener('input', onFormActivity);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { redispatch(); injectCopyAction(); injectRetry(); writeUrl(true); });
  } else {
    redispatch(); injectCopyAction(); injectRetry(); writeUrl(true);
  }
})();
