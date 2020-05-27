import unittest

from lib import utils


class TestUtils(unittest.TestCase):

    def test_combine_dicts_with_list_values(self):
        extended = {"1": ["1", "2", "3"],
                    "2": ["4", "5", "6"]}
        added = {"3": ["8", "9"],
                 "2": ["4", "5", "6", "7"]}

        utils.combine_dicts_with_list_values(extended, added)
        # Note after combining lists, the original order is not preserved
        extended.get("1").sort()
        extended.get("2").sort()
        extended.get("3").sort()
        self.assertEqual(extended.get("1"), ["1", "2", "3"])
        self.assertEqual(extended.get("2"), ["4", "5", "6", "7"])
        self.assertEqual(extended.get("3"), ["8", "9"])


if __name__ == '__main__':
    unittest.main()
