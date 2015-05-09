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

"""Performs actions when server is empty."""

import minqlbot
import random

class emptyactions(minqlbot.Plugin):
    def __init__(self):
        super().__init__()
        self.add_hook("player_disconnect", self.handle_player_disconnect)

    def handle_player_disconnect(self, player, reason):
        teams = self.teams()
        count = len(teams["red"]) + len(teams["blue"]) + len(teams["spectator"])
        
        if (count < 2):
            config = minqlbot.get_config()
            new_ts = 0
            if "EmptyActions" in config and "TSOnEmpty" in config["EmptyActions"]:
                new_ts = int(config["EmptyActions"]["TSOnEmpty"])
            if (new_ts > 0 and new_ts <= 8):
                self.teamsize(new_ts)
                self.delay(5, self.change_map)
            else:
                self.change_map()
        
    def change_map(self):
        config = minqlbot.get_config()
        new_map = ""
        if "EmptyActions" in config and "MapOnEmpty" in config["EmptyActions"]:
            try:
                new_map = random.choice([s.strip() for s in config["EmptyActions"]["MapOnEmpty"].split(",")])
            except IndexError:
                return

        if new_map != "":
            self.changemap(new_map)
        