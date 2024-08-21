from variable_collector import (
    collect_declared_variables, 
    collect_parameter_variables, 
    collect_common_blocks, 
    collect_data_initializations
)
import re

def collect_known_variables(file_path):
    """
    Collects all known variables from declared variables, parameters, common blocks, and data initializations.
    """
    # Collect declared variables
    declared_variables = collect_declared_variables(file_path)

    # Collect parameter variables
    parameter_variables = collect_parameter_variables(file_path)

    # Collect common block variables
    common_blocks = collect_common_blocks(file_path)

    # Collect data initializations
    data_initializations = collect_data_initializations(file_path)

    # Combine all known variables into a single set
    known_variables = set(declared_variables.keys())
    known_variables.update(parameter_variables.keys())
    for block_vars in common_blocks.values():
        known_variables.update(block_vars)
    known_variables.update(data_initializations.keys())

    return known_variables
def remove_string_literals(line):
    """
    Removes string literals from the line, ignoring text within quotes.
    """
    return re.sub(r"'.*?'", '', line)  # Removes single-quoted strings
    # Optionally, you can extend this to handle double-quoted strings if used:
    # return re.sub(r"['\"].*?['\"]", '', line)

import re

def find_undeclared_variables(file_path, known_variables):
    """
    Scans the file for variables that are used but not declared, ignoring comments, string literals, 
    FORMAT statements, and Fortran logical operators.
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return set()

    undeclared_variables = set()

    # Regex to match logical operators and skip them
    logical_operators_pattern = re.compile(r'\.\s*(and|or|not|eq|ne|lt|le|gt|ge|eqv|neqv)\s*\.', re.IGNORECASE)

    for line in lines:
        # Skip entire line if it's a comment or FORMAT statement
        if line.strip().startswith('!') or is_format_statement(line):
            continue

        # Remove inline comments
        line = line.split('!')[0]

        # Remove string literals
        line = remove_string_literals(line)

        # Remove logical operators from the line
        line = logical_operators_pattern.sub('', line)

        # Find all variables in the line
        variable_pattern = re.compile(r'\b([a-zA-Z]\w*)\b')
        matches = variable_pattern.findall(line)
        for var in matches:
            # If variable is not in known_variables, not a Fortran keyword, and not a common block name, add to undeclared
            if var.lower() not in known_variables and not is_fortran_keyword(var) and not is_common_block(line):
                undeclared_variables.add(var)

    return undeclared_variables


def is_format_statement(line):
    """
    Checks if a line is a FORMAT statement.
    """
    return bool(re.match(r'^\s*\d+\s*format\s*\(.*\)', line, re.IGNORECASE))

def is_common_block(line):
    """
    Checks if a line is declaring a common block.
    """
    return bool(re.match(r'^\s*common\s*/', line, re.IGNORECASE))

def is_fortran_keyword(word):
    """
    Checks if a word is a Fortran keyword or logical operator to avoid false positives.
    """
    fortran_keywords = {
        'do', 'if', 'then', 'else', 'elseif', 'end', 'subroutine', 'function', 'program', 'module',
        'use', 'call', 'continue', 'return', 'stop', 'print', 'write', 'read', 'format', 'go', 'to',
        'parameter', 'common', 'dimension', 'logical', 'integer', 'real', 'character', 'complex',
        'double', 'precision', 'implicit', 'none', 'data', 'contains', 'external', 'intrinsic'
    }

    # Add logical operators and other intrinsic functions
    fortran_logical_operators = {
        '.and.', '.or.', '.not.', '.eq.', '.ne.', '.lt.', '.le.', '.gt.', '.ge.', '.eqv.', '.neqv.'
    }

    # Combine both sets
    all_fortran_keywords = fortran_keywords.union(fortran_logical_operators)

    return word.lower() in all_fortran_keywords

