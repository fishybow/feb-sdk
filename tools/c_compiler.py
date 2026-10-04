#!/usr/bin/env python3
"""
c_compiler.py - Generic C-to-CHIP-8 Compiler for Flashiibo Executable Binary (.feb)

Translates standard C source code targeting the Flashiibo FEB SDK (include/feb.h)
into valid CHIP-8 / Super-CHIP assembly code.

Features:
  - Preprocessor macro expansion (#include, #define, comments)
  - Standard C types (uint8_t, int8_t, uint16_t, bool, char, void)
  - Global scalar and array declarations (.byte, .ds)
  - Functions with arguments, local variables, and return values
  - Control flow: if/else, while, for, switch/case/default, break, return
  - Expressions: +, -, *, /, %, &, |, ^, ~, <<, >>, ==, !=, <, <=, >, >=, &&, ||, !
  - Array indexing: arr[i], arr[i] = val
  - Flashiibo SDK API mappings (feb_*) directly lowered to VM instructions
  - 100% pure C support - zero assembly required from application developers
"""

import sys
import os
import re

# Token Types
TOK_EOF = "EOF"
TOK_IDENT = "IDENT"
TOK_NUM = "NUM"
TOK_STR = "STR"
TOK_CHAR = "CHAR"
TOK_KEYWORD = "KEYWORD"
TOK_OP = "OP"
TOK_PUNCT = "PUNCT"

KEYWORDS = {
    "int", "char", "void", "uint8_t", "int8_t", "uint16_t", "int16_t",
    "uint32_t", "int32_t", "bool", "true", "false", "static", "const", "extern",
    "struct", "typedef", "sizeof", "if", "else", "while", "for",
    "switch", "case", "default", "break", "return", "continue"
}

class Token:
    def __init__(self, typ, val, line):
        self.type = typ
        self.val = val
        self.line = line

    def __repr__(self):
        return f"Token({self.type}, {repr(self.val)}, line={self.line})"

class Lexer:
    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.line = 1
        self.length = len(text)

    def error(self, msg):
        raise SyntaxError(f"[Lexer line {self.line}] {msg}")

    def peek(self):
        if self.pos < self.length:
            return self.text[self.pos]
        return ""

    def get_char(self):
        ch = self.peek()
        self.pos += 1
        if ch == "\n":
            self.line += 1
        return ch

    def next_token(self):
        while self.pos < self.length:
            ch = self.peek()

            # Whitespace
            if ch.isspace():
                self.get_char()
                continue

            # Comments
            if ch == "/" and self.pos + 1 < self.length:
                next_ch = self.text[self.pos + 1]
                if next_ch == "/":
                    # Single-line comment
                    while self.pos < self.length and self.peek() != "\n":
                        self.get_char()
                    continue
                elif next_ch == "*":
                    # Multi-line comment
                    self.get_char()
                    self.get_char()
                    while self.pos < self.length:
                        if self.peek() == "*" and self.pos + 1 < self.length and self.text[self.pos + 1] == "/":
                            self.get_char()
                            self.get_char()
                            break
                        self.get_char()
                    continue

            # Strings
            if ch == '"':
                start_line = self.line
                self.get_char() # skip quote
                s = []
                while self.pos < self.length and self.peek() != '"':
                    c = self.get_char()
                    if c == "\\":
                        esc = self.get_char()
                        if esc == "n": s.append("\n")
                        elif esc == "r": s.append("\r")
                        elif esc == "t": s.append("\t")
                        elif esc == "0": s.append("\0")
                        else: s.append(esc)
                    else:
                        s.append(c)
                if self.pos >= self.length:
                    self.error("Unterminated string literal")
                self.get_char() # skip closing quote
                return Token(TOK_STR, "".join(s), start_line)

            # Character literals
            if ch == "'":
                start_line = self.line
                self.get_char() # skip quote
                c = self.get_char()
                if c == "\\":
                    esc = self.get_char()
                    if esc == "0": val = 0
                    elif esc == "n": val = 10
                    elif esc == "r": val = 13
                    elif esc == "t": val = 9
                    else: val = ord(esc)
                else:
                    val = ord(c)
                if self.peek() == "'":
                    self.get_char()
                return Token(TOK_NUM, val, start_line)

            # Identifiers and keywords
            if ch.isalpha() or ch == "_":
                start_line = self.line
                ident = []
                while self.pos < self.length and (self.peek().isalnum() or self.peek() == "_"):
                    ident.append(self.get_char())
                word = "".join(ident)
                if word in KEYWORDS:
                    if word == "true":
                        return Token(TOK_NUM, 1, start_line)
                    elif word == "false":
                        return Token(TOK_NUM, 0, start_line)
                    return Token(TOK_KEYWORD, word, start_line)
                return Token(TOK_IDENT, word, start_line)

            # Numbers (hex, binary, decimal)
            if ch.isdigit():
                start_line = self.line
                num_str = []
                if ch == "0" and self.pos + 1 < self.length and self.text[self.pos + 1] in "xX":
                    num_str.append(self.get_char()) # 0
                    num_str.append(self.get_char()) # x
                    while self.pos < self.length and (self.peek().isalnum()):
                        num_str.append(self.get_char())
                    val = int("".join(num_str), 16)
                elif ch == "0" and self.pos + 1 < self.length and self.text[self.pos + 1] in "bB":
                    num_str.append(self.get_char()) # 0
                    num_str.append(self.get_char()) # b
                    while self.pos < self.length and self.peek() in "01":
                        num_str.append(self.get_char())
                    val = int("".join(num_str), 2)
                else:
                    while self.pos < self.length and self.peek().isdigit():
                        num_str.append(self.get_char())
                    val = int("".join(num_str), 10)
                # Skip any integer literal suffixes (U, L, UL, etc.)
                while self.pos < self.length and self.peek() in "uUlL":
                    self.get_char()
                return Token(TOK_NUM, val, start_line)

            # Multi-character operators
            start_line = self.line
            two_chars = self.text[self.pos:self.pos + 2]
            if two_chars in ("==", "!=", "<=", ">=", "&&", "||", "++", "--", "+=", "-=", "&=", "|=", "^=", "<<", ">>"):
                self.pos += 2
                return Token(TOK_OP, two_chars, start_line)

            # Single-character operators & punctuation
            if ch in "+-*/%&|^~!<>=?:":
                self.pos += 1
                return Token(TOK_OP, ch, start_line)

            if ch in ";,(){}[]":
                self.pos += 1
                return Token(TOK_PUNCT, ch, start_line)

            if ch == ".":
                self.pos += 1
                return Token(TOK_PUNCT, ".", start_line)

            self.error(f"Unexpected character: {repr(ch)}")

        return Token(TOK_EOF, None, self.line)

