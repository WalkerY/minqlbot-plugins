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

"""Plugin for unattended reconnecting and joining servers.

When bot disconnects from server this plugin will make it try 
reconnecting several times and if it fails it will try to join 
server that specified player has joined until successfull in 
joining this player or until manually moved to any server by any 
means. 

Also provides command to remotely move bot to a new server.

Internally plugin has two loops:
- "reconnect then join" automatic loop (called reconnect loop below)
- "join me" command loop (called join loop below)

Config.cfg snippet:
    [AutoConnect]
    ReconnectFallbackJoinName = WalkerY
When ReconnectFallbackJoinName is not configured, reconnect loop
won't proceed with joininig after maximum reconnect retries.
"""

import minqlbot

__version__ = '1.0.0'

# Number of samples we collect in order to determine if player is
# flooding bot. Each bot command sent to bot counts as 1 sample.
COMMAND_FLOOD_NUMBER_OF_SAMPLES = 5
# Minimum average frequency of commands sending to qualify as flooding 
# bot. In commands per second.
COMMAND_FLOOD_QUALIFYING_FREQUENCY = 1.5
         
class floodprotect(minqlbot.Plugin):
    def __init__(self):
        super().__init__()
        self.add_hook("chat", self.handle_chat, minqlbot.PRI_HIGH)
        #self.add_hook("player_disconnect")

    def handle_chat(self, player, msg, channel):
        self.msg("Command prefix: ={}=".format(minqlbot.COMMAND_PREFIX))
        

