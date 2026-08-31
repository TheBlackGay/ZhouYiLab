const form = document.querySelector('#chart-form');
const submitButton = form.querySelector('.primary-action');
const errorBox = document.querySelector('#form-error');
const emptyState = document.querySelector('#empty-state');
const resultContent = document.querySelector('#result-content');
const trueSolarInput = document.querySelector('#true-solar');
const solarOptions = document.querySelector('#solar-options');

const desktopPositions = [13, 9, 5, 1, 2, 3, 4, 8, 12, 16, 15, 14];
const layerNames = { da_xian: '大限', xiao_xian: '小限', liu_nian: '流年', liu_yue: '流月', liu_ri: '流日', liu_shi: '流时' };
const layerColors = { all: '#18201d', da_xian: '#59625d', liu_nian: '#286fa6', liu_yue: '#bc681b', liu_ri: '#7650a3', liu_shi: '#a83232' };
let currentData = null;
let currentAnalysis = null;

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  })[character]);
}

function parts(value) {
  const [date, time] = value.split('T');
  const [year, month, day] = date.split('-').map(Number);
  const [hour, minute] = time.split(':').map(Number);
  return { year, month, day, hour, minute };
}

function dateAndTime(dateId, timeId) {
  return parts(`${document.querySelector(dateId).value}T${document.querySelector(timeId).value}`);
}

function updateAge() {
  const birthYear = Number(document.querySelector('#birth-date').value.slice(0, 4));
  const targetYear = Number(document.querySelector('#target-date').value.slice(0, 4));
  if (birthYear && targetYear) document.querySelector('#age').value = targetYear - birthYear + 1;
}

function setLoading(loading) {
  submitButton.disabled = loading;
  submitButton.classList.toggle('loading', loading);
}

function palaceName(chart, index) {
  return chart.palaces[index]?.name || `第${index}宫`;
}

function fourPillars(data) {
  return [data.si_zhu.year, data.si_zhu.month, data.si_zhu.day, data.si_zhu.hour].join(' ');
}

function starMarkup(star, primary = false) {
  const transformation = star.si_hua
    ? `<em class="star-transform">${star.si_hua.replace('化', '')}</em>`
    : '';
  const brightness = star.liang_du
    ? `<small class="brightness">${star.liang_du}</small>`
    : '';
  return `<span class="star${primary ? ' primary' : ''}"><span class="star-name">${star.name}${transformation}</span>${brightness}</span>`;
}

function starDetails(palace, detailKey, legacyKey) {
  if (Array.isArray(palace[detailKey])) return palace[detailKey];
  return (palace[legacyKey] || []).map(name => ({ name, liang_du: '' }));
}

function shenShaMarkup(palace) {
  const values = palace.shen_sha || {};
  const items = [
    ['长生', values.chang_sheng_12],
    ['博士', values.bo_shi_12],
    ['岁前', values.sui_qian_12],
    ['将前', values.jiang_qian_12],
  ].filter(([, value]) => value);
  if (!items.length) return '';
  return `<div class="shen-sha-zone"><small class="zone-label">十二神</small><div class="shen-sha-list">${items.map(([label, value]) => `<span><small>${label}</small><strong>${escapeHtml(value)}</strong></span>`).join('')}</div></div>`;
}

function transitStarMarkup(star, layer) {
  const brightness = star.liang_du ? `<small>${escapeHtml(star.liang_du)}</small>` : '';
  return `<span class="transit-star ${layer}" data-layer="${layer}" title="${escapeHtml(layerNames[layer])} · ${escapeHtml(star.name)}"><b>${escapeHtml(star.display_name)}</b>${brightness}</span>`;
}

function renderSummary(data) {
  const correction = data.birth_time;
  document.querySelector('#summary-title').textContent = correction.recorded_time.slice(0, 16);
  document.querySelector('#summary-subtitle').textContent = `${data.gender} · ${data.lunar_date}`;
  document.querySelector('#metric-pillars').textContent = fourPillars(data);
  document.querySelector('#metric-wuxing').textContent = data.wu_xing_ju;
  document.querySelector('#metric-ming').textContent = palaceName(data, data.ming_gong_index);
  document.querySelector('#metric-solar').textContent = correction.mode === 'true_solar_time' ? correction.chart_time.slice(11, 16) : '未启用';
  document.querySelector('#center-lunar').textContent = data.lunar_date;
  document.querySelector('#center-four-pillars').textContent = fourPillars(data).replaceAll(' ', '　');
  document.querySelector('#center-recorded').textContent = correction.recorded_time.slice(11, 16);
  document.querySelector('#center-solar').textContent = correction.mode === 'true_solar_time' ? correction.chart_time.slice(11, 16) : '未启用';
  document.querySelector('#center-target').textContent = `运限 · ${data.target.solar_time}`;
}

