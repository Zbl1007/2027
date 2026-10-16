# 参数冻结前的文献与来源补充

核查日期：2026-10-16。补充 P0 的来源检索，不执行建模、改参或优化。

**先完成参数溯源，再冻结取值。当前本地 TAP case 缺参，不等于 TAP 官方项目没有可参考的封装/热参数；官方热模型的参数也不等于完整 P/G 和力学设计。**

## 1. 直接相关的来源

| 来源 | 本轮核查到的内容 | 可以支持什么 / 不可以支持什么 |
|---|---|---|
| Ma 等，TAP-2.5D，DATE 2021，[会议原文](https://www.date-conference.com/proceedings-archive/2021/pdf/1516.pdf)，§III-A、§IV、参考文献 [28][29] | 六层热模型、芯粒案例和热边界说明；Multi-GPU 是概念案例 | 支持 benchmark 与热建模背景；没有给出完整多 rail P/G 网表或工作温度应力模型 |
| TAP 官方固定提交的 [sys_multigpu.cfg](https://github.com/bu-icsg/TAP-2.5D/blob/3a3f4e5a4d019b2d9cda1f72d8d1755238845dbb/configs/sys_multigpu.cfg) | 原始尺寸、功耗、通信、50 mm 包络 | 支持原始输入；不提供最终布局坐标，不能消除本地派生尺寸的差异 |
| TAP 官方固定提交的 [passive_interposer.py](https://github.com/bu-icsg/TAP-2.5D/blob/3a3f4e5a4d019b2d9cda1f72d8d1755238845dbb/passive_interposer.py) 与 [hotspot.config](https://github.com/bu-icsg/TAP-2.5D/blob/3a3f4e5a4d019b2d9cda1f72d8d1755238845dbb/util/hotspot.config) | 热模型的材料、尺寸、层叠和边界实现 | 可建立有出处的热基线候选；不自动批准为本地三场参数 |
| Lu 等，Thermo-Mechanical Reliability of 3-D ICs containing Through Silicon Vias，ECTC 2009，pp. 630–634，[作者机构原文](https://sites.utexas.edu/ruihuang/files/2021/03/ECTC2009.pdf) | 单孔、衬层、孔阵列相互作用的 FEA 与解析分析 | 支持力学建模及验证方法；该文包含制造过程残余应力，不能把其温度历程直接搬到本项目的工作温升模型 |
| Characterization and Design of Through-Silicon Via Arrays in Three-Dimensional ICs Based on Thermomechanical Modeling，IEEE TED 58(2), 279–287，DOI 10.1109/TED.2010.2089987，[出版方页面](https://ieeexplore.ieee.org/document/5640664/) | 本轮核查出版方摘要：研究孔高、直径、间距和阵列大小对温度/应力的影响 | 可作为后续精读候选；未取得全文参数表，不从摘要填材料或几何数值 |

TAP §III-A 引用的工艺来源为：R. Chaware 等，Assembly and reliability challenges in 3D integration of 28nm FPGA die on a large high density 65nm passive interposer，ECTC 2012；J. Charbonnier 等，High density 3D silicon interposer technology development and electrical characterization for high end applications，ESTC 2012。本轮通过 TAP 原文确认这两条引用，未取得两篇会议全文，不能声称已逐项核对其表格。

可继续追溯 [CEA-Leti 官方 2012 年研究报告](https://www.cea.fr/cea-tech/leti/Documents/Rapport%20scientifique/Rapports%202012/Annual%20Research%20report%20DCOSDTSI%202012.pdf) 中 Charbonnier 团队的对应工作。它是另一试验载体，不能把载体尺寸直接替换进 Multi-GPU。

## 2. 已核查的官方热模型候选值

以下来自固定提交源码，状态均为 **source_verified / adoption_pending**，没有写入生产配置。

| 项目 | 原始值 | 本地保存的证据 |
|---|---:|---|
| TSV diameter | 10 µm | `evidence/literature_20261016/passive_interposer.py:33` |
| TSV_edge，等效密度尺度 | 50 µm | 同文件 :34–44 |
| 硅中介层厚度 | 110 µm | 同文件 :146 |
| 芯粒层 / TIM 厚度 | 150 / 20 µm | 同文件 :148–149 |
| 环境温度 | 318.15 K（45 °C） | `evidence/literature_20261016/hotspot.config:78` |

这份模型使用均匀等效 TSV 材料，不输出逐孔 P/G 身份。其铜占比公式采用 `(diameter/edge)^2`；显式圆孔应重新核对面积，不能无声混用。把等效层与新增孔叠加还可能重复计算铜量。

源码的 `resistivity_Cu` 是热阻率，单位 m·K/W，不是电阻率 Ω·m。官方热参数不能填入 DC 的电阻率字段。

取值还存在版本选择问题：本地 `ICCAD/table1.tex` 使用 TSV 直径 20 µm、高 100 µm；它与上述官方热模型不一致，而且本地表本身不是这些数值的外部出处。本次没有混合两套数值。

## 3. P/G 数量仍然需要独立依据

已核对的 TAP 资料没有给出本案例 P/G 各自孔数、逐网电流分配和逐孔坐标。不能用整片面积除以 50 µm 网格面积得到“已公开 P/G 数量”，也不能把所有热等效 TSV 都算作可移动 P/G 孔。

可接受的来源路径有两种：有完整公开设计时直接采用其明确预算；否则在电压、负载、电流密度限制、IR-drop 目标和合法几何均有依据后，推导研究用预算并记录公式、余量和适用范围。这类预算应标为 derived_design / explicit_assumption，不能写成 TAP 原论文数据。固定孔数用于控制比较条件，不会自动让所选数字获得文献依据。

力学还需材料弹性参数、CTE、无应力参考状态、衬层/界面与约束；现有来源没有组成一套可直接用于本案例的完整参数集。缺失项继续留空，不输出零应力。

## 4. 对 P0 和下一步的影响

- 参数表 G03/G04/G10/G17/G19 的“可用来源”应补充上述官方模型；原表的本地缺参状态依然成立。来源存在、已核查、已采用是三个不同状态。
- P1 的第一步应是逐字段来源表：参数、值、单位、原文页/表或源码行、物理含义、适用条件、推导过程及采用状态。先解决冲突，再生成固定配置。
- 可以复用 TAP 的公开热模型作为参考基线；扩展电学与力学后应明确称为 TAP-derived research model，不能宣称恢复了原论文未给出的三场设计。
- 若一项关键值既无直接来源，也无法从有依据的设计约束推导，就保持 missing_parameters。引用几篇论文不能替代逐参数的证据。

本轮只静态读取公开资料。保存了两份官方源码快照及 SHA-256，见 `evidence/literature_20261016/sources.json`；未执行下载的代码，未重跑原有 130 项测试，也未扩大它们的验证范围。
