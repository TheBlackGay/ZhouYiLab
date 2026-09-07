const form = document.querySelector('#bazi-form');
const submitButton = form.querySelector('.primary-action');
const errorBox = document.querySelector('#form-error');
const emptyState = document.querySelector('#empty-state');
const resultContent = document.querySelector('#result-content');
const trueSolarInput = document.querySelector('#true-solar');
const solarOptions = document.querySelector('#solar-options');
const pillarNames = { year: '年柱', month: '月柱', day: '日柱', hour: '时柱' };
let currentData = null;
const shenShaDialog = document.querySelector('#shen-sha-dialog');
const shenShaDialogContent = document.querySelector('#shen-sha-dialog-content');
const shenShaResourceCache = new Map();
const shenShaIds = {
  '暗金的煞': 'an_jin_de_sha', '德秀贵人': 'de_xiu_gui_ren', '干支诸字杂犯神煞': 'gan_zhi_zi_za_fan',
  '勾绞煞': 'gou_jiao_sha', '孤辰寡宿及隔角煞': 'gu_chen_gua_su', '劫煞、亡神': 'jie_sha_wang_shen', '劫煞': 'jie_sha_wang_shen', '亡神': 'jie_sha_wang_shen',
  '劫煞十六般': 'jie_sha_shi_liu_ban', '金舆': 'jin_yu', '空亡': 'kong_wang', '六厄': 'liu_e',
  '禄神': 'lu_shen', '其他神煞（一）': 'qi_ta_shen_sha_1', '其他神煞（二）': 'qi_ta_shen_sha_2',
  '其他神煞（三）': 'qi_ta_shen_sha_3', '其他神煞（四）': 'qi_ta_shen_sha_4', '三奇贵人': 'san_qi_gui_ren',
  '十恶大败': 'shi_e_da_bai', '太极贵': 'tai_ji_gui', '太极贵人': 'tai_ji_gui',
  '天罗地网': 'tian_luo_di_wang', '天罗': 'tian_luo_di_wang', '地网': 'tian_luo_di_wang', '天乙贵人': 'tian_yi_gui_ren', '天月德': 'tian_yue_de',
  '亡神十六般': 'wang_shen_shi_liu_ban', '孤辰': 'gu_chen_gua_su', '寡宿': 'gu_chen_gua_su', '天德贵人': 'tian_yue_de', '月德合': 'tian_yue_de', '学堂词馆': 'xue_tang_ci_guan', '羊刃': 'yang_ren',
  '华盖': 'yin_shen_si_hai_si_gong_hu_huan_shen_sha', '阴差阳错煞': 'qi_ta_shen_sha_4', '淫欲妨害煞': 'qi_ta_shen_sha_4', '桃花煞': 'qi_ta_shen_sha_3',
  '驿马': 'yi_ma', '元辰': 'yuan_chen', '灾煞': 'zai_sha', '童子煞': 'qi_ta_shen_sha_2', '战斗伏降刑冲破合': 'zhan_dou_fu_jiang_xing_chong_po_he',
  '正印': 'zheng_yin', '总论禄马': 'zong_lun_lu_ma', '总论诸神煞': 'zong_lun_shen_sha',
  '官符煞': 'qi_ta_shen_sha_2', '病符煞': 'qi_ta_shen_sha_2', '死符煞': 'qi_ta_shen_sha_2', '吊客': 'qi_ta_shen_sha_2', '丧吊煞': 'qi_ta_shen_sha_2', '宅墓煞': 'qi_ta_shen_sha_2',
  '桃花红艳煞': 'qi_ta_shen_sha_3', '阴阳煞': 'qi_ta_shen_sha_4', '孤鸾寡鹄煞': 'qi_ta_shen_sha_4', '天火煞': 'qi_ta_shen_sha_1',
  '自缢煞': 'qi_ta_shen_sha_1', '水溺煞': 'qi_ta_shen_sha_1', '挂剑煞': 'qi_ta_shen_sha_1', '天屠煞': 'qi_ta_shen_sha_1', '天刑煞': 'qi_ta_shen_sha_1', '雷霆煞': 'qi_ta_shen_sha_1', '吞陷煞': 'qi_ta_shen_sha_1', '破煞': 'qi_ta_shen_sha_3',
  '国印贵人': 'qi_ta_shen_sha_1', '福星贵人': 'qi_ta_shen_sha_1', '飞刃': 'qi_ta_shen_sha_3', '丧门': 'qi_ta_shen_sha_2',
  '将星': 'qi_ta_shen_sha_1', '红艳煞': 'qi_ta_shen_sha_3', '文昌贵人': 'tai_ji_gui',
  '天厨贵人': 'qi_ta_shen_sha_1', '流霞': 'qi_ta_shen_sha_3',
  '子午卯酉四宫互换神煞': 'zi_wu_mao_you_si_gong_hu_huan_shen_sha',
  '寅申巳亥四宫互换神煞': 'yin_shen_si_hai_si_gong_hu_huan_shen_sha',
  '辰戌丑未四宫互换神煞': 'chen_xu_chou_wei_si_gong_hu_huan_shen_sha',
  '学堂': 'xue_tang_ci_guan', '词馆': 'xue_tang_ci_guan', '桃花': 'qi_ta_shen_sha_3', '咸池': 'qi_ta_shen_sha_3',
  '天德贵人': 'tian_yue_de', '月德贵人': 'tian_yue_de', '德秀': 'de_xiu_gui_ren',
  '大耗': 'yuan_chen', '勾绞': 'gou_jiao_sha', '爪牙煞': 'gou_jiao_sha',
  '龙蛇混杂': 'tian_luo_di_wang', '猪犬侵凌': 'tian_luo_di_wang',
  '无禄日': 'shi_e_da_bai', '劫煞十六般格局': 'jie_sha_shi_liu_ban', '亡神十六般格局': 'wang_shen_shi_liu_ban',
  '天禄天马': 'zong_lun_lu_ma', '禄马交驰': 'zong_lun_lu_ma', '禄马同乡': 'zong_lun_lu_ma',
  '夹禄夹马': 'zong_lun_lu_ma', '生旺禄': 'zong_lun_lu_ma', '名位禄': 'zong_lun_lu_ma',
  '真禄': 'zong_lun_lu_ma', '进退真禄': 'zong_lun_lu_ma', '食神合禄': 'zong_lun_lu_ma', '天禄贵神': 'zong_lun_lu_ma',
  '四库': 'chen_xu_chou_wei_si_gong_hu_huan_shen_sha', '四墓': 'chen_xu_chou_wei_si_gong_hu_huan_shen_sha',
  '长生': 'yin_shen_si_hai_si_gong_hu_huan_shen_sha', '进神': 'zi_wu_mao_you_si_gong_hu_huan_shen_sha',
  '贵人': 'zi_wu_mao_you_si_gong_hu_huan_shen_sha', '悬针': 'gan_zhi_zi_za_fan', '阴错阳差': 'qi_ta_shen_sha_3',
  '禄马': 'zong_lun_lu_ma', '四库': 'chen_xu_chou_wei_si_gong_hu_huan_shen_sha', '四墓': 'chen_xu_chou_wei_si_gong_hu_huan_shen_sha',
  '隔角': 'gu_chen_gua_su',
  '龙蛇混杂': 'tian_luo_di_wang', '猪犬侵凌': 'tian_luo_di_wang',
  '白虎': 'qi_ta_shen_sha_1', '平头煞': 'gan_zhi_zi_za_fan', '破字煞': 'gan_zhi_zi_za_fan',
  '悬针煞': 'gan_zhi_zi_za_fan', '杖刑煞': 'gan_zhi_zi_za_fan', '曲脚煞': 'gan_zhi_zi_za_fan',
  '吟呻': 'an_jin_de_sha', '破碎': 'an_jin_de_sha', '白衣': 'an_jin_de_sha',
  '日刑煞': 'qi_ta_shen_sha_3', '流血煞': 'qi_ta_shen_sha_3', '剑锋煞': 'qi_ta_shen_sha_3',
  '戟锋煞': 'qi_ta_shen_sha_3', '浮沉煞': 'qi_ta_shen_sha_3', '返本煞': 'qi_ta_shen_sha_4', '短寿煞': 'qi_ta_shen_sha_4',
};

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
    const shenSha = (pillar.shen_sha || []).map(name => {
      const resourceId = shenShaIds[name];
      if (!resourceId) return `<span>${escapeHtml(name)}</span>`;
      return `<button type="button" data-shen-sha-id="${resourceId}" aria-label="查看${escapeHtml(name)}说明" title="查看说明">${escapeHtml(name)}</button>`;
    }).join('');
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

