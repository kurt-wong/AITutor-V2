"""
物理知识树 V2 (新课标课程结构对齐)

课程模块结构 (6 册):
  PHYS-C1  必修第一册   (运动的描述/匀变速直线运动/相互作用力/运动和力的关系)
  PHYS-C2  必修第二册   (抛体运动/圆周运动/万有引力与宇宙航行)
  PHYS-C3  必修第三册   (静电场/恒定电流/电路及其应用/磁场)
  PHYS-S1  选择性必修第一册 (动量守恒定律/机械振动/机械波)
  PHYS-S2  选择性必修第二册 (电磁感应/交变电流/电磁振荡与电磁波)
  PHYS-S3  选择性必修第三册 (分子动理论/气体固体液体/热力学定律/原子结构/原子核)

与 physics.py (PHYS-MECH / PHYS-EM / PHYS-THERM / PHYS-OPTIC / PHYS-ATOM / PHYS-EXPR) 并行存在，
不产生 code 冲突。

编码体系:
  L2: PHYS-C{册}                    e.g. PHYS-C1
  L3: PHYS-C{册}-{章}               e.g. PHYS-C1-01
  L4: PHYS-C{册}-{章}-{节}          e.g. PHYS-C1-01-01
"""

from __future__ import annotations

from app.domains.knowledge.tree_seed.types import KnowledgeTreeSeed

