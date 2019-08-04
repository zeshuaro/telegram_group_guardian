import os
import requests
import tempfile

from dotenv import load_dotenv
from logbook import Logger
from telegram import Chat, ChatMember, InlineKeyboardMarkup, InlineKeyboardButton, ChatAction
from telegram.constants import MAX_FILESIZE_DOWNLOAD
from telegram.ext.dispatcher import run_async

from group_defender.constants import AUDIO, DOCUMENT, PHOTO, VIDEO, OK, FOUND, WARNING, FAILED
from group_defender.defend.photo import check_photo

load_dotenv()
SCANNER_TOKEN = os.environ.get('SCANNER_TOKEN')


@run_async
def process_file(update, context):
    # Check if bot in group and if bot is a group admin, if not, files will not be checked
    if update.message.chat.type in (Chat.GROUP, Chat.SUPERGROUP) and \
            context.bot.get_chat_member(update.message.chat_id, context.bot.id).status != ChatMember.ADMINISTRATOR:
        update.message.reply_text('Set me as a group admin so that I can start checking files like this.')

        return

    # Get the received file
    files = [update.message.audio, update.message.document, update.message.photo, update.message.video]
    index, file = next(x for x in enumerate(files) if x[1] is not None)

    file_types = (AUDIO, DOCUMENT, PHOTO, VIDEO)
    file_type = file_types[index]
    file = file[-1] if file_type == PHOTO else file
    file_size = file.file_size

    # Check if file is too large for bot to download
    if file_size > MAX_FILESIZE_DOWNLOAD:
        if update.message.chat.type == Chat.PRIVATE:
            text = f'Your {file_type} is too large for me to download and check.'
            update.message.reply_text(text)

        return

    with tempfile.NamedTemporaryFile() as tf:
        file_name = tf.name
        file.get_file().download(file_name)
        check_file(update, context, file_name, file_type)

        file_mime_type = 'image' if file_type == PHOTO else file.mime_type
        if file_type == 'img' or file_mime_type.startswith('image'):
            check_photo(update, context, file_name)


def check_file(update, context, file_name, file_type):
    update.message.chat.send_action(ChatAction.TYPING)
    is_safe, status, matches = scan_file(file_name)
    chat_type = update.message.chat.type
    chat_id = update.message.chat_id
    msg_id = update.message.message_id
    user_name = update.message.from_user.first_name
    msg_text = update.message.text

    if not is_safe:
        threat_type = 'contains' if status == FOUND else 'may contain'
        if chat_type in (Chat.GROUP, Chat.SUPERGROUP):
            # store_msg(chat_id, msg_id, user_name, file_id, file_type, msg_text)

            text = f'I deleted a {file_type} that {threat_type} a virus or malware (sent by {user_name}).'
            keyboard = [[InlineKeyboardButton(text='Undo', callback_data=f'undo,{msg_id}')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            update.message.delete()
            context.bot.send_message(chat_id, text, reply_markup=reply_markup)
        else:
            update.message.reply_text(f'I think it {threat_type} a virus or malware, don\'t download or open it.')
    else:
        if chat_type == Chat.PRIVATE:
            if status == OK:
                update.message.reply_text('I think it doesn\'t contain any virus or malware.')
            # elif status == PENDING:
            #     keyboard = [[InlineKeyboardButton(text='Try again', callback_data=f'again,{msg_id}')]]
            #     reply_markup = InlineKeyboardMarkup(keyboard)
            #
            #     update.message.reply_text(f'I am still scanning this {file_type}.', reply_markup=reply_markup)
            else:
                log = Logger()
                log.error(matches)
                update.message.reply_text('Something went wrong, try again.')

                # keyboard = [[InlineKeyboardButton(text='Try again', callback_data=f'again,{msg_id}')]]
                # reply_markup = InlineKeyboardMarkup(keyboard)
                #
                # update.message.reply_text(f'Something went wrong.', reply_markup=reply_markup)


def scan_file(file_name=None, file_url=None):
    is_safe = True
    status = matches = None
    url = 'https://beta.attachmentscanner.com/v0.1/scans'
    headers = {'authorization': f'bearer {SCANNER_TOKEN}'}

    if file_name is not None:
        files = {'file': open(file_name, 'rb')}
        r = requests.post(url, headers=headers, files=files)
    else:
        json = {'url': file_url}
        r = requests.post(url, headers=headers, json=json)

    if r.status_code == 200:
        results = r.json()
        status = results['status']

        if status == FAILED:
            matches = results['matches']

    if status in (FOUND, WARNING):
        is_safe = False

    return is_safe, status, matches
