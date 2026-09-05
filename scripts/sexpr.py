"""Small lossless-atom KiCad S-expression reader/writer (no external dependencies)."""
import re, json
class Atom(str): pass
def parse(text):
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text)
    stack=[]
    for t in tokens:
        if t=='(':
            a=[]
            if stack: stack[-1].append(a)
            stack.append(a)
        elif t==')':
            a=stack.pop()
            if not stack: return a
        else: stack[-1].append(json.loads(t) if t.startswith('"') else Atom(t))
def dump(x, level=0):
    if not isinstance(x,list): return str(x) if isinstance(x,Atom) else json.dumps(x,ensure_ascii=False)
    if not any(isinstance(y,list) for y in x): return '('+' '.join(dump(y) for y in x)+')'
    s='('
    for i,y in enumerate(x):
        s+= ('\n'+'\t'*(level+1) if isinstance(y,list) else (' ' if i else ''))+dump(y,level+1)
    return s+'\n'+'\t'*level+')'
def get(x,key,default=None): return next((y for y in x if isinstance(y,list) and y[0]==key),default)
def many(x,key): return [y for y in x if isinstance(y,list) and y[0]==key]
def prop(x,name): return next(y for y in many(x,'property') if y[1]==name)
