const form = document.querySelector('#bazi-form');
const submitButton = form.querySelector('.primary-action');
const errorBox = document.querySelector('#form-error');
const emptyState = document.querySelector('#empty-state');
const resultContent = document.querySelector('#result-content');
const trueSolarInput = document.querySelector('#true-solar');
const solarOptions = document.querySelector('#solar-options');
const pillarNames = { year: '年柱', month: '月柱', day: '日柱', hour: '时柱' };
let currentData = null;

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  })[character]);
}

function setLoading(loading) {
  submitButton.disabled = loading;
  submitButton.classList.toggle('loading', loading);
}

function pillarText(pillar) {
  return `${pillar?.stem || ''}${pillar?.branch || ''}`;
}

function signedOffset(seconds) {
  const sign = seconds >= 0 ? '+' : '-';
  const absolute = Math.abs(seconds);
  const minutes = Math.floor(absolute / 60);
  const remainder = absolute % 60;
  return `${sign}${minutes}分${remainder}秒`;
}

function renderPillars(data) {
  const keys = ['year', 'month', 'day', 'hour'];
  document.querySelector('#board-pillars').textContent = keys.map(key => pillarText(data.pillars[key])).join(' ');
  document.querySelector('#pillar-board').innerHTML = keys.map(key => {
    const pillar = data.pillars[key];
    const hidden = pillar.hidden_stems.map(item => `<span>${escapeHtml(item.stem)}<small>${escapeHtml(item.ten_god)} · ${escapeHtml(item.element)}</small></span>`).join('');
    const shenSha = (pillar.shen_sha || []).map(name => `<span>${escapeHtml(name)}</span>`).join('');
    return `<article class="pillar">
      <header><strong>${pillarNames[key]}</strong><span>${key === 'day' ? '日主' : escapeHtml(pillar.stem_ten_god)}</span></header>
      <div class="pillar-main"><small>${escapeHtml(pillar.stem_ten_god)}</small><strong class="stem">${escapeHtml(pillar.stem)}</strong><em>${escapeHtml(pillar.stem_yin_yang)}${escapeHtml(pillar.stem_element)}</em></div>
      <div class="pillar-main"><strong class="branch">${escapeHtml(pillar.branch)}</strong><em>${escapeHtml(pillar.branch_yin_yang)}${escapeHtml(pillar.branch_element)}</em></div>
      <div class="hidden-stems"><small>藏干 · 十神</small><div>${hidden}</div></div>
      <dl class="pillar-facts">
        <div><dt>星运</dt><dd>${escapeHtml(pillar.star_fortune)}</dd></div>
        <div><dt>自坐</dt><dd>${escapeHtml(pillar.self_sitting)}</dd></div>
        <div><dt>空亡</dt><dd>${escapeHtml(pillar.void_branches.join(''))}</dd></div>
        <div><dt>纳音</dt><dd>${escapeHtml(pillar.na_yin)}</dd></div>
      </dl>
      <div class="pillar-shensha"><small>神煞</small><div>${shenSha || '<span class="none">无</span>'}</div></div>
    </article>`;
  }).join('');
}

function renderFortune(data) {
  const currentYear = new Date().getFullYear();
  const detail = data.da_yun.start_detail;
  const elapsed = `${detail.years}年${detail.months}月${detail.days}日${detail.hours}时${detail.minutes}分`;
  document.querySelector('#fortune-title').textContent = `${data.da_yun.shun_pai ? '顺排' : '逆排'} · 出生后 ${elapsed} 起运 · 交运 ${detail.start_time}`;
  document.querySelector('#fortune-list').innerHTML = data.da_yun.list.map(item => {
    const active = currentYear >= item.start_year && currentYear <= item.end_year;
    return `<article class="fortune-card${active ? ' current' : ''}">
      <header><strong>${escapeHtml(pillarText(item.pillar))}</strong>${active ? '<span>当前</span>' : ''}</header>
      <p>${item.start_age}-${item.end_age} 岁</p>
      <small>${item.start_year}-${item.end_year} 年</small>
      <small>天干 ${escapeHtml(item.gan_shi_shen)} · 地支主气 ${escapeHtml(item.zhi_shi_shen)}</small>
    </article>`;
  }).join('');
}

