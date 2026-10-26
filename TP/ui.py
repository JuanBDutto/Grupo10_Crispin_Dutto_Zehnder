import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QComboBox, 
                             QLabel, QScrollArea, QFrame, QMessageBox, QDialog,
                             QTableWidget, QTableWidgetItem, QFileDialog,
                             QInputDialog, QAbstractItemView)
from PyQt6.QtCore import Qt
from motor import SegundoCerebro


class DialogoApps(QDialog):
    def __init__(self, motor, parent=None):
        super().__init__(parent)
        self.motor = motor
        self.setWindowTitle("Aplicaciones Predeterminadas")
        self.resize(650, 380)

        layout = QVBoxLayout(self)

        self.tabla = QTableWidget(0, 2)
        self.tabla.setHorizontalHeaderLabels(["Extensión", "Programa"])
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.tabla)

        layout_botones = QHBoxLayout()
        self.btn_agregar = QPushButton("Agregar")
        self.btn_agregar.clicked.connect(self.agregar_app)
        layout_botones.addWidget(self.btn_agregar)

        self.btn_cambiar = QPushButton("Cambiar programa")
        self.btn_cambiar.clicked.connect(self.cambiar_programa)
        layout_botones.addWidget(self.btn_cambiar)

        self.btn_quitar = QPushButton("Quitar")
        self.btn_quitar.clicked.connect(self.quitar_app)
        layout_botones.addWidget(self.btn_quitar)

        layout_botones.addStretch()

        self.btn_cerrar = QPushButton("Cerrar")
        self.btn_cerrar.clicked.connect(self.accept)
        layout_botones.addWidget(self.btn_cerrar)

        layout.addLayout(layout_botones)
        self.cargar_tabla()

    def cargar_tabla(self):
        apps = self.motor.obtener_apps_predeterminadas()
        self.tabla.setRowCount(0)
        for fila, (ext, prog) in enumerate(apps.items()):
            self.tabla.insertRow(fila)
            self.tabla.setItem(fila, 0, QTableWidgetItem(ext))
            self.tabla.setItem(fila, 1, QTableWidgetItem(prog))

    def elegir_ejecutable(self, titulo="Seleccionar ejecutable"):
        ruta, _ = QFileDialog.getOpenFileName(self, titulo)
        return ruta

    def agregar_app(self):
        texto_ext, ok = QInputDialog.getText(
            self, "Agregar Extensión", "Extensión(es) (ej: .py o .py, .js):"
        )
        if not ok or not texto_ext.strip():
            return

        programa = self.elegir_ejecutable("Seleccionar programa para la extensión")
        if not programa:
            return

        exito, mensaje = self.motor.asignar_app_a_extensiones(texto_ext, programa)
        if exito:
            self.cargar_tabla()
        else:
            QMessageBox.warning(self, "Error", mensaje)

    def cambiar_programa(self):
        filas = self.tabla.selectionModel().selectedRows()
        if not filas:
            QMessageBox.warning(self, "Aviso", "Selecciona al menos una extensión de la tabla.")
            return

        extensiones = [self.tabla.item(f.row(), 0).text() for f in filas]
        programa = self.elegir_ejecutable(f"Seleccionar programa para {', '.join(extensiones)}")
        if not programa:
            return

        exito, mensaje = self.motor.asignar_app_a_extensiones(extensiones, programa)
        if exito:
            self.cargar_tabla()
        else:
            QMessageBox.warning(self, "Error", mensaje)

    def quitar_app(self):
        filas = self.tabla.selectionModel().selectedRows()
        if not filas:
            QMessageBox.warning(self, "Aviso", "Selecciona una extensión de la tabla para quitar.")
            return

        for f in filas:
            ext = self.tabla.item(f.row(), 0).text()
            exito, mensaje = self.motor.quitar_app_de_extension(ext)
            if not exito:
                QMessageBox.warning(self, "Error", mensaje)
        self.cargar_tabla()

