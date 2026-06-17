# ============================================
#   CodeGPT++ Error Classes
# ============================================

class CGError(Exception):
    def __init__(self, message, line=0):
        self.message = message
        self.line    = line
    def __str__(self):
        if self.line:
            return f"[Line {self.line}] {self.__class__.__name__}: {self.message}"
        return f"{self.__class__.__name__}: {self.message}"

class LexerError(CGError):   pass
class ParseError(CGError):   pass
class RuntimeError(CGError): pass
