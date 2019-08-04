from datetime import datetime, timedelta
from google.cloud import datastore
from telegram import Chat, ChatMember, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest

from group_defender.constants import *


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


def process_msg(update, context):
    query = update.callback_query
    chat_id = query.message.chat_id
    user_id = query.from_user.id

    if query.message.chat.type in (Chat.GROUP, Chat.SUPERGROUP) and \
            context.bot.get_chat_member(chat_id, user_id).status not in (ChatMember.ADMINISTRATOR, ChatMember.CREATOR):
        return

    task, msg_id = query.data.split(",")
    msg_id = int(msg_id)

    if task == UNDO:
        restore_msg(context, query, chat_id, msg_id)
    elif task == DELETE:
        try:
            query.message.delete()
        except BadRequest:
            pass


def restore_msg(context, query, chat_id, msg_id):
    query.message.edit_text('Retrieving message')
    client = datastore.Client()
    msg_key = client.key(MSG, f'{chat_id},{msg_id}')
    msg = client.get(msg_key)

    if msg is not None:
        client.delete(msg_key)

        try:
            query.message.delete()
        except BadRequest:
            return

        file_id = msg[FILE_ID]
        file_type = msg[FILE_TYPE]
        username = msg[USERNAME]
        msg_text = msg[MSG_TEXT]

        keyboard = [[InlineKeyboardButton(text="Delete (Cannot be undone)", callback_data=f'{DELETE},{msg_id}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if file_id is not None:
            caption = f"@{username} sent this."
            if file_type == PHOTO:
                context.bot.send_photo(chat_id, file_id, caption=caption, reply_markup=reply_markup)
            elif file_type == AUDIO:
                context.bot.send_audio(chat_id, file_id, caption=caption, reply_markup=reply_markup)
            elif file_type == VIDEO:
                context.bot.send_video(chat_id, file_id, caption=caption, reply_markup=reply_markup)
            elif file_type == DOCUMENT:
                context.bot.send_document(chat_id, file_id, caption=caption, reply_markup=reply_markup)
        else:
            context.bot.send_message(chat_id, f"@{username} sent this:\n{msg_text}", reply_markup=reply_markup)
    else:
        try:
            query.message.edit_text("Message has expired")
        except BadRequest:
            pass
