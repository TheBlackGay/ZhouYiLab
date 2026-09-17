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
function annulus(cx, cy, outer, inner, mid) {
  const [ox1, oy1] = polar(cx, cy, outer, mid - 15), [ox2, oy2] = polar(cx, cy, outer, mid + 15);
  const [ix2, iy2] = polar(cx, cy, inner, mid + 15), [ix1, iy1] = polar(cx, cy, inner, mid - 15);
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
    const group = svg('g', {class: 'planet', tabindex: '0', role: 'img', 'aria-label': `${planet.name} ${fmt(planet.longitude)}°，第 ${planet.house} 宫${planet.retrograde ? '，逆行' : ''}`});
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
function renderWheel() {
  const root = document.querySelector('#astro-wheel');
  if (!root || !wheelChart) return;
  drawWheel(root, wheelChart, wheelOrientation);
  root.setAttribute('aria-label', wheelOrientation === 'aries' ? '本命盘圆盘图，0° 白羊在顶部，黄道逆时针排列' : '本命盘圆盘图，上升点在左侧，黄道逆时针排列');
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
  try { const response = await fetch('/api/v1/astro/charts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request)}); const payload = await response.json(); if (!response.ok || !payload.success) throw new Error(payload.error?.message || '计算失败'); const data = payload.data; document.querySelector('#astro-empty').hidden = true; document.querySelector('#astro-output').hidden = false; document.querySelector('#astro-title').textContent = `${data.input.zodiac} · ${data.input.house_system}`; document.querySelector('#astro-meta').textContent = `JD ${fmt(data.calculation.julian_day_ut)} · ${data.calculation.precision_mode}${data.calculation.warnings.length ? ` · ${data.calculation.warnings.join('、')}` : ''}`; document.querySelector('#astro-angles').innerHTML = Object.entries(data.angles).sort((first, second) => ANGLE_ORDER.indexOf(first[0]) - ANGLE_ORDER.indexOf(second[0])).map(([key,value]) => `<div><small>${esc(ANGLE_LABELS[key] || key)}</small><strong>${fmt(value)}°</strong></div>`).join(''); wheelChart = data; renderWheel(); document.querySelector('#astro-planets').innerHTML = table(['点位','黄经','星座','落宫','速度','状态'], data.planets.map(p => [p.name,`${fmt(p.longitude)}°`,p.sign_name,p.house,`${fmt(p.longitude_speed)}°/day`,p.retrograde ? '逆行' : '顺行'])); document.querySelector('#astro-houses-list').innerHTML = table(['宫位','宫头','星座'], data.houses.map(h => [h.number,`${fmt(h.cusp)}°`,h.sign_name])); document.querySelector('#astro-aspects').innerHTML = table(['点位','点位','相位','偏差'], data.aspects.map(a => [a.first,a.second,a.type,`${fmt(a.orb)}°`])); document.querySelector('#astro-prompt-text').value = buildAstroPrompt(data, await loadAstroAnalysis(data)); } catch (err) { error.textContent = err.message; error.hidden = false; } finally { button.disabled = false; }
});
