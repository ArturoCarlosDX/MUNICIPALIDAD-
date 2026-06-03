from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

from train_model import (
    MODEL_PATH,
    TRAMITES_PATH,
    asegurar_archivos,
    cargar_modelo,
    predecir_prioridad,
)


BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
app.secret_key = "municipalidad_ml_secret_key"


def cargar_tramites() -> pd.DataFrame:
    asegurar_archivos()
    if not TRAMITES_PATH.exists():
        return pd.DataFrame(
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
        )
    df = pd.read_csv(TRAMITES_PATH)
    for columna in ["fecha_registro", "fecha_actualizacion", "notificacion"]:
        if columna not in df.columns:
            df[columna] = ""
    return df


def guardar_tramites(df: pd.DataFrame) -> None:
    df.to_csv(TRAMITES_PATH, index=False, encoding="utf-8-sig")


def siguiente_id(df: pd.DataFrame) -> int:
    if df.empty or "id" not in df.columns:
        return 1
    valores = pd.to_numeric(df["id"], errors="coerce").dropna()
    if valores.empty:
        return 1
    return int(valores.max()) + 1


modelo = None


def obtener_modelo():
    global modelo
    if modelo is None:
        if not MODEL_PATH.exists():
            from train_model import crear_modelo

            modelo = crear_modelo()
        else:
            modelo = cargar_modelo()
    return modelo


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    df = cargar_tramites()
    total = len(df)
    prioridades = df["prioridad"].value_counts().to_dict() if not df.empty and "prioridad" in df.columns else {}
    estados = df["estado"].value_counts().to_dict() if not df.empty and "estado" in df.columns else {}
    return render_template(
        "dashboard.html",
        total=total,
        prioridades=prioridades,
        estados=estados,
    )


@app.route("/api/dashboard")
def api_dashboard():
    df = cargar_tramites()
    prioridades = df["prioridad"].value_counts().to_dict() if not df.empty and "prioridad" in df.columns else {}
    estados = df["estado"].value_counts().to_dict() if not df.empty and "estado" in df.columns else {}

    notificaciones = []
    if not df.empty and "notificacion" in df.columns:
        recientes = df[df["notificacion"].fillna("").astype(str).str.strip() != ""]
        recientes = recientes.sort_values(by="fecha_actualizacion", ascending=False).head(5)
        notificaciones = recientes[
            ["id", "nombre_ciudadano", "estado", "notificacion", "fecha_actualizacion"]
        ].to_dict(orient="records")

    return jsonify(
        {
            "total": int(len(df)),
            "prioridades": prioridades,
            "estados": estados,
            "notificaciones": notificaciones,
        }
    )


@app.route("/registrar", methods=["GET", "POST"])
def registrar():
    if request.method == "POST":
        nombre_ciudadano = request.form.get("nombre_ciudadano", "").strip()
        dni = request.form.get("dni", "").strip()
        tipo_tramite = request.form.get("tipo_tramite", "").strip()
        descripcion = request.form.get("descripcion", "").strip()

        if not all([nombre_ciudadano, dni, tipo_tramite, descripcion]):
            flash("Completa todos los campos antes de registrar el trámite.", "danger")
            return redirect(url_for("registrar"))

        modelo_actual = obtener_modelo()
        prioridad = predecir_prioridad(modelo_actual, tipo_tramite, descripcion)

        df = cargar_tramites()
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        nuevo = {
            "id": siguiente_id(df),
            "nombre_ciudadano": nombre_ciudadano,
            "dni": dni,
            "tipo_tramite": tipo_tramite,
            "descripcion": descripcion,
            "prioridad": prioridad,
            "estado": "Recibido",
            "fecha_registro": ahora,
            "fecha_actualizacion": ahora,
            "notificacion": f"Trámite registrado y notificado a {nombre_ciudadano}.",
        }
        df = pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True)
        guardar_tramites(df)
        flash(f"Trámite registrado correctamente con prioridad {prioridad}.", "success")
        return redirect(url_for("tramites"))

    return render_template("registrar.html")


@app.route("/tramites")
def tramites():
    df = cargar_tramites()
    if not df.empty:
        df = df.sort_values(by=["fecha_actualizacion", "id"], ascending=[False, False])
    return render_template("tramites.html", tramites=df.to_dict(orient="records"))


@app.route("/tramites/estado/<int:tramite_id>", methods=["POST"])
def cambiar_estado(tramite_id: int):
    estado = request.form.get("estado", "").strip()
    estados_validos = ["Recibido", "En Proceso", "Observado", "Finalizado"]
    if estado not in estados_validos:
        flash("Estado no válido.", "danger")
        return redirect(url_for("tramites"))

    df = cargar_tramites()
    if df.empty or "id" not in df.columns:
        flash("No se encontró el trámite solicitado.", "danger")
        return redirect(url_for("tramites"))

    ids_existentes = set(pd.to_numeric(df["id"], errors="coerce").dropna().astype(int))
    if tramite_id not in ids_existentes:
        flash("No se encontró el trámite solicitado.", "danger")
        return redirect(url_for("tramites"))

    mask = pd.to_numeric(df["id"], errors="coerce") == tramite_id
    nombre = df.loc[mask, "nombre_ciudadano"].iloc[0]
    df.loc[mask, "estado"] = estado
    df.loc[mask, "fecha_actualizacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df.loc[mask, "notificacion"] = f"El trámite fue actualizado a {estado}."
    guardar_tramites(df)
    flash(f"Estado actualizado para {nombre} a {estado}.", "info")
    return redirect(url_for("tramites"))


@app.route("/api/tramites")
def api_tramites():
    df = cargar_tramites()
    return jsonify(df.to_dict(orient="records"))


if __name__ == "__main__":
    asegurar_archivos()
    if not MODEL_PATH.exists():
        obtener_modelo()
    app.run(debug=True)