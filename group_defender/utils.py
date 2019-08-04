from google.cloud import datastore
from telegram import ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import ConversationHandler
from telegram.ext.dispatcher import run_async

from group_defender.constants import UNDO, SETTING, VALUE
from group_defender.store import store_msg


def get_setting(name):
    return get_settings([name])[0]


def get_settings(names):
    client = datastore.Client()
    values = []

    for name in names:
        key = client.key(SETTING, name)
        values.append(client.get(key)[VALUE])

    return values


@run_async
def cancel(update, _):
    """
    Cancel operation for conversation fallback
    Args:
        update: the update object
        _:

    Returns:
        The variable indicating the conversation has ended
    """
    update.message.reply_text('Operation cancelled.', reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def filter_msg(update, context, file_id, file_type, text):
    """
    Delete and send new message
    Args:
        update: the update object
        context: the context object
        file_id: the int of the file ID
        file_type: the string of the file type
        text: the string of text to be sent

    Returns:
        None
    """
    chat_id = update.message.chat_id
    msg_id = update.message.message_id
    store_msg(chat_id, msg_id, update.message.from_user.username, file_id, file_type, update.message.text)

    try:
        update.message.delete()

        keyboard = [[InlineKeyboardButton(text='Undo', callback_data=f'{UNDO},{msg_id}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(chat_id, text, reply_markup=reply_markup)
    except BadRequest:
        update.message.reply_text('I was not able to delete this unsafe message.\n\n'
                                  'Go to group admin settings and ensure that "Delete Messages" is on for me.')
