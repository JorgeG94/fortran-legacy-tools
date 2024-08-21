import unittest
import tempfile
import os
from add_names_to_ends import process_fortran_file, replace_generic_end

class TestFortranProcessing(unittest.TestCase):

    def setUp(self):
        """Create a temporary file for testing."""
        self.test_dir = tempfile.TemporaryDirectory()
        self.test_file_path = os.path.join(self.test_dir.name, "test_file.f90")

    def tearDown(self):
        """Clean up the temporary directory after tests."""
        self.test_dir.cleanup()

    def write_to_file(self, content):
        with open(self.test_file_path, 'w') as file:
            file.write(content)

    def read_file(self):
        with open(self.test_file_path, 'r') as file:
            return file.read()

    def test_process_fortran_file(self):
        content = (
            "subroutine mysub()\n"
            "  ! some code\n"
            "end subroutine\n"
            "function myfunc() result(res)\n"
            "  ! some code\n"
            "end function\n"
            "module mymodule\n"
            "  ! some code\n"
            "end module\n"
        )
        expected_output = (
            "subroutine mysub()\n"
            "  ! some code\n"
            "end subroutine mysub\n"
            "function myfunc() result(res)\n"
            "  ! some code\n"
            "end function myfunc\n"
            "module mymodule\n"
            "  ! some code\n"
            "end module mymodule\n"
        )

        self.write_to_file(content)
        process_fortran_file(self.test_file_path)
        result = self.read_file()

        self.assertEqual(result, expected_output)

    def test_replace_generic_end(self):
        content = (
            "subroutine mysub()\n"
            "  ! some code\n"
            "end\n"
            "function myfunc() result(res)\n"
            "  ! some code\n"
            "end\n"
            "module mymodule\n"
            "  ! some code\n"
            "end\n"
        )
        expected_output = (
            "subroutine mysub()\n"
            "  ! some code\n"
            "end subroutine mysub\n"
            "function myfunc() result(res)\n"
            "  ! some code\n"
            "end function myfunc\n"
            "module mymodule\n"
            "  ! some code\n"
            "end module mymodule\n"
        )

        self.write_to_file(content)
        replace_generic_end(self.test_file_path)
        result = self.read_file()

        self.assertEqual(result, expected_output)

    def test_process_fortran_file_with_type_function(self):
        content = (
            "integer function myfunc() result(res)\n"
            "  ! some code\n"
            "end function\n"
        )
        expected_output = (
            "integer function myfunc() result(res)\n"
            "  ! some code\n"
            "end function myfunc\n"
        )

        self.write_to_file(content)
        process_fortran_file(self.test_file_path)
        result = self.read_file()

        self.assertEqual(result, expected_output)

    def test_replace_generic_end_with_type_function(self):
        content = (
            "integer function myfunc() result(res)\n"
            "  ! some code\n"
            "end\n"
        )
        expected_output = (
            "integer function myfunc() result(res)\n"
            "  ! some code\n"
            "end function myfunc\n"
        )

        self.write_to_file(content)
        replace_generic_end(self.test_file_path)
        result = self.read_file()

        self.assertEqual(result, expected_output)
    def test_process_fortran_file_with_module(self):
        content = (
            "module mymodule\n"
            "  subroutine mysub()\n"
            "    ! some code\n"
            "  end subroutine\n"
            "  integer function myfunc() result(res)\n"
            "    ! some code\n"
            "  end function\n"
            "end module\n"
        )
        expected_output = (
            "module mymodule\n"
            "  subroutine mysub()\n"
            "    ! some code\n"
            "  end subroutine mysub\n"
            "  integer function myfunc() result(res)\n"
            "    ! some code\n"
            "  end function myfunc\n"
            "end module mymodule\n"
        )

        self.write_to_file(content)
        process_fortran_file(self.test_file_path)
        result = self.read_file()

        self.assertEqual(result, expected_output)

    def test_replace_generic_end_with_module(self):
        content = (
            "module mymodule\n"
            "  subroutine mysub()\n"
            "    ! some code\n"
            "  end\n"
            "  integer function myfunc() result(res)\n"
            "    ! some code\n"
            "  end\n"
            "end\n"
        )
        expected_output = (
            "module mymodule\n"
            "  subroutine mysub()\n"
            "    ! some code\n"
            "  end subroutine mysub\n"
            "  integer function myfunc() result(res)\n"
            "    ! some code\n"
            "  end function myfunc\n"
            "end module mymodule\n"
        )

        self.write_to_file(content)
        replace_generic_end(self.test_file_path)
        result = self.read_file()
#        print(result)

        self.assertEqual(result, expected_output)


if __name__ == "__main__":
    unittest.main()

