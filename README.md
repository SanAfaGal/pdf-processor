# PDF Processor

Procesador de PDFs y facturas para auditoría y organización de documentos (hospital / SIHOS).

## Entorno virtual (venv)

Siempre usar un entorno virtual para instalar dependencias y ejecutar el proyecto.

### Crear y activar el venv

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Instalar dependencias

Con el venv activado:

```bash
pip install -r requirements.txt
```

### Ejecutar la aplicación

**Opción 1 – Usando el venv automáticamente (recomendado)**  
Desde la raíz del proyecto, sin activar el venv a mano:

- Windows PowerShell: `.\run.ps1`
- Windows CMD: `run.bat`

**Opción 2 – Con el venv ya activado**

```bash
python main.py
```

o:

```bash
python -m cli.main
```

Se mostrará un menú en bucle con las acciones disponibles (cargar Excel, normalizar archivos, verificar facturas, etc.).

### Configuración

Crear un archivo `.env` en la raíz con las variables requeridas (rutas, hospital activo, credenciales de Drive, etc.). La aplicación valida la configuración al iniciar.
