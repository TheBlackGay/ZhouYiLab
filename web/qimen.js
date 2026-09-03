const form = document.querySelector('#qimen-form');
const submitButton = form.querySelector('.primary-action');
const errorBox = document.querySelector('#form-error');
const solarFields = document.querySelector('#solar-fields');
const lunarFields = document.querySelector('#lunar-fields');
const resultContent = document.querySelector('#result-content');
const emptyState = document.querySelector('#empty-state');
const tabs = [...document.querySelectorAll('[role="tab"]')];
const copyButton = document.querySelector('#copy-reading');
const copyStatus = document.querySelector('#copy-status');
const helpDialog = document.querySelector('#help-dialog');
const openHelpButton = document.querySelector('#open-help');
const closeHelpButton = document.querySelector('#close-help');
const {
  palaceKnowledge,
  gateElements,
  isVoidPalace,
  getElementRelation,
  getHourHorse,
  isGatePressured,
  isInstrumentPunishment,
  isWonderInTomb,
  isFiveNotMeet,
  getStemResponse,
  resolveLifeStem,
  detectPlatePatterns,
} = window.QiMenLearning;

const gridPositions = {
  4: [1, 1], 9: [1, 2], 2: [1, 3],
  3: [2, 1], 5: [2, 2], 7: [2, 3],
  8: [3, 1], 1: [3, 2], 6: [3, 3],
};

const questionProfiles = {
  general: {
    label: '综合观察',
    description: '以值符、值使、日干和时干建立全局关系，再根据具体问题追加专项用神。',
    items: ['chief', 'envoy', 'dayStem', 'hourStem'],
    prompt: '先建立值符、值使、日干宫和时干宫之间的主客与生克关系，再指出还需要哪类专项用神。',
  },
  career: {
    label: '事业与求职',
    description: '以开门观察工作与职位，生门观察收益与发展，景门辅助观察文书、考试和成果呈现。',
    items: ['dayStem', 'gate:开', 'gate:生', 'gate:景', 'chief'],
    prompt: '重点比较日干宫、开门宫和生门宫，分析职位机会、个人承接能力、收益空间、阻力与行动时机。',
  },
  relationship: {
    label: '感情与关系',
    description: '以日干代表求测者，结合乙、庚、六合与休门观察关系双方、撮合状态和相处方式。',
    items: ['dayStem', 'stem:乙', 'stem:庚', 'spirit:六合', 'gate:休'],
    prompt: '先确认人物身份和乙庚取法，再比较日干、乙奇、庚、六合及休门所在宫的生克、旺衰与互动。',
  },
  wealth: {
    label: '财运与经营',
    description: '以生门观察收益、资源与增长，以开门观察业务和经营机会，并结合日干判断承接能力。',
    items: ['dayStem', 'gate:生', 'gate:开', 'chief'],
    prompt: '重点比较日干宫、生门宫和开门宫，分析收入来源、资源条件、经营机会、成本压力和兑现路径。',
  },
  travel: {
    label: '出行与方位',
    description: '结合休门、开门、时干及实际目的选择方向；用神落宫方向只是线索，还需检查宫位状态。',
    items: ['hourStem', 'gate:休', 'gate:开', 'envoy'],
    prompt: '重点读取时干、休门和开门的落宫方向，区分出发方、目的方与行动路径，并说明方向判断的限制。',
  },
};

let currentChart = null;
let currentMinute = 0;
let currentLifeProfiles = { subject: null, counterpart: null };

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  })[character]);
}

function localDateTime() {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60000;
  return new Date(now.getTime() - offset).toISOString();
}

function setInitialTime() {
  const local = localDateTime();
  document.querySelector('#solar-date').value = local.slice(0, 10);
  document.querySelector('#qimen-time').value = local.slice(11, 16);
}

function setLoading(loading) {
  submitButton.disabled = loading;
  submitButton.classList.toggle('loading', loading);
}

function pillarText(pillar) {
  return pillar ? `${pillar.stem}${pillar.branch}` : '--';
}

