# ZhouYiLab 紫微斗数 HTTP API

> API 版本：`v1`
> 文档版本：`1.3.0`
> 更新日期：`2026-08-31`
> 字符编码：UTF-8
> 当前服务：本地 Python HTTP 适配层 + C++ 紫微斗数计算核心

## 1. 接口范围

当前 API 提供以下能力：

| 能力 | 方法 | 路径 | 状态 |
|---|---|---|---|
| 服务健康检查 | `GET` | `/api/v1/health` | 已实现 |
| 紫微能力元数据 | `GET` | `/api/v1/ziwei/meta` | 已实现 |
| 出生真太阳时校正 | `POST` | `/api/v1/ziwei/time-correction` | 已实现 |
| 本命盘计算 | `POST` | `/api/v1/ziwei/charts` | 已实现 |
| 运限计算 | `POST` | `/api/v1/ziwei/fortune` | 已实现 |
| 本命十二宫结构化解读 | `POST` | `/api/v1/ziwei/analysis` | 已实现 |

本命盘、真太阳时、运限和本命结构化解读已经通过接口提供。命盘解读必须遵守[紫微斗数命盘与运限分析准则](./紫微斗数命盘与运限分析准则.md)。`1.3.0` 的解读接口只开放本命层，大限和流年结构化解读完成前不得返回占位性结果。

## 2. 基本约定

### 2.1 基础地址

本地开发环境：

```text
http://127.0.0.1:8765
```

所有正式业务接口使用 `/api/v1` 前缀。新增不兼容字段或语义时必须发布新的主版本路径，不能静默修改 `v1`。

### 2.2 请求格式

`POST` 请求必须使用：

```http
Content-Type: application/json
```

请求体最大为 64 KiB。日期时间按数值字段提交，不依赖客户端的字符串解析或系统时区。

### 2.3 时间语义

- `birth` 表示出生证明或用户记录的当地钟表时间。
- `time_correction` 只校正出生时间，用于本命时辰、身宫和斗君起点。
- `target` 表示需要计算运限的目标时间，不进行真太阳时校正。
- 当前服务不存储用户时区，调用方必须确保提交的数值时间已经符合业务采用的历法时区。
- 中国大陆场景通常采用 `Asia/Shanghai` 和东经 120 度标准经线。

### 2.4 统一成功响应

```json
{
  "success": true,
  "data": {},
  "meta": {
    "api_version": "v1",
    "algorithm_version": "zhouyilab-core/1.3.0",
    "request_id": "b416827b90274e5c837d1ef12f39e776"
  }
}
```

### 2.5 统一错误响应

```json
{
  "success": false,
  "error": {
    "code": "INVALID_ARGUMENT",
    "message": "birth.gender 必须是 male 或 female"
  },
  "meta": {
    "api_version": "v1",
    "algorithm_version": "zhouyilab-core/1.3.0",
    "request_id": "e2481168ad76405995b163e0a758fe2d"
  }
}
```

客户端判断请求结果时必须同时检查 HTTP 状态码与 `success`，不要依赖中文错误文案。

## 3. 公共数据结构

### 3.1 Birth 出生时间

| 字段 | 类型 | 必填 | 约束 | 说明 |
|---|---|---|---|---|
| `year` | integer | 是 | 合法公历年份 | 出生年 |
| `month` | integer | 是 | `1..12` | 出生月 |
| `day` | integer | 是 | 合法公历日期 | 出生日 |
| `hour` | integer | 否 | `0..23`，默认 `0` | 出生小时 |
| `minute` | integer | 否 | `0..59`，默认 `0` | 出生分钟 |
| `second` | integer | 否 | `0..59`，默认 `0` | 出生秒 |
| `gender` | string | 排盘时是 | `male`、`female` | 性别；单独校时时可省略 |

### 3.2 TimeCorrection 出生时间校正

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `mode` | string | 否 | `standard_time` | `standard_time` 或 `true_solar_time` |
| `longitude` | number | 否 | `120.0` | 出生地经度，东经为正，范围 `-180..180` |
| `standard_meridian` | number | 否 | `120.0` | 钟表时间采用的标准经线 |
| `daylight_saving_minutes` | integer | 否 | `0` | 需要先扣除的夏令时分钟，范围 `0..180` |

开启真太阳时后的计算关系：

```text
标准时间 = 记录时间 - 夏令时
真太阳时 = 标准时间 + 经度时差 + 均时差
```

### 3.3 Target 运限目标时间