function renderBoard(data) {
  const board = document.querySelector('#palace-board');
  board.querySelectorAll('.palace').forEach(node => node.remove());
  const flagsByPalace = {};
  const transitStarsByPalace = {};
  Object.entries(data.fortune).forEach(([key, layer]) => {
    if (layer && Number.isInteger(layer.palace_index)) {
      (flagsByPalace[layer.palace_index] ||= []).push({ key, label: layerNames[key] });
    }
    (layer?.transit_stars || []).forEach(star => {
      (transitStarsByPalace[star.palace_index] ||= []).push({ ...star, layer: key });
    });
  });
  data.palaces.forEach((palace, index) => {
    const node = document.createElement('article');
    node.className = 'palace';
    const palaceFlags = flagsByPalace[index] || [];
    node.dataset.layers = palaceFlags.map(item => item.key).join(' ');
    const position = desktopPositions[index];
    node.style.gridArea = `${Math.ceil(position / 4)} / ${((position - 1) % 4) + 1}`;
    const primary = palace.zhu_xing.map(star => starMarkup(star, true)).join('');
    const secondary = [
      ...starDetails(palace, 'fu_xing_detail', 'fu_xing'),
      ...starDetails(palace, 'sha_xing_detail', 'sha_xing'),
      ...starDetails(palace, 'za_yao_detail', 'za_yao'),
    ].map(star => starMarkup(star)).join('');
    const transitStars = (transitStarsByPalace[index] || [])
      .map(star => transitStarMarkup(star, star.layer)).join('');
    const transitZone = transitStars
      ? `<div class="transit-zone"><small class="zone-label">运限流曜</small><div class="transit-stars">${transitStars}</div></div>`
      : '';
    const flags = palaceFlags.map(item => `<span class="flow-flag ${item.key}">${item.label}</span>`).join('');
    node.innerHTML = `<header><h3>${escapeHtml(palace.name)}</h3><span class="branch">${escapeHtml(palace.gan_zhi)}</span></header><div class="star-zone"><small class="zone-label">主星</small><div class="stars">${primary || '<span class="star">空宫</span>'}</div></div><div class="secondary-zone"><small class="zone-label">辅星 · 煞曜 · 杂曜</small><div class="stars">${secondary || '<span class="star">无</span>'}</div></div>${shenShaMarkup(palace)}${transitZone}<div class="flow-flags">${flags}</div>`;
    board.appendChild(node);
  });
}

function setActiveLayer(layer) {
  const board = document.querySelector('#palace-board');
  board.dataset.activeLayer = layer;
  board.style.setProperty('--active-layer-color', layerColors[layer] || layerColors.all);
  board.querySelectorAll('.palace').forEach(node => {
    const layers = node.dataset.layers.split(' ');
    node.classList.toggle('layer-active', layer === 'all' || layers.includes(layer));
  });
  board.querySelectorAll('.transit-star').forEach(node => {
    node.hidden = layer !== 'all' && node.dataset.layer !== layer;
  });
  document.querySelectorAll('.layer-filter button, .flow-track button').forEach(button => {
    button.setAttribute('aria-pressed', String(button.dataset.layer === layer));
  });
}

function renderFlowTrack(data) {
  const fortune = data.fortune;
  const items = [
    { layer: 'all', label: '本命', value: data.si_zhu.year, detail: palaceName(data, data.ming_gong_index) },
    { layer: 'da_xian', label: '大限', value: fortune.da_xian?.age_range || '--', detail: fortune.da_xian?.palace || '--' },
    { layer: 'liu_nian', label: '流年', value: fortune.liu_nian.gan_zhi, detail: fortune.liu_nian.palace },
    { layer: 'liu_yue', label: '流月', value: fortune.liu_yue.gan_zhi, detail: fortune.liu_yue.palace },
    { layer: 'liu_ri', label: '流日', value: fortune.liu_ri.gan_zhi, detail: fortune.liu_ri.palace },
    { layer: 'liu_shi', label: '流时', value: fortune.liu_shi.gan_zhi, detail: fortune.liu_shi.palace },
  ];
  document.querySelector('#flow-track').innerHTML = items.map(item => `<button type="button" data-layer="${item.layer}" aria-pressed="${item.layer === 'all'}" style="--track-color:${layerColors[item.layer]}"><b>${item.label}</b><strong>${item.value}</strong><small>${item.detail}</small></button>`).join('');
}

