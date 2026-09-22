const form = document.querySelector('#liu-yao-form');
const submitButton = form.querySelector('.primary-action');
const currentTimeButton = document.querySelector('#set-current-time');
const advancedToggle = document.querySelector('#toggle-advanced');

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  })[character]);
}

function pillarText(pillar) {
  if (!pillar || typeof pillar !== 'object') return String(pillar ?? '');
  return `${pillar.stem || ''}${pillar.branch || ''}`;
}

function isYinYao(value) {
  return value === '0' || value === 0 || value === 48;
}

function setLoading(loading) {
  submitButton.disabled = loading;
  submitButton.textContent = loading ? '正在排盘...' : '开始排盘';
}

function buildRequest() {
  const changingLines = document.querySelector('#changing-lines').value
    .split(',').map(value => value.trim()).filter(Boolean).map(Number);
  if (changingLines.some(value => !Number.isInteger(value) || value < 1 || value > 6)) {
    throw new Error('动爻位置必须是 1 到 6 的整数');
  }
  return {
    calendar: document.querySelector('input[name="calendar"]:checked').value,
    question_type: document.querySelector('#question-type').value,
    question_detail: document.querySelector('#question-detail').value.trim(),
    date: {
      year: Number(document.querySelector('#year').value),
      month: Number(document.querySelector('#month').value),
      day: Number(document.querySelector('#day').value),
      hour: Number(document.querySelector('#hour').value),
      minute: Number(document.querySelector('#minute').value),
    },
    hexagram_code: document.querySelector('#hexagram-code').value,
    changing_lines: [...new Set(changingLines)],
  };
}

currentTimeButton.addEventListener('click', () => {
  const now = new Date();
  document.querySelector('#year').value = now.getFullYear();
  document.querySelector('#month').value = now.getMonth() + 1;
  document.querySelector('#day').value = now.getDate();
  document.querySelector('#hour').value = now.getHours();
  document.querySelector('#minute').value = now.getMinutes();
});

function detailText(relative, pillar, element) {
  if (!relative && !element) return '无';
  return [relative, pillarText(pillar), element].filter(Boolean).join(' ') || '无';
}

function buildAiText(data) {
  const yao = data.yao || [];
  const questionType = document.querySelector('#question-type')?.selectedOptions[0]?.textContent || '综合观察';
  const questionDetail = document.querySelector('#question-detail')?.value.trim() || '未填写具体问题';
  const bazi = ['year', 'month', 'day', 'hour'].map(key => pillarText(data.ba_zi?.[key]));
  const changing = yao.filter(item => item.isChanging).map(item => `${item.position}爻`).join('、') || '无';
  const rows = yao.slice().sort((a, b) => a.position - b.position).map(item => {
    const mark = item.shiYingMark?.trim() || '';
    const line = isYinYao(item.mainYaoType) ? '阴爻' : '阳爻';
    const changed = item.isChanging ? detailText(item.changedRelative, item.changedPillar, item.changedElement) : '静爻';
    return `${item.position}爻${mark ? `（${mark}）` : ''}｜${line}｜六神：${item.spirit || '无'}｜伏神：${detailText(item.hiddenRelative, item.hiddenPillar, item.hiddenElement)}｜本卦：${detailText(item.mainRelative, item.mainPillar, item.mainElement)}｜旺衰：${item.wangShuai || '无'}｜变卦：${changed}｜状态：${(item.state_tags || []).join('、') || '无特殊状态'}`;
  });
  return [`请根据以下六爻排盘信息，结合我的具体问题进行分析。请先说明取用神依据，再分别分析世应、用神旺衰、动爻和变卦，并区分盘面事实与推断。`, `问题类型：${questionType}`, `具体问题：${questionDetail}`, `本卦：${data.ben_gua_name || '无'}`, `变卦：${data.bian_gua_name || '无变卦'}`, `动爻：${changing}`, `起课四柱：${bazi.join(' ')}`, `旬空：${data.ba_zi?.xun_kong_1 || ''}${data.ba_zi?.xun_kong_2 || ''}`.replace(/：$/, '：无'), '六爻（初爻到上爻）：', ...rows].join('\n');
}

