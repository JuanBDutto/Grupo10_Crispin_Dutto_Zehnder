import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QComboBox, 
                             QLabel, QScrollArea, QFrame, QMessageBox)
from PyQt6.QtCore import Qt
from motor import SegundoCerebro

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
            
            self.layout_resultados.addWidget(frame)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion") 
    ventana = InterfazCerebro()
    ventana.show()
    sys.exit(app.exec())