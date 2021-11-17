# -*- coding: utf-8 -*-
from notion_token import NotionToken
from utils.config import Config
from notion_backup import NotionUp


def start():
    print("Run with configs:")
    print("config = {}".format(Config.to_string()))

    if not Config.username() and not Config.password() and not Config.token_v2():
        raise Exception('username|password or token_v2 should be presented!')

    if Config.username() and Config.password():
        new_token = NotionToken.getNotionToken(Config.username(), Config.password())
        if len(new_token) > 0:
            print("Use new token fetched by username-password.")
            Config.set_token_v2(new_token)

    if Config.action() not in ['all', 'export', 'unzip']:
        raise Exception('unknown action: {}'.format(Config.action()))

    if Config.action() in ['all', 'export']:
        # get backup file
        zips = NotionUp.backup()
        Config.set_zip_files(zips)

    if Config.action() in ['all', 'unzip']:
        # unzip
        NotionUp.unzip()
        # archive files


# Cli cmd example:
# python main.py \
#     --action <acton>
#     --username <token_v2>  # Only when token_v2 is not presented
#     --password <token_v2>  # Only when token_v2 is not presented
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
