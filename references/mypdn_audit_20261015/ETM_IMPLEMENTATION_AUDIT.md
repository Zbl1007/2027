# TAP Multi-GPU 电—热—力建模前审计（P0）

审计日期：2026-10-15（Asia/Shanghai）。对象：当前 `mypdn` 工作区，而非仅 Git HEAD。
HEAD：`373645e631af872be175e9966c82b3a0d6ae460f`。工作区已有大量修改与未跟踪实现；本轮基线见 `evidence/git_status_at_start.txt` 和 `evidence/input_hashes.json`。

**结论：现有 DC、热网络、电热映射和 hard rebuild 有真实可复用实现；当前 TAP Multi-GPU 尚不是参数齐全的三场案例。未找到 TAP cfg importer、逐孔三维物理实体及真实力学后端。P0 已完成核查，不具备宣称 TAP 三场求解完成或进入优化的依据。**

本轮没有修改生产求解器或案例参数，没有运行优化、全尺寸模型、COMSOL 或有限元网格。数值探针全部使用已有小型 `synthetic_fixture`；其结果不能移作 TAP 参数、温度或应力。

2026-10-16 来源范围补充：已进一步核查 TAP 官方热模型及力学文献。部分封装/热参数有公开依据，但尚未进入本地 case；见 [参数文献溯源补充](ETM_LITERATURE_PROVENANCE_ADDENDUM.md)。本地缺参结论不应解释为外部来源不存在。

## 1. 请求边界、资料与证据等级

用户当前请求是 P0 审计。桌面 `TAP25D_ETM_Modeling_Design_for_Codex.md` 是目标规格；`Codex_Prompts_ETM_Modeling.md` 的 P1–P6 提示和命令是后续参考，未被当作本轮执行指令。源码中的历史授权、配置里的 `user_authorized` 仅描述原案例，不能转移为新 TAP profile 的参数批准。

已检查：

- 用户提供的 AGENTS 指令及 `/Users/zbl/.codex/RTK.md`；根目录及上级未找到额外 AGENTS.md。
- 仓库三份旧设计：`CoWoS_L_PG_TIV_Electrothermal_Placement_Implementation_Design.md`、`TAP_2_5D_to_CoWoS_L_TIV_Case_Integration_Design_for_Codex.md`、`Bump_Level_Multi_Rail_Case_Integration_Design_for_Codex.md`，以及 `docs/current_architecture.md`、物理/电热契约、测试说明和依赖配置。
- 根 README 与 `docs/RESEARCH_CONTEXT.md`：未找到。`tests/README.md`、`data/tap_50x50/README.md` 实际存在。
- AIWorkflow 生效红线为空；AITDD 默认启用、正式 Run 为 explicit。本轮新建独立 `CoWoSLTIV/ETMModelingAudit/v0.1.0`，不复用最少通孔优化 Issue 的验收结论。

证据分为：本轮真实运行（R）、源码静态核查（S）、历史日志/文档（H）、测试接口或合成数据（F）。H 不替代 R；F 的数值计算可验证实现，但不代表产品校准或真实 COMSOL 求解。

## 2. 能力判定矩阵

“已实现且测试通过”只适用于表中明确的范围，不意味着研究案例完成。

