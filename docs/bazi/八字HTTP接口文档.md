# 八字 HTTP 接口

引擎：`ZhouYi.BaZi`（`ba_zi_web_cli`）；口径：`data.meta.rule_profile`（对象，版本串在 `.profile_version`）= `bazi-rules/0.1`；顶层 envelope `meta` 仅 `api_version`/`algorithm_version`/`request_id`；
校准状态：`in_progress`。

## 对外访问地址

- 本地：`http://127.0.0.1:8765` 或部署机 `:8768`
- 生产：`https://zhouyilab.k8s.gold`（详见 [HTTP 接口访问地址](../HTTP接口访问地址.md)）

## 排盘

`POST /api/v1/bazi/charts`

```json
{"date": {"year": 1990, "month": 6, "day": 15, "hour": 14, "minute": 30},
 "gender": "male", "calendar": "solar"}
```

- `calendar`：`solar`/`lunar`；闰月标志是 `date.leap_month`（**位于 `date` 对象内**，顶层同名键被静默忽略），见响应 `lunar_date` 回显；
- `gender`：`male`/`female`（影响大运顺逆与神煞性别项）。

响应 `data` 关键字段（全部为事实结构，无断语）：

| 组 | 字段 |
| --- | --- |
| 四柱 | `ba_zi`（年月日时干支）、`pillars`（`{year,month,day,hour}` 对象；逐柱含十神 `stem_ten_god`、藏干 `hidden_stems`、纳音 `na_yin`/`na_yin_element`、旬空 `void_branches`、自坐 `self_sitting`、逐柱神煞 `shen_sha`/`shen_sha_details`、星运 `star_fortune`） |
| 日主 | `day_master`：`{stem, element, yin_yang}`；旺衰强弱未实现（`rules.boundary_note` 自述），勿在客户端臆造 |
| 历法回显 | `solar_date`、`lunar_date`、`chart_lunar_date`、`birth_date`、`birth_time`、`calendar`、`gender`、`is_male` |
| 空亡 | `xun_kong`（日柱旬内二空） |
| 大运 | `da_yun`：`{list[10], qi_yun_age, shun_pai, start_detail}` |
| 神煞 | `shen_sha_summary` 顶层 18 键、四种形状：① `tian_yi_gui_ren`/`yi_ma`/`san_qi`/`tai_ji` = `{matched, occurrences}`；② `lu_shen`/`jin_yu` = `{basis, day_stem, matched, occurrence_count}`；③ `xue_guan` 仅 `{occurrences}`，`de_xiu`/`tian_yue_de`/`tian_luo_di_wang`/`tong_zi` 各有自形；④ 汇总类：`auxiliary`（孤辰寡宿/勾神绞煞/空亡/安身财等子标签组）、`relations`（干支关系/`interchanges` 四宫互换/`sanhe_ju`/`wangshuai_info`）、`group1_occurrences`/`group2_occurrences`/`source_occurrences`/`lu_ma_patterns`（四宫互换与禄马细节）、`source`（单一古籍口径字符串） |

## 神煞知识文档

`GET /api/v1/bazi/shen-sha/<id>`

- `id` = `config/bazi/shen_sha/` 的 ASCII slug（如 `jie_sha_wang_shen`、
  `tian_luo_di_wang`；总索引 id 是 `catalog`，**不带 .json 后缀**）；三份中文名文档经别名访问
  （`zi_wu_mao_you_si_gong_hu_huan_shen_sha`、`yin_shen_si_hai_…`、
  `chen_xu_chou_wei_…`）。
- 响应在 JSON 资源上自动挂载 `document_markdown`（`source_document` 指向
  `docs/bazi/*.md` 校订文），含 `calculation`（安煞法）、`boundaries`、
  `editorial_notes`、`calibration_status`；`calculation` 仅单煞资源有，
  三份四宫互换章节级资源无该键。
- 错误：400 `INVALID_SHEN_SHA_ID`（非 ASCII slug）、404 `SHEN_SHA_NOT_FOUND`、
  500 `SHEN_SHA_RESOURCE_ERROR`。

## 分布画像（人性化图表数据包）

`POST /api/v1/bazi/distribution`

入参：`{"chart": <排盘 data>}` 或 `{"chart_request": <排盘入参>}`（二选一），
可选 `"label"`（≤60 字符）。返回 `bazi-distribution/1.0`：

`data.charts` 为 3 元素数组，每图以 `id` 区分：
- `signs` 干支五行分布（木火土金水，一支本气即该支五行）；
- `gods` 十神五类分布（比劫/食伤/财/官杀/印）；
- `polarity` 阴阳底色；
- 顶层 `summary_zh` "×"式底色总结、`label` 回显；`point_basis`：
  `{id: "stems_plus_hidden", count, points[{point_id, point_name, kind}]}`——
  四柱天干+地支藏干逐字计点（五行/阴阳图全计；十神图分母不含日干自身）；
  数据源全部为排盘既有字段 + 内核标准表，零新增算法、**无吉凶断语**。

## 已知边界

- 十二长生/神煞口径以 `data.meta.rule_profile` 逐条自述为准；古籍出处校勘与
  六爻伏神章同批挂起（网络通道恢复后处理）；
- 起运精确到节令差分，真太阳时校正走 `/api/v1/calendar/true-solar-time`
  先行换算再入 `date`（本接口不内嵌经纬度校正）；
- 回归锁：`tests/test_bazi_web_contract`、`tests/test_bazi_distribution`
  （与 `config/platform/calibration_suites.json` 登记一致）。
