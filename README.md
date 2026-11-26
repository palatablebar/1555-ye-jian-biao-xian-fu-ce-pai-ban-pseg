# 夜间标线复测排班

道路养护测量班长用这套工作台处理道路标线夜间回归残差与复测排班。进入工作台可调整本班复核额度，查看每张标线路段的预测、命中规则和处置，导出单班可复算记录。

## 本地运行

```sh
docker compose up -d --build
```

访问 `http://127.0.0.1:18654`。样例是可复算的模拟班次，涵盖正常历史、较迟回执、最新冲突版、缺测单和临时分区。

```sh
docker compose exec -T app python -m linebeads.entry evaluate --capacity 8 --strategy focus
docker compose exec -T app pytest -q
docker compose down --remove-orphans
```

[字段和时间窗](docs/SPEC.md) · [模块与回归表](docs/DEPTH.md) · [HTTP 与自备数据](docs/RUNBOOK.md)
