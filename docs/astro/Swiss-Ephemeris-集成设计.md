# Swiss Ephemeris 西洋占星模块集成设计（Draft）

> 状态：待评审，不执行代码变更。
>
> 目标：将 Swiss Ephemeris 集成为 ZhouYiLab 的独立“西洋占星/天文星历”模块，与紫微斗数、八字在产品入口、核心库、JSON CLI、HTTP API、Web 页面、测试和部署层面保持同等级别。

## 1. 设计结论

可以实现，且不需要改写现有紫微斗数或八字算法。当前仓库已经具备接入所需的边界：

- C++23 Modules 核心库由 `CMakeLists.txt` 统一构建。
- 各术数拥有独立的 `src/<module>` 模块和控制器。
- 网页计算通过 `examples/*_web_cli` 的 JSON 标准输入/输出桥接。
- `web/server.py` 负责静态页面、CLI 子进程和 `/api/v1/*` 路由。
- Docker 构建会复制 CLI 和配置资源，适合增加星历资源目录。

Swiss Ephemeris 只负责天体历算。本模块负责把历算结果组织成西洋占星排盘数据，但不在核心层加入性格、吉凶、运势或 AI 解读。

## 2. 产品边界

### 2.1 首版目标（MVP）

- 公历出生时间的本命盘计算。
- 太阳、月亮、水星、金星、火星、木星、土星、天王星、海王星、冥王星。
- 北交点、南交点和凯龙星作为可选点位；缺少对应星历文件时必须返回明确警告。
- 热带黄道（Tropical）为默认口径。
- Placidus 宫制为默认宫制，Whole Sign 作为第二种宫制。
- 上升点 ASC、天顶 MC、下降点 DSC、天底 IC。
- 行星黄经、黄纬、距离、速度、逆行状态、所属星座和星座内度数。
- 十二宫宫头、行星落宫和主要相位。
- JSON CLI、HTTP API、基础 Web 星盘页面、接口元数据和健康检查。

首版通过可选构建开关 `ZHOUYILAB_ENABLE_ASTRO` 控制模块和 CLI 是否编译，避免未启用星历时影响现有模块。

### 2.2 后续版本

- 恒星黄道和岁差参数配置。
- 更多小行星、黑月、阿拉伯点和自定义点位。
- 行运、次限、太阳回归、月返等时间盘。
- 日月食、行星升落和天文事件查询。
- 多种相位组、可配置容许度和相位应用/离相状态。
- 解释规则库和研究工具。解释层必须与历算层分离。

### 2.3 明确不做

- 不把 Swiss Ephemeris 输出直接转换成确定性人生结论。
- 不在首版支持农历日期作为西占的原始输入。需要农历时，先由现有 `tyme4cpp` 转换为公历，再进入统一时间管线。
- 不在首版支持全球历史时区规则。首版使用显式 UTC 偏移，避免不同平台时区数据库导致结果不一致。
- 不将 Swiss Ephemeris 的上游源码改造成 C++ Module。

## 3. 算法口径

### 3.1 时间

输入为当地民用时间和 `utc_offset_minutes`。计算流程为：

```text
当地日期时间 - UTC 偏移
    ↓
UTC 时间
    ↓
Julian Day UT（用于 swe_calc_ut）
    ↓
天体位置、宫位和相位
```

首版请求必须包含：

- 年、月、日、时、分、秒；
- UTC 偏移分钟数，范围 `-720..840`；
- 纬度、经度（经度东正西负）；
- 可选海拔，默认 0 米。

首版按公历（Gregorian）解释日期，输入不接受闰秒。`utc_offset_minutes` 表示当地民用时间相对于 UTC 的偏移，不等同于根据地理经度换算出的真太阳时偏移。

首版不自动应用真太阳时。西洋占星的宫位计算使用出生地的地理经度和纬度，不能直接复用八字/紫微的真太阳时修正结果。若用户选择真太阳时，必须作为单独的高级选项，并在响应中记录校正前后的时间。

### 3.2 坐标和黄道

