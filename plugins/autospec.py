# Copyright (C) 2015 WalkerY (on github)

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

"""Plugin moves players to spectator at the start of each round if
teams are uneven. Last connect - first to spec order.  

Players that connected before loading plugin won't be speced.

"""

import minqlbot
import collections

__version__ = '0.9.0'

# List of excluded from specing.
EXCLUDE_LIST = ["walkerx", "walkerz", "walkery"]
         
         
class autospec(minqlbot.Plugin):
    def __init__(self):
        super().__init__()
        self.add_hook("player_disconnect", self.handle_player_disconnect)
        self.add_hook("player_connect", self.handle_player_connect)
        self.add_hook("round_start", self.handle_round_start)
        # We don't hook bot_connect as we don't manage players
        # for whom we don't know when they connected.
        
        self.connects = collections.OrderedDict()
        
    def handle_player_disconnect(self, player, reason):
        name = player.clean_name.lower()
        if name in self.connects:
            del self.connects[name]

    def handle_player_connect(self, player):
        name = player.clean_name.lower()
        if name in EXCLUDE_LIST:
            return
        self.connects[name] = player

    def handle_round_start(self, round_):    
        teams = self.teams()        
        count = {"red": len(teams["red"]), "blue":len(teams["blue"])}        
        another_team = {"red": "blue", "blue": "red"}
        players = []
        counter = {"red": 0, "blue": 0}

        for team in another_team:
                for player_name in reversed(self.connects):
                    if (count[team] - counter[team] > count[another_team[team]] and 
                        count[team] - counter[team] >= 2):
                        if self.connects[player_name].team == team:
                            players.append(self.connects[player_name])
                            counter[team] += 1
                    else:
                        break
        
        for player in players:
            self.put(player, "spectator")
            self.msg("^7Player {}^7 was moved to spectators to even teams."
                     .format(player.name))
            self.msg("^7The last ^6to connect^7 to server is chosen to spectate.")
