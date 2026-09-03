const app = document.querySelector('#review-app');
const loadingState = document.querySelector('#loading-state');
const errorState = document.querySelector('#error-state');
const errorMessage = document.querySelector('#error-message');
const caseList = document.querySelector('#case-list');
const dimensionList = document.querySelector('#dimension-list');
const importFile = document.querySelector('#import-file');
const toast = document.querySelector('#toast');

let packet = null;
let submission = null;
let currentCaseIndex = 0;
let toastTimer = null;

function storageKey() {
  return `zhouyilab-blind-review:${packet.packet_id}`;
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function showToast(message) {
  toast.textContent = message;
  toast.hidden = false;
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => { toast.hidden = true; }, 2800);
}

function saveProgress() {
  if (!packet || !submission) return;
  try {
    localStorage.setItem(storageKey(), JSON.stringify(submission));
    document.querySelector('#save-status').textContent = `已保存 · ${new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`;
  } catch (_) {
    document.querySelector('#save-status').textContent = '本地保存失败，请及时导出';
  }
}

function normalizeSubmission(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('评分文件格式不正确');
  if (value.packet_id !== packet.packet_id) throw new Error('评分文件不属于当前盲评包');
  if (typeof value.rater_id !== 'string' || typeof value.rater_group !== 'string') throw new Error('评分者字段必须是文本');

  const caseCodes = new Set(packet.cases.map(item => item.case_code));
  const dimensionIds = new Set(packet.dimensions.map(item => item.id));
  const allowedScores = new Set(packet.rating_scale.allowed_values);
  if (!Array.isArray(value.ratings) || value.ratings.length !== caseCodes.size) throw new Error('评分文件案例数量不正确');

  const normalized = clone(value);
  const submittedCases = new Set();
  normalized.ratings.forEach(caseRating => {
    if (!caseRating || typeof caseRating !== 'object' || !caseCodes.has(caseRating.case_code)) throw new Error('评分文件包含未知案例');
    if (submittedCases.has(caseRating.case_code)) throw new Error('评分文件包含重复案例');
    submittedCases.add(caseRating.case_code);
    if (!Array.isArray(caseRating.dimensions) || caseRating.dimensions.length !== dimensionIds.size) throw new Error('评分文件维度数量不正确');

    const submittedDimensions = new Set();
    caseRating.dimensions.forEach(rating => {
      if (!rating || typeof rating !== 'object' || !dimensionIds.has(rating.dimension_id)) throw new Error('评分文件包含未知维度');
      if (submittedDimensions.has(rating.dimension_id)) throw new Error('评分文件包含重复维度');
      submittedDimensions.add(rating.dimension_id);
      if (rating.score !== null && !allowedScores.has(rating.score)) throw new Error('评分文件包含量尺之外的分值');
      if (typeof rating.rationale !== 'string') throw new Error('判断依据必须是文本');
      if (typeof rating.reviewed !== 'boolean') {
        rating.reviewed = rating.score !== null || Boolean(rating.rationale.trim());
      } else if (!rating.reviewed && (rating.score !== null || rating.rationale.trim())) {
        rating.reviewed = true;
      }
    });
  });
  return normalized;
}

function initializeSubmission() {
  const saved = localStorage.getItem(storageKey());
  if (saved) {
    try {
      submission = normalizeSubmission(JSON.parse(saved));
    } catch (_) {
      localStorage.removeItem(storageKey());
    }
  }
  if (!submission) submission = normalizeSubmission(packet.submission_template);
}

function caseRatingByCode(code) {
  return submission.ratings.find(item => item.case_code === code);
}

function dimensionRating(code, dimensionId) {
  return caseRatingByCode(code).dimensions.find(item => item.dimension_id === dimensionId);
}

function ratingComplete(rating) {
  if (!rating.reviewed) return false;
  return rating.score === null || Boolean(String(rating.rationale || '').trim());
}

function caseProgress(code) {
  const ratings = caseRatingByCode(code).dimensions;
  return {
    completed: ratings.filter(ratingComplete).length,
    total: ratings.length,
  };
}

function completedCases() {
  return packet.cases.filter(item => {
    const progress = caseProgress(item.case_code);
    return progress.completed === progress.total;
  }).length;
}

