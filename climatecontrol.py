import re
import appdaemon.plugins.hass.hassapi as hass


class SmartCV(hass.Hass):


	def initialize(self):
		self.setpoint_pattern = re.compile('.*([\\d]+|[\\d]+\\.[\\d]*)')
		self.calendar = self.args['calendar']
		self.boiler = self.args['boiler']
		self.zones = self.args['zones']

		self.listen_state(self.calendar_set_cb, self.calendar, new = 'on')
		self.listen_state(self.calendar_unset_cb, self.calendar, new = 'off')

		self.turn_off(self.boiler)
		for zone in self.zones:
			for control in zone['controls']:
				self.turn_off(control)
				self.listen_state(self.update_boiler_cb, control)


	def _initialize_state(self):
		


	def _get_controls(self, calendar_message):
		for zone in self.zones:
			if calendar_message.starts_with(zone['name']):
				return zone['controls']
		return None


	def _parse(self, calendar_message):
		controls = self._get_controls(calendar_message)
		
		setpoint = None
		setpoint_match = self.setpoint_pattern.match(calendar_message)
		if setpoint_match:
			setpoint = float(setpoint_match.group[1])

		return (controls, setpoint)


	def calendar_set_cb(self, entity, attribute, old, new, kwargs):
		setpoint, controls = self._parse(kwargs['message'])
		if setpoint is None or controls is None:
			return
		self.call_service('climate/set_temperature', entity_id = controls, temperature = setpoint)
		self.call_service('climate/turn_on', entity_id = controls)


	def calendar_unset_cb(self, entity, attribute, old, new, kwargs):
		controls = self._get_controls(kwargs['message'])
		if controls is None:
			return

		self.call_service('climate/turn_off', entity_id = controls)


	def _get_required_boiler_state(self):
		for zone in self.zones:
			for control in zone['controls']:
				if self.entities[control].state != 'off' and self.entities[control].attributes.current_temperature < self.entities[control].attributes.temperature:
					return 'on'
		return 'off'


	def update_boiler_cb(self, entity, attribute, old, new, kwargs):
		if self.entities[self.boiler].state != self._get_required_boiler_state():
			self.toggle(self.boiler)