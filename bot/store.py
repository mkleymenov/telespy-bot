from abc import ABCMeta, abstractmethod


class MasterSettings(object):
    """ A simple class for storing SpyBot's Masters settings. """

    def __init__(self, master_id, report_chat_id):
        """ Create new MasterSettings.

        Arguments:
            master_id (:obj:`int`): a Telegram user id of the bot's Master
            report_chat_id (:obj:`int`): an id of a Telegram chat to forward
                spied messaged to
        """
        self._master_id = master_id
        self._report_chat_id = report_chat_id

    @property
    def master_id(self):
        return self._master_id

    @property
    def report_chat_id(self):
        return self._report_chat_id

    @report_chat_id.setter
    def report_chat_id(self, new_report_chat_id):
        self._report_chat_id = new_report_chat_id

    def __str__(self):
        return 'MasterSettings({master_id}, {report_chat_id})' \
            .format(master_id=self._master_id,
                    report_chat_id=self.report_chat_id)

    def __eq__(self, other):
        return isinstance(other, MasterSettings) and \
               other.master_id == self._master_id

    def __hash__(self):
        return 31 * hash(self._master_id)


class AbstractStore:
    """ A base interface for SpyBot persistence layer. """
    __metaclass__ = ABCMeta

    @abstractmethod
    def save_or_update_master(self, master_settings):
        """ Register a new SpyBot's Master or update an existing one.

        Arguments:
            master_settings (:obj:`MasterSettings`): Master settings
        """
        pass

    @abstractmethod
    def get_master(self, master_id):
        """ Retrieve a Master by its Telegram user ID.

        Arguments:
            master_id (:obj:`int`): a Telegram ID of a Master user

        Return:
            :obj:`MasterSettings`: Master settings or ``None``
        """
        pass

    @abstractmethod
    def remove_master(self, master_id):
        """ Remove registered Master settings.

        Arguments:
            master_id (:obj:`int`): a Telegram ID of a Master user
        """
        pass

    @abstractmethod
    def subscribe(self, master_id, chat_id):
        """ Subscribe a specified Master to the specified chat.

        Arguments:
            master_id (:obj:`int`): a Telegram ID of a Master user
            chat_id (:obj:`int`): a Telegram chat ID
        """
        pass

    @abstractmethod
    def unsubscribe(self, chat_id, master_id=None):
        """ Remove subscription on the chat.

        Arguments:
            chat_id (:obj:`int`): a Telegram chat ID
            master_id (:obj:`int`): (Optional) a Master's Telegram user ID.
                If set, only the specified Master will be unsubscribed from
                the chat. Otherwise all subscriptions will be canceled.
        """
        pass

    @abstractmethod
    def get_subscribers(self, chat_id):
        """ Return a list of all subscribers on the specified chat.

        Arguments:
            chat_id (:obj:`int`): A Telegram chat ID

        Return:
            :obj:`list`: a list of ``MasterSettings``
        """


class InMemoryStore(AbstractStore):
    """ A simple in-memory implementation of the AbstractStore. """

    # A map of Master IDs to Master Settings
    _MASTERS = dict()
    # A map of Chat IDs to a collection of IDs of subscribed Masters
    _CHATS = dict()

    def save_or_update_master(self, master_settings):
        InMemoryStore._MASTERS[master_settings.master_id] = master_settings

    def get_master(self, master_id):
        return InMemoryStore._MASTERS.get(master_id, None)

    def remove_master(self, master_id):
        # Remove Master settings
        master_settings = InMemoryStore._MASTERS.pop(master_id, None)
        # Ensure consistency
        assert master_settings, "Master should be registered first"

        # Remove the Master from the list of subscribers
        for chat_id, subscribers in InMemoryStore._CHATS.iteritems():
            if master_settings in subscribers:
                # Remove master settings from the set
                subscribers -= {master_settings}
                # If a chat has no subscribers, remove the chat
                if not subscribers:
                    del InMemoryStore._CHATS[chat_id]

    def subscribe(self, master_id, chat_id):
        # Get Master settings
        master_settings = InMemoryStore._MASTERS.get(master_id, None)
        # Ensure consistency
        assert master_settings, "Master should be registered first"

        if chat_id in InMemoryStore._CHATS:
            # Add the Master to the list of subscribers
            InMemoryStore._CHATS[chat_id] |= {master_settings}
        else:
            # Create a new list of subscribers for this chat
            InMemoryStore._CHATS[chat_id] = {master_settings}

    def unsubscribe(self, chat_id, master_id=None):
        if not master_id:
            # Delete all subscribers of this chat
            subscribers = InMemoryStore._CHATS.pop(chat_id, None)
            # Ensure consistency
            assert subscribers, "Chat should be registered first"
        else:
            # Get Master settings
            master_settings = InMemoryStore._MASTERS.get(master_id, None)
            # Ensure consistency
            assert master_settings, "Master should be registered first"
            # Get chat subscribers
            subscribers = InMemoryStore._CHATS.get(chat_id, None)
            # Ensure consistency
            assert subscribers, "Chat should be registered first"
            # Remove the master from chat subscribers
            subscribers -= {master_settings}

    def get_subscribers(self, chat_id):
        if chat_id in InMemoryStore._CHATS:
            return list(InMemoryStore._CHATS[chat_id])
        else:
            return list()
