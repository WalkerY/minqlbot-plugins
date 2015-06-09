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

"""
warmup plugin displays warmup message

"""

import minqlbot
import traceback

class warmup(minqlbot.Plugin):
    def __init__(self):
        super().__init__()
        __version__ = '1.0.0'
        
        self.add_hook("player_connect", self.handle_player_connect)
       
    def handle_player_connect(self, player):
        self.delay(20, lambda: 
            player.tell("^7{} please warmup before joining. To warmup type ^6join walkerz^7 in console.".format(player.name)))
        