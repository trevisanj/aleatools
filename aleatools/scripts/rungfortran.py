"""
Runs gfortran filtering out "deleted feature" warnings
"""

import subprocess, argparse, a107, re

def compile_fortran(command):
    # Compile the Fortran code
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Capture the output and errors
    stdout, stderr = process.communicate()



    # Filter out blocks of warnings related to "Deleted feature"

    print(a107.format_box("STDERR", fmt=str))

    filtered_lines = []
    current_block = []
    expr = re.compile(".*:.*:.*:")
    flag_skip = False
    for line in stderr.splitlines():

        if "deleted feature" in line.lower():
            # If the current block ends with a "Deleted feature" warning, discard it
            flag_skip = True
        elif expr.match(line):
            # End of a block, append it if it's not a deleted feature warning
            if not flag_skip:
                filtered_lines.extend(current_block)
            current_block = []
            flag_skip = False

        current_block.append(line)


    # Catch any remaining block after the loop
    if current_block and not flag_skip:
        filtered_lines.extend(current_block)

    # Print the filtered warnings (if any)
    if filtered_lines:
        print("\n".join(filtered_lines))

    print(a107.format_box("STDOUT", fmt=str))
    print(stdout)

    # Return the exit code of the compilation process
    return process.returncode

# Example usage
source_file = "your_code.f90"
output_file = "your_program"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__,  formatter_class=a107.SmartFormatter)
    parser.add_argument('statement', nargs="?")

    args = parser.parse_args()

    if args.statement is None:
        parser.error("Please specify statement")

    exit_code = compile_fortran(args.statement)