function currentShenShaDetails(id) {
  if (!currentData) return [];
  return ['year', 'month', 'day', 'hour'].flatMap(key =>
    (currentData.pillars[key].shen_sha_details || [])
      .filter(item => item.id === id)
      .map(item => ({ ...item, pillar: pillarNames[key] }))
  );
}

function renderShenShaCatalog(data) {
  const matched = new Set(['year', 'month', 'day', 'hour'].flatMap(key => data.pillars[key].shen_sha || []));
  const summary = data.shen_sha_summary || {};
  const yiMaEvidence = (summary.yi_ma?.occurrences || []).map(item => `${item.pillar}${item.source === 'yearBranch' ? '年支' : '日支'}`).join('、');
  const tianYiEvidence = (summary.tian_yi_gui_ren?.occurrences || []).map(item => `${item.pillar}${item.method === 'tianyige_guanglu' ? '古诀' : '通行'}`).join('、');
  const sanQiEvidence = (summary.san_qi?.occurrences || []).map(item => `${item.type}（${item.positions}）`).join('、');
  const relations = summary.relations || {};
  const relationItems = [
    ...(relations.branch_relations || []),
    ...(relations.stem_relations || []),
    ...(relations.interchanges || []),
    ...(relations.sanhe_ju || []),
  ];
  const relationEvidence = relationItems.slice(0, 4).map(item => {
    const type = item.type || (item.element ? '三合局' : '关系');
    return item.detail ? `${type}：${item.detail}` : type;
  }).join('、');
  const evidence = [
    yiMaEvidence && `驿马：${yiMaEvidence}`,
    tianYiEvidence && `天乙：${tianYiEvidence}`,
    sanQiEvidence && `三奇：${sanQiEvidence}`,
    relationItems.length && `关系：${relationItems.length} 项${relationEvidence ? `（${relationEvidence}）` : ''}`,
  ].filter(Boolean).join(' · ');
  const entries = Object.entries(shenShaIds)
    .sort(([left], [right]) => left.localeCompare(right, 'zh-CN'));
  document.querySelector('#shen-sha-catalog').innerHTML = `
    <header><div><span>资料索引</span><strong>神煞原文与取法</strong>${evidence ? `<small class="shen-sha-evidence">${escapeHtml(evidence)}</small>` : ''}</div><small>${matched.size} 项命中</small></header>
    <div class="shen-sha-catalog-list">${entries.map(([name, id]) => `
      <button type="button" class="shen-sha-catalog-item${matched.has(name) ? ' matched' : ''}" data-shen-sha-id="${escapeHtml(id)}">
        <span>${escapeHtml(name)}</span><small>${matched.has(name) ? '本盘命中' : '查看资料'}</small>
      </button>`).join('')}</div>`;
}

