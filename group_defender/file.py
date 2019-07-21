import tempfile

from telegram import Chat, ChatMember
from telegram.constants import MAX_FILESIZE_DOWNLOAD
from telegram.ext.dispatcher import run_async

from group_defender.constants import AUDIO, DOCUMENT, PHOTO, VIDEO
from group_defender.scan_file import check_file
from group_defender.scan_photo import check_photo


@run_async
def process_file(update, context):
    # Check if bot in group and if bot is a group admin, if not, files will not be checked
    if update.message.chat.type in (Chat.GROUP, Chat.SUPERGROUP) and \
            context.bot.get_chat_member(update.message.chat_id, context.bot.id).status != ChatMember.ADMINISTRATOR:
        update.message.reply_text('Set me as a group admin so that I can start checking files like this.')

        return

    # Get the received file
    files = [update.message.audio, update.message.document, update.message.photo, update.message.video]
    index, file = next(x for x in enumerate(files) if x[1] is not None)

    file_types = (AUDIO, DOCUMENT, PHOTO, VIDEO)
    file_type = file_types[index]
    file = file[-1] if file_type == PHOTO else file
    file_size = file.file_size

    # Check if file is too large for bot to download
    if file_size > MAX_FILESIZE_DOWNLOAD:
        if update.message.chat.type == Chat.PRIVATE:
            text = f'Your {file_type} is too large for me to download and process.'
            update.message.reply_text(text)

        return

    with tempfile.NamedTemporaryFile() as tf:
        file_name = tf.name
        file.get_file().download(file_name)
        check_file(update, context, file_name, file_type)

        file_mime_type = 'image' if file_type == PHOTO else file.mime_type
        if file_type == 'img' or file_mime_type.startswith('image'):
            check_photo(update, context, file_name)
