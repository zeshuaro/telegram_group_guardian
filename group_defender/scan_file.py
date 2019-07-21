import os
import requests

from dotenv import load_dotenv
from logbook import Logger
from telegram import Chat, InlineKeyboardMarkup, InlineKeyboardButton, ChatAction

from group_defender.constants import OK, FOUND, WARNING, PENDING, FAILED

load_dotenv()
SCANNER_TOKEN = os.environ.get('SCANNER_TOKEN')


def check_file(update, context, file_name, file_type):
    update.message.chat.send_action(ChatAction.TYPING)
    status, matches = scan_file(file_name)
    chat_type = update.message.chat.type
    chat_id = update.message.chat_id
    msg_id = update.message.message_id
    user_name = update.message.from_user.first_name
    msg_text = update.message.text

    if status == OK:
        if chat_type == Chat.PRIVATE:
            update.message.reply_text('I think it doesn\'t contain any virus or malware.')
    elif status in (FOUND, WARNING):
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
    elif status == PENDING:
        keyboard = [[InlineKeyboardButton(text='Try again', callback_data=f'again,{msg_id}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(f'I am still scanning this {file_type}.', reply_markup=reply_markup)
    else:
        log = Logger()
        log.error(matches)

        keyboard = [[InlineKeyboardButton(text='Try again', callback_data=f'again,{msg_id}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(f'Something went wrong.', reply_markup=reply_markup)


def scan_file(file_name):
    status = matches = None
    url = 'https://beta.attachmentscanner.com/scans'
    headers = {'authorization': f'bearer {SCANNER_TOKEN}'}
    files = {'file': open(file_name, 'rb')}
    r = requests.post(url=url, headers=headers, files=files)

    if r.status_code == 200:
        results = r.json()
        status = results['status']

        if status == FAILED:
            matches = results['matches']

    return status, matches
