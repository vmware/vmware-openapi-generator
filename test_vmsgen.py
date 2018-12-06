import vmsgen
import unittest
from unittest import mock as mock


class TestVmsGen(unittest.TestCase):

    def test_tags_generation_from_short_name(self):
        expected = ['']
        vmsgen.TAG_SEPARATOR = ''
        actual = vmsgen.tags_from_service_name('three.levels.deep')
        self.assertEqual(expected, actual)

    def test_tags_generation_from_proper_name(self):
        expected = ['levels_deep']
        vmsgen.TAG_SEPARATOR = '_'
        actual = vmsgen.tags_from_service_name('more.than.three.levels.deep')
        self.assertEqual(expected, actual)

    def test_default_ssl_security_option(self):
        test_args = ['vmsgen', '-vc', 'v_url']
        ssl_verify_expected = True
        with mock.patch('sys.argv', test_args):
            _, _, _, ssl_verify_actual = vmsgen.get_input_params()
        self.assertEqual(ssl_verify_expected, ssl_verify_actual)

    def test_setting_insecure_ssl_security_option(self):
        test_args = ['vmsgen', '-vc', 'v_url', '-k']
        ssl_verify_expected = False
        with mock.patch('sys.argv', test_args):
            _, _, _, ssl_verify_actual = vmsgen.get_input_params()
        self.assertEqual(ssl_verify_expected, ssl_verify_actual)

    def test_default_tag_separator_option(self):
        test_args = ['vmsgen', '-vc', 'v_url', '-k']
        tag_separator_expected = '/'
        with mock.patch('sys.argv', test_args):
            vmsgen.get_input_params()
        self.assertEqual(tag_separator_expected, vmsgen.TAG_SEPARATOR)

    def test_tag_separator_option(self):
        expected = '_'
        test_args = ['vmsgen', '-vc', 'v_url', '-s', expected]
        with mock.patch('sys.argv', test_args):
            vmsgen.get_input_params()
        self.assertEqual(expected, vmsgen.TAG_SEPARATOR)

    def test_default_operation_id_option(self):
        test_args = ['vmsgen', '-vc', 'v_url', '-k']
        generate_op_id_expected = False
        with mock.patch('sys.argv', test_args):
            vmsgen.get_input_params()
        self.assertEqual(generate_op_id_expected, vmsgen.GENERATE_UNIQUE_OP_IDS)

    def test_operation_id_option(self):
        generate_op_id_expected = True
        test_args = ['vmsgen', '-vc', 'v_url', '-k', '-uo']
        with mock.patch('sys.argv', test_args):
            vmsgen.get_input_params()
        self.assertEqual(generate_op_id_expected, vmsgen.GENERATE_UNIQUE_OP_IDS)


if __name__ == '__main__':
    unittest.main()
