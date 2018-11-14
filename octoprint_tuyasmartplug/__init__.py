# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
from octoprint.server import user_permission
import socket
import json
import logging
import os
import re
import threading
import time
import pytuya


class tuyasmartplugPlugin(octoprint.plugin.SettingsPlugin,
			octoprint.plugin.AssetPlugin,
			octoprint.plugin.TemplatePlugin,
			octoprint.plugin.SimpleApiPlugin,
			octoprint.plugin.StartupPlugin):

	def __init__(self):
		self._logger = logging.getLogger("octoprint.plugins.tuyasmartplug")
		self._tuyasmartplug_logger = logging.getLogger("octoprint.plugins.tuyasmartplug.debug")

	# ~~ StartupPlugin mixin

	def on_startup(self, host, port):
		# setup customized logger
		from octoprint.logging.handlers import CleaningTimedRotatingFileHandler
		tuyasmartplug_logging_handler = CleaningTimedRotatingFileHandler(self._settings.get_plugin_logfile_path(postfix="debug"), when="D", backupCount=3)
		tuyasmartplug_logging_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))
		tuyasmartplug_logging_handler.setLevel(logging.DEBUG)

		self._tuyasmartplug_logger.addHandler(tuyasmartplug_logging_handler)
		self._tuyasmartplug_logger.setLevel(logging.DEBUG if self._settings.get_boolean(["debug_logging"]) else logging.INFO)
		self._tuyasmartplug_logger.propagate = False

	def on_after_startup(self):
		self._logger.info("TuyaSmartplug loaded!")

	# ~~ SettingsPlugin mixin

	def get_settings_defaults(self):
		return dict(
			debug_logging=False,
			arrSmartplugs=[
				{
					'ip': '',
					'id': '',
					'slot': 1,
					'localKey': '',
					'label': '',
					'icon': 'icon-bolt',
					'displayWarning': True,
					'warnPrinting': False,
					'gcodeEnabled': False,
					'gcodeOnDelay': 0,
					'gcodeOffDelay': 0,
					'autoConnect': True,
					'autoConnectDelay': 10.0,
					'autoDisconnect': True,
					'autoDisconnectDelay': 0,
					'sysCmdOn': False,
					'sysRunCmdOn': '',
					'sysCmdOnDelay': 0,
					'sysCmdOff': False,
					'sysRunCmdOff': '',
					'sysCmdOffDelay': 0,
					'currentState': 'unknown',
					'btnColor': '#808080',
					'useCountdownRules': False,
					'countdownOnDelay': 0,
					'countdownOffDelay': 0
				}
			],
			pollingInterval=15,
			pollingEnabled=False
		)

	def get_settings_restricted_paths(self):
		return dict(admin=[["arrSmartplugs", ], ])

	def on_settings_save(self, data):
		old_debug_logging = self._settings.get_boolean(["debug_logging"])

		octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

		new_debug_logging = self._settings.get_boolean(["debug_logging"])
		if old_debug_logging != new_debug_logging:
			if new_debug_logging:
				self._tuyasmartplug_logger.setLevel(logging.DEBUG)
			else:
				self._tuyasmartplug_logger.setLevel(logging.INFO)

	def get_settings_version(self):
		return 2

	def on_settings_migrate(self, target, current=None):
		if current is None or current < self.get_settings_version():
			# Reset plug settings to defaults.
			self._logger.debug("Resetting arrSmartplugs for tuyasmartplug settings.")
			self._settings.set(['arrSmartplugs'], self.get_settings_defaults()["arrSmartplugs"])

	# ~~ AssetPlugin mixin

	def get_assets(self):
		return dict(
			js=["js/tuyasmartplug.js"],
			css=["css/tuyasmartplug.css"]
		)

	# ~~ TemplatePlugin mixin

	def get_template_configs(self):
		return [
			dict(type="navbar", custom_bindings=True),
			dict(type="settings", custom_bindings=True)
		]

	# ~~ SimpleApiPlugin mixin

	def turn_on(self, plugip):
		self._tuyasmartplug_logger.debug("Turning on %s." % plugip)
		if self.is_turned_on(plugip=plugip):
			self._tuyasmartplug_logger.debug("Plug %s already turned on" % plugip)
			self._plugin_manager.send_plugin_message(self._identifier, dict(currentState="on", ip=plugip))
			return
		plug = self.plug_search(self._settings.get(["arrSmartplugs"]), "ip", plugip)
		self._tuyasmartplug_logger.debug(plug)
		if plug["useCountdownRules"]:
			chk = self.sendCommand('countdown', plug['ip'], plug['countdownOnDelay'])
		else:
			chk = self.sendCommand('on', plug['ip'])

		if chk is not False:
			self.check_status(plug['ip'], chk)
			if plug["autoConnect"]:
				c = threading.Timer(int(plug["autoConnectDelay"]), self._printer.connect)
				c.start()
			if plug["sysCmdOn"]:
				t = threading.Timer(int(plug["sysCmdOnDelay"]), os.system, args=[plug["sysRunCmdOn"]])
				t.start()
		else:
			self._plugin_manager.send_plugin_message(self._identifier, dict(currentState="unknown", ip=plugip))

	def turn_off(self, plugip):
		self._tuyasmartplug_logger.debug("Turning off %s." % plugip)
		if not self.is_turned_on(plugip=plugip):
			self._tuyasmartplug_logger.debug("Plug %s already turned off" % plugip)
			self._plugin_manager.send_plugin_message(self._identifier, dict(currentState="off", ip=plugip))
			return
		plug = self.plug_search(self._settings.get(["arrSmartplugs"]), "ip", plugip)
		self._tuyasmartplug_logger.debug(plug)
		if plug["useCountdownRules"]:
			chk = self.sendCommand('countdown', plug['ip'], plug['countdownOffDelay'])

		if plug["sysCmdOff"]:
			t = threading.Timer(int(plug["sysCmdOffDelay"]), os.system, args=[plug["sysRunCmdOff"]])
			t.start()
		if plug["autoDisconnect"]:
			self._printer.disconnect()
			time.sleep(int(plug["autoDisconnectDelay"]))

		if not plug["useCountdownRules"]:
			chk = self.sendCommand('off', plug['ip'])

		if chk is not False:
			self.check_status(plug['ip'], chk)
		else:
			self._plugin_manager.send_plugin_message(self._identifier, dict(currentState="unknown", ip=plugip))

	def check_status(self, plugip, resp=None):
		self._tuyasmartplug_logger.debug("Checking status of %s." % plugip)
		if plugip != "":
			response = resp or self.sendCommand('info', plugip)
			if response is False:
				self._plugin_manager.send_plugin_message(self._identifier, dict(currentState="unknown", ip=plugip))
			else:
				self._plugin_manager.send_plugin_message(self._identifier, dict(currentState=("on" if self.is_turned_on(response) else "off"), ip=plugip))

	def is_turned_on(self, data=None, plugip=None):
		if data is None and plugip:
			data = self.sendCommand('info', plugip)

		plug = self.plug_search(self._settings.get(["arrSmartplugs"]), "ip", plugip)
		return data and data.get('dps', {}).get(plug['slot'])

	def get_api_commands(self):
		return dict(turnOn=["ip"], turnOff=["ip"], checkStatus=["ip"])

	def on_api_command(self, command, data):
		if not user_permission.can():
			from flask import make_response
			return make_response("Insufficient rights", 403)

		if command == 'turnOn':
			self.turn_on("{ip}".format(**data))
		elif command == 'turnOff':
			self.turn_off("{ip}".format(**data))
		elif command == 'checkStatus':
			self.check_status("{ip}".format(**data))

	# ~~ Utilities

	def plug_search(self, list, key, value):
		for item in list:
			if item[key] == value:
				return item

	def sendCommand(self, cmd, plugip, args=None, tries=1):
		self._tuyasmartplug_logger.debug('Sending command: %s to %s' % (cmd, plugip))
		plug = self.plug_search(self._settings.get(["arrSmartplugs"]), "ip", plugip)
		device = pytuya.OutletDevice(plug['id'], plug['ip'], plug['localKey'])

		commands = {
			'info': ('status', None),
			'on': ('set_status', (True, plug['slot'])),
			'off': ('set_status', (False, plug['slot'])),
			'countdown': ('set_timer', None),
		}

		try:
			command, arg = commands[cmd]
			func = getattr(device, command, None)
			if not func:
				self._tuyasmartplug_logger.debug("No such command '%s'" % command)
				return False
			if args:
				func(args)
			elif arg is not None:
				if isinstance(arg, list):
					func(*arg)
				else:
					func(arg)
			else:
				func()
			time.sleep(0.5)
			ret = device.status()
			self._tuyasmartplug_logger.debug('Status: %s' % str(ret))
			return ret
		except socket.error as e:
			if e.errno == 104:
				if tries <= 3:
					self._tuyasmartplug_logger.debug("Connection refused... Trying again soon")
					time.sleep(1)
					return self.sendCommand(cmd, plugip, args, tries + 1)
				self._tuyasmartplug_logger.debug("Too many failed attempts")
				return False
			self._tuyasmartplug_logger.debug("Network error")
			return False
		except:
			self._tuyasmartplug_logger.debug('Something went wrong while running the command')
			return False

	# ~~ Gcode processing hook

	def gcode_turn_off(self, plug):
		if plug["warnPrinting"] and self._printer.is_printing():
			self._logger.info("Not powering off %s because printer is printing." % plug["label"])
		else:
			self.turn_off(plug["ip"])

	def processGCODE(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
		if gcode:
			if cmd.startswith("M80"):
				plugip = re.sub(r'^M80\s?', '', cmd)
				self._tuyasmartplug_logger.debug("Received M80 command, attempting power on of %s." % plugip)
				plug = self.plug_search(self._settings.get(["arrSmartplugs"]), "ip", plugip)
				self._tuyasmartplug_logger.debug(plug)
				if plug["gcodeEnabled"]:
					t = threading.Timer(int(plug["gcodeOnDelay"]), self.turn_on, args=[plugip])
					t.start()
				return
			elif cmd.startswith("M81"):
				plugip = re.sub(r'^M81\s?', '', cmd)
				self._tuyasmartplug_logger.debug("Received M81 command, attempting power off of %s." % plugip)
				plug = self.plug_search(self._settings.get(["arrSmartplugs"]), "ip", plugip)
				self._tuyasmartplug_logger.debug(plug)
				if plug["gcodeEnabled"]:
					t = threading.Timer(int(plug["gcodeOffDelay"]), self.gcode_turn_off, [plug])
					t.start()
				return
			else:
				return

		elif cmd.startswith("@TUYAON"):
			plugip = re.sub(r'^@TUYAON\s?', '', cmd)
			self._tuyasmartplug_logger.debug("Received @TUYAON command, attempting power on of %s." % plugip)
			plug = self.plug_search(self._settings.get(["arrSmartplugs"]), "ip", plugip)
			self._tuyasmartplug_logger.debug(plug)
			if plug["gcodeEnabled"]:
				t = threading.Timer(int(plug["gcodeOnDelay"]), self.turn_on, args=[plugip])
				t.start()
			return None
		elif cmd.startswith("@TUYAOFF"):
			plugip = re.sub(r'^@TUYAOFF\s?', '', cmd)
			self._tuyasmartplug_logger.debug("Received TUYAOFF command, attempting power off of %s." % plugip)
			plug = self.plug_search(self._settings.get(["arrSmartplugs"]), "ip", plugip)
			self._tuyasmartplug_logger.debug(plug)
			if plug["gcodeEnabled"]:
				t = threading.Timer(int(plug["gcodeOffDelay"]), self.gcode_turn_off, [plug])
				t.start()
			return None

	# ~~ Softwareupdate hook

	def get_update_information(self):
		# Define the configuration for your plugin to use with the Software Update
		# Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
		# for details.
		return dict(
			tuyasmartplug=dict(
				displayName="Tuya Smartplug",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="ziirish",
				repo="OctoPrint-TuyaSmartplug",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/ziirish/OctoPrint-TuyaSmartplug/archive/{target_version}.zip"
			)
		)


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Tuya Smartplug"


def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = tuyasmartplugPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.comm.protocol.gcode.queuing": __plugin_implementation__.processGCODE,
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}

