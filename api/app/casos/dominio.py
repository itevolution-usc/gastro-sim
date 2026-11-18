"""
Reglas del dominio de casos clínicos. Python puro: sin SQL, sin HTTP, sin LLM.
Responsable: Emmanuel Ospina · Actividades 4206 y 4208 (RF-14.2, RF-14.4, RNF-13).

Contiene:
  1. PERFILES: cómo se presenta típicamente cada clase de hallazgo
     (síntomas, antecedentes, edad) y qué palabras revelarían la respuesta.
  2. La cadena de validadores (patrón Chain of Responsibility, informe de
     diseño §4): cada regla revisa una cosa; si falla, el caso se descarta y
     el servicio genera otro.

Contenido educativo y sintético: no proviene de pacientes reales.
"""
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

DIFICULTADES = ("basico", "intermedio", "avanzado")
REGIONES = ("esofago", "estomago", "duodeno")


@dataclass(frozen=True)
class PerfilClinico:
    motivo: str
    sintomas: tuple[str, ...]
    antecedentes: tuple[str, ...]
    rango_edad: tuple[int, int]
    # Palabras que delatarían la respuesta si aparecen en la historia (RF-14.4).
    revela: tuple[str, ...]


_NORMAL = ("normal", "sin hallazgos", "sin alteraciones", "mucosa sana")

PERFILES: dict[str, PerfilClinico] = {
    "z-line": PerfilClinico(
        motivo="molestias digestivas leves",
        sintomas=("molestia epigástrica ocasional", "sensación de llenura después de comer", "eructos frecuentes"),
        antecedentes=("sin antecedentes de importancia", "consumo ocasional de café", "vida sedentaria"),
        rango_edad=(22, 60),
        revela=_NORMAL + ("línea z", "linea z", "unión escamocolumnar", "union escamocolumnar"),
    ),
    "pylorus": PerfilClinico(
        motivo="dolor epigástrico intermitente",
        sintomas=("dolor en la boca del estómago", "náuseas ocasionales", "llenura precoz"),
        antecedentes=("uso ocasional de antiinflamatorios", "estrés laboral", "comidas irregulares"),
        rango_edad=(20, 65),
        revela=_NORMAL + ("píloro", "piloro", "pilórico", "pilorico"),
    ),
    "retroflex-stomach": PerfilClinico(
        motivo="dispepsia de varios meses",
        sintomas=("pesadez después de las comidas", "distensión abdominal", "eructos frecuentes"),
        antecedentes=("dieta rica en grasas", "consumo de bebidas gaseosas", "sin cirugías previas"),
        rango_edad=(25, 70),
        revela=_NORMAL + ("retroflexión", "retroflexion", "fondo gástrico", "fondo gastrico"),
    ),
    "esophagitis-a": PerfilClinico(
        motivo="acidez frecuente",
        sintomas=("ardor retroesternal después de las comidas", "regurgitación ácida", "sabor amargo en la boca"),
        antecedentes=("sobrepeso", "consumo de café y alcohol", "cenas abundantes antes de dormir"),
        rango_edad=(25, 65),
        revela=("esofagitis", "grado a", "los ángeles", "los angeles", "erosión", "erosion", "erosiones"),
    ),
    "esophagitis-b-d": PerfilClinico(
        motivo="ardor intenso en el pecho",
        sintomas=("ardor retroesternal diario", "dolor al tragar", "tos nocturna", "regurgitación al acostarse"),
        antecedentes=("hernia hiatal conocida", "tabaquismo", "obesidad", "consumo frecuente de alcohol"),
        rango_edad=(30, 75),
        revela=("esofagitis", "grado b", "grado c", "grado d", "los ángeles", "los angeles",
                "úlcera esofágica", "ulcera esofagica", "erosiones", "erosión", "erosion"),
    ),
    "barretts": PerfilClinico(
        motivo="reflujo de larga evolución",
        sintomas=("acidez crónica", "regurgitación frecuente", "dificultad ocasional para tragar"),
        antecedentes=("reflujo de más de diez años", "tabaquismo", "obesidad abdominal"),
        rango_edad=(45, 80),
        revela=("barrett", "metaplasia", "epitelio columnar", "adenocarcinoma", "displasia"),
    ),
    "barretts-short-segment": PerfilClinico(
        motivo="acidez recurrente",
        sintomas=("acidez después de comidas grasas", "regurgitación ocasional", "molestia retroesternal"),
        antecedentes=("reflujo de varios años", "uso intermitente de antiácidos", "sobrepeso"),
        rango_edad=(40, 75),
        revela=("barrett", "segmento corto", "metaplasia", "epitelio columnar", "displasia"),
    ),
}

# Términos que nunca deben aparecer, sea cual sea el caso (RNF-13).
TERMINOS_PROHIBIDOS = (
    "diagnóstico:", "diagnostico:", "la respuesta", "la imagen muestra", "se observa en la imagen",
    "cédula", "cedula", "documento de identidad", "teléfono", "telefono", "dirección:", "direccion:",
)
_DATO_PERSONAL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|\b\d{7,}\b")  # correos o números largos


# ---------- Contexto que revisan los validadores ----------

@dataclass
class ContextoCaso:
    clase: str              # código HyperKvasir de la imagen (la respuesta correcta)
    region_clase: str
    region_hito: str
    region_solicitada: str | None
    historia: dict


