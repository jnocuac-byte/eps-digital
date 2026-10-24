"""Catálogo curado de motivos de consulta para atención primaria.

Los registros orientan recuperación y triaje; no sustituyen una valoración
clínica ni contienen instrucciones terapéuticas personalizadas.
"""
from __future__ import annotations

from typing import TypedDict


class PrimaryCareEntry(TypedDict):
    id: str
    especialidad: str
    motivo_consulta: str
    terminos: list[str]
    diagnostico_o_sindrome: str
    nivel_urgencia: str
    criterios_derivacion: str
    banderas_rojas: list[str]
    codigo_cie11: str | None
    fuente: str
    referencia: str
    version: str


WHO_ICD11_SOURCE = "OMS — CIE-11, navegador oficial en español"
WHO_ICD11_REFERENCE = "https://icd.who.int/browse11/l-m/es"
MINISALUD_SOURCE = "Ministerio de Salud y Protección Social de Colombia — GPC"
MINISALUD_REFERENCE = "https://gpc.minsalud.gov.co/gpc/SitePages/gpc_info_1.aspx"
DATASET_VERSION = "2026.10-primary-care-v1"


def _entry(
    id: str,
    especialidad: str,
    motivo_consulta: str,
    terminos: list[str],
    diagnostico_o_sindrome: str,
    nivel_urgencia: str,
    criterios_derivacion: str,
    banderas_rojas: list[str],
    *,
    fuente: str = MINISALUD_SOURCE,
    referencia: str = MINISALUD_REFERENCE,
) -> PrimaryCareEntry:
    return {
        "id": id,
        "especialidad": especialidad,
        "motivo_consulta": motivo_consulta,
        "terminos": terminos,
        "diagnostico_o_sindrome": diagnostico_o_sindrome,
        "nivel_urgencia": nivel_urgencia,
        "criterios_derivacion": criterios_derivacion,
        "banderas_rojas": banderas_rojas,
        "codigo_cie11": None,
        "fuente": fuente,
        "referencia": referencia,
        "version": DATASET_VERSION,
    }


