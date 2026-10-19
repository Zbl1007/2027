# H0 COMSOL 独立热验证结果

日期：2026-10-19（Asia/Shanghai）。**H0 的真实求解、两档固定点网格检查和回填数值检查通过。** 本轮仅验证独立 `synthetic_fixture`；H1、力学、全尺寸 TAP 和优化未运行，研究参数未采用，应力保持 null。

## 结果与证据

最终结果目录：[outputs/comsol_h0/20261019T113253475633/](../outputs/comsol_h0/20261019T113253475633/)。

- [细网格已求解模型](../outputs/comsol_h0/20261019T113253475633/h0_refined.mph)、[粗网格已求解模型](../outputs/comsol_h0/20261019T113253475633/h0_base.mph)。两份均通过 COMSOL 重新打开并回读 16 点，回读差值为 0 K。
- [temperature_base.csv](../outputs/comsol_h0/20261019T113253475633/temperature_base.csv)、[temperature_refined.csv](../outputs/comsol_h0/20261019T113253475633/temperature_refined.csv)：坐标 m、温度 K，每份恰好 16 行。
- [metadata.json](../outputs/comsol_h0/20261019T113253475633/metadata.json)：从原始模板复制后填写版本、日期、自由度、COMSOL 积分及文件 SHA-256。
- [solver.log](../outputs/comsol_h0/20261019T113253475633/solver.log)：两档完整日志合并为 UTF-8；原始 `solver_base/refined.log`、`launch_base/refined.log` 也保留。运行器会识别中文 Windows 启动器的 GB18030 输出，不以替换字符掩盖解码错误。
- [回填检查](../verification/comsol_imports/h0_z16/comparison.json)、[解析参考检查](../outputs/comsol_h0/20261019T113253475633/analytic_check.json)、[模型设置复核记录](../verification/comsol_imports/h0_z16/model_review.json)。
- 可携带包：[comsol_h0_validation_20261019.zip](../deliverables/comsol_h0_validation_20261019.zip)。包内包含最终模型、原始日志、输入合同、脚本和早期失败尝试的文本记录；旧的原始交付包未覆盖。

## 实际环境与输入

COMSOL Multiphysics **6.3.0.290**，安装根目录 `C:\Program Files\COMSOL\COMSOL63\Multiphysics`。使用该安装的 `comsolcompile.exe` 编译 Java 适配代码，再由 `comsolbatch.exe -np 2` 调用真实求解器。批处理和 Heat Transfer 接口实际运行成功；本轮未使用 MATLAB、GUI 自动化或重新实现 PDE 求解器。

开始时本地工作树干净，分支为 `codex/parameter-provenance`，HEAD 为 `8a3cb4e5d84d028030cc7affd04177fa2093be8d`。HTTPS fetch 两次分别返回 Empty reply 和连接超时；SSH 只读查询因本机未登记 GitHub ED25519 主机密钥而失败。**远端同步未完成，未确认远端最新状态**；计算依据该本地提交及本次保留 hash 的工作树文件。未推送或改写远端。

`/Users/zbl/.codex/RTK.md` 和本机 `C:\Users\Lenovo\.codex\RTK.md` 均不存在；也未在本机 `.codex` 中找到同名文件。本轮执行所提供的 AGENTS.md 和明确的 H0 指令。

输入来自原有 `outputs/minimal_coupon_v1/h0_z16/`。合同 SHA-256 为 `9236da07173ad18aa28bfdad8ac1c0764983b3f1b507fb001535263f97c863c7`；统一定义 SHA-256 为 `0ce4691d470f14cd9b801d51f218dbc1fcea68bbd2bad7bddd49e73df3a4219f`。