| 字段 | 类型 | 必填 | 约束 | 说明 |
|---|---|---|---|---|
| `year` | integer | 是 | 合法公历年份 | 目标年 |
| `month` | integer | 是 | `1..12` | 目标月 |
| `day` | integer | 是 | 合法公历日期 | 目标日 |
| `hour` | integer | 否 | `0..23`，默认 `0` | 目标小时 |
| `minute` | integer | 否 | `0..59`，默认 `0` | 目标分钟 |
| `second` | integer | 否 | `0..59`，默认 `0` | 目标秒 |
| `age` | integer | 否 | `1..150` | 虚岁；默认 `目标年 - 出生年 + 1` |
| `layers` | string[] | 否 | 不能为空 | 需要返回的运限层；默认返回全部 |

`layers` 支持：

| API 值 | 响应字段 | 说明 |
|---|---|---|
| `decade` | `da_xian` | 当前十年大限 |
| `minor` | `xiao_xian` | 当前虚岁小限 |
| `annual` | `liu_nian` | 流年 |
| `monthly` | `liu_yue` | 流月与流年斗君 |
| `daily` | `liu_ri` | 流日 |
| `hourly` | `liu_shi` | 流时 |

计算日、时层级时，服务端会自动完成流年、流月等依赖计算，但响应只返回 `layers` 明确请求的层级。

## 4. 健康检查

### `GET /api/v1/health`

用于部署探针和客户端连接诊断。

响应示例：

```json
{
  "success": true,
  "data": {
    "status": "ok",
    "service": "zhouyilab-ziwei-api",
    "cli_available": true
  },
  "meta": {
    "api_version": "v1",
    "algorithm_version": "zhouyilab-core/1.3.0",
    "request_id": "..."
  }
}
```

## 5. 能力元数据

### `GET /api/v1/ziwei/meta`

返回客户端可用的枚举和计算能力。App 应优先读取此接口，不要在多个客户端重复维护枚举。

响应中的 `data`：

```json
{
  "api_version": "v1",
  "algorithm_version": "zhouyilab-core/1.3.0",
  "capabilities": [
    "natal_chart",
    "true_solar_time",
    "decade",
    "minor",
    "annual",
    "monthly",
    "daily",
    "hourly",
    "fortune_transit_stars",
    "natal_shen_sha",
    "natal_analysis_fragments"
  ],
  "genders": ["male", "female"],
  "time_correction_modes": ["standard_time", "true_solar_time"],
  "fortune_layers": ["decade", "minor", "annual", "monthly", "daily", "hourly"],
  "analysis_layers": ["natal"],
  "analysis_input_modes": ["chart_request", "chart"]
}
```

## 6. 真太阳时校正

### `POST /api/v1/ziwei/time-correction`

只进行出生时间校正，不生成命盘。适用于出生资料编辑页的即时预览。

请求：

```json
{
  "birth": {
    "year": 1994,
    "month": 12,
    "day": 8,
    "hour": 9,
    "minute": 5,
    "second": 0
  },
  "time_correction": {
    "mode": "true_solar_time",
    "longitude": 120.3,
    "standard_meridian": 120.0,
    "daylight_saving_minutes": 0
  }
}
```

响应中的 `data`：

```json
{
  "mode": "true_solar_time",
  "recorded_time": "1994-12-08 09:05:00",
  "standard_time": "1994-12-08 09:05:00",
  "chart_time": "1994-12-08 09:14:14",
  "longitude": 120.3,
  "standard_meridian": 120.0,
  "daylight_saving_minutes": 0,
  "longitude_offset_seconds": 72,
  "equation_of_time_seconds": 482,
  "total_offset_seconds": 554,
  "crossed_date_boundary": false
}
```

## 7. 本命盘计算

### `POST /api/v1/ziwei/charts`

生成完整本命盘数据，不计算指定日期运限。

请求：

```json
{
  "birth": {
    "year": 1994,
    "month": 12,
    "day": 8,
    "hour": 9,
    "minute": 5,
    "second": 0,
    "gender": "male"
  },
  "time_correction": {
    "mode": "true_solar_time",
    "longitude": 120.3,
    "standard_meridian": 120.0,
    "daylight_saving_minutes": 0
  }
}
```

响应中的 `data` 为命盘对象，主要字段如下：

