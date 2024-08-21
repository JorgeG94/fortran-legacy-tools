#!/usr/bin/python3
import unittest
from io import StringIO
from flowercase import is_hollerith_constant, convert_to_lowercase

class TestFlowercase(unittest.TestCase):

    def test_is_hollerith_constant(self):
        # Test cases for Hollerith constants
        self.assertTrue(is_hollerith_constant("8HCHECK"))
        self.assertTrue(is_hollerith_constant("4HABCD"))
        self.assertFalse(is_hollerith_constant("CHECK"))
        self.assertFalse(is_hollerith_constant("4check"))
        self.assertFalse(is_hollerith_constant("H8CHECK"))
        self.assertFalse(is_hollerith_constant("12XYZ"))

    def test_convert_to_lowercase(self):
        # Test case 1: Simple uppercase conversion
        input_data = "INTEGER FUNCTION MYFUNC()\n"
        expected_output = "integer function myfunc()\n"
        self._run_convert_to_lowercase_test(input_data, expected_output)

        # Test case 2: Mixed case word should remain unchanged
        input_data = "REAL*8 MYVar\n"
        expected_output = "real*8 MYVar\n"
        self._run_convert_to_lowercase_test(input_data, expected_output)

        # Test case 3: Hollerith constant should remain uppercase
        input_data = "DATA MYVAR /8HCHECK/\n"
        expected_output = "data myvar /8HCHECK/\n"
        self._run_convert_to_lowercase_test(input_data, expected_output)

        # Test case 4: Inside a comment, nothing should change
        input_data = "! THIS IS A COMMENT\n"
        expected_output = "! THIS IS A COMMENT\n"
        self._run_convert_to_lowercase_test(input_data, expected_output)

        # Test case 5: String literals should remain unchanged
        input_data = "CALL PRINT('THIS IS A TEST')\n"
        expected_output = "call print('THIS IS A TEST')\n"
        self._run_convert_to_lowercase_test(input_data, expected_output)

        # Test case 6: Multiple lines with different scenarios
        input_data = (
            "INTEGER FUNCTION MYFUNC()\n"
            "! THIS IS A COMMENT\n"
            "DATA MYVAR /8HCHECK/\n"
            "CALL PRINT('THIS IS A TEST')\n"
        )
        expected_output = (
            "integer function myfunc()\n"
            "! THIS IS A COMMENT\n"
            "data myvar /8HCHECK/\n"
            "call print('THIS IS A TEST')\n"
        )
        self._run_convert_to_lowercase_test(input_data, expected_output)

    def _run_convert_to_lowercase_test(self, input_data, expected_output):
        """Helper method to run the convert_to_lowercase tests"""
        stream = StringIO(input_data)
        result = ''.join(convert_to_lowercase(stream))
        self.assertEqual(result, expected_output)

if __name__ == "__main__":
    unittest.main()