| 能力                     | 当前状态                                                  | 实际实现 / 本轮证据                                                                                                     | 可复用范围与限制                                                                                    |
| ------------------------ | --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| TAP `.cfg` importer    | **缺失**                                            | 全仓源码/文件名搜索无 `Tap25DParser`、TAP cfg parser；旧 TAP 设计 §6 是建议                                          | 不得把通用 JSON parser 或现成 YAML 叫作 cfg importer；需薄适配层                                    |
| frozen chiplet layout    | **部分实现；现有显式 YAML 测试通过**                | `data/tap_50x50/multigpu.yaml`；`tests/unit/test_tap_50x50_cases.py`，data_dc 组 R                                  | 刚性平移、边界、body/keepout 和总功率已测；没有独立 frozen-via manifest、朝向字段或论文最优坐标     |
| normalized case          | **已实现且小例测试通过**                            | `cases/parser.py:433 load_case_bundle`；`cases/types.py:202 NormalizedCase`；`tests/cases` R                      | 输入为 manifest + 三个 JSON；SI、raw terminal ID、net/supply pair、来源 hash；尚不接受 TAP YAML/cfg |
| compiled artifacts       | **已实现且小例实际编译通过**                        | `cases/compiler.py:751 compile_case`、`:508 load_compiled_artifacts`；20-cell compile/read/cache probe R            | NPZ/NPY/JSON 与校验/hash 可复用；不是包含三场材料/孔实体的统一三维模型                              |
| schema-v1 / v2           | **已实现且相应测试通过**                            | `config/loader.py`、`config/v2.py`、`design/v2.py:393 DesignSpecV2`；data_dc R                                    | v1 与 v2 并存；v2 typed rail/node/branch 更适合保留多 rail；热模型另有 `ThermalDesignSpec`        |
| 完整 P/G 电网络          | **已实现且解析小例通过**                            | `builders/dc_network.py:179 build_dc_circuit`；`builders/dc_v2.py:327 build_dc_v2`；双 P/G、共享/独立 return 测试 R | v2 有 package 垂直阻抗、front/back 网格；仍是等效网络，未显式建每个 microbump 与 die 内回流路径     |
| P/G 通孔宏               | **部分实现；集总公式/拓扑测试通过**                 | `candidates/types.py:56 TivMacroPhysicalSpec`；`candidates/physics.py:29 derive_tiv_macro_physics` R                | 支持孔数、直径、高度、铜/接触分离及 ΔG；无宏内孔坐标/衬层/逐孔 via ID                              |
| DC MNA / SciPy           | **已实现且本轮真实通过**                            | `Circuit.py` → `OpSimulation.py:206 OpSimulationScipy` → `analysis/dc_v2.py:279 solve_dc_v2` R                  | 复用求解器；可得实际 load Vp−Vg、Joule、全局电功率账；缺分单位 KCL/KVL 残差输出                    |
| PARDISO / cuDSS          | **实现存在，本机外部依赖阻塞**                      | `OpSimulation.py:289/:336`；本轮构造/求解小例报缺原生扩展 R                                                           | 仓库 Linux CPython 3.10 `.so` 不能替代当前 macOS Python 3.11 后端。历史服务器通过不等于本机可用   |
| R(T)                     | **已实现且映射/公式测试通过**                       | `builders/electrical.py:29`；`mapping/electrothermal.py:294`；`thermal_v2/mapping.py:270` R                       | v1 材料 TCR；v2 物理宏 bulk/contact metadata 优先，其他支路按 kind contract；非全实体材料模型       |
| 稳态热网络               | **已实现且解析/映射小例通过**                       | `builders/thermal_builder.py`、`analysis/thermal.py`；`thermal_v2/builder.py:167/:458` R                          | 分层 FVM/RC 转成热电路，由已有数值后端求解；不是 FEM 或 COMSOL；各层横向材料均匀                    |
| 通孔位置→热模型         | **已实现且小例通过；等效精度未验证**                | `thermal_v2/geometry.py:19 footprint_cell_overlaps`；builder ΔG；one_macro_move probe R                              | 改的是对应热单元/表面节点导热；没有显式孔洞网格；同单元同权重的位置可能不可分辨                     |
| Joule heat               | **部分实现；保守映射测试通过**                      | `thermal_v2/mapping.py:157/:244`；`tests/unit/test_thermal_v2_mapping.py` R                                         | 已映射列和为 1、strict 拒绝正的未映射损耗；缺 die-included / internal / external 的物理账本         |
| 电热固定点               | **部分实现；正常/不收敛路径测试通过，诊断发现缺口** | `analysis/electrothermal.py:395`；`thermal_v2/electrothermal.py:137` R/S                                            | 可复用控制器；当前不是严格 actual-IV 闭环，最终状态/停止条件需修补，详见 §6                        |
| hard rebuild / 输入 hash | **已实现且小例通过**                                | `optimization/constraints_v2.py:570 FreshHardElectrothermalEvaluatorV2` R                                             | 每次重建 DC/热/maps；并未运行 optimizer；没有力学重建或完整 ETM 缓存                                |
| 校准/参考接口            | **接口与数据验证实现；外部物理验证缺失**            | `calibration/reference.py`、`calibration/preflight.py:59`；合成 reference array 测试 F                              | RMSE、LUT、误差门禁可复用；`fem_comsol` 来源标签不是 COMSOL 求解器                                |
| 3D-ICE / HotSpot 适配    | **当前包中缺失**                                    | 未找到可调用适配器/后端命令 S/R                                                                                         | 已有热网络可先复用，不因缺适配器重写求解器                                                          |
| 力学/COMSOL              | **缺失 + 外部依赖未获可用证据**                     | 无力学 solver、网格、材料本构、温度转移、应力结果读取、`.mph`/Java model/test；本机探测 R/S                           | 机械量必须 null + reason；不提供零应力占位                                                          |

