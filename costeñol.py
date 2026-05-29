import re
import queue
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox

# ============================================================
#  COMPILADOR COSTEÑOL — ENTREGA
# Jean Maldonado, Alex Díaz, Andrés Carrillo
# ============================================================

TOKEN_DEFS = [
    ("TIPO_DATO",      r"\b(Entero|Real|Texto|Logico)\b"),
    ("BOOLEANO",       r"\b(verdadero|falso)\b"),
    ("CAPTURA",        r"Captura\.(Texto|Entero|Real|Logico)\(\)"),
    ("MENSAJE",        r"Mensaje\.Texto"),
    ("CADENA",         r'"[^"]*"'),
    ("NUMERO_REAL",    r"\d+[.,]\d+"),
    ("NUMERO_ENTERO",  r"\d+"),
    ("OP_REL",         r"(==|!=|<=|>=|<|>)"),
    ("OP_LOG",         r"(\|\||&&|!)"),
    ("OPERADOR",       r"[+\-*/=]"),
    ("PARENTESIS_AB",  r"\("),
    ("PARENTESIS_CI",  r"\)"),
    ("COMA",           r","),
    ("PUNTO_COMA",     r";"),
    ("IDENTIFICADOR",  r"[a-zA-ZáéíóúÁÉÍÓÚñÑ_][a-zA-ZáéíóúÁÉÍÓÚñÑ0-9_]*"),
]

KEYWORDS_CORRECTOS = {"Entero", "Real", "Texto", "Logico", "Captura", "Mensaje"}
KEYWORDS_LOWER     = {k.lower() for k in KEYWORDS_CORRECTOS}

# ============================================================
#  ANÁLISIS LÉXICO
# ============================================================

def tokenizar(linea):
    tokens = []
    pos = 0
    while pos < len(linea):
        if linea[pos].isspace():
            pos += 1
            continue
        matched = False
        for nombre, patron in TOKEN_DEFS:
            m = re.match(patron, linea[pos:])
            if m:
                tokens.append({"tipo": nombre, "valor": m.group()})
                pos += len(m.group())
                matched = True
                break
        if not matched:
            tokens.append({"tipo": "DESCONOCIDO", "valor": linea[pos]})
            pos += 1
    return tokens

# ============================================================
#  ANÁLISIS SINTÁCTICO Y SEMÁNTICO
# ============================================================

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
            return f"Joa compadre, '{t['valor']}' no lo reconozco, eso no va ahí"
        if t["tipo"] == "IDENTIFICADOR":
            if t["valor"] not in variables:
                return f"Epa, '{t['valor']}' no existe, declárale primero"
    if len(tokens) == 1:
        t = tokens[0]
        if t["tipo"] == "BOOLEANO" and tipo_esperado != "Logico":
            return f"Uy no, eso es Logico y la variable es {tipo_esperado}, no mezcles eso compadre"
        if t["tipo"] == "CADENA" and tipo_esperado != "Texto":
            return f"Joa, eso es Texto y la variable es {tipo_esperado}, revisa bien"
        if t["tipo"] == "NUMERO_ENTERO" and tipo_esperado == "Texto":
            return f"Epa epa, no puedes meter un Entero en una variable Texto, piénsalo bien"
        if t["tipo"] == "NUMERO_REAL" and tipo_esperado == "Texto":
            return f"Joa, un Real no cabe en un Texto, eso está malo compadre"
        if t["tipo"] == "NUMERO_REAL" and tipo_esperado == "Entero":
            return f"Ombe, un Real no es un Entero, revisa eso que está malo"
    return None

