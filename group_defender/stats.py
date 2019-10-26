import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import tempfile

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
    total = 0

    for chat in query.fetch():
        if chat.key.id > 0:
            counts["num_users"] += 1
        else:
            counts["num_groups"] += 1

        for file_type in FILE_TYPES:
            if file_type in chat:
                counts[file_type] += chat[file_type]
                total += chat[file_type]

    update.effective_message.reply_text(
        f'Number of users: {counts["num_users"]}\nNumber of groups: {counts["num_groups"]}\n'
        f"Total processed: {total}"
    )
    send_plot(update, counts)


def send_plot(update, counts):
    nums = [counts[x] for x in FILE_TYPES]
    x_pos = list(range(len(FILE_TYPES)))

    plt.rcdefaults()
    _, ax = plt.subplots()

    ax.bar(x_pos, nums, align="center")
    ax.set_xticks(x_pos)
    ax.set_xticklabels(FILE_TYPES, rotation=45)
    ax.set_xlabel("File Types")
    ax.set_ylabel("Counts")
    plt.tight_layout()

    with tempfile.NamedTemporaryFile(suffix=".png") as tf:
        plt.savefig(tf.name)
        update.effective_message.reply_photo(open(tf.name, "rb"))
