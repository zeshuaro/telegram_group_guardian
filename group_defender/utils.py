from telegram import ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import ConversationHandler
from telegram.ext.dispatcher import run_async

from group_defender.constants import UNDO
from group_defender.store import store_msg


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
