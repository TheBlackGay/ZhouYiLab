# ZhouYiLab HTTP 接口访问地址

## Base URL

- 生产环境：`https://zhouyilab.k8s.gold`
- 内网直连：`http://192.168.31.183:8768`
- 本地开发：`http://127.0.0.1:8765` 或启动 8768 端口后的 `http://127.0.0.1:8768`

生产环境通过 HTTPS 反向代理提供服务（生产域名与内网 IP 以运维登记为准）。其他项目只需将 Base URL 与下表路径拼接，不要将容器地址或端口写入业务配置。

## 模块接口

| 模块 | 主要接口 |
| --- | --- |
| 平台发现 | `GET /api/v1`、`GET /api/v1/tools` |
| 公共日历 | `POST /api/v1/calendar/convert`、`POST /api/v1/calendar/true-solar-time` |
| 紫微斗数 | `POST /api/v1/ziwei/time-correction`、`POST /api/v1/ziwei/charts`、`POST /api/v1/ziwei/fortune`、`POST /api/v1/ziwei/analysis`、`GET /api/v1/ziwei/meta`、`GET /api/v1/ziwei/symbols`、`POST /api/v1/ziwei/distribution` |
| 奇门遁甲 | `POST /api/v1/qimen/charts` |
| 八字 | `POST /api/v1/bazi/charts`、`GET /api/v1/bazi/shen-sha/<id>`、`POST /api/v1/bazi/distribution` |
| 六爻 | `POST /api/v1/liu-yao/charts`、`POST /api/v1/liu-yao/distribution` |
| 梅花易数 | `POST /api/v1/mei-hua/plates`、`POST /api/v1/mei-hua/distribution` |
| 大六壬 | `POST /api/v1/da-liu-ren/charts`、`GET /api/v1/da-liu-ren/glossary`、`POST /api/v1/da-liu-ren/distribution` |
| 西洋占星 | `GET /api/v1/astro/meta`、`POST /api/v1/astro/charts`、`POST /api/v1/astro/transits`、`POST /api/v1/astro/analysis`、`POST /api/v1/astro/transit-analysis`、`POST /api/v1/astro/daily-reading`、`POST /api/v1/astro/natal-analysis`、`POST /api/v1/astro/natal-reading`、`POST /api/v1/astro/distribution` |
| 出生地检索 | `GET /api/v1/geo/meta`、`GET /api/v1/geo/places`、`POST /api/v1/geo/place-resolve`（契约见[西洋占星 HTTP 接口文档](astro/西洋占星HTTP接口文档.md)"出生地检索"节） |
| 服务健康 | `GET /api/v1/health` |

六平台 `distribution` 为人性化画像图表数据包（三环形图 + 暖场解读 + 底色总结），
请求接受 `chart`（已排盘面）或 `chart_request`（服务端代排）二选一。

未列入上表的端点：

- 研究工具（非对外契约，见校准 TODO D4）：`GET /api/v1/ziwei/research/blind-review/packet`、`/api/v1/ziwei/research/ai-review/*`；
- 历史兼容（勿新增接入）：`POST /api/calculate`（旧紫微链，内部代理到 `/api/v1/ziwei/charts`）。

### 平台端点

| 端点 | 说明 |
|---|---|
| `GET /api/v1` | 服务发现：service/api_version/algorithm_version/governance_mode、endpoints 摘要与工具清单 |
| `GET /api/v1/tools` | 全工具注册表：各工具 id、calibration_status、rule_profile_version、pages、routes（含 handler 与 `routable` 标志） |
| `GET /api/v1/health` | 健康检查：紫微 `cli_available` + 各引擎 `*_cli_available`、`astro_ephemeris_available`、`registry_source`、`tools` 摘要 |

例如八字接口的生产地址为：

```text
https://zhouyilab.k8s.gold/api/v1/bazi/charts
```

各模块请求字段、响应结构和错误码详见对应模块文档：

- [公共日历 API 文档](common/公共日历API.md)
- [紫微斗数 HTTP 接口文档](ziwei/紫微斗数HTTP接口文档.md)
- [奇门遁甲 HTTP 接口文档](qimen/奇门遁甲HTTP接口文档.md)
- [八字 HTTP 接口文档](bazi/八字HTTP接口文档.md)
- [六爻 HTTP 接口文档](liuyao/六爻HTTP接口文档.md)
- [大六壬 HTTP 接口文档](daliuren/大六壬HTTP接口文档.md)
- [梅花易数 HTTP 接口文档](meihua/梅花易数HTTP接口文档.md)
- [西洋占星 HTTP 接口文档](astro/西洋占星HTTP接口文档.md)
