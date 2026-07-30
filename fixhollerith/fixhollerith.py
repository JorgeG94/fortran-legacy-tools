#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# fixhollerith.py: Replace Hollerith edit descriptors in FORMAT statements
#                  with quoted character literals.
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
"""Convert Hollerith edit descriptors in FORMAT statements to character literals.

    2000 FORMAT(/3X,57(1H-)/)      ->    2000 FORMAT(/3X,57('-')/)
    9010 FORMAT(1H ,20HSOME TEXT GOES HERE)  ->  9010 FORMAT(' ','SOME TEXT GOES HERE')

The Hollerith form `nHxxxx` was deleted from the standard in Fortran 95. It is
still accepted by most compilers, but it is unreadable, it cannot be checked
(the count and the text can disagree), and it blocks any tooling that needs to
understand string data.

Scope: FORMAT statements only. Hollerith constants used as data -- in DATA
statements, actual arguments, or initialisers -- are deliberately left alone.
Converting those means changing the type of the receiving variable, which is a
program-wide change and not something a source rewriter can decide.

What it will not touch:

  * comment lines and inline comments. Text like `!0604HARUTA added` parses as
    a 4-character Hollerith if you are careless, and rewriting it would corrupt
    the comment.
  * anything inside an existing character literal.
  * a descriptor whose payload would run past the end of the line, which
    indicates the parse has gone wrong rather than a real continuation: in
    practice Hollerith payloads are line-local.

Payloads containing an apostrophe are emitted with the apostrophe doubled, so
`2HA'` becomes `'A'''`.
"""

import sys
import os
import re
import argparse

# nH, not preceded by something that would make the digits part of a longer
# token. The lookbehind keeps `0604HARUTA` inside a comment from matching, and
# stops `X2H` or `1.5H` being read as a descriptor.
_HOLLERITH = re.compile(r'(?<![A-Za-z0-9_.])(\d+)[Hh]')

# A FORMAT statement, with or without a leading label. Also matches the
# character-literal form used in WRITE(...,'(...)') only when asked.
_FORMAT_STMT = re.compile(r'^\s*(?:\d+\s+)?format\s*\(', re.I)


def quote(payload):
    """Render a Hollerith payload as a Fortran character literal."""
    return "'" + payload.replace("'", "''") + "'"


def code_part(code):
    """Return `code` with any inline comment removed.

    A plain split on '!' is wrong: the character is ordinary text inside a
    literal ('BEWARE!') and is Hollerith payload in `1H!`. Getting this wrong
    truncates the line, which makes a continued FORMAT statement look finished
    and leaves the descriptors on its later lines unconverted.
    """
    i, n, quote_char = 0, len(code), None
    while i < n:
        ch = code[i]
        if quote_char is not None:
            if ch == quote_char:
                if i + 1 < n and code[i + 1] == quote_char:
                    i += 1
                else:
                    quote_char = None
            i += 1
            continue
        if ch in ("'", '"'):
            quote_char = ch
            i += 1
            continue
        m = _HOLLERITH.match(code, i)
        if m:
            count = int(m.group(1))
            if count and m.end() + count <= n:
                i = m.end() + count      # payload is data, '!' included
                continue
            i = m.end()
            continue
        if ch == '!':
            return code[:i].rstrip()
        i += 1
    return code.rstrip()


def convert_fragment(code, report=None):
    """Rewrite Hollerith descriptors in one code fragment.

    Returns (new_code, count). Character literals and inline comments are
    stepped over untouched.

    `report`, if given, is a list that collects the text of any descriptor left
    unconverted because its payload would run off the end of the fragment. Those
    are rare and are left alone deliberately, but silence about them is what lets
    a leftover pass for a clean tree.
    """
    out = []
    i, n, quote_char, nfix = 0, len(code), None, 0
    while i < n:
        ch = code[i]
        if quote_char is not None:
            out.append(ch)
            if ch == quote_char:
                if i + 1 < n and code[i + 1] == quote_char:
                    out.append(code[i + 1])
                    i += 1
                else:
                    quote_char = None
            i += 1
            continue

        if ch in ("'", '"'):
            quote_char = ch
            out.append(ch)
            i += 1
            continue

        if ch == '!':                      # inline comment, leave the rest
            out.append(code[i:])
            break

        m = _HOLLERITH.match(code, i)
        if m:
            count = int(m.group(1))
            start = m.end()
            if count == 0 or start + count > n:
                # payload would run off the end: not a real descriptor here
                if count and report is not None:
                    report.append(code[i:].rstrip())
                out.append(code[i:m.end()])
                i = m.end()
                continue
            payload = code[start:start + count]
            out.append(quote(payload))
            nfix += 1
            i = start + count
            continue

        out.append(ch)
        i += 1
    return ''.join(out), nfix


