const API_ROOT = '/api/v1/ziwei/research/ai-review';
const providerList = document.querySelector('#provider-list');
const form = document.querySelector('#experiment-form');
const toast = document.querySelector('#toast');

let meta = null;
let providers = [];
let experiments = [];
let activeExperiment = null;
let activeResults = null;
let pollTimer = null;
let toastTimer = null;

function create(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function showToast(message) {
  toast.textContent = message;
  toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.hidden = true; }, 3200);
}

async function api(path, options = {}) {
  const response = await fetch(`${API_ROOT}${path}`, {
    ...options,
    headers: options.body ? { 'Content-Type': 'application/json', ...(options.headers || {}) } : options.headers,
  });
  const payload = await response.json();
  if (!response.ok || !payload.success) throw new Error(payload.error?.message || '研究服务返回错误');
  return payload.data;
}

function field(label, value, type, onInput, options = {}) {
  const wrap = create('div', options.wide ? 'field-wide' : '');
  const id = options.id;
  const labelNode = create('label', '', label);
  labelNode.htmlFor = id;
  let input;
  if (type === 'select') {
    input = create('select');
    options.items.forEach(item => {
      const option = create('option', '', item.label);
      option.value = item.value;
      option.selected = String(value) === String(item.value);
      input.appendChild(option);
    });
  } else {
    input = create('input');
    input.type = type;
    input.value = value ?? '';
    if (options.placeholder) input.placeholder = options.placeholder;
    if (options.min !== undefined) input.min = options.min;
    if (options.max !== undefined) input.max = options.max;
    if (options.step !== undefined) input.step = options.step;
    if (options.autocomplete) input.autocomplete = options.autocomplete;
  }
  input.id = id;
  input.addEventListener('input', () => onInput(input.value));
  input.addEventListener('change', () => onInput(input.value));
  wrap.append(labelNode, input);
  return wrap;
}

function updateScale() {
  const selected = providers.filter(item => item.selected);
  document.querySelector('#provider-count').textContent = selected.length;
  document.querySelector('#task-count').textContent = selected.reduce((sum, item) => sum + Number(item.repetitions || 0) * 8, 0);
  document.querySelector('#start-experiment').disabled = selected.length === 0;
}

function renderProviders() {
  providerList.replaceChildren();
  if (!providers.length) {
    providerList.appendChild(create('p', 'empty-copy', '本地配置中没有已启用的模型'));
    updateScale();
    return;
  }
  providers.forEach((provider, index) => {
    const card = create('section', 'provider-card');
    const header = create('header');
    const selectLabel = create('label');
    const checkbox = create('input');
    checkbox.type = 'checkbox';
    checkbox.checked = provider.selected;
    checkbox.addEventListener('change', () => { provider.selected = checkbox.checked; updateScale(); });
    selectLabel.append(checkbox, create('strong', '', provider.label));
    header.append(selectLabel, create('span', 'connection-status', provider.has_api_key ? '已配密钥' : '无密钥'));
    const facts = create('dl', 'provider-facts');
    [['协议', provider.protocol === 'openai_compatible' ? 'OpenAI 兼容' : 'Ollama'], ['模型', provider.model], ['系列', provider.model_family], ['地址', provider.base_url]].forEach(([term, value]) => {
      const row = create('div');
      row.append(create('dt', '', term), create('dd', '', value));
      facts.appendChild(row);
    });
    const grid = create('div', 'field-grid');
    const id = suffix => `provider-${index}-${suffix}`;
    grid.append(
      field('温度', provider.temperature, 'number', value => { provider.temperature = Number(value); updateScale(); }, { id: id('temperature'), min: 0, max: 2, step: 0.1 }),
      field('重复运行', provider.repetitions, 'select', value => { provider.repetitions = Number(value); updateScale(); }, { id: id('repetitions'), items: [1, 2, 3, 4, 5].map(value => ({ value, label: `${value} 次` })) }),
      field('模型随机种子', provider.model_seed, 'number', value => { provider.model_seed = value === '' ? null : Number(value); updateScale(); }, { id: id('seed'), wide: true, step: 1 }),
    );
    const connection = create('div', 'connection-row');
    const testButton = create('button', '', '测试连接');
    testButton.type = 'button';
    const status = create('span', `connection-status ${provider.statusType}`, provider.status || '尚未测试');
    testButton.addEventListener('click', async () => {
      testButton.disabled = true;
      status.className = 'connection-status';
      status.textContent = '正在连接';
      try {
        const result = await api('/connections/test', { method: 'POST', body: JSON.stringify({ provider_id: provider.provider_id }) });
        provider.statusType = 'success';
        provider.status = result.configured_model_found ? `连接成功 · 已找到 ${provider.model}` : `连接成功 · 未在列表中找到 ${provider.model}`;
      } catch (error) {
        provider.statusType = 'error';
        provider.status = error.message;
      } finally {
        testButton.disabled = false;
        status.className = `connection-status ${provider.statusType}`;
        status.textContent = provider.status;
      }
    });
    connection.append(testButton, status);
    card.append(header, facts, grid, connection);
    providerList.appendChild(card);
  });
  updateScale();
}