function renderLuShenHelp(resource) {
  const dayStem = currentData?.day_master?.stem;
  const luBranch = resource.calculation.fixed_positions[dayStem] || '--';
  const matches = currentShenShaDetails(resource.id);
  const variants = resource.variants[dayStem] || [];
  const matchMarkup = matches.length
    ? matches.map(item => `<li><strong>${escapeHtml(item.pillar)} · ${escapeHtml(item.position)}</strong><span>${escapeHtml(item.ganzhi)} · ${escapeHtml(item.variant)} · ${escapeHtml(item.nature)}</span></li>`).join('')
    : '<li><strong>当前命盘未命中</strong><span>四柱地支没有出现日干对应的禄位。</span></li>';
  const variantRows = variants.map(item => `<tr><th scope="row">${escapeHtml(item.ganzhi)}</th><td>${escapeHtml(item.name)}</td><td>${escapeHtml(item.nature)}</td><td>${escapeHtml(item.meaning)}</td></tr>`).join('');
  const fixedPositions = Object.entries(resource.calculation.fixed_positions)
    .map(([stem, branch]) => `<span><strong>${escapeHtml(stem)}</strong>${escapeHtml(branch)}</span>`).join('');
  return `
    <section class="help-current">
      <h3>当前命盘</h3>
      <p>日干为<strong>${escapeHtml(dayStem || '--')}</strong>，固定禄位在<strong>${escapeHtml(luBranch)}</strong>。</p>
      <ul>${matchMarkup}</ul>
    </section>
    <section>
      <h3>取法</h3>
      <p>${escapeHtml(resource.summary)}</p>
      <blockquote>${escapeHtml(resource.original_text)}</blockquote>
      <div class="lu-position-grid" aria-label="十干固定禄位">${fixedPositions}</div>
      <p class="help-note">${escapeHtml(resource.calculation.basis)}；辰、戌、丑、未四支无十干禄位。</p>
    </section>
    <section>
      <h3>${escapeHtml(dayStem || '')}日主分禄表</h3>
      <div class="help-table-wrap"><table><thead><tr><th>干支</th><th>禄名</th><th>吉凶</th><th>简释</th></tr></thead><tbody>${variantRows}</tbody></table></div>
    </section>
    <section>
      <h3>体系边界</h3>
      <p>${escapeHtml(resource.distinction.bazi_lu_shen)}；${escapeHtml(resource.distinction.ziwei_hua_lu)}。</p>
      <p class="help-note">资料来源：${escapeHtml(resource.source)} · 校准状态：已校准</p>
    </section>`;
}

