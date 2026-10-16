# 3D-ICE—COMSOL 最小一致算例：操作任务单

日期：2026-10-16。当前包已经包含真实 3D-ICE 结果；COMSOL 尚未运行。它是可在另一台电脑照步骤建立的模型任务包，**不是已经求解的 .mph 文件，也不需要 LiveLink for MATLAB**。菜单按 COMSOL 常见 6.x 界面描述，具体版本可能略有不同。

## 本次先做什么

**先只做 H0：一个硅长方体。** 用 `h0_z16/comsol_parameters.txt` 的参数，在 COMSOL 建好并跑通，然后导出 `h0_z16/sample_points_m.txt` 指定的 16 个点。第一次回来只需要这个 H0 模型、日志和两档 COMSOL 网格的温度表。后面的 H1、M0 是后续步骤，不必一次做完。

任务包根目录下，算例实际位于 `outputs/minimal_coupon_v1/`。下文的 `h0_z16/` 等名称均相对于该目录。`definition.json` 是统一 SI 参数主表；`materials_si.csv` 是便于查看的派生表；每个 `contract.json` 记录该算例的几何、功率、网格及输入 hash。

## H0：均匀硅块

1. 新建 **3D → Heat Transfer in Solids（固体传热）→ Stationary（稳态）**。
2. 在全局参数中导入 `h0_z16/comsol_parameters.txt`。如果版本不能读该文本格式，按其“名称、表达式”两列粘贴。几何的长度单位设为 **m**；所有参数表达式自带单位。
3. 创建 Block，大小 `Lx,Ly,Lz`，基点 `(0,0,0)`：即 0.01 m × 0.01 m × 0.0001 m。**z=0 是底面，z=Lz 是顶面。**
4. 新建空白材料，选整个硅域；导热率 `si_k`、密度 `si_rho`、定压比热 `si_cp`。不要使用材料库随温度变化的默认值。比热由 Cv/ρ 得到；本轮只验证稳态，不验证瞬态。
5. 整个域添加 Heat Source：`qSi=5e9[W/m^3]`。体积积分必须是 **50 W**。
6. 仅顶面设置 Heat Flux → Convective heat flux：`hTop=1e5[W/(m^2*K)]`、`Tamb=300[K]`。底面和四侧保持 Thermal Insulation。没有辐射、接触热阻、热沉实体或空气域。
7. 用底面 Mapped + 纵向 Swept 网格。可先横向 2×2、z 向 8 段，再横向 4×4、z 向 16 段；用二阶温度插值、直接线性求解器。记录实际单元数、自由度和所用插值阶次。**COMSOL 网格不必等于 3D-ICE 网格，采样点必须相同。**
8. 求解第一档并导出 `temperature_base.csv`，加密后重新求解并导出 `temperature_refined.csv`。两次都使用同一份 `h0_z16/sample_points_m.txt`，保持对应的两份求解日志；将合并日志保存为 `solver.log`。把两份解保存在同一 .mph 中，或另附粗网格 .mph；metadata 的 `model` 指向细网格已求解模型。

核查用解析解（不是机械/COMSOL 求解输出）：

\[
T(z)=300+\frac{qL_z}{h}+\frac{q}{2k}(L_z^2-z^2).
\]

顶面 T=305 K，底面 T≈305.192307692 K，体积平均 T≈305.128205128 K。固定采样点都在单元中心，不能拿中心的最高温度直接代替表面最高温度比较。3D-ICE 逐点解析对照已放在 `analytic_comparison.csv`。

## 如何导出温度和热平衡

- 在 Results → Export → Data 中选择本次解；只导出表达式 `T`，单位 **K**。点位置选 From file，加载 `sample_points_m.txt`，坐标单位 **m**。选择 Spreadsheet 数据格式，导出坐标，使用逗号或空白分隔，至少 12 位有效数字，不追加到旧文件。
- 文件每条有效记录必须是 **x,y,z,T 四列**。COMSOL 以 `%` 开头的注释可以保留；不要导出额外的域编号、时间或参数列。脚本能重新排列点的顺序，但不会补点或插值。
- 在 Derived Values → Volume Integration，对发热硅域积分 `qSi` 得到 `integrated_source_w`。
- 在 Surface Integration，选择整个顶面，积分 `hTop*(T-Tamb)`，单位 W，得到**向外为正**的 `integrated_top_outward_heat_w`。两项都从 COMSOL 计算，不手填合同中的理论功率。
- 两档 COMSOL 网格在固定点处最大温差目标 ≤0.005 K；对 3D-ICE 最大温差目标 ≤0.05 K；源功率和散热平衡相对误差 ≤0.1%。这是本次接口验收目标，不能用来证明亚毫开尔文的位置效应。

