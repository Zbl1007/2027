# 基于 TAP-2.5D 的电—热—力三场评估平台：第一阶段实施设计

版本：V1.0  
日期：2026-10-15  
交付性质：实施规格与验收方案，不是已经完成的仿真结果  
主案例：TAP-2.5D `configs/sys_multigpu.cfg` 派生的固定布局案例  
阶段目标：给定同一个 case 和一组合法 P/G 通孔布局，生成相互一致的电学、热学、热机械模型，获得有来源、有物理含义、可复核的评估结果。暂不实现优化算法。

---

## 0. 本次任务边界

### 0.1 需要交付的能力

最终接口的逻辑含义是：

```text
固定 case + 技术/材料参数 + 工况 + 离散通孔布局
    -> 输入与连接合法性检查
    -> 编译为同一物理设计的三种离散模型
    -> DC / 温度相关 DC / 电热求解（按明确模式执行）
    -> 温度场驱动的热弹性应力求解
    -> Tmax、负载端 IR-drop、定义明确的应力指标及场分布
    -> 守恒检查、模型覆盖范围、数值质量与可追溯记录
```

电学网格、热网格、力学网格不要求一致；物理几何、材料分布、热源、电连接和通孔身份必须一致。

### 0.2 明确不做

本阶段不新增 NSGA-II、agent、强化学习、伴随算法、代理模型或自适应网格算法；不优化芯粒位置、TIV/TSV 数量或尺寸；不做 AC 优化、完整制造残余应力过程、疲劳寿命、裂纹/脱层传播、铜塑性循环或机械变形到电学的反向反馈。

已有 AC、优化器、伴随、CoWoS-L-like 案例等功能不得删除。它们只是本阶段不需要调用，不意味着重构时可以破坏。

### 0.3 封装配置原则

针对上一轮讨论，建议新增一个普通硅中介层 `silicon_interposer` 技术配置，通孔名称为 TSV，作为三场建模的第一验证场景。现有 CoWoS-L-like/TIV 配置保留，不能就地改名或覆盖。

TAP 只决定部分芯粒级案例信息，不决定完整封装工艺。若当前可运行案例已经是 CoWoS-L-like，先在审计中列清它与新硅中介层配置的差异，再通过独立 profile 扩展。缺少硅中介层/衬层等参数时，不得通过把 molding material 改成 silicon 就宣称完成转换。

### 0.4 模型分级

- `synthetic_fixture`：为软件/解析解测试定义的合成小模型，不是 TAP 产品参数。
- `research_assumption_model`：关键参数齐全且假设显式确认的研究模型，不等于实测校准模型。
- `cross_validated_model`：在声明的几何、载荷和范围内完成独立数值交叉验证。
- `industrial_validated_model`：本项目目前不得自行使用这一标签。

没有参数、没有外部求解器或没有实际执行时，应报告阻塞或部分完成，不能用默认值、零应力、伪造云图替代。

---

## 1. Phase 0：先审计现有仓库，避免重复造轮子

用户曾说明已实现 TAP 接入、bump-level 多 rail case 接入、电学求解及部分电热模块；已有设计文档也声明了相应接口。文档中的“已实现”必须通过当前代码和测试核实，不能视为已验证事实。

### 1.1 审计入口

在用户实际挂载的仓库执行；历史本地路径为 `/Users/zbl/Desktop/docker/code/mypdn`，但不得假定当前运行环境路径相同。

首先读取现有 `AGENTS.md`、README、项目配置与研究上下文。若存在，重点读取：

```text
CoWoS_L_PG_TIV_Electrothermal_Placement_Implementation_Design.md
TAP_2_5D_to_CoWoS_L_TIV_Case_Integration_Design_for_Codex.md
Bump_Level_Multi_Rail_Case_Integration_Design_for_Codex.md
docs/RESEARCH_CONTEXT.md
```

不存在就记录“未找到”，不要新建一份同名文件冒充旧文档。

### 1.2 必须核查的能力

| 能力 | 审计需要提供的证据 |
|---|---|
| TAP cfg 导入和布局冻结 | 实际文件、函数、坐标语义、输入输出样例 |
| 原始 case -> normalized case -> compiled design | 当前数据类型、单位、ID 关系、schema 版本 |
| 多 rail 与共享 ground | load 的 supply pair、返回网络连接、测试 |
| P/G 通孔宏 | 1 个候选点对应 1 根通孔还是一组 P/G 通孔；真实孔数和铜体积 |
| DC MNA 与求解器 | 当前 builder、求解入口、源/负载语义 |
| 温度相关电阻 | 更新哪些支路、温度如何映射、是否支持材料各自 TCR |
| 热模型 | FVM/RC/3D-ICE/COMSOL 中哪些真实存在，是否随通孔位置更新 |
| Joule heat 与电热固定点 | 功率政策、守恒、停止条件、未收敛状态 |
| 外部 COMSOL | 安装/版本/许可证能力、可用批处理或导入导出方式 |
| 力学模块 | 是否已有真实求解器、模型、结果读取与测试 |
| hard rebuild/结果缓存 | 布局变化是否使相应几何、矩阵、映射、缓存失效 |

