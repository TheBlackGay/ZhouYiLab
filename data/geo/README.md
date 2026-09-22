# data/geo — 出生地点解析数据（G1）

本目录承载全系统共用的**地名库与索引**，被 `web/geo_places.py` 在启动时一次性载入内存，
服务 `/api/v1/geo/*` 三个只读接口。设计依据：
`docs/product/西洋占星出生地点交互优化方案.md`（§6）。

## 文件

| 文件 | 内容 |
| --- | --- |
| `curated.json` | 精选城市数据集（唯一数据源，493 条） |
| `index.json` | 数据集 `revision`、分片计数与 sha256 校验和（G2 多分片时扩展） |
| `places.schema.json` | 单条目 JSON Schema 契约 |

## 重新生成

`curated.json` / `index.json` 由 `scripts/gen_curated_places.py` 生成：

```
python3 scripts/gen_curated_places.py
```

生成脚本内置**配额检查**（34 直辖市/省会/首府核心 + 120 地级市与重要驻地 +
193 其余地级市/自治州/盟驻地 + 20 港澳台 + 100 全球首都 + 26 海外高频城市 = 493）
与 **place_id 唯一性检查**，不满足即失败退出。

## 字段与精度

- 坐标为**城市级代表点**（约数，精度 ±0.5° 内），`approx_radius_km > 50` 的条目
  （如重庆、呼伦贝尔）在前端会提示"建议微调到出生区县"（方案 §4.5）。
- `tz` 必须是可被 `zoneinfo` 加载的 IANA 时区名；新疆城市用 `Asia/Urumqi` /
  `Asia/Kashgar`（对应 UTC+6 官方口径），不用 `Asia/Shanghai`。
- 每条数据须通过自动校验：`|lon − 标准经线(该时区当时标准偏移)| ≤ 30°`
  （见 `tests/test_geo_places.py`，方案 §6.1）。该规则要求民用 UTC+8 城市的
  代表点不晚于东经 90°，因此**日喀则市（88.88°E）与阿里地区（狮泉河，80.1°E）
  暂不收录**（用 Asia/Urumqi 等 UTC+6 时区收录会产生错误的民用偏移）。
  在该区域出生请手动填写经纬度并确认 UTC 偏移为 +8；坐标反查给出的
  「约：」城市可能落在更近的邻国条目（如廷布），仅作提示，不代表推荐。
- 自治州/盟驻地条目用「驻地名（州/盟名）」形式（如「延吉市(延边州)」），
  州名与驻地名都能被中文检索命中；`population` 取驻地市/县约数。
- `population`、`approx_radius_km` 为公开资料约数，仅用于排序与提示。

## 来源与许可

`curated` 由本项目按公开资料手工整理（常见城市名、约数坐标、IANA 时区、约数人口）。
**不复制任何商业地图数据（高德/百度等）**。G2 引入第三方数据（如 GeoNames，CC BY 4.0）
时必须在此登记许可与署名要求，并写入接口的 `provenance`。

## 时区数据版本

偏移与夏令时推导运行时用 Python 标准库 `zoneinfo`，数据目录固定到 pip `tzdata` 包
（若已安装），并在 `/api/v1/geo/meta` 与解析结果 `provenance.tzdata_version` 中报告
IANA 版本号；取不到版本时报告 `unknown:<路径>`，不编造（方案 §6.4）。