表中省略共同包前缀 `cowos_l_tiv/`。测试命令、分组与结果见 `ETM_VALIDATION_RECORD.md`。

## 3. 真实调用链与三套输入的边界

```text
data/tap_50x50/multigpu.yaml（workload + 显式布局）
  ├─ legacy build_ckt.scale_design_to_grid -> build_op_ckt -> Circuit
  │    固定电流、单侧供电网、理想全局 return；不是完整三场 P/G 案例
  └─ [缺 TAP 适配/封装与工况扩展] -> 当前 normalized/compiled 链

case.manifest.yaml + floorplan/netlist/power_report JSON
  -> load_case_bundle -> NormalizedCase
  -> compile_case -> hashed compiled artifacts
  -> design_v2_from_compiled_artifacts + 显式电学配置 -> DesignSpecV2
  -> CandidateSpace + HardPlacementV2
  -> build_dc_v2 -> PreparedCircuit -> solve_dc_v2

独立 thermal 配置 + compiled instance-area mapping + 同 selected_option_ids
  -> build_thermal_v2 -> build_electrothermal_mappings
  -> solve_electrothermal_v2 -> DC(R(T)) + Joule + thermal
  -> [无 temperature-to-mechanics / mechanical solver / ETM result]
```

`case_schema_version: 1`（TAP 派生 YAML）、`schema_version: 1`（normalized/compile）、`schema_version: 2`（设计/热）不是同一个 schema。直接把 TAP YAML 传给 `load_design` 实测拒绝，错误保存在 `evidence/case_summary.json`。

单位与坐标：normalized JSON 入口显式换算到 SI；`cases/manifest.py:194` 仅接受 lower-left、x-right/y-up、局部 bump、半开边界。`parser.py:98` 把 bump 的局部坐标直接加到实例位置，未实现旋转。现有对象没有公共 z-stack/material-region/liner/ROI 定义。名称/ID 能追踪网格支路与 raw terminal，但没有真实逐孔实体 ID。不能以同一个 option 数字替代三场共享几何 hash。

`build_electrothermal_mappings` 检查相同 selected-option 顺序，未全面验证电热 case 身份、全部实例位置、层叠与材料一致性；数值权重守恒并不足以补齐这层契约。

## 4. P/G 闭环、通孔资源与几何传播

### 电学实际覆盖

v2 为每个 rail 建 front/back 有限电阻网，package source 与 package terminal 分开，负载电流源从局部 power front 连到配对 return front；P/G vertical 或 option 连通上下层。`common_ideal` 只钳位 package ground，front/back ground 没有全部归零；`separate_with_impedance` 明确加入 package return 阻抗。不同 return 的网格身份独立，package 之间是否等电位由 policy 决定，不能把 `common_ideal` 叫作完全隔离 ground。

