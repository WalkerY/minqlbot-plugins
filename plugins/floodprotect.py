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
import threading

__version__ = '2.0.0'
    
class FloodProcessor:
    # Number of samples we collect in order to determine if player is
    # flooding bot. Each bot command sent to bot counts as 1 sample.
    DEFAULT_COMMAND_FLOOD_NUMBER_OF_SAMPLES = 4
    # Minimum average frequency of commands sending to qualify as flooding 
    # bot. In commands per second.
    DEFAULT_COMMAND_FLOOD_QUALIFYING_FREQUENCY = 1.0
    # Ban period when flood is detected. String format the same as in 'ban'
    # command in 'ban' plugin.
    DEFAULT_BAN_DURATION = "1 hour"
    DEFAULT_BAN_REASON = "Flood detected."

    # Timeout for local cache of recently banned flooding players
    COMMAND_FLOOD_BANNED_TIMEOUT = 30

    plugin = None

    # We cache most recently banned players to avoid double 
    # banning and checking in db.
    banned = {}
    banned_lock = threading.RLock()

    def __init__(self, plugin, samples=None, frequency=None, ban_duration=None, ban_reason=None):
        self.plugin = plugin
        if samples is not None:
            self.samples = samples
        else:
            self.samples = self.DEFAULT_COMMAND_FLOOD_NUMBER_OF_SAMPLES
        if frequency is not None:
            self.frequency = frequency
        else:
            self.frequency = self.DEFAULT_COMMAND_FLOOD_QUALIFYING_FREQUENCY
        if ban_duration is not None:
            self.ban_duration = ban_duration
        else:
            self.ban_duration = self.DEFAULT_BAN_DURATION
        if ban_reason is not None:
            self.ban_reason = ban_reason
        else:
            self.ban_reason = self.DEFAULT_BAN_REASON
            
        self.min_total_seconds = samples / frequency

        # Timestamp of the most recent event per player.
        self.timestamp = {}
        # Timedeltas between timestamps for each player.
        self.deltas = {}
        # Sum of all Timedeltas for each player.
        self.deltas_sum = {}
        
    def clear_player_events(self, player):
        name = player.clean_name.lower()
        if name in self.timestamp:
            del self.timestamp[name]
        if name in self.deltas:
            del self.deltas[name]            
        if name in self.deltas_sum:
            del self.deltas_sum[name] 

    @classmethod        
    def clear_banned_log(cls):
        with cls.banned_lock:
            for thread in cls.banned:
                cls.banned[thread].cancel()       
        
    def trigger_event(self, player):
        name = player.clean_name.lower()
        if name == minqlbot.NAME.lower():
            return
            
        with self.banned_lock:
            if name in self.banned:
                # kickban here is mostly for the case that 'ban' plugin
                # is not loaded and player quickly returned.
                self.plugin.kickban(name)
                return
        
        self.__process_event(player)
        
    def __process_event(self, player):
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
        if samples > self.samples:
            last_delta = self.deltas[name].popleft()
            self.deltas_sum[name] -= last_delta
            samples -= 1
        
        if samples == self.samples:
            if self.deltas_sum[name].days != 0:
                return
            
            seconds = float(self.deltas_sum[name].seconds)
            seconds += self.deltas_sum[name].microseconds / 1000000
            if seconds >= self.min_total_seconds:
                return
            
            self.__flood_detected(player)
            
    def __flood_detected(self, player):
        if "ban" in self.plugin.plugins:
            ban = self.plugin.plugins["ban"]
            ban.cmd_ban(player, 
                        ["ban", 
                         player.clean_name.lower(),
                         self.ban_duration,
                         self.ban_reason],
                        minqlbot.CHAT_CHANNEL)
            self.plugin.msg("^7{}^7 ban reason: ^1{}".format(player.name, self.ban_reason))
        else:
            self.plugin.kickban(player.clean_name.lower())
            self.plugin.msg("^7{}^7 kick reason: ^1{}".format(player.name, self.ban_reason))

        # Add player to cache and set timer to remove it
        with self.banned_lock:
            name = player.clean_name.lower()
            self.banned[name] = \
                threading.Timer(self.COMMAND_FLOOD_BANNED_TIMEOUT, 
                                function=self.__remove_banned,
                                args=(name, ))
            self.banned[name].start()
            self.plugin.debug("Player {} added to banned cache.".format(name))        
     
    def __remove_banned(self, name):
        with self.banned_lock:
            if name in self.banned:
                del self.banned[name]
        self.plugin.debug("Player {} removed from banned cache.".format(name))
         

class floodprotect(minqlbot.Plugin):
    flood_processors = {}

    def __init__(self):
        super().__init__()
        self.add_hook("chat", self.handle_chat, minqlbot.PRI_HIGH)
        self.add_hook("vote_called", self.handle_vote_called, minqlbot.PRI_HIGH)
        self.add_hook("player_disconnect", self.handle_player_disconnect)
        self.add_hook("unload", self.handle_unload)

        self.flood_processors = {
            "chat_command": FloodProcessor(self, 4, 1.0), # Max. 4 commands in 4 seconds
            "chat_command_lowerf": FloodProcessor(self, 6, 1.0 / 3.0), # Max. 6 commands in 18 seconds
            "chat_command_lowestf": FloodProcessor(self, 20, 1.0 / 45.0), # Max. 20 commands in 15 minutes
            "vote": FloodProcessor(self, 3, 1.0), # Max. 3 votes in 3 seconds
            "vote_lowerf": FloodProcessor(self, 6, 1.0 / 3.0), # Max. 6 votes in 18 seconds
            "vote_lowestf": FloodProcessor(self, 20, 1.0 / 45.0), # Max. 20 votes in 15 minutes
            "chat": FloodProcessor(self, 12, 1.0 / 0.6) # Max. 12 chat messages in 7,2 seconds
            }

    def handle_unload(self):
        FloodProcessor.clear_banned_log()

    def handle_vote_called(self, caller, vote, args):
        for processor in self.flood_processors:
            if processor.startswith("vote"):
                self.flood_processors[processor].trigger_event(caller)
        
    def handle_chat(self, player, msg, channel):
        for processor in self.flood_processors:
            if (msg.startswith(minqlbot.COMMAND_PREFIX) and
               processor.startswith("chat_command")):
                self.flood_processors[processor].trigger_event(player)    
            if processor.startswith("chat"):
                self.flood_processors[processor].trigger_event(player)    

    def handle_player_disconnect(self, player, reason):
        for processor in self.flood_processors: 
            self.flood_processors[processor].clear_player_events(player)
        