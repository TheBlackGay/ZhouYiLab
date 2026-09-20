# 梅花易数 HTTP 接口

梅花易数网页与接口由 `web/server.py` 提供，默认只监听本机地址。路由由工具清单
`config/platform/tools/mei_hua.json` 注册（平台注册表 `engine_chart` 分发，非手写分支）。

内核契约：`meihua-plate/1.0` 事实盘；规则口径：`meihua-rules/0.1`（calibration
**pending**——只输出盘面事实与体用生克结构判词，不输出吉凶、应期与事类断语）。

## 对外访问地址

- 生产 Base URL：`https://zhouyilab.k8s.gold`
- 内网直连 Base URL：`http://192.168.31.183:8768`
- 本地开发 Base URL：`http://127.0.0.1:8768`

## 启动

```bash
./build.sh
python3 web/server.py
```

浏览器访问 `http://127.0.0.1:8768/meihua.html`。

## 起卦

`POST /api/v1/mei-hua/plates`

时间起卦（公历）：

```json
{
  "mode": "time",
  "calendar": "solar",
  "date": { "year": 1917, "month": 1, "day": 10, "hour": 16 }
}
```

时间起卦（农历，书例同一盘）：

```json
{
  "mode": "time",
  "calendar": "lunar",
  "date": { "year": 1916, "month": 12, "day": 17, "hour": 16 }
}
```

报数起卦（两数或三数；`date` 仍须提供，用于月令旺衰）：

```json
{
  "mode": "numbers",
  "calendar": "solar",
  "date": { "year": 2025, "month": 2, "day": 12, "hour": 10 },
  "numbers": [3, 7]
}
```

- `hour` 为 0-23；年支以立春为岁首（统一八字历法层口径），时辰由历法层归支。
- 农历 `leap_month: true` 时，闰月取数按**十五分界**（D13.1，与紫微 D12 同尺）：
  十五日前作本闰月，十六日起作下月，闰十二下半月回绕作正月。
- 起卦公式：上卦 =（年支序+月+日）mod 8，下卦 =（+时支序）mod 8，动爻 = 总数 mod 6；
  余 0 一律作满数（8/6）。先天卦数乾1兑2离3震4巽5坎6艮7坤8。

## 响应（envelope 下 data 即事实盘）

```json
{
  "schema_version": "meihua-plate/1.0",
  "casting": { "method": "time", "year_branch_order": 5, "lunar_month_used": 12,
               "lunar_day": 17, "hour_branch_order": 9, "upper_sum": 34, "lower_sum": 43,
               "leap_month_rule": "fifteen_boundary", "formula": "..." },
  "ba_zi": { "year": {"stem":"丙","branch":"辰"}, "...": {},
             "month_command": "丑" },
  "ben_gua": { "code": "101110", "name": "泽火革", "palace": "坎",
               "inner": "离", "inner_element": "火", "outer": "兑", "outer_element": "金" },
  "hu_gua": { "code": "011111", "name": "天风姤" },
  "bian_gua": { "code": "001110", "name": "泽山咸" },
  "moving_line": 1,
  "trigrams": { "upper": {"number":2,"name":"兑","element":"金"},
                "lower": {"number":3,"name":"离","element":"火"} },
  "ti_yong": { "ti": "upper", "yong": "lower",
               "ti_element": "金", "yong_element": "火",
               "relation": "用克体", "ti_wang_shuai": "相", "yong_wang_shuai": "休" },
  "meta": { "rule_profile": { "profile_version": "meihua-rules/0.1",
                              "calibration_status": "pending", "rules": { "...": "8 项口径" } } }
}
```

- 体用：动爻所临经卦为用、另一为体；判词五态＝体用比和/用生体/用克体/体生用/体克用。
- 旺衰：体用两卦各按《翼氏大典》月令五态通行表（与六爻内核共用同一函数，
  DEF-4 修复后口径；`tests/test_meihua_plate_contract.py` 书例全锁）。

## 错误

无效入参返回 422 + `{"error": {"code": "INVALID_ARGUMENT", "message": "..."}}`：
mode/calendar 非法、报数非 2-3 个正整数、日期越界等。

## 已知边界

- 无起卦"心诚则灵"意义上的随机数供应（报数由求测方自备）；摇卦器（如六爻投币）暂缺，列 M2 之后观察。
- 卦名/宫位查表沿用六爻内核京房八宫表，仅作盘面结构信息；断语、事类、应期在未校准（pending）前不接入。
