# ZhouYiLab - 周易实验室

基于 C++23 Modules 的传统术数算法库，同时提供本地 Web 界面、JSON API、声明式紫微格局引擎与研究评审工具。

[![C++23](https://img.shields.io/badge/C%2B%2B-23-blue.svg)](https://en.cppreference.com/w/cpp/23)
[![CMake](https://img.shields.io/badge/CMake-3.28%2B-green.svg)](https://cmake.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

当前开发分支为 `r_3.0.0`（首发版本 **3.0.0**，2026-09-20 分支归并后单线推进），HTTP API 版本为 `v1`，接口返回的算法标识为 `zhouyilab-core/2.0.0`。

## 算法校准状态

本项目正在逐项复核各术数算法。这里的“已有实现”和“已经校准”是两个不同状态：已有代码只表示能够运行；已经校准表示当前版本已针对原有错误进行修正，并按照项目确认的规则口径完成案例回归。

当前状态：

| 算法 | 校准状态 | 说明 |
| --- | --- | --- |
| 紫微斗数 | 已校准 | 本命与运限按确认口径复核：大限宫干五虎遁重排经案例回归验证（丁年命宫甲辰→癸卯/壬寅；甲年命宫丙寅→丁卯/戊辰，2026-09-19）；本命闰月默认十五分界（《斗数宣微》口径），人生轨迹反推案例为后续任务；旧巡运口径保留 `daxian_gan_method=original` 对照 |
| 奇门遁甲 | 已校准 | 已重新校正原有起局实现，当前采用项目文档确认的拆补法时家转盘口径，并建立回归测试 |
| 八字 | 校准中 | 已复核真太阳时、四柱基础字段、起运及首批《渊海子平》《三命通会》神煞；旺衰、喜忌与格局仍待校准 |
| 六爻 | 校准中 | 算法口径已确认以《增删卜易》为主（D1=A，2026-09-20）：旺衰五态月令表按通行表修复（DEF-4）、进退神收窄为子化丑/巳化午进、丑化子/午化巳退四对；伏神章原文校勘与案例回归进行中 |
| 大六壬 | 待校准 | 2.0.0 已提供页面、结构化接口与逐项规则口径标识（`meta.rule_profile`）；盘面事实可追溯，算法口径仍待复核，不输出断语 |
| 梅花易数 | 待校准 | 2026-09-20 立项（D6/D13）：时间/报数起卦 + 体用互变事实盘（`meihua-plate/1.0`，`meihua-rules/0.1`）；书例"丙辰年腊十七申时→泽火革"锁测试通过；断语层待案例校准后评审接入 |

后续版本将继续校准其他算法。每项算法完成校准后，需要同步补充规则口径、边界案例、回归测试和对应文档，再将状态改为“已校准”。

## 当前能力

| 模块 | 状态 | 主要能力 |
| --- | --- | --- |
| 紫微斗数 | 可用 | 本命盘、真太阳时、大限、小限、流年、流月、流日、流时、四化、神煞与亮度 |
| 紫微结构解读 | 可用 | 十二宫结构化碎片、三方四正证据、格局归属、成格/增强/减弱/破格状态 |
| 分布画像（人性化） | 可用 | 六平台同款图表数据包 API（`/api/v1/<模块>/distribution`）：西洋占星/紫微/八字/六爻/梅花/大六壬，三环形图 + 暖场解读 + 整体底色总结；图示数据一律源自内核事实字段，梅花侧带运行时内核交叉锁（漂移拒出图） |
| 紫微格局引擎 | 可用 | 39 条声明式规则配置，逐宫匹配、条件追踪、规则库清单与未命中展示 |
| 奇门遁甲 | 可用 | 拆补法时家转盘奇门、公历/农历起局、九宫盘、直符直使与学习提示 |
| 紫微盲评研究 | 可用 | 匿名盲评包、维度量尺、协议与一致性研究配置 |
| AI 多模型预评审 | 实验性 | Ollama/OpenAI 兼容接口、多模型重复实验、结果统计与 SQLite 留档 |
| 八字 | 初步可用 | 公历/农历输入、真太阳时、四柱、十神、藏干、十二长生、逐柱旬空、纳音、首批神煞、起运与十步大运 |
| 西洋占星 | 实验性 | Swiss Ephemeris 本命盘、主要行星、四轴、十二宫、主要相位、黄道与宫位布局速读、逐点位/十二宫/相位解读卡片和 Moshier 降级提示 |
| 大六壬 | 2.1.0 开发中 | 快速/专业双模式、问题上下文、术语口径弹层、`meta.rule_profile` 规则口径；2.1.0 新增天地盘 SVG 可视化（十二宫位、上神/神将/遁干/三传徽章/旬空）；算法仍待校准，不断吉凶 |
| 六爻 | 页面可用 | 排盘含纳甲/六神/伏神/旺衰/变卦、摇卦模拟器与 AI 素材导出；口径已定（《增删卜易》为主，D1=A），案例校准中 |
| 梅花易数 | 页面可用 | 时间/报数起卦，本互变三卦、体用生克与月令旺衰事实盘（M1-M2）+ 体用分布画像（M4）+ 盘面事实案例库 staged（M3）；书例校勘进行中；断语未上线 |

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
- 梅花易数：[http://127.0.0.1:8768/meihua.html](http://127.0.0.1:8768/meihua.html)
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

#### 一键部署到 10.10.8.99

本机已配置 SSH 别名 `cloud-deploy-99` 时，在项目根目录执行：

```bash
./scripts/deploy-zhouyilab-99.sh
```

脚本会同步当前代码到 `/home/h3c/zhouyilab`，在服务器上重新构建并启动容器，
最后检查 `/api/v1/health`。可用环境变量覆盖默认目标：

```bash
ZHOUYILAB_DEPLOY_HOST=cloud-deploy-99 \
ZHOUYILAB_DEPLOY_DIR=/home/h3c/zhouyilab \
ZHOUYILAB_DEPLOY_PORT=8768 \
./scripts/deploy-zhouyilab-99.sh
```

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

#### 构建并推送阿里云 Container Registry 镜像

以下命令使用阿里云个人版 Container Registry。登录密码请按阿里云提示输入，
不要把密码写入命令或提交到仓库。

```bash
docker login --username=tb63126440 crpi-ip3van137b8rcj4d.cn-hangzhou.personal.cr.aliyuncs.com
docker build --build-arg BUILD_JOBS=auto -t tb63126440/zhouyilab:3.0.0 .
docker tag tb63126440/zhouyilab:3.0.0 crpi-ip3van137b8rcj4d.cn-hangzhou.personal.cr.aliyuncs.com/zhuifengderen/zhouyilab:3.0.0
docker push crpi-ip3van137b8rcj4d.cn-hangzhou.personal.cr.aliyuncs.com/zhuifengderen/zhouyilab:3.0.0
```

如果基础镜像下载较慢，可先配置 Docker 镜像加速器，或将基础镜像同步到可访问的仓库后替换：

```bash
docker build --build-arg BUILDER_IMAGE=<你的镜像仓库>/silkeh/clang:20 \
  --build-arg RUNTIME_IMAGE=<你的镜像仓库>/ubuntu:24.04 \
  --build-arg BUILD_JOBS=auto -t tb63126440/zhouyilab:3.0.0 .
```

> `BUILD_JOBS=auto` 会使用容器可见的 CPU 核数；内存较小的机器可改为 `BUILD_JOBS=2`。

#### 他人部署（使用已发布镜像）

部署者只需要一台安装 Docker Engine 24+ 和 Docker Compose v2+ 的服务器，
不需要安装 C++、CMake 或 Python。先获取 Compose 配置：

```bash
git clone --depth 1 https://github.com/TheBlackGay/ZhouYiLab.git
cd ZhouYiLab
```

该 ACR 仓库如果设置为私有，需要每位部署者使用自己的阿里云账号登录；密码按终端提示输入，
不要写入脚本或提交到仓库。然后拉取并启动已发布镜像：

```bash
export ZHOUYILAB_IMAGE=crpi-ip3van137b8rcj4d.cn-hangzhou.personal.cr.aliyuncs.com/zhuifengderen/zhouyilab:3.0.0
docker login --username=tb63126440 crpi-ip3van137b8rcj4d.cn-hangzhou.personal.cr.aliyuncs.com
docker compose pull
docker compose up -d --no-build
```

启动后访问 `http://服务器IP:8768/`，或检查健康接口：

```bash
curl http://127.0.0.1:8768/api/v1/health
```

如果宿主机的 `8768` 端口已被占用，可以换端口：

```bash
ZHOUYILAB_PORT=9000 docker compose up -d --no-build
```

此时访问 `http://服务器IP:9000/`。公网部署还需要在防火墙或安全组放行对应端口。

只使用 Docker CLI 运行（不使用 Compose）：

```bash
docker pull crpi-ip3van137b8rcj4d.cn-hangzhou.personal.cr.aliyuncs.com/zhuifengderen/zhouyilab:3.0.0
docker volume create zhouyilab-data
docker run -d --name zhouyilab \
  --restart unless-stopped \
  -p 8768:8768 \
  -v zhouyilab-data:/app/.zhouyilab \
  crpi-ip3van137b8rcj4d.cn-hangzhou.personal.cr.aliyuncs.com/zhuifengderen/zhouyilab:3.0.0
```

查看运行状态：

```bash
docker ps
curl http://127.0.0.1:8768/api/v1/health
```

更新镜像并重新部署：

```bash
docker compose pull
docker compose up -d --no-build
docker image prune -f
```

### 2.x 产品规划

- [2.x 版本路线图](docs/product/ZhouYiLab-2.x-版本路线图.md)
- [2.0.0 需求规格](docs/product/ZhouYiLab-2.0.0-需求规格.md)
- [2.0.0 产品规划头脑风暴](docs/product/ZhouYiLab-2.0.0-产品规划头脑风暴.md)
- [西洋占星生活化解析设计方案](docs/product/西洋占星生活化解析设计方案.md)
- [西洋占星本命盘布局解读设计方案（已实现归档）](docs/product/archive/西洋占星本命盘布局解读设计方案.md)

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

### 大六壬

2.0.0 把大六壬做成易用样板：

- 输入支持公历/农历/闰月、一键当前时间与示例时间，时辰下拉显式标注早子/夜子换日口径；
- 问题类型与描述只保留在页面，不发送给服务；
- 小白模式展示四柱、月将、贵人、本课重点与 起因→发展→归结 三传流程，不给吉凶断语；
- 专业模式提供四课、三传详情（遁干/六亲）、天地盘十二位表、神煞卦体与**规则口径**页签；
- 术语弹层由 `config/daliuren/glossary.json` 驱动，每条注明当前实现口径；
- 接口响应携带 `meta.rule_profile`（`calibration_status: pending`，算法校准前不伪装已完成）。

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
    "algorithm_version": "zhouyilab-core/2.0.0",
    "request_id": "..."
  }
}
```

主要接口：

对外生产 API Base URL：`https://zhouyilab.k8s.gold`。下表中的接口路径均拼接在该 Base URL 后使用；内网直连地址为 `http://192.168.31.183:8768`，本地开发地址按启动参数为 `http://127.0.0.1:8765` 或 `http://127.0.0.1:8768`。

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/v1` | 平台发现端点：工具→路由→页面→接口文档→可见性索引 |
| GET | `/api/v1/health` | 服务及 C++ 引擎健康状态（含各工具校准状态） |
| GET | `/api/v1/tools` | 平台工具注册清单（manifest、路由、引擎可用性） |
| POST | `/api/v1/calendar/convert` | 公历/农历互转 |
| POST | `/api/v1/calendar/true-solar-time` | 通用真太阳时计算 |
| GET | `/api/v1/ziwei/meta` | 紫微接口能力和版本信息 |
| GET | `/api/v1/ziwei/symbols` | 内核权威符号字典（星曜、亮度、四化、宫位、干支） |
| POST | `/api/v1/ziwei/distribution` | 紫微分布画像图表数据包（气质/阴阳/明暗 + 解读） |
| POST | `/api/v1/ziwei/time-correction` | 真太阳时校正 |
| POST | `/api/v1/ziwei/charts` | 生成紫微本命盘 |
| POST | `/api/v1/ziwei/fortune` | 生成紫微命盘及运限 |
| POST | `/api/v1/ziwei/analysis` | 生成本命结构解读与格局结果 |
| POST | `/api/v1/qimen/charts` | 生成奇门遁甲盘 |
| POST | `/api/v1/liu-yao/charts` | 生成六爻卦盘（纳甲/六神/六亲/伏神/旺衰/世应/变卦，含 `meta.rule_profile`） |
| POST | `/api/v1/liu-yao/distribution` | 六爻卦面画像（六亲重心/爻之五行/月令旺衰五态三图） |
| POST | `/api/v1/da-liu-ren/charts` | 生成大六壬课盘（含 `meta.rule_profile` 口径标识） |
| GET | `/api/v1/da-liu-ren/glossary` | 大六壬术语与当前实现口径 |
| POST | `/api/v1/da-liu-ren/distribution` | 六壬盘面画像图表数据包（上神五行/遁干/阴阳 + 气象解读） |
| POST | `/api/v1/mei-hua/plates` | 梅花易数起卦事实盘（时间/报数→本互变+体用+月令旺衰，含 `meta.rule_profile`） |
| POST | `/api/v1/mei-hua/distribution` | 梅花体用画像（三卦六体五行/六卦旺衰/本卦阴阳结构三图；运行时内核交叉锁） |
| POST | `/api/v1/bazi/charts` | 生成八字四柱与大运 |
| POST | `/api/v1/bazi/distribution` | 八字画像（干支五行/十神五类/干之阴阳底色三图） |
| GET | `/api/v1/astro/meta` | 西洋占星能力和版本信息 |
| POST | `/api/v1/astro/charts` | 使用 Swiss Ephemeris 生成西洋星盘 |
| POST | `/api/v1/astro/transits` | 计算指定时刻的行运事实包 |
| POST | `/api/v1/astro/analysis` | 基于结构化星盘和规则库生成证据分析包 |
| POST | `/api/v1/astro/transit-analysis` | 将行运事实映射为生活领域信号，不生成文案或评分 |
| POST | `/api/v1/astro/daily-reading` | 将生活领域信号渲染为无评分日运解析包 |
| POST | `/api/v1/astro/natal-analysis` | 将本命盘读成黄道与宫位布局统计、原始信号和规则命中 |
| POST | `/api/v1/astro/natal-reading` | 将布局统计与规则命中渲染为无评分布局速读解析包 |
| POST | `/api/v1/astro/distribution` | 占星分布画像（元素/阴阳/三性质三图） |
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
- [梅花易数 HTTP 接口文档](docs/梅花易数HTTP接口文档.md)
- [六爻 HTTP 接口文档](docs/六爻HTTP接口文档.md)
- [八字 HTTP 接口文档](docs/八字HTTP接口文档.md)
- [大六壬 HTTP 接口文档](docs/大六壬HTTP接口文档.md)
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

## 平台注册与治理

### 工具注册清单（P0-1）

每门术数在 `config/platform/tools/<id>.json` 声明一份清单：引擎 CLI 路径、
路由、页面、校准状态与启动要求。奇门/八字/六爻/大六壬的排盘路由由清单驱动
分发（新增同类工具 = 加一份 manifest，无需改 `server.py`）；
`/api/v1/tools` 与 `/api/v1/health` 直接暴露注册结果。清单目录缺失时服务
回退到 `web/tool_registry.py` 内建默认；清单存在但非法则拒绝启动（fail fast）。

### API 治理（P0-2）

`/api/` 请求支持最小治理层：访问日志（JSON Lines，落
`.zhouyilab/logs/access.jsonl`，含 request_id、耗时与治理裁决）、
`X-API-Key` 鉴权与每密钥令牌桶限流。环境变量：

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `ZHOUYILAB_API_MODE` | `observe` | `off` 关闭；`observe` 只记录不拦截（**默认**）；`enforce` 强制密钥+限流 |
| `ZHOUYILAB_RATE_LIMIT_RPM` | `120` | 每密钥每分钟配额 |
| `ZHOUYILAB_API_KEYS_FILE` | `config/platform/api_keys.local.json` | `{label: key}` 映射，已被 Git 忽略；enforce 且无密钥时自动降级 observe |
| `ZHOUYILAB_ACCESS_LOG` | `.zhouyilab/logs/access.jsonl` | 访问日志路径 |

`/api/v1/health` 永远豁免。生产 enforce 推荐由反向代理为浏览器同源流量注入
内部密钥（`proxy_set_header X-API-Key`），外部接入方发放独立密钥按标签归因。

### 符号字典单源化（P0-4）

`GET /api/v1/ziwei/symbols` 透传内核 `symbols` operation（紫微 CLI），输出
可上盘星名全集（109）、亮度、四化、宫位与干支五行。回归测试强制
`symbolism_dictionary.json` 的星名 ⊆ 内核符号集，拼错星名会在审计期暴露；
格局引擎的星名校验以此为上游。

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
│   ├── platform/
│   │   └── tools/           # 工具注册清单（manifest + schema）
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
