# Factrix

个人公募基金持仓穿透分析工具。把你持有的基金拆到最底层，看看每只基金到底买了什么股票，有没有表面分散实际抱团，风格有没有漂移，极端行情下会亏多少。

## 功能

**七个分析维度：**

1. **全景诊断** — 综合评分 0-100，给出体检结论和扣分项明细
2. **PBSA 持仓穿透** — 用余弦相似度计算基金间持仓重合度，热力图展示抱团风险；穿透到底层个股和五大行业分布
3. **RBSA 风格回归** — 用收益率反推组合在大盘价值/成长、小盘价值/成长、国债五个因子上的真实暴露，SLSQP 约束优化
4. **Rolling RBSA 风格漂移** — 60天滚动窗口监测风格变化轨迹，方差和偏移量超阈值时触发警告
5. **CVaR 尾部风险** — Cornish-Fisher 修正的 95%/99% 条件风险价值，加上 2015 股灾、2020 疫情、2022 股债双杀三个历史场景压力测试
6. **前景理论胜率赔率** — 滚动持有期的胜率、盈亏比、Kahneman-Tversky 效用值（λ=2.25）、Omega 比率
7. **带摩擦调仓** — 二次规划优化器，赎回费率阶梯（<7天1.5%、<30天0.75%、<365天0.5%）作为摩擦成本约束，输出具体买卖金额和避费建议

**数据来源：** AkShare 开源接口，本地 SQLite 缓存，首次拉取后秒级读取。

## 安装

需要 Python 3.10+，推荐用 [uv](https://github.com/astral-sh/uv) 管理环境：

```bash
git clone <repo-url>
cd Factrix
uv sync
```

## 使用

1. 准备持仓 CSV 文件（格式参考 `fundlist.csv`），放到项目根目录
2. 启动看板：

```bash
uv run streamlit run app.py
```

看板分 5 个 Tab：全景诊断、静态穿透、风格画像、尾部防御、调仓指南。每个维度都有白话小贴士解释专业概念。

## 项目结构

```
Factrix/
├── app.py                     # Streamlit 看板入口
├── fundlist.csv               # 持仓清单（你的数据）
├── fund_data.db               # SQLite 数据缓存
├── pyproject.toml
├── src/
│   ├── config.py              # 全局配置（基准指数、行业映射、费率阶梯、前景理论参数）
│   ├── data/
│   │   ├── csv_parser.py      # CSV 解析（多编码、6位补零、重复聚合）
│   │   ├── storage.py         # SQLite 缓存层
│   │   └── fetcher.py         # AkShare 数据抓取（指数退避重试 + 缓存优先）
│   ├── engine/
│   │   ├── pbsa.py            # 持仓穿透 & 重合度矩阵
│   │   ├── rbsa.py            # 收益率风格回归
│   │   ├── rolling_rbsa.py    # 滚动风格漂移
│   │   ├── cvar_stress.py     # CVaR & 压力测试
│   │   ├── prospect_theory.py # 胜率赔率 & 前景理论
│   │   ├── rebalance.py       # 带摩擦调仓优化
│   │   └── health_score.py    # 综合评分
│   └── ui/
│       ├── charts.py          # Plotly 图表（热力图、雷达图、折线图、柱状图、气泡图）
│       └── components.py      # Streamlit 组件（健康卡片、调仓指南、白话贴士）
└── tests/
    ├── conftest.py            # 测试 fixtures & 网络拦截
    ├── test_data_layer.py     # 数据层测试
    ├── test_engine.py         # 引擎单元测试
    ├── test_e2e_app.py        # 4-Tier E2E 测试
    ├── test_infra.py          # 测试基础设施自检
    ├── test_ui.py             # UI 组件测试
    └── fixtures/              # 离线 mock 数据
```

## 测试

```bash
# 全量测试（68 个用例）
uv run pytest -v

# 按层级运行
uv run pytest -m tier1    # 功能覆盖
uv run pytest -m tier2    # 边界异常
uv run pytest -m tier3    # 交叉组合
uv run pytest -m tier4    # 真实场景 E2E

# 单独运行某个测试文件
uv run pytest tests/test_engine.py -v
```

测试覆盖 4 层：功能 Happy Path → 边界异常 → 多引擎交叉联动 → 真实无网络 E2E。所有测试零外网依赖。

## 配置

编辑 `src/config.py` 可调整：

| 配置项 | 说明 | 默认值 |
|---|---|---|
| `RBSA_BENCHMARKS` | 5 个风格因子基准指数代码 | 中证大盘/小盘价值/成长 + 国债指数 |
| `SECTOR_CATEGORY_MAP` | 申万一级行业 → 五大类映射 | 30+ 个行业映射 |
| `PROSPECT_LAMBDA` | 损失厌恶系数 | 2.25 |
| `REDEMPTION_FEE_TIERS` | 赎回费率阶梯 | <7d 1.5%, <30d 0.75%, <365d 0.5% |
| `AKSHARE_MAX_RETRIES` | API 重试次数 | 3 |

## 技术栈

Python · Streamlit · Plotly · pandas · NumPy · SciPy · AkShare · SQLite
