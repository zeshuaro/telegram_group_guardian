import logbook
import mimetypes
import os
import requests
import sys

from dotenv import load_dotenv
from datetime import datetime, timedelta
# from google.cloud import vision
from logbook import Logger, StreamHandler

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ChatMember, Chat, MessageEntity, ChatAction
from telegram.constants import *
from telegram.error import BadRequest
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
    logbook.set_datetime_format('local')
    format_string = '[{record.time:%Y-%m-%d %H:%M:%S}] {record.level_name}: {record.message}'
    StreamHandler(sys.stdout, format_string=format_string).push_application()
    log = Logger()

    # Create the EventHandler and pass it your bot's token.
    updater = Updater(
        TELE_TOKEN, use_context=True, request_kwargs={'connect_timeout': TIMEOUT, 'read_timeout': TIMEOUT})

    # job_queue = updater.job_queue
    # job_queue.run_repeating(delete_expired_msg, timedelta(days=MSG_LIFETIME), 0)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start_msg))
    dispatcher.add_handler(CommandHandler("help", help_msg))
    dispatcher.add_handler(CommandHandler("donate", send_payment_options))
    dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, greet_group))
    dispatcher.add_handler(MessageHandler((Filters.audio | Filters.document | Filters.photo | Filters.video), check_file))
    dispatcher.add_handler(MessageHandler(Filters.entity(MessageEntity.URL), check_url))
    dispatcher.add_handler(CallbackQueryHandler(inline_button_handler))
    dispatcher.add_handler(feedback_cov_handler())
    dispatcher.add_handler(CommandHandler("send", send, Filters.user(DEV_TELE_ID), pass_args=True))

    # log all errors
    dispatcher.add_error_handler(error_callback)

    # Start the Bot
    if APP_URL:
        updater.start_webhook(listen="0.0.0.0",
                              port=PORT,
                              url_path=TELE_TOKEN)
        updater.bot.set_webhook(APP_URL + TELE_TOKEN)
        log.notice('Bot started webhook')
    else:
        updater.start_polling()
        log.notice('Bot started polling')

    # Run the bot until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


# Delete expired message
def delete_expired_msg(bot, job):
    curr_datetime = datetime.now()
    with conn_db() as conn:
        with conn.cursor() as cur:
            cur.execute("delete from msg_info where expire < %s",  (curr_datetime,))


def start_msg(update, _):
    """
    Send start message
    Args:
        update: the update object
        _: unused variable

    Returns:
        None
    """
    text = "Welcome to Group Guardian!\n\n"
    text += "I can protect you and your group from files or links that may contain threats, and photos or urls of " \
            "photos that may contain adult, spoof, medical, violence or racy content.\n\n"
    text += "Type /help to see how to use me."

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
        'If you\'re just chatting with me, simply send me a photo, a file or a url and '
        'I\'ll tell you if it is safe or NSFW.\n\n'
        'If you want me to defend your group, add me into your group and set me as an admin. '
        'I\'ll filter all the unsafe content.', reply_markup=reply_markup)


@run_async
def process_callback_query(update, context):
    query = update.callback_query
    if query.data == PAYMENT:
        send_payment_options(update, context, query.from_user.id)


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


# Store message information on Google Datastore
def store_msg(chat_id, msg_id, user_name, file_id, file_type, msg_text):
    expire = datetime.now() + timedelta(days=MSG_LIFETIME)
    with conn_db() as conn:
        with conn.cursor() as cur:
            cur.execute("insert into msg_info values (%s, %s, %s, %s, %s, %s, %s)",
                        (chat_id, msg_id, user_name, file_id, file_type, msg_text, expire))