function renderFortune(data) {
  document.querySelector('#fortune-target').textContent = data.target.solar_time;
  document.querySelector('#fortune-lunar').textContent = data.target.lunar_date;
  const grid = document.querySelector('#fortune-grid');
  grid.innerHTML = '';
  ['da_xian', 'xiao_xian', 'liu_nian', 'liu_yue', 'liu_ri', 'liu_shi'].forEach(key => {
    const layer = data.fortune[key];
    if (!layer) return;
    const item = document.createElement('article');
    item.className = 'fortune-item';
    item.style.setProperty('--item-color', layerColors[key] || layerColors.all);
    const extra = key === 'liu_yue' ? `<p>斗君：${layer.dou_jun_palace}</p>` : key === 'da_xian' ? `<p>虚岁 ${layer.age_range}</p>` : '';
    const transformations = (layer.si_hua || []).map(value => `<span><b>${value.type}</b>${value.star}</span>`).join('');
    const transitStars = (layer.transit_stars || []).map(star => `<span><b>${escapeHtml(star.display_name)}</b><small>${escapeHtml(star.palace)}${star.liang_du ? ` · ${escapeHtml(star.liang_du)}` : ''}</small></span>`).join('');
    const transitSection = transitStars ? `<div class="fortune-star-section"><h4>运限流曜</h4><div class="fortune-star-list">${transitStars}</div></div>` : '';
    item.innerHTML = `<h3>${layerNames[key]}</h3><div class="fortune-place"><strong>${layer.gan_zhi || `${layer.age}岁`}</strong><span>${layer.palace}</span></div>${extra}<div class="sihua-list">${transformations}</div>${transitSection}`;
    grid.appendChild(item);
  });
}

function signedSeconds(value) {
  const sign = value > 0 ? '+' : '';
  return `${sign}${value} 秒`;
}

function renderCorrection(data) {
  const value = data.birth_time;
  const details = [
    ['模式', value.mode === 'true_solar_time' ? '真太阳时' : '北京时间'],
    ['记录时间', value.recorded_time],
    ['标准时间', value.standard_time],
    ['排盘时间', value.chart_time],
    ['出生地经度', `${value.longitude.toFixed(6)}°`],
    ['标准经线', `${value.standard_meridian.toFixed(6)}°`],
    ['夏令时', `${value.daylight_saving_minutes} 分钟`],
    ['经度校正', signedSeconds(value.longitude_offset_seconds)],
    ['均时差', signedSeconds(value.equation_of_time_seconds)],
    ['是否跨日', value.crossed_date_boundary ? '是' : '否'],
  ];
  document.querySelector('#correction-list').innerHTML = details.map(([term, detail]) => `<div><dt>${term}</dt><dd>${detail}</dd></div>`).join('');
  document.querySelector('#offset-total').textContent = signedSeconds(value.total_offset_seconds);
  const marker = document.querySelector('#offset-marker');
  marker.style.left = `${Math.max(4, Math.min(96, 50 + value.total_offset_seconds / 240))}%`;
}

function fragmentHeadline(fragment) {
  if (fragment.facts.rule_name) return fragment.facts.rule_name;
  if (fragment.type === 'palace_symbolism') return `${fragment.effect_palace}基础象义`;
  if (fragment.type === 'shen_sha_in_palace') return `${fragment.facts.shen_sha} · ${fragment.facts.system_label}`;
  if (fragment.type === 'unconfigured_star') return `${fragment.facts.star} · 待配置`;
  const relationNames = { self: '本宫', triad: '三合', opposite: '对宫' };
  const relation = relationNames[fragment.facts.relation] || '本宫';
  return `${fragment.facts.star || '四化'} · ${relation}`;
}

const fragmentTypeLabels = {
  palace_symbolism: '宫位定义',
  star_in_palace: '本宫星曜',
  four_directions: '三方四正',
  transformation: '四化修正',
  combination: '星曜组合',
  pattern: '格局',
  shen_sha_in_palace: '十二神',
  unconfigured_star: '未配置',
};

