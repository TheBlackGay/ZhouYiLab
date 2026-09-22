# 八字 HTTP 接口

引擎：`ZhouYi.BaZi`（`ba_zi_web_cli`）；口径：`meta.rule_profile` = `bazi-rules/0.1`；
校准状态：`in_progress`。

## 对外访问地址

- 本地：`http://127.0.0.1:8765` 或部署机 `:8768`
- 生产：`https://zhouyilab.k8s.gold`（详见 [HTTP 接口访问地址](HTTP接口访问地址.md)）

## 排盘

`POST /api/v1/bazi/charts`

```json
{"date": {"year": 1990, "month": 6, "day": 15, "hour": 14, "minute": 30},
 "gender": "male", "calendar": "solar"}
```

- `calendar`：`solar`/`lunar`（农历含闰月语义，见响应 `lunar_date` 回显）；
- `gender`：`male`/`female`（影响大运顺逆与神煞性别项）。

响应 `data` 关键字段（全部为事实结构，无断语）：

| 组 | 字段 |
| --- | --- |
| 四柱 | `ba_zi`（年月日时干支）、`pillars`（逐柱含十神 `shi_shen`、藏干、纳音、逐柱旬空） |
| 日主 | `day_master`（天干/五行/强弱依据） |
| 历法回显 | `solar_date`、`lunar_date`、`chart_lunar_date`、`birth_date`、`birth_time`、`calendar`、`gender`、`is_male` |
| 空亡 | `xun_kong`（日柱旬内二空） |
| 大运 | `da_yun`：`{list[10], qi_yun_age, shun_pai, start_detail}` |
| 神煞 | `shen_sha_summary`：按煞分组（`tian_yi_gui_ren/yi_ma/lu_shen/jin_yu/san_qi/tai_ji/xue_guan/kongwang 类 auxiliary/relations 干支关系/四宫互换 …`），每组含 `matched/occurrences/basis`，`source` 指回知识文档 |

## 神煞知识文档

`GET /api/v1/bazi/shen-sha/<id>`

- `id` = `config/bazi/shen_sha/` 的 ASCII slug（如 `jie_sha_wang_shen`、
  `tian_luo_di_wang`、`catalog.json` 为总索引）；三份中文名文档经别名访问
  （`zi_wu_mao_you_si_gong_hu_huan_shen_sha`、`yin_shen_si_hai_…`、
  `chen_xu_chou_wei_…`）。
- 响应在 JSON 资源上自动挂载 `document_markdown`（`source_document` 指向
  `docs/bazi/*.md` 校订文），含 `calculation`（安煞法）、`boundaries`、
  `editorial_notes`、`calibration_status`。
- 错误：400 `INVALID_SHEN_SHA_ID`（非 ASCII slug）、404 `SHEN_SHA_NOT_FOUND`、
  500 `SHEN_SHA_RESOURCE_ERROR`。

## 分布画像（人性化图表数据包）

`POST /api/v1/bazi/distribution`

入参：`{"chart": <排盘 data>}` 或 `{"chart_request": <排盘入参>}`（二选一），
可选 `"label"`（≤60 字符）。返回 `bazi-distribution/1.0`：

- `charts[signs]` 干支五行分布（木火土金水，一支本气即该支五行）；
- `charts[gods]` 十神五类分布（比劫/食伤/财/官杀/印）；
- `charts[polarity]` 干之阴阳底色；
- 顶层 `summary_zh` "×"式底色总结；数据源全部为排盘既有字段 + 内核标准表，
  零新增算法、**无吉凶断语**。

## 已知边界

- 十二长生/神煞口径以 `meta.rule_profile` 逐条自述为准；古籍出处校勘与
  六爻伏神章同批挂起（网络通道恢复后处理）；
- 起运精确到节令差分，真太阳时校正走 `/api/v1/calendar/true-solar-time`
  先行换算再入 `date`（本接口不内嵌经纬度校正）；
- 回归锁：`tests/test_divination_web_contract.py`、`test_bazi_*` 与
  `config/platform/calibration_suites.json` 登记套件。
