# -*- coding: utf-8 -*-
from notion_backup import NotionUp
from utils.config import Config


def start():
    print("Run with configs:")
    print("config = {}".format(Config.to_string()))

    if Config.action() in ['all', 'export']:
        # get backup file
        zips = NotionUp.backup()
        Config.set_zip_files(zips)

    if Config.action() in ['all', 'unzip']:
        # unzip
        NotionUp.unzip()

    if Config.action() in ['archive']:
        # re-archive unzipped directories
        import os
        from pathlib import Path
        output_dir = Config.output()
        if os.path.exists(output_dir):
            for item in os.listdir(output_dir):
                item_path = os.path.join(output_dir, item)
                if os.path.isdir(item_path):
                    zip_path = os.path.join(output_dir, f"{item}.zip")
                    NotionUp.archiveDir(item_path, zip_path)


# Cli cmd example:
# python main.py \
#     --action <acton>
#     --token_v2 <token_v2>
#     --username <username>  # Only when token_v2 is not presented
#     --password <password>  # Only when token_v2 is not presented
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
