from collections import defaultdict
from google.cloud import datastore

from group_defender.constants import CHAT, FILE_TYPES
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
    query = client.query(kind=CHAT)
    counts = defaultdict(int)

    for chat in query.fetch():
        if chat.key.id > 0:
            counts['num_users'] += 1
        else:
            counts['num_groups'] += 1

        for file_type in FILE_TYPES:
            if file_type in chat:
                counts[file_type] += chat[file_type]

    text = f'Number of users: {counts["num_users"]}\nNumber of groups: {counts["num_groups"]}\n\n'
    total = 0

    for file_type in FILE_TYPES:
        if file_type in counts:
            text += f'Processed {file_type}: {counts[file_type]}\n'
            total += counts[file_type]
        else:
            text += f'Processed {file_type}: 0\n'

    text += f'\nTotal processed: {total}'
    update.effective_message.reply_text(text)
