# 大六壬 HTTP 接口

大六壬网页与接口由 `web/server.py` 提供，默认只监听本机地址。路由由工具清单
`config/platform/tools/da_liu_ren.json` 注册（平台注册表分发，非手写分支）。

## 对外访问地址

- 生产 Base URL：`https://zhouyilab.k8s.gold`
- 内网直连 Base URL：`http://192.168.31.183:8768`
- 本地开发 Base URL：`http://127.0.0.1:8765`

## 启动

```bash
./build.sh
python3 web/server.py --port 8765
```

浏览器访问 `http://127.0.0.1:8765/da-liu-ren.html`。

## 排盘

`POST /api/v1/da-liu-ren/charts`

公历请求：

```json
{
  "calendar": "solar",
  "date": { "year": 2025, "month": 11, "day": 3, "hour": 16 }
}
```

农历请求使用 `calendar: "lunar"`；该年存在闰月时可加 `"leap_month": true`。
`hour` 为双小时起始值（早子=0 … 夜子=23）；分钟不参与起课。

可选入参 `yuejiang_method`（D2 决策）：`"zhongqi"`（默认，中气过宫）或
`"guifa_suicha"`（古法歌诀十二定切点，对照/旧盘复现用）。页面固定走默认口径、
不暴露该参数；外部接入方可显式请求对照口径，未知值返回 422。

成功响应 `data` 字段：

- `ba_zi`：四柱（年/月/日/时各含 `stem`、`branch`）与 `xun_kong_1`、`xun_kong_2` 旬空；
- `yue_jiang`（月将）、`gui_ren`（贵人）、`is_day`（昼夜）；
- `si_ke`：四课 `first`–`fourth`（干支字符串）；
- `san_chuan`：`chu_chuan`/`zhong_chuan`/`mo_chuan`、`ke_shi`（首项为九宗门名）、
  `details[]`（`stage`、`branch`、`dun_gan`、`liu_qin`）；
- `tian_di_pan`：12 项数组，`position`/`tian_pan`/`dun_gan`/`shen_jiang`；
- `shen_sha`：按 基础/年/月/日/地支神煞 分组的结构化对象；
- `gua_ti`：卦体名称数组（只命名，不断吉凶）；
- `meta.rule_profile`：本盘生成所依据的规则口径标识，见下节；
- `meta.yuejiang_method`：本盘实际使用的月将取法（`zhongqi` / `guifa_suicha`）。

错误：输入非法返回 HTTP 422，`error.code` 为 `INVALID_ARGUMENT` 等；
不存在的闰月由引擎拒绝（`illegal leap month`，页面已本地化为可操作提示）。

## 规则口径 `meta.rule_profile`

```json
{
  "profile_version": "da-liu-ren-rules/0.2",
  "calibration_status": "pending",
  "rules": { "four_pillars": "...", "yue_jiang": "...", "gui_ren": "...",
             "shen_jiang": "...", "gan_ji_gong": "...", "san_chuan": "...",
             "dun_gan": "...", "liu_qin": "...", "gua_ti": "...",
             "time_granularity": "..." }
}
```

口径措辞逐条来自代码实际实现（0.2 起月将默认**中气过宫**、以中气交节时刻精确到分为切点，歌诀十二定切点保留为 `guifa_suicha` 对照口径；
九宗门顺序伏吟→返吟→贼克(含比用/涉害细分)→遥克→昴星→别责→八专）。
`calibration_status` 在校准完成前保持 `pending`；算法口径变更必须同步
`profile_version`。契约测试：`tests/test_da_liu_ren_engine_contract.py`。

## 术语帮助

`GET /api/v1/da-liu-ren/glossary`

返回 `config/daliuren/glossary.json`（`static_config` 注册路由，只读）。
每条术语含 `definition` 与 `caliber`（当前实现口径），覆盖 DLR-204 要求的
四课、三传、初传、中传、末传、月将、贵人、课式、六亲、旬空十词及天地盘、
神将、遁干、卦体、神煞扩展词条。

## 页面

- 小白/专业双模式在**同一份数据**上切换，不重复请求接口；
- 问题类型与描述仅存在于浏览器页面，不发送给服务、不进访问日志；
- 小白模式不输出吉凶断语；专业模式“规则口径”页签展示本次 `rule_profile`。

## 已知边界（2.0.0）

- 算法整体处于**待校准**状态（README 校准状态表），本接口只保证盘面事实与
  结构命名的可追溯性；
- 2.0.0 不含天地盘 SVG 可视化（2.1.0）、规则解释（2.2.0）与案例校准报告（2.3.0）。

## 盘面画像（人性化图表数据包）

`POST /api/v1/da-liu-ren/distribution`

入参：`{"chart": <课盘对象>} 或 {"chart_request": {calendar, date, yuejiang_method?}}，可选 `"label"`。

返回 `dlr-distribution/1.0` 数据包，与占星/紫微画像同构：

- `charts[signs]` 盘面上神五行：十二宫天盘上神地支的五行（木火土金水），课面气象叙事；
- `charts[stems]` 天盘遁干五行：旬空两位自动不入分母（`point_total` 自释）；
- `charts[polarity]` 上神支阴阳：阳支子寅辰午申戌 / 阴支丑卯巳未酉亥；
- 顶层 `summary_zh` 三合一底色句；文案一律"气象描写"（升发/升腾/稳重……），**无吉凶断语**——六壬 calibration 仍为 pending。

数据源全部为课盘既有字段 + 与内核一致的标准五行表（契约测试交叉锁定），零新增算法。
