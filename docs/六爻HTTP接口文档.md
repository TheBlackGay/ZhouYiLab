# 六爻 HTTP 接口

引擎：`ZhouYi.LiuYao`（`liu_yao_web_cli`）；口径：`meta.rule_profile`
= `liu-yao-rules/0.2`（**D1=A 以《增删卜易》为主**，2026-09-20 拍板）；
校准状态：`in_progress`（结构层案例 ✅ `config/liuyao/cases/`，古籍验例待校勘）。

## 对外访问地址

- 本地：`http://127.0.0.1:8765`（开发端口）或部署机 `:8768`
- 生产：`https://zhouyilab.k8s.gold`（详见 [HTTP 接口访问地址](HTTP接口访问地址.md)）

## 起卦（排盘）

`POST /api/v1/liu-yao/charts`

```json
{
  "calendar": "solar",
  "date": {"year": 2025, "month": 2, "day": 12, "hour": 10},
  "hexagram_code": "110001",
  "changing_lines": [3]
}
```

- `hexagram_code`：**自初爻（索引 0）到上爻**六位 `0`/`1` 串，1 阳 0 阴；
  摇卦器（页面 `liuyao.html`）产出的即是该编码，接口层不做起卦随机数。
- `changing_lines`：动爻序号数组（1-6，可空＝静盘）。
- `calendar`：`solar`/`lunar`；月建日辰与旬空由内核历法换算（`data.ba_zi` 呈四柱+旬空）。

## 响应（envelope 下 data）

```
{
  "ben_gua_name": "艮宫: 山泽损",   // 卦名带宫（"宫: 卦名"）
  "bian_gua_name": "风泽中孚",      // 无动爻时缺省
  "ba_zi": { "day": {"stem":"壬","branch":"子"}, ..., "xun_kong_1": "寅", "xun_kong_2": "卯" },
  "shen_sa": { "劫煞": ["巳"], ... },  // 日课神煞 → 落爻地支
  "yao": [ {…六爻逐爻对象，见下} ],
  "meta": { "rule_profile": {…} }
}
```

每爻对象关键字段组（31 键，全为事实标注，**无断语**）：

| 组 | 字段 | 说明 |
| --- | --- | --- |
| 纳甲 | `mainPillar{stem,branch}` / `changedPillar` / `hiddenPillar` | 本爻、变爻、伏神干支（变卦纳甲按变卦内外卦；伏神取本宫纯卦） |
| 六亲 | `mainRelative` / `changedRelative` / `hiddenRelative` / `mainElement` / `changedElement` / `hiddenElement` | 一律按**本卦宫五行**论 |
| 世应六神 | `shiYingMark`（世/应）/ `spirit`（六神）/ `changeMark`（X/O）/ `mainYaoType` | |
| 旺衰 | `wangShuai`（旺相休囚死五态） | 月令通行表，DEF-4 修复后口径 |
| 状态标签 | `yue_po` `xun_kong` `he_ban` `an_dong` `jin_shen` `tui_shen` `hua_po` `hua_mu` `ru_mu` `ri_shengke` `ri_yue_hechong` `state_tags` `state_note` | 进退神＝《增删卜易》四对（子→丑/巳→午进，镜像退）；暗动须旺/相且被日冲 |
| 伏神 | `hidden_state_tags` / `hidden_state_note` | 只标月破/旬空/入飞神墓等**事实**；"出不出、破空可否用"待伏神章校勘（DEF-5），接口不下结论 |

## 卦面画像（人性化图表数据包）

`POST /api/v1/liu-yao/distribution`

入参：`{"chart": <卦盘对象>}` 或 `{"chart_request": <起卦入参原样透传>}`（二选一），
可选 `"label"`（≤60 字符）。返回 `liuyao-distribution/1.0`：

- `charts[rels]` 六亲重心分布（父母/兄弟/子孙/妻财/官鬼）；
- `charts[signs]` 爻之五行分布（木火土金水）；
- `charts[states]` 月令旺衰五态分布（旺相休囚死）；
- 顶层 `summary_zh` 三合一底色句；**无吉凶断语**——claim 为 in_progress，
  画像 basis 文案注明通行表出处。

## 错误

- 入参非法（卦码非 0/1 六位、动爻越界、日期非法等）：422
  `{"error": {"code": "INVALID_ARGUMENT", "message": "卦象代码只能包含 '0' 和 '1'"…}}`；
- distribution 入参二选一违规/label 超长：400 `INVALID_REQUEST`。

## 已知边界

- 起卦归人：接口只接受编码，"心诚则灵"式随机源不代供（摇卦器在页面）；
- 伏神可用结论、古籍验例：待《增删卜易》原文逐字校勘
  （[`伏神章校勘工作底稿`](product/伏神章校勘工作底稿.md)）；
- 结构回归锁：`test_liuyao_hexagram_table_contract`（64 卦全表）、
  `test_liuyao_jin_tui_contract`（四对扫描）、`test_liuyao_cases`（七例重放）、
  `test_wang_shuai_contract`（五表）。
