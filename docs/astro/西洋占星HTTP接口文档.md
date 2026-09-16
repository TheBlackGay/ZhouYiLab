# 西洋占星 HTTP 接口文档

## 基本信息

- 生产 Base URL：`https://zhouyilab.k8s.gold`
- 内网直连 Base URL：`http://192.168.31.183:8768`
- 本地开发 Base URL：`http://127.0.0.1:8768`
- Content-Type：`application/json`
- 当前生产域名由 HTTPS 反向代理转发至应用容器；调用方优先使用生产 Base URL，不要依赖容器端口。
- 当前仅支持本命盘（`natal`）
- 角度单位为度（°），速度单位为度/日（°/day），距离单位为 AU

所有接口使用统一响应封装：

```json
{
  "success": true,
  "data": {},
  "meta": {
    "api_version": "v1",
    "algorithm_version": "zhouyilab-astro/0.1.0",
    "request_id": "..."
  }
}
```

## 获取能力元数据

`GET /api/v1/astro/meta`

完整地址：`https://zhouyilab.k8s.gold/api/v1/astro/meta`

返回支持的点位、黄道、岁差、宫制和相位类型。当前支持点位：
`sun`、`moon`、`mercury`、`venus`、`mars`、`jupiter`、`saturn`、
`uranus`、`neptune`、`pluto`、`true_node`、`chiron`。

## 计算本命盘

`POST /api/v1/astro/charts`

请求字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `date.year` | integer | 是 | `1-9999` |
| `date.month` | integer | 是 | `1-12` |
| `date.day` | integer | 是 | 合法日期 |
| `date.hour` | integer | 否 | `0-23`，默认 `0` |
| `date.minute` | integer | 否 | `0-59`，默认 `0` |
| `date.second` | integer | 否 | `0-59`，默认 `0` |
| `utc_offset_minutes` | integer | 是 | `-720` 至 `840` |
| `location.latitude` | number | 是 | `-90` 至 `90` |
| `location.longitude` | number | 是 | `-180` 至 `180` |
| `location.elevation_m` | number | 否 | 海拔米数，默认 `0` |
| `zodiac` | string | 否 | `tropical` 或 `sidereal`，默认 `tropical` |
| `ayanamsa` | string | 否 | 热带必须为 `none`；恒星黄道当前使用 `fagan_bradley` |
| `house_system` | string | 否 | `placidus` 或 `whole_sign`，默认 `placidus` |
| `points` | string[] | 否 | 点位列表；省略时计算全部支持点位 |
| `include_aspects` | boolean | 否 | 是否计算主要相位，默认 `true` |
| `allow_moshier_fallback` | boolean | 否 | 缺少 `.se1` 时是否允许降级，默认 `false` |

省略 `points` 时，高精度 Swiss 模式默认返回 12 个点位（含 `chiron`）。若缺少 `.se1` 并显式允许 Moshier 降级，Moshier 不支持凯龙星，响应会跳过 `chiron`，并在 `calculation.warnings` 返回 `Moshier 模式不支持凯龙星，已跳过 chiron`；需要凯龙星时必须提供高精度星历文件。

请求示例：

```bash
curl -sS -X POST https://zhouyilab.k8s.gold/api/v1/astro/charts \
  -H 'Content-Type: application/json' \
  -d '{
    "date": {"year": 1990, "month": 5, "day": 20, "hour": 14},
    "utc_offset_minutes": 480,
    "location": {"latitude": 31.2304, "longitude": 121.4737},
    "zodiac": "tropical",
    "house_system": "placidus",
    "include_aspects": true,
    "allow_moshier_fallback": false
  }'
```

成功响应的 `data` 包含：

- `input`：标准化后的 UTC 时间、位置、黄道和宫制
- `calculation`：`julian_day_ut`、星历来源、`precision_mode` 和警告
- `angles`：上升点、中天、下降点、天底
- `planets`：黄经、黄纬、速度、星座、落宫、逆行状态
- `houses`：十二宫宫头和星座
- `aspects`：合相、六合、刑相、拱相、对冲及容许度
- `structured`：面向规则引擎和数据分析的稳定结构化视图，使用英文 ID、枚举和数值字段，不依赖中文展示文本

### `structured` 结构化视图

`structured.schema_version` 当前为 `astro-structured/1.0`。其中：

