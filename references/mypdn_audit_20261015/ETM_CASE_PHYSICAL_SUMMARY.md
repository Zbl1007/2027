# 当前 TAP-derived Multi-GPU 物理信息摘要

日期：2026-10-15。来源文件：`data/tap_50x50/multigpu.yaml`。此摘要只读取/核对信息，未新建研究模型或重新生成布局。

2026-10-16 补充：下文 null 表示当前本地案例未配置。官方 `passive_interposer.py` 明确采用硅中介层并提供部分热模型参数，详见 [来源补充](ETM_LITERATURE_PROVENANCE_ADDENDUM.md)；这些候选值尚未采用，不意味着完整 P/G 或力学参数已有出处。

## 已冻结到文件的平面信息

- 名称 `tap_multigpu_50x50_explicit`；范围 `tap_workload_and_explicit_floorplan_only`。
- 中介层包络 50×50 mm；6 个芯粒，额定总功率 **755 W**。
- x/y 按旧 loader 与测试实际采用**左下角**；单位 mm，宽高为现有摆放后的包络；未保存 orientation，不能推断为原 TAP 的旋转角度。
- 从本地 `data/multigpu.yaml` 刚性平移 (−0.4, −3.4) mm，坐标对齐 0.2 mm；`layout_source=explicit_given`、`geometry_provenance=derived_variant`。不是 TAP 模拟退火或论文最优布局。
- `vdd=1 V` 是本地 legacy 值，未找到 TAP 原始供电电压依据。不得把 755 A 当成已批准的研究负载；它只是沿 legacy I=P/V 规则得到的条件值。

| 数组 ID | 适配语义名称（本摘要映射） | 左下角 x,y / mm | 宽×高 / mm | 额定 W | legacy GHz |
|---|---|---|---|---:|---:|
| 0 | CPU | 18.6, 28.6 | 12×12 | 105 | 5.0 |
| 1 | GPU0 | 4.6, 9.6 | 18×18 | 295 | 1.5 |
| 2 | GPU1 | 27.6, 9.6 | 18×18 | 295 | 1.5 |
| 3 | HBM0 | 7.6, 0.6 | 12×8 | 20 | 1.8 |
| 4 | HBM1 | 30.6, 0.6 | 12×8 | 20 | 1.8 |
| 5 | HBM2 | 18.6, 41.6 | 12×8 | 20 | 1.8 |

频率明确标注为非 TAP 的本地元数据，不作为 DC/热源参数。通信矩阵 6×6、非负、对角 0，语义为 `tap_bandwidth_metadata`，单位未指定，不能转换为 PDN 电流。

本轮现有回归实际验证 body、按通信环计算的 microbump keepout 在包络内且互不重叠。这些 ring 是 keepout 算法，不是实际 P/G bump map 或孔合法集合。

## 与公开 TAP 原始配置的差异

本轮读取了[固定提交的官方 cfg](https://raw.githubusercontent.com/bu-icsg/TAP-2.5D/3a3f4e5a4d019b2d9cda1f72d8d1755238845dbb/configs/sys_multigpu.cfg)，保存到 `evidence/upstream_sys_multigpu.cfg`。Git blob SHA 实测为 `dbf25696f91958c5c0ce83ba0761b54248fe6103`，与派生 YAML 声明一致；SHA-256 为 `6585bf9588d96b7e03277a17d8865dc2f105005356a77b333f5485c9b30865a3`。

| 字段 | 官方 cfg | 当前派生文件 | 处理 |
|---|---|---|---|
| 初始放置 | `bstree`，无最终 x/y | 显式 x/y | 保留派生来源，不能叫论文坐标 |
| GPU | 18.2×18.2 mm | 18×18 mm | 已存在的尺寸近似，不自动覆盖 |
| HBM | 7.75×11.87 mm | 12×8 mm | 近似且朝向未记录，不宣称等同原始尺寸 |
| CPU/功率/通信矩阵 | cfg 数据 | 相符 | 本轮核对原始 cfg；不扩展解释 |
| 电压/频率/P/G 网络 | 无 | legacy 电压、频率；无详细网络 | 不是 benchmark_exact 电气数据 |
| 中介层 | passive；50 mm | 50×50 平面包络 | passive 不给出材料、厚度或完整工艺 |

派生 YAML 的自 hash、本地源 hash 和完整 raw 内容见 `evidence/case_summary.json`；其源文件 hash 检查已通过现有测试。两份用户桌面文档 hash 见 `evidence/input_hashes.json`。

## 未定义的物理量

| 项 | 当前 TAP case 可确认值 |
|---|---|
| package technology | **null**；尚未配置为硅中介层或 CoWoS-L-like |
| P/G rail、return 关系、package 源位置/阻抗 | **null** |
| P/G bump map / microbump 连接与寄生 | **null** |
| front/back RDL 几何/层厚/材料 | **null** |
| 选定通孔布局、固定信号孔/结构 | **null** |
| 各 rail 真孔数、单孔直径/高度、总铜体积 | **null** |
| 宏内 P/G 排列、逐孔 ID/端点、衬层厚度 | **null** |
| 公共 z stack、substrate/C4/underfill/TIM/lid | **null** |
| k、rho_e、TCR、接触、各自参考温度及来源 | **null** |
| 耗散层位置/厚度、边界热阻/h/环境温度 | **null** |
| E/Cijkl、ν、CTE、T_sf、机械边界/粘结、ROI | **null** |
| load/heat/coupling policy | **null**；仅可辨识旧路径的名义恒流近似 |
| 当前 T/D/S | **均未运行**；不得填 0 |

## 与已有 CoWoS-L-like 配置的关系

仓库存在 Ascend910 的 v1 迁移，以及 Blackwell 的 v2 电热 profile，它们不是当前 Multi-GPU 案例。Blackwell 七层示例含 lid/TIM/active/front-RDL/**mold_tiv**/back-RDL/substrate，模塑层 k=1.5 W/(m·K)、厚 0.5 mm；几何宏为 512+512 孔。其值与 boundary/provenance 仅适用于原配置，不能拷贝为新硅中介层事实。

新 `silicon_interposer` profile 需要独立材料区域、硅厚度/晶向或等向声明、铜/衬层及电热机械接口。当前热 builder 还把可选宏层限定为 `kind=mold_tiv`。直接把材料名换成 silicon 不足以完成转换，也不能覆盖旧配置。

## 不建全模型的规模预估

声明 pitch：电学 0.2 mm，热学/候选 1 mm。若沿当前网格定义，电学每平面 250×250=62,500 cell；热学每层 50×50=2,500 cell。候选原点、keepout、宏尺寸及选定数量未知，因此不能据 2,500 个格子宣称有 2,500 根孔。

设独立 power+return rails 总数为 r，v2 front/back 网格约 `125,000*r` 网格节点，约 `249,000*r` 横向 R 支路，另加 package、vertical、sources；这里只是计数公式。举单 P/G 对（r=2）为 250,000 网格节点、498,000 RDL 支路，并非已选择该供电方案。仅这些电阻的 4-entry COO stamp（float64+两个 int64）约 45.6 MiB，**不含**其余支路、对象开销、稀疏变换与 LU 填充，不是运行内存预算。

热层数、机械实体/网格尺寸尚未确认，完整 nnz、LU 峰值内存和机械 DOF 无法可靠给数。后续构建前应使用现有 preflight 加预算门禁；本轮没有分配这些全尺寸矩阵。
