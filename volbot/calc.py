import math
import random

import ply.lex
import ply.yacc


##############################################################
# Initialization
##############################################################

# Limits on arithmetic
MAX_MULT = 10**10000
MAX_EXP = 9999
MAX_FACT = 9999

# pre-defined functions
funcs = {
    'int': int,
    'float': float,
    'bool': bool,
    'pow': pow,
    'rand': random.randint,
    'log2': lambda x: math.log(x,2),
}


# pre-defined variables
variables  = {
    'pi': math.pi,
    'e': math.e,
    'True': True,
    'False': False,
}

# make certain math library functions available
math_funcs = [
    'acos', 'acosh', 'asin', 'asinh', 'atan', 'atan2', 'atanh','ceil',
    'copysign', 'cos', 'cosh', 'degrees', 'erf', 'erfc', 'exp', 'expm1',
    'fabs', 'factorial', 'floor', 'fmod', 'frexp', 'gamma', 'hypot', 'ldexp',
    'lgamma', 'log', 'log10', 'log1p', 'radians', 'sin', 'sinh', 'sqrt', 'tan',
    'tanh'
]
for f in math_funcs:
    funcs[f] = getattr(math, f)


##############################################################
# Lexical Analysis
##############################################################

# List of all tokens, required by PLY
tokens = (
    'AND', 'OR', 'NOT', 'RSHIFT', 'LSHIFT', 'EXP', 'OREQ', 'XOREQ', 'ANDEQ',
    'LSHIFTEQ', 'RSHIFTEQ', 'PLUSEQ', 'MINUSEQ', 'TIMESEQ', 'DIVEQ', 'MODEQ',
    'EXPEQ', 'LTEQ', 'GTEQ', 'NEQ', 'EQ', 'FLOAT', 'INT', 'ID'
)

# single-character tokens (most operators)
literals = ';=,<>|^&+-*/%~!()'

# multi-character operators
t_LTEQ = '<='
t_GTEQ = '>='
t_NEQ = '!='
t_EQ = '=='
t_RSHIFT = r'>>'
t_LSHIFT = r'<<'
t_EXP = r'\*\*'
t_OREQ = r'\|='
t_XOREQ = r'\^='
t_ANDEQ = r'&='
t_LSHIFTEQ = r'<<='
t_RSHIFTEQ = r'>>='
t_PLUSEQ = r'\+='
t_MINUSEQ = r'-='
t_TIMESEQ = r'\*='
t_DIVEQ = r'/='
t_MODEQ = r'%='
t_EXPEQ = r'\*\*='

reserved = {
    'or': 'OR',
    'and': 'AND',
    'not': 'NOT',
}

# regex for identifiers
def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    if t.value in reserved:
        t.type = reserved[t.value]
    return t
        

# float token; the regex ought to be pretty close to python's float format
def t_FLOAT(t):
    r'(([0-9]+\.[0-9]*|[0-9]*\.[0-9]+)(e[+-]?[0-9]+)?)|[0-9]+e[+-]?[0-9]+'
    t.value = float(t.value)
    return t

# int token; recognizes decimal, hex, octal, and binary
def t_INT(t):
    r'(0b[01]+)|(0o[0-7]+)|(0x[0-9a-fA-F]+)|([0-9]+)'
    if t.value.startswith('0b'):
        t.value = int(t.value[2:], 2)
    elif t.value.startswith('0o'):
        t.value = int(t.value[2:], 8)
    elif t.value.startswith('0x'):
        t.value = int(t.value[2:], 16)
    else:
        t.value = int(t.value)
    return t

# ignore all whitespace
t_ignore = ' \t\r\n'


##############################################################
# Grammar Rules
##############################################################

def p_commands(p):
    'commands : command'
    p[0] = p[1]
def p_commands_more(p):
    'commands : command ";" commands'
    # the result of a string of commands is the result of the last command
    # (that returned a non-null value)
    if p[3] is not None:
        p[0] = p[3]
    else:
        p[0] = p[1]

def p_command(p):
    'command : assign'
    # set the variable '_' to result of most recent command
    variables['_'] = p[1]
    p[0] = p[1]
def p_command_blank(p):
    'command : '
    # allow blank commands, why not?
    pass

# lots and lots of alternate assignment rules...
def p_assign(p):
    'assign : expr'
    p[0] = p[1]
def p_assign_eq(p):
    'assign : ID "=" assign'
    name = p[1]
    variables[name] = p[3]
    p[0] = variables[name]
