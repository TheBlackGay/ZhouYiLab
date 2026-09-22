#!/usr/bin/env python3
"""生成 data/geo/curated.json（G1 精选地名库）与 index.json。

来源：本项目按公开资料手工整理的常用城市（名称、约数坐标、IANA 时区、
约数人口、约数半径），不复制任何商业地图数据（见 docs/product/
西洋占星出生地点交互优化方案.md §6.1 许可约束）。

分组配额（合计 493）：
  cn_core   34  直辖市、省会/首府与计划单列核心城市
  cn_extra 120  计划单列市、人口前列地级市与重要口岸/地区驻地
  cn_more  193  其余全部地级市/自治州/盟驻地，补齐大陆 333 个地级区划
                （日喀则、狮泉河因 §6.1 的 |经度−标准经线|≤30° 校验
                 无法用 Asia/Shanghai 收录，暂缺，见 data/geo/README.md）
  tw_hk_mo  20  港澳台城市（含台北、香港、澳门）
  world_cap 100 全球首都
  world_ext  26 其他高频海外城市

行格式：(name_zh, name_en, admin1, country_zh, cc, lat, lon, tz, population, approx_radius_km, extra_aliases)

用法：python3 scripts/gen_curated_places.py
"""
import hashlib
import json
import unicodedata
from datetime import date
from pathlib import Path

REVISION = "2026.09.22"
ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "geo"

QUOTA = {"cn_core": 34, "cn_extra": 120, "cn_more": 193, "tw_hk_mo": 20, "world_cap": 100, "world_ext": 26, "total": 493}

CN_CORE = [
    ("北京市", "Beijing", "北京市", "中国", "CN", 39.9042, 116.4074, "Asia/Shanghai", 21890000, 40, ["北京", "京", "beijing", "bj"]),
    ("上海市", "Shanghai", "上海市", "中国", "CN", 31.2304, 121.4737, "Asia/Shanghai", 24280000, 30, ["上海", "沪", "shanghai", "sh"]),
    ("天津市", "Tianjin", "天津市", "中国", "CN", 39.0842, 117.2010, "Asia/Shanghai", 13870000, 40, ["天津", "津", "tianjin", "tj"]),
    ("重庆市", "Chongqing", "Chongqing", "中国", "CN", 29.5630, 106.5516, "Asia/Shanghai", 32050000, 150, ["重庆", "渝", "chongqing", "cq"]),
    ("石家庄市", "Shijiazhuang", "河北省", "中国", "CN", 38.0428, 114.5149, "Asia/Shanghai", 11230000, 35, ["石家庄", "shijiazhuang", "sjz"]),
    ("太原市", "Taiyuan", "山西省", "中国", "CN", 37.8706, 112.5489, "Asia/Shanghai", 5300000, 25, ["太原", "taiyuan", "ty"]),
    ("呼和浩特市", "Hohhot", "内蒙古自治区", "中国", "CN", 40.8424, 111.7490, "Asia/Shanghai", 3440000, 25, ["呼和浩特", "呼市", "hohhot", "hhht"]),
    ("沈阳市", "Shenyang", "辽宁省", "中国", "CN", 41.8057, 123.4315, "Asia/Shanghai", 9070000, 35, ["沈阳", "shenyang", "sy"]),
    ("大连市", "Dalian", "辽宁省", "中国", "CN", 38.9140, 121.6147, "Asia/Shanghai", 7450000, 25, ["大连", "dalian", "dl"]),
    ("长春市", "Changchun", "吉林省", "中国", "CN", 43.8171, 125.3235, "Asia/Shanghai", 9090000, 30, ["长春", "changchun", "cc"]),
    ("哈尔滨市", "Harbin", "黑龙江省", "中国", "CN", 45.8038, 126.5350, "Asia/Shanghai", 10010000, 35, ["哈尔滨", "harbin", "heb"]),
    ("南京市", "Nanjing", "江苏省", "中国", "CN", 32.0603, 118.7969, "Asia/Shanghai", 9420000, 30, ["南京", "nanjing", "nj"]),
    ("杭州市", "Hangzhou", "浙江省", "中国", "CN", 30.2741, 120.1551, "Asia/Shanghai", 12200000, 30, ["杭州", "hangzhou", "hz"]),
    ("合肥市", "Hefei", "安徽省", "中国", "CN", 31.8206, 117.2272, "Asia/Shanghai", 9630000, 30, ["合肥", "hefei", "hf"]),
    ("福州市", "Fuzhou", "福建省", "中国", "CN", 26.0745, 119.2965, "Asia/Shanghai", 8420000, 25, ["福州", "fuzhou", "fz"]),
    ("南昌市", "Nanchang", "江西省", "中国", "CN", 28.6820, 115.8579, "Asia/Shanghai", 6440000, 25, ["南昌", "nanchang", "nc"]),
    ("济南市", "Jinan", "山东省", "中国", "CN", 36.6512, 117.1201, "Asia/Shanghai", 9200000, 30, ["济南", "jinan", "jn"]),
    ("青岛市", "Qingdao", "山东省", "中国", "CN", 36.0671, 120.3826, "Asia/Shanghai", 10070000, 30, ["青岛", "qingdao", "qd"]),
    ("郑州市", "Zhengzhou", "河南省", "中国", "CN", 34.7466, 113.6254, "Asia/Shanghai", 12600000, 30, ["郑州", "zhengzhou", "zz"]),
    ("武汉市", "Wuhan", "湖北省", "中国", "CN", 30.5928, 114.3055, "Asia/Shanghai", 13650000, 35, ["武汉", "wuhan", "wh"]),
    ("长沙市", "Changsha", "湖南省", "中国", "CN", 28.2278, 112.9388, "Asia/Shanghai", 10050000, 30, ["长沙", "changsha", "cs"]),
    ("广州市", "Guangzhou", "广东省", "中国", "CN", 23.1291, 113.2644, "Asia/Shanghai", 18680000, 35, ["广州", "羊城", "guangzhou", "gz"]),
    ("深圳市", "Shenzhen", "广东省", "中国", "CN", 22.5431, 114.0579, "Asia/Shanghai", 17560000, 25, ["深圳", "shenzhen", "sz"]),
    ("南宁市", "Nanning", "广西壮族自治区", "中国", "CN", 22.8170, 108.3665, "Asia/Shanghai", 8740000, 30, ["南宁", "nanning", "nn"]),
    ("海口市", "Haikou", "海南省", "中国", "CN", 20.0444, 110.1999, "Asia/Shanghai", 2840000, 20, ["海口", "haikou", "hk"]),
    ("成都市", "Chengdu", "四川省", "中国", "CN", 30.5728, 104.0668, "Asia/Shanghai", 20940000, 40, ["成都", "蓉", "chengdu", "cd"]),
    ("贵阳市", "Guiyang", "贵州省", "中国", "CN", 26.6470, 106.6302, "Asia/Shanghai", 5990000, 25, ["贵阳", "guiyang", "gy"]),
    ("昆明市", "Kunming", "云南省", "中国", "CN", 25.0389, 102.7183, "Asia/Shanghai", 8460000, 30, ["昆明", "kunming", "km"]),
    ("拉萨市", "Lhasa", "西藏自治区", "中国", "CN", 29.6520, 91.1721, "Asia/Shanghai", 900000, 25, ["拉萨", "lhasa", "lsa"]),
    ("西安市", "Xi'an", "陕西省", "中国", "CN", 34.3416, 108.9398, "Asia/Shanghai", 12950000, 35, ["西安", "长安", "xian", "xa"]),
    ("兰州市", "Lanzhou", "甘肃省", "中国", "CN", 36.0611, 103.8343, "Asia/Shanghai", 4360000, 20, ["兰州", "lanzhou", "lz"]),
    ("西宁市", "Xining", "青海省", "中国", "CN", 36.6171, 101.7782, "Asia/Shanghai", 2470000, 20, ["西宁", "xining", "xn"]),
    ("银川市", "Yinchuan", "宁夏回族自治区", "中国", "CN", 38.4872, 106.2309, "Asia/Shanghai", 2860000, 20, ["银川", "yinchuan", "yc"]),
    ("乌鲁木齐市", "Urumqi", "新疆维吾尔自治区", "中国", "CN", 43.8256, 87.6168, "Asia/Urumqi", 4050000, 30, ["乌鲁木齐", "乌市", "urumqi", "wlmq"]),
]

