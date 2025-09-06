"""
Maybe use in an MCP route?
"""

import inspect
import types
from bog_builder import builder

mod = builder
try:
    mod_file = inspect.getsourcefile(mod) or inspect.getfile(mod)
except TypeError:
    mod_file = None  # builtins/frozen


def is_defined_here(obj):
    try:
        f = inspect.getsourcefile(obj) or inspect.getfile(obj)
        return mod_file is not None and f == mod_file
    except TypeError:
        return False


print(f"MODULE: {mod.__name__}")
print(f"FILE:   {mod_file}")

# ---------- Classes ----------
print("\nCLASSES (defined in this file):")
classes = [
    (n, c) for n, c in inspect.getmembers(mod, inspect.isclass) if is_defined_here(c)
]
if not classes:
    print("  (none)")
for name, cls in classes:
    try:
        line = inspect.getsourcelines(cls)[1]
    except OSError:
        line = "?"
    bases = [b.__name__ for b in cls.__bases__ if b is not object]
    base_str = f" : {', '.join(bases)}" if bases else ""
    print(f"\n  class {name}{base_str}  (line {line})")

    # Collect methods from the class dict to correctly detect static/class/props
    inst_methods = []
    class_methods = []
    static_methods = []
    properties = []
    others = []

    for attr_name, attr_val in cls.__dict__.items():
        # Skip dunders to reduce noise (comment this out if you want everything)
        if attr_name.startswith("__") and attr_name.endswith("__"):
            continue

        if isinstance(attr_val, (types.FunctionType, types.BuiltinFunctionType)):
            # Regular function in class body => instance method
            inst_methods.append(attr_name)
        elif isinstance(attr_val, classmethod):
            class_methods.append(attr_name)
        elif isinstance(attr_val, staticmethod):
            static_methods.append(attr_name)
        elif isinstance(attr_val, property):
            properties.append(attr_name)
        else:
            others.append(attr_name)

    if inst_methods:
        print("    instance methods:")
        for m in inst_methods:
            print(f"      - {m}")
    if class_methods:
        print("    class methods:")
        for m in class_methods:
            print(f"      - {m}")
    if static_methods:
        print("    static methods:")
        for m in static_methods:
            print(f"      - {m}")
    if properties:
        print("    properties:")
        for m in properties:
            print(f"      - {m}")
    if others:
        print("    other class attrs:")
        for m in others:
            print(f"      - {m}")

# ---------- Functions ----------
print("\nFUNCTIONS (top-level, defined in this file):")
funcs = [
    (n, f) for n, f in inspect.getmembers(mod, inspect.isfunction) if is_defined_here(f)
]
if not funcs:
    print("  (none)")
for name, fn in funcs:
    try:
        line = inspect.getsourcelines(fn)[1]
    except OSError:
        line = "?"
    print(f"  def {name}(... )  (line {line})")

# ---------- (Optional) Dump names that look like constants ----------
print("\nCONSTANT-LIKE GLOBALS (UPPERCASE, defined in this file):")
globals_here = []
for n, v in vars(mod).items():
    if not n.isupper():
        continue
    # Try to ensure it's from this file (skip imports)
    if is_defined_here(v) or not callable(v):
        globals_here.append(n)
if globals_here:
    for n in globals_here:
        print(f"  {n}")
else:
    print("  (none)")
