#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# fixed2free2.py: Conversion of Fortran code from fixed to free
#                 source form.
#
# Copyright (C) 2012    Elias Rabel
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

# author: Elias Rabel, 2012
# Let me know if you find this script useful:
# ylikx.0 at gmail
# https://www.github.com/ylikx/

import sys
import os
import re
import argparse

# Hollerith constant: nH followed by exactly n literal characters. The payload
# may contain quotes -- GAMESS has DATA items like 8HA'      for the Cs
# symmetry irrep labels A' and A" -- so it must be consumed literally or the
# quote scanner desynchronises and misplaces comments and continuations.
_HOLLERITH = re.compile(r'(?<![A-Za-z0-9_.])(\d+)[Hh]')

# Characters that can be interior to a single Fortran token. If a continuation
# boundary falls between two of these, the halves must rejoin with no blank.
TOKEN_CHARS = set('abcdefghijklmnopqrstuvwxyz'
                  'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                  '0123456789_.')

# A real literal may also be split part-way through its exponent, leaving the
# previous line ending in the exponent letter (0.44D | -2) or in the exponent
# sign (0.44D- | 2). Neither seam is covered by TOKEN_CHARS alone, because '-'
# is not token-interior anywhere else.
_EXP_LETTER_PENDING = re.compile(r'[0-9.][DdEeQq]$')
_EXP_SIGN_PENDING = re.compile(r'[0-9.][DdEeQq][-+]$')

# Two-character operators can also straddle the seam, e.g. T30* | *2 meaning
# T30**2. Each half is meaningless alone, so these must rejoin tight.

# A continuation seam that falls right after a keyword must NOT be closed up.
# Fixed form ignores blanks and the lexer still recognises the keyword, so
# "CALL" at the end of a line followed by "SUB(...)" is a call; joined tight in
# free form it becomes the single identifier "CALLSUB". Where the two halves
# form a legal compound keyword (GO TO, END DO) leaving the blank in is equally
# valid, so declining to join is always safe here.
KEYWORDS = frozenset("""
call if then else elseif endif do enddo end goto go to return continue stop
subroutine function program module use implicit none contains interface
integer real double precision complex logical character dimension common data
parameter external intrinsic save equivalence entry format write read print
open close rewind backspace inquire allocate deallocate nullify allocatable
pointer target intent optional public private type class select case where
forall while result recursive pure elemental block cycle exit assign namelist
include only operator assignment procedure sequence kind len in out inout
threadprivate print rewind flush wait
""".split())

_TRAILING_WORD = re.compile(r'([A-Za-z_]\w*)$')

_SPLIT_OPERATORS = {'**', '//', '==', '/=', '<=', '>=', '=>', '::',
                    '(/', '/)'}   # array constructor delimiters


def needs_tight_join(prev, nxt):
    """True if the continuation boundary falls inside a single token."""
    if prev.end_state is not None:
        return False              # inside a literal: blanks are significant data
    if not prev.code_tail or not nxt.first_code_char:
        return False
    if prev.last_code_char in TOKEN_CHARS and nxt.first_code_char in TOKEN_CHARS:
        w = _TRAILING_WORD.search(prev.code_tail)
        if w and w.group(1).lower() in KEYWORDS:
            return False
        return True
    if _EXP_LETTER_PENDING.search(prev.code_tail) and nxt.first_code_char in '+-0123456789':
        return True
    if _EXP_SIGN_PENDING.search(prev.code_tail) and nxt.first_code_char.isdigit():
        return True
    if prev.last_code_char + nxt.first_code_char in _SPLIT_OPERATORS:
        return True
    return False


def scan_quotes(code, state=None):
    """Return the character-context state at the end of `code`.

    The state is one of:
      None  -- not inside a character context
      "'" / '"'  -- inside a quoted literal opened with that delimiter
      int   -- inside a Hollerith payload, with this many characters still to
               come from the following lines

    A Hollerith payload can run off the end of the code field and be completed
    by the blank padding out to column 72, e.g. 20HELECTRONIC ENERGY, whose text
    is only 17 characters. Truncating those blanks corrupts the constant, so the
    unfinished count is carried to the next line.
    """
    i, n = 0, len(code)
    if isinstance(state, int):
        if state >= n:
            return state - n
        i, state = state, None
    while i < n:
        ch = code[i]
        if state is None:
            m = _HOLLERITH.match(code, i)
            if m:
                need = int(m.group(1))
                avail = n - m.end()
                if avail < need:
                    return need - avail
                i = m.end() + need
                continue
            if ch in ("'", '"'):
                state = ch
            elif ch == '!':
                return None
        else:
            if ch == state:
                if i + 1 < n and code[i + 1] == state:
                    i += 1
                else:
                    state = None
        i += 1
    return state

class FortranLine:
    def __init__(self, line, state=None):
        self.line = line
        self.line_conv = line
        self.isComment = False
        self.isContinuation = False
        self.in_state = state      # literal state inherited from previous line
        self.omp_prefix = ''       # '!$' sentinel, for OpenMP conditional lines
        self.end_state = None      # literal state after this line
        self.__analyse()

    def __repr__(self):
        return self.line_conv

    def continueLine(self, tight=False):
        """Insert line continuation symbol at correct position in a free format line.

        `tight` suppresses the blank before '&'. It is required when the next
        line rejoins mid-token: a blank there would separate the two halves into
        distinct tokens instead of one.
        """

        if self.end_state is not None:
            # A character literal is still open at the end of this line. Fixed
            # form pads the statement out to column 72 and those blanks are part
            # of the literal, so restore them before the continuation marker
            # instead of stripping them.
            body = self.line_conv.rstrip('\n')
            self.line_conv = body.ljust(self.prefix_len + 66) + "&\n"
            return

        if self.line_conv.strip() == '':
            # An empty continuation line contributes no characters to the
            # statement. In free form a blank line is a comment line and is
            # permitted between continuations, so emit it blank: a lone '&'
            # here reads as ending the statement rather than continuing it.
            self.line_conv = '\n'
            return

        if not self.isOMP:
            before_inline_comment, inline_comment = extract_inline_comment(self.line_conv)
        else:
            tmp, inline_comment = extract_inline_comment(self.line_conv[1:].lstrip())
            before_inline_comment = "!" + tmp

        amp = "&" if tight else " &"
        if inline_comment == "":
            self.line_conv = self.line_conv.rstrip() + amp + "\n"
        else:
            len_before = len(before_inline_comment)
            before = before_inline_comment.rstrip() + amp + " "
            self.line_conv = before.ljust(len_before) + inline_comment

    def __analyse(self):
        line = self.line
        firstchar = line[0] if len(line) > 0 else ''
        self.label = line[0:5].strip().lower() + ' ' if len(line) > 1 else ''
        cont_char = line[5] if len(line) >= 6 else ''
        fivechars = line[1:5] if len(line) > 1 else ''
        self.isShort = (len(line) <= 6)
        self.isLong  = (len(line) > 73)

        self.isComment = firstchar in "cC*!"
        self.isNewComment = '!' in fivechars and not self.isComment
        # this is a very specific use case for the application called GAMESS, sometimes there's omp behind C$ which was annoying to deal with
        # OpenMP sentinels in fixed form: the directive form [cC*!]$OMP, and
        # the conditional-compilation form [cC*!]$ where columns 3-5 are the
        # ordinary label field -- so C$ 96 FORMAT(...) is conditional code with
        # label 96, not a comment, and its continuation belongs to it.
        self.isOMP = self.isComment and (
            fivechars.lower() == "$omp"
            or (line[1:2] == '$' and re.fullmatch(r'[0-9 ]*', line[2:5] or '')))
#        self.isOMP = self.isComment and fivechars.lower() == "$omp"
        if self.isOMP:
            self.isComment = False
            self.label = ''
        self.isCppLine = (firstchar == '#')
        self.is_regular = (not (self.isComment or self.isNewComment or
                           self.isCppLine or self.isShort))
        self.isContinuation = (not (cont_char.isspace() or cont_char == '0') and
                               self.is_regular)

        self.code = line[6:] if len(line) > 6 else '\n'

        # Literal state inherited from the previous line only applies if this
        # line continues that statement.
        incoming = self.in_state if self.isContinuation else None

        self.excess_line = ''
        if self.isLong and self.is_regular:
            if scan_quotes(line[6:72], incoming) is not None:
                # Column 72 falls inside a character literal. Fixed form
                # discards everything past it, and a '!' appended here would
                # become string content rather than a comment, silently
                # corrupting the string. Drop the excess, as the compiler does.
                line = line[:72] + '\n'
                self.code = line[6:]
            else:
                code, inline_comment = extract_inline_comment(self.code, incoming)
                if inline_comment == "" or len(code) >= 72 - 6:
                    self.excess_line = line[72:]
                    line = line[:72] + '\n'
                    self.code = line[6:]

        # First and last significant characters of the code portion, used to
        # detect a token split across a continuation boundary.
        self.first_code_char = ''
        self.last_code_char = ''
        self.code_tail = ''
        if self.is_regular:
            self.end_state = scan_quotes(self.code.rstrip('\n'), incoming)
            bare, _ = extract_inline_comment(self.code.rstrip('\n'), incoming)
            stripped = bare.strip()
            if stripped:
                self.first_code_char = bare.lstrip()[0]
                self.last_code_char = stripped[-1]
                self.code_tail = stripped[-24:]

        self.line = line
        self.__convert()

    def joinAdjacent(self):
        """Emit a leading '&' so this continuation rejoins with no blank.

        Fixed form ignores blanks, so a token may straddle the boundary. Free
        form needs '&' at the start of the continuation for the two halves to
        form one token.
        """
        # The blanks between column 7 and the first character are insignificant
        # in fixed form; they must go, or they still separate the two halves of
        # the token in free form.
        pre = self.omp_prefix
        self.line_conv = pre + '&' + self.code.lstrip()
        self.prefix_len = len(pre) + 1

    def joinCharContext(self):
        """Resume a continued character literal with a leading '&'.

        A continued character context must restart with an ampersand, and the
        literal resumes at the character right after it. The leading blanks are
        kept, because in fixed form columns 7-72 of the continuation line are
        part of the string.
        """
        pre = self.omp_prefix
        self.line_conv = pre + '&' + self.code
        self.prefix_len = len(pre) + 1

    def __convert(self):
        line = self.line

        # prefix_len is how much of line_conv precedes what was column 7 of the
        # fixed-form line. Needed to restore blank padding out to column 72 when
        # a character literal is continued.
        self.prefix_len = 0
        if self.isComment:
            self.line_conv = '!' + line[1:]
        elif self.isNewComment or self.isCppLine:
            self.line_conv = line
        elif self.isOMP:
            self.omp_prefix = '!' + line[1:5]
            self.line_conv = self.omp_prefix + ' ' + self.code
            self.prefix_len = len(self.omp_prefix) + 1
        elif not self.label.isspace():
            self.line_conv = self.label + self.code
            self.prefix_len = len(self.label)
        else:
            self.line_conv = self.code

        if self.excess_line != '':
            if self.excess_line.lstrip().startswith("!"):
                marker = ""
            else:
                marker = "!"

            self.line_conv = self.line_conv.rstrip().ljust(72) + marker + self.excess_line

def extract_inline_comment(code, state=None):
    """Splits line of code into (code, inline comment).

    `state` is the character-literal state inherited from the previous line, so
    that a literal continued across lines is not mistaken for code. Hollerith
    payloads are skipped literally.
    """
    i, n = 0, len(code)
    while i < n:
        ch = code[i]
        if state is None:
            m = _HOLLERITH.match(code, i)
            if m:
                i = m.end() + int(m.group(1))
                continue
            if ch in ("'", '"'):
                state = ch
            elif ch == '!':
                return code[:i], code[i:]
        else:
            if ch == state:
                if i + 1 < n and code[i + 1] == state:
                    i += 1
                else:
                    state = None
        i += 1
    return code, ""

def convertToFree(stream):
    """Convert stream from fixed source form to free source form."""
    linestack = []
    state = None

    for line in stream:
        convline = FortranLine(line, state)

        # A continuation line whose code field is blank, or is entirely an
        # inline comment, contributes nothing to the statement. Demote it to a
        # comment line so no '&' is placed on the preceding line: in fixed form
        # the statement ends if the next line is not itself a continuation,
        # whereas a trailing '&' in free form would run the statement on into
        # whatever follows. Not applicable inside a character context, where
        # those columns are significant data.
        if convline.isContinuation and state is None:
            bare, _ = extract_inline_comment(convline.code.rstrip('\n'))
            if bare.strip() == '':
                text = convline.code.rstrip('\n')
                if text.strip() == '':
                    convline.line_conv = '\n'
                elif text.lstrip().startswith('!'):
                    convline.line_conv = text + '\n'
                else:
                    convline.line_conv = '!' + text + '\n'
                convline.is_regular = False
                convline.isContinuation = False

        if convline.is_regular:
            state = convline.end_state

        if convline.is_regular:
            if convline.isContinuation and linestack:
                prev = linestack[0]
                # A token split across the boundary must rejoin with no blank.
                # Only relevant outside a character literal: inside one, fixed
                # form keeps the blanks and the padding in continueLine covers it.
                tight = needs_tight_join(prev, convline)
                if tight:
                    convline.joinAdjacent()
                elif prev.end_state is not None:
                    convline.joinCharContext()
                prev.continueLine(tight)
            for l in linestack:
                yield str(l)
            linestack = []

        linestack.append(convline)

    for l in linestack:
        yield str(l)

def main():
    parser = argparse.ArgumentParser(description="Convert fixed-form Fortran to free-form.")
    parser.add_argument("input_file", help="Input Fortran file (fixed form).")
    parser.add_argument("-i", "--inplace", action="store_true", help="Edit the file in place.")
    parser.add_argument("-o", "--output", help="Redirect to an output file (default: converted_<input_file>).")

    args = parser.parse_args()

    input_file = args.input_file
    output_file = args.output

    if not output_file:
        base_name, suffix = os.path.splitext(input_file)
        if suffix in [".f", ".F"]:
            output_suffix = ".f90" if suffix == ".f" else ".F90"
            output_file = f"converted_{os.path.basename(base_name)}{output_suffix}"
        else:
            output_file = f"converted_{os.path.basename(base_name)}{suffix}"

    with open(input_file, 'r') as infile:
        converted_lines = list(convertToFree(infile))

    if args.inplace:
        with open(input_file, 'w') as outfile:
            outfile.writelines(converted_lines)
    else:
        with open(output_file, 'w') as outfile:
            outfile.writelines(converted_lines)

    print(f"Conversion completed. Output written to {output_file if not args.inplace else input_file}.")

if __name__ == "__main__":
    main()

