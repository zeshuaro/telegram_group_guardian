import os

from azure.cognitiveservices.vision.contentmoderator import ContentModeratorClient
from datetime import date
from dotenv import load_dotenv
from google.cloud import vision, datastore
from logbook import Logger
from msrest.authentication import CognitiveServicesCredentials
from telegram import Chat, ChatAction

from group_defender.constants import *
from group_defender.utils import filter_msg, get_settings
from group_defender.store import datastore_client

load_dotenv()
AZURE_TOKEN = os.environ.get('AZURE_TOKEN')
AZURE_LOC = os.environ.get('AZURE_LOC')

if AZURE_TOKEN is None:
    AZURE_TOKEN, AZURE_LOC = get_settings(['AZURE_TOKEN', 'AZURE_LOC'])


def check_photo(update, context, file_id, file_name, file_type):
    """
    Check if the photo is safe or not
    Args:
        update: the update object
        context: the context object
        file_id: the int of the file ID
        file_name: the string of the file name
        file_type: the string of the file type

    Returns:
        None
    """
    message = update.effective_message
    message.chat.send_action(ChatAction.TYPING)
    is_safe, likelihood = scan_photo(file_name)
    chat_type = message.chat.type

    if is_safe is not None:
        if not is_safe:
            # Delete message if it is a group chat
            if chat_type in (Chat.GROUP, Chat.SUPERGROUP):
                text = f'I\'ve deleted a photo that\'s {likelihood} to contain ' \
                    f'NSFW content (sent by @{message.from_user.username}).'
                filter_msg(update, context, file_id, file_type, text)
            else:
                message.reply_text(f'I think it\'s {likelihood} to contain NSFW content.', quote=True)
        else:
            if chat_type == Chat.PRIVATE:
                message.reply_text('I think it doesn\'t contain any NSFW content.', quote=True)
    else:
        if chat_type == Chat.PRIVATE:
            message.reply_text('Photo scanning is currently unavailable.', quote=True)

    return is_safe


def scan_photo(file_name=None, file_url=None):
    curr_datetime = date.today()
    curr_year = curr_datetime.year
    curr_month = curr_datetime.month

    query = datastore_client.query(kind=API_COUNT)
    query.add_filter(YEAR, '=', curr_year)
    query.add_filter(MONTH, '=', curr_month)
    entities = {}

    for entity in query.fetch():
        entities[entity[NAME]] = entity[COUNT]

    is_safe = likelihood = None
    if GCP not in entities or entities[GCP] <= GCP_LIMIT:
        is_safe, likelihood = gcp_scan(file_name, file_url)
        update_api_count(datastore_client, GCP, curr_year, curr_month)
    elif AZURE not in entities or entities[AZURE] <= AZURE_LIMIT:
        is_safe, likelihood = azure_scan(file_name, file_url)
        update_api_count(datastore_client, AZURE, curr_year, curr_month)
    else:
        log = Logger()
        log.warn('Vision scan tokens exhausted')

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


def azure_scan(file_name=None, file_url=None):
    client = ContentModeratorClient(
        f'https://{AZURE_LOC}.api.cognitive.microsoft.com/', CognitiveServicesCredentials(AZURE_TOKEN))
    if file_name is not None:
        evaluation = client.image_moderation.evaluate_file_input(
            image_stream=open(file_name, 'rb'),
            cache_image=True
        )
    else:
        evaluation = client.image_moderation.evaluate_url_input(
            content_type="application/json",
            cache_image=True,
            data_representation="URL",
            value=file_url
        )

    results = [evaluation.adult_classification_score, evaluation.racy_classification_score]
    is_safe = all(x < AZURE_THRESHOLD for x in results)
    max_score = max(results)

    if max_score >= 0.9:
        likelihood = 'very likely'
    elif max_score >= 0.75:
        likelihood = 'likely'
    elif max_score >= 0.5:
        likelihood = 'possible'
    elif max_score >= 0.25:
        likelihood = 'unlikely'
    else:
        likelihood = 'very unlikely'

    return is_safe, likelihood


def update_api_count(client, name, curr_year, curr_month):
    with client.transaction():
        key = client.key(API_COUNT, f'{name}{curr_year}{curr_month}')
        entity = client.get(key)

        if entity is None:
            entity = datastore.Entity(key)
            count = 1
        else:
            count = entity[COUNT] + 1

        entity.update({
            NAME: name,
            COUNT: count,
            YEAR: curr_year,
            MONTH: curr_month
        })
        client.put(entity)
