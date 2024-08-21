import re

def extract_variables(line, keyword):
    """
    Extracts variables from a line of Fortran code given a specific keyword.
    """
    # Remove keyword and split by commas
    variables_part = line.split(keyword, 1)[1]
    # Remove anything after a comment or continuation mark
    variables_part = variables_part.split('!')[0].split('&')[0]
    # Split variables and strip spaces
    variables = [var.strip() for var in variables_part.split(',')]
    return variables

def preprocess_lines(lines):
    """
    Concatenate lines ending with a continuation character (&) to handle multi-line declarations.
    """
    concatenated_lines = []
    current_line = ""

    for line in lines:
        stripped_line = line.strip()
        if stripped_line.endswith('&'):
            # Remove the '&' and concatenate
            current_line += stripped_line[:-1] + " "
        else:
            current_line += stripped_line
            concatenated_lines.append(current_line)
            current_line = ""

    if current_line:
        concatenated_lines.append(current_line)

    return concatenated_lines

def collect_declared_variables(file_path):
    """
    Collects all variables that are properly declared with a valid Fortran identifier.
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return {}

    declared_variables = {}

    # Preprocess lines to handle multi-line declarations
    lines = preprocess_lines(lines)

    # Regular expressions for identifying declarations
    patterns = {
        'integer': re.compile(r'^\s*integer\b', re.IGNORECASE),
        'logical': re.compile(r'^\s*logical\b', re.IGNORECASE),
        'character': re.compile(r'^\s*character\*\d+\s+(\w+)', re.IGNORECASE),
        'double precision': re.compile(r'^\s*double\s+precision\b', re.IGNORECASE),
        'real': re.compile(r'^\s*real\*\d+\s+(\w+)', re.IGNORECASE),
        'complex': re.compile(r'^\s*complex\b', re.IGNORECASE),
    }

    for line in lines:
        for key, pattern in patterns.items():
            if key in ['character', 'real']:
                match = pattern.search(line)
                if match:
                    declared_variables[match.group(1)] = key
            else:
                if pattern.search(line):
                    variables = extract_variables(line, key)
                    for var in variables:
                        declared_variables[var] = key

    return declared_variables

def collect_parameter_variables(file_path):
    """
    Collects variables declared in parameter statements.
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return {}

    parameter_variables = {}

    # Preprocess lines to handle multi-line declarations
    lines = preprocess_lines(lines)

    # Regular expression to identify parameter statements
    parameter_pattern = re.compile(r'^\s*parameter\s*\((.*?)\)', re.IGNORECASE)

    for line in lines:
        match = parameter_pattern.search(line)
        if match:
            params_part = match.group(1)
            params = [param.split('=')[0].strip() for param in params_part.split(',')]
            for param in params:
                parameter_variables[param] = 'parameter'

    return parameter_variables
def collect_common_blocks(file_path):
    """
    Collects common blocks and associated variables in a Fortran file.
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return {}

    common_blocks = {}

    # Preprocess lines to handle multi-line common blocks
    lines = preprocess_lines(lines)

    # Regular expression to identify common block declarations
    common_pattern = re.compile(r'^\s*common\s*/(\w+)/\s*(.*)', re.IGNORECASE)

    for line in lines:
        match = common_pattern.search(line)
        if match:
            block_name = match.group(1)
            # Extract only variable names, removing any array dimensions
            variables = [var.strip().split('(')[0] for var in match.group(2).split(',')]
            common_blocks[block_name] = variables

    return common_blocks


def collect_data_initializations(file_path):
    """
    Collects variables initialized using data statements with Hollerith constants.
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return {}

    data_initializations = {}

    # Preprocess lines to handle multi-line data statements
    lines = preprocess_lines(lines)

    # Regular expression to identify data statements with Hollerith constants
    data_pattern = re.compile(r'\b(\w+)\s*/\d+H([\w\s]*)\s*/')

    for line in lines:
        # Find all matches in the line
        matches = data_pattern.findall(line)
        for match in matches:
            # Extract variable names and their corresponding Hollerith values
            var_name = match[0].strip()
            hollerith_value = match[1].strip()
            data_initializations[var_name] = hollerith_value

    return data_initializations

