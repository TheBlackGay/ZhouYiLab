# ZhouYiLab 紫微斗数 HTTP API

> API 版本：`v1`
> 文档版本：`1.4.1`
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
| 本地研究盲评包 | `GET` | `/api/v1/ziwei/research/blind-review/packet` | 研究工具 |
| AI 预评审元数据 | `GET` | `/api/v1/ziwei/research/ai-review/meta` | 研究工具 |
| AI 模型连接测试 | `POST` | `/api/v1/ziwei/research/ai-review/connections/test` | 研究工具 |
| AI 预评审实验 | `GET/POST` | `/api/v1/ziwei/research/ai-review/experiments` | 研究工具 |
| AI 实验进度 | `GET` | `/api/v1/ziwei/research/ai-review/experiments/{id}` | 研究工具 |
| AI 实验结果 | `GET` | `/api/v1/ziwei/research/ai-review/experiments/{id}/results` | 研究工具 |

本命盘、真太阳时、运限和本命结构化解读已经通过接口提供。命盘解读必须遵守[紫微斗数命盘与运限分析准则](./紫微斗数命盘与运限分析准则.md)。`1.4.1` 完善格局结果的页面展示；解读接口仍只开放本命层，大限和流年结构化解读完成前不得返回占位性结果。

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

请求体最大为 256 KiB。日期时间按数值字段提交，不依赖客户端的字符串解析或系统时区。

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
    "algorithm_version": "zhouyilab-core/1.4.1",
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
    "algorithm_version": "zhouyilab-core/1.4.1",
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
    "algorithm_version": "zhouyilab-core/1.4.1",
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
  "algorithm_version": "zhouyilab-core/1.4.1",
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
    "natal_analysis_fragments",
    "natal_structured_sections",
    "natal_ai_packet",
    "natal_shen_sha_analysis",
    "declarative_pattern_engine",
    "pattern_condition_trace",
    "focus_palace_pattern_attribution",
    "local_blind_review_packet",
    "ai_multi_model_review_lab"
  ],
  "genders": ["male", "female"],
  "time_correction_modes": ["standard_time", "true_solar_time"],
  "fortune_layers": ["decade", "minor", "annual", "monthly", "daily", "hourly"],
  "analysis_layers": ["natal"],
  "analysis_input_modes": ["chart_request", "chart"]
}
```

## 6. 本地研究盲评包

### `GET /api/v1/ziwei/research/blind-review/packet`

生成可复现的匿名盲评包，供本地研究页面 `/blind-review.html` 使用。该接口是研究工具，不是面向 App 用户的命盘解读接口。

查询参数：

| 字段 | 类型 | 必填 | 默认值 | 约束 |
|---|---|---|---|---|
| `seed` | string | 否 | `pilot-2026` | 1-128 个字符；同版本配置与同种子必须生成相同包 |

请求示例：

```http
GET /api/v1/ziwei/research/blind-review/packet?seed=pilot-2026
```

响应中的 `data` 包含：

- `packet_id`：包版本与种子的稳定指纹。
- `dimensions`：冻结的研究维度及定义。
- `cases`：随机化后的匿名案例与可见事实。
- `submission_template`：评分提交模板。

默认响应绝不包含 `answer_key`、原始实验案例 ID、预期结果或格局名称。带答案映射的包只能由研究负责人在命令行离线生成，HTTP 接口不提供该能力。

### AI 多模型预评审

AI 实验台位于 `/ai-review.html`，完整说明见 [AI 多模型定性预评审平台](./research/AI多模型定性预评审平台-v0.1.md)。

```http
GET  /api/v1/ziwei/research/ai-review/meta
POST /api/v1/ziwei/research/ai-review/connections/test
GET  /api/v1/ziwei/research/ai-review/experiments
POST /api/v1/ziwei/research/ai-review/experiments
GET  /api/v1/ziwei/research/ai-review/experiments/{id}
GET  /api/v1/ziwei/research/ai-review/experiments/{id}/results
POST /api/v1/ziwei/research/ai-review/experiments/{id}/cancel
```

模型连接只从 `ai_model_providers.local.json` 读取。创建实验时客户端只提交 `provider_ids` 和可选的 `temperature`、`repetitions`、`model_seed` 覆盖值，不提交服务地址或 API Key。响应和数据库不会返回或持久化 `api_key`。

AI 结果使用 `results_schema_version: "0.2.0"`。维度汇总中的主要统计字段为：

- `direction_prevalence_ratio`：所有模型-案例单元中，最常见方向所占的比例。
- `within_case_cross_model_agreement`：先合并同一模型的重复运行，再按同一案例比较不同模型，最后对案例求平均的众数一致比例。
- `unanimous_case_count` / `comparable_case_count`：完全同向案例数与可比较案例数。
- `pairwise_direction_agreement`：同一案例内，不同模型两两同向的比例。
- `cross_model_descriptive_consensus_ratio`：兼容旧客户端的别名，值等同于 `within_case_cross_model_agreement`。

这些指标均为描述性指标，不是人工专家一致性、准确率或星曜权重。只有一个模型时不能计算跨模型一致度，相关字段返回 `null`。

## 7. 真太阳时校正

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

## 8. 本命盘计算

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

### 8.1 Palace 宫位对象

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

### 8.2 Star 星曜对象

```json
{
  "name": "武曲",
  "liang_du": "利",
  "si_hua": "化科"
}
```

`si_hua` 与 `liang_du` 均为可选字段。`liang_du` 来自版本化星曜亮度表，可能值为 `庙、旺、得、利、平、陷、不`；配置为空白或 `-` 时不返回该字段，也不参与结构化解读。

## 9. 运限计算

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

## 10. 状态码与错误码

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

## 11. CORS 与部署

当前本地开发服务返回：

```http
Access-Control-Allow-Origin: *
```

这便于独立前端和移动端调试。正式部署如接入用户账号、保存出生资料或使用 Cookie，必须改成允许名单，不得继续使用通配来源。

当前 Python 服务是开发适配层。正式部署可以保留 `/api/v1` 契约，把内部执行方式替换成常驻 C++ 服务、动态库或独立计算微服务，客户端不需要随之改变。

## 12. 旧接口迁移

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

## 13. 本命结构化解读

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
    "scenarios": ["职场"],
    "pattern_inputs": {
      "pattern.ling_tan_ge": {
        "has_auspicious": true
      }
    }
  }
}
```

