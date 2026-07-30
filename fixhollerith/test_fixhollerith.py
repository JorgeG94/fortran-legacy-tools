#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Unit tests for fixhollerith.py"""

import unittest
from fixhollerith import convert_fragment, convert_lines, quote, code_part


def conv(text):
    return convert_fragment(text)[0]


def count(text):
    return convert_fragment(text)[1]


def lines(*ls, all_statements=False):
    out, n = convert_lines([l + "\n" for l in ls], all_statements=all_statements)
    return "".join(out), n


class TestBasicDescriptors(unittest.TestCase):

    def test_single_character(self):
        self.assertEqual(conv("9000 FORMAT(1H-)"), "9000 FORMAT('-')")

    def test_repeat_count(self):
        self.assertEqual(conv("2000 FORMAT(/3X,57(1H-)/)"),
                         "2000 FORMAT(/3X,57('-')/)")

    def test_multi_character_payload(self):
        # the count defines the payload; here it is exactly the 19 characters
        self.assertEqual(conv("FORMAT(19HSOME TEXT GOES HERE)"),
                         "FORMAT('SOME TEXT GOES HERE')")

    def test_count_that_overruns_into_the_delimiter(self):
        # 20H against 19 characters of text swallows the closing paren. That is
        # what the compiler does too, so reproducing it is correct -- and it is
        # why a miscounted Hollerith is so hard to spot by eye.
        self.assertEqual(conv("FORMAT(20HSOME TEXT GOES HERE)"),
                         "FORMAT('SOME TEXT GOES HERE)'")

    def test_payload_keeps_significant_blanks(self):
        # the count is what defines the payload, trailing blanks included
        self.assertEqual(conv("FORMAT(8HAB      )"), "FORMAT('AB      ')")

    def test_several_on_one_line(self):
        self.assertEqual(conv("FORMAT(1H ,3HABC)"), "FORMAT(' ','ABC')")
        self.assertEqual(count("FORMAT(1H ,3HABC)"), 2)

    def test_lowercase_h(self):
        self.assertEqual(conv("format(3habc)"), "format('abc')")


class TestQuoting(unittest.TestCase):

    def test_apostrophe_is_doubled(self):
        self.assertEqual(quote("A'"), "'A'''")

    def test_payload_with_apostrophe(self):
        self.assertEqual(conv("FORMAT(2HA')"), "FORMAT('A''')")

    def test_payload_that_is_a_quote(self):
        self.assertEqual(conv("FORMAT(1H')"), "FORMAT('''')")

    def test_payload_with_parenthesis(self):
        # a parenthesis inside a payload is data, not structure
        self.assertEqual(conv("FORMAT(3H(x))"), "FORMAT('(x)')")


class TestThingsItMustNotTouch(unittest.TestCase):

    def test_inline_comment_is_left_alone(self):
        src = "LHISX = LFTmax + MAXCYC   !0604HARUTA added for DI"
        self.assertEqual(count(src), 0)
        self.assertEqual(conv(src), src)

    def test_text_inside_a_literal(self):
        src = "WRITE(6,*) 'value 1H- here'"
        self.assertEqual(count(src), 0)

    def test_doubled_quote_inside_literal(self):
        src = "WRITE(6,*) 'it''s 2HAB'"
        self.assertEqual(count(src), 0)

    def test_digits_that_are_part_of_a_name(self):
        self.assertEqual(count("X = AB2HC"), 0)

    def test_real_literal_is_not_a_descriptor(self):
        self.assertEqual(count("X = 1.5H"), 0)

    def test_zero_count(self):
        self.assertEqual(count("FORMAT(0H)"), 0)

    def test_payload_longer_than_the_line(self):
        # a count that overruns means the parse is wrong, leave it
        self.assertEqual(count("FORMAT(40HSHORT)"), 0)


