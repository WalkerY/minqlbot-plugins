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

"""Kicks players that are flooding bot with commands.  """

import minqlbot
import datetime
import collections

__version__ = '1.0.0'

# Number of samples we collect in order to determine if player is
# flooding bot. Each bot command sent to bot counts as 1 sample.
COMMAND_FLOOD_NUMBER_OF_SAMPLES = 5
# Minimum average frequency of commands sending to qualify as flooding 
# bot. In commands per second.
COMMAND_FLOOD_QUALIFYING_FREQUENCY = 1.5
# Ban period when flood is detected. String format the same as in 'ban'
# command in 'ban' plugin.
BAN_DURATION = "1 hour"
BAN_REASON = "Flooding bot with commands."

MIN_TOTAL_SECONDS = \
    COMMAND_FLOOD_NUMBER_OF_SAMPLES / COMMAND_FLOOD_QUALIFYING_FREQUENCY
         
class floodprotect(minqlbot.Plugin):
    def __init__(self):
        super().__init__()
        self.add_hook("chat", self.handle_chat, minqlbot.PRI_HIGH)
        self.add_hook("player_disconnect", self.handle_player_disconnect)
        
        # Timestamp of the most recent command per player.
        self.timestamp = {}
        # Timedeltas between timestamps for each player.
        self.deltas = {}
        # Sum of all Timedeltas for each player.
        self.deltas_sum = {}
        
    def handle_chat(self, player, msg, channel):
        if player.clean_name.lower() == minqlbot.NAME.lower():
            return
    
        if not msg.startswith(minqlbot.COMMAND_PREFIX):
            return
        
        self.new_command(player)

    def handle_player_disconnect(self, player, reason):
        name = player.clean_name.lower()
        if name in self.timestamp:
            del self.timestamp[name]
        if name in self.deltas:
            del self.deltas[name]            
        if name in self.deltas_sum:
            del self.deltas_sum[name]            
        
    def new_command(self, player):
        name = player.clean_name.lower()
        
        if name not in self.timestamp:
            self.timestamp[name] = datetime.datetime.now()
            self.deltas[name] = collections.deque()
            self.deltas_sum[name] = datetime.timedelta()
            return
        
        # At least one timestamp was already saved.
        last_timestamp = self.timestamp[name]
        self.timestamp[name] = datetime.datetime.now()
        delta = self.timestamp[name] - last_timestamp
        
        self.deltas[name].append(delta)
        self.deltas_sum[name] += delta
        
        samples = len(self.deltas[name]) + 1
        
        # If we have too many samples, we remove the least recent one.
        if samples > COMMAND_FLOOD_NUMBER_OF_SAMPLES:
            last_delta = self.deltas[name].popleft()
            self.deltas_sum[name] -= last_delta
            samples -= 1
        
        if samples == COMMAND_FLOOD_NUMBER_OF_SAMPLES:
            if self.deltas_sum[name].days != 0:
                return
            
            seconds = float(self.deltas_sum[name].seconds)
            seconds += self.deltas_sum[name].microseconds / 1000000
            self.debug("cur: {}".format(seconds))
            self.debug("min: {}".format(MIN_TOTAL_SECONDS))
            if seconds >= MIN_TOTAL_SECONDS:
                return
            
            self.flood_detected(player)
            
    def flood_detected(self, player):
        if "ban" in self.plugins:
            ban = self.plugins["ban"]
            ban.cmd_ban(player, 
                        "ban {} {} {}".format(player.clean_name.lower(),
                                              BAN_DURATION,
                                              BAN_REASON),
                        minqlbot.CHAT_CHANNEL)
            self.msg("^7{}^7 ban reason: ^1{}".format(player.name, BAN_REASON))
        else:
            self.kickban(player.clean_name.lower())
            self.msg("^7{}^7 kick reason: ^1{}".format(player.name, BAN_REASON))