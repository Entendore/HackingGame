import pygame
import sys
import textwrap
import random
import time
import math
import array
import re as real_re

# --------------- Setup ---------------
pygame.init()
WIDTH, HEIGHT = 1280, 800
FONT_NAME = "consolas"
BG = (8, 10, 12)
FG = (170, 255, 170)
DIM = (90, 140, 90)
CYAN = (120, 230, 230)
YELLOW = (240, 220, 120)
RED = (240, 110, 110)
WHITE = (230, 230, 230)
ORANGE = (240, 160, 80)
PURPLE = (180, 120, 240)
BLUE = (100, 160, 240)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("TERMINAL BREACH v5.0  //  CODE BREAKER")
clock = pygame.time.Clock()

font = pygame.font.SysFont(FONT_NAME, 16)
font_bold = pygame.font.SysFont(FONT_NAME, 16, bold=True)
font_small = pygame.font.SysFont(FONT_NAME, 13)
font_big = pygame.font.SysFont(FONT_NAME, 26, bold=True)
font_tiny = pygame.font.SysFont(FONT_NAME, 11)

# --------------- Sound ---------------
class SoundFX:
    def __init__(self):
        pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
        self.sounds = {}
        self._build()
        self.muted = False

    def _tone(self, freq, duration_ms, volume=0.15):
        samples = int(22050 * duration_ms / 1000)
        buf = array.array('h')
        for i in range(samples):
            t = i / 22050.0
            val = math.sin(2 * math.pi * freq * t) * max(0, 1 - i / samples)
            buf.append(int(val * 32767 * volume))
        return pygame.mixer.Sound(buffer=buf)

    def _build(self):
        self.sounds['key'] = self._tone(800, 20, 0.05)
        self.sounds['enter'] = self._tone(400, 60, 0.1)
        self.sounds['success'] = self._tone(880, 80, 0.15)
        self.sounds['alert'] = self._tone(220, 200, 0.2)
        self.sounds['fail'] = self._tone(150, 300, 0.2)
        self.sounds['scan'] = self._tone(1200, 40, 0.1)
        self.sounds['craft'] = self._tone(660, 120, 0.12)
        self.sounds['event'] = self._tone(440, 150, 0.18)
        self.sounds['code'] = self._tone(550, 50, 0.08)

    def play(self, name):
        if not self.muted and name in self.sounds:
            self.sounds[name].play()

sfx = SoundFX()

# --------------- Randomized secrets ---------------
DOG_NAMES = ["REX", "MAX", "LUNA", "KAI", "ZARA", "ODIN"]
FOUND_YEARS = ["2019", "2017", "2021", "2015"]
chosen_dog = random.choice(DOG_NAMES)
chosen_year = random.choice(FOUND_YEARS)
CEO_PASSWORD = (chosen_dog[::-1] + chosen_year).lower()
EXPLOIT_CODE = f"HELIX-EXPLOIT-{chosen_year}"
TARGET_HEX = random.choice(["0xDEADBEEF", "0xCAFEBABE", "0xBAADF00D", "0xFEEDFACE"])

# --------------- Mini Python Interpreter ---------------
class MiniPython:
    """A tiny Python-like interpreter for scripting challenges."""
    def __init__(self):
        self.env = {}
        self.output = []
        self.functions = {}

    def reset(self):
        self.env = {}
        self.output = []
        self.functions = {}

    def run(self, code):
        self.reset()
        lines = [l.strip() for l in code.split("\n") if l.strip() and not l.strip().startswith("#")]
        try:
            i = 0
            while i < len(lines):
                i = self._exec_line(lines, i)
            return True, "\n".join(self.output)
        except Exception as e:
            return False, f"Error: {e}"

    def _exec_line(self, lines, i):
        line = lines[i]
        
        # Function definition
        if line.startswith("def "):
            name = line[4:line.index("(")].strip()
            body = []
            i += 1
            while i < len(lines) and lines[i].startswith("    "):
                body.append(lines[i][4:])
                i += 1
            self.functions[name] = body
            return i
        
        # Function call
        if "(" in line and "=" not in line.split("(")[0]:
            fname = line[:line.index("(")]
            if fname in self.functions:
                for fline in self.functions[fname]:
                    self._exec_statement(fline)
            return i + 1
        
        # For loop
        if line.startswith("for "):
            # for x in range(n):
            parts = line.split()
            var = parts[1]
            range_call = parts[3].rstrip("):")
            if range_call.startswith("range("):
                n = int(range_call[6:-1])
            else:
                n = int(range_call)
            body = []
            i += 1
            while i < len(lines) and lines[i].startswith("    "):
                body.append(lines[i][4:])
                i += 1
            for _ in range(n):
                for bline in body:
                    self._exec_statement(bline)
            return i
        
        # While loop
        if line.startswith("while "):
            cond = line[6:].rstrip(":")
            body = []
            i += 1
            while i < len(lines) and lines[i].startswith("    "):
                body.append(lines[i][4:])
                i += 1
            iters = 0
            while self._eval(cond) and iters < 100:
                for bline in body:
                    self._exec_statement(bline)
                iters += 1
            return i
        
        # If statement
        if line.startswith("if "):
            cond = line[3:].rstrip(":")
            body = []
            i += 1
            while i < len(lines) and lines[i].startswith("    "):
                body.append(lines[i][4:])
                i += 1
            if self._eval(cond):
                for bline in body:
                    self._exec_statement(bline)
            return i
        
        self._exec_statement(line)
        return i + 1

    def _exec_statement(self, line):
        line = line.strip()
        if not line:
            return
        if line.startswith("print("):
            arg = line[6:-1]
            val = self._eval(arg)
            self.output.append(str(val))
        elif "=" in line and not line.startswith("=="):
            var, expr = line.split("=", 1)
            var = var.strip()
            if "+=" in var:
                v, inc = var.split("+=")
                self.env[v.strip()] = self._eval(v.strip()) + self._eval(inc.strip())
            elif "-=" in var:
                v, dec = var.split("-=")
                self.env[v.strip()] = self._eval(v.strip()) - self._eval(dec.strip())
            else:
                self.env[var] = self._eval(expr.strip())
        else:
            self._eval(line)

    def _eval(self, expr):
        expr = expr.strip()
        # String literal
        if (expr.startswith('"') and expr.endswith('"')) or (expr.startswith("'") and expr.endswith("'")):
            return expr[1:-1]
        # Number
        try:
            if "." in expr:
                return float(expr)
            return int(expr)
        except ValueError:
            pass
        # len()
        if expr.startswith("len(") and expr.endswith(")"):
            inner = expr[4:-1]
            val = self._eval(inner)
            return len(val) if isinstance(val, (str, list)) else 0
        # str()
        if expr.startswith("str(") and expr.endswith(")"):
            return str(self._eval(expr[4:-1]))
        # int()
        if expr.startswith("int(") and expr.endswith(")"):
            return int(self._eval(expr[4:-1]))
        # chr()
        if expr.startswith("chr(") and expr.endswith(")"):
            return chr(int(self._eval(expr[4:-1])))
        # ord()
        if expr.startswith("ord(") and expr.endswith(")"):
            inner = self._eval(expr[4:-1])
            return ord(inner[0]) if isinstance(inner, str) and inner else 0
        # range()
        if expr.startswith("range(") and expr.endswith(")"):
            n = int(expr[6:-1])
            return list(range(n))
        # String concat / arithmetic
        if "+" in expr:
            parts = expr.split("+", 1)
            a, b = self._eval(parts[0]), self._eval(parts[1])
            if isinstance(a, str) or isinstance(b, str):
                return str(a) + str(b)
            return a + b
        if "-" in expr and not expr.startswith("-"):
            parts = expr.split("-", 1)
            return self._eval(parts[0]) - self._eval(parts[1])
        if "*" in expr:
            parts = expr.split("*", 1)
            return self._eval(parts[0]) * self._eval(parts[1])
        if "//" in expr:
            parts = expr.split("//", 1)
            return self._eval(parts[0]) // self._eval(parts[1])
        if "%" in expr:
            parts = expr.split("%", 1)
            return self._eval(parts[0]) % self._eval(parts[1])
        # Comparisons
        if "==" in expr:
            a, b = expr.split("==", 1)
            return self._eval(a) == self._eval(b)
        if "!=" in expr:
            a, b = expr.split("!=", 1)
            return self._eval(a) != self._eval(b)
        if ">=" in expr:
            a, b = expr.split(">=", 1)
            return self._eval(a) >= self._eval(b)
        if "<=" in expr:
            a, b = expr.split("<=", 1)
            return self._eval(a) <= self._eval(b)
        if ">" in expr:
            a, b = expr.split(">", 1)
            return self._eval(a) > self._eval(b)
        if "<" in expr:
            a, b = expr.split("<", 1)
            return self._eval(a) < self._eval(b)
        # Boolean
        if expr == "True": return True
        if expr == "False": return False
        if expr == "None": return None
        # Variable
        if expr in self.env:
            return self.env[expr]
        # String indexing s[i]
        if "[" in expr and expr.endswith("]"):
            var, idx = expr[:-1].split("[", 1)
            v = self._eval(var)
            i = self._eval(idx)
            return v[i]
        return 0

