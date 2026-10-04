"""
tools/compiler - Modular C-to-CHIP-8 compiler for Flashiibo FEB SDK.
"""

import os
from .lexer import Token, Lexer
from .preprocessor import Preprocessor
from .parser import CParser
from .codegen import CodeGenerator


class CCompiler:
    """Generic C-to-CHIP-8 Compiler."""

    def __init__(self, include_dirs=None):
        self.include_dirs = include_dirs or []

    def compile(self, c_filepath):
        preprocessor = Preprocessor(self.include_dirs)
        preprocessed_text = preprocessor.process(c_filepath)

        lexer = Lexer(preprocessed_text)
        tokens = []
        while True:
            t = lexer.next_token()
            tokens.append(t)
            if t.type == "EOF":
                break

        parser = CParser(tokens, macros=preprocessor.macros)
        parser.parse_program()

        ast_data = {
            "globals": parser.globals,
            "functions": parser.functions,
            "strings": parser.strings,
            "struct_types": parser.struct_types,
        }

        codegen = CodeGenerator(ast_data, macros=preprocessor.macros)
        return codegen.generate()


def compile_c_to_asm(c_filepath, include_dirs=None):
    """
    Public entry point to compile a C source file to CHIP-8 assembly.
    """
    if include_dirs is None:
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        include_dirs = [
            os.path.join(repo_root, "include"),
            os.path.dirname(os.path.abspath(c_filepath)),
        ]
    compiler = CCompiler(include_dirs)
    return compiler.compile(c_filepath)