真实解析测试得到共享 return 的负载电压 0.51 V/0.58 V、局部 ground 0.36 V；加 0.05 Ω package ground 后 ground bounce 为 0.15 V。负载不是另外叠加 ground sink。hard 模式去掉未选孔支路；v1 soft 的 `G_off` 是优化松弛支路，不是研究 hard 网络的物理连接。

局限：负载按 power bump 所在网格聚合，return 端接同一网格的 return rail；未把每个原始 G bump 的实际坐标逐一接入 die 网络。RDL 是 full-extent 等效网；package source 是简化边界。旧 `build_ckt.py:61` 使用理想 `vdd`、全局 0、硬编码 20 µm×100 µm TSV，无真实 G 通孔回路。它的常数不得冒充 TAP 技术数据。

### 物理宏不等于单孔

v1 宏已有 `n_power_vias/n_ground_vias`；v2 的可选 `physical_model` 有 P/return 孔数和圆柱尺寸，计算 `R=(rho L/A+Rc)/N`、总铜面积及 `ΔG=A_cu(1/(L/k_cu+R''c)−k_matrix/L)`。物理模型缺失的历史宏仍可仅提供 lumped R/ΔG，不能自动升级为已知铜量。

现有 Blackwell **独立参考配置** `blackwell_physics_v2_b4.yaml` 为 512 P + 512 G、直径 10 µm、高 0.5 mm、0.6×0.6 mm footprint。这是来源标注的 CoWoS-L-like 有效几何估计，不是 TAP 参数。宏名含 32×32，并未生成一份 1024 根孔的排列、衬层、净距和端点清单。

TAP 文件无已选宏/真孔数/尺寸，故本次其 `N_P/N_G/铜体积` 都是 **null**。1 mm 候选 pitch 不能解释为孔径、制造 pitch 或真实孔数。

### 位置进入三场的程度

| 位置对象    | 电学                                            | 热学                                                    | 力学               |
| ----------- | ----------------------------------------------- | ------------------------------------------------------- | ------------------ |
| site/option | site→电网 cell，连接真实有限 RDL 的 front/back | footprint→热 cell 精确面积权重；mold top/bottom 间 ΔG | 无消费端           |
| 宏内每个孔  | 未展开；P/G 各并联一个等效支路                  | 未展开；聚合铜面积作为增量                              | 无铜/衬层/基体实体 |
| 同资源移动  | 本轮小例端点、数值结果变化                      | 本轮小例 overlap、Joule map、温度变化                   | 无法检查           |

one_macro_move 探针仅移动现成 fixture 中一个可选宏，固定锚点不变，两个方案均为 2 宏（各宏 64 P+64 G、5 µm×0.2 mm）。fingerprint、DC 端点、热 overlap、Joule map 全部改变。它验证软件传播，不是 TAP 三布局试验，也不证明实际位置收益大小。

热基体背景 + 铜替换增量的公式避免了把整片背景和整孔铜导热简单相加；builder 还检查孔高与 mold 厚度、matrix k 一致。**这不是三维布尔扣孔/衬层体积互斥验证。** 各层仍为横向均匀等效材料，chiplet body 主要约束热源和温度观测，不能直接导出为真实力学芯粒实体。粗网格内等权重位置不可分辨，尚无 `subgrid_layout_unresolved` 状态。

## 5. 当前负载和热功率政策

TAP 派生 YAML 只有 legacy `vdd: 1`、芯粒 `power`，没有显式 analysis policy。它能推导额定 `I=P/Vnom`，不能凭此宣称 1 V 是 TAP 公开参数或 policy 已批准。

- v1：`builders/power_mapping.py:110` 用额定功率 / Vnom 得恒流；热源取固定 chiplet total power。
- v2：`cases/grid.py:350 build_instance_thermal_mapping` 明确使用 **connection.current_a × pair.nominal_voltage_v**；不是 DC 求解后的局部 Vp−Vg。`netlist_iv_power` 这个名称不能解释成 actual-IV。
- `thermal_v2/builder.py:357` 从固定 `instance_power_w` 组装 chip power；`with_joule_power` 只替换 Joule RHS。固定点不更新 die heat。
- 当前代码没有 `fixed_current_actual_iv` 或 `constant_power` 负载迭代。其语义接近规格的 `prescribed_heat_nominal_current`，但缺少政策枚举及热源与 actual-IV 差额的专门报告。

