# -*- coding: utf-8 -*-

from utils.config import Config
from notion_backup import NotionUp


def start():
    print("Run with configs:")
    print("config = {}".format(Config.to_string()))
    # get backup file
    zips = NotionUp.backup()
    # unzip
    NotionUp.unzip(zips)
    # archive files


# Cli cmd example:
# python main.py \
#     --token_v2 <token_v2>
# or
# python main.py \
#     --config_file '.config_file.json'
#
if __name__ == '__main__':
    Config.parse_configs()
    Config.check_required_args()
    Config.check_required_modules()

    print('\nHello, NotionDown!\n')
    start()