class DialogoDirectorios(QDialog):
    def __init__(self, motor, parent=None):
        super().__init__(parent)
        self.motor = motor
        self.setWindowTitle("Directorios Indexados")
        self.resize(600, 320)

        layout = QVBoxLayout(self)

        self.tabla = QTableWidget(0, 1)
        self.tabla.setHorizontalHeaderLabels(["Ruta del Directorio"])
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.tabla)

        layout_botones = QHBoxLayout()
        
        self.btn_eliminar = QPushButton("🗑️ Eliminar y Desindexar")
        self.btn_eliminar.clicked.connect(self.eliminar_directorio)
        layout_botones.addWidget(self.btn_eliminar)

        layout_botones.addStretch()

        self.btn_cerrar = QPushButton("Cerrar")
        self.btn_cerrar.clicked.connect(self.accept)
        layout_botones.addWidget(self.btn_cerrar)

        layout.addLayout(layout_botones)
        self.cargar_tabla()

    def cargar_tabla(self):
        directorios = self.motor.config.get("directorios", [])
        self.tabla.setRowCount(0)
        for fila, ruta in enumerate(directorios):
            self.tabla.insertRow(fila)
            self.tabla.setItem(fila, 0, QTableWidgetItem(ruta))

    def eliminar_directorio(self):
        filas = self.tabla.selectionModel().selectedRows()
        if not filas:
            QMessageBox.warning(self, "Aviso", "Selecciona al menos un directorio para eliminar.")
            return

        self.btn_eliminar.setText("⏳ Desindexando...")
        self.btn_eliminar.setEnabled(False)
        QApplication.processEvents()

        for f in filas:
            ruta = self.tabla.item(f.row(), 0).text()
            exito, mensaje = self.motor.eliminar_directorio_indice(ruta)
            if exito:
                QMessageBox.information(self, "Directorio Eliminado", mensaje)
            else:
                QMessageBox.warning(self, "Error", mensaje)

        self.btn_eliminar.setText("🗑️ Eliminar y Desindexar")
        self.btn_eliminar.setEnabled(True)
        self.cargar_tabla()

