#!/usr/bin/env python
# -*- coding: utf-8 -*-


import configparser
import logging
import os
import subprocess

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, RegexHandler

from helpers.delugehelper import DelugeHelper

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Getting configurations
config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), 'config.cfg'))
users = config['CONFIG']['id'].split(',')

# Connecting to deluge daemon
torrent = DelugeHelper(config['DELUGE_CONFIG']['deluged_ip'], config['DELUGE_CONFIG']['deluged_port'],
                       config['DELUGE_CONFIG']['deluged_user'], config['DELUGE_CONFIG']['deluged_pass'])


# Handlers
def start(bot, update):
    if str(update.message.from_user.id) in users:
        keyboard = [[InlineKeyboardButton("Raspberry status", callback_data='status_raspberry'),
                     InlineKeyboardButton("Torrent status", callback_data='status_torrent')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text('Main menu:', reply_markup=reply_markup)


def action(bot, update):
    query = update.callback_query

    if str(query.from_user.id) in users:
        # Defining menu keyboard
        menu_keyboard = [[InlineKeyboardButton("Raspberry status", callback_data='status_raspberry'),
                          InlineKeyboardButton("Torrent status", callback_data='status_torrent')]]
        menu_reply_markup = InlineKeyboardMarkup(menu_keyboard)
        # Defining torrent status menu
        torrent_keyboard = [[InlineKeyboardButton("Downloading torrents", callback_data='torrent_downloading'),
                             InlineKeyboardButton("Finished torrents", callback_data='torrent_finished')],
                            [InlineKeyboardButton("Delete torrents", callback_data='torrent_delete')],
                            [InlineKeyboardButton("Back to main menu", callback_data='menu')]]
        torrent_reply_markup = InlineKeyboardMarkup(torrent_keyboard)

        if query.data == "menu":
            query.message.edit_text('Choose option:', reply_markup=menu_reply_markup)
        elif query.data == "status_raspberry":
            bot.edit_message_text(text=str(subprocess.check_output([os.path.join(os.path.dirname(__file__),
                                                                                 'status_raspberry.sh')]), 'utf-8'),
                                  chat_id=query.message.chat_id,
                                  message_id=query.message.message_id)
            query.message.reply_text('Choose option:', reply_markup=menu_reply_markup)
        elif query.data == "status_torrent":
            query.message.edit_text('Choose option:', reply_markup=torrent_reply_markup)
        elif query.data == "torrent_downloading":
            bot.edit_message_text(text=torrent.get_active_torrents(),
                                  chat_id=query.message.chat_id,
                                  message_id=query.message.message_id)
            query.message.reply_text('Choose option:', reply_markup=torrent_reply_markup)
        elif query.data == "torrent_finished":
            bot.edit_message_text(text=torrent.get_finished_torrents(),
                                  chat_id=query.message.chat_id,
                                  message_id=query.message.message_id)
            query.message.reply_text('Choose option:', reply_markup=torrent_reply_markup)
        elif query.data == "torrent_delete":
            bot.edit_message_text(text=torrent.get_torrents_to_delete(),
                                  chat_id=query.message.chat_id,
                                  message_id=query.message.message_id)


def download(bot, update):
    if str(update.message.from_user.id) in users:
        update.message.reply_text(
            torrent.add_torrent(update.message.text, config['DELUGE_CONFIG']['download_location']))


def delete(bot, update):
    if str(update.message.from_user.id) in users:
        torrent_id = update.message.text.split('_', maxsplit=1)[1]
        update.message.reply_text(torrent.delete_torrent(torrent_id))


# Error handler
def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"' % (update, error))


def main():
    updater = Updater(config['CONFIG']['token'])
    dp = updater.dispatcher

    # Handlers
    dp.add_handler(CommandHandler("start", start))
    updater.dispatcher.add_handler(CallbackQueryHandler(action))
    dp.add_handler(RegexHandler('magnet:\?', download))
    dp.add_handler(RegexHandler('/del_', delete))

    # Log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