官方说明：[数据导出](https://doc.comsol.com/6.4/doc/com.comsol.help.comsol/comsol_ref_results.37.224.html)。该链接是 6.4 版参考；若本机界面没有 From file，先记录版本和可选项，保留模型，不改采样坐标或用近邻值代替。

## H1：铜核—SiO2 衬层—硅

H0 通过后再做。优先建立 `h1_centered_xy8_z16`，随后复制模型只改位置，建立 `h1_shifted_xy8_z16`。

| 项目 | 居中 | 偏移 |
|---|---:|---:|
| 外形 | 50×50×110 µm | 同左 |
| 铜核截面 | 10×10 µm | 同左 |
| 衬层外边长 | 12 µm | 同左 |
| 铜核中心 x,y | 25,25 µm | 17,25 µm |
| 硅体积 | 2.5916e-13 m³ | 同左 |
| 铜体积 | 1.1e-14 m³ | 同左 |
| SiO2 体积 | 4.84e-15 m³ | 同左 |
| 硅域总发热 | 0.0012958 W | 同左 |

这是**方形截面接口测试结构**，不等同于直径 10 µm 的圆柱 TSV，不将它的铜面积作为真实孔资源。

最不容易混淆的建模方法：按各目录 `regions_si.csv` 建立 9 个无重叠 Block；每块基点为 `(x_m,y_m,0)`，大小为 `(width_m,depth_m,Lz)`。Form Union 并保留内边界，根据表中 material 字段指定材料。4 块硅、4 块 SiO2 和 1 块铜恰好铺满横截面；不能在完整硅块上再叠加铜块。

三个材料使用包中的 k、ρ、Cp 常数。只在 4 块硅域加 `qSi`，铜和 SiO2 的外加体热源明确为零；不加 Joule 热。顶面包括三种材料，全部施加同一对流条件。内部材料连接为理想连续；保留的硅—硅等内部边界也必须连续，不能误加绝热。

使用相容的映射/扫掠网格：每个衬层厚度方向至少 2、4、8 个单元逐级检查；其他区域同步细化，z 向至少 8、16、32 段。上面是初始网格建议，实际停止由固定采样点的温度变化决定。可先比较两档；若变化大于 0.005 K，继续加密并保留全部历史。COMSOL 内部 9 块间的面网格必须相容，不能强求每块都有相同的横向分段数。

每个位置的 COMSOL 细网格解可分别在该位置 3 份 `sample_points_m.txt` 上导出，对应三档 3D-ICE 网格。不同采样文件的行数为 144、1152、9216，不要混用。

当前 3D-ICE H1 峰值在最后两档网格间仍变化约 0.015 K；居中/偏移差异仅约 0.00058 K。因此目前 H1 只是几何和材料输入链已运行，**位置效应尚未分辨，也未得到外部精度验证**。

## M0：先验证真实机械求解

在新模型里使用 H0 几何和硅材料的 E=135 GPa、ν=0.28、α=2.6e-6/K；Solid Mechanics，静态、小变形、线弹性，无重力、无塑性。给定温度 310 K，热膨胀参考温度 300 K。该参考态只是人工验证定义，不是 TAP 制造应力自由温度。

**M0a 自由膨胀：** 在 x=0 面只约束 u=0；y=0 面只约束 v=0；z=0 面只约束 w=0。其余位移分量不勾选，其他面无外力。这允许均匀自由膨胀并去除刚体模态。不要使用整面 Fixed Constraint。

求解后检查远端位移：u(Lx)=2.6e-7 m，v(Ly)=2.6e-7 m，w(Lz)=2.6e-9 m。解析应力为零，但**必须保存真实 COMSOL 计算的残余应力**。初始目标：位移误差≤1%、全域最大 von Mises 应力≤1000 Pa。

**M0b 轴向约束：** 复制 M0a，在 z=Lz 面再仅约束 w=0，保留横向自由。解析 σzz=−EαΔT=−3.51 MPa，σxx=σyy=0，横向应变 (1+ν)αΔT=3.328e-5；z=Lz 面反力合量的绝对值为351 N（面积1e-4 m²）。核对有符号 σzz、反力和位移；目标误差≤1%。固定两个端面的全部位移会形成另一个问题。

填写 `mechanical_return_template.json` 的真实输出，附 .mph、日志、所选边界截图及其 hash。模板中的 null 保持未求解含义；不把本节解析参考直接复制为求解结果。本轮热结果导入器不自动认定机械验证通过，机械证据回来后逐项审查。

## M1：异质体热应力（后续阶段）

H1 热验证和 M0 都通过后，在同一个 H1 几何上加入 Solid Mechanics 和 Thermal Expansion：材料按表，理想结合，所有外表面无机械外载。使用一个覆盖整个连通体的 **Rigid Motion Suppression** 节点，不再叠加其他约束；不要把偏移结构的 x=0/y=0 面当作对称面。

先用统一 310 K 对 300 K 参考态求解，检查 CTE 不匹配引起的真实应力；再使用该 COMSOL 模型已交叉核查的热解作为载荷。这里验证的是同一连续温度问题下的热—力计算；**还不是将 3D-ICE 的单元中心温度直接导入力学域**。后者需要单独处理边界覆盖和温度映射误差，本包没有实现。

导出位移、σxx/σyy/σzz/σxy/σxz/σyz、von Mises，应明确域、点集和坐标；报告各材料体积平均量和固定内部采样点。方形异质尖角、自由边和约束附近可能有峰值不收敛，原始全域峰值单独保留，不能当作失效指标。后续需要定义圆柱几何、ROI、网格收敛及合适的应力指标。本包的 `sigma_allow_pa` 仍为 null。

官方依据：[顺序热—结构求解](https://doc.comsol.com/6.3/doc/com.comsol.help.sme/sme_ug_modeling.05.160.html)、[刚体运动抑制](https://doc.comsol.com/6.3/doc/com.comsol.help.sme/sme_ug_solid.07.069.html)。

## 回传与本地核查

每个热算例新建一个结果文件夹，放入：

1. `temperature_base.csv` 和 `temperature_refined.csv`；
2. 保存了真实解的 `.mph`，以及两档网格的完整 `solver.log`；
3. 将该算例 `return_metadata_template.json` 复制为 `metadata.json`，填写版本、日期、实际自由度、积分结果和备注；只有真实求解完成才将 status 改为 solved；
4. 计算模型及日志 SHA-256。Windows PowerShell：`Get-FileHash .\h0.mph -Algorithm SHA256`；macOS/Linux：`shasum -a 256 h0.mph`。把结果按小写写入 metadata 的 evidence 对应项。

在解压后的任务包根目录（需 Python 3.9+，仅标准库）运行：

```sh
python scripts/import_comsol.py h0_z16 path/to/your_result_folder
```

或者把上述文件带回本项目再执行同一命令。输出保存到 `verification/comsol_imports/h0_z16/`；退出码 0 表示该热算例的数值检查通过，1 表示差异未达目标，异常表示数据合同不满足。它不检查 .mph 的内部模型设置，仍需人工复核材料/边界选择；也不意味着其他热算例、力学或 TAP 三场已验证。

## 参数来源与证据限制

来源主表是 `cases/minimal_coupons/provenance.json`。Si 热参数与 H0 尺度来自锁定的 3D-ICE 示例；Cu 热参数来自 TAP 热模型；SiO2 热参数来自 Hung 等论文 Table 2；E/ν/CTE 与 Si/Cu 密度来自 Coppeta 等论文 Table 1。SiO2 密度采用 Hung 的2200 kg/m³，不采用 Coppeta 表内印刷的220。

H1 的方形截面、1 µm 衬层、位置移动、网格及测试温升是明确声明的验证定义；不是已经确认的工艺实测值。研究参数台账不因此自动采用任何参数。

3D-ICE 非均匀模式的底层竖向导热距离特殊处理会增加 H0 最底层中心误差，详见 `docs/MINIMAL_COUPON_RESULTS.md`。本包仅修改温度输出精度，保留这一后端行为。若后续需要高精度，应先用此回归算例评估并独立修复后端，再重新锁定版本。
