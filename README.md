# GASTRO-SIM

**Simulador web 3D para el entrenamiento de la toma de decisiones humano–IA en escenarios gastrointestinales.**

Proyecto final del curso *Gestión de Proyectos de TI* (2026-B) · Programa de Ingeniería de Sistemas · Universidad Santiago de Cali.

> ⚠️ **Uso exclusivamente académico.** GASTRO-SIM no es un dispositivo médico, no realiza diagnósticos y no usa datos de pacientes reales.

## ¿Qué es?

En GASTRO-SIM el estudiante:

1. Solicita un caso clínico que **genera un agente de IA** a partir de una imagen endoscópica pública (dataset HyperKvasir).
2. **Recorre en 3D** el esófago, el estómago y el duodeno con un endoscopio virtual y captura el hallazgo.
3. Registra una **decisión inicial**, ve la **recomendación de una IA de visión** (que a veces se altera a propósito) y puede consultar a un **agente tutor**.
4. Registra su **decisión final** y recibe retroalimentación.

El sistema registra cada intento para medir la precisión de las decisiones, la detección de errores de la IA y la dependencia de sus recomendaciones.

## Equipo ITEVOLUTION

| Integrante | Rol de gestión | Rol TSP |
|---|---|---|
| Emmanuel Ospina Giraldo | Líder – Director de Proyecto | Team Leader |
| Jahan Michelle Chará Bolaños | Analista | Planning Manager |
| Diego Armando Agudelo | Desarrollador – Proveedor de Soluciones | Development Manager |
| Nestor David Velasco Orozco | Tester – Garantía de Calidad | Quality/Process Manager |
| Cristian Camilo Cruz Gallego | Diseñador | Support Manager |

**Propietario del Proyecto (Product Owner):** Jair E. Sanclemente Castro.

## Metodología

- **Gestión del proyecto:** PMBOK 6.ª edición, con plantillas PM².
- **Desarrollo del software:** TSP (Team Software Process), en tres ciclos.
- **Requisitos:** ISO/IEC/IEEE 29148, priorizados con MoSCoW.

## Gestión del proyecto (para la revisión del docente)

