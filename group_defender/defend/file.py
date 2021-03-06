import os
import requests
import tempfile

from dotenv import load_dotenv
from logbook import Logger
from moviepy.editor import VideoFileClip
from telegram import Chat, ChatMember, ChatAction
from telegram.constants import MAX_FILESIZE_DOWNLOAD
from telegram.ext.dispatcher import run_async

from group_defender.constants import (
    AUDIO,
    DOCUMENT,
    PHOTO,
    VIDEO,
    OK,
    FOUND,
    WARNING,
    FAILED,
    ANIMATION,
    STICKER,
)
from group_defender.defend.photo import check_photo
from group_defender.utils import filter_msg, get_setting
from group_defender.stats import update_stats

load_dotenv()
SCANNER_TOKEN = os.environ.get("SCANNER_TOKEN")

if SCANNER_TOKEN is None:
    SCANNER_TOKEN = get_setting("SCANNER_TOKEN")


@run_async
def process_file(update, context):
    # Check if bot in group and if bot is a group admin, if not, files will not be checked
    message = update.effective_message
    if (
        message.chat.type in (Chat.GROUP, Chat.SUPERGROUP)
        and message.chat.get_member(context.bot.id).status != ChatMember.ADMINISTRATOR
    ):
        message.reply_text(
            "Set me as a group admin so that I can start checking files like this."
        )

        return

    # Get the received file
    files = [
        message.animation,
        message.audio,
        message.document,
        message.sticker,
        message.video,
        message.photo,
    ]
    index, file = next(x for x in enumerate(files) if x[1] is not None)

    file_types = (ANIMATION, AUDIO, DOCUMENT, STICKER, VIDEO, PHOTO)
    file_type = file_types[index]
    file = file[-1] if file_type == PHOTO else file
    file_size = file.file_size

    # Check if file is too large for bot to download
    if file_size > MAX_FILESIZE_DOWNLOAD:
        if message.chat.type == Chat.PRIVATE:
            message.reply_text(
                f"Your {file_type} is too large for me to download and check."
            )

        return
    elif file_type == STICKER and file.is_animated:
        if message.chat.type == Chat.PRIVATE:
            message.reply_text(f"Animated stickers are not supported yet")

        return

    with tempfile.NamedTemporaryFile() as tf1, tempfile.NamedTemporaryFile(
        suffix=".gif"
    ) as tf2:
        file_id = file.file_id
        file_size = file.file_size
        file_name = tf1.name

        tele_file = context.bot.get_file(file_id)
        tele_file.download(file_name)

        # Convert animation to gif
        if file_type == ANIMATION:
            clip = VideoFileClip(tf1.name)
            clip.write_gif(tf2.name, program="ffmpeg", logger=None)
            file_size = os.path.getsize(tf2.name)

            if file_size <= MAX_FILESIZE_DOWNLOAD:
                file_name = tf2.name

        if file_size <= MAX_FILESIZE_DOWNLOAD:
            is_safe = True
            if file_type in [ANIMATION, PHOTO, STICKER] or file.mime_type.startswith(
                "image"
            ):
                is_safe = check_photo(update, context, file_id, file_name, file_type)

            # if is_safe is None or is_safe:
            #     check_file(update, context, file_id, file_name, file_type)

    update_stats(message.chat_id, {file_type: 1})


def check_file(update, context, file_id, file_name, file_type):
    """
    Check if the file is safe or not
    Args:
        update: the update object
        context: the context object
        file_id: the int of the file ID
        file_name: the string of the file name
        file_type: the string of the file type

    Returns:
        None
    """
    message = update.effective_message
    message.chat.send_action(ChatAction.TYPING)
    is_safe, status, matches = scan_file(file_name)
    chat_type = message.chat.type

    if not is_safe:
        threat_type = "contains" if status == FOUND else "may contain"
        if chat_type in (Chat.GROUP, Chat.SUPERGROUP):
            text = (
                f"I've deleted a {file_type} that {threat_type} a virus or malware "
                f"(sent by @{message.from_user.username})."
            )
            filter_msg(update, context, file_id, file_type, text)
        else:
            message.reply_text(
                f"I think it {threat_type} a virus or malware, don't download or open it.",
                quote=True,
            )
    else:
        if chat_type == Chat.PRIVATE:
            if status == OK:
                message.reply_text(
                    "I think it doesn't contain any virus or malware.", quote=True
                )
            else:
                log = Logger()
                log.error(matches)
                message.reply_text("Something went wrong, try again.", quote=True)


def scan_file(file_name=None, file_url=None):
    """
    Scan the file using the API
    Args:
        file_name: the string of the file name
        file_url: the string of the file url

    Returns:
        A tuple of a bool indicating whether the file is safe or not, the status and
        matches from the API call
    """
    is_safe = True
    status = matches = None
    url = "https://beta.attachmentscanner.com/v0.1/scans"
    headers = {"authorization": f"bearer {SCANNER_TOKEN}"}

    if file_name is not None:
        files = {"file": open(file_name, "rb")}
        r = requests.post(url, headers=headers, files=files)
    else:
        json = {"url": file_url}
        r = requests.post(url, headers=headers, json=json)

    if r.status_code == 200:
        results = r.json()
        status = results["status"]

        if status == FAILED:
            matches = results["matches"]

    if status in (FOUND, WARNING):
        is_safe = False

    return is_safe, status, matches
