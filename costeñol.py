import re
import tkinter as tk
from tkinter import ttk, scrolledtext

# ============================================================
#  COMPILADOR COSTEÑOL — ENTREGA
# Jean Maldonado, Alex Díaz, Andrés Carrillo
# ============================================================

variables = {}

# ---- TOKENS ------------------------------------------------
TOKEN_DEFS = [
    ("TIPO_DATO",      r"(Entero|Real|Texto|Logico)\b"),
    ("CAPTURA",        r"Captura\.(Texto|Entero|Real|Logico)\(\)"),
    ("MENSAJE",        r"Mensaje\.Texto"),
    ("CADENA",         r'"[^"]*"'),
    ("NUMERO_REAL",    r"\d+[.,]\d+"),
    ("NUMERO_ENTERO",  r"\d+"),
    ("OPERADOR",       r"[+\-*/=]"),
    ("PARENTESIS_AB",  r"\("),
    ("PARENTESIS_CI",  r"\)"),
    ("PUNTO_COMA",     r";"),
    ("IDENTIFICADOR",  r"[a-zA-ZáéíóúÁÉÍÓÚñÑ_][a-zA-ZáéíóúÁÉÍÓÚñÑ0-9_]*"),
]

PATRON = "|".join(f"(?P<{n}>{p})" for n, p in TOKEN_DEFS)

KEYWORDS_CORRECTOS = {"Entero", "Real", "Texto", "Logico", "Captura", "Mensaje"}
KEYWORDS_LOWER = {k.lower() for k in KEYWORDS_CORRECTOS}

def tokenizar(linea):
    tokens = []
    pos = 0
    while pos < len(linea):
        if linea[pos].isspace():
            pos += 1
            continue
        match = None
        for nombre, patron in TOKEN_DEFS:
            m = re.match(patron, linea[pos:])
            if m:
                tokens.append({"tipo": nombre, "valor": m.group()})
                pos += len(m.group())
                match = True
                break
        if not match:
            tokens.append({"tipo": "DESCONOCIDO", "valor": linea[pos]})
            pos += 1
    return tokens

# ---- ANÁLISIS ----------------------------------------------

def dividir_por_punto_coma(tokens):
    grupos, actual = [], []
    for t in tokens:
        actual.append(t)
        if t["tipo"] == "PUNTO_COMA":
            grupos.append(actual)
            actual = []
    if actual:
        grupos.append(actual)
    return grupos

def validar_expresion(tokens, variables, tipo_esperado):
    for t in tokens:
        if t["tipo"] == "DESCONOCIDO":
            return f"Carácter inválido: '{t['valor']}'"
        if t["tipo"] == "IDENTIFICADOR":
            if t["valor"] not in variables:
                return f"Variable '{t['valor']}' no fue declarada"
    if len(tokens) == 1:
        t = tokens[0]
        if t["tipo"] == "CADENA" and tipo_esperado != "Texto":
            return f"No se puede asignar Texto a variable de tipo {tipo_esperado}"
        if t["tipo"] == "NUMERO_ENTERO" and tipo_esperado == "Texto":
            return f"No se puede asignar Entero a variable de tipo Texto"
        if t["tipo"] == "NUMERO_REAL" and tipo_esperado == "Texto":
            return f"No se puede asignar Real a variable de tipo Texto"
        if t["tipo"] == "NUMERO_REAL" and tipo_esperado == "Entero":
            return f"No se puede asignar Real a variable de tipo Entero"
    return None