| 字段 | 类型 | 说明 |
|---|---|---|
| `solar_date` | string | 排盘使用的阳历日期 |
| `lunar_date` | string | 农历日期 |
| `lunar_hour` | string | 农历时辰 |
| `gender` | string | `男` 或 `女`，属于展示值 |
| `birth_time` | object | 完整出生时间校正明细 |
| `si_zhu` | object | 年、月、日、时四柱 |
| `wu_xing_ju` | string | 五行局 |
| `ming_gong_index` | integer | 命宫索引，以寅宫为 `0` |
| `shen_gong_index` | integer | 身宫索引，以寅宫为 `0` |
| `palaces` | array | 十二宫数据，固定 12 项 |
| `ge_ju` | object | 当前 C++ 格局分析结果 |
| `si_hua` | object | 宫干四化和自化数据 |
| `da_xian` | array | 十二个大限区间 |

### 7.1 Palace 宫位对象

| 字段 | 类型 | 说明 |
|---|---|---|
| `name` | string | 本命功能宫名称 |
| `gan_zhi` | string | 宫干支 |
| `is_ming_palace` | boolean | 是否命宫 |
| `is_body_palace` | boolean | 是否身宫 |
| `zhu_xing` | Star[] | 主星及亮度、四化 |
| `fu_xing` | string[] | 兼容字段，仅星名 |
| `fu_xing_detail` | Star[] | 辅星明细 |
| `sha_xing` | string[] | 兼容字段，仅星名 |
| `sha_xing_detail` | Star[] | 煞星明细 |
| `za_yao` | string[] | 兼容字段，仅星名 |
| `za_yao_detail` | Star[] | 杂曜明细 |
| `shen_sha` | ShenSha | 长生、博士、岁前、将前四套十二神在本宫的值 |

`ShenSha` 对象包含 `chang_sheng_12`、`bo_shi_12`、`sui_qian_12`、`jiang_qian_12` 四个可选字符串字段。分类字段必须保留，不能因为“小耗、大耗、病符”等名称与其他星曜重复而合并。

### 7.2 Star 星曜对象

```json
{
  "name": "武曲",
  "liang_du": "利",
  "si_hua": "化科"
}
```

`si_hua` 与 `liang_du` 均为可选字段。`liang_du` 来自版本化星曜亮度表，可能值为 `庙、旺、得、利、平、陷、不`；配置为空白或 `-` 时不返回该字段，也不参与结构化解读。

## 8. 运限计算

### `POST /api/v1/ziwei/fortune`

以出生资料和目标时间计算本命盘及指定运限层。接口为无状态计算，不依赖服务端保存的用户或命盘 ID。

请求全部层级：

```json
{
  "birth": {
    "year": 1994,
    "month": 12,
    "day": 8,
    "hour": 9,
    "minute": 5,
    "second": 0,
    "gender": "male"
  },
  "time_correction": {
    "mode": "true_solar_time",
    "longitude": 120.3,
    "standard_meridian": 120.0,
    "daylight_saving_minutes": 0
  },
  "target": {
    "year": 2026,
    "month": 8,
    "day": 24,
    "hour": 15,
    "minute": 5,
    "second": 0,
    "age": 33,
    "layers": ["decade", "minor", "annual", "monthly", "daily", "hourly"]
  }
}
```

只请求流年和流月：

```json
{
  "birth": {
    "year": 1994,
    "month": 12,
    "day": 8,
    "hour": 9,
    "minute": 5,
    "gender": "male"
  },
  "time_correction": {
    "mode": "true_solar_time",
    "longitude": 120.3
  },
  "target": {
    "year": 2026,
    "month": 8,
    "day": 24,
    "hour": 15,
    "minute": 5,
    "layers": ["annual", "monthly"]
  }
}
```

响应中的 `data`：

```json
{
  "chart": {
    "solar_date": "1994年12月8日",
    "palaces": []
  },
  "target": {
    "solar_time": "2026年8月24日 15:05:00",
    "lunar_date": "农历丙午年七月十二",
    "lunar_month": 7,
    "lunar_day": 12,
    "age": 33,
    "requested_layers": ["annual", "monthly"]
  },
  "fortune": {
    "liu_nian": {
      "gan_zhi": "丙午",
      "palace_index": 4,
      "palace": "兄弟宫",
      "si_hua": [
        {"type": "禄", "star": "天同"},
        {"type": "权", "star": "天机"},
        {"type": "科", "star": "文昌"},
        {"type": "忌", "star": "廉贞"}
      ],
      "transit_stars": [
        {
          "name": "天喜",
          "display_name": "年喜",
          "palace_index": 10,
          "palace": "奴仆宫",
          "liang_du": "旺"
        }
      ]
    },
    "liu_yue": {
      "gan_zhi": "丙申",
      "palace_index": 5,
      "palace": "命宫",
      "dou_jun_index": 11,
      "dou_jun_palace": "迁移宫",
      "si_hua": []
    }
  }
}
```