function statusLabel(status) {
  return ({ queued: '排队中', running: '运行中', completed: '已完成', completed_with_errors: '完成但有失败', failed: '运行失败', cancelled: '已停止', interrupted: '服务中断' })[status] || status;
}

function renderExperiment(experiment) {
  activeExperiment = experiment;
  document.querySelector('#overview-title').textContent = experiment ? experiment.id : '尚未开始实验';
  document.querySelector('#metric-status').textContent = experiment ? statusLabel(experiment.status) : '待配置';
  document.querySelector('#metric-complete').textContent = experiment ? `${experiment.completed_tasks} / ${experiment.total_tasks}` : '0 / 0';
  document.querySelector('#metric-failed').textContent = experiment?.failed_tasks ?? 0;
  document.querySelector('#metric-families').textContent = experiment ? new Set(experiment.providers.map(item => item.model_family)).size : 0;
  const progress = experiment?.progress_percent ?? 0;
  document.querySelector('#experiment-progress').style.width = `${progress}%`;
  document.querySelector('#progress-text').textContent = `${progress}%`;
  const running = experiment && ['queued', 'running'].includes(experiment.status);
  document.querySelector('#cancel-experiment').hidden = !running;
  document.querySelector('#export-results').disabled = !activeResults;
}

function renderHistory() {
  const container = document.querySelector('#experiment-history');
  container.replaceChildren();
  if (!experiments.length) {
    container.appendChild(create('p', 'empty-copy', '暂无实验记录'));
    return;
  }
  experiments.forEach(item => {
    const button = create('button', 'history-item');
    button.type = 'button';
    button.setAttribute('aria-current', String(activeExperiment?.id === item.id));
    button.append(create('strong', '', item.id), create('span', '', statusLabel(item.status)), create('small', '', `${item.completed_tasks}/${item.total_tasks} 完成 · ${item.providers.length} 个连接`));
    button.addEventListener('click', () => selectExperiment(item.id));
    container.appendChild(button);
  });
}

function renderDimensions(dimensions = []) {
  const container = document.querySelector('#dimension-results');
  container.replaceChildren();
  if (!dimensions.length) {
    container.appendChild(create('p', 'empty-copy', '实验产生有效评分后显示结果'));
    return;
  }
  dimensions.forEach(item => {
    const row = create('div', 'dimension-row');
    const copy = create('div', 'dimension-copy');
    copy.append(create('strong', '', item.name), create('code', '', item.dimension_id));
    const bar = create('div', 'direction-bar');
    const total = item.score_count || 1;
    ['negative', 'neutral', 'positive'].forEach(direction => {
      const count = item.model_case_direction_counts[direction];
      const segment = create('i', direction, count ? String(count) : '');
      segment.style.width = `${count / total * 100}%`;
      if (!count) segment.hidden = true;
      bar.appendChild(segment);
    });
    const mean = create('span', 'dimension-number', item.mean_score === null ? '--' : `${item.mean_score > 0 ? '+' : ''}${item.mean_score}`);
    const prevalence = create('div', 'consensus');
    prevalence.append(create('strong', '', item.direction_prevalence_ratio === null ? '--' : `${Math.round(item.direction_prevalence_ratio * 100)}%`), create('small', '', `${item.model_case_count} 个模型-案例单元`));
    const agreementValue = item.within_case_cross_model_agreement ?? item.cross_model_descriptive_consensus_ratio;
    const agreement = create('div', 'consensus');
    agreement.append(create('strong', '', agreementValue === null || agreementValue === undefined ? '--' : `${Math.round(agreementValue * 100)}%`), create('small', '', `${item.unanimous_case_count ?? 0}/${item.comparable_case_count ?? 0} 案例完全一致`));
    row.append(copy, bar, mean, prevalence, agreement);
    container.appendChild(row);
  });
}

function renderStability(items = []) {
  const container = document.querySelector('#stability-results');
  container.replaceChildren();
  if (!items.length) {
    container.appendChild(create('p', 'empty-copy', '需要重复运行后才可计算'));
    return;
  }
  items.forEach(item => {
    const row = create('div', 'stability-item');
    const copy = create('div');
    copy.append(create('strong', '', item.provider_label), create('small', '', `${item.model_family} · ${item.repetitions} 次运行`));
    row.append(copy, create('b', '', item.mean_exact_pair_agreement === null ? '--' : `${Math.round(item.mean_exact_pair_agreement * 100)}%`));
    container.appendChild(row);
  });
}

