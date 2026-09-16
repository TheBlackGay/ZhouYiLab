# ZhouYiLab 模块架构文档

公共能力清单与组件抽取记录见 [`docs/common/公共能力与组件设计.md`](docs/common/公共能力与组件设计.md)。

## 模块层次结构

```

                应用层 (main.cpp)                 

                        

              功能模块层                          
       
   LiuYao    DaLiuRen  BaZi   ZiWei        
       
                                     
    QiMen                                      
                                     

                        

              通用模块层                          
     
   BaZiBase   WuXingUtils  Common.Calendar
     
     
    GanZhi   Common.DateTime   ZhMapper
     
                    
                 ZhouYi.tyme
                    

                        

            第三方库 & 标准库层                   
      
   fmt  nlohmann.json   magic_enum         
      
                                
    import std                                
                                

```

## 模块详细说明

### 1. 通用基础模块 (Common Layer)

#### ZhouYi.BaZiBase
**文件**: `src/common/tian_gan/ba_zi_base.cppm`

**导出内容**:
- `struct Pillar` - 干支柱（天干地支组合）
- `struct BaZi` - 四柱八字

**依赖**:
```cpp
import nlohmann.json;  // JSON 序列化
import ZhouYi.GanZhi;  // 干支类型
import ZhouYi.Common.Calendar;  // 历法适配
import ZhouYi.tyme;  // 农历历法
import std;            // 标准库
```

**用途**: 被所有需要使用干支柱和八字的模块引用。日期和 `tyme` 适配流程通过 `ZhouYi.Common.Calendar` 复用。

---

#### ZhouYi.Common.DateTime
**文件**: `src/common/calendar/date_time.cppm`

**导出内容**:
- `SolarDateTime`、`LunarDateTime` - 公历/农历日期时间值对象
- `is_leap_year()`、`days_in_month()`、`day_of_year()` - 公历基础计算
- `is_valid_solar_date_time()`、`is_valid_lunar_date()` - 输入校验
- `format()` - 统一日期时间格式化

**用途**: 统一所有排盘入口的日期时间基础能力，不包含时区和术数规则。

---

#### ZhouYi.Common.Calendar
**文件**: `src/common/calendar/calendar.cppm`

**导出内容**:
- `to_solar_time()`、`to_lunar_hour()` - 创建 `tyme` 时间对象
- `solar_to_lunar()`、`lunar_to_solar()` - 公历/农历公共值对象互转
- `from_solar_time()`、`from_lunar_time()` - 转换为公共日期值对象
- `correct_solar_time()`、`calculate_true_solar_time()` - 标准时间/真太阳时校正 API
- `calculate_equation_of_time_seconds()` - 均时差计算 API
- `eight_char_from_solar_time()`、`eight_char_from_lunar_time()` - 统一获取八字

**依赖**:
```cpp
export import ZhouYi.Common.DateTime;
import ZhouYi.tyme;
```

**用途**: 隔离功能模块与 `tyme4cpp` 的重复适配代码，并向外提供统一的公历/农历转换和真太阳时计算 API。

---

#### ZhouYi.WuXingUtils
**文件**: `src/common/wu_xing_utils.cppm`

**导出内容**:
- `enum class ElementalRelation` - 五行关系枚举
- `branchFiveElements` - 地支五行映射表
- `fiveElementIndex` - 五行索引映射
- `hiddenStems` - 地支藏干映射
- `getElementalRelationship()` - 五行关系判断
- `relationToString()` - 五行关系转中文
- `getBranchElement()` - 获取地支五行

**依赖**:
```cpp
import std;  // 标准库
```

**用途**: 提供五行相关的所有工具函数和数据映射

---

#### ZhouYi.GanZhi
**文件**: `src/common/ganzhi.cppm`

**导出内容**:
- `enum class TianGan` - 天干枚举
- `enum class DiZhi` - 地支枚举
- `enum class WuXing` - 五行枚举
- `enum class YinYang` - 阴阳枚举
- 六十甲子相关函数
- 干支关系判断函数

**依赖**:
```cpp
import magic_enum;  // 枚举反射
import std;         // 标准库
```

---

#### ZhouYi.ZhMapper
**文件**: `src/common/zh_mapper.cppm`

**导出内容**:
- `template<typename E> struct ZhMap` - 中文映射模板
- `to_zh()`, `from_zh()` - 枚举与中文互转
- `get_all_zh_names()` - 获取所有中文名
- `get_all_info()` - 获取枚举详细信息

**依赖**:
```cpp
import magic_enum;  // 枚举反射
import std;         // 标准库
```

---

### 2. 功能模块 (Feature Layer)

#### ZhouYi.BaZi
**文件**: `src/ba_zi/ba_zi.cppm`

