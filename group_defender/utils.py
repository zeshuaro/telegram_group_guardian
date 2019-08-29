import secrets

from telegram import ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import ConversationHandler
from telegram.ext.dispatcher import run_async

from group_defender.constants import UNDO, SETTING, VALUE, PAYMENT
from group_defender.store import store_msg
from group_defender.store import datastore_client


def get_setting(name):
    return get_settings([name])[0]


def get_settings(names):
    values = []
    for name in names:
        key = datastore_client.key(SETTING, name)
        values.append(datastore_client.get(key)[VALUE])

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
    update.effective_message.reply_text('Operation cancelled.', reply_markup=ReplyKeyboardRemove())

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
    message = update.effective_message
    chat_id = message.chat_id
    msg_id = message.message_id
    store_msg(chat_id, msg_id, message.from_user.username, file_id, file_type,
              message.text)

    try:
        message.delete()
        keyboard = [[InlineKeyboardButton(text='Undo', callback_data=f'{UNDO},{msg_id}')]]

        if secrets.randbelow(2):
            keyboard.append([InlineKeyboardButton('Support Group Defender', callback_data=PAYMENT)])

        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(chat_id, text, reply_markup=reply_markup)
    except BadRequest:
        message.reply_text('I was not able to delete this unsafe message.\n\n'
                           'Go to group admin settings and ensure that "Delete Messages" is on for me.')
