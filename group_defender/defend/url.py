import inflect
import mimetypes
import os
import re
import requests

from dotenv import load_dotenv
from requests.exceptions import ConnectionError
from telegram import Chat, ChatAction, ChatMember, MessageEntity, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext.dispatcher import run_async

from group_defender.defend.file import scan_file
from group_defender.defend.photo import scan_photo


load_dotenv()
GOOGLE_TOKEN = os.environ.get('GOOGLE_TOKEN')


@run_async
def check_url(update, context):
    # Check if bot in group and if bot is a group admin, if not, links will not be checked
    if update.message.chat.type in (Chat.GROUP, Chat.SUPERGROUP) and \
            context.bot.get_chat_member(update.message.chat_id, context.bot.id).status != ChatMember.ADMINISTRATOR:
        update.message.reply_text('Set me as a group admin so that I can start checking links like this.')

        return

    update.message.chat.send_action(ChatAction.TYPING)
    chat_type = update.message.chat.type
    chat_id = update.message.chat_id
    msg_id = update.message.message_id
    user_name = update.message.from_user.first_name
    msg_text = update.message.text

    entities = update.message.parse_entities([MessageEntity.URL])
    urls = entities.values()
    active_urls = get_active_urls(urls)
    is_url_safe, safe_list = scan_url(active_urls)
    is_file_safe = is_photo_safe = True

    if is_url_safe:
        is_file_safe, is_photo_safe, safe_list = check_file_photo(urls)

    if not is_url_safe or not is_file_safe or not is_photo_safe:
        if not is_photo_safe:
            content = 'NSFW content'
        else:
            content = 'a virus or malware'

        if chat_type in (Chat.GROUP, Chat.SUPERGROUP):
            # store_msg(chat_id, msg_id, user_name, None, 'url', msg_text)

            text = f'I deleted a message that contains links with {content} (sent by {user_name}).'
            keyboard = [[InlineKeyboardButton(text='Undo', callback_data=f'undo,{msg_id}')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            update.message.delete()
            context.bot.send_message(chat_id, text, reply_markup=reply_markup)
        else:
            ordinals = []
            p = inflect.engine()

            for i, is_link_safe in enumerate(safe_list):
                if not is_link_safe:
                    ordinals.append(p.ordinal(i + 1))

            if len(urls) == 1:
                update.message.reply_text(f'I think the link contains {content}, don\'t open it.')
            else:
                update.message.reply_text(f'I think the {", ".join(ordinals)} links contain a virus or malware or '
                                          f'NSFW content, don\'t open them.')
    else:
        if chat_type == Chat.PRIVATE:
            if len(active_urls) == 0:
                update.message.reply_text('I couldn\'t check the link(s) as they are unavailable.')
            else:
                update.message.reply_text('I think the link(s) are safe.')


def get_active_urls(urls):
    active_urls = []
    for url in urls:
        if url.startswith('https://'):
            url = re.sub(r'^https://', 'http://', url)
        elif not url.startswith('http://'):
            url = f'http://{url}'

        try:
            r = requests.get(url)
            if r.status_code == 200:
                active_urls.append(url)
        except ConnectionError:
            continue

    return active_urls


# Check if url is safe
def scan_url(urls):
    is_safe = True
    safe_list = [True] * len(urls)

    safe_browsing_url = 'https://safebrowsing.googleapis.com/v4/threatMatches:find'
    params = {'key': GOOGLE_TOKEN}
    json = {
        'threatInfo': {
            'threatTypes': ['THREAT_TYPE_UNSPECIFIED', 'MALWARE', 'SOCIAL_ENGINEERING', 'UNWANTED_SOFTWARE',
                            'POTENTIALLY_HARMFUL_APPLICATION'],
            'platformTypes': ['ANY_PLATFORM'],
            'threatEntryTypes': ['URL'],
            'threatEntries': [{'url': url} for url in urls]
        }
    }
    r = requests.post(safe_browsing_url, params=params, json=json)

    if r.status_code == 200:
        results = r.json()
        if 'matches' in results and results['matches']:
            is_safe = False
            matches = results['matches']
            urls_dict = {k: v for v, k in enumerate(urls)}

            for match in matches:
                safe_list[urls_dict[match['threat']['url']]] = False

    return is_safe, safe_list


def check_file_photo(urls):
    is_file_safe = is_photo_safe = True
    file_safe_list = []
    photo_safe_list = []

    for url in urls:
        mime_type = mimetypes.guess_type(url)
        if mime_type[0] is not None:
            if not scan_file(file_url=url)[0]:
                is_file_safe = False
                file_safe_list.append(False)
            else:
                file_safe_list.append(True)

            if is_file_safe and mime_type[0].startswith('image'):
                if not scan_photo(file_url=url)[0]:
                    is_photo_safe = False
                    photo_safe_list.append(False)
                else:
                    photo_safe_list.append(True)

    if not is_file_safe or is_photo_safe:
        safe_list = [a if not a else b for a, b in zip(file_safe_list, photo_safe_list)]
    else:
        safe_list = [True] * len(urls)

    return is_file_safe, is_photo_safe, safe_list