也可以将 `/api/v1/ziwei/charts` 返回的命盘对象放入 `chart` 字段。`chart` 与 `chart_request` 必须且只能提供一个。

`scope` 字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `layers` | string[] | 否 | `1.4.1` 只支持 `["natal"]` |
| `focus_palaces` | string[] | 否 | 指定需要分析的宫位；默认分析十二宫 |
| `scenarios` | string[] | 否 | 按配置中的中文场景精确筛选衍生定义；省略时返回全部候选场景 |
| `pattern_inputs` | object | 否 | 按格局 ID 隔离的外部布尔确认项；未知格局、非对象或非布尔值返回 `400 INVALID_REQUEST` |

`pattern_inputs` 不等同于自动判盘结果，只用于古文提到某条件但当前文本未定义可计算口径的情况。字段缺失或值为 `false` 时按未确认处理；字符串 `"true"` 不会被接受。铃贪格第一版只读取 `pattern.ling_tan_ge.has_auspicious`，系统不会自行扫描候选吉星来填充它。

火贪格的三方吉化同样采用外部确认：

```json
{
  "pattern_inputs": {
    "pattern.huo_tan_ge": {
      "has_jihua": true
    }
  }
}
```

该值只产生增益标记，不参与基础成格或羊陀劫空破格判断。

紫府朝垣格的流禄巡逢使用同样机制：

```json
{
  "pattern_inputs": {
    "pattern.zi_fu_chao_yuan_ge": {
      "has_liu_lu": true
    }
  }
}
```

响应中的 `data`：

