#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# fixspacedops.py: Collapse blanks inside Fortran operator tokens in
#                  fixed source form files.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""Collapse blanks inside operator tokens in fixed source form Fortran.

Blanks are insignificant inside tokens in fixed source form, so this is legal
and surprisingly common in old code::

    IF(DONE. AND. IERR3.NE.0) THEN
    IF(T2X25 . GT . C4) GO TO 80

It is a syntax error in free source form, where a blank separates tokens. Run
this before fixed2free2.py: it rewrites the operators in place, which is a
no-op for the fixed form build and makes the same source convertible.

The rewrite is deliberately conservative:

  * only the intrinsic operator and logical literal names are touched, so an
    unrelated pair of '.' characters is never rewritten;
  * columns 1-6 and anything beyond column 72 are left alone;
  * comment lines are skipped, and character literals and Hollerith payloads
    are stepped over, so text data is never modified.

The Hollerith handling matters in practice. Legacy code contains constants
whose payload holds an apostrophe, such as the Cs point group irreducible
representation labels::

    DATA GANT/8HA       ,8HAG      ,8HAU      ,8HA'      ,

A scanner that does not consume ``nH`` payloads literally will treat that
apostrophe as opening a character literal and lose synchronisation for the rest
of the line.

Because only blanks are removed, lines can only get shorter, so a statement can
never be pushed past column 72 by this tool.
"""

import sys
import os
import re
import argparse

# Intrinsic operators and logical literals. Anything else between dots is left
# untouched -- a defined operator could legitimately contain no blanks, and we
# have no way to know that a spaced one was meant to be a single token.
OPERATORS = frozenset([
    'AND', 'OR', 'NOT', 'EQV', 'NEQV', 'XOR',
    'EQ', 'NE', 'LT', 'LE', 'GT', 'GE',
    'TRUE', 'FALSE',
])

# nH followed by exactly n literal characters.
_HOLLERITH = re.compile(r'(?<![A-Za-z0-9_.])(\d+)[Hh]')

# '.' then letters, possibly separated by blanks, then '.'
_DOTTED = re.compile(r'\.[ \t]*[A-Za-z][A-Za-z \t]*\.')

# A real literal whose exponent is separated from the mantissa by blanks, e.g.
# 0.000 D+00 or 1.5D +3. Blanks are insignificant in fixed form so this is one
# token; in free form it is a syntax error.
_SPACED_REAL = re.compile(
    r'(?<![A-Za-z0-9_])(\d+\.?\d*|\.\d+)([ \t]*[DdEeQq][ \t]*[-+]?[ \t]*\d+)')

# An integer literal broken up by blanks, used as a thousands separator:
#     PARAMETER (MEMSIZ= 1 000 000)
# Two numbers separated only by blanks is never valid Fortran on its own -- an
# operator or separator would be required -- so a run of digit groups joined by
# blanks is always a single literal in fixed form.
_SPACED_INT = re.compile(r'(?<![A-Za-z0-9_.])\d+(?:[ \t]+\d+)+(?![A-Za-z0-9_.])')

# Array constructor delimiters split by blanks: ( / ... / ). Blanks are
# insignificant in fixed form so these are single tokens; free form needs them
# closed up. A '(' followed by '/' can only be a constructor -- division there
# would have no left operand -- and likewise '/' followed by ')'.
_SPACED_CTOR = re.compile(r'\([ \t]+/|/[ \t]+\)')

CODE_START = 6      # column 7, zero based
CODE_END = 72       # last significant column


def fix_code(code):
    """Rewrite spaced operators in one code fragment.

    Returns (new_code, number_of_rewrites).
    """
    out = []
    i, n, quote, nfix = 0, len(code), None, 0
    while i < n:
        ch = code[i]
        if quote is None:
            m = _HOLLERITH.match(code, i)
            if m:                           # Hollerith payload is literal data
                end = m.end() + int(m.group(1))
                out.append(code[i:end])
                i = end
                continue
            if ch in ("'", '"'):
                quote = ch
                out.append(ch)
                i += 1
                continue
            if ch == '!':                   # inline comment, leave the rest
                out.append(code[i:])
                break
            m = _DOTTED.match(code, i)
            if m:
                token = m.group(0)
                inner = token[1:-1].replace(' ', '').replace('\t', '')
                if inner.upper() in OPERATORS and inner != token[1:-1]:
                    out.append('.' + inner + '.')
                    nfix += 1
                else:
                    out.append(token)
                i = m.end()
                continue
            m = (_SPACED_REAL.match(code, i) or _SPACED_INT.match(code, i)
                 or _SPACED_CTOR.match(code, i))
            if m:
                token = m.group(0)
                collapsed = token.replace(' ', '').replace('\t', '')
                if collapsed != token:
                    out.append(collapsed)
                    nfix += 1
                else:
                    out.append(token)
                i = m.end()
                continue
            out.append(ch)
        else:
            out.append(ch)
            if ch == quote:
                if i + 1 < n and code[i + 1] == quote:
                    out.append(code[i + 1])     # doubled delimiter, escaped
                    i += 1
                else:
                    quote = None
        i += 1
    return ''.join(out), nfix


def fix_lines(lines):
    """Rewrite an iterable of source lines. Returns (new_lines, count)."""
    new_lines, total = [], 0
    for line in lines:
        raw = line.rstrip('\n')
        if not raw or raw[0] in 'cC*!#':        # comment or preprocessor line
            new_lines.append(line)
            continue
        head = raw[:CODE_START]
        code = raw[CODE_START:CODE_END]
        tail = raw[CODE_END:]
        fixed, n = fix_code(code)
        if n:
            total += n
            # Removing blanks shortens the code field, which would slide
            # anything beyond column 72 back into the significant region and
            # change the meaning of the statement. Pad back to the original
            # width so the tail stays where the compiler ignores it.
            if tail:
                fixed = fixed.ljust(len(code))
            new_lines.append(head + fixed + tail + '\n')
        else:
            new_lines.append(line)
    return new_lines, total


def main():
    parser = argparse.ArgumentParser(
        description="Collapse blanks inside operator tokens in fixed-form Fortran.")
    parser.add_argument("input_file", nargs='+',
                        help="Input Fortran file(s) (fixed source form).")
    parser.add_argument("-i", "--inplace", action="store_true",
                        help="Edit the files in place.")
    parser.add_argument("-o", "--output",
                        help="Output file (only with a single input file; "
                             "default: converted_<input_file>).")
    parser.add_argument("-n", "--dry-run", action="store_true",
                        help="Report what would change, write nothing.")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="Only report the total.")

    args = parser.parse_args()

    if args.output and len(args.input_file) > 1:
        parser.error("--output cannot be used with more than one input file")
    if args.output and args.inplace:
        parser.error("--output and --inplace are mutually exclusive")

    grand = 0
    for input_file in args.input_file:
        with open(input_file, errors='replace') as infile:
            new_lines, count = fix_lines(infile)
        grand += count
        if count and not args.quiet:
            print(f"{os.path.basename(input_file):24s} {count}")
        if args.dry_run or not count:
            continue

        if args.inplace:
            output_file = input_file
        elif args.output:
            output_file = args.output
        else:
            output_file = f"converted_{os.path.basename(input_file)}"
        with open(output_file, 'w') as outfile:
            outfile.writelines(new_lines)

    what = "dry run" if args.dry_run else "applied"
    print(f"---- {grand} spaced operators in "
          f"{len(args.input_file)} file(s) ({what})")


if __name__ == "__main__":
    main()