### 1.3 Phase 0 交付

输出 `ETM_IMPLEMENTATION_AUDIT.md`，逐项分成：已实现且测试通过、已实现但未验证、部分实现、缺失、外部依赖阻塞。

每条已实现结论给出代码位置与实际测试命令/结果。不得只引用 TODO、函数名、协议类或 mock 测试。

同时输出：

- `ETM_PARAMETER_GAPS.csv`：参数缺口、影响的后端、可用来源、是否阻塞研究模型。
- `ETM_REUSE_AND_CHANGE_PLAN.md`：保留、扩展、新增的模块及兼容性风险。
- 一份当前案例的物理信息摘要，不启动完整规模网格或优化。

Phase 0 可以只运行低成本现有测试。不得擅自开始长时 COMSOL 任务或大规模有限元网格。

---

## 2. 唯一物理数据源与编译流程

### 2.1 保持已有层次

优先扩展已有 `DesignSpec/PhysicalDesign` 或 normalized/compiled 类型，不另造与之并行的三个原始 JSON 解析器。

```text
原始 TAP cfg + frozen layout
              + package/PDN/material extension
              + operating condition
              + discrete via layout
                          |
                   validate / normalize
                          |
               共享的 CompiledPhysicalDesign
                  /           |           \
            DC adapter   Thermal adapter   Mechanics adapter
                  \           |           /
                       ETM runner
                          |
                 results + manifest + checks
```

这里的类型名称是逻辑示意；实际命名由仓库审计决定。求解器不应自行读取 TAP raw cfg，也不应自行决定参数缺省值。

### 2.2 统一约定

内部统一 SI：m、K、V、A、W、Pa、ohm。输入可显式使用 mm/um/°C，解析边界统一转换；结果可另导出 mm、°C、mV、MPa。

建议基准坐标为封装左下角；z 正方向朝芯粒/顶部散热路径。层高由共同 stackup 计算，不允许三个后端各自累计不同 z。

每个输入来源必须声明坐标是芯粒中心还是左下角。中心坐标转换必须使用经过朝向处理的实际长宽。芯粒局部 bump 坐标要做相同的旋转、平移；不能只旋转外接矩形而不变换 bump。

`case_id`、`chiplet_id`、`rail_id`、`supply_pair_id`、`via_id`、`branch_id`、`material_id`、`region_id` 为稳定 typed ID。不能依赖字符串拆分猜测网名或支路类型。

### 2.3 建议的数据内容

| 对象 | 必须承载的信息 |
|---|---|
| Case manifest | 原始来源、commit/file hash、版本、配置类型、假设批准状态 |
| Frozen layout | 芯粒实体包络、旋转、坐标、中介层包络及 keepout |
| Stackup | 每层 z、厚度、材料区域、相邻层、接触/粘结定义 |
| Materials | rho_e/TCR、电/热参考温度、k 张量、力学参数、数据来源及有效范围 |
| Supply pairs | 正电源、return、标称电压、负载规则及观测位置 |
| Branch geometry | 支路路径、截面、所属材料、温度采样范围、Joule heat 空间归属 |
| Via layout | 物理铜孔几何、电连接端点、衬层、孔间距、固定/可变状态 |
| Boundary conditions | 热边界和机械边界分开定义、具名物理选择 |
| Observation regions | 芯粒热源层、负载端、电流密度观测、应力 ROI |
| Analysis policy | one-way/two-way、load/power policy、网格、求解容差与失败行为 |

### 2.4 物理实体不是候选位点

若当前 1 mm 候选网格中的一个 site 表示通孔簇，它只是设计位置分辨率，不是单孔直径或工艺 pitch。必须保存该簇展开后的实际 P/G 铜孔数量、尺寸、位置与体积。

模型之间转移的是实际物理通孔。不能电学使用 32 个并联孔，热学只增加一个孔，力学又使用整个候选格大小的铜块。

### 2.5 来源与未决参数

每个关键参数至少保留：value、unit、source_kind、source_locator、physical_role、calibration_status、approval_status。

`source_kind` 建议区分 benchmark_exact、existing_case、literature、measured/calibrated、explicit_assumption、synthetic_fixture。

不存在的值用 null；研究运行在必需参数缺失时阻塞。Codex 可以建立显式标注的解析解 fixture，不可以把 fixture 参数无声复制到 TAP case。材料来源不同、stackup 简化不同均须记录，不强行合并为“原论文参数”。

---

## 3. TAP Multi-GPU case 的接入与冻结

### 3.1 已核对的公开配置

当前核对的 `configs/sys_multigpu.cfg` 有 6 个芯粒，`intp_size=50`，采用被动中介层配置。

