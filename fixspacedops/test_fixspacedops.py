#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Unit tests for fixspacedops.py"""

import unittest
from fixspacedops import fix_code, fix_lines


def code(text):
    """Helper: run fix_code on a bare code fragment."""
    return fix_code(text)[0]


def count(text):
    return fix_code(text)[1]


class TestOperators(unittest.TestCase):

    def test_space_after_dot(self):
        self.assertEqual(code("IF(DONE. AND. IERR3.NE.0) THEN"),
                         "IF(DONE.AND. IERR3.NE.0) THEN")

    def test_spaces_both_sides(self):
        self.assertEqual(code("IF(T2X25 . GT . C4) GO TO 80"),
                         "IF(T2X25 .GT. C4) GO TO 80")

    def test_space_inside_name(self):
        self.assertEqual(code("IF(A .A ND. B)"), "IF(A .AND. B)")

    def test_already_tight_is_untouched(self):
        self.assertEqual(count("IF(A.AND.B)"), 0)

    def test_logical_literals(self):
        self.assertEqual(code("X = . TRUE ."), "X = .TRUE.")
        self.assertEqual(code("Y = . FALSE ."), "Y = .FALSE.")

    def test_lowercase(self):
        self.assertEqual(code("if(a . and . b)"), "if(a .and. b)")

    def test_counts_each_rewrite(self):
        self.assertEqual(count("IF(A . AND . B . OR . C)"), 2)

    def test_unknown_dotted_name_left_alone(self):
        # a defined operator, or an unrelated pair of dots
        self.assertEqual(count("X = A . CROSS . B"), 0)

    def test_reals_are_not_operators(self):
        self.assertEqual(count("X = 1.0 + 2.0"), 0)
        self.assertEqual(count("X = 1.0D+00"), 0)


class TestTextIsPreserved(unittest.TestCase):

    def test_string_content_untouched(self):
        src = "WRITE(6,*) 'USE . AND . HERE'"
        self.assertEqual(count(src), 0)
        self.assertEqual(code(src), src)

    def test_doubled_quote_inside_string(self):
        src = "WRITE(6,*) 'IT''S . OR . FINE'"
        self.assertEqual(count(src), 0)

    def test_double_quoted_string(self):
        src = 'WRITE(6,*) "A . EQ . B"'
        self.assertEqual(count(src), 0)

    def test_code_after_string_still_fixed(self):
        self.assertEqual(code("IF(S.EQ.'X' . AND . T) GO TO 1"),
                         "IF(S.EQ.'X' .AND. T) GO TO 1")

    def test_hollerith_payload_untouched(self):
        # payload holds an apostrophe: the Cs irrep label A'
        src = "DATA GANT/8HA       ,8HAG      ,8HA'      ,"
        self.assertEqual(count(src), 0)

    def test_operator_after_hollerith_with_apostrophe(self):
        # the apostrophe inside the payload must not desynchronise the scan
        src = "DATA X/8HA'      / ! keep"
        self.assertEqual(count(src), 0)

    def test_hollerith_containing_dots(self):
        src = "CALL FOO(5H. OR ., N)"
        self.assertEqual(count(src), 0)

    def test_inline_comment_untouched(self):
        src = "X = A ! use . AND . later"
        self.assertEqual(count(src), 0)


class TestLineHandling(unittest.TestCase):

    def test_comment_lines_skipped(self):
        for marker in 'cC*!':
            lines = [marker + " use . AND . here\n"]
            self.assertEqual(fix_lines(lines)[1], 0)

    def test_preprocessor_line_skipped(self):
        self.assertEqual(fix_lines(["#ifdef . AND .\n"])[1], 0)

    def test_columns_1_to_6_preserved(self):
        lines = ["  100 IF(A . EQ . B) GO TO 200\n"]
        new, n = fix_lines(lines)
        self.assertEqual(n, 1)
        self.assertTrue(new[0].startswith("  100 "))

    def test_past_column_72_preserved(self):
        body = "      IF(A . EQ . B) GO TO 200"
        line = body.ljust(72) + "TRAILING\n"
        new, n = fix_lines([line])
        self.assertEqual(n, 1)
        self.assertTrue(new[0].rstrip('\n').endswith("TRAILING"))

    def test_line_only_gets_shorter(self):
        line = "      IF(A . EQ . B) GO TO 200\n"
        new, _ = fix_lines([line])
        self.assertLess(len(new[0]), len(line) + 1)

    def test_operator_beyond_column_72_untouched(self):
        line = "      X = 1".ljust(72) + " . AND .\n"
        self.assertEqual(fix_lines([line])[1], 0)

    def test_blank_line(self):
        self.assertEqual(fix_lines(["\n"])[1], 0)

    def test_unchanged_lines_are_identical(self):
        lines = ["      X = 1\n", "C comment\n"]
        new, n = fix_lines(lines)
        self.assertEqual(n, 0)
        self.assertEqual(new, lines)


class TestSpacedNumericLiterals(unittest.TestCase):

    def test_space_before_exponent(self):
        self.assertEqual(code("X = 0.000 D+00"), "X = 0.000D+00")

    def test_space_after_exponent_letter(self):
        self.assertEqual(code("X = 1.5D +3"), "X = 1.5D+3")

    def test_spaces_everywhere(self):
        self.assertEqual(code("X = 1.5 D + 3"), "X = 1.5D+3")

    def test_already_tight(self):
        self.assertEqual(count("X = 1.0D0"), 0)

    def test_identifier_after_comma_untouched(self):
        self.assertEqual(count("CALL SUB(N, EPS)"), 0)

    def test_operator_between_untouched(self):
        self.assertEqual(count("X = 2 * EPS"), 0)

    def test_data_repeat_count_untouched(self):
        self.assertEqual(count("DATA X/2*0.0D0/"), 0)

    def test_inside_string_untouched(self):
        self.assertEqual(count("WRITE(6,*) 'A 1 D+00 B'"), 0)

    def test_tail_past_column_72_does_not_slide_in(self):
        body = "      X = 0.000 D+00"
        line = body.ljust(72) + "TAIL\n"
        new, n = fix_lines([line])
        self.assertEqual(n, 1)
        # the tail must still begin at column 73
        self.assertEqual(new[0][72:].rstrip('\n'), "TAIL")


if __name__ == "__main__":
    unittest.main()
