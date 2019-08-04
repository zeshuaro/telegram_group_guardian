from google.cloud import vision
from telegram import Chat, InlineKeyboardButton, InlineKeyboardMarkup, ChatAction

from group_defender.constants import SAFE_ANN_LIKELIHOODS, SAFE_ANN_TYPES, SAFE_ANN_THRESHOLD, PHOTO, UNDO
from group_defender.store import store_msg


def check_photo(update, context, file_id, file_name):
    update.message.chat.send_action(ChatAction.TYPING)
    is_safe, results = scan_photo(file_name)
    safe_ann_index = next((x[0] for x in enumerate(results) if x[1] > SAFE_ANN_THRESHOLD), 0)
    safe_ann_value = results[safe_ann_index]
    chat_type = update.message.chat.type

    if not is_safe:
        # Delete message if it is a group chat
        if chat_type in (Chat.GROUP, Chat.SUPERGROUP):
            chat_id = update.message.chat_id
            msg_id = update.message.message_id
            username = update.message.from_user.username
            store_msg(chat_id, msg_id, username, file_id, PHOTO, update.message.text)

            text = f'I deleted a photo that\'s {SAFE_ANN_LIKELIHOODS[safe_ann_value]} to contain ' \
                f'{SAFE_ANN_TYPES[safe_ann_index]} content (sent by @{username}).'
            keyboard = [[InlineKeyboardButton(text='Undo', callback_data=f'{UNDO},{msg_id}')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            update.message.delete()
            context.bot.send_message(chat_id, text, reply_markup=reply_markup)
        else:
            update.message.reply_text(f'And I think it\'s {SAFE_ANN_LIKELIHOODS[safe_ann_value]} to contain '
                                      f'{SAFE_ANN_TYPES[safe_ann_index]} content.')
    else:
        if chat_type == Chat.PRIVATE:
            update.message.reply_text('And I think it doesn\'t contain any NSFW content.')


def scan_photo(file_name=None, file_url=None):
    if file_name is not None:
        img_src = {'content': open(file_name, 'rb').read()}
    else:
        img_src = {'source': {'image_uri': file_url}}

    client = vision.ImageAnnotatorClient()
    response = client.annotate_image({
        'image': img_src,
        'features': [{'type': vision.enums.Feature.Type.SAFE_SEARCH_DETECTION}],
    })

    safe_ann = response.safe_search_annotation
    results = [safe_ann.adult, safe_ann.spoof, safe_ann.medical, safe_ann.violence, safe_ann.racy]
    is_safe = all(x < SAFE_ANN_THRESHOLD for x in results)

    return is_safe, results
