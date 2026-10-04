"""
lexer.py - Lexical analyzer and token definitions for Flashiibo C-to-CHIP-8 compiler.
"""

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
