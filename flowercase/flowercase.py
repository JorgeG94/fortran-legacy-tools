# flowercase.py: Conversion of Fortran code from traditional all
#                uppercase source to more readable lowercase.
#
# Copyright (C) 2012-2021    Elias Rabel
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

""" 
Script that converts free form Fortran code to lower case
without messing with comments or strings. Mixed case words remain
untouched. 

Note: works only in free source form, use fixed2free.py first to
convert.

Usage: file name as first command line parameter
"""

# author: Elias Rabel, 2012
# Let me know when you find this script useful:
# ylikx.0 at gmail
# https://www.github.com/ylikx/

#from __future__ import print_function
import sys
import os
import argparse

def convert_to_lowercase(stream):
    """Convert all uppercase keywords in the Fortran source file to lowercase."""
    commentmode = False
    stringmode = False
    stringchar = ''

    for line in stream:
        line_new = ''
        word = ''
        commentmode = False

        for character in line:
            if not character.isalnum() and character != '_':
                if not stringmode and not commentmode:
                    if word.isupper():  # means: do not convert mixed case words
                        word = word.lower()

                line_new += word
                line_new += character
                word = ''

                if (character == '"' or character == "'") and not commentmode:
                    if not stringmode:
                        stringchar = character
                        stringmode = True
                    else:
                        stringmode = not (character == stringchar)

                if character == '!' and not stringmode:
                    commentmode = True  # treat rest of line as comment

            else:
                word += character

        line_new += word
        yield line_new

def main():
    parser = argparse.ArgumentParser(description="Convert Fortran file keywords to lowercase.")
    parser.add_argument("input_file", help="Input Fortran file.")
    parser.add_argument("-i", "--inplace", action="store_true", help="Edit the file in place.")
    parser.add_argument("-o", "--output", help="Redirect to an output file (default: converted_<input_file>.f90 or .F90).")

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
        converted_lines = list(convert_to_lowercase(infile))

    if args.inplace:
        with open(input_file, 'w') as outfile:
            outfile.writelines(converted_lines)
    else:
        with open(output_file, 'w') as outfile:
            outfile.writelines(converted_lines)

    print(f"Conversion completed. Output written to {output_file if not args.inplace else input_file}.")

if __name__ == "__main__":
    main()

