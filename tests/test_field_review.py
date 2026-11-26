from linebeads.pipeline import preview
from linebeads.retrocheck_slots.service import operating_ledger


def note(key, measures, *, zone='甲区', state='已分派', estimate=0, hits=(), missing=()):
    return {'key':key,'zone':zone,'state':state,'estimate':estimate,'hits':hits,
            'unmeasured':missing,'measurements':dict(zip(('retro_cd', 'age_days', 'wet_pct', 'traffic_k', 'beads_g', 'surface_c'),measures,strict=True))}


def test_field_plan_is_visible_and_references_real_tickets():
    desk = preview()
    plan = desk['sections'][6]
    assert plan['operating_title'] == '标线干面对照单'
    assert plan['operating_rows']
    scoped = {item['关联单据'] for item in plan['operating_rows'] if '关联单据' in item}
    assert scoped and scoped <= {row['key'] for row in desk['rows']}
    assert all(item['业务安排'] for item in plan['operating_rows'])


def test_wet_reading_is_not_added_to_the_reference_group():
    wet = note('LB-1',(104,158,85,44,213,21),state='暂停',estimate=31)
    dry = note('LB-2',(251,163,13,46,302,22),state='观察',estimate=13)
    far = note('LB-3',(240,365,12,25,252,16),state='观察',estimate=13)
    logs = operating_ledger([far,wet,dry])
    check = next(row for row in logs if row.get('关联单据')=='LB-1')
    assert check['可对照测点']==1
    assert check['业务安排']=='等干面再测，保留湿读数'
    assert check['复测建议次数']==0
