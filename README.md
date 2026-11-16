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

### Estructura del código

| Carpeta | Contenido | Responsable |
|---|---|---|
| `db/migraciones/` | Esquema de la base de datos (se aplica solo al crear el contenedor) | Jahan Chará |
| `api/app/` | API: configuración, conexión a la base de datos, errores y rutas | Diego Agudelo |
| `api/app/seguridad.py`, `api/app/auth_admin.py`, `api/app/routers/cuentas.py` | Sesión, 2FA y códigos de recuperación (fase 2) | Diego Agudelo |
| `frontend/` | Aplicación web (React): pantallas W01 a W06 | Cristian Cruz |
| `db/verificaciones/` | Verificación del esquema en Supabase | Jahan Chará |
| `api/tests/`, `.github/workflows/`, `docker-compose.yml`, `api/Dockerfile` | Pruebas automáticas, integración continua y empaquetado | Nestor Velasco |

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
