"""
parser.py - Syntax analyzer and AST generator for Flashiibo C-to-CHIP-8 compiler.
"""

from .lexer import (
    Token, TOK_EOF, TOK_IDENT, TOK_NUM, TOK_STR, TOK_CHAR,
    TOK_KEYWORD, TOK_OP, TOK_PUNCT
)


class CParser:
    """Parses token stream into an Abstract Syntax Tree (AST)."""
    def __init__(self, tokens, macros=None):
        self.tokens = tokens
        self.tok_idx = 0
        self.macros = macros or {}
        self.globals = {}
        self.strings = {}
        self.functions = {}
        self.struct_types = {}

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
        is_typedef = self.match("typedef")
        struct_tag = None
        if self.match("struct"):
            if self.peek().type == TOK_IDENT:
                struct_tag = self.consume().val

        if self.peek().val == "{":
            self.consume("{")
            fields = {}
            cur_offset = 0
            while self.peek().val != "}" and self.peek().type != TOK_EOF:
                f_type = self.skip_type_specifiers()
                f_name = self.consume(expected_type=TOK_IDENT).val
                f_size = 1
                if self.match("["):
                    f_size = self.parse_constant_expr()
                    self.consume("]")
                self.consume(";")
                fields[f_name] = {"offset": cur_offset, "size": f_size, "type": f_type}
                cur_offset += f_size
            self.consume("}")

            type_name = struct_tag
            if is_typedef:
                type_name = self.consume(expected_type=TOK_IDENT).val
            self.consume(";")

            struct_info = {"size": cur_offset, "fields": fields}
            if type_name:
                self.struct_types[type_name] = struct_info
            if struct_tag:
                self.struct_types[f"struct {struct_tag}"] = struct_info
                self.struct_types[struct_tag] = struct_info
        else:
            # Fallback: skip until ';' respecting nested braces
            depth = 0
            while self.peek().type != TOK_EOF:
                val = self.peek().val
                if val == "{":
                    depth += 1
                    self.consume("{")
                elif val == "}":
                    depth -= 1
                    self.consume("}")
                elif val == ";" and depth == 0:
                    self.consume(";")
                    break
                else:
                    self.consume()

    def skip_type_specifiers(self):
        while self.peek().val in ("static", "const", "volatile", "unsigned", "signed", "extern"):
            self.consume()
        if self.peek().val == "struct":
            self.consume("struct")
            type_name = "struct " + self.consume().val
        else:
            type_name = self.consume().val
        while self.peek().val == "*":
            self.consume("*")
        return type_name

    def parse_global_or_function(self):
        # Parse return type or variable type
        type_name = self.skip_type_specifiers()
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
        elif type_name in self.struct_types:
            st_info = self.struct_types[type_name]
            self.consume(";")
            self.globals[name] = {"type": "struct", "struct_name": type_name, "size": st_info["size"]}
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
        elif tok.val in self.macros:
            val = int(eval(self.macros[tok.val]))
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
        node = self.parse_assignment()
        return self.fold_constants(node)

    def fold_constants(self, node):
        if not isinstance(node, dict):
            return node
        ntype = node.get("type")
        if ntype == "binary":
            left = self.fold_constants(node["left"])
            right = self.fold_constants(node["right"])
            node["left"] = left
            node["right"] = right
            if left.get("type") == "num" and right.get("type") == "num":
                lval = left["val"]
                rval = right["val"]
                op = node["op"]
                res = None
                if op == "+": res = (lval + rval) & 0xFF
                elif op == "-": res = (lval - rval) & 0xFF
                elif op == "*": res = (lval * rval) & 0xFF
                elif op == "/" and rval != 0: res = (lval // rval) & 0xFF
                elif op == "%" and rval != 0: res = (lval % rval) & 0xFF
                elif op == "<<": res = (lval << rval) & 0xFF
                elif op == ">>": res = (lval >> rval) & 0xFF
                elif op == "&": res = (lval & rval) & 0xFF
                elif op == "|": res = (lval | rval) & 0xFF
                elif op == "^": res = (lval ^ rval) & 0xFF
                elif op == "==": res = 1 if lval == rval else 0
                elif op == "!=": res = 1 if lval != rval else 0
                elif op == "<": res = 1 if lval < rval else 0
                elif op == "<=": res = 1 if lval <= rval else 0
                elif op == ">": res = 1 if lval > rval else 0
                elif op == ">=": res = 1 if lval >= rval else 0
                if res is not None:
                    return {"type": "num", "val": res}
        elif ntype == "unary":
            sub = self.fold_constants(node["expr"])
            node["expr"] = sub
            if sub.get("type") == "num":
                sval = sub["val"]
                op = node["op"]
                if op == "-": return {"type": "num", "val": (-sval) & 0xFF}
                elif op == "!": return {"type": "num", "val": 0 if sval else 1}
                elif op == "~": return {"type": "num", "val": (~sval) & 0xFF}
        return node

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
            if tok.val in self.macros:
                try:
                    val = int(eval(self.macros[tok.val]))
                    return {"type": "num", "val": val}
                except Exception:
                    pass
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

