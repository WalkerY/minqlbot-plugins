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

Config sample:
# [AutoSpec]
# ExcludeList = WalkerX, WalkerY, WalkerZ

"""

import minqlbot
import collections

class autospec(minqlbot.Plugin):
    def __init__(self):
        super().__init__()
        
        self.__version__ = '1.0.0'        
        
        self.add_hook("player_disconnect", self.handle_player_disconnect)
        self.add_hook("player_connect", self.handle_player_connect)
        self.add_hook("round_start", self.handle_round_start)
        # We don't hook bot_connect as we don't manage players
        # for whom we don't know when they connected.
            
        self.connects = collections.OrderedDict()
        
        config = minqlbot.get_config()
        if "AutoSpec" in config and "ExcludeList" in config["AutoSpec"]:
            list = config["AutoSpec"]["ExcludeList"]
            self.exclude_list = [s.strip().lower() for s in list.split(",")]
        else:
            self.exclude_list = []
        
    def handle_player_disconnect(self, player, reason):
        name = player.clean_name.lower()
        if name in self.connects:
            del self.connects[name]

    def handle_player_connect(self, player):
        name = player.clean_name.lower()
        if name in self.exclude_list:
            return
        self.connects[name] = player

    def handle_round_start(self, round_):    
        teams = self.teams()        
        count = {"red": len(teams["red"]), "blue":len(teams["blue"])}        
        another_team = {"red": "blue", "blue": "red"}
        players = []

        for team in another_team:
                counter = 0
                for player_name in reversed(self.connects):
                    if (count[team] - counter > count[another_team[team]] and 
                        count[team] - counter >= 2):
                        if self.connects[player_name].team == team:
                            players.append(self.connects[player_name])
                            counter += 1
                    else:
                        break
        
        for player in players:
            self.put(player, "spectator")
            self.msg("^7Player {}^7 was moved to spectators to even teams."
                     .format(player.name))
        self.msg("^7The last ^6to connect^7 to server is chosen to spectate.")
