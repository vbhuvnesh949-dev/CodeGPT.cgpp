# ============================================
#   CodeGPT++ Parser v1.0
#   Builds AST from Token list
# ============================================

from lexer import *
from nodes import *
from errors import ParseError

class Parser:
    def __init__(self, tokens):
        self.tokens  = tokens
        self.pos     = 0

    # ---------- helpers ----------
    def current(self):
        return self.tokens[self.pos]

    def peek(self, offset=1):
        idx = self.pos + offset
        return self.tokens[idx] if idx < len(self.tokens) else self.tokens[-1]

    def advance(self):
        tok = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return tok

    def expect(self, type_, value=None):
        tok = self.current()
        if tok.type != type_:
            raise ParseError(f"Expected {type_!r}, got {tok.type!r} ({tok.value!r})", tok.line)
        if value is not None and tok.value != value:
            raise ParseError(f"Expected {value!r}, got {tok.value!r}", tok.line)
        return self.advance()

    def skip_newlines(self):
        while self.current().type == TT_NEWLINE:
            self.advance()

    def match(self, type_, value=None):
        tok = self.current()
        if tok.type != type_:
            return False
        if value is not None and tok.value != value:
            return False
        self.advance()
        return True

    # ---------- entry ----------
    def parse(self):
        self.skip_newlines()
        stmts = self.parse_statements()
        return ProgramNode(stmts)

    def parse_statements(self, stop_on_rbrace=False):
        stmts = []
        while True:
            self.skip_newlines()
            tok = self.current()
            if tok.type == TT_EOF:
                break
            if stop_on_rbrace and tok.type == TT_RBRACE:
                break
            stmt = self.parse_statement()
            if stmt is not None:
                stmts.append(stmt)
        return stmts

    def parse_block(self):
        self.expect(TT_LBRACE)
        self.skip_newlines()
        stmts = self.parse_statements(stop_on_rbrace=True)
        self.skip_newlines()
        self.expect(TT_RBRACE)
        return stmts

    # ---------- statements ----------
    def parse_statement(self):
        tok = self.current()

        # let / const
        if tok.type == TT_KEYWORD and tok.value in ('let', 'const'):
            return self.parse_var_decl()

        # if
        if tok.type == TT_KEYWORD and tok.value == 'if':
            return self.parse_if()

        # while
        if tok.type == TT_KEYWORD and tok.value == 'while':
            return self.parse_while()

        # for
        if tok.type == TT_KEYWORD and tok.value == 'for':
            return self.parse_for()

        # fun
        if tok.type == TT_KEYWORD and tok.value == 'fun':
            return self.parse_func_def()

        # return
        if tok.type == TT_KEYWORD and tok.value == 'return':
            self.advance()
            val = None
            if self.current().type not in (TT_NEWLINE, TT_RBRACE, TT_EOF):
                val = self.parse_expr()
            return ReturnNode(val)

        # break / continue
        if tok.type == TT_KEYWORD and tok.value == 'break':
            self.advance(); return BreakNode()
        if tok.type == TT_KEYWORD and tok.value == 'continue':
            self.advance(); return ContinueNode()

        # print
        if tok.type == TT_KEYWORD and tok.value == 'print':
            return self.parse_print()

        # class
        if tok.type == TT_KEYWORD and tok.value == 'class':
            return self.parse_class()

        # import
        if tok.type == TT_KEYWORD and tok.value == 'import':
            self.advance()
            path = self.expect(TT_STRING).value
            return ImportNode(path)

        # expression statement (assignment or call)
        return self.parse_expr_stmt()

    # ---------- var decl ----------
    def parse_var_decl(self):
        is_const = self.advance().value == 'const'
        name = self.expect(TT_IDENTIFIER).value
        self.expect(TT_EQ)
        value = self.parse_expr()
        return VarAssignNode(name, value, declare=True, const=is_const)

    # ---------- if ----------
    def parse_if(self):
        self.advance()  # skip 'if'
        cond = self.parse_expr()
        body = self.parse_block()
        cases = [(cond, body)]

        while self.current().type == TT_KEYWORD and self.current().value == 'elif':
            self.advance()
            c = self.parse_expr()
            b = self.parse_block()
            cases.append((c, b))

        else_body = None
        if self.current().type == TT_KEYWORD and self.current().value == 'else':
            self.advance()
            else_body = self.parse_block()

        return IfNode(cases, else_body)

    # ---------- while ----------
    def parse_while(self):
        self.advance()
        cond = self.parse_expr()
        body = self.parse_block()
        return WhileNode(cond, body)

    # ---------- for ----------
    def parse_for(self):
        self.advance()
        var = self.expect(TT_IDENTIFIER).value
        self.expect(TT_KEYWORD, 'in')
        iterable = self.parse_expr()
        body = self.parse_block()
        return ForNode(var, iterable, body)

    # ---------- function ----------
    def parse_func_def(self):
        self.advance()  # skip 'fun'
        name = self.expect(TT_IDENTIFIER).value
        self.expect(TT_LPAREN)
        params = []
        def read_param():
            tok = self.current()
            if tok.type == TT_IDENTIFIER:
                return self.advance().value
            if tok.type == TT_KEYWORD and tok.value == 'self':
                return self.advance().value
            from errors import ParseError
            raise ParseError(f"Expected param name, got {tok.value!r}", tok.line)
        if self.current().type != TT_RPAREN:
            params.append(read_param())
            while self.match(TT_COMMA):
                params.append(read_param())
        self.expect(TT_RPAREN)
        body = self.parse_block()
        return FuncDefNode(name, params, body)

    # ---------- class ----------
    def parse_class(self):
        self.advance()
        name = self.expect(TT_IDENTIFIER).value
        self.expect(TT_LBRACE)
        self.skip_newlines()
        methods = []
        while self.current().type != TT_RBRACE and self.current().type != TT_EOF:
            self.skip_newlines()
            if self.current().type == TT_KEYWORD and self.current().value == 'fun':
                methods.append(self.parse_func_def())
            else:
                self.advance()
            self.skip_newlines()
        self.expect(TT_RBRACE)
        return ClassDefNode(name, methods)

    # ---------- print ----------
    def parse_print(self):
        self.advance()
        self.expect(TT_LPAREN)
        args = []
        if self.current().type != TT_RPAREN:
            args.append(self.parse_expr())
            while self.match(TT_COMMA):
                args.append(self.parse_expr())
        self.expect(TT_RPAREN)
        return PrintNode(args)

    # ---------- expr statement (assignment / call) ----------
    def parse_expr_stmt(self):
        expr = self.parse_expr()

        # assignment:  name = ...  or  name[i] = ...
        if self.current().type == TT_EQ:
            self.advance()
            val = self.parse_expr()
            if isinstance(expr, VarAccessNode):
                return VarAssignNode(expr.name, val, declare=False)
            if isinstance(expr, IndexNode):
                return IndexAssignNode(expr.obj, expr.index, val)
            if isinstance(expr, AttributeNode):
                from nodes import AttributeAssignNode
                return AttributeAssignNode(expr.obj, expr.attr, val)
            raise ParseError("Invalid assignment target", 0)

        return expr

    # =========================================================
    #   Expression parsing  (precedence climbing)
    # =========================================================

    def parse_expr(self):
        return self.parse_or()

    def parse_or(self):
        left = self.parse_and()
        while self.current().type == TT_KEYWORD and self.current().value == 'or':
            op = self.advance().value
            right = self.parse_and()
            left = BinOpNode(left, op, right)
        return left

    def parse_and(self):
        left = self.parse_not()
        while self.current().type == TT_KEYWORD and self.current().value == 'and':
            op = self.advance().value
            right = self.parse_not()
            left = BinOpNode(left, op, right)
        return left

    def parse_not(self):
        if self.current().type == TT_KEYWORD and self.current().value == 'not':
            op = self.advance().value
            return UnaryOpNode(op, self.parse_not())
        return self.parse_comparison()

    def parse_comparison(self):
        left = self.parse_add()
        cmp_types = {TT_EQEQ, TT_NEQ, TT_LT, TT_GT, TT_LTE, TT_GTE}
        while self.current().type in cmp_types:
            op = self.advance().value
            right = self.parse_add()
            left = BinOpNode(left, op, right)
        return left

    def parse_add(self):
        left = self.parse_mul()
        while self.current().type in (TT_PLUS, TT_MINUS):
            op = self.advance().value
            right = self.parse_mul()
            left = BinOpNode(left, op, right)
        return left

    def parse_mul(self):
        left = self.parse_power()
        while self.current().type in (TT_MUL, TT_DIV, TT_MOD):
            op = self.advance().value
            right = self.parse_power()
            left = BinOpNode(left, op, right)
        return left

    def parse_power(self):
        left = self.parse_unary()
        if self.current().type == TT_POWER:
            op = self.advance().value
            right = self.parse_power()  # right-associative
            return BinOpNode(left, op, right)
        return left

    def parse_unary(self):
        if self.current().type == TT_MINUS:
            op = self.advance().value
            return UnaryOpNode(op, self.parse_unary())
        return self.parse_call()

    def parse_call(self):
        expr = self.parse_primary()

        while True:
            if self.current().type == TT_LPAREN:
                self.advance()
                args = []
                if self.current().type != TT_RPAREN:
                    args.append(self.parse_expr())
                    while self.match(TT_COMMA):
                        args.append(self.parse_expr())
                self.expect(TT_RPAREN)
                expr = CallNode(expr, args)

            elif self.current().type == TT_LBRACKET:
                self.advance()
                index = self.parse_expr()
                self.expect(TT_RBRACKET)
                expr = IndexNode(expr, index)

            elif self.current().type == TT_DOT:
                self.advance()
                attr = self.expect(TT_IDENTIFIER).value
                expr = AttributeNode(expr, attr)

            else:
                break

        return expr

    def parse_primary(self):
        tok = self.current()

        if tok.type == TT_INT:
            self.advance(); return NumberNode(tok.value)
        if tok.type == TT_FLOAT:
            self.advance(); return NumberNode(tok.value)
        if tok.type == TT_STRING:
            self.advance(); return StringNode(tok.value)
        if tok.type == TT_BOOL:
            self.advance(); return BoolNode(tok.value)
        if tok.type == TT_KEYWORD and tok.value == 'null':
            self.advance(); return NullNode()

        # list literal  [a, b, c]
        if tok.type == TT_LBRACKET:
            self.advance()
            elems = []
            if self.current().type != TT_RBRACKET:
                elems.append(self.parse_expr())
                while self.match(TT_COMMA):
                    elems.append(self.parse_expr())
            self.expect(TT_RBRACKET)
            return ListNode(elems)

        # input(...)
        if tok.type == TT_KEYWORD and tok.value == 'input':
            self.advance()
            self.expect(TT_LPAREN)
            prompt = None
            if self.current().type != TT_RPAREN:
                prompt = self.parse_expr()
            self.expect(TT_RPAREN)
            return InputNode(prompt)

        # builtin calls that look like keywords: range(...), len(...), etc.
        if tok.type == TT_KEYWORD and tok.value in ('range', 'len', 'abs', 'sqrt', 'pow',
                                                     'max', 'min', 'round', 'type',
                                                     'append', 'pop', 'push'):
            self.advance()
            return VarAccessNode(tok.value, tok.line)

        # type casts  int(...) float(...) str(...) bool(...)
        if tok.type == TT_KEYWORD and tok.value in ('int', 'float', 'str', 'bool'):
            type_ = self.advance().value
            self.expect(TT_LPAREN)
            expr = self.parse_expr()
            self.expect(TT_RPAREN)
            return CastNode(type_, expr)

        # 'new' keyword for class instantiation: new ClassName(...)
        if tok.type == TT_KEYWORD and tok.value == 'new':
            self.advance()
            name = self.expect(TT_IDENTIFIER).value
            return VarAccessNode(name, tok.line)

        # 'self' keyword used inside methods
        if tok.type == TT_KEYWORD and tok.value == 'self':
            self.advance()
            return VarAccessNode('self', tok.line)

        # identifier
        if tok.type == TT_IDENTIFIER:
            self.advance()
            return VarAccessNode(tok.value, tok.line)

        # grouped expression
        if tok.type == TT_LPAREN:
            self.advance()
            expr = self.parse_expr()
            self.expect(TT_RPAREN)
            return expr

        raise ParseError(f"Unexpected token {tok.type!r} ({tok.value!r})", tok.line)
