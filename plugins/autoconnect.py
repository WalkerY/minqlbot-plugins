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

"""Plugin for unattended reconnecting and joining servers.

When bot disconnects from server this plugin will make it try 
reconnecting several times and if it fails it will try to join 
server that specified player has joined until successfull in 
joining this player or until manually moved to any server by any 
means. 

Also provides command to remotely move bot to a new server.

Internally plugin has two loops:
- "reconnect then join" automatic loop (called reconnect loop below)
- "join me" command loop (called join loop below)

Config.cfg snippet:
    [AutoConnect]
    ReconnectFallbackJoinName = WalkerY
When ReconnectFallbackJoinName is not configured, reconnect loop
won't proceed with joininig after maximum reconnect retries.
"""

import minqlbot
import threading

__version__ = '1.0.0'

# Parameters for reconnect loop
RECONNECT_RETRY_DELAY = 60
RECONNECT_JOIN_RETRY_DELAY = 60
# If joinme action takes RECONNECT_JOINME_TIMEOUT seconds we ignore 
# joinme_event lock and enter reconnect loop.
RECONNECT_JOINME_TIMEOUT = 600
# How many times we try to reconnect before trying to join.
RECONNECT_MAX_TRIES = 5
# How long to wait before starting reconnect loop after 'disconnect'
# event.
RECONNECT_LOOP_START_DELAY = 5