function renderYaoRow(item) {
  const yin = isYinYao(item.mainYaoType);
  const mark = item.shiYingMark?.trim();
  const changed = item.isChanging
    ? detailText(item.changedRelative, item.changedPillar, item.changedElement)
    : '静爻';
  const stateTags = Array.isArray(item.state_tags) ? item.state_tags : [];
  const stateNote = item.state_note || '无特殊状态';
  const hiddenTitle = item.hidden_state_tags?.length ? `伏神状态：${item.hidden_state_tags.join('、')}` : '';
  return `<article class="yao-row${item.isChanging ? ' changing' : ''}">
    <div class="yao-position"><strong>${item.position}爻</strong><span>${escapeHtml(mark || ' ')}</span></div>
    <div class="yao-spirit"><small>六神</small><strong>${escapeHtml(item.spirit || '--')}</strong></div>
    <div class="yao-hidden" title="${escapeHtml(hiddenTitle)}"><small>伏神</small><span>${escapeHtml(detailText(item.hiddenRelative, item.hiddenPillar, item.hiddenElement))}</span></div>
    <div class="yao-main"><small>本卦</small><strong>${escapeHtml(detailText(item.mainRelative, item.mainPillar, item.mainElement))}</strong><span>${escapeHtml(item.wangShuai || '')}</span></div>
    <div class="yao-symbol"><span class="yao-line${yin ? ' yin' : ''}" aria-label="${yin ? '阴爻' : '阳爻'}"></span>${item.isChanging ? `<b title="动爻">${escapeHtml(item.changeMark?.trim() || '动')}</b>` : ''}</div>
    <div class="yao-changed"><small>变卦</small><span>${escapeHtml(changed)}</span></div>
    <div class="yao-states" title="${escapeHtml(stateNote)}">${stateTags.length ? stateTags.map(tag => `<span>${escapeHtml(tag)}</span>`).join('') : '<span class="state-empty">无特殊状态</span>'}</div>
  </article>`;
}

function render(data) {
  const yao = data.yao || [];
  const bazi = ['year', 'month', 'day', 'hour'].map(key => pillarText(data.ba_zi?.[key]));
  document.querySelector('#summary-title').textContent = data.ben_gua_name || '六爻';
  document.querySelector('#summary-date').textContent = `四柱 ${bazi.join(' ')}`;
  document.querySelector('#metrics').innerHTML = [
    ['本卦', data.ben_gua_name],
    ['变卦', data.bian_gua_name || '无变卦'],
    ['动爻', yao.filter(item => item.isChanging).map(item => `${item.position}爻`).join('、') || '无'],
  ].map(([label, value]) => `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`).join('');
  const changing = yao.filter(item => item.isChanging).map(item => `${item.position}爻`).join('、') || '无';
  document.querySelector('#beginner-summary-list').innerHTML = [
    ['世爻与应爻', yao.filter(item => item.shiYingMark?.trim()).map(item => `${item.position}爻 ${item.shiYingMark.trim()}`).join('、') || '请在明细中查看', '先把自己（世）和所问对象或环境（应）分开看。'],
    ['动爻', changing, changing === '无' ? '没有动爻，重点看当前卦象的状态。' : '动爻是事情变化最明显的位置。'],
    ['本卦与变卦', `${data.ben_gua_name || '无'} · ${data.bian_gua_name || '无变卦'}`, '本卦看现在，变卦看变化后的方向。'],
  ].map(([label, value, note]) => `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd><small>${escapeHtml(note)}</small></div>`).join('');
  document.querySelector('#yao-list').innerHTML = yao.slice().reverse().map(renderYaoRow).join('');
  loadLiuyaoProfile(data);
  document.querySelector('#summary-grid').innerHTML = `
    <article class="fact-card"><h3>起课四柱</h3><p>${bazi.map(escapeHtml).join('　')}</p><p>旬空 ${escapeHtml(`${data.ba_zi?.xun_kong_1 || ''}${data.ba_zi?.xun_kong_2 || ''}` || '无')}</p></article>
    <article class="fact-card"><h3>神煞</h3><dl class="shen-sha-list">${Object.entries(data.shen_sa || {}).map(([name, branches]) => `<div><dt>${escapeHtml(name)}</dt><dd>${escapeHtml(branches.join('、'))}</dd></div>`).join('')}</dl></article>`;
  document.querySelector('#ai-text').value = buildAiText(data);
  document.querySelector('#copy-status').textContent = '';
  document.querySelector('#empty-state').hidden = true;
  document.querySelector('#result-content').hidden = false;
}

