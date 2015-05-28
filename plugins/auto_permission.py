# Copyright (C) WalkerY (github)

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

"""Automatically grant players permission based on how many games they completed on server."""

import minqlbot

class auto_permission(minqlbot.Plugin):
    def __init__(self):
        super().__init__()
        if "permission" not in self.plugins:
            self.debug("Plugin Auto_permission requires Permission plugin.")
            minqlbot.unload_plugin("auto_permission")
        else:
            self.add_hook("player_connect", self.handle_player_connect)
        
    def handle_player_connect(self, player):    
        config = minqlbot.get_config()
        
        if "AutoPermission" in config and "GamesCompletedPermission1" in config["AutoPermission"]:
            level1_completed = int(config["AutoPermission"]["GamesCompletedPermission1"])
        else:
            level1_completed = 0
        
        if "AutoPermission" in config and "GamesCompletedPermission2" in config["AutoPermission"]:
            level2_completed = int(config["AutoPermission"]["GamesCompletedPermission2"])
        else:
            level2_completed = 0      
        
        if (level1_completed == 0 and level2_completed == 0):
            return None
        
        if "AutoPermission" in config and "ExceptionList" in config["AutoPermission"]:
            exception_list = [s.strip().lower() for s in config["AutoPermission"]["ExceptionList"].split(",")]
        else:
            exception_list = []
        
        permission = self.plugins["permission"]
        
        name = player.clean_name.lower()
        if name in exception_list:
            return None
        
        perm = permission.get_permission(name)
        if perm is not None and perm >= 2:
            return None
        
        c = self.db_query("SELECT * FROM Players WHERE name=?", name)
        row = c.fetchone()
        if not row:
            return None

        completed = row["games_completed"]
        if not completed:
            return None
             
        if (perm < 1 and completed > level1_completed):
            permission.set_permissions(name, 1, minqlbot.CONSOLE_CHANNEL)
            self.msg("^6{}^7's permission level has been automatically set to ^6{}^7 due to completion of more than ^6{}^7 games."
                .format(name, 1, level1_completed))
                
        if (perm < 2 and completed > level2_completed):
            permission.set_permissions(name, 2, minqlbot.CONSOLE_CHANNEL)
            self.msg("^6{}^7's permission level has been automatically set to ^6{}^7 due to completion of more than ^6{}^7 games."
                .format(name, 2, level2_completed))         
            