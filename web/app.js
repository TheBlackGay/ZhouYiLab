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
  Object.entries(data.fortune).forEach(([key, layer]) => {
    if (layer && Number.isInteger(layer.palace_index)) {
      (flagsByPalace[layer.palace_index] ||= []).push({ key, label: layerNames[key] });
    }
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
    const flags = palaceFlags.map(item => `<span class="flow-flag ${item.key}">${item.label}</span>`).join('');
    node.innerHTML = `<header><h3>${palace.name}</h3><span class="branch">${palace.gan_zhi}</span></header><div class="star-zone"><small class="zone-label">主星</small><div class="stars">${primary || '<span class="star">空宫</span>'}</div></div><div class="secondary-zone"><small class="zone-label">辅星 · 煞曜 · 杂曜</small><div class="stars">${secondary || '<span class="star">无</span>'}</div></div><div class="flow-flags">${flags}</div>`;
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
    item.innerHTML = `<h3>${layerNames[key]}</h3><div class="fortune-place"><strong>${layer.gan_zhi || `${layer.age}岁`}</strong><span>${layer.palace}</span></div>${extra}<div class="sihua-list">${transformations}</div>`;
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
      birth: dateAndTime('#birth-date', '#birth-time'),
      gender: form.elements.gender.value,
      age: Number(document.querySelector('#age').value),
      options: {
        trueSolarTime: trueSolarInput.checked,
        longitude: Number(document.querySelector('#longitude').value),
        standardMeridian: Number(document.querySelector('#meridian').value),
        daylightSavingMinutes: Number(document.querySelector('#dst').value),
      },
      target: dateAndTime('#target-date', '#target-time'),
    };
    const response = await fetch('/api/calculate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const data = await response.json();
    if (!response.ok || data.error) throw new Error(data.error || '排盘失败');
    render(data);
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
