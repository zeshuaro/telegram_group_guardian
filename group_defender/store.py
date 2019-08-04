from datetime import datetime, timedelta
from google.cloud import datastore

from group_defender.constants import MSG, MSG_LIFETIME, USERNAME, FILE_ID, FILE_TYPE, MSG_TEXT, EXPIRY


def store_msg(chat_id, msg_id, username, file_id, file_type, msg_text):
    expiry = datetime.utcnow() + timedelta(days=MSG_LIFETIME)
    client = datastore.Client()
    msg_key = client.key(MSG, f'{chat_id},{msg_id}')
    msg = datastore.Entity(msg_key)
    msg.update({
        USERNAME: username,
        FILE_ID: file_id,
        FILE_TYPE: file_type,
        MSG_TEXT: msg_text,
        EXPIRY: expiry
    })
    client.put(msg)
