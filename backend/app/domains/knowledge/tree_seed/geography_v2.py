"""
地理知识树 V2 (新课标课程结构对齐)

课程模块结构 (2 必修 + 3 选必):
  GEOG-C1  必修一   (自然地理基础)
  GEOG-C2  必修二   (人文地理基础)
  GEOG-S1  选必一   (自然地理基础)
  GEOG-S2  选必二   (区域发展)
  GEOG-S3  选必三   (资源、环境与国家安全)

与 humanities.py (GEOG-PHYS / GEOG-HUMN / GEOG-REGN) 并行存在，
不产生 code 冲突。

编码体系:
  L2: GEOG-{C|S}{册}              e.g. GEOG-C1
  L3: GEOG-{C|S}{册}-CH{章}       e.g. GEOG-C1-CH1
  L4: GEOG-{C|S}{册}-CH{章}-{节}   e.g. GEOG-C1-CH1-01
"""

from __future__ import annotations

from app.domains.knowledge.tree_seed.types import KnowledgeTreeSeed

GEOGRAPHY_KNOWLEDGE_TREE_V2: list[KnowledgeTreeSeed] = [

    # ═══════════════════════════════════════════════════════════════════════════════
    #  Level 2: 课程模块 (5 册)
    # ═══════════════════════════════════════════════════════════════════════════════

    KnowledgeTreeSeed(
        code="GEOG-C1",
        name="必修一 · 自然地理基础",
        level=2,
        parent_code="GEOG",
        description="宇宙中的地球、地球上的大气、地球上的水、地貌、植被与土壤、自然灾害",
        keywords=["必修一", "自然地理", "大气", "水", "地貌", "土壤"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-C2",
        name="必修二 · 人文地理基础",
        level=2,
        parent_code="GEOG",
        description="人口、乡村和城镇、产业区位因素、交通运输布局与区域发展、环境与发展",
        keywords=["必修二", "人文地理", "人口", "城镇", "产业", "交通"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-S1",
        name="选必一 · 自然地理基础",
        level=2,
        parent_code="GEOG",
        description="地球运动、地表形态变化、大气运动、水的运动、自然环境整体性与差异性",
        keywords=["选必一", "地球运动", "大气运动", "水运动", "整体性", "差异性"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-S2",
        name="选必二 · 区域发展",
        level=2,
        parent_code="GEOG",
        description="区域与区域发展、不同类型区域的发展、区域协调",
        keywords=["选必二", "区域", "区域发展", "区域协调"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-S3",
        name="选必三 · 资源、环境与国家安全",
        level=2,
        parent_code="GEOG",
        description="资源安全与国家安全、环境安全与国家安全、生态安全与国家安全、全球变化与国家安全",
        keywords=["选必三", "资源安全", "环境安全", "生态安全", "国家安全"],
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  GEOG-C1: 必修一 · 自然地理基础
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第一章: 宇宙中的地球 ───────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="GEOG-C1-CH1",
        name="宇宙中的地球",
        level=3,
        parent_code="GEOG-C1",
        description="地球的宇宙环境、太阳对地球的影响、地球的历史、地球的圈层结构",
        keywords=["宇宙", "太阳", "地球历史", "圈层结构"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-C1-CH1-01",
        name="地球的宇宙环境",
        level=4,
        parent_code="GEOG-C1-CH1",
        description="天体与天体系统(地月系→太阳系→银河系→总星系)、地球在太阳系中的位置(宜居带)、地球存在生命的条件",
        keywords=["天体", "天体系统", "太阳系", "宜居带", "生命条件"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-C1-CH1-02",
        name="太阳对地球的影响",
        level=4,
        parent_code="GEOG-C1-CH1",
        description="太阳辐射(能量来源/影响气候与生物)、太阳活动(黑子/耀斑/太阳风)对地球的影响(磁暴/极光/电离层扰动)",
        keywords=["太阳辐射", "太阳活动", "黑子", "耀斑", "磁暴", "极光"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-C1-CH1-03",
        name="地球的历史",
        level=4,
        parent_code="GEOG-C1-CH1",
        description="地质年代(宙/代/纪)、地球的演化历程(前寒武纪/古生代/中生代/新生代)、地层与化石",
        keywords=["地质年代", "化石", "地层", "前寒武纪", "中生代", "新生代"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-C1-CH1-04",
        name="地球的圈层结构",
        level=4,
        parent_code="GEOG-C1-CH1",
        description="地球的内部圈层(地壳/地幔/地核/莫霍面/古登堡面)、地球的外部圈层(大气圈/水圈/生物圈/岩石圈)",
        keywords=["地壳", "地幔", "地核", "莫霍面", "古登堡面", "外部圈层"],
    ),

    # ── 第二章: 地球上的大气 ───────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="GEOG-C1-CH2",
        name="地球上的大气",
        level=3,
        parent_code="GEOG-C1",
        description="大气的组成与垂直分层、大气的受热过程与大气运动、气压带与风带、天气与气候",
        keywords=[
            "大气",
            "气压带",
            "风带",
            "天气",
            "气候",
            "冷锋",
            "厄尔尼诺",
            "反气旋",
            "台风",
            "地形",
            "天气系统",
            "季风",
            "寒潮",
            "拉尼娜",
            "暖锋",
            "梅雨",
            "气旋",
            "气温",
            "水文",
            "温室效应",
            "热力环流",
            "等温线",
            "自然",
            "锋面",
            "降水",
            "降雪",
        ]
    ),
    KnowledgeTreeSeed(
        code="GEOG-C1-CH2-01",
        name="大气的组成与垂直分层",
        level=4,
        parent_code="GEOG-C1-CH2",
        description="大气的组成(干洁空气/水汽/固体杂质)、大气的垂直分层(对流层/平流层/高层大气)及其特征",
        keywords=["大气组成", "对流层", "平流层", "高层大气", "气温递减"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-C1-CH2-02",
        name="大气的受热过程与大气运动",
        level=4,
        parent_code="GEOG-C1-CH2",
        description="大气的受热过程(太阳暖大地/大地暖大气/大气还大地)、热力环流(山谷风/海陆风/城市热岛)、大气的水平运动(风)",
        keywords=["大气受热", "热力环流", "山谷风", "海陆风", "城市热岛", "风"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-C1-CH2-03",
        name="气压带与风带",
        level=4,
        parent_code="GEOG-C1-CH2",
        description="三圈环流与全球气压带风带(赤道低压/副热带高压/副极地低压/极地高压)、气压带风带的季节移动、季风环流",
        keywords=["气压带", "风带", "三圈环流", "季风", "副热带高压", "信风"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-C1-CH2-04",
        name="天气与气候",
        level=4,
        parent_code="GEOG-C1-CH2",
        description="常见天气系统(冷锋/暖锋/准静止锋/气旋/反气旋)、气候的形成因素(纬度/海陆/地形/洋流)、世界主要气候类型",
        keywords=["冷锋", "暖锋", "气旋", "反气旋", "气候类型", "温带海洋", "地中海"],
    ),

    # ── 第三章: 地球上的水 ─────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="GEOG-C1-CH3",
        name="地球上的水",
        level=3,
        parent_code="GEOG-C1",
        description="水循环、海水的性质、海水的运动、水资源的合理利用",
        keywords=["水循环", "海水", "洋流", "水资源"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-C1-CH3-01",
        name="水循环",
        level=4,
        parent_code="GEOG-C1-CH3",
        description="水循环的类型(海陆间/陆地内/海上内循环)、水循环的环节(蒸发/水汽输送/降水/径流)、人类活动对水循环的影响",
        keywords=[
            "水循环",
            "海陆间循环",
            "蒸发",
            "降水",
            "径流",
            "下渗",
            "含沙量",
            "地下水",
            "水库",
            "水文",
            "汛期",
            "河流",
            "洋流",
            "流域",
            "湖泊",
            "结冰期",
        ]
    ),
    KnowledgeTreeSeed(
        code="GEOG-C1-CH3-02",
        name="海水的性质与运动",
        level=4,
        parent_code="GEOG-C1-CH3",
        description="海水的温度(纬度/深度/洋流影响)与盐度(蒸发/降水/径流影响)、洋流(风海流/密度流/补偿流)的分布与影响",
        keywords=["海水温度", "盐度", "洋流", "风海流", "暖流", "寒流", "渔场"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-C1-CH3-03",
        name="水资源的合理利用",
        level=4,
        parent_code="GEOG-C1-CH3",
        description="水资源的分布(不均衡)、水资源短缺的原因与对策、跨流域调水(南水北调)",
        keywords=["水资源", "水资源短缺", "跨流域调水", "南水北调", "节水"],
    ),

    # ── 第四章: 地貌 ───────────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="GEOG-C1-CH4",
        name="地貌",
        level=3,
        parent_code="GEOG-C1",
        description="常见地貌类型(河流/风成/喀斯特/冰川/海岸)、地貌的观察",
        keywords=["地貌", "河流地貌", "喀斯特", "风成地貌", "冰川地貌"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-C1-CH4-01",
        name="常见地貌类型",
        level=4,
        parent_code="GEOG-C1-CH4",
        description="河流地貌(冲积扇/河漫滩/三角洲)、风成地貌(沙丘)、喀斯特地貌(溶洞/石林)、冰川地貌(U型谷/冰碛)、海岸地貌",
        keywords=["冲积扇", "三角洲", "沙丘", "喀斯特", "溶洞", "U型谷", "海岸地貌"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-C1-CH4-02",
        name="地貌的观察",
        level=4,
        parent_code="GEOG-C1-CH4",
        description="等高线地形图的判读(山顶/山谷/山脊/鞍部/陡崖)、地形剖面图、地貌对人类活动的影响",
        keywords=["等高线", "地形图", "山顶", "山谷", "山脊", "陡崖", "地形剖面"],
    ),

    # ── 第五章: 植被与土壤 ─────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="GEOG-C1-CH5",
        name="植被与土壤",
        level=3,
        parent_code="GEOG-C1",
        description="植被的类型与分布、土壤的形成与特征",
        keywords=["植被", "土壤", "自然带", "森林", "草原"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-C1-CH5-01",
        name="植被",
        level=4,
        parent_code="GEOG-C1-CH5",
        description="植被的概念与类型(森林/草原/荒漠)、世界主要植被类型的分布与特征、植被与环境的关系",
        keywords=["植被", "热带雨林", "温带落叶阔叶林", "草原", "荒漠", "针叶林"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-C1-CH5-02",
        name="土壤",
        level=4,
        parent_code="GEOG-C1-CH5",
        description="土壤的组成(矿物质/有机质/水分/空气)、土壤的形成因素(成土母质/气候/生物/地形/时间)、土壤剖面与土壤类型",
        keywords=["土壤", "有机质", "腐殖质", "成土母质", "土壤剖面", "红壤", "黑土"],
    ),

    # ── 第六章: 自然灾害 ───────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="GEOG-C1-CH6",
        name="自然灾害",
        level=3,
        parent_code="GEOG-C1",
        description="气象灾害、地质灾害、防灾减灾、地理信息技术在防灾中的应用",
        keywords=["自然灾害", "气象灾害", "地质灾害", "防灾减灾"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-C1-CH6-01",
        name="气象灾害与地质灾害",
        level=4,
        parent_code="GEOG-C1-CH6",
        description="气象灾害(台风/寒潮/暴雨/干旱/沙尘暴)、地质灾害(地震/火山/滑坡/泥石流)的成因与分布",
        keywords=["台风", "寒潮", "干旱", "地震", "火山", "滑坡", "泥石流"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-C1-CH6-02",
        name="防灾减灾与地理信息技术",
        level=4,
        parent_code="GEOG-C1-CH6",
        description="防灾减灾措施(监测/预警/防御)、地理信息技术(RS遥感/GPS定位/GIS地理信息系统)在防灾中的应用",
        keywords=[
            "防灾减灾",
            "遥感",
            "GPS",
            "GIS",
            "监测预警",
            "应急响应",
            "世界地理",
            "东南亚",
            "中东",
            "亚洲",
            "北美",
            "区域分析",
            "区域差异",
            "区域特征",
            "南极",
            "南美",
            "国家",
            "地理信息技术",
            "大洋洲",
            "大洲",
            "定位",
            "数字地球",
            "欧洲",
            "比较",
            "非洲",
        ]
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  GEOG-C2: 必修二 · 人文地理基础
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第一章: 人口 ───────────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="GEOG-C2-CH1",
        name="人口",
        level=3,
        parent_code="GEOG-C2",
        description="人口的分布、人口的迁移、人口的合理容量",
        keywords=[
            "人口",
            "人口分布",
            "人口迁移",
            "人口容量",
            "人口增长",
            "住宅区",
            "商业区",
            "城市",
            "城市功能分区",
            "城市化",
            "城市等级",
            "城镇化",
            "工业区",
        ]
    ),
    KnowledgeTreeSeed(
        code="GEOG-C2-CH1-01",
        name="人口的分布与迁移",
        level=4,
        parent_code="GEOG-C2-CH1",
        description="世界人口分布(沿海/平原/中低纬度密集)、影响人口分布的因素(自然/经济/社会)、人口迁移的类型与原因(推拉理论)",
        keywords=["人口分布", "人口密度", "人口迁移", "推拉理论", "胡焕庸线"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-C2-CH1-02",
        name="人口的合理容量",
        level=4,
        parent_code="GEOG-C2-CH1",
        description="人口增长模式(原始/传统/现代/低增长)、环境承载力与人口合理容量、人口问题(老龄化/人口过多)",
        keywords=["人口增长模式", "环境承载力", "人口合理容量", "老龄化", "人口红利"],
    ),

    # ── 第二章: 乡村和城镇 ─────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="GEOG-C2-CH2",
        name="乡村和城镇",
        level=3,
        parent_code="GEOG-C2",
        description="城镇和乡村的空间结构、城镇化、地域文化与城乡景观",
        keywords=["城镇", "乡村", "城镇化", "空间结构"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-C2-CH2-01",
        name="城镇和乡村的空间结构",
        level=4,
        parent_code="GEOG-C2-CH2",
        description="城市功能分区(商业区/住宅区/工业区)、城市空间结构模式(同心圆/扇形/多核心)、乡村空间结构",
        keywords=["功能分区", "商业区", "住宅区", "工业区", "同心圆", "地租"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-C2-CH2-02",
        name="城镇化与地域文化",
        level=4,
        parent_code="GEOG-C2-CH2",
        description="城镇化的标志与动力、世界城镇化进程(初期/中期/后期)、城镇化对地理环境的影响、地域文化对城乡景观的影响",
        keywords=["城镇化", "城镇化率", "逆城市化", "城市问题", "地域文化"],
    ),

    # ── 第三章: 产业区位因素 ───────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="GEOG-C2-CH3",
        name="产业区位因素",
        level=3,
        parent_code="GEOG-C2",
        description="农业的区位因素、工业的区位因素、服务业的区位因素",
        keywords=["区位因素", "农业", "工业", "服务业", "人口", "人文", "城市"]
    ),
    KnowledgeTreeSeed(
        code="GEOG-C2-CH3-01",
        name="农业的区位因素",
        level=4,
        parent_code="GEOG-C2-CH3",
        description="自然因素(气候/地形/土壤/水源)与社会经济因素(市场/交通/政策/劳动力)、农业地域类型(季风水田/商品谷物/大牧场/混合农业)",
        keywords=[
            "农业区位",
            "季风水田",
            "商品谷物",
            "大牧场放牧",
            "混合农业",
            "区位因素",
            "产业",
            "农业",
            "农业地域",
            "区位",
            "工业",
            "工业地域",
            "集聚",
        ]
    ),
    KnowledgeTreeSeed(
        code="GEOG-C2-CH3-02",
        name="工业的区位因素",
        level=4,
        parent_code="GEOG-C2-CH3",
        description="工业区位因素(原料/市场/交通/劳动力/技术/政策)、工业地域的形成(工业集聚/工业分散)、传统工业区与新工业区",
        keywords=["工业区位", "工业集聚", "工业分散", "传统工业", "新工业区", "硅谷"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-C2-CH3-03",
        name="服务业的区位因素",
        level=4,
        parent_code="GEOG-C2-CH3",
        description="商业性服务业(零售/金融/餐饮)的区位因素(市场/交通/集聚)、非商业性服务业(教育/医疗/行政)的区位因素",
        keywords=["服务业区位", "商业", "零售", "集聚", "服务范围"],
    ),

    # ── 第四章: 交通运输布局与区域发展 ─────────────────────────────────────────
    KnowledgeTreeSeed(
        code="GEOG-C2-CH4",
        name="交通运输布局与区域发展",
        level=3,
        parent_code="GEOG-C2",
        description="交通运输方式与布局、交通运输对区域发展的影响",
        keywords=["交通运输", "铁路", "公路", "港口", "航空", "交通", "区域发展", "商业网点", "物流", "聚落", "运输"]
    ),
    KnowledgeTreeSeed(
        code="GEOG-C2-CH4-01",
        name="交通运输方式与布局",
        level=4,
        parent_code="GEOG-C2-CH4",
        description="五种交通运输方式(铁路/公路/水运/航空/管道)的特点与选择、交通运输布局的区位因素(自然/经济/社会/技术)",
        keywords=["铁路", "公路", "水运", "航空", "管道", "交通运输布局"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-C2-CH4-02",
        name="交通运输对区域发展的影响",
        level=4,
        parent_code="GEOG-C2-CH4",
        description="交通运输对聚落发展的影响(城市沿交通线扩展)、对商业网点的影响、交通建设与区域经济发展",
        keywords=["聚落发展", "商业网点", "交通建设", "区域经济", "高铁"],
    ),

    # ── 第五章: 环境与发展 ─────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="GEOG-C2-CH5",
        name="环境与发展",
        level=3,
        parent_code="GEOG-C2",
        description="环境问题(生态破坏/环境污染)、可持续发展、中国国家发展战略",
        keywords=["环境问题", "可持续发展", "国家战略"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-C2-CH5-01",
        name="环境问题与可持续发展",
        level=4,
        parent_code="GEOG-C2-CH5",
        description="环境问题的表现(资源短缺/生态破坏/环境污染)、可持续发展的内涵(生态/经济/社会可持续)、可持续发展的原则(公平/持续/共同)",
        keywords=[
            "环境问题",
            "可持续发展",
            "生态可持续",
            "循环经济",
            "绿色经济",
            "人地关系",
            "森林",
            "水土流失",
            "湿地",
            "环境",
            "生态",
            "生物多样性",
            "荒漠化",
            "资源",
        ]
    ),
    KnowledgeTreeSeed(
        code="GEOG-C2-CH5-02",
        name="中国国家发展战略",
        level=4,
        parent_code="GEOG-C2-CH5",
        description="主体功能区(优化开发/重点开发/限制开发/禁止开发)、长江经济带发展、京津冀协同发展、一带一路",
        keywords=[
            "主体功能区",
            "长江经济带",
            "京津冀",
            "一带一路",
            "区域协调",
            "东北",
            "东部",
            "中国地理",
            "南水北调",
            "四大区域",
            "珠三角",
            "西气东输",
            "西电东送",
            "西部",
            "长三角",
        ]
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  GEOG-S1: 选必一 · 自然地理基础
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第一章: 地球的运动 ─────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="GEOG-S1-CH1",
        name="地球的运动",
        level=3,
        parent_code="GEOG-S1",
        description="地球的自转与公转、昼夜变化与四季五带、时间计算",
        keywords=["地球自转", "地球公转", "昼夜", "四季", "时区"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-S1-CH1-01",
        name="地球的自转",
        level=4,
        parent_code="GEOG-S1-CH1",
        description="自转的方向(自西向东)、周期(恒星日/太阳日)、速度(角速度/线速度)、地理意义(昼夜交替/地转偏向/时间差异)",
        keywords=["自转", "恒星日", "太阳日", "角速度", "线速度", "地转偏向力"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-S1-CH1-02",
        name="地球的公转",
        level=4,
        parent_code="GEOG-S1-CH1",
        description="公转的轨道(近日点/远日点)、速度(快慢变化)、黄赤交角(23°26')及其影响",
        keywords=["公转", "近日点", "远日点", "黄赤交角", "回归年"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-S1-CH1-03",
        name="昼夜变化与四季五带",
        level=4,
        parent_code="GEOG-S1-CH1",
        description="昼夜长短的变化规律、正午太阳高度角的变化、四季的划分(天文四季/气候四季)、五带的划分",
        keywords=[
            "昼夜长短",
            "正午太阳高度",
            "四季",
            "五带",
            "太阳直射点",
            "区时",
            "地图",
            "地球运动",
            "太阳高度角",
            "方向",
            "日照",
            "时区",
            "比例尺",
            "等高线",
            "经纬度",
            "经纬网",
        ]
    ),
    KnowledgeTreeSeed(
        code="GEOG-S1-CH1-04",
        name="时间计算",
        level=4,
        parent_code="GEOG-S1-CH1",
        description="地方时(经度不同时间不同)、时区与区时(24个时区/东加西减)、日界线(180°经线/日期变更)",
        keywords=["地方时", "时区", "区时", "日界线", "东加西减"],
    ),

    # ── 第二章: 地表形态的变化 ─────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="GEOG-S1-CH2",
        name="地表形态的变化",
        level=3,
        parent_code="GEOG-S1",
        description="内力作用(地壳运动/岩浆活动/变质作用)、外力作用(风化/侵蚀/搬运/堆积)、人类活动对地表形态的影响",
        keywords=["内力作用", "外力作用", "地壳运动", "板块构造"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-S1-CH2-01",
        name="内力作用与地表形态",
        level=4,
        parent_code="GEOG-S1-CH2",
        description="地壳运动(水平运动/垂直运动)、板块构造学说(六大板块/生长边界/消亡边界)、地质构造(褶皱/断层)",
        keywords=["地壳运动", "板块构造", "褶皱", "断层", "背斜", "向斜", "地垒", "地堑"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-S1-CH2-02",
        name="外力作用与地表形态",
        level=4,
        parent_code="GEOG-S1-CH2",
        description="风化作用(物理/化学/生物风化)、侵蚀作用(流水/风力/冰川/海浪侵蚀)、搬运与堆积作用、人类活动对地表形态的影响",
        keywords=[
            "风化",
            "侵蚀",
            "搬运",
            "堆积",
            "流水侵蚀",
            "风力堆积",
            "人类活动",
            "三角洲",
            "丹霞",
            "冰川",
            "冲积扇",
            "喀斯特",
            "地壳",
            "地幔",
            "地核",
            "地貌",
            "地质",
            "岩石圈",
            "断层",
            "板块",
            "沉积",
            "火山",
            "褶皱",
            "软流圈",
        ]
    ),

    # ── 第三章: 大气的运动 ─────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="GEOG-S1-CH3",
        name="大气的运动",
        level=3,
        parent_code="GEOG-S1",
        description="常见天气系统、气压带风带与气候、气候类型与自然带",
        keywords=["天气系统", "气压带", "风带", "气候类型", "自然带"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-S1-CH3-01",
        name="常见天气系统",
        level=4,
        parent_code="GEOG-S1-CH3",
        description="锋面系统(冷锋/暖锋/准静止锋)、气旋(低压)与反气旋(高压)、锋面气旋、天气系统的判读与预报",
        keywords=["冷锋", "暖锋", "准静止锋", "气旋", "反气旋", "锋面气旋"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-S1-CH3-02",
        name="气压带风带与气候",
        level=4,
        parent_code="GEOG-S1-CH3",
        description="气压带风带对气候的影响(热带雨林/热带沙漠/温带海洋)、季风环流(东亚季风/南亚季风)、气候类型的判读方法",
        keywords=["气压带", "风带", "季风", "气候判读", "气温曲线", "降水柱状图"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-S1-CH3-03",
        name="气候与自然带",
        level=4,
        parent_code="GEOG-S1-CH3",
        description="世界主要气候类型的分布与特征、气候与自然带的对应关系、非地带性气候的成因",
        keywords=["气候类型", "自然带", "热带雨林带", "温带落叶阔叶林带", "非地带性"],
    ),

    # ── 第四章: 水的运动 ───────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="GEOG-S1-CH4",
        name="水的运动",
        level=3,
        parent_code="GEOG-S1",
        description="陆地水体及其相互关系、洋流、海—气相互作用",
        keywords=["陆地水体", "洋流", "海气作用"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-S1-CH4-01",
        name="陆地水体及其相互关系",
        level=4,
        parent_code="GEOG-S1-CH4",
        description="河流的补给类型(雨水/冰雪融水/湖泊水/地下水)、河流的水文特征(流量/水位/含沙量/结冰期)与水系特征",
        keywords=["河流补给", "水文特征", "水系特征", "流量", "含沙量", "汛期"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-S1-CH4-02",
        name="洋流与海—气相互作用",
        level=4,
        parent_code="GEOG-S1-CH4",
        description="世界洋流的分布规律(以副热带为中心的环流/北印度洋季风洋流)、洋流对气候与渔场的影响、厄尔尼诺与拉尼娜",
        keywords=["洋流分布", "暖流", "寒流", "渔场", "厄尔尼诺", "拉尼娜", "海气作用"],
    ),

    # ── 第五章: 自然环境的整体性与差异性 ─────────────────────────────────────
    KnowledgeTreeSeed(
        code="GEOG-S1-CH5",
        name="自然环境的整体性与差异性",
        level=3,
        parent_code="GEOG-S1",
        description="自然环境的整体性(各要素相互联系)、自然环境的差异性(地带性/非地带性)",
        keywords=["整体性", "差异性", "地带性", "自然带", "土壤", "垂直地带", "山地垂直", "植被", "生物多样性", "纬度地带性", "经度地带性", "雪线"]
    ),
    KnowledgeTreeSeed(
        code="GEOG-S1-CH5-01",
        name="自然环境的整体性",
        level=4,
        parent_code="GEOG-S1-CH5",
        description="自然环境各要素的相互作用(气候/地貌/水文/土壤/植被)、整体性的表现(牵一发而动全身)、自然环境的生产/平衡功能",
        keywords=["整体性", "要素相互作用", "牵一发而动全身", "自然环境功能"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-S1-CH5-02",
        name="自然环境的差异性",
        level=4,
        parent_code="GEOG-S1-CH5",
        description="纬度地带性(热量)、经度地带性(水分)、垂直地带性(海拔)、非地带性因素(地形/洋流/海陆分布)",
        keywords=["纬度地带性", "经度地带性", "垂直地带性", "非地带性", "自然带", "雪线"],
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  GEOG-S2: 选必二 · 区域发展
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第一章: 区域与区域发展 ─────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="GEOG-S2-CH1",
        name="区域与区域发展",
        level=3,
        parent_code="GEOG-S2",
        description="区域的含义与特征、区域发展的自然与人文条件、区域发展的阶段",
        keywords=["区域", "区域特征", "区域发展", "世界", "中国", "可持续发展"]
    ),
    KnowledgeTreeSeed(
        code="GEOG-S2-CH1-01",
        name="区域的含义与特征",
        level=4,
        parent_code="GEOG-S2-CH1",
        description="区域的概念(具有一定区位特征的地理空间)、区域的特征(整体性/差异性/开放性)、区域的划分方法",
        keywords=["区域", "整体性", "差异性", "开放性", "区域划分"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-S2-CH1-02",
        name="区域发展的条件与阶段",
        level=4,
        parent_code="GEOG-S2-CH1",
        description="区域发展的自然条件(地理位置/气候/地形/资源)与人文条件(人口/交通/技术/政策)、区域发展的不同阶段",
        keywords=["区域条件", "发展阶段", "资源", "交通", "技术", "政策"],
    ),

    # ── 第二章: 区域发展 ───────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="GEOG-S2-CH2",
        name="区域发展",
        level=3,
        parent_code="GEOG-S2",
        description="生态脆弱区的发展(荒漠化/水土流失)、资源枯竭型城市的转型发展、产业结构升级",
        keywords=["生态脆弱区", "荒漠化", "水土流失", "资源枯竭", "产业升级"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-S2-CH2-01",
        name="生态脆弱区的发展",
        level=4,
        parent_code="GEOG-S2-CH2",
        description="荒漠化的成因(自然/人为)与防治(植被恢复/合理用水/工程措施)、水土流失的治理(黄土高原/小流域综合治理)",
        keywords=["荒漠化", "水土流失", "黄土高原", "小流域治理", "退耕还林"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-S2-CH2-02",
        name="资源枯竭型城市与产业结构升级",
        level=4,
        parent_code="GEOG-S2-CH2",
        description="资源枯竭型城市面临的问题(资源衰竭/环境恶化/经济衰退)、转型发展的途径(培育新产业/发展旅游/生态修复)、产业结构升级",
        keywords=["资源枯竭", "产业转型", "产业升级", "新兴产业", "可持续发展"],
    ),

    # ── 第三章: 区域协调 ───────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="GEOG-S2-CH3",
        name="区域协调",
        level=3,
        parent_code="GEOG-S2",
        description="大都市辐射带动(城市群)、产业转移与区域协调、流域的综合开发与协调",
        keywords=["区域协调", "城市群", "产业转移", "流域开发"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-S2-CH3-01",
        name="大都市辐射带动与产业转移",
        level=4,
        parent_code="GEOG-S2-CH3",
        description="大都市的辐射带动作用(长三角/珠三角/京津冀)、产业转移的原因(劳动力/内部交易成本/市场/政策)与影响",
        keywords=["大都市辐射", "城市群", "产业转移", "长三角", "珠三角"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-S2-CH3-02",
        name="流域的综合开发",
        level=4,
        parent_code="GEOG-S2-CH3",
        description="流域的基本特征(分水岭/干支流/流域面积)、流域综合开发的思路(防洪/发电/航运/灌溉/旅游)、田纳西河流域的综合开发经验",
        keywords=["流域", "综合开发", "防洪", "水电", "航运", "田纳西河"],
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  GEOG-S3: 选必三 · 资源、环境与国家安全
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第一章: 资源安全与国家安全 ─────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="GEOG-S3-CH1",
        name="资源安全与国家安全",
        level=3,
        parent_code="GEOG-S3",
        description="资源安全的含义与影响因素、水资源安全、耕地资源安全、矿产资源安全、能源安全",
        keywords=["资源安全", "水资源", "耕地", "矿产", "能源"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-S3-CH1-01",
        name="水资源与耕地资源安全",
        level=4,
        parent_code="GEOG-S3-CH1",
        description="水资源安全(分布不均/水污染/过度开采)、耕地资源安全(面积减少/质量下降)、保障措施(节水/跨流域调水/保护耕地)",
        keywords=["水资源安全", "耕地安全", "节水", "南水北调", "耕地红线"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-S3-CH1-02",
        name="矿产资源与能源安全",
        level=4,
        parent_code="GEOG-S3-CH1",
        description="矿产资源安全(储量有限/分布不均)、能源安全(石油/天然气/煤炭/新能源)、能源结构调整与能源安全战略",
        keywords=["矿产资源", "能源安全", "石油", "新能源", "能源结构", "能源战略"],
    ),

    # ── 第二章: 环境安全与国家安全 ─────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="GEOG-S3-CH2",
        name="环境安全与国家安全",
        level=3,
        parent_code="GEOG-S3",
        description="环境污染(大气/水/土壤)对国家安全的影响、环境污染防治、绿色发展",
        keywords=["环境污染", "大气污染", "水污染", "土壤污染", "污染防治"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-S3-CH2-01",
        name="环境污染与防治",
        level=4,
        parent_code="GEOG-S3-CH2",
        description="大气污染(酸雨/PM2.5/臭氧层破坏)、水污染(工业废水/农业面源/生活污水)、土壤污染(重金属/农药)及其防治措施",
        keywords=["大气污染", "酸雨", "PM2.5", "水污染", "土壤污染", "污染防治"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-S3-CH2-02",
        name="绿色发展与环境保护",
        level=4,
        parent_code="GEOG-S3-CH2",
        description="绿色发展理念、清洁生产与循环经济、环境保护的法律法规、公众参与",
        keywords=["绿色发展", "清洁生产", "循环经济", "碳达峰", "碳中和"],
    ),

    # ── 第三章: 生态安全与国家安全 ─────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="GEOG-S3-CH3",
        name="生态安全与国家安全",
        level=3,
        parent_code="GEOG-S3",
        description="生态退化的表现与危害、生态保护的措施、自然保护区与国家公园",
        keywords=["生态安全", "生态退化", "生态保护", "自然保护区"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-S3-CH3-01",
        name="生态退化与生态保护",
        level=4,
        parent_code="GEOG-S3-CH3",
        description="生态退化的表现(森林减少/草地退化/湿地萎缩/生物多样性下降)、生态保护措施(退耕还林/退牧还草/湿地恢复)",
        keywords=["生态退化", "森林减少", "草地退化", "湿地萎缩", "退耕还林"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-S3-CH3-02",
        name="自然保护区与国家公园",
        level=4,
        parent_code="GEOG-S3-CH3",
        description="自然保护区的建立与功能(核心区/缓冲区/实验区)、国家公园体制、生物多样性保护",
        keywords=["自然保护区", "国家公园", "核心区", "缓冲区", "生物多样性"],
    ),

    # ── 第四章: 全球变化与国家安全 ─────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="GEOG-S3-CH4",
        name="全球变化与国家安全",
        level=3,
        parent_code="GEOG-S3",
        description="全球气候变化(温室效应)、全球气候变化对国家安全的影响、应对全球气候变化的措施",
        keywords=["全球变化", "气候变化", "温室效应", "碳排放"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-S3-CH4-01",
        name="全球气候变化及其影响",
        level=4,
        parent_code="GEOG-S3-CH4",
        description="全球变暖的原因(温室气体排放)与证据(气温升高/冰川消融/海平面上升)、全球变暖对自然环境与人类社会的影响",
        keywords=["全球变暖", "温室气体", "冰川消融", "海平面上升", "极端天气"],
    ),
    KnowledgeTreeSeed(
        code="GEOG-S3-CH4-02",
        name="应对全球气候变化",
        level=4,
        parent_code="GEOG-S3-CH4",
        description="国际合作(巴黎协定)、中国的碳达峰碳中和目标、减缓与适应措施(节能减排/新能源/碳汇)",
        keywords=["巴黎协定", "碳达峰", "碳中和", "节能减排", "新能源", "碳汇"],
    ),
]
