## Instalación y Configuración

Para ejecutar este proyecto, deberás crear un entorno virtual, activarlo e instalar las dependencias necesarias. Sigue estos pasos:

### 1. Crear el entorno virtual
Asegúrate de estar en la carpeta raíz del proyecto y ejecuta el siguiente comando usando `uv`:

```bash
uv venv
```

### 2. Activar el entorno
Dependiendo de tu sistema operativo, utiliza el comando correspondiente para activar el entorno virtual que acabamos de crear:

**En Windows:**
```bash
.venv\Scripts\activate
```

**En Mac / Linux:**
```bash
source .venv/bin/activate
```
*(Sabrás que el entorno está activo porque verás un indicador como `(.venv)` al principio de la línea en tu terminal).*

### 3. Instalar las dependencias
Una vez activado el entorno, lee el archivo de configuración para instalar todas las librerías necesarias ejecutando:

```bash
uv pip install -r requirements.txt
```

### 4. Verificar la instalación
Una vez finalizado el comando de instalación, puedes confirmar que todos los paquetes se agregaron correctamente a tu entorno ejecutando:

```bash
uv pip list
```