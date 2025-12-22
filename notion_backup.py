import json
import os
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
        if Config.token_v2():
            return Config.token_v2()

        if not Config.username() or not Config.password():
            raise Exception('username|password or token_v2 should be presented!')

        new_token = NotionToken.getNotionToken(Config.username(), Config.password())
        if len(new_token) > 0:
            print("Use new token fetched by username-password.")
            Config.set_token_v2(new_token)
            return new_token
        
        raise Exception('Failed to fetch token from username/password')

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
        # Set a cutoff time (current time - 10 minutes buffer) to filter out stale exports
        min_timestamp = int(time.time() * 1000) - (10 * 60 * 1000)
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
                    url = NotionUp._parse_notification_log(notification_res, spaceId, min_timestamp)
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
                        url = NotionUp._parse_notification_log(notification_res_v2, spaceId, min_timestamp)
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
    def _get_export_list(response, spaceId=None):
        activities = response.get('recordMap', {}).get('activity', {})
        found_exports = []
        for act_id, act_item in activities.items():
            # Structure: 
            # V1: value -> value -> type
            # V2: value -> type
            act_value = act_item.get('value', {})
            if act_value.get('value'):
                act_value = act_value.get('value')
            
            if act_value.get('type') == 'export-completed':
                # Check spaceId match if provided
                if spaceId and act_value.get('space_id') != spaceId:
                    continue
                
                # Extract URL from edits
                edits = act_value.get('edits', [])
                if edits and edits[0].get('link'):
                    # V2 uses 'start_time' or 'end_time' directly in the value object
                    timestamp = act_value.get('end_time') or act_value.get('start_time', 0)
                    found_exports.append({
                        'url': edits[0].get('link'),
                        'timestamp': int(timestamp)
                    })
        
        # Sort by timestamp descending (newest first)
        found_exports.sort(key=lambda x: x['timestamp'], reverse=True)
        return found_exports

    @staticmethod
    def _parse_notification_log(response, spaceId=None, min_timestamp=0):
        found_exports = NotionUp._get_export_list(response, spaceId)
        if found_exports:
            # Filter exports older than min_timestamp
            latest_export = found_exports[0]
            if latest_export['timestamp'] >= min_timestamp:
                url = latest_export['url']
                print(f'\n[DEBUG] Found URL from notification log: {url}')
                return url
            else:
                elapsed_hrs = (int(time.time() * 1000) - latest_export['timestamp']) / (1000 * 3600)
                print(f'\n[DEBUG] Found export in log but it is too old ({elapsed_hrs:.2f} hours). Ignoring.')
        return None

    @staticmethod
    def findRecentExport(spaceId):
        print(f'Checking for recent exports for space: {spaceId}')
        try:
            # Check V2 first
            payload = {
                'spaceId': spaceId,
                'size': 20,
                'type': 'unread_and_read',
                'variant': 'no_grouping'
            }
            notification_res_v2 = NotionUp.requestPost('getNotificationLogV2', payload)
            found_exports = NotionUp._get_export_list(notification_res_v2, spaceId)
            
            if not found_exports:
                # Fallback to V1
                notification_res_v1 = NotionUp.requestPost('getNotificationLog', {'spaceId': spaceId} if spaceId else {})
                found_exports = NotionUp._get_export_list(notification_res_v1, spaceId)
                
            if found_exports:
                latest = found_exports[0]
                url = latest['url']
                timestamp = latest['timestamp']
                
                now_ms = int(time.time() * 1000)
                elapsed_hrs = (now_ms - timestamp) / (1000 * 3600)
                
                if elapsed_hrs < 24:
                    print(f'[INFO] Found a valid recent export ({elapsed_hrs:.2f} hours old). Skipping new export.')
                    return url
                else:
                    print(f'[DEBUG] Found export but it is too old ({elapsed_hrs:.2f} hours old).')
        except Exception as e:
            print(f'[DEBUG] Failed to check for recent exports: {e}')
        return None

    @staticmethod
    def downloadFile(url, filename) -> str:
        file = FileUtils.new_file(Config.output(), filename)
        FileUtils.create_file(file)
        
        cookie = f'token_v2={NotionUp.getToken()}; '
        if Config.file_token():
            cookie += f'file_token={Config.file_token()}; '

        headers = {
            'cookie': cookie,
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        print(f'Downloading from {url}')
        with requests.get(url, stream=True, headers=headers) as r:
            if r.status_code != 200:
                print(f'\n[ERROR] Download failed with status {r.status_code}')
                print(f'Response snippet: {r.text[:1000]}')
                raise Exception(f'Download failed with status {r.status_code}')
            
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
            
            # 1. Check for recent export
            url = NotionUp.findRecentExport(spaceId)
            
            if not url:
                # 2. No recent export, request new export task
                print("No recent export found. Requesting new export task...")
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

            zip_size = os.path.getsize(filePath)
            print(f'Unzipping {filePath} ({zip_size} bytes) to {saveDir}...')
            
            with zipfile.ZipFile(filePath) as z:
                file_list = z.namelist()
                print(f'Zip contains {len(file_list)} items: {file_list[:10]}...')
                z.extractall(saveDir)
            
            # Delete original zip after extraction to avoid duplicates in archives
            print(f'Deleting original zip: {filePath}')
            os.remove(filePath)

            # Recursive unzip for nested zips (Notion often nests Part-1.zip etc.)
            for root, dirs, files in os.walk(saveDir):
                for file in files:
                    if file.endswith('.zip'):
                        nested_path = os.path.join(root, file)
                        print(f'Found nested zip: {nested_path}. Extracting...')
                        # Extract nested zip into the SAME directory
                        with zipfile.ZipFile(nested_path) as nz:
                            nz.extractall(root)
                        os.remove(nested_path)

            return saveDir
        except Exception as e:
            print(f'{filePath} unzip fail,{str(e)}')

    @staticmethod
    def archiveDir(dirPath: str, zipPath: str):
        try:
            print(f'Archiving {dirPath} to {zipPath}...')
            # shutil.make_archive takes base_name without .zip
            base_name = zipPath.replace('.zip', '')
            shutil.make_archive(base_name, 'zip', dirPath)
            return zipPath
        except Exception as e:
            print(f'Archive {dirPath} fail: {str(e)}')
            return None

    @staticmethod
    def unzip():
        for file in Config.zip_files():
            print('unzip exported zip: {}'.format(file))
            NotionUp.unzipFile(file)