**导出内容**:
- `struct BaZiResult` - 八字排盘结果
- `struct DaYun` - 大运信息
- `struct LiuNian` - 流年信息
- `struct LiuYue` - 流月信息
- `pai_pan_solar()` - 公历排盘
- `pai_pan_lunar()` - 农历排盘
- `get_da_yun_list()` - 获取大运列表
- `get_liu_nian()` - 获取流年
- `get_liu_yue_list()` - 获取流月列表

**依赖**:
```cpp
import ZhouYi.BaZiBase;        // 八字基础
import ZhouYi.GanZhi;          // 干支系统
import ZhouYi.tyme;            // 农历历法
import std;                    // 标准库
```

**使用示例**:
```cpp
import ZhouYi.BaZiController;

using namespace ZhouYi::BaZiController;

// 公历排盘
auto result = pai_pan_solar(2000, 7, 15, 16, 30, true);
const auto& ba_zi = result.ba_zi;
std::println("年柱：{}", ba_zi.year.to_string());
```

---

#### ZhouYi.DaLiuRen
**文件**: `src/da_liu_ren/da_liu_ren.cppm`

**导出内容**:
- `struct DaLiuRenResult` - 大六壬排盘结果
- `struct SiKe` - 四课信息
- `struct SanChuan` - 三传信息
- `struct TianDiPan` - 天地盘信息
- `pai_pan()` - 公历排盘
- `pai_pan_lunar()` - 农历排盘

**依赖**:
```cpp
import ZhouYi.GanZhi;          // 干支系统
import ZhouYi.tyme;            // 农历历法
import nlohmann.json;          // JSON 序列化
import std;                    // 标准库
```

**使用示例**:
```cpp
import ZhouYi.DaLiuRen.Controller;

using namespace ZhouYi::DaLiuRen;

auto result = DaLiuRenEngine::pai_pan(2024, 10, 13, 14);
std::println("月将: {}", result.yue_jiang);
```

---

#### ZhouYi.QiMen
**文件**: `src/qi_men/qi_men.cppm`, `src/qi_men/qi_men_pan.cppm`, `src/qi_men/qi_men_controller.cppm`

**导出内容**:
- `struct QiMenPan` - 奇门盘信息
- `enum class Dun` - 阴阳遁枚举
- `enum class Palace` - 九宫枚举
- `enum class SolarTerm` - 二十四节气枚举
- `pai_pan_solar()` - 公历排盘
- `pai_pan_lunar()` - 农历排盘
- `get_summary()` - 获取排盘摘要
- `analyze_auspiciousness()` - 分析宫位吉凶

**依赖**:
```cpp
import ZhouYi.GanZhi;          // 干支系统
import ZhouYi.tyme;            // 农历历法
import std;                    // 标准库
```

**使用示例**:
```cpp
import ZhouYi.QiMen.Controller;

using namespace ZhouYi::QiMen;

// 公历排盘
auto result = QiMenController::pai_pan_solar(2011, 6, 18, 3, 56);
if (result) {
    const auto& pan = result.value();
    std::println("阴阳遁：{}", pan.dun == Dun::Yang ? "阳遁" : "阴遁");
    std::println("局数：第{}局", pan.ju);
}
```

---

#### ZhouYi.LiuYao
**文件**: `src/liu_yao/liu_yao.cppm`

**导出内容**:
- `struct YaoDetails` - 爻详细信息
- `struct HexagramInfo` - 卦象信息
- `hexagramMap` - 六十四卦信息映射
- `palaceBranchPatterns` - 宫位地支序列
- `palaceStemPatterns` - 宫位天干序列
- `sixYaoDivination()` - 六爻排盘主函数
- `buildShenShaMap()` - 神煞计算
- `analyzeXingChongKeHaiHe()` - 关系分析

**依赖**:
```cpp
import fmt;                    // 格式化输出
import nlohmann.json;          // JSON 序列化
import ZhouYi.BaZiBase;        // 八字基础
import ZhouYi.WuXingUtils;     // 五行工具
import ZhouYi.GanZhi;          // 地支关系与干支映射
import std;                    // 标准库
```

**使用示例**:
```cpp
import ZhouYi.LiuYao;

using namespace ZhouYi::LiuYao;

BaZi bazi{...};
auto [yaoList, json] = sixYaoDivination("111111", bazi, {1, 4});
```

---

#### ZhouYi.Astro
**文件**: `src/astro/astro.cppm`, `src/astro/astro_controller.cppm`

**导出内容**:
- `ChartRequest`、`ChartResult` - 西洋占星输入与结果
- `calculate()` - Swiss Ephemeris 本命盘计算
- `ZhouYi.Astro.Controller` - JSON 请求解析和结构化输出

**依赖**:
```cpp
import ZhouYi.Common.DateTime;  // 公历日期校验
import nlohmann.json;
import std;
```

**用途**: 西洋占星历算和结构化 JSON 输出。占星规则不进入传统术数公共层。

