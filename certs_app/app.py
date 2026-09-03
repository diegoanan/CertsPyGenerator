from __future__ import annotations

import os
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, simpledialog, ttk

from certs_app.openssl_utils import (
    build_bundle_filename,
    build_cert_filename,
    build_csr_filename,
    build_key_filename,
    concatenate_files,
    generate_csr,
    generate_private_key,
    normalize_certificate_file,
    remove_key_password,
    verify_key_pair_match,
)
from certs_app.storage import CertificateHistoryRepository, SubjectRepository


class CertsPyGeneratorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("CertsPyGenerator")
        self.geometry("1300x860")
        self.minsize(1100, 760)
        self.configure(bg="#f3f7fb")

        self.repo = SubjectRepository("certs_subjects.db")
        self.history = CertificateHistoryRepository("certs_history.db")

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f3f7fb")
        style.configure("TLabel", background="#f3f7fb", foreground="#1f2937")
        style.configure("TLabelframe", background="#f3f7fb")
        style.configure("TLabelframe.Label", background="#f3f7fb", foreground="#0f172a", font=("Segoe UI", 10, "bold"))
        style.configure("TButton", padding=(12, 8), font=("Segoe UI", 10, "bold"), background="#e2e8f0", foreground="#0f172a")
        style.configure("Accent.TButton", background="#2563eb", foreground="#ffffff", padding=(12, 9), font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton", background=[("active", "#1d4ed8"), ("pressed", "#1e3a8a")], foreground=[("active", "#ffffff")])
        style.map("TButton", background=[("active", "#dbeafe"), ("pressed", "#bfdbfe")], foreground=[("active", "#0f172a")])
        style.configure("TEntry", fieldbackground="#ffffff", foreground="#0f172a")
        style.configure("TCombobox", fieldbackground="#ffffff", foreground="#0f172a")
        style.configure("Treeview", rowheight=26, background="#ffffff", fieldbackground="#ffffff", foreground="#0f172a")
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background="#e2e8f0", foreground="#0f172a")
        style.configure("TNotebook", background="#eef4fb", bordercolor="#dbeafe")
        style.configure("TNotebook.Tab", padding=(14, 8), background="#e2e8f0", foreground="#334155", font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", "#ffffff"), ("active", "#f8fafc")], foreground=[("selected", "#0f172a"), ("active", "#0f172a")])
        self.configure(bg="#f3f7fb")

        self.bind_all("<MouseWheel>", self._on_mousewheel)
        self.bind_all("<Button-4>", self._on_mousewheel)
        self.bind_all("<Button-5>", self._on_mousewheel)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=12)

        self.key_tab = ttk.Frame(self.notebook)
        self.repo_tab = ttk.Frame(self.notebook)
        self.verify_tab = ttk.Frame(self.notebook)
        self.cert_tab = ttk.Frame(self.notebook)
        self.history_tab = ttk.Frame(self.notebook)
        self.concat_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.key_tab, text="Claves y CSR")
        self.notebook.add(self.repo_tab, text="Repositorio")
        self.notebook.add(self.verify_tab, text="Verificación")
        self.notebook.add(self.cert_tab, text="Certificado")
        self.notebook.add(self.concat_tab, text="Concatenación")
        self.notebook.add(self.history_tab, text="Historial")

        self._build_key_tab()
        self._build_repo_tab()
        self._build_verify_tab()
        self._build_cert_tab()
        self._build_history_tab()
        self._build_concat_tab()
        self._refresh_history()

    def _create_scrollable_area(self, parent):
        container = ttk.Frame(parent)
        container.pack(fill="both", expand=True)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

        canvas = tk.Canvas(container, highlightthickness=0, bg="#f3f7fb")
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        inner = ttk.Frame(canvas)
        inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfigure(inner_id, width=max(canvas.winfo_width(), inner.winfo_reqwidth()))

        def _on_canvas_configure(event):
            canvas.itemconfigure(inner_id, width=max(event.width, inner.winfo_reqwidth()))

        inner.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        def _on_canvas_scroll(event):
            if event.delta > 0:
                canvas.yview_scroll(-1, "units")
            else:
                canvas.yview_scroll(1, "units")

        canvas.bind("<MouseWheel>", _on_canvas_scroll)
        canvas.bind("<Button-4>", _on_canvas_scroll)
        canvas.bind("<Button-5>", _on_canvas_scroll)
        return inner

    def _on_mousewheel(self, event):
        widget = event.widget
        if widget is None:
            return

        target = widget
        if isinstance(target, str):
            try:
                target = self.nametowidget(target)
            except Exception:
                return

        while target is not None and not hasattr(target, "yview"):
            if not hasattr(target, "winfo_parent"):
                target = None
                break
            try:
                parent_name = target.winfo_parent()
            except Exception:
                target = None
                break
            if not parent_name or parent_name == "__tk_filedialog":
                target = None
                break
            try:
                parent = self.nametowidget(parent_name)
            except (KeyError, AttributeError, tk.TclError):
                target = None
                break
            target = parent

        if target is None or not hasattr(target, "yview"):
            return

        if event.num == 4:
            target.yview_scroll(-1, "units")
        elif event.num == 5:
            target.yview_scroll(1, "units")
        else:
            target.yview_scroll(int(-event.delta / 120), "units")

    def _build_key_tab(self) -> None:
        frame = ttk.LabelFrame(self._create_scrollable_area(self.key_tab), text="Generación de claves y CSR")
        frame.pack(fill="both", expand=True, padx=12, pady=10)
        frame.columnconfigure(1, weight=1)

        self.key_name_var = tk.StringVar(value="server")
        self.key_dir_var = tk.StringVar(value=os.getcwd())
        self.rsa_bits_var = tk.StringVar(value="2048")
        self.encrypted_key_var = tk.BooleanVar(value=True)
        self.key_password_var = tk.StringVar(value="")

        ttk.Label(frame, text="Nombre base:").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        ttk.Entry(frame, textvariable=self.key_name_var).grid(row=0, column=1, sticky="ew", padx=10, pady=8)

        ttk.Label(frame, text="Carpeta destino:").grid(row=1, column=0, sticky="w", padx=10, pady=8)
        ttk.Entry(frame, textvariable=self.key_dir_var).grid(row=1, column=1, sticky="ew", padx=10, pady=8)
        ttk.Button(frame, text="Elegir carpeta", command=self._choose_key_dir).grid(row=1, column=2, padx=(0, 10), pady=8)

        ttk.Label(frame, text="Bits RSA:").grid(row=2, column=0, sticky="w", padx=10, pady=8)
        ttk.Combobox(frame, textvariable=self.rsa_bits_var, values=["2048", "3072", "4096"], state="readonly", width=10).grid(row=2, column=1, sticky="w", padx=10, pady=8)

        ttk.Checkbutton(frame, text="Generar clave cifrada", variable=self.encrypted_key_var).grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=8)
        ttk.Label(frame, text="Contraseña:").grid(row=4, column=0, sticky="w", padx=10, pady=8)
        ttk.Entry(frame, textvariable=self.key_password_var, show="*", width=30).grid(row=4, column=1, sticky="w", padx=10, pady=8)

        ttk.Button(frame, text="Generar clave privada", command=self._generate_key, style="Accent.TButton").grid(row=5, column=0, padx=10, pady=12)
        self.key_status = tk.StringVar(value="En espera.")
        ttk.Label(frame, textvariable=self.key_status, wraplength=900).grid(row=5, column=1, sticky="w", padx=10, pady=8)

        self.csr_name_var = tk.StringVar(value="")
        self.csr_key_path = tk.StringVar(value="")
        self.csr_output_dir = tk.StringVar(value="")
        self.csr_password_var = tk.StringVar(value="")
        self.repo_select_var = tk.StringVar(value="")
        self.csr_subject_fields = {
            "C": tk.StringVar(value="ES"),
            "ST": tk.StringVar(value="Madrid"),
            "L": tk.StringVar(value="Madrid"),
            "O": tk.StringVar(value="CertsPyGenerator"),
            "OU": tk.StringVar(value="DevOps"),
            "CN": tk.StringVar(value="example.local"),
            "email": tk.StringVar(value="admin@example.local"),
        }

        ttk.Label(frame, text="Perfil guardado:").grid(row=6, column=0, sticky="w", padx=10, pady=8)
        self.repo_combo = ttk.Combobox(frame, textvariable=self.repo_select_var, state="readonly")
        self.repo_combo.grid(row=6, column=1, sticky="ew", padx=10, pady=8)
        ttk.Button(frame, text="Aplicar perfil", command=self._apply_subject_from_repo).grid(row=6, column=2, padx=(0, 10), pady=8)
        self._update_repo_combo()

        ttk.Label(frame, text="Clave usada:").grid(row=7, column=0, sticky="w", padx=10, pady=8)
        ttk.Entry(frame, textvariable=self.csr_key_path).grid(row=7, column=1, sticky="ew", padx=10, pady=8)
        ttk.Button(frame, text="Seleccionar clave", command=self._select_csr_key).grid(row=7, column=2, padx=(0, 10), pady=8)

        ttk.Label(frame, text="Nombre CSR:").grid(row=8, column=0, sticky="w", padx=10, pady=8)
        ttk.Entry(frame, textvariable=self.csr_name_var).grid(row=8, column=1, sticky="ew", padx=10, pady=8)

        ttk.Label(frame, text="Carpeta destino CSR:").grid(row=9, column=0, sticky="w", padx=10, pady=8)
        ttk.Entry(frame, textvariable=self.csr_output_dir).grid(row=9, column=1, sticky="ew", padx=10, pady=8)
        ttk.Button(frame, text="Elegir carpeta", command=self._choose_csr_output_dir).grid(row=9, column=2, padx=(0, 10), pady=8)

        ttk.Label(frame, text="Contraseña clave:").grid(row=10, column=0, sticky="w", padx=10, pady=8)
        ttk.Entry(frame, textvariable=self.csr_password_var, show="*").grid(row=10, column=1, sticky="w", padx=10, pady=8)

        row_idx = 11
        for key in ["C", "ST", "L", "O", "OU", "CN", "email"]:
            ttk.Label(frame, text={"C": "País", "ST": "Provincia", "L": "Localidad", "O": "Organización", "OU": "Unidad", "CN": "Nombre común", "email": "Email"}[key]).grid(row=row_idx, column=0, sticky="w", padx=10, pady=6)
            ttk.Entry(frame, textvariable=self.csr_subject_fields[key]).grid(row=row_idx, column=1, sticky="ew", padx=10, pady=6)
            row_idx += 1

        ttk.Button(frame, text="Generar CSR", command=self._generate_csr, style="Accent.TButton").grid(row=row_idx, column=0, padx=10, pady=12)
        self.csr_status = tk.StringVar(value="Sin CSR generado.")
        ttk.Label(frame, textvariable=self.csr_status, wraplength=900).grid(row=row_idx, column=1, sticky="w", padx=10, pady=8)

        remove_frame = ttk.LabelFrame(frame, text="Quitar contraseña de clave")
        remove_frame.grid(row=row_idx + 1, column=0, columnspan=3, sticky="ew", padx=10, pady=12)
        remove_frame.columnconfigure(1, weight=1)

        self.remove_key_input = tk.StringVar(value="")
        self.remove_key_output = tk.StringVar(value="")
        self.remove_key_password = tk.StringVar(value="")

        ttk.Label(remove_frame, text="Clave cifrada:").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        ttk.Entry(remove_frame, textvariable=self.remove_key_input).grid(row=0, column=1, sticky="ew", padx=10, pady=8)
        ttk.Button(remove_frame, text="Seleccionar", command=lambda: self._select_file(self.remove_key_input, filetypes=[("KEY", "*.key"), ("PEM", "*.pem")])).grid(row=0, column=2, padx=(0, 10), pady=8)

        ttk.Label(remove_frame, text="Destino:").grid(row=1, column=0, sticky="w", padx=10, pady=8)
        ttk.Entry(remove_frame, textvariable=self.remove_key_output).grid(row=1, column=1, sticky="ew", padx=10, pady=8)
        ttk.Button(remove_frame, text="Guardar", command=lambda: self._save_file(self.remove_key_output, default_name="server_nopass.key")).grid(row=1, column=2, padx=(0, 10), pady=8)

        ttk.Label(remove_frame, text="Contraseña:").grid(row=2, column=0, sticky="w", padx=10, pady=8)
        ttk.Entry(remove_frame, textvariable=self.remove_key_password, show="*").grid(row=2, column=1, sticky="w", padx=10, pady=8)
        ttk.Button(remove_frame, text="Quitar contraseña", command=self._remove_key_password, style="Accent.TButton").grid(row=3, column=0, padx=10, pady=12)
        self.remove_key_status = tk.StringVar(value="Sin acción.")
        ttk.Label(remove_frame, textvariable=self.remove_key_status, wraplength=800).grid(row=3, column=1, sticky="w", padx=10, pady=8)

    def _build_repo_tab(self) -> None:
        frame = ttk.LabelFrame(self._create_scrollable_area(self.repo_tab), text="Repositorio de perfiles")
        frame.pack(fill="both", expand=True, padx=12, pady=10)
        frame.columnconfigure(1, weight=1)

        self.repo_fields = {
            "name": tk.StringVar(value=""),
            "C": tk.StringVar(value="ES"),
            "ST": tk.StringVar(value="Madrid"),
            "L": tk.StringVar(value="Madrid"),
            "O": tk.StringVar(value="CertsPyGenerator"),
            "OU": tk.StringVar(value="DevOps"),
            "CN": tk.StringVar(value="example.local"),
            "email": tk.StringVar(value="admin@example.local"),
        }

        row_idx = 0
        for key, label in {"name": "Nombre", "C": "País", "ST": "Provincia", "L": "Localidad", "O": "Organización", "OU": "Unidad", "CN": "Nombre común", "email": "Email"}.items():
            ttk.Label(frame, text=label).grid(row=row_idx, column=0, sticky="w", padx=10, pady=6)
            ttk.Entry(frame, textvariable=self.repo_fields[key]).grid(row=row_idx, column=1, sticky="ew", padx=10, pady=6)
            row_idx += 1

        actions = ttk.Frame(frame)
        actions.grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=10, pady=(8, 12))
        ttk.Button(actions, text="Guardar perfil", command=self._save_subject_to_repo).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Eliminar perfil", command=self._delete_subject_from_repo).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Exportar CSV", command=self._export_repo_backup).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Importar CSV", command=self._import_repo_backup).pack(side="left")

        self.repo_list = tk.Listbox(frame, height=12, width=120)
        self.repo_list.grid(row=row_idx + 1, column=0, columnspan=2, sticky="nsew", padx=10, pady=(0, 10))
        self.repo_list.bind("<<ListboxSelect>>", self._repo_selection_changed)
        frame.grid_rowconfigure(row_idx + 1, weight=1)
        self._refresh_repo_list()

    def _build_verify_tab(self) -> None:
        frame = ttk.LabelFrame(self._create_scrollable_area(self.verify_tab), text="Verificación de pares de claves")
        frame.pack(fill="both", expand=True, padx=12, pady=10)
        frame.columnconfigure(1, weight=1)

        self.verify_file_a = tk.StringVar(value="")
        self.verify_file_b = tk.StringVar(value="")
        self.verify_password_a = tk.StringVar(value="")
        self.verify_password_b = tk.StringVar(value="")

        ttk.Label(frame, text="Archivo A:").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        ttk.Entry(frame, textvariable=self.verify_file_a).grid(row=0, column=1, sticky="ew", padx=10, pady=8)
        ttk.Button(frame, text="Seleccionar", command=lambda: self._select_file(self.verify_file_a, filetypes=[("Todos", "*.*")])).grid(row=0, column=2, padx=(0, 10), pady=8)

        # ttk.Label(frame, text="Contraseña A (si aplica):").grid(row=1, column=0, sticky="w", padx=10, pady=8)
        # ttk.Entry(frame, textvariable=self.verify_password_a, show="*").grid(row=1, column=1, sticky="ew", padx=10, pady=8)

        ttk.Label(frame, text="Archivo B:").grid(row=2, column=0, sticky="w", padx=10, pady=8)
        ttk.Entry(frame, textvariable=self.verify_file_b).grid(row=2, column=1, sticky="ew", padx=10, pady=8)
        ttk.Button(frame, text="Seleccionar", command=lambda: self._select_file(self.verify_file_b, filetypes=[("Todos", "*.*")])).grid(row=2, column=2, padx=(0, 10), pady=8)

        # ttk.Label(frame, text="Contraseña B (si aplica):").grid(row=3, column=0, sticky="w", padx=10, pady=8)
        # ttk.Entry(frame, textvariable=self.verify_password_b, show="*").grid(row=3, column=1, sticky="ew", padx=10, pady=8)

        ttk.Button(frame, text="Verificar coincidencia", command=self._verify_keys, style="Accent.TButton").grid(row=4, column=0, padx=10, pady=12)
        self.verify_status = tk.StringVar(value="Sin verificación.")
        ttk.Label(frame, textvariable=self.verify_status, wraplength=900).grid(row=4, column=1, sticky="w", padx=10, pady=8)

    def _build_cert_tab(self) -> None:
        frame = ttk.LabelFrame(self._create_scrollable_area(self.cert_tab), text="Normalización y formato de .cer o .pem")
        frame.pack(fill="both", expand=True, padx=12, pady=10)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Archivo certificado:").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        self.cert_input_path = tk.StringVar(value="")
        ttk.Entry(frame, textvariable=self.cert_input_path).grid(row=0, column=1, sticky="ew", padx=10, pady=8)
        ttk.Button(frame, text="Seleccionar", command=lambda: self._select_file(self.cert_input_path, filetypes=[("CER", "*.cer"), ("PEM", "*.pem"), ("CRT", "*.crt")])).grid(row=0, column=2, padx=(0, 10), pady=8)

        ttk.Label(frame, text="Nombre de salida:").grid(row=1, column=0, sticky="w", padx=10, pady=8)
        self.cert_output_name = tk.StringVar(value="")
        ttk.Entry(frame, textvariable=self.cert_output_name).grid(row=1, column=1, sticky="ew", padx=10, pady=8)
        ttk.Button(frame, text="Guardar destino", command=lambda: self._save_file(self.cert_output_name, default_name=build_cert_filename("cert"))).grid(row=1, column=2, padx=(0, 10), pady=8)

        ttk.Button(frame, text="Verificar y normalizar", command=self._normalize_certificate, style="Accent.TButton").grid(row=2, column=0, padx=10, pady=12)
        self.cert_status = tk.StringVar(value="Sin revisión.")
        ttk.Label(frame, textvariable=self.cert_status, wraplength=700).grid(row=2, column=1, sticky="w", padx=10, pady=8)

        history_actions = ttk.Frame(frame)
        history_actions.grid(row=3, column=0, columnspan=3, sticky="w", padx=10, pady=(0, 8))
        ttk.Button(history_actions, text="Ver archivo", command=self._view_selected_history_file).pack(side="left", padx=(0, 8))
        ttk.Button(history_actions, text="Eliminar selección", command=self._delete_history_entry).pack(side="left")

        self.history_tree = ttk.Treeview(frame, columns=("id", "name", "kind", "path", "status", "fecha"), show="headings", height=10)
        self.history_tree.column("id", width=0, stretch=False)
        self.history_tree.heading("id", text="ID")
        self.history_tree.heading("name", text="Nombre")
        self.history_tree.heading("kind", text="Tipo")
        self.history_tree.heading("path", text="Ruta")
        self.history_tree.heading("status", text="Estado")
        self.history_tree.heading("fecha", text="Fecha")
        self.history_tree.grid(row=4, column=0, columnspan=3, sticky="nsew", padx=10, pady=(0, 10))
        self.history_tree.bind("<<TreeviewSelect>>", self._preview_history_entry)
        frame.grid_rowconfigure(4, weight=1)
        frame.grid_columnconfigure(1, weight=1)

    def _build_history_tab(self) -> None:
        frame = ttk.LabelFrame(self._create_scrollable_area(self.history_tab), text="Historial de certificados concatenados")
        frame.pack(fill="both", expand=True, padx=12, pady=10)

        actions = ttk.Frame(frame)
        actions.pack(fill="x", padx=10, pady=(10, 6))
        ttk.Button(actions, text="Ver archivo", command=self._view_selected_bundle_history_file).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Eliminar selección", command=self._delete_bundle_history_entry).pack(side="left")

        self.bundle_history_tree = ttk.Treeview(frame, columns=("id", "name", "kind", "path", "status", "fecha"), show="headings", height=16)
        self.bundle_history_tree.column("id", width=0, stretch=False)
        self.bundle_history_tree.heading("id", text="ID")
        self.bundle_history_tree.heading("name", text="Nombre")
        self.bundle_history_tree.heading("kind", text="Tipo")
        self.bundle_history_tree.heading("path", text="Ruta")
        self.bundle_history_tree.heading("status", text="Estado")
        self.bundle_history_tree.heading("fecha", text="Fecha")
        self.bundle_history_tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.bundle_history_tree.bind("<<TreeviewSelect>>", self._preview_bundle_history_entry)

    def _build_concat_tab(self) -> None:
        frame = ttk.LabelFrame(self._create_scrollable_area(self.concat_tab), text="Concatenar archivos de solicitud y certificados")
        frame.pack(fill="both", expand=True, padx=12, pady=10)

        actions = ttk.Frame(frame)
        actions.pack(fill="x", padx=10, pady=10)
        ttk.Button(actions, text="Agregar archivos", command=self._add_concat_files).pack(side="left", padx=6)
        ttk.Button(actions, text="Ver archivo", command=self._view_concat_selection).pack(side="left", padx=6)
        ttk.Button(actions, text="Limpiar lista", command=self._clear_concat_files).pack(side="left", padx=6)
        ttk.Button(actions, text="Generar concatenado", command=self._concatenate_selected_files).pack(side="left", padx=6)

        self.concat_files = []
        self.concat_listbox = tk.Listbox(frame, height=18, width=140)
        self.concat_listbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        output_frame = ttk.Frame(frame)
        output_frame.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Label(output_frame, text="Destino del resultado:").pack(side="left")
        self.concat_output_path = tk.StringVar(value="")
        ttk.Entry(output_frame, textvariable=self.concat_output_path, width=70).pack(side="left", padx=8)
        self.concat_extension_var = tk.StringVar(value=".pem")
        ttk.Combobox(output_frame, textvariable=self.concat_extension_var, values=[".pem", ".cert"], state="readonly", width=8).pack(side="left", padx=(0, 8))
        ttk.Button(output_frame, text="Guardar destino", command=lambda: self._save_file(self.concat_output_path, default_name=build_bundle_filename("combined", extension=self.concat_extension_var.get()))).pack(side="left", padx=6)

        self.concat_status = tk.StringVar(value="Lista vacía.")
        ttk.Label(frame, textvariable=self.concat_status, wraplength=1200).pack(fill="x", padx=10, pady=(0, 8))

    def _choose_key_dir(self) -> None:
        folder = filedialog.askdirectory(title="Seleccionar carpeta de destino")
        if folder:
            self.key_dir_var.set(folder)

    def _select_file(self, var: tk.StringVar, filetypes=None) -> None:
        if filetypes is None:
            filetypes = [("Todos", "*.*")]
        filename = filedialog.askopenfilename(title="Seleccionar archivo", filetypes=filetypes)
        if filename:
            var.set(filename)

    def _select_csr_key(self) -> None:
        filename = filedialog.askopenfilename(
            title="Seleccionar clave privada",
            filetypes=[("KEY", "*.key"), ("PEM", "*.pem")],
        )
        if filename:
            self.csr_key_path.set(filename)
            self.csr_output_dir.set(os.path.dirname(filename))

    def _choose_csr_output_dir(self) -> None:
        folder = filedialog.askdirectory(title="Seleccionar carpeta de destino del CSR")
        if folder:
            self.csr_output_dir.set(folder)

    def _save_file(self, var: tk.StringVar, default_name: str) -> None:
        filename = filedialog.asksaveasfilename(title="Guardar archivo", initialfile=default_name, defaultextension="")
        if filename:
            var.set(filename)

    def _prompt_for_password(self, label: str, file_path: str) -> str | None:
        return simpledialog.askstring(
            "Contraseña requerida",
            f"Se necesita la contraseña para {label}:\n{file_path}",
            show="*",
        )

    def _is_encrypted_key_file(self, file_path: str) -> bool:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
        except Exception:
            return False
        return "BEGIN ENCRYPTED PRIVATE KEY" in text.upper()

    def _show_file_content_popup(self, title: str, file_path: str) -> None:
        if not file_path or not os.path.exists(file_path):
            return
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except Exception:
            try:
                with open(file_path, "rb") as fh:
                    content = fh.read(2000).decode("utf-8", errors="replace")
            except Exception:
                return

        popup = tk.Toplevel(self)
        popup.title(title)
        popup.geometry("820x520")
        popup.minsize(500, 300)
        popup.transient(self)
        popup.update_idletasks()
        try:
            if popup.winfo_viewable():
                popup.grab_set()
        except tk.TclError:
            pass

        text_widget = tk.Text(popup, wrap="word", font=("Segoe UI", 10))
        text_widget.insert("1.0", content)
        text_widget.configure(state="disabled")
        text_widget.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        scrollbar = ttk.Scrollbar(popup, orient="vertical", command=text_widget.yview)
        scrollbar.pack(fill="y", side="right")
        text_widget.configure(yscrollcommand=scrollbar.set)

        ttk.Button(popup, text="Cerrar", command=popup.destroy).pack(pady=10)

    def _preview_history_entry(self, event=None) -> None:
        selection = self.history_tree.selection()
        if not selection:
            return
        values = self.history_tree.item(selection[0], "values")
        if not values or len(values) < 4:
            return
        file_path = values[3]
        if file_path:
            self._show_file_content_popup(f"Contenido: {values[1]}", file_path)

    def _view_selected_history_file(self) -> None:
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("Historial", "Selecciona un registro para ver el archivo.")
            return
        file_path = self.history_tree.item(selection[0], "values")[3]
        if file_path:
            self._show_file_content_popup(f"Contenido: {self.history_tree.item(selection[0], 'values')[1]}", file_path)

    def _preview_bundle_history_entry(self, event=None) -> None:
        selection = self.bundle_history_tree.selection()
        if not selection:
            return
        values = self.bundle_history_tree.item(selection[0], "values")
        if not values or len(values) < 4:
            return
        file_path = values[3]
        if file_path:
            self._show_file_content_popup(f"Resultado concatenado: {values[1]}", file_path)

    def _view_selected_bundle_history_file(self) -> None:
        selection = self.bundle_history_tree.selection()
        if not selection:
            messagebox.showwarning("Historial concatenado", "Selecciona un registro para ver el archivo.")
            return
        file_path = self.bundle_history_tree.item(selection[0], "values")[3]
        if file_path:
            self._show_file_content_popup(f"Resultado concatenado: {self.bundle_history_tree.item(selection[0], 'values')[1]}", file_path)

    def _view_concat_selection(self) -> None:
        selection = self.concat_listbox.curselection()
        if not selection:
            messagebox.showwarning("Concatenación", "Selecciona un archivo de la lista para ver su contenido.")
            return
        file_path = self.concat_listbox.get(selection[0])
        self._show_file_content_popup(f"Vista previa: {os.path.basename(file_path)}", file_path)

    def _update_repo_combo(self) -> None:
        if hasattr(self, "repo_combo"):
            options = [item["name"] for item in self.repo.list_subjects()]
            self.repo_combo["values"] = options
            if options:
                if self.repo_select_var.get() not in options:
                    self.repo_select_var.set(options[0])
            else:
                self.repo_select_var.set("")

    def _apply_subject_from_repo(self, event=None) -> None:
        profile_name = self.repo_select_var.get().strip()
        if not profile_name:
            return
        subject = self.repo.get_subject(profile_name)
        if not subject:
            return
        for key, var in self.csr_subject_fields.items():
            if key == "email":
                value = subject.get("email", "") or subject.get("emailAddress", "")
            else:
                value = subject.get(key, "")
            var.set(value)

    def _generate_key(self) -> None:
        try:
            base_name = self.key_name_var.get().strip() or "server"
            folder = self.key_dir_var.get().strip() or os.getcwd()
            file_name = build_key_filename(base_name, bool(self.encrypted_key_var.get()))
            key_path = os.path.join(folder, file_name)
            password = self.key_password_var.get() if self.encrypted_key_var.get() else None
            generate_private_key(key_path, password=password, rsa_bits=int(self.rsa_bits_var.get()))
            self.key_status.set(f"Clave generada correctamente en: {key_path}")
            self._add_history_entry(base_name, "key", key_path, "generated")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
            self.key_status.set(f"Error: {exc}")

    def _generate_csr(self) -> None:
        try:
            key_path = self.csr_key_path.get()
            if not key_path:
                raise ValueError("Selecciona la clave privada antes de generar el CSR.")

            custom_name = self.csr_name_var.get().strip()
            custom_dir = ""
            if custom_name:
                custom_path = os.path.expanduser(custom_name)
                file_name = os.path.basename(custom_path)
                base_name = os.path.splitext(file_name)[0]
                custom_dir = os.path.dirname(custom_path)
            else:
                base_name = os.path.splitext(os.path.basename(key_path))[0]
            output_dir = self.csr_output_dir.get().strip() or custom_dir or os.path.dirname(key_path) or os.getcwd()
            output_path = os.path.join(output_dir, build_csr_filename(base_name))

            subject = {
                "C": self.csr_subject_fields["C"].get(),
                "ST": self.csr_subject_fields["ST"].get(),
                "L": self.csr_subject_fields["L"].get(),
                "O": self.csr_subject_fields["O"].get(),
                "OU": self.csr_subject_fields["OU"].get(),
                "CN": self.csr_subject_fields["CN"].get(),
                "emailAddress": self.csr_subject_fields["email"].get(),
            }
            generate_csr(key_path, output_path, subject, password=self.csr_password_var.get() or None)
            self.csr_status.set(f"CSR generado en: {output_path}")
            self._add_history_entry(os.path.splitext(os.path.basename(output_path))[0], "csr", output_path, "generated")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
            self.csr_status.set(f"Error: {exc}")

    def _remove_key_password(self) -> None:
        try:
            source = self.remove_key_input.get()
            if not source:
                raise ValueError("Selecciona la clave cifrada a convertir.")
            source_name = os.path.basename(source)
            base_name = os.path.splitext(source_name)[0]
            if "_pass" in base_name.lower():
                base_name = base_name.replace("_pass", "")
                target_name = f"{base_name}_nopass.key"
            elif "_nopass" in base_name.lower():
                target_name = f"{base_name}.key"
            elif "_no_pass" in base_name.lower():
                target_name = f"{base_name}_nopass.key"
            else:
                target_name = f"{base_name}_nopass.key"

            destination = self.remove_key_output.get()
            if not destination:
                destination = os.path.join(os.path.dirname(source), target_name)

            remove_key_password(source, destination, password=self.remove_key_password.get() or None)
            self.remove_key_status.set(f"Contraseña eliminada. Nueva clave: {destination}")
            self._add_history_entry(os.path.splitext(os.path.basename(destination))[0], "key", destination, "unencrypted")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
            self.remove_key_status.set(f"Error: {exc}")

    def _save_subject_to_repo(self) -> None:
        subject = {key: var.get() for key, var in self.repo_fields.items()}
        if not subject.get("name"):
            messagebox.showwarning("Repositorios", "Debe indicar un nombre para el perfil.")
            return
        try:
            self.repo.add_subject(subject)
            self._update_repo_combo()
            self._refresh_repo_list()
            messagebox.showinfo("Repositorio", "Perfil guardado correctamente.")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def _delete_subject_from_repo(self) -> None:
        selection = self.repo_list.curselection()
        if not selection:
            messagebox.showwarning("Repositorio", "Selecciona un perfil para eliminarlo.")
            return
        name = self.repo_list.get(selection[0]).split(" | ")[0]
        self.repo.delete_subject(name)
        self._update_repo_combo()
        self._refresh_repo_list()

    def _refresh_repo_list(self) -> None:
        self.repo_list.delete(0, tk.END)
        for item in self.repo.list_subjects():
            self.repo_list.insert(tk.END, f"{item['name']} | CN={item.get('CN','')} | O={item.get('O','')}")

    def _repo_selection_changed(self, event=None) -> None:
        selection = self.repo_list.curselection()
        if not selection:
            return
        name = self.repo_list.get(selection[0]).split(" | ")[0]
        subject = self.repo.get_subject(name)
        if subject:
            for key, var in self.repo_fields.items():
                var.set(subject.get(key, ""))

    def _export_repo_backup(self) -> None:
        path = filedialog.asksaveasfilename(title="Exportar respaldo CSV", initialfile="subject_backup.csv", defaultextension=".csv")
        if not path:
            return
        export_path = self.repo.export_csv(path)
        messagebox.showinfo("Exportación", f"Copia de seguridad exportada en: {export_path}")

    def _import_repo_backup(self) -> None:
        path = filedialog.askopenfilename(title="Importar CSV", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        count = self.repo.import_csv(path)
        self._update_repo_combo()
        self._refresh_repo_list()
        messagebox.showinfo("Importación", f"Se importaron {count} perfiles desde CSV.")

    def _verify_keys(self) -> None:
        try:
            files = [
                (self.verify_file_a.get(), self.verify_password_a, "Archivo A"),
                (self.verify_file_b.get(), self.verify_password_b, "Archivo B"),
            ]
            for file_path, password_var, label in files:
                if not file_path:
                    continue
                if self._is_encrypted_key_file(file_path):
                    current_password = password_var.get().strip()
                    if not current_password:
                        current_password = self._prompt_for_password(label, file_path)
                        if current_password is None:
                            raise ValueError(f"Se requiere la contraseña para {label}: {file_path}")
                        password_var.set(current_password)

            result = verify_key_pair_match(
                self.verify_file_a.get(),
                self.verify_file_b.get(),
                password_a=self.verify_password_a.get() or None,
                password_b=self.verify_password_b.get() or None,
            )
            if result:
                self.verify_status.set("Coincidencia correcta: las llaves pertenecen al mismo par.")
            else:
                self.verify_status.set("Error: las llaves no coinciden o no pertenecen al mismo par.")
        except Exception as exc:
            self.verify_status.set(f"Error: {exc}")
            messagebox.showerror("Verificación", str(exc))

    def _normalize_certificate(self) -> None:
        try:
            source = self.cert_input_path.get().strip()
            if not source:
                raise ValueError("Selecciona un archivo de certificado antes de normalizarlo.")
            if not self.cert_output_name.get().strip():
                base_name = os.path.splitext(os.path.basename(source))[0]
                output = os.path.join(os.path.dirname(source), build_cert_filename(base_name))
            else:
                output = self.cert_output_name.get()
            normalized = normalize_certificate_file(source, output)
            self.cert_status.set(f"Certificado normalizado en: {normalized}")
            self._add_history_entry(os.path.splitext(os.path.basename(normalized))[0], "cert", normalized, "normalized")
            self._refresh_history()
        except Exception as exc:
            self.cert_status.set(f"Error: {exc}")
            messagebox.showerror("Formato", str(exc))

    def _add_concat_files(self) -> None:
        files = filedialog.askopenfilenames(
            title="Seleccionar archivos a concatenar",
            filetypes=[
                ("Certificados y solicitudes", "*.pem;*.csr;*.cer;*.crt;*.cert;*.key;*.txt"),
                ("PEM", "*.pem"),
                ("CSR", "*.csr"),
                ("CER", "*.cer"),
                ("CRT", "*.crt"),
                ("CERT", "*.cert"),
                ("KEY", "*.key"),
                ("Todos", "*.*"),
            ],
        )
        if not files:
            return
        for item in files:
            if item not in self.concat_files:
                self.concat_files.append(item)
                self.concat_listbox.insert(tk.END, item)
        self.concat_status.set(f"{len(self.concat_files)} archivo(s) cargado(s).")

    def _clear_concat_files(self) -> None:
        self.concat_files = []
        self.concat_listbox.delete(0, tk.END)
        self.concat_status.set("Lista vacía.")

    def _concatenate_selected_files(self) -> None:
        if not self.concat_files:
            messagebox.showwarning("Concatenación", "Selecciona al menos un archivo para combinar.")
            return
        if not self.concat_output_path.get().strip():
            default_name = build_bundle_filename("combined", extension=self.concat_extension_var.get())
            output = os.path.join(os.getcwd(), default_name)
        else:
            output = self.concat_output_path.get()
            if os.path.splitext(output)[1].lower() not in {".pem", ".cert"}:
                output = f"{os.path.splitext(output)[0]}{self.concat_extension_var.get()}"
        try:
            final_path = concatenate_files(self.concat_files, output)
            self.concat_status.set(f"Concatenación completada. Resultado: {final_path}")
            self._add_history_entry(os.path.splitext(os.path.basename(final_path))[0], "bundle", final_path, "concatenated")
            self._refresh_history()
        except Exception as exc:
            messagebox.showerror("Concatenación", str(exc))
            self.concat_status.set(f"Error: {exc}")

    def _add_history_entry(self, name: str, kind: str, path: str, status: str) -> None:
        self.history.add_entry(name, kind, path, status)
        self._refresh_history()

    def _edit_history_entry(self) -> None:
        if not hasattr(self, "history_tree"):
            return
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("Historial", "Selecciona un registro para editar.")
            return
        entry_id = self.history_tree.item(selection[0], "values")[0]
        existing = next((row for row in self.history.list_entries() if row["id"] == entry_id), None)
        if not existing:
            return

        updated_name = simpledialog.askstring("Editar historial", "Nombre:", initialvalue=existing["name"])
        if updated_name is None:
            return
        updated_path = simpledialog.askstring("Editar historial", "Ruta:", initialvalue=existing["path"])
        if updated_path is None:
            return
        updated_status = simpledialog.askstring("Editar historial", "Estado:", initialvalue=existing["status"])
        if updated_status is None:
            return

        self.history.update_entry(entry_id, updated_name, existing["kind"], updated_path, updated_status)
        self._refresh_history()

    def _delete_bundle_history_entry(self) -> None:
        if not hasattr(self, "bundle_history_tree"):
            return
        selection = self.bundle_history_tree.selection()
        if not selection:
            messagebox.showwarning("Historial concatenado", "Selecciona un registro para eliminar.")
            return

        entry_id = self.bundle_history_tree.item(selection[0], "values")[0]
        record_name = self.bundle_history_tree.item(selection[0], "values")[1]
        confirm = messagebox.askyesno(
            "Confirmar eliminación",
            f"¿Deseas eliminar el registro '{record_name}' del historial de concatenados?",
        )
        if not confirm:
            return

        self.history.delete_entry(entry_id)
        self._refresh_history()

    def _delete_history_entry(self) -> None:
        if not hasattr(self, "history_tree"):
            return
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("Historial", "Selecciona un registro para eliminar.")
            return
        entry_id = self.history_tree.item(selection[0], "values")[0]
        record_name = self.history_tree.item(selection[0], "values")[1]
        confirm = messagebox.askyesno(
            "Confirmar eliminación",
            f"¿Deseas eliminar el registro '{record_name}' del historial general?",
        )
        if not confirm:
            return
        self.history.delete_entry(entry_id)
        self._refresh_history()

    def _refresh_history(self) -> None:
        if hasattr(self, "history_tree"):
            for item in self.history_tree.get_children():
                self.history_tree.delete(item)
            entries = self.history.list_entries()
            for row in entries:
                self.history_tree.insert("", "end", values=(row["id"], row["name"], row["kind"], row["path"], row["status"], row["created_at"]))

        if hasattr(self, "bundle_history_tree"):
            for item in self.bundle_history_tree.get_children():
                self.bundle_history_tree.delete(item)
            entries = self.history.list_entries_by_kind("bundle")
            for row in entries:
                self.bundle_history_tree.insert("", "end", values=(row["id"], row["name"], row["kind"], row["path"], row["status"], row["created_at"]))


def main() -> None:
    app = CertsPyGeneratorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