function palaceLocation(palace) {
  if (!palace) return '未定位';
  const knowledge = palaceKnowledge[palace.palace_num];
  return `${palace.palace_name}宫${palace.palace_num}（${knowledge.direction}，${knowledge.element}）`;
}

function findTianStemPalace(data, stem) {
  const palace = data.palaces.find(candidate => candidate.tian_gan === stem);
  if (palace?.palace_num !== 5) return palace;
  return data.palaces.find(candidate => candidate.palace_num === 2);
}

function resolveFocusItem(data, item, lifeProfiles) {
  let label;
  let palace;
  let role = 'focus';
  if (item === 'chief') {
    label = `值符${data.zhi_fu_star}`;
    palace = data.palaces.find(candidate => candidate.palace_name === data.zhi_fu_palace);
  } else if (item === 'envoy') {
    label = `值使${data.zhi_shi_gate}门`;
    palace = data.palaces.find(candidate => candidate.palace_name === data.zhi_shi_palace);
  } else if (item === 'dayStem' || item === 'hourStem') {
    const pillar = item === 'dayStem' ? data.ba_zi?.day : data.ba_zi?.hour;
    label = `${item === 'dayStem' ? '日干' : '时干'}${pillar?.stem || '--'}`;
    palace = findTianStemPalace(data, pillar?.stem);
    if (item === 'dayStem') role = 'subject';
  } else if (item === 'subjectLife' || item === 'counterpartLife') {
    const itemRole = item === 'subjectLife' ? 'subject' : 'counterpart';
    const profile = lifeProfiles[itemRole];
    role = itemRole;
    label = `${itemRole === 'subject' ? '求测者年命' : '相关人物年命'}${profile.pillarText}${profile.hidden ? `（甲遁${profile.lookupStem}）` : ''}`;
    palace = findTianStemPalace(data, profile.lookupStem);
  } else {
    const [type, value] = item.split(':');
    const field = { gate: 'gate', spirit: 'spirit', stem: 'tian_gan' }[type];
    label = type === 'gate' ? `${value}门` : value;
    palace = type === 'stem'
      ? findTianStemPalace(data, value)
      : data.palaces.find(candidate => candidate[field] === value);
  }
  return { label, palace, role, text: `${label}：${palaceLocation(palace)}` };
}

function getQuestionContext(data) {
  const type = document.querySelector('#question-type').value;
  const profile = questionProfiles[type] || questionProfiles.general;
  const subjectLife = currentLifeProfiles.subject;
  const counterpartLife = currentLifeProfiles.counterpart;
  const itemKeys = profile.items.map(item => (
    item === 'dayStem' && subjectLife ? 'subjectLife' : item
  ));
  if (counterpartLife) itemKeys.splice(1, 0, 'counterpartLife');
  return {
    type,
    profile,
    subjectLife,
    counterpartLife,
    detail: document.querySelector('#question-detail').value.trim(),
    focusItems: itemKeys.map(item => resolveFocusItem(data, item, currentLifeProfiles)),
  };
}