def analizar_segmento(tokens, variables):
    tks = tokens[:-1] if tokens and tokens[-1]["tipo"] == "PUNTO_COMA" else tokens
    if not tks:
        return None
    if not tokens or tokens[-1]["tipo"] != "PUNTO_COMA":
        return "Se te olvidó el punto y coma al final, ponle el ';' ahí compadre"

    for t in tks:
        if t["tipo"] == "IDENTIFICADOR":
            val_lower = t["valor"].lower()
            if val_lower in KEYWORDS_LOWER and t["valor"] not in KEYWORDS_CORRECTOS:
                correcto = next(k for k in KEYWORDS_CORRECTOS if k.lower() == val_lower)
                return f"Revisa bien compadre, '{t['valor']}' se escribe es '{correcto}'"

    n = len(tks)

    # DECLARACIÓN: nombre TipoDato
    if n == 2 and tks[0]["tipo"] == "IDENTIFICADOR" and tks[1]["tipo"] == "TIPO_DATO":
        nombre = tks[0]["valor"]
        tipo   = tks[1]["valor"]
        if nombre in KEYWORDS_CORRECTOS:
            return f"Joa, '{nombre}' es una palabra reservada, búscate otro nombre"
        variables[nombre] = {"tipo": tipo, "inicializada": False, "valor": None}
        return None

    # CAPTURA: nombre = Captura.Tipo()
    if (n == 3
            and tks[0]["tipo"] == "IDENTIFICADOR"
            and tks[1]["tipo"] == "OPERADOR" and tks[1]["valor"] == "="
            and tks[2]["tipo"] == "CAPTURA"):
        nombre = tks[0]["valor"]
        m = re.match(r"Captura\.(Entero|Real|Texto|Logico)", tks[2]["valor"])
        tipo_captura = m.group(1) if m else None
        if nombre not in variables:
            return f"Ombe, '{nombre}' no está declarada, declárale primero compadre"
        if variables[nombre]["tipo"] != tipo_captura:
            return f"Epa compadre, '{nombre}' es {variables[nombre]['tipo']} pero lo estás capturando como {tipo_captura}, eso no funciona"
        variables[nombre]["inicializada"] = True
        return None

    # MENSAJE: Mensaje.Texto(elem1, elem2, ...);
    if tks[0]["tipo"] == "MENSAJE":
        if (n >= 4
                and tks[1]["tipo"] == "PARENTESIS_AB"
                and tks[-1]["tipo"] == "PARENTESIS_CI"):
            contenido = tks[2:-1]
            elementos, actual = [], []
            for t in contenido:
                if t["tipo"] == "COMA":
                    elementos.append(actual)
                    actual = []
                else:
                    actual.append(t)
            elementos.append(actual)
            for elem in elementos:
                if len(elem) == 0:
                    return "Joa, hay un elemento vacío en el Mensaje.Texto(), revisa esas comas"
                if len(elem) == 1:
                    t = elem[0]
                    if t["tipo"] == "CADENA":
                        continue
                    if t["tipo"] == "IDENTIFICADOR":
                        if t["valor"] not in variables:
                            return f"Epa, '{t['valor']}' no existe, declárale primero"
                        continue
                return "Ombe, en el Mensaje.Texto() solo van cadenas o variables, nada más"
            return None
        return 'Joa ese Mensaje.Texto() está malo, úsalo así: Mensaje.Texto("texto"); o Mensaje.Texto(variable); o Mensaje.Texto("texto", variable);'

    # ASIGNACIÓN: nombre = expresión
    if (n >= 3
            and tks[0]["tipo"] == "IDENTIFICADOR"
            and tks[1]["tipo"] == "OPERADOR" and tks[1]["valor"] == "="):
        nombre = tks[0]["valor"]
        if nombre not in variables:
            return f"Variable '{nombre}' no fue declarada"
        err = validar_expresion(tks[2:], variables, variables[nombre]["tipo"])
        if err:
            return err
        variables[nombre]["inicializada"] = True
        return None

    return f"Eso no lo entiendo compadre, revisa bien esa línea: '{' '.join(t['valor'] for t in tokens)}'"