class TestStatementSelection(unittest.TestCase):

    def test_data_statement_untouched_by_default(self):
        out, n = lines("      DATA BASMD3/8HMINDO   /")
        self.assertEqual(n, 0)

    def test_data_statement_converted_with_all_statements(self):
        out, n = lines("      DATA BASMD3/8HMINDO   /", all_statements=True)
        self.assertEqual(n, 1)
        self.assertIn("'MINDO   '", out)

    def test_format_with_label(self):
        out, n = lines("9010 FORMAT(1H-)")
        self.assertEqual(n, 1)

    def test_format_without_label(self):
        out, n = lines("      FORMAT(1H-)")
        self.assertEqual(n, 1)

    def test_continued_format_statement(self):
        out, n = lines("2000 FORMAT(/3X,57(1H-)/ &",
                       "     3X,20HCONTINUED TEXT HERE)")
        self.assertEqual(n, 2)

    def test_statement_after_a_continued_format_is_not_converted(self):
        out, n = lines("2000 FORMAT(/3X,57(1H-)/ &",
                       "     3X,4HABCD)",
                       "      DATA X/8HMINDO   /")
        self.assertEqual(n, 2)

    def test_comment_and_preprocessor_lines_skipped(self):
        out, n = lines("! FORMAT(1H-)", "#ifdef FOO")
        self.assertEqual(n, 0)


class TestExclamationIsNotAlwaysAComment(unittest.TestCase):
    """A '!' only ends the line when it is outside a literal and outside a
    Hollerith payload. Treating it as a comment unconditionally makes a
    continued FORMAT look finished, so descriptors on its later lines survive.
    """

    def test_bang_inside_a_literal_does_not_end_the_statement(self):
        out, n = lines("9150 FORMAT(1X,'BEWARE! ORBITALS ARE UNMIXED'/ &",
                       "     1X,49(1H-))")
        self.assertEqual(n, 1)
        self.assertIn("49('-')", out)

    def test_bang_as_hollerith_payload_does_not_end_the_statement(self):
        out, n = lines("8000 FORMAT(//1X,62(1H!),/1X,'HONDO', &",
                       "     1X,62(1H!),//)")
        self.assertEqual(n, 2)
        self.assertEqual(out.count("62('!')"), 2)

    def test_real_inline_comment_still_ends_the_statement(self):
        out, n = lines("9000 FORMAT(1H-) ! trailing note with 4HABCD in it",
                       "      DATA X/8HMINDO   /")
        self.assertEqual(n, 1)
        self.assertIn("4HABCD", out)

    def test_bang_in_a_literal_on_a_middle_continuation_line(self):
        out, n = lines("8150 FORMAT(1X,'based ', &",
                       "     'on Koopmans'' theorem (FMO!) ', &",
                       "     1X,9(1H-))")
        self.assertEqual(n, 1)
        self.assertIn("9('-')", out)

    def test_descriptor_left_alone_is_reported(self):
        # 20H with only 5 characters behind it runs off the end. Leaving it is
        # right, staying quiet about it is not.
        report = []
        out, n = convert_fragment("9000 FORMAT(20HSHORT", report=report)
        self.assertEqual(n, 0)
        self.assertEqual(len(report), 1)
        self.assertIn("20HSHORT", report[0])

    def test_nothing_reported_when_all_converted(self):
        report = []
        convert_fragment("9000 FORMAT(1H-,4HABCD)", report=report)
        self.assertEqual(report, [])

    def test_report_carries_line_numbers(self):
        report = []
        convert_lines(["9000 FORMAT(1H-)\n", "9010 FORMAT(20HSHORT\n"],
                      report=report)
        self.assertEqual([lineno for lineno, _ in report], [2])

    def test_code_part_strips_only_genuine_comments(self):
        from fixhollerith import code_part
        self.assertEqual(code_part("A = 1 ! note"), "A = 1")
        self.assertEqual(code_part("FORMAT('BEWARE!') ! note"), "FORMAT('BEWARE!')")
        self.assertEqual(code_part("FORMAT(1H!) ! note"), "FORMAT(1H!)")
        self.assertEqual(code_part("FORMAT(1H-) &"), "FORMAT(1H-) &")


if __name__ == "__main__":
    unittest.main()
