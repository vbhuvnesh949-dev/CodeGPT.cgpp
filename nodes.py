# ============================================
#   CodeGPT++ AST Nodes
#   All node types used by Parser & Interpreter
# ============================================

# ---------- Literals ----------
class NumberNode:
    def __init__(self, value): self.value = value

class StringNode:
    def __init__(self, value): self.value = value

class BoolNode:
    def __init__(self, value): self.value = value

class NullNode:
    pass

# ---------- Collections ----------
class ListNode:
    def __init__(self, elements): self.elements = elements   # [expr, ...]

# ---------- Variable ----------
class VarAccessNode:
    def __init__(self, name, line=0):
        self.name = name
        self.line = line

class VarAssignNode:
    def __init__(self, name, value, declare=False, const=False):
        self.name    = name
        self.value   = value
        self.declare = declare   # True if 'let'
        self.const   = const     # True if 'const'

class IndexAssignNode:
    """list[i] = value"""
    def __init__(self, obj, index, value):
        self.obj   = obj
        self.index = index
        self.value = value

# ---------- Operations ----------
class BinOpNode:
    def __init__(self, left, op, right):
        self.left  = left
        self.op    = op
        self.right = right

class UnaryOpNode:
    def __init__(self, op, operand):
        self.op      = op
        self.operand = operand

# ---------- Index / Attribute ----------
class IndexNode:
    def __init__(self, obj, index):
        self.obj   = obj
        self.index = index

class AttributeNode:
    def __init__(self, obj, attr):
        self.obj  = obj
        self.attr = attr

# ---------- Control Flow ----------
class IfNode:
    def __init__(self, cases, else_body):
        self.cases     = cases       # [(condition, body), ...]
        self.else_body = else_body   # [stmt, ...] or None

class WhileNode:
    def __init__(self, condition, body):
        self.condition = condition
        self.body      = body

class ForNode:
    def __init__(self, var, iterable, body):
        self.var      = var
        self.iterable = iterable
        self.body     = body

class BreakNode:    pass
class ContinueNode: pass

class ReturnNode:
    def __init__(self, value): self.value = value

# ---------- Functions ----------
class FuncDefNode:
    def __init__(self, name, params, body):
        self.name   = name
        self.params = params   # [str, ...]
        self.body   = body     # [stmt, ...]

class CallNode:
    def __init__(self, callee, args):
        self.callee = callee   # expr
        self.args   = args     # [expr, ...]

# ---------- Built-ins ----------
class PrintNode:
    def __init__(self, args): self.args = args

class InputNode:
    def __init__(self, prompt): self.prompt = prompt

# ---------- Type casts ----------
class CastNode:
    def __init__(self, type_, expr):
        self.type_ = type_
        self.expr  = expr

# ---------- Class ----------
class ClassDefNode:
    def __init__(self, name, methods):
        self.name    = name
        self.methods = methods   # [FuncDefNode, ...]

# ---------- Import ----------
class ImportNode:
    def __init__(self, path): self.path = path

# ---------- Program ----------
class ProgramNode:
    def __init__(self, statements): self.statements = statements

class AttributeAssignNode:
    def __init__(self, obj, attr, value):
        self.obj   = obj
        self.attr  = attr
        self.value = value
