# 奇门遁甲 HTTP 接口

奇门网页与接口由 `web/server.py` 提供，默认只监听本机地址。

## 对外访问地址

- 生产 Base URL：`https://zhouyilab.k8s.gold`
- 内网直连 Base URL：`http://192.168.31.183:8768`
- 本地开发 Base URL：`http://127.0.0.1:8765`

其他项目接入时请优先使用生产地址，例如：

```text
https://zhouyilab.k8s.gold/api/v1/qimen/charts
```

生产域名由 HTTPS 反向代理转发至应用容器，不需要直接暴露或依赖容器端口。

## 启动

```bash
cmake -S . -B build
cmake --build build --target qi_men_web_cli
python3 web/server.py --port 8765
```

浏览器访问 `http://127.0.0.1:8765/qimen.html`。

## 排盘

`POST /api/v1/qimen/charts`

公历请求：

```json
{
  "calendar": "solar",
  "date": {
    "year": 2011,
    "month": 6,
    "day": 18,
    "hour": 3,
    "minute": 56
  }
}
```

需要按出生地真太阳时起局时，在请求中加入统一的 `time_correction`：

```json
{
  "calendar": "solar",
  "date": {
    "year": 2026,
    "month": 9,
    "day": 2,
    "hour": 20,
    "minute": 20
  },
  "time_correction": {
    "mode": "true_solar_time",
    "longitude": 121.4737,
    "standard_meridian": 120,
    "daylight_saving_minutes": 0
  },
  "location": {
    "latitude": 31.2304,
    "longitude": 121.4737,
    "timezone": "Asia/Shanghai"
  }
}
```

奇门会先将农历输入转换为公历，再按 `time_correction` 计算 `chart_time`，最后使用校正后的日期、节气、日干支和时干支起局。未提供该字段时默认使用标准时间，保持兼容。

农历请求使用 `calendar: "lunar"`，闰月需额外传入 `"leap_month": true`——该键位于 `date` 对象内，顶层同名键会被静默忽略。

成功响应的 `data` 包含：

- `method` 与 `center_lodging` 算法规则标识；
- `birth_date` 与 `birth_time`：校正明细**嵌在 `data.birth_time` 内**（`mode`、`recorded_time`、`standard_time`、`chart_time`、`longitude`、`standard_meridian`、`daylight_saving_minutes`、`longitude_offset_seconds`、`equation_of_time_seconds`、`total_offset_seconds`、`crossed_date_boundary`），`data` 顶层无 `time_correction` 键；
- 公历、农历和四柱信息；
- 阴阳遁、三元、局数和节气；
- 直符、直使及直符所在宫；
- 九宫的九星、八门、八神、天盘干和地盘干。

接口返回统一的 `success`、`data`、`meta` 结构（顶层 `meta` 仅 `api_version`/`algorithm_version`/`request_id`）。引擎口径自述位于 `data.meta.rule_profile`。输入错误返回 HTTP 422 `INVALID_ARGUMENT`；请求体非法 JSON/缺运算字段返回 400 `INVALID_REQUEST`；超时 504 `CALCULATION_TIMEOUT`；引擎未构建 500 `ENGINE_UNAVAILABLE`。错误说明见 `error.code` 与 `error.message`。

## 排盘规则

当前实现采用拆补法时家转盘奇门：

- 按日干支回推符头，确定上、中、下元；
- 按时干支确定六甲旬首及对应六仪；
- 甲时按所在旬遁藏，不统一按甲子戊处理；
- 阳遁顺布、阴遁逆布地盘奇仪；
- 旬首六仪落中五宫时寄坤二宫判定；天禽随天芮转动，并通过宫位的 `lodged_star`、`lodged_tian_gan` 标明；
- 中宫不配置八门和八神，JSON 中对应字段为空字符串。

不同网站可能采用置闰法、超神接气、真太阳时或不同的中宫寄法，跨来源比较前必须先确认规则一致。

## 规则口径

响应 `data.meta.rule_profile`：`profile_version` = `qi-men-rules/1.0`，
`calibration_status` = `calibrated`，`rules` 共 8 键：`jia_hidden`、`pan_method`、
`qi_ju_method`、`shen_sha_set`、`shichen_scope`、`time_correction`、`zhi_fu_zhi_shi`、
`zhong_gong_ji_kun`（实测 2026-09-02 例响应）。回归锁：`tests.test_qimen_learning_rules`、
`tests.test_qimen_regression`（`config/platform/calibration_suites.json` 登记）。
