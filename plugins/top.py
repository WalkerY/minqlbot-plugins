# Copyright (C) 2015 WalkerY (github)

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

"""Puts n best players into teams and others on spec. Designed for CA
but may work with other team modes. 

"""

import minqlbot
import datetime

class top(minqlbot.Plugin):
    def __init__(self):
        super().__init__()
        self.__version__ = "0.1.2"
        self.add_command("top", self.cmd_top, 1, usage="<number> [+<player_name>] [-<player_name>]", channels=("chat", ))
        self.add_command("tops", self.cmd_tops, 0, usage="<number> [+<player_name>] [-<player_name>]", channels=("chat", ))
        self.add_command("version", self.cmd_version, 0)
        
        # Due to unreliable 'balance' implementation there is a timeout
        # for top.
        self.timeout = 5
        
        # We want to ignore top operations started when first is still
        # in progress.
        self.in_progress = False
        self.last_call_time = None
       
    def cmd_version(self, player, msg, channel):    
        channel.reply("^6Top^7 plugin version ^6{}^7, author: ^6WalkerY^7 (github)".format(self.__version__))       
       
    def cmd_tops(self, player, msg, channel):
        return self.cmd_top(player, msg, channel)
       
    def cmd_top(self, player, msg, channel):
        """Lists every player in the game's rating in the current game mode.
        """
        
        is_simulation = (msg[0].lower() == "!tops")
        
        if not self.is_warmup() and not is_simulation:
            self.msg("^1TOP:^7 Command only allowed during Warm-up. For simulation use ^6!tops^7.")
            return

        # Cooperation with queueinfo plugin
        if not self.waiting_queue_is_top_allowed() and not is_simulation:
            self.msg("^1TOP:^7 Command not allowed due to queue resource plugin rule.")
            self.msg("^1TOP:^1 Restricting rule is: ^7{}"
                     .format(self.waiting_queue().full_rule_str))
            return
            
        if self.in_progress:
            if self.last_call_time is not None:
                delta = datetime.datetime.now() - self.last_call_time
                if delta.days > 0 or delta.seconds > self.timeout:
                    self.in_progress = True
                    self.last_call_time = datetime.datetime.now()
                else:
                    channel.reply("^3TOP:^7 Another ^6TOP^7 operation in progress. Please try again in few seconds.")
            else:
                self.debug("Warning 002")
                self.in_progress = True
                self.last_call_time = datetime.datetime.now()
        
        ts = int(self.game().teamsize)

        to_join = []
        to_spec = []
        number = 0
            
        if len(msg) < 2:
            return minqlbot.RET_USAGE
        else: 
            try:
                number = int(msg[1])
            except ValueError:
                number = ts*2
                
            if (number > ts*2):
                self.msg("^7Teamsize is too low to put {} players in teams.".format(number))
                return
                
        if len(msg) > 1:
            for arg in msg[1:]:
                if arg.startswith("+"):
                    pl = self.find_player(arg[1:])
                    if pl is None:
                        self.msg("^1TOP:^7 Couldn't find player ^7{}^7. Ignoring argument.".format(arg[1:]))
                        continue
                    to_join.append(pl)
                elif arg.startswith("-"):
                    pl = self.find_player(arg[1:])
                    if pl is None:
                        self.msg("^1TOP:^7 Couldn't find player ^7{}^7. Ignoring argument.".format(arg[1:]))
                        continue
                    to_spec.append(pl)
                    
        teams = self.teams()
        teams = teams["red"] + teams["blue"] + teams["spectator"]
        now = datetime.datetime.now()
        self.debug("^2TOP:^7 Choosing ^6{}^7 top players. Fetching QLRanks ratings...".format(number))
        channel.reply("^2TOP:^7 Choosing ^6{}^7 top players. Fetching QLRanks ratings...".format(number))
        self.top(teams, channel, self.game().short_type, number, to_join, to_spec, now, is_simulation)

    def top(self, names, channel, game_type, number, to_join, to_spec, call_time, is_simulation):
        if "balance" not in self.plugins:
            return        
        
        balance = self.plugins["balance"]

        not_cached = balance.not_cached(game_type, names)
        if not_cached:
            with balance.rlock:
                for lookup in balance.lookups:
                    for n in balance.lookups[lookup][1]:
                        if n in not_cached:
                            not_cached.remove(n)
                if not_cached:
                    balance.fetch_player_ratings(not_cached, channel, game_type)
                if (self.top, (names, channel, game_type, number, to_join, to_spec, call_time, is_simulation)) not in balance.pending:
                    balance.pending.append((self.top, (names, channel, game_type, number, to_join, to_spec, call_time, is_simulation)))
                return False
    
        # Return if we are called after timeout by balance plugin.
        delta = datetime.datetime.now() - call_time
        if delta.seconds >= self.timeout:
            self.debug("^^2TOP:^7 ^1Timed out^7.")
            # We return true so that it can be removed from balance's 
            # pending list
            return True
        else:
            self.debug("^2TOP:^7 Fetching completed. Setting up teams... ")
            channel.reply("^2TOP:^7 Fetching completed. Setting up teams... ")

        if not is_simulation:
            self.send_command("lock")
            
        teams = self.teams()    
        all_sorted = sorted(teams["red"]+teams["blue"]+teams["spectator"], 
                        key=lambda x: balance.cache[x.clean_name.lower()][game_type]["elo"], 
                        reverse=True)
             
        # ignore afks/not playing, including flagged players by ban/balance 
        # plugins
        if self.waiting_queue() is not None:
            not_playing = self.waiting_queue().not_playing_players
            for pl in not_playing:
                all_sorted.remove(pl)
            if len(not_playing) > 0:
                self.msg("^3TOP:^7 Ignored not playing: ^7{}"
                        .format("^7, ^7".join([x.name for x in not_playing])))

        for pl in all_sorted:
            if pl in to_join and pl in to_spec:
                self.msg("^3TOP:^7 ^3'+' argument takes precedence over '-' for ^7'{}^7'.".format(pl.name))
                to_spec.remove(pl)
        
        for pl in all_sorted:
            if pl.clean_name.lower() == minqlbot.NAME.lower():
                if pl not in to_join:
                    all_sorted.remove(pl)
                break
        
        top_list = all_sorted.copy()
        
        for pl in top_list:
            if pl in to_spec:
                top_list.remove(pl)
            elif pl in to_join:
                top_list.remove(pl)
               
        top_list = top_list[:max(0, min(number-len(to_join), len(top_list)))]
        
        for pl in to_join:
            if pl not in top_list:
                top_list.append(pl)
        
        another_team = {"red":"blue","blue":"red"}      
        teams = self.teams()

        for pl in all_sorted:
            if pl not in top_list:
                if pl.team != "spectator":
                    teams[pl.team].remove(pl)
                    teams["spectator"].append(pl)
                    if not is_simulation:
                        pl.put("spectator")
             
        for pl in top_list:
            if pl.team == "spectator":
                if len(teams["red"]) < len(teams["blue"]):
                    teams["spectator"].remove(pl)
                    teams["red"].append(pl)
                    if not is_simulation:
                        pl.put("red")
                else:
                    teams["spectator"].remove(pl)
                    teams["blue"].append(pl)
                    if not is_simulation:
                        pl.put("blue")
        
        for pl in top_list:
            if pl in teams["red"]:
                team = "red"
            elif pl in teams["blue"]:
                team = "blue"
            else:
                self.debug("Error 001")
                return True
            
            if len(teams[team]) > len(teams[another_team[team]]) + 1:
                teams[team].remove(pl)
                teams[another_team[team]].append(pl)
                if not is_simulation:
                    pl.put(another_team[team])
                
        
        players = "^7" + "^7, ".join([x.name for x in top_list])
        td = datetime.datetime.now() - call_time
        durationms = int(td.seconds * 1000 + td.microseconds / 1000)
        
        if not is_simulation:
            msg_core = "Completed in"
        else:
            msg_core = "^2SIMULATED^7 in"
        
        if len(top_list) != 0:
            channel.reply("^2TOP:^7 {} ^6{}^7ms. Players: {}"
                     .format(msg_core, durationms, players))
        else: 
            channel.reply("^2TOP:^7 {} ^6{}^7ms. No players in teams."
                     .format(msg_core, durationms))
                     
        self.in_progress = False
        self.last_call_time = None
        
        return True

    def is_connected(self):
        """Checks if bot is connected to game server."""        
        return (minqlbot.connection_status() == 8)
        
    def is_warmup(self):
        """Checks if game is in warmup state. """        
        return (self.is_connected() and 
                self.game and 
                self.game().state == "warmup")
                
    # Gets interface to queueinfo plugin
    def waiting_queue(self):
        if "queueinfo" in self.plugins:
            return self.plugins["queueinfo"].interface
        else:
            return None
                
    def waiting_queue_is_top_allowed(self):
        if self.waiting_queue() is not None:
            rule = self.waiting_queue().rule_str
            time = self.waiting_queue().rule_time
            if time is not None and "TOP COMMAND ALLOWED" in rule:
                now = datetime.datetime.now()
                return (now.hour > time.hour or
                       (now.hour == time.hour and now.minute >= time.minute))
        return True
        
        