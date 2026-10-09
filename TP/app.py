import os
import json
import time
import threading
import subprocess
import platform
import schedule
import questionary
import fitz  # PyMuPDF
import docx  # python-docx

from whoosh.index import create_in, open_dir, exists_in
from whoosh.fields import Schema, TEXT, ID
from whoosh.qparser import QueryParser
from whoosh.analysis import LanguageAnalyzer
from whoosh.analysis import RegexTokenizer, LowercaseFilter, StopFilter, StemFilter
from whoosh.fields import Schema, TEXT, ID, STORED

class SegundoCerebro:
    def __init__(self, config_path="config.json"):
        self.cargar_config(config_path)
        self.dir_indice = "indice_cerebro"
        
        self._inicializar_whoosh()
        
        # Iniciar la primera indexación al abrir el programa
        self.ejecutar_indexacion()
        
        # Configurar la tarea programada
        schedule.every(self.config['intervalo_minutos']).minutes.do(self.ejecutar_indexacion)
        self.iniciar_hilo_background()
        
    def indexar_txt_por_fragmentos(self, writer, ruta, archivo, mtime_actual, lineas_por_chunk=5000):
        """Lee un archivo gigante línea por línea y lo guarda en bloques ligeros."""
        try:
            # errors='ignore' evita que el programa falle si hay caracteres extraños
            with open(ruta, 'r', encoding='utf-8', errors='ignore') as f:
                chunk = []
                numero_parte = 1
                
                for linea in f:
                    chunk.append(linea)
                    
                    if len(chunk) >= lineas_por_chunk:
                        contenido = "".join(chunk)
                        # El truco: Hacemos la ruta única agregando el número de parte
                        writer.update_document(
                            titulo=f"{archivo} (Parte {numero_parte})", 
                            ruta=f"{ruta}?parte={numero_parte}",  
                            contenido=contenido,
                            mtime=mtime_actual
                        )
                        chunk = [] # Vaciamos la memoria RAM
                        numero_parte += 1
                        
                # Guardamos lo que haya sobrado al final del archivo
                if chunk:
                    contenido = "".join(chunk)
                    writer.update_document(
                        titulo=f"{archivo} (Parte {numero_parte})", 
                        ruta=f"{ruta}?parte={numero_parte}", 
                        contenido=contenido,
                        mtime=mtime_actual
                    )
        except Exception as e:
            print(f"Error procesando {archivo}: {e}")

    def cargar_config(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

    def _inicializar_whoosh(self):
        analizador_codigo = (
            RegexTokenizer(r"[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ]+") | 
            LowercaseFilter() | 
            StopFilter(lang="es") | 
            StemFilter(lang="es")
        )

        esquema = Schema(
            titulo=TEXT(stored=True),
            ruta=ID(stored=True, unique=True), 
            contenido=TEXT(analyzer=analizador_codigo, stored=True),
            mtime=STORED() # <-- NUEVO: Guardará la marca de tiempo
        )
    
        if not os.path.exists(self.dir_indice):
            os.mkdir(self.dir_indice)
            self.indice = create_in(self.dir_indice, esquema)
        else:
            self.indice = open_dir(self.dir_indice)

    # --- EXTRACTORES DE TEXTO ---
    def extraer_pdf(self, ruta):
        texto = ""
        try:
            with fitz.open(ruta) as doc:
                for pagina in doc: texto += pagina.get_text() + " \n"
        except: pass
        return texto

    def extraer_docx(self, ruta):
        try:
            doc = docx.Document(ruta)
            return '\n'.join([p.text for p in doc.paragraphs])
        except: return ""

    def extraer_texto_plano(self, ruta):
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                return f.read()
        except: return ""

# --- LÓGICA DE INDEXACIÓN ---
    def ejecutar_indexacion(self):
        archivos_conocidos = {}
        with self.indice.searcher() as searcher:
            for campos in searcher.all_stored_fields():
                ruta_indexada = campos.get('ruta')
                # Obtenemos la ruta real (le quitamos el "?parte=...")
                ruta_real = ruta_indexada.split("?parte=")[0]
                archivos_conocidos[ruta_real] = campos.get('mtime', 0)

        writer = self.indice.writer()
        exts_codigo = self.config.get("extensiones_codigo", [])
        
        # --- Fase de Limpieza ---
        with self.indice.searcher() as searcher:
            for campos in searcher.all_stored_fields():
                ruta_indexada = campos.get('ruta')
                ruta_real = ruta_indexada.split("?parte=")[0]
                
                if not os.path.exists(ruta_real):
                    writer.delete_by_term('ruta', ruta_indexada)
                    print(f"🗑️ Limpiando: {ruta_indexada}")

        # --- Fase de Indexación ---
        for carpeta in self.config["directorios"]:
            if not os.path.exists(carpeta): continue
            
            for raiz, _, archivos in os.walk(carpeta):
                for archivo in archivos:
                    ruta = os.path.join(raiz, archivo)
                    ext = os.path.splitext(archivo)[1].lower()
                    
                    mtime_actual = os.path.getmtime(ruta)
                    if ruta in archivos_conocidos and mtime_actual <= archivos_conocidos[ruta]:
                        continue 
                    
                    # --- NUEVO FLUJO ---
                    if ext == '.pdf': 
                        contenido = self.extraer_pdf(ruta)
                    elif ext == '.docx': 
                        contenido = self.extraer_docx(ruta)
                    elif ext == '.txt' or ext in exts_codigo: 
                        # Delegamos los TXT y Código a nuestra nueva función que usa poca RAM
                        self.indexar_txt_por_fragmentos(writer, ruta, archivo, mtime_actual)
                        print(f"✅ Indexado por fragmentos: {archivo}")
                        continue # Pasamos al siguiente archivo
                    else:
                        continue

                    if contenido.strip():
                        writer.update_document(
                            titulo=archivo, ruta=ruta, contenido=contenido, mtime=mtime_actual
                        )
                        print(f"✅ Indexado: {archivo}")
                        
        writer.commit()

    def iniciar_hilo_background(self):
        """Ejecuta el planificador en un hilo separado para no bloquear la consola"""
        def correr_schedule():
            while True:
                schedule.run_pending()
                time.sleep(1)
                
        hilo = threading.Thread(target=correr_schedule, daemon=True)
        hilo.start()

    # --- LÓGICA DE BÚSQUEDA Y CLI ---
    def buscar(self, query_str):
        parser = QueryParser("contenido", schema=self.indice.schema)
        try:
            consulta = parser.parse(query_str)
        except: return []

        resultados = []
        with self.indice.searcher() as searcher:
            hits = searcher.search(consulta, limit=20) # Limitamos a los mejores 20
            for hit in hits:
                resultados.append({"titulo": hit["titulo"], "ruta": hit["ruta"]})
        return resultados

    def abrir_archivo(self, ruta):
        # Limpiamos el sufijo del fragmento para recuperar la ruta real
        ruta_real = ruta.split("?parte=")[0]
        
        print(f"\nAbriendo: {ruta_real} ...")
        if platform.system() == 'Windows':
            os.startfile(ruta_real)
        elif platform.system() == 'Darwin':
            subprocess.call(('open', ruta_real))
        else:
            subprocess.call(('xdg-open', ruta_real))

    def iniciar_cli(self):
        print("\n--- SEGUNDO CEREBRO ---")
        print("Motor listo. Escribe tu búsqueda (o 'salir' para cerrar).")
        
        while True:
            query = input("\n🔍 Buscar: ").strip()
            if query.lower() in ['salir', 'exit', 'quit']:
                break
            if not query: continue

            resultados = self.buscar(query)
            
            if len(resultados) == 0:
                print("❌ No se encontraron documentos.")
                
            elif len(resultados) == 1:
                self.abrir_archivo(resultados[0]["ruta"])
                
            else:
                # Menú interactivo con flechas usando questionary
                opciones = [f"📄 {r['titulo']}  ({r['ruta']})" for r in resultados]
                opciones.append("❌ Cancelar")
                
                eleccion = questionary.select(
                    f"Se encontraron {len(resultados)} resultados. Selecciona uno:",
                    choices=opciones
                ).ask()
                
                if eleccion and eleccion != "❌ Cancelar":
                    # Recuperamos la ruta original buscando qué resultado coincide con la elección
                    indice_elegido = opciones.index(eleccion)
                    self.abrir_archivo(resultados[indice_elegido]["ruta"])

if __name__ == "__main__":
    app = SegundoCerebro()
    app.iniciar_cli()