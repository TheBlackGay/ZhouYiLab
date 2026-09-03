# ZhouYiLab - 周易实验室

基于 C++23 Modules 的传统术数算法库，同时提供本地 Web 界面、JSON API、声明式紫微格局引擎与研究评审工具。

[![C++23](https://img.shields.io/badge/C%2B%2B-23-blue.svg)](https://en.cppreference.com/w/cpp/23)
[![CMake](https://img.shields.io/badge/CMake-3.28%2B-green.svg)](https://cmake.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

当前开发分支为 `r_1.5.0`，HTTP API 版本为 `v1`，接口返回的算法标识为 `zhouyilab-core/1.4.1`。

## 算法校准状态

本项目正在逐项复核各术数算法。这里的“已有实现”和“已经校准”是两个不同状态：已有代码只表示能够运行；已经校准表示当前版本已针对原有错误进行修正，并按照项目确认的规则口径完成案例回归。

当前状态：

| 算法 | 校准状态 | 说明 |
| --- | --- | --- |
| 紫微斗数 | 已校准 | 已复核排盘、亮度、四化、运限和声明式格局规则，修正原有错误并建立结构化案例验证 |
| 奇门遁甲 | 已校准 | 已重新校正原有起局实现，当前采用项目文档确认的拆补法时家转盘口径，并建立回归测试 |
| 八字 | 待校准 | 现有 C++ 模块和示例可运行，不代表算法口径已经完成复核 |
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
| 八字、六爻、大六壬 | C++ 示例 | 核心模块与示例程序 |

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

网页服务依赖两个 C++ JSON CLI：

```bash
cmake -S . -B build
cmake --build build --target zi_wei_web_cli qi_men_web_cli
```

构建产物：

```text
build/examples/zi_wei_web_cli
build/examples/qi_men_web_cli
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

启动后访问：

- 紫微斗数：[http://127.0.0.1:8768/](http://127.0.0.1:8768/)
- 奇门遁甲：[http://127.0.0.1:8768/qimen.html](http://127.0.0.1:8768/qimen.html)
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

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/v1/health` | 服务及 C++ 引擎健康状态 |
| GET | `/api/v1/ziwei/meta` | 紫微接口能力和版本信息 |
| POST | `/api/v1/ziwei/time-correction` | 真太阳时校正 |
| POST | `/api/v1/ziwei/charts` | 生成紫微本命盘 |
| POST | `/api/v1/ziwei/fortune` | 生成紫微命盘及运限 |
| POST | `/api/v1/ziwei/analysis` | 生成本命结构解读与格局结果 |
| POST | `/api/v1/qimen/charts` | 生成奇门遁甲盘 |
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
- [奇门遁甲 HTTP 接口文档](docs/奇门遁甲HTTP接口文档.md)

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
