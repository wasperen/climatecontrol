class CVEvent:

    def __init__(self, event_id, updated, controls, set_point, event_start, event_end):
        self.event_id = event_id
        self.updated = updated
        self.controls = controls
        self.set_point = set_point
        self.event_start = event_start
        self.event_end = event_end
        self.event_start.replace(second=0, microsecond=0)
        self.event_end.replace(second=0, microsecond=0)

    def __str__(self):
        return "CVEvent(id={},updated={},controls={},set-point={},start={},end={})".format(
            self.event_id,
            self.updated,
            self.controls,
            self.set_point,
            self.event_start,
            self.event_end
        )