function renderJinYuHelp(resource) {
  const dayStem = currentData?.day_master?.stem;
  const luBranch = resource.calculation.lu_positions[dayStem] || '--';
  const jinYuBranch = resource.calculation.jin_yu_positions[dayStem] || '--';
  const matches = currentShenShaDetails(resource.id);
  const matchMarkup = matches.length
    ? matches.map(item => `<li><strong>${escapeHtml(item.pillar)} · ${escapeHtml(item.position)}</strong><span>${escapeHtml(item.priority)} · 命中金舆地支 ${escapeHtml(jinYuBranch)}</span></li>`).join('')
    : '<li><strong>当前命盘未命中</strong><span>四柱地支没有出现日干禄前二辰。</span></li>';
  const fixedPositions = Object.entries(resource.calculation.jin_yu_positions)
    .map(([stem, branch]) => `<span><strong>${escapeHtml(stem)}</strong>${escapeHtml(branch)}</span>`).join('');
  return `
    <section class="help-current">
      <h3>当前命盘</h3>
      <p>日干为<strong>${escapeHtml(dayStem || '--')}</strong>，禄位在<strong>${escapeHtml(luBranch)}</strong>，禄前二辰金舆在<strong>${escapeHtml(jinYuBranch)}</strong>。</p>
      <ul>${matchMarkup}</ul>
    </section>
    <section>
      <h3>取法</h3>
      <p>${escapeHtml(resource.summary)}</p>
      <blockquote>${escapeHtml(resource.original_text)}</blockquote>
      <div class="lu-position-grid" aria-label="十干金舆地支">${fixedPositions}</div>
      <p class="help-note">只以日干取禄并顺推二辰；日柱、时柱优先，月柱次之，年柱再次之。</p>
    </section>
    <section>
      <h3>原书断语</h3>
      <ul class="help-quote-list">${resource.interpretations.map(item => `<li><strong>${escapeHtml(item.title)}</strong><span>${escapeHtml(item.text)}</span></li>`).join('')}</ul>
    </section>
    <section>
      <h3>体系边界</h3>
      <p>${escapeHtml(resource.boundaries)}</p>
      <p class="help-note">资料来源：${escapeHtml(resource.source)} · 校准状态：已校准</p>
    </section>`;
}