CN_EXTRA = [
    ("唐山市", "Tangshan", "河北省", "中国", "CN", 39.6305, 118.1831, "Asia/Shanghai", 7710000, 40, ["唐山", "tangshan", "ts"]),
    ("秦皇岛市", "Qinhuangdao", "河北省", "中国", "CN", 39.9354, 119.5996, "Asia/Shanghai", 3140000, 40, ["秦皇岛", "qinhuangdao", "qhd"]),
    ("邯郸市", "Handan", "河北省", "中国", "CN", 36.6256, 114.5391, "Asia/Shanghai", 9410000, 40, ["邯郸", "handan", "hd"]),
    ("保定市", "Baoding", "河北省", "中国", "CN", 38.8740, 115.4646, "Asia/Shanghai", 9240000, 50, ["保定", "baoding", "bd"]),
    ("沧州市", "Cangzhou", "河北省", "中国", "CN", 38.3044, 116.8389, "Asia/Shanghai", 7310000, 50, ["沧州", "cangzhou", "cz"]),
    ("张家口市", "Zhangjiakou", "河北省", "中国", "CN", 40.8240, 114.8875, "Asia/Shanghai", 4120000, 60, ["张家口", "zhangjiakou", "zjk"]),
    ("廊坊市", "Langfang", "河北省", "中国", "CN", 39.5250, 116.6837, "Asia/Shanghai", 5460000, 30, ["廊坊", "langfang", "lf"]),
    ("大同市", "Datong", "山西省", "中国", "CN", 40.0768, 113.3001, "Asia/Shanghai", 3110000, 40, ["大同", "datong", "dt"]),
    ("长治市", "Changzhi", "山西省", "中国", "CN", 36.1954, 113.1163, "Asia/Shanghai", 3190000, 40, ["长治", "changzhi", "ci"]),
    ("晋城市", "Jincheng", "山西省", "中国", "CN", 35.4907, 112.8512, "Asia/Shanghai", 2200000, 30, ["晋城", "jincheng", "jc"]),
    ("运城市", "Yuncheng", "山西省", "中国", "CN", 35.0263, 111.0038, "Asia/Shanghai", 4780000, 50, ["运城", "yuncheng", "yco"]),
    ("临汾市", "Linfen", "山西省", "中国", "CN", 36.0880, 111.5190, "Asia/Shanghai", 3980000, 50, ["临汾", "linfen", "liuf"]),
    ("包头市", "Baotou", "内蒙古自治区", "中国", "CN", 40.6574, 109.8404, "Asia/Shanghai", 2710000, 40, ["包头", "baotou", "bt"]),
    ("鄂尔多斯市", "Ordos", "内蒙古自治区", "中国", "CN", 39.6086, 109.7810, "Asia/Shanghai", 2170000, 80, ["鄂尔多斯", "ordos", "eeds"]),
    ("赤峰市", "Chifeng", "内蒙古自治区", "中国", "CN", 42.2700, 118.8900, "Asia/Shanghai", 4030000, 80, ["赤峰", "chifeng", "cf"]),
    ("通辽市", "Tongliao", "内蒙古自治区", "中国", "CN", 43.6524, 122.2460, "Asia/Shanghai", 2880000, 70, ["通辽", "tongliao", "tl"]),
    ("呼伦贝尔市", "Hulunbuir", "内蒙古自治区", "中国", "CN", 49.2122, 119.7650, "Asia/Shanghai", 2550000, 260, ["呼伦贝尔", "海拉尔", "hulunbuir", "hlbe"]),
    ("鞍山市", "Anshan", "辽宁省", "中国", "CN", 41.1087, 122.9946, "Asia/Shanghai", 3330000, 40, ["鞍山", "anshan", "as"]),
    ("丹东市", "Dandong", "辽宁省", "中国", "CN", 40.0090, 124.3550, "Asia/Shanghai", 2280000, 30, ["丹东", "dandong", "dd"]),
    ("锦州市", "Jinzhou", "辽宁省", "中国", "CN", 41.0954, 121.1270, "Asia/Shanghai", 3000000, 40, ["锦州", "jinzhou", "jzo"]),
    ("吉林市", "Jilin City", "吉林省", "中国", "CN", 43.8370, 126.5490, "Asia/Shanghai", 3700000, 40, ["吉林市", "jilin", "jlc"]),
    ("齐齐哈尔市", "Qiqihar", "黑龙江省", "中国", "CN", 47.3543, 123.9180, "Asia/Shanghai", 4400000, 60, ["齐齐哈尔", "qiqihar", "qqhe"]),
    ("牡丹江市", "Mudanjiang", "黑龙江省", "中国", "CN", 44.5520, 129.6330, "Asia/Shanghai", 2300000, 50, ["牡丹江", "mudanjiang", "mdj"]),
    ("无锡市", "Wuxi", "江苏省", "中国", "CN", 31.4912, 120.3119, "Asia/Shanghai", 7460000, 25, ["无锡", "wuxi", "wx"]),
    ("苏州市", "Suzhou", "江苏省", "中国", "CN", 31.2989, 120.5853, "Asia/Shanghai", 12750000, 30, ["苏州", "suzhou", "sz"]),
    ("南通市", "Nantong", "江苏省", "中国", "CN", 31.9802, 120.8943, "Asia/Shanghai", 7700000, 35, ["南通", "nantong", "nt"]),
    ("徐州市", "Xuzhou", "江苏省", "中国", "CN", 34.2058, 117.2848, "Asia/Shanghai", 9080000, 40, ["徐州", "xuzhou", "xz"]),
    ("常州市", "Changzhou", "江苏省", "中国", "CN", 31.8107, 119.9740, "Asia/Shanghai", 5260000, 25, ["常州", "changzhou", "cz"]),
    ("盐城市", "Yancheng", "江苏省", "中国", "CN", 33.3447, 120.1620, "Asia/Shanghai", 6720000, 50, ["盐城", "yancheng", "yco"]),
    ("扬州市", "Yangzhou", "江苏省", "中国", "CN", 32.3947, 119.4120, "Asia/Shanghai", 4560000, 30, ["扬州", "yangzhou", "yz"]),
    ("泰州市", "Taizhou", "江苏省", "中国", "CN", 32.4560, 119.9220, "Asia/Shanghai", 4520000, 30, ["泰州", "taizhou-js", "tz"]),
    ("镇江市", "Zhenjiang", "江苏省", "中国", "CN", 32.2044, 119.4250, "Asia/Shanghai", 3220000, 25, ["镇江", "zhenjiang", "zj"]),
    ("宁波市", "Ningbo", "浙江省", "中国", "CN", 29.8683, 121.5440, "Asia/Shanghai", 9540000, 30, ["宁波", "ningbo", "nb"]),
    ("温州市", "Wenzhou", "浙江省", "中国", "CN", 27.9938, 120.6994, "Asia/Shanghai", 9600000, 40, ["温州", "wenzhou", "wz"]),
    ("绍兴市", "Shaoxing", "浙江省", "中国", "CN", 30.0303, 120.5800, "Asia/Shanghai", 5270000, 25, ["绍兴", "shaoxing", "sx"]),
    ("金华市", "Jinhua", "浙江省", "中国", "CN", 29.0790, 119.6470, "Asia/Shanghai", 7050000, 40, ["金华", "jinhua", "jh"]),
    ("嘉兴市", "Jiaxing", "浙江省", "中国", "CN", 30.7522, 120.7500, "Asia/Shanghai", 5400000, 30, ["嘉兴", "jiaxing", "jx"]),
    ("台州市", "Taizhou", "浙江省", "中国", "CN", 28.6560, 121.4200, "Asia/Shanghai", 6600000, 40, ["台州", "taizhou-zj", "tzz"]),
    ("芜湖市", "Wuhu", "安徽省", "中国", "CN", 31.3526, 118.4330, "Asia/Shanghai", 3730000, 25, ["芜湖", "wuhu", "wu"]),
    ("安庆市", "Anqing", "安徽省", "中国", "CN", 30.5434, 117.0610, "Asia/Shanghai", 4160000, 40, ["安庆", "anqing", "aq"]),
    ("阜阳市", "Fuyang", "安徽省", "中国", "CN", 32.8901, 115.8140, "Asia/Shanghai", 8200000, 40, ["阜阳", "fuyang", "fy"]),
    ("泉州市", "Quanzhou", "福建省", "中国", "CN", 24.8741, 118.6757, "Asia/Shanghai", 8780000, 40, ["泉州", "quanzhou", "qzo"]),
    ("漳州市", "Zhangzhou", "福建省", "中国", "CN", 24.5130, 117.6470, "Asia/Shanghai", 5060000, 40, ["漳州", "zhangzhou", "zzo"]),
    ("厦门市", "Xiamen", "福建省", "中国", "CN", 24.4798, 118.0894, "Asia/Shanghai", 5160000, 25, ["厦门", "鹭", "xiamen", "xm"]),
    ("赣州市", "Ganzhou", "江西省", "中国", "CN", 25.8310, 114.9350, "Asia/Shanghai", 8980000, 60, ["赣州", "ganzhou", "gzo"]),
    ("九江市", "Jiujiang", "江西省", "中国", "CN", 29.7050, 116.0020, "Asia/Shanghai", 4580000, 40, ["九江", "jiujiang", "jj"]),
    ("上饶市", "Shangrao", "江西省", "中国", "CN", 28.4550, 117.9430, "Asia/Shanghai", 6490000, 50, ["上饶", "shangrao", "sr"]),
    ("景德镇市", "Jingdezhen", "江西省", "中国", "CN", 29.2750, 117.1780, "Asia/Shanghai", 1620000, 25, ["景德镇", "jingdezhen", "jdz"]),
    ("烟台市", "Yantai", "山东省", "中国", "CN", 37.4638, 121.4479, "Asia/Shanghai", 7100000, 40, ["烟台", "yantai", "yt"]),
    ("潍坊市", "Weifang", "山东省", "中国", "CN", 36.7064, 119.1620, "Asia/Shanghai", 9420000, 40, ["潍坊", "weifang", "wf"]),
    ("济宁市", "Jining", "山东省", "中国", "CN", 35.4140, 116.5870, "Asia/Shanghai", 8360000, 45, ["济宁", "jining", "jog"]),
    ("临沂市", "Linyi", "山东省", "中国", "CN", 35.1040, 118.3560, "Asia/Shanghai", 11000000, 50, ["临沂", "linyi", "li"]),
    ("菏泽市", "Heze", "山东省", "中国", "CN", 35.2330, 115.4800, "Asia/Shanghai", 8790000, 45, ["菏泽", "heze", "hz"]),
    ("泰安市", "Tai'an", "山东省", "中国", "CN", 36.1880, 117.1300, "Asia/Shanghai", 5470000, 30, ["泰安", "taian", "ta"]),
    ("淄博市", "Zibo", "山东省", "中国", "CN", 36.8130, 118.0550, "Asia/Shanghai", 4700000, 30, ["淄博", "zibo", "zb"]),
    ("洛阳市", "Luoyang", "河南省", "中国", "CN", 34.6197, 112.4540, "Asia/Shanghai", 7060000, 35, ["洛阳", "luoyang", "lyo"]),
    ("开封市", "Kaifeng", "河南省", "中国", "CN", 34.7970, 114.3070, "Asia/Shanghai", 4820000, 30, ["开封", "kaifeng", "kf"]),
    ("南阳市", "Nanyang", "河南省", "中国", "CN", 32.9908, 112.5280, "Asia/Shanghai", 9630000, 50, ["南阳", "nanyang", "ny"]),
    ("商丘市", "Shangqiu", "河南省", "中国", "CN", 34.4390, 115.6590, "Asia/Shanghai", 7800000, 40, ["商丘", "shangqiu", "sq"]),
    ("周口市", "Zhoukou", "河南省", "中国", "CN", 33.6204, 114.6500, "Asia/Shanghai", 8850000, 45, ["周口", "zhoukou", "zk"]),
    ("信阳市", "Xinyang", "河南省", "中国", "CN", 32.1240, 114.0910, "Asia/Shanghai", 6230000, 45, ["信阳", "xinyang", "xo"]),
    ("安阳市", "Anyang", "河南省", "中国", "CN", 36.0980, 114.3930, "Asia/Shanghai", 5450000, 35, ["安阳", "anyang", "ao"]),
    ("新乡市", "Xinxiang", "河南省", "中国", "CN", 35.3030, 113.9260, "Asia/Shanghai", 6250000, 35, ["新乡", "xinxiang", "xx"]),
    ("宜昌市", "Yichang", "湖北省", "中国", "CN", 30.6919, 111.2860, "Asia/Shanghai", 4000000, 40, ["宜昌", "yichang", "yc"]),
    ("襄阳市", "Xiangyang", "湖北省", "中国", "CN", 32.0419, 112.1220, "Asia/Shanghai", 5260000, 40, ["襄阳", "xiangyang", "xo"]),
    ("十堰市", "Shiyan", "湖北省", "中国", "CN", 32.6250, 110.7810, "Asia/Shanghai", 3210000, 50, ["十堰", "shiyan", "so"]),
    ("衡阳市", "Hengyang", "湖南省", "中国", "CN", 26.9000, 112.5720, "Asia/Shanghai", 6640000, 35, ["衡阳", "hengyang", "ho"]),
    ("岳阳市", "Yueyang", "湖南省", "中国", "CN", 29.3570, 113.1290, "Asia/Shanghai", 5060000, 35, ["岳阳", "yueyang", "yo"]),
    ("常德市", "Changde", "湖南省", "中国", "CN", 29.0110, 111.6990, "Asia/Shanghai", 5280000, 40, ["常德", "changde", "co"]),
    ("邵阳市", "Shaoyang", "湖南省", "中国", "CN", 27.2390, 111.4690, "Asia/Shanghai", 6620000, 45, ["邵阳", "shaoyang", "soy"]),
    ("佛山市", "Foshan", "广东省", "中国", "CN", 23.0218, 113.1219, "Asia/Shanghai", 9500000, 25, ["佛山", "foshan", "fo"]),
    ("东莞市", "Dongguan", "广东省", "中国", "CN", 23.0207, 113.7518, "Asia/Shanghai", 10470000, 30, ["东莞", "dongguan", "dg"]),
    ("中山市", "Zhongshan", "广东省", "中国", "CN", 22.5170, 113.3930, "Asia/Shanghai", 4420000, 25, ["中山", "zhongshan", "zs"]),
    ("珠海市", "Zhuhai", "广东省", "中国", "CN", 22.2707, 113.5768, "Asia/Shanghai", 2440000, 25, ["珠海", "zhuhai", "zo"]),
    ("汕头市", "Shantou", "广东省", "中国", "CN", 23.3535, 116.6820, "Asia/Shanghai", 5500000, 30, ["汕头", "shantou", "sto"]),
    ("湛江市", "Zhanjiang", "广东省", "中国", "CN", 21.2719, 110.3570, "Asia/Shanghai", 6990000, 45, ["湛江", "zhanjiang", "zo"]),
    ("惠州市", "Huizhou", "广东省", "中国", "CN", 23.1120, 114.4160, "Asia/Shanghai", 6070000, 35, ["惠州", "huizhou", "ho"]),
    ("江门市", "Jiangmen", "广东省", "中国", "CN", 22.5800, 113.0820, "Asia/Shanghai", 4800000, 30, ["江门", "jiangmen", "jm"]),
    ("茂名市", "Maoming", "广东省", "中国", "CN", 21.6630, 110.9250, "Asia/Shanghai", 6200000, 40, ["茂名", "maoming", "mo"]),
    ("梅州市", "Meizhou", "广东省", "中国", "CN", 24.2880, 116.1220, "Asia/Shanghai", 4100000, 40, ["梅州", "meizhou", "mz"]),
    ("柳州市", "Liuzhou", "广西壮族自治区", "中国", "CN", 24.3146, 109.4280, "Asia/Shanghai", 4150000, 30, ["柳州", "liuzhou", "lzo"]),
    ("桂林市", "Guilin", "广西壮族自治区", "中国", "CN", 25.2736, 110.2900, "Asia/Shanghai", 4930000, 40, ["桂林", "guilin", "gl"]),
    ("北海市", "Beihai", "广西壮族自治区", "中国", "CN", 21.4816, 109.1200, "Asia/Shanghai", 1850000, 30, ["北海", "beihai", "bo"]),
    ("三亚市", "Sanya", "海南省", "中国", "CN", 18.2528, 109.5119, "Asia/Shanghai", 1030000, 30, ["三亚", "sanya", "sa"]),
    ("绵阳市", "Mianyang", "四川省", "中国", "CN", 31.4680, 104.6790, "Asia/Shanghai", 4870000, 40, ["绵阳", "mianyang", "myo"]),
    ("宜宾市", "Yibin", "四川省", "中国", "CN", 28.7700, 104.6310, "Asia/Shanghai", 4600000, 45, ["宜宾", "yibin", "yb"]),
    ("南充市", "Nanchong", "四川省", "中国", "CN", 30.8370, 106.1100, "Asia/Shanghai", 5630000, 45, ["南充", "nanchong", "no"]),
    ("乐山市", "Leshan", "四川省", "中国", "CN", 29.5520, 103.7660, "Asia/Shanghai", 3500000, 40, ["乐山", "leshan", "lo"]),
    ("自贡市", "Zigong", "四川省", "中国", "CN", 29.3390, 104.7780, "Asia/Shanghai", 2570000, 30, ["自贡", "zigong", "zg"]),
    ("攀枝花市", "Panzhihua", "四川省", "中国", "CN", 26.5820, 101.7140, "Asia/Shanghai", 1220000, 35, ["攀枝花", "panzhihua", "pzh"]),
    ("达州市", "Dazhou", "四川省", "中国", "CN", 31.2090, 107.4680, "Asia/Shanghai", 5400000, 50, ["达州", "dazhou", "da"]),
    ("遵义市", "Zunyi", "贵州省", "中国", "CN", 27.7210, 106.9280, "Asia/Shanghai", 6600000, 50, ["遵义", "zunyi", "zy"]),
    ("曲靖市", "Qujing", "云南省", "中国", "CN", 25.4900, 103.7960, "Asia/Shanghai", 5770000, 50, ["曲靖", "qujing", "qo"]),
    ("大理市", "Dali", "云南省大理白族自治州", "中国", "CN", 25.6065, 100.2680, "Asia/Shanghai", 800000, 25, ["大理", "dali", "dl"]),
    ("丽江市", "Lijiang", "云南省", "中国", "CN", 26.8550, 100.2330, "Asia/Shanghai", 1290000, 50, ["丽江", "lijiang", "lj"]),
    ("玉溪市", "Yuxi", "云南省", "中国", "CN", 24.3520, 102.5420, "Asia/Shanghai", 2250000, 40, ["玉溪", "yuxi", "yo"]),
    ("昌都市", "Chamdo", "西藏自治区", "中国", "CN", 31.1360, 97.1780, "Asia/Shanghai", 760000, 90, ["昌都", "chamdo", "cd"]),
    ("林芝市", "Nyingchi", "西藏自治区", "中国", "CN", 29.6540, 94.3620, "Asia/Shanghai", 240000, 100, ["林芝", "nyingchi", "ni"]),
    ("咸阳市", "Xianyang", "陕西省", "中国", "CN", 34.3330, 108.7080, "Asia/Shanghai", 4200000, 25, ["咸阳", "xianyang", "xo"]),
    ("宝鸡市", "Baoji", "陕西省", "中国", "CN", 34.3620, 107.2370, "Asia/Shanghai", 3320000, 35, ["宝鸡", "baoji", "bo"]),
    ("延安市", "Yan'an", "陕西省", "中国", "CN", 36.5850, 109.4980, "Asia/Shanghai", 2290000, 55, ["延安", "yanan", "oa"]),
    ("汉中市", "Hanzhong", "陕西省", "中国", "CN", 33.0690, 107.0230, "Asia/Shanghai", 3410000, 45, ["汉中", "hanzhong", "ho"]),
    ("天水市", "Tianshui", "甘肃省", "中国", "CN", 34.5810, 105.7250, "Asia/Shanghai", 3000000, 45, ["天水", "tianshui", "ti"]),
    ("嘉峪关市", "Jiayuguan", "甘肃省", "中国", "CN", 39.7730, 98.2900, "Asia/Shanghai", 315000, 20, ["嘉峪关", "jiayuguan", "jyg"]),
    ("敦煌市", "Dunhuang", "甘肃省酒泉市", "中国", "CN", 40.1420, 94.6620, "Asia/Shanghai", 200000, 40, ["敦煌", "dunhuang", "do"]),
    ("酒泉市", "Jiuquan", "甘肃省", "中国", "CN", 39.7330, 98.4940, "Asia/Shanghai", 1100000, 100, ["酒泉", "jiuquan", "jo"]),
    ("张掖市", "Zhangye", "甘肃省", "中国", "CN", 38.9300, 100.4500, "Asia/Shanghai", 1200000, 80, ["张掖", "zhangye", "zo"]),
    ("武威市", "Wuwei", "甘肃省", "中国", "CN", 37.9290, 102.6380, "Asia/Shanghai", 1500000, 50, ["武威", "wuwei", "wo"]),
    ("吴忠市", "Wuzhong", "宁夏回族自治区", "中国", "CN", 37.9860, 106.1990, "Asia/Shanghai", 1380000, 40, ["吴忠", "wuzhong", "wo"]),
    ("中卫市", "Zhongwei", "宁夏回族自治区", "中国", "CN", 37.5150, 105.1900, "Asia/Shanghai", 1070000, 45, ["中卫", "zhongwei", "zo"]),
    ("石嘴山市", "Shizuishan", "宁夏回族自治区", "中国", "CN", 39.0180, 106.3760, "Asia/Shanghai", 750000, 25, ["石嘴山", "shizuishan", "szs"]),
    ("格尔木市", "Golmud", "青海省海西蒙古族藏族自治州", "中国", "CN", 36.4064, 94.9010, "Asia/Shanghai", 230000, 90, ["格尔木", "golmud", "gem"]),
    ("喀什市", "Kashgar", "新疆维吾尔自治区喀什地区", "中国", "CN", 39.4704, 75.9900, "Asia/Kashgar", 800000, 30, ["喀什", "kashgar", "kashi", "ks"]),
    ("伊宁市", "Yining", "新疆维吾尔自治区伊犁哈萨克自治州", "中国", "CN", 43.9080, 81.2850, "Asia/Urumqi", 700000, 35, ["伊宁", "yining", "o"]),
    ("库尔勒市", "Korla", "新疆维吾尔自治区巴音郭楞蒙古自治州", "中国", "CN", 41.7640, 86.1460, "Asia/Urumqi", 580000, 50, ["库尔勒", "korla", "ke"]),
    ("哈密市", "Hami", "新疆维吾尔自治区", "中国", "CN", 42.8330, 93.5140, "Asia/Urumqi", 670000, 80, ["哈密", "hami", "ha"]),
    ("吐鲁番市", "Turpan", "新疆维吾尔自治区", "中国", "CN", 42.9510, 89.1890, "Asia/Urumqi", 690000, 50, ["吐鲁番", "turpan", "tl"]),
    ("阿克苏市", "Aksu", "新疆维吾尔自治区阿克苏地区", "中国", "CN", 41.1710, 80.2600, "Asia/Kashgar", 590000, 60, ["阿克苏", "aksu", "aek"]),
    ("克拉玛依市", "Karamay", "新疆维吾尔自治区", "中国", "CN", 45.6000, 84.8700, "Asia/Urumqi", 490000, 40, ["克拉玛依", "karamay", "kly"]),
    ("石河子市", "Shihezi", "新疆维吾尔自治区", "中国", "CN", 44.3100, 86.0800, "Asia/Urumqi", 780000, 25, ["石河子", "shihezi", "shz"]),
]

