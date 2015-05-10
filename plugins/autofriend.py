# minqlbot - A Quake Live server administrator bot.
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

"""Invites all friends that are online. Befriends all ppl above certain elo limit after they have completed the game."""
"""Requires ExtraQL with inviteall and addfriend commands."""

import minqlbot

class autofriend(minqlbot.Plugin):
    def __init__(self):
        super().__init__()
        self.add_hook("game_end", self.handle_game_end)
        self.add_command("inviteall", self.cmd_inviteall, 5)
        self.add_command("befriend", self.cmd_befriend, 5, usage="<nick>")
            
    def handle_game_end(self, game, score, winner):
        config = minqlbot.get_config()
        if "AutoFriend" in config and "AutoFriend" in config["AutoFriend"]:
            auto_friend = config["AutoFriend"].getboolean("AutoFriend", fallback=False)
        
        if auto_friend:
            teams = self.teams()
            players = teams["red"] + teams["blue"]
            self.conditional_befriend(players, minqlbot.CHAT_CHANNEL, self.game().short_type)
         
    def cmd_inviteall(self, player, msg, channel):
        self.inviteall()

    def cmd_befriend(self, player, msg, channel):
        if len(msg) < 2:
            return minqlbot.RET_USAGE
      
        self.befriend(msg[1])
        
    def inviteall(self):
        minqlbot.console_command("inviteall")
        
    def befriend(self, name):
        minqlbot.console_command("addfriend {}".format(name))

    def conditional_befriend(self, players, channel, short_game_type):
        config = minqlbot.get_config()
        if "AutoFriend" in config and "AutoFriendMinimumRating" in config["AutoFriend"]:
            try:
                minimum_rating = int(config["AutoFriend"]["AutoFriendMinimumRating"])
            except ValueError:
                minimum_rating = 0
                
        if minimum_rating > 0:
            balance = self.plugins["balance"]
            not_cached = balance.not_cached(short_game_type, players)
            if not_cached:
                with balance.rlock:
                    for lookup in balance.lookups:
                        for n in balance.lookups[lookup][1]:
                            if n in not_cached:
                                not_cached.remove(n)
                    if not_cached:
                        balance.fetch_player_ratings(not_cached, channel, short_game_type, use_local=False, use_aliases=False)
                    if (self.conditional_befriend, (players, channel, short_game_type)) not in balance.pending:
                        balance.pending.append((self.conditional_befriend, (players, channel, short_game_type)))
                    return

            for player in players:
                if balance.cache[player.clean_name.lower()][short_game_type]["elo"] >= minimum_rating:
                    self.befriend(player.clean_name.lower())
        else:
            for player in players:
                self.befriend(player.clean_name.lower())
                
                