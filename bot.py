import logbook
import os
import sys

from dotenv import load_dotenv
from datetime import timedelta
from logbook import Logger, StreamHandler
from logbook.compat import redirect_logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters
from telegram.ext.dispatcher import run_async
from telegram.parsemode import ParseMode

from group_defender import *

load_dotenv()
APP_URL = os.environ.get("APP_URL")
PORT = int(os.environ.get('PORT', '8443'))
TELE_TOKEN = os.environ.get('TELE_TOKEN_BETA', os.environ.get('TELE_TOKEN'))
DEV_TELE_ID = int(os.environ.get('DEV_TELE_ID'))
GCP_KEY_FILE = os.environ.get('GCP_KEY_FILE')
GCP_CRED = os.environ.get('GCP_CRED')

if GCP_CRED is not None:
    with open(GCP_KEY_FILE, 'w') as f:
        f.write(GCP_CRED)


def main():
    # Setup logging
    redirect_logging()
    logbook.set_datetime_format('local')
    format_string = '[{record.time:%Y-%m-%d %H:%M:%S}] {record.level_name}: {record.message}'
    StreamHandler(sys.stdout, format_string=format_string, level='INFO').push_application()
    log = Logger()

    # Create the EventHandler and pass it your bot's token.
    updater = Updater(
        TELE_TOKEN, use_context=True, request_kwargs={'connect_timeout': TIMEOUT, 'read_timeout': TIMEOUT})

    job_queue = updater.job_queue
    job_queue.run_repeating(delete_expired_msg, timedelta(days=MSG_LIFETIME), 0)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start_msg))
    dispatcher.add_handler(CommandHandler("help", help_msg))
    dispatcher.add_handler(CommandHandler("donate", send_payment_options))
    dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, greet_group))
    dispatcher.add_handler(MessageHandler(
        (Filters.audio | Filters.document | Filters.photo | Filters.video), process_file))
    dispatcher.add_handler(MessageHandler(Filters.entity(MessageEntity.URL), check_url))
    dispatcher.add_handler(CallbackQueryHandler(process_callback_query))
    dispatcher.add_handler(feedback_cov_handler())
    dispatcher.add_handler(CommandHandler("send", send, Filters.user(DEV_TELE_ID), pass_args=True))

    # log all errors
    dispatcher.add_error_handler(error_callback)

    # Start the Bot
    if APP_URL:
        updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TELE_TOKEN)
        updater.bot.set_webhook(APP_URL + TELE_TOKEN)
        log.notice('Bot started webhook')
    else:
        updater.start_polling()
        log.notice('Bot started polling')

    # Run the bot until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


def start_msg(update, _):
    """
    Send start message
    Args:
        update: the update object
        _: unused variable

    Returns:
        None
    """
    update.message.reply_text(
        'Welcome to Group Defender!\n\n*Features*\n'
        '- Filter files and links that may contain virus or malwares\n'
        '- Filter photos and links of photos that are NSFW\n\n'
        'Type /help to see how to use Group Defender.', parse_mode=ParseMode.MARKDOWN)


@run_async
def help_msg(update, _):
    """
    Send help message
    Args:
        update: the update object
        _: unused variable

    Returns:
        None
    """
    keyboard = [[InlineKeyboardButton('Join Channel', f'https://t.me/grpdefbotdev'),
                 InlineKeyboardButton('Support Group Defender', callback_data=PAYMENT)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        'If you\'re just chatting with me, simply send me a photo, a file or a link and '
        'I\'ll tell you if it safe.\n\n'
        'If you want me to defend your group, add me into your group and set me as an admin. '
        'I\'ll filter all the unsafe content.', reply_markup=reply_markup)


@run_async
def process_callback_query(update, context):
    query = update.callback_query
    if query.data == PAYMENT:
        send_payment_options(update, context, query.from_user.id)
    else:
        process_msg(update, context)


# Greet when bot is added to group and asks for bot admin
@run_async
def greet_group(update, context):
    """
    Send a greeting message when the bot is added to a group
    Args:
        update: the update object
        context: the context object

    Returns:
        None
    """
    for user in update.message.new_chat_members:
        if user.id == context.bot.id:
            context.bot.send_message(
                update.message.chat.id,
                'Hello everyone! I am Group Defender. Set me as one of the admins so that '
                'I can start defending your group.')


def send(update, context):
    """
    Send a message to a user
    Args:
        update: the update object
        context: the context object

    Returns:
        None
    """
    tele_id = int(context.args[0])
    message = ' '.join(context.args[1:])

    try:
        context.bot.send_message(tele_id, message)
    except Exception as e:
        log = Logger()
        log.error(e)
        update.message.reply_text(DEV_TELE_ID, 'Failed to send message')


def error_callback(update, context):
    log = Logger()
    log.error(f'Update "{update}" caused error "{context.error}"')


if __name__ == "__main__":
    main()
