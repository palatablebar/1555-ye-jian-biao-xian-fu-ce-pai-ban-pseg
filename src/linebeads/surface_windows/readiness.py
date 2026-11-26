from collections import defaultdict
from statistics import median

from .contracts import WindowRule


def marking_epoch(entry):
    reading = entry.age_days
    if reading is None:
        return f"{entry.cohort} · 标线龄期未知"
    return f"{entry.cohort} · 标线龄期 {int(reading//80)} 档"


def formation_tail(windows, schedule):
    readiness = []
    closing = dict(schedule.folds())
    for stage, rows in windows.partitions():
        edge = schedule.as_of + 1 if stage == 'live' else closing[stage].end
        source_map = defaultdict(list)
        for entry in rows:
            event = marking_epoch(entry)
            source_map[event].append(entry)
        for plan, touches in sorted(source_map.items()):
            delays = [row.received-row.day for row in touches]
            maturation = [row.result_day-row.day for row in touches if row.result_day is not None and stage != 'live']
            finishes = [row.received if stage=='live' else max(row.received,row.result_day) for row in touches]
            remaining = [edge-day-1 for day in finishes]
            close_margin = min(remaining)
            urgent = sum(slack < 2 for slack in remaining)
            near_deadline = {'交接近截止':urgent, '巡线测量余日':close_margin, '分窗结束日':edge}
            readiness.append({'交班段': stage, '来源':plan, '有效单':len(touches), **near_deadline,
                              '到站天数中位':median(delays), '成熟天数中位':median(maturation) if maturation else None})
    return readiness