def p_assign_oreq(p):
    'assign : ID OREQ assign'
    name = p[1]
    check_var(name)
    variables[name] |= p[3]
    p[0] = variables[name]
def p_assign_xoreq(p):
    'assign : ID XOREQ assign'
    name = p[1]
    check_var(name)
    variables[name] ^= p[3]
    p[0] = variables[name]
def p_assign_andeq(p):
    'assign : ID ANDEQ assign'
    name = p[1]
    check_var(name)
    variables[name] &= p[3]
    p[0] = variables[name]
def p_assign_lshifteq(p):
    'assign : ID LSHIFTEQ assign'
    name = p[1]
    check_var(name)
    check_lshift(variables[name], p[3])
    variables[name] <<= p[3]
    p[0] = variables[name]
def p_assign_rshifteq(p):
    'assign : ID RSHIFTEQ assign'
    name = p[1]
    check_var(name)
    variables[name] >>= p[3]
    p[0] = variables[name]
def p_assign_pluseq(p):
    'assign : ID PLUSEQ assign'
    name = p[1]
    check_var(name)
    variables[name] += p[3]
    p[0] = variables[name]
def p_assign_minuseq(p):
    'assign : ID MINUSEQ assign'
    name = p[1]
    check_var(name)
    variables[name] -= p[3]
    p[0] = variables[name]
def p_assign_timeseq(p):
    'assign : ID TIMESEQ assign'
    name = p[1]
    check_var(name)
    check_mult(variables[name])
    check_mult(p[3])
    variables[name] *= p[3]
    p[0] = variables[name]
def p_assign_diveq(p):
    'assign : ID DIVEQ assign'
    name = p[1]
    check_var(name)
    variables[name] /= p[3]
    p[0] = variables[name]
def p_assign_modeq(p):
    'assign : ID MODEQ assign'
    name = p[1]
    check_var(name)
    variables[name] %= p[3]
    p[0] = variables[name]
def p_assign_expeq(p):
    'assign : ID EXPEQ assign'
    name = p[1]
    check_var(name)
    check_exp(variables[name], p[3])
    variables[name] **= p[3]
    p[0] = variables[name]

def p_expr(p):
    'expr : bort'
    p[0] = p[1]
def p_expr_bor(p):
    'expr : expr OR bort'
    p[0] = p[1] or p[3]

def p_bort(p):
    'bort : bandt'
    p[0] = p[1]
def p_bort_band(p):
    'bort : bort AND bandt'
    p[0] = p[1] and p[3]

def p_bandt(p):
    'bandt : bnott'
    p[0] = p[1]
def p_bandt_bnot(p):
    'bandt : NOT bandt'
    p[0] = not p[2]

def p_bnott(p):
    'bnott : compt'
    p[0] = p[1]
def p_bnott_lt(p):
    'bnott : bnott "<" compt'
    p[0] = p[1] < p[3]
def p_bnott_lteq(p):
    'bnott : bnott LTEQ compt'
    p[0] = p[1] <= p[3]
def p_bnott_gt(p):
    'bnott : bnott ">" compt'
    p[0] = p[1] > p[3]
def p_bnott_gteq(p):
    'bnott : bnott GTEQ compt'
    p[0] = p[1] >= p[3]
def p_bnott_eq(p):
    'bnott : bnott EQ compt'
    p[0] = p[1] == p[3]
def p_bnott_neq(p):
    'bnott : bnott NEQ compt'
    p[0] = p[1] != p[3]

def p_compt(p):
    'compt : ort'
    p[0] = p[1]
def p_compt_or(p):
    'compt : compt "|" ort'
    p[0] = p[1] | p[3]

def p_ort(p):
    'ort : xort'
    p[0] = p[1]
def p_ort_xor(p):
    'ort : ort "^" xort'
    p[0] = p[1] ^ p[3]

def p_xort(p):
    'xort : andt'
    p[0] = p[1]
def p_xort_and(p):
    'xort : xort "&" andt'
    p[0] = p[1] & p[3]

def p_andt(p):
    'andt : shiftt'
    p[0] = p[1]
def p_andt_lshift(p):
    'andt : andt LSHIFT shiftt'
    check_lshift(p[1], p[3])
    p[0] = p[1] << p[3]
def p_andt_rshift(p):
    'andt : andt RSHIFT shiftt'
    p[0] = p[1] >> p[3]

