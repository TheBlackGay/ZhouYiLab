# 公共日历 API

公共日历能力由 `ZhouYi.Common.Calendar` 提供，功能模块不需要直接构造 `tyme::SolarTime` 或 `tyme::LunarHour`。

## C++ Module API

```cpp
import ZhouYi.Common.Calendar;

using namespace ZhouYi::Common;
using namespace ZhouYi::Common::Calendar;

const SolarDateTime solar{2024, 2, 10, 9, 5, 0};
const LunarDateTime lunar = solar_to_lunar(solar);
const SolarDateTime restored = lunar_to_solar(lunar);

const SolarTimeCorrection correction = calculate_true_solar_time(
    solar,
    TrueSolarTimeOptions{.longitude = 104.066});
```

公历/农历值对象 API：

| API | 说明 |
| --- | --- |
| `solar_to_lunar(SolarDateTime)` | 公历转换为农历 |
| `lunar_to_solar(LunarDateTime)` | 农历转换为公历 |
| `to_solar_time(SolarDateTime)` | 构造 `tyme::SolarTime` |
| `to_lunar_hour(LunarDateTime)` | 构造 `tyme::LunarHour` |

农历月份约定为：正数表示普通月，负数表示闰月。例如 `-4` 表示闰四月。公共值对象校验年月日时分秒范围，实际不存在的农历日期或闰月由 `tyme4cpp` 拒绝并抛出 `std::invalid_argument`。

真太阳时 API：

| API | 说明 |
| --- | --- |
| `calculate_equation_of_time_seconds(SolarDateTime)` | 计算均时差，单位为秒 |
| `correct_solar_time(SolarDateTime, SolarTimeOptions)` | 按模式计算标准时间或真太阳时 |
| `calculate_true_solar_time(SolarDateTime, TrueSolarTimeOptions)` | 直接计算真太阳时 |

计算关系为：

```text
标准时间 = 记录时间 - 夏令时
真太阳时 = 标准时间 + (出生地经度 - 标准经线) * 4分钟 + 均时差
```

`SolarTimeCorrection` 返回记录时间、标准时间、校正时间、经度校正秒数、均时差、总校正秒数及是否跨日。

## HTTP API

公共接口使用与其他服务相同的响应包装：`success`、`data`、`meta`
（顶层 `meta` 仅 `api_version`/`algorithm_version`/`request_id`）。

### 部署与 CLI 依赖

两个 HTTP 端点由 server.py 调 `build/examples/common_calendar_web_cli`（注入
`operation` 字段：`calendar_convert` / `calendar_true_solar_time`）。该工具在清单中
`required_at_startup: false`：日历 CLI 缺失**不阻塞服务启动**，但调用两端点将返回
500 `ENGINE_UNAVAILABLE`（消息"计算引擎尚未构建"）。接入前可用
`GET /api/v1/health` 的 `calendar_cli_available` 预检。

### `POST /api/v1/calendar/convert`

公历请求：

```json
{
  "calendar": "solar",
  "date": {
    "year": 2024,
    "month": 2,
    "day": 10,
    "hour": 9,
    "minute": 5,
    "second": 0
  }
}
```

农历请求使用正数 `month` 和 `leap_month` 标记闰月：

```json
{
  "calendar": "lunar",
  "date": {
    "year": 2023,
    "month": 2,
    "leap_month": true,
    "day": 1,
    "hour": 9,
    "minute": 5,
    "second": 0
  }
}
```

响应 `data` 包含 `source`、`solar` 和 `lunar`。两个日期对象均包含年月日时分秒及 `display` 字段；农历对象额外包含 `leap_month`。

> 闰月时 `lunar.display` 的月位以“闰NN”呈现（实测 `2023-闰02-01 09:05:00`）；
> 程序消费请优先使用结构化的 `month`+`leap_month` 字段，不要解析 `display`。

### `POST /api/v1/calendar/true-solar-time`

请求：

```json
{
  "date": {
    "year": 1994,
    "month": 12,
    "day": 8,
    "hour": 9,
    "minute": 5,
    "second": 0
  },
  "longitude": 104.066,
  "standard_meridian": 120.0,
  "daylight_saving_minutes": 0
}
```

响应 `data` 包含 `recorded_time`、`standard_time`、`true_solar_time`、`chart_time` 和全部校正明细。`chart_time` 与现有紫微接口保持同名兼容，`true_solar_time` 是公共接口的明确名称。

错误输入返回统一错误对象 `{"error": {"code", "message"}, "meta": …}`，按状态码：

| HTTP | code | 场景 |
|---|---|---|
| 400 | `INVALID_REQUEST` | 请求体非 JSON 等 server 层校验 |
| 422 | `INVALID_ARGUMENT` | 引擎/tyme 校验：非法 `calendar` 值、不存在的闰月、日期越界（消息透传，英文） |
| 500 | `ENGINE_UNAVAILABLE` | 日历 CLI 未构建（见"部署与 CLI 依赖"） |
| 500 | `CALCULATION_FAILED` | 引擎崩溃兜底（正常输入不应出现，非"常见"） |
| 504 | `CALCULATION_TIMEOUT` | 引擎超时 |