def analizar_segmento(tokens, variables):
    # Quitar punto y coma al final
    tks = tokens[:-1] if tokens and tokens[-1]["tipo"] == "PUNTO_COMA" else tokens

    if not tks:
        return None

    # Verificar que termina con ;
    if not tokens or tokens[-1]["tipo"] != "PUNTO_COMA":
        return "Falta ';' al final de la instrucción"

    # Case-sensitive check
    for t in tks:
        if t["tipo"] == "IDENTIFICADOR":
            val_lower = t["valor"].lower()
            if val_lower in KEYWORDS_LOWER and t["valor"] not in KEYWORDS_CORRECTOS:
                correcto = next(k for k in KEYWORDS_CORRECTOS if k.lower() == val_lower)
                return f"'{t['valor']}' debe escribirse como '{correcto}' (mayúscula inicial)"

    n = len(tks)

    # DECLARACIÓN: nombre Tipo
    if (n == 2
            and tks[0]["tipo"] == "IDENTIFICADOR"
            and tks[1]["tipo"] == "TIPO_DATO"):
        nombre = tks[0]["valor"]
        tipo = tks[1]["valor"]
        if nombre in KEYWORDS_CORRECTOS:
            return f"'{nombre}' es una palabra reservada"
        variables[nombre] = {"tipo": tipo, "inicializada": False}
        return None

    # CAPTURA: var = Captura.Tipo()
    if (n == 3
            and tks[0]["tipo"] == "IDENTIFICADOR"
            and tks[1]["tipo"] == "OPERADOR" and tks[1]["valor"] == "="
            and tks[2]["tipo"] == "CAPTURA"):
        nombre = tks[0]["valor"]
        m = re.match(r"Captura\.(Entero|Real|Texto|Logico)", tks[2]["valor"])
        tipo_captura = m.group(1) if m else None
        if nombre not in variables:
            return f"Variable '{nombre}' no fue declarada"
        if variables[nombre]["tipo"] != tipo_captura:
            return (f"Tipo incompatible: '{nombre}' es {variables[nombre]['tipo']} "
                    f"pero se captura como {tipo_captura}")
        variables[nombre]["inicializada"] = True
        return None

    # MENSAJE: Mensaje.Texto("...")
    if tks[0]["tipo"] == "MENSAJE":
        if (n == 4
                and tks[1]["tipo"] == "PARENTESIS_AB"
                and tks[2]["tipo"] == "CADENA"
                and tks[3]["tipo"] == "PARENTESIS_CI"):
            return None
        return 'Sintaxis incorrecta. Uso correcto: Mensaje.Texto("texto");'

    # ASIGNACIÓN: var = expresion
    if (n >= 3
            and tks[0]["tipo"] == "IDENTIFICADOR"
            and tks[1]["tipo"] == "OPERADOR" and tks[1]["valor"] == "="):
        nombre = tks[0]["valor"]
        if nombre not in variables:
            return f"Variable '{nombre}' no fue declarada"
        expr = tks[2:]
        err = validar_expresion(expr, variables, variables[nombre]["tipo"])
        if err:
            return err
        variables[nombre]["inicializada"] = True
        return None

    return f"Instrucción no reconocida: '{' '.join(t['valor'] for t in tokens)}'"

def analizar_linea(tokens, variables):
    if not tokens:
        return None

    hay_desconocido = next((t for t in tokens if t["tipo"] == "DESCONOCIDO"), None)
    if hay_desconocido:
        return f"Carácter no reconocido: '{hay_desconocido['valor']}'"

    segmentos = dividir_por_punto_coma(tokens)
    if len(segmentos) > 1:
        for seg in segmentos:
            if not seg:
                continue
            err = analizar_segmento(seg, variables)
            if err:
                return err
        return None

    return analizar_segmento(tokens, variables)

def compilar_codigo(codigo):
    errores = []
    all_tokens = []
    variables = {}

    lineas = codigo.split("\n")
    for n_linea, raw in enumerate(lineas, start=1):
        linea = raw.strip()
        if not linea or linea.startswith("//"):
            continue
        tokens = tokenizar(linea)
        all_tokens.append({"linea": n_linea, "tokens": tokens})
        err = analizar_linea(tokens, variables)
        if err:
            errores.append({"linea": n_linea, "msg": err})

    return errores, all_tokens, variables

# ============================================================
#  INTERFAZ GRÁFICA (TKINTER)
# ============================================================

BG       = "#1e1e2e"
BG2      = "#181825"
PANEL    = "#252538"
BORDER   = "#45475a"
ACCENT   = "#cba6f7"   # lila
VERDE    = "#a6e3a1"
ROJO     = "#f38ba8"
AMARILLO = "#f9e2af"
TEXTO    = "#cdd6f4"
MUTED    = "#6c7086"
AZUL     = "#89b4fa"
FONT_MONO = ("Consolas", 11)
FONT_UI   = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_TIT  = ("Segoe UI", 13, "bold")


class CompiladorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Compilador Costeñol — Entrega")
        self.root.configure(bg=BG)
        self.root.geometry("1000x640")
        self.root.minsize(800, 500)
        self._construir_ui()

    def _construir_ui(self):
        # ── HEADER ──────────────────────────────────────────
        hdr = tk.Frame(self.root, bg=PANEL, height=48)
        hdr.pack(fill=tk.X, side=tk.TOP)
        hdr.pack_propagate(False)

        tk.Label(hdr, text=" CUL ", bg=ACCENT, fg=BG,
                 font=("Segoe UI", 11, "bold"), padx=6).pack(side=tk.LEFT, padx=12, pady=10)
        tk.Label(hdr, text="COMPILADOR COSTEÑOL", bg=PANEL, fg=TEXTO,
                 font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, pady=10)
        tk.Label(hdr, text="ENTREGA ", bg=AZUL, fg=BG,
                 font=("Segoe UI", 9, "bold"), padx=8).pack(side=tk.RIGHT, padx=12, pady=14)

        # ── BODY (editor + resultado) ────────────────────────
        body = tk.PanedWindow(self.root, orient=tk.HORIZONTAL,
                              bg=BORDER, sashwidth=3, sashrelief=tk.FLAT)
        body.pack(fill=tk.BOTH, expand=True)

        # Panel izquierdo — editor
        left = tk.Frame(body, bg=BG)
        body.add(left, minsize=300, width=480)

        tk.Label(left, text="  Editor de código", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9), anchor="w").pack(fill=tk.X)

        editor_frame = tk.Frame(left, bg=BG)
        editor_frame.pack(fill=tk.BOTH, expand=True)

        # Números de línea
        self.line_num = tk.Text(editor_frame, width=4, bg=BG2, fg=MUTED,
                                font=FONT_MONO, state=tk.DISABLED,
                                relief=tk.FLAT, bd=0, padx=6, pady=6,
                                cursor="arrow")
        self.line_num.pack(side=tk.LEFT, fill=tk.Y)

        sep = tk.Frame(editor_frame, bg=BORDER, width=1)
        sep.pack(side=tk.LEFT, fill=tk.Y)

        self.editor = tk.Text(editor_frame, bg=BG, fg=TEXTO, insertbackground=TEXTO,
                              font=FONT_MONO, relief=tk.FLAT, bd=0,
                              padx=10, pady=6, undo=True, wrap=tk.NONE,
                              selectbackground=PANEL, selectforeground=TEXTO,
                              tabs="4c")
        self.editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll_y = tk.Scrollbar(editor_frame, command=self._scroll_editor, bg=BG2)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.editor.config(yscrollcommand=scroll_y.set)

        self.editor.bind("<KeyRelease>", self._actualizar_lineas)
        self.editor.bind("<MouseWheel>", self._sync_scroll)
        self.editor.bind("<Tab>", self._insertar_tab)
        self._actualizar_lineas()

        # Botones
        btn_frame = tk.Frame(left, bg=PANEL, pady=6)
        btn_frame.pack(fill=tk.X)

        self._btn(btn_frame, "▶  Compilar", self.compilar, ACCENT, BG).pack(side=tk.LEFT, padx=8)
        self._btn(btn_frame, "✕  Limpiar", self.limpiar, BORDER, TEXTO).pack(side=tk.LEFT)
        self._btn(btn_frame, "Cargar ejemplo", self.ejemplo, BG2, AZUL).pack(side=tk.RIGHT, padx=8)

        # Panel derecho — resultado
        right = tk.Frame(body, bg=BG)
        body.add(right, minsize=280)

        # Banner resultado
        self.banner = tk.Label(right, text="", bg=BG, fg=TEXTO,
                               font=("Segoe UI", 13, "bold"), pady=8)
        self.banner.pack(fill=tk.X)

        # Notebook
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TNotebook", background=PANEL, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=MUTED,
                        font=("Segoe UI", 9, "bold"), padding=[12, 6])
        style.map("TNotebook.Tab",
                  background=[("selected", BG)],
                  foreground=[("selected", ACCENT)])

        nb = ttk.Notebook(right)
        nb.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        # Tab Errores
        self.tab_err = tk.Frame(nb, bg=BG)
        nb.add(self.tab_err, text="Errores")
        self.txt_err = scrolledtext.ScrolledText(
            self.tab_err, bg=BG, fg=TEXTO, font=FONT_MONO,
            relief=tk.FLAT, bd=0, padx=10, pady=8, state=tk.DISABLED, wrap=tk.WORD)
        self.txt_err.pack(fill=tk.BOTH, expand=True)
        self.txt_err.tag_config("error_line", foreground=MUTED, font=("Consolas", 9))
        self.txt_err.tag_config("error_msg",  foreground=ROJO)
        self.txt_err.tag_config("ok",         foreground=VERDE)
        self.txt_err.tag_config("muted",      foreground=MUTED)

        # Tab Tokens
        self.tab_tok = tk.Frame(nb, bg=BG)
        nb.add(self.tab_tok, text="Tokens")
        self.txt_tok = scrolledtext.ScrolledText(
            self.tab_tok, bg=BG, fg=TEXTO, font=FONT_MONO,
            relief=tk.FLAT, bd=0, padx=10, pady=8, state=tk.DISABLED, wrap=tk.NONE)
        self.txt_tok.pack(fill=tk.BOTH, expand=True)
        self.txt_tok.tag_config("linea",  foreground=MUTED, font=("Consolas", 9))
        self.txt_tok.tag_config("tipo",   foreground=MUTED)
        self.txt_tok.tag_config("arrow",  foreground=BORDER)
        self.txt_tok.tag_config("kw",     foreground=ACCENT)
        self.txt_tok.tag_config("str",    foreground=VERDE)
        self.txt_tok.tag_config("num",    foreground=AMARILLO)
        self.txt_tok.tag_config("op",     foreground=AZUL)
        self.txt_tok.tag_config("id",     foreground=TEXTO)
        self.txt_tok.tag_config("punc",   foreground=MUTED)
        self.txt_tok.tag_config("unk",    foreground=ROJO)

        # Tab Variables
        self.tab_var = tk.Frame(nb, bg=BG)
        nb.add(self.tab_var, text="Variables")
        cols = ("Nombre", "Tipo", "Estado")
        self.tree = ttk.Treeview(self.tab_var, columns=cols, show="headings",
                                 style="Custom.Treeview")
        style.configure("Custom.Treeview",
                        background=BG, fieldbackground=BG, foreground=TEXTO,
                        rowheight=26, font=FONT_MONO, borderwidth=0)
        style.configure("Custom.Treeview.Heading",
                        background=PANEL, foreground=MUTED,
                        font=("Segoe UI", 9, "bold"), relief=tk.FLAT)
        style.map("Custom.Treeview", background=[("selected", PANEL)])
        for c in cols:
            self.tree.heading(c, text=c)
        self.tree.column("Nombre", width=130)
        self.tree.column("Tipo",   width=90, anchor="center")
        self.tree.column("Estado", width=130, anchor="center")
        self.tree.tag_configure("init",   foreground=VERDE)
        self.tree.tag_configure("no_init",foreground=AMARILLO)
        vsb = tk.Scrollbar(self.tab_var, command=self.tree.yview, bg=BG2)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.config(yscrollcommand=vsb.set)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Status bar
        self.status = tk.Label(self.root,
                               text="  Listo — escriba código Costeñol y presione Compilar",
                               bg=PANEL, fg=MUTED, font=("Segoe UI", 9),
                               anchor="w", pady=4)
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

    # ── HELPERS UI ───────────────────────────────────────────
    def _btn(self, parent, texto, cmd, bg, fg):
        return tk.Button(parent, text=texto, command=cmd,
                         bg=bg, fg=fg, font=FONT_BOLD,
                         relief=tk.FLAT, padx=14, pady=5,
                         activebackground=PANEL, activeforeground=TEXTO,
                         cursor="hand2", bd=0)

    def _scroll_editor(self, *args):
        self.editor.yview(*args)
        self.line_num.yview(*args)

    def _sync_scroll(self, event):
        self.line_num.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _insertar_tab(self, event):
        self.editor.insert(tk.INSERT, "  ")
        return "break"

    def _actualizar_lineas(self, event=None):
        contenido = self.editor.get("1.0", tk.END)
        n = contenido.count("\n")
        nums = "\n".join(str(i) for i in range(1, n + 1))
        self.line_num.config(state=tk.NORMAL)
        self.line_num.delete("1.0", tk.END)
        self.line_num.insert("1.0", nums)
        self.line_num.config(state=tk.DISABLED)

    def _texto_widget(self, widget, contenido_fn):
        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        contenido_fn(widget)
        widget.config(state=tk.DISABLED)

    # ── COMPILAR ─────────────────────────────────────────────
    def compilar(self):
        codigo = self.editor.get("1.0", tk.END).strip()
        if not codigo:
            return

        errores, all_tokens, variables = compilar_codigo(codigo)

        # Banner
        if errores:
            self.banner.config(text="✘  BARRO, CONOCES A YAPER?", bg=BG,
                               fg=ROJO)
            self.status.config(text=f"  {len(errores)} error(es) encontrado(s)")
        else:
            self.banner.config(text="✔  ¡MONO CUCO!", bg=BG, fg=VERDE)
            self.status.config(text="  Compilación exitosa — sin errores")

        # Tab Errores
        def mostrar_errores(w):
            if not errores:
                w.insert(tk.END, "✔ Sin errores — compilación exitosa.\n", "ok")
            else:
                for e in errores:
                    w.insert(tk.END, f"Línea {e['linea']}  ", "error_line")
                    w.insert(tk.END, e["msg"] + "\n", "error_msg")

        self._texto_widget(self.txt_err, mostrar_errores)

        # Tab Tokens
        TOKEN_TAG = {
            "TIPO_DATO": "kw", "CAPTURA": "kw", "MENSAJE": "kw",
            "CADENA": "str",
            "NUMERO_REAL": "num", "NUMERO_ENTERO": "num",
            "OPERADOR": "op",
            "PARENTESIS_AB": "punc", "PARENTESIS_CI": "punc", "PUNTO_COMA": "punc",
            "IDENTIFICADOR": "id",
            "DESCONOCIDO": "unk",
        }

        def mostrar_tokens(w):
            if not all_tokens:
                w.insert(tk.END, "Sin tokens.\n", "linea")
                return
            for bloque in all_tokens:
                w.insert(tk.END, f"── Línea {bloque['linea']} ──\n", "linea")
                for t in bloque["tokens"]:
                    tipo_str = f"  {t['tipo']:<16}"
                    w.insert(tk.END, tipo_str, "tipo")
                    w.insert(tk.END, "→  ", "arrow")
                    tag = TOKEN_TAG.get(t["tipo"], "id")
                    w.insert(tk.END, t["valor"] + "\n", tag)

        self._texto_widget(self.txt_tok, mostrar_tokens)

        # Tab Variables
        for row in self.tree.get_children():
            self.tree.delete(row)
        for nombre, info in variables.items():
            estado = "✔ Inicializada" if info["inicializada"] else "⚠ Sin valor"
            tag = "init" if info["inicializada"] else "no_init"
            self.tree.insert("", tk.END,
                             values=(nombre, info["tipo"], estado),
                             tags=(tag,))

    # ── LIMPIAR ──────────────────────────────────────────────
    def limpiar(self):
        self.editor.delete("1.0", tk.END)
        self._actualizar_lineas()
        self.banner.config(text="", bg=BG)
        self.status.config(text="  Listo")
        self._texto_widget(self.txt_err, lambda w: None)
        self._texto_widget(self.txt_tok, lambda w: None)
        for row in self.tree.get_children():
            self.tree.delete(row)

# ============================================================
#  MAIN
# ============================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = CompiladorApp(root)
    root.mainloop()