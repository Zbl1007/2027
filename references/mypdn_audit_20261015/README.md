# TAP ETM P0 审计交付

本文件夹仅交付 2026-10-15 的建模前审计，**未开始优化或三场模型实施**。

2026-10-16 来源补充：TAP 官方热模型含可追溯的 TSV/层叠/边界参数；本地尚未采用。先读 [参数文献溯源补充](ETM_LITERATURE_PROVENANCE_ADDENDUM.md)，区分“本地缺参”“公开来源存在”和“已批准采用”。

| 文件 | 内容 |
|---|---|
| [ETM_IMPLEMENTATION_AUDIT.md](ETM_IMPLEMENTATION_AUDIT.md) | 实现/接口/缺失/后端状态、真实调用链、几何与功率政策、复现问题 |
| [ETM_PARAMETER_GAPS.csv](ETM_PARAMETER_GAPS.csv) | 36 项参数/契约缺口，单位、影响、可用来源和阻塞条件 |
| [ETM_REUSE_AND_CHANGE_PLAN.md](ETM_REUSE_AND_CHANGE_PLAN.md) | 保留/扩展/新增边界、最小实施顺序和停止条件 |
| [ETM_CASE_PHYSICAL_SUMMARY.md](ETM_CASE_PHYSICAL_SUMMARY.md) | 当前六芯粒布局、755 W 名义功率、官方尺寸差异、物理缺参和规模公式 |
| [ETM_VALIDATION_RECORD.md](ETM_VALIDATION_RECORD.md) | 130 项现有测试结果、真实小模型诊断、环境与重现命令 |
| [ETM_LITERATURE_PROVENANCE_ADDENDUM.md](ETM_LITERATURE_PROVENANCE_ADDENDUM.md) | 官方热模型候选参数、工艺/力学参考及 P/G 数量证据边界 |
| `evidence/` | 原始日志、JUnit、输入 hash、来源 cfg、环境和探针数据 |
| `scripts/` | 有界测试驱动、证据采集、交付完整性检查；没有新求解器 |

当前最重要的结论：DC/热网络/R(T)/Joule/hard rebuild 可复用；TAP cfg 适配和逐孔三维几何缺失；现有名义恒流/固定热源不满足严格 actual-IV 闭环；没有找到本机可调用的 COMSOL 或真实力学实现。缺失应力不填写零。

130 项测试通过只覆盖所选现有小模型与数据契约。审计另复现 v1 固定点过早停止、热边界绝对值收支错误；具体数值与源码位置见审计。没有把 mock、合成 reference 数组或旧服务器日志当作 TAP 三场结果。