PRIMARY_CARE_CATALOG: tuple[PrimaryCareEntry, ...] = (
    _entry("cardiologia-palpitaciones", "Cardiología", "Palpitaciones", ["corazón acelerado", "latidos irregulares"], "Síntoma compatible con alteración del ritmo cardíaco", "prioritario", "Remitir a valoración si es recurrente, nuevo o se acompaña de mareo.", ["dolor torácico intenso", "desmayo", "dificultad respiratoria severa"]),
    _entry("cardiologia-presion-alta", "Cardiología", "Presión arterial elevada", ["hipertensión", "tensión alta", "dolor de cabeza por presión"], "Posible síndrome hipertensivo que requiere confirmar mediciones", "programable", "Orientar a control médico y revisión de mediciones repetidas.", ["dolor torácico", "confusión", "debilidad súbita"]),
    _entry("cardiologia-dolor-toracico", "Cardiología", "Dolor en el pecho", ["opresión en el pecho", "dolor torácico"], "Dolor torácico de causa no determinada", "urgente", "Enviar a urgencias ante dolor opresivo, persistente o asociado a síntomas vegetativos.", ["dolor irradiado a brazo, cuello o mandíbula", "sudoración fría", "falta de aire"]),
    _entry("neurologia-cefalea", "Neurología", "Dolor de cabeza recurrente", ["cefalea", "migraña", "jaqueca"], "Cefalea recurrente sin causa confirmada", "programable", "Valorar frecuencia, duración, evolución y signos neurológicos asociados.", ["inicio súbito e intenso", "confusión", "debilidad de un lado"]),
    _entry("neurologia-mareo", "Neurología", "Mareo o vértigo persistente", ["vértigo", "inestabilidad", "sensación de giro"], "Síndrome vertiginoso o mareo persistente", "prioritario", "Remitir si es persistente, recurrente o afecta la marcha y actividades diarias.", ["desmayo", "dificultad para hablar", "pérdida de fuerza"]),
    _entry("neurologia-hormigueo", "Neurología", "Hormigueo o pérdida de sensibilidad", ["parestesias", "entumecimiento", "adormecimiento"], "Alteración sensitiva de causa no determinada", "prioritario", "Valorar distribución, duración, progresión y enfermedades asociadas.", ["debilidad súbita", "asimetría facial", "pérdida de control de esfínteres"]),
    _entry("pediatria-fiebre", "Pediatría", "Fiebre en niños", ["temperatura alta", "fiebre infantil", "calentura"], "Síndrome febril pediátrico", "prioritario", "La edad, duración y estado general determinan la prioridad de valoración.", ["menor de 3 meses con fiebre", "dificultad respiratoria", "somnolencia extrema"]),
    _entry("pediatria-tos", "Pediatría", "Tos o síntomas respiratorios en niños", ["tos infantil", "mocos", "gripa en niños"], "Síndrome respiratorio agudo pediátrico", "programable", "Valorar hidratación, respiración, duración y estado general.", ["hundimiento de costillas", "coloración azulada", "pausas respiratorias"]),
    _entry("pediatria-diarrea", "Pediatría", "Diarrea o vómito en niños", ["gastroenteritis infantil", "deposiciones líquidas", "vómito infantil"], "Síndrome gastrointestinal agudo pediátrico", "prioritario", "Priorizar valoración por edad, duración y riesgo de deshidratación.", ["no tolera líquidos", "ausencia de orina", "sangre en heces"]),
    _entry("dermatologia-erupcion", "Dermatología", "Erupción o manchas en la piel", ["ronchas", "sarpullido", "lesiones cutáneas"], "Erupción cutánea de causa no determinada", "programable", "Valorar extensión, duración, exposición y síntomas acompañantes.", ["hinchazón de labios o garganta", "dificultad respiratoria", "ampollas extensas"]),
    _entry("dermatologia-acne", "Dermatología", "Acné persistente o severo", ["granos", "espinillas", "acné inflamatorio"], "Acné con impacto funcional o riesgo de cicatriz", "programable", "Remitir si es persistente, extenso o afecta el bienestar emocional.", ["fiebre", "lesiones rápidamente extensas", "dolor intenso"]),
    _entry("dermatologia-lesion", "Dermatología", "Lunar o lesión que cambia", ["lunar nuevo", "mancha que crece", "lesión pigmentada"], "Lesión cutánea que requiere evaluación", "prioritario", "Valorar cambios de tamaño, forma, color, sangrado o evolución.", ["sangrado persistente", "ulceración", "crecimiento acelerado"]),
    _entry("odontologia-dolor", "Odontología", "Dolor dental", ["dolor de muela", "dolor en diente", "odontalgia"], "Dolor odontogénico de causa no determinada", "prioritario", "Remitir a valoración odontológica, especialmente si persiste o limita la alimentación.", ["hinchazón facial", "dificultad para tragar", "dificultad respiratoria"]),
    _entry("odontologia-encias", "Odontología", "Sangrado o inflamación de encías", ["encías sangrantes", "gingivitis", "encías inflamadas"], "Inflamación gingival o periodontal", "programable", "Orientar a valoración odontológica y revisión de higiene oral.", ["sangrado incontrolable", "fiebre alta", "hinchazón progresiva"]),
    _entry("odontologia-trauma", "Odontología", "Trauma o fractura dental", ["diente roto", "golpe en la boca", "diente salido"], "Trauma dentoalveolar", "prioritario", "Requiere valoración odontológica pronta para conservar función y tejido.", ["sangrado abundante", "dificultad respiratoria", "pérdida de conciencia"]),
    _entry("ginecologia-dolor-pelvico", "Ginecología", "Dolor pélvico", ["dolor bajo vientre", "dolor de ovarios", "dolor abdominal bajo"], "Dolor pélvico de causa no determinada", "prioritario", "Valorar intensidad, embarazo posible, sangrado y síntomas urinarios o digestivos.", ["dolor súbito intenso", "desmayo", "embarazo con dolor o sangrado"]),
    _entry("ginecologia-sangrado", "Ginecología", "Sangrado vaginal anormal", ["sangrado entre periodos", "menstruación abundante", "metrorragia"], "Sangrado uterino anormal", "prioritario", "Remitir según cantidad, duración, edad y posibilidad de embarazo.", ["sangrado que empapa toallas continuamente", "mareo intenso", "embarazo"]),
    _entry("ginecologia-flujo", "Ginecología", "Flujo vaginal, picazón o dolor", ["infección vaginal", "flujo anormal", "ardor vaginal"], "Síntomas vulvovaginales de causa no determinada", "programable", "Orientar a consulta para examen y diagnóstico diferencial.", ["fiebre alta", "dolor pélvico intenso", "embarazo con dolor"]),
    _entry("medicina-general-gripa", "Medicina General", "Síntomas gripales", ["resfriado", "congestión", "dolor de garganta"], "Síndrome respiratorio agudo no complicado", "programable", "Valorar duración, fiebre, comorbilidades y estado general.", ["dificultad respiratoria", "confusión", "coloración azulada"]),
    _entry("medicina-general-dolor-abdominal", "Medicina General", "Dolor abdominal leve", ["dolor de estómago", "retortijones", "dolor de barriga"], "Dolor abdominal de causa no determinada", "prioritario", "Evaluar localización, duración, evolución y síntomas gastrointestinales o urinarios.", ["abdomen rígido", "dolor súbito intenso", "sangrado"]),
    _entry("medicina-general-chequeo", "Medicina General", "Chequeo preventivo", ["control general", "exámenes de rutina", "prevención"], "Consulta preventiva y evaluación integral", "programable", "Coordinar valoración según edad, antecedentes y factores de riesgo.", ["síntomas agudos de alarma"]),
    _entry("oftalmologia-vision-borrosa", "Oftalmología", "Visión borrosa", ["veo borroso", "visión nublada", "problemas para ver"], "Alteración visual de causa no determinada", "prioritario", "Valorar inicio, unilateralidad, dolor, trauma y síntomas neurológicos.", ["pérdida súbita de visión", "dolor ocular intenso", "debilidad súbita"]),
    _entry("oftalmologia-ojo-rojo", "Oftalmología", "Ojo rojo o irritado", ["enrojecimiento ocular", "conjuntivitis", "ardor en los ojos"], "Síndrome de ojo rojo", "programable", "Remitir si persiste, hay secreción importante, dolor o compromiso visual.", ["dolor intenso", "fotofobia marcada", "pérdida visual"]),
    _entry("oftalmologia-trauma", "Oftalmología", "Trauma ocular", ["golpe en el ojo", "cuerpo extraño", "lesión ocular"], "Trauma ocular", "urgente", "Requiere valoración urgente ante impacto, cuerpo extraño o cambio visual.", ["pérdida de visión", "herida penetrante", "dolor intenso"]),
    _entry("ortopedia-dolor-lumbar", "Ortopedia y Traumatología", "Dolor lumbar", ["dolor de espalda", "lumbalgia", "dolor en la cintura"], "Dolor lumbar de causa no determinada", "programable", "Valorar duración, trauma, fiebre, cáncer previo y síntomas neurológicos.", ["debilidad progresiva", "pérdida de control de esfínteres", "trauma mayor"]),
    _entry("ortopedia-dolor-articular", "Ortopedia y Traumatología", "Dolor o inflamación articular", ["dolor de rodilla", "articulación inflamada", "artralgia"], "Síndrome doloroso articular", "prioritario", "Valorar articulación afectada, trauma, fiebre y limitación funcional.", ["articulación roja y caliente con fiebre", "deformidad", "incapacidad para apoyar"]),
    _entry("ortopedia-fractura", "Ortopedia y Traumatología", "Trauma con posible fractura", ["caída", "fractura", "golpe fuerte"], "Trauma musculoesquelético con posible fractura", "urgente", "Requiere valoración e imágenes según mecanismo y función.", ["deformidad evidente", "extremidad fría o pálida", "herida abierta"]),
    _entry("gastroenterologia-reflujo", "Gastroenterología", "Acidez o reflujo", ["agruras", "ardor en el pecho", "reflujo gástrico"], "Síntomas compatibles con reflujo gastroesofágico", "programable", "Remitir si es persistente, recurrente o afecta alimentación y sueño.", ["dificultad para tragar", "sangrado digestivo", "pérdida de peso"]),
    _entry("gastroenterologia-diarrea", "Gastroenterología", "Diarrea persistente", ["deposiciones líquidas", "diarrea crónica", "urgencia intestinal"], "Síndrome diarreico persistente", "prioritario", "Valorar duración, hidratación, sangre, fiebre y pérdida de peso.", ["deshidratación", "sangre en heces", "dolor abdominal intenso"]),
    _entry("gastroenterologia-sangrado", "Gastroenterología", "Sangrado digestivo", ["sangre en heces", "heces negras", "vómito con sangre"], "Sangrado gastrointestinal de causa no determinada", "urgente", "Enviar a urgencias para valoración inmediata.", ["vómito con sangre", "heces negras abundantes", "mareo o desmayo"]),
)
