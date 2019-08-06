from google.cloud import vision
from telegram import Chat, ChatAction

from group_defender.constants import SAFE_ANN_LIKELIHOODS, SAFE_ANN_TYPES, SAFE_ANN_THRESHOLD, PHOTO
from group_defender.utils import filter_msg


def check_photo(update, context, file_id, file_name):
    """
    Check if the photo is safe or not
    Args:
        update: the update object
        context: the context object
        file_id: the int of the file ID
        file_name: the string of the file name

    Returns:
        None
    """
    update.message.chat.send_action(ChatAction.TYPING)
    is_safe, results = scan_photo(file_name)
    safe_ann_index = next((x[0] for x in enumerate(results) if x[1] >= SAFE_ANN_THRESHOLD), 0)
    safe_ann_value = results[safe_ann_index]
    chat_type = update.message.chat.type

    if not is_safe:
        # Delete message if it is a group chat
        if chat_type in (Chat.GROUP, Chat.SUPERGROUP):
            text = f'I deleted a photo that\'s {SAFE_ANN_LIKELIHOODS[safe_ann_value]} to contain ' \
                f'{SAFE_ANN_TYPES[safe_ann_index]} content (sent by @{update.message.from_user.username}).'
            filter_msg(update, context, file_id, PHOTO, text)
        else:
            update.message.reply_text(f'I think it\'s {SAFE_ANN_LIKELIHOODS[safe_ann_value]} to contain '
                                      f'{SAFE_ANN_TYPES[safe_ann_index]} content.')
    else:
        if chat_type == Chat.PRIVATE:
            update.message.reply_text('I think it doesn\'t contain any NSFW content.')

    return is_safe


def scan_photo(file_name=None, file_url=None):
    """
    Scan the photo using the API
    Args:
        file_name: the string of the file name
        file_url: the string of the file url

    Returns:
        A tuple of a bool indicating if the photo is safe or not and the results from the API call
    """
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