| 语义名称（适配层约定） | 数量 | 单颗宽×高 (mm) | 单颗额定功耗 (W) |
|---|---:|---:|---:|
| CPU | 1 | 12×12 | 105 |
| GPU | 2 | 18.2×18.2 | 295 |
| HBM | 3 | 7.75×11.87 | 20 |

额定功耗合计为 755 W。原 cfg 使用数组下标，语义命名应在适配层保存明确映射，不依赖文件名猜顺序。

该公开 cfg 使用 `initial_placement=bstree`，没有直接提供最终芯粒 x/y。不得宣称已经从这个 cfg 读到论文优化后坐标。

### 3.2 首先复用已有 frozen layout

优先采用用户当前已验证的 TAP-derived frozen layout。检查尺寸、边界、重叠、朝向、body/keepout 区别，并保存 hash。

只有确实没有现成布局时，才通过现有合法布局生成器生成一个固定种子的布局。标明 `generated_layout`，不能称为 TAP 论文原始最优布局。基于图片手工估算坐标也必须标注来源和误差，不能装作精确数字。

本阶段不得把原论文、GitHub cfg 与后续 TCSI 论文的尺寸/面积混合为未说明的一套参数。保留现有案例时记录偏差，不自动覆盖。

### 3.3 TAP 缺失的部分

TAP 芯粒功耗与通信矩阵，不提供完整的 DC 电源网表、P/G bump assignment、实际供电电压、完整 RDL 几何、通孔可放置规则和力学参数。

`connections` 是通信背景信息，不是 PDN 电流。没有真实 bump map 时可采用显式合成生成器；不得将其标为工业原始数据。已有详细 bump case 必须优先保真导入，不得退化为单一总电流而不说明。

### 3.4 初始三种布局只用于验证位置效应

固定同一 case、P/G 各网真实孔数、直径、高度、总铜量、合法候选集合和源/负载条件。生成：

1. `uniform_legal`：在合法区域内尽可能均匀；不是强制网格化到非法位置。
2. `load_biased_legal`：依据既有负载/连接信息向负载需求区域分配。
3. `hotspot_biased_legal`：依据同一个初始热基准场生成，不能对不同算法使用不同热基准。

这三组不是“优化算法 baseline 已完成”，也不预设谁最好。可选再加一个 `dispersed_legal` 检查局部密集效应。

不能删除或移动固定信号通孔/机械结构以腾出不真实的合法空间。

---

## 4. 根据 case 建立物理结构，不只是生成三个文件

### 4.1 建议层次

从下到上按照已确认参数建立：

```text
封装电源入口 / substrate 等效供电边界
substrate 实体及其热、机械边界
C4 与 underfill（显式或经过验证的等效层）
背面 P/G RDL
硅中介层基体 + 可变 P/G TSV + 必要衬层 + 固定结构
正面 P/G RDL
microbump 与 underfill
芯粒实体 / 规定的耗散层
TIM
盖板或散热扩展层（若实际模型包含）
明确的顶部散热边界
```

这是建模层次，不是补齐工艺参数的许可证。厚度、接触、材料等从现有案例/公开来源取得；缺失项进入参数表。

若热模型把顶部散热器简化为等效边界，机械模型仍须说明盖板、TIM 和约束的物理处理。热边界不能自动变成机械固定边界。

### 4.2 三套模型中的相同与不同

电学可以用 RDL 网络和通孔支路，不逐点划分硅体；热学可以采用各向异性等效层；力学可采用显式局部孔和经验证的全局模型。

但任何“等效”的范围与校准记录必须可追溯，不能让粗化改变实际资源预算。

### 4.3 通孔几何互斥

铜孔、衬层、基体的体积必须互斥；相邻层表面必须正确连接。显式孔应从基体扣除，不能在未扣除的硅/模塑实体中再放完整铜域形成重复体积。

既有整片 TSV 等效材料已经包含铜时，不能再叠加全部显式孔。应分解固定背景贡献与可变贡献，或重新建立不含可变孔的基体。

### 4.4 预检查

检查层叠间是否存在非预期空隙、重叠或断开的热/机械域；检查各通孔是否穿透声明的正确层、是否连接正确端点、衬层是否错误阻断电端连接。

生成 geometry/selection manifest 和层叠剖面数据。几何预览可由程序绘图或 CAD 导出，不凭示意图宣称实际网格连通。

---

## 5. 电学评估器：以现有 DC MNA 为核心

### 5.1 完整供电与回流路径

```text
电源 -> 有限阻抗的 package/背面电网 -> P TSV
     -> 正面 RDL -> P bump -> 芯片负载
     -> G bump -> 正面 return RDL -> G TSV
     -> 背面 return/package -> 电源 return
```

电气参考地只处理方程参考电位，不得把所有物理 ground 节点钳制为零。不同正电源可共享 return，但不同 ground net 不能无声短接。增加 load 时不得另加一套重复 ground sink。

上下层有明确 RDL 连接；移动 TSV 后，不能凭空赋予新位置理想电源。信号网络不进入 DC 供电电流。

### 5.2 支路电阻及温度

对于均匀支路：

