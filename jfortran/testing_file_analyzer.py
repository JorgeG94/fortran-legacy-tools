import unittest
from variable_collector import collect_declared_variables, collect_parameter_variables,collect_common_blocks, collect_data_initializations
from undeclared import (
    collect_known_variables,
    remove_string_literals,
    find_undeclared_variables,
    is_fortran_keyword
)

class TestVariableCollector(unittest.TestCase):

    def test_single_line_declaration(self):
        file_content = """\
        integer ddi_world, ddi_group, ddi_subgroup, ddi_superworld
        logical aimpac, rpac, pltorb
        character*40 versn
        character*20 inpwar
        double precision morokm
        real*8 distance
        """
        with open('test_single_line.f90', 'w') as f:
            f.write(file_content)
        
        expected_variables = {
            'ddi_world': 'integer',
            'ddi_group': 'integer',
            'ddi_subgroup': 'integer',
            'ddi_superworld': 'integer',
            'aimpac': 'logical',
            'rpac': 'logical',
            'pltorb': 'logical',
            'versn': 'character',
            'inpwar': 'character',
            'morokm': 'double precision',
            'distance': 'real'
        }
        
        self.assertEqual(collect_declared_variables('test_single_line.f90'), expected_variables)

    def test_multi_line_declaration(self):
        file_content = """\
        integer ddi_world, ddi_group, &
                ddi_subgroup, ddi_superworld
        logical aimpac, rpac, &
                pltorb
        character*40 versn
        double precision morokm
        real*8 distance
        """
        with open('test_multi_line.f90', 'w') as f:
            f.write(file_content)

        expected_variables = {
            'ddi_world': 'integer',
            'ddi_group': 'integer',
            'ddi_subgroup': 'integer',
            'ddi_superworld': 'integer',
            'aimpac': 'logical',
            'rpac': 'logical',
            'pltorb': 'logical',
            'versn': 'character',
            'morokm': 'double precision',
            'distance': 'real'
        }
        
        self.assertEqual(collect_declared_variables('test_multi_line.f90'), expected_variables)

    def test_mixed_declarations(self):
        file_content = """\
        integer ddi_world, ddi_group
        logical aimpac
        character*40 versn
        double precision morokm
        real*8 distance
        integer ddi_subgroup, ddi_superworld
        logical rpac, pltorb
        """
        with open('test_mixed.f90', 'w') as f:
            f.write(file_content)

        expected_variables = {
            'ddi_world': 'integer',
            'ddi_group': 'integer',
            'ddi_subgroup': 'integer',
            'ddi_superworld': 'integer',
            'aimpac': 'logical',
            'rpac': 'logical',
            'pltorb': 'logical',
            'versn': 'character',
            'morokm': 'double precision',
            'distance': 'real'
        }
        
        self.assertEqual(collect_declared_variables('test_mixed.f90'), expected_variables)

    def test_no_declarations(self):
        file_content = """\
        print *, 'Hello, world!'
        call some_subroutine()
        """
        with open('test_no_declarations.f90', 'w') as f:
            f.write(file_content)

        expected_variables = {}
        
        self.assertEqual(collect_declared_variables('test_no_declarations.f90'), expected_variables)

    def test_parameter_variables(self):
        file_content = """\
        integer ddi_world, ddi_group
        parameter (ddi_world=0)
        parameter (ddi_group=1)
        """
        with open('test_parameters.f90', 'w') as f:
            f.write(file_content)

        expected_parameters = {
            'ddi_world': 'parameter',
            'ddi_group': 'parameter',
        }

        self.assertEqual(collect_parameter_variables('test_parameters.f90'), expected_parameters)


    def test_single_line_common_block(self):
        file_content = """\
        common /chmgms/ xchm(mxchrm), ychm(mxchrm), zchm(mxchrm)
        """
        with open('test_single_line_common.f90', 'w') as f:
            f.write(file_content)

        expected_common_blocks = {
            'chmgms': ['xchm', 'ychm', 'zchm']
        }

        self.assertEqual(collect_common_blocks('test_single_line_common.f90'), expected_common_blocks)

    def test_multi_line_common_block(self):
        file_content = """\
        common /chmgms/ xchm(mxchrm), ychm(mxchrm), zchm(mxchrm), &
                        dxelmm(mxchrm), dyelmm(mxchrm), dzelmm(mxchrm)
        common /cifils/ nft11, nft12, nft13, nft14, nft15, nft16, idaf20, nememx
        """
        with open('test_multi_line_common.f90', 'w') as f:
            f.write(file_content)

        expected_common_blocks = {
            'chmgms': ['xchm', 'ychm', 'zchm', 'dxelmm', 'dyelmm', 'dzelmm'],
            'cifils': ['nft11', 'nft12', 'nft13', 'nft14', 'nft15', 'nft16', 'idaf20', 'nememx']
        }

        self.assertEqual(collect_common_blocks('test_multi_line_common.f90'), expected_common_blocks)

    def test_no_common_blocks(self):
        file_content = """\
        integer a, b, c
        logical flag
        """
        with open('test_no_common_blocks.f90', 'w') as f:
            f.write(file_content)

        expected_common_blocks = {}

        self.assertEqual(collect_common_blocks('test_no_common_blocks.f90'), expected_common_blocks)
    def test_single_line_data(self):
        file_content = """\
        data check /8HCHECK /
        """
        with open('test_single_line_data.f90', 'w') as f:
            f.write(file_content)

        expected_data_initializations = {
            'check': 'CHECK'
        }

        self.assertEqual(collect_data_initializations('test_single_line_data.f90'), expected_data_initializations)

    def test_multi_line_data(self):
        file_content = """\
        data check /8HCHECK /,energy /8HENERGY /,anebp /8HNEBPATH /
        data morokm /8HMOROKUMA/,globop /8HGLOBOP /,fmohess/8HFMOHESS /
        """
        with open('test_multi_line_data.f90', 'w') as f:
            f.write(file_content)

        expected_data_initializations = {
            'check': 'CHECK',
            'energy': 'ENERGY',
            'anebp': 'NEBPATH',
            'morokm': 'MOROKUMA',
            'globop': 'GLOBOP',
            'fmohess': 'FMOHESS',
        }

        self.assertEqual(collect_data_initializations('test_multi_line_data.f90'), expected_data_initializations)

    def test_data_with_blanks(self):
        file_content = """\
        data blank /8H        /
        """
        with open('test_data_with_blanks.f90', 'w') as f:
            f.write(file_content)

        expected_data_initializations = {
            'blank': ''
        }

        self.assertEqual(collect_data_initializations('test_data_with_blanks.f90'), expected_data_initializations)

    def test_collect_known_variables(self):
        file_content = """\
        integer a, b
        parameter (c=1)
        common /block1/ d, e, f
        data g /8HSTRING /
        """
        with open('test_known_variables.f90', 'w') as f:
            f.write(file_content)

        expected_known_variables = {'a', 'b', 'c', 'd', 'e', 'f', 'g'}

        self.assertEqual(collect_known_variables('test_known_variables.f90'), expected_known_variables)

    def test_remove_string_literals(self):
        line = "print *, 'This is a test', var1, 'Another string'"
        expected_result = "print *, , var1, "
        self.assertEqual(remove_string_literals(line), expected_result)

        line_with_no_strings = "a = b + c"
        self.assertEqual(remove_string_literals(line_with_no_strings), line_with_no_strings)

    def test_find_undeclared_variables(self):
        file_content = """\
        integer a, b
        parameter (c=1)
        common /block1/ d, e, f
        data g /8HSTRING /
        print *, 'This is a test', var1, 'Another string'
        x = a + b + c
        y = d + e + f
        z = g + h
        9001 format(' EXECUTION OF GAMESS BEGUN ',3a8)
        9002 format(' EXECUTION OF GAMESS TERMINATED NORMALLY ',3a8)
        """
        with open('test_find_undeclared_variables.f90', 'w') as f:
            f.write(file_content)

        known_variables = collect_known_variables('test_find_undeclared_variables.f90')
        expected_undeclared_variables = {'var1', 'x', 'y', 'z', 'h'}

        self.assertEqual(find_undeclared_variables('test_find_undeclared_variables.f90', known_variables), expected_undeclared_variables)


    def test_is_fortran_keyword(self):
        # Test basic Fortran keywords
        self.assertTrue(is_fortran_keyword('if'))
        self.assertTrue(is_fortran_keyword('do'))
        self.assertTrue(is_fortran_keyword('then'))
        self.assertTrue(is_fortran_keyword('subroutine'))
        self.assertTrue(is_fortran_keyword('module'))
        
        # Test logical and relational operators
        self.assertTrue(is_fortran_keyword('.and.'))
        self.assertTrue(is_fortran_keyword('.or.'))
        self.assertTrue(is_fortran_keyword('.not.'))
        self.assertTrue(is_fortran_keyword('.eq.'))
        self.assertTrue(is_fortran_keyword('.ne.'))
        self.assertTrue(is_fortran_keyword('.lt.'))
        self.assertTrue(is_fortran_keyword('.le.'))
        self.assertTrue(is_fortran_keyword('.gt.'))
        self.assertTrue(is_fortran_keyword('.ge.'))
        self.assertTrue(is_fortran_keyword('.eqv.'))
        self.assertTrue(is_fortran_keyword('.neqv.'))
        
        # Test non-Fortran words
        self.assertFalse(is_fortran_keyword('variable'))
        self.assertFalse(is_fortran_keyword('customSubroutine'))
        self.assertFalse(is_fortran_keyword('myfunction'))
        self.assertFalse(is_fortran_keyword('.customOp.'))

if __name__ == '__main__':
    unittest.main()