def analizar_linea(tokens, variables):
    if not tokens:
        return None
    hay_desc = next((t for t in tokens if t["tipo"] == "DESCONOCIDO"), None)
    if hay_desc:
        return f"Joa, '{hay_desc['valor']}' no hace parte del Costeñol, quítalo de ahí"
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
    errores    = []
    all_tokens = []
    variables  = {}
    for n_linea, raw in enumerate(codigo.split("\n"), start=1):
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
#  EJECUCIÓN
# ============================================================

def evaluar_expresion_valor(tks, variables):
    partes = []
    for t in tks:
        if t["tipo"] == "BOOLEANO":
            partes.append("True" if t["valor"] == "verdadero" else "False")
        elif t["tipo"] == "NUMERO_REAL":
            partes.append(t["valor"].replace(",", "."))
        elif t["tipo"] == "NUMERO_ENTERO":
            partes.append(t["valor"])
        elif t["tipo"] == "CADENA":
            partes.append(t["valor"])
        elif t["tipo"] == "IDENTIFICADOR":
            val = variables.get(t["valor"], {}).get("valor")
            if isinstance(val, str):
                partes.append(f'"{val}"')
            elif val is None:
                partes.append("0")
            else:
                partes.append(str(val))
        elif t["tipo"] in ("OPERADOR", "PARENTESIS_AB", "PARENTESIS_CI"):
            partes.append(t["valor"])
        elif t["tipo"] == "OP_REL":
            partes.append(t["valor"])
        elif t["tipo"] == "OP_LOG":
            # Traducir && → and, || → or, ! → not
            op_map = {"&&": "and", "||": "or", "!": "not"}
            partes.append(op_map.get(t["valor"], t["valor"]))
    try:
        return eval(" ".join(partes))
    except Exception:
        return None

def ejecutar_segmento(tokens, variables, salida_fn, captura_fn):
    tks = tokens[:-1] if tokens and tokens[-1]["tipo"] == "PUNTO_COMA" else tokens
    if not tks:
        return
    n = len(tks)

    # DECLARACIÓN
    if n == 2 and tks[0]["tipo"] == "IDENTIFICADOR" and tks[1]["tipo"] == "TIPO_DATO":
        nombre = tks[0]["valor"]
        tipo   = tks[1]["valor"]
        if nombre not in variables:
            variables[nombre] = {"tipo": tipo, "inicializada": False, "valor": None}
        return

    # CAPTURA
    if (n == 3
            and tks[0]["tipo"] == "IDENTIFICADOR"
            and tks[1]["valor"] == "="
            and tks[2]["tipo"] == "CAPTURA"):
        nombre = tks[0]["valor"]
        m = re.match(r"Captura\.(Entero|Real|Texto|Logico)", tks[2]["valor"])
        tipo_captura = m.group(1) if m else "Texto"
        raw = captura_fn(nombre, tipo_captura)
        try:
            if tipo_captura == "Entero":
                valor = int(raw)
            elif tipo_captura == "Real":
                valor = float(raw.replace(",", "."))
            elif tipo_captura == "Logico":
                valor = raw.strip().lower() in ("true", "verdadero", "1", "si", "sí")
            else:
                valor = raw
        except Exception:
            valor = raw
        variables[nombre]["valor"]        = valor
        variables[nombre]["inicializada"] = True
        return

    # MENSAJE con concatenacion por coma
    if tks[0]["tipo"] == "MENSAJE" and tks[1]["tipo"] == "PARENTESIS_AB" and tks[-1]["tipo"] == "PARENTESIS_CI":
        contenido = tks[2:-1]
        elementos, actual = [], []
        for t in contenido:
            if t["tipo"] == "COMA":
                elementos.append(actual)
                actual = []
            else:
                actual.append(t)
        elementos.append(actual)
        partes = []
        for elem in elementos:
            if len(elem) == 1:
                t = elem[0]
                if t["tipo"] == "CADENA":
                    partes.append(t["valor"].strip('"'))
                elif t["tipo"] == "IDENTIFICADOR":
                    val = variables.get(t["valor"], {}).get("valor")
                    partes.append(str(val) if val is not None else "(sin valor)")
        salida_fn("".join(partes))
        return

    # ASIGNACIÓN
    if n >= 3 and tks[0]["tipo"] == "IDENTIFICADOR" and tks[1]["valor"] == "=":
        nombre    = tks[0]["valor"]
        resultado = evaluar_expresion_valor(tks[2:], variables)
        variables[nombre]["valor"]        = resultado
        variables[nombre]["inicializada"] = True
        return

