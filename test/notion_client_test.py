import os
import unittest

from notion_token import NotionToken


class NotionClientTest(unittest.TestCase):

    def test_check_env(self):
        self.assertTrue("NOTION_USERNAME" in os.environ)
        self.assertTrue("NOTION_PASSWORD" in os.environ)

    def test_get_token_v2(self):
        self.test_check_env()
        token = NotionToken.getNotionToken(
            os.environ['NOTION_USERNAME'],
            os.environ['NOTION_PASSWORD']
        )
        self.assertTrue(len(token) > 0, "get token: {}".format(token))


