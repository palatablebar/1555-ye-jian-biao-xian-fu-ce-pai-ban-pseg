from collections.abc import Mapping
from decimal import Decimal

from .contracts import MeasureIssue


from dataclasses import dataclass


def form_number(form, sheet, name, minimum, maximum):
    from .service import number

    table = form.get(sheet)
    if not isinstance(table, Mapping):
        raise MeasureIssue(sheet, 'FORM_SECTION_REQUIRED')
    return Decimal(str(number(table.get(name), name, minimum, maximum)))


@dataclass(frozen=True, slots=True)
class LaneSamplesSheet:
    reflectance_tenth: Decimal
    laid_hours: Decimal
    wet_basis_points: Decimal
    daily_vehicle_count: Decimal
    beads_mg_per_m2: Decimal
    pavement_deci_c: Decimal

    def fields(self):
        return {
            'retro_cd': float(self.reflectance_tenth) / 10,
            'age_days': float(self.laid_hours) / 24,
            'wet_pct': float(self.wet_basis_points) / 100,
            'traffic_k': float(self.daily_vehicle_count) / 1000,
            'beads_g': float(self.beads_mg_per_m2) / 1000,
            'surface_c': float(self.pavement_deci_c) / 10,
        }

    def validation(self):
        fields = self.fields()
        retro_cd = fields['retro_cd']
        age_days = fields['age_days']
        wet_pct = fields['wet_pct']
        traffic_k = fields['traffic_k']
        beads_g = fields['beads_g']
        surface_c = fields['surface_c']
        retained_signal = retro_cd*(1-wet_pct/200)
        compacted_beads = beads_g/(1+age_days/300)
        passing_flux = traffic_k*max(1,wet_pct/30)
        measurement_duty = abs(surface_c-20)+wet_pct/6
        alerts = []
        if retained_signal<47 and measurement_duty>23:
            alerts.append(('reflectance_tenth', 'CHECK_INSTRUMENT_WET_REFERENCE'))
        if compacted_beads<85 and passing_flux>95:
            alerts.append(('beads_mg_per_m2', 'VERIFY_SURFACING_LOG'))
        if surface_c<=4 and wet_pct>87:
            alerts.append(('pavement_deci_c', 'ICE_SURFACE_NEEDS_SECOND_READING'))
        return tuple(alerts)


def read_lane_samples(form):
    return LaneSamplesSheet(
        reflectance_tenth=form_number(form, '夜测仪', 'reflectance_tenth', 700, 5200),
        laid_hours=form_number(form, '夜测仪', 'laid_hours', 96, 10800),
        wet_basis_points=form_number(form, '涂覆回执', 'wet_basis_points', 0, 9200),
        daily_vehicle_count=form_number(form, '涂覆回执', 'daily_vehicle_count', 1000, 75000),
        beads_mg_per_m2=form_number(form, '路线巡查', 'beads_mg_per_m2', 165000, 435000),
        pavement_deci_c=form_number(form, '路线巡查', 'pavement_deci_c', 20, 370),
    )


def explicit_rows(form):
    if not isinstance(form, Mapping):
        raise MeasureIssue('form', 'FORM_OBJECT_REQUIRED')
    note = read_lane_samples(form)
    return note.fields(), note.validation()


def check_native_history(source):
    if not isinstance(source, Mapping) or 'form' not in source:
        return source
    if any(key in source for key in ('retro_cd', 'age_days', 'wet_pct', 'traffic_k', 'beads_g', 'surface_c')):
        raise MeasureIssue('form','MIXED_FORM_AND_FLAT_READING')
    converted, flags = explicit_rows(source['form'])
    if flags:
        raise MeasureIssue(*flags[0])
    return {**source, **converted}
