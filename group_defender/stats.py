from group_defender.constants import BOT_COUNT, COUNT, FILE, PHOTO
from group_defender.store import datastore_client


def update_stats(counts):
    keys = [datastore_client.key(BOT_COUNT, x) for x in counts.keys()]
    with datastore_client.transaction():
        entities = datastore_client.get_multi(keys)
        for entity in entities:
            entity[COUNT] += counts[entity.key.name]

        datastore_client.put_multi(entities)


def get_stats(update, _):
    query = datastore_client.query(kind=BOT_COUNT)
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
