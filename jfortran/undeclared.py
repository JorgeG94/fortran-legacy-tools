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

def find_undeclared_variables(file_path, known_variables):
    """
    Scans the file for variables that are used but not declared, ignoring comments, string literals,
    FORMAT statements, Fortran logical operators, and subroutine names in CALL statements.
    Returns a dictionary where the keys are undeclared variables and values are the lines where they are used.
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return {}

    undeclared_variables = {}
    variable_pattern = re.compile(r'\b([a-zA-Z]\w*)\b')
    implicit_found = False

    for i, line in enumerate(lines, start=1):  # Enumerate lines with line numbers starting at 1
        # Skip entire line if it's a comment or FORMAT statement
        if line.strip().startswith('!') or is_format_statement(line):
            continue

        # Check for implicit statement
        if re.search(r'implicit\s+', line, re.IGNORECASE):
            implicit_found = True
            continue  # Move to next line after finding implicit

        # Remove inline comments
        line = line.split('!')[0]

        # Remove string literals
        line = remove_string_literals(line)

        # Replace logical operators with spaces to prevent variable concatenation
        logical_operators_pattern = re.compile(r'\.\s*(and|or|not|eq|ne|lt|le|gt|ge|eqv|neqv)\s*\.', re.IGNORECASE)
        line = logical_operators_pattern.sub(' ', line)

        # Check for subroutine calls and handle them
        if "call" in line.lower():
            subroutine_call_pattern = re.compile(r'\bcall\s+([a-zA-Z]\w*)\s*\((.*)\)', re.IGNORECASE)
            match = subroutine_call_pattern.search(line)
            if match:
                subroutine_name = match.group(1)  # The subroutine name (e.g., 'a')
                arguments = match.group(2)  # The arguments inside the parentheses (e.g., 'x')
                argument_vars = variable_pattern.findall(arguments)
                for arg in argument_vars:
                    arg_lower = arg.lower()
                    if implicit_found and arg_lower not in known_variables and not is_fortran_keyword(arg_lower):
                        if arg_lower not in undeclared_variables:
                            undeclared_variables[arg_lower] = []
                        undeclared_variables[arg_lower].append(i)
            continue  # Skip to the next line

        # Find all other variables in the line
        matches = variable_pattern.findall(line)
        for var in matches:
            var_lower = var.lower()
            # Before implicit, add variables to known_variables
            if not implicit_found:
                known_variables.add(var_lower)
            # After implicit, check for undeclared variables
            elif var_lower not in known_variables and not is_fortran_keyword(var_lower) and not is_common_block(line):
                if var_lower not in undeclared_variables:
                    undeclared_variables[var_lower] = []
                undeclared_variables[var_lower].append(i)  # Append the line number

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

def check_proper_type_declaration(declared_variables, common_blocks, parameter_variables, data_initializations):
    """
    Checks if variables in common blocks, parameter statements, and data statements have proper type declarations.
    Returns a set of variables that are missing type declarations.
    """
    missing_declarations = set()

    # Combine all variables from common blocks, parameter statements, and data initializations
    all_vars_to_check = set(parameter_variables.keys())
    for block_vars in common_blocks.values():
        all_vars_to_check.update(block_vars)
    all_vars_to_check.update(data_initializations.keys())

    # Cross-reference with declared variables
    for var in all_vars_to_check:
        if var.lower() not in declared_variables:
            missing_declarations.add(var)

    return missing_declarations
def is_fortran_keyword(word):
    """
    Checks if a word is a Fortran keyword, logical operator, or format specifier to avoid false positives.
    """
    # Fortran keywords
    fortran_keywords = {
        'do', 'if', 'then', 'else', 'elseif', 'end', 'subroutine', 'function', 'program', 'module',
        'use', 'call', 'continue', 'return', 'stop', 'print', 'write', 'read', 'format', 'go', 'to',
        'parameter', 'common', 'dimension', 'logical', 'integer', 'real', 'character', 'complex',
        'double', 'precision', 'implicit', 'none', 'data', 'contains', 'external', 'intrinsic', 'endif'
    }

    # Logical operators
    fortran_logical_operators = {
        '.and.', '.or.', '.not.', '.eq.', '.ne.', '.lt.', '.le.', '.gt.', '.ge.', '.eqv.', '.neqv.', '.true.', '.false.'
    }

    # Combine keywords and logical operators
    all_fortran_keywords = fortran_keywords.union(fortran_logical_operators)

    # Check if the word matches format specifiers with numbers (like i8, f12.5, etc.)
    format_specifiers = {'i', 'f', 'e', 'g', 'a', 'l', 'd', 'x', '1x', 'h'}
    if word.lower() in format_specifiers:
        return False  # Exclude basic format specifiers from being treated as keywords

    # Check if the word starts with a format specifier and is followed by digits
    if any(word.lower().startswith(fmt) and word[len(fmt):].isdigit() for fmt in format_specifiers):
        return False  # Exclude format specifiers with numbers

    return word.lower() in all_fortran_keywords

