from telegram import Chat, ChatMember, ChatAction
from telegram.constants import MAX_FILESIZE_DOWNLOAD
from telegram.ext.dispatcher import run_async

from group_defender.constants import AUDIO, DOCUMENT, PHOTO, VIDEO
from group_defender.defend import process_file


@run_async
def check_file(update, context):
    # Check if bot in group and if bot is a group admin, if not, files will not be checked
    if update.message.chat.type in (Chat.GROUP, Chat.SUPERGROUP) and \
            context.bot.get_chat_member(update.message.chat_id, context.bot.id).status != ChatMember.ADMINISTRATOR:
        update.message.reply_text('Set me as a group admin so that I can start checking files like this.')

        return

    # Get the received file
    update.message.chat.send_action(ChatAction.TYPING)
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

    tele_file = file.get_file()
    file_mime_type = 'image' if file_type == PHOTO else file.mime_type

    process_file(update, context, tele_file, file_type)
    # _, text = is_malware_and_vision_safe(bot, update, tele_file.file_path, file_type, file_mime_type, file_size,
    #                                      file.file_id)
    # if text:
    #     update.message.reply_text(text, quote=True)
