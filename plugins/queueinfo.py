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

"""Displays Queue of players and also detects AFKs/Not playing players.
Players are removed from queue after they have played for PENDING_REMOVAL_TIME
seconds or after they have been disconnected for ABSENT_REMOVAL_TIME seconds.
When they are playing and in queue they are marked green. Whey they are disconnected
and still in queue they are marked black.

Setrule command allows one to introduce non-standard playing order rule so
that it is displayed when players connect and also when they use !queue
command.

Config sample:
    [QueueInfo]

    # Automatically mark player as Not Playing if he is waiting specified
    # time in minutes in queue on spec and not joining. He can mark himself 
    # as WAITING again by using !waiting command or one of its aliases. Value
    # 0 disables this feature (players are not marked afk automatically).
    WaitingTime: 45

"""


import minqlbot
import datetime
import time

class queueinfo(minqlbot.Plugin):
    def __init__(self):
        super().__init__()
        self.__version__ = "0.9.9"
        self.add_hook("player_connect", self.handle_player_connect)
        self.add_hook("player_disconnect", self.handle_player_disconnect)
        self.add_hook("team_switch", self.handle_team_switch)
        self.add_hook("round_start", self.handle_round_start, priority=minqlbot.PRI_LOWEST)
        self.add_hook("round_end", self.handle_round_end, priority=minqlbot.PRI_LOWEST)        
        self.add_command(("queue", "kolejka", "q", "k"), self.cmd_queue, 0)
        self.add_command(("playing", "here", "notafk", "waiting"), self.cmd_playing, 0)
        self.add_command(("notplaying", "afk", "gone", "bye", "brb", "bb"), self.cmd_notplaying, 0)
        self.add_command("setrule", self.cmd_setrule, 5, usage="<rule>")
        self.add_command("remrule", self.cmd_remrule, 5)
        self.add_command("version", self.cmd_version, 0)

        # Minimum play time before removal from queue in seconds.
        self.PENDING_REMOVAL_TIME = 120

        # Minimum absent time after leaving server before removal from
        # queue in seconds.
        self.ABSENT_REMOVAL_TIME = 120
        
        # List of players in queue, their queue join times and other info as required.
        # {"walkerx": {"joinTime": datetime}}
        self.queue = {}
                
        self.initialize()

        self.rule = ""
        
    def initialize(self):
        specs = self.teams()["spectator"]
        for spec in specs:
            name = spec.clean_name.lower()
            if name not in self.queue:
                self.add(spec)
                time.sleep(0.01) # let's make each time differ always internally
        self.remove_bot()
    
    def handle_player_connect(self, player):
        name = player.clean_name.lower()
        self.try_removal(name)
        if name not in self.queue:
            self.add(player)
        else:
            # Quickly returning player - we put him back into
            # present status in queue.
            if name in self.queue:
                if "disconnectTime" in self.queue[name]:
                    del self.queue[name]["disconnectTime"]

        self.remove_bot()
        
        if self.rule != "":
            self.delay(20, lambda: player.tell("^1WARNING ^7!!! Custom order rule: ^6{}".format(self.rule)))
        
    def handle_player_disconnect(self, player, reason):
        name = player.clean_name.lower()
        self.try_removal(name)
        if name in self.queue:
            if "pendingRemoval" in self.queue[name]:
                del self.queue[name]["pendingRemoval"]
            if "pendingRemovalTime" in self.queue[name]:
                del self.queue[name]["pendingRemovalTime"]
            self.queue[name]["disconnectTime"] = datetime.datetime.now()
        #if name in self.queue:
        #    del self.queue[name]
            
    def handle_team_switch(self, player, old_team, new_team):
        name = player.clean_name.lower()
        if new_team == "spectator":
            if name not in self.queue:
                self.add(player)
            else:
                self.cancel_pending_remove(name)
        elif new_team != "spectator":
            if name in self.queue:
                self.pending_remove(name)
                
        self.remove_bot()

    def handle_round_end(self, score, winner):        
        self.try_removals()

    def handle_round_start(self, round_):
        # Start counting playtime for all players
        # that have been in queue
        for name in self.queue:
            if (self.queue[name]["player"].team != "spectator" and
                "pendingRemoval" in self.queue[name] and
                self.queue[name]["pendingRemoval"] and
               "pendingRemovalTime" not in self.queue[name]):
                self.queue[name]["pendingRemovalTime"] = \
                    datetime.datetime.now()

    def cmd_version(self, player, msg, channel):    
        channel.reply("^6QueueInfo^7 plugin version ^6{}^7, author: ^6WalkerY^7 (github)".format(self.__version__))
                    
    def cmd_remrule(self, player, msg, channel):    
        self.rule = ""
        self.msg("^7Queue rule removed. Normal playing order now.")

    def cmd_setrule(self, player, msg, channel):    
        if len(msg) < 2:
            return minqlbot.RET_USAGE
        self.rule = " ".join(msg[1:])
        self.msg("^7Playing order rule: ^6{}^7.".format(self.rule))
        
    def cmd_playing(self, player, msg, channel):    
        self.mark_playing(player.clean_name.lower())
        channel.reply("^7Player {} ^7was marked as playing.".format(player.name))
    
    def cmd_notplaying(self, player, msg, channel):    
        if player.team == "spectator":
            self.mark_notplaying(player.clean_name.lower())
            channel.reply("^7Player {} ^7was marked as not playing.".format(player.name))
        else: 
            channel.reply("^7Player {} ^7can't be marked as not playing.".format(player.name))
    
    def cmd_queue(self, player, msg, channel):        
        config = minqlbot.get_config()
        # check for configured Auto Not Playing Time
        if "QueueInfo" in config and "WaitingTime" in config["QueueInfo"]:
            maxwaitingtime = int(config["QueueInfo"]["WaitingTime"])
        else:
            maxwaitingtime = 45
        
        self.try_removals()
            
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
                
                if self.is_pending_removal(name):
                    waiting_time += "^2*^7"
                    reply = reply + "^2{} ^7{}".format(name, waiting_time)
                elif self.is_on_short_leave(name):
                    waiting_time += "^0*^7"
                    reply = reply + "^0{} ^7{}".format(name, waiting_time)
                else:
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

                    if self.is_pending_removal(name):
                        waiting_time += "^2*^7"
                    elif self.is_on_short_leave(name):
                        waiting_time += "^0*^7"
                        
                    reply = reply + "^5{} ^5{}".format(name, waiting_time)
                    
                channel.reply(reply)     
                for name in notplaying:
                    player_ = self.find_player(name)
                    if player_:
                        if "autoNotPlaying" in self.queue[name] and self.queue[name]["autoNotPlaying"]:                       
                            player_.tell("^7Due to a long waiting time, you have been automatically marked as NOT PLAYING.")
                        player_.tell("^7{} ^7to change your status to WAITING type ^6!waiting^7 in chat".format(player_.name))
                
            if self.rule != "":
                channel.reply("^1WARNING ^7!!! Custom order rule: ^6{}".format(self.rule))

    # check if marked as Not Playing
    def is_notplaying(self, name):
        if name in self.queue and "notPlaying" in self.queue[name]:
            return self.queue[name]["notPlaying"]
        else:
            return False

    def add(self, player):
        name = player.clean_name.lower()    
        self.queue[name] = {"joinTime": datetime.datetime.now(), 
                            "name": player.name,
                            "player": player}
        
    def pending_remove(self, name):
        '''We don't remove immediately as player may not start playing
        after joining.  
        
        '''
        self.queue[name]["pendingRemoval"] = True

    def cancel_pending_remove(self, name):
        if name in self.queue:
            if "pendingRemoval" in self.queue[name]:
                del self.queue[name]["pendingRemoval"]
            if "pendingRemovalTime" in self.queue[name]:
                del self.queue[name]["pendingRemovalTime"]    
                
    def is_pending_removal(self, name):
        if name in self.queue:
            if "pendingRemoval" in self.queue[name]:
                return self.queue[name]["pendingRemoval"]
                
        return False 

    def is_on_short_leave(self, name):
        if name in self.queue:
            if "disconnectTime" in self.queue[name]:
                return True
        return False         
        
    def try_removals(self):
        for name in self.queue.copy():
            self.try_removal(name)
        
    def try_removal(self, name):
        '''We remove only if player played for some time.  
        
        '''
        if name in self.queue:
            if "pendingRemovalTime" in self.queue[name]:
                delta = datetime.datetime.now() - \
                        self.queue[name]["pendingRemovalTime"]
                if (delta.days > 0 or 
                    delta.seconds > self.PENDING_REMOVAL_TIME):
                    del self.queue[name]
            if "disconnectTime" in self.queue[name]:
                delta = datetime.datetime.now() - \
                        self.queue[name]["disconnectTime"]
                if (delta.days > 0 or 
                    delta.seconds > self.ABSENT_REMOVAL_TIME):
                    del self.queue[name]
            
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