def is_format_line(line, in_continued_format):
    """True if this line belongs to a FORMAT statement."""
    if _FORMAT_STMT.match(line):
        return True
    return in_continued_format


def convert_lines(lines, all_statements=False, report=None):
    """Rewrite an iterable of source lines. Returns (new_lines, count).

    `report`, if given, is a list that collects (line_number, text) for every
    descriptor left unconverted. See convert_fragment.
    """
    new_lines, total = [], 0
    in_format = False
    for lineno, line in enumerate(lines, 1):
        raw = line.rstrip('\n')
        stripped = raw.lstrip()

        if not stripped or stripped.startswith('!') or stripped.startswith('#'):
            new_lines.append(line)
            continue

        target = True if all_statements else is_format_line(raw, in_format)

        if target:
            skipped = [] if report is not None else None
            fixed, k = convert_fragment(raw, report=skipped)
            total += k
            if skipped:
                report.extend((lineno, s) for s in skipped)
            new_lines.append(fixed + '\n')
        else:
            new_lines.append(line)

        # track whether the FORMAT statement continues on the next line
        code = code_part(raw)
        if is_format_line(raw, in_format):
            in_format = code.endswith('&')
        elif not code.endswith('&'):
            in_format = False

    return new_lines, total


def main():
    parser = argparse.ArgumentParser(
        description="Convert Hollerith edit descriptors in FORMAT statements "
                    "to character literals.")
    parser.add_argument("input_file", nargs='+', help="Fortran source file(s).")
    parser.add_argument("-i", "--inplace", action="store_true",
                        help="Edit the files in place.")
    parser.add_argument("-o", "--output",
                        help="Output file (single input only; default: "
                             "converted_<input_file>).")
    parser.add_argument("-n", "--dry-run", action="store_true",
                        help="Report what would change, write nothing.")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="Only report the total.")
    parser.add_argument("--all-statements", action="store_true",
                        help="Also convert descriptors outside FORMAT "
                             "statements. Off by default: elsewhere a "
                             "Hollerith is data, and replacing it with a "
                             "character literal changes the type of the "
                             "expression.")

    args = parser.parse_args()
    if args.output and len(args.input_file) > 1:
        parser.error("--output cannot be used with more than one input file")
    if args.output and args.inplace:
        parser.error("--output and --inplace are mutually exclusive")

    grand, hit_files, left_behind = 0, 0, 0
    for input_file in args.input_file:
        report = []
        with open(input_file, errors='replace') as fh:
            new_lines, count = convert_lines(fh, all_statements=args.all_statements,
                                             report=report)
        grand += count
        if count:
            hit_files += 1
        if count and not args.quiet:
            print(f"{os.path.basename(input_file):28s} {count}")
        for lineno, text in report:
            left_behind += 1
            print(f"{input_file}:{lineno}: left alone, payload runs past the "
                  f"end of the line: {text}", file=sys.stderr)
        if args.dry_run or not count:
            continue

        if args.inplace:
            out = input_file
        elif args.output:
            out = args.output
        else:
            out = f"converted_{os.path.basename(input_file)}"
        with open(out, 'w') as fh:
            fh.writelines(new_lines)

    what = "dry run" if args.dry_run else "applied"
    # Count the files that actually carry descriptors, not the files scanned.
    # Reporting the latter makes "1761 in 439 files" out of 123 real ones, which
    # is useless for judging how much work is left.
    print(f"---- {grand} Hollerith descriptors in {hit_files} of "
          f"{len(args.input_file)} file(s) scanned ({what})")
    if left_behind:
        print(f"---- {left_behind} left alone, see above", file=sys.stderr)


if __name__ == "__main__":
    main()
