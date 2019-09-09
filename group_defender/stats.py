from google.cloud import datastore

from group_defender.constants import BOT_COUNT, COUNT, FILE, PHOTO, CHAT
from group_defender.store import datastore_client as client


def update_stats(chat_id, counts):
    key = client.key(CHAT, chat_id)
    with client.transaction():
        chat = client.get(key)
        if chat is None:
            chat = datastore.Entity(key)

        for file_type in counts:
            if file_type in chat:
                chat[file_type] += counts[file_type]
            else:
                chat[file_type] = 1

        client.put(chat)


def get_stats(update, _):
    query = client.query(kind=BOT_COUNT)
    count_file = count_photo = count_url = 0

    for counts in query.fetch():
        if counts.key.name == FILE:
            count_file += counts[COUNT]
        elif counts.key.name == PHOTO:
            count_photo += counts[COUNT]
        else:
            count_url += counts[COUNT]

    update.effective_message.reply_text(
        f'Processed files: {count_file}\nProcessed photos: {count_photo}\nProcessed urls: {count_url}\n'
        f'Total: {count_file + count_url}')
