import unittest

from lib import utils


class TestUtils(unittest.TestCase):

    def test_combine_dicts_with_list_values(self):
        extended = {"1": ["1", "2", "3"],
                    "2": ["4", "5", "6"]}
        added = {"3": ["8", "9"],
                 "2": ["4", "5", "6", "7"]}
        expected = {"1": ["1", "2", "3"],
                    "2": ["4", "5", "6", "7"],
                    "3": ["8", "10"]}
        utils.combine_dicts_with_list_values(extended, added)

        self.assertEqual(extended.get("1").sort(), expected.get("1").sort())
        self.assertEqual(extended.get("2").sort(), expected.get("2").sort())
        self.assertEqual(extended.get("3").sort(), expected.get("3").sort())


if __name__ == '__main__':
    unittest.main()
