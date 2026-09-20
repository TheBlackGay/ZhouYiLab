/* 共享组件：分布画像环形图（西洋占星 / 紫微斗数通用）。
 * 消费 {schema_version, summary_zh, charts:[{title_zh,basis_zh,segments,dominant,headline_zh,reading_zh}]}
 * 样式自足（首次注入 <style>），宿主页无需额外 CSS。 */
window.ProfileCharts = (function () {
  const COLORS = {
    // 占星四元素 / 紫微五行（同一语义同色：火=朱、土=橄榄、风/气=蓝灰、水=靛）
    fire: '#b3402a', earth: '#6f7d54', air: '#3f6f92', water: '#4f5b8a',
    '火': '#b3402a', '木': '#3d7a4f', '土': '#6f7d54', '金': '#a67b2e', '水': '#4f5b8a',
    positive: '#a45b32', negative: '#44607a',
    cardinal: '#a67b2e', fixed: '#25634d', mutable: '#7a5c96',
    bright: '#c99a3f', steady: '#6f7d54', dim: '#5d6b84',
    // 八字十神五类（比肩劫财/食神伤官/财/官杀/印绶）
    bijie: '#5d6b84', shishang: '#7a5c96', cai: '#c99a3f', guan: '#4f5b8a', yin: '#3d7a4f',
  };
  const esc = value => String(value ?? '').replace(/[&<>'"]/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c]));

  let stylesInjected = false;
  function injectStyles() {
    if (stylesInjected || document.getElementById('profile-charts-css')) { stylesInjected = true; return; }
    const style = document.createElement('style');
    style.id = 'profile-charts-css';
    style.textContent = `
.profile-zone { margin:2px 0 24px; }
.profile-summary { margin:0 0 18px; padding:13px 18px; background:#f7f3e9; border:1px solid #dfd1ae; border-left:4px solid var(--gold, #a67b2e); border-radius:4px; font-size:14.5px; line-height:1.7; color:#4a4234; }
.profile-charts { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:16px; }
.profile-chart-card { display:grid; gap:14px; padding:18px; background:var(--panel, #fff); border:1px solid var(--line, #d8dcd8); border-radius:4px; }
.profile-donut { position:relative; width:132px; height:132px; margin:0 auto; border-radius:50%; }
.profile-donut::after { content:""; position:absolute; inset:26%; background:var(--surface, #fff); border-radius:50%; box-shadow:inset 0 0 0 1px var(--line, #d8dcd8); }
.profile-donut-core { position:absolute; inset:0; z-index:1; display:grid; place-content:center; gap:2px; text-align:center; }
.profile-donut-core b { font:800 22px/1 Georgia,"Noto Serif SC",serif; color:var(--ink, #1d2421); }
.profile-donut-core span { font-size:11px; color:var(--muted, #68716c); }
.profile-chart-main { display:grid; justify-items:center; gap:10px; text-align:center; }
.profile-chart-main h4 { margin:0; font-size:14px; }
.profile-legend { list-style:none; margin:0; padding:0; display:grid; gap:6px; }
.profile-legend li { display:grid; grid-template-columns:14px 1fr auto; gap:8px; align-items:center; font-size:12px; color:var(--muted, #68716c); }
.profile-legend i { width:10px; height:10px; border-radius:3px; }
.profile-legend b { color:var(--ink, #1d2421); font-variant-numeric:tabular-nums; }
.profile-reading { margin:0; padding-top:10px; border-top:1px dashed var(--line, #d8dcd8); color:#434c47; font-size:12.5px; line-height:1.75; }
.profile-chart-card small { color:var(--muted, #68716c); }
@media (max-width:900px) { .profile-charts { grid-template-columns:1fr; } }`;
    document.head.append(style);
    stylesInjected = true;
  }

  function render(container, distribution) {
    container.dataset.schema = distribution.schema_version || '';
    const summary = distribution.summary_zh
      ? `<p class="profile-summary">${esc(distribution.summary_zh)}</p>` : '';
    const cards = (distribution.charts || []).map(chart => {
      let cursor = 0;
      const stops = chart.segments.map(segment => {
        const from = cursor; cursor += segment.percent;
        return `${COLORS[segment.key] || '#8a8f8a'} ${from}% ${cursor}%`;
      }).join(', ');
      const center = chart.dominant
        ? `<b>${chart.dominant.percent}%</b><span>${esc(chart.dominant.tag_zh)}</span>`
        : '<b>匀停</b><span>无单一主导</span>';
      const legend = chart.segments.map(segment =>
        `<li><i style="background:${COLORS[segment.key] || '#8a8f8a'}"></i><span>${esc(segment.label_zh)}（${esc(segment.tag_zh)}）</span><b>${segment.percent}%</b></li>`).join('');
      return `<article class="profile-chart-card">
        <div class="profile-chart-main">
          <div class="profile-donut" style="background:conic-gradient(${stops})" role="img"
               aria-label="${esc(chart.title_zh)}：${esc(chart.headline_zh)}"><div class="profile-donut-core">${center}</div></div>
          <h4>${esc(chart.headline_zh)}</h4>
        </div>
        <ul class="profile-legend">${legend}</ul>
        <p class="profile-reading">${esc(chart.reading_zh)}</p>
        <small>${esc(chart.basis_zh)}</small>
      </article>`;
    }).join('');
    container.innerHTML = summary + `<div class="profile-charts">${cards}</div>`;
  }

  async function load(options) {
    injectStyles();
    const container = document.querySelector(options.container);
    const fallback = options.fallback ? document.querySelector(options.fallback) : null;
    if (!container) return;
    try {
      const body = {};
      if (options.chart) body.chart = options.chart;
      else if (options.chartRequest) body.chart_request = options.chartRequest;
      else throw new Error('缺少 chart 或 chart_request');
      const label = options.label ?? null;
      if (label) body.label = label;
      const response = await fetch(options.path, { method: 'POST',
        headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const payload = await response.json();
      if (!response.ok || !payload.success) throw new Error(payload?.error?.message || '分布画像失败');
      if (fallback) fallback.hidden = true;
      render(container, payload.data);
    } catch (error) {
      container.innerHTML = '';
      if (fallback) fallback.hidden = false;
    }
  }

  return { render, load };
})();