`fortune` 只包含请求的层级。客户端必须按字段是否存在进行渲染，不能假设六层始终全部返回。

除小限外，各层的 `transit_stars` 返回魁、钺、昌、曲、禄、羊、陀、马、鸾、喜十类流曜；流年另含年解。`name` 是标准星名，`display_name` 是层级简称：大限使用“大”前缀，流年、流月、流日、流时分别使用“年、月、日、时”，例如天喜显示为“大喜、年喜、月喜、日喜、时喜”。`liang_du` 按实际落宫从亮度配置补充，无资料时省略。

## 9. 状态码与错误码

| HTTP 状态 | 错误码 | 场景 |
|---:|---|---|
| `400` | `INVALID_REQUEST` | Content-Type、JSON 结构或基础请求格式错误 |
| `404` | `ENDPOINT_NOT_FOUND` | 接口路径不存在 |
| `422` | `INVALID_JSON` | C++ 桥接无法解析请求 JSON |
| `422` | `INVALID_ARGUMENT` | 日期、性别、经度、层级或虚岁不合法 |
| `500` | `CALCULATION_FAILED` | 排盘核心计算失败 |
| `500` | `INVALID_ENGINE_RESPONSE` | C++ 计算核心返回非 JSON 内容 |
| `500` | `INTERNAL_ERROR` | HTTP 适配层未知错误 |
| `504` | `CALCULATION_TIMEOUT` | C++ 计算超过 20 秒 |

客户端可以将 `request_id` 提供给服务端日志查询，但不应向最终用户展示内部错误详情。

## 10. CORS 与部署

当前本地开发服务返回：

```http
Access-Control-Allow-Origin: *
```

这便于独立前端和移动端调试。正式部署如接入用户账号、保存出生资料或使用 Cookie，必须改成允许名单，不得继续使用通配来源。

当前 Python 服务是开发适配层。正式部署可以保留 `/api/v1` 契约，把内部执行方式替换成常驻 C++ 服务、动态库或独立计算微服务，客户端不需要随之改变。

## 11. 旧接口迁移

旧页面接口：

```text
POST /api/calculate
```

目前仍保留兼容，但属于废弃接口，不再增加新字段。新客户端必须使用 `/api/v1/ziwei/fortune`。

主要变化：

| 旧字段 | 新字段 |
|---|---|
| `gender` | `birth.gender` |
| `options.trueSolarTime` | `time_correction.mode` |
| `options.standardMeridian` | `time_correction.standard_meridian` |
| `options.daylightSavingMinutes` | `time_correction.daylight_saving_minutes` |
| `age` | `target.age` |
| 固定返回全部层级 | `target.layers` 按需返回 |
| 裸数据或字符串错误 | `success/data/error/meta` 统一包络 |

## 12. 本命结构化解读

### `POST /api/v1/ziwei/analysis`

将本命盘事实、宫位象义、星曜象义、三方四正、四化及命中的静态规则输出为可追溯分析碎片。接口不生成最终命理文章，返回的碎片用于页面校验和后续 AI 场景化表达。

可以使用 `chart_request` 让服务端即时排盘：

```json
{
  "chart_request": {
    "birth": {
      "year": 1994,
      "month": 12,
      "day": 8,
      "hour": 9,
      "minute": 5,
      "gender": "male"
    },
    "time_correction": {
      "mode": "standard_time"
    }
  },
  "scope": {
    "layers": ["natal"],
    "focus_palaces": ["父母宫"],
    "scenarios": ["职场"]
  }
}
```

也可以将 `/api/v1/ziwei/charts` 返回的命盘对象放入 `chart` 字段。`chart` 与 `chart_request` 必须且只能提供一个。

`scope` 字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `layers` | string[] | 否 | `1.3.0` 只支持 `["natal"]` |
| `focus_palaces` | string[] | 否 | 指定需要分析的宫位；默认分析十二宫 |
| `scenarios` | string[] | 否 | 按配置中的中文场景精确筛选衍生定义；省略时返回全部候选场景 |

响应中的 `data`：

```json
{
  "chart": {},
  "analysis": {
    "analysis_version": "1.3.0",
    "layer": "natal",
    "scope": {},
    "config": {},
    "fragment_contract": {},
    "palaces": [],
    "fragments": [],
    "ai_packet": {},
    "ai_context": {}
  }
}
```

分析碎片示例：

