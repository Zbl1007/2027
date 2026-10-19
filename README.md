# TAP25D ETM

独立研究工作区：在同一固定芯粒布局、固定 P/G 通孔数量与尺寸下，为电学、热学和热机械应力模型准备可追溯输入。

当前阶段是 **参数溯源 + 3D-ICE—COMSOL 最小算例验证**。已用真实 3D-ICE 跑通独立测试算例；2026-10-19 在 Windows COMSOL 6.3.0.290 完成 H0 两档真实求解、保存模型回读和固定 16 点数值回填检查。TAP 全尺寸模型仍缺参，没有三场求解结果，没有启动优化，也没有把测试参数自动采用为研究参数。

## 现在从这里开始

- [COMSOL H0 验证报告](docs/COMSOL_H0_RESULTS.md)：两档已求解模型、完整日志、温度、积分、hash 和失败记录；[结果包](deliverables/comsol_h0_validation_20261019.zip)。仅 H0 数值验证通过，人工 GUI 复核未执行。
- [COMSOL 操作任务单](docs/COMSOL_TASK.md)：保留建模定义；H1、M0 是后续工作，本轮未启动。
- [可携带任务包](deliverables/3dice_comsol_minimal_v1.zip)：参数导入文本、几何分区、采样坐标、真实 3D-ICE 输出、回传模板和校验脚本；无已求解 `.mph`。
- [本轮结果与已知限制](docs/MINIMAL_COUPON_RESULTS.md)：H0 解析收敛通过，H1 位置差异尚未分辨，并记录非均匀底层导热距离偏差。
- [统一 SI 定义](cases/minimal_coupons/definition.json) / [测试参数来源](cases/minimal_coupons/provenance.json)：独立 `synthetic_fixture`，不覆盖 TAP 参数台账。

## 先读这些文件

| 文件 | 用途 |
|---|---|
| [docs/STATUS.md](docs/STATUS.md) | 当前完成项、缺口与下一步 |
| [docs/PARAMETER_PROVENANCE.md](docs/PARAMETER_PROVENANCE.md) | 可读的逐参数来源表：候选值、出处、适用限制 |
| [parameters/registry.json](parameters/registry.json) | 参数台账的结构化主数据；selected_value 为 null 表示尚未采用 |
| [parameters/gap_registry.json](parameters/gap_registry.json) | 延续原审计的 36 项缺口，附已找到的候选来源 |
| [sources/catalog.json](sources/catalog.json) | 官方代码/论文/本地参考的访问范围、链接和快照 hash |
| [docs/REUSE_BOUNDARY.md](docs/REUSE_BOUNDARY.md) | 后续如何复用 mypdn，避免重写求解器 |
| [cases/tap_multigpu_research_definition.json](cases/tap_multigpu_research_definition.json) | 固定布局起点与尚未定义的物理输入；不是 solver-ready 配置 |
| [references/mypdn_audit_20261015/README.md](references/mypdn_audit_20261015/README.md) | 旧仓库审计及证据快照 |

## 目录与来源

本目录与 `../mypdn` 同级，是独立 Git 仓库。`references/` 保存原审计、用户设计文档、当前派生布局和已核查官方代码的逐字节快照；`references/import_manifest.json` 记录原路径及 SHA-256。

旧仓库审计里的源码路径仍指向当时的 mypdn；历史脚本只用于追溯，不能直接当成本项目运行入口。用户设计文档描述目标，提示词文件描述后续可能的任务，均不自动授权实施。

## 运行当前检查

只依赖 Python 3 标准库，不需要安装求解器或科学计算依赖：

```sh
cd /Users/zbl/Desktop/docker/code/tap25d-etm
/usr/bin/python3 scripts/validate_provenance.py
```

检查快照 hash、来源关联、参数状态、引用行号及缺口覆盖，输出 `verification/provenance_validation.json`。检查通过只代表资料完整性通过；研究模型仍是 `missing_parameters`，机械应力仍为 null。

## 研究模型的后续工作

1. 逐参数核对原文或固定提交源码，记录取值和物理含义。
2. 解决 TAP 官方热模型与本地电学参考的尺寸、材料和铜量冲突。
3. 为 P/G 孔数、负载政策、机械材料与边界寻找直接来源或有依据的推导条件。
4. 先完成最小算例交叉验证，再接入 mypdn 的现有 DC/输入链；热后端按用户决定使用 3D-ICE，真实力学使用 COMSOL，详见复用边界。

本轮已创建本地项目。Codex 侧栏尚未注册：现有工具没有创建本地项目接口，界面自动化被工具安全限制拒绝。可按[官方项目说明](https://learn.chatgpt.com/docs/projects)在侧栏添加此目录；这不影响本目录中文件的独立性。