**本轮真实 synthetic_fixture 的能量账：**

| 项                   |                 W |
| -------------------- | ----------------: |
| 电源输出             | 3.400000000000085 |
| 实际负载 received IV | 1.544919652072744 |
| PDN 损耗             | 1.855080347927280 |
| 固定 die heat        | 3.400000000000000 |
| 叠加 Joule heat      | 1.855080347927280 |
| 注入热域总功率       | 5.255080347927279 |

电功率残差约 `6.15e-14 W`，热网络收支残差约 `1.78e-15 W`，现有 hard contract 仍可判 feasible；但热输入比电源输出多 `1.85508035 W`。两个单场守恒账均通过并不等于系统电热能量闭合。

这里不能仅凭缺失 scope 就断言所有现有案例把同一条片内线损算了两次。准确判定是：

1. 已映射支路的 Joule 算法按 I²R/V²G、列权重和为 1，无证据表明同一支路在映射中重复注入；P/G 分支各自计热是正确的。
2. 固定名义 die heat + PDN Joule 与实际 DC 功率账不一致；若把名义 die heat 解释为 source input，则损耗等价被重复计入热输入。若坚持 prescribed heat 近似，则必须显式声明额外热源及差额。
3. 没有 `heat_accounting_scope`、`external_loss_w`，也没有 raw die power 已含哪些片内/封装损耗的来源清单，因此无法排除物理范围重复计热。
4. v1 映射仅 RDL/TIV；v2 包括 package terminal、fixed vertical、option 和 RDL。package Joule 的两个分配层由配置指定（现 Blackwell 是 active/substrate），不是经空间路径验证的真实 C4 体积。`ground_reference` 的有限阻抗损耗没有默认归属，strict 会拒绝正的未映射损耗；需明确域外记账而非随意塞进芯粒。

## 6. 固定点、残差和热流的具体缺口

**F1：v1 用松弛后的步长作为收敛残差。** `analysis/electrothermal.py:431` 计算 `updated=ω*Traw+(1−ω)*T` 后检查 `|updated−T|`。本轮仅把既有合成小例设为 ω=1e−8、tol=1e−4 K、1 次迭代：返回 `converged=True`，记录 `5.07e−8 K`，实际未松弛固定点残差约 **5.065 K**。输出温度也不是这一轮原始热方程的解。需要在现有控制器中修补，不能让极小松弛人为通过门禁。

**F2：v2 已检查未松弛温度残差，但最终状态未同步复算。** `thermal_v2/electrothermal.py:159` 在 working T 上更新 R/DC/Joule，返回的是由该 Joule 得到的新 T；小于阈值即退出。没有在最终输出 T 上再次 DC 与热残差核对，也没有 ΔV、行缩放 KCL/KVL、跨场能量账联合门禁。默认 0.1 K/10 次的旧 Blackwell 设置不能自动成为新研究精度标准。超迭代明确返回 `fixed_point_not_converged`，这一行为已有通过测试，应保留。

**F3：热边界收支用绝对值。** `thermal_v2/builder.py:440` 累加 `abs(current[boundary_sink])`。零热源、上边界 308.15 K/下边界 288.15 K 的真实小例，稳态净边界流应为 0，代码却报告 0.118443316 W、残差 −0.118443316 W。所有边界只散热的常见工况不暴露该问题。需要带符号的 per-face 热流和 top/bottom/side 分类；目前的总量不可推广到有热流入的边界。

**F4：部分“功率残差”是定义恒等式。** `analysis/dc_v2.py:199` 把 pair transfer 定义为 source−load−allocated_loss，再从同式扣掉 transfer 得 residual，按构造为 0；它不是独立守恒校验。全局 `source−actual_load−Joule` 是有效独立检查。`DcV2SolverDiagnostics` 目前主要记录维度/finite，不含分电流方程和电压约束的残差。

