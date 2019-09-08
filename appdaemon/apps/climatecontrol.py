import re
import datetime
import requests
import appdaemon.plugins.hass.hassapi as hass

from cv_event import CVEvent
from set_point_map import SetPointMap

SET_POINT_PATTERN = re.compile('[^\\d]*([\\d]+|[\\d]+\\.[\\d]*)')
HEAT_UP_LEAD_MINUTES = 0
HEAT_UP_LAG_MINUTES = 0
MIN_TEMPERATURE_GAP = 0.5
OVERRIDE_MINUTES = 30

# borrowed from Mark Dickinson here:
# https://stackoverflow.com/questions/13071384/python-ceil-a-datetime-to-next-quarter-of-an-hour/32657466#comment53190737_32657466
def ceil_dt(dt, delta):
    return dt + (datetime.datetime.min - dt) % delta


class SmartCV(hass.Hass):

    def initialize(self):
        self.log("Smart CV initializing...")

        self.calendar = self.args['calendar']
        self.calendar_id = self.args['calendar_id']
        self.boiler = self.args['boiler']
        self.zones = self.args['zones']
        self.schedule = {}
        self.set_point_map = SetPointMap()

        # initialize schedule update
        self.update_schedule_cb(None)
        schedule_update_time = ceil_dt(self.get_now(), datetime.timedelta(minutes=10))
        self.log("Next first scheduled calendar update will be at {}".format(schedule_update_time))
        self.run_every(self.update_schedule_cb, schedule_update_time, 10 * 60)

        # schedule state updates
        self.run_minutely(self.update_states_cb, datetime.time(0, 0, 10))
        self.run_minutely(self.update_boiler_cb, datetime.time(0, 0, 40))

        # register manual override
        for (zone_name, control) in [(z, c) for z in self.zones for c in self.zones[z]]:
            self.listen_state(self.manual_override_cb, entity=control, attribute='temperature', zone=zone_name)

    def _get_controls(self, calendar_message):
        for zone in self.zones:
            if calendar_message.startswith(zone):
                return self.zones[zone]
        return None

    def _parse(self, calendar_message):
        controls = self._get_controls(calendar_message)

        set_point = None
        set_point_match = SET_POINT_PATTERN.match(calendar_message)
        if set_point_match:
            set_point = float(set_point_match.group(1))

        return controls, set_point

    def _get_calendar_events(self, start, end):
        config = self.AD.get_plugin(self.namespace).config
        if "cert_path" in config:
            cert_path = config["cert_path"]
        else:
            cert_path = False

        if "token" in config:
            headers = {'Authorization': "Bearer {}".format(config["token"])}
        elif "ha_key" in config:
            headers = {'x-ha-access': config["ha_key"]}
        else:
            headers = {}

        apiurl = "{}/api/calendars/{}".format(config["ha_url"], self.calendar)
        params = {"start": start.isoformat()+'Z', "end": end.isoformat()+'Z'}

        r = requests.get(apiurl, headers=headers, verify=cert_path, params=params)
        r.raise_for_status()
        return r.json()

    def parse_calendar_event(self, event):
        if 'id' not in event:
            self.log("Got calendar event without id: {}".format(event), level="WARNING")
            return None
        event_id = event['id']

        if 'summary' not in event:
            self.log("Get a calendar event without summary: {}".format(event), level="WARNING")
            return None
        calendar_message = event['summary']

        controls, set_point = self._parse(calendar_message)
        if controls is None:
            self.log("Could not determine controls from calendar message '{}'".format(calendar_message), level="WARNING")
            return None

        if set_point is None:
            self.log("Got calendar event for {} without set-point: {}".format(controls, event), level="WARNING")
            return None
        if set_point > 30 or set_point < 10:
            self.log("Unrealistic set point at {}".format(set_point), level="WARNING")
            return None

        if 'start' not in event or 'dateTime' not in event['start']:
            self.log("Got calendar event without start dateTime: {}".format(event), level="WARNING")
            return None
        event_start = datetime.datetime.fromisoformat(event["start"]["dateTime"])

        if 'end' not in event or 'dateTime' not in event['end']:
            self.log("Got calendar event without end dateTime: {}".format(event), level="WARNING")
            return None
        event_end = datetime.datetime.fromisoformat(event["end"]["dateTime"])

        if 'updated' not in event and 'created' not in event:
            self.log("Got calendar event without updated nor created timestamps {}".format(event), level="WARNING")
            return None
        updated = event["updated"] if 'updated' in event else event["created"]

        return CVEvent(event_id, updated, controls, set_point, event_start, event_end)

    @staticmethod
    def _get_ts(dt, offset=0):
        dt_offset = dt + datetime.timedelta(minutes=offset)
        return int(dt_offset.replace(second=0, microsecond=0).timestamp())

    def _get_lead_ts(self, control, a_time):
        return self._get_ts(a_time, HEAT_UP_LEAD_MINUTES)

    def _get_lag_ts(self, control, a_time):
        return self._get_ts(a_time, HEAT_UP_LAG_MINUTES)

    def _get_oldest_to_keep_ts(self):
        return self._get_ts(self.get_now(), HEAT_UP_LAG_MINUTES)

    def update_schedule_cb(self, kwargs):
        horizon = datetime.timedelta(hours=12)
        start = self.get_now() - horizon
        end = self.get_now() + horizon

        calendar_events = self._get_calendar_events(start, end)
        if calendar_events is None:
            self.log("Got no calendar events", level="WARNING")
            return

        events = {}
        for calendar_event in calendar_events:
            event = self.parse_calendar_event(calendar_event)
            if event is not None:
                events[event.event_id] = event

        self.log("Calendar events: {}".format(events), level="DEBUG")

        # remove events that are no longer on the calendar
        to_remove = [self.schedule[event_id] for event_id in self.schedule if event_id not in events]
        for to_remove_event in to_remove:
            self.log("Removing {}".format(to_remove_event))
            self.set_point_map.remove_cv_event(to_remove_event)
            self.schedule.pop(to_remove_event.event_id)

        # insert / update events from the calendar
        for event_id, event in events.items():
            if event_id in self.schedule:
                if event.updated != self.schedule[event_id].updated:
                    self.schedule[event_id].remove_from_set_point_map(self.set_point_map)
                else:
                    continue
            self.schedule[event_id] = event
            self.log("Adding {}".format(event))
            self.set_point_map.add_cv_event(event)

        self.log("Schedule: {}".format(self.schedule), level="DEBUG")
        self.log("Set Point Map: {}".format(self.set_point_map), level="DEBUG")

        # remove irrelevant minutes from set-point map
        self.set_point_map.clear_all_before(self._get_oldest_to_keep_ts())

    def _update_temperature(self, zone_name, control, set_point):
        if set_point is None:
            return

        current_set_point = self.get_state(control, attribute='temperature')
        if current_set_point is None:
            self.log("Could not obtain current set-point from control '{}'".format(control), level="WARNING")
            return

        if current_set_point != set_point:
            self.log("Setting '{}' from {} to {} in zone '{}'".format(
                control, current_set_point, set_point, zone_name), level="INFO")
            self.call_service('climate/set_temperature', entity_id=control, temperature=set_point)
        else:
            self.log("No need to chance control '{}' from set-point {}".format(control, set_point), level="DEBUG")

    def update_states_cb(self, kwargs):
        now = self.get_now()

        for (zone_name, control) in [(z, c) for z in self.zones for c in self.zones[z]]:
            current_state = self.get_state(control)
            if current_state is None:
                self.log("Could not obtain current state of control {}".format(control), level="WARNING")
                continue

            lead_ts = self._get_lead_ts(control, now)
            lead_set_point = self.set_point_map.get_set_point(lead_ts, control)
            self._update_temperature(zone_name, control, lead_set_point)

            lag_ts = self._get_lag_ts(control, now)
            lag_set_point = self.set_point_map.get_set_point(lag_ts, control)

            if current_state == 'off':
                if lead_set_point is not None and lag_set_point is not None:
                    self.log("Switching on {} in zone {}".format(control, zone_name), level="INFO")
                    self.call_service('climate/turn_on', entity_id=control)
                else:
                    self.log("Not switching on control '{}' for zone '{}'".format(control, zone_name), level="DEBUG")
            else:
                if lag_set_point is None and lead_set_point is None:
                    self.log("Switching off {} in zone {}".format(control, zone_name), level="INFO")
                    self.call_service('climate/turn_off', entity_id=control)
                else:
                    self.log("Not switching off control '{}' in zone '{}'".format(control, zone_name), level="DEBUG")

    def update_boiler_cb(self, kwargs):
        reasons_for_on = {}
        for (zone_name, control) in [(z, c) for z in self.zones for c in self.zones[z]
                                     if self.get_state(c) != 'off']:

            current_temperature = self.get_state(control, attribute="current_temperature")
            if current_temperature is None:
                self.log("Could not determine current temperature from control '{}'".format(control), level="WARNING")
                continue

            target_temperature = self.get_state(control, attribute="temperature")
            if target_temperature is None:
                self.log("Could not determine target temperature for control '{}'".format(control), level="WARNING")
                continue

            if current_temperature + MIN_TEMPERATURE_GAP < target_temperature:
                reasons_for_on[zone_name] = [
                    *reasons_for_on.get(zone_name, []),
                    {control: "{}<{}".format(current_temperature, target_temperature)}
                ]

        current_state = self.get_state(self.boiler)
        if current_state is None:
            self.log("Could not determine current state of boiler '{}'".format(self.boiler), level="WARNING")
            return

        if len(reasons_for_on) > 0:
            if current_state != 'on':
                self.log("Setting boiler state to on, reasons: {}".format(reasons_for_on), level="INFO")
                self.turn_on(self.boiler)
            else:
                self.log("Boiler state already 'on'")
        else:
            if current_state != 'off':
                self.log("Setting target boiler state to off", level="INFO")
                self.turn_off(self.boiler)
            else:
                self.log("Boiler state already 'off'")

    def manual_override_cb(self, entity, attribute, old, new, kwargs):
        zone = kwargs.get('zone', '_unknown-zone_')
        self.log("Got state update of {} in zone {} from {} to {}".format(entity, zone, old, new))
        if old == new:
            self.log("Got identical temperature settings of {} for {}".format(new, entity))
            return

        now = self.get_now()
        lead_ts = self._get_lead_ts(entity, now)
        set_point = self.set_point_map.get_set_point(lead_ts, entity)
        if set_point != new:
            self.log("Now we set an override of {} for {} in {}".format(new, entity, zone))
            controls = self.zones[zone]
            self.set_point_map.add_override(now, now+datetime.timedelta(minutes=OVERRIDE_MINUTES), controls, new)
            self.log("Override from {} to {}".format(now, now+datetime.timedelta(minutes=OVERRIDE_MINUTES)))