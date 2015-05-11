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

"""Lists all players that are on server and have permissions granted."""

import minqlbot

class listperms(minqlbot.Plugin):
    def __init__(self):
        super().__init__()
        if "permission" not in self.plugins:
            self.debug("Plugin Listperm requires Permission plugin.")
            minqlbot.unload_plugin("listperms")
        else:
            self.add_command(("getperms","listperms"), self.cmd_getperms, 0)
        
    def cmd_getperms(self, player, msg, channel):
        permission = self.plugins["permission"]
            
        teams = self.teams() 
        players = teams["red"] + teams["blue"] + teams["spectator"]
        sorted_list = sorted(players, key=lambda x: permission.get_permission(x.clean_name.lower()), reverse=True)
        sorted_string = ", ".join(["{} ^6{}^7".format(p.name, permission.get_permission(p.clean_name.lower())) for p in sorted_list if permission.get_permission(p.clean_name.lower()) > 0 and permission.get_permission(p.clean_name.lower()) < 999])
        channel.reply("^7Permission levels: " + sorted_string)        
        