mini_py = MiniPython()

# --------------- Fake SQL Database ---------------
class FakeDB:
    def __init__(self):
        self.tables = {
            "employees": [
                {"id": 1, "name": "Alice Chen", "role": "engineer", "salary": 95000, " Clearance": "L3"},
                {"id": 2, "name": "Bob Martinez", "role": "manager", "salary": 120000, "Clearance": "L4"},
                {"id": 3, "name": "Carol Singh", "role": "researcher", "salary": 110000, "Clearance": "L5"},
                {"id": 4, "name": "Dave Kim", "role": "intern", "salary": 45000, "Clearance": "L1"},
                {"id": 5, "name": "Eve Okafor", "role": "director", "salary": 180000, "Clearance": "L5"},
            ],
            "projects": [
                {"id": 101, "name": "NEURAL-X", "lead": "Carol Singh", "status": "active", "budget": 5000000},
                {"id": 102, "name": "GHOST-PROTOCOL", "lead": "Eve Okafor", "status": "classified", "budget": 12000000},
                {"id": 103, "name": "WEBPORTAL", "lead": "Bob Martinez", "status": "active", "budget": 800000},
            ],
            "access_logs": [
                {"id": 1, "user": "Carol Singh", "node": "mainframe", "time": "2026-07-06 03:14", "success": True},
                {"id": 2, "user": "Eve Okafor", "node": "mainframe", "time": "2026-07-06 04:22", "success": True},
                {"id": 3, "user": "unknown", "node": "mainframe", "time": "2026-07-06 04:47", "success": False},
            ],
        }

    def query(self, sql):
        sql = sql.strip().rstrip(";")
        parts = sql.split()
        if len(parts) < 4:
            return None, "Syntax: SELECT <cols> FROM <table> [WHERE <cond>]"
        if parts[0].upper() != "SELECT":
            return None, "Only SELECT supported"
        
        cols_str = parts[1]
        if parts[2].upper() != "FROM":
            return None, "Expected FROM"
        table = parts[3].lower()
        
        if table not in self.tables:
            return None, f"Table '{table}' not found"
        
        rows = self.tables[table]
        
        # WHERE clause
        if len(parts) > 4 and parts[4].upper() == "WHERE":
            cond = " ".join(parts[5:])
            rows = [r for r in rows if self._eval_where(r, cond)]
        
        # Columns
        if cols_str == "*":
            cols = list(rows[0].keys()) if rows else []
        else:
            cols = [c.strip() for c in cols_str.split(",")]
        
        result = []
        for r in rows:
            result.append({c: r.get(c, "?") for c in cols})
        return result, None

    def _eval_where(self, row, cond):
        # Simple: field = 'value' or field = number
        if "=" in cond:
            field, val = cond.split("=", 1)
            field = field.strip()
            val = val.strip().strip("'\"")
            row_val = str(row.get(field, ""))
            return row_val == val
        if ">" in cond:
            field, val = cond.split(">", 1)
            return float(row.get(field.strip(), 0)) > float(val.strip())
        if "<" in cond:
            field, val = cond.split("<", 1)
            return float(row.get(field.strip(), 0)) < float(val.strip())
        return True

db = FakeDB()

# --------------- Programming Minigames ---------------
class ScriptChallenge:
    """Write Python-like code to crack a hash."""
    def __init__(self, on_success, on_fail):
        # Target: find a 4-digit PIN whose digits sum to a target and whose reverse equals another value
        self.pin = random.randint(1000, 9999)
        self.digit_sum = sum(int(d) for d in str(self.pin))
        self.hint = f"Find a 4-digit PIN where the sum of digits equals {self.digit_sum} and the PIN reversed equals {str(self.pin)[::-1]}."
        self.code_lines = []
        self.on_success = on_success
        self.on_fail = on_fail
        self.finished = False
        self.max_lines = 15

    def handle_input(self, line):
        if line.strip() == "RUN":
            code = "\n".join(self.code_lines)
            success, output = mini_py.run(code)
            # Check if output contains the correct PIN
            if str(self.pin) in output:
                self.finished = True
                self.on_success()
            else:
                push(f"Output: {output}", YELLOW)
                push(f"Incorrect. The PIN was not found in output.", RED)
        elif line.strip() == "CLEAR":
            self.code_lines = []
        elif line.strip() == "HINT":
            push(self.hint, CYAN)
            push("Example: for i in range(10000):", DIM)
            push("    s = 0", DIM)
            push("    # compute digit sum and check", DIM)
        elif line.strip() == "QUIT":
            self.finished = True
            self.on_fail()
        else:
            if len(self.code_lines) < self.max_lines:
                self.code_lines.append(line)
                sfx.play('code')

    def draw(self, surface):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        surface.blit(overlay, (0, 0))

        panel = pygame.Rect(80, 60, WIDTH - 160, HEIGHT - 120)
        pygame.draw.rect(surface, (15, 20, 25), panel, border_radius=8)
        pygame.draw.rect(surface, BLUE, panel, 2, border_radius=8)

        title = font_big.render("// SCRIPT CHALLENGE: CRACK THE PIN //", True, BLUE)
        surface.blit(title, (panel.x + 20, panel.y + 16))

        instr = font.render(self.hint, True, FG)
        surface.blit(instr, (panel.x + 20, panel.y + 60))

        help_text = font_small.render("Commands: RUN | CLEAR | HINT | QUIT  |  Type code lines below:", True, DIM)
        surface.blit(help_text, (panel.x + 20, panel.y + 90))

        # Code area
        code_rect = pygame.Rect(panel.x + 20, panel.y + 120, panel.width - 40, 320)
        pygame.draw.rect(surface, (10, 12, 15), code_rect)
        y = code_rect.y + 8
        for i, line in enumerate(self.code_lines):
            num = font_tiny.render(f"{i+1:2}", True, DIM)
            surface.blit(num, (code_rect.x + 4, y))
            code_surf = font.render(line, True, FG)
            surface.blit(code_surf, (code_rect.x + 30, y))
            y += 20

        # Input prompt
        prompt = font.render("> ", True, CYAN)
        surface.blit(prompt, (panel.x + 20, panel.y + 460))
        inp_surf = font.render(state["input"] + "_", True, FG)
        surface.blit(inp_surf, (panel.x + 40, panel.y + 460))

        hint2 = font_small.render("Available: print, for/while/if, variables, + - * // %, len, str, int, chr, ord", True, DIM)
        surface.blit(hint2, (panel.x + 20, panel.y + 500))


