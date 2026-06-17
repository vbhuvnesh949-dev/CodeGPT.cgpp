# ============================================
#   CodeGPT++ Lexer v1.0
#   Tokenizes .cgpp source code
# ============================================

import re

# ---------- Token Types ----------
TT_INT        = 'INT'
TT_FLOAT      = 'FLOAT'
TT_STRING     = 'STRING'
TT_BOOL       = 'BOOL'
TT_IDENTIFIER = 'IDENTIFIER'
TT_KEYWORD    = 'KEYWORD'

TT_PLUS       = 'PLUS'
TT_MINUS      = 'MINUS'
TT_MUL        = 'MUL'
TT_DIV        = 'DIV'
TT_MOD        = 'MOD'
TT_POWER      = 'POWER'

TT_EQ         = 'EQ'         # =
TT_EQEQ       = 'EQEQ'      # ==
TT_NEQ        = 'NEQ'        # !=
TT_LT         = 'LT'         # <
TT_GT         = 'GT'         # >
TT_LTE        = 'LTE'        # <=
TT_GTE        = 'GTE'        # >=

TT_LPAREN     = 'LPAREN'     # (
TT_RPAREN     = 'RPAREN'     # )
TT_LBRACE     = 'LBRACE'     # {
TT_RBRACE     = 'RBRACE'     # }
TT_LBRACKET   = 'LBRACKET'   # [
TT_RBRACKET   = 'RBRACKET'   # ]
TT_COMMA      = 'COMMA'      # ,
TT_COLON      = 'COLON'      # :
TT_DOT        = 'DOT'        # .
TT_SEMICOLON  = 'SEMICOLON'  # ;
TT_NEWLINE    = 'NEWLINE'
TT_EOF        = 'EOF'

# ---------- Keywords ----------
KEYWORDS = [
    'let', 'const',
    'if', 'elif', 'else',
    'while', 'for', 'in', 'range',
    'fun', 'return',
    'print', 'input',
    'true', 'false', 'null',
    'and', 'or', 'not',
    'break', 'continue',
    'import',
    'class', 'new', 'self',
    'int', 'float', 'str', 'bool',
]

# ---------- Token ----------
class Token:
    def __init__(self, type_, value=None, line=0):
        self.type  = type_
        self.value = value
        self.line  = line

    def __repr__(self):
        if self.value is not None:
            return f'Token({self.type}, {self.value!r})'
        return f'Token({self.type})'

