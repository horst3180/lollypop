#!/usr/bin/python
# Copyright (c) 2014 Cedric Bellegarde <gnumdk@gmail.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
# Many code inspiration from gnome-music at the GNOME project

class DatabaseUpgrade:

	"""
		Init object
	"""
	def __init__(self, sql, version):
		self._sql = sql
		self._version = version
		self._reset = False
		# Here are schema upgrade, key is database version, value function doing shema update
		self._UPGRADES = { 
							1: self._db_add_modification_time,
							2: self._db_add_performer_disc
						 }

	"""
		Return upgrade count
		ret: int
	"""
	def count(self):
		return len(self._UPGRADES)

	"""
		True if db need a reset
		ret: bool
	"""
	def reset_needed(self):
		return self._reset

	"""
		Upgrade database based on version
		ret: new db version as int
	"""	
	def do_db_upgrade(self):
		for i in range(self._version.get_int32()+1, len(self._UPGRADES)+1):
			try:
				self._UPGRADES[i]()
			except Exception as e:
				print("Database upgrade failed: ", e)
		return len(self._UPGRADES)

	"""
		Add modification time to track table
	"""
	def _db_add_modification_time(self):
 		self._sql.execute("ALTER TABLE tracks ADD COLUMN mtime INT")

	"""
		Add performer time to track table and disc number
	"""
	def _db_add_performer_disc(self):
		self._sql.execute("ALTER TABLE tracks ADD COLUMN performer_id INT")
		self._sql.execute("ALTER TABLE tracks ADD COLUMN discnumber INT")
		# reset mtime to rescan tags
		self._reset = True
