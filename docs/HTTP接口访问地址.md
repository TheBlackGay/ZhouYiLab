# ZhouYiLab HTTP 接口访问地址

## Base URL

- 生产环境：`https://zhouyilab.k8s.gold`
- 内网直连：`http://192.168.31.183:8768`
- 本地开发：`http://127.0.0.1:8765` 或启动 8768 端口后的 `http://127.0.0.1:8768`

生产环境通过 HTTPS 反向代理提供服务。其他项目只需将 Base URL 与下表路径拼接，不要将容器地址或端口写入业务配置。

## 模块接口

| 模块 | 主要接口 |
| --- | --- |
| 公共日历 | `POST /api/v1/calendar/convert`、`POST /api/v1/calendar/true-solar-time` |
| 紫微斗数 | `GET /api/v1/ziwei/meta`、`POST /api/v1/ziwei/charts`、`POST /api/v1/ziwei/fortune`、`POST /api/v1/ziwei/analysis` |
| 奇门遁甲 | `POST /api/v1/qimen/charts` |
| 八字 | `POST /api/v1/bazi/charts` |
| 六爻 | `POST /api/v1/liu-yao/charts` |
| 大六壬 | `POST /api/v1/da-liu-ren/charts` |
| 西洋占星 | `GET /api/v1/astro/meta`、`POST /api/v1/astro/charts`、`POST /api/v1/astro/analysis` |
| 服务健康 | `GET /api/v1/health` |

例如八字接口的生产地址为：

```text
https://zhouyilab.k8s.gold/api/v1/bazi/charts
```

各模块请求字段、响应结构和错误码详见对应模块文档：

- [公共日历 API 文档](common/公共日历API.md)
- [紫微斗数 HTTP 接口文档](ziwei/紫微斗数HTTP接口文档.md)
- [奇门遁甲 HTTP 接口文档](奇门遁甲HTTP接口文档.md)
- [西洋占星 HTTP 接口文档](astro/西洋占星HTTP接口文档.md)
