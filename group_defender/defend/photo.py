import os

from azure.cognitiveservices.vision.contentmoderator import ContentModeratorClient
from datetime import date
from dotenv import load_dotenv
from google.cloud import vision, datastore
from telegram import Chat, ChatAction

from group_defender.constants import *
from group_defender.utils import filter_msg, get_setting

load_dotenv()
AZURE_TOKEN = os.environ.get('AZURE_TOKEN')

if AZURE_TOKEN is None:
    AZURE_TOKEN = get_setting('AZURE_TOKEN')


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
    is_safe, likelihood = scan_photo(file_name)
    chat_type = update.message.chat.type

    if is_safe is not None:
        if not is_safe:
            # Delete message if it is a group chat
            if chat_type in (Chat.GROUP, Chat.SUPERGROUP):
                text = f'I deleted a photo that\'s {likelihood} to contain ' \
                    f'NSFW content (sent by @{update.message.from_user.username}).'
                filter_msg(update, context, file_id, PHOTO, text)
            else:
                update.message.reply_text(f'I think it\'s {likelihood} to contain NSFW content.', quote=True)
        else:
            if chat_type == Chat.PRIVATE:
                update.message.reply_text('I think it doesn\'t contain any NSFW content.', quote=True)
    else:
        update.message.reply_text('Photo scanning is currently unavailable.', quote=True)

    return is_safe


def scan_photo(file_name=None, file_url=None):
    curr_datetime = date.today()
    curr_year = curr_datetime.year
    curr_month = curr_datetime.month

    client = datastore.Client()
    query = client.query(kind=API_COUNT)
    query.add_filter(YEAR, '=', curr_year)
    query.add_filter(MONTH, '=', curr_month)
    entities = {}

    for entity in query.fetch():
        entities[entity[NAME]] = entity[COUNT]

    is_safe = likelihood = None
    if GCP not in entities or entities[GCP] <= GCP_LIMIT:
        is_safe, likelihood = gcp_scan(file_name, file_url)
        with client.transaction():
            key = client.key(API_COUNT, f'{GCP}{curr_year}{curr_month}')
            entity = client.get(key)

            if entity is None:
                entity = datastore.Entity(key)
                count = 1
            else:
                count = entity[COUNT] + 1

            entity.update({
                NAME: GCP,
                COUNT: count,
                YEAR: curr_year,
                MONTH: curr_month
            })
            client.put(entity)

    return is_safe, likelihood


def gcp_scan(file_name=None, file_url=None):
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
    is_safe = all(x < GCP_THRESHOLD for x in results)

    return is_safe, GCP_LIKELIHOODS[max(results)]