def p_shiftt(p):
    'shiftt : addt'
    p[0] = p[1]
def p_shiftt_add(p):
    'shiftt : shiftt "+" addt'
    p[0] = p[1] + p[3]
def p_shiftt_sub(p):
    'shiftt : shiftt "-" addt'
    p[0] = p[1] - p[3]

def p_addt(p):
    'addt : multt'
    p[0] = p[1]
def p_addt_mult(p):
    'addt : addt "*" multt'
    check_mult(p[1])
    check_mult(p[3])
    p[0] = p[1] * p[3]
def p_addt_div(p):
    'addt : addt "/" multt'
    p[0] = p[1] / p[3]
def p_addt_mod(p):
    'addt : addt "%" multt'
    p[0] = p[1] % p[3]

def p_multt(p):
    'multt : factt'
    p[0] = p[1]
def p_multt_pos(p):
    'multt : "+" multt'
    p[0] = p[2]
def p_multt_neg(p):
    'multt : "-" multt'
    p[0] = -p[2]
def p_multt_not(p):
    'multt : "~" multt'
    p[0] = ~p[2]
def p_multt_exp(p):
    'multt : val EXP multt'
    check_exp(p[1], p[3])
    p[0] = p[1] ** p[3]

def p_factt(p):
    'factt : val'
    p[0] = p[1]
def p_factt_fact(p):
    'factt : factt "!"'
    check_fact(p[1])
    p[0] = math.factorial(p[1])

def p_val_int(p):
    'val : INT'
    p[0] = p[1]
def p_val_float(p):
    'val : FLOAT'
    p[0] = p[1]
def p_val_id(p):
    'val : ID'
    check_var(p[1])
    p[0] = variables[p[1]]
def p_val_func(p):
    'val : ID "(" args ")"'
    check_func(p[1])
    p[0] = funcs[p[1]](*p[3])
def p_val_func_empty(p):
    'val : ID "(" ")"'
    check_func(p[1])
    p[0] = funcs[p[1]]()
def p_val_expr(p):
    'val : "(" expr ")"'
    p[0] = p[2]

def p_args_args(p):
    'args : args "," expr'
    p[0] = p[1] + (p[3],)
def p_args_expr(p):
    'args : expr'
    p[0] = (p[1],)


##############################################################
# Error Handling
##############################################################

def t_error(t):
    abort("Illegal character '%s'" % t.value[0])

def p_error(t):
    if t is not None:
        abort("Syntax error at '%s'" % t.value) 
    else:
        abort("Syntax error.")

class CalculationException(Exception):
    """An exception that occurs while evaluating an expression."""
    pass

def abort(msg):
    """Raise a CalculationException with given message"""
    raise CalculationException(msg)

def check_var(name):
    """Check if a variable exists; if not, abort"""
    if name not in variables:
        abort("Unknown variable: %s" % name)

def check_func(name):
    """Check if a function exists; if not, abort"""
    if name not in funcs:
        abort("Unknown function: %s" % name)

def check_lshift(a, b):
    """Check if left shift operands are too big; if so, abort"""
    # a << b is equivalent to a * (2**b), so treat a as mulitplicand and b as exponent
    if a > MAX_MULT:
        abort("Number too large to shift: %s" % a)
    if b > MAX_EXP:
        abort("Shift amount too large: %s" % b)

def check_mult(*nums):
    """Check if multiplication operands are too big; if so, abort"""
    for a in nums:
        if abs(a) > MAX_MULT:
            abort("Number too large to multiply: %s" % a)

def check_exp(a, b):
    """Check if exponentiation operands are too big; if so, abort"""
    if abs(a) > MAX_MULT:
        abort("Number too large for exponent base: %s" % a)
    if b > MAX_EXP:
        abort("Number too large for exponent: %s" % b)
    
def check_fact(a):
    """Check if factorial operand is too big; if so, abort"""
    if a > MAX_FACT:
        abort("Factorial too large: %d" % a)


##############################################################
# Module Code
##############################################################

lexer = ply.lex.lex()
parser = ply.yacc.yacc()

def eval(expr):
    """Evaluate a string of expressions and return the result."""
    try:
        return parser.parse(expr)
    except Exception as e:
        raise CalculationException(str(e))
        
if __name__ == '__main__':
    while True:
        try:
            print(eval(raw_input('> ')))
        except CalculationException as e:
            print("Error: %s" % e)
        except KeyboardInterrupt:
            break

