# 六爻校准案例库（liuyao-case/1.0）

D1=A（以《增删卜易》为主口径，2026-09-20 拍板）的**盘面事实回归层**：
每个案例 = 输入（公历/农历日期 + 六爻卦码 + 动爻）+ 引擎输出事实字段的
点分路径锁定（`yao.N.…` 按 position 寻址，列表值逗号连接）。

## 收录现状（stage1_plate_facts）

| 案例 | 锁什么 |
| --- | --- |
| `jin_shen_zi_hua_chou` / `tui_shen_chou_hua_zi` | 进退神四对口径（D1=A）行为锁 |
| `def7_qian_moving_2_changed_ji_chou` | DEF-7 纳甲表修复（乾二爻动变同人须化己丑） |
| `an_dong_xiang_not_rest` | DEF-4 旺衰修复后的暗动口径（相而受冲方动） |
| `kun_moving_2_bian_shi_regression` | 变卦推演 + 变爻纳甲 + 化六亲（按本卦宫五行） |
| `sun_fu_shen_facts` | 伏神事实层：伏支/伏六亲/月破/入飞神墓标签（**不含可用结论**） |
| `tongren_shi_ying_and_najia` | 归魂卦世应 + DEF-7 修复后本卦纳甲 |

## 边界（诚实闸）

* **古籍书例槽位空置**：《增删卜易》原书占验例须逐字校勘后以
  `origin=classic_example` + `verification=pending_manual_collation` 入册，
  校勘前不得转写（不假托、不脑补情节）。
* **伏神"出不出、破空可否用"**：DEF-5 跟踪，伏神章校勘前不建任何 expected
  结论字段——引擎与案例只呈现事实状态标签。
* 断语/吉凶/应期类判断一律不入库（与梅花 M3、平台"断语押后"总纲同纪律）。
* claim 升级由人工决策；`check_calibration.py` 只验证套件可执行。

## 重放

`python3 -m unittest tests.test_liuyao_cases`（需已构建 `liu_yao_web_cli`；
引擎行为漂移即红）。改口径属校准决策，须同步：内核注释、rule_profile、
本库案例、`test_liuyao_jin_tui_contract` / `test_liuyao_hexagram_table_contract`。
