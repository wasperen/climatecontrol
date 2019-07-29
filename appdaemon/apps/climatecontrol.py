import re
import datetime
from iso8601 import parse_date, ParseError
import appdaemon.plugins.hass.hassapi as hass

DEFAULT_BOILER_TARGET_ENTITY = 'binary_sensor.boiler_target'


class SmartCV(hass.Hass):

	def initialize(self):
		self.log("Smart CV initializing...")

		self.set_point_pattern = re.compile('[^\\d]*([\\d]+|[\\d]+\\.[\\d]*)')
		self.calendar = self.args['calendar']
		self.boiler = self.args['boiler']
		self.boiler_target = self.args.get('boiler_target', DEFAULT_BOILER_TARGET_ENTITY)
		self.zones = self.args['zones']

		self._initialize_state()

		self.listen_state(self.calendar_cb, self.calendar, attribute="all", new='on')
		self.run_minutely(self.update_boiler_cb, datetime.time(0, 0, 0))

	def _initialize_state(self):
		# TODO we should obtain the current state from the calendar using the hass api; for now switch everything off
		self.turn_off(self.boiler)
		self.set_state(self.boiler_target, state="off", attributes=dict(trigger="initialize"))

		for control in set([c for z in self.zones for c in z['controls']]):
			self.turn_off(control)
			self.listen_state(self.update_boiler_target_cb, control)

	def _get_controls(self, calendar_message):
		for zone in self.zones:
			if calendar_message.startswith(zone['name']):
				return zone['controls']
		return None

	def _parse(self, calendar_message):
		controls = self._get_controls(calendar_message)

		set_point = None
		set_point_match = self.set_point_pattern.match(calendar_message)
		if set_point_match:
			set_point = float(set_point_match.group(1))

		return controls, set_point

	def calendar_cb(self, entity, attribute, old_state, new_state, kwargs):
		if new_state["state"] != 'on':
			self.log("Received calendar event with new state {}".format(new_state["state"]), level="DEBUG")
			return

		if "attributes" not in new_state:
			self.log("Got calendar state change with no attributes: {}".format(new_state), level="WARNING")
			return

		attributes = new_state["attributes"]

		if "message" not in attributes:
			self.log("Got a calendar state change with no message attribute: {}".format(new_state), level="WARNING")
			return

		message = attributes["message"]
		if message is None or message == "":
			self.log("Got a calendar state change with an empty message", level="WARNING")
			return

		self.log("Got a calendar state change with message '{}'".format(message), level="DEBUG")

		controls, set_point = self._parse(message)
		if set_point is None or controls is None:
			self.log("Could not determine controls or set_point from message '{}'".format(message), level="WARNING")
			return

		if set_point > 30 or set_point < 10:
			self.log("Unrealistic set point at {}".format(set_point), level="WARNING")
			return

		if "end_time" not in attributes:
			self.log("Calendar event attributes do not contain end_time: {}".format(new_state), level="WARNING")
			return

		try:
			switch_off_time = parse_date(attributes["end_time"]) - datetime.timedelta(minutes=-1)
		except ParseError as error:
			self.log("Failure parsing datetime from calendar event end_time: {}".format(attributes["end_time"]), level="WARNING")
			self.log("Parse Error: {}".format(error), level="WARNING")
			return

		self.log("Setting {} to {} and plan to switch off at {}".format(controls, set_point, switch_off_time), level="INFO")
		self.call_service('climate/set_temperature', entity_id=controls, temperature=set_point)
		self.call_service('climate/turn_on', entity_id=controls)

		self.run_at(self.timed_off_cb(), switch_off_time)

	def timed_off_cb(self, controls):
		self.log("Switching off {}".format(controls), level="INFO")
		self.call_service('climate/turn_off', entity_id=controls)

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
				reasons[zone_name] = reasons.get(zone_name, default=[]).append(
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
