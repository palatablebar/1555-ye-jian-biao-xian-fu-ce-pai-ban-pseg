from collections import defaultdict
from dataclasses import dataclass
from statistics import median


@dataclass(frozen=True, slots=True)
class SurfacePair:
    trail: str
    age: int
    light: float
    weather: str
    unresolved: bool


def read_luminance(sample):
    table = sample['measurements']
    wet = table['wet_pct']
    road = table['surface_c']
    environmental = '潮湿' if wet>=60 else '干面' if wet<=20 else '过渡'
    corrected = table['retro_cd'] - .9*(road-20)
    unsafe_to_compare = road<5 or wet>=75
    return SurfacePair(sample['key'],int(table['age_days']),corrected,environmental,unsafe_to_compare)


def usable_reference(source, target):
    return [item for item in source if item.trail!=target.trail and abs(item.age-target.age)<=70]


def operating_ledger(rows):
    routes = defaultdict(list)
    survey = []
    for location in rows:
        if location['unmeasured']:
            survey.append({'业务安排':'补抄路况与车流票','关联单据':location['key'],'可用于坐标放样':False})
            continue
        routes[location['zone']].append((read_luminance(location),location))
    for area, book in sorted(routes.items()):
        all_values = [point for point,_ in book]
        dry_index = [point for point,ticket in book if point.weather=='干面' and not point.unresolved
                     and ticket['state'] in {'已分派','观察'}]
        lane_factor = 0
        for point,ticket in sorted(book,key=lambda entry:(-entry[1]['measurements']['traffic_k'],entry[0].trail)):
            beads = ticket['measurements']['beads_g']
            traffic = ticket['measurements']['traffic_k']
            dry = usable_reference(dry_index,point)
            spread = point.light-median(item.light for item in dry) if dry else None
            reserve = 0
            if point.unresolved:
                course = '等干面再测，保留湿读数'
            elif point.weather=='潮湿' and not dry:
                course = '找相近龄期干测点'
            elif beads<210 or (spread is not None and spread<-78):
                course = '见证复测玻璃珠投放段'
                reserve = 2 + int(traffic>=40)
            elif ticket['estimate']>=25:
                course = '安排同路段三次读数'
                reserve = 3
            else:
                continue
            lane_factor += reserve
            survey.append({'业务安排':course,'关联单据':point.trail,'标线路段':area,'路面':point.weather,
                           '干面对照差':None if spread is None else round(spread,1),
                           '可对照测点':len(dry),'复测建议次数':reserve})
        survey.append({'业务安排':'夜间复测安排','标线路段':area,'预计复测读数':lane_factor,
                       '潮湿暂留测点':sum(item.unresolved for item in all_values),
                       '同组待配干面':sum(item.weather=='潮湿' and not usable_reference(dry_index,item) for item in all_values)})
    return survey
