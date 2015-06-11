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

"""Balances teams automatically.

Config sample:
[AutoBalance]

# Auto-balance or round countdown unless one of the teams
# reaches this score. Set to 0 to disable, 3 is default.
AutoBalancedMaxScore = 0

# Auto-balance on game countdown.
AutoBalanceOnGameCountDown = True

DisplayBalanceOnTeamsChange = True

"""

import minqlbot

class autobalance(minqlbot.Plugin):
    CONFIG_SECTION_NAME = "AutoBalance"
    
    config_defaults = {"AutoBalancedMaxScore": 3,
                       "AutoBalanceOnGameCountDown": True,
                       "DisplayBalanceOnTeamsChange": True}
    config = None

    def __init__(self):
        super().__init__()
        
        self.__version__ = '1.3.1'
        
        self.add_hook("player_connect", self.handle_player_connect)
        self.add_hook("game_countdown", self.handle_game_countdown)
        self.add_hook("round_countdown", self.handle_round_countdown)
        self.add_hook("team_switch", self.handle_team_switch)
        self.add_command("version", self.cmd_version, 0)

        self.teams_changed = True
        
        self.get_config()
        
    def handle_player_connect(self, player):
        name = player.clean_name.lower()
        if "balance" not in self.plugins:
            return
        channel = minqlbot.CHAT_CHANNEL
        balance = self.plugins["balance"]
        not_cached = balance.not_cached(self.game().short_type, [player])
        if not_cached:
            with balance.rlock:
                for lookup in balance.lookups:
                    for n in balance.lookups[lookup][1]:
                        if n in not_cached:
                            not_cached.remove(n)
                if not_cached:
                    balance.fetch_player_ratings(not_cached, channel, self.game().short_type)        

    def handle_team_switch(self, player, old_team, new_team):
        self.teams_changed = True        
        
    def handle_game_countdown(self):
        #auto-balance
        if ("balance" in self.plugins and 
             self.config["AutoBalanceOnGameCountDown"]):
            self.plugins["balance"].cmd_balance(None, None, minqlbot.CHAT_CHANNEL)
            
    def handle_round_countdown(self, round_): 
        if not self.teams_changed:
            return
        if "balance" not in self.plugins:
            return
        balance = self.plugins["balance"]
        channel = minqlbot.CHAT_CHANNEL        
        teams = self.teams()
        teams = teams["red"] + teams["blue"]
        not_cached = balance.not_cached(self.game().short_type, teams)
        if not_cached:
            with balance.rlock:
                for lookup in balance.lookups:
                    for n in balance.lookups[lookup][1]:
                        if n in not_cached:
                            not_cached.remove(n)
                if not_cached:
                    balance.fetch_player_ratings(not_cached, channel, self.game().short_type)
        else:
            first_cond = ("balance" in self.plugins and 
                    max(self.game().red_score, self.game().blue_score)
                        <= self.config["AutoBalancedMaxScore"])
            if first_cond:
                self.plugins["balance"].cmd_balance(None, 
                                                    None, 
                                                    minqlbot.CHAT_CHANNEL) 
            
            # For some reason, teams status is outdated when
            # cmd_teams follows cmd_balance immediately
            # so we don't want to display it.
            if first_cond:
                channel = minqlbot.CONSOLE_CHANNEL
            else:
                channel = minqlbot.CHAT_CHANNEL
                
            if ("balance" in self.plugins and 
                  self.config["DisplayBalanceOnTeamsChange"] and 
                  self.teams_changed):
                self.plugins["balance"].cmd_teams(None, 
                                                  None,
                                                  channel)
        self.teams_changed = False                                          

    def cmd_version(self, player, msg, channel):    
        channel.reply("^6AutoBalance^7 plugin version ^6{}^7, author: ^6WalkerY^7 (github)".format(self.__version__))            

    def get_config(self, param = ""):
        if param == "":
            self.config = {}
            for name in self.config_defaults:
                if name != "":
                    self.config[name] = self.get_config(name)
                    self.debug("Config param {} set to {}".format(name, self.config[name]))
                else:
                    RuntimeError("Empty config variable name")
            return None
            
        config = minqlbot.get_config()
        fallback = self.config_defaults[param]
        try:
            section = self.CONFIG_SECTION_NAME
            if section in config and param in config[section]:
                if type(fallback) is bool:
                    value = config[section][param].strip().lower()
                    if value == "true":
                        ret = True
                    elif value == "false":
                        ret = False
                    else:
                        raise TypeError("Unrecognized value")
                elif type(fallback) is int:
                    ret = int(config[section][param])
                elif type(fallback) is str:
                    ret = config[section][param].strip()
                else:
                    raise TypeError("Unknown config parameter type.")
            else:
                ret = fallback
        except TypeError as err:
            ret = fallback
            self.debug("TypeError: " + err)
            
        return ret