- 默认使用地心、视黄经/黄纬。
- MVP 不做观测者地心差异，因此海拔仅作为预留字段；启用顶心坐标后才使用它。
- 默认黄道为热带黄道。
- 恒星黄道必须显式指定 `zodiac: "sidereal"` 和 `ayanamsa`，不得静默改变默认结果。
- `zodiac: "tropical"` 时 `ayanamsa` 必须为 `"none"`；`sidereal` 时必须指定受支持的岁差模型。
- 所有角度归一化到 `[0, 360)`。
- 逆行由经度速度小于 0 判断；接近 0 的停滞状态保留原始速度并提供 `stationary` 标记。

### 3.3 宫位

首版支持：

| `house_system` | 含义 |
| --- | --- |
| `placidus` | Placidus，默认 |
| `whole_sign` | 整宫制 |

高纬度地区可能无法计算 Placidus 宫位。此时 API 返回 `HOUSE_CALCULATION_FAILED`，不自动切换宫制；用户可以重试 `whole_sign`。

### 3.4 相位

首版默认计算以下主要相位：合相 0°、六合 60°、刑相 90°、拱相 120°、对冲 180°。相位结果至少包含：

- 两个点位的稳定 ID；
- 相位类型和精确角度；
- 实际夹角、偏差（orb）；
- 应用/离相状态（能计算时）；
- 是否使用默认容许度。

默认容许度必须集中配置，不散落在前端。首版建议按点位类型设置保守默认值，并在 `meta` 接口公开。

## 4. 模块和目录设计

### 4.1 第三方依赖

建议将官方 Swiss Ephemeris 源码固定在 `3rdparty/swisseph`，使用项目自己的 CMake 包装目标构建，不修改上游源码。上游 C 头文件只在适配实现单元中出现，不向其他模块暴露。Swiss 相关目标与 `ZhouYiLabCore` 分开，只有启用星历的 Astro 模块和 `astro_web_cli` 链接它，避免无关可执行文件被强制依赖。

建议增加：

```text
3rdparty/swisseph/
  CMakeLists.txt
  src/                 # 上游源码或固定版本源码
  LICENSE              # 上游许可证原文
data/ephemeris/       # .se1 文件，不与代码混用
```

星历文件路径由 `ZHOUYILAB_EPHEMERIS_PATH` 环境变量或启动参数配置。未配置时按以下顺序查找：

1. 环境变量指定路径；
2. 项目运行目录下的 `data/ephemeris`；
3. 系统安装路径；
4. 内置 Moshier 模式（仅在请求允许降级时）。

Swiss Ephemeris 可能在 `.se1` 文件缺失时自动返回 Moshier 结果。适配层必须检查返回的计算 flags 和诊断文本：请求不允许降级时将其转换为 `EPHEMERIS_UNAVAILABLE`，允许时明确标记 `precision_mode: "moshier"` 并写入警告。

### 4.2 C++ Modules

```text
src/astro/
  astro_types.cppm                 // 请求、点位、坐标、相位、错误类型
  astro_swiss_ephemeris.cppm       // 对 Swiss C API 的最小适配接口
  astro_swiss_ephemeris.cpp        // C 头文件、RAII、全局状态保护
  astro.cppm                       // 排盘流程和领域计算
  astro.cpp                        // 星座、宫位、相位和格式化实现
  astro_controller.cppm            // 对外控制器接口
  astro_controller.cpp              // JSON/控制台辅助实现
```

建议模块名：

```text
ZhouYi.Astro.Types
ZhouYi.Astro.SwissEphemeris
ZhouYi.Astro
ZhouYi.Astro.Controller
```

`ZhouYi.Astro.SwissEphemeris` 只暴露 ZhouYiLab 自己的类型，不导出 `swephexp.h` 中的宏、全局状态或 C 结构体。

### 4.2.1 CMake 目标边界

当前 CMake 的 C++ Module 图要求 Astro 与现有模块共享标准库 BMI。实现时将 Astro 源文件按条件加入现有 Core 目标，同时仅在 Astro 启用时链接 Swiss Ephemeris：

```text
ZhouYiLabCore       = 现有术数模块 + 可选 Astro Modules，按开关链接 swisseph
astro_web_cli       = 链接 ZhouYiLabCore，仅在 Astro 启用时创建
```