# 其余地级市/自治州/盟驻地（含济源/仙桃等省辖市与兵团直辖市），补齐大陆地级行政区。
# 州/盟驻地用「驻地名（州/盟名）」形式，保证两个名字都能被中文检索命中。
CN_MORE = [
    # 河北省（3）
    ("邢台市", "Xingtai", "河北省", "中国", "CN", 37.0702, 114.5044, "Asia/Shanghai", 7500000, 35, ["xingtai", "xt"]),
    ("承德市", "Chengde", "河北省", "中国", "CN", 40.9512, 117.9275, "Asia/Shanghai", 3350000, 40, ["chengde", "cd"]),
    ("衡水市", "Hengshui", "河北省", "中国", "CN", 37.7359, 115.6705, "Asia/Shanghai", 4210000, 35, ["hengshui", "hs"]),
    # 山西省（5）
    ("阳泉市", "Yangquan", "山西省", "中国", "CN", 37.8572, 113.5833, "Asia/Shanghai", 1320000, 25, ["yangquan", "yq"]),
    ("朔州市", "Shuozhou", "山西省", "中国", "CN", 39.3312, 112.4334, "Asia/Shanghai", 1590000, 35, ["shuozhou", "sz"]),
    ("晋中市", "Jinzhong", "山西省", "中国", "CN", 37.6872, 112.7380, "Asia/Shanghai", 3380000, 35, ["jinzhong", "jz"]),
    ("忻州市", "Xinzhou", "山西省", "中国", "CN", 38.4170, 112.7335, "Asia/Shanghai", 2690000, 50, ["xinzhou", "xz"]),
    ("吕梁市", "Luliang", "山西省", "中国", "CN", 37.5183, 111.1430, "Asia/Shanghai", 3400000, 50, ["lüliang", "lvliang", "ll"]),
    # 内蒙古自治区（6：地级市 + 盟驻地）
    ("乌海市", "Wuhai", "内蒙古自治区", "中国", "CN", 39.6737, 106.8256, "Asia/Shanghai", 560000, 25, ["wuhai", "wh"]),
    ("巴彦淖尔市", "Bayannur", "内蒙古自治区", "中国", "CN", 40.7570, 107.4162, "Asia/Shanghai", 1510000, 50, ["bayannaoer", "byne"]),
    ("乌兰察布市", "Ulanqab", "内蒙古自治区", "中国", "CN", 41.0225, 113.1119, "Asia/Shanghai", 1790000, 50, ["wulanchabu", "wlcb"]),
    ("锡林浩特市(锡林郭勒盟)", "Xilinhot", "内蒙古自治区锡林郭勒盟", "中国", "CN", 43.9334, 116.0820, "Asia/Shanghai", 300000, 40, ["xilinhuote", "xlht"]),
    ("乌兰浩特市(兴安盟)", "Ulanhot", "内蒙古自治区兴安盟", "中国", "CN", 46.0687, 122.0700, "Asia/Shanghai", 370000, 35, ["ulanhaote", "ulht"]),
    ("巴彦浩特镇(阿拉善盟)", "Bayanhot", "内蒙古自治区阿拉善盟", "中国", "CN", 38.8514, 105.8491, "Asia/Shanghai", 130000, 60, ["bayanhaote", "alashan", "blht"]),
    # 辽宁省（9）
    ("抚顺市", "Fushun", "辽宁省", "中国", "CN", 41.8807, 123.8746, "Asia/Shanghai", 1860000, 30, ["fushun", "fs"]),
    ("本溪市", "Benxi", "辽宁省", "中国", "CN", 41.2983, 123.7604, "Asia/Shanghai", 1380000, 30, ["benxi", "bx"]),
    ("营口市", "Yingkou", "辽宁省", "中国", "CN", 40.6670, 122.2358, "Asia/Shanghai", 1870000, 30, ["yingkou", "yk"]),
    ("朝阳市", "Chaoyang", "辽宁省", "中国", "CN", 41.5737, 120.4504, "Asia/Shanghai", 2880000, 40, ["chaoyang", "cy"]),
    ("阜新市", "Fuxin", "辽宁省", "中国", "CN", 42.0215, 121.6680, "Asia/Shanghai", 1650000, 30, ["fuxin", "fx"]),
    ("辽阳市", "Liaoyang", "辽宁省", "中国", "CN", 41.2675, 123.1770, "Asia/Shanghai", 1530000, 25, ["liaoyang", "liao"]),
    ("盘锦市", "Panjin", "辽宁省", "中国", "CN", 41.1195, 122.0707, "Asia/Shanghai", 1390000, 30, ["panjin", "pj"]),
    ("葫芦岛市", "Huludao", "辽宁省", "中国", "CN", 40.7135, 120.8376, "Asia/Shanghai", 2360000, 40, ["huludao", "hld"]),
    ("铁岭市", "Tieling", "辽宁省", "中国", "CN", 42.2873, 123.8480, "Asia/Shanghai", 2390000, 35, ["tieling", "tl"]),
    # 吉林省（5 地级市 + 延边州驻地）
    ("延吉市(延边州)", "Yanji", "吉林省延边朝鲜族自治州", "中国", "CN", 42.8965, 129.5100, "Asia/Shanghai", 520000, 30, ["yanbian", "yanji", "yj"]),
    ("四平市", "Siping", "吉林省", "中国", "CN", 43.1665, 124.3507, "Asia/Shanghai", 1810000, 40, ["siping", "sp"]),
    ("通化市", "Tonghua", "吉林省", "中国", "CN", 41.7280, 125.9403, "Asia/Shanghai", 1820000, 35, ["tonghua", "th"]),
    ("白山市", "Baishan", "吉林省", "中国", "CN", 41.9416, 126.4277, "Asia/Shanghai", 950000, 40, ["baishan", "bs"]),
    ("松原市", "Songyuan", "吉林省", "中国", "CN", 45.1418, 124.8254, "Asia/Shanghai", 2380000, 45, ["songyuan", "syo"]),
    ("白城市", "Baicheng", "吉林省", "中国", "CN", 45.6210, 122.8370, "Asia/Shanghai", 1550000, 45, ["baicheng", "bc"]),
    # 黑龙江省（9 地级市 + 大兴安岭地区驻地）
    ("佳木斯市", "Jiamusi", "黑龙江省", "中国", "CN", 46.8236, 130.3230, "Asia/Shanghai", 2160000, 40, ["jiamusi", "jms"]),
    ("大庆市", "Daqing", "黑龙江省", "中国", "CN", 46.5914, 125.1036, "Asia/Shanghai", 2780000, 35, ["daqing", "dq"]),
    ("鸡西市", "Jixi", "黑龙江省", "中国", "CN", 45.2950, 130.9695, "Asia/Shanghai", 1500000, 35, ["jixi", "jx"]),
    ("鹤岗市", "Hegang", "黑龙江省", "中国", "CN", 47.3454, 130.2979, "Asia/Shanghai", 740000, 30, ["hegang", "hg"]),
    ("双鸭山市", "Shuangyashan", "黑龙江省", "中国", "CN", 46.6466, 131.1594, "Asia/Shanghai", 830000, 35, ["shuangyashan", "sys"]),
    ("七台河市", "Qitaihe", "黑龙江省", "中国", "CN", 45.7713, 130.8645, "Asia/Shanghai", 690000, 25, ["qitaihe", "qth"]),
    ("黑河市", "Heihe", "黑龙江省", "中国", "CN", 50.2443, 127.5299, "Asia/Shanghai", 1290000, 50, ["heihe", "hh"]),
    ("绥化市", "Suihua", "黑龙江省", "中国", "CN", 46.6338, 126.9745, "Asia/Shanghai", 3760000, 45, ["suihua", "sui"]),
    ("伊春市", "Yichun", "黑龙江省", "中国", "CN", 47.7273, 128.8911, "Asia/Shanghai", 830000, 70, ["yichun-heilongjiang", "yichun", "yich"]),
    ("加格达奇(大兴安岭地区)", "Jiagedaqi", "黑龙江省大兴安岭地区", "中国", "CN", 50.4135, 124.1211, "Asia/Shanghai", 110000, 40, ["daxinganning", "jgdq"]),
    # 江苏省（3）
    ("连云港市", "Lianyungang", "江苏省", "中国", "CN", 34.5967, 119.1245, "Asia/Shanghai", 4600000, 35, ["lianyungang", "lyg"]),
    ("淮安市", "Huai'an", "江苏省", "中国", "CN", 33.5006, 119.0206, "Asia/Shanghai", 4550000, 35, ["huaian", "ha"]),
    ("宿迁市", "Suqian", "江苏省", "中国", "CN", 33.9396, 118.2977, "Asia/Shanghai", 4990000, 35, ["suqian", "sqq"]),
    # 浙江省（4）
    ("湖州市", "Huzhou", "浙江省", "中国", "CN", 30.8939, 120.0886, "Asia/Shanghai", 3370000, 30, ["huzhou", "hz"]),
    ("衢州市", "Quzhou", "浙江省", "中国", "CN", 28.9353, 118.8675, "Asia/Shanghai", 2280000, 35, ["quzhou", "qzo"]),
    ("舟山市", "Zhoushan", "浙江省", "中国", "CN", 29.9927, 122.2064, "Asia/Shanghai", 1160000, 25, ["zhoushan", "zs"]),
    ("丽水市", "Lishui", "浙江省", "中国", "CN", 28.4686, 119.9227, "Asia/Shanghai", 2190000, 35, ["lishui", "ls"]),
    # 安徽省（12）
    ("蚌埠市", "Bengbu", "安徽省", "中国", "CN", 32.9169, 117.3532, "Asia/Shanghai", 3300000, 30, ["bengbu", "bb"]),
    ("淮南市", "Huainan", "安徽省", "中国", "CN", 32.6267, 116.8107, "Asia/Shanghai", 3030000, 30, ["huainan", "hnn"]),
    ("马鞍山市", "Ma'anshan", "安徽省", "中国", "CN", 31.6707, 118.5090, "Asia/Shanghai", 2160000, 25, ["maanshan", "mas"]),
    ("淮北市", "Huaibei", "安徽省", "中国", "CN", 33.9531, 116.7979, "Asia/Shanghai", 1970000, 30, ["huaibei", "hob"]),
    ("铜陵市", "Tongling", "安徽省", "中国", "CN", 30.9456, 117.8125, "Asia/Shanghai", 1310000, 25, ["tongling", "tli"]),
    ("黄山市", "Huangshan", "安徽省", "中国", "CN", 29.7149, 118.3375, "Asia/Shanghai", 1320000, 30, ["huangshan", "hsg"]),
    ("滁州市", "Chuzhou", "安徽省", "中国", "CN", 32.3022, 118.3176, "Asia/Shanghai", 3990000, 40, ["chuzhou", "czh"]),
    ("宿州市", "Suzhou", "安徽省", "中国", "CN", 33.6338, 116.9844, "Asia/Shanghai", 5300000, 40, ["anhui suzhou", "suzhou-ah", "suzh"]),
    ("六安市", "Lu'an", "安徽省", "中国", "CN", 31.7512, 116.5076, "Asia/Shanghai", 4390000, 40, ["luan", "la"]),
    ("亳州市", "Bozhou", "安徽省", "中国", "CN", 33.8695, 115.7770, "Asia/Shanghai", 4990000, 35, ["bozhou", "bz"]),
    ("池州市", "Chizhou", "安徽省", "中国", "CN", 30.6594, 117.4885, "Asia/Shanghai", 1150000, 30, ["chizhou", "ciz"]),
    ("宣城市", "Xuancheng", "安徽省", "中国", "CN", 30.9406, 118.7577, "Asia/Shanghai", 2500000, 35, ["xuancheng", "xch"]),
    # 福建省（5）
    ("莆田市", "Putian", "福建省", "中国", "CN", 25.4311, 119.0078, "Asia/Shanghai", 3210000, 25, ["putian", "pt"]),
    ("三明市", "Sanming", "福建省", "中国", "CN", 26.2655, 117.6390, "Asia/Shanghai", 2430000, 40, ["sanming", "smg"]),
    ("南平市", "Nanping", "福建省", "中国", "CN", 26.6386, 118.1279, "Asia/Shanghai", 2640000, 45, ["nanping", "npg"]),
    ("宁德市", "Ningde", "福建省", "中国", "CN", 26.6612, 119.5271, "Asia/Shanghai", 3150000, 40, ["ningde", "nde"]),
    ("龙岩市", "Longyan", "福建省", "中国", "CN", 25.0907, 117.0288, "Asia/Shanghai", 2730000, 40, ["longyan", "lyo"]),
    # 江西省（6）
    ("萍乡市", "Pingxiang", "江西省", "中国", "CN", 27.6231, 113.8549, "Asia/Shanghai", 1800000, 30, ["pingxiang", "pxg"]),
    ("新余市", "Xinyu", "江西省", "中国", "CN", 27.8170, 114.9252, "Asia/Shanghai", 1210000, 25, ["xinyu", "xyu"]),
    ("鹰潭市", "Yingtan", "江西省", "中国", "CN", 28.2390, 117.0450, "Asia/Shanghai", 1150000, 25, ["yingtan", "yta"]),
    ("吉安市", "Ji'an", "江西省", "中国", "CN", 27.1134, 114.9928, "Asia/Shanghai", 4460000, 45, ["jian", "ja"]),
    ("宜春市", "Yichun", "江西省", "中国", "CN", 27.8157, 114.4028, "Asia/Shanghai", 5000000, 40, ["yichun-jiangxi", "yichun", "yic"]),
    ("抚州市", "Fuzhou", "江西省", "中国", "CN", 27.9512, 116.3583, "Asia/Shanghai", 1770000, 35, ["fuzhou-jx", "jiangxi fuzhou", "fzo"]),
    # 山东省（7）
    ("枣庄市", "Zaozhuang", "山东省", "中国", "CN", 34.8100, 117.3238, "Asia/Shanghai", 3860000, 30, ["zaozhuang", "zao"]),
    ("东营市", "Dongying", "山东省", "中国", "CN", 37.4638, 118.6108, "Asia/Shanghai", 2190000, 30, ["dongying", "dyi"]),
    ("威海市", "Weihai", "山东省", "中国", "CN", 37.4639, 122.1204, "Asia/Shanghai", 2910000, 30, ["weihai", "whi"]),
    ("日照市", "Rizhao", "山东省", "中国", "CN", 35.4164, 119.5271, "Asia/Shanghai", 2970000, 30, ["rizhao", "rz"]),
    ("德州市", "Dezhou", "山东省", "中国", "CN", 37.4357, 116.3569, "Asia/Shanghai", 4910000, 40, ["dezhou", "dzo"]),
    ("聊城市", "Liaocheng", "山东省", "中国", "CN", 36.4564, 115.9806, "Asia/Shanghai", 5950000, 40, ["liaocheng", "lcg"]),
    ("滨州市", "Binzhou", "山东省", "中国", "CN", 37.3824, 118.0260, "Asia/Shanghai", 3930000, 35, ["binzhou", "bzo"]),
    # 河南省（8 地级市 + 省辖济源）
    ("平顶山市", "Pingdingshan", "河南省", "中国", "CN", 33.7693, 113.1929, "Asia/Shanghai", 4990000, 35, ["pingdingshan", "pds"]),
    ("鹤壁市", "Hebi", "河南省", "中国", "CN", 35.7482, 114.2954, "Asia/Shanghai", 1570000, 25, ["hebi", "hb2"]),
    ("焦作市", "Jiaozuo", "河南省", "中国", "CN", 35.2159, 113.2415, "Asia/Shanghai", 3540000, 30, ["jiaozuo", "jzo"]),
    ("濮阳市", "Puyang", "河南省", "中国", "CN", 35.7616, 115.0292, "Asia/Shanghai", 3770000, 30, ["puyang", "py"]),
    ("许昌市", "Xuchang", "河南省", "中国", "CN", 34.0357, 113.8518, "Asia/Shanghai", 4380000, 30, ["xuchang", "xcg"]),
    ("漯河市", "Luohe", "河南省", "中国", "CN", 33.5767, 114.0166, "Asia/Shanghai", 2370000, 25, ["luohe", "lh"]),
    ("三门峡市", "Sanmenxia", "河南省", "中国", "CN", 34.7727, 111.2003, "Asia/Shanghai", 2030000, 35, ["sanmenxia", "smx"]),
    ("驻马店市", "Zhumadian", "河南省", "中国", "CN", 32.9802, 114.0229, "Asia/Shanghai", 7010000, 40, ["zhumadian", "zmd"]),
    ("济源市", "Jiyuan", "河南省", "中国", "CN", 35.0688, 112.6019, "Asia/Shanghai", 730000, 25, ["jiyuan", "jyu"]),
    # 湖北省（8 地级市 + 恩施州驻地 + 3 省辖市）
    ("黄石市", "Huangshi", "湖北省", "中国", "CN", 30.2025, 115.0389, "Asia/Shanghai", 2470000, 25, ["huangshi", "hsg2"]),
    ("鄂州市", "Ezhou", "湖北省", "中国", "CN", 30.3963, 114.8944, "Asia/Shanghai", 1070000, 20, ["ezhou", "ez"]),
    ("荆门市", "Jingmen", "湖北省", "中国", "CN", 31.0354, 112.2005, "Asia/Shanghai", 2600000, 35, ["jingmen", "jmn"]),
    ("孝感市", "Xiaogan", "湖北省", "中国", "CN", 30.9246, 113.9165, "Asia/Shanghai", 4270000, 35, ["xiaogan", "xg"]),
    ("荆州市", "Jingzhou", "湖北省", "中国", "CN", 30.3315, 112.2411, "Asia/Shanghai", 5240000, 35, ["jingzhou", "jog2"]),
    ("黄冈市", "Huanggang", "湖北省", "中国", "CN", 30.4536, 114.8722, "Asia/Shanghai", 5880000, 40, ["huanggang", "hgg"]),
    ("咸宁市", "Xianning", "湖北省", "中国", "CN", 29.8412, 114.3224, "Asia/Shanghai", 1940000, 30, ["xianning", "xin"]),
    ("随州市", "Suizhou", "湖北省", "中国", "CN", 31.6958, 113.3829, "Asia/Shanghai", 2040000, 35, ["suizhou", "szo"]),
    ("恩施市(恩施州)", "Enshi", "湖北省恩施土家族苗族自治州", "中国", "CN", 30.2737, 109.4884, "Asia/Shanghai", 820000, 45, ["enshi", "ens"]),
    ("仙桃市", "Xiantao", "湖北省", "中国", "CN", 30.3650, 113.4431, "Asia/Shanghai", 1130000, 25, ["xiantao", "xta"]),
    ("潜江市", "Qianjiang", "湖北省", "中国", "CN", 30.4221, 112.8992, "Asia/Shanghai", 840000, 25, ["qianjiang", "qjo"]),
    ("天门市", "Tianmen", "湖北省", "中国", "CN", 30.6645, 113.1657, "Asia/Shanghai", 1150000, 25, ["tianmen", "tmm"]),
    # 湖南省（7 地级市 + 湘西州驻地）
    ("株洲市", "Zhuzhou", "湖南省", "中国", "CN", 27.8274, 113.1340, "Asia/Shanghai", 2890000, 30, ["zhuzhou", "zho"]),
    ("湘潭市", "Xiangtan", "湖南省", "中国", "CN", 27.8297, 112.9340, "Asia/Shanghai", 2730000, 25, ["xiangtan", "xtan"]),
    ("张家界市", "Zhangjiajie", "湖南省", "中国", "CN", 29.1166, 110.4789, "Asia/Shanghai", 1510000, 30, ["zhangjiajie", "zjj"]),
    ("益阳市", "Yiyang", "湖南省", "中国", "CN", 28.5538, 112.3550, "Asia/Shanghai", 3850000, 35, ["yiyang", "yiy"]),
    ("郴州市", "Chenzhou", "湖南省", "中国", "CN", 25.7708, 113.0311, "Asia/Shanghai", 4660000, 40, ["chenzhou", "czc"]),
    ("永州市", "Yongzhou", "湖南省", "中国", "CN", 26.4535, 111.6130, "Asia/Shanghai", 5290000, 40, ["yongzhou", "yzo"]),
    ("怀化市", "Huaihua", "湖南省", "中国", "CN", 27.5550, 109.9920, "Asia/Shanghai", 4590000, 45, ["huaihua", "hth"]),
    ("娄底市", "Loudi", "湖南省", "中国", "CN", 27.7037, 111.9936, "Asia/Shanghai", 3830000, 30, ["loudi", "ldi"]),
    ("吉首市(湘西州)", "Jishou", "湖南省湘西土家族苗族自治州", "中国", "CN", 28.3120, 109.7390, "Asia/Shanghai", 290000, 30, ["xiangxi", "jishou", "jsh"]),
    # 广东省（9）
    ("韶关市", "Shaoguan", "广东省", "中国", "CN", 24.8100, 113.5971, "Asia/Shanghai", 2860000, 40, ["shaoguan", "sog"]),
    ("肇庆市", "Zhaoqing", "广东省", "中国", "CN", 23.0470, 112.4652, "Asia/Shanghai", 4110000, 35, ["zhaoqing", "zq"]),
    ("汕尾市", "Shanwei", "广东省", "中国", "CN", 22.7858, 115.3642, "Asia/Shanghai", 2670000, 35, ["shanwei", "swi"]),
    ("河源市", "Heyuan", "广东省", "中国", "CN", 23.7464, 114.7007, "Asia/Shanghai", 2840000, 35, ["heyuan", "hy"]),
    ("阳江市", "Yangjiang", "广东省", "中国", "CN", 21.8596, 111.9834, "Asia/Shanghai", 2600000, 35, ["yangjiang", "yji"]),
    ("清远市", "Qingyuan", "广东省", "中国", "CN", 23.6818, 113.0567, "Asia/Shanghai", 3970000, 40, ["qingyuan", "qyg"]),
    ("潮州市", "Chaozhou", "广东省", "中国", "CN", 23.6567, 116.6224, "Asia/Shanghai", 2530000, 25, ["chaozhou", "chz"]),
    ("揭阳市", "Jieyang", "广东省", "中国", "CN", 23.5500, 116.3724, "Asia/Shanghai", 5580000, 30, ["jieyang", "jy"]),
    ("云浮市", "Yunfu", "广东省", "中国", "CN", 22.9152, 112.0440, "Asia/Shanghai", 2330000, 35, ["yunfu", "yfu"]),
    # 广西壮族自治区（10）
    ("梧州市", "Wuzhou", "广西壮族自治区", "中国", "CN", 23.4770, 111.2992, "Asia/Shanghai", 2830000, 35, ["wuzhou", "wzo"]),
    ("防城港市", "Fangchenggang", "广西壮族自治区", "中国", "CN", 21.6173, 108.3553, "Asia/Shanghai", 1050000, 30, ["fangchenggang", "fcg"]),
    ("钦州市", "Qinzhou", "广西壮族自治区", "中国", "CN", 21.9536, 108.6543, "Asia/Shanghai", 3310000, 35, ["qinzhou", "qzh"]),
    ("贵港市", "Guigang", "广西壮族自治区", "中国", "CN", 23.1106, 109.6069, "Asia/Shanghai", 4350000, 35, ["guigang", "ggu"]),
    ("玉林市", "Yulin", "广西壮族自治区", "中国", "CN", 22.6321, 110.1516, "Asia/Shanghai", 5800000, 35, ["yulin-guangxi", "yulin", "yln"]),
    ("百色市", "Baise", "广西壮族自治区", "中国", "CN", 23.9026, 106.6187, "Asia/Shanghai", 3570000, 45, ["baise", "bse"]),
    ("贺州市", "Hezhou", "广西壮族自治区", "中国", "CN", 24.4136, 111.5575, "Asia/Shanghai", 1970000, 35, ["hezhou", "hze"]),
    ("河池市", "Hechi", "广西壮族自治区", "中国", "CN", 24.6929, 108.0390, "Asia/Shanghai", 3420000, 45, ["hechi", "hch"]),
    ("来宾市", "Laibin", "广西壮族自治区", "中国", "CN", 23.7472, 109.2291, "Asia/Shanghai", 2100000, 40, ["laibin", "lbn"]),
    ("崇左市", "Chongzuo", "广西壮族自治区", "中国", "CN", 22.3769, 107.3573, "Asia/Shanghai", 2090000, 40, ["chongzuo", "czu"]),
    # 海南省（4 省辖地级市 + 4 省辖县，不含远海岛礁）
    ("儋州市", "Danzhou", "海南省", "中国", "CN", 19.5209, 109.5809, "Asia/Shanghai", 950000, 35, ["danzhou", "dzh"]),
    ("琼海市", "Qionghai", "海南省", "中国", "CN", 19.2540, 110.4740, "Asia/Shanghai", 490000, 25, ["qionghai", "qha"]),
    ("文昌市", "Wenchang", "海南省", "中国", "CN", 19.7505, 110.7500, "Asia/Shanghai", 440000, 30, ["wenchang", "wch"]),
    ("万宁市", "Wanning", "海南省", "中国", "CN", 18.9203, 110.3892, "Asia/Shanghai", 550000, 30, ["wanning", "wni"]),
    ("东方市", "Dongfang", "海南省", "中国", "CN", 19.1017, 108.6173, "Asia/Shanghai", 440000, 30, ["dongfang", "dof"]),
    ("三沙市", "Sansha", "海南省", "中国", "CN", 16.8339, 112.3345, "Asia/Shanghai", 2000, 20, ["sansha", "sya"]),
    # 四川省（8 地级市 + 3 州驻地）
    ("泸州市", "Luzhou", "四川省", "中国", "CN", 28.8717, 105.4426, "Asia/Shanghai", 4050000, 35, ["luzhou", "luz"]),
    ("德阳市", "Deyang", "四川省", "中国", "CN", 31.1279, 104.3979, "Asia/Shanghai", 4270000, 30, ["deyang", "dyg"]),
    ("广元市", "Guangyuan", "四川省", "中国", "CN", 32.4356, 105.8436, "Asia/Shanghai", 2300000, 35, ["guangyuan", "gyu"]),
    ("遂宁市", "Suining", "四川省", "中国", "CN", 30.5328, 105.5842, "Asia/Shanghai", 2820000, 30, ["suining", "sni"]),
    ("内江市", "Neijiang", "四川省", "中国", "CN", 29.5801, 105.0603, "Asia/Shanghai", 3770000, 30, ["neijiang", "njo"]),
    ("眉山市", "Meishan", "四川省", "中国", "CN", 30.0469, 103.8391, "Asia/Shanghai", 2960000, 30, ["meishan", "msh"]),
    ("广安市", "Guang'an", "四川省", "中国", "CN", 30.4306, 106.6328, "Asia/Shanghai", 3250000, 30, ["guangan", "gan"]),
    ("雅安市", "Ya'an", "四川省", "中国", "CN", 29.9917, 103.0407, "Asia/Shanghai", 1510000, 40, ["yaan", "yas"]),
    ("巴中市", "Bazhong", "四川省", "中国", "CN", 31.8588, 106.7507, "Asia/Shanghai", 2720000, 35, ["bazhong", "bzh"]),
    ("马尔康市(阿坝州)", "Barkam", "四川省阿坝藏族羌族自治州", "中国", "CN", 31.9058, 102.2087, "Asia/Shanghai", 60000, 60, ["aba", "maergang", "abaz"]),
    ("康定市(甘孜州)", "Kangding", "四川省甘孜藏族自治州", "中国", "CN", 30.0460, 101.9600, "Asia/Shanghai", 130000, 80, ["ganzi", "kangding", "gzz"]),
    ("西昌市(凉山州)", "Xichang", "四川省凉山彝族自治州", "中国", "CN", 27.8854, 102.2588, "Asia/Shanghai", 690000, 50, ["liangshan", "xichang", "lsz"]),
    # 贵州省（4 地级市 + 3 州驻地）
    ("六盘水市", "Liupanshui", "贵州省", "中国", "CN", 26.5937, 104.8317, "Asia/Shanghai", 3030000, 35, ["liupanshui", "lps"]),
    ("安顺市", "Anshun", "贵州省", "中国", "CN", 26.2534, 105.9490, "Asia/Shanghai", 2470000, 35, ["anshun", "ash"]),
    ("毕节市", "Bijie", "贵州省", "中国", "CN", 27.2895, 105.2883, "Asia/Shanghai", 6900000, 45, ["bijie", "bje"]),
    ("铜仁市", "Tongren", "贵州省", "中国", "CN", 27.7183, 109.1907, "Asia/Shanghai", 3300000, 40, ["tongren", "tng"]),
    ("凯里市(黔东南州)", "Kaili", "贵州省黔东南苗族侗族自治州", "中国", "CN", 26.5728, 107.9800, "Asia/Shanghai", 500000, 30, ["qiandongnan", "kaili", "qdn"]),
    ("都匀市(黔南州)", "Duyun", "贵州省黔南布依族苗族自治州", "中国", "CN", 26.2581, 107.5170, "Asia/Shanghai", 490000, 35, ["qiannan", "duyun", "qnn"]),
    ("兴义市(黔西南州)", "Xingyi", "贵州省黔西南布依族苗族自治州", "中国", "CN", 25.5894, 104.9037, "Asia/Shanghai", 900000, 40, ["qianxinan", "xingyi", "qxn"]),
    # 云南省（4 地级市 + 6 州驻地 + 保山）
    ("保山市", "Baoshan", "云南省", "中国", "CN", 25.1176, 99.1669, "Asia/Shanghai", 930000, 45, ["baoshan", "bso"]),
    ("昭通市", "Zhaotong", "云南省", "中国", "CN", 27.3392, 103.7141, "Asia/Shanghai", 5090000, 45, ["zhaotong", "zto"]),
    ("普洱市", "Pu'er", "云南省", "中国", "CN", 22.7818, 100.9721, "Asia/Shanghai", 2400000, 50, ["puer", "pe"]),
    ("临沧市", "Lincang", "云南省", "中国", "CN", 23.8839, 100.0879, "Asia/Shanghai", 2250000, 50, ["lincang", "lco"]),
    ("楚雄市(楚雄州)", "Chuxiong", "云南省楚雄彝族自治州", "中国", "CN", 25.0394, 101.5400, "Asia/Shanghai", 440000, 40, ["chuxiong", "cx"]),
    ("蒙自市(红河州)", "Mengzi", "云南省红河哈尼族彝族自治州", "中国", "CN", 23.3661, 103.7400, "Asia/Shanghai", 550000, 30, ["honghe", "mengzi", "hhz"]),
    ("文山市(文山州)", "Wenshan", "云南省文山壮族苗族自治州", "中国", "CN", 23.3695, 104.2800, "Asia/Shanghai", 350000, 35, ["wenshan", "ws"]),
    ("景洪市(西双版纳州)", "Jinghong", "云南省西双版纳傣族自治州", "中国", "CN", 22.0078, 100.8000, "Asia/Shanghai", 540000, 35, ["banna", "xishuangbanna", "jh2"]),
    ("芒市(德宏州)", "Mangshi", "云南省德宏傣族景颇族自治州", "中国", "CN", 24.4303, 98.5800, "Asia/Shanghai", 400000, 30, ["dehong", "mangshi", "dho"]),
    ("泸水市(怒江州)", "Lushui", "云南省怒江傈僳族自治州", "中国", "CN", 25.8510, 98.8700, "Asia/Shanghai", 140000, 60, ["nujiang", "lushui", "njo"]),
    ("香格里拉市(迪庆州)", "Shangri-La", "云南省迪庆藏族自治州", "中国", "CN", 27.8300, 99.7000, "Asia/Shanghai", 80000, 60, ["diqing", "shangrila", "dqc"]),
    # 西藏自治区（2；日喀则/阿里因经度-时区校验暂缺）
    ("山南市", "Shannan", "西藏自治区", "中国", "CN", 29.2620, 91.7780, "Asia/Shanghai", 350000, 80, ["shannan", "snn"]),
    ("那曲市", "Nagqu", "西藏自治区", "中国", "CN", 31.4798, 92.0510, "Asia/Shanghai", 500000, 100, ["nagqu", "nq"]),
    # 陕西省（5）
    ("榆林市", "Yulin", "陕西省", "中国", "CN", 38.2858, 109.7507, "Asia/Shanghai", 3600000, 45, ["yulin-shanxi", "yulin", "yls"]),
    ("渭南市", "Weinan", "陕西省", "中国", "CN", 34.4996, 109.4946, "Asia/Shanghai", 4680000, 40, ["weinan", "wcn"]),
    ("铜川市", "Tongchuan", "陕西省", "中国", "CN", 34.8990, 108.9503, "Asia/Shanghai", 700000, 25, ["tongchuan", "tch"]),
    ("安康市", "Ankang", "陕西省", "中国", "CN", 32.6831, 109.0311, "Asia/Shanghai", 2490000, 40, ["ankang", "ank"]),
    ("商洛市", "Shangluo", "陕西省", "中国", "CN", 33.8659, 109.9380, "Asia/Shanghai", 2040000, 45, ["shangluo", "shl"]),
    # 甘肃省（5 地级市 + 2 州驻地）
    ("金昌市", "Jinchang", "甘肃省", "中国", "CN", 38.5104, 102.1880, "Asia/Shanghai", 440000, 25, ["jinchang", "jc"]),
    ("白银市", "Baiyin", "甘肃省", "中国", "CN", 36.5466, 104.1400, "Asia/Shanghai", 1510000, 35, ["baiyin", "by"]),
    ("平凉市", "Pingliang", "甘肃省", "中国", "CN", 35.5428, 106.6790, "Asia/Shanghai", 1890000, 40, ["pingliang", "pgl"]),
    ("庆阳市", "Qingyang", "甘肃省", "中国", "CN", 35.7357, 107.6400, "Asia/Shanghai", 2150000, 45, ["qingyang", "qya"]),
    ("定西市", "Dingxi", "甘肃省", "中国", "CN", 35.5802, 104.6200, "Asia/Shanghai", 2550000, 45, ["dingxi", "dgx"]),
    ("陇南市", "Longnan", "甘肃省", "中国", "CN", 33.3953, 104.9200, "Asia/Shanghai", 2400000, 50, ["longnan", "lnn"]),
    ("临夏市(临夏州)", "Linxia", "甘肃省临夏回族自治州", "中国", "CN", 35.6015, 103.2106, "Asia/Shanghai", 250000, 30, ["linxia", "lxi"]),
    ("合作市(甘南州)", "Hezuo", "甘肃省甘南藏族自治州", "中国", "CN", 34.9877, 102.9100, "Asia/Shanghai", 80000, 50, ["gannan", "hezuo", "gnz"]),
    # 青海省（1 地级市 + 5 州驻地）
    ("海东市", "Haidong", "青海省", "中国", "CN", 36.5001, 102.4017, "Asia/Shanghai", 1360000, 35, ["haidong", "hdo"]),
    ("德令哈市(海西州)", "Delingha", "青海省海西蒙古族藏族自治州", "中国", "CN", 37.3696, 97.3426, "Asia/Shanghai", 80000, 60, ["haixi", "delingha", "hlh"]),
    ("同仁市(黄南州)", "Tongren", "青海省黄南藏族自治州", "中国", "CN", 35.5143, 102.0200, "Asia/Shanghai", 90000, 40, ["qinghai tongren", "tongren-qh", "huangnan"]),
    ("共和县(海南州)", "Gonghe", "青海省海南藏族自治州", "中国", "CN", 36.2629, 100.0200, "Asia/Shanghai", 160000, 60, ["gonghe", "qinghai hainan", "qnz"]),
    ("玛沁县(果洛州)", "Madoi", "青海省果洛藏族自治州", "中国", "CN", 34.4778, 100.2400, "Asia/Shanghai", 50000, 80, ["guoluo", "madoi", "glz"]),
    ("玉树市(玉树州)", "Yushu", "青海省玉树藏族自治州", "中国", "CN", 33.0011, 96.9720, "Asia/Shanghai", 100000, 80, ["yushu", "ys"]),
    ("海晏县(海北州)", "Haiyan", "青海省海北藏族自治州", "中国", "CN", 36.9770, 100.8300, "Asia/Shanghai", 30000, 40, ["haibei", "haiyan", "hbz"]),
    # 宁夏回族自治区（1）
    ("固原市", "Guyuan", "宁夏回族自治区", "中国", "CN", 35.9978, 106.2800, "Asia/Shanghai", 1140000, 35, ["guyuan", "gya"]),
    # 新疆维吾尔自治区（6 地级/州驻地 + 3 兵团直辖市级；全部用 UTC+6 口径时区）
    ("昌吉市", "Changji", "新疆维吾尔自治区昌吉回族自治州", "中国", "CN", 44.0138, 87.3100, "Asia/Urumqi", 470000, 30, ["changji", "cji"]),
    ("博乐市(博州)", "Bortala", "新疆维吾尔自治区博尔塔拉蒙古自治州", "中国", "CN", 44.9080, 82.0670, "Asia/Urumqi", 100000, 40, ["boertala", "bortala", "bol"]),
    ("阿图什市(克州)", "Artux", "新疆维吾尔自治区克孜勒苏柯尔克孜自治州", "中国", "CN", 39.7210, 76.1710, "Asia/Kashgar", 180000, 40, ["kezilesu", "artux", "atz"]),
    ("和田市", "Hotan", "新疆维吾尔自治区和田地区", "中国", "CN", 37.0890, 79.9230, "Asia/Kashgar", 330000, 40, ["hetian", "hotan", "htn"]),
    ("塔城市", "Tacheng", "新疆维吾尔自治区塔城地区", "中国", "CN", 46.7220, 82.9800, "Asia/Urumqi", 150000, 45, ["tacheng", "tcg"]),
    ("阿勒泰市", "Altay", "新疆维吾尔自治区阿勒泰地区", "中国", "CN", 47.7180, 88.1400, "Asia/Urumqi", 140000, 50, ["aletai", "altay", "alt"]),
    ("阿拉尔市", "Aral", "新疆维吾尔自治区(兵团第一师)", "中国", "CN", 40.5500, 81.2600, "Asia/Urumqi", 280000, 30, ["aral", "alaer"]),
    ("图木舒克市", "Tumshuk", "新疆维吾尔自治区(兵团第三师)", "中国", "CN", 41.9720, 79.1870, "Asia/Kashgar", 240000, 30, ["tumushuke", "tmsk"]),
    ("五家渠市", "Wujiaqu", "新疆维吾尔自治区(兵团第六师)", "中国", "CN", 44.1680, 87.9860, "Asia/Urumqi", 140000, 25, ["wujiaqu", "wjq"]),
]

