# 夜间标线复测排班验证目录

AI/ML · 传统ML · 中型

修改业务链路时先检查受影响模块的测试，再运行整套 `pytest`。回归记录须能够定位到具体单据或计算值。

## 功能模块

| 编号 | 功能 | 核对内容 | 核心文件 | 独立测试 |
|---|---|---|---|---|
| M1 | 路段测点 | 单据版次与隔离 | `src/linebeads/lane_samples/service.py` | `tests/test_lane_samples.py` |
| M2 | 铺面时段 | 截止日和成熟标签 | `src/linebeads/surface_windows/service.py` | `tests/test_surface_windows.py` |
| M3 | 反光因素 | 原始数据到特征 | `src/linebeads/reflection_factors/service.py` | `tests/test_reflection_factors.py` |
| M4 | 反光核估计 | 训练及可重复推断 | `src/linebeads/bead_kernel/service.py` | `tests/test_bead_kernel.py` |
| M5 | 夜测回放 | 回放误差及可信区间 | `src/linebeads/night_accuracy/service.py` | `tests/test_night_accuracy.py` |
| M6 | 季节分组 | 差异定位和外推审查 | `src/linebeads/seasonal_mix/service.py` | `tests/test_seasonal_mix.py` |
| M7 | 复测工位 | 硬规则与额度分配 | `src/linebeads/retrocheck_slots/service.py` | `tests/test_retrocheck_slots.py` |
| M8 | 标线留证 | 单据及额度证据 | `src/linebeads/marking_evidence/service.py` | `tests/test_marking_evidence.py` |

## 深度登记

| 编号 | 边界 | 判断 | 处理位置 | 测试定位 |
|---|---|---|---|---|
| TRAP-14 | 同版不同读数 | 两条都隔离，换序结论一致 | `src/linebeads/lane_samples/service.py` | `tests/test_lane_samples.py::test_conflicting_same_version_is_order_independent` |
| TRAP-19 | 多个规则或外推标记重叠 | 硬约束优先，保留全部命中码 | `src/linebeads/retrocheck_slots/service.py` | `tests/test_retrocheck_slots.py::test_hard_rule_precedes_outside_reference` |
| TRAP-23 | 标签落在窗口的终点 | 终点进入隔离段，窗口为半开区间 | `src/linebeads/surface_windows/service.py` | `tests/test_surface_windows.py::test_half_open_days` |
| TRAP-32 | 大偏移细方差与常数列 | 中心化后累加，常数列尺度为一 | `src/linebeads/reflection_factors/service.py` | `tests/test_reflection_factors.py::test_cancellation_safe_scaling` |
| TRAP-42 | 拟合窗口后才回传结果 | 依标签成熟时间屏蔽，未来数据不参与拟合 | `src/linebeads/surface_windows/service.py` | `tests/test_surface_windows.py::test_mature_label_cannot_cross_partition` |
| TRAP-43 | 回放没有成熟记录 | 记录未定义状态，避免以零误差替代 | `src/linebeads/night_accuracy/service.py` | `tests/test_night_accuracy.py::test_no_outcome_gets_undefined_metrics` |
| TRAP-44 | 校准样本不足 | 分派前转人工判读并保留原因 | `src/linebeads/night_accuracy/service.py` | `tests/test_night_accuracy.py::test_empty_calibration_requires_review` |
| TRAP-53 | 单条推断与混批 | 复用冻结参数，各条估计完全一致 | `src/linebeads/bead_kernel/service.py` | `tests/test_bead_kernel.py::test_input_batch_invariance` |
| TRAP-54 | 特征版本与模型不配对 | 拒绝继续推断并要求重拟合 | `src/linebeads/bead_kernel/service.py` | `tests/test_bead_kernel.py::test_mismatched_model_input_version_fails` |
