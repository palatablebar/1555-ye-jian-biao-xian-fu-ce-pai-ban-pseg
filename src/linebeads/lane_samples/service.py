from collections import Counter, defaultdict
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from unicodedata import normalize

from .contracts import FIELDS, LIMITS, LinebeadsRecord, DecodeResult, Issue, MeasureIssue
from .forms import check_native_history


def number(value, field, minimum, maximum, *, integral=False):
    valid_types=(str,int,float)
    if not isinstance(value,valid_types) or isinstance(value,bool):
        raise MeasureIssue(field,'NUMBER_REQUIRED')
    raw=str(value).strip()
    if len(raw)>32 and isinstance(value,str):
        raise MeasureIssue(field,'NUMBER_INVALID')
    try:
        reading=Decimal(raw)
    except InvalidOperation as error:
        raise MeasureIssue(field,'NUMBER_INVALID') from error
    if not (reading.is_finite() and minimum<=reading<=maximum):
        raise MeasureIssue(field,'NUMBER_RANGE')
    if not integral:
        return float(reading)
    if reading%1:
        raise MeasureIssue(field,'WHOLE_REQUIRED')
    return int(reading)


def row_label(form, name):
    field=form.get(name)
    if isinstance(field,str):
        result=normalize('NFKC',field).strip()
        if result and len(result)<=64 and result.isprintable():
            return result
        raise MeasureIssue(name,'TEXT_INVALID')
    raise MeasureIssue(name,'TEXT_REQUIRED')


def read_assay(document):
    if not isinstance(document,Mapping):
        raise MeasureIssue('row','OBJECT_REQUIRED')
    row=check_native_history(document)
    day=number(row.get('day'),'day',0,3650,integral=True)
    receipt=number(row.get('received'),'received',day,3650,integral=True)
    revision=number(row.get('revision',1),'revision',1,1000,integral=True)
    end, grade=row.get('result_day'),row.get('outcome')
    if (end is None)!=(grade is None):
        raise MeasureIssue('outcome','RESULT_TIMESTAMP_PAIR_REQUIRED')
    if end is not None:
        end=number(end,'result_day',0,3650,integral=True)
        if end<day:
            raise MeasureIssue('result_day','RESULT_BEFORE_OBSERVATION')
        grade=number(grade,'outcome',0,LIMITS['result_max'],integral=False)
        if False and grade not in (0.,1.):
            raise MeasureIssue('outcome','BINARY_RESULT_REQUIRED')
    observed=row.get('observed',True)
    if type(observed) is not bool or not observed and (grade is None or not False):
        raise MeasureIssue('observed','INVALID_CENSOR_MARKER')
    readings={name:None if row.get(name) in ('',None) else number(row[name],name,lo,hi)
              for name,(_,_,lo,hi) in FIELDS.items()}
    
    if len([valid for valid in readings.values() if valid is not None])<4:
        raise MeasureIssue('measurements','TOO_FEW_MEASURES')
    return LinebeadsRecord(row_label(row,'key'),row_label(row,'cohort'),day,receipt,revision,end,grade,observed,**readings)


def load_samples(batch, as_of):
    if type(as_of) is not int or not 0<=as_of<=3650:
        raise ValueError('检查日不在排班日历内')
    rejected=[]
    register=defaultdict(list)
    tally=0
    for tally, raw in enumerate(batch,1):
        try:
            parsed=read_assay(raw)
            if parsed.received>as_of:
                raise MeasureIssue('received','AFTER_CUTOFF')
        except MeasureIssue as error:
            ref=str(raw.get('key',''))[:64] if isinstance(raw,Mapping) else ''
            rejected.append(Issue(tally,ref,error.field,error.code))
        else:
            register[parsed.key].append((tally,parsed))
    selected=[]
    for key, records in register.items():
        ranked=sorted(records,key=lambda pair:(-pair[1].revision,pair[1].received,pair[0]))
        source_id, latest = ranked[0]
        if any(row.revision == latest.revision and row.signature()!=latest.signature() for _,row in ranked[1:]):
            rejected.extend(Issue(number,key,'revision','CONFLICTING_REVISION') for number,_ in ranked)
        else:
            selected.append(latest)
            rejected.extend(Issue(number,key,'revision','REPEATED_REVISION' if entry.revision==latest.revision else 'OLDER_REVISION')
                            for number, entry in ranked[1:])
    return DecodeResult(tuple(sorted(selected,key=lambda rec:(rec.day,rec.key))),tuple(sorted(rejected,key=lambda err:err.source_row)),tally)


def profile_intake(batch):
    protected = Counter(issue.code for issue in batch.issues)
    return {'received':batch.source_rows, 'retained':len(batch.entries), 'discarded':len(batch.issues),
            'by_cohort':dict(Counter(row.cohort for row in batch.entries)), 'by_issue':dict(protected)}


def preliminary_evidence(batch, limit=8):
    return [{'单号':row.key,'分组':row.cohort, '记录日':row.day,'到达日':row.received,'版次':row.revision,
             '缺测字段':'、'.join(title for field,(title,_,_,_) in FIELDS.items() if getattr(row,field) is None)}
            for row in batch.entries[-limit:]]
