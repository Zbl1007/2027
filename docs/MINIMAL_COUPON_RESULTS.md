# 最小算例：本轮结果与边界

日期：2026-10-16。3D-ICE 后端为用户指定仓库 Zbl1007/3d-ice，提交 `4953952a1ef6d38807ff307212a6f15e5b2ef935`。运行平台 macOS arm64；Apple Clang 16 + OpenMP + OpenBLAS + SuperLU_MT 4.0.0。实际构建命令、源码工作树 hash、二进制 hash、链接库和原始日志在 `verification/three_d_ice_build/`。

2026-10-19 更新：H0 已用 Windows COMSOL 6.3.0.290 完成两档真实独立求解；同一 16 点与 3D-ICE 最大差异为 0.000939002380 K，COMSOL 两档变化为 2.15e-11 K，回填数值检查通过。模型、功率积分和操作记录见 [COMSOL_H0_RESULTS.md](COMSOL_H0_RESULTS.md)。以下 3D-ICE 历史数值保持原样。

## H0 已有真实解析对照

| z 层数 | 单元中心最大绝对误差 / K | 相邻误差比 |
|---:|---:|---:|
| 4 | 0.01502403846 | — |
| 8 | 0.00375600960 | 4.00000001 |
| 16 | 0.00093900240 | 4.00000001 |

在本次连续问题和给定阈值下，最细网格误差≤0.001 K，误差随纵向步长减半约缩小4倍。**这只说明 H0 的网格渐近行为和所声明误差目标通过，并不代表整个求解器或异质材料模式已经充分验证。**

VTK 温度输出原为 `%7.3f`，会损失这个误差量级的信息。唯一源码补丁 `patches/3dice-vtk-precision.patch` 将温度文本改为17位有效数字，并将相应 VTK scalar 类型标为 double。没有修改离散方程、功率分配或线性求解器。

## 发现的底层误差

`sources/thermal_grid.c` 的 `get_conductance_non_uniform_z`（锁定提交约第553–569行）在普通 SOURCE/SOLID 的第0层使用整个单元高度作为竖向分支距离，内部层使用半高。按本包 VTK 几何的单元中心解释，底部两相邻中心之间应由两个半高度组成。

实测 H0_z4：最底层中心误差0.01502403846 K，其余中心误差约0.00300480769 K；差值0.01201923077 K与这一额外半层热阻的预测相符。这项源代码和数值证据表明，粗网格底层偏差不能当成 COMSOL 边界设置问题。本轮保留原分支行为以建立可追溯基线；后续后端修复必须另存补丁、重锁 hash 并复跑本包，不能覆盖本轮基线冒充原版本结果。

## H1 运行结果，尚未验证位置效应

| 每区域横向分段 / z层数 | 单元数 | 居中最高单元温度 / K | 偏移最高单元温度 / K |
|---:|---:|---:|---:|
| 2 / 4 | 144 | 305.453079302 | 305.453589874 |
| 4 / 8 | 1152 | 305.427651815 | 305.428149825 |
| 8 / 16 | 9216 | 305.412931791 | 305.413510325 |

两种位置的硅/铜/SiO2体积和总功率相同。输出检查覆盖单元数、坐标范围、区域体积、正温度、唯一采样点以及由顶层单元温度重建的散热平衡。逐次源功率/散热误差见 `verification/minimal_coupon_validation.json`。

最细档位置差约0.000578534 K，居中模型最后两档网格的峰值变化约0.014720024 K。峰值变化还包含采样点位置变化，不能据此直接估计严格误差界；但目前证据显然不足以认定细微位置效应。应先完成 COMSOL 固定点交叉验证，再决定非均匀网格改进和圆柱几何验证。

## 尚未完成的部分

- 原始参数包没有 COMSOL 求解结果；H0 已在 2026-10-19 单独完成并另存结果包。COMSOL H1、人工 GUI 设置复核和 M0/M1 仍未完成。
- M0/M1 力学结果均未产生；应力是 null。任务单的自由膨胀零应力和轴向压应力都是解析参考，不是求解数据。
- 3D-ICE 中心温度到 COMSOL 全机械域的插值/边界覆盖尚未实现。M1 初步使用经过热交叉验证的 COMSOL 自身温度场。
- TAP 全尺寸研究案例仍缺参；本轮测试材料与几何不自动采用到研究台账，也未接入 DC、电热迭代或优化。

## 本机重现

Python 3.9+。`prepare/run/import/package` 均只使用 Python 标准库；热求解必须调用真实 3D-ICE 可执行文件。

```sh
# 本机已有依赖时构建；不会自动安装依赖
/usr/bin/python3 scripts/build_3dice.py
/usr/bin/python3 scripts/prepare_coupons.py
/usr/bin/python3 scripts/run_coupons.py
/usr/bin/python3 scripts/test_coupons.py
/usr/bin/python3 scripts/validate_provenance.py
/usr/bin/python3 scripts/package_coupons.py
```

构建脚本目前针对本机 macOS/Homebrew 路径，不能声称跨平台已验证。本轮为构建安装了 OpenBLAS、libomp、Bison；OpenBLAS 的 Homebrew 依赖带入了 GCC 等。Homebrew 首次安装同时自动更新了自身；GCC 16 与本机 SDK 头文件不兼容，最终使用 Apple Clang。Linux/Windows 的 COMSOL 侧不需要这些构建依赖，仅需要任务包和 COMSOL；回传校验需要 Python。

包内原始日志的内存数字未经平台单位核对，不作为性能测量。构建中有上游语法弃用/格式警告，未将它们改写成求解器变更。
