# 逐参数来源台账

日期：2026-10-16。主数据为 [registry.json](../parameters/registry.json)，出处目录为 [catalog.json](../sources/catalog.json)。

**候选值均未自动采用；缺失值保持 null。此表不是可运行物理配置。**

保留当前派生布局。官方与本地尺寸、热等效孔与物理 P/G 孔、热阻率与电阻率，均须分别核对。

| 参数 | 候选值 | 证据位置 | 状态与使用限制 |
|---|---|---|---|
| 中介层平面边长 | 50 mm | [tap_cfg](../references/upstream/tap25d/configs/sys_multigpu.cfg):10 | 来源已核查，未采用；官方与派生包络一致 |
| 芯粒数量 | 6 count | [tap_cfg](../references/upstream/tap25d/configs/sys_multigpu.cfg):14 | 来源已核查，未采用；数组 ID 0-5 |
| 各芯粒额定功率 | [105, 295, 295, 20, 20, 20] W | [tap_cfg](../references/upstream/tap25d/configs/sys_multigpu.cfg):17 | 来源已核查，未采用；名义功率，不是 actual-IV |
| 芯粒宽高版本 | [[12, 12], [18.2, 18.2], [18.2, 18.2], [7.75, 11.87], [7.75, 11.87], [7.75, 11.87]] mm | [tap_cfg](../references/upstream/tap25d/configs/sys_multigpu.cfg):15 | 版本冲突，未选择；官方宽高在 15、16 行 |
| 芯粒宽高版本 | [[12, 12], [18, 18], [18, 18], [12, 8], [12, 8], [12, 8]] mm | [local_layout](../references/mypdn_case/multigpu.yaml):25 | 版本冲突，未选择；当前派生尺寸 |
| 芯粒朝向与局部坐标变换 | null | 待查 | 未保存显式朝向 |
| 封装技术 | silicon_interposer enum | [tap_thermal](../references/upstream/tap25d/passive_interposer.py):146 | 来源已核查，未采用；官方热结构；本地三场 profile 尚未配置 |
| TSV 直径 | 10 um | [tap_thermal](../references/upstream/tap25d/passive_interposer.py):33 | 版本冲突，未选择；官方热模型取值 |
| TSV 直径 | 20 um | [local_iccad](../references/mypdn_model_reference/table1.tex):23 | 版本冲突，未选择；本地电学参考，外部出处未核实 |
| TSV_edge 等效密度尺度 | 50 um | [tap_thermal](../references/upstream/tap25d/passive_interposer.py):34 | 来源已核查，未采用；不是完整逐孔 P/G 阵列 |
| 物理 TSV 高度 | 100 um | [local_iccad](../references/mypdn_model_reference/table1.tex):24 | 有条件候选；旧参考，外部出处未核实 |
| 物理 TSV 高度 | 110 um | [tap_thermal](../references/upstream/tap25d/passive_interposer.py):146 | 有条件候选；仅在恰好贯穿该层且不含端接的假设下成立；推导：L_TSV = t_interposer = 0.00011 m; assumption required |
| 基板层厚 | 200 um | [tap_thermal](../references/upstream/tap25d/passive_interposer.py):144 | 来源已核查，未采用；官方分层热模型；机械实体需另核对 |
| C4/underfill层厚 | 70 um | [tap_thermal](../references/upstream/tap25d/passive_interposer.py):145 | 来源已核查，未采用；官方分层热模型；机械实体需另核对 |
| 硅中介层层厚 | 110 um | [tap_thermal](../references/upstream/tap25d/passive_interposer.py):146 | 来源已核查，未采用；官方分层热模型；机械实体需另核对 |
| microbump/underfill层厚 | 10 um | [tap_thermal](../references/upstream/tap25d/passive_interposer.py):147 | 来源已核查，未采用；官方分层热模型；机械实体需另核对 |
| 芯粒层厚 | 150 um | [tap_thermal](../references/upstream/tap25d/passive_interposer.py):148 | 来源已核查，未采用；官方分层热模型；机械实体需另核对 |
| TIM层厚 | 20 um | [tap_thermal](../references/upstream/tap25d/passive_interposer.py):149 | 来源已核查，未采用；官方分层热模型；机械实体需另核对 |
| 铜热导率 | 400 W/(m*K) | [tap_thermal](../references/upstream/tap25d/passive_interposer.py):25 | 来源已核查，未采用；热阻率倒数；不是电阻率，温变/各向异性未证明；推导：k = 1 / 0.0025 = 400 W/(m*K) |
| 硅热导率 | 100 W/(m*K) | [tap_thermal](../references/upstream/tap25d/passive_interposer.py):27 | 来源已核查，未采用；热阻率倒数；不是电阻率，温变/各向异性未证明；推导：k = 1 / 0.01 = 100 W/(m*K) |
| underfill热导率 | 1.6 W/(m*K) | [tap_thermal](../references/upstream/tap25d/passive_interposer.py):26 | 来源已核查，未采用；热阻率倒数；不是电阻率，温变/各向异性未证明；推导：k = 1 / 0.625 = 1.6 W/(m*K) |
| TIM热导率 | 4 W/(m*K) | [tap_thermal](../references/upstream/tap25d/passive_interposer.py):149 | 来源已核查，未采用；热阻率倒数；不是电阻率，温变/各向异性未证明；推导：k = 1 / 0.25 = 4 W/(m*K) |
| 环境温度 | 318.15 K | [tap_hotspot](../references/upstream/tap25d/util/hotspot.config):78 | 来源已核查，未采用；不自动作为无应力或电阻参考温度 |
| 扩展板/散热器边长 | {"spreader": 100, "heatsink": 200} mm | [tap_thermal](../references/upstream/tap25d/passive_interposer.py):154 | 来源已核查，未采用；仅适用于 50 mm 包络与官方冷却结构；推导：spreader = 2*50 mm; heatsink = 2*spreader |
| 散热器总对流热阻 | 0.009 K/W | [tap_thermal](../references/upstream/tap25d/passive_interposer.py):156 | 来源已核查，未采用；不能直接搬到中介层顶面；须保留散热路径；推导：0.1*(0.06**2)/(0.2**2) = 0.009 K/W |
| 标称供电电压 | 1 V | [local_layout](../references/mypdn_case/multigpu.yaml):4 | 仅本地参考；local legacy，没有 TAP 电气来源 |
| 铜电阻率 | 1.7e-08 ohm*m | [local_iccad](../references/mypdn_model_reference/table1.tex):26 | 仅本地参考；缺外部来源、参考温度和温区 |
| P/G 金属线宽 | 20 um | [local_iccad](../references/mypdn_model_reference/table1.tex):13 | 仅本地参考；旧参考，不代表当前 TAP routing |
| P/G 金属厚度 | 0.7 um | [local_iccad](../references/mypdn_model_reference/table1.tex):14 | 仅本地参考；外部出处与等效并联模型待核实 |
| 各 rail 固定 P/G 真孔数 | null | 待查 | 需公开预算或基于有来源负载和限值推导 |
| 逐孔 ID、rail、坐标和端点 | null | 待查 | 缺共享实体列表 |
| P/G bump 与负载分配 | null | 待查 | 通信矩阵不是供电电流 |
| 封装入口与回流阻抗 | null | 待查 | 需坐标、阻抗与 ground policy |
| 衬层及阻挡层 | null | 待查 | 需材料、厚度和端接 |
| TCR 及参考温度 | null | 待查 | 需材料温区和 bulk/contact 政策 |
| 热界面接触 | null | 待查 | 与 TIM/等效边界分账，防重复热阻 |
| 负载与热功率政策 | null | 待查 | 区分 nominal heat、actual-IV、内部和外部损耗 |
| E/nu 或刚度张量 | null | 待查 | 按实体定义，明确硅晶向/等向近似 |
| CTE 与热应变模型 | null | 待查 | 需温区和切线/割线约定 |
| 无应力参考状态 | null | 待查 | 不能自动等于环境或退火温度 |
| 机械支撑和界面 | null | 待查 | 不能用热边界代替机械约束 |
| 温度转移和应力 ROI | null | 待查 | 需要共同实体及覆盖范围 |
| 真实机械后端 | null | 待查 | 旧审计本机未发现可用 COMSOL，新项目未重探测 |
| 允许电流密度与应力 | null | 待查 | 容量推导或安全性判断需要有来源限值 |

## 文献阅读范围

- [TAP DATE 2021](https://www.date-conference.com/proceedings-archive/2021/pdf/1516.pdf)：已核查热模型、案例和工艺引用，继续追溯 [28][29] 全文。
- [Lu 等 ECTC 2009](https://sites.utexas.edu/ruihuang/files/2021/03/ECTC2009.pdf)：已核查单孔/阵列与制造应力设置；未直接填充当前材料表。
- [IEEE TED 2011](https://ieeexplore.ieee.org/document/5640664/)：仅摘要与出版信息，不从摘要填参数。

## 下一批取证

优先查 P/G 预算及设计约束、供电与负载分配、衬层、E/ν/CTE、无应力参考状态和机械边界。有条件推导须明确假设，不标为 TAP 原始数据。

旧 36 项缺口保留在 [gap_registry.json](../parameters/gap_registry.json)。数值误差、缓存、后端和资源预算是模型契约，不应为了填表任意给数。
