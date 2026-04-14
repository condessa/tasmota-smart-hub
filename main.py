import tkinter as tk
from tkinter import ttk, messagebox
import paho.mqtt.client as mqtt
import json
import threading
import os
import datetime
from PIL import Image, ImageDraw, ImageTk

CONFIG_FILE = "tasmota_mqtt_config.json"

# ─────────────────────────────────────────────
#  Paleta AluminioManager / HCsoftware
# ─────────────────────────────────────────────
BG_MAIN    = "#2b2b2b"   # fundo principal
BG_PANEL   = "#3c3c3c"   # painéis / hover
BG_CARD    = "#444444"   # cards / frames internos
BG_TOPBAR  = "#1e1e1e"   # topbar / cabeçalhos de tabela
BG_SIDEBAR = "#252525"   # sidebar
BG_INPUT   = "#3a3a3a"   # inputs

ACCENT     = "#4a90d9"   # azul HCsoftware — botão Conectar
ACCENT_HOV = "#5ba3f0"
ACCENT_DRK = "#357abd"

TEXT_PRI   = "#e8e8e8"
TEXT_SEC   = "#a0a0a0"
TEXT_MUT   = "#6e6e6e"

SUCCESS    = "#5cb85c"
DANGER     = "#d9534f"
WARNING    = "#f0ad4e"
INFO       = "#5bc0de"

GREEN      = "#00ff7f"
RED        = "#ff4444"
YELLOW     = "#FFD700"

BORDER     = "#555555"
DIVIDER    = "#404040"

LOG_BG     = "#0d1117"
LOG_SENT   = "#d29922"
LOG_RECV   = "#3fb950"

RULE_BG    = "#1e2a1e"
RULE_DIS   = "#2a1a1a"

# ─────────────────────────────────────────────
#  Cores dos botões da toolbar
#  (edita aqui para mudar o aspeto dos botões)
# ─────────────────────────────────────────────

# ⚙ Broker MQTT — verde-azulado suave
BTN_TEAL_BG  = "#2a4a4a"
BTN_TEAL_FG  = "#7ecaca"
BTN_TEAL_HOV = "#335555"
BTN_TEAL_AFG = "#9adada"

# 📋 Log MQTT — olive/âmbar suave
BTN_OLIVE_BG  = "#3a3a1e"
BTN_OLIVE_FG  = "#b8b06a"
BTN_OLIVE_HOV = "#484828"
BTN_OLIVE_AFG = "#d4cc88"


