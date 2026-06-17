# ============================================
#   CodeGPT++ Interpreter v1.0
#   Tree-walk interpreter
# ============================================

import math, os
from nodes import *
from errors import RuntimeError as CGRuntimeError

# -------- signals (non-exception flow control) --------
class ReturnSignal(Exception):
    def __init__(self, value): self.value = value

class BreakSignal(Exception):  pass
class ContinueSignal(Exception): pass

# -------- Environment (scope) --------
class Environment:
    def __init__(self, parent=None):
        self.vars   = {}
        self.consts = set()
        self.parent = parent

    def get(self, name, line=0):
        if name in self.vars:
            return self.vars[name]
        if self.parent:
            return self.parent.get(name, line)
        raise CGRuntimeError(f"Undefined variable '{name}'", line)

    def set(self, name, value, declare=False, const=False):
        if declare:
            self.vars[name] = value
            if const:
                self.consts.add(name)
            return
        # reassign: find the scope that owns it
        scope = self._find(name)
        if scope is None:
            self.vars[name] = value   # auto-declare at global
            return
        if name in scope.consts:
            raise CGRuntimeError(f"Cannot reassign const '{name}'", 0)
        scope.vars[name] = value

    def _find(self, name):
        if name in self.vars: return self
        if self.parent: return self.parent._find(name)
        return None

# -------- Function / Class objects --------
class Function:
    def __init__(self, name, params, body, closure):
        self.name    = name
        self.params  = params
        self.body    = body
        self.closure = closure
    def __repr__(self): return f"<fun {self.name}>"

class CGClass:
    def __init__(self, name, methods, closure):
        self.name    = name
        self.methods = methods   # {str: FuncDefNode}
        self.closure = closure
    def __repr__(self): return f"<class {self.name}>"

class CGInstance:
    def __init__(self, klass):
        self.klass = klass
        self.attrs = {}
    def __repr__(self): return f"<{self.klass.name} instance>"

# -------- Built-in functions --------
BUILTINS = {
    'len'   : lambda args: len(args[0]),
    'range' : lambda args: list(range(*[int(a) for a in args])),
    'abs'   : lambda args: abs(args[0]),
    'sqrt'  : lambda args: math.sqrt(args[0]),
    'pow'   : lambda args: math.pow(args[0], args[1]),
    'max'   : lambda args: max(args),
    'min'   : lambda args: min(args),
    'round' : lambda args: round(args[0], int(args[1]) if len(args) > 1 else 0),
    'type'  : lambda args: type(args[0]).__name__,
    'append': lambda args: args[0].append(args[1]) or args[0],
    'pop'   : lambda args: args[0].pop() if len(args)==1 else args[0].pop(int(args[1])),
    'push'  : lambda args: args[0].insert(0, args[1]) or args[0],
}

