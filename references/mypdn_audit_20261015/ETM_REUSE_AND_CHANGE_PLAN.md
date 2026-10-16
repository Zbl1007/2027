# ETM 最小增量修改计划（建议，未执行）

依据当前 P0 审计。当前授权到审计为止，下述为后续实施范围；不启动任何搜索或优化。优先复用 v2 typed case/builders、现有 MNA 与热网络，兼容保留 v1、CoWoS-L-like、Blackwell、Ascend910、AC 和现有优化流程。

## 保留、扩展与新增

| 分类 | 模块 | 最小动作 | 兼容性要求 |
|---|---|---|---|
| 保留 | `Circuit.py`、`OpSimulation.py`、现有数值后端 | 直接调用；不写第二套 DC/热稀疏求解器 | 不改变已验证 stamping、backend ABI、AC/伴随 |
| 保留并扩展输入 | `cases/parser.py`、`manifest.py`、`compiler.py`、`grid.py` | 在现有 normalized/compiled 链加入 TAP 薄适配，复用 SI、hash、精确面积映射 | 原 JSON bundle 格式及源 hash 不被覆盖 |
| 扩展 | `design/v2.py`、`candidates/types.py`、`candidates/physics.py` | 共享实体/材料/z-stack 与逐孔 realization；保留并联宏公式 | 缺少物理孔数据的旧宏仍可运行旧模式，不能获 ETM 研究资格 |
| 扩展 | `builders/dc_v2.py`、`analysis/dc_v2.py` | 加几何/材料/热归属、实际负载定位、独立残差和按孔/宏统计 | 不把旧 P/G 端点或 ground policy 静默改掉 |
| 扩展 | `thermal_v2/{types,builder,geometry,mapping}.py` | 共享技术层类型、体积/热流/覆盖信息及有符号边界账 | 保持旧 mold layer 与已有 footprint ΔG 路径 |
| 修补 | 两个现有 electrothermal controller | 修正 v1 残差，增加显式功率 policy、最终状态复算和失败门禁 | 旧 policy 默认行为保留并明确命名；新模式 opt-in |
| 扩展 | `FreshHardElectrothermalEvaluatorV2`、artifact/manifest | 复用 fresh rebuild，加入全物理输入与 backend-version/ROI hash | 不复用旧数值 LU；保留旧 artifact schema/结果 |
| 新增最薄后端边界 | mechanics adapter + task/result contract | 对接真实可用 COMSOL 或批准的其他线弹性后端 | 无后端/缺参数返回 null+reason；mock 严格隔离 |
| 新增 profile | 独立 TAP `silicon_interposer` | 只填有来源且确认的参数；旧 CoWoS-L 不覆盖 | 不能仅替换 molding material；禁止默认复制 Blackwell 值 |

## 建议实施顺序与停止条件

### A. 冻结案例与参数契约（P1 最小范围）

前置步骤（2026-10-16 补充）：先完成 [逐参数文献溯源](ETM_LITERATURE_PROVENANCE_ADDENDUM.md)，区分官方模型取值、其他工艺参数及需要推导的设计选择；不要求用户凭空填数。来源核查和采用决定完成后再冻结配置。

1. 保留当前 50×50 显式布局及尺寸派生标签；把 CPU/GPU/HBM 数组 ID 映射、单位、左下角、朝向写入 manifest。若要恢复官方尺寸，必须另建版本并重新检查合法性，不能悄悄改旧布局。
2. 新增 TAP cfg 到现有 normalized case 的薄适配/映射；TAP 没有的 bump/供电/工艺不在 parser 中默认补齐。明确保留 nominal/declared power，不生成独立的三套 raw parser。
3. 固定 P/G 各 rail 真孔预算和尺寸；把宏展开为带稳定 via_id 的孔位置、铜/衬层/基体、上下端点及固定结构。电热仍可使用聚合宏，但必须能由实体列表复算孔数、铜体积和端点。
4. 增加公共 stackup/region/material/provenance/approval/reference-temperature；在缺口未确认时给 missing_parameters。ETM 检查 mode 不允许 fixture 数据满足 research gate。

验收：现有导入/编译回归；新 TAP 原始字段核对；坐标/朝向/body+bump 同步；孔数/铜体积、边界/重叠、缺参拒绝和旧 profile 不变。未确认供电、孔/层叠参数时停止研究 evaluate，可保留解析 fixture。

### B. 电学与功率账修补（P2）

