# ZhouYiLab 紫微斗数 HTTP API

> API 版本：`v1`
> 文档版本：`1.1.0`
> 更新日期：`2026-08-30`
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
| 十二宫及格局解读 | `POST` | `/api/v1/ziwei/analysis` | 预留，尚未开放 |

本命盘、真太阳时和运限已经通过接口提供。命盘解读必须遵守[紫微斗数命盘与运限分析准则](./紫微斗数命盘与运限分析准则.md)，在规则引擎完成前不得返回占位性分析结果。

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
    "algorithm_version": "zhouyilab-core/1.1.0",
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
    "algorithm_version": "zhouyilab-core/1.1.0",
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
    "algorithm_version": "zhouyilab-core/1.1.0",
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
  "algorithm_version": "zhouyilab-core/1.1.0",
  "capabilities": [
    "natal_chart",
    "true_solar_time",
    "decade",
    "minor",
    "annual",
    "monthly",
    "daily",
    "hourly"
  ],
  "genders": ["male", "female"],
  "time_correction_modes": ["standard_time", "true_solar_time"],
  "fortune_layers": ["decade", "minor", "annual", "monthly", "daily", "hourly"]
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

### 7.2 Star 星曜对象

```json
{
  "name": "武曲",
  "liang_du": "利",
  "si_hua": "化科"
}
```

`si_hua` 为可选字段。`liang_du` 当前可能值为 `庙、旺、得、利、平、陷`。

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

## 12. 解读接口预留

未来的 `/api/v1/ziwei/analysis` 应支持：

```json
{
  "chart_request": {},
  "scope": {
    "layers": ["natal", "decade", "annual"],
    "focus_palaces": ["命宫", "官禄宫"],
    "depth": "full"
  }
}
```

正式实现必须：

1. 本命、大限、流年分别完成十二宫和格局分析。
2. 独立分析完成后才进行跨层叠加。
3. 流月、流日、流时按请求计算。
4. 每条事实携带 `source_layer`。
5. 每个格局携带 `effect_palace` 和 `effect_subject`。
6. 返回命中的规则 ID、版本和证据，不能只返回自然语言。

在上述条件完成前，此路径保持 `404 ENDPOINT_NOT_FOUND`，避免客户端误用不完整结果。

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
