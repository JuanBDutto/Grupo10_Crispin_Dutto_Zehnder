import questionary
from motor import SegundoCerebro

def iniciar_cli():
    motor = SegundoCerebro()
    print("\n--- SEGUNDO CEREBRO (Modo Consola) ---")
    print("💡 Para buscar: Escribe las palabras (ej: api rest) o 'buscar palabra'")
    print("💡 Para indexar: Escribe indexar \"C:/Ruta/A/Carpeta\"")
    print("💡 Para establecer intervalo: Escribe intervalo 5")
    print("Escribe 'salir' para cerrar.")
    
    while True:
        comando = input("\n> ").strip()
        
        if comando.lower() in ['salir', 'exit', 'quit']: 
            break
        if not comando: 
            continue

        # --- MODO BÚSQUEDA "buscar " ---
        if comando.lower().startswith("buscar "):
            termino_busqueda = comando[7:]  # Recorta "buscar "
            resultados = motor.buscar(termino_busqueda)
            print(termino_busqueda)
            if len(resultados) == 0:
                print(f"❌ No se encontraron documentos para: '{comando}'")
                        
            elif len(resultados) == 1:
                print(f"✅ 1 resultado encontrado. Abriendo automáticamente...")
                motor.abrir_archivo(resultados[0]["ruta"])
                        
            else:
                opciones = [f"📄 {r['titulo']}  ({r['ruta']})" for r in resultados]
                opciones.append("❌ Cancelar")
                        
                eleccion = questionary.select(
                    f"Se encontraron {len(resultados)} resultados. Selecciona uno:",
                    choices=opciones
                ).ask()
                        
                if eleccion and eleccion != "❌ Cancelar":
                    indice_elegido = opciones.index(eleccion)
                    motor.abrir_archivo(resultados[indice_elegido]["ruta"])
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
            continue # Vuelve al inicio del bucle para pedir otro comando

        # --- MODO INTERVALO "intervalo " ---
        if comando.lower().startswith("intervalo "):
            minutos_str = comando[9:].strip(' ')  # Recorta "intervalo " y espacios
            print(minutos_str)
            exito, mensaje = motor.modificar_intervalo_minutos(minutos_str)
            if exito:
                print(f"✅ {mensaje}")
            else:
                print(f"❌ {mensaje}")
            continue

        # --- MODO BÚSQUEDA (Por defecto) ---
        resultados = motor.buscar(comando)
        
        if len(resultados) == 0:
            print(f"❌ No se encontraron documentos para: '{comando}'")
            
        elif len(resultados) == 1:
            print(f"✅ 1 resultado encontrado. Abriendo automáticamente...")
            motor.abrir_archivo(resultados[0]["ruta"])
            
        else:
            opciones = [f"📄 {r['titulo']}  ({r['ruta']})" for r in resultados]
            opciones.append("❌ Cancelar")
            
            eleccion = questionary.select(
                f"Se encontraron {len(resultados)} resultados. Selecciona uno:",
                choices=opciones
            ).ask()
            
            if eleccion and eleccion != "❌ Cancelar":
                indice_elegido = opciones.index(eleccion)
                motor.abrir_archivo(resultados[indice_elegido]["ruta"])

if __name__ == "__main__":
    iniciar_cli()