Astro 代码仍保持 `ZhouYi.Astro` 命名空间和独立目录边界；`ZHOUYILAB_ENABLE_ASTRO=OFF` 时不编译 Astro 源文件、不创建 CLI 和相关 Web 能力。后续若 CMake 支持跨目标共享标准库 BMI，再考虑拆分为独立 `ZhouYiLabAstro` 目标。

当 Astro 未启用时，`web/server.py` 的必需引擎列表不得包含 `astro_web_cli`；Astro 路由返回 `ENGINE_UNAVAILABLE` 或在能力元数据中标记为不可用，但不影响现有页面启动。启用 Astro 时才将 CLI 加入构建脚本、Docker 目标和启动检查。

### 4.3 线程和资源管理

Swiss Ephemeris 存在全局状态。适配层必须：

- 用进程级初始化对象管理一次性的 `swe_set_ephe_path`；`swe_close` 只在进程退出阶段调用，不在单次请求或临时对象析构时调用；
- 对计算调用使用进程级或库级互斥锁；
- 每次计算显式设置 flags、黄道和观测点，不依赖上一次请求留下的状态；
- 将错误码和错误文本转换为 `AstroError`，不让 C 字符串泄漏到 API 层；
- 禁止在请求线程中改变全局星历路径；路径变更必须重启 CLI 或服务。

CLI 是独立进程，因此 Web 层已经天然提供一层故障隔离。后续若改为常驻库调用，仍需保留互斥保护。

## 5. 数据模型

### 5.1 请求模型

```json
{
  "date": {
    "year": 1990,
    "month": 5,
    "day": 20,
    "hour": 14,
    "minute": 0,
    "second": 0
  },
  "utc_offset_minutes": 480,
  "location": {
    "latitude": 31.2304,
    "longitude": 121.4737,
    "elevation_m": 4.0
  },
  "zodiac": "tropical",
  "ayanamsa": "none",
  "house_system": "placidus",
  "points": ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto", "true_node", "chiron"],
  "include_aspects": true,
  "allow_moshier_fallback": false
}
```

校验规则：

- 日期和时间必须真实有效；
- 纬度范围 `[-90, 90]`，经度范围 `[-180, 180]`；
- 纬度为 ±90° 时拒绝 Placidus，其他高纬度情况以 Swiss 返回的宫位计算状态为准；
- 未提供地点时，首版拒绝本命盘请求，而不是返回缺少 ASC 的半成品；
- 点位 ID、黄道、岁差和宫制只能取 `meta` 公布的值；
- 当 `allow_moshier_fallback` 为 `false` 时，高精度文件不可用必须报错；为 `true` 时才允许返回 `precision_mode: "moshier"` 和警告。

### 5.2 响应模型

```json
{
  "chart_type": "natal",
  "input": {
    "utc_datetime": "1990-05-20T06:00:00Z",
    "utc_offset_minutes": 480,
    "latitude": 31.2304,
    "longitude": 121.4737,
    "zodiac": "tropical",
    "ayanamsa": "none",
    "house_system": "placidus"
  },
  "calculation": {
    "julian_day_ut": 2448031.75,
    "ephemeris": "swiss",
    "ephemeris_version": "<实际版本>",
    "precision_mode": "high",
    "warnings": []
  },
  "angles": {
    "ascendant": 123.456789,
    "midheaven": 234.567890,
    "descendant": 303.456789,
    "imum_coeli": 54.567890
  },
  "planets": [
    {
      "id": "sun",
      "name": "太阳",
      "longitude": 59.123456,
      "latitude": 0.001234,
      "distance_au": 1.012345,
      "longitude_speed": 0.985600,
      "sign": "gemini",
      "sign_name": "双子座",
      "degree_in_sign": 29.123456,
      "house": 10,
      "retrograde": false,
      "stationary": false
    }
  ],
  "houses": [
    {"number": 1, "cusp": 123.456789, "sign": "leo", "sign_name": "狮子座"}
  ],
  "aspects": []
}
```

数值字段保留原始浮点精度，展示层再格式化为度分秒。稳定 ID 使用英文枚举，中文名称仅用于展示，避免客户端依赖中文文本。