# Check for url
@run_async
def check_url(bot, update):
    # Check if bot in group and if bot is a group admin, if not, urls will not be checked
    if update.message.chat.type in (Chat.GROUP, Chat.SUPERGROUP) and \
            bot.get_chat_member(update.message.chat_id, bot.id).status != ChatMember.ADMINISTRATOR:
        update.message.reply_text("Please set me as a group admin so that I can start checking urls like this.")

        return

    update.message.chat.send_action(ChatAction.TYPING)
    chat_type = update.message.chat.type
    chat_id = update.message.chat_id
    msg_id = update.message.message_id
    user_name = update.message.from_user.first_name
    msg_text = update.message.text

    entities = update.message.parse_entities([MessageEntity.URL])
    urls = entities.values()
    reply_text = ""

    for url in urls:
        mime_type = mimetypes.guess_type(url)[0]
        if mime_type:
            response = requests.get(url)
            if response.status_code == 200:
                safe, text = is_malware_and_vision_safe(bot, update, url, "url", mime_type, len(response.content))
                reply_text += f"{text}\n\n"

                if not safe and chat_type in (Chat.GROUP, Chat.SUPERGROUP):
                    break
            else:
                if chat_type == Chat.PRIVATE:
                    reply_text += f"{url}\n⬆ I couldn't check it as I couldn't access it.\n\n"
        else:
            if not is_url_safe(url):
                # Delete message if it is a group chat
                if chat_type in (Chat.GROUP, Chat.SUPERGROUP):
                    store_msg(chat_id, msg_id, user_name, None, "url", msg_text)

                    text = f"I deleted a message that contains urls with threats (sent by {user_name})."
                    keyboard = [[InlineKeyboardButton(text="Undo", callback_data=f"undo,{msg_id}")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    update.message.delete()
                    bot.send_message(chat_id, text, reply_markup=reply_markup)
                    break
                else:
                    reply_text += f"{url}\n⬆ I think it contains threats, don't open it.\n\n"
            else:
                if chat_type == Chat.PRIVATE:
                    reply_text += f"{url}\n⬆ I think it is safe.\n\n"

    if chat_type == Chat.PRIVATE:
        update.message.reply_text(reply_text, quote=True, disable_web_page_preview=True)


# Check if url is safe
def is_url_safe(url):
    safe_url = True

    safe_browsing_url = "https://safebrowsing.googleapis.com/v4/threatMatches:find"
    headers = {"Content-Type": "application/json"}
    params = {"key": GOOGLE_TOKEN}
    json = {
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}]
        }
    }
    response = requests.post(url=safe_browsing_url, headers=headers, params=params, json=json)

    if response.status_code == 200:
        results = response.json()
        if "matches" in results and results["matches"]:
            safe_url = False

    return safe_url


# Handle inline button
@run_async
def inline_button_handler(bot, update):
    query = update.callback_query
    chat_id = query.message.chat_id
    user_id = query.from_user.id
    task, msg_id = query.data.split(",")
    msg_id = int(msg_id)

    if query.message.chat.type in (Chat.GROUP, Chat.SUPERGROUP) and \
            bot.get_chat_member(chat_id, user_id).status not in (ChatMember.ADMINISTRATOR, ChatMember.CREATOR):
        return

    if task == "undo":
        with conn_db() as conn:
            with conn.cursor() as cur:
                cur.execute("select user_name, file_id, file_type, msg_text from msg_info "
                            "where chat_id = %s and msg_id = %s", (chat_id, msg_id))
                row = cur.fetchone()

                if row:
                    user_name, file_id, file_type, msg_text = row
                    cur.execute("delete from msg_info where chat_id = %s and msg_id = %s", (chat_id, msg_id))

                    try:
                        query.message.delete()
                    except BadRequest:
                        return

                    keyboard = [[InlineKeyboardButton(text="Delete (No Undo)", callback_data="delete," + str(msg_id))]]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    if file_id:
                        if file_type == "img":
                            bot.send_photo(chat_id, file_id,
                                           caption=f"{user_name} sent this.",
                                           reply_markup=reply_markup)
                        elif file_type == "aud":
                            bot.send_audio(chat_id, file_id,
                                           caption=f"{user_name} sent this.",
                                           reply_markup=reply_markup)
                        elif file_type == "vid":
                            bot.send_video(chat_id, file_id,
                                           caption=f"{user_name} sent this.",
                                           reply_markup=reply_markup)
                        else:
                            bot.send_document(chat_id, file_id,
                                              caption=f"{user_name} sent this.",
                                              reply_markup=reply_markup)
                    else:
                        bot.send_message(chat_id, f"{user_name} sent this:\n{msg_text}",
                                         reply_markup=reply_markup)
                else:
                    try:
                        query.message.edit_text("Message has expired")
                    except BadRequest:
                        pass
    elif task == "delete":
        try:
            query.message.delete()
        except BadRequest:
            pass


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