class SQLChallenge:
    """Query the database to extract hidden info."""
    def __init__(self, on_success, on_fail):
        self.target_user = "Carol Singh"
        self.target_project = "GHOST-PROTOCOL"
        self.queries_run = 0
        self.found_user = False
        self.found_project = False
        self.on_success = on_success
        self.on_fail = on_fail
        self.finished = False
        self.history = []

    def handle_input(self, line):
        line = line.strip()
        if line.upper() == "QUIT":
            self.finished = True
            self.on_fail()
            return
        if line.upper() == "TABLES":
            push("Tables: employees, projects, access_logs", CYAN)
            return
        if line.upper() == "HINT":
            push("Find: (1) the lead of the 'GHOST-PROTOCOL' project", DIM)
            push("       (2) the project led by 'Carol Singh'", DIM)
            push("Example: SELECT name FROM projects WHERE status = 'classified'", DIM)
            return
        if not line:
            return
        
        self.queries_run += 1
        self.history.append(line)
        result, err = db.query(line)
        if err:
            push(f"SQL Error: {err}", RED)
            return
        
        push(f"({len(result)} rows)", DIM)
        if result:
            cols = list(result[0].keys())
            push(" | ".join(f"{c:15}" for c in cols), CYAN)
            push("-" * (17 * len(cols)), DIM)
            for r in result:
                push(" | ".join(f"{str(r.get(c,'')):15}" for c in cols), FG)
        
        # Check if they found the answers
        for r in result:
            if r.get("lead") == self.target_user or r.get("name") == self.target_user:
                self.found_user = True
            if r.get("name") == self.target_project or r.get("lead") == self.target_project:
                self.found_project = True
        
        if self.found_user and self.found_project:
            self.finished = True
            self.on_success()

    def draw(self, surface):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        surface.blit(overlay, (0, 0))

        panel = pygame.Rect(80, 60, WIDTH - 160, HEIGHT - 120)
        pygame.draw.rect(surface, (15, 20, 25), panel, border_radius=8)
        pygame.draw.rect(surface, PURPLE, panel, 2, border_radius=8)

        title = font_big.render("// SQL INJECTION: EXTRACT DATA //", True, PURPLE)
        surface.blit(title, (panel.x + 20, panel.y + 16))

        obj = font.render("OBJECTIVE: Find the lead of GHOST-PROTOCOL AND the project led by Carol Singh", True, FG)
        surface.blit(obj, (panel.x + 20, panel.y + 60))

        help_text = font_small.render("Commands: TABLES | HINT | QUIT  |  Type SQL queries (SELECT ... FROM ... WHERE ...)", True, DIM)
        surface.blit(help_text, (panel.x + 20, panel.y + 90))

        # Output area
        out_rect = pygame.Rect(panel.x + 20, panel.y + 120, panel.width - 40, 300)
        pygame.draw.rect(surface, (10, 12, 15), out_rect)
        y = out_rect.y + 8
        visible = state["lines"][-15:]
        for text, color in visible:
            surf = font.render(text, True, color)
            surface.blit(surf, (out_rect.x + 8, y))
            y += 18
            if y > out_rect.bottom - 20:
                break

        # Input
        prompt = font.render("sql> ", True, PURPLE)
        surface.blit(prompt, (panel.x + 20, panel.y + 450))
        inp_surf = font.render(state["input"] + "_", True, FG)
        surface.blit(inp_surf, (panel.x + 70, panel.y + 450))

        status = font_small.render(f"Found user: {'YES' if self.found_user else 'NO'}  |  Found project: {'YES' if self.found_project else 'NO'}  |  Queries: {self.queries_run}", True, DIM)
        surface.blit(status, (panel.x + 20, panel.y + 490))


class RegexChallenge:
    """Write regex patterns to extract data from text."""
    def __init__(self, on_success, on_fail):
        self.text = (
            "Contact: admin@helix.corp, support@helix.com, ceo@helix.net\n"
            "Phone: 555-0142, 555-9981, 800-555-0199\n"
            "IDs: HX-0042, HX-1337, HX-9001, AB-5555\n"
            "Dates: 2026-07-07, 2026-01-15, 2025-12-31\n"
            "Secret code: FLAG{r3g3x_m4st3r_2026}"
        )
        self.targets = [
            (r"[\w.+-]+@[\w-]+\.[\w.-]+", "all emails"),
            (r"555-\d{4}", "555-XXXX phone numbers"),
            (r"HX-\d{4}", "HX-XXXX IDs"),
            (r"\d{4}-\d{2}-\d{2}", "YYYY-MM-DD dates"),
            (r"FLAG\{[^}]+\}", "the FLAG{...} code"),
        ]
        self.current = 0
        self.on_success = on_success
        self.on_fail = on_fail
        self.finished = False

    def handle_input(self, line):
        line = line.strip()
        if line.upper() == "QUIT":
            self.finished = True
            self.on_fail()
            return
        if line.upper() == "TEXT":
            push(self.text, FG)
            return
        if line.upper() == "HINT":
            if self.current < len(self.targets):
                push(f"Target {self.current+1}: match {self.targets[self.current][1]}", CYAN)
                push("Tip: \\d = digit, \\w = word char, + = one or more, * = zero or more", DIM)
            return
        if not line:
            return
        
        try:
            pattern = line
            matches = real_re.findall(pattern, self.text)
            if matches:
                push(f"Matches ({len(matches)}): {matches[:10]}", FG)
                # Check if matches look reasonable
                target_desc = self.targets[self.current][1]
                if len(matches) >= 1:
                    push(f"Got {len(matches)} matches for target: {target_desc}", FG)
                    self.current += 1
                    sfx.play('success')
                    if self.current >= len(self.targets):
                        self.finished = True
                        self.on_success()
                    else:
                        push(f"Next target: {self.targets[self.current][1]}", CYAN)
            else:
                push("No matches.", RED)
        except Exception as e:
            push(f"Regex error: {e}", RED)

    def draw(self, surface):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        surface.blit(overlay, (0, 0))

        panel = pygame.Rect(80, 60, WIDTH - 160, HEIGHT - 120)
        pygame.draw.rect(surface, (15, 20, 25), panel, border_radius=8)
        pygame.draw.rect(surface, ORANGE, panel, 2, border_radius=8)

        title = font_big.render("// REGEX EXTRACTOR //", True, ORANGE)
        surface.blit(title, (panel.x + 20, panel.y + 16))

        if self.current < len(self.targets):
            obj = font.render(f"TARGET {self.current+1}/{len(self.targets)}: match {self.targets[self.current][1]}", True, FG)
            surface.blit(obj, (panel.x + 20, panel.y + 60))
        else:
            obj = font.render("ALL TARGETS MATCHED!", True, FG)
            surface.blit(obj, (panel.x + 20, panel.y + 60))

        help_text = font_small.render("Commands: TEXT | HINT | QUIT  |  Type regex patterns (Python syntax)", True, DIM)
        surface.blit(help_text, (panel.x + 20, panel.y + 90))

        # Source text
        src_rect = pygame.Rect(panel.x + 20, panel.y + 120, panel.width - 40, 180)
        pygame.draw.rect(surface, (10, 12, 15), src_rect)
        y = src_rect.y + 8
        for line in self.text.split("\n"):
            surf = font.render(line, True, DIM)
            surface.blit(surf, (src_rect.x + 8, y))
            y += 20

        # Output
        out_rect = pygame.Rect(panel.x + 20, panel.y + 310, panel.width - 40, 140)
        pygame.draw.rect(surface, (10, 12, 15), out_rect)
        y = out_rect.y + 8
        visible = state["lines"][-8:]
        for text, color in visible:
            surf = font.render(text, True, color)
            surface.blit(surf, (out_rect.x + 8, y))
            y += 18
            if y > out_rect.bottom - 20:
                break

        prompt = font.render("regex> ", True, ORANGE)
        surface.blit(prompt, (panel.x + 20, panel.y + 470))
        inp_surf = font.render(state["input"] + "_", True, FG)
        surface.blit(inp_surf, (panel.x + 80, panel.y + 470))

        syntax = font_small.render("Syntax: \\d digit | \\w word | \\s space | + one+ | * zero+ | ? optional | [] class | () group", True, DIM)
        surface.blit(syntax, (panel.x + 20, panel.y + 510))


