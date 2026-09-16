const astroForm = document.querySelector('#astro-form');
const esc = value => String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const fmt = value => Number(value).toFixed(4);
const SVG_NS = 'http://www.w3.org/2000/svg';
const signs = ['白羊','金牛','双子','巨蟹','狮子','处女','天秤','天蝎','射手','摩羯','水瓶','双鱼'];
const symbols = {sun:'☉',moon:'☽',mercury:'☿',venus:'♀',mars:'♂',jupiter:'♃',saturn:'♄',uranus:'♅',neptune:'♆',pluto:'♇',true_node:'☊',chiron:'⚷'};
const colors = ['#b14b3d','#4c7a68','#48729a','#a16207','#7c5b9e','#4c6475','#b36b3f','#557c78','#6b5d4d','#8e4f69','#3d777d','#8b6d42'];
function table(headers, rows) { return `<table><thead><tr>${headers.map(h => `<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(row => `<tr>${row.map(v => `<td>${esc(v)}</td>`).join('')}</tr>`).join('')}</tbody></table>`; }
function polar(cx, cy, radius, longitude) { const angle = (longitude - 90) * Math.PI / 180; return [cx + radius * Math.cos(angle), cy + radius * Math.sin(angle)]; }
function svg(name, attrs = {}) { const node = document.createElementNS(SVG_NS, name); Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value)); return node; }
function drawWheel(data) {
  const root = document.querySelector('#astro-wheel'); root.replaceChildren(); const cx = 310, cy = 310, outer = 286, signInner = 224, houseInner = 76;
  for (let i = 0; i < 12; i += 1) { const start = polar(cx, cy, outer, i * 30), end = polar(cx, cy, outer, (i + 1) * 30); root.appendChild(svg('path', {d:`M ${cx} ${cy} L ${start[0]} ${start[1]} A ${outer} ${outer} 0 0 1 ${end[0]} ${end[1]} Z`, class:'sign-sector'})); const label = polar(cx, cy, (outer + signInner) / 2, i * 30 + 15); const text = svg('text', {x:label[0], y:label[1], class:'sign-label'}); text.textContent = signs[i]; root.appendChild(text); }
  root.append(svg('circle', {cx, cy, r:outer, class:'ring'}), svg('circle', {cx, cy, r:signInner, class:'inner-ring'}), svg('circle', {cx, cy, r:houseInner, class:'inner-ring'}));
  const cusps = data.houses.map(h => h.cusp);
  cusps.forEach((cusp, index) => { const [x1,y1] = polar(cx,cy,houseInner,cusp), [x2,y2] = polar(cx,cy,signInner,cusp); root.appendChild(svg('line', {x1,y1,x2,y2,class:index === 0 || index === 9 ? 'house-line major' : 'house-line'})); let span = (cusps[(index + 1) % 12] - cusp + 360) % 360 || 30; const label = polar(cx,cy,houseInner + 28,cusp + span / 2); const text = svg('text', {x:label[0],y:label[1],class:'house-label'}); text.textContent = index + 1; root.appendChild(text); });
  data.aspects.forEach(aspect => { const first = data.planets.find(p => p.id === aspect.first), second = data.planets.find(p => p.id === aspect.second); if (!first || !second) return; const [x1,y1] = polar(cx,cy,houseInner - 8,first.longitude), [x2,y2] = polar(cx,cy,houseInner - 8,second.longitude); root.appendChild(svg('line', {x1,y1,x2,y2,class:'aspect-line'})); });
  data.planets.forEach((planet,index) => { const [x,y] = polar(cx,cy,signInner - 24 - (index % 2) * 22,planet.longitude); const group = svg('g', {'aria-label':`${planet.name} ${fmt(planet.longitude)}°`}); const dot = svg('circle', {cx:x,cy:y,r:10,fill:colors[index % colors.length],class:'planet-dot',tabindex:'0'}); const title = svg('title'); title.textContent = `${planet.name} ${fmt(planet.longitude)}°`; dot.appendChild(title); const label = svg('text', {x,y:y - 17,class:'planet-label'}); label.textContent = symbols[planet.id] || planet.name.slice(0,1); group.append(dot,label); root.appendChild(group); });
}
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
  try { const response = await fetch('/api/v1/astro/charts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request)}); const payload = await response.json(); if (!response.ok || !payload.success) throw new Error(payload.error?.message || '计算失败'); const data = payload.data; document.querySelector('#astro-empty').hidden = true; document.querySelector('#astro-output').hidden = false; document.querySelector('#astro-title').textContent = `${data.input.zodiac} · ${data.input.house_system}`; document.querySelector('#astro-meta').textContent = `JD ${fmt(data.calculation.julian_day_ut)} · ${data.calculation.precision_mode}${data.calculation.warnings.length ? ` · ${data.calculation.warnings.join('、')}` : ''}`; document.querySelector('#astro-angles').innerHTML = Object.entries(data.angles).map(([key,value]) => `<div><small>${esc(key)}</small><strong>${fmt(value)}°</strong></div>`).join(''); drawWheel(data); document.querySelector('#astro-planets').innerHTML = table(['点位','黄经','星座','落宫','速度','状态'], data.planets.map(p => [p.name,`${fmt(p.longitude)}°`,p.sign_name,p.house,`${fmt(p.longitude_speed)}°/day`,p.retrograde ? '逆行' : '顺行'])); document.querySelector('#astro-houses-list').innerHTML = table(['宫位','宫头','星座'], data.houses.map(h => [h.number,`${fmt(h.cusp)}°`,h.sign_name])); document.querySelector('#astro-aspects').innerHTML = table(['点位','点位','相位','偏差'], data.aspects.map(a => [a.first,a.second,a.type,`${fmt(a.orb)}°`])); document.querySelector('#astro-prompt-text').value = buildAstroPrompt(data, await loadAstroAnalysis(data)); } catch (err) { error.textContent = err.message; error.hidden = false; } finally { button.disabled = false; }
});
