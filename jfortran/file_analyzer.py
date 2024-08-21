import argparse
from undeclared import (
    collect_known_variables,
    find_undeclared_variables,
    collect_declared_variables,
    collect_parameter_variables,
    collect_common_blocks,
    collect_data_initializations,
    check_proper_type_declaration
)

def main():
    parser = argparse.ArgumentParser(description="Fortran Variable Declaration, Parameter, Common Block, Data Statement, and Undeclared Variable Analyzer")
    parser.add_argument("file", help="Path to the Fortran file to analyze")
    
    args = parser.parse_args()
    
    # Collect declared variables
    declared_variables = collect_declared_variables(args.file)

    # Collect variables from common blocks, parameter, and data statements
    parameter_variables = collect_parameter_variables(args.file)
    common_blocks = collect_common_blocks(args.file)
    data_initializations = collect_data_initializations(args.file)

    # Check for missing type declarations
    missing_declarations = check_proper_type_declaration(
        declared_variables,
        common_blocks,
        parameter_variables,
        data_initializations
    )

    # Print missing type declarations
    if missing_declarations:
        print("\nVariables missing type declarations:")
        for var in sorted(missing_declarations):
            print(f"Variable '{var}' is missing a type declaration.")
    else:
        print("All variables have proper type declarations.")

    # Collect all known variables as a set
    known_variables = set(declared_variables.keys())  # Convert to a set

    # Find undeclared variables
    undeclared_variables = find_undeclared_variables(args.file, known_variables)

    # Print undeclared variables with line numbers
    if undeclared_variables:
        print("\nUndeclared variables found:")
        for var, lines in sorted(undeclared_variables.items()):
            line_info = ', '.join(str(line) for line in lines)
            print(f"Variable '{var}' is used but not declared. Found on line(s): {line_info}")
    else:
        print("No undeclared variables found.")


if __name__ == "__main__":
    main()

