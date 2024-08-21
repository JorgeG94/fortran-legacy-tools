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
import argparse

class FortranLine:
    def __init__(self, line):
        self.line = line
        self.line_conv = line
        self.isComment = False
        self.isContinuation = False
        self.__analyse()

    def __repr__(self):
        return self.line_conv

    def continueLine(self):
        """Insert line continuation symbol at correct position in a free format line."""

        if not self.isOMP:
            before_inline_comment, inline_comment = extract_inline_comment(self.line_conv)
        else:
            tmp, inline_comment = extract_inline_comment(self.line_conv[1:].lstrip())
            before_inline_comment = "!" + tmp

        if inline_comment == "":
            self.line_conv = self.line_conv.rstrip() + " &\n"
        else:
            len_before = len(before_inline_comment)
            before = before_inline_comment.rstrip() + " & "
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
        self.isOMP = self.isComment and (fivechars.lower() == "$omp" or fivechars.lower() == "$   ")
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

        self.excess_line = ''
        if self.isLong and self.is_regular:
            code, inline_comment = extract_inline_comment(self.code)
            if inline_comment == "" or len(code) >= 72 - 6:
                self.excess_line = line[72:]
                line = line[:72] + '\n'
                self.code = line[6:]

        self.line = line
        self.__convert()

    def __convert(self):
        line = self.line

        if self.isComment:
            self.line_conv = '!' + line[1:]
        elif self.isNewComment or self.isCppLine:
            self.line_conv = line
        elif self.isOMP:
            self.line_conv = '!' + line[1:5] + ' ' + self.code
        elif not self.label.isspace():
            self.line_conv = self.label + self.code
        else:
            self.line_conv = self.code

        if self.excess_line != '':
            if self.excess_line.lstrip().startswith("!"):
                marker = ""
            else:
                marker = "!"

            self.line_conv = self.line_conv.rstrip().ljust(72) + marker + self.excess_line

def extract_inline_comment(code):
    """Splits line of code into (code, inline comment)"""
    stringmode = False
    stringchar = ""

    for column, character in enumerate(code):
        is_string_delimiter = (character == "'" or character == '"')
        if not stringmode and is_string_delimiter:
            stringmode = True
            stringchar = character
        elif stringmode and is_string_delimiter:
            stringmode = (character != stringchar)
        elif not stringmode and character == "!":
            return code[:column], code[column:]

    return code, ""

def convertToFree(stream):
    """Convert stream from fixed source form to free source form."""
    linestack = []

    for line in stream:
        convline = FortranLine(line)

        if convline.is_regular:
            if convline.isContinuation and linestack:
                linestack[0].continueLine()
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