# ─────────────────────────────────────────────
#  Logo HCsoftware
# ─────────────────────────────────────────────
def _load_logo(height=28):
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, "imagens", "HCsoftware.png")
    try:
        img   = Image.open(path).convert("RGBA")
        ratio = height / img.height
        new_w = max(1, int(img.width * ratio))
        img   = img.resize((new_w, height), Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception as e:
        print(f"[logo] Não foi possível carregar {path}: {e}")
        return None


class TasmotaSmartHub:
    def __init__(self, root):
        self.root = root
        self.root.title("Tasmota Smart Hub — HCsoftware")
        self.root.geometry("1300x760")
        self.root.minsize(1050, 640)
        self.root.configure(bg=BG_MAIN)

        self.devices   = {}
        self.config    = self.load_config()
        self.client    = None
        self.log_open  = False

        self.rules_data = {}
        self._rule_vars = {}

        self._build_leds()
        self._build_styles()
        self._build_ui()

        if self.config:
            self.start_mqtt()

    # ──────────────────────────────────────────
    #  LEDs
    # ──────────────────────────────────────────
    def _build_leds(self):
        def led(color):
            img = Image.new("RGBA", (14, 14), (0, 0, 0, 0))
            ImageDraw.Draw(img).ellipse([1, 1, 13, 13], fill=color, outline=color)
            return ImageTk.PhotoImage(img)
        self.led_on   = led(GREEN)
        self.led_off  = led(RED)
        self.led_idle = led("#555555")

    # ──────────────────────────────────────────
    #  Estilos ttk
    # ──────────────────────────────────────────
    def _build_styles(self):
        s = ttk.Style()
        s.theme_use('clam')

        # Treeview — estilo AluminioManager
        s.configure("AM.Treeview",
                    background=BG_CARD,
                    foreground=TEXT_PRI,
                    fieldbackground=BG_CARD,
                    rowheight=34,
                    font=('Segoe UI', 10),
                    borderwidth=0,
                    relief="flat")
        s.map("AM.Treeview",
              background=[('selected', ACCENT_DRK)],
              foreground=[('selected', TEXT_PRI)])
        s.configure("AM.Treeview.Heading",
                    background=BG_TOPBAR,
                    foreground=TEXT_SEC,
                    relief="flat",
                    font=('Segoe UI', 9, 'bold'))
        s.map("AM.Treeview.Heading",
              background=[('active', BG_PANEL)])

        # Scrollbar fina
        s.configure("AM.Vertical.TScrollbar",
                    background=BG_PANEL,
                    troughcolor=BG_CARD,
                    bordercolor=BG_CARD,
                    arrowcolor=TEXT_MUT,
                    width=8)

    # ──────────────────────────────────────────
    #  Interface principal
    # ──────────────────────────────────────────
    def _build_ui(self):
        # ══ TOPBAR ══════════════════════════════
        topbar = tk.Frame(self.root, bg=BG_TOPBAR, height=52)
        topbar.pack(fill=tk.X)
        topbar.pack_propagate(False)

        inner_top = tk.Frame(topbar, bg=BG_TOPBAR)
        inner_top.pack(fill=tk.BOTH, expand=True, padx=16)

        # Logo + título
        left_top = tk.Frame(inner_top, bg=BG_TOPBAR)
        left_top.pack(side=tk.LEFT, fill=tk.Y)

        self._brand_img = _load_logo(height=28)
        if self._brand_img:
            tk.Label(left_top, text="by", bg=BG_TOPBAR, fg=TEXT_MUT,
                     font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 4), pady=12)
            tk.Label(left_top, image=self._brand_img,
                     bg=BG_TOPBAR).pack(side=tk.LEFT, padx=(0, 10), pady=12)

        tk.Label(left_top, text="Tasmota Smart Hub",
                 font=("Segoe UI", 16, "bold"),
                 bg=BG_TOPBAR, fg=ACCENT).pack(side=tk.LEFT, pady=12)

        # Separador vertical
        tk.Frame(inner_top, bg=BORDER, width=1).pack(
            side=tk.LEFT, fill=tk.Y, padx=14, pady=10)

        tk.Label(inner_top, text="Gestão de Dispositivos IoT",
                 font=("Segoe UI", 10),
                 bg=BG_TOPBAR, fg=TEXT_SEC).pack(side=tk.LEFT, pady=12)

        # Status à direita
        right_top = tk.Frame(inner_top, bg=BG_TOPBAR)
        right_top.pack(side=tk.RIGHT, fill=tk.Y)

        self.lbl_status = tk.Label(right_top,
                                   text="● Desconectado",
                                   fg=DANGER, bg=BG_TOPBAR,
                                   font=("Segoe UI", 10, "bold"))
        self.lbl_status.pack(side=tk.RIGHT, pady=12, padx=(8, 0))

        # Separador horizontal sob topbar
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill=tk.X)

        # ══ TOOLBAR ═════════════════════════════
        toolbar = tk.Frame(self.root, bg=BG_TOPBAR, pady=7, padx=14)
        toolbar.pack(fill=tk.X)

        self._tb_btn(toolbar, "⚙  Broker MQTT",  self.open_config_window, style="teal").pack(side=tk.LEFT, padx=(0, 6))
        self._tb_btn(toolbar, "⚡  Conectar",     self.start_mqtt,          style="pri").pack(side=tk.LEFT, padx=(0, 6))

        tk.Frame(toolbar, bg=BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y, pady=4, padx=6)

        self._tb_btn(toolbar, "📋  Log MQTT",     self.toggle_log,          style="olive").pack(side=tk.LEFT, padx=(0, 6))

        # Separador horizontal
        tk.Frame(self.root, bg=DIVIDER, height=1).pack(fill=tk.X)

        # ══ CORPO ═══════════════════════════════
        body = tk.Frame(self.root, bg=BG_MAIN)
        body.pack(fill=tk.BOTH, expand=True)

        # ── Tabela de dispositivos (esquerda) ──
        left = tk.Frame(body, bg=BG_MAIN)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(14, 6), pady=12)

        # Cabeçalho da secção
        sec_hdr = tk.Frame(left, bg=BG_MAIN)
        sec_hdr.pack(fill=tk.X, pady=(0, 6))
        tk.Label(sec_hdr, text="DISPOSITIVOS ONLINE",
                 font=("Segoe UI", 8, "bold"),
                 bg=BG_MAIN, fg=TEXT_MUT).pack(side=tk.LEFT)

        # Frame da tabela com borda
        tree_frame = tk.Frame(left, bg=BORDER, bd=1, relief="flat")
        tree_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("ID", "Estado", "Conexão", "Atualizado")
        self.tree = ttk.Treeview(tree_frame, columns=cols,
                                  show='tree headings',
                                  style="AM.Treeview")
        self.tree.heading("#0",         text="",           anchor="center")
        self.tree.heading("ID",         text="Dispositivo",anchor="w")
        self.tree.heading("Estado",     text="Estado",     anchor="center")
        self.tree.heading("Conexão",    text="Conexão",    anchor="center")
        self.tree.heading("Atualizado", text="Atualizado", anchor="center")
        self.tree.column("#0",         width=36,  anchor="center", stretch=False)
        self.tree.column("ID",         width=200, anchor="w")
        self.tree.column("Estado",     width=100, anchor="center")
        self.tree.column("Conexão",    width=100, anchor="center")
        self.tree.column("Atualizado", width=120, anchor="center")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",
                             command=self.tree.yview,
                             style="AM.Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Tags de linha para colorir estado
        self.tree.tag_configure("row_on",      background=BG_CARD)
        self.tree.tag_configure("row_off",     background=BG_CARD)
        self.tree.tag_configure("row_offline", background="#2e2e2e", foreground=TEXT_MUT)

        self.tree.bind("<ButtonRelease-1>", self._on_select)
        self.tree.bind("<Double-1>",        self.on_double_click)

        # ── Painel direito ──
        right_outer = tk.Frame(body, bg=BG_MAIN, width=340)
        right_outer.pack(side=tk.RIGHT, fill=tk.Y,
                         padx=(0, 14), pady=12)
        right_outer.pack_propagate(False)
        self._build_right_panel(right_outer)

        # ══ LOG MQTT (recolhível) ════════════════
        self.log_frame = tk.Frame(self.root, bg=LOG_BG, height=160)
        self.log_frame.pack_propagate(False)
        # não faz pack aqui — é controlado pelo toggle_log

        log_hdr = tk.Frame(self.log_frame, bg=BG_TOPBAR)
        log_hdr.pack(fill=tk.X)
        tk.Label(log_hdr, text="  LOG MQTT",
                 font=("Segoe UI", 8, "bold"),
                 bg=BG_TOPBAR, fg=TEXT_MUT,
                 pady=5).pack(side=tk.LEFT)
        tk.Button(log_hdr, text="limpar",
                  command=self._clear_log,
                  bg=BG_TOPBAR, fg=TEXT_MUT,
                  bd=0, cursor="hand2",
                  font=("Segoe UI", 8),
                  activebackground=BG_TOPBAR,
                  activeforeground=TEXT_SEC).pack(side=tk.RIGHT, padx=8)

        self.log_text = tk.Text(self.log_frame,
                                 bg=LOG_BG, fg=LOG_RECV,
                                 font=("Monospace", 9),
                                 bd=0, wrap=tk.NONE,
                                 state=tk.DISABLED,
                                 insertbackground=TEXT_PRI)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=(2, 6))
        self.log_text.tag_config("sent", foreground=LOG_SENT)
        self.log_text.tag_config("recv", foreground=LOG_RECV)

        # ══ RODAPÉ ══════════════════════════════
        self._foot_frame = tk.Frame(self.root, bg=BG_TOPBAR, padx=14, pady=5)
        self._foot_frame.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Frame(self._foot_frame, bg=BORDER, height=1).pack(fill=tk.X, side=tk.TOP)
        tk.Label(self._foot_frame,
                 text="Clique para selecionar  ·  Duplo clique = TOGGLE  (porta → Power2 ON)",
                 bg=BG_TOPBAR, fg=TEXT_MUT,
                 font=("Segoe UI", 8, "italic")).pack(side=tk.LEFT)



    # ──────────────────────────────────────────
    #  Helper: botão toolbar
    # ──────────────────────────────────────────
    def _tb_btn(self, parent, text, cmd, style="sec"):
        if style == "pri":
            return tk.Button(parent, text=text, command=cmd,
                             bg=ACCENT, fg="#ffffff",
                             bd=0, padx=14, pady=5,
                             font=("Segoe UI", 9, "bold"),
                             cursor="hand2",
                             activebackground=ACCENT_HOV,
                             activeforeground="#ffffff",
                             relief="flat")
        elif style == "teal":
            # Broker MQTT — verde-azulado suave
            return tk.Button(parent, text=text, command=cmd,
                             bg=BTN_TEAL_BG, fg=BTN_TEAL_FG,
                             bd=0, padx=12, pady=5,
                             font=("Segoe UI", 9),
                             cursor="hand2",
                             activebackground=BTN_TEAL_HOV,
                             activeforeground=BTN_TEAL_AFG,
                             relief="flat")
        elif style == "olive":
            # Log MQTT — âmbar/olive suave
            return tk.Button(parent, text=text, command=cmd,
                             bg=BTN_OLIVE_BG, fg=BTN_OLIVE_FG,
                             bd=0, padx=12, pady=5,
                             font=("Segoe UI", 9),
                             cursor="hand2",
                             activebackground=BTN_OLIVE_HOV,
                             activeforeground=BTN_OLIVE_AFG,
                             relief="flat")
        else:
            return tk.Button(parent, text=text, command=cmd,
                             bg=BG_PANEL, fg=TEXT_SEC,
                             bd=1, padx=12, pady=4,
                             font=("Segoe UI", 9),
                             cursor="hand2",
                             activebackground=BG_CARD,
                             activeforeground=TEXT_PRI,
                             relief="flat",
                             highlightthickness=1,
                             highlightbackground=BORDER)

    # ──────────────────────────────────────────
    #  Painel direito com abas
    # ──────────────────────────────────────────
    def _build_right_panel(self, parent):
        # Card do dispositivo selecionado
        dev_card = tk.Frame(parent, bg=BG_CARD,
                             highlightthickness=1,
                             highlightbackground=BORDER)
        dev_card.pack(fill=tk.X, pady=(0, 8))

        dev_hdr = tk.Frame(dev_card, bg=BG_TOPBAR)
        dev_hdr.pack(fill=tk.X)
        tk.Label(dev_hdr, text="DISPOSITIVO SELECIONADO",
                 font=("Segoe UI", 8, "bold"),
                 bg=BG_TOPBAR, fg=TEXT_MUT,
                 padx=10, pady=6).pack(side=tk.LEFT)

        dev_body = tk.Frame(dev_card, bg=BG_CARD, padx=10, pady=6)
        dev_body.pack(fill=tk.X)
        tk.Label(dev_body, text="ID:", bg=BG_CARD, fg=TEXT_MUT,
                 font=("Segoe UI", 8)).pack(side=tk.LEFT)
        self.lbl_selected = tk.Label(dev_body, text="— nenhum —",
                                      bg=BG_CARD, fg=ACCENT,
                                      font=("Segoe UI", 10, "bold"))
        self.lbl_selected.pack(side=tk.LEFT, padx=6)

        # Barra de abas
        tab_bar = tk.Frame(parent, bg=BG_TOPBAR,
                            highlightthickness=1,
                            highlightbackground=BORDER)
        tab_bar.pack(fill=tk.X, pady=(0, 0))

        self._tab_cmds  = tk.Frame(parent, bg=BG_MAIN)
        self._tab_rules = tk.Frame(parent, bg=BG_MAIN)

        self._btn_tab_cmds = tk.Button(
            tab_bar, text="⚡  Comandos",
            bg=ACCENT, fg="#ffffff",
            bd=0, padx=14, pady=6,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            relief="flat",
            activebackground=ACCENT_HOV,
            activeforeground="#ffffff",
            command=lambda: self._switch_tab("cmds"))
        self._btn_tab_cmds.pack(side=tk.LEFT)

        self._btn_tab_rules = tk.Button(
            tab_bar, text="📜  Rules",
            bg=BG_TOPBAR, fg=TEXT_MUT,
            bd=0, padx=14, pady=6,
            font=("Segoe UI", 9),
            cursor="hand2",
            relief="flat",
            activebackground=BG_PANEL,
            activeforeground=TEXT_PRI,
            command=lambda: self._switch_tab("rules"))
        self._btn_tab_rules.pack(side=tk.LEFT)

        self._build_commands_tab(self._tab_cmds)
        self._build_rules_tab(self._tab_rules)
        self._switch_tab("cmds")

    def _switch_tab(self, tab):
        if tab == "cmds":
            self._tab_rules.pack_forget()
            self._tab_cmds.pack(fill=tk.BOTH, expand=True)
            self._btn_tab_cmds.config(bg=ACCENT,   fg="#ffffff",
                                       font=("Segoe UI", 9, "bold"))
            self._btn_tab_rules.config(bg=BG_TOPBAR, fg=TEXT_MUT,
                                        font=("Segoe UI", 9))
        else:
            self._tab_cmds.pack_forget()
            self._tab_rules.pack(fill=tk.BOTH, expand=True)
            self._btn_tab_cmds.config(bg=BG_TOPBAR, fg=TEXT_MUT,
                                       font=("Segoe UI", 9))
            self._btn_tab_rules.config(bg=ACCENT,    fg="#ffffff",
                                        font=("Segoe UI", 9, "bold"))

    # ──────────────────────────────────────────
    #  Aba Comandos
    # ──────────────────────────────────────────
    def _build_commands_tab(self, parent):
        canvas = tk.Canvas(parent, bg=BG_MAIN, highlightthickness=0)
        sb = ttk.Scrollbar(parent, orient="vertical",
                            command=canvas.yview,
                            style="AM.Vertical.TScrollbar")
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inner  = tk.Frame(canvas, bg=BG_MAIN)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(win_id, width=e.width))
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll( 1, "units"))

        sections = [
            ("⚡  Energia / Power", [
                ("POWER ON",      "Liga o relay principal",         lambda: self._send("POWER", "ON")),
                ("POWER OFF",     "Desliga o relay principal",      lambda: self._send("POWER", "OFF")),
                ("POWER TOGGLE",  "Alterna estado ON/OFF",          lambda: self._send("POWER", "TOGGLE")),
                ("POWER ?",       "Consulta estado atual",          lambda: self._send("POWER", "")),
                ("Power2 ON",     "Liga relay 2 (ex: porta)",       lambda: self._send("Power2", "ON")),
                ("Power2 OFF",    "Desliga relay 2",                lambda: self._send("Power2", "OFF")),
                ("Power2 TOGGLE", "Alterna relay 2",                lambda: self._send("Power2", "TOGGLE")),
                ("PowerAll ON",   "Liga todos os relays",           lambda: self._send("PowerAll", "ON")),
                ("PowerAll OFF",  "Desliga todos os relays",        lambda: self._send("PowerAll", "OFF")),
            ]),
            ("📡  Estado / Telemetria", [
                ("State",     "Estado completo do dispositivo",     lambda: self._send("State", "")),
                ("Status 0",  "Todos os parâmetros de status",      lambda: self._send("Status", "0")),
                ("Status 1",  "Info do firmware",                   lambda: self._send("Status", "1")),
                ("Status 5",  "Info de rede (IP, MAC)",             lambda: self._send("Status", "5")),
                ("Status 6",  "Info MQTT",                         lambda: self._send("Status", "6")),
                ("Status 10", "Dados de sensores",                  lambda: self._send("Status", "10")),
            ]),
            ("💡  Luz / Dimmer", [
                ("Dimmer 100",     "Brilho máximo",                 lambda: self._send("Dimmer", "100")),
                ("Dimmer 50",      "Meia intensidade",              lambda: self._send("Dimmer", "50")),
                ("Dimmer 10",      "Brilho mínimo",                 lambda: self._send("Dimmer", "10")),
                ("Color BRANCO",   "RGB branco puro",               lambda: self._send("Color", "FFFFFF")),
                ("Color VERMELHO", "RGB vermelho",                  lambda: self._send("Color", "FF0000")),
                ("Color AZUL",     "RGB azul",                     lambda: self._send("Color", "0000FF")),
                ("CT 200",         "Temperatura de cor quente",     lambda: self._send("CT", "200")),
                ("CT 400",         "Temperatura de cor fria",       lambda: self._send("CT", "400")),
            ]),
            ("⏱  Timers / Pulso", [
                ("PulseTime 10",  "Pulso de 1 segundo (10×100ms)",  lambda: self._send("PulseTime1", "10")),
                ("PulseTime 30",  "Pulso de 3 segundos",            lambda: self._send("PulseTime1", "30")),
                ("PulseTime OFF", "Desativa pulso",                 lambda: self._send("PulseTime1", "0")),
                ("RuleTimer 60",  "Inicia timer de regra (60s)",    lambda: self._send("RuleTimer1", "60")),
            ]),
            ("🔌  Sistema", [
                ("Restart",      "Reinicia o dispositivo",          lambda: self._send("Restart", "1")),
                ("Reset config", "Repõe configs de fábrica",        lambda: self._confirm_reset()),
                ("Upgrade OTA",  "Atualiza firmware via OTA",       lambda: self._send("Upgrade", "1")),
                ("SaveData",     "Grava configuração na flash",     lambda: self._send("SaveData", "1")),
            ]),
            ("🌐  Rede / MQTT", [
                ("MqttHost ?",    "Consulta broker atual",          lambda: self._send("MqttHost", "")),
                ("Topic ?",       "Consulta tópico MQTT",           lambda: self._send("Topic", "")),
                ("Hostname ?",    "Consulta hostname de rede",      lambda: self._send("Hostname", "")),
                ("IPAddress ?",   "Consulta IP do dispositivo",     lambda: self._send("IPAddress1", "")),
                ("WifiConfig AP", "Ativa modo AP de config. WiFi",  lambda: self._send("WifiConfig", "2")),
            ]),
        ]

        for title, cmds in sections:
            self._build_section(inner, title, cmds)
        self._build_custom_section(inner)

    def _build_section(self, parent, title, commands):
        # Cabeçalho da secção — estilo AluminioManager
        hdr = tk.Frame(parent, bg=BG_TOPBAR, cursor="hand2")
        hdr.pack(fill=tk.X, pady=(6, 0))

        lbl_arrow = tk.Label(hdr, text="▼", bg=BG_TOPBAR, fg=TEXT_MUT,
                              font=("Segoe UI", 8), width=2)
        lbl_arrow.pack(side=tk.LEFT, padx=(6, 0))
        tk.Label(hdr, text=title, bg=BG_TOPBAR, fg=TEXT_SEC,
                 font=("Segoe UI", 9, "bold"), pady=6).pack(side=tk.LEFT, padx=4)

        # Linha divisória sob o cabeçalho
        tk.Frame(parent, bg=DIVIDER, height=1).pack(fill=tk.X)

        container = tk.Frame(parent, bg=BG_MAIN)
        container.pack(fill=tk.X)

        def toggle(c=container, a=lbl_arrow):
            if c.winfo_ismapped():
                c.pack_forget(); a.config(text="▶")
            else:
                c.pack(fill=tk.X); a.config(text="▼")

        hdr.bind("<Button-1>", lambda e: toggle())
        lbl_arrow.bind("<Button-1>", lambda e: toggle())

        for name, desc, cmd in commands:
            self._cmd_button(container, name, desc, cmd)

    def _cmd_button(self, parent, name, desc, cmd):
        row = tk.Frame(parent, bg=BG_CARD, cursor="hand2")
        row.pack(fill=tk.X, pady=1, padx=0)

        def on_enter(e, r=row):
            r.config(bg=BG_PANEL)
            for w in r.winfo_children():
                w.config(bg=BG_PANEL)
        def on_leave(e, r=row):
            r.config(bg=BG_CARD)
            for w in r.winfo_children():
                w.config(bg=BG_CARD)

        row.bind("<Enter>",    on_enter)
        row.bind("<Leave>",    on_leave)
        row.bind("<Button-1>", lambda e, c=cmd: c())

        # Barra de acento azul à esquerda
        tk.Frame(row, bg=ACCENT, width=3).pack(side=tk.LEFT, fill=tk.Y)

        lbl_n = tk.Label(row, text=name, bg=BG_CARD, fg=ACCENT,
                          font=("Segoe UI", 9, "bold"),
                          anchor="w", padx=10, pady=6)
        lbl_n.pack(side=tk.LEFT)
        lbl_d = tk.Label(row, text=desc, bg=BG_CARD, fg=TEXT_MUT,
                          font=("Segoe UI", 8), anchor="e", padx=8)
        lbl_d.pack(side=tk.RIGHT)

        for lbl in (lbl_n, lbl_d):
            lbl.bind("<Button-1>", lambda e, c=cmd: c())
            lbl.bind("<Enter>",    on_enter)
            lbl.bind("<Leave>",    on_leave)

    def _build_custom_section(self, parent):
        tk.Frame(parent, bg=DIVIDER, height=1).pack(fill=tk.X, pady=10)

        sec = tk.Frame(parent, bg=BG_TOPBAR)
        sec.pack(fill=tk.X)
        tk.Label(sec, text="⌨  COMANDO PERSONALIZADO",
                 font=("Segoe UI", 8, "bold"),
                 bg=BG_TOPBAR, fg=TEXT_MUT,
                 padx=10, pady=6).pack(side=tk.LEFT)
        tk.Frame(parent, bg=DIVIDER, height=1).pack(fill=tk.X)

        f = tk.Frame(parent, bg=BG_MAIN, pady=8, padx=8)
        f.pack(fill=tk.X)

        tk.Label(f, text="Comando", bg=BG_MAIN, fg=TEXT_MUT,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.entry_cmd = tk.Entry(f, bg=BG_INPUT, fg=TEXT_PRI,
                                   insertbackground=TEXT_PRI,
                                   bd=0, font=("Segoe UI", 10),
                                   relief="flat",
                                   highlightthickness=1,
                                   highlightbackground=BORDER,
                                   highlightcolor=ACCENT)
        self.entry_cmd.pack(fill=tk.X, ipady=5, pady=(2, 8))

        tk.Label(f, text="Payload", bg=BG_MAIN, fg=TEXT_MUT,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.entry_payload = tk.Entry(f, bg=BG_INPUT, fg=TEXT_PRI,
                                       insertbackground=TEXT_PRI,
                                       bd=0, font=("Segoe UI", 10),
                                       relief="flat",
                                       highlightthickness=1,
                                       highlightbackground=BORDER,
                                       highlightcolor=ACCENT)
        self.entry_payload.pack(fill=tk.X, ipady=5, pady=(2, 10))

        self.entry_cmd.bind("<Return>",     lambda e: self.entry_payload.focus())
        self.entry_payload.bind("<Return>", lambda e: self._send_custom())

        tk.Button(f, text="  Enviar  ▶",
                  command=self._send_custom,
                  bg=ACCENT, fg="#ffffff",
                  bd=0, pady=7,
                  font=("Segoe UI", 9, "bold"),
                  cursor="hand2",
                  activebackground=ACCENT_HOV,
                  activeforeground="#ffffff",
                  relief="flat").pack(fill=tk.X)

    # ──────────────────────────────────────────
    #  Aba Rules
    # ──────────────────────────────────────────
    def _build_rules_tab(self, parent):
        top = tk.Frame(parent, bg=BG_TOPBAR)
        top.pack(fill=tk.X)
        tk.Label(top, text="RULES DO DISPOSITIVO",
                 font=("Segoe UI", 8, "bold"),
                 bg=BG_TOPBAR, fg=TEXT_MUT,
                 padx=10, pady=6).pack(side=tk.LEFT)
        tk.Button(top, text="↺  Consultar todas",
                  command=self._query_all_rules,
                  bg=BG_TOPBAR, fg=TEXT_SEC,
                  bd=0, padx=10, pady=4,
                  font=("Segoe UI", 8),
                  cursor="hand2",
                  activebackground=BG_PANEL,
                  activeforeground=TEXT_PRI,
                  relief="flat").pack(side=tk.RIGHT, padx=6)
        tk.Frame(parent, bg=DIVIDER, height=1).pack(fill=tk.X)

        canvas = tk.Canvas(parent, bg=BG_MAIN, highlightthickness=0)
        sb = ttk.Scrollbar(parent, orient="vertical",
                            command=canvas.yview,
                            style="AM.Vertical.TScrollbar")
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inner  = tk.Frame(canvas, bg=BG_MAIN)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(win_id, width=e.width))
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll( 1, "units"))

        self._rule_vars = {}
        for slot in (1, 2, 3):
            self._build_rule_slot(inner, slot)

    def _build_rule_slot(self, parent, slot):
        enabled_var = tk.BooleanVar(value=False)
        self._rule_vars[slot] = {"enabled": enabled_var}

        # Card da rule
        card = tk.Frame(parent, bg=BG_CARD,
                         highlightthickness=1,
                         highlightbackground=BORDER)
        card.pack(fill=tk.X, pady=(8, 0), padx=6)

        # Cabeçalho
        hdr = tk.Frame(card, bg=BG_TOPBAR)
        hdr.pack(fill=tk.X)

        # Barra colorida à esquerda
        tk.Frame(hdr, bg=YELLOW, width=3).pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(hdr, text=f"Rule{slot}",
                 bg=BG_TOPBAR, fg=YELLOW,
                 font=("Segoe UI", 10, "bold"),
                 padx=8, pady=6).pack(side=tk.LEFT)

        # Checkbox
        chk = tk.Checkbutton(hdr, text="Ativa",
                              variable=enabled_var,
                              bg=BG_TOPBAR, fg=TEXT_SEC,
                              selectcolor=BG_CARD,
                              activebackground=BG_TOPBAR,
                              activeforeground=SUCCESS,
                              font=("Segoe UI", 8),
                              command=lambda s=slot: self._toggle_rule(s))
        chk.pack(side=tk.LEFT, padx=4)

        tk.Button(hdr, text="↺",
                  command=lambda s=slot: self._send(f"Rule{s}", ""),
                  bg=BG_TOPBAR, fg=TEXT_MUT,
                  bd=0, padx=8, pady=4,
                  font=("Segoe UI", 9),
                  cursor="hand2",
                  activebackground=BG_PANEL,
                  activeforeground=TEXT_PRI,
                  relief="flat").pack(side=tk.RIGHT, padx=4)

        tk.Frame(card, bg=DIVIDER, height=1).pack(fill=tk.X)

        # Área de texto
        txt_frame = tk.Frame(card, bg=BG_INPUT, padx=4, pady=4)
        txt_frame.pack(fill=tk.X, padx=0, pady=0)

        txt = tk.Text(txt_frame, bg=BG_INPUT, fg=INFO,
                       insertbackground=TEXT_PRI,
                       font=("Monospace", 8),
                       bd=0, wrap=tk.WORD,
                       height=4, relief="flat")
        txt.pack(fill=tk.X)
        txt.insert("1.0", "— clica ↺ para consultar —")
        txt.config(state=tk.DISABLED)
        self._rule_vars[slot]["text_widget"] = txt

        tk.Frame(card, bg=DIVIDER, height=1).pack(fill=tk.X)

        # Botões de ação
        btn_f = tk.Frame(card, bg=BG_CARD, pady=6, padx=8)
        btn_f.pack(fill=tk.X)

        def _action_btn(parent, text, cmd, fg_color, bg_color):
            return tk.Button(parent, text=text, command=cmd,
                             bg=bg_color, fg=fg_color,
                             bd=0, padx=10, pady=4,
                             font=("Segoe UI", 8, "bold"),
                             cursor="hand2",
                             activebackground=BG_PANEL,
                             activeforeground=TEXT_PRI,
                             relief="flat",
                             highlightthickness=1,
                             highlightbackground=BORDER)

        _action_btn(btn_f, "✏  Editar",
                    lambda s=slot: self._edit_rule(s),
                    TEXT_SEC, BG_PANEL).pack(side=tk.LEFT, padx=(0, 4))
        _action_btn(btn_f, "💾  Salvar",
                    lambda s=slot: self._save_rule(s),
                    SUCCESS, "#1a3a1a").pack(side=tk.LEFT, padx=(0, 4))
        _action_btn(btn_f, "🗑  Apagar",
                    lambda s=slot: self._delete_rule(s),
                    DANGER, "#3a1a1a").pack(side=tk.LEFT)

    # ──────────────────────────────────────────
    #  Lógica Rules (inalterada)
    # ──────────────────────────────────────────
    def _query_all_rules(self):
        dev = self._get_selected_device()
        if not dev: return
        for slot in (1, 2, 3):
            self._send(f"Rule{slot}", "")

    def _toggle_rule(self, slot):
        dev = self._get_selected_device()
        if not dev: return
        val = "1" if self._rule_vars[slot]["enabled"].get() else "0"
        self._send(f"Rule{slot}", val)

    def _edit_rule(self, slot):
        txt       = self._rule_vars[slot]["text_widget"]
        last_text = self._rule_vars[slot].get("last_text", "")
        txt.config(state=tk.NORMAL, bg="#1a2030", fg=TEXT_PRI)
        txt.delete("1.0", tk.END)
        txt.insert("1.0", last_text)
        txt.focus_set()
        txt.mark_set("insert", tk.END)

    def _save_rule(self, slot):
        dev = self._get_selected_device()
        if not dev: return
        txt = self._rule_vars[slot]["text_widget"]
        content = txt.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("Rule vazia",
                                   f"Escreve o conteúdo da Rule{slot} antes de salvar.")
            return
        txt.config(state=tk.DISABLED, bg=BG_INPUT)
        self._send(f"Rule{slot}", content)

    def _delete_rule(self, slot):
        dev = self._get_selected_device()
        if not dev: return
        if messagebox.askyesno("Apagar Rule",
                               f"Apagar Rule{slot} de '{dev}'?"):
            self._send(f"Rule{slot}", "0")
            txt = self._rule_vars[slot]["text_widget"]
            txt.config(state=tk.NORMAL)
            txt.delete("1.0", tk.END)
            txt.insert("1.0", "— rule apagada —")
            txt.config(state=tk.DISABLED, bg=BG_INPUT)
            self._rule_vars[slot]["enabled"].set(False)

    def _update_rule_display(self, slot, rule_data):
        if slot not in self._rule_vars:
            return
        txt       = self._rule_vars[slot]["text_widget"]
        state_raw = rule_data.get("State", 0)
        if isinstance(state_raw, str):
            enabled = state_raw.upper() == "ON"
        else:
            enabled = bool(state_raw & 1)

        rule_text = rule_data.get("Rules", "").strip()
        self._rule_vars[slot]["enabled"].set(enabled)
        self._rule_vars[slot]["last_text"] = rule_text

        txt.config(state=tk.NORMAL,
                   bg=RULE_BG if enabled else RULE_DIS)
        txt.delete("1.0", tk.END)
        txt.insert("1.0", rule_text if rule_text else "— rule vazia —")
        txt.config(state=tk.DISABLED)

    # ──────────────────────────────────────────
    #  Envio MQTT (inalterado)
    # ──────────────────────────────────────────
    def _get_selected_device(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Sem dispositivo",
                                   "Seleciona um dispositivo na tabela primeiro.")
            return None
        return self.tree.item(sel[0], "values")[0]

    def _send(self, cmd, payload):
        dev = self._get_selected_device()
        if not dev: return
        if not self.client:
            messagebox.showwarning("Desconectado", "Liga ao broker MQTT primeiro.")
            return
        topic = f"cmnd/{dev}/{cmd}"
        self.client.publish(topic, payload)
        self._log(f"ENVIADO  {topic}  →  {payload or '(vazio)'}", tag="sent")

    def _send_custom(self):
        cmd     = self.entry_cmd.get().strip()
        payload = self.entry_payload.get().strip()
        if not cmd:
            messagebox.showwarning("Comando vazio", "Escreve um comando.")
            return
        self._send(cmd, payload)

    def _confirm_reset(self):
        dev = self._get_selected_device()
        if not dev: return
        if messagebox.askyesno("Confirmar Reset",
                               f"Tens a certeza que queres fazer reset ao '{dev}'?\n"
                               "Isto repõe as configurações de fábrica."):
            self._send("Reset", "1")

    # ──────────────────────────────────────────
    #  Log MQTT
    # ──────────────────────────────────────────
    def _log(self, text, tag="recv"):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{ts}]  {text}\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _clear_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)

    def toggle_log(self):
        self.log_open = not self.log_open
        if self.log_open:
            self.log_frame.pack(fill=tk.X, side=tk.BOTTOM, before=self._foot_frame)
        else:
            self.log_frame.pack_forget()

    # ──────────────────────────────────────────
    #  Seleção tabela
    # ──────────────────────────────────────────
    def _on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        dev = self.tree.item(sel[0], "values")[0]
        self.lbl_selected.config(text=dev)
        for slot in (1, 2, 3):
            if slot in self._rule_vars:
                txt = self._rule_vars[slot]["text_widget"]
                txt.config(state=tk.NORMAL, bg=BG_INPUT)
                txt.delete("1.0", tk.END)
                txt.insert("1.0", "— clica ↺ para consultar —")
                txt.config(state=tk.DISABLED)
                self._rule_vars[slot]["enabled"].set(False)

    # ──────────────────────────────────────────
    #  Configuração
    # ──────────────────────────────────────────
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except:
                return None
        return None

    def open_config_window(self):
        win = tk.Toplevel(self.root)
        win.title("Configurar Broker MQTT")
        win.geometry("340x340")
        win.configure(bg=BG_MAIN)
        win.grab_set()
        win.resizable(False, False)

        # Topbar da janela
        top = tk.Frame(win, bg=BG_TOPBAR)
        top.pack(fill=tk.X)
        tk.Label(top, text="⚙  Broker MQTT",
                 font=("Segoe UI", 12, "bold"),
                 bg=BG_TOPBAR, fg=ACCENT,
                 padx=16, pady=12).pack(side=tk.LEFT)
        tk.Frame(win, bg=BORDER, height=1).pack(fill=tk.X)

        body = tk.Frame(win, bg=BG_MAIN, padx=20, pady=16)
        body.pack(fill=tk.BOTH, expand=True)

        fields  = ["host", "port", "user", "pass"]
        labels  = ["Host / IP", "Porta", "Utilizador", "Password"]
        entries = {}
        for f, lbl in zip(fields, labels):
            tk.Label(body, text=lbl, bg=BG_MAIN, fg=TEXT_MUT,
                     font=("Segoe UI", 8, "bold")).pack(anchor="w")
            e = tk.Entry(body, bg=BG_INPUT, fg=TEXT_PRI,
                          insertbackground=TEXT_PRI,
                          bd=0, font=("Segoe UI", 10),
                          relief="flat",
                          highlightthickness=1,
                          highlightbackground=BORDER,
                          highlightcolor=ACCENT,
                          show="*" if f == "pass" else "")
            e.pack(fill=tk.X, ipady=5, pady=(2, 10))
            if self.config:
                e.insert(0, self.config.get(f, ""))
            entries[f] = e

        def save():
            new_conf = {f: entries[f].get() for f in fields}
            try:
                new_conf["port"] = int(new_conf["port"])
            except ValueError:
                messagebox.showerror("Erro", "Porta inválida.")
                return
            with open(CONFIG_FILE, "w") as fp:
                json.dump(new_conf, fp)
            self.config = new_conf
            win.destroy()
            self.start_mqtt()

        tk.Frame(win, bg=BORDER, height=1).pack(fill=tk.X)
        foot = tk.Frame(win, bg=BG_TOPBAR, padx=16, pady=10)
        foot.pack(fill=tk.X)
        tk.Button(foot, text="  SALVAR E LIGAR  ",
                  command=save,
                  bg=ACCENT, fg="#ffffff",
                  bd=0, pady=7,
                  font=("Segoe UI", 9, "bold"),
                  cursor="hand2",
                  activebackground=ACCENT_HOV,
                  activeforeground="#ffffff",
                  relief="flat").pack(fill=tk.X)

    # ──────────────────────────────────────────
    #  MQTT (inalterado)
    # ──────────────────────────────────────────
    def start_mqtt(self):
        if not self.config:
            self.open_config_window()
            return
        if self.client:
            try: self.client.disconnect()
            except: pass

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if self.config.get("user"):
            self.client.username_pw_set(self.config["user"], self.config["pass"])
        self.client.on_connect    = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message    = self.on_message

        def run():
            try:
                self.client.connect(self.config["host"],
                                    int(self.config["port"]), 60)
                self.client.loop_forever()
            except Exception as e:
                msg = str(e)
                self.root.after(0, lambda m=msg: self.lbl_status.config(
                    text=f"● Erro: {m}", fg=DANGER))

        threading.Thread(target=run, daemon=True).start()

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            self.root.after(0, lambda: self.lbl_status.config(
                text="● Online (Broker)", fg=GREEN))
            for topic in ("tele/+/LWT", "stat/+/POWER",
                          "stat/+/RESULT", "tele/+/STATE"):
                client.subscribe(topic)
            self._log("Ligado ao broker MQTT")
        else:
            self.root.after(0, lambda: self.lbl_status.config(
                text=f"● Erro rc={reason_code}", fg=DANGER))

    def on_disconnect(self, client, userdata, flags, reason_code, properties):
        self.root.after(0, lambda: self.lbl_status.config(
            text="● Desconectado", fg=DANGER))

    def on_message(self, client, userdata, msg):
        try:
            device_id = msg.topic.split('/')[1]
            payload   = msg.payload.decode()
            now       = datetime.datetime.now().strftime("%H:%M:%S")

            self._log(f"RECEBIDO {msg.topic}  ←  {payload}")

            if "LWT" in msg.topic:
                if payload.upper() == "OFFLINE":
                    self.root.after(0, self.remove_device, device_id)
                else:
                    if device_id not in self.devices:
                        client.publish(f"cmnd/{device_id}/POWER", "")
                    self.root.after(0, self.update_row, device_id, None, "ONLINE", now)
                return

            if payload.startswith("{"):
                data = json.loads(payload)
                for slot in (1, 2, 3):
                    key = f"Rule{slot}"
                    if key in data:
                        self.root.after(0, self._update_rule_display, slot, data[key])
                state = data.get("POWER", data.get("POWER1", data.get("POWER2")))
                if state:
                    self.root.after(0, self.update_row,
                                    device_id, state.upper(), None, now)
            elif payload in ("ON", "OFF"):
                self.root.after(0, self.update_row,
                                device_id, payload, None, now)

        except Exception:
            pass

    def update_row(self, device_id, state, presence, time_str):
        if device_id not in self.devices:
            if presence == "ONLINE":
                iid = self.tree.insert("", tk.END,
                                       values=(device_id, "---", "ONLINE", time_str),
                                       image=self.led_idle)
                self.devices[device_id] = iid
        else:
            iid = self.devices[device_id]
            if presence:
                self.tree.set(iid, "Conexão", presence)
            if state:
                self.tree.set(iid, "Estado", state)
                self.tree.item(iid, image=self.led_on if state == "ON" else self.led_off)
            self.tree.set(iid, "Atualizado", time_str)

    def remove_device(self, device_id):
        if device_id in self.devices:
            self.tree.delete(self.devices[device_id])
            del self.devices[device_id]

    def on_double_click(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid or not self.client: return
        dev_id = self.tree.item(iid, "values")[0]
        if dev_id == "porta":
            self.client.publish(f"cmnd/{dev_id}/Power2", "ON")
            self._log(f"ENVIADO  cmnd/{dev_id}/Power2  →  ON", tag="sent")
        else:
            self.client.publish(f"cmnd/{dev_id}/POWER", "TOGGLE")
            self._log(f"ENVIADO  cmnd/{dev_id}/POWER  →  TOGGLE", tag="sent")


if __name__ == "__main__":
    root = tk.Tk()
    app  = TasmotaSmartHub(root)
    root.mainloop()
