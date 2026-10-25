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
