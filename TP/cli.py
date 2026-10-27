import questionary
from motor import SegundoCerebro

def separar_filtro(texto):
    """Extrae un token 'ext:.py' de la consulta. Devuelve (consulta, filtro)."""
    palabras, filtro = [], "Todos"
    for p in texto.split():
        if p.lower().startswith("ext:"):
            ext = p[4:].strip().lower()
            if ext:
                filtro = ext if ext.startswith(".") else "." + ext
        else:
            palabras.append(p)
    return " ".join(palabras), filtro


def buscar_y_abrir(motor, texto):
    consulta, filtro = separar_filtro(texto)
    if not consulta:
        print("⚠️ Escribe al menos una palabra a buscar.")
        return

    resultados = motor.buscar(consulta, filtro_ext=filtro)
    etiqueta_filtro = f" (filtro: {filtro})" if filtro != "Todos" else ""

    if not resultados:
        print(f"❌ No se encontraron documentos para: '{consulta}'{etiqueta_filtro}")
    elif len(resultados) == 1:
        print("✅ 1 resultado encontrado. Abriendo automáticamente...")
        motor.abrir_archivo(resultados[0]["ruta"])
    else:
        opciones = [f"📄 {r['titulo']}  ({r['ruta']})" for r in resultados]
        opciones.append("❌ Cancelar")
        eleccion = questionary.select(
            f"Se encontraron {len(resultados)} resultados{etiqueta_filtro}. Selecciona uno:",
            choices=opciones
        ).ask()
        if eleccion and eleccion != "❌ Cancelar":
            motor.abrir_archivo(resultados[opciones.index(eleccion)]["ruta"])

def iniciar_cli():
    motor = SegundoCerebro()
    print("\n--- SEGUNDO CEREBRO (Modo Consola) ---")
    print("💡 Para buscar: Escribe las palabras (ej: api rest) o buscar palabra")
    print("💡 Para filtrar por tipo: agrega ext:.py (ej: api rest ext:.pdf)")
    print("💡 Para indexar: Escribe indexar \"C:/Ruta/A/Carpeta\"")
    print("💡 Para forzar la reindexación: Escribe reindexar")
    print("💡 Para establecer intervalo: Escribe intervalo 5")
    print("💡 Para desindexar: Escribe desindexar \"C:/Ruta/A/Carpeta\"")
    print("💡 Para ver las aplicaciones predeterminadas: Escribe predeterminado")
    print("💡 Para asignar una aplicación predeterminada: Escribe predeterminado .py \"C:/Ruta/A/Programa.exe\"")
    print("💡 Para quitar una aplicación predeterminada: Escribe predeterminado .py")
    print("Escribe 'salir' para cerrar.")
    
    while True:
        comando = input("\n> ").strip()
        
        if comando.lower() in ['salir', 'exit', 'quit']: 
            break
        if not comando: 
            continue

        # --- MODO BÚSQUEDA "buscar " ---
        if comando.lower().startswith("buscar "):
            buscar_y_abrir(motor, comando[7:])
            continue

        # --- MODO INDEXAR ---
        if comando.lower().startswith("indexar "):
            ruta = comando[8:].strip(' "') # Recorta la palabra "indexar " y las comillas
            print(f"\n⏳ Indexando directorio: {ruta}")
            print("Por favor, espera...")
            
            exito, mensaje = motor.agregar_e_indexar_ruta(ruta)
            
            if exito:
                print(f"✅ {mensaje}")
            else:
                print(f"❌ {mensaje}")
            continue # Vuelve al inicio del bucle para pedir otro comando{}

        if comando.lower() == "reindexar":
            motor.forzar_reindexacion()
            continue

        # --- MODO DESINDEXAR ---
        if comando.lower().startswith("desindexar "):
            ruta = comando[11:].strip(' "') # Recorta la palabra "desindexar " y las comillas
            print(f"\n⏳ Desindexando directorio: {ruta}")
            
            exito, mensaje = motor.eliminar_directorio_indice(ruta)
            
            if exito:
                print(f"✅ {mensaje}")
            else:
                print(f"❌ {mensaje}")
            continue # Vuelve al inicio del bucle para pedir otro comando

        # --- MODO APLICACIÓN PREDETERMINADA "predeterminado" ---
        if comando.lower().startswith("predeterminado") or comando.lower().startswith("predeterminado "):
            argumentos = comando[14:].strip()  # Recorta "predeterminado"

            # Caso 1: Solo escribió "predeterminado" -> Mostrar las configuradas
            if not argumentos:
                apps = motor.obtener_apps_predeterminadas()
                if not apps:
                    print("No hay aplicaciones predeterminadas configuradas (se usa el sistema).")
                else:
                    print("\nAplicaciones predeterminadas actuales:")
                    for ext, app in apps.items():
                        print(f"  • {ext} -> {app}")
                continue

            # Separar las extensiones de la ruta del programa (dividiendo en el primer espacio)
            partes = argumentos.split(maxsplit=1)
            extensiones_str = partes[0].strip()

            # Caso 2: Escribió "predeterminado .py" (sin ruta) -> Quitar la app asignada
            if len(partes) == 1 or partes[1].strip(' "\'').lower() in ["ninguno", "default", "quitar"]:
                exito, mensaje = motor.quitar_app_de_extension(extensiones_str)
                print(f"{'✅' if exito else '❌'} {mensaje}")
                continue

            # Caso 3: Escribió "predeterminado .py "C:/Ruta/programa.exe"" -> Añadir o Modificar
            ruta_programa = partes[1].strip()
            if not (ruta_programa.startswith('"') and ruta_programa.endswith('"')):
                print('⚠️ Formato incorrecto. La ruta del programa debe ir entre comillas dobles.')
                print('   Ejemplo: predeterminado .py "C:/Ruta/Al/Programa.exe"')
                continue

            ruta_limpia = ruta_programa.strip('"')
            exito, mensaje = motor.asignar_app_a_extensiones(extensiones_str, ruta_limpia)
            print(f"{'✅' if exito else '❌'} {mensaje}")
            continue

        # --- MODO INTERVALO "intervalo " ---
        if comando.lower().startswith("intervalo "):
            minutos_str = comando[10:].strip()  # Recorta "intervalo " y espacios
            exito, mensaje = motor.modificar_intervalo_minutos(minutos_str)
            if exito:
                print(f"✅ {mensaje}")
            else:
                print(f"❌ {mensaje}")
            continue


        # --- MODO BÚSQUEDA (Por defecto) ---
        buscar_y_abrir(motor, comando)
        continue


if __name__ == "__main__":
    iniciar_cli()