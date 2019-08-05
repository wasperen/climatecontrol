import re
import datetime
import requests
import appdaemon.plugins.hass.hassapi as hass

DEFAULT_BOILER_TARGET_ENTITY = 'binary_sensor.boiler_target'
SET_POINT_PATTERN = re.compile('[^\\d]*([\\d]+|[\\d]+\\.[\\d]*)')


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

	def _loop_through_set_point_map(self, set_point_map, f):
		minute = self.event_start
		step = datetime.timedelta(minutes=1)
		while minute < self.event_end:
			minute_ts = int(minute.replace(second=0, microsecond=0).timestamp())
			set_points = set_point_map.get(minute_ts, {})
			for control in self.controls:
				set_points[control] = f(set_points.get(control, []))
			set_point_map[minute_ts] = set_points
			minute += step

	def add_to_set_point_map(self, set_point_map):
		self._loop_through_set_point_map(set_point_map, lambda l: [*l, self.set_point])

	def remove_from_set_point_map(self, set_point_map):
		def filter_first_occurrence(l, v):
			try:
				l.remove(v)
			except ValueError:
				pass
			return l

		self._loop_through_set_point_map(set_point_map, lambda l: filter_first_occurrence(l, self.set_point))


class SmartCV(hass.Hass):

	def initialize(self):
		self.log("Smart CV initializing...")

		self.calendar = self.args['calendar']
		self.boiler = self.args['boiler']
		self.boiler_target = self.args.get('boiler_target', DEFAULT_BOILER_TARGET_ENTITY)
		self.zones = self.args['zones']
		self.schedule = {}
		self.set_point_map = {}

		# listen to all controls to update boiler target state
		for control in [c for z in self.zones for c in z['controls']]:
			self.listen_event(self.update_boiler_target_cb, control, attribute='all')

		time_zero = datetime.time(0, 0, 0)
		self.run_every(self.update_schedule_cb, self.get_now(), 10 * 60)
		self.run_minutely(self.update_states_cb, time_zero)
		self.run_minutely(self.update_boiler_cb, time_zero)

	def _get_controls(self, calendar_message):
		for zone in self.zones:
			if calendar_message.startswith(zone['name']):
				return zone['controls']
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

		r = requests.get(
			apiurl, headers=headers, verify=cert_path, params=params
		)
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
			to_remove_event.remove_from_set_point_map(self.set_point_map)
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
			event.add_to_set_point_map(self.set_point_map)

		self.log("Schedule: {}".format(self.schedule), level="DEBUG")
		self.log("Set Point Map: {}".format(self.set_point_map), level="DEBUG")

		# remove irrelevant minutes from set-point map
		now_ts = int(self.get_now().replace(second=0, microsecond=0).timestamp())
		to_remove = [minute_ts for minute_ts in self.set_point_map if minute_ts < now_ts]
		for minute_ts in to_remove:
			self.set_point_map.pop(minute_ts)

	def update_states_cb(self, kwargs):
		current_ts = int(self.get_now().replace(second=0, microsecond=0).timestamp())
		if current_ts not in self.set_point_map:
			self.log("No set-points for timestamp {}".format(current_ts))

		set_points = self.set_point_map.get(current_ts, {})
		for (zone_name, control) in [(z["name"], c) for z in self.zones for c in z['controls']]:
			current_state = self.get_state(control)
			if current_state is None:
				self.log("Could not obtain current state of control {}".format(control), level="WARNING")
				continue

			if control in set_points and len(set_points[control]) > 0:
				current_set_point = self.get_state(control, attribute='temperature')
				if current_set_point is None:
					self.log("Could not obtain current set-point from control {}".format(control), level="WARNING")
					continue

				set_point = max(set_points[control])
				if current_set_point != set_point:
					self.log("Setting {} from {} to {} in zone {}".format(
						control, current_set_point, set_point, zone_name), level="INFO")
					self.call_service('climate/set_temperature', entity_id=control, temperature=set_point)
				else:
					self.log("No need to chance control {} form set-point {}".format(control, set_point))

				if current_state == 'off':
					self.log("Switching on {} in zone {}".format(control, zone_name), level="INFO")
					self.call_service('climate/turn_on', entity_id=control)
				else:
					self.log("Control {} already on".format(control))
			else:
				if current_state != 'off':
					self.log("Switching off {} in zone {}".format(control, zone_name), level="INFO")
					self.call_service('climate/turn_off', entity_id=control)
				else:
					self.log("Control {} already off".format(control))

	def update_boiler_target_cb(self, entity, attribute, old, new, kwargs):
		self.log("Got a state change from {}, updating target boiler state now".format(entity), level="INFO")
		reasons = {}
		for (zone_name, control) in [(z["name"], c) for z in self.zones for c in z['controls']]:
			if self.get_state(control) == 'off':
				continue

			current_temperature = self.get_state(control, attribute="current_temperature")
			if current_temperature is None:
				self.log("Could not determine current temperature from {}".format(control), level="WARNING")
				continue

			target_temperature = self.get_state(control, attribute="temperature")
			if target_temperature is None:
				self.log("Could not determine target temperature for {}".format(control), level="WARNING")
				continue

			if current_temperature < target_temperature:
				reasons[zone_name] = reasons.get(zone_name, []).append(
					{control: "{}<{}".format(current_temperature, target_temperature)}
				)

		if len(reasons) > 0:
			self.log("Setting target boiler state to on, reasons: {}".format(reasons), level="INFO")
			self.set_state(self.boiler_target, state='on', attributes=dict(trigger=entity, reasons=reasons))
		else:
			self.log("Setting target boiler state to off", level="INFO")
			self.set_state(self.boiler_target, state='off', attributes=dict(trigger=entity))

	def update_boiler_cb(self, kwargs):
		current_state = self.get_state(self.boiler)
		if current_state is None:
			self.log("Could not determine current state of boiler with entity id {}".format(self.boiler), level="WARNING")
			return

		target_state = self.get_state(self.boiler_target)
		if target_state is None:
			self.log("Could not determine target state of boiler with entity id {}".format(self.boiler_target), level="WARNING")
			return

		if current_state != target_state:
			self.log("Switching boiler from {} to {}".format(current_state, target_state))
			self.toggle(self.boiler)
		else:
			self.log("No need to change the boiler state", level="DEBUG")