TW_HK_MO = [
    ("台北市", "Taipei", "中国台湾", "中国", "TW", 25.0330, 121.5654, "Asia/Taipei", 2600000, 15, ["台北", "taibei", "tb"]),
    ("高雄市", "Kaohsiung", "中国台湾", "中国", "TW", 22.6273, 120.3014, "Asia/Taipei", 2770000, 20, ["高雄", "kaohsiung", "kh"]),
    ("台中市", "Taichung", "中国台湾", "中国", "TW", 24.1469, 120.6839, "Asia/Taipei", 2860000, 20, ["台中", "taichung", "tc"]),
    ("台南市", "Tainan", "中国台湾", "中国", "TW", 22.9993, 120.2170, "Asia/Taipei", 1880000, 25, ["台南", "tainan", "tn"]),
    ("新北市", "New Taipei", "中国台湾", "中国", "TW", 25.0120, 121.4680, "Asia/Taipei", 3900000, 25, ["新北", "new taipei", "xb"]),
    ("桃园市", "Taoyuan", "中国台湾", "中国", "TW", 24.9936, 121.3010, "Asia/Taipei", 2260000, 20, ["桃园", "taoyuan", "to"]),
    ("基隆市", "Keelung", "中国台湾", "中国", "TW", 25.1290, 121.7420, "Asia/Taipei", 370000, 15, ["基隆", "keelung", "ji"]),
    ("新竹市", "Hsinchu", "中国台湾", "中国", "TW", 24.8060, 120.9680, "Asia/Taipei", 450000, 15, ["新竹", "hsinchu", "xo"]),
    ("嘉义市", "Chiayi", "中国台湾", "中国", "TW", 23.4800, 120.4450, "Asia/Taipei", 270000, 15, ["嘉义", "chiayi", "ja"]),
    ("苗栗市", "Miaoli", "中国台湾", "中国", "TW", 24.5590, 120.8260, "Asia/Taipei", 160000, 20, ["苗栗", "miaoli", "mi"]),
    ("彰化市", "Changhua", "中国台湾", "中国", "TW", 24.0720, 120.5450, "Asia/Taipei", 230000, 20, ["彰化", "changhua", "oha"]),
    ("南投市", "Nantou", "中国台湾", "中国", "TW", 23.9130, 120.6910, "Asia/Taipei", 160000, 25, ["南投", "nantou", "no"]),
    ("斗六市", "Douliu", "中国台湾", "中国", "TW", 23.7050, 120.5430, "Asia/Taipei", 260000, 25, ["斗六", "云林", "douliu", "yo"]),
    ("屏东市", "Pingtung", "中国台湾", "中国", "TW", 22.6750, 120.4900, "Asia/Taipei", 260000, 25, ["屏东", "pingtung", "po"]),
    ("宜兰市", "Yilan", "中国台湾", "中国", "TW", 24.7550, 121.7540, "Asia/Taipei", 190000, 25, ["宜兰", "yilan", "yi"]),
    ("台东市", "Taitung", "中国台湾", "中国", "TW", 22.7560, 121.1440, "Asia/Taipei", 100000, 25, ["台东", "taitung", "tdo"]),
    ("花莲市", "Hualien", "中国台湾", "中国", "TW", 23.9800, 121.6050, "Asia/Taipei", 100000, 25, ["花莲", "hualien", "ho"]),
    ("马公市", "Makung", "中国台湾澎湖", "中国", "TW", 23.5650, 119.5680, "Asia/Taipei", 60000, 15, ["马公", "澎湖", "makung", "ph"]),
    ("香港", "Hong Kong", "中国香港", "中国", "HK", 22.3193, 114.1694, "Asia/Hong_Kong", 7480000, 20, ["港", "hongkong", "xianggang", "xg"]),
    ("澳门", "Macau", "中国澳门", "中国", "MO", 22.1987, 113.5439, "Asia/Macau", 680000, 5, ["澳", "macao", "aomen", "am"]),
]

