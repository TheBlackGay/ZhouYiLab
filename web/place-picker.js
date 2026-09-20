/* 出生地点选择组件（G1b，中立、不绑定命理语义）。
 *
 * 见 docs/product/archive/西洋占星出生地点交互优化方案.md §4/§5/§8：
 * - 主路径：地名搜索（combobox + listbox，键盘可完成全流程）；
 * - 选中后：地点卡（坐标 / 时区 / 当时偏移 / 夏令时证据行 / 软校验警告）；
 * - 兜底：微调面板（坐标 + 半球下拉 + UTC 时区下拉 + 恢复自动推导）；
 * - 状态机：空 empty → 自动 auto ⇄ 已校正 manual；手动坐标 unresolved；
 * - 输出控件沿用各页旧 id（type=hidden，无 required），本组件只负责写入值；
 * - 时区推导全部来自服务端 /api/v1/geo/*（本地 tzdata，不联网、不猜）。
 *
 * 页面适配（示例见 astro.html）：
 *   window.PLACE_PICKER_CONFIG = {
 *     mount, dateInput, timeInput, houseInput,
 *     mode: 'geo+offset',
 *     outputs: { offset, lat, lon },
 *     popular: [{ id, name }],   // G1 空输入快捷项；最近使用属 G2
 *   };
 */