\[
R_e(T)=\rho_{e,0}[1+\alpha_{R,e}(\bar T_e-T_{R,e})]\frac{L_e}{A_e}+R_{c,e}(T).
\]

接触电阻有独立参数/温度政策；不能默认与体铜完全相同。电阻率的单位为 ohm·m，TAP 热模型中的 `resistivity_Cu=0.0025` 是热材料上下文的量，绝不能当作铜电阻率。

长 RDL 或竖直孔可按路径积分/分段：

\[
R_e=\int_{\Gamma_e}\frac{\rho_e(T(s))}{A_e(s)}\,\mathrm ds+R_{c,e}.
\]

不能统一把 GPU 最高温度赋给全部支路。不得使用 `Gmin` 等数值漏电路径给物理断路“补通”后报告可行。

### 5.3 首版输出

- 所有实际 load terminals 的局部 P/G 电压差。
- 每个 supply pair、chiplet 的最差/平均压降与最差位置。
- P、G 通孔支路电流、方向和平均电流密度。
- 各类有损支路 Joule 功率，包含其空间归属。
- source power、load received power、PDN loss 与电功率平衡。
- 电流方程/电压约束残差分开检查；MNA 不同单位的行不能直接用未经缩放的单一范数掩盖误差。

压降定义：

\[
D_n=V_{\mathrm{nom},n}-(V_{P,n}-V_{G,n}).
\]

保留有符号值，并另报告欠压违约量；不要裁零后丢失过压或错误连接线索。

### 5.4 温度基准对照

同一布局同时支持：参考温度 DC 和采用空间温度场的 DC。两者不改变负载模式或端点，只改变明确支持的电阻温度项。

---

## 6. 热学评估器：必须体现通孔位置

### 6.1 后端选择

先审计并优先复用已存在的稳态 FVM/热网络；不要重写一套同功能求解器。若已有 3D-ICE 接口，扩展它；若没有可用热后端，再实现 3D-ICE 4.0 适配。

COMSOL 用于小结构和代表性方案交叉验证；用户已有 COMSOL 热模型可优先复用。不同后端只在相同物理设定下比较，不把不同边界条件造成的差异归因于求解器精度。

### 6.2 方程与离散单位

\[
-\nabla\cdot(\mathbf k\nabla T)=q'''_{\mathrm{die}}+q'''_J.
\]

控制体格式可以为 `K_T T = b_T`；此时 `K_T` 单位 W/K，单元功率右端单位 W。若后端接收体积热源，则单位 W/m³，必须由体积转换。外部工具的长度和材料单位在适配器边界转换，不能全局假定都是 SI 输入格式。

热边界具名声明：固定温度、对流、规定热流或绝热。禁止对同一散热路径重复施加 TIM 热阻、接触热阻和已包含该项的等效换热系数。

### 6.3 芯粒热源

缺少 block-level power map 时，以真实芯粒 body 内均匀热功率密度作为显式假设。电流从 bump 进入的位置不是晶体管实际发热位置，不能默认复制 bump current map 为 die power map。

芯粒功率按几何面积/体积交叠映射，不得按单元数量平均而忽略边界截断。对每个 chiplet 保证映射后的总功率等于当前功率政策给定的热功率。

耗散层厚度和位置必须显式配置。若采用整个等效 die 体积发热，必须记录；不得一边热源位于底面，另一边在体内重复施加同样功率。

### 6.4 通孔局部导热

单根理想铜柱轴向热导的参考公式：

\[
G_{z,v}=k_{\mathrm{Cu}}A_v/L_v.
\]

区域模型必须由本次实际铜占比更新。轴向平行传热的简单混合式只可用于适用条件下的初始近似：

\[
k_{z,\mathrm{eff}}=f k_{\mathrm{Cu}}+(1-f)k_{\mathrm{matrix}}.
\]

它不是完整三维通孔结构的自动精确模型。横向导热、衬层、接触与扩散热阻应通过单元/小阵列模型验证，不得将同一式无条件用于 x/y/z。

两个布局若在当前每个热单元内具有相同铜占比，粗热模型可能无法区分它们。这属于分辨率限制，应标记 `subgrid_layout_unresolved`，而非伪造温度变化。

P/G 网名变化不改变同几何铜的导热材料；电流分配改变才可能通过 Joule heat 改变温度。热域包含所有固定金属结构，不只包含当前目标电源域。

### 6.5 热场输出

- 真实热单元或 FE 单元/节点的 x/y/z、所属层/材料、温度。
- 每个 chiplet 的最高与体积/面积加权平均温度，观测位置固定。
- 关键互连层与通孔温度，供电阻映射使用。
- 外部边界净流出热功率、各散热边界功率、顶部/底部等路径占比。
- 热源功率总账和热平衡残差。

表面温度均匀性采用面积权重或固定采样点；不能在非均匀网格上用节点数量隐含改变区域权重。热图必须有单位、观察面高度、case/layout hash。

---

## 7. 先冻结负载与热功率政策，再启用闭环

