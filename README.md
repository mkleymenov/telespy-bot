# telespy-bot
A Telegram bot that forwards all text messages from groups where it's a member to a specified chat.

**NOTE**: This software provided "as is" without any warranty. The bot was created just for fun
and not ready for production. However you are welcome to use it as a starting point for your own
bots.

Powered by [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot).

## Commands
The bot supports the following commands:
- `/start` - Begins interaction between the user and the bot. The bot registers a user as a new
_Master_ and will use the chat where this command was posted for forwarded messages.
- `/help` - Display usage information
- `/spy` - A way to explicitly tell the bot to watch messages in the chat where the command was 
posted. This can be useful under certain circumstances (see use cases below).
- `/dismiss` - Tells the bot to stop spying on messages in the channel where the command was posted.
- `/report_here` - Tells the bot to report all his findings to the group where the command was posted.

## Usage

Start your interaction with the both with a `/start` command, as usual. The bot will register you as
a new user and will use this chat as a default destination for spied messages from other channels. If
you want to change the default destination chat, send `/report_here` command to the bot from the chat
or group that should be the new destination.

In order to start watching messages of a Telegram chat or group, the bot should be added there as a
member. If you (i.e. the _Master_) add the bot to a group yourself, the bot will start watching
messages in the group automatically. If, however, you do not have permissions to add new members to a
group, you can still ask group administration to do that for you, and then issue a `/spy` command in
the group chat, to explicitly tell the bot to watch this group.

You can tell the bot to stop watching a particular group at any time by sending a `/dismiss` command
in the group chat. 