# ---------- Lexer ----------
class Lexer:
    def __init__(self, source):
        self.source = source
        self.pos    = 0
        self.line   = 1
        self.tokens = []

    def error(self, ch):
        from errors import LexerError
        raise LexerError(f"Unknown character '{ch}'", self.line)

    def peek(self, offset=1):
        idx = self.pos + offset
        return self.source[idx] if idx < len(self.source) else '\0'

    def advance(self):
        ch = self.source[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
        return ch

    def current(self):
        return self.source[self.pos] if self.pos < len(self.source) else '\0'

    # ---- skip whitespace & comments ----
    def skip_whitespace(self):
        while self.pos < len(self.source) and self.current() in ' \t\r':
            self.advance()

    def skip_comment(self):
        # single-line  //
        if self.current() == '/' and self.peek() == '/':
            while self.pos < len(self.source) and self.current() != '\n':
                self.advance()
        # multi-line  /* ... */
        elif self.current() == '/' and self.peek() == '*':
            self.advance(); self.advance()
            while self.pos < len(self.source):
                if self.current() == '*' and self.peek() == '/':
                    self.advance(); self.advance()
                    break
                self.advance()

    # ---- read number ----
    def read_number(self):
        num = ''
        is_float = False
        while self.pos < len(self.source) and (self.current().isdigit() or self.current() == '.'):
            if self.current() == '.':
                if is_float: break
                is_float = True
            num += self.advance()
        if is_float:
            return Token(TT_FLOAT, float(num), self.line)
        return Token(TT_INT, int(num), self.line)

    # ---- read string ----
    def read_string(self, quote):
        self.advance()   # skip opening quote
        s = ''
        while self.pos < len(self.source) and self.current() != quote:
            if self.current() == '\\':
                self.advance()
                esc = {'n':'\n','t':'\t','\\':'\\','"':'"',"'":"'"}.get(self.current(), self.current())
                s += esc
                self.advance()
            else:
                s += self.advance()
        self.advance()   # skip closing quote
        return Token(TT_STRING, s, self.line)

    # ---- read identifier / keyword ----
    def read_ident(self):
        word = ''
        while self.pos < len(self.source) and (self.current().isalnum() or self.current() == '_'):
            word += self.advance()
        if word in ('true', 'false'):
            return Token(TT_BOOL, word == 'true', self.line)
        if word in KEYWORDS:
            return Token(TT_KEYWORD, word, self.line)
        return Token(TT_IDENTIFIER, word, self.line)

    # ---- main tokenise ----
    def tokenise(self):
        while self.pos < len(self.source):
            self.skip_whitespace()
            if self.pos >= len(self.source):
                break

            ch = self.current()

            # newline
            if ch == '\n':
                self.tokens.append(Token(TT_NEWLINE, '\n', self.line))
                self.advance()
                continue

            # comment
            if ch == '/' and self.peek() in ('/', '*'):
                self.skip_comment()
                continue

            # number
            if ch.isdigit():
                self.tokens.append(self.read_number())
                continue

            # string
            if ch in ('"', "'"):
                self.tokens.append(self.read_string(ch))
                continue

            # identifier / keyword
            if ch.isalpha() or ch == '_':
                self.tokens.append(self.read_ident())
                continue

            # operators & punctuation
            self.advance()
            if   ch == '+': self.tokens.append(Token(TT_PLUS,  '+', self.line))
            elif ch == '-': self.tokens.append(Token(TT_MINUS, '-', self.line))
            elif ch == '*':
                if self.current() == '*':
                    self.advance()
                    self.tokens.append(Token(TT_POWER, '**', self.line))
                else:
                    self.tokens.append(Token(TT_MUL, '*', self.line))
            elif ch == '/': self.tokens.append(Token(TT_DIV,  '/', self.line))
            elif ch == '%': self.tokens.append(Token(TT_MOD,  '%', self.line))
            elif ch == '=':
                if self.current() == '=':
                    self.advance()
                    self.tokens.append(Token(TT_EQEQ, '==', self.line))
                else:
                    self.tokens.append(Token(TT_EQ, '=', self.line))
            elif ch == '!':
                if self.current() == '=':
                    self.advance()
                    self.tokens.append(Token(TT_NEQ, '!=', self.line))
            elif ch == '<':
                if self.current() == '=':
                    self.advance()
                    self.tokens.append(Token(TT_LTE, '<=', self.line))
                else:
                    self.tokens.append(Token(TT_LT, '<', self.line))
            elif ch == '>':
                if self.current() == '=':
                    self.advance()
                    self.tokens.append(Token(TT_GTE, '>=', self.line))
                else:
                    self.tokens.append(Token(TT_GT, '>', self.line))
            elif ch == '(': self.tokens.append(Token(TT_LPAREN,   '(', self.line))
            elif ch == ')': self.tokens.append(Token(TT_RPAREN,   ')', self.line))
            elif ch == '{': self.tokens.append(Token(TT_LBRACE,   '{', self.line))
            elif ch == '}': self.tokens.append(Token(TT_RBRACE,   '}', self.line))
            elif ch == '[': self.tokens.append(Token(TT_LBRACKET, '[', self.line))
            elif ch == ']': self.tokens.append(Token(TT_RBRACKET, ']', self.line))
            elif ch == ',': self.tokens.append(Token(TT_COMMA,    ',', self.line))
            elif ch == ':': self.tokens.append(Token(TT_COLON,    ':', self.line))
            elif ch == '.': self.tokens.append(Token(TT_DOT,      '.', self.line))
            elif ch == ';': self.tokens.append(Token(TT_SEMICOLON,';', self.line))
            else:
                self.error(ch)

        self.tokens.append(Token(TT_EOF, None, self.line))
        return self.tokens
