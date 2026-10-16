# Codex 分阶段任务：TAP-2.5D 电—热—力模型

配套规格：`TAP25D_ETM_Modeling_Design_for_Codex.md`。

使用方式：先将规格加入当前仓库可读取位置，并发送 P0。看到真实审计后，按 P1、P2……依次执行。不要一次性要求完成优化器或把所有阶段都声称通过。

---

## P0：仓库与参数审计（建议现在首先发送）

```text
请读取当前挂载的 mypdn 仓库及 TAP25D_ETM_Modeling_Design_for_Codex.md。

我的当前目标是：基于 TAP-2.5D Multi-GPU 派生案例，固定芯粒布局及 P/G 通孔数量、尺寸，建立同一个实际物理设计的电学、热学和热机械应力评估模型。此阶段只做建模和验证，不做优化器，不加 agent，也不新增伴随或代理模型。

先完成 P0 审计，不要直接重写求解器：
1. 读取 AGENTS.md、README 和现有研究上下文。查找旧 TAP 接入与 bump-level 多 rail 设计文档；以代码和测试核对“已实现”的说法。
2. 定位 raw case -> normalized/compiled design、TAP importer、frozen layout、supply pair/shared return、P/G via macro、DC、温度相关电阻、thermal、Joule heat、electrothermal fixed point、hard rebuild 的真实调用链。
3. 对每项给出实际文件/函数、已有测试、已实现/未验证/部分/缺失状态。不要把 mock 或协议定义当真实求解器。
4. 读取当前 TAP-derived case，确认它是硅中介层还是 CoWoS-L-like；输出芯粒尺寸/功耗/坐标、单位、实际 P/G 孔数、上下层连接、层叠、材料及边界的参数来源。缺失参数列清楚，不能补假数据。
5. 明确当前负载与热功率政策：恒流还是恒功率，die heat 来自额定功率还是实际 IV，哪些 Joule loss 已计入 die heat，是否存在重复计热或能量不一致。
6. 核查现有热后端是否真正随通孔位置更新；核查 COMSOL 或其他已有真实力学后端的可用性，不假定许可证/批处理可用。
7. 根据规格给出最小增量修改方案，保留既有电学、多电源域、CoWoS-L、AC 和优化功能。新建硅中介层 profile 不能覆盖旧 case。

交付 ETM_IMPLEMENTATION_AUDIT.md、ETM_PARAMETER_GAPS.csv、ETM_REUSE_AND_CHANGE_PLAN.md，以及真实执行过的低成本测试记录。
当前不要运行长时全尺寸 FEM、不要安装大批新依赖、不要创建优化器。遇到参数或环境阻塞，报告准确原因，同时完成不受阻塞的审计。不要仅输出泛泛计划，必须检查代码。
```

## P1：统一物理 case 与布局编译

```text
依据已完成的 P0 审计和 TAP25D_ETM_Modeling_Design_for_Codex.md，实施 P1。

复用既有 importer、normalizer、compiler，不为三套求解器各写一个 raw parser。
冻结一个 TAP-derived Multi-GPU 布局；公开 cfg 没有最终坐标时优先读取现有 frozen layout，不得伪造论文坐标。
建立或扩展明确的 technology/material/condition/observation 配置；统一内部 SI、坐标基准、z 层叠、芯粒朝向和 bump 变换。
建立可跨三场识别的真实 via ID、铜/衬层几何和端点。现有一个 candidate site 若是多孔宏，必须展开真实孔数和体积，不得当作一根巨型铜柱。
固定各 rail 资源预算，保留 shared ground 与独立 ground 的区别。检查几何互斥、连通、keepout、输入来源和缺失参数。
缺失研究参数用 null 并阻塞研究 evaluate；可建立带明确 synthetic_fixture 标签的小模型进行单元测试。
新增 profile 不得覆盖旧 CoWoS-L 或 Blackwell policy。

交付：编译后的 case 摘要、参数 provenance、几何/连接验证、单位/旋转/真实孔数/功率合计测试，以及修改文件与实际测试结果。此阶段不启动优化。
```

## P2：电学评估与温度/功率接口

```text
实施规格 P2，复用已有 DC MNA、求解器和多 rail 数据结构。

检查真实 P/G 回流闭环、有限阻抗 ground、bump/load 端点和移动通孔后的上下层接入，不允许通过理想电源复制或 Gmin 漏电掩盖断路。
为温度相关支路补齐材料、路径、截面、接触参数、温度采样与热归属；不得把 TAP 的 thermal resistivity 当电阻率。
输出全部负载端 Vp-Vg、各域最差压降、逐孔电流/平均电流密度、支路 Joule loss、电源与负载功率总账。
负载模式沿用已确认 manifest；如新增模式必须显式配置，不修改旧实验。对 declared heat 与实际 IV 的差额按规格报告，不伪造全局电热守恒。
用解析串并联、有限 ground/shared return、参考温度/统一升温、断路失败测试验证。

交付代码、真实测试记录、一个小模型 DC 结果和电功率检查；不把接口测试当大案例已验证。
```