这是实施前必须明确的事项。`P_report/V_nom` 得到恒流，不等于负载在压降后仍消耗严格恒功率。

### 7.1 三种政策不得混称

| 模式 | 电流 | 芯粒热源 | 用途与声明 |
|---|---|---|---|
| `prescribed_heat_nominal_current` | I=P_report/V_nom，固定 | P_report，固定 | 初步单向温度修正；报告热源与实际 IV 差额，不宣称系统严格电热能量闭合 |
| `fixed_current_actual_iv` | 额定电流固定 | sum((Vp−Vg)I) | 首选的保守能量记账闭环候选；755 W 是额定功率，不再要求实际负载功率恒等于 755 W |
| `constant_power` | I=P_report/(Vp−Vg) | P_report，固定 | 等功率工作负载比较；非线性负载，需要明确求解与欠压失效策略 |

先读取并保留现有 case 的显式 policy，不得因本方案而静默改变用户旧实验。对新案例，建议复用已验证的恒流求解能力：先执行单向诊断，再经显式配置转入 `fixed_current_actual_iv`。恒功率作为需要时的独立阶段，不是 Phase 0 的必做项。

若论文最终要求不同布局严格相同实际计算功耗，应采用经验证的恒功率模型，或提供相应负载模式敏感性分析；不能把高压降导致的实际功率下降全部记为散热设计收益。

所有政策都保留 TAP 的 declared/nominal power，不覆盖原始数据。policies 不同时不能在同一个对照表中当作同工况直接比较。

### 7.2 Joule heat 不重复计数

\[
p_e=I_e^2R_e,\qquad Q_{J,i}=\sum_e H_{ie}p_e.
\]

以总功率 W 表示时，完整映射应满足每个内部有损支路 `sum_i H_ie=1`。在热域之外的 package/VRM 损耗记为 `external_loss_w`，不强行丢到芯粒里；若其热影响重要，应显式扩展热域或定义边界模型。

已经包含在 die power 中的片内导线损耗，不能作为另一个 PDN 电阻热源重复增加。每个有损支路必须声明 `heat_accounting_scope`：已包含于 die、显式热域内部、热域外部。

### 7.3 电热固定点（严格记账模式）

```text
初始化 T
循环：
    按 T 更新有温度模型的电阻
    解 DC/负载非线性
    计算实际负载功率和逐支路 Joule heat
    按 heat accounting scope 组装热源
    求解温度 T_new
    必要时欠松弛
    检查温度、电压变化、方程残差、功率收支
结束后：
    在最终 T 上重新执行 DC 与热残差检查
    保存同一收敛状态的电压、电流、热源、温度
    再执行力学分析
```

只限制温度变化不够。达到最大迭代数仍未收敛时输出 `not_converged`；不得把最后一轮状态标为“成功”。恒功率模式遇到低电压/无解不能偷偷截断电流后继续报告满足负载。

---

## 8. 热机械评估器：真实热弹性求解，不用经验分数冒充

### 8.1 物理范围

第一版为小变形、线弹性、规定参考状态下的稳态热应力：

\[
\nabla\cdot\boldsymbol\sigma+\mathbf b=0,\qquad
\boldsymbol\sigma=\mathbf C:\left[\boldsymbol\varepsilon(\mathbf u)-\boldsymbol\varepsilon_{th}\right].
\]

恒定各向同性 CTE 时：

\[
\boldsymbol\varepsilon_{th}=\alpha_{CTE}(T-T_{sf})\mathbf I.
\]

温度相关 CTE 要区分切线/割线定义；采用积分或后端正确材料模型，不混用。`T_sf` 是无热应变/应力参考状态的模型定义，不必与热环境温度或电阻参考温度相同。

不将 `E*alpha*DeltaT`、温度标准差、通孔间距罚项或机器学习随机值当作已经求解出的局部应力。这些若用于诊断，必须另命名，不能填写 `stress_pa`。

### 8.2 推荐后端

第一版采用用户实际可用的 COMSOL 热膨胀 + 固体力学求解作为参考。Codex 先检查本机/批处理环境与许可。优先复用用户已有的参数化模型和具名选择。

接口可以采用本机可用的 Java/batch 或经过验证的文件往返。不要假定某个 Python 包或服务已安装、已获授权。自动接口未配置时，允许导出明确的求解任务包与回填数据规范；此时应力状态为 `pending_external_solver`，不是完成。

mock 只能用于接口测试，必须带 `mock=true` 且禁止进入论文结果目录或未来优化器的有效目标。

### 8.3 必需的机械参数

每种被力学模型使用的实体必须有弹性模量/刚度张量、泊松比（适用时）、CTE/热应变模型、参考温度。硅晶向若不建模，必须标注等向近似。TIM/underfill/粘结界面的力学处理不能完全缺省为与硅相同。

不需要疲劳参数来运行首版线弹性模型。但要声称“无屈服”或“安全”则需要相应允许值和适用温度范围；缺失时只报告应力，不作寿命/安全结论。

