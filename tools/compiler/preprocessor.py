"""
preprocessor.py - Preprocessor for Flashiibo C-to-CHIP-8 compiler.
"""

import os
import re

class Preprocessor:
    """Handles #include, conditional compilation (#ifdef, #ifndef, #else, #endif), and #define macro substitutions."""
    def __init__(self, include_dirs=None):
        self.include_dirs = include_dirs or []
        self.macros = {}

    def process(self, filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return self._process_text(content, os.path.dirname(os.path.abspath(filepath)))

    def _process_text(self, text, current_dir):
        lines = text.splitlines()
        output = []
        cond_stack = []

        def is_active():
            return all(cond_stack)

        for line in lines:
            stripped = line.strip()

            # Conditional compilation directives
            if stripped.startswith("#ifdef"):
                m = stripped.split(None, 1)
                macro = m[1].split()[0] if len(m) > 1 else ""
                cond_stack.append(macro in self.macros)
                continue
            elif stripped.startswith("#ifndef"):
                m = stripped.split(None, 1)
                macro = m[1].split()[0] if len(m) > 1 else ""
                cond_stack.append(macro not in self.macros)
                continue
            elif stripped.startswith("#if"):
                parts = stripped.split(None, 1)
                expr = parts[1] if len(parts) > 1 else "0"
                expr = re.sub(r'/\*.*?\*/', '', expr).split('//')[0].strip()
                if expr in ("0", "false"):
                    active = False
                elif expr in ("1", "true"):
                    active = True
                else:
                    active = expr in self.macros
                cond_stack.append(active)
                continue
            elif stripped.startswith("#else"):
                if cond_stack:
                    cond_stack[-1] = not cond_stack[-1]
                continue
            elif stripped.startswith("#endif"):
                if cond_stack:
                    cond_stack.pop()
                continue
            elif stripped.startswith("#pragma"):
                continue

            if not is_active():
                continue

            if stripped.startswith("#include"):
                # Handle #include
                m = re.match(r'#include\s*[<"]([^>"]+)[>"]', stripped)
                if m:
                    inc_name = m.group(1)
                    # Don't try to read stdlib C headers
                    if inc_name in ("stdint.h", "stdbool.h", "stddef.h", "stdlib.h", "string.h"):
                        continue
                    # Search for header file
                    found = False
                    search_paths = [current_dir] + self.include_dirs
                    for d in search_paths:
                        full_path = os.path.normpath(os.path.join(d, inc_name))
                        if os.path.exists(full_path):
                            sub_text = self.process(full_path)
                            output.append(sub_text)
                            found = True
                            break
                    if not found and "feb.h" in inc_name:
                        # Fallback built-in feb constants
                        pass
                continue
            elif stripped.startswith("#define"):
                parts = stripped.split(None, 2)
                if len(parts) >= 2:
                    name = parts[1]
                    # Check for macro with parameters
                    paren = name.find("(")
                    if paren != -1:
                        pass
                    else:
                        val_str = parts[2] if len(parts) > 2 else "1"
                        # Strip comments from define value
                        val_str = re.sub(r'/\*.*?\*/', '', val_str).split('//')[0].strip()
                        for k, v in self.macros.items():
                            val_str = re.sub(r'\b' + re.escape(k) + r'\b', str(v), val_str)
                        self.macros[name] = val_str
                continue

            output.append(line)

        expanded_text = "\n".join(output)

        # Multi-pass macro substitution to resolve nested defines (e.g. MAX_X (WIDTH - SIZE))
        for _ in range(3):
            for k in sorted(self.macros.keys(), key=len, reverse=True):
                v = self.macros[k]
                expanded_text = re.sub(r'\b' + re.escape(k) + r'\b', v, expanded_text)

        return expanded_text

