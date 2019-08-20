from google.cloud import datastore

from group_defender.constants import BOT_COUNT, COUNT, FILE, PHOTO


def update_stats(count_key, num_count=1):
    client = datastore.Client()
    with client.transaction():
        count_key = client.key(BOT_COUNT, count_key)
        count = client.get(key=count_key)
        count[COUNT] += num_count
        client.put(count)


def get_stats(update, _):
    client = datastore.Client()
    query = client.query(kind=BOT_COUNT)
    count_file = count_photo = count_url = 0

    for counts in query.fetch():
        if counts.key.name == FILE:
            count_file += counts[COUNT]
        elif counts.key.name == PHOTO:
            count_photo += counts[COUNT]
        else:
            count_url += counts[COUNT]

    update.message.reply_text(
        f'Processed files: {count_file}\nProcessed photos: {count_photo}\nProcessed urls: {count_url}\n'
        f'Total: {count_file + count_url}')
