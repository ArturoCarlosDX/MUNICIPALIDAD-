from __future__ import annotations

import random
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "dataset.csv"
MODEL_PATH = BASE_DIR / "modelo.pkl"
TRAMITES_PATH = BASE_DIR / "tramites.csv"


def _categoria_base(tipo_tramite: str, descripcion: str) -> str:
    texto = f"{tipo_tramite} {descripcion}".lower()
    high_keywords = [
        "emerg",
        "urg",
        "salud",
        "riesgo",
        "inspeccion",
        "denuncia",
        "desastre",
        "seguridad",
        "construccion",
        "licencia de funcionamiento",
    ]
    medium_keywords = [
        "certificado",
        "constancia",
        "permiso",
        "actualizacion",
        "trámite",
        "tramite",
        "autorizacion",
        "licencia",
    ]
    if any(keyword in texto for keyword in high_keywords):
        return "Alta prioridad"
    if any(keyword in texto for keyword in medium_keywords):
        return "Media prioridad"
    return "Baja prioridad"


def generar_dataset_ejemplo(cantidad: int = 180) -> pd.DataFrame:
    random.seed(42)

    tipos = [
        ("Licencia de construcción", "Solicitud urgente para iniciar obra y revisión técnica municipal."),
        ("Atención médica", "Atención prioritaria por emergencia y riesgo para la salud."),
        ("Denuncia vecinal", "Reporte por ruidos molestos y riesgo de seguridad ciudadana."),
        ("Inspección de local", "Inspección por posible incumplimiento de normas y seguridad."),
        ("Permiso de funcionamiento", "Permiso para apertura de negocio con revisión documental."),
        ("Certificado de domicilio", "Emisión de certificado para trámite administrativo."),
        ("Constancia de posesión", "Constancia solicitada para respaldo documental del vecino."),
        ("Copia de expediente", "Solicitud de copia simple para archivo personal."),
        ("Consulta de estado", "Consulta general del estado del trámite ingresado."),
        ("Actualización de datos", "Actualización de información del ciudadano en el sistema."),
        ("Autorización de evento", "Autorización para actividad pública con revisión municipal."),
        ("Reporte de emergencia", "Reporte urgente por incidente y atención inmediata requerida."),
    ]

    ciudadanos = [
        "María Quispe",
        "Juan Pérez",
        "Rosa Huamán",
        "Luis Torres",
        "Elena Castillo",
        "Carlos Mendoza",
        "Ana Rojas",
        "Pedro Flores",
        "Carmen Díaz",
        "José Vargas",
    ]

    filas = []
    for index in range(cantidad):
        tipo, descripcion_base = tipos[index % len(tipos)]
        ciudadano = ciudadanos[index % len(ciudadanos)]
        if index % 7 == 0:
            descripcion = descripcion_base + " Se requiere atención prioritaria e inmediata."
        elif index % 5 == 0:
            descripcion = descripcion_base + " Se solicita revisión técnica complementaria."
        else:
            descripcion = descripcion_base

        prioridad = _categoria_base(tipo, descripcion)
        texto_combinado = f"{tipo} {descripcion}"

        filas.append(
            {
                "ciudadano": ciudadano,
                "tipo_tramite": tipo,
                "descripcion": descripcion,
                "texto_combinado": texto_combinado,
                "prioridad": prioridad,
            }
        )

    df = pd.DataFrame(filas)
    df.to_csv(DATASET_PATH, index=False, encoding="utf-8-sig")
    return df


def asegurar_dataset(minimo_registros: int = 100) -> pd.DataFrame:
    if DATASET_PATH.exists():
        df = pd.read_csv(DATASET_PATH)
        if len(df) >= minimo_registros and {"texto_combinado", "prioridad"}.issubset(df.columns):
            return df
    return generar_dataset_ejemplo(max(minimo_registros, 180))


def crear_modelo() -> Pipeline:
    dataset = asegurar_dataset()

    if "texto_combinado" not in dataset.columns:
        dataset["texto_combinado"] = dataset["tipo_tramite"].fillna("") + " " + dataset["descripcion"].fillna("")

    x_train, x_test, y_train, y_test = train_test_split(
        dataset["texto_combinado"],
        dataset["prioridad"],
        test_size=0.2,
        random_state=42,
        stratify=dataset["prioridad"],
    )

    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=1500)),
            ("clf", LogisticRegression(max_iter=1000)),
        ]
    )

    pipeline.fit(x_train, y_train)
    y_pred = pipeline.predict(x_test)
    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, zero_division=0)

    joblib.dump(
        {
            "model": pipeline,
            "accuracy": accuracy,
            "report": report,
        },
        MODEL_PATH,
    )
    return pipeline


def cargar_modelo() -> Pipeline:
    if MODEL_PATH.exists():
        contenido = joblib.load(MODEL_PATH)
        if isinstance(contenido, dict) and "model" in contenido:
            return contenido["model"]
        return contenido
    return crear_modelo()


def asegurar_archivos() -> None:
    asegurar_dataset()
    if not TRAMITES_PATH.exists():
        pd.DataFrame(
            columns=[
                "id",
                "nombre_ciudadano",
                "dni",
                "tipo_tramite",
                "descripcion",
                "prioridad",
                "estado",
                "fecha_registro",
                "fecha_actualizacion",
                "notificacion",
            ]
        ).to_csv(TRAMITES_PATH, index=False, encoding="utf-8-sig")


def predecir_prioridad(modelo: Pipeline, tipo_tramite: str, descripcion: str) -> str:
    texto = f"{tipo_tramite} {descripcion}"
    return str(modelo.predict([texto])[0])


if __name__ == "__main__":
    asegurar_archivos()
    modelo = crear_modelo()
    print("Modelo entrenado correctamente y guardado en modelo.pkl")
    print("Dataset generado en dataset.csv")
    print(f"Instancia del modelo: {modelo.__class__.__name__}")