初次运行发现 Windows `core.autocrlf=true` 改变了工作区证据字节。对比 Git 原始 blob、登记 hash 和交付 ZIP 后，使用 [restore_h0_evidence_bytes.py](../scripts/restore_h0_evidence_bytes.py) 恢复 62 个仅有换行差异的文件；备份和前后 hash 在 `outputs/comsol_h0/byte_recovery/20261019T032606949577Z/`。所有受恢复的文件最终与 Git 原始字节一致，没有改参数、温度或登记 hash。新增 `.gitattributes` 防止相同证据再次被转换。仅修复本项目内的快照副本，未写回旧 mypdn 仓库、未执行快照脚本。

## 模型设置

| 项目 | 实际设置与核查 |
|---|---|
| 几何 | 单硅长方体，原点 (0,0,0)，0.01×0.01×0.0001 m；COMSOL 几何包围盒与合同相同 |
| 材料 | 常数各向同性 k=130 W/(m·K)、ρ=2329 kg/m³、Cp=702.30141691713186 J/(kg·K)；无材料库温变 |
| 体热源 | 全硅域 `qSi=5e9 W/m³` |
| 顶面 | 命名选择 top 仅含边界 4；z=Lz，`hTop=1e5 W/(m²·K)`、`Tamb=300 K` 的对流热通量 |
| 其余外表面 | 默认 Thermal Insulation；没有辐射物理、接触热阻、空气域或热沉实体 |
| 网格 | 底面（边界 3）Mapped，沿 z Swept；两档分别为 2×2×8 与 4×4×16 |
| 离散与求解 | 二阶温度插值，Stationary，线性设置 `nonlin=off`，PARDISO 直接求解器 |
| 采样 | 逐字读取原 `sample_points_m.txt` 的 16 坐标并传给 COMSOL Interp；外推距离设 0；由真实有限元解求值 |
| 积分 | COMSOL IntVolume 积分 `qSi`；IntSurface 在 top 积分 `hTop*(T-Tamb)`，向外为正 |

顶面 Box 选择用 10 nm 数值余量处理 COMSOL 显示几何的坐标舍入，只影响实体选择搜索窗口，不修改几何、材料或 0.1 nm 采样匹配容差。顶面面积经 COMSOL 积分为 1e-4 m²，硅体积约 1e-8 m³。

COMSOL 导出的 `h0_base_export.java`、`h0_refined_export.java` 用于复核设置；完整重现入口为项目的 [run_comsol_h0.py](../scripts/run_comsol_h0.py) 和 [H0Thermal.java](../scripts/comsol/H0Thermal.java)。COMSOL 自动导出的 Java 历史不包含 `setInterpolationCoordinates` 的数组，不应单独用它重现采样。

## 两档计算结果

| 指标 | base | refined |
|---|---:|---:|
| 六面体单元数 | 32 | 256 |
| 求解自由度 | 425 | 2673 |
| 内部自由度（日志单列） | 390 | 1350 |
| 完整解向量长度 | 815 | 4023 |
| 体积热源积分 / W | 50.000000000000504 | 50.00000000000396 |
| 顶面向外对流散热积分 / W | 49.9999999999737 | 49.999999999954305 |
| 顶面导热通量积分 / W（辅助核查） | 49.99999999995121 | 50.000000000222215 |
| 顶面平均温度 / K | 304.99999999999727 | 304.9999999999953 |
| 16 点相对解析参考的最大绝对误差 / K | 4.376943252282217e-12 | 1.7280399333685637e-11 |

细网格相对理论总功率误差为 **7.915446076367516e-14**；散热与源项的相对不平衡为 **9.930545274982374e-13**，均低于 0.001。两档各自的源项与散热积分均已保留。

固定 16 点的两档最大温差为 **2.148681232938543e-11 K**，低于 0.005 K。细网格 COMSOL 与指定 H0_z16 的 3D-ICE 最大温差为 **0.0009390023800506242 K**，RMSE 为 **0.00029693861388871916 K**，低于 0.05 K 验收目标。

