const astroForm = document.querySelector('#astro-form');
const esc = value => String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const fmt = value => Number(value).toFixed(4);
const SVG_NS = 'http://www.w3.org/2000/svg';
const SIGNS = [
  {name:'白羊', element:'fire',  mode:'cardinal'},
  {name:'金牛', element:'earth', mode:'fixed'},
  {name:'双子', element:'air',   mode:'mutable'},
  {name:'巨蟹', element:'water', mode:'cardinal'},
  {name:'狮子', element:'fire',  mode:'fixed'},
  {name:'处女', element:'earth', mode:'mutable'},
  {name:'天秤', element:'air',   mode:'cardinal'},
  {name:'天蝎', element:'water', mode:'fixed'},
  {name:'射手', element:'fire',  mode:'mutable'},
  {name:'摩羯', element:'earth', mode:'cardinal'},
  {name:'水瓶', element:'air',   mode:'fixed'},
  {name:'双鱼', element:'water', mode:'mutable'},
];
const symbols = {sun:'☉',moon:'☽',mercury:'☿',venus:'♀',mars:'♂',jupiter:'♃',saturn:'♄',uranus:'♅',neptune:'♆',pluto:'♇',true_node:'☊',chiron:'⚷'};
const colors = ['#b14b3d','#4c7a68','#48729a','#a16207','#7c5b9e','#4c6475','#b36b3f','#557c78','#6b5d4d','#8e4f69','#3d777d','#8b6d42'];
const ANGLE_LABELS = {ascendant:'上升点', descendant:'下降点', midheaven:'中天', imum_coeli:'天底'};
const ANGLE_ORDER = ['ascendant', 'descendant', 'midheaven', 'imum_coeli'];
// 圆盘半径布局（viewBox 640，圆心 320）。约束：度数标签统一环 R=210，与最外层星体
// (178+11) 保持 32px 径向余量，即使径向对齐也不会压到星体或符号；宫位号收到内圈 R=104，
// 与最内层星体错开；黄道环按四元素着色，模式环为次级信号。
const WHEEL = {
  cx: 320, cy: 320, rim: 282,
  signInner: 232, signLabel: 257,
  modeInner: 220,
  houseNumber: 104, houseInner: 92,
  aspect: 72, axisLabel: 302,
  labelRadius: 210, dotRadii: [178, 152, 126], dotR: 11,
  dotSeparation: 12, labelSeparation: 12,
};
function table(headers, rows) { return `<table><thead><tr>${headers.map(h => `<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(row => `<tr>${row.map(v => `<td>${esc(v)}</td>`).join('')}</tr>`).join('')}</tbody></table>`; }
function polar(cx, cy, radius, longitude) { const angle = (longitude - 90) * Math.PI / 180; return [cx + radius * Math.cos(angle), cy + radius * Math.sin(angle)]; }
function svg(name, attrs = {}) { const node = document.createElementNS(SVG_NS, name); Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value)); return node; }
function annulus(cx, cy, outer, inner, mid, half = 15) {
  const [ox1, oy1] = polar(cx, cy, outer, mid - half), [ox2, oy2] = polar(cx, cy, outer, mid + half);
  const [ix2, iy2] = polar(cx, cy, inner, mid + half), [ix1, iy1] = polar(cx, cy, inner, mid - half);
  return `M ${ox1} ${oy1} A ${outer} ${outer} 0 0 1 ${ox2} ${oy2} L ${ix2} ${iy2} A ${inner} ${inner} 0 0 0 ${ix1} ${iy1} Z`;
}
function spreadLabels(items, separation) {
  const total = items.length;
  if (total < 2) return;
  let cut = 0, widest = -1;
  for (let index = 0; index < total; index += 1) {
    const gap = items[(index + 1) % total].angle + (index === total - 1 ? 360 : 0) - items[index].angle;
    if (gap > widest) { widest = gap; cut = (index + 1) % total; }
  }
  const sequence = items.slice(cut).concat(items.slice(0, cut));
  for (let index = 1; index < total; index += 1) {
    sequence[index].angle = Math.max(sequence[index].angle, sequence[index - 1].angle + separation);
  }
}
function degreeLabel(longitude) {
  const normalized = ((Number(longitude) % 360) + 360) % 360;
  const degree = Math.floor(normalized % 30);
  const minute = Math.floor((normalized % 1) * 60);
  return `${String(degree).padStart(2, '0')}°${String(minute).padStart(2, '0')}′`;
}
function drawWheel(root, data, orientation) {
  root.replaceChildren();
  // 黄经逆时针排列：上升点时把上升点转到左侧，白羊在顶时把 0° 白羊转到正上方。
  const base = orientation === 'aries' ? 0 : (Number(data.angles?.ascendant ?? 0) + 270) % 360;
  const screen = longitude => ((base - Number(longitude)) % 360 + 360) % 360;
  const rotate = (radius, longitude) => polar(WHEEL.cx, WHEEL.cy, radius, screen(longitude));

  SIGNS.forEach((sign, index) => {
    const mid = screen(index * 30 + 15);
    root.appendChild(svg('path', {d: annulus(WHEEL.cx, WHEEL.cy, WHEEL.rim, WHEEL.signInner, mid), class: `sign-sector element-${sign.element}`}));
    root.appendChild(svg('path', {d: annulus(WHEEL.cx, WHEEL.cy, WHEEL.signInner, WHEEL.modeInner, mid), class: `mode-sector mode-${sign.mode}`}));
    const [x, y] = rotate(WHEEL.signLabel, index * 30 + 15);
    const label = svg('text', {x, y, class: 'sign-label'});
    label.textContent = sign.name;
    root.appendChild(label);
  });

  [WHEEL.rim, WHEEL.signInner, WHEEL.modeInner, WHEEL.houseInner, WHEEL.aspect].forEach((radius, index) => {
    root.appendChild(svg('circle', {cx: WHEEL.cx, cy: WHEEL.cy, r: radius, class: index === 0 ? 'ring' : 'inner-ring'}));
  });

  const cusps = data.houses.map(house => Number(house.cusp));
  cusps.forEach((cusp, index) => {
    const axis = index % 3 === 0;
    const [x1, y1] = rotate(WHEEL.houseInner, cusp);
    const [x2, y2] = rotate(axis ? WHEEL.rim : WHEEL.modeInner, cusp);
    root.appendChild(svg('line', {x1, y1, x2, y2, class: axis ? 'house-line major' : 'house-line'}));
    const span = (((cusps[(index + 1) % 12] - cusp) % 360) + 360) % 360 || 30;
    // 宫位扇区默认不可见，只作为「布局速读 → 圆盘」高亮的承载层。
    root.appendChild(svg('path', {
      d: annulus(WHEEL.cx, WHEEL.cy, WHEEL.modeInner, WHEEL.houseInner, cusp + span / 2, Math.max(span / 2, 0.5)),
      class: 'house-sector', 'data-house': String(index + 1),
    }));
    const [hx, hy] = rotate(WHEEL.houseNumber, cusp + span / 2);
    const label = svg('text', {x: hx, y: hy, class: 'house-label'});
    label.textContent = index + 1;
    root.appendChild(label);
  });

  [['ascendant', 'ASC'], ['descendant', 'DSC'], ['midheaven', 'MC'], ['imum_coeli', 'IC']].forEach(([key, text]) => {
    if (data.angles?.[key] === undefined) return;
    const [x, y] = rotate(WHEEL.axisLabel, data.angles[key]);
    const label = svg('text', {x, y, class: `axis-label axis-${key}`});
    label.textContent = text;
    root.appendChild(label);
  });

  (data.aspects || []).forEach(aspect => {
    const first = data.planets.find(planet => planet.id === aspect.first);
    const second = data.planets.find(planet => planet.id === aspect.second);
    if (!first || !second) return;
    const [x1, y1] = rotate(WHEEL.aspect, first.longitude);
    const [x2, y2] = rotate(WHEEL.aspect, second.longitude);
    root.appendChild(svg('line', {x1, y1, x2, y2, class: `aspect-line aspect-${aspect.type}`}));
  });

  const palette = new Map(data.planets.map((planet, index) => [planet.id, colors[index % colors.length]]));
  const planets = [...data.planets].sort((first, second) => first.longitude - second.longitude);
  const levelCursor = WHEEL.dotRadii.map(() => -Infinity);
  planets.forEach(planet => {
    let level = levelCursor.findIndex(cursor => planet.longitude - cursor >= WHEEL.dotSeparation);
    if (level === -1) level = levelCursor.indexOf(Math.min(...levelCursor));
    levelCursor[level] = planet.longitude;
    planet.level = level;
  });

  const labels = planets.map(planet => ({planet, dotAngle: screen(planet.longitude), angle: screen(planet.longitude)}));
  labels.sort((first, second) => first.angle - second.angle);
  spreadLabels(labels, WHEEL.labelSeparation);

  labels.forEach(({planet, dotAngle, angle}) => {
    const [dx, dy] = polar(WHEEL.cx, WHEEL.cy, WHEEL.dotRadii[planet.level], dotAngle);
    const [lx, ly] = polar(WHEEL.cx, WHEEL.cy, WHEEL.labelRadius, angle);
    if (Math.abs(((angle - dotAngle + 540) % 360) - 180) > 2) {
      const [mx, my] = polar(WHEEL.cx, WHEEL.cy, WHEEL.labelRadius, dotAngle);
      root.appendChild(svg('path', {d: `M ${dx} ${dy} L ${mx} ${my} L ${lx} ${ly}`, class: 'planet-leader'}));
    } else {
      root.appendChild(svg('line', {x1: dx, y1: dy, x2: lx, y2: ly, class: 'planet-leader'}));
    }
    const group = svg('g', {class: 'planet', 'data-point': planet.id, tabindex: '0', role: 'img', 'aria-label': `${planet.name} ${fmt(planet.longitude)}°，第 ${planet.house} 宫${planet.retrograde ? '，逆行' : ''}`});
    const title = svg('title');
    title.textContent = `${planet.name} ${fmt(planet.longitude)}° ${planet.sign_name} 第 ${planet.house} 宫`;
    const dot = svg('circle', {cx: dx, cy: dy, r: WHEEL.dotR, fill: palette.get(planet.id), class: 'planet-dot'});
    const glyph = svg('text', {x: dx, y: dy, class: 'planet-glyph'});
    glyph.textContent = symbols[planet.id] || planet.name.slice(0, 1);
    const degree = svg('text', {x: lx, y: ly, class: 'planet-degree'});
    degree.textContent = `${degreeLabel(planet.longitude)}${planet.retrograde ? 'R' : ''}`;
    group.append(title, dot, glyph, degree);
    root.appendChild(group);
  });
}
let wheelChart = null;
let wheelOrientation = 'ascendant';
let wheelHighlight = {houses: [], label: ''};
function applyWheelHighlight() {
  const root = document.querySelector('#astro-wheel');
  if (!root) return;
  root.querySelectorAll('.house-sector').forEach(node => {
    node.classList.toggle('on', wheelHighlight.houses.includes(Number(node.dataset.house)));
  });
  const note = document.querySelector('#astro-wheel-highlight');
  if (!note) return;
  if (!wheelHighlight.houses.length) {
    note.hidden = true;
    note.textContent = '';
    return;
  }
  note.hidden = false;
  note.innerHTML = `<strong>圆盘高亮</strong> ${esc(wheelHighlight.label)}（${esc(wheelHighlight.houses.join('、'))} 宫）<button id="astro-wheel-highlight-clear" type="button">清除高亮</button>`;
}
function highlightWheelHouses(houses, label) {
  wheelHighlight = {houses: [...houses], label};
  applyWheelHighlight();
}
function renderWheel() {
  const root = document.querySelector('#astro-wheel');
  if (!root || !wheelChart) return;
  drawWheel(root, wheelChart, wheelOrientation);
  root.setAttribute('aria-label', wheelOrientation === 'aries' ? '本命盘圆盘图，0° 白羊在顶部，黄道逆时针排列' : '本命盘圆盘图，上升点在左侧，黄道逆时针排列');
  applyWheelHighlight();
}
document.querySelectorAll('[data-orientation]').forEach(button => {
  button.addEventListener('click', () => {
    wheelOrientation = button.dataset.orientation;
    document.querySelectorAll('[data-orientation]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    renderWheel();
  });
});
function buildAstroPrompt(chart, analysis) {
  const packet = {
    chart_type: chart.chart_type,
    input: chart.input,
    calculation: chart.calculation,
    structured: chart.structured,
    analysis: analysis || null,
  };
  return `你是一名严谨的西洋占星数据分析助手。请只依据下方 JSON 中的可验证事实进行分析，不要臆造缺失信息，不要把占星内容表述为确定性的人生结论。\n\n请按以下顺序输出：1. 数据校验与精度说明；2. 核心点位（太阳、月亮、上升点）；3. 元素、模式和宫位分布；4. 主要派生信号及其证据；5. 相位网络中的重点连接；6. 明确区分事实、推断和不确定性。保留所有点位 ID、规则 ID 和数值证据。\n\n星盘结构化数据：\n${JSON.stringify(packet, null, 2)}`;
}
async function loadAstroAnalysis(chart) {
  try {
    const response = await fetch('/api/v1/astro/analysis', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({chart})});
    if (!response.ok) return null;
    const payload = await response.json();
    return payload.success ? payload.data.analysis : null;
  } catch (error) { return null; }
}
const astroTabs = [...document.querySelectorAll('[role="tab"][aria-controls^="astro-"]')];
function activateAstroTab(tab) {
  astroTabs.forEach(item => {
    const selected = item === tab;
    item.setAttribute('aria-selected', String(selected));
    item.tabIndex = selected ? 0 : -1;
    const panel = document.getElementById(item.getAttribute('aria-controls'));
    if (panel) panel.hidden = !selected;
  });
}
astroTabs.forEach((tab, index) => {
  tab.addEventListener('click', () => activateAstroTab(tab));
  tab.addEventListener('keydown', event => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const offset = event.key === 'ArrowLeft' ? -1 : event.key === 'ArrowRight' ? 1 : 0;
    const nextIndex = event.key === 'Home' ? 0 : event.key === 'End' ? astroTabs.length - 1 : (index + offset + astroTabs.length) % astroTabs.length;
    astroTabs[nextIndex].focus();
    activateAstroTab(astroTabs[nextIndex]);
  });
});
/* ---------- 本命解读：布局速读（方案 N2） ---------- */
const READING_SLOT_LABELS = {ascendant: '上升', sun: '太阳', moon: '月亮', chart_ruler: '命主星'};
const READING_DIMENSION_LABELS = {layout: '布局', distribution: '分布', concentration: '集中度', aspect: '相位', angularity: '角宫', motion: '逆行', placement: '落点', field: '宫位'};
const ELEMENT_LABELS = {fire: '火', earth: '土', air: '风', water: '水'};
const MODALITY_LABELS = {cardinal: '基本', fixed: '固定', mutable: '变动'};

function layoutBar(label, segments, options = {}) {
  const clickable = Boolean(options.clickable);
  const body = segments.map(segment => {
    const grow = Math.max(Number(segment.value) || 0, 0.4);
    const tone = segment.tone ? ` tone-${segment.tone}` : '';
    const title = `${segment.label} ${segment.value}`;
    if (!clickable) return `<span class="layout-bar-seg${tone}" style="flex:${grow}" title="${esc(title)}"><span>${esc(segment.label)}</span><b>${esc(segment.value)}</b></span>`;
    const houses = (segment.houses || []).join(',');
    const segmentLabel = options.label ? `${options.label} · ${segment.label}` : segment.label;
    return `<button type="button" class="layout-bar-seg${tone}" style="flex:${grow}" data-houses="${esc(houses)}" data-label="${esc(segmentLabel)}" aria-pressed="false" title="在圆盘上高亮 ${esc(title)}"><span>${esc(segment.label)}</span><b>${esc(segment.value)}</b></button>`;
  }).join('');
  return `<div class="layout-bar"><span class="layout-bar-label">${esc(label)}</span><div class="layout-bar-track">${body}</div>${options.totalText ? `<span class="layout-bar-total">${esc(options.totalText)}</span>` : ''}</div>`;
}
function clearLayoutSelection() {
  document.querySelectorAll('#astro-layout-bars .layout-bar-seg.is-active').forEach(node => {
    node.classList.remove('is-active');
    node.setAttribute('aria-pressed', 'false');
  });
  highlightWheelHouses([], '');
}
function renderNatalReading(reading) {
  natalReading = reading;
  const stats = reading.layout_stats || {};
  const hemispheres = Object.fromEntries((((stats.hemispheres || {}).items) || []).map(item => [item.name, item]));
  const core = reading.highlights || {};
  document.querySelector('#astro-core-row').innerHTML = ['ascendant', 'sun', 'moon', 'chart_ruler']
    .filter(slot => core[slot])
    .map(slot => `<article class="core-card"><small>${esc(READING_SLOT_LABELS[slot])}</small><strong>${esc(core[slot].title)}</strong><p>${esc(core[slot].summary)}</p></article>`)
    .join('');
  const total = (stats.hemispheres || {}).counted_total || 0;
  const network = stats.aspect_network || {};
  const hemisphereSegments = pair => [
    {label: pair[0][1], value: (hemispheres[pair[0][0]] || {}).count || 0, houses: (hemispheres[pair[0][0]] || {}).houses, tone: pair[0][2]},
    {label: pair[1][1], value: (hemispheres[pair[1][0]] || {}).count || 0, houses: (hemispheres[pair[1][0]] || {}).houses, tone: pair[1][2]},
  ];
  document.querySelector('#astro-layout-bars').innerHTML = [
    layoutBar('左右半球', hemisphereSegments([['left', '左半盘', 'earth'], ['right', '右半盘', 'air']]), {clickable: true, label: '左右半球', totalText: `共 ${total} 个行星`}),
    layoutBar('上下半球', hemisphereSegments([['above', '上半盘', 'cinnabar'], ['below', '下半盘', 'jade']]), {clickable: true, label: '上下半球', totalText: `共 ${total} 个行星`}),
    layoutBar('象限', (((stats.quadrants || {}).items) || []).map(item => ({label: `第${item.name}象限`, value: item.count, houses: item.houses, tone: 'muted'})), {clickable: true, label: '象限', totalText: `共 ${total} 个行星`}),
    layoutBar('相位', [
      {label: '顺畅', value: network.harmony || 0, tone: 'jade'},
      {label: '张力', value: network.tension || 0, tone: 'cinnabar'},
      {label: '合相/梅花', value: network.neutral || 0, tone: 'muted'},
    ], {totalText: `共 ${network.total || 0} 条`}),
  ].join('');
  const groups = new Map();
  (reading.layout || []).forEach(item => {
    if (!groups.has(item.dimension)) groups.set(item.dimension, []);
    groups.get(item.dimension).push(item);
  });
  document.querySelector('#astro-layout-notes').innerHTML = [...groups].map(([dimension, items]) => {
    const notes = items.map(item => {
      const scale = item.count === null || item.count === undefined ? ''
        : ` · ${esc(item.count)}${item.total === null || item.total === undefined ? '' : `/${esc(item.total)}`}`;
      return `<li><p>${esc(item.text)}</p><span class="layout-note-meta">${esc(item.rule_id)} · r${esc(item.revision)}${scale}</span></li>`;
    }).join('');
    return `<li class="layout-note-group"><h3>${esc(READING_DIMENSION_LABELS[dimension] || dimension)}</h3><ul>${notes}</ul></li>`;
  }).join('');
  const definitions = [
    ['半球与象限口径', (stats.hemispheres || {}).definition],
    ['参与统计的点位', (((stats.hemispheres || {}).counted_point_names) || []).join('、')],
    ['相位网络口径', (stats.aspect_network || {}).definition],
    ['空宫', ((((stats.house_occupancy || {}).empty_houses) || []).join('、')) || '无'],
  ].filter(([, value]) => value);
  document.querySelector('#astro-layout-defs-body').innerHTML = definitions
    .map(([name, value]) => `<div><dt>${esc(name)}</dt><dd>${esc(value)}</dd></div>`).join('');
  const distribution = reading.distribution || {};
  document.querySelector('#astro-distribution').innerHTML = [
    layoutBar('元素', Object.entries(distribution.element_counts || {}).map(([key, value]) => ({label: ELEMENT_LABELS[key] || key, value, tone: key})), {totalText: '十大行星'}),
    layoutBar('模式', Object.entries(distribution.modality_counts || {}).map(([key, value]) => ({label: MODALITY_LABELS[key] || key, value, tone: 'muted'})), {totalText: '十大行星'}),
  ].join('');
  document.querySelector('#astro-boundaries').innerHTML = (reading.boundaries || []).map(item => `<li>${esc(item)}</li>`).join('');
  document.querySelector('#astro-layout-meta').textContent = `${reading.ruler_system === 'traditional' ? '传统主星' : '现代主星'} · 命中 ${reading.coverage.matched} / 事实 ${reading.coverage.facts} · 未覆盖 ${reading.coverage.uncovered}`;
  renderPointCards();
  renderHouseCards();
  renderAspects();
}
/* ---------- 本命解读：逐点位 / 十二宫 / 相位卡片（方案 N4） ---------- */
const SIGN_SEQUENCE = ['aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 'libra', 'scorpio', 'sagittarius', 'capricorn', 'aquarius', 'pisces'];
const MARKER_LABELS = {angular_planet: '角宫', retrograde_point: '逆行', house_stellium: '宫位聚集', sign_stellium: '星座聚集'};
let natalReading = null;
let pointSort = 'point';

function markerChips(point, aspectById) {
  return (point.markers || []).map(signalId => {
    const aspect = aspectById.get(signalId);
    const text = aspect ? `${aspect.title} ${aspect.orb}°` : (MARKER_LABELS[signalId.split(':')[0]] || signalId);
    return `<span class="natal-marker" title="${esc(signalId)}">${esc(text)}</span>`;
  }).join('');
}
function blockList(blocks) {
  return (blocks || []).map(block => `<div><dt>${esc(block.label || block.slot)}</dt><dd>${esc(block.text)}</dd></div>`).join('');
}
function pointCard(point, aspectById) {
  const evidence = point.evidence || {};
  const facts = [];
  if (typeof evidence.longitude === 'number') facts.push(`黄经 ${fmt(evidence.longitude)}°`);
  if (typeof evidence.degree_in_sign === 'number') facts.push(`座内 ${fmt(evidence.degree_in_sign)}°`);
  if (evidence.house) facts.push(`第${evidence.house}宫${evidence.house_system ? `（${esc(evidence.house_system)}，宫头 ${fmt(evidence.house_cusp)}°）` : ''}`);
  return `<details class="natal-card" id="natal-point-${esc(point.point_id)}" data-point="${esc(point.point_id)}" data-house="${esc(point.house || '')}" data-sign="${esc(point.sign_id || '')}">
    <summary>
      <span class="natal-card-title"><strong>${esc(point.title)}</strong><small>${esc(point.summary)}</small></span>
      <span class="natal-card-tags">${point.retrograde ? '<span class="natal-retro">R</span>' : ''}${markerChips(point, aspectById)}</span>
    </summary>
    <div class="natal-card-body">
      <dl class="natal-blocks">${blockList(point.blocks)}</dl>
      <p class="natal-evidence">证据：${esc(facts.join('、')) || '—'}</p>
      <p class="natal-rule">rule: ${esc((point.blocks || []).map(block => block.rule_id).join(' · '))}</p>
      <button type="button" class="natal-locate" data-locate="${esc(point.point_id)}">在圆盘上查看</button>
    </div>
  </details>`;
}
function houseCard(house) {
  const chips = (house.points || []).map(point =>
    `<span class="natal-chip${point.virtual ? ' is-virtual' : ''}">${esc(point.point_name)}</span>`).join('');
  const ruler = house.ruler || {};
  const rulerText = ruler.point_id
    ? `${esc(ruler.point_name)} · ${esc(ruler.sign_name)} · 第${esc(ruler.house)}宫`
    : '未找到宫主星';
  const system = house.evidence && house.evidence.house_system;
  return `<details class="natal-card" id="natal-house-${esc(house.house)}" data-house="${esc(house.house)}">
    <summary>
      <span class="natal-card-title"><strong>${esc(house.title)}</strong><small>${esc(house.summary)}</small></span>
      <span class="natal-card-tags"><span class="natal-chip is-muted">主星 ${esc(ruler.point_name || '—')}</span></span>
    </summary>
    <div class="natal-card-body">
      <p class="natal-chips">${chips || '<span class="natal-chip is-empty">宫内无点位</span>'}</p>
      <dl class="natal-blocks">${blockList(house.blocks)}</dl>
      <p class="natal-evidence">证据：宫头 ${fmt(house.cusp)}°${system ? ` · ${esc(system)}` : ''}</p>
      <p class="natal-rule">宫主星：${rulerText}</p>
    </div>
  </details>`;
}
function aspectRow(aspect) {
  return `<div class="natal-aspect tone-${esc(aspect.tone)}${aspect.tight ? ' is-tight' : ''}">
    <span class="natal-aspect-title"><strong>${esc(aspect.title)}</strong><small>${esc(aspect.summary)}</small></span>
    <span class="natal-aspect-meta">${esc(aspect.label)} · ${fmt(aspect.orb)}° · ${esc(aspect.phase_label)}${aspect.tight ? ' · 紧密' : ''}</span>
  </div>`;
}
function renderPointCards() {
  const root = document.querySelector('#astro-point-cards');
  if (!root || !natalReading) return;
  const aspectById = new Map((natalReading.aspects || []).flatMap(aspect =>
    (aspect.signal_ids || []).map(signalId => [signalId, aspect])));
  const points = [...(natalReading.points || [])];
  if (pointSort === 'house') points.sort((first, second) => (first.house || 99) - (second.house || 99) || first.point_id.localeCompare(second.point_id));
  else if (pointSort === 'sign') points.sort((first, second) => SIGN_SEQUENCE.indexOf(first.sign_id) - SIGN_SEQUENCE.indexOf(second.sign_id) || first.point_id.localeCompare(second.point_id));
  root.innerHTML = points.map(point => pointCard(point, aspectById)).join('');
}
function renderHouseCards() {
  const root = document.querySelector('#astro-house-cards');
  if (root && natalReading) root.innerHTML = (natalReading.houses || []).map(houseCard).join('');
}
function renderAspects() {
  const root = document.querySelector('#astro-aspect-list');
  if (root && natalReading) root.innerHTML = (natalReading.aspects || []).map(aspectRow).join('');
}
function focusPlanet(pointId) {
  const root = document.querySelector('#astro-wheel');
  if (!root) return;
  root.querySelectorAll('.planet.is-focused').forEach(node => node.classList.remove('is-focused'));
  const target = root.querySelector(`.planet[data-point="${pointId}"]`);
  if (!target) return;
  target.classList.add('is-focused');
  target.scrollIntoView({block: 'center', behavior: 'smooth'});
}
function openPointCard(pointId) {
  activateAstroTab(document.querySelector('#astro-reading-tab'));
  const card = document.getElementById(`natal-point-${pointId}`);
  if (!card) return;
  card.open = true;
  card.scrollIntoView({block: 'center', behavior: 'smooth'});
  const summary = card.querySelector('summary');
  if (summary) summary.focus();
}
document.querySelectorAll('[data-sort]').forEach(button => {
  button.addEventListener('click', () => {
    pointSort = button.dataset.sort;
    document.querySelectorAll('[data-sort]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    renderPointCards();
  });
});
document.querySelector('#astro-point-cards').addEventListener('click', event => {
  const button = event.target.closest('[data-locate]');
  if (!button) return;
  activateAstroTab(document.querySelector('#astro-chart-tab'));
  focusPlanet(button.dataset.locate);
});
document.querySelector('#astro-wheel').addEventListener('click', event => {
  const group = event.target.closest('.planet[data-point]');
  if (group) openPointCard(group.dataset.point);
});
document.querySelector('#astro-wheel').addEventListener('keydown', event => {
  if (!['Enter', ' '].includes(event.key)) return;
  const group = event.target.closest('.planet[data-point]');
  if (!group) return;
  event.preventDefault();
  openPointCard(group.dataset.point);
});
async function loadNatalReading(chart) {
  try {
    const response = await fetch('/api/v1/astro/natal-reading', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({chart})});
    if (!response.ok) return null;
    const payload = await response.json();
    return payload.success ? payload.data : null;
  } catch (error) { return null; }
}
async function refreshNatalReading(chart) {
  const empty = document.querySelector('#astro-reading-empty');
  const reading = await loadNatalReading(chart);
  if (!reading) {
    natalReading = null;
    ['#astro-core-row', '#astro-layout-bars', '#astro-layout-notes', '#astro-layout-defs-body',
     '#astro-distribution', '#astro-boundaries', '#astro-point-cards', '#astro-house-cards',
     '#astro-aspect-list']
      .forEach(selector => { document.querySelector(selector).innerHTML = ''; });
    document.querySelector('#astro-layout-meta').textContent = '解读不可用';
    empty.hidden = false;
    empty.textContent = '暂时无法生成本命布局解读，请稍后重试；「本命盘」与「结构事实」页签不受影响。';
    return;
  }
  empty.hidden = true;
  renderNatalReading(reading);
}
document.querySelector('#astro-layout-bars').addEventListener('click', event => {
  const button = event.target.closest('[data-houses]');
  if (!button) return;
  const houses = (button.dataset.houses || '').split(',').map(Number).filter(Boolean);
  if (!houses.length) return;
  const wasActive = button.classList.contains('is-active');
  clearLayoutSelection();
  if (wasActive) return;
  button.classList.add('is-active');
  button.setAttribute('aria-pressed', 'true');
  activateAstroTab(document.querySelector('#astro-chart-tab'));
  highlightWheelHouses(houses, button.dataset.label || '');
});
document.querySelector('#astro-wheel-highlight').addEventListener('click', event => {
  if (event.target.closest('#astro-wheel-highlight-clear')) clearLayoutSelection();
});
async function copyPrompt() {
  const text = document.querySelector('#astro-prompt-text').value;
  const status = document.querySelector('#astro-copy-status');
  try {
    if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(text);
    else { const area = document.querySelector('#astro-prompt-text'); area.select(); document.execCommand('copy'); area.setSelectionRange(0, 0); }
    status.textContent = '已复制，可粘贴到 AI 对话中';
  } catch (error) { status.textContent = '复制失败，请手动选择文本复制'; }
}
document.querySelector('#astro-copy-prompt').addEventListener('click', copyPrompt);
astroForm.addEventListener('submit', async event => {
  event.preventDefault(); const error = document.querySelector('#astro-error'); error.hidden = true; const [year,month,day] = document.querySelector('#astro-date').value.split('-').map(Number); const [hour,minute,second = 0] = document.querySelector('#astro-time').value.split(':').map(Number); const zodiac = document.querySelector('#astro-zodiac').value; const request = {date:{year,month,day,hour,minute,second},utc_offset_minutes:Number(document.querySelector('#astro-offset').value),location:{latitude:Number(document.querySelector('#astro-lat').value),longitude:Number(document.querySelector('#astro-lon').value)},zodiac,ayanamsa:zodiac === 'sidereal' ? 'fagan_bradley' : 'none',house_system:document.querySelector('#astro-houses').value,include_aspects:true,allow_moshier_fallback:document.querySelector('#astro-moshier').checked}; const button = astroForm.querySelector('button'); button.disabled = true;
  try { const response = await fetch('/api/v1/astro/charts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request)}); const payload = await response.json(); if (!response.ok || !payload.success) throw new Error(payload.error?.message || '计算失败'); const data = payload.data; document.querySelector('#astro-empty').hidden = true; document.querySelector('#astro-output').hidden = false; document.querySelector('#astro-title').textContent = `${data.input.zodiac} · ${data.input.house_system}`; document.querySelector('#astro-meta').textContent = `JD ${fmt(data.calculation.julian_day_ut)} · ${data.calculation.precision_mode}${data.calculation.warnings.length ? ` · ${data.calculation.warnings.join('、')}` : ''}`; document.querySelector('#astro-angles').innerHTML = Object.entries(data.angles).sort((first, second) => ANGLE_ORDER.indexOf(first[0]) - ANGLE_ORDER.indexOf(second[0])).map(([key,value]) => `<div><small>${esc(ANGLE_LABELS[key] || key)}</small><strong>${fmt(value)}°</strong></div>`).join(''); wheelChart = data; renderWheel(); clearLayoutSelection(); await refreshNatalReading(data); document.querySelector('#astro-planets').innerHTML = table(['点位','黄经','星座','落宫','速度','状态'], data.planets.map(p => [p.name,`${fmt(p.longitude)}°`,p.sign_name,p.house,`${fmt(p.longitude_speed)}°/day`,p.retrograde ? '逆行' : '顺行'])); document.querySelector('#astro-houses-list').innerHTML = table(['宫位','宫头','星座'], data.houses.map(h => [h.number,`${fmt(h.cusp)}°`,h.sign_name])); document.querySelector('#astro-aspects').innerHTML = table(['点位','点位','相位','偏差'], data.aspects.map(a => [a.first,a.second,a.type,`${fmt(a.orb)}°`])); document.querySelector('#astro-prompt-text').value = buildAstroPrompt(data, await loadAstroAnalysis(data)); } catch (err) { error.textContent = err.message; error.hidden = false; } finally { button.disabled = false; }
});