# -------- Interpreter --------
class Interpreter:
    def __init__(self):
        self.global_env = Environment()
        # seed builtins
        for name, fn in BUILTINS.items():
            self.global_env.vars[name] = fn

    def run(self, program):
        return self.exec_stmts(program.statements, self.global_env)

    # ---- execute a list of statements ----
    def exec_stmts(self, stmts, env):
        result = None
        for stmt in stmts:
            result = self.exec(stmt, env)
        return result

    def exec(self, node, env):
        method = f'exec_{type(node).__name__}'
        fn = getattr(self, method, None)
        if fn is None:
            raise CGRuntimeError(f"Unknown node: {type(node).__name__}", 0)
        return fn(node, env)

    # ---- literals ----
    def exec_NumberNode(self, node, env):  return node.value
    def exec_StringNode(self, node, env):  return node.value
    def exec_BoolNode(self, node, env):    return node.value
    def exec_NullNode(self, node, env):    return None
    def exec_ListNode(self, node, env):
        return [self.exec(e, env) for e in node.elements]

    # ---- variable ----
    def exec_VarAccessNode(self, node, env):
        val = env.get(node.name, node.line)
        if callable(val) and not isinstance(val, Function):
            return val   # builtin
        return val

    def exec_VarAssignNode(self, node, env):
        val = self.exec(node.value, env)
        env.set(node.name, val, declare=node.declare, const=node.const)
        return val

    def exec_IndexAssignNode(self, node, env):
        obj   = self.exec(node.obj, env)
        idx   = self.exec(node.index, env)
        val   = self.exec(node.value, env)
        obj[int(idx)] = val
        return val

    # ---- binary operation ----
    def exec_BinOpNode(self, node, env):
        left  = self.exec(node.left,  env)
        right = self.exec(node.right, env)
        op    = node.op
        try:
            if op == '+':  return left + right
            if op == '-':  return left - right
            if op == '*':  return left * right
            if op == '/':
                if right == 0: raise CGRuntimeError("Division by zero", 0)
                return left / right
            if op == '%':  return left % right
            if op == '**': return left ** right
            if op == '==': return left == right
            if op == '!=': return left != right
            if op == '<':  return left < right
            if op == '>':  return left > right
            if op == '<=': return left <= right
            if op == '>=': return left >= right
            if op == 'and': return left and right
            if op == 'or':  return left or right
        except TypeError as e:
            raise CGRuntimeError(str(e), 0)

    def exec_UnaryOpNode(self, node, env):
        val = self.exec(node.operand, env)
        if node.op == '-':   return -val
        if node.op == 'not': return not val
        return val

    # ---- index / attribute ----
    def exec_IndexNode(self, node, env):
        obj = self.exec(node.obj, env)
        idx = self.exec(node.index, env)
        if isinstance(obj, str):
            return obj[int(idx)]
        return obj[int(idx)]

    def exec_AttributeNode(self, node, env):
        obj  = self.exec(node.obj, env)
        attr = node.attr

        # string methods
        if isinstance(obj, str):
            method_map = {
                'upper'  : lambda args: obj.upper(),
                'lower'  : lambda args: obj.lower(),
                'len'    : lambda args: len(obj),
                'split'  : lambda args: obj.split(args[0] if args else None),
                'replace': lambda args: obj.replace(args[0], args[1]),
                'strip'  : lambda args: obj.strip(),
                'startswith': lambda args: obj.startswith(args[0]),
                'endswith'  : lambda args: obj.endswith(args[0]),
            }
            if attr == 'len': return len(obj)
            if attr in method_map:
                return method_map[attr]
            raise CGRuntimeError(f"String has no attribute '{attr}'", 0)

        # list methods
        if isinstance(obj, list):
            list_map = {
                'len'    : lambda args: len(obj),
                'append' : lambda args: obj.append(args[0]) or obj,
                'pop'    : lambda args: obj.pop() if not args else obj.pop(int(args[0])),
                'reverse': lambda args: obj.reverse() or obj,
                'sort'   : lambda args: obj.sort() or obj,
            }
            if attr == 'len': return len(obj)
            if attr in list_map:
                return list_map[attr]
            raise CGRuntimeError(f"List has no attribute '{attr}'", 0)

        # class instance
        if isinstance(obj, CGInstance):
            if attr in obj.attrs:
                return obj.attrs[attr]
            if attr in obj.klass.methods:
                fn_node = obj.klass.methods[attr]
                return Function(attr, fn_node.params, fn_node.body, obj.klass.closure), obj
            raise CGRuntimeError(f"Instance has no attribute '{attr}'", 0)

        raise CGRuntimeError(f"Cannot access attribute on {type(obj).__name__}", 0)

    # ---- control flow ----
    def exec_IfNode(self, node, env):
        for cond, body in node.cases:
            if self.exec(cond, env):
                local = Environment(parent=env)
                return self.exec_stmts(body, local)
        if node.else_body is not None:
            local = Environment(parent=env)
            return self.exec_stmts(node.else_body, local)
        return None

    def exec_WhileNode(self, node, env):
        result = None
        while self.exec(node.condition, env):
            local = Environment(parent=env)
            try:
                result = self.exec_stmts(node.body, local)
            except BreakSignal:
                break
            except ContinueSignal:
                continue
        return result

    def exec_ForNode(self, node, env):
        iterable = self.exec(node.iterable, env)
        if callable(iterable):          # builtin like range
            iterable = iterable([])
        result = None
        for item in iterable:
            local = Environment(parent=env)
            local.set(node.var, item, declare=True)
            try:
                result = self.exec_stmts(node.body, local)
            except BreakSignal:
                break
            except ContinueSignal:
                continue
        return result

    def exec_BreakNode(self, node, env):    raise BreakSignal()
    def exec_ContinueNode(self, node, env): raise ContinueSignal()

    def exec_ReturnNode(self, node, env):
        val = self.exec(node.value, env) if node.value is not None else None
        raise ReturnSignal(val)

    # ---- functions ----
    def exec_FuncDefNode(self, node, env):
        fn = Function(node.name, node.params, node.body, env)
        env.set(node.name, fn, declare=True)
        return fn

    def exec_CallNode(self, node, env):
        callee = self.exec(node.callee, env)
        args   = [self.exec(a, env) for a in node.args]

        # tuple means (method, instance)
        if isinstance(callee, tuple):
            fn, instance = callee
            local = Environment(parent=fn.closure)
            local.set('self', instance, declare=True)
            for p, a in zip(fn.params[1:], args):  # skip 'self'
                local.set(p, a, declare=True)
            try:
                self.exec_stmts(fn.body, local)
            except ReturnSignal as rs:
                return rs.value
            return None

        # user-defined function
        if isinstance(callee, Function):
            local = Environment(parent=callee.closure)
            for p, a in zip(callee.params, args):
                local.set(p, a, declare=True)
            try:
                self.exec_stmts(callee.body, local)
            except ReturnSignal as rs:
                return rs.value
            return None

        # class instantiation
        if isinstance(callee, CGClass):
            instance = CGInstance(callee)
            if 'init' in callee.methods:
                fn_node = callee.methods['init']
                fn      = Function('init', fn_node.params, fn_node.body, callee.closure)
                local   = Environment(parent=fn.closure)
                local.set('self', instance, declare=True)
                for p, a in zip(fn.params[1:], args):
                    local.set(p, a, declare=True)
                try:
                    self.exec_stmts(fn.body, local)
                except ReturnSignal:
                    pass
            return instance

        # callable builtin (lambda)
        if callable(callee):
            return callee(args)

        raise CGRuntimeError(f"'{callee}' is not callable", 0)

    # ---- class ----
    def exec_ClassDefNode(self, node, env):
        methods = {m.name: m for m in node.methods}
        klass   = CGClass(node.name, methods, env)
        env.set(node.name, klass, declare=True)
        return klass

    # ---- builtins ----
    def exec_PrintNode(self, node, env):
        vals = [self.exec(a, env) for a in node.args]
        out  = []
        for v in vals:
            if v is True:  out.append('true')
            elif v is False: out.append('false')
            elif v is None: out.append('null')
            elif isinstance(v, float) and v == int(v):
                out.append(str(int(v)))
            else:
                out.append(str(v))
        print(' '.join(out))
        return None

    def exec_InputNode(self, node, env):
        prompt = self.exec(node.prompt, env) if node.prompt else ''
        return input(str(prompt))

    def exec_CastNode(self, node, env):
        val = self.exec(node.expr, env)
        try:
            if node.type_ == 'int':   return int(val)
            if node.type_ == 'float': return float(val)
            if node.type_ == 'str':   return str(val)
            if node.type_ == 'bool':  return bool(val)
        except (ValueError, TypeError) as e:
            raise CGRuntimeError(f"Cannot cast to {node.type_}: {e}", 0)


    def exec_AttributeAssignNode(self, node, env):
        obj  = self.exec(node.obj, env)
        val  = self.exec(node.value, env)
        if isinstance(obj, CGInstance):
            obj.attrs[node.attr] = val
            return val
        raise CGRuntimeError(f"Cannot set attribute on {type(obj).__name__}", 0)

    # ---- import ----
    def exec_ImportNode(self, node, env):
        path = node.path
        if not os.path.isabs(path):
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
        with open(path, 'r') as f:
            src = f.read()
        from lexer   import Lexer
        from parser  import Parser
        from nodes   import ProgramNode
        tokens  = Lexer(src).tokenise()
        program = Parser(tokens).parse()
        self.exec_stmts(program.statements, env)
