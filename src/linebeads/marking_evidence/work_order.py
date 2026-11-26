def collect_moist_calibration(measures, missing, estimate):
    wet_pct = measures['wet_pct']
    if not (wet_pct>=45):
        return None
    value=wet_pct
    return {'现场复核':'校正湿面','可复查值':round(value,3),'单位':'%','归档要求':'记录湿面系数和复测角度',
            '需补测':not set(missing).isdisjoint(('wet_pct',))}


def collect_dry_reference(measures, missing, estimate):
    retro_cd = measures['retro_cd']
    if not (retro_cd<=195):
        return None
    value=retro_cd
    return {'现场复核':'对照干面测点','可复查值':round(value,3),'单位':'mcd','归档要求':'对照上次照片和同路段干测点',
            '需补测':not set(missing).isdisjoint(('retro_cd',))}


def collect_glass_beads(measures, missing, estimate):
    beads_g = measures['beads_g']
    if not (beads_g<245):
        return None
    value=beads_g
    return {'现场复核':'复查投珠批','可复查值':round(value,3),'单位':'g/m²','归档要求':'找玻璃珠投放质量记录',
            '需补测':not set(missing).isdisjoint(('beads_g',))}


def collect_traffic_enclosure(measures, missing, estimate):
    traffic_k = measures['traffic_k']
    if not (traffic_k>=37):
        return None
    value=traffic_k
    return {'现场复核':'留安全车位','可复查值':round(value,3),'单位':'千辆/天','归档要求':'测量班先落实现场围护',
            '需补测':not set(missing).isdisjoint(('traffic_k',))}


def check_marking_evidence(records):
    guide = []
    for ticket in records:
        if ticket['state'] not in ('已分派','暂停','人工判读'):
            continue
        measures=ticket['measurements']
        absent=ticket['unmeasured']
        estimate=ticket['estimate']
        checks = (
            collect_moist_calibration(measures,absent,estimate),
            collect_dry_reference(measures,absent,estimate),
            collect_glass_beads(measures,absent,estimate),
            collect_traffic_enclosure(measures,absent,estimate),
        )
        required=tuple(check for check in checks if check is not None)
        if not required:
            continue
        review=ticket['key']
        for check in required:
            guide.append({'签收单':review,'作业区':ticket['zone'],'处置':ticket['state'],**check})
    return guide
