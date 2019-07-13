from telegram import ReplyKeyboardRemove
from telegram.ext import ConversationHandler
from telegram.ext.dispatcher import run_async


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
