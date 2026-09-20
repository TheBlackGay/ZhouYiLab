/* 大六壬 2.1.0 天地盘可视化（自足组件，风格同 profile-charts.js：样式首用注入）。
 * 消费 da_liu_ren_web_cli 既有字段，零新增算法、零口径发明：
 *   外圈地盘（固定十二位 + 旬空标记）/ 内圈天盘（上神、神将、遁干）
 *   / 三传徽章（初·中·末，按上神地支落位，天盘为十二支排列故唯一）
 *   / 中心：日辰昼夜、月将、贵人、课体、三传六亲。
 * 四课有意不上盘：引擎 si_ke 仅有字符对，映射宫位需新口径（不发明）。
 * 布局：盖天说方位，午（南）居正上方，顺时针 午未申酉戌亥子丑寅卯辰巳。 */
window.DlrPlate = (function () {
  'use strict';

  // 地盘固定环：自正上方起顺时针排列（南上）
  const EARTHWHEEL_CLOCKWISE = ['午', '未', '申', '酉', '戌', '亥', '子', '丑', '寅', '卯', '辰', '巳'];
  const BRANCH_ELEMENT = { 子: '水', 丑: '土', 寅: '木', 卯: '木', 辰: '土', 巳: '火',
    午: '火', 未: '土', 申: '金', 酉: '金', 戌: '土', 亥: '水' };
  const ELEMENT_FILL = { 木: '#3d7a4f', 火: '#b3402a', 土: '#6f7d54', 金: '#a67b2e', 水: '#4f5b8a' };
  const CHUAN_STYLE = { 初: '#b3402a', 中: '#4f5b8a', 末: '#25634d' };
  const esc = value => String(value ?? '').replace(/[&<>'"]/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c]));

  let stylesInjected = false;
  function injectStyles() {
    if (stylesInjected || document.getElementById('dlr-plate-css')) { stylesInjected = true; return; }
    const style = document.createElement('style');
    style.id = 'dlr-plate-css';
    style.textContent = `
.dlr-plate-wrap { max-width:520px; margin:0 auto 10px; }
.dlr-plate-wrap svg { width:100%; height:auto; display:block; }
.dlr-plate text { font-family:Georgia,"Noto Serif SC",serif; fill:var(--ink,#1d2421); }
.dlr-plate-legend { display:flex; gap:14px; flex-wrap:wrap; justify-content:center;
  margin-top:8px; font-size:12px; color:var(--muted,#68716c); }
.dlr-plate-legend i { display:inline-block; width:10px; height:10px; border-radius:3px; margin-right:4px; }
.dlr-plate-note { margin:6px auto 0; max-width:520px; text-align:center; font-size:12.5px; color:var(--muted,#68716c); }`;
    document.head.append(style);
    stylesInjected = true;
  }

  const RAD = Math.PI / 180;
  // 屏幕极坐标：θ 自正上方起、顺时针
  const px = (cx, cy, r, deg) => [cx + r * Math.sin(deg * RAD), cy - r * Math.cos(deg * RAD)];

  function annulus(cx, cy, rIn, rOut, a0, a1) {
    const large = a1 - a0 > 180 ? 1 : 0;
    const [x0, y0] = px(cx, cy, rOut, a0);
    const [x1, y1] = px(cx, cy, rOut, a1);
    const [x2, y2] = px(cx, cy, rIn, a1);
    const [x3, y3] = px(cx, cy, rIn, a0);
    return `M${x0.toFixed(1)} ${y0.toFixed(1)}A${rOut} ${rOut} 0 ${large} 1 ${x1.toFixed(1)} ${y1.toFixed(1)}L${x2.toFixed(1)} ${y2.toFixed(1)}A${rIn} ${rIn} 0 ${large} 0 ${x3.toFixed(1)} ${y3.toFixed(1)}Z`;
  }

  function collect(data) {
    const pan = data?.tian_di_pan;
    if (!Array.isArray(pan) || pan.length !== 12) throw new Error('缺少完整天盘 tian_di_pan');
    const byEarth = new Map(pan.map(slot => [slot.position, slot]));
    if (byEarth.size !== 12) throw new Error('地盘宫位重复，盘面异常');
    for (const b of EARTHWHEEL_CLOCKWISE) if (!byEarth.has(b)) throw new Error(`天盘缺地盘位 ${b}`);
    return byEarth;
  }

  function render(container, data) {
    injectStyles();
    let byEarth;
    try { byEarth = collect(data); } catch (error) { container.textContent = ''; return; }

    const cx = 240, cy = 240;
    const R_E_OUT = 230, R_E_IN = 196, R_H_OUT = 194, R_H_IN = 132;
    const voids = new Set([data.ba_zi?.xun_kong_1, data.ba_zi?.xun_kong_2].filter(Boolean));
    // 三传徽章：按上神地支在天盘找落位（天盘是十二支的一个排列，唯一）
    const chuanOf = {};
    for (const d of data.san_chuan?.details ?? []) {
      const tag = { chu_chuan: '初', zhong_chuan: '中', mo_chuan: '末' }[d.stage];
      if (tag) chuanOf[d.branch] = { tag, liuQin: d.liu_qin };
    }
    let cells = '';
    EARTHWHEEL_CLOCKWISE.forEach((earthBranch, i) => {
      const angle = i * 30, mid = angle; // 扇区中心角（a0=-15..+15）
      const slot = byEarth.get(earthBranch) || {};
      const heaven = slot.tian_pan ?? '';
      // 地盘环
      const [ex, ey] = px(cx, cy, (R_E_OUT + R_E_IN) / 2, mid);
      cells += `<path d="${annulus(cx, cy, R_E_IN, R_E_OUT, angle - 15, angle + 15)}" fill="#f3ede0" stroke="#d8dcd8"/>`;
      cells += `<text x="${ex.toFixed(1)}" y="${(ey + 5).toFixed(1)}" font-size="16" text-anchor="middle">${esc(earthBranch)}</text>`;
      if (voids.has(earthBranch)) {
        const [vx, vy] = px(cx, cy, R_E_OUT - 12, mid + 9);
        cells += `<text x="${vx.toFixed(1)}" y="${vy.toFixed(1)}" font-size="10" fill="#a45b32" text-anchor="middle">旬</text>`;
      }
      // 天盘环（底色=上神五行淡彩）
      const fill = ELEMENT_FILL[BRANCH_ELEMENT[heaven]] ?? '#888';
      cells += `<path d="${annulus(cx, cy, R_H_IN, R_H_OUT, angle - 15, angle + 15)}" fill="${fill}" fill-opacity="0.13" stroke="#d8dcd8"/>`;
      const [hy, hxOff] = [px(cx, cy, (R_H_OUT + R_H_IN) / 2 + 14, mid), 0];
      cells += `<text x="${hy[0].toFixed(1)}" y="${hy[1].toFixed(1)}" font-size="19" font-weight="700" text-anchor="middle">${esc(heaven)}</text>`;
      const [sy] = [px(cx, cy, (R_H_OUT + R_H_IN) / 2 - 8, mid)];
      cells += `<text x="${sy[0].toFixed(1)}" y="${sy[1].toFixed(1)}" font-size="10" fill="#68716c" text-anchor="middle">${esc(slot.shen_jiang || '—')}</text>`;
      const [dy] = [px(cx, cy, (R_H_OUT + R_H_IN) / 2 - 24, mid)];
      cells += `<text x="${dy[0].toFixed(1)}" y="${dy[1].toFixed(1)}" font-size="10.5" fill="#68716c" text-anchor="middle">${slot.dun_gan ? esc('干' + slot.dun_gan) : '空'}</text>`;
      const chuan = chuanOf[heaven];
      if (chuan) {
        const [bx, by] = px(cx, cy, R_H_OUT - 12, mid - 11);
        cells += `<circle cx="${bx.toFixed(1)}" cy="${by.toFixed(1)}" r="8.5" fill="${CHUAN_STYLE[chuan.tag]}"/>`
          + `<text x="${bx.toFixed(1)}" y="${(by + 3.5).toFixed(1)}" font-size="10.5" fill="#fff" text-anchor="middle">${chuan.tag}</text>`;
      }
      cells += `<title>地盘${esc(earthBranch)}位 · 天盘上神${esc(heaven)} · ${esc(slot.shen_jiang || '无将')} · ${slot.dun_gan ? '遁干' + esc(slot.dun_gan) : '旬空无干'}${chuan ? ` · ${chuan.tag}传（${esc(chuan.liuQin || '')}）` : ''}</title>`;
    });

    // 中心：日辰/昼夜/月将/贵人/课体 + 三传直读
    const day = data.ba_zi?.day;
    const keShi = (data.san_chuan?.ke_shi ?? []).join('·');
    const chuanLine = ['chu_chuan', 'zhong_chuan', 'mo_chuan'].map((k, i) => {
      const branch = data.san_chuan?.[k];
      const d = (data.san_chuan?.details ?? []).find(x => x.stage === k);
      return ['初', '中', '末'][i] + (branch ? `${esc(branch)}${d?.liu_qin ? '·' + esc(d.liu_qin) : ''}` : '—');
    }).join('  ');
    const center = `
      <circle cx="${cx}" cy="${cy}" r="${R_H_IN - 8}" fill="#fffdf6" stroke="#d8dcd8"/>
      <text x="${cx}" y="${cy - 44}" font-size="17" font-weight="700" text-anchor="middle">${esc((day?.stem ?? '') + (day?.branch ?? ''))}日 · ${data.is_day ? '昼' : '夜'}占</text>
      <text x="${cx}" y="${cy - 20}" font-size="13" text-anchor="middle">月将 ${esc(data.yue_jiang ?? '—')} · 贵人 ${esc(data.gui_ren ?? '—')}</text>
      <text x="${cx}" y="${cy + 6}" font-size="13" fill="#a45b32" text-anchor="middle">${esc(keShi || '—')}</text>
      <text x="${cx}" y="${cy + 34}" font-size="13.5" text-anchor="middle">${chuanLine}</text>
      <text x="${cx}" y="${cy + 58}" font-size="10.5" fill="#68716c" text-anchor="middle">外圈地盘 · 内圈天盘</text>`;

    container.innerHTML = `<div class="dlr-plate-wrap"><svg class="dlr-plate" viewBox="0 0 480 480" role="img" aria-label="六壬天地盘">${cells}${center}</svg>
      <div class="dlr-plate-legend">
        <span><i style="background:#f3ede0;border:1px solid #d8dcd8"></i>地盘（固定十二位）</span>
        <span><i style="background:${CHUAN_STYLE.初}"></i>初传</span>
        <span><i style="background:${CHUAN_STYLE.中}"></i>中传</span>
        <span><i style="background:${CHUAN_STYLE.末}"></i>末传</span>
        <span>旬=旬空位（无遁干）</span>
      </div>
      <p class="dlr-plate-note">天盘随月将加占时旋转；上神淡彩为该支五行归类（结构性着色，不表吉凶）。悬停/点按宫位可查看逐位信息。</p></div>`;
  }

  return { render, EARTHWHEEL_CLOCKWISE, BRANCH_ELEMENT };
})();