| Qué revisar | Dónde | Qué muestra |
|---|---|---|
| **Tablero del proyecto** | [GitHub Projects](https://github.com/orgs/itevolution-usc/projects/1) | Las 78 actividades del cronograma en vistas de cronograma, tablero, ciclo TSP y responsable |
| **Hitos** | [Milestones](https://github.com/itevolution-usc/gastro-sim/milestones?state=all) | Los 13 hitos de la Lista de Hitos con su fecha, evidencia y avance |
| **Actividades** | [Issues](https://github.com/itevolution-usc/gastro-sim/issues?q=is%3Aissue) | Una por actividad: paquete de la EDT, requisito, criterios de aceptación, responsable, fechas y evidencia |
| **Control de cambios** | [Pull requests](https://github.com/itevolution-usc/gastro-sim/pulls?q=is%3Apr) | Cada cambio entra revisado por otro integrante |

**Trazabilidad:** requisito (Matriz v1.3) → paquete de la EDT → actividad (issue) → hito (milestone) → evidencia (documento en `docs/`).

### Estado al 25/10/2026

- ✅ Hitos cumplidos: H01 a H05 (inicio, requisitos, línea base, plan de calidad) y H07 (diseño del software).
- 🔄 En curso: construcción del ciclo TSP 1 (plataforma con 2FA, generador de casos, modelo de visión) y prototipo técnico 3D.
- ⚠️ H08 (v0.5, 25/10) no se alcanzó en la fecha: la construcción está atrasada respecto a la línea base. Se gestiona con el riesgo R11 (capacidad del equipo) y se presentará una solicitud de cambio al cronograma al Propietario del Proyecto.

## Documentación

| Carpeta | Contenido |
|---|---|
| [`docs/01-inicio`](docs/01-inicio) | Acta de Constitución |
| [`docs/02-requisitos`](docs/02-requisitos) | Matriz de trazabilidad, priorización MoSCoW, diagrama de casos de uso, SRS (ISO 29148) y caso de uso general |
| [`docs/03-planeacion`](docs/03-planeacion) | Planes de alcance, cronograma, calidad y dirección del proyecto; EDT; lista de actividades; lista de hitos; cronograma (Gantt y GanttProject) |
| [`docs/04-diseno`](docs/04-diseno) | Arquitectura del sistema y del software, justificación (ADR), patrones de diseño, base de datos (con script SQL) e interfaz (wireframes W01–W21) |

## Cómo ejecutar el sistema (desarrollo local)

Con **un solo comando** se levantan la base de datos (PostgreSQL 16) y la API (FastAPI, Python 3.12). No hace falta instalar Python ni PostgreSQL: Docker los trae.

### Requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) abierto (en Windows, con WSL 2).
- [Git](https://git-scm.com/) o [GitHub Desktop](https://desktop.github.com/).

### Pasos

1. Clonar el repositorio:

   ```bash
   git clone https://github.com/itevolution-usc/gastro-sim.git
   cd gastro-sim
   ```

2. Crear el archivo de configuración local a partir de la plantilla y cambiar la contraseña en **las dos líneas** donde aparece (`POSTGRES_PASSWORD` y `DATABASE_URL`):

   | Windows (PowerShell) | macOS / Linux |
   |---|---|
   | `Copy-Item .env.example .env` | `cp .env.example .env` |

   > El archivo `.env` es personal y Git lo ignora: **nunca se sube** al repositorio.

3. Construir y levantar el sistema:

   ```bash
   docker compose up --build
   ```

   La primera vez tarda unos minutos. Está listo cuando aparece `Uvicorn running on http://0.0.0.0:8000`.

4. Comprobar en el navegador:

   | Dirección | Qué debe mostrar |
   |---|---|
   | <http://localhost:8000/salud> | `"estado": "ok"` y la base de datos conectada con 18 tablas |
   | <http://localhost:8000/catalogos/hitos> | Los 7 hitos anatómicos en orden |
   | <http://localhost:8000/docs> | La documentación interactiva de la API |

5. Ejecutar las pruebas automáticas (en otra terminal, con el sistema levantado):

   ```bash
   docker compose exec api pytest -v
   ```

   Resultado esperado: `5 passed`.

6. Detener el sistema: `Ctrl + C` y luego `docker compose down`. Para borrar también los datos de la base: `docker compose down -v`.

### Fase 2: cuentas, inicio de sesión y 2FA

La autenticación usa **Supabase Auth** (contraseña + código TOTP de una app autenticadora). El navegador solo habla con Supabase para iniciar sesión; los datos siempre pasan por la API, que valida el token y exige el segundo factor (RF-01.5).

1. **Configurar la API**: en el `.env` de la raíz, completar `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` y, para usar la base de datos de Supabase, `DATABASE_URL` con la cadena del *Session pooler* (agregando `?sslmode=require` al final).
2. **Configurar el frontend**: copiar `frontend/.env.example` como `frontend/.env` y completar `VITE_SUPABASE_URL` y `VITE_SUPABASE_ANON_KEY` (clave pública).
3. **Levantar todo** (requiere [Node.js 22 LTS](https://nodejs.org/)):

   ```bash
   docker compose up --build -d
   cd frontend
   npm ci
   npm run dev
   ```

4. Abrir <http://localhost:5173>: crear cuenta (W02) → aceptar el aviso y activar el 2FA (W03) → guardar los 10 códigos de recuperación → inicio (W06).

| Pantalla | Ruta | Requisito |
|---|---|---|
| W01 Inicio de sesión | `/ingresar` | RF-01.2 |
| W02 Crear cuenta | `/registro` | RF-01.1 |
| W03 Aviso y activación del 2FA | `/activar` | RF-01.4, RF-01.6 |
| W04 Verificación del 2FA | `/verificar` | RF-01.5 |
| W05 Código de recuperación | `/recuperar` | RF-01.6 |
| W06 Inicio (versión fase 2) | `/inicio` | — |

**Pruebas:** `docker compose exec api pytest -v` (22 pruebas de la API) y, en `frontend/`, `npm test` (reglas de navegación). En cada pull request, GitHub Actions las ejecuta automáticamente (`.github/workflows/pruebas.yml`).

### Fase 3: casos clínicos generados con IA

El estudiante elige dificultad (y, si quiere, región) y la API arma un caso en menos de 15 s (RNF-14):

1. Elige una imagen de **HyperKvasir** (pública, desidentificada, CC BY 4.0) guardada en Supabase Storage (RF-14.1).
2. Ubica el hallazgo en la ruta 3D según `ubicacion_3d` (RF-14.3).
3. **Gemini** redacta una historia clínica **sintética**; si está saturado, reintenta y cambia a un modelo de respaldo; si nada responde, usa el generador local de plantillas (RF-14.2, RF-07.3).
4. Una cadena de validadores revisa campos, coherencia de región, que no revele la respuesta y que no tenga datos personales (RF-14.4, RNF-13). Hasta 3 intentos; si fallan, queda registro en `generacion_fallida`.
5. Se guarda con modelo, versión de instrucciones y semilla para poder reproducirlo (RF-14.5). El docente lo aprueba o descarta (RF-14.6).

**Configurar:**

- `.env` de la raíz: `GEMINI_API_KEY` (gratis en <https://aistudio.google.com>). Si se deja vacía, funciona con el generador local.
- Supabase → SQL Editor: ejecutar `db/migraciones/002_catalogo_casos.sql` (ubicaciones 3D y bucket privado `imagenes`).
- Cargar el subconjunto de imágenes (5 por clase, solo baja esas imágenes, no los 3,9 GB):

  ```bash
  docker compose build api
  docker compose run --rm api python -m scripts.cargar_imagenes --solo-listar
  docker compose run --rm api python -m scripts.cargar_imagenes --por-clase 5
  ```

| Pantalla / ruta | Qué hace | Requisito |
|---|---|---|
| W06 `/inicio` | Formulario de nuevo caso (dificultad y región) | RF-02.1, RF-02.2 |
| W07 `/caso/nuevo` | Generando el caso | RF-02.1 |
| W08 `/caso/nuevo` | Error al generar, con reintento | RF-14.4 |
| W10 `/caso/:id` | Historia clínica e imagen, sin la respuesta | RF-04 |

| API | Rol | Requisito |
|---|---|---|
| `POST /casos` | Estudiante | RF-02.1, RF-14.1–14.5 |
| `GET /casos/{id}` | Estudiante | RF-04 |
| `GET /docente/casos?estado=pendiente` | Docente | RF-14.6 |
| `PATCH /docente/casos/{id}` | Docente | RF-14.6 |

**Pruebas:** 45 de la API (23 nuevas: validadores, reintentos de Gemini, generación y revisión docente) y 13 del frontend. Ninguna prueba llama a Gemini.

### Fase 4: resolver un caso (decisiones, IA, tutor y puntaje)

Desde un caso, **Resolver este caso** abre un *intento* que avanza por estados (patrón State, figura SW6):

1. **Decisión inicial** (W10): el estudiante elige el hallazgo y su confianza de 1 a 5, antes de ver a la IA (RF-05).
2. **Recomendación de la IA** (W11): clase sugerida, % de confianza y recuadro (ROI) sobre la imagen (RF-06). Un porcentaje se **altera a propósito** (clase incorrecta, confianza engañosa o recuadro desplazado) para medir la sobre-dependencia (RF-08). El docente configura el porcentaje y los tipos (máx. 50 %; por defecto 25 %).
3. **Tutor socrático** (W11/W13): Gemini guía con preguntas, **no conoce la respuesta** y un guardián bloquea cualquier respuesta que afirme un diagnóstico. Si Gemini no responde, contesta una guía local. Máximo 8 preguntas por caso (RF-07).
4. **Decisión final** (RF-09) y **retroalimentación** (W14): respuesta correcta, si la IA fue alterada, puntaje (acierto 100 + detectar el error de la IA 50 + calibración hasta 25), puntos, nivel e insignias (RF-10, RF-11).

Mientras se entrena el modelo de visión (actividad 4304), la recomendación la da una **IA simulada** (`simulada-v0`): acierta la clase con una confianza verosímil, y sus errores vienen solo de las alteraciones controladas. Cuando la tabla `prediccion` tenga datos del modelo real, la API los usa automáticamente.

| API | Rol | Requisito |
|---|---|---|
| `POST /intentos` · `GET /intentos/{id}` | Estudiante | RF-05 |
| `POST /intentos/{id}/eventos` | Estudiante (escena 3D) | RF-12 |
| `POST /intentos/{id}/decision-inicial` | Estudiante | RF-05, RF-06, RF-08 |
| `POST /intentos/{id}/tutor` | Estudiante | RF-07 |
| `POST /intentos/{id}/decision-final` | Estudiante | RF-09, RF-10, RF-11 |
| `GET` · `PUT /docente/alteraciones` | Docente | RF-08.1, RF-08.2 |

**Pruebas:** 70 de la API (25 nuevas) y 17 del frontend. Ninguna prueba llama a Gemini.

### Fase 5: escena 3D del tracto superior (simulador del endoscopio)

Al resolver un caso, el estudiante primero **recorre el tracto en 3D** (W09) y luego decide (W10):

1. **Modelo 3D** (`frontend/public/modelos/tracto_superior.glb`): hecho en Blender por Cristian. 1 unidad = 1 cm, 7 hitos con nombre y el punto `camara_inicio`. Pesa ~190 KB y tiene ~4.200 triángulos (RF-03.1, RNF-02).
2. **Endoscopio virtual** (RF-03.2): **W/S** avanzar y retroceder por la ruta de los hitos, **A/D** girar, **arrastrar con el mouse** para orientar la punta (incluida la retroflexión), **Q/E** rotar. En celular y tableta hay botones en pantalla.
3. **Registro de hitos** (RF-03.3) y **minimapa** (RF-03.6): cada hito se marca al pasar a menos de 2,5 cm y se muestra el % visitado. El minimapa se puede ocultar. Recorrer los 7 da la insignia **Explorador**.
4. **Hallazgo en su punto 3D** (RF-03.4): la mancha se pinta en la pared más cercana a la ubicación del caso (`ubicacion_3d`). Se ve **igual para todas las clases patológicas**; un hallazgo **normal** (línea Z, píloro o retroflexión) no muestra lesión, como pide RF-03.4. La clase nunca llega al navegador.
5. **Captura** (RF-03.5): se puede capturar si el hallazgo está cerca y en el centro de la mira. Si no lo encuentra, puede **decidir con la imagen** (queda registrado como `hallazgo_omitido`).
6. **Telemetría** (RF-12): hitos, capturas, capturas inválidas y pausas se envían en lotes cada 3 s a `POST /intentos/{id}/eventos`.

Diseño: patrón **Observer** (figura P5). El motor 3D *emite* eventos en un bus; la lista de hitos, el minimapa y la telemetría *se suscriben*. three.js se descarga solo al abrir el simulador (RNF-02).

**Probar la escena sin iniciar sesión** (solo en desarrollo): `npm run dev` y abrir <http://localhost:5173/demo-3d>. Opciones: `?zona=linea_z`, `?zona=cardias`, `?zona=piloro` y `&en=0.55,180,0` (saltar a un punto: avance 0–1, giro y inclinación en grados).

**Pruebas:** 77 de la API (7 nuevas de la escena) y 32 del frontend (15 nuevas de la escena).

### Estructura del código

| Carpeta | Contenido | Responsable |
|---|---|---|
| `db/migraciones/` | Esquema de la base de datos (se aplica solo al crear el contenedor) | Jahan Chará |
| `api/app/` | API: configuración, conexión a la base de datos, errores y rutas | Diego Agudelo |
| `api/app/seguridad.py`, `api/app/auth_admin.py`, `api/app/routers/cuentas.py` | Sesión, 2FA y códigos de recuperación (fase 2) | Diego Agudelo |
| `frontend/` | Aplicación web (React): pantallas W01 a W11, W13 y W14 | Cristian Cruz |
| `frontend/src/escena/`, `frontend/public/modelos/` | Simulador 3D: motor three.js, bus de eventos, telemetría y modelo de Blender (fase 5) | Cristian Cruz |
| `db/verificaciones/` | Verificación del esquema en Supabase | Jahan Chará |
| `api/tests/`, `.github/workflows/`, `docker-compose.yml`, `api/Dockerfile` | Pruebas automáticas, integración continua y empaquetado | Nestor Velasco |
| `api/app/casos/`, `api/app/llm.py`, `api/app/routers/casos.py` | Generador de casos con IA (fase 3) | Emmanuel Ospina |
| `api/app/storage.py`, `api/scripts/` | Imágenes en Supabase Storage y carga del dataset (fase 3) | Diego Agudelo |
| `api/app/alteraciones/`, `api/app/tutor/`, `api/app/routers/alteraciones.py` | Alteraciones de la IA y tutor socrático (fase 4) | Emmanuel Ospina |
| `api/app/intentos/puntaje.py` | Puntaje, niveles e insignias (fase 4) | Jahan Chará |
| `api/app/intentos/`, `api/app/routers/intentos.py` | Intentos, recomendación de la IA y telemetría (fase 4) | Diego Agudelo |
| Validación de hitos y `hitos_visitados` en `api/app/intentos/` y `routers/intentos.py` | Registro de hitos de la escena 3D (fase 5) | Jahan Chará |

### Problemas frecuentes

| Síntoma | Solución |
|---|---|
| `Cannot connect to the Docker daemon` / `error during connect` | Abrir Docker Desktop y esperar a que diga *Engine running* |
| `port is already allocated` | Otro programa usa el puerto 8000 o 5433: cerrarlo o reiniciar Docker Desktop |
| `/salud` responde `503` | La base de datos aún arranca: esperar unos segundos y recargar |
| Cambios en `db/migraciones/` no se aplican | Las migraciones solo corren con la base vacía: `docker compose down -v` y volver a levantar |

## Versiones

| Versión | Contenido | Fecha objetivo |
|---|---|---|
| v0.1 | Línea base de alcance y cronograma | 11/10/2026 |
| v0.5 | Diseño, prototipo 3D, modelo de IA base y autenticación con 2FA | 25/10/2026 |
| v0.9 | Flujo completo integrado | 15/11/2026 |
| v1.0 | Versión final probada y documentada | 29/11/2026 |

## Reglas del repositorio

- La rama `main` está protegida: todo cambio entra por **pull request** con la aprobación de otro integrante.
- Las ramas se nombran con el requisito: `feature/RF-14.2`, `docs/...`.
- **Las credenciales nunca se suben**: van en un archivo `.env` local, que Git ignora.