(function () {
  'use strict';

  var UID = 0;
  var API = {
    places: '/api/v1/geo/places',
    resolve: '/api/v1/geo/place-resolve',
  };
  var STATUS_LABELS = { empty: '', auto: '自动推导', manual: '已手动校正', unresolved: '未解析' };

  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>'"]/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[ch];
    });
  }

  function el(tag, className, html) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (html != null) node.innerHTML = html;
    return node;
  }

  function debounce(fn, ms) {
    var timer = null;
    return function () {
      var args = arguments, self = this;
      if (timer) clearTimeout(timer);
      timer = setTimeout(function () { timer = null; fn.apply(self, args); }, ms);
    };
  }

  function fmtUTC(total) {
    var sign = total < 0 ? '-' : '+';
    var abs = Math.abs(total);
    var hours = Math.floor(abs / 60), rest = abs % 60;
    var label = rest === 0 ? 'UTC' + sign + hours : 'UTC' + sign + hours + ':' + String(rest).padStart(2, '0');
    return label + '（' + total + ' 分钟）';
  }

  function fmtCoord(value, positive, negative) {
    return Math.abs(value).toFixed(4) + '°' + (value < 0 ? negative : positive);
  }

  function fmtOffsetShort(minutes) {
    var total = Math.round(minutes);
    var sign = total < 0 ? '-' : '+';
    var abs = Math.abs(total);
    var hours = Math.floor(abs / 60), rest = abs % 60;
    return 'UTC' + sign + hours + (rest ? ':' + String(rest).padStart(2, '0') : '');
  }

  /* UTC-12 … UTC+14，含常用 :30 / :45 档（§4.3） */
  function timezoneOptions() {
    var hours = [];
    for (var h = -12; h <= 14; h += 1) hours.push(h * 60);
    var extras = [-390, -270, -210, 210, 270, 330, 345, 390, 525, 570, 630, 765];
    var seen = {};
    var out = [];
    hours.concat(extras).sort(function (a, b) { return a - b; }).forEach(function (minutes) {
      if (seen[minutes]) return;
      seen[minutes] = true;
      out.push({ value: minutes, label: fmtUTC(minutes).replace('（' + minutes + ' 分钟）', '') });
    });
    return out;
  }

  function apiJSON(url, body) {
    var init = { headers: { 'Content-Type': 'application/json' } };
    if (body !== undefined) {
      init.method = 'POST';
      init.body = JSON.stringify(body);
    }
    return fetch(url, init).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (payload) {
        if (!response.ok || !payload.success) {
          var error = new Error((payload.error && payload.error.message) || ('请求失败：' + response.status));
          error.code = payload.error && payload.error.code;
          throw error;
        }
        return payload.data;
      });
    });
  }

  function createPlacePicker(config) {
    var mount = document.querySelector(config.mount);
    if (!mount) throw new Error('place-picker: mount 不存在 ' + config.mount);
    var dateInput = document.querySelector(config.dateInput);
    var timeInput = config.timeInput ? document.querySelector(config.timeInput) : null;
    var houseInput = config.houseInput ? document.querySelector(config.houseInput) : null;
    var outputs = {};
    Object.keys(config.outputs).forEach(function (key) {
      outputs[key] = document.querySelector(config.outputs[key]);
    });
    var uid = (UID += 1);
    var listId = 'place-list-' + uid;
    var inputId = 'place-search-' + uid;

    var state = 'empty';            // empty | auto | manual | unresolved（§4.7）
    var selected = null;            // 当前选中的地名 hit
    var lastResolution = null;      // 最近一次 PlaceResolution
    var searchToken = 0;

    // ---------- DOM 构建 ----------
    var root = el('div', 'place-picker');

    var searchRow = el('div', 'place-combobox');
    var search = el('input', 'place-search');
    search.id = inputId;
    search.type = 'text';
    search.setAttribute('role', 'combobox');
    search.setAttribute('aria-expanded', 'false');
    search.setAttribute('aria-controls', listId);
    search.setAttribute('aria-autocomplete', 'list');
    search.setAttribute('autocomplete', 'off');
    search.placeholder = '搜索城市 / 拼音（如：上海、shanghai、sh）';
    var searchStatus = el('span', 'place-search-status');
    searchStatus.setAttribute('role', 'status');
    searchStatus.setAttribute('aria-live', 'polite');
    searchRow.append(search, searchStatus);

    var listbox = el('ul', 'place-list');
    listbox.id = listId;
    listbox.setAttribute('role', 'listbox');
    listbox.setAttribute('aria-label', '地名候选');
    listbox.hidden = true;

    var quickRow = el('div', 'place-quick');
    quickRow.setAttribute('role', 'group');
    quickRow.setAttribute('aria-label', '常用城市');
    (config.popular || []).forEach(function (item) {
      var chip = el('button', 'place-chip');
      chip.type = 'button';
      chip.textContent = item.name;
      chip.addEventListener('click', function () { resolveById(item.id); });
      quickRow.appendChild(chip);
    });

    var noMatch = el('div', 'place-nomatch');
    noMatch.hidden = true;

    var card = el('div', 'place-card');
    card.setAttribute('aria-live', 'polite');
    card.hidden = true;

    var tune = el('div', 'place-tune');
    tune.hidden = true;
    tune.innerHTML =
      '<div class="place-tune-head">' +
      '  <strong>微调坐标与时区</strong>' +
      '  <button type="button" class="place-restore" hidden>恢复自动推导</button>' +
      '</div>' +
      '<div class="two-fields">' +
      '  <div><label for="place-tune-lat-' + uid + '">纬度</label>' +
      '    <div class="unit-input"><input id="place-tune-lat-' + uid + '" type="number" min="0" max="90" step="0.0001" inputmode="decimal"><select class="place-hem-lat" aria-label="南北纬"><option value="N">北纬 N</option><option value="S">南纬 S</option></select></div></div>' +
      '  <div><label for="place-tune-lon-' + uid + '">经度</label>' +
      '    <div class="unit-input"><input id="place-tune-lon-' + uid + '" type="number" min="0" max="180" step="0.0001" inputmode="decimal"><select class="place-hem-lon" aria-label="东西经"><option value="E">东经 E</option><option value="W">西经 W</option></select></div></div>' +
      '</div>' +
      '<label for="place-tune-tz-' + uid + '">时区</label>' +
      '<div class="unit-input"><select id="place-tune-tz-' + uid + '" class="place-tz-select"><option value="">（保持当前）</option></select><span>UTC</span></div>' +
      '<p class="place-tune-note">手动值不会被自动推导静默覆盖；点「恢复自动推导」才回到地点库结果。</p>';
    var tuneInputs = tune.querySelectorAll('input[type=number]');
    var tuneLat = tuneInputs[0];
    var tuneLon = tuneInputs[1];
    var tuneLatHem = tune.querySelector('.place-hem-lat');
    var tuneLonHem = tune.querySelector('.place-hem-lon');
    var tuneTz = tune.querySelector('.place-tz-select');
    var restoreButton = tune.querySelector('.place-restore');
    timezoneOptions().forEach(function (option) {
      var node = document.createElement('option');
      node.value = String(option.value);
      node.textContent = option.label + '（' + option.value + ' 分钟）';
      tuneTz.appendChild(node);
    });

    var notice = el('p', 'place-warning');
    notice.setAttribute('role', 'status');
    notice.setAttribute('aria-live', 'polite');
    notice.hidden = true;

    var tuneToggle = el('button', 'place-open-tune');
    tuneToggle.type = 'button';
    tuneToggle.textContent = '手动输入坐标 / 时区';
    tuneToggle.hidden = true;

    root.append(searchRow, listbox, quickRow, noMatch, card, notice, tuneToggle, tune);
    mount.appendChild(root);

    // ---------- 工具 ----------
    function currentBirthDate() {
      if (!dateInput || !dateInput.value) return null;
      var parts = dateInput.value.split('-').map(Number);
      var time = timeInput && timeInput.value ? timeInput.value.split(':').map(Number) : [12, 0];
      return { year: parts[0], month: parts[1], day: parts[2], hour: time[0] || 0, minute: time[1] || 0 };
    }

    function readOutput(name) {
      return outputs[name] ? Number(outputs[name].value) : NaN;
    }

    function writeOutput(name, value) {
      if (outputs[name]) outputs[name].value = String(value);
    }

    function setStatus(next) {
      state = next;
      // 回显给「解析提示词」页签（§4.7）；排盘请求体不含这份摘要
      window.PlacePickerState = {
        state: next,
        summary: buildSummary(),
      };
    }

    function buildSummary() {
      if (!lastResolution && !selected) return null;
      var source = lastResolution || {};
      var place = source.place || selected || {};
      var time = source.time || {};
      return {
        status: STATUS_LABELS[state] || state,
        place_id: place.id || null,
        place: place.display || place.name_zh || null,
        level: place.level || null,
        lat: readOutput('lat'),
        lon: readOutput('lon'),
        utc_offset_minutes: Number.isFinite(readOutput('offset')) ? readOutput('offset') : null,
        tz_name: time.tz_name || place.tz || null,
        std_offset_minutes: time.std_offset_minutes == null ? null : time.std_offset_minutes,
        dst_minutes: time.dst_minutes == null ? null : time.dst_minutes,
        dst_active: !!time.dst_active,
        dst_transition: time.dst_transition || null,
        confidence: time.confidence || null,
        derived_from: (source.provenance || {}).derived_from || null,
        provenance: source.provenance || null,
      };
    }

    function emitChange() {
      if (typeof config.onChange === 'function') config.onChange(buildSummary());
    }

    // ---------- 渲染 ----------
    function renderOptions(hits) {
      listbox.replaceChildren();
      hits.forEach(function (hit, index) {
        var item = el('li', 'place-option');
        item.id = listId + '-option-' + index;
        item.setAttribute('role', 'option');
        item.setAttribute('aria-selected', 'false');
        item.innerHTML =
          '<span class="place-option-name">' + esc(hit.display) + '</span>' +
          '<span class="place-option-admin">' + esc(hit.admin1) + '</span>' +
          '<span class="place-option-geo">' + esc(hit.country_zh) + ' · ' + esc(fmtCoord(hit.lon, 'E', 'W')) + ' ' + esc(fmtCoord(hit.lat, 'N', 'S')) + '</span>' +
          '<span class="place-option-tz">[' + esc(hit.tz) + ']</span>';
        item.addEventListener('click', function () { selectHit(hit); });
        listbox.appendChild(item);
      });
      activeIndex = -1;
      listbox.hidden = hits.length === 0;
      search.setAttribute('aria-expanded', hits.length ? 'true' : 'false');
      search.removeAttribute('aria-activedescendant');
    }

    var activeIndex = -1;
    function moveActive(delta) {
      var items = listbox.querySelectorAll('[role=option]');
      if (!items.length) return;
      activeIndex = (activeIndex + delta + items.length) % items.length;
      items.forEach(function (item, index) {
        item.setAttribute('aria-selected', index === activeIndex ? 'true' : 'false');
        if (index === activeIndex) {
          item.scrollIntoView({ block: 'nearest' });
          search.setAttribute('aria-activedescendant', item.id);
        }
      });
    }

    function renderCard() {
      var resolution = lastResolution;
      if (!resolution) return;
      var place = resolution.place;
      var time = resolution.time;
      var provenance = resolution.provenance;
      var lat = readOutput('lat');
      var lon = readOutput('lon');
      var offset = readOutput('offset');
      var lines = [];

      var pointLabel = place && place.level === 'city' ? '城市代表点' : (place ? place.level + ' 代表点' : '手动坐标');
      lines.push('<div class="place-card-coord">' + esc(pointLabel) + ' · ' + esc(fmtCoord(lon, 'E', 'W')) + ' · ' + esc(fmtCoord(lat, 'N', 'S')) +
        (place && place.distance_km != null ? ' · 距最近收录城市约 ' + esc(place.distance_km) + ' km' : '') + '</div>');

      var offsetLine = '时区 ' + esc(time.tz_name || '未知') + ' · 当时偏移 ';
      if (state === 'manual') {
        offsetLine += esc(fmtUTC(offset)) + '（<strong>已手动校正</strong>，自动推导为 ' + esc(fmtUTC(time.utc_offset_minutes)) + '）';
      } else if (state === 'unresolved' && time.utc_offset_minutes != null && offset !== time.utc_offset_minutes) {
        offsetLine += esc(fmtUTC(time.utc_offset_minutes)) + '；当前表单 ' + esc(fmtUTC(offset)) + '，两者不一致';
      } else if (time.utc_offset_minutes == null) {
        offsetLine += esc(time.tz_available === false ? '（时区数据不可用，请手动选择）' : '（未解析，当前 ' + fmtUTC(offset || 0) + '）');
      } else {
        offsetLine += esc(fmtUTC(time.utc_offset_minutes)) + (state === 'auto' ? '（自动推导）' : '（当前值）');
      }
      lines.push('<div class="place-card-tz">' + offsetLine + '</div>');

      // 证据行是必显项（§4.4）
      var evidence;
      if (time.tz_available === false) {
        evidence = 'ⓘ 时区数据不可用：偏移未能自动推导，请在「微调」中手动选择时区。地名与坐标解析不受影响。';
      } else if (time.dst_active && time.dst_transition) {
        evidence = 'ⓘ ' + esc(time.dst_transition.start) + ' 起至 ' + esc(time.dst_transition.end) +
          ' 当地实行夏令时，' + esc(time.dst_transition.resume) + ' 起恢复 ' +
          esc(fmtOffsetShort(time.std_offset_minutes)) + '。';
      } else if (time.dst_minutes < 0) {
        evidence = 'ⓘ 该日期当地实行「负夏令时」（标准 ' + esc(fmtUTC(time.std_offset_minutes)) +
          '，实际 ' + esc(fmtUTC(time.utc_offset_minutes)) + '），按实际偏移计算。';
      } else {
        evidence = 'ⓘ 该日期当地不处于夏令时，偏移即标准偏移 ' + esc(fmtUTC(time.utc_offset_minutes)) + '。';
      }
      if (time.confidence === 'uncertain') {
        evidence += ' ⚠ 出生日早于该时区首个切换点（地方平时 LMT 段），引擎按整数分钟取整，误差 ≤30 秒。';
      }
      var confidenceLabel = { exact: '区县精确', city: '城市级', approximate: '近似', uncertain: '不确定' }[time.confidence] || time.confidence;
      lines.push(
        '<div class="place-evidence"><span>' + evidence + '</span>' +
        '<details class="place-why"><summary>为什么？</summary><ul>' +
        '<li>推导规则：' + esc(provenance.rule || 'zoneinfo') + '，日期 ' + esc(provenance.birth_date) + '（取该日 ' + esc(provenance.birth_time_used || '12:00') + '）</li>' +
        '<li>时区数据：tzdata ' + esc(provenance.tzdata_version) + '（' + esc(provenance.tz_source) + '）</li>' +
        '<li>地名数据：' + esc(provenance.dataset) + ' revision ' + esc(provenance.dataset_revision) + '，来源 ' + esc(provenance.derived_from) + '</li>' +
        '<li>置信度：' + esc(confidenceLabel || '—') + '；偏移取整误差 ≤30 秒（≈上升 0.01°）</li>' +
        '<li>本卡只陈述民用地名与时区法规事实，不含任何命理结论。</li>' +
        '</ul></details></div>');

      card.innerHTML =
        '<div class="place-card-head"><strong>' + esc(place ? place.display : '手动坐标') + '</strong>' +
        '<span class="place-status" data-state="' + esc(state) + '">' + esc(STATUS_LABELS[state] || '未解析') + '</span>' +
        '<span class="place-card-actions">' +
        '<button type="button" class="place-change">更换</button>' +
        '<button type="button" class="place-tune-open">微调</button></span></div>' +
        lines.join('');
      card.hidden = false;
      card.querySelector('.place-change').addEventListener('click', function () {
        selected = null;
        lastResolution = null;
        card.hidden = true;
        tuneToggle.hidden = false;
        setStatus('empty');
        search.focus();
        search.select();
        runSearch('');
      });
      card.querySelector('.place-tune-open').addEventListener('click', openTune);

      var warningBox = el('div', 'place-warnings');
      warningBox.setAttribute('aria-live', 'polite');
      (resolution.warnings || []).forEach(function (warning) {
        warningBox.appendChild(el('p', 'place-warning', (warning.level === 'notice' ? 'ℹ ' : '⚠ ') + esc(warning.text)));
      });
      card.appendChild(warningBox);
      // 卡片与「解析提示词」页签的回显保持同源（§4.7）
      if (window.PlacePickerState) window.PlacePickerState.summary = buildSummary();
      emitChange();
    }

    function showNotice(text, action) {
      notice.replaceChildren();
      notice.appendChild(el('span', null, '⚠ ' + text));
      if (action) {
        var button = el('button', 'place-notice-action');
        button.type = 'button';
        button.textContent = action.label;
        button.addEventListener('click', action.onClick);
        notice.appendChild(button);
      }
      notice.hidden = false;
    }

    function clearNotice() {
      notice.hidden = true;
      notice.replaceChildren();
    }

    // ---------- 状态切换 ----------
    function openTune() {
      var lat = readOutput('lat');
      var lon = readOutput('lon');
      var offset = readOutput('offset');
      tuneLat.value = String(Math.abs(lat));
      tuneLatHem.value = lat < 0 ? 'S' : 'N';
      tuneLon.value = String(Math.abs(lon));
      tuneLonHem.value = lon < 0 ? 'W' : 'E';
      var option = null;
      timezoneOptions().some(function (item) {
        if (item.value === offset) { option = item; return true; }
        return false;
      });
      tuneTz.value = option ? String(option.value) : '';
      restoreButton.hidden = !selected;
      tune.hidden = false;
      tuneLat.focus();
    }

    function applyTune(sourceField) {
      var latAbs = parseFloat(tuneLat.value);
      var lonAbs = parseFloat(tuneLon.value);
      if (Number.isFinite(latAbs)) writeOutput('lat', (tuneLatHem.value === 'S' ? -1 : 1) * Math.min(90, Math.max(0, latAbs)));
      if (Number.isFinite(lonAbs)) writeOutput('lon', (tuneLonHem.value === 'W' ? -1 : 1) * Math.min(180, Math.max(0, lonAbs)));
      if (tuneTz.value !== '') writeOutput('offset', parseInt(tuneTz.value, 10));
      setStatus(selected ? 'manual' : 'unresolved');
      // 坐标/偏移变了：刷新可核对的地点卡（不静默改用户值，§4.4）
      var placeId = (selected && selected.id) ||
        (lastResolution && lastResolution.place && lastResolution.place.id) || null;
      restoreButton.hidden = !selected;
      if (placeId && state === 'manual') {
        resolveById(placeId, true);
      } else {
        rederive();
      }
    }

    function renderCardFromCache() {
      if (lastResolution) renderCard();
    }

    // ---------- 主流程 ----------
    function runSearch(query) {
      var token = (searchToken += 1);
      if (!query) {
        listbox.hidden = true;
        search.setAttribute('aria-expanded', 'false');
        noMatch.hidden = true;
        quickRow.hidden = false;
        return;
      }
      quickRow.hidden = true;
      var isCJK = !!query.match(/[\u3400-\u9fff]/);
      if (!isCJK && query.replace(/\s/g, '').length < 2) {
        listbox.hidden = true;
        noMatch.hidden = true;
        return;
      }
      apiJSON(API.places + '?q=' + encodeURIComponent(query) + '&limit=8').then(function (data) {
        if (token !== searchToken) return;
        if (data.results.length) {
          noMatch.hidden = true;
          renderOptions(data.results);
        } else {
          listbox.hidden = true;
          search.setAttribute('aria-expanded', 'false');
          noMatch.hidden = false;
          noMatch.innerHTML = '';
          noMatch.appendChild(el('p', 'place-nomatch-text', '没有找到「' + esc(query) + '」。'));
          var manualButton = el('button', 'place-nomatch-action');
          manualButton.type = 'button';
          manualButton.textContent = '手动输入坐标';
          manualButton.addEventListener('click', function () { openTune(); });
          var nearestButton = el('button', 'place-nomatch-action');
          nearestButton.type = 'button';
          nearestButton.textContent = '按坐标找最近城市';
          nearestButton.addEventListener('click', function () { resolveByCoordinates(); });
          noMatch.append(manualButton, nearestButton);
        }
      }).catch(function (error) {
        if (token !== searchToken) return;
        showNotice('地名搜索失败：' + (error.message || error));
      });
    }

    function selectHit(hit) {
      selected = hit;
      listbox.hidden = true;
      search.setAttribute('aria-expanded', 'false');
      search.value = hit.display;
      noMatch.hidden = true;
      quickRow.hidden = true;
      tuneToggle.hidden = true;
      writeOutput('lat', hit.lat);
      writeOutput('lon', hit.lon);
      resolveById(hit.id);
    }

    function resolveById(placeId, keepValues) {
      var date = currentBirthDate();
      if (!date) {
        showNotice('请先填写出生日期，再选择地点（偏移按出生时刻推导）。');
        return;
      }
      var payload = { place_id: placeId, date: date };
      if (houseInput) payload.house_system = houseInput.value;
      if (keepValues) payload.utc_offset_minutes = readOutput('offset');  // 仅供服务端比较警告，不写回
      apiJSON(API.resolve, payload).then(function (data) {
        lastResolution = data;
        selected = data.place || selected;
        if (!keepValues) {
          if (data.time.utc_offset_minutes != null) writeOutput('offset', data.time.utc_offset_minutes);
          if (data.place) {
            writeOutput('lat', data.place.lat);
            writeOutput('lon', data.place.lon);
          }
          setStatus('auto');
        }
        clearNotice();
        renderCard();
        search.value = data.place ? data.place.display : search.value;
      }).catch(function (error) {
        if (error.code === 'GEO_CONFIG_ERROR') {
          showNotice('地名库不可用，已退回手动模式：请用「手动输入坐标」填写，提交仍可用。');
        } else {
          showNotice('地点解析失败：' + (error.message || error));
        }
        tuneToggle.hidden = false;
      });
    }

    /* 用当前表单值重推参考偏移与警告，不写回任何输出（manual/unresolved 专用，§4.4） */
    function rederive() {
      var date = currentBirthDate();
      if (!date) { renderCardFromCache(); return; }
      var payload = {
        latitude: readOutput('lat'), longitude: readOutput('lon'),
        utc_offset_minutes: readOutput('offset'), date: date,
      };
      if (houseInput) payload.house_system = houseInput.value;
      apiJSON(API.resolve, payload).then(function (data) {
        lastResolution = data;
        renderCard();
      }).catch(function () { renderCardFromCache(); });
    }

    function resolveByCoordinates() {
      var date = currentBirthDate();
      if (!date) {
        showNotice('请先填写出生日期。');
        return;
      }
      var payload = {
        latitude: readOutput('lat'), longitude: readOutput('lon'),
        utc_offset_minutes: readOutput('offset'), date: date,
      };
      if (houseInput) payload.house_system = houseInput.value;
      apiJSON(API.resolve, payload).then(function (data) {
        lastResolution = data;
        // 反查仅作提示，不改变状态与用户值（§4.7）
        selected = null;
        setStatus('unresolved');
        renderCard();
        tuneToggle.hidden = false;
      }).catch(function (error) {
        showNotice('坐标解析失败：' + (error.message || error));
      });
    }

    /* 首屏口径提示（§11 默认案例决策）：不自动改值，只把矛盾摆出来 */
    function initialCheck() {
      var date = currentBirthDate();
      if (!date) return;
      var payload = {
        latitude: readOutput('lat'), longitude: readOutput('lon'),
        utc_offset_minutes: readOutput('offset'), date: date,
      };
      if (houseInput) payload.house_system = houseInput.value;
      apiJSON(API.resolve, payload).then(function (data) {
        lastResolution = data;
        var derived = data.time && data.time.utc_offset_minutes;
        var current = readOutput('offset');
        if (derived == null || derived === current) return;
        var hint = '当前偏移 ' + fmtUTC(current) + '；按出生坐标' +
          (data.place ? '（' + data.place.display + '）' : '') + '与 ' + data.provenance.birth_date +
          ' 自动推导为 ' + fmtUTC(derived) +
          (data.time.dst_active && data.time.dst_transition
            ? '（该日期当地处于夏令时，' + data.time.dst_transition.start + ' 起至 ' + data.time.dst_transition.end + '，' + data.time.dst_transition.resume + ' 起恢复）'
            : '') + '。搜索并选择出生地点即可采用推导值。';
        setStatus('unresolved');
        renderCard();
        showNotice(hint, {
          label: '采用推导值 ' + fmtUTC(derived).replace('（' + derived + ' 分钟）', ''),
          onClick: function () {
            writeOutput('offset', derived);
            setStatus('unresolved');
            renderCard();
            clearNotice();
            emitChange();
          },
        });
      }).catch(function () { /* 时区服务缺失不拦截表单（§6.4 降级） */ });
    }

    // ---------- 事件绑定 ----------
    var debouncedSearch = debounce(function () { runSearch(search.value.trim()); }, 120);
    search.addEventListener('input', function () {
      clearNotice();
      debouncedSearch();
    });
    search.addEventListener('focus', function () {
      if (!search.value.trim()) runSearch('');
    });
    search.addEventListener('blur', function () {
      // Tab/点击离开：保留输入，不强行清掉；候选列表收起
      setTimeout(function () {
        listbox.hidden = true;
        search.setAttribute('aria-expanded', 'false');
        search.removeAttribute('aria-activedescendant');
      }, 120);
    });
    search.addEventListener('keydown', function (event) {
      if (event.key === 'ArrowDown') { event.preventDefault(); moveActive(1); }
      else if (event.key === 'ArrowUp') { event.preventDefault(); moveActive(-1); }
      else if (event.key === 'Enter') {
        var items = listbox.querySelectorAll('[role=option]');
        if (!listbox.hidden && items.length) {
          event.preventDefault();
          var index = activeIndex >= 0 ? activeIndex : 0;
          // click 已绑定选择逻辑；直接合成点击以复用数据闭包
          items[index].click();
        }
      } else if (event.key === 'Escape') {
        listbox.hidden = true;
        search.setAttribute('aria-expanded', 'false');
      }
    });

    tuneLat.addEventListener('change', function () { applyTune('lat'); });
    tuneLatHem.addEventListener('change', function () { applyTune('lat'); });
    tuneLon.addEventListener('change', function () { applyTune('lon'); });
    tuneLonHem.addEventListener('change', function () { applyTune('lon'); });
    tuneTz.addEventListener('change', function () { applyTune('tz'); });

    restoreButton.addEventListener('click', function () {
      if (!selected && !(lastResolution && lastResolution.place)) {
        showNotice('没有已选地点，无法恢复自动推导。');
        return;
      }
      resolveById((lastResolution.place && lastResolution.place.id) || selected.id);
    });

    tuneToggle.addEventListener('click', openTune);

    if (dateInput) {
      dateInput.addEventListener('change', function () {
        if (state === 'auto' && lastResolution && lastResolution.place) {
          resolveById(lastResolution.place.id);
        } else if (state === 'manual' && selected && selected.id) {
          resolveById(selected.id, true);
        } else if (state === 'manual' || state === 'unresolved') {
          rederive();
        }
      });
    }
    if (houseInput) {
      houseInput.addEventListener('change', function () {
        if (state === 'auto' && lastResolution && lastResolution.place) resolveById(lastResolution.place.id);
        else if (state === 'manual' && selected && selected.id) resolveById(selected.id, true);
        else if (lastResolution || selected) rederive();
      });
    }

    // 初始：暴露当前状态给提示词页签 + 首屏口径检查
    setStatus('empty');
    window.PlacePickerState.summary = buildSummary();
    initialCheck();

    return {
      getState: function () { return state; },
      summary: buildSummary,
    };
  }

  function boot() {
    var config = window.PLACE_PICKER_CONFIG;
    if (!config) return;
    try {
      window.placePicker = createPlacePicker(config);
    } catch (error) {
      // 组件故障不能让表单不可用（降级为手动，§6.4）
      console.error('place-picker 初始化失败：', error);
    }
  }

  window.createPlacePicker = createPlacePicker;
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
