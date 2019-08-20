import logbook
import os
import re
import sys

from dotenv import load_dotenv
from datetime import timedelta
from logbook import Logger, StreamHandler
from logbook.compat import redirect_logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity, Chat
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters, PreCheckoutQueryHandler
from telegram.ext.dispatcher import run_async
from telegram.parsemode import ParseMode

from group_defender import *

load_dotenv()
APP_URL = os.environ.get('APP_URL')
PORT = int(os.environ.get('PORT', '8443'))
TELE_TOKEN = os.environ.get('TELE_TOKEN_BETA', os.environ.get('TELE_TOKEN'))
DEV_TELE_ID = int(os.environ.get('DEV_TELE_ID', 0))
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')

if PROJECT_ID is not None:
    TELE_TOKEN, DEV_TELE_ID = get_settings(['TELE_TOKEN', 'DEV_TELE_ID'])
    APP_URL = f'https://{PROJECT_ID}.appspot.com/'


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

    # Setup job
    job_queue = updater.job_queue
    job_queue.run_repeating(delete_expired_msg, timedelta(days=MSG_LIFETIME), 0)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Commands handlers
    dispatcher.add_handler(CommandHandler('start', start_msg))
    dispatcher.add_handler(CommandHandler('help', help_msg))
    dispatcher.add_handler(CommandHandler('donate', send_payment_options))
    dispatcher.add_handler(CommandHandler('send', send, Filters.user(DEV_TELE_ID)))

    # Callback query handler
    dispatcher.add_handler(CallbackQueryHandler(process_callback_query))

    # Group Defender handlers
    dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, greet_group))
    dispatcher.add_handler(MessageHandler(
        (Filters.audio | Filters.document | Filters.photo | Filters.video), process_file))
    dispatcher.add_handler(MessageHandler(Filters.entity(MessageEntity.URL), check_url))

    # Payment handlers
    dispatcher.add_handler(MessageHandler(Filters.regex(
        rf'^({re.escape(PAYMENT_THANKS)}|{re.escape(PAYMENT_COFFEE)}|{re.escape(PAYMENT_BEER)}|'
        rf'{re.escape(PAYMENT_MEAL)})$'), send_payment_invoice))
    dispatcher.add_handler(payment_cov_handler())
    dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_check))
    dispatcher.add_handler(MessageHandler(Filters.successful_payment, successful_payment))

    # Feedback handler
    dispatcher.add_handler(feedback_cov_handler())

    # Log all errors
    dispatcher.add_error_handler(error_callback)

    # Start the Bot
    if APP_URL is not None:
        updater.start_webhook(listen='0.0.0.0', port=PORT, url_path=TELE_TOKEN)
        updater.bot.set_webhook(APP_URL + TELE_TOKEN)
        log.notice('Bot started webhook')
    else:
        updater.start_polling()
        log.notice('Bot started polling')

    # Run the bot until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


def start_msg(update, context):
    """
    Send start message
    Args:
        update: the update object
        context: the context object

    Returns:
        None
    """
    if update.message.chat.type in (Chat.GROUP, Chat.SUPERGROUP):
        update.message.reply_text('I\'ve PM you the start message.')

    context.bot.send_message(
        update.message.from_user.id,
        'Welcome to Group Defender!\n\n*Features*\n'
        '- Filter files and links that may contain virus or malwares\n'
        '- Filter photos and links of photos that are NSFW\n\n'
        'Type /help to see how to use Group Defender.', parse_mode=ParseMode.MARKDOWN)


@run_async
def help_msg(update, context):
    """
    Send help message
    Args:
        update: the update object
        context: the context object

    Returns:
        None
    """
    if update.message.chat.type in (Chat.GROUP, Chat.SUPERGROUP):
        update.message.reply_text('I\'ve PM you the help message.')

    keyboard = [[InlineKeyboardButton('Join Channel', f'https://t.me/grpdefbotdev')],
                [InlineKeyboardButton('Support Group Defender', callback_data=PAYMENT)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(
        update.message.from_user.id,
        'If you\'re just chatting with me, simply send me a photo, a file or a link and '
        'I\'ll tell you if it safe.\n\n'
        'If you want me to defend your group, add me into your group and set me as an admin. '
        'I\'ll filter all the unsafe content. When I removed a message, '
        'only group admins can undo or delete the action.', reply_markup=reply_markup)


@run_async
def process_callback_query(update, context):
    """
    Process callback query
    Args:
        update: the update object
        context: the context object

    Returns:
        None
    """
    query = update.callback_query
    if query.data == PAYMENT:
        send_payment_options(update, context, query.from_user.id)
    else:
        process_msg(update, context)


@run_async
def greet_group(update, context):
    """
    Send a greeting message when the bot is added into a group
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
        update.message.reply_text('Failed to send message')


def error_callback(update, context):
    """
    Log errors
    Args:
        update: the update object
        context: the context object

    Returns:
        None
    """
    log = Logger()
    log.error(f'Update "{update}" caused error "{context.error}"')


if __name__ == "__main__":
    main()