```json
{
  "fragment_id": "natal.parents.star_in_palace.self.lingxing.6",
  "type": "star_in_palace",
  "source_layer": "natal",
  "effect_palace": "父母宫",
  "effect_subject": ["哺育与保护来源", "直接权威", "认可与文书", "上层传递"],
  "facts": {
    "focus_palace": "父母宫",
    "physical_palace": "父母宫",
    "relation": "self",
    "star": "铃星",
    "brightness": "平",
    "transformation": null
  },
  "palace_original_meanings": [],
  "star_original_meanings": [],
  "star_derived_meanings": [],
  "modifiers": [],
  "evidence": [],
  "confidence": {
    "level": "baseline",
    "reason": "命盘事实与宫位、星曜象义均可追溯"
  }
}
```

碎片类型：

| 类型 | 说明 |
|---|---|
| `palace_symbolism` | 焦点宫的原始定义和场景衍生 |
| `star_in_palace` | 星曜实际坐入焦点宫 |
| `four_directions` | 星曜从三合宫或对宫作用于焦点宫，保留实际落宫 |
| `transformation` | 本命四化修正，不改变实际落宫和归属宫位 |
| `combination` | 命中静态配置中的星曜组合 |
| `pattern` | 命中静态配置中的宫位规则或格局 |
| `shen_sha_in_palace` | 当前宫的十二神辅助信号，保留长生、博士、岁前、将前系统身份 |
| `unconfigured_star` | 仅保留盘面事实，因静态象义未校订而不进入推理结论 |

每个 `palaces[]` 同时返回以下结构化字段：

| 字段 | 说明 |
|---|---|
| `sections.palace_symbolism` | 宫位原始定义碎片 ID |
| `sections.self_stars` | 本宫星曜碎片 ID |
| `sections.triad_stars` | 两个三合宫星曜碎片 ID |
| `sections.opposite_stars` | 对宫星曜碎片 ID |
| `sections.transformations` | 独立四化修正碎片 ID；星曜碎片只通过 `related_fragment_ids` 引用，不重复计权 |
| `sections.patterns` | 同宫组合、格局和宫位规则碎片 ID |
| `sections.shen_sha` | 四套十二神碎片 ID |
| `sections.unconfigured` | 未配置星曜事实碎片 ID |
| `signal_summary` | 确定性的核心、辅助、张力信号 ID 及配置覆盖情况 |

`ai_packet` 是给后续 AI 场景化表达使用的最小输入包。它只引用有效碎片 ID，并明确允许归纳、连接场景和简化语言；禁止重新排盘、改变宫位归属、合并不同十二神系统或发明格局。

接口保证：

1. 本命层按焦点宫分别完成十二宫、三方四正和已配置规则分析。
2. 每条事实携带 `source_layer`。
3. 三方四正星曜保留 `physical_palace` 和 `relation`，不能伪装成本宫坐星。
4. 每个格局携带 `effect_palace` 和 `effect_subject`。
5. 返回命中的配置 ID、版本和证据，不能只返回自然语言。
6. `ai_packet` 和 `ai_context` 明确 AI 只能归纳和改写，不得重新排盘或发明格局。
7. 四化只由独立 `transformation` 碎片承担修正权重，星曜碎片不得重复携带四化 modifier。
8. 十二神按四套系统独立解析，同名的博士大耗与岁前大耗不能合并。

当前第 1 条只完成本命层。请求 `decade`、`annual` 等未开放层级时返回 `400 INVALID_REQUEST`，不会返回不完整分析。

## 13. cURL 示例

健康检查：

```bash
curl -sS http://127.0.0.1:8765/api/v1/health
```

本命盘：

```bash
curl -sS \
  -H 'Content-Type: application/json' \
  -d '{
    "birth": {
      "year": 1994,
      "month": 12,
      "day": 8,
      "hour": 9,
      "minute": 5,
      "gender": "male"
    },
    "time_correction": {
      "mode": "true_solar_time",
      "longitude": 120.3
    }
  }' \
  http://127.0.0.1:8765/api/v1/ziwei/charts
```

流年、流月：

```bash
curl -sS \
  -H 'Content-Type: application/json' \
  -d '{
    "birth": {
      "year": 1994,
      "month": 12,
      "day": 8,
      "hour": 9,
      "minute": 5,
      "gender": "male"
    },
    "time_correction": {
      "mode": "true_solar_time",
      "longitude": 120.3
    },
    "target": {
      "year": 2026,
      "month": 8,
      "day": 24,
      "hour": 15,
      "minute": 5,
      "layers": ["annual", "monthly"]
    }
  }' \
  http://127.0.0.1:8765/api/v1/ziwei/fortune
```
