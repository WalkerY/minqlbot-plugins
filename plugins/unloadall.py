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

"""Command to load and unload all non-critical plugins at once.  """

import minqlbot

__version__ = '0.1.0'
    
class unloadall(minqlbot.Plugin):
    EXCEPTION_LIST = ["plugin_manager", "autoconnect", "unloadall", "permission"]

    def __init__(self):
        super().__init__()
        self.add_command("unloadall", self.cmd_unloadall, 5)
        self.add_command("loadall", self.cmd_loadall, 5)
        
        self.unloaded = []
  
    def cmd_unloadall(self, player, msg, channel):
        if "plugin_manager" in self.plugins:
            pm = self.plugins["plugin_manager"]
            
            self.unloaded = []
            
            for plugin in self.plugins:
                if plugin in self.EXCEPTION_LIST:
                    continue
                else:
                    try:
                        pm.cmd_unload(None, ["", plugin], channel)
                        self.unloaded.append(plugin)
                    except:
                        self.msg("^7Ingorring erorrs.")
                        
                        
        
    def cmd_loadall(self, player, msg, channel):
        if "plugin_manager" in self.plugins:
            pm = self.plugins["plugin_manager"]
            
            for plugin in self.unloaded:
                if plugin in self.EXCEPTION_LIST:
                    continue
                else:
                    try:
                        pm.cmd_load(None, ["", plugin], channel)
                    except:
                        self.msg("^7Ingorring erorrs.")        
        