### 8.4 机械边界与连接

以 `boundary_condition_id` 保存真实约束：底部支撑、封装安装或自由结构。仅消除刚体运动的约束不能被误写为整个底面完全固定。所有自由度固定会制造不合理热应力。

界面理想粘结可作为首版假设，但要显式记录；不同材料接触面应正确连接。通孔位置变化后必须更新铜/衬层/基体几何及界面，不能只更新温度载荷。

使用热外推到力学节点时，不能跨不连续界面无声混合。超出热模型范围的节点不能自动填室温；需要明确补充模型或标为覆盖失败。

### 8.5 先验证小模型，再做系统级

M0：单材料自由膨胀、约束杆等解析解测试。

M1：包含真实铜孔、衬层和基体的小尺寸三维单元/小阵列。先统一温升比较几何作用，再加载实际非均匀温度。

M2：TAP 系统的全局结构与局部通孔子模型。全局提供合理位移/温度边界；局部用于孔附近应力。不能直接把任意局部块四周固定并叫作全封装应力。

当全尺寸显式网格成本过高时，采用 global-local；但全局等效刚度/热膨胀参数需验证，不能简单把铜体积分数代入任意混合式后宣称局部可靠性准确。子模型应做尺寸扩大与边界敏感性验证。

### 8.6 应力观测与覆盖范围

建议第一版重点观察铜通孔及指定连接部位的 von Mises 应力。硅最大主拉应力、翘曲等可以补充输出，不与铜屈服混用。

建议同时输出：

- `sigma_vm_raw_max_pa`：原始峰值与位置，诊断潜在奇异性；
- `sigma_vm_p99_volume_weighted_pa`：指定物理 ROI 内体积加权 99 分位；
- `sigma_vm_roi_mean_pa`：固定体积 ROI 平均；
- `sigma1_tensile_max_pa`：所选材料区域的主拉应力；
- `warpage_m`：规定表面、扣除或声明刚体平面后的翘曲量；
- `stress_coverage`：实际求解覆盖的通孔/ROI、未覆盖部分、模型层次。

最终用哪一个作为 `Scrit`，应在优化前由研究定义冻结。99 分位是布局比较指标，不是零屈服保证；不能掩盖真实高应力。若使用峰值，必须确保几何细节与网格收敛可接受；不能用随网格发散的尖角峰值作为稳定目标。

仅求解局部若干 ROI，输出必须叫 `selected_roi_max` 等，不能叫全系统最大应力。`global_sigma_max` 只有在覆盖充分且验证通过时才允许使用。

### 8.7 失败与可信度

没有力学后端、缺少材料参数、域不连通或数值不收敛时，Scrit 返回 null 并写状态。模型跨出线弹性适用范围时标记适用性风险，不把线弹性大应力解释为准确的塑性后状态。

---

## 9. 分辨率与模型规模管理

电网离散、热网格、力学网格分别管理；不强迫三者都达到最小通孔尺度。

- 系统电网：复用现有离散与聚合方式，确认聚合后保留需要的压降观测与通孔电流。
- 系统热网格：足以区分待比较的位置分布和关键层热流。
- 局部力学：显式描述孔、衬层和关键接口，并检查网格/域范围收敛。

热网格粗到不能区分布局、或力学只覆盖部分局部区域时，应在结果中反映，不允许软件看似完整却隐藏分辨率限制。

任何完整规模构建前，输出预计电节点数、热单元数、力学自由度、稀疏非零元量级和内存预算。超过预算先停止并给出分级模型建议，不能默认启动数百万实体孔的布尔运算。

首轮不引入代理模型；不能因 COMSOL 较慢就自动以启发式代替应力求解。

---

## 10. 评估接口、运行记录与错误行为

### 10.1 逻辑接口

```python
# 仅为接口规格，不是当前仓库已存在的函数。
compiled = compile_physical_design(case, technology, condition, via_layout)
validation = validate_physical_design(compiled)
et_result = evaluate_electrothermal(compiled, analysis_policy)
mechanical_result = evaluate_thermomechanical(compiled, et_result.temperature)
result = assemble_etm_result(compiled, et_result, mechanical_result)
```

实际适配已有 runner；不要写第二套电热固定点。

### 10.2 结果的基本要求

`EtmResult` 的语义至少包含：

```text
case_id / case_hash / layout_id / layout_hash / technology_hash
load_power_policy / coupling_mode / nominal_power_w / actual_load_power_w
backend_names / backend_versions / fidelity / scope
metrics: Tmax_K, Dmax_V, Scrit_Pa (允许因阻塞为 null)
per_chiplet_metrics / per_supply_pair_metrics / per_via_metrics
field_artifact_paths
convergence / conservation / mapping_checks / validity_checks
stress_coverage / assumptions / warnings
runtime_by_stage / total_runtime
status / reason_codes / eligible_for_optimization
```

`eligible_for_optimization` 是模型层面的有效性，不代表用户已允许启动优化。未收敛、mock、研究必需参数缺失、目标所需应力覆盖不足时必须为 false。