function fragmentDetail(fragment) {
  if (fragment.summary) return fragment.summary;
  if (fragment.type === 'transformation') {
    return `${fragment.facts.star}${fragment.facts.transformation}，实际位于${fragment.facts.physical_palace}`;
  }
  if (fragment.type === 'shen_sha_in_palace') return `${fragment.summary} ${fragment.boundary}`;
  if (fragment.type === 'unconfigured_star') return fragment.summary;
  const originals = fragment.star_original_meanings || [];
  return originals.map(item => item.definition).join('；') || '宫位基础定义与场景映射';
}

function evidenceLabel(evidence) {
  const identity = evidence.rule_id || evidence.entry_id || evidence.path || '';
  return [evidence.source, evidence.system, identity].filter(Boolean).join(' · ');
}

const patternStatusLabels = {
  formed: '成格',
  strengthened: '增强',
  weakened: '减弱',
  broken: '破格',
  tendency: '倾向',
};

function patternConditionNames(traces) {
  return (traces || []).map(trace => trace.name || trace.condition_id).filter(Boolean);
}

function patternMeta(fragment) {
  if (fragment.type !== 'pattern') return '';
  const status = fragment.facts?.status || 'formed';
  const trace = fragment.condition_trace || {};
  const required = patternConditionNames(trace.matched_conditions);
  const conditionLabel = status === 'tendency' ? '倾向条件' : '必要条件';
  const modifiers = fragment.modifiers || {};
  const groups = [
    ['增强', patternConditionNames(modifiers.enhancers)],
    ['减弱', patternConditionNames(modifiers.weakeners)],
    ['破格', patternConditionNames(modifiers.breakers)],
  ].filter(([, names]) => names.length);
  const modifierHtml = groups.map(([label, names]) => (
    `<span><b>${escapeHtml(label)}</b>${escapeHtml(names.join('、'))}</span>`
  )).join('');
  return `
    <div class="pattern-result">
      <span class="pattern-status pattern-status-${escapeHtml(status)}">${escapeHtml(patternStatusLabels[status] || status)}</span>
      <span><b>作用宫位</b>${escapeHtml(fragment.effect_palace || '')}</span>
      <span><b>${conditionLabel}</b>${escapeHtml(required.join('、') || '未提供条件名称')}</span>
      ${modifierHtml}
    </div>`;
}

function renderFragmentRows(fragments, signalSummary) {
  if (!fragments.length) return '<p class="analysis-empty">当前没有匹配内容</p>';
  const core = new Set(signalSummary.core);
  const supporting = new Set(signalSummary.supporting);
  const tensions = new Set(signalSummary.tensions);
  return `<div class="fragment-list">${fragments.map(fragment => {
    const facts = fragment.facts || {};
    const factMeta = [facts.physical_palace, { self: '本宫', triad: '三合', opposite: '对宫' }[facts.relation], facts.brightness, facts.transformation].filter(Boolean);
    const signals = [];
    if (core.has(fragment.fragment_id)) signals.push('<span class="signal-tag signal-core">核心</span>');
    if (supporting.has(fragment.fragment_id)) signals.push('<span class="signal-tag signal-support">辅助</span>');
    if (tensions.has(fragment.fragment_id)) signals.push('<span class="signal-tag signal-tension">张力</span>');
    const evidence = (fragment.evidence || []).map(item => `<code>${escapeHtml(evidenceLabel(item))}</code>`).join('');
    return `
      <article class="fragment-row">
        <div class="fragment-kind">${escapeHtml(fragmentTypeLabels[fragment.type] || fragment.type)}</div>
        <div class="fragment-body"><strong>${escapeHtml(fragmentHeadline(fragment))}</strong><p>${escapeHtml(fragmentDetail(fragment))}</p>${patternMeta(fragment)}<small>${factMeta.map(escapeHtml).join(' · ')}</small></div>
        <div class="fragment-source"><div>${signals.join('') || `<span>${escapeHtml(fragment.confidence?.level || 'fact')}</span>`}</div>${evidence}</div>
      </article>
    `;
  }).join('')}</div>`;
}

function renderFragmentSection(title, ids, fragmentMap, signalSummary, hint = '') {
  const fragments = ids.map(id => fragmentMap.get(id)).filter(Boolean);
  return `
    <section class="analysis-section">
      <div class="analysis-section-title"><div><h3>${escapeHtml(title)}</h3>${hint ? `<p>${escapeHtml(hint)}</p>` : ''}</div><span>${fragments.length} 条</span></div>
      ${renderFragmentRows(fragments, signalSummary)}
    </section>
  `;
}

