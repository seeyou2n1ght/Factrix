# Alpha & Beta 归因引擎架构分析与设计策略报告

> 思维路径：基于 src/engine/rbsa.py、pbsa.py 与 cvar_stress.py 现存引擎的代码范式分析，已有引擎普遍采用 typing 类型注解、Numpy与Pandas 向量化计算及防御性边界校验机制。AlphaBetaEngine 的设计遵循该架构模式，引入单只基金与组合层面的 CAPM 回归指标计算，并针对基准缺失建立合成基准回退策略。

**BLUF**: 本报告完成 Factrix 引擎架构评估，为 AlphaBetaEngine 规范了高内聚静态类结构、合成基准兜底逻辑及 tests/test_engine.py 单元测试方案。

## 现存引擎防御性编程标准评估

src/engine/rbsa.py (302行)、pbsa.py (425行) 及 cvar_stress.py (204行) 展现了统一的防御性架构范式。这三个核心模块在类型注解、向量化运算与异常处理三个维度具备高度的一致性。

### 类型注解与规范约束
现存引擎全面引入 Python 标准库 typing 模块与 Pandas/Numpy 类型声明。函数入参与返回值显式标注 Dict[str, pd.DataFrame]、pd.Series、np.ndarray 与 Optional[Dict[str, float]]。这种严格的类型约束确保了数据在引擎层传递时的静态可检查性与接口契约明确度。

### Numpy与Pandas向量化计算
数据处理全流程依赖 Pandas 与 Numpy 矩阵运算提升执行效率。RBSAEngine 采用 np.dot 与 scipy.optimize.minimize 执行约束二次规划，PBSAEngine 利用 np.outer 与 np.linalg.norm 进行基金持仓余弦相似度矩阵计算，CVaRStressEngine 采用向量化布尔掩码筛选尾部收益率。这种向量化设计规避了原生循环的性能瓶颈。

### 异常处理与边界防御机制
引擎在数据入口与计算关键节点部署了多重防御屏障。输入字典为空或数据行数低于阈值 3 时，引擎自动截断并返回预定义的默认数据结构。针对零方差、零分母与浮点数溢出场景，代码通过 np.errstate 及 1e-12 极小值保护机制维持数学计算的稳定运行。

## AlphaBetaEngine 类结构与计算方法设计

AlphaBetaEngine 采用与 RBSAEngine 和 PBSAEngine 一致的无状态静态类设计范式。此类聚焦于 CAPM 回归模型与绩效归因指标的计算。

### 类接口定义与输入输出契约
AlphaBetaEngine 核心入口为静态方法 calculate，接受 nav_df_dict、market_benchmark_df 及 fund_market_values 作为主输入。系统支持可选参数无风险利率 rf_rate (默认 0.015) 与年化因子 annualization_factor (默认 252.0)。输出结果返回包含组合 Alpha、Beta、R2、Sharpe、Treynor、Information Ratio、Tracking Error、单基金指标及散点数据的字典。

### CAPM 核心计算逻辑与向量化实现
组合日收益率由各基金日收益率按持仓市值权重线性组合而成。基准收益率与组合收益率在日期维度完成内外连接对齐。系统利用 Numpy 协方差矩阵 np.cov 一次性提取组合与基准的方差及协方差，计算 Beta 与 Alpha 年化值。特雷诺比率、信息比率与跟踪误差通过超额收益率序列的均值与标准差向量化求得。

### 单基金与组合指标的双层归因结构
计算流程分为组合整体归因与单只基金归因两个独立层次。系统遍历 nav_df_dict 中的每只基金，单独与基准收益率执行 CAPM 回归，生成 fund_metrics 字典。组合层面的指标由加权收益率序列直接回归得出，确保组合 Beta 与单基金加权 Beta 具备可比性与交叉校验能力。

## 合成基准数据兜底机制设计

基准大盘指数 DataFrame 存在缺失、字段不符或收益率序列零方差的客观情况。AlphaBetaEngine 内置合成基准生成器以保障归因计算流程的平稳运行。

### 触发条件与校验逻辑
系统在提取基准收益率时执行三级校验。第一级检查 DataFrame 是否为空或 None；第二级检查对齐后的有效重合交易日是否少于 3 天；第三级检查基准收益率序列的方差是否小于 1e-12。任意条件满足即触发合成基准生成逻辑。

### 沪深300合成算法与参数拟合
合成基准基于沪深300历史波动特征构建随机收益率序列。合成序列采用公式 $r_m = 0.6 \cdot r_p + \epsilon$ 生成，其中 $r_p$ 为组合日收益率，$\epsilon \sim \mathcal{N}(0.0001, 0.008^2)$ 为高斯白噪声。此公式保持合成基准与组合收益率合理的正相关性与市场波动率特征。

### 兜底标记与透明度输出
合成基准激活时系统保持计算流程连贯。输出字典的元数据字段包含 is_synthetic_benchmark 标记，用于告知上层 UI 界面及调试工具当前结果基于合成基准产生。这种设计兼顾了系统的鲁棒性与计算结果的透明度。

## Unit Test Suite 测试套件规划 (tests/test_engine.py)

针对 AlphaBetaEngine 的单元测试集成至 tests/test_engine.py，构建覆盖正常、极限与边界场景的测试集。

- test_alpha_beta_engine_normal：验证标准多基金与沪深300基准输入下的全量 9 个契约字段与数值合理区间。
- test_alpha_beta_engine_perfect_correlation：验证基准等于组合收益率时 Beta=1.0、Alpha=0.0、R2=1.0 及 Tracking Error=0.0。
- test_alpha_beta_engine_synthetic_fallback：验证基准为空时触发合成基准兜底且正常返回散点数据与标记。
- test_alpha_beta_engine_zero_variance：验证平坦净值序列在零方差防御下平稳运行而不触发除零异常。
- test_alpha_beta_engine_empty_input：验证空字典与空持仓数值下准确返回预定义默认数据结构。