function renderRuns() {
  const container = document.querySelector('#run-results');
  container.replaceChildren();
  const filter = document.querySelector('#run-filter').value;
  const runs = (activeResults?.runs || []).filter(item => filter === 'all' || item.status === filter);
  if (!runs.length) {
    container.appendChild(create('p', 'empty-copy', '当前没有符合条件的运行记录'));
    return;
  }
  runs.forEach(item => {
    const row = create('div', `run-item ${item.status}`);
    row.append(create('strong', '', item.provider_label), create('span', '', `第 ${item.repetition} 轮`), create('code', '', item.case_code), create('span', 'status', statusLabel(item.status)));
    if (item.error_message) row.appendChild(create('p', '', item.error_message));
    container.appendChild(row);
  });
}

async function loadHistory() {
  experiments = await api('/experiments');
  renderHistory();
}

async function selectExperiment(id) {
  try {
    const [experiment, results] = await Promise.all([api(`/experiments/${id}`), api(`/experiments/${id}/results`)]);
    activeResults = results;
    renderExperiment(experiment);
    renderDimensions(results.dimensions);
    renderStability(results.provider_stability);
    renderRuns();
    renderHistory();
    schedulePoll();
  } catch (error) {
    showToast(error.message);
  }
}

function schedulePoll() {
  clearTimeout(pollTimer);
  if (!activeExperiment || !['queued', 'running'].includes(activeExperiment.status)) return;
  pollTimer = setTimeout(async () => {
    await selectExperiment(activeExperiment.id);
    await loadHistory();
  }, 1800);
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  const errorNode = document.querySelector('#form-error');
  const button = document.querySelector('#start-experiment');
  errorNode.hidden = true;
  button.disabled = true;
  button.classList.add('loading');
  try {
    const selected = providers.filter(item => item.selected);
    const experiment = await api('/experiments', {
      method: 'POST',
      body: JSON.stringify({
        seed: document.querySelector('#experiment-seed').value,
        provider_ids: selected.map(item => item.provider_id),
        overrides: Object.fromEntries(selected.map(item => [item.provider_id, {
          temperature: item.temperature,
          repetitions: item.repetitions,
          model_seed: item.model_seed,
        }])),
      }),
    });
    activeResults = null;
    renderExperiment(experiment);
    renderDimensions();
    renderStability();
    renderRuns();
    await loadHistory();
    schedulePoll();
    showToast('实验已进入后台运行');
  } catch (error) {
    errorNode.textContent = error.message;
    errorNode.hidden = false;
  } finally {
    button.disabled = false;
    button.classList.remove('loading');
  }
});

document.querySelector('#reload-config').addEventListener('click', async () => {
  try { await loadMeta(); showToast('模型配置已重载'); } catch (error) { showToast(error.message); }
});
document.querySelector('#refresh-history').addEventListener('click', loadHistory);
document.querySelector('#run-filter').addEventListener('change', renderRuns);
document.querySelector('#cancel-experiment').addEventListener('click', async () => {
  if (!activeExperiment) return;
  try {
    await api(`/experiments/${activeExperiment.id}/cancel`, { method: 'POST', body: '{}' });
    showToast('已请求停止，当前调用结束后生效');
    schedulePoll();
  } catch (error) { showToast(error.message); }
});
document.querySelector('#export-results').addEventListener('click', () => {
  if (!activeResults) return;
  const blob = new Blob([JSON.stringify(activeResults, null, 2)], { type: 'application/json' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `${activeResults.experiment.id}-results.json`;
  link.click();
  URL.revokeObjectURL(link.href);
});

async function start() {
  try {
    await loadMeta();
    await loadHistory();
    if (experiments.length) await selectExperiment(experiments[0].id);
  } catch (error) {
    const errorNode = document.querySelector('#form-error');
    errorNode.textContent = error.message;
    errorNode.hidden = false;
  }
}

async function loadMeta() {
  meta = await api('/meta');
  document.querySelector('#packet-preview').textContent = `协议 ${meta.protocol.protocol_version} · 提示词 ${meta.protocol.prompt_version}`;
  document.querySelector('#provider-config-path').textContent = meta.provider_config_path;
  const previous = new Map(providers.map(item => [item.provider_id, item]));
  providers = meta.providers.map(item => ({
    ...item,
    selected: previous.get(item.provider_id)?.selected || false,
    temperature: previous.get(item.provider_id)?.temperature ?? item.temperature,
    repetitions: previous.get(item.provider_id)?.repetitions ?? item.repetitions,
    model_seed: previous.get(item.provider_id)?.model_seed ?? item.model_seed,
    status: '', statusType: '',
  }));
  renderProviders();
}

start();
