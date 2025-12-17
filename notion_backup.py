import json
import shutil
import time
import zipfile
from pathlib import Path
from typing import List

import requests
from slugify import slugify

from notion_token import NotionToken
from utils.config import Config
from utils.utils import FileUtils


class NotionUp:

    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    def getToken():
        if not Config.username() and not Config.password() and not Config.token_v2():
            raise Exception('username|password or token_v2 should be presented!')

        if Config.username() and Config.password():
            new_token = NotionToken.getNotionToken(Config.username(), Config.password())
            if len(new_token) > 0:
                print("Use new token fetched by username-password.")
                Config.set_token_v2(new_token)
        return Config.token_v2()

    @staticmethod
    def exportTask(spaceId):
        return {
            'task': {
                'eventName': "exportSpace",
                'request': {
                    'spaceId': spaceId,
                    'exportOptions': {
                        'exportType': 'markdown',
                        'timeZone': Config.notion_timezone(),
                        'locale': Config.notion_locale(),
                    }
                }
            }
        }

    @staticmethod
    def requestPost(endpoint: str, params: object):
        cookie = f'token_v2={NotionUp.getToken()}; '
        if Config.file_token():
            cookie += f'file_token={Config.file_token()}; '

        response = requests.post(
            f'{Config.notion_api()}/{endpoint}',
            data=json.dumps(params).encode('utf8'),
            headers={
                'content-type': 'application/json',
                'cookie': cookie
            },
        )

        return response.json()

    @staticmethod
    def getUserContent():
        return NotionUp.requestPost("loadUserContent", {})["recordMap"]

    @staticmethod
    def waitForExportedUrl(taskId, spaceId=None):
        print('Polling for export task: {}'.format(taskId))
        success_no_url_retries = 0
        wait_interval = 10
        max_retries = Config.wait_timeout() // wait_interval

        while True:
            res = NotionUp.requestPost('getTasks', {'taskIds': [taskId]})
            tasks = res.get('results')
            task = next(t for t in tasks if t['id'] == taskId)
            
            if task['state'] == 'success':
                # Try finding exportURL in various locations in the task object
                url = task.get('status', {}).get('exportURL')
                if not url:
                    url = task.get('result', {}).get('exportURL')
                if not url:
                    url = task.get('exportURL')
                
                if url:
                    print('\n' + url)
                    break
                
                # If URL still missing, check getNotificationLog (V1)
                print(f'\n[DEBUG] Task success but exportURL missing. Checking getNotificationLog...')
                try:
                    notification_res = NotionUp.requestPost('getNotificationLog', {'spaceId': spaceId} if spaceId else {})
                    url = NotionUp._parse_notification_log(notification_res, spaceId)
                except Exception as e:
                    print(f'\n[DEBUG] Failed to check getNotificationLog: {e}')

                # If URL still missing, check getNotificationLogV2 (V2)
                if not url:
                    print(f'\n[DEBUG] URL not found in V1 log. Checking getNotificationLogV2...')
                    try:
                        payload = {
                            'spaceId': spaceId,
                            'size': 20,
                            'type': 'unread_and_read',
                            'variant': 'no_grouping'
                        }
                        notification_res_v2 = NotionUp.requestPost('getNotificationLogV2', payload)
                        url = NotionUp._parse_notification_log(notification_res_v2, spaceId)
                    except Exception as e:
                        print(f'\n[DEBUG] Failed to check getNotificationLogV2: {e}')

                if url:
                    print('\n' + url)
                    break
                else:
                    # Task success but URL missing. Retry.
                    success_no_url_retries += 1
                    if success_no_url_retries > max_retries:
                        print(f'\n[DEBUG] Task success but exportURL missing after {max_retries} retries. Task: {json.dumps(task)}')
                        raise Exception('Export URL not found in success response after timeout.')
                    
                    print(f'\n[INFO] Task state is success but exportURL is not yet available. Retrying... (Attempt {success_no_url_retries}/{max_retries})')
                    time.sleep(wait_interval)
            else:
                print('.', end="", flush=True)
                time.sleep(wait_interval)
        return url

    @staticmethod
    def _parse_notification_log(response, spaceId=None):
        activities = response.get('recordMap', {}).get('activity', {})
        found_exports = []
        for act_id, act_item in activities.items():
            # Structure: value -> value -> type
            act_value = act_item.get('value', {}).get('value', {})
            if act_value.get('type') == 'export-completed':
                # Check spaceId match if provided
                if spaceId and act_value.get('space_id') != spaceId:
                    continue
                
                # Extract URL from edits
                edits = act_value.get('edits', [])
                if edits and edits[0].get('link'):
                    found_exports.append({
                        'url': edits[0].get('link'),
                        'timestamp': int(act_value.get('end_time', 0))
                    })
        
        # Sort by timestamp descending (newest first)
        found_exports.sort(key=lambda x: x['timestamp'], reverse=True)
        
        if found_exports:
            url = found_exports[0]['url']
            print(f'\n[DEBUG] Found URL from notification log: {url}')
            return url
        return None

    @staticmethod
    def downloadFile(url, filename) -> str:
        file = FileUtils.new_file(Config.output(), filename)
        FileUtils.create_file(file)
        with requests.get(url, stream=True) as r:
            with open(file, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
        return file

    @staticmethod
    def backup() -> List[str]:
        zips = []
        # tokens
        userContent = NotionUp.getUserContent()
        userId = list(userContent["notion_user"].keys())[0]
        print(f"User id: {userId}")

        # list spaces
        spaces = [(space_id, space_details["value"]["name"]) for (space_id, space_details) in userContent["space"].items()]
        print("Available spaces total: {}".format(len(spaces)))
        for (spaceId, spaceName) in spaces:
            print(f"\nexport space: {spaceId}, {spaceName}")
            # request export task
            taskId = NotionUp.requestPost('enqueueTask', NotionUp.exportTask(spaceId)).get('taskId')
            # get exported file url and download
            url = NotionUp.waitForExportedUrl(taskId, spaceId)
            filename = slugify(f'{spaceName}-{spaceId}') + '.zip'
            print('download exported zip: {}, {}'.format(url, filename))
            filePath = NotionUp.downloadFile(url, filename)
            zips.append(filePath)
            break
        return zips

    @staticmethod
    def unzipFile(filePath: str, saveDir: str = None):
        try:
            if not saveDir:
                saveDir = FileUtils.new_file(Config.output(), Path(filePath).name.replace('.zip', ''))
            FileUtils.clean_dir(saveDir)

            file = zipfile.ZipFile(filePath)
            file.extractall(saveDir)
            file.close()
            return saveDir
        except Exception as e:
            print(f'{filePath} unzip fail,{str(e)}')

    @staticmethod
    def unzip():
        for file in Config.zip_files():
            print('unzip exported zip: {}'.format(file))
            NotionUp.unzipFile(file)