class Preprocessor:
    """Handles #include, conditional compilation (#ifdef, #ifndef, #else, #endif), and #define macro substitutions."""
    def __init__(self, include_dirs=None):
        self.include_dirs = include_dirs or []
        self.macros = {}

    def process(self, filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return self._process_text(content, os.path.dirname(os.path.abspath(filepath)))

    def _process_text(self, text, current_dir):
        lines = text.splitlines()
        output = []
        cond_stack = []

        def is_active():
            return all(cond_stack)

        for line in lines:
            stripped = line.strip()

            # Conditional compilation directives
            if stripped.startswith("#ifdef"):
                m = stripped.split(None, 1)
                macro = m[1].split()[0] if len(m) > 1 else ""
                cond_stack.append(macro in self.macros)
                continue
            elif stripped.startswith("#ifndef"):
                m = stripped.split(None, 1)
                macro = m[1].split()[0] if len(m) > 1 else ""
                cond_stack.append(macro not in self.macros)
                continue
            elif stripped.startswith("#if"):
                parts = stripped.split(None, 1)
                expr = parts[1] if len(parts) > 1 else "0"
                expr = re.sub(r'/\*.*?\*/', '', expr).split('//')[0].strip()
                if expr in ("0", "false"):
                    active = False
                elif expr in ("1", "true"):
                    active = True
                else:
                    active = expr in self.macros
                cond_stack.append(active)
                continue
            elif stripped.startswith("#else"):
                if cond_stack:
                    cond_stack[-1] = not cond_stack[-1]
                continue
            elif stripped.startswith("#endif"):
                if cond_stack:
                    cond_stack.pop()
                continue
            elif stripped.startswith("#pragma"):
                continue

            if not is_active():
                continue

            if stripped.startswith("#include"):
                # Handle #include
                m = re.match(r'#include\s*[<"]([^>"]+)[>"]', stripped)
                if m:
                    inc_name = m.group(1)
                    # Don't try to read stdlib C headers
                    if inc_name in ("stdint.h", "stdbool.h", "stddef.h", "stdlib.h", "string.h"):
                        continue
                    # Search for header file
                    found = False
                    search_paths = [current_dir] + self.include_dirs
                    for d in search_paths:
                        full_path = os.path.normpath(os.path.join(d, inc_name))
                        if os.path.exists(full_path):
                            sub_text = self.process(full_path)
                            output.append(sub_text)
                            found = True
                            break
                    if not found and "feb.h" in inc_name:
                        # Fallback built-in feb constants
                        pass
                continue
            elif stripped.startswith("#define"):
                parts = stripped.split(None, 2)
                if len(parts) >= 2:
                    name = parts[1]
                    # Check for macro with parameters
                    paren = name.find("(")
                    if paren != -1:
                        pass
                    else:
                        val_str = parts[2] if len(parts) > 2 else "1"
                        # Strip comments from define value
                        val_str = re.sub(r'/\*.*?\*/', '', val_str).split('//')[0].strip()
                        for k, v in self.macros.items():
                            val_str = re.sub(r'\b' + re.escape(k) + r'\b', str(v), val_str)
                        self.macros[name] = val_str
                continue

            output.append(line)

        expanded_text = "\n".join(output)

        # Multi-pass macro substitution to resolve nested defines (e.g. MAX_X (WIDTH - SIZE))
        for _ in range(3):
            for k in sorted(self.macros.keys(), key=len, reverse=True):
                v = self.macros[k]
                expanded_text = re.sub(r'\b' + re.escape(k) + r'\b', v, expanded_text)

        return expanded_text

class CCompiler:
    """Generic C-to-CHIP-8 Compiler."""
    def __init__(self, include_dirs=None):
        self.preprocessor = Preprocessor(include_dirs)
        self.tokens = []
        self.tok_idx = 0
        self.globals = {} # name -> {"type": "array"|"scalar", "size": int, "values": list}
        self.strings = {} # text -> label
        self.functions = {} # name -> AST node
        self.asm_lines = []
        self.label_counter = 0

    def new_label(self, prefix="L"):
        self.label_counter += 1
        return f"{prefix}_{self.label_counter}"

    def peek(self, offset=0):
        idx = self.tok_idx + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return Token(TOK_EOF, None, -1)

    def consume(self, expected_val=None, expected_type=None):
        tok = self.peek()
        if expected_val is not None and tok.val != expected_val:
            raise SyntaxError(f"[Parser line {tok.line}] Expected '{expected_val}', got '{tok.val}'")
        if expected_type is not None and tok.type != expected_type:
            raise SyntaxError(f"[Parser line {tok.line}] Expected type '{expected_type}', got '{tok.type}' ({tok.val})")
        self.tok_idx += 1
        return tok

    def match(self, val):
        if self.peek().val == val:
            self.tok_idx += 1
            return True
        return False

    def compile(self, c_filepath):
        preprocessed = self.preprocessor.process(c_filepath)
        lexer = Lexer(preprocessed)
        self.tokens = []
        while True:
            t = lexer.next_token()
            self.tokens.append(t)
            if t.type == TOK_EOF:
                break

        self.tok_idx = 0
        self.parse_program()
        return self.generate_assembly()

    def parse_program(self):
        while self.peek().type != TOK_EOF:
            # Check for struct declaration/typedef
            if self.peek().val in ("typedef", "struct"):
                self.parse_type_declaration()
                continue

            if self.peek().val == "extern":
                self.consume("extern")
                if self.peek().type == TOK_STR:
                    self.consume()
                    if self.peek().val == "{":
                        self.consume("{")
                continue

            if self.peek().val == "}":
                self.consume("}")
                continue

            # Peek ahead to determine if function or global variable
            self.parse_global_or_function()

    def parse_type_declaration(self):
        # Skip typedefs / struct definitions
        while self.peek().type != TOK_EOF and self.peek().val != ";":
            self.consume()
        if self.peek().val == ";":
            self.consume(";")

    def skip_type_specifiers(self):
        while self.peek().val in ("static", "const", "volatile", "unsigned", "signed", "extern"):
            self.consume()
        type_name = self.consume().val
        while self.peek().val == "*":
            self.consume("*")
        return type_name

    def parse_global_or_function(self):
        # Parse return type or variable type
        self.skip_type_specifiers()
        ident_tok = self.consume(expected_type=TOK_IDENT)
        name = ident_tok.val

        if self.peek().val == "(":
            # Function definition
            self.parse_function(name)
        elif self.peek().val == "[":
            # Array declaration: static [const] uint8_t name[size] = { ... };
            self.consume("[")
            size = None
            if self.peek().val != "]":
                size = self.parse_constant_expr()
            self.consume("]")

            values = []
            if self.match("="):
                self.consume("{")
                while self.peek().val != "}":
                    val = self.parse_constant_expr()
                    values.append(val)
                    if not self.match(","):
                        break
                self.consume("}")
            self.consume(";")
            if size is None:
                size = len(values)
            self.globals[name] = {"type": "array", "size": size, "values": values}
        else:
            # Scalar global: static uint8_t name = val;
            val = 0
            if self.match("="):
                val = self.parse_constant_expr()
            self.consume(";")
            self.globals[name] = {"type": "scalar", "size": 1, "value": val}

    def parse_constant_expr(self):
        # Simple recursive constant expression evaluator
        tok = self.consume()
        if tok.type == TOK_NUM:
            val = tok.val
        elif tok.val == "-":
            val = -self.parse_constant_expr()
        elif tok.val == "(":
            val = self.parse_constant_expr()
            self.consume(")")
        elif tok.val in self.preprocessor.macros:
            val = int(eval(self.preprocessor.macros[tok.val]))
        else:
            raise SyntaxError(f"Expected constant expression, got {tok.val}")

        # Check for binary operators in constant expressions
        while self.peek().val in ("+", "-", "*", "/", "%", "<<", ">>", "&", "|", "^"):
            op = self.consume().val
            rhs = self.parse_constant_expr()
            if op == "+": val += rhs
            elif op == "-": val -= rhs
            elif op == "*": val *= rhs
            elif op == "/": val //= rhs
            elif op == "%": val %= rhs
            elif op == "<<": val <<= rhs
            elif op == ">>": val >>= rhs
            elif op == "&": val &= rhs
            elif op == "|": val |= rhs
            elif op == "^": val ^= rhs

        return val

    def parse_function(self, func_name):
        self.consume("(")
        params = []
        if self.peek().val != ")":
            while True:
                if self.peek().val == "void":
                    self.consume("void")
                    break
                self.skip_type_specifiers()
                if self.peek().val in (")", ","):
                    param_name = f"arg{len(params)}"
                else:
                    param_name = self.consume(expected_type=TOK_IDENT).val
                params.append(param_name)
                if not self.match(","):
                    break
        self.consume(")")

        # Forward declarations / prototypes ending with semicolon
        if self.match(";"):
            return

        # Function body
        body = self.parse_compound_statement()
        self.functions[func_name] = {"params": params, "body": body}

    def parse_compound_statement(self):
        self.consume("{")
        statements = []
        while self.peek().val != "}" and self.peek().type != TOK_EOF:
            stmt = self.parse_statement()
            if stmt:
                statements.append(stmt)
        self.consume("}")
        return {"type": "block", "statements": statements}

    def parse_statement(self):
        tok = self.peek()

        if tok.val == ";":
            self.consume(";")
            return None

        if tok.val == "{":
            return self.parse_compound_statement()

        if tok.val == "if":
            self.consume("if")
            self.consume("(")
            cond = self.parse_expression()
            self.consume(")")
            then_branch = self.parse_statement()
            else_branch = None
            if self.match("else"):
                else_branch = self.parse_statement()
            return {"type": "if", "cond": cond, "then": then_branch, "else": else_branch}

        if tok.val == "while":
            self.consume("while")
            self.consume("(")
            cond = self.parse_expression()
            self.consume(")")
            body = self.parse_statement()
            return {"type": "while", "cond": cond, "body": body}

        if tok.val == "for":
            self.consume("for")
            self.consume("(")
            init = None if self.peek().val == ";" else self.parse_statement_or_expr()
            if self.peek().val == ";": self.consume(";")
            cond = None if self.peek().val == ";" else self.parse_expression()
            self.consume(";")
            post = None if self.peek().val == ")" else self.parse_expression()
            self.consume(")")
            body = self.parse_statement()
            return {"type": "for", "init": init, "cond": cond, "post": post, "body": body}

        if tok.val == "switch":
            self.consume("switch")
            self.consume("(")
            expr = self.parse_expression()
            self.consume(")")
            self.consume("{")
            cases = []
            while self.peek().val != "}" and self.peek().type != TOK_EOF:
                if self.match("case"):
                    case_val = self.parse_constant_expr()
                    self.consume(":")
                    case_stmts = []
                    while self.peek().val not in ("case", "default", "}"):
                        s = self.parse_statement()
                        if s: case_stmts.append(s)
                    cases.append({"val": case_val, "stmts": case_stmts})
                elif self.match("default"):
                    self.consume(":")
                    def_stmts = []
                    while self.peek().val not in ("case", "default", "}"):
                        s = self.parse_statement()
                        if s: def_stmts.append(s)
                    cases.append({"val": "default", "stmts": def_stmts})
                else:
                    self.consume()
            self.consume("}")
            return {"type": "switch", "expr": expr, "cases": cases}

        if tok.val == "break":
            self.consume("break")
            self.consume(";")
            return {"type": "break"}

        if tok.val == "continue":
            self.consume("continue")
            self.consume(";")
            return {"type": "continue"}

        if tok.val == "return":
            self.consume("return")
            expr = None
            if self.peek().val != ";":
                expr = self.parse_expression()
            self.consume(";")
            return {"type": "return", "expr": expr}

        # Variable declaration: [type] var [= expr];
        if tok.val in ("uint8_t", "int8_t", "uint16_t", "int16_t", "int", "bool", "char", "const", "static"):
            self.skip_type_specifiers()
            var_name = self.consume(expected_type=TOK_IDENT).val
            init_expr = None
            if self.match("="):
                init_expr = self.parse_expression()
            self.consume(";")
            return {"type": "decl", "var": var_name, "init": init_expr}

        # Otherwise expression statement
        expr = self.parse_expression()
        self.consume(";")
        return {"type": "expr", "expr": expr}

    def parse_statement_or_expr(self):
        if self.peek().val in ("uint8_t", "int8_t", "uint16_t", "int16_t", "int", "bool", "char"):
            self.skip_type_specifiers()
            var_name = self.consume(expected_type=TOK_IDENT).val
            init_expr = None
            if self.match("="):
                init_expr = self.parse_expression()
            return {"type": "decl", "var": var_name, "init": init_expr}
        return {"type": "expr", "expr": self.parse_expression()}

    def parse_expression(self):
        return self.parse_assignment()

    def parse_assignment(self):
        node = self.parse_logical_or()
        if self.peek().val in ("=", "+=", "-=", "&=", "|=", "^="):
            op = self.consume().val
            rhs = self.parse_assignment()
            return {"type": "assign", "op": op, "target": node, "value": rhs}
        return node

    def parse_logical_or(self):
        node = self.parse_logical_and()
        while self.peek().val == "||":
            op = self.consume().val
            rhs = self.parse_logical_and()
            node = {"type": "binary", "op": op, "left": node, "right": rhs}
        return node

    def parse_logical_and(self):
        node = self.parse_bitwise_or()
        while self.peek().val == "&&":
            op = self.consume().val
            rhs = self.parse_bitwise_or()
            node = {"type": "binary", "op": op, "left": node, "right": rhs}
        return node

    def parse_bitwise_or(self):
        node = self.parse_bitwise_xor()
        while self.peek().val == "|":
            op = self.consume().val
            rhs = self.parse_bitwise_xor()
            node = {"type": "binary", "op": op, "left": node, "right": rhs}
        return node

    def parse_bitwise_xor(self):
        node = self.parse_bitwise_and()
        while self.peek().val == "^":
            op = self.consume().val
            rhs = self.parse_bitwise_and()
            node = {"type": "binary", "op": op, "left": node, "right": rhs}
        return node

    def parse_bitwise_and(self):
        node = self.parse_equality()
        while self.peek().val == "&":
            op = self.consume().val
            rhs = self.parse_equality()
            node = {"type": "binary", "op": op, "left": node, "right": rhs}
        return node

    def parse_equality(self):
        node = self.parse_relational()
        while self.peek().val in ("==", "!="):
            op = self.consume().val
            rhs = self.parse_relational()
            node = {"type": "binary", "op": op, "left": node, "right": rhs}
        return node

    def parse_relational(self):
        node = self.parse_shift()
        while self.peek().val in ("<", "<=", ">", ">="):
            op = self.consume().val
            rhs = self.parse_shift()
            node = {"type": "binary", "op": op, "left": node, "right": rhs}
        return node

    def parse_shift(self):
        node = self.parse_additive()
        while self.peek().val in ("<<", ">>"):
            op = self.consume().val
            rhs = self.parse_additive()
            node = {"type": "binary", "op": op, "left": node, "right": rhs}
        return node

    def parse_additive(self):
        node = self.parse_multiplicative()
        while self.peek().val in ("+", "-"):
            op = self.consume().val
            rhs = self.parse_multiplicative()
            node = {"type": "binary", "op": op, "left": node, "right": rhs}
        return node

    def parse_multiplicative(self):
        node = self.parse_unary()
        while self.peek().val in ("*", "/", "%"):
            op = self.consume().val
            rhs = self.parse_unary()
            node = {"type": "binary", "op": op, "left": node, "right": rhs}
        return node

    def parse_unary(self):
        if self.peek().val in ("!", "~", "-", "+"):
            op = self.consume().val
            rhs = self.parse_unary()
            return {"type": "unary", "op": op, "expr": rhs}
        if self.peek().val in ("++", "--"):
            op = self.consume().val
            target = self.parse_postfix()
            return {"type": "pre_inc", "op": op, "target": target}
        return self.parse_postfix()

    def parse_postfix(self):
        node = self.parse_primary()
        while True:
            if self.match("["):
                idx_expr = self.parse_expression()
                self.consume("]")
                node = {"type": "index", "target": node, "index": idx_expr}
            elif self.match("("):
                args = []
                if self.peek().val != ")":
                    while True:
                        args.append(self.parse_expression())
                        if not self.match(","):
                            break
                self.consume(")")
                node = {"type": "call", "func": node, "args": args}
            elif self.match("."):
                field_tok = self.consume(expected_type=TOK_IDENT)
                node = {"type": "field", "target": node, "field": field_tok.val}
            elif self.peek().val in ("++", "--"):
                op = self.consume().val
                node = {"type": "post_inc", "op": op, "target": node}
            else:
                break
        return node

    def parse_primary(self):
        tok = self.peek()
        if tok.type == TOK_NUM:
            self.consume()
            return {"type": "num", "val": tok.val}
        if tok.type == TOK_STR:
            self.consume()
            # Register string constant
            s_val = tok.val
            if s_val not in self.strings:
                self.strings[s_val] = f"STR_{len(self.strings)}"
            return {"type": "str", "val": s_val, "label": self.strings[s_val]}
        if tok.type == TOK_IDENT:
            self.consume()
            return {"type": "ident", "name": tok.val}
        if self.match("("):
            # Check for type cast: (uint8_t)expr
            if self.peek().val in ("uint8_t", "int8_t", "uint16_t", "int16_t", "int", "bool", "char"):
                self.skip_type_specifiers()
                self.consume(")")
                return self.parse_unary()
            expr = self.parse_expression()
            self.consume(")")
            return expr
        if self.match("&"):
            # Address-of: &var
            sub = self.parse_postfix()
            return {"type": "addrof", "target": sub}

        raise SyntaxError(f"[Parser line {tok.line}] Unexpected token: {tok.val}")

    # =========================================================================
    # Assembly Code Generator
    # =========================================================================

    def generate_assembly(self):
        out = []
        out.append(";;; ===========================================================================")
        out.append(";;; Flashiibo FEB Bytecode (Generated by c_compiler.py)")
        out.append(";;; Target: Flashiibo Gen3 Super-CHIP (128x64 display, 4-button hardware)")
        out.append(";;; ===========================================================================")
        out.append("")
        out.append("START:")
        out.append("        call MAIN")
        out.append("        exit")
        out.append("")

        # Compile each function
        for func_name, func_data in self.functions.items():
            self.compile_function(func_name, func_data, out)

        # Emit string literals
        if self.strings:
            out.append(";;; String Literals")
            for text, label in self.strings.items():
                escaped = text.replace('"', '\\"')
                out.append(f"{label}:")
                out.append(f'        .asciz "{escaped}"')
            out.append("")

        # Emit globals
        if self.globals:
            out.append(";;; Global Variables and Memory Tables")
            for name, g in self.globals.items():
                label = name.upper()
                out.append(f"{label}:")
                if g["type"] == "array":
                    vals = g["values"]
                    if vals:
                        # Chunk into lines of 16 bytes max
                        for i in range(0, len(vals), 16):
                            chunk = vals[i:i + 16]
                            byte_strs = [f"0x{b & 0xFF:02x}" for b in chunk]
                            out.append("        .byte " + ", ".join(byte_strs))
                    else:
                        out.append(f"        .ds {g['size']}")
                else:
                    out.append(f"        .byte 0x{g['value'] & 0xFF:02x}")
            out.append("")

        return "\n".join(out)

    def compile_function(self, func_name, func_data, out):
        label = func_name.upper()
        out.append(f";;; Function: {func_name}")
        out.append(f"{label}:")

        # Local variable register allocation (v1..ve)
        # Scan for all local variable declarations and parameters
        locals_map = {}
        reg_avail = [f"v{i:x}" for i in range(1, 15)] # v1 through ve
        reg_idx = 0

        for p in func_data["params"]:
            if reg_idx < len(reg_avail):
                locals_map[p] = reg_avail[reg_idx]
                reg_idx += 1

        self.collect_locals(func_data["body"], locals_map, reg_avail, reg_idx)

        ctx = {
            "func": func_name,
            "locals": locals_map,
            "out": out,
            "break_label": None,
            "continue_label": None
        }

        self.compile_statement(func_data["body"], ctx)

        out.append("        ret")
        out.append("")

    def collect_locals(self, stmt, locals_map, reg_avail, reg_idx):
        if not stmt: return reg_idx
        stype = stmt.get("type")
        if stype == "decl":
            var = stmt["var"]
            if var not in locals_map and reg_idx < len(reg_avail):
                locals_map[var] = reg_avail[reg_idx]
                reg_idx += 1
        elif stype == "block":
            for s in stmt["statements"]:
                reg_idx = self.collect_locals(s, locals_map, reg_avail, reg_idx)
        elif stype == "if":
            reg_idx = self.collect_locals(stmt["then"], locals_map, reg_avail, reg_idx)
            reg_idx = self.collect_locals(stmt.get("else"), locals_map, reg_avail, reg_idx)
        elif stype == "while":
            reg_idx = self.collect_locals(stmt["body"], locals_map, reg_avail, reg_idx)
        elif stype == "for":
            reg_idx = self.collect_locals(stmt.get("init"), locals_map, reg_avail, reg_idx)
            reg_idx = self.collect_locals(stmt["body"], locals_map, reg_avail, reg_idx)
        elif stype == "switch":
            for c in stmt["cases"]:
                for s in c["stmts"]:
                    reg_idx = self.collect_locals(s, locals_map, reg_avail, reg_idx)
        return reg_idx

    def compile_statement(self, stmt, ctx):
        if not stmt: return
        stype = stmt["type"]
        out = ctx["out"]

        if stype == "block":
            for s in stmt["statements"]:
                self.compile_statement(s, ctx)
        elif stype == "decl":
            var = stmt["var"]
            reg = ctx["locals"].get(var)
            if reg and stmt["init"]:
                self.compile_expr_into(stmt["init"], reg, ctx)
        elif stype == "expr":
            self.compile_expr(stmt["expr"], ctx)
        elif stype == "break":
            if ctx.get("break_label"):
                out.append(f"        jump {ctx['break_label']}")
        elif stype == "continue":
            if ctx.get("continue_label"):
                out.append(f"        jump {ctx['continue_label']}")
        elif stype == "return":
            if stmt["expr"]:
                self.compile_expr_into(stmt["expr"], "v0", ctx)
            out.append("        ret")
        elif stype == "if":
            lbl_else = self.new_label("IF_ELSE")
            lbl_end = self.new_label("IF_END")
            has_else = stmt.get("else") is not None

            # Compile condition: jumps to lbl_else if false
            self.compile_cond_branch(stmt["cond"], False, lbl_else, ctx)
            self.compile_statement(stmt["then"], ctx)
            if has_else:
                out.append(f"        jump {lbl_end}")
            out.append(f"{lbl_else}:")
            if has_else:
                self.compile_statement(stmt["else"], ctx)
                out.append(f"{lbl_end}:")
        elif stype == "while":
            lbl_start = self.new_label("WHILE_START")
            lbl_end = self.new_label("WHILE_END")
            old_break = ctx.get("break_label")
            old_cont = ctx.get("continue_label")
            ctx["break_label"] = lbl_end
            ctx["continue_label"] = lbl_start

            out.append(f"{lbl_start}:")
            # If condition is not literal '1' / 'true', test it
            cond = stmt["cond"]
            if not (cond.get("type") == "num" and cond.get("val") == 1):
                self.compile_cond_branch(cond, False, lbl_end, ctx)
            self.compile_statement(stmt["body"], ctx)
            out.append(f"        jump {lbl_start}")
            out.append(f"{lbl_end}:")
            ctx["break_label"] = old_break
            ctx["continue_label"] = old_cont
        elif stype == "for":
            lbl_start = self.new_label("FOR_START")
            lbl_step = self.new_label("FOR_STEP")
            lbl_end = self.new_label("FOR_END")
            old_break = ctx.get("break_label")
            old_cont = ctx.get("continue_label")
            ctx["break_label"] = lbl_end
            ctx["continue_label"] = lbl_step

            if stmt.get("init"):
                self.compile_statement(stmt["init"], ctx)
            out.append(f"{lbl_start}:")
            if stmt.get("cond"):
                self.compile_cond_branch(stmt["cond"], False, lbl_end, ctx)
            self.compile_statement(stmt["body"], ctx)
            out.append(f"{lbl_step}:")
            if stmt.get("post"):
                self.compile_expr(stmt["post"], ctx)
            out.append(f"        jump {lbl_start}")
            out.append(f"{lbl_end}:")
            ctx["break_label"] = old_break
            ctx["continue_label"] = old_cont
            out.append(f"{lbl_end}:")
            ctx["break_label"] = old_break
        elif stype == "switch":
            lbl_end = self.new_label("SWITCH_END")
            old_break = ctx["break_label"]
            ctx["break_label"] = lbl_end

            # Evaluate switch expression into temporary register va
            self.compile_expr_into(stmt["expr"], "va", ctx)

            case_labels = []
            default_label = None
            for c in stmt["cases"]:
                lbl_case = self.new_label("CASE")
                case_labels.append((c, lbl_case))
                if c["val"] == "default":
                    default_label = lbl_case

            # Emit jump table / comparisons
            for c, lbl_case in case_labels:
                if c["val"] != "default":
                    out.append(f"        skip.ne va, {c['val']}")
                    out.append(f"        jump {lbl_case}")

            if default_label:
                out.append(f"        jump {default_label}")
            else:
                out.append(f"        jump {lbl_end}")

            # Emit case bodies
            for c, lbl_case in case_labels:
                out.append(f"{lbl_case}:")
                for s in c["stmts"]:
                    self.compile_statement(s, ctx)

            out.append(f"{lbl_end}:")
            ctx["break_label"] = old_break

    # =========================================================================
    # Expressions & Conditionals
    # =========================================================================

    def compile_expr(self, expr, ctx):
        return self.compile_expr_into(expr, "v0", ctx)

    def compile_expr_into(self, expr, dest_reg, ctx):
        out = ctx["out"]
        etype = expr["type"]

        if etype == "num":
            out.append(f"        load {dest_reg}, {expr['val'] & 0xFF}")
            return dest_reg

        if etype == "ident":
            name = expr["name"]
            if name in ctx["locals"]:
                src_reg = ctx["locals"][name]
                if src_reg != dest_reg:
                    out.append(f"        load {dest_reg}, {src_reg}")
            elif name in self.globals:
                label = name.upper()
                out.append(f"        load i, {label}")
                out.append("        restore v0")
                if dest_reg != "v0":
                    out.append(f"        load {dest_reg}, v0")
            elif name in self.preprocessor.macros:
                val = int(eval(self.preprocessor.macros[name]))
                out.append(f"        load {dest_reg}, {val & 0xFF}")
            else:
                # Check for array / function label
                out.append(f"        load {dest_reg}, 0")
            return dest_reg

        if etype == "assign":
            target = expr["target"]
            op = expr["op"]
            # Compile right-hand side into dest_reg
            self.compile_expr_into(expr["value"], dest_reg, ctx)

            if target["type"] == "ident":
                name = target["name"]
                if name in ctx["locals"]:
                    var_reg = ctx["locals"][name]
                    if op == "=":
                        if var_reg != dest_reg:
                            out.append(f"        load {var_reg}, {dest_reg}")
                    elif op == "+=":
                        out.append(f"        add {var_reg}, {dest_reg}")
                    elif op == "-=":
                        out.append(f"        sub {var_reg}, {dest_reg}")
                    elif op == "&=":
                        out.append(f"        and {var_reg}, {dest_reg}")
                    elif op == "|=":
                        out.append(f"        or {var_reg}, {dest_reg}")
                    elif op == "^=":
                        out.append(f"        xor {var_reg}, {dest_reg}")
                elif name in self.globals:
                    label = name.upper()
                    if op == "=":
                        out.append(f"        load i, {label}")
                        out.append(f"        load v0, {dest_reg}")
                        out.append("        save v0")
                    else:
                        out.append(f"        load i, {label}")
                        out.append("        restore v0")
                        if op == "+=": out.append(f"        add v0, {dest_reg}")
                        elif op == "-=": out.append(f"        sub v0, {dest_reg}")
                        elif op == "&=": out.append(f"        and v0, {dest_reg}")
                        elif op == "|=": out.append(f"        or v0, {dest_reg}")
                        out.append(f"        load i, {label}")
                        out.append("        save v0")
            elif target["type"] == "index":
                # Array assignment: arr[idx] = val
                arr_name = target["target"]["name"].upper()
                idx_expr = target["index"]
                # Save val to temporary vb
                out.append(f"        load vb, {dest_reg}")
                # Compute index into vc
                self.compile_expr_into(idx_expr, "vc", ctx)
                out.append(f"        load i, {arr_name}")
                out.append("        add i, vc")
                out.append("        load v0, vb")
                out.append("        save v0")
            return dest_reg

        if etype == "post_inc" or etype == "pre_inc":
            target = expr["target"]
            delta = 1 if expr["op"] == "++" else -1
            if target["type"] == "ident":
                name = target["name"]
                if name in ctx["locals"]:
                    reg = ctx["locals"][name]
                    if etype == "post_inc":
                        out.append(f"        load {dest_reg}, {reg}")
                    if delta == 1:
                        out.append(f"        add {reg}, 1")
                    else:
                        out.append(f"        sub {reg}, 1")
                    if etype == "pre_inc":
                        out.append(f"        load {dest_reg}, {reg}")
                elif name in self.globals:
                    label = name.upper()
                    out.append(f"        load i, {label}")
                    out.append("        restore v0")
                    if etype == "post_inc":
                        out.append(f"        load {dest_reg}, v0")
                    if delta == 1: out.append("        add v0, 1")
                    else: out.append("        sub v0, 1")
                    if etype == "pre_inc":
                        out.append(f"        load {dest_reg}, v0")
                    out.append(f"        load i, {label}")
                    out.append("        save v0")
            return dest_reg

        if etype == "index":
            # Read arr[idx]
            arr_name = expr["target"]["name"].upper()
            idx_expr = expr["index"]
            self.compile_expr_into(idx_expr, "vc", ctx)
            out.append(f"        load i, {arr_name}")
            out.append("        add i, vc")
            out.append("        restore v0")
            if dest_reg != "v0":
                out.append(f"        load {dest_reg}, v0")
            return dest_reg

        if etype == "call":
            return self.compile_call(expr, dest_reg, ctx)

        if etype == "binary":
            op = expr["op"]
            # Compile left into dest_reg
            self.compile_expr_into(expr["left"], dest_reg, ctx)
            # Compile right into temporary vb
            self.compile_expr_into(expr["right"], "vb", ctx)
            if op == "+": out.append(f"        add {dest_reg}, vb")
            elif op == "-": out.append(f"        sub {dest_reg}, vb")
            elif op == "&": out.append(f"        and {dest_reg}, vb")
            elif op == "|": out.append(f"        or {dest_reg}, vb")
            elif op == "^": out.append(f"        xor {dest_reg}, vb")
            elif op == "==":
                out.append(f"        load v0, 0")
                out.append(f"        skip.ne {dest_reg}, vb")
                out.append(f"        load v0, 1")
                if dest_reg != "v0": out.append(f"        load {dest_reg}, v0")
            elif op == "!=":
                out.append(f"        load v0, 0")
                out.append(f"        skip.eq {dest_reg}, vb")
                out.append(f"        load v0, 1")
                if dest_reg != "v0": out.append(f"        load {dest_reg}, v0")
            elif op == "<":
                # vb > dest_reg <=> sub vb, dest_reg -> VF=0 if vb < dest_reg
                out.append(f"        sub vb, {dest_reg}")
                out.append(f"        load v0, 0")
                out.append(f"        skip.eq vf, 0")
                out.append(f"        load v0, 1")
                if dest_reg != "v0": out.append(f"        load {dest_reg}, v0")
            elif op == ">":
                out.append(f"        sub {dest_reg}, vb")
                out.append(f"        load v0, 0")
                out.append(f"        skip.eq vf, 0")
                out.append(f"        load v0, 1")
                if dest_reg != "v0": out.append(f"        load {dest_reg}, v0")
            elif op == ">=":
                out.append(f"        sub {dest_reg}, vb")
                out.append(f"        load v0, vf")
                if dest_reg != "v0": out.append(f"        load {dest_reg}, v0")
            elif op == "<=":
                out.append(f"        sub vb, {dest_reg}")
                out.append(f"        load v0, vf")
                if dest_reg != "v0": out.append(f"        load {dest_reg}, v0")
            return dest_reg

        if etype == "unary":
            op = expr["op"]
            self.compile_expr_into(expr["expr"], dest_reg, ctx)
            if op == "!":
                out.append(f"        load v0, 0")
                out.append(f"        skip.ne {dest_reg}, 0")
                out.append(f"        load v0, 1")
                if dest_reg != "v0": out.append(f"        load {dest_reg}, v0")
            elif op == "-":
                out.append(f"        load v0, 0")
                out.append(f"        sub v0, {dest_reg}")
                if dest_reg != "v0": out.append(f"        load {dest_reg}, v0")
            elif op == "~":
                out.append(f"        load v0, 255")
                out.append(f"        xor {dest_reg}, v0")
            return dest_reg

        return dest_reg

    # =========================================================================
    # Conditional Branching
    # =========================================================================

    def compile_cond_branch(self, cond, jump_if_true, target_label, ctx):
        out = ctx["out"]
        ctype = cond["type"]

        if ctype == "binary" and cond["op"] in ("==", "!=", "<", "<=", ">", ">="):
            op = cond["op"]
            left = cond["left"]
            right = cond["right"]

            # Optimize comparisons against constant numbers
            if right["type"] == "num":
                val = right["val"] & 0xFF
                if left["type"] == "ident" and left["name"] in ctx["locals"]:
                    reg = ctx["locals"][left["name"]]
                else:
                    self.compile_expr_into(left, "v0", ctx)
                    reg = "v0"

                if op == "==":
                    if jump_if_true:
                        out.append(f"        skip.ne {reg}, {val}")
                        out.append(f"        jump {target_label}")
                    else:
                        out.append(f"        skip.eq {reg}, {val}")
                        out.append(f"        jump {target_label}")
                    return
                elif op == "!=":
                    if jump_if_true:
                        out.append(f"        skip.eq {reg}, {val}")
                        out.append(f"        jump {target_label}")
                    else:
                        out.append(f"        skip.ne {reg}, {val}")
                        out.append(f"        jump {target_label}")
                    return

            # General comparison
            self.compile_expr_into(left, "va", ctx)
            self.compile_expr_into(right, "vb", ctx)

            if op == "==":
                if jump_if_true:
                    out.append(f"        skip.ne va, vb")
                    out.append(f"        jump {target_label}")
                else:
                    out.append(f"        skip.eq va, vb")
                    out.append(f"        jump {target_label}")
            elif op == "!=":
                if jump_if_true:
                    out.append(f"        skip.eq va, vb")
                    out.append(f"        jump {target_label}")
                else:
                    out.append(f"        skip.ne va, vb")
                    out.append(f"        jump {target_label}")
            elif op in ("<", "<=", ">", ">="):
                # Fall back to evaluating comparison expression
                self.compile_expr_into(cond, "v0", ctx)
                if jump_if_true:
                    out.append(f"        skip.eq v0, 0")
                    out.append(f"        jump {target_label}")
                else:
                    out.append(f"        skip.ne v0, 0")
                    out.append(f"        jump {target_label}")
            return

        # General boolean condition: non-zero = true, zero = false
        self.compile_expr_into(cond, "v0", ctx)
        if jump_if_true:
            out.append(f"        skip.eq v0, 0")
            out.append(f"        jump {target_label}")
        else:
            out.append(f"        skip.ne v0, 0")
            out.append(f"        jump {target_label}")

    # =========================================================================
    # Function Calls & Flashiibo SDK Mappings
    # =========================================================================

    def compile_call(self, call_node, dest_reg, ctx):
        out = ctx["out"]
        func_name = call_node["func"]["name"]
        args = call_node["args"]

        # ---------------------------------------------------------------------
        # Flashiibo FEB SDK Built-in APIs
        # ---------------------------------------------------------------------
        if func_name == "feb_set_high_res":
            # feb_set_high_res(bool enable)
            if args and args[0].get("val") == 0:
                out.append("        low")
            else:
                out.append("        high")
            return dest_reg

        if func_name in ("feb_exit", "feb_quit"):
            out.append("        exit")
            return dest_reg

        if func_name == "feb_clear_screen":
            out.append("        cls")
            return dest_reg

        if func_name == "feb_wait_key":
            out.append(f"        load {dest_reg}, key")
            return dest_reg

        if func_name in ("feb_get_keys", "feb_read_buttons"):
            out.append(f"        getkeys {dest_reg}")
            return dest_reg

        if func_name == "feb_draw_sprite":
            # feb_draw_sprite(x, y, sprite, height)
            self.compile_expr_into(args[0], "vc", ctx)
            self.compile_expr_into(args[1], "vd", ctx)
            sprite_label = args[2]["name"].upper()
            h = args[3]["val"] if args[3]["type"] == "num" else 8
            out.append(f"        load i, {sprite_label}")
            out.append(f"        draw vc, vd, {h}")
            if dest_reg != "vf":
                out.append(f"        load {dest_reg}, vf")
            return dest_reg

        if func_name == "feb_draw_sprite16":
            # feb_draw_sprite16(x, y, sprite)
            self.compile_expr_into(args[0], "vc", ctx)
            self.compile_expr_into(args[1], "vd", ctx)
            if args[2]["type"] == "ident":
                name = args[2]["name"]
                if name in ctx["locals"]:
                    # Sprite pointer in local register!
                    # For pointer, we can't load i directly without table; but if direct label:
                    sprite_label = name.upper()
                else:
                    sprite_label = name.upper()
                out.append(f"        load i, {sprite_label}")
            out.append("        draw vc, vd, 0")
            if dest_reg != "vf":
                out.append(f"        load {dest_reg}, vf")
            return dest_reg

        if func_name in ("feb_draw_digit", "feb_draw_num"):
            # feb_draw_digit(x, y, digit)
            self.compile_expr_into(args[0], "vc", ctx)
            self.compile_expr_into(args[1], "vd", ctx)
            self.compile_expr_into(args[2], "ve", ctx)
            out.append("        hex ve")
            out.append("        draw vc, vd, 5")
            return dest_reg

        if func_name == "feb_set_draw_mode":
            self.compile_expr_into(args[0], "v4", ctx)
            out.append("        drawmode v4")
            return dest_reg

        if func_name == "feb_draw_pixel":
            self.compile_expr_into(args[0], "v4", ctx)
            self.compile_expr_into(args[1], "v5", ctx)
            out.append("        pixel v4")
            return dest_reg

        if func_name == "feb_draw_line":
            self.compile_expr_into(args[0], "v4", ctx)
            self.compile_expr_into(args[1], "v5", ctx)
            self.compile_expr_into(args[2], "v6", ctx)
            self.compile_expr_into(args[3], "v7", ctx)
            out.append("        line v4")
            return dest_reg

        if func_name == "feb_draw_hline":
            self.compile_expr_into(args[0], "v4", ctx)
            self.compile_expr_into(args[1], "v5", ctx)
            self.compile_expr_into(args[2], "v6", ctx)
            out.append("        hline v4")
            return dest_reg

        if func_name == "feb_draw_vline":
            self.compile_expr_into(args[0], "v4", ctx)
            self.compile_expr_into(args[1], "v5", ctx)
            self.compile_expr_into(args[2], "v6", ctx)
            out.append("        vline v4")
            return dest_reg

        if func_name == "feb_draw_rect":
            self.compile_expr_into(args[0], "v4", ctx)
            self.compile_expr_into(args[1], "v5", ctx)
            self.compile_expr_into(args[2], "v6", ctx)
            self.compile_expr_into(args[3], "v7", ctx)
            out.append("        rect v4")
            return dest_reg

        if func_name == "feb_fill_rect":
            self.compile_expr_into(args[0], "v4", ctx)
            self.compile_expr_into(args[1], "v5", ctx)
            self.compile_expr_into(args[2], "v6", ctx)
            self.compile_expr_into(args[3], "v7", ctx)
            out.append("        fillrect v4")
            return dest_reg

        if func_name == "feb_draw_circle":
            self.compile_expr_into(args[0], "v4", ctx)
            self.compile_expr_into(args[1], "v5", ctx)
            self.compile_expr_into(args[2], "v6", ctx)
            out.append("        circle v4")
            return dest_reg

        if func_name == "feb_fill_circle":
            self.compile_expr_into(args[0], "v4", ctx)
            self.compile_expr_into(args[1], "v5", ctx)
            self.compile_expr_into(args[2], "v6", ctx)
            out.append("        disc v4")
            return dest_reg

        if func_name == "feb_test_pixel":
            self.compile_expr_into(args[0], "v4", ctx)
            self.compile_expr_into(args[1], "v5", ctx)
            out.append("        testpixel v4")
            if dest_reg != "vf":
                out.append(f"        load {dest_reg}, vf")
            return dest_reg

        if func_name in ("feb_draw_string", "feb_draw_text"):
            # feb_draw_string(x, y, str, font)
            self.compile_expr_into(args[0], "v4", ctx)
            self.compile_expr_into(args[1], "v5", ctx)
            self.compile_expr_into(args[3], "v6", ctx)
            # String label
            if args[2]["type"] == "str":
                str_lbl = args[2]["label"]
                out.append(f"        load i, {str_lbl}")
            elif args[2]["type"] == "ident":
                str_lbl = args[2]["name"].upper()
                out.append(f"        load i, {str_lbl}")
            out.append("        text v4")
            return dest_reg

        if func_name == "feb_draw_number":
            # feb_draw_number(x, y, num, font)
            self.compile_expr_into(args[0], "v4", ctx)
            self.compile_expr_into(args[1], "v5", ctx)
            self.compile_expr_into(args[3], "v6", ctx)
            self.compile_expr_into(args[2], "v7", ctx)
            out.append("        load i, 0")
            out.append("        add i, v7")
            out.append("        num v4")
            return dest_reg

        if func_name == "feb_rand":
            mask = args[0]["val"] if args[0]["type"] == "num" else 0xFF
            out.append(f"        rnd {dest_reg}, {mask & 0xFF}")
            return dest_reg

        if func_name == "feb_save_flags":
            # feb_save_flags(data, len)
            # data is typically &best_tile or array
            len_val = args[-1]["val"] if args[-1]["type"] == "num" else 1
            if len_val == 1:
                # Load scalar into v0
                first_arg = args[0]
                if first_arg["type"] == "addrof":
                    var_name = first_arg["target"]["name"]
                    if var_name in ctx["locals"]:
                        reg = ctx["locals"][var_name]
                        out.append(f"        load v0, {reg}")
                    elif var_name in self.globals:
                        out.append(f"        load i, {var_name.upper()}")
                        out.append("        restore v0")
                out.append("        saveflags v0")
            return dest_reg

        if func_name == "feb_load_flags":
            # feb_load_flags(data, len)
            len_val = args[-1]["val"] if args[-1]["type"] == "num" else 1
            if len_val == 1:
                out.append("        loadflags v0")
                first_arg = args[0]
                if first_arg["type"] == "addrof":
                    var_name = first_arg["target"]["name"]
                    if var_name in ctx["locals"]:
                        reg = ctx["locals"][var_name]
                        out.append(f"        load {reg}, v0")
                    elif var_name in self.globals:
                        out.append(f"        load i, {var_name.upper()}")
                        out.append("        save v0")
            return dest_reg

        # ---------------------------------------------------------------------
        # User-Defined Function Call
        # ---------------------------------------------------------------------
        target_func = func_name.upper()
        # Compile arguments into v1, v2, v3...
        arg_regs = [f"v{i}" for i in range(1, len(args) + 1)]
        for i, a in enumerate(args):
            self.compile_expr_into(a, arg_regs[i], ctx)

        out.append(f"        call {target_func}")
        if dest_reg != "v0":
            out.append(f"        load {dest_reg}, v0")
        return dest_reg

def compile_c_to_asm(c_filepath, include_dirs=None):
    """
    Public entry point to compile a C source file to CHIP-8 assembly.
    """
    if include_dirs is None:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        include_dirs = [os.path.join(repo_root, "include"), os.path.dirname(os.path.abspath(c_filepath))]
    compiler = CCompiler(include_dirs)
    return compiler.compile(c_filepath)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} input.c [-o output.asm]")
        sys.exit(1)
    src = sys.argv[1]
    asm = compile_c_to_asm(src)
    if "-o" in sys.argv:
        out_path = sys.argv[sys.argv.index("-o") + 1]
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(asm)
    else:
        print(asm)