function renderGenericShenShaHelp(resource) {
  const matches = currentShenShaDetails(resource.id);
  const matchMarkup = matches.length
    ? `<ul>${matches.map(item => `<li><strong>${escapeHtml(item.pillar)}</strong><span>${escapeHtml(item.position && /柱$/.test(item.position) ? item.position : '命盘命中')}</span></li>`).join('')}</ul>`
    : '<p class="help-note">当前命盘未返回该神煞的具体命中位置。</p>';
  const calculation = resource.calculation || {};
  const rules = Object.entries(calculation)
    .filter(([, value]) => typeof value === 'string' || typeof value === 'number')
    .map(([key, value]) => `<li><strong>${escapeHtml(key)}</strong><span>${escapeHtml(value)}</span></li>`).join('');
  const original = resource.original_text || resource.summary || '原文尚未完成结构化转录，请以来源页图为准。';
  const documentText = resource.document_markdown || '';
  const refs = (resource.source_references || []).map(ref => `${ref.work || ''} · 书内页 ${ref.printed_pages || '--'} · PDF 页 ${ref.pdf_pages || '--'}`).join('；');
  return `
    <section class="help-current"><h3>当前命盘</h3>${matchMarkup}</section>
    <section><h3>原文与说明</h3><blockquote>${escapeHtml(original)}</blockquote>${rules ? `<ul class="help-quote-list">${rules}</ul>` : ''}${documentText ? `<details class="source-document"><summary>展开知识文档原文</summary><pre>${escapeHtml(documentText)}</pre></details>` : ''}</section>
    <section><h3>资料来源</h3><p>${escapeHtml(refs || resource.source || '来源待补')}</p><p class="help-note">校准状态：${escapeHtml(resource.calibration_status || 'draft')}</p></section>`;
}

async function openShenShaHelp(id) {
  document.querySelector('#shen-sha-dialog-title').textContent = '加载中';
  document.querySelector('#shen-sha-dialog-source').textContent = '神煞说明';
  shenShaDialogContent.innerHTML = '<p class="dialog-loading">正在读取校准资料…</p>';
  shenShaDialog.showModal();
  try {
    if (!shenShaResourceCache.has(id)) {
      const response = await fetch(`/api/v1/bazi/shen-sha/${encodeURIComponent(id)}`);
      const result = await response.json();
      if (!response.ok || !result.success) throw new Error(result.error?.message || '神煞说明加载失败');
      shenShaResourceCache.set(id, result.data);
    }
    const resource = shenShaResourceCache.get(id);
    document.querySelector('#shen-sha-dialog-title').textContent = resource.name;
    document.querySelector('#shen-sha-dialog-source').textContent = `${resource.system} · ${resource.source}`;
    shenShaDialogContent.innerHTML = id === 'lu_shen' ? renderLuShenHelp(resource)
      : id === 'jin_yu' ? renderJinYuHelp(resource) : renderGenericShenShaHelp(resource);
  } catch (error) {
    document.querySelector('#shen-sha-dialog-title').textContent = '无法读取说明';
    shenShaDialogContent.innerHTML = `<p class="dialog-error">${escapeHtml(error.message)}</p>`;
  }
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
  renderShenShaCatalog(data);
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

document.querySelector('#pillar-board').addEventListener('click', event => {
  const trigger = event.target.closest('[data-shen-sha-id]');
  if (trigger) openShenShaHelp(trigger.dataset.shenShaId);
});

document.querySelector('#shen-sha-dialog-close').addEventListener('click', () => shenShaDialog.close());
shenShaDialog.addEventListener('click', event => {
  if (event.target === shenShaDialog) shenShaDialog.close();
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