```json
{
  "chart": {},
  "analysis": {
    "analysis_version": "1.4.1",
    "layer": "natal",
    "scope": {},
    "config": {},
    "fragment_contract": {},
    "palaces": [],
    "fragments": [],
    "pattern_engine": {},
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

格局碎片在通用字段之外还返回规则状态、条件轨迹和修正条件：

```json
{
  "fragment_id": "natal.ming.pattern.jia_gui_jia_lu.flanking",
  "type": "pattern",
  "source_layer": "natal",
  "effect_palace": "命宫",
  "effect_subject": ["盘主自身"],
  "facts": {
    "rule_id": "pattern.jia_gui_jia_lu.flanking",
    "rule_name": "夹贵夹禄格",
    "status": "formed",
    "base_status": "formed",
    "focus_palace": "命宫",
    "matched_variant_count": 2,
    "matched_variants": [
      {"id": "bing_ding_ren_gui_chen_xu_kui_yue", "name": "子型1：丙丁壬癸-辰戌-魁钺夹贵"},
      {"id": "ke_quan_lu_flank", "name": "子型3：科权禄夹命或身"}
    ],
    "target": {"functional_palace": "命宫", "roles": ["ming"], "branch": "辰", "index": 2},
    "adjacent_palaces": {
      "left": {"name": "兄弟宫", "branch": "卯", "index": 1},
      "right": {"name": "父母宫", "branch": "巳", "index": 3}
    },
    "transformation_distribution": {
      "left": [{"star": "廉贞", "transformation": "化禄", "physical_palace": "兄弟宫"}],
      "right": [{"star": "破军", "transformation": "化权", "physical_palace": "父母宫"}]
    },
    "lu_cun_positions": [],
    "star_positions": [],
    "malefic_notes": {"target": [], "adjacent": [], "four_directions": []},
    "rule_notes": [],
    "status_message": null,
    "textual_variants": [{"original": "廉贞化禄居限", "normalized": "廉贞化禄居亥"}]
  },
  "condition_trace": {
    "required": {"logic": "all", "matched": true, "children": []},
    "tendency": null,
    "matched_conditions": [],
    "missing_conditions": [],
    "observations": [],
    "matched_observations": []
  },
  "modifiers": {
    "enhancers": [],
    "weakeners": [],
    "breakers": []
  },
  "evidence": [{
    "source": "pattern_catalog",
    "path": "config/ziwei/patterns/jia_gui_jia_lu.json",
    "rule_id": "pattern.jia_gui_jia_lu.flanking",
    "rule_revision": 2
  }]
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
| `pattern` | 命中 `config/ziwei/patterns/` 中的声明式格局规则 |
| `pattern_observation` | 普通宫位出现与某格局相似的夹辅现象；只作备注，不代表成格，也不计入格局数量 |
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
| `sections.palace_rules` | 空宫借对宫及 `pattern_observation` 等观察碎片 ID，不计入格局数量 |
| `sections.combinations` | 星曜组合碎片 ID |
| `sections.patterns` | 声明式格局引擎命中的格局碎片 ID |
| `sections.shen_sha` | 四套十二神碎片 ID |
| `sections.unconfigured` | 未配置星曜事实碎片 ID |
| `signal_summary` | 确定性的核心、辅助、张力信号 ID 及配置覆盖情况 |

`ai_packet` 是给后续 AI 场景化表达使用的最小输入包。它只引用有效碎片 ID，并明确允许归纳、连接场景和简化语言；禁止重新排盘、改变宫位归属、合并不同十二神系统或发明格局。

接口保证：

1. 本命层按焦点宫分别完成十二宫、三方四正和已配置规则分析。
2. 每条事实携带 `source_layer`。
3. 三方四正星曜保留 `physical_palace` 和 `relation`，不能伪装成本宫坐星。
4. 每个格局携带 `effect_palace` 和 `effect_subject`；具体适用宫位服从规则原文。`夹贵夹禄格` 只允许命宫、身宫成格，其他宫位的相同结构只返回观察碎片。
5. 返回命中的配置 ID、版本和证据，不能只返回自然语言。
6. `ai_packet` 和 `ai_context` 明确 AI 只能归纳和改写，不得重新排盘或发明格局。
7. 四化只由独立 `transformation` 碎片承担修正权重，星曜碎片不得重复携带四化 modifier。
8. 十二神按四套系统独立解析，同名的博士大耗与岁前大耗不能合并。
9. 格局只在同一盘层、同一焦点宫上下文中匹配，不得把本命、大限、流年的星曜或四化拼成一个格局。
10. `pattern_engine` 明确声明配置引擎是结构化分析的权威来源；旧 C++ `chart.ge_ju` 仅兼容返回，不参与结构化结论。
11. 多变体格局通过 `facts.matched_variant_count` 和 `facts.matched_variants` 返回实际命中的严格变体，不要求调用方解析条件树。
12. `夹贵夹禄格` revision 2 严格包含三个可同时命中的子型；煞曜和亮度不参与成格判断，煞曜仅在 `facts.malefic_notes` 留痕。
13. `昌曲夹命格` revision 3 仅包含文昌文曲夹命身；`modifiers.breakers[].evidence` 返回导致破格的空劫羊铃及物理落宫。日月夹命已拆分为独立格局。
14. `雄宿乾元格` revision 1 只匹配两个已确认的真实排盘分支：廉贞七杀同坐未宫命身，或七杀坐午宫命身。`facts.star_positions` 返回廉贞、七杀实际落宫和亮度；廉贞化忌或落陷时 `facts.base_status` 仍为 `formed`，最终 `facts.status` 为 `broken`，同时由 `facts.status_message` 返回古文降级标记。A/B固定星位下廉贞落陷不可达的事实保存在 `facts.rule_notes`。
15. `七杀朝斗格` revision 1 返回 `facts.flags.has_auspicious`，表示本宫、三方或对宫是否出现任意左辅、右弼、天魁、天钺、文昌、文曲；本宫擎羊、陀罗、火星、铃星、地空、地劫任一出现时保留命中并将 `status` 标记为 `broken`。大限上下文提供 `is_auspicious_limit=true` 时返回 `facts.flags.is_auspicious_limit=true` 与“遇吉限尤美”备注。
16. `紫府同临格` revision 1 仅匹配命宫寅申紫微天府同宫；`facts.flags.has_auspicious` 表示三方或对宫是否有左右魁钺，`facts.flags.jia_bonus` 表示本命生年干是否为甲。身宫紫府同宫和其他宫位相似结构不计入该格局，煞曜只作备注。
17. `三吉加会格` revision 1 对命宫、身宫分别执行独立上下文；`facts.matched_conditions` 返回化禄、化权、化科的实体落宫证据，三化齐全且目标宫、财帛/官禄、目标三合均有覆盖才命中。允许同一物理宫同时满足多个类别，对宫四化仅备注，不触发格局。
18. `武贪百工之人（武贪格）` revision 1 返回 `facts.grade` 区分辰戌命身“上格”和丑未命宫“次格”；`facts.flags.has_auspicious` 只在本宫、三方或对宫实际见权禄左右昌曲时为 `true`。
19. `日月同临格` revision 1 仅匹配丑未命宫的对宫太阳太阴同宫；`facts.flags.bing_xin_bonus` 表示本命生年干是否为丙或辛。日月坐命或仅身宫符合不计入格局，身宫相似结构只返回观察备注。
20. `铃贪格` revision 1 仅匹配辰戌丑未子命宫贪狼铃星同宫；`facts.grade` 默认“普通”，仅子辰命宫且请求传入 `scope.pattern_inputs.pattern.ling_tan_ge.has_auspicious=true` 时为“佳”。`facts.flags.has_auspicious` 只复述该外部确认值，`facts.flags.wu_ji_bonus` 表示盘主本命出生年干是否为戊或己；本命、大限匹配均复用该出生年干。
21. `火贪格` revision 1 对辰戌丑未命宫返回“上格”，对卯宫返回“次格”。命宫或三方出现擎羊、陀罗、地劫、地空时，`facts.base_status` 保持 `formed`、`facts.status` 返回 `broken`，原始 `facts.grade` 不丢失；`facts.break_check.break_star_list` 返回实际破格星曜、物理宫位和地支。`facts.flags.has_jihua` 只复述外部 `scope.pattern_inputs["pattern.huo_tan_ge"].has_jihua`，不由程序自动扫描。
22. `紫府朝垣格` revision 1 仅匹配寅命午戌、申命子辰的紫微天府一宫一颗分占结构，两星可以交换但不可同宫。`facts.named_star_positions.zi_palace` 与 `fu_palace` 返回紫微、天府实际地支；命宫七杀使 `facts.grade="上格"`，否则为“普通吉格”。命宫或三方四煞及化忌触发 `broken`，化忌证据同时返回承载星曜、`transformation="化忌"` 和物理落宫；`facts.flags.has_liu_lu` 只复述外部确认值。
23. `科权对拱` revision 1 仅匹配命宫。分支A为化科、化权均在迁移、财帛、官禄，分支B为命宫化科化权且三方化禄；两颗四化允许同落一宫。骨架成立返回 `base_status="formed"`、`grade="普通吉格"`；命宫或三方见擎羊、陀罗、火星、铃星、地劫、地空或任意化忌时保留格局并返回 `status="broken"` 与 `facts.break_check.break_star_list`（含星曜、化忌、物理宫位证据）。身宫相似结构只作 `pattern_observation`，对宫四化仅作备注。
24. `日月并明格` revision 1 仅匹配命宫丑、太阳巳、太阴酉的固定来朝结构，太阳太阴不得互换。`facts.named_star_positions.solar_palace` 与 `lunar_palace` 返回实际地支；乙辛、丙、丁生年干只作增益标签。命宫或三方四煞、空劫、化忌触发 `status="broken"`，保留 `base_status="formed"` 和 `facts.break_check.break_star_list`；身宫相似结构只作观察。
25. `机月同梁格` revision 1 对命宫、身宫分别执行独立匹配；目标宫及两个三合宫集齐天机、太阴、天同、天梁即命中，文昌文曲增益通过 `facts.flags.chang_qu_status` 返回 `none`、`single_chang`、`single_qu` 或 `both`。触发源宫及三方四煞或化忌时保留 `base_status="formed"` 并返回 `status="broken"` 和破格证据。
26. `日照雷门格` revision 1 仅匹配卯宫命宫太阳坐守；三方左右昌曲魁钺通过 `facts.flags.lucky_star_status` 返回 `none`、`partial` 或 `full`。甲乙庚辛生年干为增益标签；命宫或三方见刑忌四杀时 `status` 仍为 `normal`，并返回 `facts.flags.level_down=true`，表示层次降为温饱，不返回 `broken`。
27. `月朗天门格` revision 1 仅匹配亥宫命宫太阴坐守；三方六吉曜通过 `facts.flags.three_side_arch` 展示，丙丁、壬癸生年干分别通过 `facts.flags.gui_year_gan`、`facts.flags.fu_year_gan` 展示。命宫及三方煞忌通过 `facts.flags.has_bad_star_note` 和观察证据返回，原文无破格或降级规则，`status` 保持 `normal`。
28. `禄空倒马格` revision 1 仅在 `annual` 流年上下文执行；`facts` 返回 `lu_ma_palace_code`、`lu_ma_state`、`tai_sui_palace_code`、`tai_sui_have_kong_jie`、`meet_type` 等动态证据。禄马败/绝/空亡且太岁宫会地劫或天空才命中，命中为凶格但不标记 `broken` 或 `level_down`；本命层不返回此格局。
29. `极居卯酉格` revision 1 仅匹配卯酉命宫紫微贪狼同守；`facts.flags.monk_tendency`、`facts.flags.sha_count` 返回煞重与六煞计数，`facts.flags.noble` 表示无重煞、吉化及左右魁钺达标，命中时 `facts.grade` 升为“贵格”。煞曜只改变倾向标签，不触发 `broken`。
30. `马头带剑格` revision 1 仅匹配命宫本宫午卯酉擎羊或寅申巳亥陀罗；辰戌丑未不成格。`facts.flags.trigger_type` 返回触发类型，命中为凶格且 `status="formed"`，不设置 `broken` 或 `level_down`；身宫相似结构只作观察。
31. `英星入庙格` revision 1 仅匹配子午命宫破军坐守；命宫及三方出现任一六吉曜时 `facts.flags.has_auspicious=true`，不出现则为 `false`。吉星只改变增益标签，煞星不触发 `broken` 或 `level_down`，身宫相似结构只作观察。
32. `文华文桂格` revision 1 仅匹配丑未命宫文昌文曲同守，并要求吉化（化禄/化科）或禄星与六吉曜拱夹至少一项；`facts.flags.reason_tag` 返回 `hua_condition` 或 `lucky_arch_clamp`，缺少两类条件则不成格。煞星只作备注。
33. `石中隐玉格` revision 1 对命宫、身宫分别执行独立匹配；子午目标宫巨门坐守即命中，`facts.flags.trigger_from` 返回 `ming_palace` 或 `shen_palace`，寅戌申辰化科/化禄合照通过 `facts.flags.has_ke_lu_shine` 展示。煞星不破格。
34. `日月反背格` revision 1 以全盘太阳、太阴失辉宫位为必要条件，报告入口归属命宫但不要求日月坐命；`facts.flags.has_good_transform` 表示日月所在宫及各自三方是否出现化禄、化权、化科。煞星只作备注，不触发破格或降级。
35. `廉贞清白格` revision 1 仅匹配命宫廉贞坐守且宫位与本命生年干满足未-甲、申-癸、寅-己三组之一；`facts.flags.match_case` 返回 `wei_jia`、`shen_gui` 或 `yin_ji`，命中档位为“上等格局”。身宫相似结构不成格，煞星只作备注。
36. `禄马交持格` revision 1 匹配同一物理宫内携带化禄的实体主星与天马，双方亮度字段兼容 `brightness`/`liang_du` 且均非“陷”；`facts.flags.occur_pal` 返回共同宫位，`facts.flags.debug_brightness` 返回两颗星的亮度证据。煞星只作备注。
37. `桃花犯主格` revision 1 匹配命宫或身宫紫微贪狼同宫；左右相邻宫分别见左辅、右弼时视为“辅弼夹帝”豁免，不返回格局命中。无豁免时返回特殊格局，煞星只作备注。
38. `君臣庆会格` revision 1 仅匹配命宫紫微坐守且得臣星相助或臣星夹帝；`facts.flags.trigger_type` 标记触发分支，`facts.flags.debug_clip_stars` 返回夹宫臣星。命宫四煞同度时 `status="broken"`，三方分散不触发破格。
39. `刑囚夹印格` revision 1 匹配命宫或身宫天相被左右邻宫擎羊、廉贞夹持，`facts.flags.trigger_type` 返回 `ming_palace` 或 `body_palace`；不把地劫、亮度或四化加入条件，煞星只作备注。
40. `善荫朝纲格` revision 1 匹配命宫或身宫辰戌天机天梁同宫且目标宫见化禄、化权、化科之一；`facts.flags.reduce_rank` 表示目标宫见刑忌耗煞，状态仍保留 `formed`，不触发 `broken`。
41. `日丽中天格` revision 1 匹配命宫或身宫午宫太阳坐守；`facts.flags.is_best` 仅在本命年干为庚/辛且请求 `chart.is_daytime=true` 时为真，缺失或 `false` 均为假。
42. `水澄桂萼、月生沧海格` revision 1 匹配命宫或身宫子宫太阴坐守；`facts.flags.is_best` 仅在本命年干为丙/丁且请求 `chart.is_daytime=false` 时为真，缺失或 `true` 均为假。
43. `泛水桃花格` revision 1 匹配命宫或身宫亥子贪狼坐守；目标宫本宫吉曜/化吉输出 `facts.flags.has_good`，刑忌煞输出 `facts.flags.degenerate=true`，但格局状态仍为 `formed`。
44. `风流彩杖格` revision 1 仅匹配寅宫命宫或身宫贪狼擎羊同宫；寅宫贪狼陀罗仅作为 `pattern_observation` 参考，不进入格局命中，煞星只作备注。
45. `财荫夹印格` revision 1 仅匹配命宫或田宅宫被左右邻宫武曲、天梁夹持；`facts.flags.target_type` 标记目标类型，其他功能宫相似结构不计格局。
46. `日月照壁格` revision 1 仅匹配田宅宫太阳、太阴同守；`facts.flags.is_tomb_house` 表示田宅宫是否位于辰、戌、丑、未墓库，墓库只作增强标签。
47. `日月夹命格` revision 1 仅匹配命宫左右邻宫太阳、太阴分夹；`facts.flags.cond_perfect` 表示命宫无天空地空且本宫有吉星，完备条件不影响基础 `formed`，身宫仅输出观察。

破格诊断对象格式：

```json
{
  "break_check": {
    "status": "broken",
    "break_star": ["擎羊", "陀罗", "地劫", "地空"],
    "break_star_list": [
      {"star": "擎羊", "palace": "财帛宫", "branch": "亥"}
    ],
    "scan_scope": "命宫、三方宫",
    "note": "命宫或三方见羊陀劫空时保留格局记录并标记破格"
  }
}
```

当前第 1 条只完成本命层。请求 `decade`、`annual` 等未开放层级时返回 `400 INVALID_REQUEST`，不会返回不完整分析。

## 14. cURL 示例

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
