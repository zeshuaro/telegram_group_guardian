import os
import requests
import tempfile

from dotenv import load_dotenv
from logbook import Logger
from telegram import Chat, InlineKeyboardMarkup, InlineKeyboardButton

from group_defender.constants import OK, FOUND, WARNING, PENDING, FAILED

load_dotenv()
SCANNER_TOKEN = os.environ.get('SCANNER_TOKEN') 


# Master function for checking malware and vision
def is_malware_and_vision_safe(bot, update, file_url, file_type, file_mime_type, file_size, file_id=None):
    if file_id is None and file_url is None:
        raise ValueError('You must provide either file_id or file_url')

    # Setup return variables
    safe = True
    reply_text = ''

    # Grab info from message
    chat_type = update.message.chat.type
    chat_id = update.message.chat_id
    msg_id = update.message.message_id
    user_name = update.message.from_user.first_name
    msg_text = update.message.text

    if not check_file(file_url):
        safe = False

        # Delete message if it is a group chat
        if chat_type in (Chat.GROUP, Chat.SUPERGROUP):
            store_msg(chat_id, msg_id, user_name, file_id, file_type, msg_text)

            text = f'I deleted a {FILE_TYPE_NAMES[file_type]} that contains threats (sent by {user_name}).'
            keyboard = [[InlineKeyboardButton(text='Undo', callback_data=f'undo,{msg_id}')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            update.message.delete()
            bot.send_message(chat_id, text, reply_markup=reply_markup)
        else:
            if file_id:
                reply_text += 'I think it contains threats, don\'t download or open it.'
            else:
                reply_text += f'{file_url}\n⬆ I think it contains threats, don\'t download or open it.'
    else:
        if chat_type == Chat.PRIVATE:
            if file_id:
                reply_text += 'I think it doesn\'t contain threats. '
            else:
                reply_text += f'{file_url}\n⬆ I think it doesn\'t contain threats. '

        if file_type == 'img' or file_mime_type.startswith('image'):
            if file_size <= VISION_IMAGE_SIZE_LIMIT:
                vision_safe, vision_results = is_vision_safe(file_url)
                safe_ann_index = next((x[0] for x in enumerate(vision_results) if x[1] > SAFE_ANN_THRESHOLD), 0)
                safe_ann_value = vision_results[safe_ann_index]

                if not vision_safe:
                    safe = False
                    safe_ann_likelihoods = ('unknown', 'very likely', 'unlikely', 'possible', 'likely', 'very likely')
                    safe_ann_types = ('adult', 'spoof', 'medical', 'violence', 'racy')

                    # Delete message if it is a group chat
                    if chat_type in (Chat.GROUP, Chat.SUPERGROUP):
                        store_msg(chat_id, msg_id, user_name, file_id, file_type, msg_text)

                        if file_id:
                            text = 'I deleted a photo that\'s '
                        else:
                            text = 'I deleted a message which contains a link of photo that\'s '

                        text += f'{safe_ann_likelihoods[safe_ann_value]} to contain ' \
                                f'{safe_ann_types[safe_ann_index]} content (sent by {user_name}).'

                        keyboard = [[InlineKeyboardButton(text='Undo', callback_data=f'undo,{msg_id}')]]
                        reply_markup = InlineKeyboardMarkup(keyboard)

                        update.message.delete()
                        bot.send_message(chat_id, text, reply_markup=reply_markup)
                    else:
                        reply_text += f'But I think it is {safe_ann_likelihoods[safe_ann_value]} ' \
                                      f'to contain {safe_ann_types[safe_ann_index]} content.'
                else:
                    if chat_type == Chat.PRIVATE:
                        reply_text += 'And I think it doesn\'t contain any inappropriate content.'
            else:
                if update.message.chat.type == Chat.PRIVATE:
                    reply_text += 'But it is too large for me to check for inappropriate content.'

    return safe, reply_text


def process_file(update, context, file, file_type):
    status, matches = scan_file(file)
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


def scan_file(file):
    status = matches = None
    url = 'https://beta.attachmentscanner.com/scans'
    headers = {'authorization': f'bearer {SCANNER_TOKEN}'}

    with tempfile.NamedTemporaryFile() as tf:
        file.download(tf.name)
        files = {'file': open(tf.name, 'rb')}
        r = requests.post(url=url, headers=headers, files=files)

    if r.status_code == 200:
        results = r.json()
        status = results['status']

        if status == FAILED:
            matches = results['matches']

    return status, matches


# Check if the image is vision safe
def is_vision_safe(file_url):
    safe = True
    client = vision.ImageAnnotatorClient()
    image = vision.types.Image()
    image.source.image_uri = file_url
    response = client.safe_search_detection(image=image)

    safe_ann = response.safe_search_annotation
    safe_ann_results = [safe_ann.adult, safe_ann.spoof, safe_ann.medical, safe_ann.violence, safe_ann.racy]

    if any(x > SAFE_ANN_THRESHOLD for x in safe_ann_results):
        safe = False

    return safe, safe_ann_results