function renderAnalysisPalace(palaceName) {
  if (!currentAnalysis) return;
  const palace = currentAnalysis.palaces.find(item => item.palace === palaceName);
  if (!palace) return;
  document.querySelectorAll('#analysis-palace-tabs button').forEach(button => {
    button.setAttribute('aria-pressed', String(button.dataset.palace === palaceName));
  });
  const fragmentMap = new Map(palace.fragments.map(fragment => [fragment.fragment_id, fragment]));
  const sections = palace.sections;
  const symbolism = fragmentMap.get(sections.palace_symbolism[0]);
  const directions = palace.four_directions;
  const originalRows = symbolism.original_meanings.map(item => `
    <div class="meaning-row"><b>${escapeHtml(item.concept)}</b><p>${escapeHtml(item.definition)}</p><code>${escapeHtml(item.id)}</code></div>
  `).join('');
  const derivedRows = symbolism.derived_meanings.map(item => `
    <div class="derived-row"><span>${escapeHtml(item.scenario)}</span><div><strong>${escapeHtml(item.meaning)}</strong><small>${escapeHtml(item.boundary)}</small></div><code>${escapeHtml(item.derived_from.join(' + '))}</code></div>
  `).join('');
  const summary = palace.signal_summary;
  const summaryBar = `
    <div class="signal-summary" aria-label="结构化信号摘要">
      <div><span>核心信号</span><strong>${summary.core.length}</strong></div>
      <div><span>辅助信号</span><strong>${summary.supporting.length}</strong></div>
      <div><span>张力信号</span><strong>${summary.tensions.length}</strong></div>
      <div><span>待配置</span><strong>${summary.coverage.unconfigured_occurrences}</strong></div>
    </div>`;
  document.querySelector('#analysis-content').innerHTML = `
    <header class="analysis-palace-heading">
      <div><span>${escapeHtml(palace.gan_zhi)}</span><h2>${escapeHtml(palace.palace)}</h2></div>
      <dl><div><dt>三合</dt><dd>${directions.triads.map(item => escapeHtml(item.palace)).join(' · ')}</dd></div><div><dt>对宫</dt><dd>${escapeHtml(directions.opposite.palace)}</dd></div><div><dt>主星</dt><dd>${palace.facts.primary_stars.map(escapeHtml).join(' · ') || '空宫'}</dd></div></dl>
    </header>
    ${summaryBar}
    <section class="analysis-section"><h3>宫位原始定义</h3><div class="meaning-list">${originalRows}</div></section>
    <section class="analysis-section"><h3>场景映射</h3><div class="derived-list">${derivedRows || '<p class="analysis-empty">当前筛选下无场景映射</p>'}</div></section>
    ${renderFragmentSection('本宫星曜', sections.self_stars, fragmentMap, summary, '星曜实际坐入当前焦点宫。')}
    ${renderFragmentSection('三方星曜', sections.triad_stars, fragmentMap, summary, '保留实际落宫，仅作为三合关系作用于当前宫。')}
    ${renderFragmentSection('对宫星曜', sections.opposite_stars, fragmentMap, summary, '保留实际落宫，仅作为对宫关系作用于当前宫。')}
    ${renderFragmentSection('四化修正', sections.transformations, fragmentMap, summary, '四化只在此处计权，星曜碎片仅保留关联。')}
    ${renderFragmentSection('星曜组合', sections.combinations || [], fragmentMap, summary, '组合描述星曜共同作用，保留实际宫位和三方四正关系。')}
    ${renderFragmentSection('格局匹配', sections.patterns, fragmentMap, summary, '格局由配置规则逐宫匹配，效果归属于当前焦点宫代表的人与领域。')}
    ${renderFragmentSection('十二神', sections.shen_sha, fragmentMap, summary, '四套系统独立展示，重名条目不会合并。')}
    ${renderFragmentSection('未配置内容', sections.unconfigured, fragmentMap, summary, '仅保留盘面事实，不进入推理结论。')}
  `;
}

