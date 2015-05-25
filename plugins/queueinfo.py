# Copyright (C) WalkerY (github) aka WalkerX (ql)

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

"""Displays Queue of players and also detects AFKs/Not playing players."""
# Config sample:
#[QueueInfo]
#
## Automatically mark player as Not Playing if he is waiting specified time in minutes in queue on spec and not joining.
## He can mark himself as WAITING again by using !waiting command or one of its aliases. Value 0 disables this feature.
#WaitingTime: 45

import minqlbot
import datetime
import time

class queueinfo(minqlbot.Plugin):
    def __init__(self):
        super().__init__()
        self.add_hook("player_connect", self.handle_player_connect)
        self.add_hook("player_disconnect", self.handle_player_disconnect)
        self.add_hook("team_switch", self.handle_team_switch)
        self.add_command(("queue", "kolejka", "q", "k"), self.cmd_queue, 0)
        self.add_command(("playing", "here", "notafk", "waiting"), self.cmd_playing, 0)
        self.add_command(("notplaying", "afk", "gone", "bye", "brb", "bb"), self.cmd_notplaying, 0)

        # List of players in queue, their queue join times and other info as required.
        # {"walkerx": {"joinTime": datetime}}
        self.queue = {}
        self.initialize()
        
    def initialize(self):
        specs = self.teams()["spectator"]
        for spec in specs:
            name = spec.clean_name.lower()
            if name not in self.queue:
                self.queue[name] = {"joinTime": datetime.datetime.now(), "name": spec.name}
                time.sleep(0.01) # let's make each time differ always internally
        self.remove_bot()
    
    def handle_player_connect(self, player):
        name = player.clean_name.lower()
        if name not in self.queue:
            self.queue[name] = {"joinTime": datetime.datetime.now(), "name": player.name}
        self.remove_bot()
        
    def handle_player_disconnect(self, player, reason):
        name = player.clean_name.lower()
        if name in self.queue:
            del self.queue[name]
            
    def handle_team_switch(self, player, old_team, new_team):
        name = player.clean_name.lower()
        if new_team == "spectator":
            if name not in self.queue:
                self.queue[name] = {"joinTime": datetime.datetime.now(), "name": player.name}
        elif new_team != "spectator":
            if name in self.queue:
                del self.queue[name]
                
        self.remove_bot()
    
    def cmd_playing(self, player, msg, channel):    
        self.mark_playing(player.clean_name.lower())
        channel.reply("^7Player {} ^7was marked as playing.".format(player.name))
    
    def cmd_notplaying(self, player, msg, channel):    
        self.mark_notplaying(player.clean_name.lower())
        channel.reply("^7Player {} ^7was marked as not playing.".format(player.name))
    
    def cmd_queue(self, player, msg, channel):        
        config = minqlbot.get_config()
        # check for configured Auto Not Playing Time
        if "QueueInfo" in config and "WaitingTime" in config["QueueInfo"]:
            maxwaitingtime = int(config["QueueInfo"]["WaitingTime"])
        else:
            maxwaitingtime = 45
            
            
        time_now = datetime.datetime.now()
        namesbytime = sorted(self.queue, key=lambda x: self.queue[x]["joinTime"])       
        if not len(namesbytime):
            channel.reply("^7No players in queue.")
        else:
            reply = "^7WAITING: "
            counter = 0
            notplaying = []
            for name in namesbytime:
                diff = time_now - self.queue[name]["joinTime"]
                seconds = diff.days * 3600 * 24
                seconds = seconds + diff.seconds
                minutes = seconds // 60
                waiting_time = ""
                
                # Check if marked as Not Playing
                if self.is_notplaying(name):
                    # add to Not Playing queue
                    notplaying.append(name)
                    continue
                
                # check if should be marked automatically as NotPlaying                    
                elif maxwaitingtime > 0 and minutes > maxwaitingtime:
                    # check for time overrule
                    if "playingOverrideTime" in self.queue[name]:
                        diff2 = time_now - self.queue[name]["playingOverrideTime"]
                        seconds2 = diff2.days * 3600 * 24
                        seconds2 = seconds2 + diff2.seconds
                        minutes2 = seconds2 // 60
                        if minutes2 > maxwaitingtime:
                            self.mark_notplaying(name, True)
                            notplaying.append(name)
                            continue
                    else:
                        self.mark_notplaying(name, True)
                        notplaying.append(name)
                        continue
                
                if minutes:
                    waiting_time = "^6{}m^7".format(minutes)
                else:
                    waiting_time = "^6{}s^7".format(seconds)
                counter = counter + 1
                if counter != 1:
                    reply = reply + ", "
                reply = reply + "^7{} ^7{}".format(self.queue[name]["name"], waiting_time)
                
            if counter != 0: 
                channel.reply(reply)
            
            if len(notplaying):
                reply = "^5NOT PLAYING: "
                counter = 0
                for name in notplaying:
                    diff = time_now - self.queue[name]["joinTime"]
                    seconds = diff.days * 3600 * 24
                    seconds = seconds + diff.seconds
                    minutes = seconds // 60
                    waiting_time = ""

                    if minutes:
                        waiting_time = "^5{}m^7".format(minutes)
                    else:
                        waiting_time = "^5{}s^7".format(seconds)
                    counter = counter + 1
                    if counter != 1:
                        reply = reply + ", "
                    reply = reply + "^5{} ^5{}".format(name, waiting_time)
                channel.reply(reply)     
                for name in notplaying:
                    player_ = self.find_player(name)
                    if player_:
                        if "autoNotPlaying" in self.queue[name] and self.queue[name]["autoNotPlaying"]:                       
                            player_.tell("^7Due to a long waiting time, you have been automatically marked as NOT PLAYING.")
                        player_.tell("^7{} ^7to change your status to WAITING type ^6!waiting^7 in chat".format(player_.name))

    # check if marked as Not Playing
    def is_notplaying(self, name):
        if name in self.queue and "notPlaying" in self.queue[name]:
            return self.queue[name]["notPlaying"]
        else:
            return False
            
    # mark as not playing
    def mark_notplaying(self, name, automatic=False):
        if name in self.queue:
            self.queue[name]["notPlaying"] = True
            if "playingOverrideTime" in self.queue[name]:
                del self.queue[name]["playingOverrideTime"]
            if automatic:
                self.queue[name]["autoNotPlaying"] = True
    
    # mark as playing
    def mark_playing(self, name):
        if name in self.queue:
            if "notPlaying" in self.queue[name]:
                del self.queue[name]["notPlaying"]
            self.queue[name]["playingOverrideTime"] = datetime.datetime.now()
            if "autoNotPlaying" in self.queue[name]:
                del self.queue[name]["autoNotPlaying"]
            
    # remove bot from queue
    def remove_bot(self):
        config = minqlbot.get_config()
        if "Core" in config and "Nickname" in config["Core"]:
            if config["Core"]["Nickname"].lower() in self.queue:
                del self.queue[config["Core"]["Nickname"].lower()]