/* 大六壬 2.0.0 页面：所问之事 → 起课时间（含闰月/夜子时口径）→ 小白/专业双模式结果。
 * 术语解释来自注册表清单声明的 GET /api/v1/da-liu-ren/glossary。 */
const form = document.querySelector('#da-liu-ren-form');
const esc = value => String(value ?? '').replace(/[&<>'"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c]));
const el = id => document.querySelector(id);
const pillarText = pillar => pillar && typeof pillar === 'object' ? `${pillar.stem ?? ''}${pillar.branch ?? ''}` : String(pillar ?? '');

const SHICHEN = [
  { hour: 0, zh: '早子', label: '早子时 00:00–00:59' },
  { hour: 1, zh: '丑', label: '丑时 01:00–02:59' },
  { hour: 3, zh: '寅', label: '寅时 03:00–04:59' },
  { hour: 5, zh: '卯', label: '卯时 05:00–06:59' },
  { hour: 7, zh: '辰', label: '辰时 07:00–08:59' },
  { hour: 9, zh: '巳', label: '巳时 09:00–10:59' },
  { hour: 11, zh: '午', label: '午时 11:00–12:59' },
  { hour: 13, zh: '未', label: '未时 13:00–14:59' },
  { hour: 15, zh: '申', label: '申时 15:00–16:59' },
  { hour: 17, zh: '酉', label: '酉时 17:00–18:59' },
  { hour: 19, zh: '戌', label: '戌时 19:00–20:59' },
  { hour: 21, zh: '亥', label: '亥时 21:00–22:59' },
  { hour: 23, zh: '夜子', label: '夜子时 23:00–23:59（日柱算次日）' },
];
const HOUR_TO_SHICHEN = new Map(SHICHEN.map(item => [item.hour, item]));
const QUESTION_ZH = { general: '泛论本课', love: '感情', career: '工作', wealth: '财运', travel: '出行', health: '健康', other: '其他' };
const STAGE_ZH = { chu_chuan: '初传 · 起因', zhong_chuan: '中传 · 发展', mo_chuan: '末传 · 归结' };
const PROFILE_RULE_ZH = {
  four_pillars: '四柱', time_granularity: '时间粒度', yue_jiang: '月将',
  gui_ren: '贵人', shen_jiang: '神将顺逆', gan_ji_gong: '日干寄宫',
  san_chuan: '三传九宗门', dun_gan: '遁干', liu_qin: '六亲', gua_ti: '卦体',
};

/* ===== 时辰下拉与输入联动 ===== */
const hourSelect = el('#hour');
SHICHEN.forEach(item => {
  const option = document.createElement('option');
  option.value = String(item.hour);
  option.textContent = item.label;
  hourSelect.append(option);
});
hourSelect.value = '15';

const calendarInputs = [...form.querySelectorAll('input[name="calendar"]')];
const syncCalendarMode = () => {
  const lunar = form.querySelector('input[name="calendar"]:checked').value === 'lunar';
  el('#leap-row').hidden = !lunar;
  if (!lunar) el('#leap-month').checked = false;
};
calendarInputs.forEach(input => input.addEventListener('change', syncCalendarMode));

const setDateTime = (date, hour) => {
  calendarInputs.find(input => input.value === 'solar').checked = true;
  syncCalendarMode();
  el('#year').value = date.getFullYear();
  el('#month').value = date.getMonth() + 1;
  el('#day').value = date.getDate();
  hourSelect.value = String(hour);
};
/* 双小时起始值：0→早子、23→夜子、其余偶数回退一小时 */
const shichenBucket = h => (h === 0 || h === 23) ? h : h - (h % 2 === 0 ? 1 : 0);
el('#fill-now').addEventListener('click', () => {
  const now = new Date();
  setDateTime(now, shichenBucket(now.getHours()));
});
el('#fill-sample').addEventListener('click', () => setDateTime(new Date(2025, 10, 3), 15));

/* ===== 错误本地化（引擎/tyme 英文报错转可操作中文，输入保留） ===== */
function localizeError(message, code) {
  const text = String(message ?? '');
  if (/illegal leap month/i.test(text)) return '该农历该年没有这个闰月：请取消勾选闰月，或改为该年真实存在的闰月';
  if (/illegal day|day.*illegal/i.test(text)) return '该日期不存在，请检查当月天数';
  if (/illegal month|month.*illegal/i.test(text)) return '农历月份无效，请输入 1–12';
  if (code === 'CALCULATION_TIMEOUT') return '起课超时，请点击“开始起课”重试';
  if (code === 'ENGINE_UNAVAILABLE') return '计算引擎尚未构建，请先执行 ./build.sh';
  return `起课失败：${text || code || '未知错误'}`;
}

/* ===== 术语库与帮助弹层（DLR-204：口径随词条展示，键盘可达） ===== */
let glossary = null;
async function loadGlossary() {
  try {
    const response = await fetch('/api/v1/da-liu-ren/glossary');
    const payload = await response.json();
    glossary = new Map((payload.data?.terms ?? []).map(term => [term.id, term]));
  } catch (_) {
    glossary = new Map();
  }
  return glossary;
}
loadGlossary();

const termButton = id => `<button type="button" class="dlr-term" data-term="${esc(id)}">？</button>`;
document.addEventListener('click', async event => {
  const trigger = event.target.closest('.dlr-term');
  if (!trigger) return;
  if (!glossary) await loadGlossary();
  const term = glossary.get(trigger.dataset.term);
  el('#glossary-body').innerHTML = term
    ? `<h3>${esc(term.term)}</h3><p>${esc(term.definition)}</p><p class="glossary-caliber"><strong>当前口径：</strong>${esc(term.caliber)}</p>`
    : '<p>术语库暂不可用，请稍后重试。</p>';
  el('#glossary-dialog').showModal();
});
el('#glossary-close').addEventListener('click', () => el('#glossary-dialog').close());

el('#caliber-open').addEventListener('click', () => {
  if (el('#result-content').hidden) return;
  setMode('pro');
  activateTab('rule-tab');
  el('#rule-panel').scrollIntoView({ behavior: 'smooth' });
});

/* ===== 双模式与专业 tab（同一份数据切换，不重复请求） ===== */
function setMode(mode) {
  document.querySelector(`input[name="result-mode"][value="${mode}"]`).checked = true;
  el('#beginner-view').hidden = mode !== 'beginner';
  el('#pro-view').hidden = mode !== 'pro';
  el('#pro-tabs').hidden = mode !== 'pro';
  el('#mode-context').textContent = mode === 'pro' ? '专业盘' : '本课要点';
}
document.querySelectorAll('input[name="result-mode"]').forEach(input =>
  input.addEventListener('change', () => setMode(input.value)));

const TABS = ['sike-tab', 'pan-tab', 'extra-tab', 'rule-tab'];
function activateTab(id) {
  TABS.forEach(tab => {
    const button = el(`#${tab}`);
    const active = tab === id;
    button.setAttribute('aria-selected', String(active));
    button.tabIndex = active ? 0 : -1;
    el(`#${button.getAttribute('aria-controls')}`).hidden = !active;
  });
}
TABS.forEach(tab => el(`#${tab}`).addEventListener('click', () => activateTab(tab)));

/* ===== 渲染 ===== */
function factCard(title, value, note = '', term = '') {
  return `<article class="fact-card"><h3>${esc(title)}${term ? ` ${termButton(term)}` : ''}</h3><p>${esc(value || '--')}</p>${note ? `<p class="muted">${esc(note)}</p>` : ''}</article>`;
}

function renderQuestionContext() {
  const type = el('#question-type').value;
  const notes = el('#question-notes').value.trim();
  const node = el('#question-context');
  if (type === 'general' && !notes) { node.hidden = true; return; }
  node.hidden = false;
  node.innerHTML = `所问：${esc(QUESTION_ZH[type] ?? type)}${notes ? ` —— ${esc(notes)}` : ''}（仅保留在本页，未发送给服务）`;
}
el('#question-type').addEventListener('change', renderQuestionContext);
el('#question-notes').addEventListener('input', renderQuestionContext);

let lastChartData = null;
function render(data) {
  lastChartData = data;
  const pillars = ['year', 'month', 'day', 'hour'].map(key => pillarText(data.ba_zi?.[key]));
  el('#summary-title').textContent = pillars.join(' ');
  const keShi = data.san_chuan?.ke_shi ?? [];
  const zongMen = keShi[0] ?? '--';
  el('#summary-date').textContent = `月将 ${data.yue_jiang || '--'} · 贵人 ${data.gui_ren || '--'} · ${zongMen}`;

  el('#metrics').innerHTML = [
    ['昼夜', esc(data.is_day ? '白天' : '夜晚')],
    ['月将', `${esc(data.yue_jiang || '--')} ${termButton('yue_jiang')}`],
    ['贵人', `${esc(data.gui_ren || '--')} ${termButton('gui_ren')}`],
    ['旬空', `${esc(`${data.ba_zi?.xun_kong_1 ?? ''}${data.ba_zi?.xun_kong_2 ?? ''}`)} ${termButton('xun_kong')}`],
  ].map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${v}</dd></div>`).join('');

  renderQuestionContext();

  el('#focus-title').textContent = `${zongMen}${data.gua_ti?.length ? ` · ${data.gua_ti.join('、')}` : ''}`;
  el('#focus-grid').innerHTML = [
    factCard('四柱', pillars.join('　'), '日柱为全课之主', 'si_ke'),
    factCard('三传', (data.san_chuan?.details ?? []).map(x => x.branch).join(' → '), '取传依据见专业模式·四课三传', 'san_chuan'),
    factCard('课式', keShi.join(' · '), '结构命名，非吉凶断语', 'ke_shi'),
  ].join('');

  el('#chuan-flow').innerHTML = (data.san_chuan?.details ?? []).map(item => `
    <article class="flow-step">
      <h3>${esc(STAGE_ZH[item.stage] ?? item.stage)} ${termButton(item.stage)}</h3>
      <p class="flow-branch">${esc(item.branch || '--')}</p>
      <p class="muted">${item.dun_gan ? `遁干 ${esc(item.dun_gan)} ${termButton('dun_gan')} · ` : ''}${esc(item.liu_qin || '')}${item.liu_qin ? ` ${termButton('liu_qin')}` : ''}</p>
    </article>`).join('') || '<p class="muted">无三传数据</p>';

  renderProfessional(data, pillars);
}

function renderProfessional(data, pillars) {
  const ke = data.si_ke ?? {};
  const details = data.san_chuan?.details ?? [];
  el('#chart-grid').innerHTML = [
    factCard('第一课（日干寄宫之上神）', ke.first, '', 'si_ke'),
    factCard('第二课（第一课上神之上）', ke.second, '', 'si_ke'),
    factCard('第三课（日支之上神）', ke.third, '', 'si_ke'),
    factCard('第四课（第三课上神之上）', ke.fourth, '', 'si_ke'),
    ...details.map(item => factCard(STAGE_ZH[item.stage] ?? item.stage,
      `${item.branch ?? '--'}${item.dun_gan ? ` · 遁干${item.dun_gan}` : ''}${item.liu_qin ? ` · ${item.liu_qin}` : ''}`, '', 'san_chuan')),
    factCard('课式', data.san_chuan?.ke_shi?.join('、'), '九宗门名在首位', 'ke_shi'),
  ].join('');

  const rows = (data.tian_di_pan ?? []).map(item => `<tr><td>${esc(item.position)}</td><td>${esc(item.tian_pan)}</td><td>${esc(item.dun_gan || '—')}</td><td>${esc(item.shen_jiang || '—')}</td></tr>`).join('');
  el('#pan-table-wrap').innerHTML = `<table class="pan-table"><caption class="muted">地盘固定十二位；天盘随月将加占时旋转；旬空位无遁干</caption><thead><tr><th>地盘位</th><th>天盘上神 ${termButton('tian_di_pan')}</th><th>遁干 ${termButton('dun_gan')}</th><th>神将 ${termButton('shen_jiang')}</th></tr></thead><tbody>${rows}</tbody></table>`;

  el('#extra-grid').innerHTML = [
    factCard('旬空', `${data.ba_zi?.xun_kong_1 ?? ''}${data.ba_zi?.xun_kong_2 ?? ''}`, '日柱旬内无地支之二位', 'xun_kong'),
    factCard('卦体', (data.gua_ti ?? []).join('、'), '只命名、不断吉凶', 'gua_ti'),
    ...Object.entries(data.shen_sha ?? {}).map(([group, value]) =>
      `<article class="fact-card"><h3>神煞 · ${esc(group)} ${termButton('shen_sha')}</h3><pre class="shen-sha-list">${esc(formatShenSha(value))}</pre></article>`),
  ].join('');

  const profile = data.meta?.rule_profile;
  if (profile) {
    el('#rule-grid').innerHTML = [
      `<article class="fact-card"><h3>口径版本</h3><p>${esc(profile.profile_version)}</p><p class="muted">校准状态：${esc(profile.calibration_status)}（pending = 口径校准中，结论仅作参考）</p></article>`,
      ...Object.entries(profile.rules ?? {}).map(([key, text]) =>
        `<article class="fact-card"><h3>${esc(PROFILE_RULE_ZH[key] ?? key)}</h3><p>${esc(text)}</p></article>`),
    ].join('');
  } else {
    el('#rule-grid').innerHTML = '<p class="muted">本次结果未携带规则口径（引擎版本过旧，请重新构建）。</p>';
  }
}

function formatShenSha(value) {
  if (!value || typeof value !== 'object') return String(value ?? '--');
  if (Array.isArray(value)) return value.join('、') || '--';
  const lines = [];
  const append = (entries, indent) => Object.entries(entries).forEach(([name, detail]) => {
    if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
      lines.push(`${indent}${name}`); append(detail, `${indent}  `);
    } else if (Array.isArray(detail)) {
      if (detail.length) lines.push(`${indent}${name}：${detail.join('、')}`);
    } else if (detail) lines.push(`${indent}${name}：${detail}`);
  });
  Object.entries(value).forEach(([group, entries]) => {
    lines.push(group);
    if (entries && typeof entries === 'object' && !Array.isArray(entries)) append(entries, '  ');
    else if (Array.isArray(entries) && entries.length) lines.push(`  ${entries.join('、')}`);
  });
  return lines.join('\n');
}

/* ===== 提交（DLR-201：禁用按钮、状态提示、失败保留输入） ===== */
form.addEventListener('submit', async event => {
  event.preventDefault();
  const button = el('#submit-btn');
  const status = el('#form-status');
  const error = el('#form-error');
  error.hidden = true;
  const calendar = form.querySelector('input[name="calendar"]:checked').value;
  const date = { year: +el('#year').value, month: +el('#month').value, day: +el('#day').value, hour: +hourSelect.value };
  if (calendar === 'lunar' && el('#leap-month').checked) date.leap_month = true;
  const request = { calendar, date };
  button.disabled = true;
  status.hidden = false;
  status.textContent = '正在起课…';
  try {
    const response = await fetch('/api/v1/da-liu-ren/charts', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(request),
    });
    const payload = await response.json();
    if (!response.ok || !payload.success) throw new Error(localizeError(payload.error?.message, payload.error?.code));
    render(payload.data);
    el('#empty-state').hidden = true;
    el('#result-content').hidden = false;
    setMode(document.querySelector('input[name="result-mode"]:checked').value);
    status.textContent = `起课完成 · ${HOUR_TO_SHICHEN.get(date.hour)?.label ?? `时值 ${date.hour}`}`;
  } catch (err) {
    error.textContent = err.message;
    error.hidden = false;
    status.textContent = '';
  } finally {
    button.disabled = false;
  }
});
