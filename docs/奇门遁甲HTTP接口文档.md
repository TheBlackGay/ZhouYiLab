# 奇门遁甲 HTTP 接口

奇门网页与接口由 `web/server.py` 提供，默认只监听本机地址。

## 启动

```bash
cmake -S . -B build
cmake --build build --target zi_wei_web_cli qi_men_web_cli
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

农历请求使用 `calendar: "lunar"`，闰月需额外传入 `"leap_month": true`。

成功响应的 `data` 包含：

- `method` 与 `center_lodging` 算法规则标识；
- 公历、农历和四柱信息；
- 阴阳遁、三元、局数和节气；
- 直符、直使及直符所在宫；
- 九宫的九星、八门、八神、天盘干和地盘干。

接口返回统一的 `success`、`data`、`meta` 结构。输入错误返回 HTTP 422，并在 `error.code` 和 `error.message` 中说明原因。

## 排盘规则

当前实现采用拆补法时家转盘奇门：

- 按日干支回推符头，确定上、中、下元；
- 按时干支确定六甲旬首及对应六仪；
- 甲时按所在旬遁藏，不统一按甲子戊处理；
- 阳遁顺布、阴遁逆布地盘奇仪；
- 旬首六仪落中五宫时寄坤二宫判定；天禽随天芮转动，并通过宫位的 `lodged_star`、`lodged_tian_gan` 标明；
- 中宫不配置八门和八神，JSON 中对应字段为空字符串。

不同网站可能采用置闰法、超神接气、真太阳时或不同的中宫寄法，跨来源比较前必须先确认规则一致。
