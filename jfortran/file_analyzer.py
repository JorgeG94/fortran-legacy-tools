import argparse
from variable_collector import (
    collect_declared_variables, 
    collect_parameter_variables, 
    collect_common_blocks, 
    collect_data_initializations
)
from undeclared import (
    collect_known_variables,
    find_undeclared_variables
)
import re

def main():
    parser = argparse.ArgumentParser(description="Fortran Variable Declaration, Parameter, Common Block, Data Statement, and Undeclared Variable Analyzer")
    parser.add_argument("file", help="Path to the Fortran file to analyze")
    
    args = parser.parse_args()
    
    # Collect all known variables
    known_variables = collect_known_variables(args.file)

    # Find undeclared variables
    undeclared_variables = find_undeclared_variables(args.file, known_variables)

    # Print undeclared variables
    if undeclared_variables:
        print("\nUndeclared variables found:")
        for var in sorted(undeclared_variables):
            print(f"Variable '{var}' is used but not declared.")
    else:
        print("No undeclared variables found.")

if __name__ == "__main__":
    main()