function renderAnalysis(analysis) {
  currentAnalysis = analysis;
  document.querySelector('#analysis-title').textContent = '本命十二宫结构化解读';
  document.querySelector('#analysis-palace-count').textContent = analysis.palaces.length;
  document.querySelector('#analysis-fragment-count').textContent = analysis.fragments.length;
  document.querySelector('#analysis-config-version').textContent = analysis.config.symbolism_dictionary_version;
  const navigation = document.querySelector('#analysis-palace-tabs');
  navigation.innerHTML = analysis.palaces.map((palace, index) => `
    <button type="button" data-palace="${escapeHtml(palace.palace)}" aria-pressed="${index === 0}"><span>${escapeHtml(palace.gan_zhi)}</span><strong>${escapeHtml(palace.palace)}</strong><small>${palace.fragments.length} 条</small></button>
  `).join('');
  document.querySelector('#analysis-loading').hidden = true;
  document.querySelector('#analysis-workspace').hidden = false;
  renderAnalysisPalace(analysis.palaces[0].palace);
}

async function loadAnalysis(chart) {
  currentAnalysis = null;
  document.querySelector('#analysis-error').hidden = true;
  document.querySelector('#analysis-loading').hidden = false;
  document.querySelector('#analysis-workspace').hidden = true;
  document.querySelector('#analysis-title').textContent = '正在生成结构化碎片';
  try {
    const response = await fetch('/api/v1/ziwei/analysis', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chart, scope: { layers: ['natal'] } }),
    });
    const result = await response.json();
    if (!response.ok || !result.success) throw new Error(result.error?.message || '结构化解读失败');
    renderAnalysis(result.data.analysis);
  } catch (error) {
    document.querySelector('#analysis-loading').hidden = true;
    const analysisError = document.querySelector('#analysis-error');
    analysisError.textContent = error.message;
    analysisError.hidden = false;
  }
}

function render(data) {
  currentData = data;
  renderSummary(data);
  renderBoard(data);
  renderFlowTrack(data);
  renderFortune(data);
  renderCorrection(data);
  setActiveLayer('all');
  emptyState.hidden = true;
  resultContent.hidden = false;
  if (window.innerWidth <= 900) resultContent.scrollIntoView({ block: 'start' });
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  errorBox.hidden = true;
  setLoading(true);
  try {
    const payload = {
      birth: {
        ...dateAndTime('#birth-date', '#birth-time'),
        second: 0,
        gender: form.elements.gender.value,
      },
      time_correction: {
        mode: trueSolarInput.checked ? 'true_solar_time' : 'standard_time',
        longitude: Number(document.querySelector('#longitude').value),
        standard_meridian: Number(document.querySelector('#meridian').value),
        daylight_saving_minutes: Number(document.querySelector('#dst').value),
      },
      target: {
        ...dateAndTime('#target-date', '#target-time'),
        second: 0,
        age: Number(document.querySelector('#age').value),
        layers: ['decade', 'minor', 'annual', 'monthly', 'daily', 'hourly'],
      },
    };
    const response = await fetch('/api/v1/ziwei/fortune', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const result = await response.json();
    if (!response.ok || !result.success) throw new Error(result.error?.message || '排盘失败');
    render({ ...result.data.chart, target: result.data.target, fortune: result.data.fortune });
    await loadAnalysis(result.data.chart);
  } catch (error) {
    errorBox.textContent = error.message;
    errorBox.hidden = false;
  } finally {
    setLoading(false);
  }
});

document.querySelectorAll('.tabs button').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('.tabs button').forEach(item => item.setAttribute('aria-selected', String(item === button)));
  document.querySelectorAll('.tab-panel').forEach(panel => { panel.hidden = panel.id !== `tab-${button.dataset.tab}`; });
}));

document.querySelector('.layer-filter').addEventListener('click', event => {
  const button = event.target.closest('button[data-layer]');
  if (button && currentData) setActiveLayer(button.dataset.layer);
});

document.querySelector('#flow-track').addEventListener('click', event => {
  const button = event.target.closest('button[data-layer]');
  if (button && currentData) setActiveLayer(button.dataset.layer);
});

document.querySelector('#analysis-palace-tabs').addEventListener('click', event => {
  const button = event.target.closest('button[data-palace]');
  if (button) renderAnalysisPalace(button.dataset.palace);
});

document.querySelector('.board-view-toggle').addEventListener('click', event => {
  const button = event.target.closest('button[data-view]');
  if (!button) return;
  document.querySelector('#palace-board').dataset.view = button.dataset.view;
  document.querySelectorAll('.board-view-toggle button').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
});

trueSolarInput.addEventListener('change', () => { solarOptions.hidden = !trueSolarInput.checked; });
document.querySelector('#birth-date').addEventListener('change', updateAge);
document.querySelector('#target-date').addEventListener('change', updateAge);
window.addEventListener('DOMContentLoaded', () => form.requestSubmit());