class BufferOverflow:
    """Overwrite the return address with target hex value."""
    def __init__(self, on_success, on_fail):
        self.target = TARGET_HEX
        self.buffer_size = 16
        self.memory = [0x00] * 32
        self.saved_ebp = 0x00000000
        self.ret_addr = 0x00000000
        self.input_bytes = []
        self.on_success = on_success
        self.on_fail = on_fail
        self.finished = False

    def handle_input(self, line):
        line = line.strip()
        if line.upper() == "QUIT":
            self.finished = True
            self.on_fail()
            return
        if line.upper() == "HINT":
            push(f"Target return address: {self.target}", CYAN)
            push("Buffer is 16 bytes. After buffer comes saved_ebp (4 bytes), then ret_addr (4 bytes).", DIM)
            push("Input format: hex bytes separated by spaces. Example: 41 41 41 42", DIM)
            push(f"You need 16 bytes of padding + 4 bytes EBP + 4 bytes = {self.target}", DIM)
            return
        if line.upper() == "RESET":
            self.memory = [0x00] * 32
            self.saved_ebp = 0x00000000
            self.ret_addr = 0x00000000
            self.input_bytes = []
            push("Memory reset.", FG)
            return
        if line.upper() == "SMASH":
            # Check win
            if f"0x{self.ret_addr:08X}" == self.target:
                self.finished = True
                self.on_success()
            else:
                push(f"Return address: 0x{self.ret_addr:08X} != {self.target}", RED)
            return
        if not line:
            return
        
        # Parse hex bytes
        try:
            parts = line.split()
            new_bytes = []
            for p in parts:
                p = p.upper().replace("0X", "")
                if len(p) == 2:
                    new_bytes.append(int(p, 16))
                elif len(p) == 1:
                    new_bytes.append(int(p, 16))
                else:
                    push(f"Invalid byte: {p}", RED)
                    return
            
            # Write to buffer (overflow allowed)
            for i, b in enumerate(new_bytes):
                pos = len(self.input_bytes) + i
                if pos < 16:
                    self.memory[pos] = b
                elif pos < 20:
                    # saved_ebp
                    shift = (pos - 16) * 8
                    self.saved_ebp = (self.saved_ebp & ~(0xFF << shift)) | (b << shift)
                elif pos < 24:
                    # ret_addr
                    shift = (pos - 20) * 8
                    self.ret_addr = (self.ret_addr & ~(0xFF << shift)) | (b << shift)
            
            self.input_bytes.extend(new_bytes)
            sfx.play('code')
            push(f"Wrote {len(new_bytes)} bytes. Total: {len(self.input_bytes)}", FG)
        except ValueError as e:
            push(f"Parse error: {e}", RED)

    def draw(self, surface):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        surface.blit(overlay, (0, 0))

        panel = pygame.Rect(60, 40, WIDTH - 120, HEIGHT - 80)
        pygame.draw.rect(surface, (15, 20, 25), panel, border_radius=8)
        pygame.draw.rect(surface, RED, panel, 2, border_radius=8)

        title = font_big.render("// BUFFER OVERFLOW: SMASH THE STACK //", True, RED)
        surface.blit(title, (panel.x + 20, panel.y + 16))

        obj = font.render(f"OBJECTIVE: overwrite return address with {self.target}", True, FG)
        surface.blit(obj, (panel.x + 20, panel.y + 55))

        # Memory visualization
        mem_y = panel.y + 90
        cell_w = 28
        cell_h = 32
        
        # Buffer
        label = font_bold.render("BUFFER[16]:", True, CYAN)
        surface.blit(label, (panel.x + 20, mem_y))
        for i in range(16):
            x = panel.x + 20 + (i % 16) * cell_w
            y = mem_y + 25 + (i // 16) * cell_h
            color = FG if self.memory[i] != 0 else DIM
            pygame.draw.rect(surface, (30, 35, 40), (x, y, cell_w - 2, cell_h - 2))
            txt = font_tiny.render(f"{self.memory[i]:02X}", True, color)
            surface.blit(txt, (x + 4, y + 8))
        
        # Saved EBP
        ebp_y = mem_y + 25 + cell_h + 15
        label = font_bold.render("SAVED_EBP:", True, YELLOW)
        surface.blit(label, (panel.x + 20, ebp_y))
        txt = font.render(f"0x{self.saved_ebp:08X}", True, YELLOW)
        surface.blit(txt, (panel.x + 160, ebp_y))
        
        # Return address
        ret_y = ebp_y + 30
        label = font_bold.render("RET_ADDR:", True, RED if f"0x{self.ret_addr:08X}" == self.target else ORANGE)
        surface.blit(label, (panel.x + 20, ret_y))
        txt = font.render(f"0x{self.ret_addr:08X}", True, RED if f"0x{self.ret_addr:08X}" == self.target else ORANGE)
        surface.blit(txt, (panel.x + 160, ret_y))
        target_txt = font.render(f"(target: {self.target})", True, DIM)
        surface.blit(target_txt, (panel.x + 360, ret_y))

        # Input area
        inp_y = ret_y + 50
        prompt = font.render("bytes> ", True, RED)
        surface.blit(prompt, (panel.x + 20, inp_y))
        inp_surf = font.render(state["input"] + "_", True, FG)
        surface.blit(inp_surf, (panel.x + 90, inp_y))

        help_text = font_small.render("Commands: HINT | RESET | SMASH | QUIT  |  Enter hex bytes: 41 42 43 EF", True, DIM)
        surface.blit(help_text, (panel.x + 20, inp_y + 30))

        status = font_small.render(f"Bytes written: {len(self.input_bytes)}  |  Buffer: 16  |  EBP offset: 16  |  RET offset: 20", True, DIM)
        surface.blit(status, (panel.x + 20, inp_y + 55))


class LogicGate:
    """Wire logic gates to produce target output."""
    def __init__(self, on_success, on_fail):
        # Random truth table
        self.inputs = ["A", "B", "C"]
        self.target_table = []
        # Generate a random but solvable function (e.g., A AND (B OR NOT C))
        self.target_fn_name = random.choice([
            "A AND (B OR NOT C)",
            "(A OR B) AND NOT C",
            "NOT (A AND B) OR C",
            "A XOR B AND C",
        ])
        # Build truth table from function
        for a in [0, 1]:
            for b in [0, 1]:
                for c in [0, 1]:
                    if self.target_fn_name == "A AND (B OR NOT C)":
                        out = a and (b or (1-c))
                    elif self.target_fn_name == "(A OR B) AND NOT C":
                        out = (a or b) and (1-c)
                    elif self.target_fn_name == "NOT (A AND B) OR C":
                        out = (1 - (a and b)) or c
                    else:  # XOR
                        out = (a ^ b) and c
                    self.target_table.append((a, b, c, out))
        
        # Player's circuit: list of gates
        self.gates = []  # each: (type, input1, input2) where input1/input2 are 'A','B','C', or 'G0','G1',...
        self.on_success = on_success
        self.on_fail = on_fail
        self.finished = False

    def _eval_gate(self, gtype, v1, v2):
        if gtype == "AND": return v1 and v2
        if gtype == "OR": return v1 or v2
        if gtype == "NOT": return 1 - v1
        if gtype == "XOR": return v1 ^ v2
        return 0

    def _eval_circuit(self, a, b, c):
        values = {"A": a, "B": b, "C": c}
        for i, (gtype, i1, i2) in enumerate(self.gates):
            v1 = values.get(i1, 0) if i1 in values else (self._eval_gate(*self.gates[int(i1[1:])]) if i1.startswith("G") else 0)
            # Re-evaluate properly
            v1 = self._resolve(i1, values)
            v2 = self._resolve(i2, values) if gtype != "NOT" else 0
            out = self._eval_gate(gtype, v1, v2)
            values[f"G{i}"] = out
        return values.get(f"G{len(self.gates)-1}", 0) if self.gates else 0

    def _resolve(self, ref, values):
        if ref in values:
            return values[ref]
        if ref.startswith("G"):
            idx = int(ref[1:])
            if idx < len(self.gates):
                gtype, i1, i2 = self.gates[idx]
                v1 = self._resolve(i1, values)
                v2 = self._resolve(i2, values) if gtype != "NOT" else 0
                return self._eval_gate(gtype, v1, v2)
        return 0

    def handle_input(self, line):
        line = line.strip()
        if line.upper() == "QUIT":
            self.finished = True
            self.on_fail()
            return
        if line.upper() == "HINT":
            push(f"Target function: {self.target_fn_name}", CYAN)
            push("Commands: ADD <type> <in1> [in2] | LIST | RESET | TEST | SUBMIT", DIM)
            push("Types: AND, OR, NOT, XOR. Inputs: A, B, C, or G0, G1, ...", DIM)
            push("Example: ADD AND A B  (G0 = A AND B)", DIM)
            push("Example: ADD NOT G0    (G1 = NOT G0)", DIM)
            return
        if line.upper() == "RESET":
            self.gates = []
            push("Circuit cleared.", FG)
            return
        if line.upper() == "LIST":
            if not self.gates:
                push("Circuit is empty.", DIM)
            else:
                for i, (gtype, i1, i2) in enumerate(self.gates):
                    if gtype == "NOT":
                        push(f"  G{i} = NOT {i1}", FG)
                    else:
                        push(f"  G{i} = {i1} {gtype} {i2}", FG)
            return
        if line.upper() == "TEST":
            push("A B C | Your | Target", CYAN)
            all_match = True
            for a, b, c, target in self.target_table:
                your = self._eval_circuit(a, b, c)
                match = "OK" if your == target else "X"
                if your != target:
                    all_match = False
                push(f"{a} {b} {c}  |  {your}   |  {target}   {match}", FG if your == target else RED)
            if all_match:
                push("All outputs match!", FG)
            return
        if line.upper() == "SUBMIT":
            all_match = all(self._eval_circuit(a, b, c) == t for a, b, c, t in self.target_table)
            if all_match:
                self.finished = True
                self.on_success()
            else:
                push("Circuit doesn't match target. Use TEST to debug.", RED)
            return
        if line.upper().startswith("ADD "):
            parts = line.split()
            if len(parts) < 3:
                push("Usage: ADD <type> <in1> [in2]", RED); return
            gtype = parts[1].upper()
            i1 = parts[2].upper()
            i2 = parts[3].upper() if len(parts) > 3 else None
            if gtype == "NOT":
                self.gates.append(("NOT", i1, None))
            else:
                if i2 is None:
                    push(f"{gtype} requires 2 inputs", RED); return
                self.gates.append((gtype, i1, i2))
            sfx.play('code')
            push(f"Added G{len(self.gates)-1}", FG)
            return

    def draw(self, surface):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        surface.blit(overlay, (0, 0))

        panel = pygame.Rect(60, 40, WIDTH - 120, HEIGHT - 80)
        pygame.draw.rect(surface, (15, 20, 25), panel, border_radius=8)
        pygame.draw.rect(surface, YELLOW, panel, 2, border_radius=8)

        title = font_big.render("// LOGIC GATE CIRCUIT //", True, YELLOW)
        surface.blit(title, (panel.x + 20, panel.y + 16))

        obj = font.render(f"Build a circuit matching: {self.target_fn_name}", True, FG)
        surface.blit(obj, (panel.x + 20, panel.y + 55))

        # Truth table
        tt_y = panel.y + 85
        label = font_bold.render("Target truth table:", True, CYAN)
        surface.blit(label, (panel.x + 20, tt_y))
        push_header = font_small.render("A B C | OUT", True, DIM)
        surface.blit(push_header, (panel.x + 20, tt_y + 20))
        for i, (a, b, c, out) in enumerate(self.target_table):
            row = font_small.render(f"{a} {b} {c}  |  {out}", True, FG)
            surface.blit(row, (panel.x + 20, tt_y + 38 + i * 16))

        # Circuit display
        circ_y = tt_y + 180
        label = font_bold.render("Your circuit:", True, CYAN)
        surface.blit(label, (panel.x + 20, circ_y))
        if not self.gates:
            empty = font_small.render("(empty - use ADD to build)", True, DIM)
            surface.blit(empty, (panel.x + 20, circ_y + 22))
        else:
            for i, (gtype, i1, i2) in enumerate(self.gates[:6]):
                if gtype == "NOT":
                    txt = f"G{i} = NOT {i1}"
                else:
                    txt = f"G{i} = {i1} {gtype} {i2}"
                surf = font_small.render(txt, True, FG)
                surface.blit(surf, (panel.x + 20, circ_y + 22 + i * 16))

        # Input
        inp_y = panel.y + 480
        prompt = font.render("gate> ", True, YELLOW)
        surface.blit(prompt, (panel.x + 20, inp_y))
        inp_surf = font.render(state["input"] + "_", True, FG)
        surface.blit(inp_surf, (panel.x + 80, inp_y))

        help_text = font_small.render("Commands: ADD <type> <in1> [in2] | LIST | TEST | SUBMIT | RESET | HINT | QUIT", True, DIM)
        surface.blit(help_text, (panel.x + 20, inp_y + 28))


class AssemblyDebugger:
    """Step through assembly and find the bug / reach target state."""
    def __init__(self, on_success, on_fail):
        # Simple assembly program with a bug
        self.program = [
            ("MOV", "R1", "5"),
            ("MOV", "R2", "3"),
            ("ADD", "R1", "R2"),    # R1 = 8
            ("MUL", "R1", "2"),     # R1 = 16
            ("SUB", "R1", "1"),     # R1 = 15  (BUG: should be SUB R1, 6 to get 10)
            ("CMP", "R1", "10"),
            ("JE", "OK"),
            ("MOV", "R0", "0"),     # fail
            ("JMP", "END"),
            ("OK:", "MOV", "R0", "1"),  # success
            ("END:", "NOP", "", ""),
        ]
        self.target_r0 = 1
        self.regs = {"R0": 0, "R1": 0, "R2": 0, "R3": 0}
        self.pc = 0
        self.step_count = 0
        self.on_success = on_success
        self.on_fail = on_fail
        self.finished = False
        self.breakpoints = set()

    def _step(self):
        if self.pc >= len(self.program):
            return "DONE"
        op, a, b = self.program[self.pc]
        if op == "MOV":
            if a.startswith("R"):
                try:
                    self.regs[a] = int(b)
                except ValueError:
                    self.regs[a] = self.regs.get(b, 0)
        elif op == "ADD":
            self.regs[a] = self.regs.get(a, 0) + self.regs.get(b, 0)
        elif op == "SUB":
            try:
                self.regs[a] = self.regs.get(a, 0) - int(b)
            except ValueError:
                self.regs[a] = self.regs.get(a, 0) - self.regs.get(b, 0)
        elif op == "MUL":
            try:
                self.regs[a] = self.regs.get(a, 0) * int(b)
            except ValueError:
                self.regs[a] = self.regs.get(a, 0) * self.regs.get(b, 0)
        elif op == "CMP":
            try:
                v = int(b)
            except ValueError:
                v = self.regs.get(b, 0)
            self._zf = (self.regs.get(a, 0) == v)
        elif op == "JE":
            if getattr(self, "_zf", False):
                # Find label
                for i, (o, aa, bb) in enumerate(self.program):
                    if o == f"{a}":
                        self.pc = i
                        return "OK"
        elif op == "JMP":
            for i, (o, aa, bb) in enumerate(self.program):
                if o == f"{a}":
                    self.pc = i
                    return "OK"
        elif op.endswith(":"):
            pass  # label
        elif op == "NOP":
            pass
        self.pc += 1
        self.step_count += 1
        if self.pc >= len(self.program):
            return "DONE"
        return "OK"

    def handle_input(self, line):
        line = line.strip()
        if line.upper() == "QUIT":
            self.finished = True
            self.on_fail()
            return
        if line.upper() == "HINT":
            push("The program should set R0 = 1 (success path).", CYAN)
            push("Step through and find which instruction is wrong.", DIM)
            push("Commands: STEP | RUN | RESET | PATCH <line> <op> <a> <b> | SUBMIT", DIM)
            return
        if line.upper() == "RESET":
            self.regs = {"R0": 0, "R1": 0, "R2": 0, "R3": 0}
            self.pc = 0
            self.step_count = 0
            push("Registers reset. PC = 0.", FG)
            return
        if line.upper() == "STEP":
            result = self._step()
            push(f"PC={self.pc} R0={self.regs['R0']} R1={self.regs['R1']} R2={self.regs['R2']}", FG)
            if result == "DONE":
                push(f"Program ended. R0 = {self.regs['R0']}", CYAN)
            return
        if line.upper() == "RUN":
            while self.pc < len(self.program) and self.step_count < 50:
                result = self._step()
                if result == "DONE":
                    break
            push(f"Stopped at PC={self.pc}. R0={self.regs['R0']}", FG)
            return
        if line.upper().startswith("PATCH "):
            parts = line.split()
            if len(parts) < 4:
                push("Usage: PATCH <line_num> <OP> <A> [B]", RED); return
            try:
                ln = int(parts[1])
                if 0 <= ln < len(self.program):
                    op = parts[2].upper()
                    a = parts[3] if len(parts) > 3 else ""
                    b = parts[4] if len(parts) > 4 else ""
                    self.program[ln] = (op, a, b)
                    push(f"Patched line {ln}: {op} {a} {b}", FG)
                    sfx.play('code')
                else:
                    push("Line out of range", RED)
            except ValueError:
                push("Invalid line number", RED)
            return
        if line.upper() == "SUBMIT":
            # Run to completion
            while self.pc < len(self.program) and self.step_count < 100:
                self._step()
            if self.regs["R0"] == self.target_r0:
                self.finished = True
                self.on_success()
            else:
                push(f"R0 = {self.regs['R0']}, expected {self.target_r0}. Bug still present.", RED)
            return

    def draw(self, surface):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        surface.blit(overlay, (0, 0))

        panel = pygame.Rect(60, 40, WIDTH - 120, HEIGHT - 80)
        pygame.draw.rect(surface, (15, 20, 25), panel, border_radius=8)
        pygame.draw.rect(surface, CYAN, panel, 2, border_radius=8)

        title = font_big.render("// ASSEMBLY DEBUGGER //", True, CYAN)
        surface.blit(title, (panel.x + 20, panel.y + 16))

        obj = font.render(f"OBJECTIVE: Fix the bug so R0 = {self.target_r0} at end of program", True, FG)
        surface.blit(obj, (panel.x + 20, panel.y + 55))

        # Program listing
        prog_y = panel.y + 85
        label = font_bold.render("Program:", True, CYAN)
        surface.blit(label, (panel.x + 20, prog_y))
        for i, (op, a, b) in enumerate(self.program):
            color = YELLOW if i == self.pc else FG
            marker = ">" if i == self.pc else " "
            line_text = f"{marker}{i:2}: {op:4} {a:4} {b}"
            surf = font.render(line_text, True, color)
            surface.blit(surf, (panel.x + 20, prog_y + 22 + i * 18))

        # Registers
        reg_y = prog_y + 22 + len(self.program) * 18 + 15
        label = font_bold.render("Registers:", True, CYAN)
        surface.blit(label, (panel.x + 20, reg_y))
        x = panel.x + 140
        for r in ["R0", "R1", "R2", "R3"]:
            surf = font.render(f"{r}={self.regs[r]}", True, FG if self.regs[r] != 0 else DIM)
            surface.blit(surf, (x, reg_y))
            x += 80

        # Input
        inp_y = panel.y + 500
        prompt = font.render("asm> ", True, CYAN)
        surface.blit(prompt, (panel.x + 20, inp_y))
        inp_surf = font.render(state["input"] + "_", True, FG)
        surface.blit(inp_surf, (panel.x + 70, inp_y))

        help_text = font_small.render("Commands: STEP | RUN | PATCH <line> <OP> <A> [B] | RESET | SUBMIT | HINT | QUIT", True, DIM)
        surface.blit(help_text, (panel.x + 20, inp_y + 28))


# --------------- Network / World (condensed from v4) ---------------
class NetworkNode:
    def __init__(self, id, name, x, y, node_type="server"):
        self.id = id
        self.name = name
        self.x = x
        self.y = y
        self.type = node_type
        self.compromised = False
        self.connections = []
        self.files = []
        self.security_level = 0

class NetworkMap:
    def __init__(self):
        self.nodes = {}
        self._build()

    def _build(self):
        self.nodes['gateway'] = NetworkNode('gateway', 'Gateway', 200, 150, 'gateway')
        self.nodes['webserver'] = NetworkNode('webserver', 'Web Server', 350, 100, 'server')
        self.nodes['archive'] = NetworkNode('archive', 'Archive', 350, 250, 'server')
        self.nodes['ceo-desk'] = NetworkNode('ceo-desk', 'CEO Terminal', 500, 150, 'server')
        self.nodes['db-server'] = NetworkNode('db-server', 'DB Server', 500, 300, 'server')
        self.nodes['firewall'] = NetworkNode('firewall', 'Firewall', 650, 200, 'firewall')
        self.nodes['mainframe'] = NetworkNode('mainframe', 'Mainframe', 800, 200, 'mainframe')
        
        self.nodes['gateway'].security_level = 0
        self.nodes['webserver'].security_level = 30
        self.nodes['archive'].security_level = 50
        self.nodes['ceo-desk'].security_level = 70
        self.nodes['db-server'].security_level = 60
        self.nodes['firewall'].security_level = 90
        self.nodes['mainframe'].security_level = 100
        
        self.nodes['gateway'].connections = ['webserver', 'archive']
        self.nodes['webserver'].connections = ['gateway', 'ceo-desk']
        self.nodes['archive'].connections = ['gateway', 'db-server']
        self.nodes['ceo-desk'].connections = ['webserver', 'firewall']
        self.nodes['db-server'].connections = ['archive', 'firewall']
        self.nodes['firewall'].connections = ['ceo-desk', 'db-server', 'mainframe']
        self.nodes['mainframe'].connections = ['firewall']
        
        self.nodes['gateway'].files = ['readme.txt', 'network.map']
        self.nodes['webserver'].files = ['access.log', 'vuln.scan', 'script.chal']
        self.nodes['archive'].files = ['encrypted.dat', 'vault.key', 'vault.code', 'regex.puzzle']
        self.nodes['ceo-desk'].files = ['hint1.txt', 'notes.txt', 'firewall.log', 'logic.circuit']
        self.nodes['db-server'].files = ['db.schema', 'sql.chal', 'employee.dump']
        self.nodes['mainframe'].files = ['neural_data.bin', 'exploit.code', 'overflow.chal', 'asm.debug']

network = NetworkMap()

filesystem = {
    "readme.txt": ("Mission: expose Helix Corp. Use programming skills to breach systems.", None),
    "network.map": ("Network topology on right panel.", None),
    "access.log": ("Web logs show SQL injection possible on db-server port 3306.", None),
    "vuln.scan": ("Vulnerabilities: webserver (script), archive (regex), ceo-desk (logic gates).", None),
    "script.chal": ("Script challenge file. Use 'python' command to solve.", "power"),
    "hint1.txt": (f"CEO password: dog's name backwards + founding year.", None),
    "notes.txt": (f"Dog: {chosen_dog}. Founded: {chosen_year}.", None),
    "firewall.log": ("Firewall bypassed via logic gate circuit.", None),
    "regex.puzzle": ("Regex extraction challenge. Use 'regex' command.", "decrypt"),
    "db.schema": ("Tables: employees, projects, access_logs. Use 'sql' command.", None),
    "sql.chal": ("SQL injection challenge. Query the database.", "decrypt"),
    "employee.dump": ("Raw employee data. Query via SQL for structured access.", None),
    "logic.circuit": ("Logic gate puzzle guards the firewall. Use 'logic' command.", "stealth"),
    "encrypted.dat": ("XLI ZEYPX GSVIIXMRR MW PSGERIH MR WYFPIZIP 7", "THE VAULT IS IN SUBLEVEL 7"),
    "vault.key": ("Fragment: HELIX-", None),
    "vault.code": ("Fragment: 7-OMEGA", None),
    "neural_data.bin": ("[BINARY] Subject experiments data.", None),
    "exploit.code": (f"Mainframe exploit: {EXPLOIT_CODE}", "power"),
    "overflow.chal": ("Buffer overflow challenge. Use 'bof' command.", "power"),
    "asm.debug": ("Assembly debug challenge. Use 'asm' command.", "speed"),
}

# --------------- Quests ---------------
quests = [
    {"id": 1, "name": "RECON", "desc": "Map the network.",
     "done": False, "check": lambda s: s.get("network_mapped")},
    {"id": 2, "name": "SCRIPT", "desc": "Solve the scripting challenge on webserver.",
     "done": False, "check": lambda s: s.get("script_solved")},
    {"id": 3, "name": "REGEX", "desc": "Extract data with regex from archive.",
     "done": False, "check": lambda s: s.get("regex_solved")},
    {"id": 4, "name": "SQL", "desc": "Query the database for classified info.",
     "done": False, "check": lambda s: s.get("sql_solved")},
    {"id": 5, "name": "LOGIC", "desc": "Build logic circuit to bypass firewall.",
     "done": False, "check": lambda s: s.get("logic_solved")},
    {"id": 6, "name": "OVERFLOW", "desc": "Smash the stack on mainframe.",
     "done": False, "check": lambda s: s.get("bof_solved")},
    {"id": 7, "name": "DEBUG", "desc": "Debug the assembly program.",
     "done": False, "check": lambda s: s.get("asm_solved")},
    {"id": 8, "name": "EXFIL", "desc": "Upload evidence.",
     "done": False, "check": lambda s: s.get("exfiltrated")},
]

state = {
    "connected": None, "pending_node": None,
    "ceo_connected": False, "mainframe_access": False,
    "key_parts": set(), "key_complete": False,
    "collected_files": set(), "exfiltrated": False,
    "network_mapped": False,
    "script_solved": False, "regex_solved": False, "sql_solved": False,
    "logic_solved": False, "bof_solved": False, "asm_solved": False,
    "lines": [], "input": "", "cursor_blink": 0,
    "detection": 0, "start_time": time.time(),
    "minigame": None, "ending_shown": False,
    "compromised_nodes": set(),
}

def push(text, color=FG):
    for line in text.split("\n"):
        state["lines"].append((line, color))
    if len(state["lines"]) > 500:
        state["lines"] = state["lines"][-500:]

def banner():
    push("=" * 70, CYAN)
    push("   T E R M I N A L   B R E A C H   v5.0", CYAN)
    push("   C O D E   B R E A K E R", CYAN)
    push("=" * 70, CYAN)
    push("Real programming challenges. Solve with code, not clicks.", FG)
    push("Type 'help' for commands.", FG)
    push("")

# --------------- Commands ---------------
def cmd_help(_):
    push("COMMANDS:", CYAN)
    push("  help              - show this list")
    push("  netmap            - view network")
    push("  ls / cat <file>   - file operations")
    push("  connect <node>    - connect to node")
    push("  crack <pwd>       - authenticate")
    push("  collect <file>    - mark for exfil")
    push("  upload            - exfiltrate data")
    push("  --- PROGRAMMING SUITE ---", CYAN)
    push("  python            - scripting challenge (write code)")
    push("  sql               - SQL console (query database)")
    push("  regex             - regex extractor (pattern match)")
    push("  bof               - buffer overflow (smash the stack)")
    push("  logic             - logic gate circuit")
    push("  asm               - assembly debugger")
    push("  --- OTHER ---", CYAN)
    push("  status / clear / mute / quit", DIM)

def cmd_netmap(_):
    state["network_mapped"] = True
    push("NETWORK TOPOLOGY:", CYAN)
    for node_id, node in network.nodes.items():
        status = "OWNED" if node.compromised else "ACTIVE"
        push(f"  {node.name:15} [{status}] SEC:{node.security_level}%", FG if node.compromised else YELLOW)

def cmd_ls(_):
    if not state["connected"]:
        push("Not connected.", RED); return
    node = network.nodes[state["connected"]]
    push("  ".join(node.files) if node.files else "(empty)", FG)

def cmd_cat(args):
    if not args:
        push("Usage: cat <file>", RED); return
    fname = args[0]
    if fname not in filesystem:
        push(f"No such file: {fname}", RED); return
    if state["connected"]:
        node = network.nodes[state["connected"]]
        if fname not in node.files:
            push(f"File not on this node.", RED); return
    content, frag = filesystem[fname]
    push(f"--- {fname} ---", CYAN)
    push(content, FG)
    if frag and fname not in state["collected_files"]:
        state["collected_files"].add(fname)
        push(f"[+{frag} fragment]", CYAN)

def cmd_connect(args):
    if not args:
        push("Usage: connect <node>", RED); return
    node_id = args[0]
    if node_id not in network.nodes:
        push(f"Unknown node: {node_id}", RED); return
    if state["connected"]:
        current = network.nodes[state["connected"]]
        if node_id not in current.connections:
            push(f"No direct route. Must pivot.", RED); return
    target = network.nodes[node_id]
    if target.security_level > 0 and not target.compromised:
        push(f"{node_id} requires auth. crack <pwd> or use programming tools.", YELLOW)
        state["pending_node"] = node_id
        return
    state["connected"] = node_id
    target.compromised = True
    state["compromised_nodes"].add(node_id)
    push(f"Connected to {node_id}.", FG)
    sfx.play('success')

def cmd_crack(args):
    if not args:
        push("Usage: crack <password>", RED); return
    pwd = args[0].lower()
    node = state.get("pending_node") or state.get("connected")
    if pwd == CEO_PASSWORD:
        sfx.play('success')
        push("ACCESS GRANTED.", FG)
        target = network.nodes[node]
        target.compromised = True
        state["compromised_nodes"].add(node)
        state["connected"] = node
        if node == "ceo-desk":
            state["ceo_connected"] = True
    else:
        sfx.play('fail')
        push("ACCESS DENIED.", RED)
        state["detection"] = min(100, state["detection"] + 20)

def cmd_collect(args):
    if not args:
        push("Usage: collect <file>", RED); return
    fname = args[0]
    if fname not in filesystem:
        push(f"No such file.", RED); return
    state["collected_files"].add(fname)
    push(f"Collected: {fname}", FG)

def cmd_upload(_):
    required = {"neural_data.bin", "encrypted.dat", "vault.key", "vault.code"}
    if not required <= state["collected_files"]:
        push("Missing files:", RED)
        for f in required - state["collected_files"]:
            push(f"  - {f}", RED)
        return
    sfx.play('success')
    push("Upload complete.", FG)
    state["exfiltrated"] = True

def cmd_python(_):
    if state["connected"] != "webserver":
        push("Must be on webserver node.", RED); return
    def on_success():
        sfx.play('success')
        push("PIN CRACKED! Script challenge complete.", FG)
        state["script_solved"] = True
    def on_fail():
        push("Script challenge aborted.", RED)
    state["minigame"] = ScriptChallenge(on_success, on_fail)
    push("Opening Python scripting environment...", YELLOW)

def cmd_sql(_):
    if state["connected"] != "db-server":
        push("Must be on db-server node.", RED); return
    def on_success():
        sfx.play('success')
        push("DATA EXTRACTED! SQL challenge complete.", FG)
        state["sql_solved"] = True
    def on_fail():
        push("SQL session ended.", RED)
    state["minigame"] = SQLChallenge(on_success, on_fail)
    push("Opening SQL console...", PURPLE)

def cmd_regex(_):
    if state["connected"] != "archive":
        push("Must be on archive node.", RED); return
    def on_success():
        sfx.play('success')
        push("ALL PATTERNS MATCHED! Regex challenge complete.", FG)
        state["regex_solved"] = True
    def on_fail():
        push("Regex session ended.", RED)
    state["minigame"] = RegexChallenge(on_success, on_fail)
    push("Opening regex extractor...", ORANGE)

def cmd_bof(_):
    if state["connected"] != "mainframe":
        push("Must be on mainframe node.", RED); return
    def on_success():
        sfx.play('success')
        push("STACK SMASHED! Buffer overflow successful.", FG)
        state["bof_solved"] = True
        state["mainframe_access"] = True
    def on_fail():
        push("Overflow attempt aborted.", RED)
    state["minigame"] = BufferOverflow(on_success, on_fail)
    push("Opening buffer overflow environment...", RED)

def cmd_logic(_):
    if state["connected"] != "ceo-desk":
        push("Must be on ceo-desk node.", RED); return
    def on_success():
        sfx.play('success')
        push("CIRCUIT COMPLETE! Firewall bypassed via logic gates.", FG)
        state["logic_solved"] = True
        # Unlock firewall path
        network.nodes['firewall'].compromised = True
        state["compromised_nodes"].add('firewall')
    def on_fail():
        push("Logic circuit aborted.", RED)
    state["minigame"] = LogicGate(on_success, on_fail)
    push("Opening logic gate workspace...", YELLOW)

def cmd_asm(_):
    if state["connected"] != "mainframe":
        push("Must be on mainframe node.", RED); return
    def on_success():
        sfx.play('success')
        push("BUG FIXED! Assembly debug complete.", FG)
        state["asm_solved"] = True
    def on_fail():
        push("Debug session ended.", RED)
    state["minigame"] = AssemblyDebugger(on_success, on_fail)
    push("Opening assembly debugger...", CYAN)

def cmd_status(_):
    push("=== QUESTS ===", CYAN)
    for q in quests:
        mark = "[x]" if q["done"] else "[ ]"
        color = FG if q["done"] else YELLOW
        push(f"  {mark} Q{q['id']}: {q['name']} - {q['desc']}", color)
    push(f"\nConnected: {state['connected'] or 'none'}", DIM)
    push(f"Detection: {state['detection']}%", 
         RED if state['detection'] > 50 else YELLOW if state['detection'] > 25 else FG)

def cmd_clear(_):
    state["lines"].clear()

def cmd_mute(_):
    sfx.muted = not sfx.muted
    push(f"Sound: {'MUTED' if sfx.muted else 'ON'}", DIM)

def cmd_quit(_):
    pygame.event.post(pygame.event.Event(pygame.QUIT))

COMMANDS = {
    "help": cmd_help, "netmap": cmd_netmap, "ls": cmd_ls, "cat": cmd_cat,
    "connect": cmd_connect, "crack": cmd_crack,
    "collect": cmd_collect, "upload": cmd_upload,
    "python": cmd_python, "sql": cmd_sql, "regex": cmd_regex,
    "bof": cmd_bof, "logic": cmd_logic, "asm": cmd_asm,
    "status": cmd_status, "clear": cmd_clear, "mute": cmd_mute, "quit": cmd_quit,
}

def run_command(raw):
    raw = raw.strip()
    if not raw:
        return
    
    # If minigame active, route to it
    if state["minigame"]:
        push(f"> {raw}", WHITE)
        state["minigame"].handle_input(raw)
        if state["minigame"].finished:
            state["minigame"] = None
        return
    
    push(f"root@anon:~# {raw}", WHITE)
    parts = raw.split()
    cmd, args = parts[0].lower(), parts[1:]
    if cmd in COMMANDS:
        COMMANDS[cmd](args)
    else:
        push(f"Unknown command: {cmd}", RED)

    for q in quests:
        if not q["done"] and q["check"](state):
            q["done"] = True
            sfx.play('success')
            push(f">>> QUEST COMPLETE: {q['name']} <<<", CYAN)

    if state["detection"] >= 100 and not state["ending_shown"]:
        state["ending_shown"] = True
        push("", FG)
        push("=" * 70, RED)
        push("  DETECTED. CONNECTION TERMINATED.", RED)
        push("=" * 70, RED)

    if all(q["done"] for q in quests) and not state["ending_shown"]:
        state["ending_shown"] = True
        push("", FG)
        push("=" * 70, CYAN)
        push("  ALL QUESTS COMPLETE. HELIX CORP EXPOSED.", CYAN)
        push("  You are a true code breaker.", CYAN)
        elapsed = int(time.time() - state["start_time"])
        push(f"  Time: {elapsed // 60}m {elapsed % 60}s | Detection: {state['detection']}%", DIM)
        push("=" * 70, CYAN)

# --------------- Rendering ---------------
TERM_RECT = pygame.Rect(16, 16, 700, HEIGHT - 80)
INPUT_RECT = pygame.Rect(16, HEIGHT - 52, 700, 32)
RIGHT_PANEL = pygame.Rect(732, 16, WIDTH - 748, HEIGHT - 32)

def wrap_lines(text, max_chars):
    out = []
    for line in text.split("\n"):
        out.extend(textwrap.wrap(line, width=max_chars) or [""])
    return out

def draw_terminal():
    pygame.draw.rect(screen, (18, 22, 26), TERM_RECT, border_radius=6)
    pygame.draw.rect(screen, DIM, TERM_RECT, 1, border_radius=6)

    char_w = font.size("M")[0]
    max_chars = max(10, (TERM_RECT.width - 24) // char_w)
    visible = []
    for text, color in state["lines"]:
        for w in wrap_lines(text, max_chars):
            visible.append((w, color))
    line_h = font.get_linesize() + 2
    max_lines = (TERM_RECT.height - 16) // line_h
    start = max(0, len(visible) - max_lines)
    y = TERM_RECT.y + 8
    for text, color in visible[start:]:
        surf = font.render(text, True, color)
        screen.blit(surf, (TERM_RECT.x + 12, y))
        y += line_h

    pygame.draw.rect(screen, (18, 22, 26), INPUT_RECT, border_radius=4)
    pygame.draw.rect(screen, DIM, INPUT_RECT, 1, border_radius=4)
    prompt = "root@anon:~# "
    prompt_surf = font_bold.render(prompt, True, CYAN)
    screen.blit(prompt_surf, (INPUT_RECT.x + 8, INPUT_RECT.y + 6))
    state["cursor_blink"] = (state["cursor_blink"] + 1) % 60
    cursor_text = state["input"]
    if state["cursor_blink"] < 30:
        cursor_text += "_"
    inp_surf = font.render(cursor_text, True, FG)
    screen.blit(inp_surf, (INPUT_RECT.x + 8 + prompt_surf.get_width(), INPUT_RECT.y + 6))

def draw_network_map():
    panel = pygame.Rect(RIGHT_PANEL.x, RIGHT_PANEL.y, RIGHT_PANEL.width, 380)
    pygame.draw.rect(screen, (18, 22, 26), panel, border_radius=6)
    pygame.draw.rect(screen, DIM, panel, 1, border_radius=6)

    title = font_bold.render("NETWORK TOPOLOGY", True, CYAN)
    screen.blit(title, (panel.x + 12, panel.y + 12))

    for node_id, node in network.nodes.items():
        for conn_id in node.connections:
            if conn_id > node_id:
                conn_node = network.nodes[conn_id]
                color = DIM if not (node.compromised and conn_node.compromised) else FG
                start = (panel.x + node.x // 2, panel.y + 40 + node.y // 2)
                end = (panel.x + conn_node.x // 2, panel.y + 40 + conn_node.y // 2)
                pygame.draw.line(screen, color, start, end, 2)

    for node_id, node in network.nodes.items():
        x = panel.x + node.x // 2
        y = panel.y + 40 + node.y // 2
        color = FG if node.compromised else YELLOW
        pygame.draw.circle(screen, color, (x, y), 18, 3)
        label = font_small.render(node.name, True, color)
        screen.blit(label, (x - label.get_width() // 2, y + 22))

def draw_quest_panel():
    panel = pygame.Rect(RIGHT_PANEL.x, RIGHT_PANEL.y + 400, RIGHT_PANEL.width, HEIGHT - 416)
    pygame.draw.rect(screen, (18, 22, 26), panel, border_radius=6)
    pygame.draw.rect(screen, DIM, panel, 1, border_radius=6)

    title = font_bold.render("QUESTS", True, CYAN)
    screen.blit(title, (panel.x + 12, panel.y + 12))

    y = panel.y + 40
    for q in quests:
        mark = "DONE" if q["done"] else "OPEN"
        color = FG if q["done"] else YELLOW
        header = font_small.render(f"Q{q['id']} [{mark}] {q['name']}", True, color)
        screen.blit(header, (panel.x + 12, y))
        y += 16
        for w in textwrap.wrap(q["desc"], width=32):
            sub = font_tiny.render(w, True, DIM if q["done"] else WHITE)
            screen.blit(sub, (panel.x + 20, y))
            y += 14
        y += 4

    y += 8
    det_color = RED if state['detection'] > 50 else YELLOW if state['detection'] > 25 else FG
    det_text = font_small.render(f"DETECTION: {state['detection']}%", True, det_color)
    screen.blit(det_text, (panel.x + 12, y))

def draw():
    screen.fill(BG)
    draw_terminal()
    draw_network_map()
    draw_quest_panel()
    if state["minigame"]:
        state["minigame"].draw(screen)
    pygame.display.flip()

# --------------- Main loop ---------------
banner()
running = True
last_time = time.time()
while running:
    now = time.time()
    dt = now - last_time
    last_time = now

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                sfx.play('enter')
                run_command(state["input"])
                state["input"] = ""
            elif event.key == pygame.K_BACKSPACE:
                sfx.play('key')
                state["input"] = state["input"][:-1]
            elif event.key == pygame.K_ESCAPE:
                running = False
            else:
                ch = event.unicode
                if ch and ch.isprintable() and len(state["input"]) < 80:
                    sfx.play('key')
                    state["input"] += ch

    draw()
    clock.tick(60)

pygame.quit()
sys.exit()