字段单位固定为：角度为度（°），速度为度/日（°/day），距离为天文单位（AU），高度为米。位数和误差阈值由测试规范和版本策略明确，不由前端自行猜测。

## 6. API 设计

### 6.1 元数据

`GET /api/v1/astro/meta`

返回：

- API 和算法版本；
- 可用点位；
- 支持的黄道、岁差和宫制；
- 支持的相位和默认容许度；
- 当前星历模式（Swiss 高精度/Moshier）；
- 星历目录是否可用；
- 许可证提示和构建特性。

### 6.2 本命盘

`POST /api/v1/astro/charts`

请求体为第 5.1 节模型，成功时沿用现有响应封装：

```json
{
  "success": true,
  "data": {"chart_type": "natal"},
  "meta": {
    "api_version": "v1",
    "algorithm_version": "zhouyilab-astro/<version>",
    "request_id": "..."
  }
}
```

错误码至少包括：

| 错误码 | HTTP | 场景 |
| --- | ---: | --- |
| `INVALID_REQUEST` | 400 | 字段缺失或范围错误 |
| `EPHEMERIS_UNAVAILABLE` | 422 | 高精度星历文件不可用 |
| `HOUSE_CALCULATION_FAILED` | 422 | 当前纬度和宫制无法计算 |
| `CALCULATION_TIMEOUT` | 504 | CLI 计算超时 |
| `CALCULATION_FAILED` | 422 | Swiss Ephemeris 返回计算错误 |
| `ENGINE_UNAVAILABLE` | 500 | `astro_web_cli` 尚未构建 |

### 6.3 健康检查

`GET /api/v1/health` 新增：

其中 `astro_ephemeris_available` 专指高精度 Swiss 星历文件和目录是否可用；Moshier 内置模式可用不代表该字段为 `true`。

```json
{
  "astro_cli_available": true,
  "astro_ephemeris_available": true
}
```

原有字段不删除、不改语义。

## 7. CLI、Web 和部署

### 7.1 CLI

新增 `examples/astro_web_cli.cpp`，遵循现有 CLI 约定：

- 从 stdin 读取一个 JSON 对象；
- stdout 只输出一个 JSON 对象；
- 错误输出到 JSON 的 `error.code` 和 `error.message`；
- 不把日志写入 stdout；
- CMake 目标名为 `astro_web_cli`。

`build.sh` 和 Docker 构建目标增加该 CLI。

### 7.2 Web 页面

新增：

```text
web/astro.html
web/astro.js
web/astro.css（若现有共享样式不足）
```

首版页面包含：出生时间、UTC 偏移、经纬度、宫制、黄道、点位选择、提交状态、星体列表、四轴、十二宫和相位表。盘面可视化不是首版验收前提，可先以结构化列表呈现。

页面必须同步更新 `web/index.html` 和 `web/navigation.js` 的入口，不将 Astro 页面做成孤立文件。

### 7.3 Docker 和本地运行

- Builder 阶段安装/编译 Swiss Ephemeris；
- Runtime 阶段复制 `astro_web_cli`；
- 星历文件通过镜像内只读目录或外部 volume 提供；
- 启动时不因缺少可选小行星文件而阻止太阳系主要行星计算；
- 高精度星历不可用时，默认拒绝静默降级；只有请求显式允许时才使用 Moshier。

Astro 关闭时 Docker 仍按现有五个 Web CLI 构建和启动；不应因为未提供星历文件而使现有术数功能不可用。

## 8. 许可证和发布决策

Swiss Ephemeris 为 AGPL/商业许可证双授权。当前仓库为 MIT，静态链接 Swiss Ephemeris 后不能继续简单地把整个发布物声明为纯 MIT。

如采用第 4.2.1 节的目标隔离，`ZhouYiLabCore` 及未启用 Astro 的现有可执行文件可以继续按项目 MIT 许可发布；`ZhouYiLabAstro` 、`astro_web_cli` 和包含它们的部署物必须按所选 Swiss 许可证标注和履行义务。这是技术隔离方案，不代替法务判断。

在代码执行前必须选择：

