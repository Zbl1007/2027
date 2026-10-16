# 与 mypdn 的复用边界

新项目负责参数、来源、案例、适配编排和研究验证。2026-10-16 用户明确指定热后端为 Zbl1007/3d-ice、COMSOL 在另一台电脑作交叉验证/力学；不在本项目重新实现求解器。mypdn 仍作为只读参考，保留其输入和 DC 的后续复用方向。

| 能力 | 已审计的现有入口 | 后续策略 |
|---|---|---|
| 输入与编译 | `cowos_l_tiv/cases/parser.py`、`compiler.py`、`design/v2.py` | 使用现有 normalized/compiled 链，增加 TAP 薄适配 |
| DC | `Circuit.py`、`OpSimulation.py`、`builders/dc_v2.py`、`analysis/dc_v2.py` | 复用有限 P/G 网络与数值后端 |
| 孔宏 | `candidates/types.py`、`candidates/physics.py` | 保留等效公式，补共享实体和逐孔 realization |
| 热与映射 | `thermal_v2/builder.py`、`geometry.py`、`mapping.py` | 参考面积映射/Joule/R(T) 数据合同；主热求解由锁定的3D-ICE承担，避免双重计铜或并行复制热后端 |
| 电热迭代 | `thermal_v2/electrothermal.py` | 后续评估复用控制器并替换热调用；当前未接入，仍需处理已有政策与停止条件问题 |
| 固定布局重建 | `optimization/constraints_v2.py:FreshHardElectrothermalEvaluatorV2` | 只编排给定 hard 布局；不调用优化搜索 |
| 力学 | 旧仓库尚无真实可用实现 | COMSOL最小任务包先验证，结果未返回时保持null；不生成mock机械结果 |

现在只记录入口，不复制生产源码，不导入或执行旧求解器。`sources/catalog.json` 与 `references/import_manifest.json` 记录静态参考版本；没有安装对 mypdn 的 editable dependency。

小算例使用 `external/3d-ice` 的独立可运行 checkout，锁在 `sources/three_d_ice.lock.json`；实际工作树文件hash与编译信息另存 `verification/three_d_ice_build/build.json`。不是从 `references/` 运行脚本。新脚本只生成输入、调用求解器、解析输出、检查数据/解析解，不离散或求解新的热/力方程。

正式接入前需确定可重复的依赖交付方式并记录源文件 hash。旧仓库工作树有未提交实现，不能通过只锁定 Git HEAD 就宣称锁住了实际代码。也不能把只含 HEAD 的新 checkout 当成审计时的完整实现。

旧模型的实际问题继续保留：负载/热功率政策未闭合、v1 松弛步长停止漏洞、热边界绝对值统计、v2 最终状态复算不足。修复它们属于后续实现；新建目录不表示这些问题已经消失。
