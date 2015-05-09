# minqlbot - A Quake Live server administrator bot.
# Copyright (C) WalkerY

# This file is part of minqlbot.

# minqlbot is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# minqlbot is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with minqlbot. If not, see <http://www.gnu.org/licenses/>.

"""Spectates one random player and sets teamsize if teams are even."""

import minqlbot
import random

class specone(minqlbot.Plugin):
    def __init__(self):
        super().__init__()
        self.add_command(("onespec", "specone", "gospec"), self.cmd_onespec, 1)
            
    def cmd_onespec(self, player, msg, channel):
        allteams = self.teams()
        teams = allteams["red"] + allteams["blue"]
        
        try:
            chosen = random.choice(teams)
        except IndexError:
            channel.reply("^7There are no players in teams to spec one.")
            return        
        self.put(chosen.clean_name, "spectator")
        
        allteams = self.teams()
        if (len(allteams["red"]) == len(allteams["blue"]) and (len(allteams["red"]) > 1)):
            new_ts = len(allteams["red"])
            self.teamsize(new_ts)
            channel.reply("^7Teamsize was set to ^6{}^7.".format(new_ts))
            
        channel.reply("^7Player ^6{}^7 was chosen to spec.".format(chosen.name))
        