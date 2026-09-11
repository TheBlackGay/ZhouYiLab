const form = document.querySelector('#da-liu-ren-form');
const esc = value => String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const pillarText = pillar => pillar && typeof pillar === 'object' ? `${pillar.stem ?? ''}${pillar.branch ?? ''}` : String(pillar ?? '');
const card = (title, value, note = '') => `<article class="fact-card"><h3>${esc(title)}</h3><p>${esc(value || '--')}</p>${note ? `<p class="muted">${esc(note)}</p>` : ''}</article>`;
const formatShenSha = value => {
  if (!value || typeof value !== 'object') return '--';
  const lines = [];
  const append = (entries, indent) => Object.entries(entries).forEach(([name, detail]) => {
    if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
      lines.push(`${indent}${name}`);
      append(detail, `${indent}  `);
    } else if (Array.isArray(detail)) {
      if (detail.length) lines.push(`${indent}${name}：${detail.join('、')}`);
    } else if (detail) lines.push(`${indent}${name}：${detail}`);
  });
  Object.entries(value).forEach(([group, entries]) => { lines.push(group); if (entries && typeof entries === 'object' && !Array.isArray(entries)) append(entries, '  '); else if (Array.isArray(entries) && entries.length) lines.push(`  ${entries.join('、')}`); });
  return lines.join('\n');
};
document.querySelectorAll('[role=tab]').forEach(tab => tab.addEventListener('click', () => document.querySelectorAll('[role=tab]').forEach(item => { const active = item === tab; item.setAttribute('aria-selected', String(active)); item.tabIndex = active ? 0 : -1; document.querySelector(`#${item.getAttribute('aria-controls')}`).hidden = !active; })));
const request = () => ({ calendar: document.querySelector('input[name="calendar"]:checked').value, date: {year:+year.value, month:+month.value, day:+day.value, hour:+hour.value} });
function render(data) {
  const pillars = ['year','month','day','hour'].map(key => pillarText(data.ba_zi?.[key]));
  document.querySelector('#summary-title').textContent = pillars.join(' ');
  document.querySelector('#summary-date').textContent = `月将 ${data.yue_jiang || '--'} · 贵人 ${data.gui_ren || '--'}`;
  document.querySelector('#metrics').innerHTML = [['昼夜',data.is_day?'白天':'夜晚'],['月将',data.yue_jiang],['贵人',data.gui_ren]].map(([k,v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join('');
  const ke = data.si_ke || {}, chuan = data.san_chuan || {}, details = chuan.details || [];
  const chuanLabel = (i, key) => { const item = details[i]; return item ? `${item.branch}${item.dun_gan ? ` · 遁干${item.dun_gan}` : ''}${item.liu_qin ? ` · ${item.liu_qin}` : ''}` : chuan[key]; };
  document.querySelector('#chart-grid').innerHTML = [['第一课（干上）',ke.first],['第二课（干上神之上神）',ke.second],['第三课（支上）',ke.third],['第四课（支上神之上神）',ke.fourth],['初传',chuanLabel(0,'chu_chuan')],['中传',chuanLabel(1,'zhong_chuan')],['末传',chuanLabel(2,'mo_chuan')],['课式',(chuan.ke_shi||[]).join('、')]].map(([k,v]) => card(k,v)).join('');
  const panText = (data.tian_di_pan || []).map(item => `${item.position}：${item.tian_pan}${item.dun_gan ? `（遁${item.dun_gan}）` : ''}${item.shen_jiang ? ` · ${item.shen_jiang}` : ''}`).join('\n');
  document.querySelector('#summary-grid').innerHTML = [card('起课八字',pillars.join('　'),`旬空 ${data.ba_zi?.xun_kong_1 || ''}${data.ba_zi?.xun_kong_2 || ''}`),card('天地盘',panText),card('卦体格局',(data.gua_ti||[]).join('、')),card('神煞',formatShenSha(data.shen_sha))].join('');
  document.querySelector('#empty-state').hidden = true; document.querySelector('#result-content').hidden = false;
}
form.addEventListener('submit', async event => { event.preventDefault(); const error = document.querySelector('#form-error'); error.hidden = true; try { const response = await fetch('/api/v1/da-liu-ren/charts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request())}); const payload = await response.json(); if (!response.ok || !payload.success) throw new Error(payload.error?.message || '起课失败'); render(payload.data); } catch (err) { error.textContent = err.message; error.hidden = false; } });
