# test plugin
from bot.pluginDespatch import Plugin
import re
import logging
from logos.settings import LOGGING
logger = logging.getLogger(__name__)
logging.config.dictConfig(LOGGING)

class MyBotPlugin(Plugin):
    def __init__(self, *args, **kwargs):
        Plugin.__init__(self, *args, **kwargs)
        self.conversation = []
    
    def privmsg(self, user, channel, message):
        # Append the last 10 messages into the conversation and delete
        # the other older ones
        self.conversation.append((user, channel, message))
        # keep only the last 10 items in the list
        self.conversation = self.conversation[-10:]

    def command(self, nick, user, chan, orig_msg, msg, act):
        logger.debug("command: " + str((nick, user, chan, orig_msg, msg, act)))
        # if !nicks is typed print all nicks in room into channel
        nicks_mch = re.match('nicks', msg)
        if nicks_mch:
            nicks = self.get_room_nicks(chan)
            self.say(chan, "Nicks in room are " + ", ".join(nicks))

        # if !demo is typed print some messages into room
        demo_mch = re.match('demo', msg)
        if demo_mch:
            self.say(chan, "Elementary my dear Watson")
            self.describe(chan, "shakes its chains")
            self.notice(nick, "Now is the time for all good men...")
            
        # if !convo is typed print the conversation list
        convo_mch = re.match('convo', msg)
        if convo_mch:
            for u, c, m in self.conversation:
                self.say(chan, "%s said %s on %s" % (u,m,c))

        # If !timer is typed then a message is displayed after 5 seconds
        timer_mch = re.match('timer', msg)
        if timer_mch:
            self.reactor.callLater(5, self.timer_expired, chan)
            self.say(chan, "The timer will expire in 5 seconds")
            
        kick_mch = re.match('kick me', msg)
        if kick_mch and chan[0] == '#':
            self.kick(chan, nick, 'Well, you asked ;)')
        
        """
        self.mode( chan, set, modes, limit = None, user = None, mask = None):
        Demonstration of changeing the modes on a user or channel.
        
        Explanation of parameters below:
        
        The {limit}, {user}, and {mask} parameters are mutually exclusive.

        chan: The name of the channel to operate on.
        set: True to give the user or channel permissions and False to
            remove them.
        modes: The mode flags to set on the user or channel.
        limit: In conjuction with the {'l'} mode flag, limits the
             number of users on the channel.
        user: The user to change the mode on.
        mask: In conjuction with the {'b'} mode flag, sets a mask of
            users to be banned from the channel.
        """ 
                     
        opme_mch = re.match('op me', msg)
        if opme_mch:
            # using True is the same as +o
            self.mode(chan, True, "o", user = nick)

        deopme_mch = re.match('deop me', msg)
        if deopme_mch:
            # using False is the same as -o
            self.mode(chan, False, "o", user = nick)
                    
    def timer_expired(self, chan):
        self.say(chan, "The timer has expired after 5 seconds")
        
    def joined(self, channel):
        self.say(channel, "I, Logos, have arrived")

    def userRenamed(self, old, new):
        self.notice(new, "You changed your nick from %s to %s" % (old, new))

    def userJoined(self, user, channel):
        self.say(channel, "%s has just joined %s" % (user,channel))

    def userLeft(self, user, channel):
        self.say(channel, "%s has just left %s" % (user,channel))

    def userQuit(self, user, quitMessage):
        # The control room or engine room is often the room designated for notices
        # and or messages if no other room is specified
        self.say(self.control_room, "%s has just quit with message  %s" % (user,quitMessage))