# (中文, 英文, 上级行政区/国名, country_zh, cc, lat, lon, tz, 人口约数, 半径, 额外别名)
WORLD_CAP = [
    ("东京", "Tokyo", "日本", "日本", "JP", 35.6762, 139.6503, "Asia/Tokyo", 13960000, 30, ["dongjing", "dj"]),
    ("首尔", "Seoul", "韩国", "韩国", "KR", 37.5665, 126.9780, "Asia/Seoul", 9510000, 20, ["shouer", "so", "汉城"]),
    ("平壤", "Pyongyang", "朝鲜", "朝鲜", "KP", 39.0392, 125.7625, "Asia/Pyongyang", 3250000, 20, ["pingrang", "pl"]),
    ("乌兰巴托", "Ulaanbaatar", "蒙古", "蒙古", "MN", 47.8864, 106.9057, "Asia/Ulaanbaatar", 1600000, 25, ["wulanbato", "wlbt"]),
    ("新德里", "New Delhi", "印度", "印度", "IN", 28.6139, 77.2090, "Asia/Kolkata", 32900000, 25, ["xindeli", "xdl"]),
    ("伊斯兰堡", "Islamabad", "巴基斯坦", "巴基斯坦", "PK", 33.6844, 73.0479, "Asia/Karachi", 1100000, 20, ["yslbb"]),
    ("达卡", "Dhaka", "孟加拉国", "孟加拉国", "BD", 23.8103, 90.4125, "Asia/Dhaka", 22480000, 20, ["daka", "dk"]),
    ("加德满都", "Kathmandu", "尼泊尔", "尼泊尔", "NP", 27.7172, 85.3240, "Asia/Kathmandu", 1440000, 15, ["jdmd"]),
    ("廷布", "Thimphu", "不丹", "不丹", "BT", 27.4712, 89.6333, "Asia/Thimphu", 140000, 15, []),
    ("内比都", "Naypyidaw", "缅甸", "缅甸", "MM", 19.7633, 96.0667, "Asia/Yangon", 1160000, 25, ["nbd"]),
    ("曼谷", "Bangkok", "泰国", "泰国", "TH", 13.7563, 100.5018, "Asia/Bangkok", 10540000, 25, ["manguo", "mg"]),
    ("河内", "Hanoi", "越南", "越南", "VN", 21.0278, 105.8342, "Asia/Ho_Chi_Minh", 8300000, 20, ["henei", "hn"]),
    ("万象", "Vientiane", "老挝", "老挝", "LA", 17.9757, 102.6331, "Asia/Bangkok", 950000, 15, ["永珍", "wanxiang", "wx"]),
    ("金边", "Phnom Penh", "柬埔寨", "柬埔寨", "KH", 11.5564, 104.9282, "Asia/Phnom_Penh", 2200000, 15, ["jinbian", "jb"]),
    ("吉隆坡", "Kuala Lumpur", "马来西亚", "马来西亚", "MY", 3.1390, 101.6869, "Asia/Kuala_Lumpur", 1980000, 20, ["jlp"]),
    ("新加坡", "Singapore", "新加坡", "新加坡", "SG", 1.3521, 103.8198, "Asia/Singapore", 5850000, 15, ["xjp", "狮城"]),
    ("雅加达", "Jakarta", "印度尼西亚", "印度尼西亚", "ID", -6.2088, 106.8456, "Asia/Jakarta", 10560000, 25, ["yjd"]),
    ("马尼拉", "Manila", "菲律宾", "菲律宾", "PH", 14.5995, 120.9842, "Asia/Manila", 1850000, 20, ["mnl"]),
    ("斯里巴加湾市", "Bandar Seri Begawan", "文莱", "文莱", "BN", 4.9031, 114.9400, "Asia/Brunei", 100000, 15, ["文莱市"]),
    ("帝力", "Dili", "东帝汶", "东帝汶", "TL", -8.5586, 125.5736, "Asia/Dili", 280000, 15, []),
    ("莫斯科", "Moscow", "俄罗斯", "俄罗斯", "RU", 55.7558, 37.6173, "Europe/Moscow", 12600000, 35, ["mosike", "msk"]),
    ("基辅", "Kyiv", "乌克兰", "乌克兰", "UA", 50.4501, 30.5234, "Europe/Kyiv", 2950000, 25, ["jifu", "jf"]),
    ("明斯克", "Minsk", "白俄罗斯", "白俄罗斯", "BY", 53.9006, 27.5590, "Europe/Minsk", 2000000, 25, []),
    ("华沙", "Warsaw", "波兰", "波兰", "PL", 52.2297, 21.0122, "Europe/Warsaw", 1790000, 25, ["huasha", "hs"]),
    ("柏林", "Berlin", "德国", "德国", "DE", 52.5200, 13.4050, "Europe/Berlin", 3600000, 30, ["bolin", "bl"]),
    ("伯尔尼", "Bern", "瑞士", "瑞士", "CH", 46.9480, 7.4474, "Europe/Zurich", 140000, 15, []),
    ("维也纳", "Vienna", "奥地利", "奥地利", "AT", 48.2082, 16.3738, "Europe/Vienna", 1900000, 20, []),
    ("巴黎", "Paris", "法国", "法国", "FR", 48.8566, 2.3522, "Europe/Paris", 2100000, 20, ["bali"]),
    ("伦敦", "London", "英国", "英国", "GB", 51.5074, -0.1278, "Europe/London", 8980000, 30, ["lundun", "ld"]),
    ("都柏林", "Dublin", "爱尔兰", "爱尔兰", "IE", 53.3498, -6.2603, "Europe/Dublin", 590000, 20, ["dbl"]),
    ("雷克雅未克", "Reykjavik", "冰岛", "冰岛", "IS", 64.1466, -21.9426, "Atlantic/Reykjavik", 130000, 15, ["lkywk"]),
    ("里斯本", "Lisbon", "葡萄牙", "葡萄牙", "PT", 38.7223, -9.1393, "Europe/Lisbon", 545000, 20, ["lsb"]),
    ("马德里", "Madrid", "西班牙", "西班牙", "ES", 40.4168, -3.7038, "Europe/Madrid", 3220000, 25, ["mdl"]),
    ("罗马", "Rome", "意大利", "意大利", "IT", 41.9028, 12.4964, "Europe/Rome", 2870000, 25, ["luoma", "lm"]),
    ("雅典", "Athens", "希腊", "希腊", "GR", 37.9838, 23.7275, "Europe/Athens", 3150000, 20, ["yadian", "yd"]),
    ("索非亚", "Sofia", "保加利亚", "保加利亚", "BG", 42.6977, 23.3219, "Europe/Sofia", 1240000, 20, []),
    ("布加勒斯特", "Bucharest", "罗马尼亚", "罗马尼亚", "RO", 44.4268, 26.1025, "Europe/Bucharest", 1880000, 20, ["bjlst"]),
    ("贝尔格莱德", "Belgrade", "塞尔维亚", "塞尔维亚", "RS", 44.7866, 20.4489, "Europe/Belgrade", 1400000, 20, ["begld"]),
    ("萨拉热窝", "Sarajevo", "波黑", "波黑", "BA", 43.8563, 18.4131, "Europe/Sarajevo", 370000, 15, ["lhrw"]),
    ("卢布尔雅那", "Ljubljana", "斯洛文尼亚", "斯洛文尼亚", "SI", 46.0569, 14.5058, "Europe/Ljubljana", 290000, 15, ["lblon"]),
    ("萨格勒布", "Zagreb", "克罗地亚", "克罗地亚", "HR", 45.8150, 15.9819, "Europe/Zagreb", 770000, 15, []),
    ("布拉格", "Prague", "捷克", "捷克", "CZ", 50.0755, 14.4378, "Europe/Prague", 1330000, 20, ["bulage", "blg"]),
    ("布达佩斯", "Budapest", "匈牙利", "匈牙利", "HU", 47.4979, 19.0402, "Europe/Budapest", 1750000, 20, ["bdps"]),
    ("维尔纽斯", "Vilnius", "立陶宛", "立陶宛", "LT", 54.6872, 25.2797, "Europe/Vilnius", 580000, 15, []),
    ("里加", "Riga", "拉脱维亚", "拉脱维亚", "LV", 56.9496, 24.1052, "Europe/Riga", 605000, 15, []),
    ("塔林", "Tallinn", "爱沙尼亚", "爱沙尼亚", "EE", 59.4370, 24.7536, "Europe/Tallinn", 430000, 15, []),
    ("奥斯陆", "Oslo", "挪威", "挪威", "NO", 59.9139, 10.7522, "Europe/Oslo", 690000, 20, []),
    ("斯德哥尔摩", "Stockholm", "瑞典", "瑞典", "SE", 59.3293, 18.0686, "Europe/Stockholm", 980000, 20, ["sdgemm"]),
    ("哥本哈根", "Copenhagen", "丹麦", "丹麦", "DK", 55.6761, 12.5683, "Europe/Copenhagen", 790000, 20, ["gbhg"]),
    ("赫尔辛基", "Helsinki", "芬兰", "芬兰", "FI", 60.1699, 24.9384, "Europe/Helsinki", 650000, 20, ["hexj"]),
    ("海牙", "The Hague", "荷兰", "荷兰", "NL", 52.0705, 4.3007, "Europe/Amsterdam", 545000, 15, ["hyya"]),
    ("布鲁塞尔", "Brussels", "比利时", "比利时", "BE", 50.8503, 4.3517, "Europe/Brussels", 1200000, 15, ["blsl"]),
    ("安卡拉", "Ankara", "土耳其", "土耳其", "TR", 39.9334, 32.8597, "Europe/Istanbul", 5700000, 25, []),
    ("第比利斯", "Tbilisi", "格鲁吉亚", "格鲁吉亚", "GE", 41.7151, 44.8271, "Asia/Tbilisi", 1110000, 15, []),
    ("埃里温", "Yerevan", "亚美尼亚", "亚美尼亚", "AM", 40.1792, 44.4991, "Asia/Yerevan", 1090000, 15, []),
    ("巴库", "Baku", "阿塞拜疆", "阿塞拜疆", "AZ", 40.4093, 49.8671, "Asia/Baku", 2300000, 20, []),
    ("阿斯塔纳", "Astana", "哈萨克斯坦", "哈萨克斯坦", "KZ", 51.1694, 71.4491, "Asia/Almaty", 1350000, 20, []),
    ("塔什干", "Tashkent", "乌兹别克斯坦", "乌兹别克斯坦", "UZ", 41.2995, 69.2401, "Asia/Tashkent", 2600000, 20, []),
    ("德黑兰", "Tehran", "伊朗", "伊朗", "IR", 35.6892, 51.3890, "Asia/Tehran", 9140000, 25, ["dhl"]),
    ("巴格达", "Baghdad", "伊拉克", "伊拉克", "IQ", 33.3152, 44.3661, "Asia/Baghdad", 8140000, 25, []),
    ("利雅得", "Riyadh", "沙特阿拉伯", "沙特阿拉伯", "SA", 24.7136, 46.6753, "Asia/Riyadh", 7000000, 25, ["lyd"]),
    ("阿布扎比", "Abu Dhabi", "阿联酋", "阿联酋", "AE", 24.4539, 54.3773, "Asia/Dubai", 1550000, 20, ["abzb"]),
    ("多哈", "Doha", "卡塔尔", "卡塔尔", "QA", 25.2854, 51.5310, "Asia/Qatar", 2400000, 15, []),
    ("马斯喀特", "Muscat", "阿曼", "阿曼", "OM", 23.5880, 58.3820, "Asia/Muscat", 1500000, 20, []),
    ("开罗", "Cairo", "埃及", "埃及", "EG", 30.0444, 31.2357, "Africa/Cairo", 20900000, 30, ["kailuo", "kl"]),
    ("阿尔及尔", "Algiers", "阿尔及利亚", "阿尔及利亚", "DZ", 36.7538, 3.0588, "Africa/Algiers", 3800000, 20, []),
    ("突尼斯城", "Tunis", "突尼斯", "突尼斯", "TN", 36.8065, 10.1815, "Africa/Tunis", 2700000, 20, []),
    ("的黎波里", "Tripoli", "利比亚", "利比亚", "LY", 32.8872, 13.1913, "Africa/Tripoli", 1200000, 20, []),
    ("拉巴特", "Rabat", "摩洛哥", "摩洛哥", "MA", 34.0181, -6.8416, "Africa/Casablanca", 580000, 15, []),
    ("喀土穆", "Khartoum", "苏丹", "苏丹", "SD", 15.5007, 32.5599, "Africa/Khartoum", 6200000, 20, []),
    ("亚的斯亚贝巴", "Addis Ababa", "埃塞俄比亚", "埃塞俄比亚", "ET", 9.0222, 38.7468, "Africa/Addis_Ababa", 5000000, 20, ["adsyb"]),
    ("内罗毕", "Nairobi", "肯尼亚", "肯尼亚", "KE", -1.2864, 36.8172, "Africa/Nairobi", 4400000, 25, ["nlb"]),
    ("达累斯萨拉姆", "Dar es Salaam", "坦桑尼亚", "坦桑尼亚", "TZ", -6.7924, 39.2083, "Africa/Dar_es_Salaam", 7100000, 25, ["dlssl"]),
    ("金沙萨", "Kinshasa", "刚果（金）", "刚果民主共和国", "CD", -4.4419, 15.2663, "Africa/Kinshasa", 15600000, 30, []),
    ("卢萨卡", "Lusaka", "赞比亚", "赞比亚", "ZM", -15.3875, 28.3228, "Africa/Lusaka", 3400000, 25, []),
    ("哈拉雷", "Harare", "津巴布韦", "津巴布韦", "ZW", -17.8292, 31.0522, "Africa/Harare", 2100000, 20, []),
    ("马普托", "Maputo", "莫桑比克", "莫桑比克", "MZ", -25.9692, 32.5731, "Africa/Maputo", 1100000, 20, []),
    ("安塔那那利佛", "Antananarivo", "马达加斯加", "马达加斯加", "MG", -18.8792, 47.5079, "Indian/Antananarivo", 2600000, 20, []),
    ("温得和克", "Windhoek", "纳米比亚", "纳米比亚", "NA", -22.5609, 17.0658, "Africa/Windhoek", 440000, 20, []),
    ("比勒陀利亚", "Pretoria", "南非", "南非", "ZA", -25.7479, 28.2293, "Africa/Johannesburg", 2900000, 25, ["bltll", "行政首都"]),
    ("华盛顿", "Washington", "美国", "美国", "US", 38.9072, -77.0369, "America/New_York", 690000, 20, ["wsd", "dc"]),
    ("渥太华", "Ottawa", "加拿大", "加拿大", "CA", 45.4215, -75.6972, "America/Toronto", 1020000, 25, ["wth"]),
    ("墨西哥城", "Mexico City", "墨西哥", "墨西哥", "MX", 19.4326, -99.1332, "America/Mexico_City", 9200000, 30, ["mxgc"]),
    ("巴西利亚", "Brasilia", "巴西", "巴西", "BR", -15.8267, -47.9210, "America/Sao_Paulo", 3000000, 25, []),
    ("布宜诺斯艾利斯", "Buenos Aires", "阿根廷", "阿根廷", "AR", -34.6037, -58.3816, "America/Argentina/Buenos_Aires", 3100000, 25, []),
    ("圣地亚哥", "Santiago", "智利", "智利", "CL", -33.4489, -70.6693, "America/Santiago", 6600000, 30, ["sdyg"]),
    ("利马", "Lima", "秘鲁", "秘鲁", "PE", -12.0464, -77.0428, "America/Lima", 10700000, 25, []),
    ("波哥大", "Bogota", "哥伦比亚", "哥伦比亚", "CO", 4.7110, -74.0721, "America/Bogota", 7900000, 25, []),
    ("基多", "Quito", "厄瓜多尔", "厄瓜多尔", "EC", -0.1807, -78.4678, "America/Guayaquil", 2000000, 20, []),
    ("加拉加斯", "Caracas", "委内瑞拉", "委内瑞拉", "VE", 10.4806, -66.9036, "America/Caracas", 2900000, 20, []),
    ("哈瓦那", "Havana", "古巴", "古巴", "CU", 23.1136, -82.3666, "America/Havana", 2100000, 20, ["hawn"]),
    ("巴拿马城", "Panama City", "巴拿马", "巴拿马", "PA", 8.9824, -79.5199, "America/Panama", 1900000, 20, []),
    ("亚松森", "Asuncion", "巴拉圭", "巴拉圭", "PY", -25.2637, -57.5759, "America/Asuncion", 520000, 15, []),
    ("蒙得维的亚", "Montevideo", "乌拉圭", "乌拉圭", "UY", -34.8836, -56.1662, "America/Montevideo", 1320000, 20, []),
    ("堪培拉", "Canberra", "澳大利亚", "澳大利亚", "AU", -35.2809, 149.1300, "Australia/Sydney", 460000, 25, ["kpl"]),
    ("惠灵顿", "Wellington", "新西兰", "新西兰", "NZ", -41.2866, 174.7756, "Pacific/Auckland", 215000, 20, ["hld", "威灵顿"]),
    ("苏瓦", "Suva", "斐济", "斐济", "FJ", -18.1248, 178.4500, "Pacific/Fiji", 94000, 15, []),
    ("莫尔兹比港", "Port Moresby", "巴布亚新几内亚", "巴布亚新几内亚", "PG", -9.4438, 147.1803, "Pacific/Port_Moresby", 380000, 20, []),
    ("阿皮亚", "Apia", "萨摩亚", "萨摩亚", "WS", -13.8333, -171.7667, "Pacific/Apia", 37000, 10, []),
    ("南塔拉瓦", "South Tarawa", "基里巴斯", "基里巴斯", "KI", 1.4518, 172.9760, "Pacific/Tarawa", 63000, 10, ["塔拉瓦"]),
]

