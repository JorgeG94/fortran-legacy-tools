import argparse
from undeclared import collect_known_variables, find_undeclared_variables

def main():
    parser = argparse.ArgumentParser(description="Fortran Variable Declaration, Parameter, Common Block, Data Statement, and Undeclared Variable Analyzer")
    parser.add_argument("file", help="Path to the Fortran file to analyze")
    
    args = parser.parse_args()
    
    # Collect all known variables
    known_variables = collect_known_variables(args.file)

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

