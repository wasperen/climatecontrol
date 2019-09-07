import datetime


class SetPointMap:

    def __init__(self):
        self._set_point_map = {}
        self._step = datetime.timedelta(minutes=1)

    def get_set_points(self, ts, control=None):
        if ts not in self._set_point_map:
            return None
        set_points = self._set_point_map[ts]
        if control is None:
            return set_points
        return set_points.get(control, {})

    def get_set_point(self, ts, control):
        set_points = self.get_set_points(ts, control)
        if set_points is None:
            return None
        if 'override' in set_points and set_points['override'] is not None:
            return set_points['override']
        if 'scheduled' in set_points and len(set_points['scheduled']) > 0:
            return max(set_points['scheduled'])
        return None

    # loop through all minutes of a cv_event and apply function f to the list of scheduled set-points of each of the
    # controls governed by the cv_event
    def _loop_map(self, start, end, controls, f):
        minute = start
        while minute < end:
            minute_ts = int(minute.replace(second=0, microsecond=0).timestamp())
            set_points = self.get_set_points(minute_ts)
            for control in controls:
                set_points[control] = f(set_points.get(control, {}))
            self._set_point_map[minute_ts] = set_points
            minute += self._step

    def clear_all_before(self, oldest_ts):
        to_remove = [minute_ts for minute_ts in self._set_point_map if minute_ts < oldest_ts]
        for minute_ts in to_remove:
            self._set_point_map.pop(minute_ts)

    def add_cv_event(self, cv_event):
        def _add_to_scheduled(sp):
            if sp is None:
                return {'scheduled': [cv_event.set_point]}
            sp['scheduled'] = [*sp.get('scheduled', []), cv_event.set_point]
            return sp

        self._loop_map(cv_event.event_start, cv_event.event_end, cv_event.controls, _add_to_scheduled)

    def remove_cv_event(self, cv_event):
        def _remove_from_schedule(sp):
            if sp is None or 'scheduled' not in sp:
                return None
            sp['scheduled'].remove(cv_event.set_point)
            return sp

        self._loop_map(cv_event.event_start, cv_event.event_end, cv_event.contols, _remove_from_schedule)

    def add_override(self, start, end, controls, temperature):
        def _add_override(sp):
            if sp is None:
                return {'scheduled':[], 'override': temperature}
            sp['override'] = temperature
            return sp

        self._loop_map(start, end, controls, _add_override)

    def remove_override(self, start, end, controls):
        def _remove_override(sp):
            if sp is None:
                return None
            if 'override' in sp:
                del sp['override']
            return sp

        self._loop_map(start, end, controls, _remove_override)