@dataclass
class Resultado:
    ok: bool
    regla: str
    motivo: str = ""


@dataclass
class Validacion:
    ok: bool
    reglas_aprobadas: list[str] = field(default_factory=list)
    fallo: Resultado | None = None

    def como_json(self) -> dict:
        return {
            "ok": self.ok,
            "reglas_aprobadas": self.reglas_aprobadas,
            "fallo": None if self.fallo is None else {"regla": self.fallo.regla, "motivo": self.fallo.motivo},
        }


# ---------- Chain of Responsibility ----------

class ValidadorCaso(ABC):
    nombre = "validador"

    def __init__(self) -> None:
        self._siguiente: "ValidadorCaso | None" = None

    def enlazar(self, siguiente: "ValidadorCaso") -> "ValidadorCaso":
        self._siguiente = siguiente
        return siguiente

    def validar(self, caso: ContextoCaso, aprobadas: list[str] | None = None) -> Validacion:
        aprobadas = [] if aprobadas is None else aprobadas
        r = self.revisar(caso)
        if not r.ok:
            return Validacion(ok=False, reglas_aprobadas=aprobadas, fallo=r)
        aprobadas.append(self.nombre)
        if self._siguiente is None:
            return Validacion(ok=True, reglas_aprobadas=aprobadas)
        return self._siguiente.validar(caso, aprobadas)

    def _bien(self) -> Resultado:
        return Resultado(True, self.nombre)

    def _mal(self, motivo: str) -> Resultado:
        return Resultado(False, self.nombre, motivo)

    @abstractmethod
    def revisar(self, caso: ContextoCaso) -> Resultado: ...


def _texto_completo(historia: dict) -> str:
    partes = [str(historia.get(k, "")) for k in ("motivo", "texto")]
    for k in ("antecedentes", "sintomas"):
        valor = historia.get(k) or []
        partes += [str(v) for v in valor] if isinstance(valor, list) else [str(valor)]
    return " ".join(partes).lower()


class CamposCompletos(ValidadorCaso):
    """La historia trae todos los campos, con tipos y tamaños razonables."""

    nombre = "campos_completos"

    def revisar(self, caso: ContextoCaso) -> Resultado:
        h = caso.historia
        if not isinstance(h, dict):
            return self._mal("La historia no es un objeto")
        edad = h.get("edad")
        if not isinstance(edad, int) or isinstance(edad, bool) or not 18 <= edad <= 90:
            return self._mal("Edad ausente o fuera de 18–90")
        if h.get("sexo") not in ("femenino", "masculino"):
            return self._mal("Sexo ausente o no válido")
        motivo = h.get("motivo")
        if not isinstance(motivo, str) or not 3 <= len(motivo.strip()) <= 200:
            return self._mal("Motivo de consulta ausente o muy largo")
        for campo in ("antecedentes", "sintomas"):
            lista = h.get(campo)
            if not isinstance(lista, list) or not 1 <= len(lista) <= 6 or not all(
                isinstance(x, str) and x.strip() for x in lista
            ):
                return self._mal(f"'{campo}' debe ser una lista de 1 a 6 textos")
        texto = h.get("texto")
        if not isinstance(texto, str) or not 80 <= len(texto.strip()) <= 1500:
            return self._mal("El texto de la historia debe tener entre 80 y 1500 caracteres")
        return self._bien()


class CoherenciaEtiquetaRegion(ValidadorCaso):
    """La clase de la imagen, el hito 3D y la región pedida coinciden."""

    nombre = "coherencia_region"

    def revisar(self, caso: ContextoCaso) -> Resultado:
        if caso.clase not in PERFILES:
            return self._mal(f"Clase desconocida: {caso.clase}")
        if caso.region_clase != caso.region_hito:
            return self._mal("La ubicación 3D no está en la región de la clase")
        if caso.region_solicitada and caso.region_solicitada != caso.region_clase:
            return self._mal("La imagen no es de la región solicitada")
        return self._bien()


class SinRespuestaEnHistoria(ValidadorCaso):
    """La historia no menciona el hallazgo: el estudiante debe descubrirlo."""

    nombre = "sin_respuesta"

    def revisar(self, caso: ContextoCaso) -> Resultado:
        texto = _texto_completo(caso.historia)
        for termino in PERFILES[caso.clase].revela:
            if termino in texto:
                return self._mal(f"La historia revela la respuesta ('{termino}')")
        return self._bien()


class TerminosProhibidos(ValidadorCaso):
    """Sin frases prohibidas ni datos que parezcan personales (RNF-08, RNF-13)."""

    nombre = "terminos_prohibidos"

    def revisar(self, caso: ContextoCaso) -> Resultado:
        texto = _texto_completo(caso.historia)
        for termino in TERMINOS_PROHIBIDOS:
            if termino in texto:
                return self._mal(f"Contiene un término prohibido ('{termino}')")
        if _DATO_PERSONAL.search(texto):
            return self._mal("Contiene algo que parece un dato personal (correo o número largo)")
        return self._bien()


def crear_cadena() -> ValidadorCaso:
    """Orden: primero lo barato (estructura), luego el contenido."""
    cadena = CamposCompletos()
    cadena.enlazar(CoherenciaEtiquetaRegion()).enlazar(SinRespuestaEnHistoria()).enlazar(TerminosProhibidos())
    return cadena
