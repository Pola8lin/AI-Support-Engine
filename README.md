# AI Support Engine

Initial project structure for an AI-powered support engine.

## Equipo

Eduardo Daniel Santos Villagrán
Ana Paola Palacios Lindo

## Structure

```text
ai-support-engine/
├── src/
│   ├── api/routes.py
│   ├── services/analyzer.py
│   ├── strategies/
│   │   ├── base.py
│   │   ├── traditional.py
│   │   └── generative.py
│   ├── validators/
│   │   ├── input_validator.py
│   │   └── response_validator.py
│   ├── models/response.py
│   └── app.py
├── tests/
├── artifacts/results.json
└── evidence/
```

## Instrucciones de Ejecución

### 1. Requisitos previos
- Python 3.11 o superior
- Una clave de API de Google AI Studio (`GEMINI_API_KEY`)

### 2. Instalación de dependencias
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Variables de entorno
Copia el archivo de ejemplo y configura tu clave local en `.env` (este archivo está ignorado en `.gitignore` y no debe subirse al repositorio):

```powershell
Copy-Item .env.example .env
```

Edita `.env`:
```env
GEMINI_API_KEY=tu_clave_aqui
GEMINI_MODEL=gemini-2.5-flash
```

### 4. Levantar la API local (FastAPI)
```powershell
python -m uvicorn src.app:app --host 127.0.0.1 --port 8000
```
- Documentación interactiva (Swagger UI): `http://127.0.0.1:8000/docs`
- Endpoint principal: `POST http://127.0.0.1:8000/api/analyze`

Ejemplos de petición:
```json
{
  "message": "No puedo iniciar sesión en mi cuenta corporativa",
  "mode": "traditional"
}
```
```json
{
  "message": "No puedo iniciar sesión en mi cuenta corporativa",
  "mode": "generative"
}
```

### 5. Ejecutar pruebas automatizadas (`pytest`)
```powershell
python -m pytest -v
```

### 6. Ejecutar el benchmark comparativo (12 casos)
Con el servidor `uvicorn` activo en otra terminal:
```powershell
python tests/run_benchmark.py
```
Este comando evalúa los casos de `tests/dataset.json` contra ambos motores (`traditional` y `generative`) y actualiza `evidence/benchmark_raw_results.json`, `artifacts/results.json` y `artifacts/results_table.md`.

## Evidencias y Reporte de Resultados

- Tabla comparativa y conclusión técnica: [artifacts/results_table.md](artifacts/results_table.md)
- Resumen numérico en JSON: [artifacts/results.json](artifacts/results.json)
- Evidencia cruda HTTP de ambos motores (12 casos): [evidence/benchmark_raw_results.json](evidence/benchmark_raw_results.json)
- Catálogo de casos etiquetados (*ground truth*): [tests/dataset.json](tests/dataset.json)