WORLD_EXT = [
    ("纽约", "New York", "美国", "美国", "US", 40.7128, -74.0060, "America/New_York", 8340000, 20, ["nyc", "niuyue"]),
    ("洛杉矶", "Los Angeles", "美国", "美国", "US", 34.0522, -118.2437, "America/Los_Angeles", 3900000, 30, ["洛城", "lsj"]),
    ("芝加哥", "Chicago", "美国", "美国", "US", 41.8781, -87.6298, "America/Chicago", 2700000, 25, ["zhijiage", "zjg"]),
    ("旧金山", "San Francisco", "美国", "美国", "US", 37.7749, -122.4194, "America/Los_Angeles", 875000, 15, ["三藩市", "jjs"]),
    ("西雅图", "Seattle", "美国", "美国", "US", 47.6062, -122.3321, "America/Los_Angeles", 750000, 20, []),
    ("波士顿", "Boston", "美国", "美国", "US", 42.3601, -71.0589, "America/New_York", 690000, 15, []),
    ("休斯敦", "Houston", "美国", "美国", "US", 29.7604, -95.3698, "America/Chicago", 2300000, 25, ["休斯顿", "xsd"]),
    ("海参崴", "Vladivostok", "俄罗斯", "俄罗斯", "RU", 43.1155, 131.8855, "Asia/Vladivostok", 600000, 20, ["符拉迪沃斯托克", "hsw"]),
    ("安克雷奇", "Anchorage", "美国", "美国", "US", 61.2181, -149.9003, "America/Anchorage", 290000, 25, []),
    ("檀香山", "Honolulu", "美国", "美国", "US", 21.3069, -157.8583, "Pacific/Honolulu", 350000, 15, ["火奴鲁鲁", "夏威夷", "txs"]),
    ("多伦多", "Toronto", "加拿大", "加拿大", "CA", 43.6532, -79.3832, "America/Toronto", 2930000, 25, ["dld"]),
    ("蒙特利尔", "Montreal", "加拿大", "加拿大", "CA", 45.5017, -73.5673, "America/Toronto", 1780000, 25, []),
    ("温哥华", "Vancouver", "加拿大", "加拿大", "CA", 49.2827, -123.1207, "America/Vancouver", 675000, 20, ["wgh"]),
    ("卡尔加里", "Calgary", "加拿大", "加拿大", "CA", 51.0447, -114.0719, "America/Edmonton", 1310000, 25, []),
    ("悉尼", "Sydney", "澳大利亚", "澳大利亚", "AU", -33.8688, 151.2093, "Australia/Sydney", 5310000, 30, ["xini", "xn"]),
    ("墨尔本", "Melbourne", "澳大利亚", "澳大利亚", "AU", -37.8136, 144.9631, "Australia/Melbourne", 5080000, 30, ["meb"]),
    ("布里斯班", "Brisbane", "澳大利亚", "澳大利亚", "AU", -27.4698, 153.0251, "Australia/Brisbane", 2560000, 30, []),
    ("珀斯", "Perth", "澳大利亚", "澳大利亚", "AU", -31.9505, 115.8605, "Australia/Perth", 2060000, 25, ["ps"]),
    ("大阪", "Osaka", "日本", "日本", "JP", 34.6937, 135.5023, "Asia/Tokyo", 2690000, 25, ["daban", "db"]),
    ("京都", "Kyoto", "日本", "日本", "JP", 35.0116, 135.7681, "Asia/Tokyo", 1460000, 20, []),
    ("札幌", "Sapporo", "日本", "日本", "JP", 43.0618, 141.3545, "Asia/Tokyo", 1970000, 25, ["zahuang", "zh"]),
    ("福冈", "Fukuoka", "日本", "日本", "JP", 33.5902, 130.4017, "Asia/Tokyo", 1590000, 20, ["fugang", "fg"]),
    ("釜山", "Busan", "韩国", "韩国", "KR", 35.1796, 129.0756, "Asia/Seoul", 3400000, 20, ["fushan"]),
    ("圣保罗", "Sao Paulo", "巴西", "巴西", "BR", -23.5558, -46.6396, "America/Sao_Paulo", 12300000, 30, ["sbl"]),
    ("迪拜", "Dubai", "阿联酋", "阿联酋", "AE", 25.2048, 55.2708, "Asia/Dubai", 3500000, 25, ["dibai"]),
    ("伊斯坦布尔", "Istanbul", "土耳其", "土耳其", "TR", 41.0082, 28.9784, "Europe/Istanbul", 15500000, 35, ["君士坦丁堡", "yselbur"]),
]


def normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKC", text or "").casefold()
    return "".join(ch for ch in folded if not ch.isspace())


def slugify(text: str) -> str:
    folded = normalize(text)
    return "".join(ch for ch in folded if ch.isascii() and (ch.isalnum() or ch == "-"))


def build():
    places = []
    seen = set()

    def add(group, rows):
        for row in rows:
            zh, en, admin1, country_zh, cc, lat, lon, tz, pop, radius, extra = row
            aliases = []
            for alias in [zh, zh.rstrip("市"), en, country_zh, *(extra or [])]:
                alias = alias.strip() if isinstance(alias, str) else alias
                if alias and alias not in aliases and alias != zh:
                    aliases.append(alias)
            # id 后缀取英文名 slug；同名城市（如江苏/浙江台州）用可区分的 ASCII 别名兜底
            slug_candidates = [slugify(en), *(slugify(a) for a in aliases), slugify(f"{en} {cc}")]
            place_id = None
            for slug in [c for c in slug_candidates if c]:
                candidate = f"curated:{cc.lower()}-{slug}"
                if candidate not in seen:
                    place_id = candidate
                    break
            if place_id is None:
                raise SystemExit(f"无法为 {zh}（{en}）生成唯一 place_id")
            seen.add(place_id)
            places.append({
                "id": place_id,
                "name_zh": zh,
                "name_en": en,
                "aliases": aliases,
                "admin1": admin1,
                "country_zh": country_zh,
                "country_code": cc,
                "lat": round(lat, 4),
                "lon": round(lon, 4),
                "approx_radius_km": radius,
                "tz": tz,
                "population": pop,
                "level": "city",
                "group": group,
                "source": "curated",
                "revision": REVISION,
            })

    add("cn_core", CN_CORE)
    add("cn_extra", CN_EXTRA)
    add("cn_more", CN_MORE)
    add("tw_hk_mo", TW_HK_MO)
    add("world_cap", WORLD_CAP)
    add("world_ext", WORLD_EXT)

    groups = {}
    for place in places:
        groups[place["group"]] = groups.get(place["group"], 0) + 1
    print("group counts:", groups, "total:", len(places))
    for group, quota in QUOTA.items():
        if group == "total":
            continue
        actual = groups.get(group, 0)
        if actual != quota:
            raise SystemExit(f"分组 {group} 条数 {actual} 与配额 {quota} 不一致")
    if len(places) != QUOTA["total"]:
        raise SystemExit(f"总条数 {len(places)} 与配额 {QUOTA['total']} 不一致")
    return places, groups


def main():
    places, groups = build()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    body = json.dumps(places, ensure_ascii=False, indent=1) + "\n"
    (OUT_DIR / "curated.json").write_text(body, encoding="utf-8")
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    index = {
        "revision": REVISION,
        "generated_on": date.today().isoformat(),
        "shards": {
            "curated": {
                "file": "curated.json",
                "count": len(places),
                "sha256": digest,
                "groups": groups,
            }
        },
        "quota": QUOTA,
    }
    (OUT_DIR / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {OUT_DIR / 'curated.json'} ({len(places)} entries, sha256 {digest[:12]})")


if __name__ == "__main__":
    main()
