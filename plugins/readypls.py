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

"""Displays pls. ready message.
It's not configurable via config file yet.

"""

import minqlbot
import datetime
import threading

class readypls(minqlbot.Plugin):
    # in seconds
    REPEAT_DELAY = 15
    DELAY_AFTER_GAME_END = 15
    DELAY_AFTER_MAP_CHANGE = 15
    READY_MSG = "^1>^2>^3>^4>^5>^6> ^7READY - ^6F3^7 NOW! ^4ALL PLAYERS MUST BE READY. ^7AUTO-BALANCE ON START."
    
    def __init__(self):
        super().__init__()
        
        self.__version__ = '0.1.1'        
        
        self.add_hook("unload", self.handle_unload)
        self.add_hook("team_switch", self.handle_team_switch)   
        self.add_hook("player_disconnect", self.handle_player_disconnect)        
        self.add_hook("game_countdown", self.handle_game_countdown)
        self.add_hook("game_end", self.handle_game_end)
        self.add_hook("map", self.handle_map)
        self.add_hook("abort", self.handle_abort)
        self.add_hook("bot_disconnect", self.handle_bot_disconnect)
        self.add_hook("bot_connect", self.handle_bot_connect)        
        self.add_command("version", self.cmd_version, 0)
        
        self.unload_event = threading.Event()
        self.unload_event.clear()
        self.game_end_event = threading.Event()
        self.game_end_event.set()
        
        self.map_event = threading.Event()
        self.map_event.set()
        
        self.shared_lock = threading.RLock()
        self.players_red = len(self.teams()["red"])
        self.players_blue = len(self.teams()["blue"])
        self.game_warmup = False
        
        if minqlbot.connection_status() == 8:
            if self.game(): 
                if self.game().state == "warmup":
                    self.game_warmup = True
                        
        threading.Thread(target = self.loop).start()

    def handle_bot_disconnect(self):
        with self.shared_lock:
            self.game_warmup = False
        
    def handle_bot_connect(self):
        with self.shared_lock:
            self.players_red = len(self.teams()["red"])
            self.players_blue = len(self.teams()["blue"])
            self.game_warmup = False
        
            if minqlbot.connection_status() == 8:
                if self.game(): 
                    if self.game().state == "warmup":
                        self.game_warmup = True

            self.game_end_event.set()

    def handle_abort(self):
        with self.shared_lock:
            self.game_warmup = True
            self.game_end_event.set()
        
    def handle_game_countdown(self):
        with self.shared_lock:
            self.game_warmup = False
            self.game_end_event.set()

    def handle_game_end(self, game, score, winner):
        with self.shared_lock:
            self.game_warmup = True
            self.game_end_event.clear()            

    def handle_map(self, map):
        with self.shared_lock:
            # On map change we wait longer before displaying
            # anything. Is this precaution unnecessary? TODO
            self.map_event.clear()
            
    def handle_unload(self):
        self.unload_event.set()
        self.game_end_event.set()
        self.map_event.set()

    def handle_team_switch(self, player, old_team, new_team):
        name = player.clean_name.lower()
        with self.shared_lock:
            self.players_red = len(self.teams()["red"])
            self.players_blue = len(self.teams()["blue"])
        
    def handle_player_disconnect(self, player, reason):
        name = player.clean_name.lower()       
        with self.shared_lock:
            self.players_red = len(self.teams()["red"])
            self.players_blue = len(self.teams()["blue"])
                
    def loop(self):
        while True:
            if self.unload_event.wait(self.REPEAT_DELAY):
                return
            if not self.game_end_event.wait(self.DELAY_AFTER_GAME_END):
                with self.shared_lock:
                    self.game_end_event.set()
            if not self.map_event.wait(self.DELAY_AFTER_MAP_CHANGE):
                with self.shared_lock:
                    self.map_event.set()
            with self.shared_lock:
                red = self.players_red
                blue = self.players_blue
                warmup = self.game_warmup
            if red == blue and red >= 2 and warmup:
                self.msg(self.READY_MSG)

    def cmd_version(self, player, msg, channel):    
        channel.reply("^6ReadyPls^7 plugin version ^6{}^7, author: ^6WalkerY^7 (github)".format(self.__version__))                            