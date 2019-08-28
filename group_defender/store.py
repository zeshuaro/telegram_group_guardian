import secrets

from datetime import datetime, timedelta
from google.cloud import datastore
from telegram import Chat, ChatMember, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest

from group_defender.constants import *

datastore_client = datastore.Client()


def store_msg(chat_id, msg_id, username, file_id, file_type, msg_text):
    """
    Store the message on datastore
    Args:
        chat_id: the int of the chat ID
        msg_id: the int of the message ID
        username: the string of the username
        file_id: the int of the file ID
        file_type: the string of the file type
        msg_text: the string of the message text

    Returns:
        None
    """
    msg_key = datastore_client.key(MSG, f'{chat_id},{msg_id}')
    msg = datastore.Entity(msg_key)
    msg.update({
        USERNAME: username,
        FILE_ID: file_id,
        FILE_TYPE: file_type,
        MSG_TEXT: msg_text,
        EXPIRY: datetime.utcnow() + timedelta(days=MSG_LIFETIME)
    })
    datastore_client.put(msg)


def process_msg(update, context):
    """
    Process the message from inline keyboard
    Args:
        update: the update object
        context: the context object

    Returns:
        None
    """
    query = update.callback_query
    chat_id = query.message.chat_id
    user_id = query.from_user.id

    if query.message.chat.type in (Chat.GROUP, Chat.SUPERGROUP) and \
            context.bot.get_chat_member(chat_id, user_id).status not in (ChatMember.ADMINISTRATOR, ChatMember.CREATOR):
        context.bot.send_message(user_id, 'You can\'t perform this action as you\'re not a group admin.')

        return

    task, msg_id = query.data.split(",")
    msg_id = int(msg_id)

    if task == UNDO:
        if (chat_id, msg_id) not in context.chat_data:
            context.chat_data[chat_id, msg_id] = None
            restore_msg(context, query, chat_id, msg_id)
    elif task == DELETE:
        try:
            query.message.delete()
        except BadRequest:
            pass


def restore_msg(context, query, chat_id, msg_id):
    """
    Restore the deleted message
    Args:
        context: the context object
        query: the query object
        chat_id: the int of the chat ID
        msg_id: the int of the message ID

    Returns:
        None
    """
    query.message.edit_text('Retrieving message')
    msg_key = datastore_client.key(MSG, f'{chat_id},{msg_id}')
    msg = datastore_client.get(msg_key)

    if msg is not None:
        datastore_client.delete(msg_key)

        try:
            query.message.delete()
        except BadRequest:
            return

        file_id = msg[FILE_ID]
        file_type = msg[FILE_TYPE]
        username = msg[USERNAME]
        msg_text = msg[MSG_TEXT]

        keyboard = [[InlineKeyboardButton(text="Delete (Cannot be undone)", callback_data=f'{DELETE},{msg_id}')]]
        if secrets.randbelow(2):
            keyboard.append([InlineKeyboardButton('Support Group Defender', callback_data=PAYMENT)])

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

    try:
        del context.chat_data[chat_id, msg_id]
    except KeyError:
        pass


def delete_expired_msg(_):
    """
    Delete expired message
    Args:
        _: unused variable

    Returns:
        None
    """
    query = datastore_client.query(kind=MSG)
    query.add_filter(EXPIRY, '<', datetime.utcnow())
    query.keys_only()
    keys = [x.key for x in query.fetch()]
    datastore_client.delete_multi(keys)