# Parameters for join loop.
JOINME_START_DELAY = 60
JOINME_RETRY_DELAY = 30
JOINME_TRIES = 4
         
         
class autoconnect(minqlbot.Plugin):
    def __init__(self):
        super().__init__()
        self.add_hook("unload", self.handle_unload)
        self.add_hook("bot_disconnect", self.handle_bot_disconnect)
        self.add_hook("bot_connect", self.handle_bot_connect)
        self.add_command(("joinme", "followme"), self.cmd_joinme, 5)

        # Shared variable used to announce unloading.
        self.unloading_lock = threading.RLock()
        self.unloading = False
        
        # Timer thread used to start reconnect loop.
        self.reconnect_loop_thread_lock = threading.RLock()
        self.reconnect_loop_thread = None
        
        # Shared variables, used for joinme action as repeated !joinme
        # commands can spawn multiple threads.
        self.following_lock = threading.RLock()
        self.following = False
        self.following_name = ""
        self.following_cleanname = ""
        
        # Event used to suspend reconnect loop while performing joinme
        # action. The idea is that reconnect loop will try to
        # reconnect/join if joinme action fails.
        self.joinme_event = threading.Event()
        self.joinme_event.set()
        
        # Needed to assure only one reconnect loop thread is operating
        # at a given time.
        self.reconnect_loop_lock = threading.Lock()
        
        # Thread used for 'sleeps' that are both blocking and 
        # interruptible on 'unload' and 'bot_connect' events.
        self.waiter_lock = threading.RLock()
        self.waiter_thread = None
        
        # Same as above, but used in joinme_thread's join loop, to 
        # avoid interlocking with reconnect loop
        self.waiter2_lock = threading.RLock()
        self.waiter2_thread = None
        
        
    def handle_unload(self):
        with self.unloading_lock:
            self.unloading = True
        
        # Immediately cancel all waiting in all Timer threads to
        # assure fast unload.
        self.cancel_timer_thread(self.waiter_lock, self.waiter_thread)
        self.cancel_timer_thread(self.waiter2_lock, self.waiter2_thread)
        self.cancel_timer_thread(self.reconnect_loop_thread_lock, 
                                 self.reconnect_loop_thread)

    def handle_bot_connect(self):
        # When we successfully connect we can cancel waiting in all
        # Timer threads so that they can proceed and immediately 
        # realize that bot is connected and in effect release quickly
        # locks accordingly.
        self.cancel_timer_thread(self.waiter_lock, self.waiter_thread)
        self.cancel_timer_thread(self.waiter2_lock, self.waiter2_thread)
        self.cancel_timer_thread(self.reconnect_loop_thread_lock,
                                 self.reconnect_loop_thread)
    
    def handle_bot_disconnect(self):
        if not self.is_unloading(): 
            self.auto_reconnect_loop_start()
    
    def cmd_joinme(self, player, msg, channel):
        """Waits some time to allow player to switch server and then
        joins this player.
        """
        # We cancel all waiting Timers in reconnect loop.
        self.cancel_timer_thread(self.waiter_lock, self.waiter_thread)
        
        # We call another thread to prevent waiting on locks in main
        # thread.
        threading.Thread(target = self.joinme_thread, 
                         args = (player, msg, channel)).start()
        
    def joinme_thread(self, player, msg, channel):
        with self.following_lock:
            following = self.following
            following_cleanname = self.following_cleanname
            following_name = self.following_name
            
        if not following:
            
            # As we are going to disconnect during join loop, we need
            # to assure reconnect loop won't trigger. At the same time,
            # it's nice to have a reconnect loop as a recovery if sth 
            # unexpected happens.
            self.joinme_event.clear()
            
            with self.following_lock:
                self.following = True
                following_name = self.following_name = player.name
                following_cleanname = \
                    self.following_cleanname = player.clean_name.lower()
                
            channel.reply("^7Sure {}^7! I will join you in {} seconds.".format
                         (following_name, JOINME_START_DELAY))
                
            # We choose non-default Timer thread to avoid interlocking
            # with delays in reconnect loop.
            self.delay_blocking(JOINME_START_DELAY, self.waiter2_lock)
                    
            # Try a few times to join player to give him more time and 
            # account for a class of potential issues.
            for n in range(1, JOINME_TRIES):
                if self.is_unloading():
                    break
                            
                self.join(JOINME_RETRY_DELAY, following_cleanname)
                    
                # Verify that we connected to server and that the 
                # player we followed is there.
                if self.is_joined(following_cleanname):
                    break
                
            with self.following_lock:
                self.following = False

            # We allow reconnect loop to proceed. It can be useful
            # if joins fail.
            self.joinme_event.set()
                
        else:
            if following_cleanname == player.clean_name.lower():
                channel.reply("^7I have been already set to follow you.")
            else:
                channel.reply(
                    "^7I am sorry, I have already promised to follow {}^7."
                    .format(following_name))
        
    def cancel_timer_thread(self, lock, timer):
        with lock:            
            if timer is not None:
                timer.cancel()
    
    def nop(self):
        return
        
    def delay_blocking(self, time_s, waiter_lock = None):
        """Blocks current thread for a given time in an interruptible 
        way and using specified lock.
        """
        if waiter_lock is not None:
            waiter_lock = self.waiter_lock
        
        # Shared global locks - only one delay_blocking allowed among
        # all threads using the same lock.
        with waiter_lock:
                # I dont use self.delay as it's not easily 
                # interruptible on unload and non-blocking, time.sleep
                # is blocking but not easily interruptible.
                waiter_thread = threading.Timer(time_s, function=self.nop)
                if waiter_lock is self.waiter_lock:
                    self.waiter_thread = waiter_thread
                elif waiter_lock is self.waiter2_lock:
                    self.waiter2_thread = waiter_thread
                else:
                    self.debug("Unexpected lock instance. "
                               "Raising ValueError exception...")
                    raise ValueError("Unexpected lock instance.")
                    
        waiter_thread.start()
        waiter_thread.join()
    
    def auto_reconnect_loop_start(self):
        if not self.is_unloading():
            with self.reconnect_loop_thread_lock:
                # wait to make sure we are fully disconnected TODO
                self.reconnect_loop_thread = \
                    threading.Timer(RECONNECT_LOOP_START_DELAY, 
                                    function=self.auto_reconnect_loop)
                self.reconnect_loop_thread.start()

    def is_unloading(self):
        """Checks if plugin received 'unload' event."""    
        with self.unloading_lock:
            unloading = self.unloading
        return unloading
        
    def is_connected(self):
        """Checks if bot is connected to game server."""        
        return (minqlbot.connection_status() == 8)
        
    def is_joined(self, clean_name):
        """Checks if we successfully joined specified player."""        
        if not self.is_connected():
            return False
        
        clean_name_lower = clean_name.lower()
        
        teams = self.teams()
        teams = teams["red"] + teams["blue"] + teams["spectator"]
        for player in teams:
            if player.clean_name.lower() == clean_name_lower:
                return True
                
        return False
        
    def join(self, delay, name):
        """Joins specified player with 'join' console command and waits
        specified time.  
        """
        self.debug("^7Trying to join {}...".format(name))
        minqlbot.console_command("join {}".format(name))
    
        if self.is_unloading():
            return False
        else:
            self.delay_blocking(delay)
            if self.is_unloading():
                return False
       
        return True
              
    def reconnect(self, delay):
        """Reconnects with 'reconnect' console command and waits
        specified time.
        """
        self.debug("^7Trying to reconnect...")
        minqlbot.console_command("reconnect")
        
        if self.is_unloading():
            return False
        else:
            self.delay_blocking(delay)
            if self.is_unloading():
                return False
                    
        return True
        
                
    def auto_reconnect_loop(self):
        """Main reconnect loop. We try to reconnect, after X tries 
        server is probably down so then we switch to trying to join 
        specified player in an infinite loop. Loop is terminated when 
        bot by any means connects to any server.
        """
        # Only one reconnect loop is allowed.
        with self.reconnect_loop_lock:
            join_name = ""
            
            config = minqlbot.get_config()
            if ("AutoConnect" in config and
                "ReconnectFallbackJoinName" in config["AutoConnect"]):
                join_name = config["AutoConnect"]["ReconnectFallbackJoinName"]

            tries = 1
            
            # Wait if joinme action is in progress, when join fails we
            # fallback to this reconnect loop.
            self.joinme_event.wait(RECONNECT_JOINME_TIMEOUT)
            
            while (not self.is_connected() and 
                   not self.is_unloading() and 
                   (tries <= RECONNECT_MAX_TRIES or join_name != "")):
                # First we try to reconnect.
                if tries <= RECONNECT_MAX_TRIES: 
                    self.reconnect(RECONNECT_RETRY_DELAY)

                # If reconnects failed we try to join specified player 
                # (we assume server is down). This makes bot more autonomous.
                elif join_name != "":
                    self.join(RECONNECT_JOIN_RETRY_DELAY, join_name)
                                
                if tries <= RECONNECT_MAX_TRIES:
                    tries += 1
                    