# 梅花易数校准案例库（M3 第一步：盘面事实）

流程口径（与 D3 三步走同构，禁止本末倒置）：

1. **事实先行**：`expected` 用点分路径锁起卦取数、本互变卦码卦名、动爻、
   体用定位与生克判词、月令旺衰——CI 可执行（`tests/test_meihua_cases.py`）；
2. **校勘断句**：classic 例只锁"数与卦体结果"，占事故事情节一律不转写；
   `verification=pending_manual_collation` 的条目须人工按所据刻本逐字核对；
3. **断语押后**：吉凶、应期、事类判断在校准（claim 升级由人工决策）与评审
   完成前，本库不建任何断语字段、内核不输出任何断语字段。

规则：

- 每条案例一个 JSON（schema：`meihua-case/1.0`），id 用 `^[a-z0-9_]+$`；
- `status=boundary` 为口径边界/等价性锁（不参与"经典例校勘"计数），
  `pending` 为待人工校勘的成例，`calibrated` 仅在人工决策后填写；
- `source_case.origin` 二选一：`classic_example`（古籍例，必须给 book/case_ref，
  verification 初始一律 `pending_manual_collation`）/ `structural_regression`
  （本仓口径回归锁，verification=`self_consistent`）；
- **palace（八宫归属）有意不进 expected**：梅花判定不引用宫位，宫名展示沿用
  六爻内核京房表，避免案例隐含"宫位归属已经独立校勘"的错误声明；
- 书例"辰年十二月十七日申时"锚定 1916 丙辰年农历映射（1976 版腊十七恰踩立春，
  干支年换丁巳、月令换寅，取数即不同——见 solar_lunar_equivalence 备注）。

当前覆盖：书例（革·初动·互姤变咸）×1；闰月十五分界两侧 ×2；报数两数式 ×1；
公历↔农历同盘等价 ×1。
