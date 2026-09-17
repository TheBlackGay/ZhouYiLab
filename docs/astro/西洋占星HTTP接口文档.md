# 西洋占星 HTTP 接口文档

## 基本信息

- 生产 Base URL：`https://zhouyilab.k8s.gold`
- 内网直连 Base URL：`http://192.168.31.183:8768`
- 本地开发 Base URL：`http://127.0.0.1:8768`
- Content-Type：`application/json`
- 当前生产域名由 HTTPS 反向代理转发至应用容器；调用方优先使用生产 Base URL，不要依赖容器端口。
- 当前支持本命盘（`natal`）和指定时刻行运事实包（`transit`）
- 角度单位为度（°），速度单位为度/日（°/day），距离单位为 AU

所有接口使用统一响应封装：

```json
{
  "success": true,
  "data": {},
  "meta": {
    "api_version": "v1",
    "algorithm_version": "zhouyilab-astro/0.2.0",
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

## 计算指定时刻行运

`POST /api/v1/astro/transits`

行运接口只返回可复核的天文和占星结构事实，不生成生活化文案、评分或吉凶判断。请求使用两个完整的时间输入：`natal` 是本命盘，`target` 是要观察的当地时刻。`target` 缺少 `utc_offset_minutes`、`location`、`zodiac`、`ayanamsa` 或 `house_system` 时，分别继承本命盘对应字段。

请求示例：

```json
{
  "natal": {
    "date": {"year": 1990, "month": 5, "day": 20, "hour": 14},
    "utc_offset_minutes": 480,
    "location": {"latitude": 31.2304, "longitude": 121.4737},
    "zodiac": "tropical",
    "house_system": "placidus"
  },
  "target": {
    "date": {"year": 2026, "month": 9, "day": 17, "hour": 12}
  },
  "transit_points": ["sun", "moon", "mercury", "venus", "mars"],
  "natal_points": ["sun", "moon", "mercury", "venus", "mars", "ascendant"],
  "include_aspects": true,
  "allow_moshier_fallback": false
}
```

省略 `transit_points` 时默认计算太阳、月亮、水星、金星和火星；省略 `natal_points` 时默认比较本命太阳、月亮、水星、金星、火星和上升点。`natal_points` 可以包含 `ascendant`、`midheaven`、`descendant`、`imum_coeli` 四个角度；其余值必须是支持的天体点位。两个输入必须使用相同的黄道、岁差和宫制。

成功响应的 `data` 包含：

- `natal`：按 `natal_points` 计算的本命盘，保留本命宫位和输入口径；
- `transit.planets`：目标时刻的行运行星，`natal_house` 表示它落入本命盘的宫位；
- `aspects`：行运行星与本命点位的主要相位，包含相位角、偏差、入相/出相；
- `calculation`：本命和目标时刻的 Julian 日、星历来源、精度模式和警告；
- `structured`：版本为 `astro-transit-structured/1.0` 的机器可读事实包。

`structured` 不携带性格、运势、领域评分或生活化断语。后续 A2 规则层只能引用其中的点位、宫位、相位和计算证据。

## 结构化分析

`POST /api/v1/astro/analysis` 接受以下两种输入之一：

完整地址：`https://zhouyilab.k8s.gold/api/v1/astro/analysis`

```json
{"chart_request": {"date": {"year": 1990, "month": 5, "day": 20}, "utc_offset_minutes": 480, "location": {"latitude": 31.2, "longitude": 121.4}}}
```

或直接传入 `/api/v1/astro/charts` 返回的 `chart` 对象。可选 `scope` 限制分区：`core_points`、`distribution`、`signals`、`aspect_network`。返回的 `analysis` 版本为 `astro-analysis/1.0`，每个分区都保留来源结构版本和信号 ID；`observations` 由 `config/astro/rules.json` 匹配生成，规则版本记录在 `rules_version`。

规则输出仍是事实代码（如 `planet_in_angular_house`、`aspect_within_orb_threshold`），不直接生成性格、吉凶或运势文案。

## 行运生活领域信号分析

`POST /api/v1/astro/transit-analysis` 将 A1 的行运事实包映射为可追溯的生活领域信号。请求可以直接传入 `/api/v1/astro/transits` 返回的 `chart`，也可以传入 `transit_request`，由服务先调用行运计算。

```json
{
  "transit_request": {
    "natal": {
      "date": {"year": 1990, "month": 5, "day": 20, "hour": 14},
      "utc_offset_minutes": 480,
      "location": {"latitude": 31.2304, "longitude": 121.4737}
    },
    "target": {"date": {"year": 2026, "month": 9, "day": 17, "hour": 12}},
    "include_aspects": true
  },
  "dimensions": ["love", "career"]
}
```

