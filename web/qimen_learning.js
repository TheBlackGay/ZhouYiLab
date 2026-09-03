(function initializeQiMenLearning(root) {
  const palaceKnowledge = Object.freeze({
    1: { element: '水', direction: '北', branches: ['子'] },
    2: { element: '土', direction: '西南', branches: ['未', '申'] },
    3: { element: '木', direction: '东', branches: ['卯'] },
    4: { element: '木', direction: '东南', branches: ['辰', '巳'] },
    5: { element: '土', direction: '中', branches: [] },
    6: { element: '金', direction: '西北', branches: ['戌', '亥'] },
    7: { element: '金', direction: '西', branches: ['酉'] },
    8: { element: '土', direction: '东北', branches: ['丑', '寅'] },
    9: { element: '火', direction: '南', branches: ['午'] },
  });

  const generates = Object.freeze({ 木: '火', 火: '土', 土: '金', 金: '水', 水: '木' });
  const controls = Object.freeze({ 木: '土', 土: '水', 水: '火', 火: '金', 金: '木' });
  const gateElements = Object.freeze({
    休: '水', 生: '土', 伤: '木', 杜: '木',
    景: '火', 死: '土', 惊: '金', 开: '金',
  });
  const originalGates = Object.freeze({
    1: '休', 2: '死', 3: '伤', 4: '杜',
    6: '开', 7: '惊', 8: '生', 9: '景',
  });
  const originalStars = Object.freeze({
    1: '天蓬', 2: '天芮', 3: '天冲', 4: '天辅',
    6: '天心', 7: '天柱', 8: '天任', 9: '天英',
  });
  const oppositePalaces = Object.freeze({
    1: 9, 9: 1, 2: 8, 8: 2, 3: 7, 7: 3, 4: 6, 6: 4,
  });
  const horseByHourBranch = Object.freeze({
    申: { branch: '寅', palaceNumber: 8 },
    子: { branch: '寅', palaceNumber: 8 },
    辰: { branch: '寅', palaceNumber: 8 },
    寅: { branch: '申', palaceNumber: 2 },
    午: { branch: '申', palaceNumber: 2 },
    戌: { branch: '申', palaceNumber: 2 },
    巳: { branch: '亥', palaceNumber: 6 },
    酉: { branch: '亥', palaceNumber: 6 },
    丑: { branch: '亥', palaceNumber: 6 },
    亥: { branch: '巳', palaceNumber: 4 },
    卯: { branch: '巳', palaceNumber: 4 },
    未: { branch: '巳', palaceNumber: 4 },
  });
  const instrumentPunishmentPalaces = Object.freeze({
    戊: 3, 己: 2, 庚: 8, 辛: 9, 壬: 4, 癸: 4,
  });
  const wonderTombPalaces = Object.freeze({ 乙: 6, 丙: 6, 丁: 8 });
  const hiddenJiaStems = Object.freeze({ 子: '戊', 戌: '己', 申: '庚', 午: '辛', 辰: '壬', 寅: '癸' });
  const stems = Object.freeze(['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']);
  const stemResponses = Object.freeze({
    戊丙: Object.freeze({
      name: '青龙返首',
      meaning: '传统上偏向回转、助力或局面重新获得推进条件；仍需检查用神、门星及宫位旺衰。',
    }),
    丙戊: Object.freeze({
      name: '飞鸟跌穴',
      meaning: '传统上偏向找到落点、获得配合或行动较易落实；不代表所有所问事项都必然顺利。',
    }),
    乙辛: Object.freeze({
      name: '青龙逃走',
      meaning: '传统上提示退避、流失、关系疏离或计划难以停驻，影响大小取决于该宫是否为用神。',
    }),
    辛乙: Object.freeze({
      name: '白虎猖狂',
      meaning: '传统上提示冲突、强硬、压力或损伤风险，宜结合问题背景识别具体作用对象。',
    }),
    丁癸: Object.freeze({
      name: '朱雀投江',
      meaning: '传统上提示表达、消息或文书受到遮蔽、误解或延迟，需要加强核实与留痕。',
    }),
    癸丁: Object.freeze({
      name: '腾蛇夭矫',
      meaning: '传统上提示缠绕、反复、疑虑或信息失真，需要分清事实、猜测与情绪。',
    }),
    庚丙: Object.freeze({
      name: '太白入荧',
      meaning: '传统上提示对抗力量进入显化阶段，矛盾容易被看见，应关注压力来源与边界。',
    }),
    丙庚: Object.freeze({
      name: '荧入太白',
      meaning: '传统上提示主动碰撞、争执升级或局势快速变化，行动前宜评估代价与替代路径。',
    }),
  });

  function isVoidPalace(palaceNumber, xunKong) {
    const voidBranches = new Set([...(xunKong || '')]);
    return palaceKnowledge[palaceNumber].branches.some(branch => voidBranches.has(branch));
  }

  function getElementRelation(subjectElement, targetElement) {
    if (!generates[subjectElement] || !generates[targetElement]) {
      throw new Error('五行必须是木、火、土、金、水之一');
    }
    if (subjectElement === targetElement) {
      return { key: 'same', label: '比和', meaning: '双方同气，关系较直接，强弱仍取决于各自宫位状态。' };
    }
    if (generates[subjectElement] === targetElement) {
      return { key: 'subject_generates', label: '我生', meaning: '求测者一方对事项投入、支持或有所消耗。' };
    }
    if (generates[targetElement] === subjectElement) {
      return { key: 'target_generates', label: '生我', meaning: '事项一方对求测者形成支持、资源或推动。' };
    }
    if (controls[subjectElement] === targetElement) {
      return { key: 'subject_controls', label: '我克', meaning: '求测者一方主动推动、管理或控制事项，同时需要付出力量。' };
    }
    return { key: 'target_controls', label: '克我', meaning: '事项一方对求测者形成约束、压力或较高要求。' };
  }

  function getHourHorse(hourBranch) {
    return horseByHourBranch[hourBranch] || null;
  }

  function isGatePressured(gate, palaceNumber) {
    const gateElement = gateElements[gate];
    const palaceElement = palaceKnowledge[palaceNumber]?.element;
    return Boolean(gateElement && palaceElement && controls[gateElement] === palaceElement);
  }

  function isInstrumentPunishment(stem, palaceNumber) {
    return instrumentPunishmentPalaces[stem] === palaceNumber;
  }

  function isWonderInTomb(stem, palaceNumber) {
    return wonderTombPalaces[stem] === palaceNumber;
  }

  function isFiveNotMeet(dayStem, hourStem) {
    const dayIndex = stems.indexOf(dayStem);
    const hourIndex = stems.indexOf(hourStem);
    return dayIndex >= 0 && hourIndex >= 0
      && (hourIndex - dayIndex + stems.length) % stems.length === 6;
  }

  function getStemResponse(tianStem, earthStem) {
    return stemResponses[`${tianStem}${earthStem}`] || null;
  }

  function resolveLifeStem(stem, branch) {
    if (!stem) return null;
    if (stem !== '甲') return { stem, lookupStem: stem, hidden: false };
    const lookupStem = hiddenJiaStems[branch];
    return lookupStem ? { stem, lookupStem, hidden: true } : null;
  }

  function arrangementMatches(palaces, field, origins, transform) {
    return Object.entries(origins).every(([origin, value]) => {
      const expectedPalace = transform(Number(origin));
      return palaces.some(palace => palace.palace_num === expectedPalace && palace[field] === value);
    });
  }

  function detectPlatePatterns(palaces) {
    return {
      gateFuyin: arrangementMatches(palaces, 'gate', originalGates, palace => palace),
      gateFanyin: arrangementMatches(palaces, 'gate', originalGates, palace => oppositePalaces[palace]),
      starFuyin: arrangementMatches(palaces, 'star', originalStars, palace => palace),
      starFanyin: arrangementMatches(palaces, 'star', originalStars, palace => oppositePalaces[palace]),
    };
  }

  const api = Object.freeze({
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
  });
  root.QiMenLearning = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
}(typeof globalThis !== 'undefined' ? globalThis : window));
