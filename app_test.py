import os
from typing import cast
from unittest import TestCase, mock

import fsspec
from fastapi.testclient import TestClient
from fsspec.implementations.dirfs import DirFileSystem

from app import (DirInfoDict, Settings, app, build_path_links,
                 count_items_by_key_value, dep_fs, matches_pattern,
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


def dep_fs_test():
    return DirFileSystem("testdata", fsspec.filesystem("file"))


class IndexViewPlanTestCase(TestCase):

    def setUp(self):
        app.dependency_overrides[dep_fs] = dep_fs_test
        self.client = TestClient(app)

    def test_default(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("content-type"),
            "text/html; charset=utf-8",
        )

    def test_format_html(self):
        response = self.client.get("/?format=html")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("content-type"),
            "text/html; charset=utf-8",
        )

    def test_format_json(self):
        response = self.client.get("/?format=json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("content-type"),
            "application/json",
        )

    def test_favicon_fallback(self):
        response = self.client.get("/favicon.ico")
        self.assertEqual(response.status_code, 404)

    def test_not_exists(self):
        response = self.client.get("/file-not-found.txt")
        self.assertEqual(response.status_code, 404)

    def test_test_txt(self):
        response = self.client.get("/test.txt")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "lorem ipsum\n")
        self.assertEqual(
            response.headers.get("content-type"),
            "text/plain; charset=utf-8",
        )


class MatchPatternTest(TestCase):

    def test__default(self):
        self.assertTrue(matches_pattern("foo/bar/baz.pdf", ["*.pdf"]))
        self.assertTrue(not matches_pattern("foo/bar/baz.pdf", ["*.py"]))
        self.assertTrue(matches_pattern("foo/bar/baz.pdf", ["foo/**/*"]))


class DepFsSpecTestCase(TestCase):

    @mock.patch.dict(os.environ, {"FSSPEC_BROWSER_DOCUMENT_ROOT": "file:///foo"})
    def test__default(self):
        settings = Settings()  # noqa
        fs: DirFileSystem = cast(DirFileSystem, dep_fs(settings))
        self.assertEqual(fs.path, "/foo")