class InterfazCerebro(QMainWindow):
    def __init__(self):
        super().__init__()
        self.motor = SegundoCerebro()

        self.setWindowTitle("Segundo Cerebro - Buscador Local")
        self.resize(850, 650)

        widget_principal = QWidget()
        layout_principal = QVBoxLayout()
        widget_principal.setLayout(layout_principal)
        self.setCentralWidget(widget_principal)

        # --- PANEL SUPERIOR: BÚSQUEDA ---
        layout_busqueda = QHBoxLayout()
        
        self.entrada_busqueda = QLineEdit()
        self.entrada_busqueda.setPlaceholderText("Escribe las palabras a buscar...")
        self.entrada_busqueda.returnPressed.connect(self.ejecutar_busqueda)
        layout_busqueda.addWidget(self.entrada_busqueda)

        self.btn_buscar = QPushButton("🔍 Buscar")
        self.btn_buscar.clicked.connect(self.ejecutar_busqueda)
        layout_busqueda.addWidget(self.btn_buscar)

        self.combo_filtro = QComboBox()
        self.combo_filtro.addItems(["Todos", ".pdf", ".docx", ".txt", ".py", ".js", ".html"])
        layout_busqueda.addWidget(self.combo_filtro)

        self.btn_reindexar = QPushButton("↻ Reindexar Todo")
        self.btn_reindexar.clicked.connect(self.reindexar)
        layout_busqueda.addWidget(self.btn_reindexar)

        self.btn_apps = QPushButton("⚙ Aplicaciones")
        self.btn_apps.clicked.connect(self.abrir_dialogo_apps)
        layout_busqueda.addWidget(self.btn_apps)

        self.btn_intervalo = QPushButton("⏱ Intervalo")
        self.btn_intervalo.clicked.connect(self.cambiar_intervalo)
        layout_busqueda.addWidget(self.btn_intervalo)

        layout_principal.addLayout(layout_busqueda)

        # --- PANEL SECUNDARIO: AGREGAR DIRECTORIO ---
        layout_directorios = QHBoxLayout()
        
        self.entrada_directorio = QLineEdit()
        self.entrada_directorio.setPlaceholderText("Pega aquí la ruta del directorio (Ej: C:/Mis Apuntes)")
        self.entrada_directorio.returnPressed.connect(self.agregar_directorio)
        layout_directorios.addWidget(self.entrada_directorio)
        
        self.btn_agregar_dir = QPushButton("➕ Indexar Nuevo Directorio")
        self.btn_agregar_dir.clicked.connect(self.agregar_directorio)
        layout_directorios.addWidget(self.btn_agregar_dir)

        self.btn_gestionar_dirs = QPushButton("📂 Ver / Eliminar Directorios")
        self.btn_gestionar_dirs.clicked.connect(self.abrir_dialogo_directorios)
        layout_directorios.addWidget(self.btn_gestionar_dirs)

        layout_principal.addLayout(layout_directorios)

        # --- PANEL CENTRAL: RESULTADOS ---
        self.area_scroll = QScrollArea()
        self.area_scroll.setWidgetResizable(True)
        
        self.contenedor_resultados = QWidget()
        self.layout_resultados = QVBoxLayout()
        self.layout_resultados.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.contenedor_resultados.setLayout(self.layout_resultados)
        
        self.area_scroll.setWidget(self.contenedor_resultados)
        layout_principal.addWidget(self.area_scroll)

    def agregar_directorio(self):
        """Valida que la ruta exista, la agrega al config e indexa"""
        ruta = self.entrada_directorio.text().strip(' "')
        if not ruta:
            return
            
        # 1. Comprobación temprana en la Interfaz
        if not os.path.exists(ruta):
            # Muestra un popup de error si la ruta no existe
            QMessageBox.warning(self, "Ruta Inválida", f"El directorio no existe en tu computadora:\n{ruta}")
            return
            
        # 2. Feedback visual de carga
        self.btn_agregar_dir.setText("⏳ Indexando...")
        self.btn_agregar_dir.setEnabled(False)
        QApplication.processEvents()
        
        # 3. Llamada al motor
        exito, mensaje = self.motor.agregar_e_indexar_ruta(ruta)
        
        # 4. Restaurar botón y mostrar resultado
        self.btn_agregar_dir.setText("➕ Indexar Nuevo Directorio")
        self.btn_agregar_dir.setEnabled(True)
        
        if exito:
            QMessageBox.information(self, "Operación Exitosa", mensaje)
            self.entrada_directorio.clear()
        else:
            QMessageBox.warning(self, "Error", mensaje)

    def reindexar(self):
        self.btn_reindexar.setText("⏳ Reindexando...")
        self.btn_reindexar.setEnabled(False)
        QApplication.processEvents() 
        
        self.motor.forzar_reindexacion()
        
        self.btn_reindexar.setText("↻ Reindexar Todo")
        self.btn_reindexar.setEnabled(True)

    def abrir_dialogo_apps(self):
        dialogo = DialogoApps(self.motor, self)
        dialogo.exec()

    def abrir_dialogo_directorios(self):
        dialogo = DialogoDirectorios(self.motor, self)
        dialogo.exec()

    def cambiar_intervalo(self):
        intervalo_actual = self.motor.config.get("intervalo_minutos", 5)
        nuevo_valor, ok = QInputDialog.getInt(
            self,
            "Intervalo de Indexación",
            "Indexar automáticamente cada (minutos):",
            value=intervalo_actual,
            min=1,
            max=1440
        )
        if not ok:
            return

        exito, mensaje = self.motor.modificar_intervalo_minutos(nuevo_valor)
        if exito:
            QMessageBox.information(self, "Intervalo Actualizado", mensaje)
        else:
            QMessageBox.warning(self, "Error", mensaje)

    def abrir_archivo_con(self, ruta):
        ruta_real = ruta.split("?parte=")[0]
        ext = os.path.splitext(ruta_real)[1].lower()
        programa, _ = QFileDialog.getOpenFileName(
            self, f"Seleccionar programa para {ext or 'el archivo'}"
        )
        if not programa:
            return

        exito, mensaje = self.motor.asignar_app_a_extensiones([ext], programa)
        if not exito:
            QMessageBox.warning(self, "Error", mensaje)
            return

        self.motor.abrir_archivo(ruta)

    def limpiar_resultados(self):
        while self.layout_resultados.count():
            item = self.layout_resultados.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def ejecutar_busqueda(self):
        # Ahora toma directamente el texto de la barra principal
        consulta = self.entrada_busqueda.text().strip()
        if not consulta:
            return

        self.limpiar_resultados()
        
        filtro = self.combo_filtro.currentText()
        resultados = self.motor.buscar(consulta, filtro_ext=filtro)
        
        if not resultados:
            lbl_vacio = QLabel(f"❌ No se encontraron documentos para: '{consulta}'")
            lbl_vacio.setStyleSheet("color: gray; font-size: 14px;")
            self.layout_resultados.addWidget(lbl_vacio)
            return
            
        # --- APERTURA AUTOMÁTICA (Si hay 1 solo resultado) ---
        if len(resultados) == 1:
            self.motor.abrir_archivo(resultados[0]['ruta'])
            
        # Dibujamos las tarjetas visuales
        for res in resultados:
            frame = QFrame()
            frame.setFrameShape(QFrame.Shape.Box) 
            layout_item = QHBoxLayout()
            frame.setLayout(layout_item)
            
            lbl_titulo = QLabel(f"📄 {res['titulo']}")
            lbl_titulo.setStyleSheet("font-weight: bold; font-size: 14px;")
            layout_item.addWidget(lbl_titulo)
            
            ruta_corta = res['ruta'][:60] + "..." if len(res['ruta']) > 60 else res['ruta']
            lbl_ruta = QLabel(ruta_corta)
            lbl_ruta.setStyleSheet("color: gray;")
            layout_item.addWidget(lbl_ruta)
            
            layout_item.addStretch()
            
            btn_abrir = QPushButton("Abrir archivo")
            btn_abrir.clicked.connect(lambda checked, r=res['ruta']: self.motor.abrir_archivo(r))
            layout_item.addWidget(btn_abrir)

            btn_abrir_con = QPushButton("Abrir con…")
            btn_abrir_con.clicked.connect(lambda checked, r=res['ruta']: self.abrir_archivo_con(r))
            layout_item.addWidget(btn_abrir_con)
            
            self.layout_resultados.addWidget(frame)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion") 
    ventana = InterfazCerebro()
    ventana.show()
    sys.exit(app.exec())