## P3：位置相关热模型和跨场映射

```text
实施规格 P3。优先复用已有 thermal/FVM；若已有 3D-ICE 接口则扩展，不重复造热求解器。

由共享几何、材料和真实 via layout 构建热模型。不能沿用整片不变的 TSV 等效导热材料而声称支持位置变化；不能在含铜等效材料上再重复叠加相同铜孔。
建立芯粒实际 body 内的面积/体积交叠热源映射。bump current map 不等于芯粒发热分布。补齐耗散层 z 和厚度，禁止重复施加功率。
建立 thermal -> branch temperature，以及内部支路 Joule heat -> thermal cell 的守恒映射；外部损耗单独记账。
输出真实 3D 温度、每芯粒温度、关键互连温度、各外边界热流和能量检查。
通孔的区域等效模型必须有显式小单元/阵列验证；记录无法分辨同一粗单元内位置变化的限制。
做一维导热、零热源、铜柱、三档网格与映射守恒测试。热模型位置效应弱时如实报告，不调整边界制造降温。

交付后端/映射代码、验证数据、模型限制和未完成项；不开始优化。
```

## P4：真实热弹性应力后端与小模型

```text
实施规格 P4。新增或复用真实的热弹性力学求解，优先使用当前可用的 COMSOL 固体力学/热膨胀接口。

先完成后端探测与小模型，不直接对整个 50 mm 系统逐孔精细剖分。
小模型需要铜孔/衬层/基体真实几何、材料刚度/CTE、明确 T_sf、机械支撑、温度载荷与界面连接。
自由膨胀模型只去除刚体运动，不得全底面固定。检查 T=T_sf 零应力、单材料自由膨胀、受限杆解析解、不同 CTE 单孔/阵列、网格收敛。
温度来自真实字段或明确解析测试场；移动 via 必须同时更新几何与接口，不仅改温度。
输出 von Mises/主应力/位移及具名 ROI，保存原始峰值、体积权重统计、结果单位和覆盖范围。不得用温差、间距罚项或 E*alpha*DeltaT 直接冒充完整应力场。
COMSOL 不可调用时实现明确的导出/导入协议并报告 pending_external_solver；不输出零应力或假 mph 文件。mock 限于 CI，强制标记并禁止科研使用。

交付真实执行的模型、输入输出与测试；未执行项标为未执行。解释下一步全局—局部力学的边界与范围，但不声称小模型等于完整 TAP 应力验证。
```

## P5：同一个 case 的电热力联评

```text
实施规格 P5，将现有模块接入同一个 ETM runner。

先支持显式标记的单向流程（规定热源 -> 温度 -> R(T) DC -> 热弹性）；再复用经验证的电热固定点执行已确认的严格记账模式。
固定点检查电压/温度变化、方程残差与功率账；最终电流和温度必须来自同一收敛状态。未收敛不得成功返回。
力学采用最终温度。全尺寸显式模型不可承受时采用经验证的 global-local；子模型边界、域大小和 stress_coverage 必须记录。只覆盖局部时，指标名称不能叫全系统最大应力。
统一 EtmResult、状态、错误码、运行日志、缓存键和 provenance。缺失应力必须返回 null+原因，不能 eligible_for_optimization=true。
验证同几何、关 Joule、仅换 P/G 网名时热力结果不变；验证布局改变后相关缓存与映射正确失效。

交付一个真实案例的可复现联评命令、结果、守恒与覆盖报告，或准确的部分完成/阻塞状态。
```

## P6：同数量位置分布对照与阶段验收

```text
实施规格 P6。固定芯粒布局、技术/材料/边界、同一负载模式、各 rail 真孔数与尺寸，仅比较 uniform_legal、load_biased_legal、hotspot_biased_legal 三种通孔分布。

此任务不是运行 NSGA-II，不做器件数量搜索。
输出每组的 Tmax、Dmax、Scrit（附指标定义/覆盖范围）、实际负载功率、热源总功率、热流路径、逐孔电流、数值误差和完整运行时间。
力学增加同一均匀温升的几何对照与各自真实温度场对照，区分几何与温度两种作用。
温度/压降/应力差异小于分辨率或验证误差时标记 effect_not_resolved；不得强行排序为显著收益。
保存冻结输入、原始日志、可复现命令和未解决问题。形成 README_ETM_MODELING.md，区分已测试通过、参数待确认、后端未运行、仅局部验证等状态。

验收重点是物理模型一致、位置作用可解释、结果可信，不是某种预设布局必须胜出。完成后停止，不自动进入优化阶段。
```
