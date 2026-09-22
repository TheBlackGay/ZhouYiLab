# 大六壬校准案例库（daliuren-case/1.0）

A3 结构层（盘面事实先行、断语押后，与大六壬 2.x 双模式/glossary 同纪律）。
案例 = 输入（公历/农历 + 可选 `yuejiang_method`）+ 引擎事实的点分路径锁。
数组提取约定：段名加 `[]` 后缀（如 `tian_di_pan[].tian_pan`）按序取字段逗号连接；
`yao` 式 position 数字寻址同样可用。

## 收录现状（stage1_plate_facts，7 例）

| 案例 | 锁什么 |
| --- | --- |
| `plate_bingzi_2025_11_03` | 基准盘全量快照：日课丙子/旬空申酉/贵人亥/月将卯/涉害课三传子未寅/四课/天盘十二位/六亲链 |
| `yuejiang_xiaoxue_before` + `_after` | 中气过宫边界（D2 默认口径）：小雪前卯→后寅，成对构成跳变判据 |
| `yuejiang_dahan_zhongqi` + `_guifa` | 古今口径对照：2025-01-20 全年首个分歧日，中气子 vs 古法丑——并存互不覆盖，接口可回退 |
| `solar_lunar_equivalence` | 农历九月十四=公历 2025-11-03 同盘等价（农历映射为引擎 brute-force 寻见证） |
| `night_plate_shenjiang` | 昼夜盘：亥时夜贵人酉（昼盘亥）、十二神将全序列换序 |

## 边界（诚实闸）

* 古籍课例（《大六壬大全》《御定六壬直指》等）须逐字校勘后以
  `classic_example + pending_manual_collation + status=pending` 入册，转写前不得背书。
* 课体吉凶、类断、应期一律不建 expected；四课入盘属**可视化口径**（台账待拍板），
  本库只锁引擎事实，不涉画面布局。
* claim 升级由人工决策；`check_calibration.py` 只验套件可执行。

## 重放

`python3 -m unittest tests.test_daliuren_cases`（需 `da_liu_ren_web_cli`）。
月将/起课口径若变更，属校准决策，须同步内核、rule_profile、本库案例与
`test_dlr_plate_contract` / `test_dlr_distribution`。