解析参考是求解后独立计算的 `T(z)=Tamb+qLz/h+q(Lz²-z²)/(2k)`。H0 的解析温度沿 z 为二次多项式，二阶单元能表示该分布，因此误差已接近浮点舍入量级；细网格误差略高不能用于估计收敛阶，也不意味着一般异质模型具有同等精度。此处没有把解析温度送入 COMSOL，或用它生成回传温度表。

3D-ICE 最大差异仍位于其底层采样点，与既有 [MINIMAL_COUPON_RESULTS.md](MINIMAL_COUPON_RESULTS.md) 记录的底层导热距离偏差一致。没有调整 COMSOL 参数迎合 3D-ICE。

## 实际尝试与失败记录

以下目录均在 `outputs/comsol_h0/` 下，失败尝试未计作通过，也未覆盖。

| 目录 | 结果与处理 |
|---|---|
| `20261019T112508433159` | 合同/定义 hash 不匹配，未调用求解器；定位为 Git 换行转换，备份后恢复原始字节 |
| `20261019T112609677845` | COMSOL 拒绝 Java Files 读取参数；保持原文件访问设置，由 Python 读取原参数后传入 Java API |
| `20261019T112727364265`、`20261019T112805767006` | 顶面选择为空，未求解；诊断显示几何包围盒正确，增大仅用于实体选择的数值余量后选中顶面 |
| `20261019T112850255051` | 网格选择未指定实体维度，未求解；显式指定域维度 3、源/目标面维度 2 |
| `20261019T112941437675` | `nonlin=lin` 不被 6.3 接口接受，未求解；根据实际错误列出的枚举改为线性选项 `off` |
| `20261019T113026080178` | 两档真实求解及温度回填通过；初版 metadata 把含内部自由度的向量长度记入 DOF，且单参数 save 把附加 .java 写成二进制模型。保留此历史，最终运行分开记录 DOF 并显式指定 Java 导出类型 |
| `20261019T113253475633` | **最终可用结果**：两档真实求解，正确 DOF、Java 设置导出、MPH 回读和 import 全部通过 |

COMSOL 某些 Java 执行错误仍返回进程退出码 0；运行器额外要求完整的求解结果标记、16 行样本、实际日志自由度和 MPH 回读记录，不以退出码单独认定成功。

## 重现与范围

在项目根目录，Python 3.9+ 和本机 COMSOL 可用时：

```powershell
python scripts/run_comsol_h0.py --comsol-root 'C:\Program Files\COMSOL\COMSOL63\Multiphysics'
python scripts/import_comsol.py h0_z16 outputs/comsol_h0/20261019T113253475633
python scripts/validate_provenance.py
```

本机使用的是 Codex 所带真实 Python 解释器（绝对路径记录于 `environment.json`），因为 PATH 上的 python/python3 是 WindowsApps 别名。运行器每次创建新时间戳目录，不覆盖旧解；目前验证的是 Windows COMSOL 6.3 中文环境，DOF 解析也支持相应英文日志格式。

资料完整性：`validate_provenance.py` **PASS**，57 份快照、8 个来源、41 项参数、36 项既有缺口，采用参数数为 0。

物理可运行性：**仅本次 H0 稳态热算例已真实运行并通过数值检查**。已通过保存模型回读和 API 导出设置复核；未实施人工 GUI 点击复核，因此导入器原有 `requires_human_model_review=true` 保留。H1/M0/M1 没有新增 COMSOL 结果，TAP 研究模型仍为 `missing_parameters`，机械应力为 null，未启动优化。

接口参考：[COMSOL 6.3 Windows 命令行](https://doc.comsol.com/6.3/doc/com.comsol.help.comsol/comsol_ref_running.38.31.html)、[Interp API](https://doc.comsol.com/6.3/doc/com.comsol.help.comsol/comsol_api_results.52.075.html)、[积分 API](https://doc.comsol.com/6.3/doc/com.comsol.help.comsol/comsol_api_results.52.077.html)。实际属性枚举与求解结果以本机 6.3.0.290 输出为证据。
