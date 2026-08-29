"""
生物知识树 V2 (新课标课程结构对齐)

课程模块结构 (5 册):
  BIO-C1  必修一   (分子与细胞)
  BIO-C2  必修二   (遗传与进化)
  BIO-S1  选必一   (稳态与调节)
  BIO-S2  选必二   (生物与环境)
  BIO-S3  选必三   (生物技术与工程)

与 biology.py (BIO-CELL / BIO-GENE / BIO-STEAD / BIO-ECOL / BIO-EXPR) 并行存在，
不产生 code 冲突。

编码体系:
  L2: BIO-{C|S}{册}              e.g. BIO-C1
  L3: BIO-{C|S}{册}-CH{章}       e.g. BIO-C1-CH1
  L4: BIO-{C|S}{册}-CH{章}-{节}   e.g. BIO-C1-CH1-01
"""

from __future__ import annotations

from app.domains.knowledge.tree_seed.types import KnowledgeTreeSeed

BIOLOGY_KNOWLEDGE_TREE_V2: list[KnowledgeTreeSeed] = [

    # ═══════════════════════════════════════════════════════════════════════════════
    #  Level 2: 课程模块 (5 册)
    # ═══════════════════════════════════════════════════════════════════════════════

    KnowledgeTreeSeed(
        code="BIO-C1",
        name="必修一 · 分子与细胞",
        level=2,
        parent_code="BIO",
        description="走近细胞、组成细胞的分子、细胞的基本结构、物质输入输出、能量供应利用、细胞的生命历程",
        keywords=["必修一", "分子", "细胞", "代谢", "光合", "呼吸", "ATP", "C₃", "C₅", "增殖", "酶"]
    ),
    KnowledgeTreeSeed(
        code="BIO-C2",
        name="必修二 · 遗传与进化",
        level=2,
        parent_code="BIO",
        description="遗传因子的发现、基因和染色体的关系、基因的本质与表达、变异、进化",
        keywords=["必修二", "遗传", "基因", "DNA", "变异", "进化", "染色体"]
    ),
    KnowledgeTreeSeed(
        code="BIO-S1",
        name="选必一 · 稳态与调节",
        level=2,
        parent_code="BIO",
        description="人体内环境与稳态、神经调节、体液调节、免疫调节、植物生命活动调节",
        keywords=["选必一", "稳态", "神经", "激素", "免疫", "植物激素", "反射", "血糖"]
    ),
    KnowledgeTreeSeed(
        code="BIO-S2",
        name="选必二 · 生物与环境",
        level=2,
        parent_code="BIO",
        description="种群及其动态、群落及其演替、生态系统及其稳定性、人与环境",
        keywords=["选必二", "种群", "群落", "生态系统", "环境保护", "生态"]
    ),
    KnowledgeTreeSeed(
        code="BIO-S3",
        name="选必三 · 生物技术与工程",
        level=2,
        parent_code="BIO",
        description="发酵工程、细胞工程、基因工程、生物技术安全性与伦理",
        keywords=["选必三", "发酵", "细胞工程", "基因工程", "PCR", "伦理", "实验"]
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  BIO-C1: 必修一 · 分子与细胞
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第一章: 走近细胞 ─────────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="BIO-C1-CH1",
        name="走近细胞",
        level=3,
        parent_code="BIO-C1",
        description="细胞是生物体结构与生命活动的基本单位、细胞的多样性与统一性",
        keywords=["细胞", "显微镜", "原核", "真核", "细胞学说", "实验", "对照", "物质鉴定", "纸层析法"]
    ),
    KnowledgeTreeSeed(
        code="BIO-C1-CH1-01",
        name="细胞是生物体结构与生命活动的基本单位",
        level=4,
        parent_code="BIO-C1-CH1",
        description="生命活动离不开细胞、细胞是最基本的生命系统、生命系统的结构层次",
        keywords=["细胞", "生命系统", "组织", "器官", "系统", "个体"],
    ),
    KnowledgeTreeSeed(
        code="BIO-C1-CH1-02",
        name="细胞的多样性与统一性",
        level=4,
        parent_code="BIO-C1-CH1",
        description="原核细胞与真核细胞的区别、细胞学说的建立过程、显微镜的使用",
        keywords=["原核细胞", "真核细胞", "细胞学说", "施莱登", "施旺", "显微镜"],
    ),

    # ── 第二章: 组成细胞的分子 ───────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="BIO-C1-CH2",
        name="组成细胞的分子",
        level=3,
        parent_code="BIO-C1",
        description="组成细胞的元素和化合物、蛋白质、核酸、糖类脂质、无机物",
        keywords=["元素", "化合物", "蛋白质", "核酸", "糖类", "脂质", "DNA", "RNA", "无机盐", "水"]
    ),
    KnowledgeTreeSeed(
        code="BIO-C1-CH2-01",
        name="组成细胞的元素和化合物",
        level=4,
        parent_code="BIO-C1-CH2",
        description="大量元素与微量元素、水和无机盐的作用、细胞中主要化合物的种类",
        keywords=["大量元素", "微量元素", "水", "无机盐", "自由水", "结合水"],
    ),
    KnowledgeTreeSeed(
        code="BIO-C1-CH2-02",
        name="蛋白质",
        level=4,
        parent_code="BIO-C1-CH2",
        description="氨基酸的结构通式、脱水缩合、肽键、蛋白质结构多样性与功能多样性",
        keywords=["氨基酸", "肽键", "脱水缩合", "多肽", "蛋白质结构", "变性", "抗体", "酶"]
    ),
    KnowledgeTreeSeed(
        code="BIO-C1-CH2-03",
        name="核酸",
        level=4,
        parent_code="BIO-C1-CH2",
        description="DNA与RNA的结构、碱基互补配对、核酸是遗传信息的携带者",
        keywords=["DNA", "RNA", "核苷酸", "碱基互补配对", "双螺旋", "遗传信息", "mRNA", "tRNA"]
    ),
    KnowledgeTreeSeed(
        code="BIO-C1-CH2-04",
        name="糖类与脂质",
        level=4,
        parent_code="BIO-C1-CH2",
        description="单糖二糖多糖的种类与功能、脂肪磷脂固醇的功能",
        keywords=["葡萄糖", "蔗糖", "淀粉", "纤维素", "脂肪", "磷脂", "胆固醇"],
    ),

    # ── 第三章: 细胞的基本结构 ───────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="BIO-C1-CH3",
        name="细胞的基本结构",
        level=3,
        parent_code="BIO-C1",
        description="细胞膜的结构与功能、细胞器的分工合作、细胞核的结构与功能",
        keywords=["细胞膜", "细胞器", "细胞核", "生物膜系统"],
    ),
    KnowledgeTreeSeed(
        code="BIO-C1-CH3-01",
        name="细胞膜",
        level=4,
        parent_code="BIO-C1-CH3",
        description="流动镶嵌模型、磷脂双分子层、膜蛋白的种类与功能、细胞膜的选择透过性",
        keywords=["流动镶嵌模型", "磷脂双分子层", "膜蛋白", "选择透过性", "糖被"],
    ),
    KnowledgeTreeSeed(
        code="BIO-C1-CH3-02",
        name="细胞器",
        level=4,
        parent_code="BIO-C1-CH3",
        description="线粒体、叶绿体、内质网、高尔基体、核糖体、溶酶体、液泡、中心体的结构与功能",
        keywords=[
            "线粒体",
            "叶绿体",
            "内质网",
            "高尔基体",
            "核糖体",
            "溶酶体",
            "中心体",
            "原核",
            "流动镶嵌",
            "液泡",
            "生物膜系统",
            "真核",
            "细胞各部分结构",
            "细胞器",
            "细胞壁",
            "细胞核",
            "细胞膜",
        ]
    ),
    KnowledgeTreeSeed(
        code="BIO-C1-CH3-03",
        name="细胞核",
        level=4,
        parent_code="BIO-C1-CH3",
        description="细胞核的结构(核膜/核仁/染色质)、细胞核是遗传和代谢的控制中心",
        keywords=["细胞核", "核膜", "核仁", "染色质", "染色体", "遗传信息库"],
    ),

    # ── 第四章: 细胞的物质输入和输出 ─────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="BIO-C1-CH4",
        name="细胞的物质输入和输出",
        level=3,
        parent_code="BIO-C1",
        description="被动运输(自由扩散/协助扩散)、主动运输、胞吞胞吐",
        keywords=["被动运输", "主动运输", "自由扩散", "协助扩散", "胞吞", "胞吐"],
    ),
    KnowledgeTreeSeed(
        code="BIO-C1-CH4-01",
        name="被动运输",
        level=4,
        parent_code="BIO-C1-CH4",
        description="自由扩散(高浓度→低浓度/不需要载体)、协助扩散(需要通道蛋白或载体蛋白)、渗透作用",
        keywords=["自由扩散", "协助扩散", "渗透作用", "半透膜", "浓度差", "通道蛋白"],
    ),
    KnowledgeTreeSeed(
        code="BIO-C1-CH4-02",
        name="主动运输与胞吞胞吐",
        level=4,
        parent_code="BIO-C1-CH4",
        description="主动运输(低浓度→高浓度/需要载体和能量)、胞吞胞吐(大分子物质运输/依赖膜流动性)",
        keywords=["主动运输", "载体蛋白", "ATP", "胞吞", "胞吐", "膜流动性"],
    ),

    # ── 第五章: 细胞的能量供应和利用 ─────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="BIO-C1-CH5",
        name="细胞的能量供应和利用",
        level=3,
        parent_code="BIO-C1",
        description="酶与ATP、细胞呼吸、光合作用",
        keywords=["酶", "ATP", "细胞呼吸", "光合作用", "能量"],
    ),
    KnowledgeTreeSeed(
        code="BIO-C1-CH5-01",
        name="酶",
        level=4,
        parent_code="BIO-C1-CH5",
        description="酶的本质(蛋白质/RNA)、酶的特性(高效性/专一性/作用条件温和)、影响酶活性的因素",
        keywords=["酶", "高效性", "专一性", "最适温度", "最适pH", "活化能"],
    ),
    KnowledgeTreeSeed(
        code="BIO-C1-CH5-02",
        name="ATP",
        level=4,
        parent_code="BIO-C1-CH5",
        description="ATP的结构(A-P~P~P)、ATP与ADP的相互转化、ATP的来源与利用",
        keywords=["ATP", "ADP", "高能磷酸键", "腺苷", "能量通货", "ATP⇌ADP", "pH对酶影响", "活化能", "酶"]
    ),
    KnowledgeTreeSeed(
        code="BIO-C1-CH5-03",
        name="细胞呼吸",
        level=4,
        parent_code="BIO-C1-CH5",
        description="有氧呼吸三个阶段(糖酵解/柠檬酸循环/电子传递链)、无氧呼吸(产乳酸/产酒精)、呼吸作用的意义",
        keywords=[
            "有氧呼吸",
            "无氧呼吸",
            "糖酵解",
            "线粒体",
            "乳酸",
            "酒精",
            "CO2",
            "BTB",
            "CO2释放",
            "O2消耗",
            "乳酸发酵",
            "呼吸商",
            "呼吸方式",
            "溴麝香草酚蓝",
            "酒精发酵",
            "酵母菌",
        ]
    ),
    KnowledgeTreeSeed(
        code="BIO-C1-CH5-04",
        name="光合作用",
        level=4,
        parent_code="BIO-C1-CH5",
        description="光反应(类囊体膜/H2O光解/ATP和NADPH生成)、暗反应(C3还原/卡尔文循环)、影响光合速率的因素",
        keywords=["光合作用", "光反应", "暗反应", "类囊体", "叶绿体", "C3", "C5", "卡尔文循环", "C₃", "C₅"]
    ),

    # ── 第六章: 细胞的生命历程 ───────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="BIO-C1-CH6",
        name="细胞的生命历程",
        level=3,
        parent_code="BIO-C1",
        description="细胞增殖(有丝分裂)、细胞分化、细胞衰老与凋亡、细胞癌变",
        keywords=["有丝分裂", "分化", "衰老", "凋亡", "癌变"],
    ),
    KnowledgeTreeSeed(
        code="BIO-C1-CH6-01",
        name="细胞增殖",
        level=4,
        parent_code="BIO-C1-CH6",
        description="细胞周期、有丝分裂各时期特点(间期/前期/中期/后期/末期)、动植物细胞有丝分裂的异同",
        keywords=["细胞周期", "有丝分裂", "间期", "纺锤体", "着丝点", "染色体", "中期", "减数分裂", "前期", "后期", "末期"]
    ),
    KnowledgeTreeSeed(
        code="BIO-C1-CH6-02",
        name="细胞分化",
        level=4,
        parent_code="BIO-C1-CH6",
        description="细胞分化的概念(基因选择性表达)、细胞全能性、干细胞",
        keywords=["细胞分化", "基因选择性表达", "全能性", "干细胞", "持久性"],
    ),
    KnowledgeTreeSeed(
        code="BIO-C1-CH6-03",
        name="细胞的衰老与凋亡",
        level=4,
        parent_code="BIO-C1-CH6",
        description="细胞衰老的特征(端粒/色素积累)、细胞凋亡(基因控制的程序性死亡)与细胞坏死的区别",
        keywords=[
            "细胞衰老",
            "端粒",
            "细胞凋亡",
            "程序性死亡",
            "细胞坏死",
            "CiPSC",
            "体细胞",
            "全能性",
            "凋亡",
            "分化",
            "去分化",
            "坏死",
            "多潜能",
            "干细胞",
            "癌变",
            "衰老",
            "衰老细胞",
            "诱导",
        ]
    ),
    KnowledgeTreeSeed(
        code="BIO-C1-CH6-04",
        name="细胞的癌变",
        level=4,
        parent_code="BIO-C1-CH6",
        description="癌细胞的特征(无限增殖/形态改变/易转移)、致癌因子(物理/化学/病毒)、原癌基因与抑癌基因",
        keywords=["癌细胞", "原癌基因", "抑癌基因", "致癌因子", "无限增殖", "转移"],
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  BIO-C2: 必修二 · 遗传与进化
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第一章: 遗传因子的发现 ───────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="BIO-C2-CH1",
        name="遗传因子的发现",
        level=3,
        parent_code="BIO-C2",
        description="孟德尔的豌豆杂交实验(一)(分离定律)、孟德尔的豌豆杂交实验二(自由组合定律)",
        keywords=["孟德尔", "分离定律", "自由组合定律", "杂交", "基因型", "自由组合", "表现型"]
    ),
    KnowledgeTreeSeed(
        code="BIO-C2-CH1-01",
        name="孟德尔的豌豆杂交实验(一)",
        level=4,
        parent_code="BIO-C2-CH1",
        description="一对相对性状的杂交实验、分离定律(等位基因随同源染色体分离而分离)、假说—演绎法",
        keywords=["分离定律", "等位基因", "显性", "隐性", "3:1", "测交", "假说演绎法"],
    ),
    KnowledgeTreeSeed(
        code="BIO-C2-CH1-02",
        name="孟德尔的豌豆杂交实验(二)",
        level=4,
        parent_code="BIO-C2-CH1",
        description="两对相对性状的杂交实验、自由组合定律(非同源染色体上非等位基因自由组合)、9:3:3:1",
        keywords=["自由组合定律", "非等位基因", "9:3:3:1", "两对性状", "棋盘格"],
    ),

    # ── 第二章: 基因和染色体的关系 ───────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="BIO-C2-CH2",
        name="基因和染色体的关系",
        level=3,
        parent_code="BIO-C2",
        description="减数分裂和受精作用、基因在染色体上、伴性遗传",
        keywords=["减数分裂", "受精", "染色体", "伴性遗传"],
    ),
    KnowledgeTreeSeed(
        code="BIO-C2-CH2-01",
        name="减数分裂和受精作用",
        level=4,
        parent_code="BIO-C2-CH2",
        description="减数分裂过程(减I同源染色体分离/减II姐妹染色单体分离)、配子形成、受精作用",
        keywords=["减数分裂", "同源染色体", "联会", "四分体", "交叉互换", "受精作用", "受精"]
    ),
    KnowledgeTreeSeed(
        code="BIO-C2-CH2-02",
        name="基因在染色体上",
        level=4,
        parent_code="BIO-C2-CH2",
        description="萨顿假说(基因在染色体上)、摩尔根果蝇实验(白眼基因在X染色体上)、基因与染色体的平行关系",
        keywords=["萨顿假说", "摩尔根", "果蝇", "基因", "染色体", "平行关系", "伴X", "伴Y"]
    ),
    KnowledgeTreeSeed(
        code="BIO-C2-CH2-03",
        name="伴性遗传",
        level=4,
        parent_code="BIO-C2-CH2",
        description="X染色体显性/隐性遗传、Y染色体遗传、伴性遗传的特点与应用(色盲/血友病)",
        keywords=["伴性遗传", "X染色体", "色盲", "血友病", "交叉遗传"],
    ),

    # ── 第三章: 基因的本质 ───────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="BIO-C2-CH3",
        name="基因的本质",
        level=3,
        parent_code="BIO-C2",
        description="DNA是主要的遗传物质、DNA的结构与复制、基因是有遗传效应的DNA片段",
        keywords=["DNA", "遗传物质", "双螺旋", "复制", "基因"],
    ),
    KnowledgeTreeSeed(
        code="BIO-C2-CH3-01",
        name="DNA是主要的遗传物质",
        level=4,
        parent_code="BIO-C2-CH3",
        description="肺炎链球菌转化实验(格里菲斯/艾弗里)、噬菌体侵染细菌实验(赫尔希和蔡斯)",
        keywords=["转化实验", "噬菌体", "放射性同位素标记", "格里菲斯", "艾弗里"],
    ),
    KnowledgeTreeSeed(
        code="BIO-C2-CH3-02",
        name="DNA的结构",
        level=4,
        parent_code="BIO-C2-CH3",
        description="DNA双螺旋结构模型(沃森和克里克)、碱基互补配对(A-T/G-C)、DNA的多样性与特异性",
        keywords=["双螺旋", "碱基互补配对", "脱氧核苷酸", "磷酸二酯键", "沃森", "克里克"],
    ),
    KnowledgeTreeSeed(
        code="BIO-C2-CH3-03",
        name="DNA的复制",
        level=4,
        parent_code="BIO-C2-CH3",
        description="半保留复制、解旋→合成子链→重新螺旋、DNA聚合酶、复制的意义",
        keywords=["半保留复制", "DNA聚合酶", "解旋酶", "引物", "复制叉", "DNA复制", "半保留"]
    ),
    KnowledgeTreeSeed(
        code="BIO-C2-CH3-04",
        name="基因是有遗传效应的DNA片段",
        level=4,
        parent_code="BIO-C2-CH3",
        description="基因与DNA的关系、基因的碱基排列顺序蕴含遗传信息、基因与性状的关系",
        keywords=["基因", "遗传效应", "碱基序列", "遗传信息", "DNA片段"],
    ),

    # ── 第四章: 基因的表达 ───────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="BIO-C2-CH4",
        name="基因的表达",
        level=3,
        parent_code="BIO-C2",
        description="基因指导蛋白质的合成(转录与翻译)、基因表达与性状的关系",
        keywords=["转录", "翻译", "密码子", "中心法则", "表达", "DNA复制", "半保留复制"]
    ),
    KnowledgeTreeSeed(
        code="BIO-C2-CH4-01",
        name="基因指导蛋白质的合成",
        level=4,
        parent_code="BIO-C2-CH4",
        description="转录(DNA→mRNA)、翻译(mRNA→蛋白质/核糖体/tRNA/密码子与反密码子)、中心法则",
        keywords=["转录", "翻译", "mRNA", "tRNA", "密码子", "反密码子", "核糖体", "中心法则"],
    ),
    KnowledgeTreeSeed(
        code="BIO-C2-CH4-02",
        name="基因表达与性状的关系",
        level=4,
        parent_code="BIO-C2-CH4",
        description="基因通过控制蛋白质的结构和酶的合成控制性状、基因与性状不是简单的一一对应关系",
        keywords=["基因表达", "蛋白质结构", "酶", "性状", "基因型", "表现型"],
    ),

    # ── 第五章: 基因突变及其他变异 ───────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="BIO-C2-CH5",
        name="基因突变及其他变异",
        level=3,
        parent_code="BIO-C2",
        description="基因突变与基因重组、染色体变异、人类遗传病",
        keywords=["基因突变", "基因重组", "染色体变异", "人类遗传病", "变异", "多倍体"]
    ),
    KnowledgeTreeSeed(
        code="BIO-C2-CH5-01",
        name="基因突变与基因重组",
        level=4,
        parent_code="BIO-C2-CH5",
        description="基因突变(碱基替换/增添/缺失)的特点(普遍/随机/低频/不定向)、基因重组的类型与意义",
        keywords=["基因突变", "碱基替换", "基因重组", "交叉互换", "随机性", "不定向性"],
    ),
    KnowledgeTreeSeed(
        code="BIO-C2-CH5-02",
        name="染色体变异",
        level=4,
        parent_code="BIO-C2-CH5",
        description="染色体结构变异(缺失/重复/倒位/易位)、染色体数目变异(个别/整倍体)、多倍体与单倍体",
        keywords=["染色体变异", "缺失", "重复", "倒位", "易位", "多倍体", "单倍体", "秋水仙素"],
    ),
    KnowledgeTreeSeed(
        code="BIO-C2-CH5-03",
        name="人类遗传病",
        level=4,
        parent_code="BIO-C2-CH5",
        description="单基因遗传病/多基因遗传病/染色体异常遗传病、遗传病的监测与预防、遗传咨询",
        keywords=["人类遗传病", "单基因", "多基因", "染色体异常", "遗传咨询", "基因诊断"],
    ),

    # ── 第六章: 生物的进化 ───────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="BIO-C2-CH6",
        name="生物的进化",
        level=3,
        parent_code="BIO-C2",
        description="共同由来的证据、自然选择与适应、种群基因频率的变化、协同进化与生物多样性",
        keywords=["进化", "自然选择", "基因频率", "物种形成", "协同进化", "隔离"]
    ),
    KnowledgeTreeSeed(
        code="BIO-C2-CH6-01",
        name="生物有共同祖先的证据",
        level=4,
        parent_code="BIO-C2-CH6",
        description="化石证据、比较解剖学证据(同源器官)、胚胎学证据、细胞和分子水平的证据",
        keywords=["化石", "同源器官", "比较解剖", "胚胎发育", "分子生物学"],
    ),
    KnowledgeTreeSeed(
        code="BIO-C2-CH6-02",
        name="自然选择与适应",
        level=4,
        parent_code="BIO-C2-CH6",
        description="适应的普遍性与相对性、达尔文自然选择学说(过度繁殖/生存斗争/遗传变异/适者生存)",
        keywords=["自然选择", "适应", "生存斗争", "适者生存", "达尔文"],
    ),
    KnowledgeTreeSeed(
        code="BIO-C2-CH6-03",
        name="种群基因组成的变化",
        level=4,
        parent_code="BIO-C2-CH6",
        description="种群是进化的基本单位、基因频率与基因型频率、Hardy-Weinberg平衡、影响基因频率的因素",
        keywords=["种群", "基因频率", "基因型频率", "Hardy-Weinberg", "突变", "迁移"],
    ),
    KnowledgeTreeSeed(
        code="BIO-C2-CH6-04",
        name="协同进化与生物多样性的形成",
        level=4,
        parent_code="BIO-C2-CH6",
        description="协同进化(物种间/生物与无机环境)、物种形成(地理隔离→生殖隔离)、生物多样性三个层次",
        keywords=["协同进化", "物种形成", "地理隔离", "生殖隔离", "生物多样性"],
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  BIO-S1: 选必一 · 稳态与调节
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第一章: 人体的内环境与稳态 ───────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="BIO-S1-CH1",
        name="人体的内环境与稳态",
        level=3,
        parent_code="BIO-S1",
        description="细胞生活的环境(内环境)、内环境的稳态",
        keywords=["内环境", "稳态", "血浆", "组织液", "淋巴", "pH"]
    ),
    KnowledgeTreeSeed(
        code="BIO-S1-CH1-01",
        name="细胞生活的环境",
        level=4,
        parent_code="BIO-S1-CH1",
        description="体液的组成(细胞内液/细胞外液)、内环境(血浆/组织液/淋巴)的成分与理化性质",
        keywords=["体液", "细胞内液", "细胞外液", "血浆", "组织液", "淋巴", "渗透压"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S1-CH1-02",
        name="内环境的稳态",
        level=4,
        parent_code="BIO-S1-CH1",
        description="稳态的概念(化学成分和理化性质相对稳定)、稳态的调节机制(神经-体液-免疫调节网络)",
        keywords=["稳态", "相对稳定", "调节机制", "神经-体液-免疫", "反馈调节"],
    ),

    # ── 第二章: 神经调节 ─────────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="BIO-S1-CH2",
        name="神经调节",
        level=3,
        parent_code="BIO-S1",
        description="神经调节的结构基础、基本方式、兴奋的产生与传导、分级调节、人脑的高级功能",
        keywords=["神经", "反射", "突触", "兴奋", "传导", "大脑皮层", "神经递质"]
    ),
    KnowledgeTreeSeed(
        code="BIO-S1-CH2-01",
        name="神经调节的结构基础",
        level=4,
        parent_code="BIO-S1-CH2",
        description="神经元的结构(胞体/树突/轴突)、神经系统的组成(中枢/外周)、反射弧的组成",
        keywords=["神经元", "胞体", "轴突", "树突", "中枢神经", "外周神经", "反射弧"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S1-CH2-02",
        name="神经调节的基本方式",
        level=4,
        parent_code="BIO-S1-CH2",
        description="反射的概念(非条件反射/条件反射)、反射弧(感受器→传入神经→神经中枢→传出神经→效应器)",
        keywords=["反射", "非条件反射", "条件反射", "反射弧", "感受器", "效应器"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S1-CH2-03",
        name="兴奋的产生与传导",
        level=4,
        parent_code="BIO-S1-CH2",
        description="静息电位(外正内负/K+外流)和动作电位(外负内正/Na+内流)、神经冲动的传导与突触传递",
        keywords=["静息电位", "动作电位", "K+外流", "Na+内流", "突触", "神经递质", "突触间隙"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S1-CH2-04",
        name="神经系统的分级调节",
        level=4,
        parent_code="BIO-S1-CH2",
        description="大脑皮层(高级中枢)、脑干(生命中枢)、脊髓(低级中枢)的分级调节关系",
        keywords=["大脑皮层", "脑干", "脊髓", "分级调节", "高级中枢", "低级中枢"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S1-CH2-05",
        name="人脑的高级功能",
        level=4,
        parent_code="BIO-S1-CH2",
        description="语言中枢(S区运动性/W区书写/V区视觉/H区听觉)、学习与记忆、情绪",
        keywords=["语言中枢", "S区", "W区", "V区", "H区", "学习", "记忆"],
    ),

    # ── 第三章: 体液调节 ─────────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="BIO-S1-CH3",
        name="体液调节",
        level=3,
        parent_code="BIO-S1",
        description="激素与内分泌腺、激素调节的过程、体液调节与神经调节的关系",
        keywords=["激素", "内分泌", "反馈调节", "血糖", "甲状腺", "胰岛素", "胰高血糖素"]
    ),
    KnowledgeTreeSeed(
        code="BIO-S1-CH3-01",
        name="激素与内分泌腺",
        level=4,
        parent_code="BIO-S1-CH3",
        description="人体主要内分泌腺(下丘脑/垂体/甲状腺/肾上腺/胰岛/性腺)及其分泌的激素",
        keywords=["内分泌腺", "下丘脑", "垂体", "甲状腺", "胰岛素", "胰高血糖素", "肾上腺素"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S1-CH3-02",
        name="激素调节的过程",
        level=4,
        parent_code="BIO-S1-CH3",
        description="血糖调节(胰岛素降血糖/胰高血糖素升血糖)、甲状腺激素的分级调节(下丘脑-垂体-甲状腺轴)",
        keywords=["血糖调节", "胰岛素", "胰高血糖素", "分级调节", "反馈调节", "甲状腺激素"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S1-CH3-03",
        name="体液调节与神经调节的关系",
        level=4,
        parent_code="BIO-S1-CH3",
        description="神经-体液调节实例(体温调节/水盐调节)、两种调节方式的协调配合",
        keywords=["神经-体液调节", "体温调节", "水盐调节", "协调配合"],
    ),

    # ── 第四章: 免疫调节 ─────────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="BIO-S1-CH4",
        name="免疫调节",
        level=3,
        parent_code="BIO-S1",
        description="免疫系统的组成与功能、特异性免疫、免疫失调、免疫学应用",
        keywords=["免疫", "抗体", "抗原", "T细胞", "B细胞", "疫苗", "HIV", "过敏"]
    ),
    KnowledgeTreeSeed(
        code="BIO-S1-CH4-01",
        name="免疫系统的组成与功能",
        level=4,
        parent_code="BIO-S1-CH4",
        description="免疫器官(骨髓/胸腺/脾/淋巴结)、免疫细胞(淋巴细胞/吞噬细胞)、免疫活性物质(抗体/淋巴因子)",
        keywords=["免疫器官", "免疫细胞", "淋巴细胞", "吞噬细胞", "抗体", "淋巴因子"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S1-CH4-02",
        name="特异性免疫",
        level=4,
        parent_code="BIO-S1-CH4",
        description="体液免疫(B细胞→浆细胞→抗体)、细胞免疫(T细胞→效应T细胞)、免疫记忆与二次免疫",
        keywords=["体液免疫", "细胞免疫", "B细胞", "浆细胞", "效应T细胞", "二次免疫", "记忆细胞"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S1-CH4-03",
        name="免疫失调与免疫学应用",
        level=4,
        parent_code="BIO-S1-CH4",
        description="免疫过强(过敏反应/自身免疫病)、免疫缺陷(HIV/AIDS)、疫苗/器官移植/免疫治疗",
        keywords=["过敏反应", "自身免疫病", "HIV", "AIDS", "疫苗", "器官移植", "免疫抑制剂"],
    ),

    # ── 第五章: 植物生命活动的调节 ───────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="BIO-S1-CH5",
        name="植物生命活动的调节",
        level=3,
        parent_code="BIO-S1",
        description="植物生长素、其他植物激素、植物生长调节剂的应用、环境因素参与调节",
        keywords=["生长素", "赤霉素", "乙烯", "脱落酸", "植物激素"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S1-CH5-01",
        name="植物生长素",
        level=4,
        parent_code="BIO-S1-CH5",
        description="生长素的发现(达尔文/詹森/拜尔/温特)、产生部位与运输(极性运输)、作用特点(两重性)",
        keywords=["生长素", "极性运输", "两重性", "向光性", "顶端优势", "温特"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S1-CH5-02",
        name="其他植物激素",
        level=4,
        parent_code="BIO-S1-CH5",
        description="赤霉素(促进伸长)、细胞分裂素(促进分裂)、脱落酸(抑制生长/促进脱落)、乙烯(促进成熟)",
        keywords=["赤霉素", "细胞分裂素", "脱落酸", "乙烯", "协同", "拮抗"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S1-CH5-03",
        name="植物生长调节剂的应用",
        level=4,
        parent_code="BIO-S1-CH5",
        description="植物生长调节剂的概念(人工合成)、应用实例(催熟/除草/促进生根)、合理使用",
        keywords=["生长调节剂", "人工合成", "催熟", "除草剂", "合理使用"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S1-CH5-04",
        name="环境因素参与调节植物的生命活动",
        level=4,
        parent_code="BIO-S1-CH5",
        description="光(光敏色素)、温度(春化作用)、重力对植物生长发育的调节",
        keywords=["光敏色素", "春化作用", "重力", "环境因素", "光周期"],
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  BIO-S2: 选必二 · 生物与环境
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第一章: 种群及其动态 ─────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="BIO-S2-CH1",
        name="种群及其动态",
        level=3,
        parent_code="BIO-S2",
        description="种群的数量特征、种群数量的变化、影响种群数量变化的因素",
        keywords=["种群", "数量特征", "增长模型", "K值", "J型", "S型", "出生率", "死亡率"]
    ),
    KnowledgeTreeSeed(
        code="BIO-S2-CH1-01",
        name="种群的数量特征",
        level=4,
        parent_code="BIO-S2-CH1",
        description="种群密度(最基本的数量特征)、出生率和死亡率、迁入率和迁出率、年龄结构、性别比例",
        keywords=["种群密度", "出生率", "死亡率", "年龄结构", "性别比例", "样方法", "标志重捕法"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S2-CH1-02",
        name="种群数量的变化",
        level=4,
        parent_code="BIO-S2-CH1",
        description="J型增长模型(理想条件/Nt=N0λt)、S型增长模型(资源有限/K值)、K/2的应用",
        keywords=["J型增长", "S型增长", "K值", "K/2", "环境容纳量", "增长速率"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S2-CH1-03",
        name="影响种群数量变化的因素",
        level=4,
        parent_code="BIO-S2-CH1",
        description="密度制约因素(食物/天敌/传染病)、非密度制约因素(气候/自然灾害)、种群研究的应用",
        keywords=["密度制约", "非密度制约", "天敌", "传染病", "气候"],
    ),

    # ── 第二章: 群落及其演替 ─────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="BIO-S2-CH2",
        name="群落及其演替",
        level=3,
        parent_code="BIO-S2",
        description="群落的结构、群落的主要类型、群落的演替",
        keywords=["群落", "丰富度", "种间关系", "演替"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S2-CH2-01",
        name="群落的结构",
        level=4,
        parent_code="BIO-S2-CH2",
        description="群落的物种组成(丰富度)、种间关系(捕食/竞争/寄生/互利共生)、群落的空间结构(垂直/水平)",
        keywords=["丰富度", "种间关系", "捕食", "竞争", "互利共生", "垂直结构", "水平结构", "演替", "群落"]
    ),
    KnowledgeTreeSeed(
        code="BIO-S2-CH2-02",
        name="群落的主要类型",
        level=4,
        parent_code="BIO-S2-CH2",
        description="荒漠/草原/森林/湿地等群落类型的特征、群落类型的决定因素(水分/温度)",
        keywords=["荒漠", "草原", "森林", "湿地", "群落类型"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S2-CH2-03",
        name="群落的演替",
        level=4,
        parent_code="BIO-S2-CH2",
        description="初生演替(从无到有/裸岩→地衣→苔藓→草本→灌木→乔木)、次生演替(保留土壤)、人类活动对演替的影响",
        keywords=["初生演替", "次生演替", "裸岩", "地衣", "顶级群落", "人类活动"],
    ),

    # ── 第三章: 生态系统及其稳定性 ───────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="BIO-S2-CH3",
        name="生态系统及其稳定性",
        level=3,
        parent_code="BIO-S2",
        description="生态系统的结构、能量流动、物质循环、信息传递、稳定性",
        keywords=["生态系统", "能量流动", "物质循环", "信息传递", "稳定性"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S2-CH3-01",
        name="生态系统的结构",
        level=4,
        parent_code="BIO-S2-CH3",
        description="生态系统的组成成分(生产者/消费者/分解者/非生物的物质和能量)、食物链与食物网",
        keywords=["生产者", "消费者", "分解者", "食物链", "食物网", "营养级", "生态系统", "碳循环", "能量流动"]
    ),
    KnowledgeTreeSeed(
        code="BIO-S2-CH3-02",
        name="生态系统的能量流动",
        level=4,
        parent_code="BIO-S2-CH3",
        description="能量流动的过程(同化/呼吸/分解)、能量流动的特点(单向流动/逐级递减/10%-20%)、能量金字塔",
        keywords=["能量流动", "同化量", "单向流动", "逐级递减", "能量金字塔", "10%-20%"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S2-CH3-03",
        name="生态系统的物质循环",
        level=4,
        parent_code="BIO-S2-CH3",
        description="物质循环的概念(全球性/循环性)、碳循环(CO2/有机物/碳酸盐)、能量流动与物质循环的关系",
        keywords=["物质循环", "碳循环", "CO2", "光合作用", "分解作用", "全球性"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S2-CH3-04",
        name="生态系统的信息传递",
        level=4,
        parent_code="BIO-S2-CH3",
        description="物理信息(光/声/温度)、化学信息(性外激素/气味)、行为信息、信息传递在农业生产中的应用",
        keywords=["信息传递", "物理信息", "化学信息", "行为信息", "信息素"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S2-CH3-05",
        name="生态系统的稳定性",
        level=4,
        parent_code="BIO-S2-CH3",
        description="抵抗力稳定性(抵抗干扰/保持原状)、恢复力稳定性(遭到破坏/恢复原状)、自我调节能力(负反馈)",
        keywords=["抵抗力稳定性", "恢复力稳定性", "自我调节", "负反馈", "物种多样性"],
    ),

    # ── 第四章: 人与环境 ─────────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="BIO-S2-CH4",
        name="人与环境",
        level=3,
        parent_code="BIO-S2",
        description="人类活动对生态环境的影响、生态环境的保护",
        keywords=["环境问题", "生物多样性", "可持续发展", "保护"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S2-CH4-01",
        name="人类活动对生态环境的影响",
        level=4,
        parent_code="BIO-S2-CH4",
        description="全球性生态环境问题(全球气候变化/臭氧层破坏/酸雨/荒漠化/水资源短缺/生物多样性丧失)",
        keywords=["全球气候变化", "臭氧层", "酸雨", "荒漠化", "水污染"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S2-CH4-02",
        name="生态环境的保护",
        level=4,
        parent_code="BIO-S2-CH4",
        description="生物多样性的保护(就地保护/易地保护)、可持续发展(生态工程)、生态文明建设",
        keywords=["生物多样性", "就地保护", "易地保护", "自然保护区", "可持续发展", "生态工程", "温室效应", "酸雨"]
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  BIO-S3: 选必三 · 生物技术与工程
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第一章: 发酵工程 ─────────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="BIO-S3-CH1",
        name="发酵工程",
        level=3,
        parent_code="BIO-S3",
        description="传统发酵技术(果酒/果醋/腐乳/泡菜)、微生物的培养与应用、发酵工程及其应用",
        keywords=["发酵", "微生物", "培养基", "灭菌", "发酵罐"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S3-CH1-01",
        name="传统发酵技术的应用",
        level=4,
        parent_code="BIO-S3-CH1",
        description="果酒制作(酵母菌/无氧)、果醋制作(醋酸菌/有氧)、腐乳制作(毛霉)、泡菜制作(乳酸菌)",
        keywords=["果酒", "果醋", "腐乳", "泡菜", "酵母菌", "醋酸菌", "乳酸菌"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S3-CH1-02",
        name="微生物的培养与应用",
        level=4,
        parent_code="BIO-S3-CH1",
        description="培养基的配制(碳源/氮源/水/无机盐)、灭菌与消毒、微生物的计数(稀释涂布/显微镜直接计数)",
        keywords=["培养基", "碳源", "氮源", "灭菌", "消毒", "稀释涂布", "菌落"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S3-CH1-03",
        name="发酵工程及其应用",
        level=4,
        parent_code="BIO-S3-CH1",
        description="发酵工程的基本环节(菌种选育→培养基配制→灭菌→接种→发酵→分离提纯)、发酵工程的应用",
        keywords=["发酵工程", "菌种选育", "发酵罐", "分离提纯", "工业化生产"],
    ),

    # ── 第二章: 细胞工程 ─────────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="BIO-S3-CH2",
        name="细胞工程",
        level=3,
        parent_code="BIO-S3",
        description="植物细胞工程(组织培养/体细胞杂交)、动物细胞工程(细胞培养/核移植/细胞融合)",
        keywords=["细胞工程", "组织培养", "体细胞杂交", "核移植", "单克隆抗体", "动物细胞培养"]
    ),
    KnowledgeTreeSeed(
        code="BIO-S3-CH2-01",
        name="植物细胞工程",
        level=4,
        parent_code="BIO-S3-CH2",
        description="植物组织培养(脱分化→再分化)、植物体细胞杂交(原生质体融合)、微型繁殖与人工种子",
        keywords=["植物组织培养", "脱分化", "再分化", "愈伤组织", "体细胞杂交", "原生质体"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S3-CH2-02",
        name="动物细胞工程",
        level=4,
        parent_code="BIO-S3-CH2",
        description="动物细胞培养(原代/传代)、动物体细胞核移植(克隆)、动物细胞融合与单克隆抗体",
        keywords=["动物细胞培养", "核移植", "克隆", "细胞融合", "单克隆抗体", "杂交瘤细胞"],
    ),

    # ── 第三章: 基因工程 ─────────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="BIO-S3-CH3",
        name="基因工程",
        level=3,
        parent_code="BIO-S3",
        description="基因工程的基本工具、基因工程的基本操作程序、基因工程的应用、蛋白质工程",
        keywords=["基因工程", "限制酶", "DNA连接酶", "载体", "PCR", "蛋白质工程", "电泳", "质粒"]
    ),
    KnowledgeTreeSeed(
        code="BIO-S3-CH3-01",
        name="基因工程的基本工具",
        level=4,
        parent_code="BIO-S3-CH3",
        description="限制性内切酶(识别并切割特定序列)、DNA连接酶(连接磷酸二酯键)、载体(质粒/噬菌体/动植物病毒)",
        keywords=["限制酶", "DNA连接酶", "质粒", "载体", "黏性末端", "平末端"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S3-CH3-02",
        name="基因工程的基本操作程序",
        level=4,
        parent_code="BIO-S3-CH3",
        description="目的基因的获取(化学合成/基因组文库/cDNA文库/PCR)、基因表达载体的构建、转化与检测",
        keywords=["目的基因", "PCR", "基因表达载体", "转化", "农杆菌", "基因枪"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S3-CH3-03",
        name="基因工程的应用与蛋白质工程",
        level=4,
        parent_code="BIO-S3-CH3",
        description="基因工程在农业(抗虫棉)/医药(胰岛素)/环保中的应用、蛋白质工程(改造蛋白质/基因修饰)",
        keywords=["基因工程应用", "转基因", "抗虫棉", "基因药物", "蛋白质工程"],
    ),

    # ── 第四章: 生物技术的安全性与伦理 ───────────────────────────────────────────
    KnowledgeTreeSeed(
        code="BIO-S3-CH4",
        name="生物技术的安全性与伦理",
        level=3,
        parent_code="BIO-S3",
        description="转基因产品的安全性、生物武器、生物技术的伦理问题",
        keywords=["安全性", "伦理", "转基因", "生物武器", "克隆人"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S3-CH4-01",
        name="转基因产品的安全性",
        level=4,
        parent_code="BIO-S3-CH4",
        description="转基因生物与食品安全、转基因生物与生物安全、理性看待转基因技术",
        keywords=["转基因安全", "食品安全", "生物安全", "标识制度"],
    ),
    KnowledgeTreeSeed(
        code="BIO-S3-CH4-02",
        name="生物技术的伦理问题",
        level=4,
        parent_code="BIO-S3-CH4",
        description="克隆人的伦理争议、设计试管婴儿的伦理争议、基因检测与隐私、生物武器的禁止",
        keywords=["克隆人", "试管婴儿", "基因检测", "生物武器", "伦理"],
    ),
]
