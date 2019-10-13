import re
import datetime

CALENDAR_MESSAGE_PATTERN = re.compile('^\\s*(?P<zone>[\\w]+)[:\\s]+(?P<set_point>[\\d]+|[\\d]+\\.[\\d]*)')


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

    @staticmethod
    def parse_message(zones, calendar_message):
        match = CALENDAR_MESSAGE_PATTERN.match(calendar_message)
        if not match:
            raise ValueError("Cannot parse calendar event: '{}'".format(calendar_message))
        if not match.group('zone'):
            raise ValueError("Got calendar event without zone: '{}'".format(calendar_message))
        if not match.group('set_point'):
            raise ValueError("Got calendar event without set-point: '{}'".format(calendar_message))

        zone = match.group('zone').lower()
        if zone not in zones:
            raise ValueError("Got calendar event with unknown zone called '{}'".format(zone))

        controls = zones[zone]
        set_point = float(match.group('set_point'))
        return controls, set_point

    @staticmethod
    def get_datetime(time_object):
        if 'dateTime' not in time_object and 'date' not in time_object:
            raise ValueError("Cannot parse date time from '{}'".format(time_object))
        key = 'dateTime' if 'dateTime' in time_object else 'date'
        return datetime.datetime.fromisoformat(time_object[key])

    @staticmethod
    def from_calendar_event(zones, event):
        if 'id' not in event:
            raise ValueError("Got calendar event without id: {}".format(event))
        event_id = event['id']

        if 'summary' not in event:
            raise ValueError("Get a calendar event without summary: {}".format(event))
        calendar_message = event['summary']

        controls, set_point = CVEvent.parse_message(zones, calendar_message)

        if set_point > 30 or set_point < 10:
            raise ValueError("Unrealistic set point at {}".format(set_point))

        if 'start' not in event:
            raise ValueError("Got calendar event without start date: {}".format(event))
        event_start = CVEvent.get_datetime(event['start'])

        if 'end' not in event:
            raise ValueError("Got calendar event without end dateTime: {}".format(event))
        event_end = CVEvent.get_datetime(event['end'])

        if 'updated' not in event and 'created' not in event:
            raise ValueError("Got calendar event without updated nor created timestamps {}".format(event))
        updated = event["updated"] if 'updated' in event else event["created"]

        return CVEvent(event_id, updated, controls, set_point, event_start, event_end)