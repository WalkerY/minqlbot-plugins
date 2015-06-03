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

"""When loaded, balances teams before match start automatically.
During each round countdown displays teams average ratings.

"""

import minqlbot

class autobalance(minqlbot.Plugin):
    def __init__(self):
        super().__init__()
        
        self.__version__ = '1.0.0'
        
        self.add_hook("game_countdown", self.handle_game_countdown)
        self.add_hook("round_countdown", self.handle_round_countdown)

        self.teams_changed = True

    def handle_team_switch(self, player, old_team, new_team):
        self.teams_changed = True        
        
    def handle_game_countdown(self):
        #auto-balance
        if "balance" in self.plugins:
            self.plugins["balance"].cmd_balance(None, None, minqlbot.CHAT_CHANNEL)
            
    def handle_round_countdown(self, round_): 
        if not self.teams_changed and round_ > 2:
            return
        else:
            self.teams_changed = False
        #teams info
        if "balance" in self.plugins:
            self.plugins["balance"].cmd_teams(None, None, minqlbot.CHAT_CHANNEL)