---

## 模块依赖关系

### BaZi 依赖树

```
ZhouYi.BaZi
 ZhouYi.BaZiBase
    nlohmann.json
    std
 ZhouYi.GanZhi
    magic_enum
    std
 ZhouYi.tyme
    std
 std
```

### DaLiuRen 依赖树

```
ZhouYi.DaLiuRen
 ZhouYi.GanZhi
    magic_enum
    std
 ZhouYi.tyme
    std
 nlohmann.json
 std
```

### QiMen 依赖树

```
ZhouYi.QiMen
 ZhouYi.GanZhi
    magic_enum
    std
 ZhouYi.tyme
    std
 std
```

### LiuYao 依赖树

```
ZhouYi.LiuYao
 ZhouYi.BaZiBase
    nlohmann.json
    std
 ZhouYi.WuXingUtils
    std
 ZhouYi.GanZhi
    magic_enum
    std
 fmt
 nlohmann.json
 std
```

### 通用模块依赖树

```
ZhouYi.BaZiBase
 nlohmann.json
 std

ZhouYi.WuXingUtils
 std

 ZhouYi.GanZhi
    magic_enum
    std

 ZhouYi.Common.DateTime
    std

 ZhouYi.Common.Calendar
    ZhouYi.Common.DateTime
    ZhouYi.tyme

ZhouYi.ZhMapper
 magic_enum
 std
```

## 模块使用原则

### 1. 分层原则
- **应用层** 只调用功能模块层
- **功能模块层** 可以调用通用模块层和第三方库
- **通用模块层** 只能调用其他通用模块和第三方库
- **禁止循环依赖**

### 2. 命名规范
- 模块名使用 `ZhouYi.` 前缀
- 子模块使用驼峰命名法（如 `BaZiBase`）
- 文件名使用下划线命名法（如 `ba_zi_base.cppm`）

### 3. 导入顺序
```cpp
// 1. 第三方库模块
import fmt;
import nlohmann.json;
import magic_enum;

// 2. 自定义模块
import ZhouYi.BaZiBase;
import ZhouYi.WuXingUtils;

// 3. 标准库模块（最后）
import std;
```

### 4. 导出规范
```cpp
export module ZhouYi.ModuleName;

// 导入其他模块...

export namespace ZhouYi::ModuleName {
    // 导出的内容
}
```

## 编译配置

### CMakeLists.txt 配置

```cmake
file(GLOB_RECURSE MODULE_FILES 
    "src/*.cppm"           # C++23 module 接口文件（递归搜索所有子目录）
    "src/*.ixx"            # MSVC module 接口文件
    "src/common/**/*.cppm"  # common 模块文件
)

target_sources(ZhouYiLab
    PUBLIC
    FILE_SET cxx_modules TYPE CXX_MODULES FILES
    ${MODULE_FILES}
    ${CMAKE_CURRENT_SOURCE_DIR}/3rdparty/magic_enum/module/magic_enum.cppm
)
```

### 编译器要求

- **Clang**: 17+ (with libc++)
- **GCC**: 14+ (with libstdc++)
- **MSVC**: 19.36+ (Visual Studio 2022 17.6+)
- **CMake**: 4.0+

## 最佳实践

### 1. 模块设计
-  单一职责：每个模块只负责一个明确的功能领域
-  高内聚：相关功能放在同一个模块中
-  低耦合：模块之间依赖关系清晰简单
-  可复用：通用功能抽取到 common 层

### 2. 性能优化
-  使用 `inline const` 替代 `static const` 全局变量
-  使用 `constexpr` 标记编译期常量
-  使用 `std::string_view` 传递字符串参数
-  使用 `auto` 和 `decltype` 简化代码

### 3. C++23 特性
-  使用 `import std` 替代传统头文件
-  使用 `<=>` 三路比较运算符
-  使用 `= default` 生成默认函数
-  使用 `std::ranges` 进行范围操作

## 已实现模块

已完成的功能模块：

1.  **ZhouYi.BaZi** - 八字排盘系统（完整实现）
2.  **ZhouYi.DaLiuRen** - 大六壬排盘系统（完整实现）
3.  **ZhouYi.QiMen** - 奇门遁甲排盘系统（完整实现）
4.  **ZhouYi.LiuYao** - 六爻排盘系统（完整实现）
5.  **ZhouYi.ZiWei** - 紫微斗数排盘系统（完整实现）

## 未来扩展

计划添加的模块：

1. **ZhouYi.FengShui** - 风水计算系统
2. **ZhouYi.MeiHua** - 梅花易数系统
3. **ZhouYi.TaiYi** - 太乙神数系统

所有新模块都应该：
- 遵循相同的命名和组织规范
- 复用 common 层的通用功能
- 提供完整的文档和示例
- 使用 C++23 模块系统

## 许可证

本项目采用 MIT 许可证。

