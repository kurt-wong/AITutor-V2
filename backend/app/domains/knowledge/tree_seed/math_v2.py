"""
数学知识树 V2 (新课标课程结构对齐)

课程模块结构 (5 册):
  MATH-C1  必修第一册   (集合/逻辑/不等式/函数/指数对数/三角函数)
  MATH-C2  必修第二册   (平面向量/复数/立体几何/统计/概率)
  MATH-C3  选必第一册   (空间向量/直线与圆/圆锥曲线)
  MATH-C4  选必第二册   (数列/导数)
  MATH-C5  选必第三册   (计数原理/随机变量/统计分析)

与 math.py (MATH-ANA / MATH-ALG / MATH-GEO / MATH-STAT) 并行存在，
不产生 code 冲突。

编码体系:
  L2: MATH-C{册}            e.g. MATH-C1
  L3: MATH-C{册}-CH{章}     e.g. MATH-C1-CH1
  L4: MATH-C{册}-CH{章}-{节} e.g. MATH-C1-CH1-01
"""

from __future__ import annotations

from app.domains.knowledge.tree_seed.types import KnowledgeTreeSeed

MATH_KNOWLEDGE_TREE_V2: list[KnowledgeTreeSeed] = [

    # ═══════════════════════════════════════════════════════════════════════════════
    #  Level 2: 课程模块 (5 册)
    # ═══════════════════════════════════════════════════════════════════════════════

    KnowledgeTreeSeed(
        code="MATH-C1",
        name="必修第一册",
        level=2,
        parent_code="MATH",
        description="集合与常用逻辑用语、一元二次函数方程和不等式、函数的概念与性质、指数函数与对数函数、三角函数",
        keywords=["必修一", "集合", "函数", "指数", "对数", "三角函数", "不等式", "导数", "数列", "极限"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C2",
        name="必修第二册",
        level=2,
        parent_code="MATH",
        description="平面向量及其应用、复数、立体几何初步、统计、概率",
        keywords=["必修二", "向量", "复数", "立体几何", "统计", "概率", "几何", "分布", "圆锥曲线", "方差", "期望", "立体", "解析"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C3",
        name="选必第一册",
        level=2,
        parent_code="MATH",
        description="空间向量与立体几何、直线和圆的方程、圆锥曲线的方程",
        keywords=["选必一", "空间向量", "直线", "圆", "圆锥曲线", "椭圆", "双曲线", "抛物线"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C4",
        name="选必第二册",
        level=2,
        parent_code="MATH",
        description="数列、导数及其应用",
        keywords=["选必二", "数列", "等差", "等比", "导数", "微积分"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C5",
        name="选必第三册",
        level=2,
        parent_code="MATH",
        description="计数原理、随机变量及其分布、成对数据的统计分析",
        keywords=["选必三", "计数", "排列", "组合", "二项式", "随机变量", "回归", "独立性检验", "不等式", "复数", "逻辑", "集合"]
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  MATH-C1: 必修第一册
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第一章: 集合与常用逻辑用语 ────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="MATH-C1-CH1",
        name="集合与常用逻辑用语",
        level=3,
        parent_code="MATH-C1",
        description="集合的概念与运算、充分必要条件、全称量词与存在量词",
        keywords=["集合", "逻辑", "充分条件", "必要条件", "量词", "充要条件", "全称量词", "命题", "存在量词"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C1-CH1-01",
        name="集合的概念",
        level=4,
        parent_code="MATH-C1-CH1",
        description="集合的含义与表示、元素与集合的关系(属于/不属于)、常用数集(N/Z/Q/R)、列举法与描述法",
        keywords=["集合", "元素", "属于", "不属于", "自然数集", "整数集", "有理数集", "实数集",
                  "列举法", "描述法", "确定性", "互异性", "无序性"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C1-CH1-02",
        name="集合间的基本关系",
        level=4,
        parent_code="MATH-C1-CH1",
        description="子集、真子集、集合相等、空集、Venn图表示集合关系",
        keywords=["子集", "真子集", "集合相等", "空集", "包含", "Venn图", "⊆", "⊂", "∅"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C1-CH1-03",
        name="集合的基本运算",
        level=4,
        parent_code="MATH-C1-CH1",
        description="交集、并集、补集的定义与运算性质、De Morgan定律",
        keywords=["交集", "并集", "补集", "∩", "∪", "∁", "De Morgan", "全集", "Venn图", "元素", "子集", "集合"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C1-CH1-04",
        name="充分条件与必要条件",
        level=4,
        parent_code="MATH-C1-CH1",
        description="充分条件、必要条件、充要条件的判定、命题的四种形式(原/逆/否/逆否)",
        keywords=["充分条件", "必要条件", "充要条件", "充分不必要", "必要不充分",
                  "原命题", "逆命题", "否命题", "逆否命题"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C1-CH1-05",
        name="全称量词与存在量词",
        level=4,
        parent_code="MATH-C1-CH1",
        description="全称量词(∀)与存在量词(∃)的含义、全称命题与特称命题的否定",
        keywords=["全称量词", "存在量词", "∀", "∃", "全称命题", "特称命题", "命题否定"],
    ),

    # ── 第二章: 一元二次函数方程和不等式 ──────────────────────────────────────────
    KnowledgeTreeSeed(
        code="MATH-C1-CH2",
        name="一元二次函数方程和不等式",
        level=3,
        parent_code="MATH-C1",
        description="等式性质与不等式性质、基本不等式、二次函数与一元二次方程不等式",
        keywords=["不等式", "等式", "基本不等式", "二次函数", "一元二次方程"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C1-CH2-01",
        name="等式性质与不等式性质",
        level=4,
        parent_code="MATH-C1-CH2",
        description="等式的基本性质、不等式的基本性质(传递性/加法/乘法/可乘性)、比较法(作差/作商)",
        keywords=["等式性质", "不等式性质", "传递性", "作差法", "作商法", "可加性", "可乘性", "作差", "比较法"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C1-CH2-02",
        name="基本不等式",
        level=4,
        parent_code="MATH-C1-CH2",
        description="a²+b²≥2ab、(a+b)/2≥√(ab) (a,b≥0)、一正二定三相等、求最值应用",
        keywords=["基本不等式", "均值不等式", "算术平均", "几何平均", "a²+b²≥2ab", "一正二定三相等", "最值", "不等式", "二次不等式", "线性规划"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C1-CH2-03",
        name="二次函数与一元二次方程不等式",
        level=4,
        parent_code="MATH-C1-CH2",
        description="二次函数图像与性质、一元二次方程的根(判别式Δ)、一元二次不等式的解法、三个二次的关系",
        keywords=["二次函数", "一元二次方程", "一元二次不等式", "判别式Δ", "韦达定理", "开口方向", "顶点", "三个二次", "二次不等式", "区间", "含参"]
    ),

    # ── 第三章: 函数的概念与性质 ──────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="MATH-C1-CH3",
        name="函数的概念与性质",
        level=3,
        parent_code="MATH-C1",
        description="函数的概念、表示法、单调性、奇偶性、幂函数",
        keywords=["函数", "函数单调性", "定义域", "值域", "单调性", "奇偶性", "幂函数", "周期性", "对称性"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C1-CH3-01",
        name="函数的概念",
        level=4,
        parent_code="MATH-C1-CH3",
        description="函数的定义(定义域/值域/对应法则)、函数的三要素、区间表示法",
        keywords=["函数", "定义域", "值域", "对应法则", "三要素", "区间", "开区间", "闭区间", "图像法", "映射", "解析式"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C1-CH3-02",
        name="函数的表示法",
        level=4,
        parent_code="MATH-C1-CH3",
        description="解析法、列表法、图像法、分段函数、映射的概念",
        keywords=["解析法", "列表法", "图像法", "分段函数", "映射", "|x|", "分类讨论", "绝对值"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C1-CH3-03",
        name="函数的单调性",
        level=4,
        parent_code="MATH-C1-CH3",
        description="增函数与减函数的定义、单调区间的判断方法(定义法/图像法)、复合函数单调性",
        keywords=["函数单调性", "单调性", "增函数", "减函数", "单调区间", "单调递增", "单调递减", "定义法", "f'(x)>0"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C1-CH3-04",
        name="函数的奇偶性",
        level=4,
        parent_code="MATH-C1-CH3",
        description="奇函数与偶函数的定义、f(-x)=f(x)与f(-x)=-f(x)、奇偶性判断、图像对称性",
        keywords=["奇函数", "偶函数", "奇偶性", "f(-x)", "关于原点对称", "关于y轴对称", "对称中心", "对称轴"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C1-CH3-05",
        name="幂函数",
        level=4,
        parent_code="MATH-C1-CH3",
        description="幂函数y=x^α的定义、五类基本幂函数(y=x, x², x³, √x, 1/x)的图像与性质",
        keywords=[
            "幂函数",
            "y=x^α",
            "y=x²",
            "y=x³",
            "y=√x",
            "y=1/x",
            "图像",
            "af(x)",
            "f(x+a)",
            "伸缩变换",
            "对称变换",
            "平移变换",
        ]
    ),

    # ── 第四章: 指数函数与对数函数 ────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="MATH-C1-CH4",
        name="指数函数与对数函数",
        level=3,
        parent_code="MATH-C1",
        description="指数与指数函数、对数与对数函数、函数的应用(增长模型)",
        keywords=["指数", "对数", "指数函数", "对数函数", "增长模型", "图像变换", "基本初等函数", "幂函数"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C1-CH4-01",
        name="指数",
        level=4,
        parent_code="MATH-C1-CH4",
        description="n次方根、根式、分数指数幂、指数幂的运算法则(同底数幂相乘/除/幂的幂)",
        keywords=["指数", "方根", "根式", "分数指数幂", "a^m·a^n", "(a^m)^n", "指数运算", "幂"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C1-CH4-02",
        name="指数函数",
        level=4,
        parent_code="MATH-C1-CH4",
        description="指数函数y=a^x(a>0且a≠1)的定义、图像与性质(过定点/单调性/值域)、指数增长与衰减模型",
        keywords=["指数函数", "y=a^x", "底数", "指数增长", "指数衰减", "过定点(0,1)"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C1-CH4-03",
        name="对数",
        level=4,
        parent_code="MATH-C1-CH4",
        description="对数的定义(a^b=N ⇔ b=log_a N)、常用对数lg、自然对数ln、对数运算法则、换底公式",
        keywords=["对数", "log", "lg", "ln", "换底公式", "对数运算", "log_a(MN)", "log_a(M/N)"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C1-CH4-04",
        name="对数函数",
        level=4,
        parent_code="MATH-C1-CH4",
        description="对数函数y=log_a x的定义、图像与性质(过定点/定义域/单调性)、与指数函数互为反函数",
        keywords=["对数函数", "y=log_a x", "反函数", "过定点(1,0)", "定义域x>0", "y=log_a(x)"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C1-CH4-05",
        name="函数的应用",
        level=4,
        parent_code="MATH-C1-CH4",
        description="函数零点与方程根的关系、二分法求近似解、函数模型(指数/对数/幂函数增长比较)、实际问题建模",
        keywords=["函数零点", "二分法", "增长模型", "指数增长", "对数增长", "幂函数增长", "建模"],
    ),

    # ── 第五章: 三角函数 ─────────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="MATH-C1-CH5",
        name="三角函数",
        level=3,
        parent_code="MATH-C1",
        description="任意角和弧度制、三角函数的概念、同角关系、诱导公式、图像与性质、三角恒等变换、应用",
        keywords=[
            "三角函数",
            "sin",
            "cos",
            "tan",
            "弧度",
            "诱导公式",
            "恒等变换",
            "sin²+cos²=1",
            "三角恒等变换",
            "单位圆",
            "解三角形",
        ]
    ),
    KnowledgeTreeSeed(
        code="MATH-C1-CH5-01",
        name="任意角和弧度制",
        level=4,
        parent_code="MATH-C1-CH5",
        description="正角/负角/零角、象限角、终边相同的角、弧度制、弧长公式与扇形面积公式",
        keywords=["任意角", "象限角", "终边", "弧度", "弧度制", "弧长", "扇形面积", "1rad"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C1-CH5-02",
        name="三角函数的概念",
        level=4,
        parent_code="MATH-C1-CH5",
        description="用单位圆定义三角函数(sinα=y, cosα=x, tanα=y/x)、三角函数线、各象限符号",
        keywords=["三角函数", "单位圆", "sinα", "cosα", "tanα", "三角函数线", "象限符号"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C1-CH5-03",
        name="同角三角函数的基本关系",
        level=4,
        parent_code="MATH-C1-CH5",
        description="平方关系sin²α+cos²α=1、商数关系tanα=sinα/cosα、齐次式化简",
        keywords=["同角关系", "sin²α+cos²α=1", "tanα=sinα/cosα", "齐次式", "化简"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C1-CH5-04",
        name="诱导公式",
        level=4,
        parent_code="MATH-C1-CH5",
        description="2kπ+α、π+α、-α、π-α、π/2-α、π/2+α的诱导公式、奇变偶不变符号看象限",
        keywords=["诱导公式", "奇变偶不变", "符号看象限", "2kπ+α", "π±α", "π/2±α"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C1-CH5-05",
        name="三角函数的图像与性质",
        level=4,
        parent_code="MATH-C1-CH5",
        description="正弦/余弦/正切函数的图像、周期性、单调性、最值、对称性、y=Asin(ωx+φ)的图像变换",
        keywords=[
            "正弦函数",
            "余弦函数",
            "正切函数",
            "五点法",
            "周期",
            "振幅",
            "相位",
            "y=Asin(ωx+φ)",
            "图像变换",
            "单调区间",
            "对称轴",
            "f(x)=Asin(ωx+φ)",
            "f(x+T)=f(x)",
            "三角函数图像",
            "三角函数图象",
            "值域",
            "最低点",
            "最小正周期",
            "最高点",
            "相邻最高点",
        ]
    ),
    KnowledgeTreeSeed(
        code="MATH-C1-CH5-06",
        name="三角恒等变换",
        level=4,
        parent_code="MATH-C1-CH5",
        description="两角和与差公式(sin(α±β)/cos(α±β)/tan(α±β))、二倍角公式、辅助角公式asinθ+bcosθ",
        keywords=[
            "和差公式",
            "sin(α+β)",
            "cos(α+β)",
            "二倍角",
            "sin2θ",
            "cos2θ",
            "辅助角公式",
            "半角公式",
            "和差化积",
            "积化和差",
            "asinθ+bcosθ",
            "cos15",
            "sin15",
            "tan2θ",
            "三角恒等式",
            "化简求值",
            "恒等变换",
        ]
    ),
    KnowledgeTreeSeed(
        code="MATH-C1-CH5-07",
        name="三角函数的应用",
        level=4,
        parent_code="MATH-C1-CH5",
        description="正弦定理、余弦定理、解三角形(已知两边一角/两角一边/三边)、三角形面积公式、实际测量应用",
        keywords=["正弦定理", "余弦定理", "解三角形", "a/sinA=2R", "a²=b²+c²-2bc·cosA",
                  "S=½ab·sinC", "测量应用"],
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  MATH-C2: 必修第二册
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第六章: 平面向量及其应用 ──────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="MATH-C2-CH6",
        name="平面向量及其应用",
        level=3,
        parent_code="MATH-C2",
        description="平面向量的概念、运算、基本定理、坐标表示、余弦定理、正弦定理",
        keywords=["平面向量", "数量积", "坐标运算", "正弦定理", "余弦定理", "向量"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C2-CH6-01",
        name="平面向量的概念",
        level=4,
        parent_code="MATH-C2-CH6",
        description="向量的定义、有向线段、零向量、单位向量、相等向量、共线向量(平行向量)",
        keywords=["向量", "有向线段", "零向量", "单位向量", "相等向量", "共线向量", "平行向量", "三角形法则", "平行四边形法则"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C2-CH6-02",
        name="平面向量的运算",
        level=4,
        parent_code="MATH-C2-CH6",
        description="向量的加法(三角形法则/平行四边形法则)、减法、数乘、数量积(点积)的定义与性质",
        keywords=["向量加法", "向量减法", "数乘", "数量积", "点积", "a·b", "三角形法则", "平行四边形法则", "夹角cosθ", "投影"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C2-CH6-03",
        name="平面向量基本定理及坐标表示",
        level=4,
        parent_code="MATH-C2-CH6",
        description="平面向量基本定理(基底)、向量的坐标表示、坐标运算法则、平行与垂直的坐标条件",
        keywords=["基本定理", "基底", "坐标表示", "坐标运算", "平行条件x₁y₂=x₂y₁",
                  "垂直条件x₁x₂+y₁y₂=0"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C2-CH6-04",
        name="平面向量的应用",
        level=4,
        parent_code="MATH-C2-CH6",
        description="向量在平面几何中的应用(证明平行/垂直/共线/求夹角)、向量法解三角形",
        keywords=["向量应用", "向量法", "几何证明", "夹角", "距离", "角度"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C2-CH6-05",
        name="余弦定理",
        level=4,
        parent_code="MATH-C2-CH6",
        description="a²=b²+c²-2bc·cosA及其推论、余弦定理的应用(已知三边求角/已知两边及夹角求第三边)",
        keywords=["余弦定理", "a²=b²+c²-2bc·cosA", "求角", "求边"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C2-CH6-06",
        name="正弦定理",
        level=4,
        parent_code="MATH-C2-CH6",
        description="a/sinA=b/sinB=c/sinC=2R、正弦定理的应用(已知两角一边/已知两边及一边对角)",
        keywords=["正弦定理", "a/sinA=2R", "外接圆", "已知两边一角", "多解问题"],
    ),

    # ── 第七章: 复数 ─────────────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="MATH-C2-CH7",
        name="复数",
        level=3,
        parent_code="MATH-C2",
        description="复数的概念、四则运算、三角表示",
        keywords=["复数", "虚数", "i", "复平面", "共轭复数", "a+bi", "共轭", "实轴", "模", "虚轴"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C2-CH7-01",
        name="复数的概念",
        level=4,
        parent_code="MATH-C2-CH7",
        description="虚数单位i(i²=-1)、复数z=a+bi、实部与虚部、复平面(实轴/虚轴)、模|z|、共轭复数",
        keywords=["复数", "虚数单位i", "a+bi", "实部", "虚部", "复平面", "模", "共轭复数", "z̄"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C2-CH7-02",
        name="复数的四则运算",
        level=4,
        parent_code="MATH-C2-CH7",
        description="复数的加减乘除运算法则、模的运算性质、共轭复数的运算性质",
        keywords=["复数加法", "复数减法", "复数乘法", "复数除法", "模的性质", "共轭运算", "|z|", "共轭复数", "复数运算", "模"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C2-CH7-03",
        name="复数的三角表示",
        level=4,
        parent_code="MATH-C2-CH7",
        description="复数的三角形式z=r(cosθ+isinθ)、辐角、复数乘除的几何意义(旋转与伸缩)",
        keywords=["三角表示", "辐角", "模r", "旋转", "伸缩", "De Moivre"],
    ),

    # ── 第八章: 立体几何初步 ─────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="MATH-C2-CH8",
        name="立体几何初步",
        level=3,
        parent_code="MATH-C2",
        description="基本立体图形、直观图、表面积与体积、空间点线面位置关系、平行与垂直的判定性质",
        keywords=["立体几何", "棱柱", "棱锥", "球", "表面积", "体积", "平行", "垂直", "二面角", "点线面", "空间向量"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C2-CH8-01",
        name="基本立体图形",
        level=4,
        parent_code="MATH-C2-CH8",
        description="棱柱/棱锥/棱台/圆柱/圆锥/圆台/球的结构特征、多面体与旋转体",
        keywords=["棱柱", "棱锥", "棱台", "圆柱", "圆锥", "圆台", "球", "多面体", "旋转体", "三视图", "斜二测"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C2-CH8-02",
        name="直观图",
        level=4,
        parent_code="MATH-C2-CH8",
        description="斜二测画法的规则、平面图形直观图的画法、空间几何体直观图的画法",
        keywords=["直观图", "斜二测", "水平放置", "45°", "平行不变", "长度减半"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C2-CH8-03",
        name="简单几何体的表面积与体积",
        level=4,
        parent_code="MATH-C2-CH8",
        description="棱柱/棱锥/棱台/圆柱/圆锥/圆台/球的表面积与体积公式、等体积法求高",
        keywords=["表面积", "体积", "侧面积", "全面积", "V=Sh", "V=⅓Sh", "V=4πR³/3",
                  "S球=4πR²", "等体积法"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C2-CH8-04",
        name="空间点直线平面之间的位置关系",
        level=4,
        parent_code="MATH-C2-CH8",
        description="点/线/面的基本位置关系、公理1-4、空间两条直线的位置关系(平行/相交/异面)、异面直线所成角",
        keywords=["公理", "点线面关系", "异面直线", "异面直线所成角", "平行直线", "相交直线"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C2-CH8-05",
        name="直线平面平行的判定与性质",
        level=4,
        parent_code="MATH-C2-CH8",
        description="线面平行判定定理(线线平行→线面平行)、面面平行判定定理、线面平行性质定理、面面平行性质定理",
        keywords=["线面平行", "面面平行", "判定定理", "性质定理", "线线平行", "中位线", "线面垂直", "面面垂直"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C2-CH8-06",
        name="直线平面垂直的判定与性质",
        level=4,
        parent_code="MATH-C2-CH8",
        description="线面垂直的定义与判定定理(线线垂直→线面垂直)、面面垂直判定与性质、三垂线定理",
        keywords=["线面垂直", "面面垂直", "判定定理", "性质定理", "垂线", "垂面", "三垂线定理"],
    ),

    # ── 第九章: 统计 ─────────────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="MATH-C2-CH9",
        name="统计",
        level=3,
        parent_code="MATH-C2",
        description="随机抽样、用样本估计总体、统计图表",
        keywords=["统计", "抽样", "样本", "总体", "频率分布", "统计图表", "回归", "平均数", "方差"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C2-CH9-01",
        name="随机抽样",
        level=4,
        parent_code="MATH-C2-CH9",
        description="简单随机抽样(抽签法/随机数法)、分层抽样、系统抽样的方法与适用场景",
        keywords=["随机抽样", "简单随机抽样", "抽签法", "随机数法", "分层抽样", "系统抽样"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C2-CH9-02",
        name="用样本估计总体",
        level=4,
        parent_code="MATH-C2-CH9",
        description="频率分布直方图、频率分布表、样本的数字特征(平均数/中位数/众数/方差/标准差)",
        keywords=["频率分布", "直方图", "平均数", "中位数", "众数", "方差", "标准差", "样本估计", "分层抽样", "随机抽样"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C2-CH9-03",
        name="统计图表",
        level=4,
        parent_code="MATH-C2-CH9",
        description="频率分布直方图、茎叶图、散点图、折线图、扇形图的绘制与信息读取",
        keywords=["频率分布直方图", "茎叶图", "散点图", "折线图", "扇形图", "统计图表", "列联表"]
    ),

    # ── 第十章: 概率 ─────────────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="MATH-C2-CH10",
        name="概率",
        level=3,
        parent_code="MATH-C2",
        description="随机事件与概率、事件的相互独立性、频率与概率",
        keywords=["概率", "随机事件", "独立事件", "频率", "古典概型", "全概率", "几何概型", "条件概率", "等可能", "贝叶斯"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C2-CH10-01",
        name="随机事件与概率",
        level=4,
        parent_code="MATH-C2-CH10",
        description="随机事件/必然事件/不可能事件、事件的关系(包含/相等/互斥/对立)、概率的定义与性质",
        keywords=[
            "随机事件",
            "必然事件",
            "不可能事件",
            "互斥事件",
            "对立事件",
            "概率",
            "P(A)",
            "0≤P(A)≤1",
            "P(AB)=P(A)P(B)",
            "互斥",
            "对立",
            "独立",
        ]
    ),
    KnowledgeTreeSeed(
        code="MATH-C2-CH10-02",
        name="事件的相互独立性",
        level=4,
        parent_code="MATH-C2-CH10",
        description="独立事件的定义P(AB)=P(A)·P(B)、互斥与独立的区别、独立事件概率的计算",
        keywords=["独立事件", "P(AB)=P(A)P(B)", "互斥与独立", "相互独立"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C2-CH10-03",
        name="频率与概率",
        level=4,
        parent_code="MATH-C2-CH10",
        description="频率的定义(频数/总数)、频率与概率的关系(大数定律)、用频率估计概率、古典概型",
        keywords=["频率", "频数", "大数定律", "频率估计概率", "古典概型", "等可能事件"],
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  MATH-C3: 选必第一册
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第一章: 空间向量与立体几何 ────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="MATH-C3-CH1",
        name="空间向量与立体几何",
        level=3,
        parent_code="MATH-C3",
        description="空间向量及其运算、基本定理、坐标表示、空间向量的应用",
        keywords=["空间向量", "空间直角坐标系", "法向量", "空间角"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C3-CH1-01",
        name="空间向量及其运算",
        level=4,
        parent_code="MATH-C3-CH1",
        description="空间向量的概念、加法/减法/数乘/数量积运算、运算律",
        keywords=["空间向量", "向量加法", "向量减法", "数乘", "数量积", "运算律"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C3-CH1-02",
        name="空间向量基本定理",
        level=4,
        parent_code="MATH-C3-CH1",
        description="空间向量基本定理(三个不共面向量作基底)、向量的线性表示",
        keywords=["空间基底", "不共面", "线性表示", "基本定理"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C3-CH1-03",
        name="空间向量的坐标表示",
        level=4,
        parent_code="MATH-C3-CH1",
        description="空间直角坐标系、向量的坐标表示、坐标运算法则、夹角与模的坐标公式",
        keywords=["空间直角坐标系", "坐标表示", "坐标运算", "夹角公式", "模的公式", "向量坐标", "垂直条件", "平行条件"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C3-CH1-04",
        name="空间向量的应用",
        level=4,
        parent_code="MATH-C3-CH1",
        description="用向量法求线面角/二面角/点到面距离、法向量的求法、空间几何证明",
        keywords=["法向量", "线面角", "二面角", "点到面距离", "向量法", "空间证明", "cosθ", "空间直角坐标系"]
    ),

    # ── 第二章: 直线和圆的方程 ────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="MATH-C3-CH2",
        name="直线和圆的方程",
        level=3,
        parent_code="MATH-C3",
        description="直线的倾斜角与斜率、直线的方程、距离公式、圆的方程、直线与圆/圆与圆的位置关系",
        keywords=["直线", "圆", "斜率", "距离", "位置关系", "切线", "弦长"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C3-CH2-01",
        name="直线的倾斜角与斜率",
        level=4,
        parent_code="MATH-C3-CH2",
        description="倾斜角α的范围[0°,180°)、斜率k=tanα、两点间斜率公式、斜率与倾斜角的关系",
        keywords=["倾斜角", "斜率", "k=tanα", "两点斜率公式", "斜率不存在"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C3-CH2-02",
        name="直线的方程",
        level=4,
        parent_code="MATH-C3-CH2",
        description="点斜式/斜截式/两点式/截距式/一般式五种形式、直线方程的互化",
        keywords=[
            "点斜式",
            "斜截式",
            "两点式",
            "截距式",
            "一般式",
            "Ax+By+C=0",
            "y=kx+b",
            "一般式Ax+By+C=0",
            "倾斜角",
            "垂直",
            "平行",
            "斜率k=tanα",
        ]
    ),
    KnowledgeTreeSeed(
        code="MATH-C3-CH2-03",
        name="直线的交点坐标与距离公式",
        level=4,
        parent_code="MATH-C3-CH2",
        description="两直线交点的求法、点到直线距离公式、两平行线间距离公式",
        keywords=["交点", "点到直线距离", "d=|Ax₀+By₀+C|/√(A²+B²)", "平行线距离"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C3-CH2-04",
        name="圆的标准方程和一般方程",
        level=4,
        parent_code="MATH-C3-CH2",
        description="标准方程(x-a)²+(y-b)²=r²、一般方程x²+y²+Dx+Ey+F=0、两种形式的互化",
        keywords=["圆的标准方程", "圆的一般方程", "(x-a)²+(y-b)²=r²", "x²+y²+Dx+Ey+F=0",
                  "圆心", "半径"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C3-CH2-05",
        name="直线与圆的位置关系",
        level=4,
        parent_code="MATH-C3-CH2",
        description="相离/相切/相交的判定(几何法d与r/代数法Δ)、圆的切线方程、弦长公式",
        keywords=["相离", "相切", "相交", "d与r", "切线方程", "弦长", "弦心距", "(x-a)²+(y-b)²=r²", "切线", "圆的方程"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C3-CH2-06",
        name="圆与圆的位置关系",
        level=4,
        parent_code="MATH-C3-CH2",
        description="外离/外切/相交/内切/内含五种位置关系、圆心距与半径的关系、公切线",
        keywords=["外离", "外切", "相交", "内切", "内含", "圆心距", "公切线"],
    ),

    # ── 第三章: 圆锥曲线的方程 ────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="MATH-C3-CH3",
        name="圆锥曲线的方程",
        level=3,
        parent_code="MATH-C3",
        description="椭圆、双曲线、抛物线、直线与圆锥曲线的位置关系",
        keywords=["椭圆", "双曲线", "抛物线", "圆锥曲线", "离心率", "准线", "焦点"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C3-CH3-01",
        name="椭圆",
        level=4,
        parent_code="MATH-C3-CH3",
        description="椭圆的定义(到两定点距离之和为常数)、标准方程x²/a²+y²/b²=1、几何性质(顶点/焦点/离心率e=c/a/准线)",
        keywords=["椭圆", "x²/a²+y²/b²=1", "焦点", "离心率", "e=c/a", "准线", "a²=b²+c²", "焦点弦", "弦长", "离心率e=c/a"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C3-CH3-02",
        name="双曲线",
        level=4,
        parent_code="MATH-C3-CH3",
        description="双曲线的定义(到两定点距离之差为常数)、标准方程x²/a²-y²/b²=1、渐近线、离心率e>1",
        keywords=["双曲线", "x²/a²-y²/b²=1", "渐近线", "实轴", "虚轴", "离心率e>1",
                  "c²=a²+b²", "等轴双曲线"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C3-CH3-03",
        name="抛物线",
        level=4,
        parent_code="MATH-C3-CH3",
        description="抛物线的定义(到定点与定直线距离相等)、四种标准方程y²=2px/y²=-2px/x²=2py/x²=-2py、焦点与准线",
        keywords=["抛物线", "y²=2px", "焦点", "准线", "焦点弦", "通径", "焦半径"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C3-CH3-04",
        name="直线与圆锥曲线的位置关系",
        level=4,
        parent_code="MATH-C3-CH3",
        description="联立方程组与判别式Δ、弦长公式、中点弦问题、定点定值问题、最值问题",
        keywords=["联立方程", "判别式Δ", "弦长公式", "韦达定理", "中点弦", "定点", "定值", "最值", "直线与圆锥曲线"]
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  MATH-C4: 选必第二册
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第四章: 数列 ─────────────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="MATH-C4-CH4",
        name="数列",
        level=3,
        parent_code="MATH-C4",
        description="数列的概念、等差数列、等比数列、数学归纳法",
        keywords=[
            "数列",
            "等差数列",
            "等比数列",
            "通项公式",
            "前n项和",
            "数学归纳法",
            "倒序相加",
            "分组求和",
            "求和",
            "等差",
            "等比",
            "裂项相消",
            "递推",
            "通项",
            "错位相减",
        ]
    ),
    KnowledgeTreeSeed(
        code="MATH-C4-CH4-01",
        name="数列的概念",
        level=4,
        parent_code="MATH-C4-CH4",
        description="数列的定义(按一定顺序排列的一列数)、通项公式a_n、递推关系、前n项和S_n与a_n的关系",
        keywords=["数列", "通项公式", "a_n", "递推关系", "前n项和", "S_n", "a_n=S_n-S_{n-1}", "递推"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C4-CH4-02",
        name="等差数列",
        level=4,
        parent_code="MATH-C4-CH4",
        description="定义(a_{n+1}-a_n=d)、通项公式a_n=a_1+(n-1)d、前n项和公式、等差中项、性质",
        keywords=["等差数列", "公差d", "a_n=a_1+(n-1)d", "S_n=na_1+n(n-1)d/2",
                  "S_n=n(a_1+a_n)/2", "等差中项"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C4-CH4-03",
        name="等比数列",
        level=4,
        parent_code="MATH-C4-CH4",
        description="定义(a_{n+1}/a_n=q)、通项公式a_n=a_1·q^(n-1)、前n项和公式、等比中项、性质",
        keywords=["等比数列", "公比q", "a_n=a_1·q^(n-1)", "S_n=a_1(1-q^n)/(1-q)",
                  "等比中项", "G²=ab"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C4-CH4-04",
        name="数学归纳法",
        level=4,
        parent_code="MATH-C4-CH4",
        description="数学归纳法的原理(奠基步+归纳步)、用数学归纳法证明等式/不等式/整除问题",
        keywords=["数学归纳法", "奠基步", "归纳步", "归纳假设", "证明", "a_{n+1}=pa_n+q", "构造法", "递推"]
    ),

    # ── 第五章: 导数及其应用 ─────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="MATH-C4-CH5",
        name="导数及其应用",
        level=3,
        parent_code="MATH-C4",
        description="导数的概念与意义、导数的运算、导数在研究函数中的应用、微积分基本定理、定积分",
        keywords=["导数", "微分", "切线", "极值", "单调性", "定积分", "参变分离", "存在性", "导数证明不等式", "恒成立", "零点个数"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C4-CH5-01",
        name="导数的概念及其意义",
        level=4,
        parent_code="MATH-C4-CH5",
        description="平均变化率、瞬时变化率(极限定义)、导数的几何意义(切线斜率)、物理意义(瞬时速度)",
        keywords=["导数定义", "平均变化率", "瞬时变化率", "极限", "切线斜率", "f'(x₀)", "瞬时速度", "切线", "切线方程", "变化率"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C4-CH5-02",
        name="导数的运算",
        level=4,
        parent_code="MATH-C4-CH5",
        description="基本初等函数导数公式、导数四则运算(加减乘除)、复合函数求导(链式法则)",
        keywords=[
            "求导公式",
            "(xⁿ)'=nxⁿ⁻¹",
            "(sinx)'=cosx",
            "(eˣ)'=eˣ",
            "(lnx)'=1/x",
            "四则运算",
            "链式法则",
            "复合函数求导",
            "(uv)'=u'v+uv'",
        ]
    ),
    KnowledgeTreeSeed(
        code="MATH-C4-CH5-03",
        name="导数在研究函数中的应用",
        level=4,
        parent_code="MATH-C4-CH5",
        description="用导数判断单调性(f'>0增/f'<0减)、求极值(f'=0的点)、求最值(闭区间)、含参讨论",
        keywords=[
            "单调性",
            "f'(x)>0",
            "f'(x)<0",
            "极值",
            "极值点",
            "f'(x₀)=0",
            "最值",
            "含参讨论",
            "减区间",
            "增区间",
            "导数判断单调",
            "最大值",
            "最小值",
            "顶点",
            "驻点",
        ]
    ),
    KnowledgeTreeSeed(
        code="MATH-C4-CH5-04",
        name="微积分基本定理",
        level=4,
        parent_code="MATH-C4-CH5",
        description="定积分的概念(面积/累积)、Newton-Leibniz公式∫_a^b f(x)dx=F(b)-F(a)、基本性质",
        keywords=["微积分基本定理", "Newton-Leibniz", "定积分", "原函数", "∫f(x)dx", "F(b)-F(a)"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C4-CH5-05",
        name="定积分的简单应用",
        level=4,
        parent_code="MATH-C4-CH5",
        description="用定积分求面积(曲边梯形)、求体积(旋转体)、物理应用(变力做功/路程)",
        keywords=["定积分应用", "曲边梯形面积", "旋转体体积", "变力做功", "路程"],
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  MATH-C5: 选必第三册
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第六章: 计数原理 ─────────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="MATH-C5-CH6",
        name="计数原理",
        level=3,
        parent_code="MATH-C5",
        description="分类加法与分步乘法计数原理、排列与组合、二项式定理",
        keywords=["计数原理", "排列", "组合", "排列组合", "二项式定理", "A(n,m)", "C(n,m)", "分步乘法", "分类加法", "计数"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C5-CH6-01",
        name="分类加法计数原理与分步乘法计数原理",
        level=4,
        parent_code="MATH-C5-CH6",
        description="分类加法原理(各类方法互斥,总数为各类之和)、分步乘法原理(各步缺一不可,总数为各步之积)",
        keywords=["分类加法原理", "分步乘法原理", "互斥", "缺一不可", "N=m₁+m₂+…", "N=m₁×m₂×…"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C5-CH6-02",
        name="排列与组合",
        level=4,
        parent_code="MATH-C5-CH6",
        description="排列的定义与排列数A(n,m)=n!/(n-m)!、组合的定义与组合数C(n,m)=n!/[m!(n-m)!]、常见模型(捆绑/插空/隔板)",
        keywords=["排列", "组合", "A(n,m)", "C(n,m)", "排列数", "组合数", "捆绑法",
                  "插空法", "隔板法", "n!"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C5-CH6-03",
        name="二项式定理",
        level=4,
        parent_code="MATH-C5-CH6",
        description="(a+b)ⁿ展开式的通项公式T_{r+1}=C(n,r)a^(n-r)b^r、二项式系数性质、杨辉三角",
        keywords=["二项式定理", "(a+b)ⁿ", "通项公式", "T_{r+1}=C(n,r)a^(n-r)b^r", "二项式系数", "杨辉三角", "系数最大项", "通项"]
    ),

    # ── 第七章: 随机变量及其分布 ──────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="MATH-C5-CH7",
        name="随机变量及其分布",
        level=3,
        parent_code="MATH-C5",
        description="条件概率与全概率公式、离散型随机变量及分布列、二项分布与超几何分布、正态分布",
        keywords=["随机变量", "分布列", "条件概率", "二项分布", "正态分布", "两点分布", "期望", "离散型"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C5-CH7-01",
        name="条件概率与全概率公式",
        level=4,
        parent_code="MATH-C5-CH7",
        description="条件概率P(B|A)=P(AB)/P(A)、乘法公式、全概率公式、贝叶斯公式",
        keywords=["条件概率", "P(B|A)", "乘法公式", "全概率公式", "贝叶斯公式", "先验概率", "后验概率"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C5-CH7-02",
        name="离散型随机变量及其分布列",
        level=4,
        parent_code="MATH-C5-CH7",
        description="离散型随机变量的定义、分布列的性质(概率之和为1)、数学期望E(X)、方差D(X)及性质",
        keywords=["离散型随机变量", "分布列", "数学期望", "E(X)", "方差", "D(X)", "标准差", "E(aX+b)", "D(aX+b)", "期望"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C5-CH7-03",
        name="二项分布与超几何分布",
        level=4,
        parent_code="MATH-C5-CH7",
        description="n次独立重复试验、二项分布X~B(n,p)(E=np,D=np(1-p))、超几何分布的定义与应用",
        keywords=["二项分布", "B(n,p)", "E=np", "D=np(1-p)", "独立重复试验", "超几何分布", "不放回抽样", "独立重复"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C5-CH7-04",
        name="正态分布",
        level=4,
        parent_code="MATH-C5-CH7",
        description="正态曲线与正态分布X~N(μ,σ²)、正态曲线的性质(对称轴/峰值/面积)、3σ原则(68-95-99.7)",
        keywords=["正态分布", "N(μ,σ²)", "正态曲线", "钟形曲线", "3σ原则", "68-95-99.7", "标准正态分布", "标准正态"]
    ),

    # ── 第八章: 成对数据的统计分析 ────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="MATH-C5-CH8",
        name="成对数据的统计分析",
        level=3,
        parent_code="MATH-C5",
        description="成对数据的统计相关性、一元线性回归模型、列联表与独立性检验",
        keywords=["相关性", "回归", "列联表", "独立性检验", "统计分析"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C5-CH8-01",
        name="成对数据的统计相关性",
        level=4,
        parent_code="MATH-C5-CH8",
        description="散点图与相关关系(正相关/负相关/不相关)、样本相关系数r的计算与含义",
        keywords=["相关性", "散点图", "正相关", "负相关", "相关系数r", "线性相关"],
    ),
    KnowledgeTreeSeed(
        code="MATH-C5-CH8-02",
        name="一元线性回归模型",
        level=4,
        parent_code="MATH-C5-CH8",
        description="最小二乘法求回归方程ŷ=bx+a、回归系数b与截距a的公式、残差分析",
        keywords=["线性回归", "最小二乘法", "ŷ=bx+a", "回归系数", "残差", "拟合", "K²检验", "y=bx+a", "回归分析", "相关系数r"]
    ),
    KnowledgeTreeSeed(
        code="MATH-C5-CH8-03",
        name="列联表与独立性检验",
        level=4,
        parent_code="MATH-C5-CH8",
        description="2×2列联表、χ²(卡方)统计量的计算、独立性检验的步骤(假设/计算/比较/结论)",
        keywords=["列联表", "2×2列联表", "χ²检验", "卡方统计量", "独立性检验",
                  "零假设", "显著性水平"],
    ),
]
