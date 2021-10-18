# -*- coding: utf-8 -*-

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pkg_resources


class Utils:

    def __init__(self):
        pass

    @staticmethod
    def pwd():
        return os.getcwd()

    @staticmethod
    def get_workspace():
        return str(Path(os.path.dirname(os.path.realpath(__file__))).parent.absolute())

    @staticmethod
    def get_temp_dir():
        return tempfile.gettempdir()

    @staticmethod
    def is_git_directory(path='.'):
        return subprocess.call(
            ['git', '-C', path, 'status'],
            stderr=subprocess.STDOUT,
            stdout=open(os.devnull, 'w')
        ) == 0

    @staticmethod
    def find(array, predicate):
        finds = [it for it in array if predicate(it)]
        return finds

    @staticmethod
    def find_one(array, predicate):
        finds = [it for it in array if predicate(it)]
        if finds:
            return finds[0]
        return finds

    @staticmethod
    def parse_json(file_path):
        with open(file_path) as f:
            data = json.load(f)
        return data

    @staticmethod
    def safe_getattr(obj, name, default_value=None):
        if name in obj:
            return obj[name]
        if hasattr(obj, name):
            return getattr(obj, name)
        return default_value

    @staticmethod
    def get_props(obj):
        return [it for it in dir(obj) if not it.startswith('_')]

    @staticmethod
    def parse_bean(bean, my_dict):
        for prop in Utils.get_props(bean):
            value = Utils.safe_getattr(my_dict, prop)
            if value:
                setattr(bean, prop, value)
        return bean

    @staticmethod
    def paging(array, page, limit):
        page = int(page)
        limit = int(limit)

        if page >= 1 and limit >= 1:
            count_str = limit * (page - 1)  # 0, 20
            count_end = limit * page  # 20, 40
            count_max = len(array)
            if count_end >= count_max:
                count_end = count_max

            print(count_str)
            print(count_end)
            print(count_max)
            array = array[count_str:count_end]

        return array

    @staticmethod
    def assert_property_presented(item, properties):
        props = []
        if isinstance(properties, list):
            props = properties
        else:
            props.append(properties)

        for key in props:
            if key not in item:
                raise Exception('\'{}\' is not given: {}'.format(key, item))

    @staticmethod
    def check_property_presented(item, properties):
        props = []
        if isinstance(properties, list):
            props = properties
        else:
            props.append(properties)

        result = True
        for key in props:
            if key not in item:
                print('\'{}\' is not given: {}'.format(key, item))
                result = False
        return result

    @staticmethod
    def check_module_installed(name):
        try:
            pkg_resources.get_distribution(name)
            return True
        except pkg_resources.DistributionNotFound:
            return False

    @staticmethod
    def is_unittest():
        return 'unittest' in sys.modules.keys()


class FileUtils:
    @staticmethod
    def new_file(file_dir, file_name):
        return os.path.join(file_dir, file_name)

    @staticmethod
    def exists(file_path):
        return Path(file_path).exists()

    @staticmethod
    def create_file(file_path, fore=False):
        path = Path(file_path)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch(exist_ok=True)

        if path.is_dir():
            if not fore:
                raise Exception("{} is dir".format(file_path))
            shutil.rmtree(path.absolute())
            path.touch(exist_ok=True)

    @staticmethod
    def create_dir(file_path, fore=False):
        path = Path(file_path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            return
        if path.is_file():
            if not fore:
                raise Exception("{} is file".format(file_path))
            os.remove(path.absolute())
            path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def clean_dir(file_path, fore=False):
        FileUtils.delete_dir(file_path, fore)
        FileUtils.create_dir(file_path, fore)

    @staticmethod
    def delete_dir(file_path, fore=False):
        path = Path(file_path)
        if path.is_file():
            if not fore:
                raise Exception("{} is file".format(file_path))
            os.remove(path.absolute())
            return
        if path.exists():
            shutil.rmtree(file_path)

    @staticmethod
    def delete(file_path):
        path = Path(file_path)
        if path.is_file():
            os.remove(path.absolute())
            return
        if path.exists():
            shutil.rmtree(file_path)

    @staticmethod
    def write_text(text, file_path, mode="w+"):
        with open(file_path, mode) as f:
            f.write(text)