PHYSICS_KNOWLEDGE_TREE_V2: list[KnowledgeTreeSeed] = [

    # ═══════════════════════════════════════════════════════════════════════════════
    #  Level 2: 课程模块 (6 册)
    # ═══════════════════════════════════════════════════════════════════════════════

    KnowledgeTreeSeed(
        code="PHYS-C1",
        name="必修第一册",
        level=2,
        parent_code="PHYS",
        description="运动的描述、匀变速直线运动的研究、相互作用——力、运动和力的关系",
        keywords=["必修一", "运动学", "力学", "牛顿定律", "匀变速"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C2",
        name="必修第二册",
        level=2,
        parent_code="PHYS",
        description="抛体运动、圆周运动、万有引力与宇宙航行",
        keywords=["必修二", "抛体", "圆周", "万有引力", "航天"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C3",
        name="必修第三册",
        level=2,
        parent_code="PHYS",
        description="静电场、恒定电流、电路及其应用、磁场",
        keywords=["必修三", "电场", "电流", "电路", "磁场"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S1",
        name="选择性必修第一册",
        level=2,
        parent_code="PHYS",
        description="动量守恒定律、机械振动、机械波",
        keywords=[
            "选必一",
            "动量",
            "碰撞",
            "振动",
            "波",
            "冲量",
            "力",
            "力学",
            "加速度",
            "弹力",
            "摩擦力",
            "机械能",
            "牛顿",
            "能量",
            "运动",
            "重力",
        ]
    ),
    KnowledgeTreeSeed(
        code="PHYS-S2",
        name="选择性必修第二册",
        level=2,
        parent_code="PHYS",
        description="电磁感应、交变电流、电磁振荡与电磁波",
        keywords=["选必二", "电磁感应", "交变电流", "电磁波", "变压器"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S3",
        name="选择性必修第三册",
        level=2,
        parent_code="PHYS",
        description="分子动理论、气体固体液体、热力学定律、原子结构、原子核",
        keywords=[
            "选必三",
            "分子",
            "热力学",
            "气体",
            "原子",
            "原子核",
            "pV=nRT",
            "ΔU=Q+W",
            "内能",
            "布朗运动",
            "温度",
            "热学",
            "热机",
            "熵",
        ]
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  PHYS-C1: 必修第一册
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第一章: 运动的描述 ────────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="PHYS-C1-01",
        name="运动的描述",
        level=3,
        parent_code="PHYS-C1",
        description="质点、参考系、时间与位移、速度、加速度、匀变速直线运动的基本概念",
        keywords=["质点", "参考系", "位移", "速度", "加速度", "匀变速", "标量", "矢量", "运动学"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-C1-01-01",
        name="质点与参考系",
        level=4,
        parent_code="PHYS-C1-01",
        description="质点的理想化模型、参考系的选取原则、坐标系的建立",
        keywords=["质点", "参考系", "坐标系", "理想模型"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C1-01-02",
        name="时间与位移",
        level=4,
        parent_code="PHYS-C1-01",
        description="时刻与时间间隔、路程与位移的区别、矢量与标量",
        keywords=["时间", "时刻", "位移", "路程", "矢量"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C1-01-03",
        name="速度",
        level=4,
        parent_code="PHYS-C1-01",
        description="平均速度与瞬时速度的定义与区别、速度—时间图像(v-t图)",
        keywords=["平均速度", "瞬时速度", "速率", "v-t图"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C1-01-04",
        name="加速度",
        level=4,
        parent_code="PHYS-C1-01",
        description="加速度的定义a=Δv/Δt、加速度的方向与速度变化量的关系",
        keywords=["加速度", "速度变化量", "匀变速", "a=Δv/Δt"],
    ),

    # ── 第二章: 匀变速直线运动的研究 ──────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="PHYS-C1-02",
        name="匀变速直线运动的研究",
        level=3,
        parent_code="PHYS-C1",
        description="实验探究匀变速直线运动、速度与时间的关系、位移与时间的关系、自由落体运动",
        keywords=[
            "匀变速",
            "实验探究",
            "自由落体",
            "纸带",
            "v-t图",
            "v0t+1/2at²",
            "v=v₀+at",
            "v²-v₀²=2ax",
            "x=v0t+",
            "初速度",
            "制动距离",
            "刹车距离",
            "匀减速",
            "匀加速",
            "末速度",
        ]
    ),
    KnowledgeTreeSeed(
        code="PHYS-C1-02-01",
        name="实验：探究匀变速直线运动",
        level=4,
        parent_code="PHYS-C1-02",
        description="打点计时器的使用、纸带数据处理、逐差法求加速度",
        keywords=[
            "打点计时器",
            "纸带",
            "逐差法",
            "实验探究",
            "刻度尺",
            "劲度系数",
            "小车质量",
            "平衡摩擦力",
            "弹簧测力计",
            "控制变量法",
            "槽码",
            "橡皮绳",
            "游标卡尺",
            "纸带分析",
            "螺旋测微器",
            "计数点",
            "钩码",
            "验证机械能守恒",
            "验证牛顿定律",
        ]
    ),
    KnowledgeTreeSeed(
        code="PHYS-C1-02-02",
        name="速度与时间的关系",
        level=4,
        parent_code="PHYS-C1-02",
        description="v=v₀+at公式的推导与应用、v-t图像的物理意义",
        keywords=["v=v₀+at", "速度公式", "v-t图", "斜率"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C1-02-03",
        name="位移与时间的关系",
        level=4,
        parent_code="PHYS-C1-02",
        description="x=v₀t+½at²的推导与应用、v²-v₀²=2ax、位移—时间图像",
        keywords=["x=v₀t+½at²", "v²-v₀²=2ax", "位移公式", "x-t图"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C1-02-04",
        name="自由落体运动",
        level=4,
        parent_code="PHYS-C1-02",
        description="自由落体运动的条件、重力加速度g、自由落体运动公式",
        keywords=["自由落体", "重力加速度", "g=9.8m/s²", "空气阻力"],
    ),

    # ── 第三章: 相互作用——力 ─────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="PHYS-C1-03",
        name="相互作用——力",
        level=3,
        parent_code="PHYS-C1",
        description="重力与弹力、摩擦力、牛顿第三定律、力的合成与分解、共点力的平衡",
        keywords=["重力", "弹力", "摩擦力", "牛顿第三定律", "共点力平衡", "f=μN", "分力", "力", "合力", "胡克定律"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-C1-03-01",
        name="重力与弹力",
        level=4,
        parent_code="PHYS-C1-03",
        description="重力G=mg的大小与方向、重心的概念、弹力的产生条件、胡克定律F=kx",
        keywords=["重力", "重心", "弹力", "胡克定律", "F=kx"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C1-03-02",
        name="摩擦力",
        level=4,
        parent_code="PHYS-C1-03",
        description="静摩擦力与滑动摩擦力的产生条件、f=μN、摩擦力方向的判定",
        keywords=["静摩擦力", "滑动摩擦力", "f=μN", "动摩擦因数"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C1-03-03",
        name="牛顿第三定律",
        level=4,
        parent_code="PHYS-C1-03",
        description="作用力与反作用力的关系、与平衡力的区别",
        keywords=["牛顿第三定律", "作用力", "反作用力", "平衡力"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C1-03-04",
        name="力的合成与分解",
        level=4,
        parent_code="PHYS-C1-03",
        description="平行四边形定则、三角形定则、正交分解法",
        keywords=["平行四边形定则", "合力", "分力", "正交分解"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C1-03-05",
        name="共点力的平衡",
        level=4,
        parent_code="PHYS-C1-03",
        description="共点力平衡条件ΣF=0、受力分析方法(整体法与隔离法)、三力汇交原理",
        keywords=[
            "共点力平衡",
            "ΣF=0",
            "受力分析",
            "整体法",
            "隔离法",
            "夹角",
            "平行四边形定则",
            "拉力",
            "支持力",
            "斜面",
            "正交分解",
            "水平方向",
            "竖直方向",
            "轻杆",
            "轻绳",
            "风力",
        ]
    ),

    # ── 第四章: 运动和力的关系 ───────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="PHYS-C1-04",
        name="运动和力的关系",
        level=3,
        parent_code="PHYS-C1",
        description="牛顿第一定律、实验探究加速度与力和质量的关系、牛顿第二定律、力学单位制、牛顿运动定律应用",
        keywords=["牛顿第一定律", "牛顿第二定律", "F=ma", "惯性", "单位制"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C1-04-01",
        name="牛顿第一定律",
        level=4,
        parent_code="PHYS-C1-04",
        description="伽利略理想实验、牛顿第一定律的内容、惯性与质量的关系",
        keywords=["牛顿第一定律", "惯性", "伽利略", "理想实验"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C1-04-02",
        name="实验：探究加速度与力和质量的关系",
        level=4,
        parent_code="PHYS-C1-04",
        description="控制变量法、实验方案设计、数据处理与图像分析",
        keywords=["控制变量法", "加速度", "实验探究", "a-F图", "a-1/m图"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C1-04-03",
        name="牛顿第二定律",
        level=4,
        parent_code="PHYS-C1-04",
        description="F=ma的内容与理解、力的独立作用原理、两类动力学问题",
        keywords=[
            "F=ma",
            "牛顿第二定律",
            "动力学",
            "合外力",
            "a=F/m",
            "制动力",
            "加速度与力",
            "弹簧伸长量",
            "恒力",
            "水平恒力",
            "电梯",
            "速度变化量",
        ]
    ),
    KnowledgeTreeSeed(
        code="PHYS-C1-04-04",
        name="力学单位制",
        level=4,
        parent_code="PHYS-C1-04",
        description="基本单位与导出单位、国际单位制(SI)、力学中的三个基本单位",
        keywords=["单位制", "基本单位", "导出单位", "SI", "kg·m·s"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C1-04-05",
        name="牛顿运动定律的应用",
        level=4,
        parent_code="PHYS-C1-04",
        description="超重与失重、连接体问题、临界与极值问题",
        keywords=["超重", "失重", "连接体", "临界问题", "电梯", "F=ma", "作用力反作用力", "惯性", "牛顿", "牛顿第三定律"]
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  PHYS-C2: 必修第二册
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第一章: 抛体运动 ─────────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="PHYS-C2-01",
        name="抛体运动",
        level=3,
        parent_code="PHYS-C2",
        description="曲线运动的条件、运动的合成与分解、实验探究平抛运动、抛体运动的规律",
        keywords=["曲线运动", "平抛", "运动合成", "运动分解"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C2-01-01",
        name="曲线运动",
        level=4,
        parent_code="PHYS-C2-01",
        description="曲线运动的速度方向、曲线运动的条件(力与速度不共线)",
        keywords=["曲线运动", "切线方向", "合外力", "变速运动", "向心力", "圆周运动", "平抛"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-C2-01-02",
        name="运动的合成与分解",
        level=4,
        parent_code="PHYS-C2-01",
        description="合运动与分运动的等时性与独立性、小船渡河问题、绳端速度分解",
        keywords=["运动合成", "运动分解", "小船渡河", "绳端速度", "分解", "合成"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-C2-01-03",
        name="实验：探究平抛运动的特点",
        level=4,
        parent_code="PHYS-C2-01",
        description="平抛运动的实验装置与方法、轨迹描绘、水平与竖直方向运动分析",
        keywords=["平抛实验", "轨迹", "频闪照片", "竖直位移"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C2-01-04",
        name="抛体运动的规律",
        level=4,
        parent_code="PHYS-C2-01",
        description="平抛运动公式x=v₀t、y=½gt²、速度偏向角与位移偏向角的关系、斜抛运动",
        keywords=["x=v₀t", "y=½gt²", "轨迹方程", "斜抛", "速度偏向角", "平抛"]
    ),

    # ── 第二章: 圆周运动 ─────────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="PHYS-C2-02",
        name="圆周运动",
        level=3,
        parent_code="PHYS-C2",
        description="圆周运动的基本物理量、向心力、向心加速度、生活中的圆周运动",
        keywords=["圆周运动", "向心力", "向心加速度", "线速度", "角速度", "a=v²/r", "ω=2π/T"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-C2-02-01",
        name="圆周运动的基本物理量",
        level=4,
        parent_code="PHYS-C2-02",
        description="线速度v、角速度ω、周期T、频率f、转速n及相互关系v=ωr=2πr/T",
        keywords=["线速度", "角速度", "周期", "频率", "v=ωr"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C2-02-02",
        name="向心加速度与向心力",
        level=4,
        parent_code="PHYS-C2-02",
        description="向心加速度a=v²/r=ω²r、向心力F=mv²/r的来源与分析",
        keywords=["向心加速度", "向心力", "a=v²/r", "F=mv²/r"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C2-02-03",
        name="生活中的圆周运动",
        level=4,
        parent_code="PHYS-C2-02",
        description="汽车转弯、火车转弯、竖直面圆周运动(绳/杆模型)、离心运动",
        keywords=["汽车转弯", "火车转弯", "竖直面", "离心运动", "临界速度"],
    ),

    # ── 第三章: 万有引力与宇宙航行 ───────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="PHYS-C2-03",
        name="万有引力与宇宙航行",
        level=3,
        parent_code="PHYS-C2",
        description="行星运动规律、万有引力定律、万有引力理论成就、宇宙航行、相对论时空观简介",
        keywords=["万有引力", "开普勒", "宇宙航行", "卫星", "相对论", "天体", "宇宙速度"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-C2-03-01",
        name="行星运动",
        level=4,
        parent_code="PHYS-C2-03",
        description="开普勒三大定律(轨道定律、面积定律、周期定律)的内容与应用",
        keywords=["开普勒定律", "椭圆轨道", "面积定律", "周期定律"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C2-03-02",
        name="万有引力定律",
        level=4,
        parent_code="PHYS-C2-03",
        description="F=GMm/r²的推导与适用条件、引力常量G的测定(卡文迪许扭秤)",
        keywords=["万有引力", "F=GMm/r²", "引力常量", "卡文迪许", "G常量", "开普勒"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-C2-03-03",
        name="万有引力理论的成就",
        level=4,
        parent_code="PHYS-C2-03",
        description="称量天体质量、发现未知天体、计算天体密度",
        keywords=["天体质量", "天体密度", "GM=gR²", "海王星"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C2-03-04",
        name="宇宙航行",
        level=4,
        parent_code="PHYS-C2-03",
        description="三个宇宙速度(7.9/11.2/16.7km/s)、人造卫星、同步卫星、变轨问题",
        keywords=["宇宙速度", "第一宇宙速度", "同步卫星", "变轨", "近地卫星", "GM=gR²", "天体运动"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-C2-03-05",
        name="相对论时空观简介",
        level=4,
        parent_code="PHYS-C2-03",
        description="狭义相对论的基本假设、时间膨胀与长度收缩、质能方程E=mc²",
        keywords=["相对论", "光速不变", "时间膨胀", "长度收缩", "E=mc²"],
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  PHYS-C3: 必修第三册
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第一章: 静电场 ───────────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="PHYS-C3-01",
        name="静电场",
        level=3,
        parent_code="PHYS-C3",
        description="电荷守恒、库仑定律、电场强度、电势能与电势、电势差、静电的防止与利用",
        keywords=["静电场", "库仑定律", "电场强度", "电势", "电势差", "带电粒子", "库仑", "电场", "电容"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-C3-01-01",
        name="电荷及其守恒定律",
        level=4,
        parent_code="PHYS-C3-01",
        description="电荷的种类、电荷守恒定律、感应起电与接触起电、元电荷e=1.6×10⁻¹⁹C",
        keywords=["电荷", "电荷守恒", "感应起电", "元电荷"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C3-01-02",
        name="库仑定律",
        level=4,
        parent_code="PHYS-C3-01",
        description="F=kQq/r²的内容与适用条件(点电荷、真空)、静电力常量k=9×10⁹N·m²/C²",
        keywords=["库仑定律", "F=kQq/r²", "点电荷", "静电力常量", "电场强度", "电场线"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-C3-01-03",
        name="电场与电场强度",
        level=4,
        parent_code="PHYS-C3-01",
        description="电场的概念、电场强度E=F/q的定义、点电荷场强E=kQ/r²、电场线与电场叠加",
        keywords=["电场", "电场强度", "E=F/q", "E=kQ/r²", "电场线"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C3-01-04",
        name="电势能与电势",
        level=4,
        parent_code="PHYS-C3-01",
        description="电势能、电势φ的定义、等势面、电场力做功与电势能变化的关系",
        keywords=["电势能", "电势", "等势面", "W=qU", "电势降低", "U=Ed", "电势差"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-C3-01-05",
        name="电势差",
        level=4,
        parent_code="PHYS-C3-01",
        description="电势差U_AB=φ_A-φ_B、匀强电场中U=Ed、电场力做功W=qU_AB",
        keywords=["电势差", "U=Ed", "匀强电场", "W=qU"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C3-01-06",
        name="静电的防止与利用",
        level=4,
        parent_code="PHYS-C3-01",
        description="静电屏蔽、静电除尘、避雷针原理、尖端放电",
        keywords=["静电屏蔽", "静电除尘", "避雷针", "尖端放电"],
    ),

    # ── 第二章: 恒定电流 ─────────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="PHYS-C3-02",
        name="恒定电流",
        level=3,
        parent_code="PHYS-C3",
        description="电源和电流、电动势、闭合电路的欧姆定律、实验：电池电动势和内阻的测量",
        keywords=["电流", "电动势", "欧姆定律", "闭合电路", "内阻", "P=UI", "R=ρL/S", "U=IR", "焦耳定律", "电功率", "电阻"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-C3-02-01",
        name="电源和电流",
        level=4,
        parent_code="PHYS-C3-02",
        description="电流的形成条件、电流的定义I=q/t、电流的方向、恒定电流",
        keywords=["电源", "电流", "I=q/t", "恒定电流", "自由电子"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C3-02-02",
        name="电动势",
        level=4,
        parent_code="PHYS-C3-02",
        description="电动势的物理意义、电动势与电压的区别、非静电力做功",
        keywords=["电动势", "非静电力", "内电压", "外电压"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C3-02-03",
        name="闭合电路的欧姆定律",
        level=4,
        parent_code="PHYS-C3-02",
        description="E=I(R+r)、路端电压U=E-Ir、电源的功率与效率",
        keywords=["闭合电路", "E=I(R+r)", "路端电压", "U=E-Ir", "电源效率"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C3-02-04",
        name="实验：电池电动势和内阻的测量",
        level=4,
        parent_code="PHYS-C3-02",
        description="伏安法测电动势和内阻、U-I图像法、误差分析",
        keywords=["伏安法", "U-I图", "电动势", "内阻", "误差分析"],
    ),

    # ── 第三章: 电路及其应用 ─────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="PHYS-C3-03",
        name="电路及其应用",
        level=3,
        parent_code="PHYS-C3",
        description="串联电路和并联电路、电阻定律、实验：练习使用多用电表、能源与可持续发展",
        keywords=["串联", "并联", "电阻定律", "多用电表", "能源"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C3-03-01",
        name="串联电路和并联电路",
        level=4,
        parent_code="PHYS-C3-03",
        description="串联电路的电流、电压、电阻特点、并联电路的电流、电压、电阻特点、混联电路",
        keywords=["串联", "并联", "分压", "分流", "混联"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C3-03-02",
        name="电阻定律",
        level=4,
        parent_code="PHYS-C3-03",
        description="R=ρL/S的内容、电阻率与温度的关系、半导体与超导体",
        keywords=["电阻定律", "R=ρL/S", "电阻率", "半导体", "超导体"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C3-03-03",
        name="实验：练习使用多用电表",
        level=4,
        parent_code="PHYS-C3-03",
        description="多用电表的结构与原理、测量电压电流电阻的操作、二极管检测",
        keywords=[
            "多用电表",
            "欧姆挡",
            "电压挡",
            "电流挡",
            "二极管",
            "E和r",
            "伏安法",
            "内接",
            "外接",
            "实验",
            "打点计时器",
            "控制变量法",
            "游标卡尺",
            "纸带分析",
            "螺旋测微器",
        ]
    ),
    KnowledgeTreeSeed(
        code="PHYS-C3-03-04",
        name="能源与可持续发展",
        level=4,
        parent_code="PHYS-C3-03",
        description="能源的分类、能量转化与守恒、可持续发展理念",
        keywords=["能源", "一次能源", "二次能源", "可持续发展"],
    ),

    # ── 第四章: 磁场 ─────────────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="PHYS-C3-04",
        name="磁场",
        level=3,
        parent_code="PHYS-C3",
        description="磁场与磁感线、磁感应强度、安培力、洛伦兹力、带电粒子在磁场中的运动",
        keywords=["磁场", "磁感应强度", "安培力", "洛伦兹力", "磁感线", "左手定则"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-C3-04-01",
        name="磁场与磁感线",
        level=4,
        parent_code="PHYS-C3-04",
        description="磁场的基本性质、磁感线的分布特点、安培定则(右手螺旋定则)",
        keywords=["磁场", "磁感线", "安培定则", "条形磁铁", "通电螺线管"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C3-04-02",
        name="磁感应强度",
        level=4,
        parent_code="PHYS-C3-04",
        description="B=F/IL的定义、磁感应强度的方向、磁通量Φ=BS",
        keywords=["磁感应强度", "B=F/IL", "磁通量", "Φ=BS", "特斯拉"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C3-04-03",
        name="安培力",
        level=4,
        parent_code="PHYS-C3-04",
        description="安培力F=BILsinθ的大小与方向、左手定则、安培力的应用",
        keywords=["安培力", "F=BIL", "左手定则", "电动机", "F=BILsinθ", "磁感应强度"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-C3-04-04",
        name="洛伦兹力",
        level=4,
        parent_code="PHYS-C3-04",
        description="洛伦兹力f=qvBsinθ的特点、洛伦兹力不做功、左手定则判断方向",
        keywords=["洛伦兹力", "f=qvB", "左手定则", "不做功"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-C3-04-05",
        name="带电粒子在磁场中的运动",
        level=4,
        parent_code="PHYS-C3-04",
        description="匀速圆周运动r=mv/qB、T=2πm/qB、质谱仪与回旋加速器的原理",
        keywords=[
            "r=mv/qB",
            "T=2πm/qB",
            "质谱仪",
            "回旋加速器",
            "匀速圆周",
            "C=Q/U",
            "C=εS/4πkd",
            "f=qvB",
            "偏转",
            "带电粒子",
            "洛伦兹力",
            "电容",
        ]
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  PHYS-S1: 选择性必修第一册
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第一章: 动量守恒定律 ─────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="PHYS-S1-01",
        name="动量守恒定律",
        level=3,
        parent_code="PHYS-S1",
        description="动量与动量定理、动量守恒定律、实验验证动量守恒定律、碰撞、反冲运动与火箭",
        keywords=["动量", "动量定理", "动量守恒", "碰撞", "反冲", "冲量", "完全非弹性", "弹性碰撞", "爆炸"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-S1-01-01",
        name="动量与动量定理",
        level=4,
        parent_code="PHYS-S1-01",
        description="动量p=mv、冲量I=Ft、动量定理I=Δp=Ft的内容与应用",
        keywords=["动量", "冲量", "p=mv", "I=Ft", "动量定理"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S1-01-02",
        name="动量守恒定律",
        level=4,
        parent_code="PHYS-S1-01",
        description="动量守恒的条件(系统合外力为零)、m₁v₁+m₂v₂=m₁v₁'+m₂v₂'",
        keywords=["动量守恒", "系统", "合外力为零", "守恒条件"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S1-01-03",
        name="实验：验证动量守恒定律",
        level=4,
        parent_code="PHYS-S1-01",
        description="气垫导轨实验、光电门测速、一维碰撞的实验验证",
        keywords=["气垫导轨", "光电门", "碰撞实验", "验证"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S1-01-04",
        name="碰撞",
        level=4,
        parent_code="PHYS-S1-01",
        description="弹性碰撞、非弹性碰撞、完全非弹性碰撞的特点与计算",
        keywords=["弹性碰撞", "非弹性碰撞", "完全非弹性", "速度交换"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S1-01-05",
        name="反冲运动与火箭",
        level=4,
        parent_code="PHYS-S1-01",
        description="反冲运动的原理、火箭的工作原理、动量守恒在反冲中的应用",
        keywords=["反冲运动", "火箭", "喷气", "动量守恒"],
    ),

    # ── 第二章: 机械振动 ─────────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="PHYS-S1-02",
        name="机械振动",
        level=3,
        parent_code="PHYS-S1",
        description="简谐运动、描述简谐运动的物理量、回复力与能量、单摆、实验测重力加速度、阻尼振动与受迫振动共振",
        keywords=["简谐运动", "单摆", "回复力", "共振", "阻尼", "干涉", "振动", "波", "衍射"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-S1-02-01",
        name="简谐运动",
        level=4,
        parent_code="PHYS-S1-02",
        description="简谐运动的定义与特征、弹簧振子模型、x-t图像(正弦曲线)",
        keywords=["简谐运动", "弹簧振子", "正弦曲线", "平衡位置"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S1-02-02",
        name="描述简谐运动的物理量",
        level=4,
        parent_code="PHYS-S1-02",
        description="振幅A、周期T、频率f、相位与初相位、简谐运动方程x=Asin(ωt+φ₀)",
        keywords=["振幅", "周期", "频率", "相位", "x=Asin(ωt+φ₀)", "F=-kx", "简谐运动"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-S1-02-03",
        name="回复力与能量",
        level=4,
        parent_code="PHYS-S1-02",
        description="回复力F=-kx的特点、简谐运动中动能与势能的转化、机械能守恒",
        keywords=["回复力", "F=-kx", "动能", "势能", "机械能守恒", "E_k=½mv²", "E_p=mgh", "功", "功率", "动能定理"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-S1-02-04",
        name="单摆",
        level=4,
        parent_code="PHYS-S1-02",
        description="单摆的周期公式T=2π√(L/g)、单摆的等时性、单摆的应用",
        keywords=["单摆", "T=2π√(L/g)", "等时性", "摆长"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S1-02-05",
        name="实验：用单摆测量重力加速度",
        level=4,
        parent_code="PHYS-S1-02",
        description="单摆法测g的原理与操作、数据处理(图像法)、误差分析",
        keywords=["单摆测g", "重力加速度", "T²-L图", "误差分析"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S1-02-06",
        name="阻尼振动、受迫振动与共振",
        level=4,
        parent_code="PHYS-S1-02",
        description="阻尼振动的振幅衰减、受迫振动的频率特征、共振的条件与应用",
        keywords=["阻尼振动", "受迫振动", "共振", "固有频率", "策动力", "T=2π√(L/g)", "单摆"]
    ),

    # ── 第三章: 机械波 ───────────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="PHYS-S1-03",
        name="机械波",
        level=3,
        parent_code="PHYS-S1",
        description="波的形成与传播、描述机械波的物理量、波的反射折射衍射、波的干涉、多普勒效应",
        keywords=[
            "机械波",
            "波长",
            "波速",
            "干涉",
            "衍射",
            "n=sinθ₁/sinθ₂",
            "v=λf",
            "Δx=Lλ/d",
            "偏振",
            "光子",
            "光学",
            "光电效应",
            "全反射",
            "双缝",
            "双缝干涉",
            "多普勒效应",
            "折射",
        ]
    ),
    KnowledgeTreeSeed(
        code="PHYS-S1-03-01",
        name="波的形成与传播",
        level=4,
        parent_code="PHYS-S1-03",
        description="横波与纵波的区别、波的形成条件、波的传播特点(质点不随波迁移)",
        keywords=["横波", "纵波", "波源", "介质", "质点振动"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S1-03-02",
        name="描述机械波的物理量",
        level=4,
        parent_code="PHYS-S1-03",
        description="波长λ、波速v、频率f的关系v=λf、波形图的识别与应用",
        keywords=["波长", "波速", "v=λf", "波形图", "频率"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S1-03-03",
        name="波的反射、折射与衍射",
        level=4,
        parent_code="PHYS-S1-03",
        description="波的反射定律、波的折射现象、波的衍射条件(障碍物尺寸与波长相当)",
        keywords=["反射", "折射", "衍射", "惠更斯原理", "n=sinθ₁/sinθ₂", "临界角", "偏振", "全反射", "单缝衍射", "马吕斯定律"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-S1-03-04",
        name="波的干涉",
        level=4,
        parent_code="PHYS-S1-03",
        description="波的叠加原理、干涉的条件(频率相同)、加强区与减弱区的判定",
        keywords=["干涉", "叠加", "加强区", "减弱区", "波程差", "Δx=Lλ/d", "双缝干涉", "薄膜干涉"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-S1-03-05",
        name="多普勒效应",
        level=4,
        parent_code="PHYS-S1-03",
        description="多普勒效应的产生原因、波源与观察者相对运动时频率的变化、应用",
        keywords=["多普勒效应", "频率变化", "波源运动", "观察者运动", "hν", "光子", "光电效应", "逸出功", "量子"]
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  PHYS-S2: 选择性必修第二册
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第一章: 电磁感应 ─────────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="PHYS-S2-01",
        name="电磁感应",
        level=3,
        parent_code="PHYS-S2",
        description="楞次定律、法拉第电磁感应定律、涡流与电磁阻尼和电磁驱动、互感和自感",
        keywords=[
            "电磁感应",
            "楞次定律",
            "法拉第",
            "涡流",
            "自感",
            "E=BLv",
            "变压器",
            "安培力",
            "楞次",
            "洛伦兹力",
            "电势",
            "电场",
            "电容",
            "电流",
            "电磁",
            "磁场",
            "磁通量",
        ]
    ),
    KnowledgeTreeSeed(
        code="PHYS-S2-01-01",
        name="楞次定律",
        level=4,
        parent_code="PHYS-S2-01",
        description="感应电流方向的判断、楞次定律(增反减同)、右手定则",
        keywords=["楞次定律", "感应电流", "增反减同", "右手定则"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S2-01-02",
        name="法拉第电磁感应定律",
        level=4,
        parent_code="PHYS-S2-01",
        description="E=nΔΦ/Δt、E=BLvsinθ(导体切割)、转动切割E=½BL²ω",
        keywords=["法拉第", "E=nΔΦ/Δt", "E=BLv", "磁通量变化率", "E=n·ΔΦ/Δt", "磁通量"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-S2-01-03",
        name="涡流、电磁阻尼与电磁驱动",
        level=4,
        parent_code="PHYS-S2-01",
        description="涡流的产生原理、电磁阻尼与电磁驱动的应用、涡流的利用与防止",
        keywords=["涡流", "电磁阻尼", "电磁驱动", "电磁炉"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S2-01-04",
        name="互感和自感",
        level=4,
        parent_code="PHYS-S2-01",
        description="互感现象与应用、自感现象、自感电动势E=-LΔI/Δt、自感系数L",
        keywords=["互感", "自感", "自感系数", "E=-LΔI/Δt", "电感", "L", "涡流"]
    ),

    # ── 第二章: 交变电流 ─────────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="PHYS-S2-02",
        name="交变电流",
        level=3,
        parent_code="PHYS-S2",
        description="交变电流的产生、描述交变电流的物理量、变压器、电能的输送",
        keywords=["交变电流", "有效值", "变压器", "远距离输电", "输电"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-S2-02-01",
        name="交变电流的产生",
        level=4,
        parent_code="PHYS-S2-02",
        description="交流发电机原理、e=E_m·sinωt、E_m=NBSω、中性面",
        keywords=["交变电流", "E_m=NBSω", "e=E_m·sinωt", "中性面", "发电机", "有效值"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-S2-02-02",
        name="描述交变电流的物理量",
        level=4,
        parent_code="PHYS-S2-02",
        description="峰值、有效值E=E_m/√2、周期与频率、平均值",
        keywords=["峰值", "有效值", "E_m/√2", "周期", "平均值"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S2-02-03",
        name="变压器",
        level=4,
        parent_code="PHYS-S2-02",
        description="变压器的原理、U₁/U₂=n₁/n₂、I₁/I₂=n₂/n₁、理想变压器功率关系",
        keywords=["变压器", "U₁/U₂=n₁/n₂", "匝数比", "升压", "降压", "远距离输电", "高压输电"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-S2-02-04",
        name="电能的输送",
        level=4,
        parent_code="PHYS-S2-02",
        description="远距离输电中的功率损失P_损=I²R、高压输电减小损耗的原理、输电电路分析",
        keywords=["远距离输电", "高压输电", "P_损=I²R", "输电效率"],
    ),

    # ── 第三章: 电磁振荡与电磁波 ─────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="PHYS-S2-03",
        name="电磁振荡与电磁波",
        level=3,
        parent_code="PHYS-S2",
        description="电磁振荡的产生、电磁场与电磁波、无线电波的发射和接收、电磁波谱",
        keywords=["电磁振荡", "电磁波", "LC回路", "电磁波谱", "无线电"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S2-03-01",
        name="电磁振荡",
        level=4,
        parent_code="PHYS-S2-03",
        description="LC振荡电路、电磁振荡的周期T=2π√(LC)、电场能与磁场能的转化",
        keywords=["电磁振荡", "LC回路", "T=2π√(LC)", "电场能", "磁场能"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S2-03-02",
        name="电磁场与电磁波",
        level=4,
        parent_code="PHYS-S2-03",
        description="麦克斯韦电磁场理论、电磁波的产生与传播特点、c=λf=3×10⁸m/s",
        keywords=["电磁波", "麦克斯韦", "c=λf", "光速", "电磁场"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S2-03-03",
        name="无线电波的发射和接收",
        level=4,
        parent_code="PHYS-S2-03",
        description="调制(调幅/调频)、调谐与解调、无线电波的传播方式",
        keywords=["调制", "调幅", "调频", "调谐", "解调"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S2-03-04",
        name="电磁波谱",
        level=4,
        parent_code="PHYS-S2-03",
        description="无线电波、红外线、可见光、紫外线、X射线、γ射线的特点与应用",
        keywords=["电磁波谱", "红外线", "紫外线", "X射线", "γ射线"],
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  PHYS-S3: 选择性必修第三册
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第一章: 分子动理论 ───────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="PHYS-S3-01",
        name="分子动理论",
        level=3,
        parent_code="PHYS-S3",
        description="分子动理论的基本内容、实验：用油膜法估测分子的大小、分子运动速率分布、分子动能和分子势能",
        keywords=["分子动理论", "分子", "油膜法", "速率分布", "内能", "分子力", "布朗运动", "扩散"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-S3-01-01",
        name="分子动理论的基本内容",
        level=4,
        parent_code="PHYS-S3-01",
        description="物质由分子组成、分子永不停息地做无规则运动(布朗运动)、分子间存在引力和斥力",
        keywords=["分子动理论", "布朗运动", "分子力", "扩散现象"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S3-01-02",
        name="实验：用油膜法估测分子的大小",
        level=4,
        parent_code="PHYS-S3-01",
        description="油酸薄膜法的原理与操作、单分子油膜模型、分子直径的估算",
        keywords=["油膜法", "油酸", "单分子膜", "分子直径"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S3-01-03",
        name="分子运动速率分布",
        level=4,
        parent_code="PHYS-S3-01",
        description="气体分子速率分布规律、温度对速率分布的影响、统计规律",
        keywords=["速率分布", "麦克斯韦分布", "温度", "统计规律"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S3-01-04",
        name="分子动能和分子势能",
        level=4,
        parent_code="PHYS-S3-01",
        description="分子平均动能与温度的关系、分子势能与分子间距的关系、物体的内能",
        keywords=["分子动能", "分子势能", "内能", "温度", "分子间距"],
    ),

    # ── 第二章: 气体、固体和液体 ────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="PHYS-S3-02",
        name="气体、固体和液体",
        level=3,
        parent_code="PHYS-S3",
        description="气体的等温变化、等容变化和等压变化、理想气体状态方程、固体、液体",
        keywords=["气体", "固体", "液体", "理想气体", "状态方程"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S3-02-01",
        name="气体的等温变化",
        level=4,
        parent_code="PHYS-S3-02",
        description="玻意耳定律p₁V₁=p₂V₂、p-V图像(等温线)、适用条件",
        keywords=["玻意耳定律", "等温变化", "p₁V₁=p₂V₂", "p-V图", "pV=C", "查理定律", "盖-吕萨克"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-S3-02-02",
        name="气体的等容变化和等压变化",
        level=4,
        parent_code="PHYS-S3-02",
        description="查理定律p₁/T₁=p₂/T₂、盖-吕萨克定律V₁/T₁=V₂/T₂、p-T图与V-T图",
        keywords=["查理定律", "盖-吕萨克定律", "等容变化", "等压变化"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S3-02-03",
        name="理想气体状态方程",
        level=4,
        parent_code="PHYS-S3-02",
        description="pV/T=C(常量)、pV=nRT的内容与应用、理想气体模型",
        keywords=["理想气体", "pV=nRT", "状态方程", "气体常量", "ΔU=Q+W", "热力学第二定律"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-S3-02-04",
        name="固体",
        level=4,
        parent_code="PHYS-S3-02",
        description="晶体与非晶体的区别、单晶体与多晶体、晶体的微观结构",
        keywords=["晶体", "非晶体", "单晶体", "多晶体", "各向异性"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S3-02-05",
        name="液体",
        level=4,
        parent_code="PHYS-S3-02",
        description="液体的表面张力、浸润与不浸润、毛细现象、液晶",
        keywords=["表面张力", "浸润", "不浸润", "毛细现象", "液晶"],
    ),

    # ── 第三章: 热力学定律 ───────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="PHYS-S3-03",
        name="热力学定律",
        level=3,
        parent_code="PHYS-S3",
        description="功和内能、热和内能、热力学第一定律、热力学第二定律、能源与环境",
        keywords=["热力学", "内能", "第一定律", "第二定律", "熵", "pV=nRT", "ΔU=Q+W", "气体"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-S3-03-01",
        name="功、热和内能",
        level=4,
        parent_code="PHYS-S3-03",
        description="做功与内能变化的关系、热传递与内能变化的关系、内能的改变方式",
        keywords=["功", "热", "内能", "绝热过程", "等温过程", "P=Fv", "W=Flcosθ", "功率", "机车启动"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-S3-03-02",
        name="热力学第一定律",
        level=4,
        parent_code="PHYS-S3-03",
        description="ΔU=Q+W的内容与符号规定、热力学第一定律的应用、第一类永动机不可能",
        keywords=["热力学第一定律", "ΔU=Q+W", "第一类永动机", "能量守恒", "功能关系", "摩擦力做功", "系统能量"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-S3-03-03",
        name="热力学第二定律",
        level=4,
        parent_code="PHYS-S3-03",
        description="热力学第二定律的两种表述(克劳修斯/开尔文)、熵的概念、第二类永动机不可能",
        keywords=["热力学第二定律", "熵增", "第二类永动机", "不可逆过程"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S3-03-04",
        name="能源与环境",
        level=4,
        parent_code="PHYS-S3-03",
        description="能源危机与环境保护、新能源开发、热机效率与可持续发展",
        keywords=["能源", "环境", "热机效率", "新能源", "可持续发展"],
    ),

    # ── 第四章: 原子结构 ─────────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="PHYS-S3-04",
        name="原子结构",
        level=3,
        parent_code="PHYS-S3",
        description="电子的发现、原子的核式结构模型、氢原子光谱、玻尔的原子模型",
        keywords=["原子结构", "电子", "核式结构", "玻尔模型", "能级", "E₁=-13.6eV", "氢光谱", "玻尔"]
    ),
    KnowledgeTreeSeed(
        code="PHYS-S3-04-01",
        name="电子的发现",
        level=4,
        parent_code="PHYS-S3-04",
        description="阴极射线实验、汤姆孙测电子比荷(e/m)、电子的发现意义",
        keywords=["电子", "阴极射线", "汤姆孙", "比荷"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S3-04-02",
        name="原子的核式结构模型",
        level=4,
        parent_code="PHYS-S3-04",
        description="α粒子散射实验(卢瑟福)、核式结构模型、原子核的估算",
        keywords=["α粒子散射", "卢瑟福", "核式结构", "原子核"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S3-04-03",
        name="氢原子光谱",
        level=4,
        parent_code="PHYS-S3-04",
        description="氢原子光谱的线系(巴耳末系等)、光谱分析、玻尔模型的实验基础",
        keywords=["氢原子光谱", "巴耳末系", "光谱分析", "线状谱"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S3-04-04",
        name="玻尔的原子模型",
        level=4,
        parent_code="PHYS-S3-04",
        description="玻尔三条假设(定态/跃迁/轨道量子化)、能级图E_n=E₁/n²、E₁=-13.6eV",
        keywords=["玻尔模型", "能级", "E_n=E₁/n²", "跃迁", "量子化"],
    ),

    # ── 第五章: 原子核 ───────────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="PHYS-S3-05",
        name="原子核",
        level=3,
        parent_code="PHYS-S3",
        description="原子核的组成、放射性元素的衰变、核力与结合能、核裂变与核聚变",
        keywords=[
            "原子核",
            "衰变",
            "核力",
            "结合能",
            "裂变",
            "聚变",
            "E=Δmc²",
            "E₁=-13.6eV",
            "hν",
            "光电效应",
            "半衰期",
            "原子",
            "双缝干涉测波长",
            "折射率",
            "插针法",
            "波粒二象性",
            "玻尔",
            "能级",
            "逸出功",
            "量子",
        ]
    ),
    KnowledgeTreeSeed(
        code="PHYS-S3-05-01",
        name="原子核的组成",
        level=4,
        parent_code="PHYS-S3-05",
        description="质子与中子的发现、核子与核素、同位素的概念",
        keywords=["质子", "中子", "核子", "核素", "同位素"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S3-05-02",
        name="放射性元素的衰变",
        level=4,
        parent_code="PHYS-S3-05",
        description="α衰变与β衰变、衰变方程、半衰期τ的统计意义",
        keywords=["α衰变", "β衰变", "半衰期", "衰变方程", "γ射线"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S3-05-03",
        name="核力与结合能",
        level=4,
        parent_code="PHYS-S3-05",
        description="核力的特点(短程力/饱和性)、质量亏损Δm、结合能与比结合能、E=Δmc²",
        keywords=["核力", "结合能", "质量亏损", "E=Δmc²", "比结合能"],
    ),
    KnowledgeTreeSeed(
        code="PHYS-S3-05-04",
        name="核裂变与核聚变",
        level=4,
        parent_code="PHYS-S3-05",
        description="重核裂变(链式反应)、轻核聚变(热核反应)、核电站原理、核能的和平利用",
        keywords=["核裂变", "链式反应", "核聚变", "热核反应", "核电站"],
    ),
]
