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

"""Commands to unload and load all essential plugins at once
 - "pause" bot.

Unloads automatically all non-essential plugins when bot tries
to perform command that requires op rights on server when bot
doesn't have such rights.

!restart - restart bot (and load plugins listed in config file)
!plugins - display list of plugins that are currently loaded

"""

import minqlbot
import traceback

__version__ = '1.0.0'
    
class unloadall(minqlbot.Plugin):
    EXCEPTION_LIST = ["plugin_manager", "autoconnect", "unloadall", 
                      "permission"]
    NO_PLUGINS_MSG = \
        "^1WARNING: ^7Bot plugins are ^6disabled^7."
    AUTO_UNLOADED_MSG = \
        "^7They were unloaded automatically as bot didn't have op permission."
    LOAD_HELP_MSG = \
        "^7You can load all plugins with command ^6!loadall^2."

    PERMISSION_LOAD = 5
    PERMISSION_RESTART = 5
    PERMISSION_PLUGINS = 0
        
    def __init__(self):
        super().__init__()
        self.add_hook("player_connect", self.handle_player_connect)
        self.add_hook("console", self.handle_console)        
        self.add_command("unloadall", self.cmd_unloadall, self.PERMISSION_LOAD)
        self.add_command("loadall", self.cmd_loadall, self.PERMISSION_LOAD)
        self.add_command("plugins", self.cmd_plugins, self.PERMISSION_PLUGINS)
        self.add_command("restart", self.cmd_restart, self.PERMISSION_RESTART)
        
        self.unloaded = []
        self.auto_unloaded = False
        
    def handle_player_connect(self, player):
        if len(self.unloaded) != 0:
            self.delay(15, lambda: player.tell(self.NO_PLUGINS_MSG)) 
            if self.auto_unloaded:
                self.delay(15.5, lambda: player.tell(self.AUTO_UNLOADED_MSG)) 
            if self.has_permission(player.clean_name.lower(), self.PERMISSION_LOAD):
                self.delay(16, lambda: player.tell(self.LOAD_HELP_MSG)) 
        
    def handle_console(self, cmd):
        if len(self.unloaded) == 0:
            if ("You do not have the privileges " 
                "required to use this command") in cmd:
                self.cmd_unloadall(None, [], minqlbot.CHAT_CHANNEL)
                self.auto_unloaded = True            
                self.msg("^1WARNING: ^7Bot plugins were unloaded "
                         "because bot doesn't have op rigths.")

    def cmd_plugins(self, player, msg, channel):
        reply = "^7Currently loaded plugins: ^6"
        reply += "^7, ^6".join(self.plugins)
        channel.reply(reply)

    def cmd_restart(self, player, msg, channel):
        minqlbot.console_command("bot restart")
        channel.reply("^7Restarted.")
            
    def cmd_unloadall(self, player, msg, channel):
        if len(self.unloaded) != 0:
            channel.reply("^7Plugins are already unloaded.")
            return
        if "plugin_manager" in self.plugins:
            pm = self.plugins["plugin_manager"]
            
            self.unloaded = []
            
            errors = 0
            
            for plugin in self.plugins:
                if plugin in self.EXCEPTION_LIST:
                    continue
                else:
                    try:
                        pm.cmd_unload(None, 
                                      ["", plugin], 
                                      minqlbot.CONSOLE_CHANNEL)
                        self.unloaded.append(plugin)
                    except:
                        e = traceback.format_exc().rstrip("\n")
                        for line in e.split("\n"):
                            self.debug(line)
                        errors += 1

            channel.reply(
                "^7Unloaded ^6{}^7 plugins, encountered ^6{}^7 errors."
                .format(len(self.unloaded)-errors, errors))
                        
                        
        
    def cmd_loadall(self, player, msg, channel):
        if "plugin_manager" in self.plugins:
            pm = self.plugins["plugin_manager"]

            self.auto_unloaded = False            
            errors = 0
            loaded = 0
            
            for plugin in self.unloaded:
                if plugin in self.EXCEPTION_LIST:
                    continue
                else:
                    try:
                        pm.cmd_load(None, 
                                    ["", plugin], 
                                    minqlbot.CONSOLE_CHANNEL)
                        loaded += 1
                    except:
                        self.msg("^1Ingoring error.")      
                        e = traceback.format_exc().rstrip("\n")
                        for line in e.split("\n"):
                            self.debug(line)                        
                        errors += 1
            
            self.unloaded = []
            channel.reply("^7Loaded ^6{}^7 plugins, encountered ^6{}^7 errors."
                          .format(loaded-errors, errors))