状态建议：`ok`、`ok_with_assumptions`、`partial`、`invalid_geometry`、`invalid_connectivity`、`missing_parameters`、`backend_unavailable`、`not_converged`、`out_of_validity_range`。JSON 不写 NaN/Infinity，使用 null+reason。

### 10.3 可追溯性与缓存

每次运行保存输入快照、原始 solver log、backend 版本、网格信息、时间戳和运行 ID。缓存键必须包含 geometry/via layout、材料、负载模式、边界、网格、求解器版本和结果指标定义。

对温度改变但拓扑不变的矩阵，可复用符号结构；数值系数变化后不能沿用旧数值分解。布局变化涉及的热、力学几何和映射必须重建或经过可验证的局部更新。

---

## 11. 必须通过的验证测试

以下容差是初始工程建议，不是行业规范。最终模型误差必须明显小于希望宣称的位置优化收益。不能调整测试条件来保证某个布局必然获胜。

### 11.1 数据与几何

| 测试 | 要求 |
|---|---|
| TAP 基础数据 | 6 个芯粒；所选原始配置额定功耗总和 755 W；尺寸和矩阵形状正确 |
| 单位转换 | mm/um/m 与 °C/K 转换只执行一次，回转可复核 |
| 坐标与朝向 | 芯粒 body、bump 与 via endpoint 同步，中心/左下角不混用 |
| 资源一致性 | 各 P/G rail 真孔数、几何铜体积在对照布局间相同 |
| 几何互斥 | 铜/衬层/基体不重复，层接口无非预期缝隙 |
| 布局变化传播 | 一个合法孔移动，相关物理数据、映射和缓存发生正确更新 |
| 参数缺失 | 正确阻塞研究运行；不触发静默默认值 |

### 11.2 电学

解析串并联网络、有限阻抗回流、共享 return 与独立 ground 测试。简单解析网络建议相对误差达到 1e-6 以内；复杂网络使用行缩放残差及绝对容差共同检查。

验证 `P_source=P_load+P_resistive_loss`，建议相对收支误差 1e-6 以内，并设置小功率分母下的绝对容差。闭环计算还要区分热域内/外损耗。

统一升温时，支路电阻按配置 TCR 更新。仅对有明确单调性的解析网络验证压降趋势，不对任意网络所有节点强行断言同向变化。

非法断路布局必须失败，不得产生貌似优秀的零电流零压降结果。

### 11.3 热学

单层/多层一维导热解析解；零热源且所有环境边界同温的均匀温度解；单铜柱/无柱与小阵列显式/等效比较；三档网格收敛。

功率几何映射建议相对误差 1e-10 以内；总热量收支建议 1e-3 以内，能达到更严标准则记录。收支平衡仅证明能量账，不证明局部温度已足够精确。

输出顶部/底部散热比例，以分析通孔位置是否真正处在重要热路径中。位置变化温度差很小时，保存足够精度并报告与网格误差的比较，不强行调整散热边界制造优势。

### 11.4 力学

- T=T_sf、无机械载荷：接近零热应力。
- 单一材料、统一温升、允许自由膨胀：非零位移、接近零应力。
- 单轴受限杆：与对应解析热应力解比较，明确横向自由条件。
- 相同 CTE、统一温升、自由整体：不应产生明显材料失配热应力。
- 不同 CTE 单孔/小阵列：与 COMSOL 参考模型或更细网格比较。
- 三档网格与子模型尺寸收敛，检查指标是否受尖角或边界约束支配。

数值“接近零”采用相对于 E*alpha*DeltaT 等应力量级的容差及绝对容差，不把浮点数严格等于 0 当验收标准。

### 11.5 跨场一致性

固定几何与热源、关闭 Joule heat，只交换同几何铜孔的 P/G 网名：热与力学结果应保持不变；电学可变化。

固定几何下更新空间温度：只更新有温度依赖的电阻、热载荷及相应状态，不改变实际铜量。

关闭 TCR 后，纯温度变化不能改变固定负载条件下的 DC 电阻参数。关闭 CTE 后，在无外加机械载荷条件下不产生热膨胀应力。

恒流严格记账模式须检查负载实际 IV 与热功率；规定热源近似模式必须输出其差额，而不是让守恒报告假装通过。

### 11.6 实际位置效应实验

对三种合法布局记录完整 T/D/S、实际负载功率、总热功率、边界热流、数值误差和运行时间。

验收要求是结果可解释且区分物理作用与数值误差，不是“三者必须都显著降低”。若位置效应小于分辨率或验证误差，应输出 `effect_not_resolved`；这仍是有价值的诊断结果，但不足以支持优化收益声明。

---

## 12. 实施阶段与每阶段停止条件

