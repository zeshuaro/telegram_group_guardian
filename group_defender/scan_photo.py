import tempfile

from google.cloud import vision
from telegram import Chat, InlineKeyboardButton, InlineKeyboardMarkup, ChatAction

from group_defender.constants import SAFE_ANN_LIKELIHOODS, SAFE_ANN_TYPES, SAFE_ANN_THRESHOLD


def check_photo(update, context, file_name):
    update.message.chat.send_action(ChatAction.TYPING)
    # if file_type == 'img' or file_mime_type.startswith('image'):
    #     if file_size <= VISION_IMAGE_SIZE_LIMIT:
    is_safe, results = scan_photo(file_name)
    safe_ann_index = next((x[0] for x in enumerate(results) if x[1] > SAFE_ANN_THRESHOLD), 0)
    safe_ann_value = results[safe_ann_index]

    chat_type = update.message.chat.type
    chat_id = update.message.chat_id
    msg_id = update.message.message_id
    user_name = update.message.from_user.first_name
    msg_text = update.message.text

    if not is_safe:
        # Delete message if it is a group chat
        if chat_type in (Chat.GROUP, Chat.SUPERGROUP):
            # store_msg(chat_id, msg_id, user_name, file_id, file_type, msg_text)
            text = f'I deleted a photo that\'s {SAFE_ANN_LIKELIHOODS[safe_ann_value]} to contain ' \
                f'{SAFE_ANN_TYPES[safe_ann_index]} content (sent by {user_name}).'
            keyboard = [[InlineKeyboardButton(text='Undo', callback_data=f'undo,{msg_id}')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            update.message.delete()
            context.bot.send_message(chat_id, text, reply_markup=reply_markup)
        else:
            update.message.reply_text(f'And I think it\'s {SAFE_ANN_LIKELIHOODS[safe_ann_value]} to contain '
                                      f'{SAFE_ANN_TYPES[safe_ann_index]} content.')
    else:
        if chat_type == Chat.PRIVATE:
            update.message.reply_text('And I think it doesn\'t contain any NSFW content.')


def scan_photo(file_name):
    client = vision.ImageAnnotatorClient()
    response = client.annotate_image({
        'image': {'content': open(file_name, 'rb').read()},
        'features': [{'type': vision.enums.Feature.Type.SAFE_SEARCH_DETECTION}],
    })

    safe_ann = response.safe_search_annotation
    results = [safe_ann.adult, safe_ann.spoof, safe_ann.medical, safe_ann.violence, safe_ann.racy]
    is_safe = any(x > SAFE_ANN_THRESHOLD for x in results)

    return is_safe, results
