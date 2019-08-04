# Telegram Group Defender

[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://t.me/grpdefbot)
[![Telegram Channel](https://img.shields.io/badge/Telegram-Channel-blue.svg)](https://t.me/grpdefbotdev)
[![MIT License](https://img.shields.io/github/license/zeshuaro/telegram-group-defender.svg)](https://github.com/zeshuaro/telegram-group-guardian/blob/master/LICENSE)

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/068e749cb48343d08811e20a15af6696)](https://www.codacy.com/app/zeshuaro/telegram-group-defender?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=zeshuaro/telegram-group-defender&amp;utm_campaign=Badge_Grade)

A PDF utility bot on Telegram that can:

* Filter files and links that may contain virus or malwares\n
* Filter photos and links of photos that are NSFW

## Getting Started

### Prerequisites

Run the following command to install the required packages:

```bash
pip install -r requirements.txt
```

The bot uses [Google Cloud Vision](https://cloud.google.com/vision/) to check for inappropriate content in images, 
[Google Safe Browsing](https://developers.google.com/safe-browsing/) to check for threats in links, and
 [Attachment Scanner](http://www.attachmentscanner.com/) to scan for virus and malware.

### Setup Your Environment Variables

Make a .env file and put your telegram token in there. Below is an example:

```bash
TELE_TOKEN="telegram_token"
SCANNER_TOKEN="scanner_token"
GOOGLE_TOKEN="google_token"
```

### Running The Bot

You can then start the bot with the following command:

```bash
python bot.py
```