**F5：材料、路径和采样精度未完成物理验证。** RDL 采用端点各半权重；TIV 用 footprint 权重×上下层各半，未沿实际孔长积分，也未显式测取孔中部温度。v2 普通支路使用按 kind 定义的 TCR/铜占比；物理宏支持独立 bulk/contact，接触温度政策固定。无材料有效温区、全路径几何及电/热 reference-state 的统一契约。

以上是本轮审计发现，不在本次修复；正常测试通过不覆盖这些反例。

## 7. hard rebuild 与缓存

`FreshHardElectrothermalEvaluatorV2.__call__` 每次重新建 DC、thermal 和映射，再调用既有电热 solver；两次相同输入得到不同 rebuild_id、相同 input_fingerprint、不同 build 对象。hard placement 必须匹配 candidate-space hash，soft/stale 输入拒绝。独立探针也证明移动一个宏传播到两场几何映射。

fingerprint 包含 resolved electrical design、candidate space、thermal design、稀疏 overlap、selected options、constraints、backend 名称；**不含 backend/solver 版本、逐孔/衬层实体、机械 BC/ROI**。当前它主要标识 fresh evaluation，不是全三场结果缓存。B2 compile cache 包含 raw/manifest/config hash 和 compiler version，生成文件有 hash 校验；本轮 tiny compile 首次 miss、二次 hit、重新读取成功。不能拿这两个局部机制宣称所有 ETM 状态均已失效重建。

## 8. 外部后端与机械可用性

本机实际运行环境见 `evidence/environment.json`：Python 3.11.13，NumPy 1.26.4、SciPy 1.17.1、Torch 2.2.2、pytest 9.0.2，临时 venv 补 Matplotlib 3.10.8。与仓库历史 Linux/CUDA 锁定环境不同。

本轮已真实求解 SciPy 小例。PARDISO 与 cuDSS smoke 明确报 `No module named op_sim_cpp/op_sim_cuda_cpp`，CUDA unavailable；没有通过 mock 替代，也没有把 skip 写成 pass。PATH 无 `comsol/comsolbatch`，常见本机安装根目录未发现 COMSOL；选定环境无 `mph/dolfin/dolfinx/sfepy/gmsh`，PATH 无 `ccx/ElmerSolver/FreeFem++`。仓库无实际力学实现与模型工件。

结论是**当前本机没有找到可调用的 COMSOL/力学后端**；不是断言用户其他机器没有安装。未访问远程服务器、未申请许可证、未确认 COMSOL 版本/模块/批处理能力。后续需要用户提供实际目标安装路径/主机、版本、Solid Mechanics/热膨胀许可或已有参数化模型，才可继续验证。`calibration` 的来源标签和参考数组/LUT 测试均不构成这些证据。

研究状态应为 `missing_parameters` + `backend_unavailable`（本机探测范围），stress 为 null；未来任务包可以标 `pending_external_solver`，但当前尚未实现该任务包。

## 9. 本轮验证与停止位置

现有测试最终 **130 passed，0 failed，0 skipped**：data/DC 62、thermal/ET 53、macro/hard/reference-contract 15。首次因 Matplotlib 缺失而 collection 失败的日志已保存；补依赖后重新运行成功。审计探针初版漏传 backend 的脚本错误也保留日志，修正仅在本审计脚本中；不是求解器失败。

额外真实运行：20-cell compiler/cache/read、有限规模 hard move、功率记账、v1 过早收敛反例、热流符号反例、后端 smoke。没有大案例电热求解或完整 AC/优化回归；生产代码未变，不需要通过启动优化来验证此审计。

P0 交付已完成；P1–P6 未执行。应优先解决 TAP 接入/参数冻结、能量政策和物理孔身份，再复用现有电热模型，最后接入并验证真实机械后端。详见参数缺口表及最小修改计划。
