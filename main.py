#!/usr/bin/env python3
# ============================================
#   CodeGPT++ v1.0  —  main entry point
#   Usage:
#       python main.py hello.cgpp       # run a file
#       python main.py                  # REPL mode
# ============================================

import sys, os

# make sure our own modules are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lexer        import Lexer
from parser       import Parser
from interpreter  import Interpreter
from errors       import CGError

BANNER = r"""
  ____          _       ____ ____ _____    _     _     
 / ___|___   __| | ___ / ___|  _ \_   _|_| |_  | |    
| |   / _ \ / _` |/ _ \ |  _| |_) || |/ _` __| | |    
| |__| (_) | (_| |  __/ |_| |  __/ | | (_| |_| |_|___ 
 \____\___/ \__,_|\___|\____|_|    |_|\__,_\__(_)_____|
                                                        
   v1.0  —  A mix of Python & C++
   Type  exit  or  quit  to leave the REPL
"""

def run_source(source, filename='<stdin>'):
    try:
        tokens      = Lexer(source).tokenise()
        program     = Parser(tokens).parse()
        interpreter = Interpreter()
        interpreter.run(program)
    except CGError as e:
        print(f"\n❌  {e}")
    except Exception as e:
        print(f"\n💥  Internal error: {e}")

def run_file(path):
    if not os.path.exists(path):
        print(f"❌  File not found: {path}")
        sys.exit(1)
    with open(path, 'r') as f:
        source = f.read()
    run_source(source, path)

def repl():
    print(BANNER)
    interpreter = Interpreter()

    while True:
        try:
            line = input("cgpp> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye! 👋")
            break

        if not line:
            continue
        if line in ('exit', 'quit'):
            print("Bye! 👋")
            break

        # multi-line input: keep reading if line ends with {
        source = line
        while source.count('{') > source.count('}'):
            try:
                more = input("  ... ")
                source += '\n' + more
            except (EOFError, KeyboardInterrupt):
                break

        try:
            from lexer       import Lexer
            from parser      import Parser
            tokens  = Lexer(source).tokenise()
            program = Parser(tokens).parse()
            result  = interpreter.run(program)
            if result is not None:
                print(result)
        except CGError as e:
            print(f"❌  {e}")
        except Exception as e:
            print(f"💥  {e}")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        run_file(sys.argv[1])
    else:
        repl()