function render(data) {
  currentData = data;
  const keys = ['year', 'month', 'day', 'hour'];
  document.querySelector('#summary-title').textContent = `${data.gender === 'male' ? '乾造' : '坤造'} · ${keys.map(key => pillarText(data.pillars[key])).join(' ')}`;
  const correction = data.birth_time;
  const solarEnabled = correction.mode === 'true_solar_time';
  document.querySelector('#summary-date').textContent = `${data.gender === 'male' ? '男' : '女'} · 钟表 ${correction.recorded_time.slice(0, 16)} · ${data.lunar_date}`;
  document.querySelector('#metric-master').textContent = `${data.day_master.yin_yang}${data.day_master.element} · ${data.day_master.stem}`;
  document.querySelector('#metric-void').textContent = data.xun_kong.filter(Boolean).join('') || '无';
  document.querySelector('#metric-start').textContent = `${data.da_yun.qi_yun_age} 岁`;
  document.querySelector('#metric-solar').textContent = solarEnabled ? correction.chart_time.slice(11, 16) : '未启用';
  document.querySelector('#time-correction-summary').innerHTML = [
    ['钟表时间', correction.recorded_time],
    ['排盘时间', correction.chart_time],
    ['总校正量', signedOffset(correction.total_offset_seconds)],
    ['跨日状态', correction.crossed_date_boundary ? '已跨日期边界' : '未跨日'],
  ].map(([label, value]) => `<div><dt>${label}</dt><dd>${escapeHtml(value)}</dd></div>`).join('');
  const tongZi = data.shen_sha_summary?.tong_zi;
  const luoWang = data.shen_sha_summary?.tian_luo_di_wang;
  document.querySelector('#shen-sha-note').textContent = [
    data.shen_sha_summary?.source || '渊海子平·三命通会口径',
    tongZi?.is_double ? '童子煞：月令、纳音双重命中' : '',
    luoWang?.tian_luo || luoWang?.di_wang ? luoWang.gender_note : '',
  ].filter(Boolean).join(' · ');
  renderPillars(data);
  renderFortune(data);
  emptyState.hidden = true;
  resultContent.hidden = false;
}

function setCalendar(calendar) {
  const lunar = calendar === 'lunar';
  document.querySelector('#solar-fields').hidden = lunar;
  document.querySelector('#lunar-fields').hidden = !lunar;
  document.querySelector('#solar-date').required = !lunar;
  ['#lunar-year', '#lunar-month', '#lunar-day'].forEach(selector => {
    document.querySelector(selector).required = lunar;
  });
}

document.querySelectorAll('[role="tab"]').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('[role="tab"]').forEach(item => {
      const selected = item === tab;
      item.setAttribute('aria-selected', String(selected));
      item.tabIndex = selected ? 0 : -1;
      document.querySelector(`#${item.getAttribute('aria-controls')}`).hidden = !selected;
    });
  });
});

form.addEventListener('change', event => {
  if (event.target.name === 'calendar') setCalendar(event.target.value);
  if (event.target === trueSolarInput) solarOptions.hidden = !trueSolarInput.checked;
});

form.addEventListener('submit', async event => {
  event.preventDefault();
  errorBox.hidden = true;
  setLoading(true);
  try {
    const calendar = form.elements.calendar.value;
    const [hour, minute] = document.querySelector('#birth-time').value.split(':').map(Number);
    let date;
    if (calendar === 'solar') {
      const [year, month, day] = document.querySelector('#solar-date').value.split('-').map(Number);
      date = { year, month, day, hour, minute };
    } else {
      date = {
        year: Number(document.querySelector('#lunar-year').value),
        month: Number(document.querySelector('#lunar-month').value),
        day: Number(document.querySelector('#lunar-day').value),
        hour,
        minute,
        leap_month: document.querySelector('#leap-month').checked,
      };
    }
    const response = await fetch('/api/v1/bazi/charts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        calendar,
        gender: form.elements.gender.value,
        date,
        time_correction: {
          mode: trueSolarInput.checked ? 'true_solar_time' : 'standard_time',
          longitude: Number(document.querySelector('#longitude').value),
          standard_meridian: Number(document.querySelector('#meridian').value),
          daylight_saving_minutes: Number(document.querySelector('#dst').value),
        },
      }),
    });
    const result = await response.json();
    if (!response.ok || !result.success) throw new Error(result.error?.message || '八字排盘失败');
    render(result.data);
  } catch (error) {
    errorBox.textContent = error.message;
    errorBox.hidden = false;
  } finally {
    setLoading(false);
  }
});

setCalendar(form.elements.calendar.value);
solarOptions.hidden = !trueSolarInput.checked;
form.requestSubmit();