def ejecutar_codigo(codigo, salida_fn, captura_fn):
    variables = {}
    for raw in codigo.split("\n"):
        linea = raw.strip()
        if not linea or linea.startswith("//"):
            continue
        tokens    = tokenizar(linea)
        segmentos = dividir_por_punto_coma(tokens)
        for seg in segmentos:
            if seg:
                ejecutar_segmento(seg, variables, salida_fn, captura_fn)
    return variables

# ============================================================
#  COLORES Y FUENTES
# ============================================================
BG       = "#1e1e2e"
BG2      = "#181825"
PANEL    = "#252538"
BORDER   = "#45475a"
ACCENT   = "#cba6f7"
VERDE    = "#a6e3a1"
ROJO     = "#f38ba8"
AMARILLO = "#f9e2af"
TEXTO    = "#cdd6f4"
MUTED    = "#6c7086"
AZUL     = "#89b4fa"

FONT_MONO = ("Consolas", 11)
FONT_BOLD = ("Segoe UI", 10, "bold")

# ============================================================
#  INTERFAZ GRÁFICA
# ============================================================

class CompiladorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Compilador Costeñol — Entrega ")
        self.root.configure(bg=BG)
        self.root.geometry("1100x680")
        self.root.minsize(800, 500)

        self._q_pedido   = queue.Queue()
        self._q_respuesta = queue.Queue()

        self._construir_ui()

    # ── CONSTRUCCIÓN DE LA VENTANA ───────────────────────────
    def _construir_ui(self):

        # HEADER
        hdr = tk.Frame(self.root, bg=PANEL, height=48)
        hdr.pack(fill=tk.X, side=tk.TOP)
        hdr.pack_propagate(False)
        tk.Label(hdr, text=" CUL ", bg=ACCENT, fg=BG,
                 font=("Segoe UI", 11, "bold"), padx=6).pack(side=tk.LEFT, padx=12, pady=10)
        tk.Label(hdr, text="Compilador Costeñol", bg=PANEL, fg=TEXTO,
                 font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, pady=10)
        tk.Label(hdr, text="Entrega", bg=VERDE, fg=BG,
                 font=("Segoe UI", 9, "bold"), padx=8).pack(side=tk.RIGHT, padx=12, pady=14)

        # CUERPO
        body = tk.PanedWindow(self.root, orient=tk.HORIZONTAL,
                              bg=BORDER, sashwidth=3, sashrelief=tk.FLAT)
        body.pack(fill=tk.BOTH, expand=True)

        # ── IZQUIERDA: editor ────────────────────────────────
        left = tk.Frame(body, bg=BG)
        body.add(left, minsize=300, width=500)

        tk.Label(left, text="  Editor de código  (.PQEK)", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9), anchor="w").pack(fill=tk.X)

        ef = tk.Frame(left, bg=BG)
        ef.pack(fill=tk.BOTH, expand=True)

        self.line_num = tk.Text(ef, width=4, bg=BG2, fg=MUTED,
                                font=FONT_MONO, state=tk.DISABLED,
                                relief=tk.FLAT, bd=0, padx=6, pady=6, cursor="arrow")
        self.line_num.pack(side=tk.LEFT, fill=tk.Y)
        tk.Frame(ef, bg=BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y)

        self.editor = tk.Text(ef, bg=BG, fg=TEXTO, insertbackground=TEXTO,
                              font=FONT_MONO, relief=tk.FLAT, bd=0,
                              padx=10, pady=6, undo=True, wrap=tk.NONE,
                              selectbackground=PANEL, selectforeground=TEXTO)
        self.editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sy = tk.Scrollbar(ef, command=self._scroll_editor, bg=BG2)
        sy.pack(side=tk.RIGHT, fill=tk.Y)
        self.editor.config(yscrollcommand=sy.set)

        self.editor.bind("<KeyRelease>", self._actualizar_lineas)
        self.editor.bind("<MouseWheel>", self._sync_scroll)
        self.editor.bind("<Tab>",        self._insertar_tab)
        self._actualizar_lineas()

        # Botones
        bf = tk.Frame(left, bg=PANEL, pady=6)
        bf.pack(fill=tk.X)
        self._btn(bf, "▶  Compila pa' ve si sabes", self.compilar, ACCENT, BG   ).pack(side=tk.LEFT, padx=8)
        self._btn(bf, "✕  Limpiar",             self.limpiar,  BORDER, TEXTO).pack(side=tk.LEFT)
        self._btn(bf, "💾  Guardalo pue' .PQEK",       self.guardar,  BG2,    AZUL ).pack(side=tk.RIGHT, padx=8)

        # ── DERECHA: resultados ──────────────────────────────
        right = tk.Frame(body, bg=BG)
        body.add(right, minsize=300)

        self.banner = tk.Label(right, text="", bg=BG, fg=TEXTO,
                               font=("Segoe UI", 13, "bold"), pady=6)
        self.banner.pack(fill=tk.X)

        # Panel de captura
        self.frame_input = tk.Frame(right, bg=PANEL, pady=8, padx=12)
        self.lbl_input   = tk.Label(self.frame_input, text="", bg=PANEL, fg=AMARILLO,
                                    font=("Segoe UI", 10, "bold"), anchor="w")
        self.lbl_input.pack(fill=tk.X, pady=(0, 4))

        fila = tk.Frame(self.frame_input, bg=PANEL)
        fila.pack(fill=tk.X)

        self.entry_input = tk.Entry(fila, bg=BG2, fg=TEXTO, insertbackground=TEXTO,
                                    font=FONT_MONO, relief=tk.FLAT, bd=0)
        self.entry_input.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 8))
        self._btn(fila, "Ingresar", self._confirmar_entrada, VERDE, BG).pack(side=tk.LEFT)
        self.entry_input.bind("<Return>", lambda e: self._confirmar_entrada())
        self.frame_input.pack_forget()

        # Pestañas
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TNotebook",     background=PANEL, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=MUTED,
                        font=("Segoe UI", 9, "bold"), padding=[12, 6])
        style.map("TNotebook.Tab",
                  background=[("selected", BG)],
                  foreground=[("selected", ACCENT)])

        self.nb = ttk.Notebook(right)
        self.nb.pack(fill=tk.BOTH, expand=True)

        # Pestaña Salida
        tab_sal = tk.Frame(self.nb, bg=BG)
        self.nb.add(tab_sal, text="Salida")
        self.txt_sal = scrolledtext.ScrolledText(
            tab_sal, bg=BG, fg=TEXTO, font=FONT_MONO,
            relief=tk.FLAT, bd=0, padx=10, pady=8, state=tk.DISABLED, wrap=tk.WORD)
        self.txt_sal.pack(fill=tk.BOTH, expand=True)
        self.txt_sal.tag_config("out",     foreground=VERDE)
        self.txt_sal.tag_config("info",    foreground=MUTED)
        self.txt_sal.tag_config("captura", foreground=AMARILLO)
        self.txt_sal.tag_config("error",   foreground=ROJO)

        # Pestaña Errores
        tab_err = tk.Frame(self.nb, bg=BG)
        self.nb.add(tab_err, text="Errores")
        self.txt_err = scrolledtext.ScrolledText(
            tab_err, bg=BG, fg=TEXTO, font=FONT_MONO,
            relief=tk.FLAT, bd=0, padx=10, pady=8, state=tk.DISABLED, wrap=tk.WORD)
        self.txt_err.pack(fill=tk.BOTH, expand=True)
        self.txt_err.tag_config("num",  foreground=AZUL,  font=("Consolas", 11, "bold"))
        self.txt_err.tag_config("sep",  foreground=BORDER)
        self.txt_err.tag_config("msg",  foreground=ROJO)
        self.txt_err.tag_config("ok",   foreground=VERDE)
        self.txt_err.tag_config("hint", foreground=MUTED, font=("Consolas", 9))

        # Pestaña Tokens
        tab_tok = tk.Frame(self.nb, bg=BG)
        self.nb.add(tab_tok, text="Tokens")
        self.txt_tok = scrolledtext.ScrolledText(
            tab_tok, bg=BG, fg=TEXTO, font=FONT_MONO,
            relief=tk.FLAT, bd=0, padx=10, pady=8, state=tk.DISABLED, wrap=tk.NONE)
        self.txt_tok.pack(fill=tk.BOTH, expand=True)
        self.txt_tok.tag_config("linea", foreground=MUTED, font=("Consolas", 9))
        self.txt_tok.tag_config("tipo",  foreground=MUTED)
        self.txt_tok.tag_config("arrow", foreground=BORDER)
        self.txt_tok.tag_config("kw",    foreground=ACCENT)
        self.txt_tok.tag_config("str",   foreground=VERDE)
        self.txt_tok.tag_config("num",   foreground=AMARILLO)
        self.txt_tok.tag_config("op",    foreground=AZUL)
        self.txt_tok.tag_config("id",    foreground=TEXTO)
        self.txt_tok.tag_config("punc",  foreground=MUTED)
        self.txt_tok.tag_config("bool",  foreground=ROJO)
        self.txt_tok.tag_config("unk",   foreground=ROJO)

        # Pestaña Variables
        tab_var = tk.Frame(self.nb, bg=BG)
        self.nb.add(tab_var, text="Variables")
        cols = ("Nombre", "Tipo", "Valor", "Estado")
        self.tree = ttk.Treeview(tab_var, columns=cols, show="headings",
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
        self.tree.column("Nombre", width=110)
        self.tree.column("Tipo",   width=80,  anchor="center")
        self.tree.column("Valor",  width=110, anchor="center")
        self.tree.column("Estado", width=120, anchor="center")
        self.tree.tag_configure("init",    foreground=VERDE)
        self.tree.tag_configure("no_init", foreground=AMARILLO)
        vsb = tk.Scrollbar(tab_var, command=self.tree.yview, bg=BG2)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.config(yscrollcommand=vsb.set)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Barra de estado
        self.status = tk.Label(self.root,
                               text="  Escribe el codigo pa' ver si es verdad que sabes",
                               bg=PANEL, fg=MUTED, font=("Segoe UI", 9), anchor="w", pady=4)
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

    # ── HELPERS UI ───────────────────────────────────────────
    def _btn(self, parent, texto, cmd, bg, fg):
        return tk.Button(parent, text=texto, command=cmd,
                         bg=bg, fg=fg, font=FONT_BOLD,
                         relief=tk.FLAT, padx=12, pady=5,
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
        n    = contenido.count("\n")
        nums = "\n".join(str(i) for i in range(1, n + 1))
        self.line_num.config(state=tk.NORMAL)
        self.line_num.delete("1.0", tk.END)
        self.line_num.insert("1.0", nums)
        self.line_num.config(state=tk.DISABLED)

    def _escribir(self, widget, fn):
        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        fn(widget)
        widget.config(state=tk.DISABLED)

    def _append(self, widget, texto, tag=""):
        widget.config(state=tk.NORMAL)
        widget.insert(tk.END, texto, tag)
        widget.config(state=tk.DISABLED)
        widget.see(tk.END)

    # ── PANEL DE CAPTURA ─────────────────────────────────────
    def _mostrar_panel_captura(self, nombre, tipo):
        self.lbl_input.config(text=f"  Ingrese valor para '{nombre}'  (tipo: {tipo})")
        self.entry_input.delete(0, tk.END)
        self.frame_input.pack(fill=tk.X, before=self.nb)
        self.entry_input.focus_set()

    def _ocultar_panel_captura(self):
        self.frame_input.pack_forget()

    def _confirmar_entrada(self):
        valor = self.entry_input.get()
        self._ocultar_panel_captura()
        self._append(self.txt_sal, f"  → Valor ingresado: {valor}\n", "captura")
        self._q_respuesta.put(valor)

    # ── POLL ─────────────────────────────────────────────────
    def _poll_pedidos(self):
        try:
            msg = self._q_pedido.get_nowait()
        except queue.Empty:
            self.root.after(50, self._poll_pedidos)
            return

        if msg[0] == "CAPTURA":
            _, nombre, tipo = msg
            self._append(self.txt_sal,
                         f"Captura requerida → '{nombre}' ({tipo}):\n", "info")
            self._mostrar_panel_captura(nombre, tipo)
            self._esperar_confirmacion()
        elif msg[0] == "SALIDA":
            _, texto = msg
            self._append(self.txt_sal, texto + "\n", "out")
            self.root.after(50, self._poll_pedidos)
        elif msg[0] == "FIN":
            _, variables_ejec = msg
            self._append(self.txt_sal, "\n── Ejecución finalizada ──\n", "info")
            self.status.config(text="  Ejecución completada")
            for row in self.tree.get_children():
                self.tree.delete(row)
            for nombre, info in variables_ejec.items():
                estado = "✔ Inicializada" if info["inicializada"] else " Sin valor"
                valor  = str(info["valor"]) if info["valor"] is not None else "—"
                tag    = "init" if info["inicializada"] else "no_init"
                self.tree.insert("", tk.END,
                                 values=(nombre, info["tipo"], valor, estado),
                                 tags=(tag,))

    def _esperar_confirmacion(self):
        # Revisa si el panel de captura ya fue ocultado (el usuario confirmó)
        if not self.frame_input.winfo_ismapped():
            self.root.after(50, self._poll_pedidos)
        else:
            self.root.after(100, self._esperar_confirmacion)

    # ── COMPILAR Y EJECUTAR ──────────────────────────────────
    def compilar(self):
        codigo = self.editor.get("1.0", tk.END).strip()
        if not codigo:
            return

        errores, all_tokens, _ = compilar_codigo(codigo)

        if errores:
            self.banner.config(text="✘  BARRO, TE TOCÓ PERDER", fg=ROJO)
            self.status.config(
                text=f"  {len(errores)} error(es) encontrado(s) — corrija eso cuadro")
        else:
            self.banner.config(text="✔  ¡MONO CUCO!", fg=VERDE)
            self.status.config(text="  Sin errores — todo mono")

        # Pestaña Errores
        def mostrar_errores(w):
            if not errores:
                w.insert(tk.END, " Sin errores — funciona todo bien.\n\n", "ok")
                w.insert(tk.END,
                    "Todas las variables están correctamente declaradas\n"
                    "y la sintaxis es válida. Procediendo a ejecución.\n", "hint")
            else:
                w.insert(tk.END, f"Se encontraron {len(errores)} error(es):\n\n", "hint")
                for e in errores:
                    w.insert(tk.END, "  Línea ", "hint")
                    w.insert(tk.END, str(e["linea"]), "num")
                    w.insert(tk.END, "  │  ", "sep")
                    w.insert(tk.END, e["msg"] + "\n", "msg")
                w.insert(tk.END,
                    "\nCorrige los errores marcados y vuelve a compilar.\n", "hint")
        self._escribir(self.txt_err, mostrar_errores)

        # Pestaña Tokens
        TOKEN_TAG = {
            "TIPO_DATO": "kw", "CAPTURA": "kw", "MENSAJE": "kw",
            "BOOLEANO": "bool",
            "CADENA": "str", "NUMERO_REAL": "num", "NUMERO_ENTERO": "num",
            "OPERADOR": "op", "OP_REL": "op", "OP_LOG": "op",
            "PARENTESIS_AB": "punc", "PARENTESIS_CI": "punc", "PUNTO_COMA": "punc",
            "IDENTIFICADOR": "id", "DESCONOCIDO": "unk",
        }
        def mostrar_tokens(w):
            for bloque in all_tokens:
                w.insert(tk.END, f"── Línea {bloque['linea']} ──\n", "linea")
                for t in bloque["tokens"]:
                    w.insert(tk.END, f"  {t['tipo']:<18}", "tipo")
                    w.insert(tk.END, "→  ", "arrow")
                    w.insert(tk.END, t["valor"] + "\n", TOKEN_TAG.get(t["tipo"], "id"))
        self._escribir(self.txt_tok, mostrar_tokens)

        if errores:
            self._escribir(self.txt_sal,
                lambda w: w.insert(tk.END,
                    "⚠  No se ejecutó.\n"
                    "Corrija los errores en la pestaña Errores.\n", "error"))
            self.nb.select(1)
            return

        # FASE 2: ejecución en hilo separado
        self._escribir(self.txt_sal, lambda w: None)
        self._append(self.txt_sal,
            "── Variables verificadas ✔  Sintaxis válida ✔ ──\n"
            "── Iniciando ejecución ──\n\n", "info")
        self.nb.select(0)

        q_pedido    = self._q_pedido
        q_respuesta = self._q_respuesta

        def salida_fn(texto):
            q_pedido.put(("SALIDA", texto))

        def captura_fn(nombre, tipo):
            q_pedido.put(("CAPTURA", nombre, tipo))
            return q_respuesta.get(block=True)

        def hilo_ejec():
            variables_ejec = ejecutar_codigo(codigo, salida_fn, captura_fn)
            q_pedido.put(("FIN", variables_ejec))

        threading.Thread(target=hilo_ejec, daemon=True).start()
        self.root.after(50, self._poll_pedidos)

    # ── LIMPIAR ──────────────────────────────────────────────
    def limpiar(self):
        self.editor.delete("1.0", tk.END)
        self._actualizar_lineas()
        self.banner.config(text="")
        self.status.config(text="  Listo")
        self._ocultar_panel_captura()
        self._escribir(self.txt_sal, lambda w: None)
        self._escribir(self.txt_err, lambda w: None)
        self._escribir(self.txt_tok, lambda w: None)
        for row in self.tree.get_children():
            self.tree.delete(row)

    # ── GUARDAR .PQEK ────────────────────────────────────────
    def guardar(self):
        codigo = self.editor.get("1.0", tk.END).rstrip("\n")
        if not codigo.strip():
            messagebox.showwarning("Guardar", "El editor está vacío.", parent=self.root)
            return
        ruta = filedialog.asksaveasfilename(
            title="Guardar archivo Costeñol",
            defaultextension=".PQEK",
            filetypes=[("Archivo Costeñol", "*.PQEK"), ("Todos los archivos", "*.*")],
            parent=self.root
        )
        if ruta:
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(codigo)
            self.status.config(text=f"  Guardado: {ruta}")

# ============================================================
#  MAIN
# ============================================================
if __name__ == "__main__":
    root = tk.Tk()
    app  = CompiladorApp(root)
    root.mainloop()