function buildClues(data, context) {
  const subject = context.focusItems.find(item => item.role === 'subject');
  if (!subject?.palace) return [];
  const subjectKnowledge = palaceKnowledge[subject.palace.palace_num];
  const seen = new Set();
  return context.focusItems
    .filter(item => item.role !== 'subject' && item.palace)
    .filter(item => {
      const key = `${item.label}:${item.palace.palace_num}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .map(item => {
      const targetKnowledge = palaceKnowledge[item.palace.palace_num];
      const relation = getElementRelation(subjectKnowledge.element, targetKnowledge.element);
      const samePalace = subject.palace.palace_num === item.palace.palace_num;
      const subjectVoid = isVoidPalace(subject.palace.palace_num, data.ba_zi?.xun_kong);
      const targetVoid = isVoidPalace(item.palace.palace_num, data.ba_zi?.xun_kong);
      const corrections = [];
      if (samePalace) corrections.push('双方同宫，相关信息彼此重叠');
      if (subjectVoid) corrections.push('求测者所在宫逢日旬空');
      if (targetVoid && !samePalace) corrections.push(`${item.label}所在宫逢日旬空`);
      if (item.palace.palace_name === data.zhi_fu_palace) corrections.push('与值符同宫');
      if (item.palace.palace_name === data.zhi_shi_palace) corrections.push('与值使同宫');
      return {
        title: `${subject.label} 与 ${item.label}`,
        relation: relation.label,
        fact: `${subject.label}落${palaceLocation(subject.palace)}，宫五行属${subjectKnowledge.element}；${item.label}落${palaceLocation(item.palace)}，宫五行属${targetKnowledge.element}。从求测者一方看为“${relation.label}”。`,
        meaning: relation.meaning,
        corrections,
      };
    });
}

function buildSpecialStates(data) {
  const states = [];
  const horse = getHourHorse(data.ba_zi?.hour?.branch);
  if (horse) {
    const palace = data.palaces.find(candidate => candidate.palace_num === horse.palaceNumber);
    states.push({
      key: 'hour_horse',
      label: '时支驿马',
      palace,
      fact: `时支${data.ba_zi.hour.branch}所属三合局取马在${horse.branch}，对应${palaceLocation(palace)}。`,
      meaning: '提示移动、变化、调动或进展加速；是否有利仍取决于驿马宫及所问事项。',
    });
  }
  data.palaces.filter(palace => isGatePressured(palace.gate, palace.palace_num)).forEach(palace => {
    states.push({
      key: 'gate_pressure',
      label: `${palace.gate}门迫`,
      palace,
      fact: `${palace.gate}门五行属${gateElements[palace.gate]}，落${palaceLocation(palace)}，门五行克宫五行，按本系统口径构成门迫。`,
      meaning: '提示该门代表的行动方式受到所在环境牵制，需要结合用神与旺衰判断影响程度。',
    });
  });
  data.palaces.forEach(sourcePalace => {
    const stem = sourcePalace.tian_gan;
    const palace = sourcePalace.palace_num === 5
      ? data.palaces.find(candidate => candidate.palace_num === 2)
      : sourcePalace;
    const lodgingNote = sourcePalace.palace_num === 5 ? '；该天盘干原列中五，按中五寄坤二判定' : '';
    if (isInstrumentPunishment(stem, palace.palace_num)) {
      states.push({
        key: 'instrument_punishment',
        label: `${stem}击刑`,
        palace,
        fact: `天盘${stem}落${palaceLocation(palace)}${lodgingNote}，按戊震、己坤、庚艮、辛离、壬癸巽的口径构成六仪击刑。`,
        meaning: '提示该天盘干所代表的人事受到约束、别扭或推进阻力；需结合其是否为本次用神判断影响范围。',
      });
    }
    if (isWonderInTomb(stem, palace.palace_num)) {
      states.push({
        key: 'wonder_in_tomb',
        label: `${stem}奇入墓`,
        palace,
        fact: `天盘${stem}落${palaceLocation(palace)}${lodgingNote}，按乙丙入乾、丁入艮的口径构成三奇入墓。`,
        meaning: '提示该奇所代表的信息有收敛、受藏或暂难发挥的倾向；不等同于事项必然无成。',
      });
    }
  });
  const dayStem = data.ba_zi?.day?.stem;
  const hourStem = data.ba_zi?.hour?.stem;
  if (isFiveNotMeet(dayStem, hourStem)) {
    states.push({
      key: 'five_not_meet',
      label: '五不遇时',
      palace: null,
      fact: `日干${dayStem}、时干${hourStem}，时干克日干且阴阳属性相同，构成五不遇时。`,
      meaning: '常提示时机与行动者不够协调、推进较费力；应结合具体问题和用神状态评估，不单独判定结果。',
    });
  }
  data.palaces.filter(palace => palace.palace_num !== 5).forEach(palace => {
    [
      { stem: palace.tian_gan, lodged: false },
      { stem: palace.lodged_tian_gan, lodged: true },
    ].filter(item => item.stem).forEach(item => {
      const response = getStemResponse(item.stem, palace.di_gan);
      if (!response) return;
      states.push({
        key: 'stem_response',
        label: response.name,
        palace,
        fact: `${item.lodged ? '天禽寄干' : '天盘'}${item.stem}加地盘${palace.di_gan}，同在${palaceLocation(palace)}，构成“${response.name}”。`,
        meaning: response.meaning,
      });
    });
  });
  const patterns = detectPlatePatterns(data.palaces);
  const patternDefinitions = [
    ['starFuyin', '星伏吟', '外围八宫九星均回到固定本位。', '常提示重复、迟缓、内守或状态稳定。'],
    ['gateFuyin', '门伏吟', '八门均回到固定本位，中五仍无门。', '常提示行动路径重复、推进偏慢或适合守成。'],
    ['starFanyin', '星反吟', '外围八宫九星均落到各自本位的对宫。', '常提示外部状态变化、反复、对冲或迁移。'],
    ['gateFanyin', '门反吟', '八门均落到各自本位的对宫。', '常提示行动路径变化较大、往返或难以一次定局。'],
  ];
  patternDefinitions.forEach(([key, label, fact, meaning]) => {
    if (patterns[key]) states.push({ key, label, palace: null, fact, meaning });
  });
  return states;
}

function buildReadingText(data, minute, context) {
  const pillars = data.ba_zi
    ? ['year', 'month', 'day', 'hour'].map(key => pillarText(data.ba_zi[key])).join(' ')
    : '--';
  const palaceLines = [...data.palaces]
    .sort((left, right) => left.palace_num - right.palace_num)
    .map(palace => {
      const gate = palace.gate ? `${palace.gate}门` : '无门';
      const spirit = palace.spirit || '无八神';
      const lodged = palace.lodged_star
        ? `，${palace.lodged_star}寄此宫（寄干${palace.lodged_tian_gan}）`
        : '';
      const knowledge = palaceKnowledge[palace.palace_num];
      const branches = knowledge.branches.join('、') || '中宫';
      const voidText = isVoidPalace(palace.palace_num, data.ba_zi?.xun_kong) ? '，日旬空' : '';
      return `${palace.palace_name}宫${palace.palace_num}（${knowledge.element}，${branches}）：${spirit}，${palace.star}${lodged}，${gate}，天盘${palace.tian_gan}，地盘${palace.di_gan}${voidText}`;
    });
  const questionDetail = context.detail || '未填写，请先向用户确认具体问题、人物身份和时间范围';
  const clues = buildClues(data, context);
  const specialStates = buildSpecialStates(data);
  const clueLines = clues.length
    ? clues.map(clue => `- ${clue.title}：${clue.fact} 传统象意：${clue.meaning}${clue.corrections.length ? ` 修正条件：${clue.corrections.join('；')}。` : ''}`).join('\n')
    : '- 暂无可计算关系；请检查求测者用神是否已定位，或补充所问人物与事项。';
  const specialStateLines = specialStates.length
    ? specialStates.map(state => `- ${state.label}：${state.fact} 传统象意：${state.meaning}`).join('\n')
    : '- 当前未命中已启用的特殊状态。';

  return `奇门遁甲排盘资料（时家转盘·拆补法）

【起局信息】
公历：${data.solar_date.year}年${data.solar_date.month}月${data.solar_date.day}日 ${String(data.solar_date.hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}
农历：${data.lunar_date.year}年${data.lunar_date.month}月${data.lunar_date.day}日${data.lunar_date.is_leap_month ? '（闰月）' : ''}
四柱：${pillars}
节气：${data.solar_term}
局式：${data.dun}，${data.yuan}，${data.ju}
值符：${data.zhi_fu_star}，落${data.zhi_fu_palace}宫
值使：${data.zhi_shi_gate}门，落${data.zhi_shi_palace}宫
旬空：${data.ba_zi?.xun_kong || '--'}

【所问事项】
类型：${context.profile.label}
具体问题：${questionDetail}

【本次取用重点】
${context.focusItems.map(item => item.text).join('\n')}

【宫位关系线索】
${clueLines}

【特殊状态】
${specialStateLines}

【九宫明细】
${palaceLines.join('\n')}

【通用解读参考】
1. 先以值符观察全局主导力量、核心人物或主要矛盾，以值使观察行动路径、执行方式与事情落点。
2. 再结合所问事项，分析用神所在宫的九星、八门、八神、天盘干与地盘干；同一符号在不同问题中可能代表不同含义。
3. 宫位之间可从五行生克、旺衰、主客关系和内外盘关系观察支持、阻力、节奏与变化方向。
4. 空亡、入墓、击刑、门迫等信息适合作为修正条件，不宜脱离全盘单独下结论。
5. 本资料只提供盘面结构与传统象意线索，不直接等同于确定的吉凶或现实结果。

【请 AI 分析】
请基于以上盘面进行结构化解读。${context.profile.prompt}先复核排盘信息，再区分“盘面事实”“象意推断”和“现实建议”。请从整体局势、主客关系、主要机会、潜在阻力、时间节奏和可执行建议几个方面分析；如缺少所问事项或人物背景，请先指出需要补充的信息，不要编造具体事实或作绝对化断言。`;
}

function activateTab(selectedTab) {
  tabs.forEach(tab => {
    const selected = tab === selectedTab;
    tab.setAttribute('aria-selected', String(selected));
    tab.tabIndex = selected ? 0 : -1;
    document.querySelector(`#${tab.getAttribute('aria-controls')}`).hidden = !selected;
  });
  selectedTab.focus();
}

function render(data, minute = 0, shouldScroll = true) {
  currentChart = data;
  currentMinute = minute;
  const context = getQuestionContext(data);
  const focusPalaces = new Set(context.focusItems.filter(item => item.palace).map(item => item.palace.palace_num));
  const specialStates = buildSpecialStates(data);
  const horsePalaces = new Set(specialStates.filter(state => state.key === 'hour_horse').map(state => state.palace.palace_num));
  const pressuredPalaces = new Set(specialStates.filter(state => state.key === 'gate_pressure').map(state => state.palace.palace_num));
  const punishedPalaces = new Set(specialStates.filter(state => state.key === 'instrument_punishment').map(state => state.palace.palace_num));
  const tombPalaces = new Set(specialStates.filter(state => state.key === 'wonder_in_tomb').map(state => state.palace.palace_num));
  const responsePalaces = new Set(specialStates.filter(state => state.key === 'stem_response').map(state => state.palace.palace_num));
  document.querySelector('#summary-title').textContent = `${data.dun} · ${data.yuan} · ${data.ju}`;
  document.querySelector('#summary-date').textContent = `${data.solar_date.year}年${data.solar_date.month}月${data.solar_date.day}日 ${String(data.solar_date.hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
  document.querySelector('#metric-term').textContent = data.solar_term;
  document.querySelector('#metric-chief').textContent = `${data.zhi_fu_star} · ${data.zhi_fu_palace}宫`;
  document.querySelector('#metric-gate').textContent = `${data.zhi_shi_gate}门 · ${data.zhi_shi_palace}宫`;
  document.querySelector('#metric-void').textContent = data.ba_zi?.xun_kong || '--';
  document.querySelector('#board-pillars').textContent = data.ba_zi
    ? ['year', 'month', 'day', 'hour'].map(key => pillarText(data.ba_zi[key])).join('　')
    : '--';
  document.querySelector('#focus-title').textContent = context.profile.label;
  document.querySelector('#focus-description').textContent = context.profile.description;
  document.querySelector('#focus-symbols').innerHTML = context.focusItems
    .map(item => `<span>${escapeHtml(item.text)}</span>`).join('');
  const clues = buildClues(data, context);
  document.querySelector('#clues-title').textContent = context.profile.label;
  document.querySelector('#pattern-list').innerHTML = specialStates.map(state => `
    <article class="pattern-item">
      <header><strong>${escapeHtml(state.label)}</strong><span>${escapeHtml(state.palace ? palaceLocation(state.palace) : '全盘')}</span></header>
      <p>${escapeHtml(state.fact)}</p>
      <small>${escapeHtml(state.meaning)}</small>
    </article>`).join('');
  document.querySelector('#clue-list').innerHTML = clues.length
    ? clues.map(clue => `
      <article class="clue-item">
        <header><strong>${escapeHtml(clue.title)}</strong><span>${escapeHtml(clue.relation)}</span></header>
        <dl>
          <div><dt>盘面事实</dt><dd>${escapeHtml(clue.fact)}</dd></div>
          <div><dt>传统象意</dt><dd>${escapeHtml(clue.meaning)}</dd></div>
          <div><dt>修正条件</dt><dd>${escapeHtml(clue.corrections.join('；') || '当前只计算五行关系，仍需结合旺衰及其他状态。')}</dd></div>
        </dl>
      </article>`).join('')
    : '<p class="clue-empty">当前没有可比较的宫位关系，请补充所问人物与事项。</p>';
  document.querySelector('#reading-text').textContent = buildReadingText(data, minute, context);
  copyStatus.textContent = '';

  const board = document.querySelector('#qimen-board');
  board.innerHTML = '';
  data.palaces.forEach(palace => {
    const [row, column] = gridPositions[palace.palace_num];
    const isChief = palace.palace_name === data.zhi_fu_palace;
    const isChiefGate = Boolean(palace.gate) && palace.gate === data.zhi_shi_gate
      && palace.palace_name === data.zhi_shi_palace;
    const spirit = palace.spirit || '中宫';
    const gate = palace.gate ? `${escapeHtml(palace.gate)}门` : '无门';
    const lodged = palace.lodged_star
      ? `<small class="lodged">寄${escapeHtml(palace.lodged_star)} · ${escapeHtml(palace.lodged_tian_gan)}</small>`
      : '';
    const node = document.createElement('article');
    node.className = 'qimen-palace';
    if (isChief) node.classList.add('chief-palace');
    const isFocus = focusPalaces.has(palace.palace_num);
    const isVoid = isVoidPalace(palace.palace_num, data.ba_zi?.xun_kong);
    if (isFocus) node.classList.add('focus-palace');
    if (isVoid) node.classList.add('void-palace');
    const isHorse = horsePalaces.has(palace.palace_num);
    const isPressured = pressuredPalaces.has(palace.palace_num);
    const isPunished = punishedPalaces.has(palace.palace_num);
    const isTomb = tombPalaces.has(palace.palace_num);
    const hasStemResponse = responsePalaces.has(palace.palace_num);
    if (isHorse) node.classList.add('horse-palace');
    if (isPressured) node.classList.add('pressured-palace');
    if (isPunished) node.classList.add('punished-palace');
    if (isTomb) node.classList.add('tomb-palace');
    if (hasStemResponse) node.classList.add('response-palace');
    const knowledge = palaceKnowledge[palace.palace_num];
    const branches = knowledge.branches.join('、') || '中宫';
    node.style.gridArea = `${row} / ${column}`;
    node.innerHTML = `
      <header><span>${escapeHtml(palace.palace_name)}宫<small>${knowledge.element} · ${branches}</small></span><span class="palace-flags">${isFocus ? '<em class="flag-focus" data-short="用">用神</em>' : ''}${isVoid ? '<em class="flag-void" data-short="空">日旬空</em>' : ''}${isHorse ? '<em class="flag-horse" data-short="马">驿马</em>' : ''}${isPressured ? '<em class="flag-pressure" data-short="迫">门迫</em>' : ''}${isPunished ? '<em class="flag-punishment" data-short="刑">击刑</em>' : ''}${isTomb ? '<em class="flag-tomb" data-short="墓">入墓</em>' : ''}${hasStemResponse ? '<em class="flag-response" data-short="应">克应</em>' : ''}<b>${palace.palace_num}</b></span></header>
      <div class="palace-core">
        <span class="spirit">${escapeHtml(spirit)}${isChief ? '<small>直符宫</small>' : ''}</span>
        <strong>${escapeHtml(palace.star)}${lodged}</strong>
        <span class="gate${isChiefGate ? ' chief-gate' : ''}">${gate}${isChiefGate ? '<small>直使</small>' : ''}</span>
      </div>
      <footer><span><small>天盘</small>${escapeHtml(palace.tian_gan)}</span><span><small>地盘</small>${escapeHtml(palace.di_gan)}</span></footer>`;
    board.appendChild(node);
  });

  emptyState.hidden = true;
  resultContent.hidden = false;
  if (shouldScroll && window.innerWidth <= 900) resultContent.scrollIntoView({ block: 'start' });
}

form.addEventListener('change', event => {
  if (event.target.name === 'calendar') {
    const lunar = event.target.value === 'lunar';
    solarFields.hidden = lunar;
    lunarFields.hidden = !lunar;
    document.querySelector('#solar-date').required = !lunar;
  }
  if (event.target.id === 'question-type' && currentChart) {
    render(currentChart, currentMinute, false);
  }
  if (['subject-birth-date', 'counterpart-birth-date'].includes(event.target.id) && currentChart) {
    form.requestSubmit();
  }
});

document.querySelector('#question-detail').addEventListener('input', () => {
  if (currentChart) render(currentChart, currentMinute, false);
});

tabs.forEach((tab, index) => {
  tab.addEventListener('click', () => activateTab(tab));
  tab.addEventListener('keydown', event => {
    if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
    event.preventDefault();
    const direction = event.key === 'ArrowRight' ? 1 : -1;
    activateTab(tabs[(index + direction + tabs.length) % tabs.length]);
  });
});

copyButton.addEventListener('click', async () => {
  const text = document.querySelector('#reading-text').textContent;
  try {
    await navigator.clipboard.writeText(text);
    copyButton.textContent = '已复制';
    copyStatus.textContent = '解读素材已复制到剪贴板';
    window.setTimeout(() => { copyButton.textContent = '复制内容'; }, 1800);
  } catch (error) {
    copyStatus.textContent = '复制失败，请选中文本后手动复制';
  }
});

openHelpButton.addEventListener('click', () => helpDialog.showModal());
closeHelpButton.addEventListener('click', () => helpDialog.close());
helpDialog.addEventListener('click', event => {
  if (event.target === helpDialog) helpDialog.close();
});

async function requestQiMenChart(calendar, date) {
  const response = await fetch('/api/v1/qimen/charts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ calendar, date }),
  });
  const result = await response.json();
  if (!response.ok || !result.success) throw new Error(result.error?.message || '奇门排盘失败');
  return result.data;
}

async function loadLifeProfile(dateText) {
  if (!dateText) return null;
  const [year, month, day] = dateText.split('-').map(Number);
  const chart = await requestQiMenChart('solar', { year, month, day, hour: 12, minute: 0 });
  const pillar = chart.ba_zi?.year;
  const resolved = resolveLifeStem(pillar?.stem, pillar?.branch);
  if (!pillar || !resolved) throw new Error(`无法换算出生日期 ${dateText} 的年命`);
  return {
    birthDate: dateText,
    pillarText: pillarText(pillar),
    branch: pillar.branch,
    ...resolved,
  };
}

function updateLifeStatus() {
  const entries = [
    ['subject', '#subject-life-status', '不填写则使用日干'],
    ['counterpart', '#counterpart-life-status', '不填写则不加入相关人物年命'],
  ];
  entries.forEach(([key, selector, emptyText]) => {
    const profile = currentLifeProfiles[key];
    document.querySelector(selector).textContent = profile
      ? `${profile.pillarText}${profile.hidden ? `，甲遁${profile.lookupStem}` : `，按天盘${profile.lookupStem}定位`}`
      : emptyText;
  });
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  errorBox.hidden = true;
  setLoading(true);
  try {
    const calendar = form.elements.calendar.value;
    const [hour, minute] = document.querySelector('#qimen-time').value.split(':').map(Number);
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
    const subjectBirthDate = document.querySelector('#subject-birth-date').value;
    const counterpartBirthDate = document.querySelector('#counterpart-birth-date').value;
    const [chart, subjectLife, counterpartLife] = await Promise.all([
      requestQiMenChart(calendar, date),
      loadLifeProfile(subjectBirthDate),
      loadLifeProfile(counterpartBirthDate),
    ]);
    currentLifeProfiles = { subject: subjectLife, counterpart: counterpartLife };
    updateLifeStatus();
    render(chart, minute);
  } catch (error) {
    errorBox.textContent = error.message;
    errorBox.hidden = false;
  } finally {
    setLoading(false);
  }
});

setInitialTime();
form.requestSubmit();
