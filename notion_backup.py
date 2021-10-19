import json
import shutil
import time
import zipfile
from pathlib import Path
from typing import List

import requests
from slugify import slugify

from utils.config import Config
from utils.utils import FileUtils


class NotionUp:

    def __init__(self) -> None:
        super().__init__()

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
        response = requests.post(
            f'{Config.notion_api()}/{endpoint}',
            data=json.dumps(params).encode('utf8'),
            headers={
                'content-type': 'application/json',
                'cookie': f'token_v2={Config.token_v2()}; '
            },
        )

        return response.json()

    @staticmethod
    def getUserContent():
        return NotionUp.requestPost("loadUserContent", {})["recordMap"]

    @staticmethod
    def waitForExportedUrl(taskId):
        print('Polling for export task: {}'.format(taskId))
        while True:
            res = NotionUp.requestPost('getTasks', {'taskIds': [taskId]})
            tasks = res.get('results')
            task = next(t for t in tasks if t['id'] == taskId)
            if task['state'] == 'success':
                url = task['status']['exportURL']
                print('\n' + url)
                break
            else:
                print('.', end="", flush=True)
                time.sleep(10)
        return url

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
            url = NotionUp.waitForExportedUrl(taskId)
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