1. 沿用 `build_dc_v2` 的有限 return 和 package 网络；明确哪些 bump/接触是等效、哪些需要显式。保留 shared return 与独立 ground，不在 TSV 新位置放理想源，不以 Gmin 接通断路。
2. 增加支路 `heat_accounting_scope` 与空间归属：die-included、内部、外部；对已计入 die 的损耗只报告不再注热。输出全局 source/actual-load/internal/external loss，别把 pair 的定义性 residual 当独立证据。
3. 将旧政策显式命名为 nominal-current/prescribed-heat；新研究 policy 经配置选择 `fixed_current_actual_iv` 时按 chiplet load 的最终局部 IV 更新 heat，保留 755 W nominal；若研究要求实际计算功率完全相同，再单独实现/验证 nonlinear constant-power，不把它塞入 P0。
4. 增加有符号 load drop、实际负载位置、per-via（明确并联均流假设）/macro 电流密度与分单位 KCL/KVL 残差。

验收：复用双 P/G、共享 return、独立 ground 小例；检查全局电功率残差、断路失败、TCR off、不同材料/TCR 和接触不缩放；新模式严格检查热输入与实际 IV，不修改旧实验 policy。

### C. 热模型与固定点质量（P3）

1. 在现有热 builder 扩展中介层材料角色，保留 mold 路径并独立加入 silicon profile。共用几何与铜占比，防止固定背景等效铜与可变孔再次叠加；加入衬层/横向/接触的有效范围。
2. 延用 exact-area 热源/footprint 映射，增加耗散层 z/厚度和一致性 hash；跨粗单元不分辨的位置显式标 unresolved。
3. 修正 boundary sink 的绝对值求和，导出带符号 per-face 热流、top/bottom/side 比例、功率账与 field x/y/z/region。
4. 修正 v1 用松弛步长停止的问题。v2 增加温度/电压变化、方程残差与跨场能量条件；最终 T 上复算 DC 与热残差，保存同一最终状态。未收敛保持明确失败。

验收：复用已有 slab/多层/界面/对流/映射测试；加入本轮两个真实反例；零源同温；真实单孔/小阵列显式或独立参考；三档温度网格收敛。现有三档 footprint ΔG 守恒和合成 reference arrays **不能**替代温度误差收敛/独立 FEM。

### D. 真实机械后端先行验证（P4）

1. 先确定可用目标环境和用户已有 `.mph`/Java 参数模型、COMSOL 版本/模块/许可证；仅做受控小例，不自动安装大型 FEM 软件或提交远程作业。
2. 新建 adapter 消费同一编译物理设计和真实温度场，显式几何扣孔、衬层/界面连接、机械支撑、T_sf、E/ν/CTE、ROI。不能用热边界代替力学固定边界。
3. 必须跑零温差、自由膨胀（有位移且近零应力）、受限杆解析解、异 CTE 孔阵列、三档网格与域尺寸收敛。输出真实 solver log、场文件和 coverage。
4. 自动后端不可用时可按后续授权完成任务包导出/结果导入；状态 pending_external_solver。缺失应力为 null，禁止零应力、经验 EαΔT 场或 mock 冒充求解结果。

停止条件：没有真实后端、机械参数或边界，就不能关闭 P4 的物理验证。材料允许值是“安全/无屈服”结论的额外门槛，不把缺疲劳参数误当线弹性首版必需阻塞。

### E. 同 case 联评与同资源位置验证（P5–P6，后续单独执行）

复用现有 fresh evaluator 编排 DC/thermal，再调用 mechanics adapter；不要复制第二套电热迭代器。统一 Result 的状态、nominal/actual power、守恒、版本、网格、coverage/ROI 定义和资格门禁。先小结构验证，再决定全局—局部；缺少覆盖不能命名 global_sigma_max。

参数、后端与模型质量满足前提后，才冻结 uniform/load-biased/hotspot-biased 三组合法布局；固定真实 P/G 孔数、直径、高度、铜体积、负载/边界与固定信号结构。分别报告 T/D/S、数值误差和电热功率差额，弱效应记 effect_not_resolved。本轮未创建这三组布局，也未预设哪组更好。

## 当前最小阻塞集合

先处理参数表 G01–G15 的 case/geometry/electrical 定义，G16–G23 的热源和功率账，以及 G24–G30 的真实机械条件。软件上优先修复审计 F1/F3 并补显式政策，再做最终状态质量门禁；其余字段增量沿现有类型扩展。优化器、代理、伴随新算法和全尺寸 FEM 均不属于这份最小计划的前置任务。