function create(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderNavigation() {
  caseList.replaceChildren();
  packet.cases.forEach((item, index) => {
    const progress = caseProgress(item.case_code);
    const button = create('button');
    button.type = 'button';
    button.setAttribute('aria-current', String(index === currentCaseIndex));
    button.classList.toggle('complete', progress.completed === progress.total);
    button.append(
      create('span', 'case-index', String(index + 1).padStart(2, '0')),
      create('strong', '', item.case_code),
      create('small', '', `${progress.completed}/${progress.total}`),
    );
    button.addEventListener('click', () => {
      currentCaseIndex = index;
      renderCase();
    });
    caseList.appendChild(button);
  });
  const complete = completedCases();
  document.querySelector('#case-count').textContent = `${complete} / ${packet.cases.length}`;
  document.querySelector('#header-progress-text').textContent = `${complete} / ${packet.cases.length}`;
  document.querySelector('#header-progress-bar').style.width = `${complete / packet.cases.length * 100}%`;
}

function renderFacts(caseData) {
  const table = document.querySelector('#fact-table');
  table.replaceChildren();
  const head = create('div', 'fact-row head');
  ['星曜', '实际位置', '关系', '地支', '亮度', '四化 / 证据身份'].forEach(label => head.appendChild(create('span', '', label)));
  table.appendChild(head);
  caseData.stars.forEach(star => {
    const row = create('div', 'fact-row');
    const status = create('span', `fact-tag${star.fact_status === 'controlled_stimulus' ? ' controlled' : ''}`, star.fact_status === 'controlled_stimulus' ? '受控刺激' : '位置事实');
    const finalCell = create('div');
    if (star.transformation) finalCell.appendChild(create('strong', '', star.transformation));
    finalCell.appendChild(status);
    row.append(
      create('strong', '', star.name),
      create('span', '', star.physical_palace),
      create('span', '', relationLabel(star.relation)),
      create('span', '', star.earthly_branch),
      create('span', '', star.brightness),
      finalCell,
    );
    table.appendChild(row);
  });

  const stimulusList = document.querySelector('#stimulus-list');
  stimulusList.replaceChildren();
  stimulusList.hidden = caseData.transformation_signals.length === 0;
  caseData.transformation_signals.forEach(signal => {
    const row = create('div', 'stimulus-row');
    row.append(
      create('strong', '', signal.transformation),
      create('span', '', relationLabel(signal.relation)),
      create('span', '', signal.physical_palace),
      create('span', '', signal.boundary),
    );
    stimulusList.appendChild(row);
  });
}

function relationLabel(relation) {
  return ({ self: '本宫', triad: '三合', opposite: '对宫' })[relation] || relation;
}

function scoreOption(caseCode, dimensionId, value, label, rating) {
  const option = create('label');
  const input = create('input');
  input.type = 'radio';
  input.name = `score-${caseCode}-${dimensionId}`;
  input.value = value;
  const isSkip = value === 'skip';
  input.checked = isSkip
    ? rating.reviewed && rating.score === null
    : rating.reviewed && rating.score === Number(value);
  input.addEventListener('change', () => {
    rating.reviewed = true;
    rating.score = isSkip ? null : Number(value);
    saveProgress();
    renderNavigation();
    updateCaseCompletion(caseCode);
  });
  option.append(input, create('span', '', label));
  return option;
}

function renderDimensions(caseData) {
  dimensionList.replaceChildren();
  packet.dimensions.forEach(dimension => {
    const rating = dimensionRating(caseData.case_code, dimension.id);
    const row = create('section', 'dimension-row');
    const copyBlock = create('div', 'dimension-copy');
    const heading = create('header');
    heading.append(create('h3', '', dimension.name), create('code', '', dimension.id));
    copyBlock.append(heading, create('p', '', dimension.definition));

    const controls = create('div', 'score-control');
    [
      ['-1', '-1'], ['-0.5', '-0.5'], ['0', '0'],
      ['0.5', '+0.5'], ['1', '+1'], ['skip', '无法判断'],
    ].forEach(([value, label]) => controls.appendChild(
      scoreOption(caseData.case_code, dimension.id, value, label, rating)
    ));

    const rationale = create('textarea', 'rationale-input');
    rationale.rows = 2;
    rationale.placeholder = rating.score === null && rating.reviewed ? '无法判断时可留空' : '填写判断依据';
    rationale.value = rating.rationale || '';
    rationale.setAttribute('aria-label', `${dimension.name}判断依据`);
    rationale.addEventListener('input', () => {
      rating.rationale = rationale.value;
      rationale.classList.remove('invalid');
      saveProgress();
      renderNavigation();
      updateCaseCompletion(caseData.case_code);
    });
    row.append(copyBlock, controls, rationale);
    dimensionList.appendChild(row);
  });
}

function updateCaseCompletion(code) {
  const progress = caseProgress(code);
  document.querySelector('#case-completion').textContent = `${progress.completed} / ${progress.total}`;
}

function renderCase() {
  const caseData = packet.cases[currentCaseIndex];
  document.querySelector('#case-code').textContent = caseData.case_code;
  document.querySelector('#case-layer').textContent = caseData.source_layer === 'natal' ? '本命' : caseData.source_layer;
  document.querySelector('#case-branch').textContent = caseData.focus.earthly_branch;
  renderFacts(caseData);
  renderDimensions(caseData);
  renderNavigation();
  updateCaseCompletion(caseData.case_code);
  document.querySelector('#previous-case').disabled = currentCaseIndex === 0;
  document.querySelector('#next-case').textContent = currentCaseIndex === packet.cases.length - 1 ? '完成检查' : '下一案例';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function validateCase(caseData, markInvalid = false) {
  const ratings = caseRatingByCode(caseData.case_code).dimensions;
  const errors = [];
  ratings.forEach((rating, index) => {
    if (!rating.reviewed) errors.push(`${packet.dimensions[index].name}尚未判断`);
    if (rating.reviewed && rating.score !== null && !String(rating.rationale || '').trim()) {
      errors.push(`${packet.dimensions[index].name}缺少依据`);
      if (markInvalid) dimensionList.querySelectorAll('.rationale-input')[index]?.classList.add('invalid');
    }
  });
  return errors;
}

function validateSubmission() {
  const errors = [];
  if (!String(submission.rater_id || '').trim() || submission.rater_id === 'REPLACE_WITH_ANONYMOUS_ID') errors.push('请填写匿名评分者 ID');
  if (!String(submission.rater_group || '').trim() || submission.rater_group === 'REPLACE_WITH_SCHOOL_OR_COHORT') errors.push('请填写流派或组别');
  packet.cases.forEach((caseData, index) => {
    if (validateCase(caseData).length) errors.push(`案例 ${index + 1} 尚未完成`);
  });
  return errors;
}

function cleanSubmission() {
  const output = clone(submission);
  output.rater_id = output.rater_id.trim();
  output.rater_group = output.rater_group.trim();
  return output;
}

function downloadSubmission() {
  const errors = validateSubmission();
  if (errors.length) {
    const firstIncomplete = packet.cases.findIndex(item => validateCase(item).length);
    if (firstIncomplete >= 0) {
      currentCaseIndex = firstIncomplete;
      renderCase();
      validateCase(packet.cases[firstIncomplete], true);
    }
    showToast(errors[0]);
    return;
  }
  const output = cleanSubmission();
  const blob = new Blob([JSON.stringify(output, null, 2)], { type: 'application/json' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `${packet.packet_id}-${output.rater_id}.json`;
  link.click();
  URL.revokeObjectURL(link.href);
  showToast('评分 JSON 已导出');
}

async function importSubmission(file) {
  try {
    submission = normalizeSubmission(JSON.parse(await file.text()));
    document.querySelector('#rater-id').value = submission.rater_id || '';
    document.querySelector('#rater-group').value = submission.rater_group || '';
    saveProgress();
    renderCase();
    showToast('评分进度已导入');
  } catch (error) {
    showToast(error.message || '评分文件无法读取');
  } finally {
    importFile.value = '';
  }
}

function bindEvents() {
  const raterId = document.querySelector('#rater-id');
  const raterGroup = document.querySelector('#rater-group');
  raterId.value = submission.rater_id === 'REPLACE_WITH_ANONYMOUS_ID' ? '' : submission.rater_id;
  raterGroup.value = submission.rater_group === 'REPLACE_WITH_SCHOOL_OR_COHORT' ? '' : submission.rater_group;
  raterId.addEventListener('input', () => { submission.rater_id = raterId.value; saveProgress(); });
  raterGroup.addEventListener('input', () => { submission.rater_group = raterGroup.value; saveProgress(); });
  document.querySelector('#previous-case').addEventListener('click', () => {
    if (currentCaseIndex > 0) { currentCaseIndex -= 1; renderCase(); }
  });
  document.querySelector('#next-case').addEventListener('click', () => {
    const errors = validateCase(packet.cases[currentCaseIndex], true);
    if (errors.length) { showToast(errors[0]); return; }
    if (currentCaseIndex < packet.cases.length - 1) {
      currentCaseIndex += 1;
      renderCase();
    } else {
      const allErrors = validateSubmission();
      showToast(allErrors.length ? allErrors[0] : '全部案例已完成，可以导出评分');
    }
  });
  document.querySelector('#export-button').addEventListener('click', downloadSubmission);
  importFile.addEventListener('change', () => {
    if (importFile.files[0]) importSubmission(importFile.files[0]);
  });
  document.querySelector('#clear-button').addEventListener('click', () => {
    if (!window.confirm('清空当前盲评包在本机保存的全部进度？')) return;
    localStorage.removeItem(storageKey());
    submission = normalizeSubmission(packet.submission_template);
    currentCaseIndex = 0;
    document.querySelector('#rater-id').value = '';
    document.querySelector('#rater-group').value = '';
    renderCase();
    showToast('本地进度已清空');
  });
}

async function start() {
  try {
    const seed = new URLSearchParams(location.search).get('seed') || 'pilot-2026';
    const response = await fetch(`/api/v1/ziwei/research/blind-review/packet?seed=${encodeURIComponent(seed)}`);
    const payload = await response.json();
    if (!response.ok || !payload.success) throw new Error(payload.error?.message || '研究接口返回错误');
    packet = payload.data;
    document.querySelector('#packet-id').textContent = packet.packet_id;
    initializeSubmission();
    bindEvents();
    renderCase();
    loadingState.hidden = true;
    app.hidden = false;
  } catch (error) {
    loadingState.hidden = true;
    errorMessage.textContent = error.message || '无法取得盲评数据';
    errorState.hidden = false;
  }
}

start();
