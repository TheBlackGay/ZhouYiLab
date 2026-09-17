# ZhouYiLab - 周易实验室

基于 C++23 Modules 的传统术数算法库，同时提供本地 Web 界面、JSON API、声明式紫微格局引擎与研究评审工具。

[![C++23](https://img.shields.io/badge/C%2B%2B-23-blue.svg)](https://en.cppreference.com/w/cpp/23)
[![CMake](https://img.shields.io/badge/CMake-3.28%2B-green.svg)](https://cmake.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

当前开发分支为 `r_1.6.0`，HTTP API 版本为 `v1`，接口返回的算法标识为 `zhouyilab-core/1.4.1`。

## 算法校准状态

本项目正在逐项复核各术数算法。这里的“已有实现”和“已经校准”是两个不同状态：已有代码只表示能够运行；已经校准表示当前版本已针对原有错误进行修正，并按照项目确认的规则口径完成案例回归。

当前状态：

| 算法 | 校准状态 | 说明 |
| --- | --- | --- |
| 紫微斗数 | 已校准 | 已复核排盘、亮度、四化、运限和声明式格局规则，修正原有错误并建立结构化案例验证 |
| 奇门遁甲 | 已校准 | 已重新校正原有起局实现，当前采用项目文档确认的拆补法时家转盘口径，并建立回归测试 |
| 八字 | 校准中 | 已复核真太阳时、四柱基础字段、起运及首批《渊海子平》《三命通会》神煞；旺衰、喜忌与格局仍待校准 |
| 六爻 | 待校准 | 现有 C++ 模块和示例可运行，不代表算法口径已经完成复核 |
| 大六壬 | 待校准 | 现有 C++ 模块和示例可运行，不代表算法口径已经完成复核 |

后续版本将继续校准其他算法。每项算法完成校准后，需要同步补充规则口径、边界案例、回归测试和对应文档，再将状态改为“已校准”。

## 当前能力

| 模块 | 状态 | 主要能力 |
| --- | --- | --- |
| 紫微斗数 | 可用 | 本命盘、真太阳时、大限、小限、流年、流月、流日、流时、四化、神煞与亮度 |
| 紫微结构解读 | 可用 | 十二宫结构化碎片、三方四正证据、格局归属、成格/增强/减弱/破格状态 |
| 紫微格局引擎 | 可用 | 39 条声明式规则配置，逐宫匹配、条件追踪、规则库清单与未命中展示 |
| 奇门遁甲 | 可用 | 拆补法时家转盘奇门、公历/农历起局、九宫盘、直符直使与学习提示 |
| 紫微盲评研究 | 可用 | 匿名盲评包、维度量尺、协议与一致性研究配置 |
| AI 多模型预评审 | 实验性 | Ollama/OpenAI 兼容接口、多模型重复实验、结果统计与 SQLite 留档 |
| 八字 | 初步可用 | 公历/农历输入、真太阳时、四柱、十神、藏干、十二长生、逐柱旬空、纳音、首批神煞、起运与十步大运 |
| 西洋占星 | 实验性 | Swiss Ephemeris 本命盘、主要行星、四轴、十二宫、主要相位和 Moshier 降级提示 |
| 六爻、大六壬 | C++ 示例 | 核心模块与示例程序 |

## 快速开始

### 1. 获取源码

```bash
git clone --recursive https://github.com/TheBlackGay/ZhouYiLab.git
cd ZhouYiLab
```

已有仓库缺少子模块时执行：

```bash
git submodule update --init --recursive
```

### 2. 构建网页计算引擎

网页服务依赖六个 C++ JSON CLI。项目根目录的 `build.sh` 会自动配置并构建它们：

```bash
./build.sh
```

构建产物：

```text
build/examples/zi_wei_web_cli
build/examples/qi_men_web_cli
build/examples/ba_zi_web_cli
build/examples/liu_yao_web_cli
build/examples/da_liu_ren_web_cli
build/examples/common_calendar_web_cli
```

如需构建所有示例：

```bash
cmake --build build --target all_examples
```

### 3. 启动本地服务

项目根目录提供了服务管理脚本，默认使用 `8768` 端口：

```bash
./start.sh
./stop.sh
./restart.sh
```

也可以使用统一入口：

```bash
./manage.sh build
./manage.sh start
./manage.sh restart
./manage.sh stop
./manage.sh status
```

启动后访问：

- 紫微斗数：[http://127.0.0.1:8768/](http://127.0.0.1:8768/)
- 奇门遁甲：[http://127.0.0.1:8768/qimen.html](http://127.0.0.1:8768/qimen.html)
- 八字：[http://127.0.0.1:8768/bazi.html](http://127.0.0.1:8768/bazi.html)
- 六爻：[http://127.0.0.1:8768/liu-yao.html](http://127.0.0.1:8768/liu-yao.html)
- 大六壬：[http://127.0.0.1:8768/da-liu-ren.html](http://127.0.0.1:8768/da-liu-ren.html)
- 西洋占星：[http://127.0.0.1:8768/astro.html](http://127.0.0.1:8768/astro.html)
- 人工盲评：[http://127.0.0.1:8768/blind-review.html](http://127.0.0.1:8768/blind-review.html)
- AI 预评审：[http://127.0.0.1:8768/ai-review.html](http://127.0.0.1:8768/ai-review.html)

运行时文件位于 `.zhouyilab/`：

```text
.zhouyilab/server.pid
.zhouyilab/server.log
.zhouyilab/research/ai_review.sqlite3
```

自定义端口：

```bash
ZHOUYILAB_PORT=9000 ./start.sh
```

也可以直接运行 Python 服务；其命令行默认端口为 `8765`：

```bash
python3 web/server.py --port 8768
```

### Docker 部署

项目提供多阶段 `Dockerfile` 和 `docker-compose.yml`。以下命令均在项目根目录执行，需要 Docker Engine 24+ 和 Docker Compose v2+。

#### 部署到 192.168.31.183

项目提供固定部署脚本 `scripts/deploy-zhouyilab-183.sh`，默认使用
`/opt/app/zhouyilab`、`1panel-network` 和端口 `8768`：

```bash
./scripts/deploy-zhouyilab-183.sh
```

脚本使用 SSH/rsync 认证，不保存服务器密码；建议提前配置 SSH 公钥登录。
如需临时覆盖端口或目标目录，可通过 `ZHOUYILAB_DEPLOY_PORT`、
`ZHOUYILAB_DEPLOY_DIR` 等同名环境变量覆盖默认值。

#### 从源码构建并启动

```bash
docker compose up -d --build
```

该命令会编译 C++ 计算引擎、构建镜像并启动容器。启动后访问 `http://127.0.0.1:8768/`，持久化数据保存在 Compose volume `zhouyilab-data` 中。

生产环境统一访问地址为 `https://zhouyilab.k8s.gold`；其他项目接入时请以该域名作为 API Base URL。

查看容器状态和日志：

```bash
docker compose ps
docker compose logs -f zhouyilab
```

停止、重启和移除容器：

```bash
docker compose stop
docker compose restart
docker compose down
```

#### 构建并推送 Docker Hub 镜像

镜像仓库为 `1047028213/zhouyilab`：

```bash
docker login -u 1047028213
docker build -t 1047028213/zhouyilab:latest .
docker push 1047028213/zhouyilab:latest
```

建议同时发布版本标签：

```bash
docker build -t 1047028213/zhouyilab:1.6.0 -t 1047028213/zhouyilab:latest .
docker push 1047028213/zhouyilab:1.6.0
docker push 1047028213/zhouyilab:latest
```

#### 使用 Docker Hub 镜像部署

在目标服务器安装 Docker 后，拉取并启动最新镜像：

```bash
docker login -u 1047028213
docker compose pull
docker compose up -d
```

只使用 Docker CLI 运行（不使用 Compose）：

```bash
docker pull 1047028213/zhouyilab:latest
docker volume create zhouyilab-data
docker run -d --name zhouyilab \
  --restart unless-stopped \
  -p 8768:8768 \
  -v zhouyilab-data:/app/.zhouyilab \
  1047028213/zhouyilab:latest
```

查看运行状态：

```bash
docker ps
curl http://127.0.0.1:8768/api/v1/health
```

更新镜像并重新部署：

```bash
docker compose pull
docker compose up -d
docker image prune -f
```

自定义宿主机端口（容器内部仍使用 `8768`）：

```bash
ZHOUYILAB_PORT=9000 docker compose up -d
```

此时访问 `http://127.0.0.1:9000/`。如果服务器通过公网访问，请在防火墙或安全组中放行对应端口。

### 2.x 产品规划

- [2.x 版本路线图](docs/product/ZhouYiLab-2.x-版本路线图.md)
- [2.0.0 需求规格](docs/product/ZhouYiLab-2.0.0-需求规格.md)
- [2.0.0 产品规划头脑风暴](docs/product/ZhouYiLab-2.0.0-产品规划头脑风暴.md)
- [西洋占星生活化解析设计方案](docs/product/西洋占星生活化解析设计方案.md)

## 页面说明

### 紫微斗数

主页提供四个结果视图：

- `十二宫`：本命盘及大限、流年、流月、流日、流时叠加展示。
- `结构解读`：本命十二宫结构化分析、全盘格局命中和规则库核对。
- `运限`：目标日期对应的运限层级与星曜。
- `时间校正`：真太阳时、经度校正、均时差与跨日信息。

格局页面会区分：

- 当前命盘实际命中的格局数量。
- 规则库中全部已加载规则。
- 成格、增强、减弱、破格和倾向状态。
- 必要条件、命中子型、关键星位、煞曜与破格证据。
- 未命中但已加载的规则。

当前结构解读只执行 `natal` 本命层。配置支持其他盘层不代表页面已经对该层执行结构分析。

### 奇门遁甲

当前实现采用拆补法时家转盘奇门，支持：

- 公历或农历输入，包含闰月标记。
- 阴遁/阳遁、三元、局数和节气。
- 九星、八门、八神、天盘干、地盘干。
- 甲时旬首遁藏、中五寄坤二、天禽随天芮等当前算法口径。
- 宫位学习提示和结构化 JSON 输出。

### 八字

八字页面沿用独立排盘工具的交互方式，当前支持：

- 公历、农历与闰月输入。
- 与紫微斗数共用经度、均时差和夏令时真太阳时校正，并显示实际排盘时间与跨日状态。
- 男女命顺逆排运。
- 年、月、日、时四柱及阴阳五行。
- 天干十神、地支藏干及对应十神。
- 星运、自坐十二长生、逐柱旬空与六十甲子纳音。
- 首批《渊海子平》《三命通会》口径神煞，按四柱分别展示；童子煞明确标注为后世民间兼容规则。
- 起运年龄、精确交运时刻与十步大运。

当前页面只呈现已经校准的排盘事实。八字仍处于校准阶段，格局、旺衰、喜忌和命理断语暂不接入页面。

## HTTP API

服务只监听 `127.0.0.1`，API 使用统一响应结构：

```json
{
  "success": true,
  "data": {},
  "meta": {
    "api_version": "v1",
    "algorithm_version": "zhouyilab-core/1.4.1",
    "request_id": "..."
  }
}
```

主要接口：

对外生产 API Base URL：`https://zhouyilab.k8s.gold`。下表中的接口路径均拼接在该 Base URL 后使用；内网直连地址为 `http://192.168.31.183:8768`，本地开发地址按启动参数为 `http://127.0.0.1:8765` 或 `http://127.0.0.1:8768`。

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/v1/health` | 服务及 C++ 引擎健康状态 |
| POST | `/api/v1/calendar/convert` | 公历/农历互转 |
| POST | `/api/v1/calendar/true-solar-time` | 通用真太阳时计算 |
| GET | `/api/v1/ziwei/meta` | 紫微接口能力和版本信息 |
| POST | `/api/v1/ziwei/time-correction` | 真太阳时校正 |
| POST | `/api/v1/ziwei/charts` | 生成紫微本命盘 |
| POST | `/api/v1/ziwei/fortune` | 生成紫微命盘及运限 |
| POST | `/api/v1/ziwei/analysis` | 生成本命结构解读与格局结果 |
| POST | `/api/v1/qimen/charts` | 生成奇门遁甲盘 |
| POST | `/api/v1/bazi/charts` | 生成八字四柱与大运 |
| GET | `/api/v1/astro/meta` | 西洋占星能力和版本信息 |
| POST | `/api/v1/astro/charts` | 使用 Swiss Ephemeris 生成西洋星盘 |
| POST | `/api/v1/astro/transits` | 计算指定时刻的行运事实包 |
| POST | `/api/v1/astro/analysis` | 基于结构化星盘和规则库生成证据分析包 |
| POST | `/api/v1/astro/transit-analysis` | 将行运事实映射为生活领域信号，不生成文案或评分 |
| POST | `/api/v1/astro/daily-reading` | 将生活领域信号渲染为无评分日运解析包 |
| GET | `/api/v1/ziwei/research/blind-review/packet` | 生成匿名盲评包 |
| GET/POST | `/api/v1/ziwei/research/ai-review/*` | AI 预评审配置、实验和结果 |

紫微本命盘示例：

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
      "longitude": 120.3,
      "standard_meridian": 120,
      "daylight_saving_minutes": 0
    }
  }' \
  http://127.0.0.1:8768/api/v1/ziwei/charts
```

完整请求和响应契约见：

- [紫微斗数 HTTP 接口文档](docs/ziwei/紫微斗数HTTP接口文档.md)
- [公共日历 API 文档](docs/common/公共日历API.md)
- [奇门遁甲 HTTP 接口文档](docs/奇门遁甲HTTP接口文档.md)
- [西洋占星 HTTP 接口文档](docs/astro/西洋占星HTTP接口文档.md)
- [统一 HTTP 接口访问地址](docs/HTTP接口访问地址.md)
- [Swiss Ephemeris 集成设计与 Astro 接口契约](docs/astro/Swiss-Ephemeris-集成设计.md)

Astro 默认使用项目内置的高精度星历文件 `data/ephemeris/*.se1`。健康检查中的
`astro_ephemeris_available` 为 `true` 时，未开启 Moshier 降级的请求会使用 Swiss
高精度模式；部署时请勿删除该目录。

## 紫微格局引擎

格局规则位于 `config/ziwei/patterns/`，每个格局使用独立 JSON 文件。清单与 schema：

```text
config/ziwei/patterns/_manifest.json
config/ziwei/patterns/pattern.schema.json
```

规则可以声明：

- 适用盘层和目标宫位。
- 命宫、身宫、三合、对宫与夹宫条件。
- 星曜、亮度、四化、出生年干和外部诊断字段。
- 必要条件、增益、减弱、破格和普通宫位观察。
- 格局档位、输出标记、关键星位和条件证据。
- 配置内置的正向、反向与边界案例。

规则引擎会校验配置字段、星曜名称、谓词、重复 ID 和清单数量，并在分析结果中返回完整条件追踪。旧 C++ `ge_ju` 字段仅为接口兼容，不是结构解读的判定权威来源。

## AI 预评审配置

AI 服务连接从本机配置读取：

```text
config/ziwei/research/ai_model_providers.local.json
```

该文件已被 Git 忽略。可以配置：

- 本地 Ollama。
- OpenAI、DeepSeek、LM Studio、vLLM 等 OpenAI 兼容接口。
- 每个模型的重复次数、温度和随机种子。
- API Key 明文或环境变量名。

不要把真实 API Key 写入已跟踪的 `ai_model_providers.json`。

详细说明见 [AI 多模型定性预评审平台](docs/ziwei/research/AI多模型定性预评审平台-v0.1.md)。

## 构建要求

- CMake `3.28+`。
- 支持 C++23 Modules 的编译器。
- Python 3，用于本地 HTTP 服务、结构分析和研究工具。
- Git，用于初始化第三方子模块。

主要第三方依赖通过 Git submodule 管理：

| 依赖 | 用途 |
| --- | --- |
| `fmt` | C++ 格式化 |
| `magic_enum` | 编译期枚举反射 |
| `nlohmann/json` | JSON 序列化 |
| `tyme4cpp` | 公历、农历、干支和节气 |

项目支持 `ZHOUYILAB_MODULE_MODE=AUTO|LOCAL|SHARED`。默认 `AUTO` 会在共享预编译模块可用时复用，否则本地构建。

## 测试与校验

Python 测试：

```bash
python3 -m unittest discover -s tests -q
```

格局配置内置案例：

```bash
python3 - <<'PY'
from pathlib import Path
import sys

sys.path.insert(0, "web")
from ziwei_pattern_engine import load_pattern_catalog, run_catalog_examples

catalog = load_pattern_catalog(Path("config/ziwei/patterns"))
failures = [case for case in run_catalog_examples(catalog) if not case["passed"]]
print({"pattern_count": len(catalog["patterns"]), "failures": failures})
PY
```

基础语法检查：

```bash
python3 -m py_compile web/*.py
node --check web/app.js
git diff --check
```

## 项目结构

```text
ZhouYiLab/
├── 3rdparty/                 # Git 子模块依赖
├── cmake/                    # C++ Modules 构建支持
├── config/
│   └── ziwei/
│       ├── patterns/        # 声明式格局配置
│       ├── research/        # 盲评与 AI 预评审协议
│       ├── symbolism_dictionary.json
│       └── star_brightness.json
├── docs/                     # API、算法和研究文档
├── examples/                 # 示例与 Web JSON CLI
├── src/
│   ├── ba_zi/
│   ├── da_liu_ren/
│   ├── liu_yao/
│   ├── qi_men/
│   └── zi_wei/
├── tests/                    # Python 回归测试
├── web/                      # 本地页面、API 与分析服务
├── start.sh
├── stop.sh
└── restart.sh
```

## 设计原则

- C++ 核心算法与 Python 分析层分离。
- 盘面事实、格局规则和语言表达分层。
- 格局规则声明化，条件和证据可追踪。
- AI 只允许组织已有事实，不得重新排盘或发明格局。
- 不同流派口径需要显式写入配置和规则说明。
- 古籍断语用于规则来源说明，不转换为现实事件保证。

## 相关文档

- [模块说明](MODULES.md)
- [紫微斗数命盘与运限分析准则](docs/ziwei/紫微斗数命盘与运限分析准则.md)
- [紫微斗数安星诀](docs/紫微斗数-安星决.md)
- [奇门遁甲起课步骤](docs/奇门遁甲起课%20步骤.md)
- [盲评与一致性分析方案](docs/ziwei/research/盲评与一致性分析方案-v0.1.md)
- [紫微斗数星曜作用模型研究协议](docs/ziwei/research/紫微斗数星曜作用模型研究协议-v0.1.md)

## 许可证

本项目采用 [MIT License](LICENSE)。

商务合作微信（备注“周易实验室”）：`17306666568`

Java 版本相关项目：[https://www.mingtugps.cn/discover](https://www.mingtugps.cn/discover)
