import re
import appdaemon.plugins.hass.hassapi as hass


class SmartCV(hass.Hass):

	def initialize(self):
		self.log("Smart CV initializing...")

		self.set_point_pattern = re.compile('[^\\d]*([\\d]+|[\\d]+\\.[\\d]*)')
		self.calendar = self.args['calendar']
		self.boiler = self.args['boiler']
		self.zones = self.args['zones']

		self.listen_state(self.calendar_cb, self.calendar, attribute="all")

		self._initialize_state()

	def _initialize_state(self):
		# TODO we should obtain the current state from the calendar using the hass api
		# for now we just put everything off
		self.turn_off(self.boiler)
		for zone in self.zones:
			for control in zone['controls']:
				self.turn_off(control)
				self.listen_state(self.update_boiler_cb, control)

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
		if "attributes" not in new_state or "message" not in new_state["attributes"]:
			self.log("Got a calendar state change with no message attribute: {}".format(new_state), level="WARNING")
			return

		message = new_state["attributes"]["message"]
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

		if new_state["state"] == 'on':
			self.log("Setting {} to {}".format(controls, set_point), level="INFO")
			self.call_service('climate/set_temperature', entity_id=controls, temperature=set_point)
			self.call_service('climate/turn_on', entity_id=controls)
		else:
			self.log("Switching off {}".format(controls), level="INFO")
			self.call_service('climate/turn_off', entity_id=controls)

	def _get_required_boiler_state(self):
		for zone in self.zones:
			for control in zone['controls']:
				if self.get_state(control) != 'off':
					current_temperature = self.get_state(control, attribute="current_temperature")
					target_temperature = self.get_state(control, attribute="temperature")
					if current_temperature is not None and target_temperature is not None:
						if current_temperature < target_temperature:
							return 'on'
		return 'off'

	def update_boiler_cb(self, entity, attribute, old, new, kwargs):
		self.log("Got a state change from {}, checking the boiler state now".format(entity), level="INFO")

		required_state = self._get_required_boiler_state()
		current_state = self.get_state(self.boiler)
		if current_state is None:
			self.log("Could not determine current state of boiler with entity id {}".format(self.boiler), level="WARNING")
			return

		if current_state != required_state:
			self.log("Switching boiler from {} to {}".format(current_state, required_state))
			self.toggle(self.boiler)
		else:
			self.log("No need to change the boiler state")
