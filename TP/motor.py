import os
import json
import time
import tempfile
import threading
import subprocess
import platform
import schedule

# Importamos las funciones del nuevo módulo
from extractores import extraer_pdf, extraer_docx, extraer_texto_plano

from whoosh.index import create_in, open_dir, exists_in
from whoosh.fields import Schema, TEXT, ID, STORED
from whoosh.qparser import QueryParser
from whoosh.analysis import RegexTokenizer, LowercaseFilter, StopFilter, StemFilter

class SegundoCerebro:
    def __init__(self, config_path="config.json"):
        self._lock_config = threading.Lock()
        self.cargar_config(config_path)
        self.dir_indice = "indice_cerebro"
        
        self._inicializar_whoosh()
        self.ejecutar_indexacion()
        
        schedule.every(self.config.get('intervalo_minutos', 5)).minutes.do(self.ejecutar_indexacion)
        self.iniciar_hilo_background()
        
    def cargar_config(self, path):
        self.config_path = os.path.abspath(path)
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

    def guardar_config(self):
        with self._lock_config:
            directorio = os.path.dirname(self.config_path) or "."
            fd, temp_path = tempfile.mkstemp(dir=directorio, suffix=".tmp", text=True)
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=4, ensure_ascii=False)
                os.replace(temp_path, self.config_path)
            except Exception:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise

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
            ext=ID(stored=True),
            contenido=TEXT(analyzer=analizador_codigo, stored=True),
            mtime=STORED() 
        )
    
        if not os.path.exists(self.dir_indice):
            os.mkdir(self.dir_indice)
            
        if exists_in(self.dir_indice):
            self.indice = open_dir(self.dir_indice)
        else:
            self.indice = create_in(self.dir_indice, esquema)

    def indexar_txt_por_fragmentos(self, writer, ruta, archivo, ext, mtime_actual, lineas_por_chunk=5000):
        try:
            with open(ruta, 'r', encoding='utf-8', errors='ignore') as f:
                chunk = []
                numero_parte = 1
                
                for linea in f:
                    chunk.append(linea)
                    if len(chunk) >= lineas_por_chunk:
                        contenido = "".join(chunk)
                        writer.update_document(
                            titulo=f"{archivo} (Parte {numero_parte})", 
                            ruta=f"{ruta}?parte={numero_parte}",  
                            ext=ext, contenido=contenido, mtime=mtime_actual
                        )
                        chunk = [] 
                        numero_parte += 1
                        
                if chunk:
                    contenido = "".join(chunk)
                    writer.update_document(
                        titulo=f"{archivo} (Parte {numero_parte})", 
                        ruta=f"{ruta}?parte={numero_parte}", 
                        ext=ext, contenido=contenido, mtime=mtime_actual
                    )
        except Exception as e:
            print(f"Error procesando {archivo}: {e}")

    def ejecutar_indexacion(self):
        archivos_conocidos = {}
        with self.indice.searcher() as searcher:
            for campos in searcher.all_stored_fields():
                ruta_indexada = campos.get('ruta')
                ruta_real = ruta_indexada.split("?parte=")[0]
                archivos_conocidos[ruta_real] = campos.get('mtime', 0)

        writer = self.indice.writer()
        exts_codigo = self.config.get("extensiones_codigo", [])
        
        with self.indice.searcher() as searcher:
            for campos in searcher.all_stored_fields():
                ruta_indexada = campos.get('ruta')
                ruta_real = ruta_indexada.split("?parte=")[0]
                if not os.path.exists(ruta_real):
                    writer.delete_by_term('ruta', ruta_indexada)
                    print(f"🗑️ Limpiando: {ruta_indexada}")

        for carpeta in self.config.get("directorios", []):
            if not os.path.exists(carpeta): continue
            
            for raiz, _, archivos in os.walk(carpeta):
                for archivo in archivos:
                    ruta = os.path.join(raiz, archivo)
                    ext = os.path.splitext(archivo)[1].lower()
                    
                    mtime_actual = os.path.getmtime(ruta)
                    if ruta in archivos_conocidos and mtime_actual <= archivos_conocidos[ruta]:
                        continue 
                    
                    if ext == '.pdf': contenido = extraer_pdf(ruta)
                    elif ext == '.docx': contenido = extraer_docx(ruta)
                    elif ext == '.txt' or ext in exts_codigo: 
                        self.indexar_txt_por_fragmentos(writer, ruta, archivo, ext, mtime_actual)
                        print(f"✅ Indexado por fragmentos: {archivo}")
                        continue 
                    else: continue

                    if contenido.strip():
                        writer.update_document(
                            titulo=archivo, ruta=ruta, ext=ext, contenido=contenido, mtime=mtime_actual
                        )
                        print(f"✅ Indexado: {archivo}")
        writer.commit()

    def forzar_reindexacion(self):
        print("Forzando indexación manual...")
        self.ejecutar_indexacion()
        print("Reindexación completada.")

    def agregar_e_indexar_ruta(self, nueva_ruta):
        nueva_ruta = nueva_ruta.replace("\\", "/")
        if not os.path.exists(nueva_ruta):
            return False, f"La ruta no existe: {nueva_ruta}"
            
        if nueva_ruta not in self.config.get("directorios", []):
            self.config.setdefault("directorios", []).append(nueva_ruta)
            self.guardar_config()
                
        self.ejecutar_indexacion()
        return True, f"Ruta indexada y guardada exitosamente:\n{nueva_ruta}"

    def obtener_apps_predeterminadas(self):
        return dict(self.config.get("apps_predeterminadas", {}))

    def asignar_app_a_extensiones(self, extensiones, programa):
        if isinstance(extensiones, str):
            lista_ext = [e for e in extensiones.replace(",", " ").split() if e.strip()]
        else:
            lista_ext = list(extensiones)

        exts_normalizadas = []
        for ext in lista_ext:
            ext_limpia = ext.strip().lower()
            if not ext_limpia or ext_limpia == ".":
                continue
            if not ext_limpia.startswith("."):
                ext_limpia = "." + ext_limpia
            exts_normalizadas.append(ext_limpia)

        if not exts_normalizadas:
            return False, "Debes indicar al menos una extensión válida."

        programa_limpio = (programa or "").strip().replace("\\", "/")
        if not programa_limpio or not os.path.isfile(programa_limpio):
            return False, f"El ejecutable no existe:\n{programa_limpio}"

        apps = self.config.setdefault("apps_predeterminadas", {})
        for ext in exts_normalizadas:
            apps[ext] = programa_limpio

        self.guardar_config()
        return True, f"Programa asignado a {', '.join(exts_normalizadas)}."

    def quitar_app_de_extension(self, extension):
        ext_limpia = (extension or "").strip().lower()
        if ext_limpia and not ext_limpia.startswith("."):
            ext_limpia = "." + ext_limpia

        apps = self.config.get("apps_predeterminadas", {})
        if ext_limpia not in apps:
            return False, f"La extensión '{ext_limpia}' no tiene una aplicación asignada."

        del apps[ext_limpia]
        self.guardar_config()
        return True, f"Se quitó la aplicación predeterminada para '{ext_limpia}'."

    def iniciar_hilo_background(self):
        def correr_schedule():
            while True:
                schedule.run_pending()
                time.sleep(1)
        hilo = threading.Thread(target=correr_schedule, daemon=True)
        hilo.start()

    def buscar(self, query_str, filtro_ext="Todos"):
        parser = QueryParser("contenido", schema=self.indice.schema)
        try: consulta = parser.parse(query_str)
        except: return []

        resultados = []
        with self.indice.searcher() as searcher:
            hits = searcher.search(consulta, limit=30)
            for hit in hits:
                if filtro_ext != "Todos" and hit.get("ext") != filtro_ext:
                    continue
                resultados.append({"titulo": hit["titulo"], "ruta": hit["ruta"], "ext": hit.get("ext")})
        return resultados

    def abrir_archivo(self, ruta):
        ruta_real = ruta.split("?parte=")[0]
        ext = os.path.splitext(ruta_real)[1].lower()
        apps_config = self.config.get("apps_predeterminadas", {})
        
        if ext in apps_config:
            programa = apps_config[ext]
            print(f"\nIntentando abrir con {programa}: {ruta_real}")
            try:
                subprocess.Popen([programa, ruta_real])
            except Exception as e:
                print(f"❌ Error: No se pudo abrir '{programa}'. Revisa tu config.json.")
                print(f"Detalle técnico: {e}")
                print("⚠️ Intentando abrir con el visor por defecto del sistema...")
                
                # Fallback: Si falla el programa custom, intentamos con el del sistema
                try:
                    if platform.system() == 'Windows': os.startfile(ruta_real)
                    elif platform.system() == 'Darwin': subprocess.call(('open', ruta_real))
                    else: subprocess.call(('xdg-open', ruta_real))
                except Exception as fallback_error:
                    print(f"❌ Tampoco se pudo abrir con el sistema: {fallback_error}")
        else:
            print(f"\nAbriendo por defecto: {ruta_real}")
            try:
                if platform.system() == 'Windows': os.startfile(ruta_real)
                elif platform.system() == 'Darwin': subprocess.call(('open', ruta_real))
                else: subprocess.call(('xdg-open', ruta_real))
            except Exception as e:
                print(f"❌ Error al abrir el archivo: {e}")