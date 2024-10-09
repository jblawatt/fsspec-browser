import unittest

from app import build_path_links


class BuildPathTest(unittest.TestCase):
    def test_foo(self):
        result = build_path_links("foo/bar/baz".split("/"))
        print(result)
