import logging
import time

from telegram import ParseMode
from telegram.error import *
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from store import MasterSettings, InMemoryStore

logging.basicConfig(
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
    level=logging.INFO)


class SpyBot(object):
    """ A Telegram bot that listens to all text messages in groups where he is
    a member and forwards these messages to the specified channel."""

    # A delay between forwards of a message from a group to all subscribers.
    # Required to avoid hitting Telegram message limits. More details at
    # https://core.telegram.org/bots/faq#my-bot-is-hitting-limits-how-do-i-avoid-this
    _FORWARD_DELAY_SEC = 0.1  # 100ms

    # Commands
    _START_CMD = 'start'
    _HELP_CMD = 'help'
    _SPY_CMD = 'spy'
    _DISMISS_CMD = 'dismiss'
    _REPORT_HERE_CMD = 'report_here'

    _HELP = """
Greetings, Master! I am SpyBot. I can help you to track what people are \
talking about in all groups where I am a member. Here is how to control me:

 * Whenever you add me to a chat or group, I will automatically start spying \
on it.
 * You can use a /{spy} command in a chat to explicitly order me to start \
watching this chat or group.
 * Use a /{dismiss} command in a chat to order me to stop watching this \
group or chat.
 * If you want to change the destination where my reports are getting sent, \
issue a /{report_here} command in the new destination chat.

Easy, isn't it? Try it now. I'm awaiting your orders.
    """.format(start=_START_CMD,
               spy=_SPY_CMD,
               dismiss=_DISMISS_CMD,
               report_here=_REPORT_HERE_CMD)

    def __init__(self, token, store=InMemoryStore()):
        """ Creates a new instance of SpyBot.

        Arguments:
            token (:obj:`str`): a bot token issued by BotFather
            store (:obj:`bot.store.AbstractStore`): a type of a persistent
                store to use for the bot. Defaults to an in-memory store.
        """
        self._log = logging.getLogger(SpyBot.__name__)
        self._store = store
        self._updater = Updater(token=token)
        self._dispatcher = self._updater.dispatcher
        self._add_handlers()
        self._dispatcher.add_error_handler(self._error)

    def run(self):
        self._log.info("Starting the SpyBot...")
        self._updater.start_polling()
        self._updater.idle()

    def _add_handlers(self):
        """ Add Telegram updates handlers.

        The order of handlers is important. The first matching handler will be
        used for processing the update.
        """
        # Command handlers
        self._dispatcher.add_handler(CommandHandler(
            command=SpyBot._START_CMD,
            callback=self._start_cmd
        ))
        self._dispatcher.add_handler(CommandHandler(
            command=SpyBot._HELP_CMD,
            callback=self._help_cmd
        ))
        self._dispatcher.add_handler(CommandHandler(
            command=SpyBot._SPY_CMD,
            callback=self._spy_cmd
        ))
        self._dispatcher.add_handler(CommandHandler(
            command=SpyBot._DISMISS_CMD,
            callback=self._dismiss_cmd
        ))
        self._dispatcher.add_handler(CommandHandler(
            command=SpyBot._REPORT_HERE_CMD,
            callback=self._report_here_cmd
        ))

        # Groups status updates handler
        status_update_filters = Filters.status_update.new_chat_members | \
            Filters.status_update.left_chat_member
        self._dispatcher.add_handler(MessageHandler(
            filters=status_update_filters,
            callback=self._status_update
        ))

        # Groups text messages handler
        self._dispatcher.add_handler(MessageHandler(
            filters=Filters.text & Filters.group,
            callback=self._forward
        ))

    def _start_cmd(self, bot, update):
        """ Handle /start command.

        Arguments:
            bot (:obj:`telegram.Bot`): An instance of the SpyBot
            update (:obj:`telegram.Update`): An update from the server
        """
        # Register a user that have sent the command as a new Master
        master_settings = MasterSettings(update.effective_user.id,
                                         update.effective_chat.id)
        self._store.save_or_update_master(master_settings)

        update.message.reply_text(
            'Yeess, Master? Add me to the groups you want me to spy on, '
            'and I shall let you know their plans at once!')

    def _help_cmd(self, bot, update):
        """ Handle /help command.

        Arguments:
            bot (:obj:`telegram.Bot`): An instance of the SpyBot
            update (:obj:`telegram.Update`): An update from the server
        """
        update.message.reply_text(SpyBot._HELP)

    def _spy_cmd(self, bot, update):
        """ Handle /spy command.

        Arguments:
            bot (:obj:`telegram.Bot`): An instance of the SpyBot
            update (:obj:`telegram.Update`): An update from the server
        """
        sender_id = update.effective_user.id
        chat_id = update.effective_chat.id

        # Was the message sent by a bot's Master?
        master_settings = self._store.get_master(sender_id)
        if master_settings and chat_id != master_settings.report_chat_id:
            # Subscribe the Master to this chat
            self._store.subscribe(sender_id, chat_id)

            self._log.info(
                "Watching chat '%s' (%s) for user '%s' (%s)",
                update.effective_chat.title or 'N/A', chat_id,
                update.effective_user.username or 'N/A', sender_id)

            # Reply
            update.message.reply_text(
                'As you wish, Master! I will spy on this group for you!')

    def _dismiss_cmd(self, bot, update):
        """ Handle /dismiss command.

        Arguments:
            bot (:obj:`telegram.Bot`): An instance of the SpyBot
            update (:obj:`telegram.Update`): An update from the server
        """
        sender_id = update.effective_user.id
        chat_id = update.effective_chat.id

        master_settings = self._store.get_master(sender_id)
        if master_settings and chat_id != master_settings.report_chat_id:
            # Unsubscribe the Master from this chat
            self._store.unsubscribe(chat_id, master_id=sender_id)

            self._log.info(
                "Stopped watching chat '%s' (%s) for user '%s' (%s)",
                update.effective_chat.title or 'N/A', chat_id,
                update.effective_user.username or 'N/A', sender_id)

            # Reply
            update.message.reply_text(
                'As you wish, Master! I will leave this group immediately!')

    def _report_here_cmd(self, bot, update):
        """ Handle /report_here command.

        Arguments:
            bot (:obj:`telegram.Bot`): An instance of the SpyBot
            update (:obj:`telegram.Update`): An update from the server
        """
        sender_id = update.effective_user.id
        chat_id = update.effective_chat.id

        master_settings = self._store.get_master(sender_id)
        if master_settings:
            # Update the report chat ID
            new_master_settings = MasterSettings(sender_id, chat_id)
            self._store.save_or_update_master(new_master_settings)

            self._log.info(
                "Sending reports for user '%s' (%s) to chat '%s' (%s)",
                update.effective_user.username or 'N/A', sender_id,
                update.effective_chat.title or 'N/A', chat_id)

            # Reply
            update.message.reply_text(
                'Sure, Master, I will report my findings here.')

    def _forward(self, bot, update):
        """ Forward spied message to all Masters subscribed on this chat.

        Arguments:
            bot (:obj:`telegram.Bot`): An instance of the SpyBot
            update (:obj:`telegram.Update`): An update from the server
        """
        from_chat_id = update.effective_chat.id
        forwarded_message = self._create_forwarded_message(update)

        subscribers = self._store.get_subscribers(from_chat_id)
        for subscriber in subscribers:
            chat_id = subscriber.report_chat_id

            try:
                bot.send_message(chat_id, forwarded_message,
                                 parse_mode=ParseMode.MARKDOWN)

            except ChatMigrated as err:
                # Id of the chat with the Master has changed
                self._log.warning("Chat ID changed from %s to %s",
                                  chat_id, err.new_chat_id)
                # Update Master settings with the new chat ID
                master_settings = MasterSettings(subscriber.master_id,
                                                 err.new_chat_id)
                self._store.save_or_update_master(master_settings)
                # Retry forwarding message
                bot.send_message(chat_id, forwarded_message)

            except Unauthorized:
                # The bot was removed or banned in the chat
                logging.exception("The bot was removed or banned in chat %s",
                                  chat_id)
                # Remove the Master
                self._store.remove_master(subscriber.master_id)

            except NetworkError:
                # A network error has occurred
                self._log.exception(
                    "A network error has occurred when forwarding message "
                    "'%s' to chat %s", update.message.text, chat_id)
                # Retry forwarding message
                bot.send_message(chat_id, forwarded_message)

            # Sleep after sending a message to a chat in order to avoid
            # hitting Telegram message limits.
            time.sleep(SpyBot._FORWARD_DELAY_SEC)

    def _status_update(self, bot, update):
        """ Watch for groups status updates.

        Arguments:
            bot (:obj:`telegram.Bot`): An instance of the SpyBot
            update (:obj:`telegram.Update`): An update from the server
        """
        message = update.message
        chat_id = update.effective_chat.id
        sender_id = update.effective_user.id

        # Check new chat members
        for member in message.new_chat_members:
            # Check if the bot has joined the chat by invitation
            # from its Master
            bot_invited_by_master = member.id == bot.id and \
                                    sender_id and \
                                    self._store.get_master(sender_id)
            if bot_invited_by_master:
                self._store.subscribe(sender_id, chat_id)

                self._log.info(
                    "Invited to chat '%s' (%s) by user '%s' (%s)",
                    update.effective_chat.title or 'N/A', chat_id,
                    update.effective_user.username or 'N/A', sender_id)

        # Check if the bot has left the group
        if message.left_chat_member and message.left_chat_member.id == bot.id:
            self._store.unsubscribe(chat_id)

            self._log.info(
                "Left from chat '%s' (%s)",
                update.effective_chat.title or 'N/A', chat_id)

    def _error(self, bot, update, error):
        """ Handle uncaught errors.

        Arguments:
            bot (:obj:`telegram.Bot`): An instance of the SpyBot
            update (:obj:`telegram.Update`): An update from the server
            error (:obj:`telegram.TelegramError`): An error object
        """
        message = update.message
        error_context = {
            'chat_id': message.chat_id,
            'group': message.chat.title or message.chat.username or 'Unknown',
            'text': message.text,
            'error': error.message
        }

        if isinstance(error, Unauthorized):
            self._log.error("Telegram returned unauthorized error",
                            extra=error_context)
        elif isinstance(error, BadRequest):
            self._log.error("Telegram returned bad request error",
                            extra=error_context)
        elif isinstance(error, TimedOut):
            self._log.error("A call to Telegram API timed out",
                            extra=error_context)
        elif isinstance(error, NetworkError):
            self._log.error("A network error occurred", extra=error_context)
        elif isinstance(error, ChatMigrated):
            self._log.error("Telegram chat migrated to the new ID %s",
                            error.new_chat_id, extra=error_context)
        else:
            self._log.error("Telegram returned generic error",
                            extra=error_context)

    def _create_forwarded_message(self, update):
        """ Compose a message that will be forwarded to all subscribers.

        Arguments:
            update (:obj:`telegram.Update`): an update from the server

        Return:
            :obj:`str`: A message text to forward
        """
        from_chat_title = update.effective_chat.title or 'Untitled'
        from_chat_username = update.effective_chat.username

        # Use a reference to a chat whenever possible,
        # otherwise just show chat name in italic
        from_chat_ref = '@' + from_chat_username if from_chat_username \
            else '_{}_'.format(from_chat_title)

        from_user_id = update.effective_user.id
        from_user_name = update.effective_user.first_name

        # Show full user name whenever possible
        if update.effective_user.last_name:
            from_user_name += ' ' + update.effective_user.last_name

        # Show a link to a user profile
        from_user_link = "[{user_name}](tg://user?id={user_id})"\
            .format(user_name=from_user_name,
                    user_id=from_user_id)

        return "{user} @ {chat}:\n{text}".format(user=from_user_link,
                                                 chat=from_chat_ref,
                                                 text=update.message.text)