`scope` 与 `dimensions` 都可以限定 `love`、`wealth`、`career`、`learning`、`social`，两者只能提供一个。也可以把整个行运响应作为 `chart` 传入：

```json
{
  "chart": {
    "chart_type": "transit",
    "structured": {
      "schema_version": "astro-transit-structured/1.0",
      "natal": {"schema_version": "astro-structured/1.0"}
    },
    "transit": {"planets": [{"id": "venus", "natal_house": 2}]},
    "aspects": []
  }
}
```

返回的 `data` 版本为 `astro-transit-analysis/1.0`，包括 `dimensions` 领域索引、扁平 `signals` 数组、`astro-transit-rules/1.0` 规则版本和 `source_schema_versions`。每个信号包含 `signal_id`、`rule_id`、`revision`、`dimension`、`direction`、`intensity`、`observation_code`、`point_ids`、A1 事实 `evidence` 和 `boundary`。

规则配置位于 `config/astro/transit_rules.json`，当前只支持 `transit_planet_in_natal_house` 和 `transit_aspect_to_natal_point`。该接口只输出事实到领域的映射，不生成摘要、建议、避免事项、幸运信息、领域评分或确定性事件判断；财富信号不提供投资、借贷或金额建议。

## 日运解析包

`POST /api/v1/astro/daily-reading` 将 A2 生活领域信号渲染为不带评分的日运解析包。可以直接传入 A2 返回的 `analysis`，也可以传入 A1 的 `chart` 或 `transit_request`，由服务依次完成行运计算、规则匹配和模板渲染。

```json
{
  "transit_request": {
    "natal": {
      "date": {"year": 1990, "month": 5, "day": 20, "hour": 14},
      "utc_offset_minutes": 480,
      "location": {"latitude": 31.2304, "longitude": 121.4737}
    },
    "target": {"date": {"year": 2026, "month": 9, "day": 17, "hour": 12}},
    "include_aspects": true
  },
  "dimensions": ["love", "career"]
}
```

当前只支持 `day` 范围；省略 `period` 时默认为 `day`。`scope` 可以传入 `day` 作为范围，也可以沿用 A2 的生活领域数组；`dimensions` 用于限定返回前参与渲染的领域。输出的 `data` 版本为 `astro-daily-reading/1.0`，模板版本为 `astro-daily-templates/1.0`。

输出包含 `overall`、`dimensions`、`summary`、`focus`、`actions`、`avoid`、`lucky` 和 `evidence`。所有领域的 `index` 和总体 `overall.index` 在 A3 固定为 `null`；`lucky` 为空对象，待后续规则校准后再启用。每个领域卡片、重点提醒和证据项都保留 `signal_ids`，顶层 `evidence` 继续携带 A2 的 `rule_id`、点位、事实证据和边界。

模板配置位于 `config/astro/daily_reading_templates.json`。缺少对应规则模板、日期格式无效或分析包版本不匹配时，接口返回 `INVALID_REQUEST`；日运解析不会补写没有命中规则的生活领域结论。

## 本命布局分析包

`POST /api/v1/astro/natal-analysis` 把 `/api/v1/astro/charts` 返回的本命盘读成「黄道与宫位布局」的结构事实，不新增排盘计算、不修改 C++ 排盘核心。可以传入完整的 `chart`，也可以用 `chart_request` 让服务先排盘。可选 `ruler_system` 取 `modern`（默认）或 `traditional`。

```json
{
  "chart_request": {
    "date": {"year": 1990, "month": 5, "day": 20, "hour": 14},
    "utc_offset_minutes": 480,
    "location": {"latitude": 31.2304, "longitude": 121.4737},
    "include_aspects": true
  },
  "ruler_system": "modern"
}
```

输出的 `data` 版本为 `astro-natal-analysis/1.0`，规则版本为 `astro-natal-rules/1.0`，分三块：

- `layout`：描述性统计，与规则配置解耦（规则为空时也必须完整可用）。包含 `core`（上升、中天、太阳、月亮、命主星）、`hemispheres`、`quadrants`、`sign_occupancy`、`house_occupancy`（含 `empty_houses`）、`elements`、`modalities` 和 `aspect_network`。`hemispheres` 显式回传 `definition`（统计口径）、`counted_point_ids`、`counted_point_names`、`counted_total` 和 `missing_point_ids`。
- `facts`：由 `layout` 与 `structured.derived_signals` 生成的原始信号，每项含 `signal_id`、`type`、`point_ids`、`point_names` 和 `evidence`。信号类型包括 `angle_in_sign`、`point_in_sign`、`point_in_house`、`house_cusp_sign`、`house_ruler_placement`、`chart_ruler_placement`、`hemisphere_stat`、`quadrant_stat`、`sign_occupancy_stat`、`empty_house`、`aspect_network_stat`，以及排盘已有的 `angular_planet`、`retrograde_point`、`element_emphasis`、`modality_emphasis`、`sign_stellium`、`house_stellium`、`tight_aspect`。
- `signals`：`config/astro/natal_rules.json` 命中的规则，每项含 `rule_id`、`revision`、`signal_id`、`signal_type`、`observation_code`、`dimension`、`point_ids`、`evidence` 和 `boundary`；规则可用 `match`、`min_count`、`min_ratio` 做阈值判定。
- `uncovered`：没有命中任何规则的信号，显式列出而不是静默丢弃。

