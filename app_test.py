from unittest import TestCase

from app import (DirInfoDict, build_path_links, count_items_by_key_value,
                 to_dir_info_context_item)


class BuildPathLinksTestCase(TestCase):
    def test_default(self):
        result = build_path_links(str("foo/bar/baz").split("/"))
        self.assertEqual(
            result,
            [
                {"name": "foo", "href": "/foo"},
                {"name": "bar", "href": "/foo/bar"},
                {"name": "baz", "href": "/foo/bar/baz"},
            ],
        )

    def test_quote(self):
        result = build_path_links(str("öäü/!&?/baz").split("/"))
        self.assertEqual(
            result,
            [
                {"name": "öäü", "href": "/%C3%B6%C3%A4%C3%BC"},
                {"name": "!&?", "href": "/%C3%B6%C3%A4%C3%BC/%21%26%3F"},
                {"name": "baz", "href": "/%C3%B6%C3%A4%C3%BC/%21%26%3F/baz"},
            ],
        )


class CountItemsByKeyValueTestCase(TestCase):

    def test_count_file(self):
        self.assertEqual(
            count_items_by_key_value(
                [
                    {
                        "type": "directory",
                        "name": "foo",
                    },
                    {
                        "type": "directory",
                        "name": "bar",
                    },
                    {
                        "type": "file",
                        "name": "baz",
                    },
                ],
                "type",
                "file",
            ),
            1,
        )

    def test_count_directory(self):
        self.assertEqual(
            count_items_by_key_value(
                [
                    {
                        "type": "directory",
                        "name": "foo",
                    },
                    {
                        "type": "directory",
                        "name": "bar",
                    },
                    {
                        "type": "file",
                        "name": "baz",
                    },
                ],
                "type",
                "directory",
            ),
            2,
        )


class ToDirInfoContextItemTestCase(TestCase):
    def test_default(self):
        in_: DirInfoDict = {
            "name": "/foo/bar/baz.pdf",
            "type": "file",
        }

        out_ = to_dir_info_context_item(
            in_,
            "/foo/bar",
            "/",
        )

        self.assertEqual(
            out_,
            {
                **in_,
                "name": "baz.pdf",
                "url": "/foo/bar/baz.pdf",
                "dirname": "/foo/bar",
            },
        )

    def test_quote(self):
        in_: DirInfoDict = {
            "name": "/foo/öäü/!&?.pdf",
            "type": "file",
        }

        out_ = to_dir_info_context_item(
            in_,
            "/foo/öäü",
            "/",
        )

        self.assertEqual(
            out_,
            {
                **in_,
                "name": "!&?.pdf",
                "url": "/foo/%C3%B6%C3%A4%C3%BC/%21%26%3F.pdf",
                "dirname": "/foo/öäü",
            },
        )