1. **AGPL 路线**：保留源码和对应许可证声明，发布组合程序时履行 AGPL 义务；
2. **商业路线**：取得 Swiss Ephemeris 商业许可证，保留采购凭证和版本范围；
3. **隔离服务路线**：将星历计算做成单独服务/进程，但仍需由法务确认组合发布和网络服务场景的许可证义务。

开发阶段可以先使用 AGPL 版本完成技术验证，但未作许可证选择前，不进入正式发布和 Docker Hub 推送。

## 9. 测试和校准

### 9.1 单元测试

- UTC 转换和 Julian Day；
- 角度归一化、星座和度数边界；
- 逆行、停滞和速度符号；
- 宫位排序、跨 0° 宫头；
- 相位夹角和容许度；
- 非法日期、非法经纬度和高纬度宫位错误。

### 9.2 金标准案例

建立固定 JSON fixture，使用同一 Swiss Ephemeris 版本生成期望值，至少覆盖：

- 常规中纬度本命盘；
- 经度跨东/西半球；
- 日期跨 UTC 日界线；
- 行星逆行和停滞附近；
- Placidus 失败并切换 Whole Sign；
- 可选星历文件缺失。

角度比较使用明确的绝对误差阈值；版本升级时必须生成差异报告，不能直接覆盖旧 fixture。

### 9.3 接口和页面验收

- CLI 输出可被 `json.loads` 解析；
- API 错误不会泄漏 C 库内部指针或路径信息；
- `/api/v1/health` 能区分 CLI 不可用和星历文件不可用；
- 页面在 375px、768px、1440px 下无横向滚动；
- 输入、结果和错误状态可通过键盘完成；
- Docker 从干净环境构建并通过健康检查。

## 10. 分阶段交付

### 阶段 A：依赖和许可证验证

- 固定 Swiss Ephemeris 上游版本；
- 验证 macOS Clang、Linux Clang、Docker Ubuntu 24.04 构建；
- 确认 `.se1` 文件分发方式；
- 完成许可证选择和 NOTICE 文件方案。

### 阶段 B：核心计算模块

- 完成 C API 适配、RAII 和线程保护；
- 完成时间、行星、四轴、宫位、相位数据模型；
- 添加金标准和边界单元测试；
- 交付可独立调用的 `ZhouYi.Astro.Controller`。

### 阶段 C：CLI、API 和健康检查

- 增加 `astro_web_cli`；
- 增加 `/api/v1/astro/meta` 和 `/api/v1/astro/charts`；
- 更新 `health`、构建脚本和 Docker；
- 补充 API 契约测试。

### 阶段 D：Web 页面和文档

- 增加西洋占星页面和导航入口；
- 显示计算口径、星历版本和警告；
- 更新 README、API 文档和发布说明；
- 完成人工验收后再进入版本规划。

## 11. 待确认决策

以下项目在实现前需要确认；若没有特别指定，建议采用“推荐值”：

| 决策项 | 推荐值 | 影响 |
| --- | --- | --- |
| 许可证 | 先完成 AGPL 技术验证，发布前选择 AGPL 或商业授权 | 决定源码和镜像发布方式 |
| 时间输入 | 公历当地时间 + 显式 UTC 偏移 | 首版不依赖平台时区数据库 |
| 黄道 | 热带黄道 | 与主流西占默认口径一致 |
| 宫制 | Placidus，失败时由用户选择 Whole Sign | 不静默改变算法口径 |
| 首版点位 | 十大行星 + 真实北交点 | 控制星历文件和测试范围 |
| 首版页面 | 结构化结果表，盘面图后置 | 先验证计算契约 |
| 解释能力 | 首版不做 | 保持星历与解读职责分离 |

## 12. 完成定义

- 核心模块、CLI、API、页面、Docker 和文档均有对应交付物。
- 所有公开字段有稳定 ID、单位、范围和版本说明。
- 金标准案例在支持的平台上通过，差异有记录。
- 高精度星历不可用、宫位失败和非法输入均有可操作错误。
- 请求中的精度模式、降级意图和警告在响应中可追溯。
- Swiss Ephemeris 许可证、星历文件来源和 NOTICE 已纳入发布检查清单。
- README、API 文档和健康检查反映实际能力，不宣称尚未完成的解释或校准能力。