统计口径：半球、象限、星座与宫位占据只统计十大行星（太阳、月亮、水星、金星、火星、木星、土星、天王星、海王星、冥王星）中落宫有效的点位；真交点、凯龙等虚点仍出现在逐点位信号里，但不参与分布统计。相位网络统计 `structured.aspects` 中已计算的全部主要相位，顺畅指拱相与六合，张力指刑相与对冲。所有输出都不含吉凶、评分或人生结论。

## 本命布局解析包

`POST /api/v1/astro/natal-reading` 把布局分析与规则命中渲染成可读的布局速读。可以直接传入 `/natal-analysis` 返回的 `analysis`，也可以传入 `chart` 或 `chart_request`，由服务依次完成排盘、布局分析和模板渲染。

```json
{
  "chart_request": {
    "date": {"year": 1990, "month": 5, "day": 20, "hour": 14},
    "utc_offset_minutes": 480,
    "location": {"latitude": 31.2304, "longitude": 121.4737},
    "include_aspects": true
  },
  "ruler_system": "traditional"
}
```

输出的 `data` 版本为 `astro-natal-reading/1.0`，模板版本为 `astro-natal-templates/1.0`，包含：

- `highlights`：上升、太阳、月亮、命主星四张核心卡，含 `title`、`summary`、`signal_ids`；
- `layout`：布局速读条目，每条含 `rule_id`、`revision`、`text`、`count`/`total`、`point_ids`、`signal_ids`、`evidence` 和 `boundary`（`core` 维度由 `highlights` 承载，不重复成条目）；
- `layout_stats`：`/natal-analysis` 的 `layout` 原样回传，供页面画分布条与「统计口径」折叠区；
- `distribution`：元素与模式计数，以及命中的强调信号 ID；
- `coverage`：`facts`、`matched`、`rendered`、`layout_lines`、`points`、`houses`、`aspects`、`uncovered` 计数；
- `boundaries`、`uncovered`、`versions`。

卡片结构：

- `points`：逐点位卡片，每个点位一张，由 `planet_core × sign_style × house_field` 组合而成。每张卡片带 `title`（如「太阳 · 金牛座 · 第9宫」）、`summary`（唯一句式拼装）、`blocks`（每段含 `slot`、`rule_id`、`revision`、`text`）、`markers`（来自派生信号的重点连接）、`signal_ids` 和 `evidence`（黄经、座内度数、宫头、宫制）；`retrograde` 标记逆行，`overrides` 列出被精修替换的槽位。
- `houses`：十二宫卡片，含宫头星座、`point_ids`（宫内点位）、`virtual_point_ids`（其中的虚点）、`empty_of_planets`（是否无十大行星）、`ruler`（宫主星及其落点）与 `house_ruler` / `house_field` 文案块。空宫、只有虚点的宫、行星与虚点同宫三种情况使用不同句式，不会把「没有十大行星」说成「宫内什么都没有」。
- `aspects`：按容许度升序排列的相位卡片，含 `label`、`tone`（`harmony` / `tension` / `merge` / `adjust`）、`orb`、`phase_label`（入相 / 出相）、`tight`（容许度不大于 3°）与 `blocks`。只描述顺畅 / 张力，不出现吉凶分类。

模板配置位于 `config/astro/natal_reading_templates.json`，覆盖 `planet_core`、`sign_style`、`house_field`、`aspect_style`、`ascendant_sign`、`sun_sign`、`moon_sign`、`house_ruler`、`summary` 与 `overrides`。`load_templates` 会校验槽位是否覆盖全部点位、十二星座、十二宫与六种相位，以及模板里的占位符是否在白名单内；缺槽位或未知占位符直接返回 `ANALYSIS_CONFIG_ERROR`。`overrides` 支持三种精修粒度：`point_sign`（星体 × 座）、`point_house`（星体 × 宫）、`point_sign_house`（整段替换星座与宫位两段），未精修的条目继续走组合式。缺失模板时进入 `uncovered`，不用大模型补写。

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