/* 卦面画像（人性化数据包）：六亲/五行/旺衰五态，组件见 profile-charts.js */
function loadLiuyaoProfile(data) {
  if (!window.ProfileCharts || !data) return;
  window.ProfileCharts.load({
    container: '#ly-profile-charts',
    fallback: '#ly-profile-fallback',
    path: '/api/v1/liu-yao/distribution',
    chart: data,
    label: null,
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

advancedToggle.addEventListener('click', () => {
  const list = document.querySelector('#yao-list');
  const expanded = list.classList.toggle('advanced-collapsed') === false;
  advancedToggle.setAttribute('aria-expanded', String(expanded));
  advancedToggle.textContent = expanded ? '隐藏辅助信息' : '显示辅助信息';
});

form.addEventListener('submit', async event => {
  event.preventDefault();
  const errorBox = document.querySelector('#form-error');
  errorBox.hidden = true;
  setLoading(true);
  try {
    const response = await fetch('/api/v1/liu-yao/charts', {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(buildRequest()),
    });
    const payload = await response.json();
    if (!response.ok || !payload.success) throw new Error(payload.error?.message || '排盘失败');
    render(payload.data);
  } catch (error) {
    errorBox.textContent = error.message;
    errorBox.hidden = false;
  } finally {
    setLoading(false);
  }
});

const helpDialog = document.querySelector('#help-dialog');
const openHelpButton = document.querySelector('#open-help');
const closeHelpButton = document.querySelector('#close-help');

openHelpButton.addEventListener('click', () => helpDialog.showModal());
closeHelpButton.addEventListener('click', () => helpDialog.close());
helpDialog.addEventListener('click', event => {
  if (event.target === helpDialog) helpDialog.close();
});

const coinDialog = document.querySelector('#coin-dialog');
const openCoinButton = document.querySelector('#open-coin-simulator');
const closeCoinButton = document.querySelector('#close-coin');
const startCoinButton = document.querySelector('#start-coin');
const resetCoinButton = document.querySelector('#reset-coin');
const coinStatus = document.querySelector('#coin-status');
const coinHistory = document.querySelector('#coin-history');
const coinFaces = [...document.querySelectorAll('.coin')];

openCoinButton.addEventListener('click', () => coinDialog.showModal());
closeCoinButton.addEventListener('click', () => coinDialog.close());
coinDialog.addEventListener('click', event => {
  if (event.target === coinDialog) coinDialog.close();
});

let throwNumber = 0;
let tossCodes = [];
let tossChanging = [];

function resetCoinSimulator() {
  throwNumber = 0; tossCodes = []; tossChanging = [];
  coinHistory.innerHTML = '';
  coinFaces.forEach(coin => { coin.textContent = '?'; coin.classList.remove('flipping'); });
  coinStatus.textContent = '每次点击一次，投掷三枚硬币，共投六次。第一次记录为初爻。';
  startCoinButton.disabled = false;
  startCoinButton.textContent = '投第 1 次';
}

async function tossCoins() {
  if (throwNumber === 0) coinHistory.innerHTML = '';
  throwNumber += 1;
  startCoinButton.disabled = true;
  resetCoinButton.disabled = true;
  coinStatus.textContent = `第 ${throwNumber} 次投掷中...`;
  coinFaces.forEach(coin => { coin.textContent = '?'; coin.classList.add('flipping'); });
  await new Promise(resolve => setTimeout(resolve, 850));
  const values = coinFaces.map(coin => { const heads = Math.random() < 0.5; coin.textContent = heads ? '正' : '反'; coin.classList.remove('flipping'); return heads ? 3 : 2; });
  const total = values.reduce((sum, value) => sum + value, 0);
  tossCodes.push(total === 6 || total === 8 ? '0' : '1');
  if (total === 6 || total === 9) tossChanging.push(throwNumber);
  const label = total === 6 ? '老阴（动）' : total === 7 ? '少阳' : total === 8 ? '少阴' : '老阳（动）';
  const row = document.createElement('div');
  row.textContent = `${throwNumber}爻：${values.map(value => value === 3 ? '正' : '反').join('、')} = ${total} · ${label}`;
  coinHistory.append(row);
  if (throwNumber === 6) {
    document.querySelector('#hexagram-code').value = tossCodes.join('');
    document.querySelector('#changing-lines').value = tossChanging.join(',');
    coinStatus.textContent = '投币完成，结果已回填。确认时间后点击“开始排盘”。';
    startCoinButton.textContent = '重新投币';
    startCoinButton.disabled = false;
    resetCoinButton.disabled = false;
    throwNumber = 0;
    return;
  }
  startCoinButton.textContent = `投第 ${throwNumber + 1} 次`;
  coinStatus.textContent = `第 ${throwNumber} 次已完成，点击按钮继续投第 ${throwNumber + 1} 次。`;
  startCoinButton.disabled = false;
  resetCoinButton.disabled = false;
}

startCoinButton.addEventListener('click', () => {
  if (startCoinButton.textContent === '重新投币') resetCoinSimulator();
  else tossCoins();
});
resetCoinButton.addEventListener('click', resetCoinSimulator);

document.querySelector('#copy-ai-text').addEventListener('click', async () => {
  const text = document.querySelector('#ai-text').value;
  const status = document.querySelector('#copy-status');
  if (!text) { status.textContent = '请先完成排盘'; return; }
  try {
    await navigator.clipboard.writeText(text);
    status.textContent = '已复制，可粘贴到 AI 对话框';
  } catch {
    const textarea = document.querySelector('#ai-text');
    textarea.focus(); textarea.select();
    status.textContent = '自动复制失败，已选中文本，请按 Command/Ctrl+C 复制';
  }
});
