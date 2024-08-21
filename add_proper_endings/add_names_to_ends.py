import os
import re

def process_fortran_file(filepath):
    with open(filepath, 'r') as file:
        lines = file.readlines()

    modified_lines = []
    inside_subroutine = False
    inside_function = False
    inside_module = False
    current_subroutine_name = None
    current_function_name = None
    current_module_name = None
    current_indent = ''

    for line in lines:
        subroutine_match = re.match(r'^(\s*)subroutine\s+(\w+)', line, re.IGNORECASE)
        # Updated to match functions with a type prefix
        function_match = re.match(r'^(\s*)((?:integer|real|double\s+precision|logical|character)\s+)?function\s+(\w+)', line, re.IGNORECASE)
        module_match = re.match(r'^(\s*)module\s+(?!procedure\b)(\w+)', line, re.IGNORECASE)
        end_subroutine_match = re.match(r'^(\s*)end\s+subroutine\s*(\w*)', line, re.IGNORECASE)
        end_function_match = re.match(r'^(\s*)end\s+function\s*(\w*)', line, re.IGNORECASE)
        end_module_match = re.match(r'^(\s*)end\s+module\s*(\w*)', line, re.IGNORECASE)

        if subroutine_match:
            inside_subroutine = True
            inside_function = False
            current_subroutine_name = subroutine_match.group(2)
            current_indent = subroutine_match.group(1)

        if function_match:
            inside_function = True
            inside_subroutine = False
            current_function_name = function_match.group(3)
            current_indent = function_match.group(1)

        if module_match:
            inside_module = True
            current_module_name = module_match.group(2)
            current_indent = module_match.group(1)

        if inside_module and end_module_match:
            if not end_module_match.group(2):
                line = f'{end_module_match.group(1)}end module {current_module_name}\n'
            inside_module = False

        if inside_subroutine and end_subroutine_match:
            if not end_subroutine_match.group(2):
                line = f'{end_subroutine_match.group(1)}end subroutine {current_subroutine_name}\n'
            inside_subroutine = False

        if inside_function and end_function_match:
            if not end_function_match.group(2):
                line = f'{end_function_match.group(1)}end function {current_function_name}\n'
            inside_function = False
                    # If inside a module and the subroutine/function is ending
        if inside_module:
            if inside_subroutine and end_subroutine_match:
                if not end_subroutine_match.group(2):
                    line = f'{end_subroutine_match.group(1)}end subroutine {current_subroutine_name}\n'
                inside_subroutine = False
            if inside_function and end_function_match:
                if not end_function_match.group(2):
                    line = f'{end_function_match.group(1)}end function {current_function_name}\n'
                inside_function = False

        modified_lines.append(line)

    with open(filepath, 'w') as file:
        file.writelines(modified_lines)


def replace_generic_end(filepath):
    with open(filepath, 'r') as file:
        lines = file.readlines()

    modified_lines = []
    inside_subroutine = False
    inside_function = False
    inside_module = False
    current_subroutine_name = None
    current_function_name = None
    current_module_name = None
    current_indent = ''

    for line in lines:
        subroutine_match = re.match(r'^(\s*)subroutine\s+(\w+)', line, re.IGNORECASE)
        # Updated to match functions with a type prefix
        function_match = re.match(r'^(\s*)((?:integer|real|double\s+precision|logical|character)\s+)?function\s+(\w+)', line, re.IGNORECASE)
        module_match = re.match(r'^(\s*)module\s+(?!procedure\b)(\w+)', line, re.IGNORECASE)
        generic_end_match = re.match(r'^(\s*)end\s*$', line, re.IGNORECASE)

        if subroutine_match:
            inside_subroutine = True
            inside_function = False
            inside_module = False
            current_subroutine_name = subroutine_match.group(2)
            current_indent = subroutine_match.group(1)

        if function_match:
            inside_function = True
            inside_subroutine = False
            inside_module = False
            current_function_name = function_match.group(3)
            current_indent = function_match.group(1)

        if module_match:
            inside_module = True
            inside_subroutine = False
            inside_function = False
            current_module_name = module_match.group(2)
            current_indent = module_match.group(1)

        if generic_end_match:
            if inside_subroutine:
                line = f'{generic_end_match.group(1)}end subroutine {current_subroutine_name}\n'
                inside_subroutine = False
            elif inside_function:
                line = f'{generic_end_match.group(1)}end function {current_function_name}\n'
                inside_function = False
            elif inside_module:
                line = f'{generic_end_match.group(1)}end module {current_module_name}\n'
                inside_module = False

        modified_lines.append(line)

    with open(filepath, 'w') as file:
        file.writelines(modified_lines)


def process_directory(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.f90') or file.endswith('.src'):
                filepath = os.path.join(root, file)
                replace_generic_end(filepath)
                process_fortran_file(filepath)

# Example usage
directory_path = 'source/'
process_directory(directory_path)