- `points`：每个天体的标准 ID、黄经、星座 `sign_id`、落宫和 `motion`；`classification` 提供元素（`fire`、`earth`、`air`、`water`）与模式（`cardinal`、`fixed`、`mutable`）。
- `angles`：ASC、MC、DSC、IC 的标准 ID、黄经和星座。
- `houses`：宫位编号、宫头、星座、元素和模式。
- `aspects`：以 `source_id`/`target_id` 连接点位，`type` 为相位枚举，`phase` 为 `applying` 或 `separating`。
- `aggregates`：元素、模式和落宫数量统计。这些是描述性统计，不代表任何占星解读结论。

原始的 `planets`、`houses`、`aspects` 字段仍然保留，便于旧客户端兼容；新规则或分析程序应优先使用 `structured`。

### `structured.derived_signals` 派生信号

`structured.derived_signals.schema_version` 当前为 `astro-derived-signals/1.0`。`signals` 中的每项均有稳定的 `signal_id`、`type`、关联的 `point_ids` 和可复核的 `evidence`。当前提供：

- `angular_planet`：行星落在第 1、4、7 或 10 宫；证据含宫位。
- `retrograde_point`：行星经度速度为负；证据含原始速度。
- `element_emphasis`、`modality_emphasis`：元素或模式计数达到 4；证据包含计数和阈值。
- `sign_stellium`、`house_stellium`：同一星座或宫位达到 3 个计算点；证据包含点位、计数和阈值。
- `tight_aspect`：容许度不大于 3° 的已计算相位；证据包含相位类型、容许度和应用/离相状态。

这些信号是供后续解释规则、研究模块或 AI 输入消费的事实层，不携带褒贬或人生结论。

`calculation.precision_mode` 的取值为：

- `high`：使用项目内 `data/ephemeris/*.se1` 的 Swiss 高精度星历
- `moshier`：未找到高精度文件且显式允许降级

## 结构化分析

`POST /api/v1/astro/analysis` 接受以下两种输入之一：

完整地址：`https://zhouyilab.k8s.gold/api/v1/astro/analysis`

```json
{"chart_request": {"date": {"year": 1990, "month": 5, "day": 20}, "utc_offset_minutes": 480, "location": {"latitude": 31.2, "longitude": 121.4}}}
```

或直接传入 `/api/v1/astro/charts` 返回的 `chart` 对象。可选 `scope` 限制分区：`core_points`、`distribution`、`signals`、`aspect_network`。返回的 `analysis` 版本为 `astro-analysis/1.0`，每个分区都保留来源结构版本和信号 ID；`observations` 由 `config/astro/rules.json` 匹配生成，规则版本记录在 `rules_version`。

规则输出仍是事实代码（如 `planet_in_angular_house`、`aspect_within_orb_threshold`），不直接生成性格、吉凶或运势文案。

## 健康检查

`GET /api/v1/health`

完整地址：`https://zhouyilab.k8s.gold/api/v1/health`

除通用服务字段外，关注：

```json
{
  "astro_cli_available": true,
  "astro_ephemeris_available": true
}
```

`astro_ephemeris_available` 表示高精度 `.se1` 文件可用；为 `false` 时，
仍可在请求中显式允许 Moshier 降级。

## 错误码

| 错误码 | HTTP | 说明 |
| --- | ---: | --- |
| `INVALID_REQUEST` | 422 | 字段缺失、格式或取值范围错误 |
| `EPHEMERIS_UNAVAILABLE` | 422 | 高精度星历不可用且未允许降级 |
| `HOUSE_CALCULATION_FAILED` | 422 | 宫位计算失败 |
| `CALCULATION_FAILED` | 422 | Swiss Ephemeris 计算失败 |
| `CALCULATION_TIMEOUT` | 504 | 计算超过服务超时限制 |
| `ENGINE_UNAVAILABLE` | 500 | Astro CLI 未构建 |

## 星历和许可证

默认星历目录为 `data/ephemeris`，包含 `sepl_18.se1`、`semo_18.se1` 和
`seas_18.se1`。可通过环境变量 `ZHOUYILAB_EPHEMERIS_PATH` 指定其他目录。
Swiss Ephemeris 许可条款见 `3rdparty/swisseph/LICENSE`。
