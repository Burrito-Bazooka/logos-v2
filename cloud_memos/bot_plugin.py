# test plugin
from bot.pluginDespatch import Plugin
import re
from datetime import datetime
import pytz
from django.contrib.auth.models import User

import logging
from logos.settings import LOGGING
logger = logging.getLogger(__name__)
logging.config.dictConfig(LOGGING)

from cloud_memos.models import Memo, Folder
from bot.logos_decorators import login_required

READ_SIZE = 250
class MemosPlugin(Plugin):
    plugin = ('memo', 'Cloud Memos')
    
    def __init__(self, *args, **kwargs):
        # Plugin.__init__(self, *args, **kwargs)
        super(MemosPlugin, self).__init__(*args, **kwargs)

        self.commands = ((r'list$', self.list_memos, 'list all memos'),
                         (r'list unread$', self.list_unread_memos, 'list new memos'),
                         (r'list new$', self.list_unread_memos, 'list new memos'),
                         (r'send (?P<recipient>\S+) (?P<message>.*)$', self.send_memo, 'send new memos'),
                         (r'check$', self.check, 'check for unread memos'),
                         (r'read (?P<memo_id>\d+)', self.read, 'read a memo'),
                         (r'delete (?P<memo_id>\d+)', self.delete_memo, 'delete a memo'),
                         (r'folders', self.list_folders, 'List memo folders'),
                         )
        # self.user_memos = {}

    def update_user_memo_info(self, user=None, folder=None, memos = None):
        if not user: return
        userl = user.lower()
        if userl not in self.user_memos:
            self.user_memos[userl] = {}
        if folder:
            self.user_memos[userl].update({'folder':folder})
        else:
            self.user_memos[userl].update({'folder':'inbox'})
        
        if memos:
            self.user_memos[userl].update({'memos':memos}) 
            
    def onSignal_login(self, source, data):
        nick = data['nick']
        
        # check for unread memos
        self._check(nick)
    
    def onSignal_logout(self, source, data):
        username = data['username']
        logger.debug("cloud memos: onSignal_logout " + repr(username))
        # del self.user_memos[username.lower()]       
    
    def _get_memos_obj(self, nick, folder_name='inbox'):
        username = self.get_auth().get_username(nick)
        user = User.objects.get(username = username)
        memos = Memo.objects.filter(folder__name=folder_name, 
            to_user__username = username.lower()).order_by('-id')
        return memos
    
    def _check(self, nick, always_respond = False):
        """  check for unread memos """

        username = self.get_auth().get_username(nick)
        user = User.objects.get(username=username)
        unread_memos = Memo.objects.filter(folder__name='inbox', 
            to_user = user, viewed_on__isnull = True).count()
        if unread_memos > 0:
            self.notice(nick,'You have %d unread memos!' % (unread_memos,))
        else:
            if always_respond:
                self.notice(nick,'You have no unread memos!')
        
    @login_required()
    def check(self, regex, chan, nick, **kwargs):
        """  check for unread memos """
        self._check(nick, always_respond = True)
        
            
    @login_required()
    def list_folders(self, regex, chan, nick, **kwargs):
        username = self.get_auth().get_username(nick)
        user = User.objects.get(username = username)
        for folder in Folder.objects.filter(user=user):
            self.notice(nick, str(folder.id)+" " +folder.name)
        self.notice(nick,'--end of list--')
    
    @login_required()
    def sel_folder(self, regex, chan, nick, **kwargs):
        username = self.get_auth().get_username(nick)
        user = User.objects.get(username = username)
        try:
            folder = Folder.objects.get(pk=regex.group('folder_id'),
                                        user = user)
            self._update_usernotes_hash(username, {'folder':folder})
            self.notice(nick, "--Folder successfully opened--")
        except Folder.DoesNotExist:
            self.notice(nick, "--Folder does not exist--")

    @login_required()
    def send_memo(self, regex, chan, nick, **kwargs):
        print ("Send Memo ...")
        recipient = regex.group('recipient')
        message = regex.group('message')
        username = self.get_auth().get_username(nick)
        user = User.objects.get(username__iexact = username)
        try:
            recip = User.objects.get(username__iexact = recipient)
        except User.DoesNotExist:
            self.notice(nick, "I do not know this user")
            return
        subject = message[:20] + "..."
        Memo.send_memo(user, recip, subject, message)
        self.notice(nick, "Memo sent")
        
    @login_required()
    def list_memos(self, regex, chan, nick, **kwargs):
        num_to_list = 10
        memos = self._get_memos_obj(nick)
                        
        if memos:
            for idx, memo in enumerate(memos):
                if not memo.viewed_on:
                    read_status = " **UNREAD** "
                else:
                    read_status = ""
                notification = str(idx) + " " + memo.from_user.username + read_status + " " + memo.subject
                self.notice(nick, notification )
                if idx >= num_to_list: break
                
        else:
            self.notice(nick, '** No memos found **')


    @login_required()
    def list_unread_memos(self, regex, chan, nick, **kwargs):
        num_to_list = 10
        memos = self._get_memos_obj(nick)
                        
        if memos:
            idx = 0
            for memo in memos:
                if not memo.viewed_on:
                    self.notice(nick, str(idx) + " " + memo.from_user.username + " " + memo.subject)
                idx += 1
                if idx >= num_to_list: break
                
        else:
            self.notice(nick, '** No memos found **')


    @login_required()
    def read(self, regex, chan, nick, **kwargs):
        logger.debug("read memos: %s %s " % (chan, nick))
        memos = self._get_memos_obj(nick)
        memo_id = int(regex.group('memo_id'))
        try:
            memo = memos[memo_id]
            text = re.sub(r'\n', ' ', memo.text)
            self.notice(nick, text)
            memo.viewed_on = datetime.now(pytz.utc)
            memo.save()
        except IndexError:
            self.notice(nick, "Memo not in list")

        

    @login_required()
    def delete_memo(self, regex, chan, nick, **kwargs):
        memos = self._get_memos_obj(nick)
        memo_id = int(regex.group('memo_id'))
        logger.debug("delete memo: %s %s %d" % (chan, nick, memo_id))

        try:
            memo = memos[memo_id]
            subject = memo.subject
            memo.delete()
            self.notice(nick, "Memo %d %s deleted" % (memo_id, subject))
        except IndexError:
            self.notice(nick, "Memo not in list")
