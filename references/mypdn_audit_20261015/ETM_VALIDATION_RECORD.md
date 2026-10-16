# P0 实际验证记录

本轮日期 2026-10-15。只验证现有实现与审计发现，不执行研究案例全模型或优化。完整命令（逐参数 argv）、退出码、耗时见 `evidence/test_runs.json`。

## 环境与初次阻塞

本机已有 Python 3.11 的 `mcp_claude` 环境具备 NumPy/SciPy/Torch/PyYAML/pytest，但缺 Matplotlib；case compiler 在 import 时导入报告绘图模块，导致选定测试首次 collection 失败。原始记录保存于 `evidence/initial_environment_blocker/`，退出码分别 2、2、4，**不计入通过数量**。

创建临时 `/tmp/mypdn-etm-p0-20261015-venv`（system-site-packages）并仅为测试补 Matplotlib 3.10.8 及其小型依赖，未修改项目 requirements 或既有环境。安装日志见 `evidence/test_environment_setup.log`。最终 Python/库/平台版本见 `evidence/environment.json`，不是历史 Linux/CUDA 版本。

## 现有测试结果

| 分组 | 结果 | pytest 内部时间 | 覆盖 | 原始证据 |
|---|---|---:|---|---|
| data_dc | 62 passed / 0 failed / 0 skipped | 4.80 s | TAP 派生布局、normalized/CLI/网格/缓存键、SI、schema、PreparedCircuit、hard-off、双 P/G、共享/独立回流 | `evidence/data_dc.log`、`.xml` |
| thermal_et | 53 passed / 0 failed / 0 skipped | 3.52 s | 热公式/映射/解析解、宏 footprint、R(T)、Joule、两个版本固定点/重试/不收敛 | `evidence/thermal_et.log`、`.xml` |
| physics_hard | 15 passed / 0 failed / 0 skipped | 4.19 s | 圆柱宏公式、非法铜占比、hard placement、fresh rebuild、stale 拒绝、SciPy hard solve、校准数据契约 | `evidence/physics_hard.log`、`.xml` |
| 合计 | **130 passed，0 failed，0 skipped** | 12.51 s | 本轮选择集合 | `evidence/test_runs.json` |

这些测试中的求解器调用是真实 SciPy；fixture 的几何/材料是合成输入，不是 TAP 研究参数。校准测试使用手工 reference arrays/LUT，只验证映射、指标和有效范围逻辑，**不是独立 FEM/COMSOL 验证**。现有 SciPy CSC 转换 warnings 已保留，未掩盖失败。

精确选择集保存在 `scripts/run_existing_checks.py`；没有调用 optimizer test 或搜索入口。fresh evaluator 虽位于 optimization 包中，执行的只是已有固定 hard 布局的 rebuild/evaluate。

## 补充审计探针

驱动 `scripts/collect_audit_evidence.py` 只调用现有 parser/compiler/builders/solvers，未实现新求解器。日志 `evidence/audit_probes.log`。初次驱动漏传 `solve_dc` 必需的 backend 参数，原始错误留在 `audit_probe_driver_initial_error.log`；修复审计脚本后完成重跑。该错误不归因于被审计 solver。

| 探针 | 实际结果 | 可证明 / 不可证明 |
|---|---|---|
| TAP 原始 cfg 来源 | 固定 commit 可读，blob SHA 与声明相符 | 证明尺寸/功率/矩阵来源；没有证明论文布局 |
| TAP YAML→现有 load_design | 明确拒绝，错误见 case_summary.json | 证明格式接入缺口；没有补默认参数 |
| 20-cell 合成 bundle compile→read→cache | 首次 miss，第二次 hit，hash 一致，load 成功 | 验证实际编译器；非完整 Blackwell/TAP 编译 |
| 严格能量账诊断 | 单场残差接近零，但热输入比电源多 1.85508035 W | 复现 nominal-heat 与 actual-IV 不同；非研究功耗估计 |
| 同数宏移动 | 2 宏保持，端点/热权重/maps/fingerprint 改变 | 真实两场位置传播；无机械传播，无优化排序 |
| v1 松弛停止 | 记录步长 5.07e−8 K，真实 raw 差约 5.065 K，仍 converged | 复现停止条件漏洞；未改生产代码 |
| 混合冷热边界 | 零热源却报净散热 0.118443316 W | 复现 abs 边界流记账问题；不是不守恒的物理解 |
| 本机 DC 后端 smoke | SciPy solved；PARDISO/cuDSS 明确 unavailable | 实际可用性；不以历史服务器日志或 mock 填补 |

探针数值完整保存于 `evidence/numerical_probes.json`。包含温度变化的值仅说明合成小模型的软件行为；禁止作为 TAP 温升、压降或位置收益发表。所有机械量保持缺失，未调用任何力学 mock。

## 重现命令

在仓库根目录运行（临时环境仍存在时）：

```sh
PYTHONDONTWRITEBYTECODE=1 /tmp/mypdn-etm-p0-20261015-venv/bin/python -u audit/etm_p0_20261015/scripts/run_existing_checks.py
PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 /tmp/mypdn-etm-p0-20261015-venv/bin/python -u audit/etm_p0_20261015/scripts/collect_audit_evidence.py
/usr/bin/python3 audit/etm_p0_20261015/scripts/verify_deliverables.py
```

测试驱动每组上限 180 s。临时目录可能被系统清理；重新建立兼容环境时，按 environment.json 复用真实库版本，不通过 mock 掉缺失依赖来跑“通过”。原始补环境命令：

```sh
/Users/zbl/opt/anaconda3/envs/mcp_claude/bin/python -m venv --system-site-packages /tmp/mypdn-etm-p0-20261015-venv
/tmp/mypdn-etm-p0-20261015-venv/bin/python -m pip install 'matplotlib==3.10.8'
```

## AITDD 与范围限制

Topic/Issue/Iteration：`CoWoSLTIV / ETMModelingAudit / v0.1.0`。本次采用单轮紧凑计划，不创建长期 Planning Plan。独立记录避免将最少通孔优化的旧验收归到本审计。

`validate-current`、`validate-resolution`、`validate-iteration` 和 `run --dry-run` **均退出 0，通过结构/配置检查**；日志见 `evidence/aitdd_validation.json`、`evidence/aitdd_*.log`。dry-run 只解析验收声明，**不是正式 Run 的 pass**；实际测试与探针来自上面的真实命令。

正式 run 不属于本次请求，依项目 explicit policy 未执行；不生成正式 AcceptanceReport/Result、不把 Iteration 从 pending 冒充为正式 pass。P0 文档交付状态与研究三场模型状态分别报告：前者完成，后者 missing_parameters/backend_unavailable。

本机 COMSOL/机械验证、服务器 PARDISO/cuDSS、完整 TAP、热/机械三档精度收敛均无本轮运行结果。审计报告已明确其物理或环境限制。未修改核心代码，不触发完整 AC/优化回归，也未为得到测试结果而启动优化。