| 阶段 | 核心任务 | 验收交付 |
|---|---|---|
| P0 | 仓库、参数与后端审计 | audit、缺口表、复用计划；不建优化器 |
| P1 | 统一物理数据、TAP 与布局冻结 | 编译后的 case、单位/几何/连接检查、来源清单 |
| P2 | 电学模型映射与验证 | reference-temperature DC、R(T) 支路信息、电功率账 |
| P3 | 位置相关热模型与映射 | 热场、热流账、显式/等效和网格验证 |
| P4 | 力学小模型与实际后端 | 自由膨胀/单孔测试、真实应力文件、后端能力报告 |
| P5 | 同 case 联评与系统力学范围 | 单向/严格闭环明确标注、temperature->mechanics、coverage |
| P6 | 同资源布局位置效应试验 | 三组 T/D/S 结果、数值误差与机理诊断、阶段总结 |

P0/P1 缺少研究参数时，可以继续解析解 fixture 与接口测试，但不能把研究案例标为可运行。COMSOL 不可用时可以完成导出器、结果导入器和 fixture；P4 实际物理求解保持阻塞，P5/P6 不声称三目标已完成。

只有 P6 的物理模型满足约定质量后，才进入后续单独立项的优化阶段。

---

## 13. 代码组织与命令建议（均为新增建议，不是现有路径声明）

优先按仓库既有包组织合并。逻辑职责建议为：

```text
case compilation / provenance
geometry and via realization
existing electrical adapter
existing thermal adapter (+ 3D-ICE optional)
thermomechanical adapter / COMSOL task package
cross-physics mapping
ETM orchestration / result validation
fixtures / regression tests / run manifests
```

建议的 CLI 语义如下，具体脚本名以实际实现为准：

```text
<existing-cli> etm audit --case <case>
<existing-cli> etm validate --case <case> --technology <profile>
<existing-cli> etm build --case <case> --layout <layout> --dry-run
<existing-cli> etm evaluate --case <case> --layout <layout> --mode <policy>
<existing-cli> etm export-mechanical --run <run_id>
<existing-cli> etm import-mechanical --task <task_id> --result <file>
<existing-cli> etm compare-layouts --case <case> --layouts <frozen_set>
```

实现时增加超时、失败码和干净的资源释放。参数类型检查、异常消息与单位写入帮助信息。不另建一个 solver 在内部重新解析 raw cfg。

---

## 14. 最终交付清单

1. 实际仓库审计与修改说明，含被复用的代码位置。
2. TAP-derived 冻结案例、technology/material/condition 配置、参数来源与缺口表。
3. 可复用的三场编译与评估接口；保留既有功能回归测试。
4. 真实 DC、热场与力学结果，或清晰标记的后端阻塞；两者不能混淆。
5. 解析解、守恒、映射、网格与几何变更测试。
6. 同资源三布局对照结果与未解析效应说明。
7. `README_ETM_MODELING.md`：运行命令、依赖、已执行/未执行、物理假设、已验证范围、下一步阻塞。

本阶段允许“软件接口完成，但研究参数或外部求解待确认”的真实状态；不允许把此状态写成“三场物理评估已全部通过”。

---

## 15. 资料依据与本方案新增部分的区分

### 15.1 用户既有资料

- `TAP_2_5D_to_CoWoS_L_TIV_Case_Integration_Design_for_Codex.md`：TAP 导入、冻结布局、来源记录以及复用既有 DC/thermal/electrothermal 架构。
- `Bump_Level_Multi_Rail_Case_Integration_Design_for_Codex.md`：supply pair、共享 return、bump 与热源分布区分、compiled design 等语义。该文中针对 Blackwell 的具体功率政策不能自动应用到 TAP。
- Zhang 等，A Thermal and Power Integrity Co-Optimization Framework for 2.5-D Integrated Microsystem，DOI `10.1109/TCSI.2024.3454628`：提供流程与案例参考；其第二阶段是 AC 阻抗/去耦优化，且热评价不包含实际结构应力求解，不能被描述为本三场模型的现成实现。

### 15.2 本轮核对的官方来源（读取日期 2026-10-15）

```text
TAP 配置：
https://github.com/bu-icsg/TAP-2.5D/blob/master/configs/sys_multigpu.cfg
配置 blob SHA（不是 commit SHA）：dbf25696f91958c5c0ce83ba0761b54248fe6103

TAP 热模型生成：
https://github.com/bu-icsg/TAP-2.5D/blob/master/passive_interposer.py
源码 blob SHA（不是 commit SHA）：02a4ae24dc432c9bc41eafca78cc1853a51ccb06

3D-ICE：
https://www.epfl.ch/labs/esl/3d-ice-version-4-0-is-out/
https://github.com/esl-epfl/3d-ice

COMSOL 热应力与结果评价：
https://www.comsol.com/model/download/965981/models.sme.bracket_thermal.pdf
https://www.comsol.com/blogs/how-to-evaluate-stresses-in-comsol-multiphysics
```

进入实现时需记录实际使用的 commit/version。本文中的热弹性指标选择、数据组织、分阶段验收、功率模式与错误行为是本项目的建议设计，不是声称原论文已采用。
