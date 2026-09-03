# AI 多模型定性预评审平台 v0.1

> 机器协议：`config/ziwei/research/ai_review_protocol.json`  
> 研究边界：[ADR-006](./decisions/ADR-006-AI多模型预评审的证据边界.md)

## 1. 用途

平台将同一份匿名盲评包发送给多个大模型，收集十一维方向评分和判断依据，用于快速发现：

- 哪些维度的定义容易被不同模型理解成不同含义。
- 哪些案例的匿名事实不足以支持判断。
- 同一模型重复运行时是否稳定。
- 哪些争议内容应优先交给人类专家评审。

它不是现实准确性验证，也不是人类专家评分的替代品。

## 2. 已支持的模型服务

### Ollama

1. 启动 Ollama。
2. 确保已下载模型，例如 `qwen3:8b`。
3. 在页面中选择 `Ollama`，地址填 `http://127.0.0.1:11434`。

### OpenAI 兼容接口

可用于 OpenAI、DeepSeek、LM Studio、vLLM 及其他提供 `/v1/chat/completions` 的服务。基础地址应包含 `/v1`，例如：

```text
https://api.openai.com/v1
https://api.deepseek.com/v1
http://127.0.0.1:1234/v1
```

云端服务通常需要 API Key。模型连接只从本机配置文件读取，页面不接收地址或 Key。

## 3. 模型配置

实际使用的本机配置为：

```text
config/ziwei/research/ai_model_providers.local.json
```

该文件已被 Git 忽略，可以填写明文 `api_key`。更推荐在系统中设置环境变量，然后只填 `api_key_env`。多个模型就在 `providers` 数组中放多个对象：

```json
{
  "config_version": "0.1.0",
  "providers": [
    {
      "provider_id": "model-a",
      "label": "模型 A",
      "protocol": "openai_compatible",
      "base_url": "https://provider.example/v1",
      "model": "exact-model-name",
      "model_family": "Model Family",
      "api_key": "",
      "api_key_env": "MODEL_A_API_KEY",
      "enabled": true,
      "temperature": 0,
      "repetitions": 3,
      "model_seed": 42
    }
  ]
}
```

- `provider_id` 必须唯一，后续不要随意修改，它用于关联实验记录。
- `model` 必须是接口接受的精确模型名。
- `model_family` 表示模型系列，例如 `Qwen3`、`GPT-5`、`DeepSeek`。
- `api_key` 和 `api_key_env` 二选一。同时填写时，环境变量有值则优先使用环境变量。
- `enabled: false` 的连接不会出现在页面中。
- 修改文件后在页面点击“重载配置”，不需要重启服务。

## 4. 使用流程

1. 打开 `/ai-review.html`。
2. 在配置文件中启用一个或多个模型连接，然后在页面重载。
3. 勾选需要参加本次实验的模型，先执行“测试连接”。
4. 每个模型建议运行 3 次，`temperature` 设为 `0`。
5. 开始实验后可关闭页面，只要 Python 服务不退出，后台任务就会继续。
6. 在结果区分别查看主方向占比、同案例跨模型一致度、模型自身稳定性和失败记录。
7. 导出 JSON 用于归档和后续研究。

## 5. 数据与复现

默认数据库位于：

```text
.zhouyilab/research/ai_review.sqlite3
```

该目录已加入 `.gitignore`。数据库记录实验 ID、盲评包 ID、模型系列、精确模型名、接口类型、重复序号、案例编码、提示词哈希、原始响应、解析后评分、重试次数和 token 用量，但不记录 API Key。

## 6. 统计解释

- `主方向占比`：把每个“模型 × 案例”视为一个单元，统计最常出现的增强、中性或抑制方向占比。它说明整体倾向，不说明模型在同一个案例上是否一致。
- `同案一致度`：先平均同一模型对同一案例的重复评分，再把均值转为方向；随后只在同一个案例内比较不同模型，并对所有可比较案例的众数比例求平均。
- `完全一致案例`：同一案例的所有有效模型方向都相同时计数。少于两个有效模型的案例不参与跨模型比较。
- `两两同向比例`：同一案例内所有模型对中方向相同的比例，用于补充说明一致性的强弱。
- `模型自身稳定性`：同一模型对同一案例的重复评分完全相同的成对比例。只运行 1 次时不计算。

重复运行只用于求模型自身的稳定性和模型-案例均值，不会增加该模型在跨模型统计中的投票权。所有指标都是描述性结果，不套用人工盲评的 Krippendorff's alpha 接受阈值。
