/* 梅花易数页面逻辑（M2）：时间/报数双模式 → /api/v1/mei-hua/plates 事实盘渲染。
 * 只渲染盘面事实（本互变三卦、体用、月令旺衰、取数审计），不生成断语。 */
const $ = selector => document.querySelector(selector);
const form = $('#meihua-form');
const errorBox = $('#form-error');
const emptyState = $('#empty-state');
const resultContent = $('#result-content');

const escapeHtml = value => String(value ?? '').replace(/[&<>'"]/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c]));

function setCalendar(calendar) {
  const lunar = calendar === 'lunar';
  $('#solar-fields').hidden = lunar;
  $('#lunar-fields').hidden = !lunar;
  ['#year', '#month', '#day'].forEach(s => { $(s).required = !lunar; });
  ['#lunar-year', '#lunar-month', '#lunar-day'].forEach(s => { $(s).required = lunar; });
}

function setMode(mode) {
  $('#numbers-fields').hidden = mode !== 'numbers';
}

form.querySelectorAll('input[name="calendar"]').forEach(input =>
  input.addEventListener('change', () => setCalendar(form.elements.calendar.value)));
form.querySelectorAll('input[name="mode"]').forEach(input =>
  input.addEventListener('change', () => setMode(form.elements.mode.value)));

/* 传统爻名：初/上分阴阳爻题，二三四五居中。 */
function yaoName(position, bit) {
  const yang = bit === '1';
  if (position === 1) return yang ? '初九' : '初六';
  if (position === 6) return yang ? '上九' : '上六';
  return yang ? `九${['', '', '二', '三', '四', '五'][position]}` : `六${['', '', '二', '三', '四', '五'][position]}`;
}

function yaoRows(code, movingLine, markMoving) {
  // 自上限向下排布（上爻在顶），与六爻明细同一阅读方向
  const rows = [];
  for (let position = 6; position >= 1; position -= 1) {
    const bit = code[position - 1];
    const mark = markMoving && position === movingLine
      ? `<span class="moving">${bit === '1' ? '○ 动' : '× 动'}</span>` : '';
    rows.push(`<div class="yao-row"><span>${bit === '1' ? '━━━━━━━' : '━━ ━━'}</span>`
      + `<small>${escapeHtml(yaoName(position, bit))}</small>${mark}</div>`);
  }
  return rows.join('');
}

function guaCard(title, subtitle, gua, movingLine, markMoving) {
  return `<article class="fact-card gua-card"><h3>${escapeHtml(title)} · ${escapeHtml(gua.name)}</h3>
    <p class="palace">${escapeHtml(subtitle)}｜${escapeHtml(gua.outer)}上${escapeHtml(gua.inner)}下 · ${escapeHtml(gua.palace)}宫</p>
    ${yaoRows(gua.code, movingLine, markMoving)}</article>`;
}

function render(data) {
  const ti = data.ti_yong;
  $('#summary-title').textContent = `${data.ben_gua.name}（动${data.moving_line}爻）→ ${data.bian_gua.name}`;
  const casting = data.casting;
  const method = casting.method === 'time' ? '时间起卦' : '报数起卦';
  $('#summary-date').textContent = `${method} · ${data.ba_zi.year.stem}${data.ba_zi.year.branch}年 `
    + `${data.ba_zi.month.stem}${data.ba_zi.month.branch}月 · 卦码 ${data.ben_gua.code}`;
  $('#metrics').innerHTML = [
    ['动爻', `${data.moving_line} 爻`],
    ['月令', data.ba_zi.month_command],
    ['体用', ti.relation],
  ].map(([label, value]) => `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`).join('');

  $('#plate-grid').innerHTML = [
    guaCard('本卦（现状）', '事之见在', data.ben_gua, data.moving_line, true),
    guaCard('互卦（中程）', '事之中程', data.hu_gua, null, false),
    guaCard('变卦（归结）', '事之终结', data.bian_gua, data.moving_line, false),
  ].join('');

  const posName = pos => pos === 'upper' ? '上卦' : '下卦';
  const tiTrigram = data.trigrams[ti.ti];
  const yongTrigram = data.trigrams[ti.yong];
  $('#tiyong-card').innerHTML = `<strong>体用</strong>
    <div class="tiyong-flow">
      <span>体 · ${posName(ti.ti)}${escapeHtml(tiTrigram.name)}（${escapeHtml(tiTrigram.element)}）· 月令${escapeHtml(ti.ti_wang_shuai)}</span>
      <span class="rel">${escapeHtml(ti.relation)}</span>
      <span>用 · ${posName(ti.yong)}${escapeHtml(yongTrigram.name)}（${escapeHtml(yongTrigram.element)}）· 月令${escapeHtml(ti.yong_wang_shuai)}</span>
    </div>
    <small>动爻所临之卦为用；判词为五行生克结构关系，非吉凶断语。</small>`;

  const details = casting.method === 'time'
    ? [['取数', `年支序 ${casting.year_branch_order} + 月 ${casting.lunar_month_used} + 日 ${casting.lunar_day} = ${casting.upper_sum}（上卦）；+ 时支序 ${casting.hour_branch_order} = ${casting.lower_sum}（下卦与动爻）`],
       ['闰月规则', casting.lunar_month_input_signed < 0
         ? `农历闰${-casting.lunar_month_input_signed}月 · 十五分界生效` : '未涉闰月']]
    : [['报数', `${casting.reported.join('、')}`],
       ['取数', `上卦=${casting.upper_sum} 定卦；和=${casting.lower_sum} 定下卦与动爻（余 0 作满数）`]];
  $('#casting-summary').innerHTML = [
    ['起卦公式', casting.formula],
    ['四柱', `${data.ba_zi.year.stem}${data.ba_zi.year.branch} ${data.ba_zi.month.stem}${data.ba_zi.month.branch} ${data.ba_zi.day.stem}${data.ba_zi.day.branch} ${data.ba_zi.hour.stem}${data.ba_zi.hour.branch}`],
    ...details,
    ['口径', `${data.meta?.rule_profile?.profile_version || 'meihua-rules'} · 校核中`],
  ].map(([label, value]) => `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`).join('');

  emptyState.hidden = true;
  resultContent.hidden = false;
  loadMeihuaProfile(data);
}

/* 卦面画像（人性化数据包）：六卦五行/月令旺衰/本卦阴阳，组件见 profile-charts.js */
function loadMeihuaProfile(data) {
  if (!window.ProfileCharts || !data) return;
  window.ProfileCharts.load({
    container: '#mh-profile-charts',
    fallback: '#mh-profile-fallback',
    path: '/api/v1/mei-hua/distribution',
    chart: data,
    label: null,
  });
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  errorBox.hidden = true;
  const mode = form.elements.mode.value;
  const calendar = form.elements.calendar.value;
  const lunar = calendar === 'lunar';
  const date = lunar
    ? {
      year: Number($('#lunar-year').value), month: Number($('#lunar-month').value),
      day: Number($('#lunar-day').value), hour: Number($('#hour').value),
      leap_month: $('#leap-month').checked,
    }
    : {
      year: Number($('#year').value), month: Number($('#month').value),
      day: Number($('#day').value), hour: Number($('#hour').value),
      minute: Number($('#minute').value || 0),
    };
  const request = { mode, calendar, date };
  if (mode === 'numbers') {
    const values = ['#num-1', '#num-2', '#num-3']
      .map(selector => $(selector).value.trim())
      .filter(value => value !== '')
      .map(Number);
    if (values.length < 2 || values.length > 3 || values.some(n => !Number.isInteger(n) || n < 1)) {
      errorBox.textContent = '报数须为 2 或 3 个正整数（第三个可选）';
      errorBox.hidden = false;
      return;
    }
    request.numbers = values;
  }
  const submit = form.querySelector('button[type="submit"]');
  submit.disabled = true;
  try {
    const response = await fetch('/api/v1/mei-hua/plates', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    const result = await response.json();
    if (!response.ok || !result.success) throw new Error(result.error?.message || '起卦失败');
    render(result.data);
  } catch (error) {
    errorBox.textContent = error.message;
    errorBox.hidden = false;
  } finally {
    submit.disabled = false;
  }
});

setCalendar(form.elements.calendar.value);
setMode(form.elements.mode.value);
