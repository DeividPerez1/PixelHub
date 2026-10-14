¡Bienvenido a **PixelHub**! Una aplicación desarrollada por **Deivid Michael** que implementa operaciones CRUD (Crear, Leer, Actualizar, Eliminar) y un sistema de filtros funcional.

## 🚀 Comenzando

Sigue estos pasos para clonar el proyecto y ejecutarlo en tu entorno local.

### Prerrequisitos
* Tener instalado Python.
* Contar con un gestor de bases de datos compatible.

### Instalación

1. **Clonar el repositorio:**
   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd PixelHub
2.Crear un entorno virtual (Opcional, pero recomendado):

Bash
python -m venv venv
# Activa el entorno virtual:
# En Windows: venv\Scripts\activate
# En macOS/Linux: source venv/bin/activate

3.Instalar las dependencias:

Bash
pip install -r requirements.txt

**Configuración**
Crea un archivo .env en la raíz del proyecto.

Configura tu cadena de conexión a la base de datos dentro del archivo:

Fragmento de código
DATABASE_URL=tu_direccion_de_base_de_datos

**💻 Ejecución**
Para poner en marcha la aplicación, simplemente ejecuta el archivo principal:

Bash
python src/app.py

## Pruebas automatizadas

Las pruebas unitarias no necesitan una base de datos ni un servidor activos. Desde la carpeta `PixelHub`, ejecútalas con:

```bash
python -m pytest tests -v
```

También puedes ejecutarlas desde la carpeta `tests` con `python -m pytest -v`.
