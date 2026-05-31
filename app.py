from pathlib import Path
from datetime import date, datetime, timedelta
from math import ceil
import math
import calendar
import csv
import json
import os

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None
    dict_row = None

from flask import Flask, Response, redirect, render_template, request, url_for


app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "finanzas.csv"
AUTOMATIZACIONES_PATH = DATA_DIR / "automatizaciones.csv"
DEUDAS_PATH = DATA_DIR / "deudas.csv"
PLANIFICACION_PATH = DATA_DIR / "planificacion.csv"
ENV_PATH = BASE_DIR / ".env"
LINK_PATH = BASE_DIR / "link.txt"
DB_LISTA = False
COLUMNAS = ["fecha", "tipo", "categoria", "descripcion", "monto"]
AUTOMATIZACION_COLUMNAS = [
    "tipo",
    "categoria",
    "descripcion",
    "monto",
    "dia_mes",
    "activo",
    "ultimo_confirmado",
    "ticket_ultimo",
    "ultimo_anulado",
    "razon_anulado",
]
DEUDA_COLUMNAS = [
    "fecha",
    "tipo",
    "persona",
    "categoria",
    "descripcion",
    "monto",
    "estado",
    "fecha_pago",
]
PLANIFICACION_COLUMNAS = ["fecha", "tipo", "categoria", "descripcion", "monto"]
TIPOS_VALIDOS = {"Ingreso", "Gasto", "Ahorro"}
TIPOS_AUTOMATIZACION = {"Gasto", "Ahorro"}
TIPOS_DEUDA = {"Me deben", "Debo"}
MESES = [
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
]


def cargar_entorno_local():
    if ENV_PATH.exists():
        for linea in ENV_PATH.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))
    if not os.getenv("DATABASE_URL") and LINK_PATH.exists():
        os.environ["DATABASE_URL"] = LINK_PATH.read_text(encoding="utf-8").strip()


cargar_entorno_local()


def database_url():
    url = os.getenv("DATABASE_URL", "").strip()
    if url and "sslmode=" not in url:
        separador = "&" if "?" in url else "?"
        url = f"{url}{separador}sslmode=require"
    return url


def usar_base_datos():
    return bool(database_url() and psycopg)


def conectar_db():
    return psycopg.connect(database_url(), row_factory=dict_row)


def asegurar_db():
    global DB_LISTA
    if not usar_base_datos():
        return
    if DB_LISTA:
        return
    with conectar_db() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS movimientos (
                    id BIGSERIAL PRIMARY KEY,
                    fecha TEXT NOT NULL DEFAULT '',
                    tipo TEXT NOT NULL DEFAULT '',
                    categoria TEXT NOT NULL DEFAULT '',
                    descripcion TEXT NOT NULL DEFAULT '',
                    monto DOUBLE PRECISION NOT NULL DEFAULT 0
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS automatizaciones (
                    id BIGSERIAL PRIMARY KEY,
                    tipo TEXT NOT NULL DEFAULT '',
                    categoria TEXT NOT NULL DEFAULT '',
                    descripcion TEXT NOT NULL DEFAULT '',
                    monto DOUBLE PRECISION NOT NULL DEFAULT 0,
                    dia_mes INTEGER NOT NULL DEFAULT 1,
                    activo BOOLEAN NOT NULL DEFAULT TRUE,
                    ultimo_confirmado TEXT NOT NULL DEFAULT '',
                    ticket_ultimo TEXT NOT NULL DEFAULT '',
                    ultimo_anulado TEXT NOT NULL DEFAULT '',
                    razon_anulado TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS deudas (
                    id BIGSERIAL PRIMARY KEY,
                    fecha TEXT NOT NULL DEFAULT '',
                    tipo TEXT NOT NULL DEFAULT '',
                    persona TEXT NOT NULL DEFAULT '',
                    categoria TEXT NOT NULL DEFAULT '',
                    descripcion TEXT NOT NULL DEFAULT '',
                    monto DOUBLE PRECISION NOT NULL DEFAULT 0,
                    estado TEXT NOT NULL DEFAULT '',
                    fecha_pago TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS planificacion (
                    id BIGSERIAL PRIMARY KEY,
                    fecha TEXT NOT NULL DEFAULT '',
                    tipo TEXT NOT NULL DEFAULT '',
                    categoria TEXT NOT NULL DEFAULT '',
                    descripcion TEXT NOT NULL DEFAULT '',
                    monto DOUBLE PRECISION NOT NULL DEFAULT 0
                )
                """
            )
    DB_LISTA = True


def asegurar_csv():
    DATA_DIR.mkdir(exist_ok=True)
    if not CSV_PATH.exists():
        with CSV_PATH.open("w", newline="", encoding="utf-8") as archivo:
            writer = csv.DictWriter(archivo, fieldnames=COLUMNAS)
            writer.writeheader()
    if not AUTOMATIZACIONES_PATH.exists():
        with AUTOMATIZACIONES_PATH.open("w", newline="", encoding="utf-8") as archivo:
            writer = csv.DictWriter(archivo, fieldnames=AUTOMATIZACION_COLUMNAS)
            writer.writeheader()
    if not DEUDAS_PATH.exists():
        with DEUDAS_PATH.open("w", newline="", encoding="utf-8") as archivo:
            writer = csv.DictWriter(archivo, fieldnames=DEUDA_COLUMNAS)
            writer.writeheader()
    if not PLANIFICACION_PATH.exists():
        with PLANIFICACION_PATH.open("w", newline="", encoding="utf-8") as archivo:
            writer = csv.DictWriter(archivo, fieldnames=PLANIFICACION_COLUMNAS)
            writer.writeheader()


def leer_movimientos():
    if usar_base_datos():
        asegurar_db()
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "SELECT fecha, tipo, categoria, descripcion, monto FROM movimientos ORDER BY id"
                )
                movimientos = []
                for indice, fila in enumerate(cursor.fetchall()):
                    movimiento = {columna: fila.get(columna, "") for columna in COLUMNAS}
                    movimiento["monto"] = float(movimiento["monto"] or 0)
                    movimiento["id"] = indice
                    movimientos.append(movimiento)
                return movimientos

    asegurar_csv()
    with CSV_PATH.open(newline="", encoding="utf-8") as archivo:
        reader = csv.DictReader(archivo)
        movimientos = []
        for indice, fila in enumerate(reader):
            movimiento = {columna: fila.get(columna, "") for columna in COLUMNAS}
            try:
                movimiento["monto"] = float(movimiento["monto"] or 0)
            except ValueError:
                movimiento["monto"] = 0
            movimiento["id"] = indice
            movimientos.append(movimiento)
    return movimientos


def escribir_movimientos(movimientos):
    if usar_base_datos():
        asegurar_db()
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("TRUNCATE movimientos RESTART IDENTITY")
                cursor.executemany(
                    """
                    INSERT INTO movimientos (fecha, tipo, categoria, descripcion, monto)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            movimiento.get("fecha", ""),
                            movimiento.get("tipo", ""),
                            movimiento.get("categoria", ""),
                            movimiento.get("descripcion", ""),
                            float(movimiento.get("monto") or 0),
                        )
                        for movimiento in movimientos
                    ],
                )
        return

    asegurar_csv()
    with CSV_PATH.open("w", newline="", encoding="utf-8") as archivo:
        writer = csv.DictWriter(archivo, fieldnames=COLUMNAS)
        writer.writeheader()
        for movimiento in movimientos:
            writer.writerow({columna: movimiento.get(columna, "") for columna in COLUMNAS})


def guardar_movimiento(movimiento):
    if usar_base_datos():
        asegurar_db()
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO movimientos (fecha, tipo, categoria, descripcion, monto)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        movimiento.get("fecha", ""),
                        movimiento.get("tipo", ""),
                        movimiento.get("categoria", ""),
                        movimiento.get("descripcion", ""),
                        float(movimiento.get("monto") or 0),
                    ),
                )
        return

    asegurar_csv()
    with CSV_PATH.open("a", newline="", encoding="utf-8") as archivo:
        writer = csv.DictWriter(archivo, fieldnames=COLUMNAS)
        writer.writerow(movimiento)


def leer_automatizaciones():
    if usar_base_datos():
        asegurar_db()
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT tipo, categoria, descripcion, monto, dia_mes, activo,
                           ultimo_confirmado, ticket_ultimo, ultimo_anulado, razon_anulado
                    FROM automatizaciones
                    ORDER BY id
                    """
                )
                automatizaciones = []
                for indice, fila in enumerate(cursor.fetchall()):
                    item = {columna: fila.get(columna, "") for columna in AUTOMATIZACION_COLUMNAS}
                    item["monto"] = float(item["monto"] or 0)
                    item["dia_mes"] = int(item["dia_mes"] or 1)
                    item["activo"] = bool(item["activo"])
                    item["id"] = indice
                    automatizaciones.append(item)
                return automatizaciones

    asegurar_csv()
    with AUTOMATIZACIONES_PATH.open(newline="", encoding="utf-8") as archivo:
        reader = csv.DictReader(archivo)
        automatizaciones = []
        for indice, fila in enumerate(reader):
            item = {columna: fila.get(columna, "") for columna in AUTOMATIZACION_COLUMNAS}
            try:
                item["monto"] = float(item["monto"] or 0)
            except ValueError:
                item["monto"] = 0
            try:
                item["dia_mes"] = int(item["dia_mes"] or 1)
            except ValueError:
                item["dia_mes"] = 1
            item["id"] = indice
            item["activo"] = item["activo"] != "No"
            automatizaciones.append(item)
    return automatizaciones


def escribir_automatizaciones(automatizaciones):
    if usar_base_datos():
        asegurar_db()
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("TRUNCATE automatizaciones RESTART IDENTITY")
                cursor.executemany(
                    """
                    INSERT INTO automatizaciones (
                        tipo, categoria, descripcion, monto, dia_mes, activo,
                        ultimo_confirmado, ticket_ultimo, ultimo_anulado, razon_anulado
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            item.get("tipo", ""),
                            item.get("categoria", ""),
                            item.get("descripcion", ""),
                            float(item.get("monto") or 0),
                            int(item.get("dia_mes") or 1),
                            bool(item.get("activo", True)),
                            item.get("ultimo_confirmado", ""),
                            item.get("ticket_ultimo", ""),
                            item.get("ultimo_anulado", ""),
                            item.get("razon_anulado", ""),
                        )
                        for item in automatizaciones
                    ],
                )
        return

    asegurar_csv()
    with AUTOMATIZACIONES_PATH.open("w", newline="", encoding="utf-8") as archivo:
        writer = csv.DictWriter(archivo, fieldnames=AUTOMATIZACION_COLUMNAS)
        writer.writeheader()
        for item in automatizaciones:
            fila = {columna: item.get(columna, "") for columna in AUTOMATIZACION_COLUMNAS}
            fila["activo"] = "Si" if item.get("activo", True) else "No"
            writer.writerow(fila)


def leer_deudas():
    if usar_base_datos():
        asegurar_db()
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT fecha, tipo, persona, categoria, descripcion, monto, estado, fecha_pago
                    FROM deudas
                    ORDER BY id
                    """
                )
                deudas = []
                for indice, fila in enumerate(cursor.fetchall()):
                    item = {columna: fila.get(columna, "") for columna in DEUDA_COLUMNAS}
                    item["monto"] = float(item["monto"] or 0)
                    item["id"] = indice
                    deudas.append(item)
                return deudas

    asegurar_csv()
    with DEUDAS_PATH.open(newline="", encoding="utf-8") as archivo:
        reader = csv.DictReader(archivo)
        deudas = []
        for indice, fila in enumerate(reader):
            item = {columna: fila.get(columna, "") for columna in DEUDA_COLUMNAS}
            try:
                item["monto"] = float(item["monto"] or 0)
            except ValueError:
                item["monto"] = 0
            item["id"] = indice
            deudas.append(item)
    return deudas


def categorias_existentes():
    categorias = {"Todas": {}}
    tipos = TIPOS_VALIDOS | TIPOS_AUTOMATIZACION | TIPOS_DEUDA
    for tipo in tipos:
        categorias[tipo] = {}

    def agregar_categoria(tipo, categoria):
        categoria = categoria.strip()
        if not categoria:
            return
        categorias.setdefault(tipo, {})
        categorias[tipo].setdefault(categoria.lower(), categoria)
        categorias["Todas"].setdefault(categoria.lower(), categoria)

    for item in leer_movimientos():
        agregar_categoria(item.get("tipo", ""), item.get("categoria", ""))
    for item in leer_automatizaciones():
        agregar_categoria(item.get("tipo", ""), item.get("categoria", ""))
    for item in leer_deudas():
        agregar_categoria(item.get("tipo", ""), item.get("categoria", ""))
    for item in leer_planificaciones():
        agregar_categoria(item.get("tipo", ""), item.get("categoria", ""))

    return {
        tipo: sorted(valores.values(), key=str.lower)
        for tipo, valores in categorias.items()
    }


def lista_categoria_para_tipo(tipo):
    ids = {
        "Ingreso": "categorias-ingreso",
        "Gasto": "categorias-gasto",
        "Ahorro": "categorias-ahorro",
        "Me deben": "categorias-me-deben",
        "Debo": "categorias-debo",
    }
    return ids.get(tipo, "categorias-todas")


@app.context_processor
def inyectar_categorias():
    return {
        "categorias_existentes": categorias_existentes(),
        "lista_categoria_para_tipo": lista_categoria_para_tipo,
    }
def escribir_deudas(deudas):
    if usar_base_datos():
        asegurar_db()
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("TRUNCATE deudas RESTART IDENTITY")
                cursor.executemany(
                    """
                    INSERT INTO deudas (
                        fecha, tipo, persona, categoria, descripcion, monto, estado, fecha_pago
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            item.get("fecha", ""),
                            item.get("tipo", ""),
                            item.get("persona", ""),
                            item.get("categoria", ""),
                            item.get("descripcion", ""),
                            float(item.get("monto") or 0),
                            item.get("estado", ""),
                            item.get("fecha_pago", ""),
                        )
                        for item in deudas
                    ],
                )
        return

    asegurar_csv()
    with DEUDAS_PATH.open("w", newline="", encoding="utf-8") as archivo:
        writer = csv.DictWriter(archivo, fieldnames=DEUDA_COLUMNAS)
        writer.writeheader()
        for item in deudas:
            writer.writerow({columna: item.get(columna, "") for columna in DEUDA_COLUMNAS})


def leer_planificaciones():
    if usar_base_datos():
        asegurar_db()
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "SELECT fecha, tipo, categoria, descripcion, monto FROM planificacion ORDER BY id"
                )
                planificaciones = []
                for indice, fila in enumerate(cursor.fetchall()):
                    item = {columna: fila.get(columna, "") for columna in PLANIFICACION_COLUMNAS}
                    item["monto"] = float(item["monto"] or 0)
                    item["id"] = indice
                    planificaciones.append(item)
                return planificaciones

    asegurar_csv()
    with PLANIFICACION_PATH.open(newline="", encoding="utf-8") as archivo:
        reader = csv.DictReader(archivo)
        planificaciones = []
        for indice, fila in enumerate(reader):
            item = {columna: fila.get(columna, "") for columna in PLANIFICACION_COLUMNAS}
            try:
                item["monto"] = float(item["monto"] or 0)
            except ValueError:
                item["monto"] = 0
            item["id"] = indice
            planificaciones.append(item)
    return planificaciones


def escribir_planificaciones(planificaciones):
    if usar_base_datos():
        asegurar_db()
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("TRUNCATE planificacion RESTART IDENTITY")
                cursor.executemany(
                    """
                    INSERT INTO planificacion (fecha, tipo, categoria, descripcion, monto)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            item.get("fecha", ""),
                            item.get("tipo", ""),
                            item.get("categoria", ""),
                            item.get("descripcion", ""),
                            float(item.get("monto") or 0),
                        )
                        for item in planificaciones
                    ],
                )
        return

    asegurar_csv()
    with PLANIFICACION_PATH.open("w", newline="", encoding="utf-8") as archivo:
        writer = csv.DictWriter(archivo, fieldnames=PLANIFICACION_COLUMNAS)
        writer.writeheader()
        for item in planificaciones:
            writer.writerow({columna: item.get(columna, "") for columna in PLANIFICACION_COLUMNAS})


def guardar_planificacion(item):
    if usar_base_datos():
        asegurar_db()
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO planificacion (fecha, tipo, categoria, descripcion, monto)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        item.get("fecha", ""),
                        item.get("tipo", ""),
                        item.get("categoria", ""),
                        item.get("descripcion", ""),
                        float(item.get("monto") or 0),
                    ),
                )
        return

    asegurar_csv()
    with PLANIFICACION_PATH.open("a", newline="", encoding="utf-8") as archivo:
        writer = csv.DictWriter(archivo, fieldnames=PLANIFICACION_COLUMNAS)
        writer.writerow(item)


def periodo_actual():
    return clave_ciclo(date.today())


def proxima_fecha_mensual(dia_mes):
    hoy = date.today()
    ultimo_dia = calendar.monthrange(hoy.year, hoy.month)[1]
    dia = min(max(int(dia_mes), 1), ultimo_dia)
    return date(hoy.year, hoy.month, dia).isoformat()


def penultimo_dia_habil_mes(hoy=None):
    hoy = hoy or date.today()
    ultimo_dia = calendar.monthrange(hoy.year, hoy.month)[1]
    dias_habiles = [
        date(hoy.year, hoy.month, dia)
        for dia in range(1, ultimo_dia + 1)
        if date(hoy.year, hoy.month, dia).weekday() < 5
    ]
    if len(dias_habiles) >= 2:
        return dias_habiles[-2].isoformat()
    return dias_habiles[-1].isoformat()


def fecha_sueldo_esperada(hoy=None):
    return fecha_movimiento(penultimo_dia_habil_mes(hoy))


def sumar_meses(fecha, meses):
    mes = fecha.month - 1 + meses
    anio = fecha.year + mes // 12
    mes = mes % 12 + 1
    dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
    return date(anio, mes, dia)


def es_sueldo(movimiento):
    if movimiento["tipo"] != "Ingreso":
        return False
    categoria = movimiento["categoria"].strip().lower()
    descripcion = movimiento["descripcion"].strip().lower()
    return categoria == "sueldo" or descripcion == "sueldo"


def ultimo_sueldo(movimientos):
    sueldos = [
        (fecha, item)
        for item in movimientos
        if es_sueldo(item) and (fecha := fecha_movimiento(item["fecha"]))
    ]
    if not sueldos:
        return None
    return max(sueldos, key=lambda item: item[0])


def ultimo_sueldo_antes_de(movimientos, fecha_limite):
    sueldos = [
        (fecha, item)
        for item in movimientos
        if es_sueldo(item)
        and (fecha := fecha_movimiento(item["fecha"]))
        and fecha < fecha_limite
    ]
    if not sueldos:
        return None
    return max(sueldos, key=lambda item: item[0])


def clave_ciclo(fecha, movimientos=None):
    movimientos = movimientos if movimientos is not None else leer_movimientos()
    sueldos = [
        fecha_sueldo
        for item in movimientos
        if es_sueldo(item)
        and (fecha_sueldo := fecha_movimiento(item.get("fecha", "")))
        and fecha_sueldo <= fecha
    ]
    if sueldos:
        return max(sueldos).isoformat()
    return f"{fecha.year}-{fecha.month:02d}"


def periodo_movimiento_ciclo(valor, movimientos=None):
    fecha = fecha_movimiento(valor)
    if not fecha:
        return ""
    return clave_ciclo(fecha, movimientos)


def saldo_antes_de(movimientos, fecha_inicio):
    saldo = 0
    for item in movimientos:
        fecha = fecha_movimiento(item.get("fecha", ""))
        if not fecha or fecha >= fecha_inicio:
            continue
        monto = float(item.get("monto") or 0)
        if item.get("tipo") == "Ingreso":
            saldo += monto
        elif item.get("tipo") in {"Gasto", "Ahorro"}:
            saldo -= monto
    return saldo


def etiqueta_ciclo(clave):
    fecha = fecha_movimiento(clave)
    if fecha:
        proximo_mes = sumar_meses(fecha, 1)
        fecha_fin = fecha_movimiento(penultimo_dia_habil_mes(proximo_mes)) - timedelta(days=1)
        mes, anio = mes_dominante(fecha, fecha_fin)
        return f"Ciclo {MESES[mes - 1]} {anio}"
    try:
        anio, mes = clave.split("-")[:2]
        return f"Ciclo {MESES[int(mes) - 1]} {anio}"
    except (ValueError, IndexError):
        return "Ciclo actual"


def mes_dominante(inicio, fin):
    dias_por_mes = {}
    actual = inicio
    while actual <= fin:
        clave = (actual.year, actual.month)
        dias_por_mes[clave] = dias_por_mes.get(clave, 0) + 1
        actual += timedelta(days=1)
    anio, mes = max(dias_por_mes, key=lambda clave: dias_por_mes[clave])
    return mes, anio


def rango_ciclo(clave, movimientos):
    fecha_inicio = fecha_movimiento(clave)
    if fecha_inicio:
        proximo_mes = sumar_meses(fecha_inicio, 1)
        fecha_fin = fecha_movimiento(penultimo_dia_habil_mes(proximo_mes))
        return fecha_inicio, fecha_fin - timedelta(days=1)

    try:
        anio, mes = [int(parte) for parte in clave.split("-")[:2]]
    except (ValueError, IndexError):
        return rango_dashboard(date.today(), movimientos)

    inicio = date(anio, mes, 1)
    fin = date(anio, mes, calendar.monthrange(anio, mes)[1])
    return inicio, fin


def opciones_ciclos(movimientos):
    claves = {
        fecha.isoformat()
        for item in movimientos
        if es_sueldo(item) and (fecha := fecha_movimiento(item.get("fecha", "")))
    }
    claves.add(clave_ciclo(date.today(), movimientos))

    if not claves:
        claves = {
            f"{fecha.year}-{fecha.month:02d}"
            for item in movimientos
            if (fecha := fecha_movimiento(item.get("fecha", "")))
        }

    return [
        {"valor": clave, "etiqueta": etiqueta_ciclo(clave)}
        for clave in sorted(claves, reverse=True)
    ]


def movimientos_de_ciclo(movimientos, clave):
    inicio, fin = rango_ciclo(clave, movimientos)
    items = [
        item
        for item in movimientos
        if (fecha := fecha_movimiento(item.get("fecha", ""))) and inicio <= fecha <= fin
    ]
    saldo_anterior = saldo_antes_de(movimientos, inicio)
    if abs(saldo_anterior) >= 0.01:
        items.append(
            {
                "fecha": inicio.isoformat(),
                "tipo": "Ingreso",
                "categoria": "Saldo anterior",
                "descripcion": "Arrastre del ciclo anterior",
                "monto": saldo_anterior,
                "id": "",
            }
        )
    return sorted(items, key=lambda item: item["fecha"], reverse=True), inicio, fin


def asegurar_sueldo_automatico(hoy=None):
    hoy = hoy or date.today()
    fecha_sueldo = fecha_sueldo_esperada(hoy)
    if not fecha_sueldo or hoy < fecha_sueldo:
        return False

    movimientos = leer_movimientos()
    if any(
        es_sueldo(item) and fecha_movimiento(item.get("fecha", "")) == fecha_sueldo
        for item in movimientos
    ):
        return False

    sueldo_anterior = ultimo_sueldo_antes_de(movimientos, fecha_sueldo)
    if not sueldo_anterior:
        return False

    guardar_movimiento(
        {
            "fecha": fecha_sueldo.isoformat(),
            "tipo": "Ingreso",
            "categoria": "Sueldo",
            "descripcion": "Sueldo",
            "monto": sueldo_anterior[1]["monto"],
        }
    )
    return True


def moneda(valor):
    return f"${valor:,.0f}".replace(",", ".")


app.jinja_env.filters["moneda"] = moneda


def tooltip_operaciones(items, titulo):
    if not items:
        return f"{titulo}: {moneda(0)}"
    total = sum(item["monto"] for item in items)
    lineas = [f"{titulo}: {moneda(total)}"]
    for item in items[:6]:
        nombre = item.get("descripcion") or item.get("categoria") or item.get("persona") or "Sin detalle"
        lineas.append(f"{item.get('fecha', '')} · {nombre}: {moneda(item['monto'])}")
    if len(items) > 6:
        lineas.append(f"+{len(items) - 6} mas")
    return "\n".join(lineas)


app.jinja_env.filters["tooltip_operaciones"] = tooltip_operaciones


def operaciones_json(items, titulo):
    total = sum(item["monto"] for item in items)
    return json.dumps(
        {
            "titulo": titulo,
            "total": moneda(total),
            "items": [
                {
                    "fecha": item.get("fecha", ""),
                    "nombre": item.get("descripcion")
                    or item.get("categoria")
                    or item.get("persona")
                    or "Sin detalle",
                    "monto": moneda(item["monto"]),
                }
                for item in items
            ],
        },
        ensure_ascii=False,
    )


app.jinja_env.filters["operaciones_json"] = operaciones_json


def color_categoria(indice):
    colores = [
        "#1f6feb",
        "#c2410c",
        "#15803d",
        "#7c3aed",
        "#b45309",
        "#0f766e",
        "#be123c",
        "#4338ca",
    ]
    return colores[indice % len(colores)]


def preparar_segmentos(items):
    total = sum(item["monto"] for item in items)
    inicio = 0
    segmentos = []
    for indice, item in enumerate(items):
        porcentaje = item["monto"] / total * 100 if total else 0
        fin = inicio + porcentaje
        item["color"] = item.get("color") or color_categoria(indice)
        item["porcentaje"] = porcentaje
        item["offset"] = -inicio
        angulo = (inicio + porcentaje / 2) / 100 * 360 - 90
        radio = 37
        item["label_x"] = 60 + radio * math.cos(math.radians(angulo))
        item["label_y"] = 60 + radio * math.sin(math.radians(angulo))
        item["mostrar_label"] = porcentaje >= 7
        segmentos.append(f"{item['color']} {inicio:.2f}% {fin:.2f}%")
        inicio = fin
    return items, ", ".join(segmentos) if segmentos else "#e5e7eb 0% 100%", total


def calcular_semanas_restantes(hoy=None, fecha_fin=None):
    hoy = hoy or date.today()
    if fecha_fin is None:
        ultimo_dia = calendar.monthrange(hoy.year, hoy.month)[1]
        fecha_fin = date(hoy.year, hoy.month, ultimo_dia)
    dias_restantes = max((fecha_fin - hoy).days + 1, 1)
    semanas = max(1, ceil(dias_restantes / 7))
    return semanas, dias_restantes, hoy


def rango_dashboard(hoy=None, movimientos=None):
    hoy = hoy or date.today()
    movimientos = movimientos or []
    sueldo = ultimo_sueldo(movimientos)
    if sueldo:
        inicio = sueldo[0]
        proximo_mes = sumar_meses(inicio, 1)
        proximo_sueldo = fecha_movimiento(penultimo_dia_habil_mes(proximo_mes))
        fin = proximo_sueldo - timedelta(days=1)
        return inicio, fin

    inicio_mes = date(hoy.year, hoy.month, 1)
    inicio = inicio_mes - timedelta(days=7)
    ultimo_dia = calendar.monthrange(hoy.year, hoy.month)[1]
    fin = date(hoy.year, hoy.month, ultimo_dia)
    return inicio, fin


def fecha_movimiento(valor):
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError:
        return None


def periodo_movimiento(valor):
    fecha = fecha_movimiento(valor)
    if not fecha:
        return ""
    return f"{fecha.year}-{fecha.month:02d}"


def descripcion_automatizacion(item):
    return item["descripcion"] or item["categoria"]


def mismo_texto(valor, otro):
    return (valor or "").strip().lower() == (otro or "").strip().lower()


def movimiento_coincide_automatizacion(movimiento, automatizacion):
    descripcion = automatizacion.get("descripcion", "").strip()
    descripcion_coincide = (
        not descripcion
        or mismo_texto(movimiento.get("descripcion"), descripcion_automatizacion(automatizacion))
    )
    return (
        movimiento.get("tipo") == automatizacion.get("tipo")
        and mismo_texto(movimiento.get("categoria"), automatizacion.get("categoria"))
        and descripcion_coincide
        and abs(float(movimiento.get("monto") or 0) - float(automatizacion.get("monto") or 0)) < 0.01
    )


def actualizar_automatizaciones_por_movimiento(movimiento, movimientos_actuales):
    periodo = periodo_movimiento_ciclo(movimiento.get("fecha", ""), movimientos_actuales)
    if not periodo:
        return

    automatizaciones = leer_automatizaciones()
    hubo_cambios = False
    for item in automatizaciones:
        if item.get("ultimo_confirmado") != periodo:
            continue
        if not movimiento_coincide_automatizacion(movimiento, item):
            continue
        existe_movimiento = any(
            periodo_movimiento_ciclo(actual.get("fecha", ""), movimientos_actuales) == periodo
            and movimiento_coincide_automatizacion(actual, item)
            for actual in movimientos_actuales
        )
        if not existe_movimiento:
            item["ultimo_confirmado"] = ""
            item["ticket_ultimo"] = ""
            hubo_cambios = True

    if hubo_cambios:
        escribir_automatizaciones(automatizaciones)


def sincronizar_automatizaciones_confirmadas():
    asegurar_sueldo_automatico()
    automatizaciones = leer_automatizaciones()
    movimientos = leer_movimientos()
    periodo = periodo_actual()
    hubo_cambios = False

    for item in automatizaciones:
        if esta_anulada(item, periodo):
            continue

        existe_en_periodo_actual = any(
            periodo_movimiento_ciclo(movimiento.get("fecha", ""), movimientos) == periodo
            and movimiento_coincide_automatizacion(movimiento, item)
            for movimiento in movimientos
        )
        if existe_en_periodo_actual and item.get("ultimo_confirmado") != periodo:
            item["ultimo_confirmado"] = periodo
            item["ticket_ultimo"] = ""
            hubo_cambios = True
            continue

        periodo_confirmado = item.get("ultimo_confirmado", "")
        if not periodo_confirmado:
            continue
        existe_movimiento = any(
            periodo_movimiento_ciclo(movimiento.get("fecha", ""), movimientos) == periodo_confirmado
            and movimiento_coincide_automatizacion(movimiento, item)
            for movimiento in movimientos
        )
        if not existe_movimiento:
            item["ultimo_confirmado"] = ""
            item["ticket_ultimo"] = ""
            hubo_cambios = True

    if hubo_cambios:
        escribir_automatizaciones(automatizaciones)

    return automatizaciones


def esta_anulada(item, periodo=None):
    periodo = periodo or periodo_actual()
    return item.get("ultimo_anulado") == periodo


def clave_periodo(fecha, vista):
    if vista == "diaria":
        return fecha.isoformat()
    if vista == "semanal":
        anio, semana, _ = fecha.isocalendar()
        return f"{anio}-S{semana:02d}"
    return f"{fecha.year}-{fecha.month:02d}"


def etiqueta_periodo(fecha, vista):
    if vista == "diaria":
        return fecha.strftime("%d-%m")
    if vista == "semanal":
        return f"S{fecha.isocalendar().week:02d}"
    return fecha.strftime("%m")


def rango_historico(vista, fechas):
    if vista == "diaria":
        fin = max(fechas)
        ventana_inicio = fin - timedelta(days=30)
        fechas_relevantes = [fecha for fecha in fechas if ventana_inicio <= fecha <= fin]
        inicio = min(fechas_relevantes) if fechas_relevantes else ventana_inicio
        return inicio, fin
    if vista == "semanal":
        fin = max(fechas)
        fin = fin - timedelta(days=fin.weekday())
        ventana_inicio = fin - timedelta(weeks=11)
        fechas_relevantes = [fecha for fecha in fechas if ventana_inicio <= fecha <= fin]
        primer_dato = min(fechas_relevantes) if fechas_relevantes else ventana_inicio
        inicio_datos = primer_dato - timedelta(days=primer_dato.weekday())
        inicio = max(inicio_datos, ventana_inicio)
        return inicio, fin
    fin = max(fechas)
    fin = date(fin.year, fin.month, 1)
    mes = fin.month - 11
    anio = fin.year
    while mes <= 0:
        mes += 12
        anio -= 1
    ventana_inicio = date(anio, mes, 1)
    fechas_relevantes = [fecha for fecha in fechas if ventana_inicio <= fecha <= fin]
    primer_dato = min(fechas_relevantes) if fechas_relevantes else ventana_inicio
    inicio_datos = date(primer_dato.year, primer_dato.month, 1)
    inicio = max(inicio_datos, ventana_inicio)
    return inicio, fin


def marcas_eje_y(maximo):
    if maximo <= 0:
        return [0]
    return [maximo * paso / 4 for paso in range(4, -1, -1)]


def construir_periodos(vista, fechas):
    periodos = {}
    if not fechas:
        return {}

    def nuevo_periodo(fecha):
        clave = clave_periodo(fecha, vista)
        periodos.setdefault(
            clave,
            {
                "periodo": clave,
                "etiqueta": etiqueta_periodo(fecha, vista),
                "ingresos": 0,
                "gastos": 0,
                "ahorros": 0,
                "me_deben": 0,
                "debo": 0,
                "balance": 0,
                "detalle_ingresos": [],
                "detalle_gastos": [],
                "detalle_ahorros": [],
                "detalle_me_deben": [],
                "detalle_debo": [],
            },
        )

    inicio, fin = rango_historico(vista, fechas)
    if vista == "diaria":
        actual = inicio
        while actual <= fin:
            nuevo_periodo(actual)
            actual += timedelta(days=1)
    elif vista == "semanal":
        actual = inicio - timedelta(days=inicio.weekday())
        while actual <= fin:
            nuevo_periodo(actual)
            actual += timedelta(days=7)
    else:
        actual = date(inicio.year, inicio.month, 1)
        while actual <= fin:
            nuevo_periodo(actual)
            if actual.month == 12:
                actual = date(actual.year + 1, 1, 1)
            else:
                actual = date(actual.year, actual.month + 1, 1)

    return periodos


def resumen_historico(vista):
    movimientos = leer_movimientos()
    deudas_lista = leer_deudas()
    fechas_movimientos = []
    fechas_deudas = []

    for item in movimientos:
        fecha = fecha_movimiento(item["fecha"])
        if fecha:
            fechas_movimientos.append(fecha)
    for item in deudas_lista:
        fecha = fecha_movimiento(item["fecha"])
        if fecha:
            fechas_deudas.append(fecha)

    periodos = construir_periodos(vista, fechas_movimientos)
    periodos_deudas = construir_periodos(vista, fechas_deudas)

    for item in movimientos:
        fecha = fecha_movimiento(item["fecha"])
        if not fecha:
            continue
        clave = clave_periodo(fecha, vista)
        if clave not in periodos:
            continue
        periodo = periodos[clave]
        if item["tipo"] == "Ingreso":
            periodo["ingresos"] += item["monto"]
            periodo["detalle_ingresos"].append(item)
        elif item["tipo"] == "Gasto":
            periodo["gastos"] += item["monto"]
            periodo["detalle_gastos"].append(item)
        elif item["tipo"] == "Ahorro":
            periodo["ahorros"] += item["monto"]
            periodo["detalle_ahorros"].append(item)

    for item in deudas_lista:
        fecha = fecha_movimiento(item["fecha"])
        if not fecha:
            continue
        clave = clave_periodo(fecha, vista)
        if clave not in periodos_deudas:
            continue
        periodo = periodos_deudas[clave]
        if item["tipo"] == "Me deben":
            periodo["me_deben"] += item["monto"]
            periodo["detalle_me_deben"].append(item)
        elif item["tipo"] == "Debo":
            periodo["debo"] += item["monto"]
            periodo["detalle_debo"].append(item)

    filas = [periodos[clave] for clave in sorted(periodos)]
    filas_deudas = [periodos_deudas[clave] for clave in sorted(periodos_deudas)]
    for fila in filas:
        fila["balance"] = fila["ingresos"] - fila["gastos"] - fila["ahorros"]
    for fila in filas_deudas:
        fila["balance"] = fila["me_deben"] - fila["debo"]

    maximo = max(
        [
            valor
            for fila in filas
            for valor in [
                fila["ingresos"],
                fila["gastos"],
                fila["ahorros"],
                fila["me_deben"],
                fila["debo"],
            ]
        ]
        or [1]
    )
    maximo_deudas = max(
        [valor for fila in filas_deudas for valor in [fila["me_deben"], fila["debo"]]]
        or [1]
    )
    return filas, maximo, marcas_eje_y(maximo), filas_deudas, maximo_deudas, marcas_eje_y(maximo_deudas)


def calcular_dashboard(filtrar_periodo=False):
    hoy = date.today()
    asegurar_sueldo_automatico(hoy)
    movimientos = leer_movimientos()
    periodo_inicio = None
    periodo_fin = None
    saldo_anterior = 0
    if filtrar_periodo:
        periodo_inicio, periodo_fin = rango_dashboard(hoy, movimientos)
        saldo_anterior = saldo_antes_de(movimientos, periodo_inicio)
        movimientos = [
            item
            for item in movimientos
            if (fecha := fecha_movimiento(item["fecha"]))
            and periodo_inicio <= fecha <= periodo_fin
        ]
        if abs(saldo_anterior) >= 0.01:
            movimientos.append(
                {
                    "fecha": periodo_inicio.isoformat(),
                    "tipo": "Ingreso",
                    "categoria": "Saldo anterior",
                    "descripcion": "Arrastre del ciclo anterior",
                    "monto": saldo_anterior,
                    "id": "",
                }
            )
    semanas, dias_restantes, hoy = calcular_semanas_restantes(hoy, periodo_fin)
    movimientos = sorted(movimientos, key=lambda item: item["fecha"], reverse=True)
    ingresos_lista = [item for item in movimientos if item["tipo"] == "Ingreso"]
    gastos_lista = [item for item in movimientos if item["tipo"] == "Gasto"]
    ahorros_lista = [item for item in movimientos if item["tipo"] == "Ahorro"]
    ingresos = sum(item["monto"] for item in ingresos_lista)
    gastos = sum(item["monto"] for item in gastos_lista)
    ahorros = sum(item["monto"] for item in ahorros_lista)
    disponible = ingresos - gastos - ahorros
    cuota_semanal = disponible / semanas if semanas > 0 else 0
    return {
        "movimientos": movimientos,
        "ingresos_lista": ingresos_lista,
        "gastos_lista": gastos_lista,
        "ahorros_lista": ahorros_lista,
        "ingresos": ingresos,
        "gastos": gastos,
        "ahorros": ahorros,
        "balance": ingresos - gastos,
        "disponible": disponible,
        "semanas": semanas,
        "dias_restantes": dias_restantes,
        "fecha_calculo": hoy,
        "periodo_inicio": periodo_inicio,
        "periodo_fin": periodo_fin,
        "cuota_semanal": cuota_semanal,
    }


def calcular_planificacion():
    datos = calcular_dashboard(filtrar_periodo=True)
    periodo_inicio = datos["periodo_inicio"]
    periodo_fin = datos["periodo_fin"]
    periodo = periodo_actual()
    movimientos = datos["movimientos"]

    automatizaciones = sincronizar_automatizaciones_confirmadas()
    fijos_pendientes = []
    for item in automatizaciones:
        if not item["activo"] or esta_anulada(item, periodo):
            continue
        if item.get("ultimo_confirmado") == periodo:
            continue
        existe_movimiento = any(
            (fecha := fecha_movimiento(movimiento.get("fecha", "")))
            and periodo_inicio <= fecha <= periodo_fin
            and movimiento_coincide_automatizacion(movimiento, item)
            for movimiento in movimientos
        )
        if not existe_movimiento:
            fijos_pendientes.append(item)

    planificaciones = []
    for item in leer_planificaciones():
        fecha = fecha_movimiento(item.get("fecha", ""))
        if fecha and periodo_inicio <= fecha <= periodo_fin:
            planificaciones.append(item)

    fijos_gastos = sum(item["monto"] for item in fijos_pendientes if item["tipo"] == "Gasto")
    fijos_ahorros = sum(item["monto"] for item in fijos_pendientes if item["tipo"] == "Ahorro")
    plan_ingresos = sum(item["monto"] for item in planificaciones if item["tipo"] == "Ingreso")
    plan_gastos = sum(item["monto"] for item in planificaciones if item["tipo"] == "Gasto")
    plan_ahorros = sum(item["monto"] for item in planificaciones if item["tipo"] == "Ahorro")

    ingresos = datos["ingresos"] + plan_ingresos
    gastos = datos["gastos"] + fijos_gastos + plan_gastos
    ahorros = datos["ahorros"] + fijos_ahorros + plan_ahorros
    disponible = ingresos - gastos - ahorros

    return {
        "periodo_inicio": periodo_inicio,
        "periodo_fin": periodo_fin,
        "ingresos_base": datos["ingresos"],
        "gastos_base": datos["gastos"],
        "ahorros_base": datos["ahorros"],
        "fijos_pendientes": fijos_pendientes,
        "fijos_gastos": fijos_gastos,
        "fijos_ahorros": fijos_ahorros,
        "planificaciones": planificaciones,
        "plan_ingresos": plan_ingresos,
        "plan_gastos": plan_gastos,
        "plan_ahorros": plan_ahorros,
        "ingresos": ingresos,
        "gastos": gastos,
        "ahorros": ahorros,
        "disponible": disponible,
    }


@app.route("/")
def index():
    return render_template("index.html", **calcular_dashboard(filtrar_periodo=True))


@app.route("/planificacion", methods=["GET", "POST"])
def planificacion():
    if request.method == "POST":
        tipo = request.form.get("tipo", "Gasto")
        if tipo not in TIPOS_VALIDOS:
            tipo = "Gasto"
        guardar_planificacion(
            {
                "fecha": request.form.get("fecha", ""),
                "tipo": tipo,
                "categoria": request.form.get("categoria", "").strip(),
                "descripcion": request.form.get("descripcion", "").strip(),
                "monto": float(request.form.get("monto", 0) or 0),
            }
        )
        return redirect(url_for("planificacion"))

    return render_template("planificacion.html", **calcular_planificacion())


@app.route("/planificacion/eliminar/<int:planificacion_id>", methods=["POST"])
def eliminar_planificacion(planificacion_id):
    planificaciones = leer_planificaciones()
    if 0 <= planificacion_id < len(planificaciones):
        planificaciones.pop(planificacion_id)
        escribir_planificaciones(planificaciones)
    return redirect(url_for("planificacion"))


@app.route("/agregar", methods=["GET", "POST"])
def agregar():
    if request.method == "POST":
        movimiento = {
            "fecha": request.form.get("fecha", ""),
            "tipo": request.form.get("tipo", "Gasto")
            if request.form.get("tipo", "Gasto") in TIPOS_VALIDOS
            else "Gasto",
            "categoria": request.form.get("categoria", "").strip(),
            "descripcion": request.form.get("descripcion", "").strip(),
            "monto": float(request.form.get("monto", 0) or 0),
        }
        guardar_movimiento(movimiento)
        return redirect(url_for("index"))

    return render_template("agregar.html")


@app.route("/agregar/<tipo>", methods=["GET", "POST"])
def agregar_por_tipo(tipo):
    tipos = {
        "ingreso": ("Ingreso", "Agregar ingreso", "Sueldo, venta, bono..."),
        "gasto": ("Gasto", "Agregar gasto", "Comida, transporte, arriendo..."),
        "ahorro": ("Ahorro", "Agregar ahorro", "Emergencia, viaje, inversion..."),
    }
    if tipo not in tipos:
        return redirect(url_for("agregar"))

    tipo_movimiento, titulo, ayuda_categoria = tipos[tipo]
    if request.method == "POST":
        movimiento = {
            "fecha": request.form.get("fecha", ""),
            "tipo": tipo_movimiento,
            "categoria": request.form.get("categoria", "").strip(),
            "descripcion": request.form.get("descripcion", "").strip(),
            "monto": float(request.form.get("monto", 0) or 0),
        }
        guardar_movimiento(movimiento)
        return redirect(url_for("index"))

    return render_template(
        "agregar.html",
        tipo=tipo_movimiento,
        titulo=titulo,
        ayuda_categoria=ayuda_categoria,
        sueldo_fecha=penultimo_dia_habil_mes() if tipo_movimiento == "Ingreso" else "",
    )


@app.route("/agregar/sueldo", methods=["POST"])
def agregar_sueldo():
    guardar_movimiento(
        {
            "fecha": penultimo_dia_habil_mes(),
            "tipo": "Ingreso",
            "categoria": "Sueldo",
            "descripcion": "Sueldo",
            "monto": float(request.form.get("monto", 0) or 0),
        }
    )
    return redirect(url_for("index"))


@app.route("/editar/<int:movimiento_id>", methods=["GET", "POST"])
def editar(movimiento_id):
    movimientos = leer_movimientos()
    if movimiento_id < 0 or movimiento_id >= len(movimientos):
        return redirect(url_for("resumen"))

    movimiento = movimientos[movimiento_id]
    if request.method == "POST":
        tipo = request.form.get("tipo", movimiento["tipo"])
        movimiento_anterior = movimiento.copy()
        movimientos[movimiento_id] = {
            "fecha": request.form.get("fecha", ""),
            "tipo": tipo if tipo in TIPOS_VALIDOS else movimiento["tipo"],
            "categoria": request.form.get("categoria", "").strip(),
            "descripcion": request.form.get("descripcion", "").strip(),
            "monto": float(request.form.get("monto", 0) or 0),
        }
        escribir_movimientos(movimientos)
        actualizar_automatizaciones_por_movimiento(movimiento_anterior, movimientos)
        return redirect(url_for("resumen"))

    return render_template(
        "agregar.html",
        titulo="Editar movimiento",
        tipo=None,
        movimiento=movimiento,
        ayuda_categoria="Categoria del movimiento",
        volver_a=url_for("resumen"),
    )


@app.route("/eliminar/<int:movimiento_id>", methods=["POST"])
def eliminar(movimiento_id):
    movimientos = leer_movimientos()
    if 0 <= movimiento_id < len(movimientos):
        movimiento_eliminado = movimientos.pop(movimiento_id)
        escribir_movimientos(movimientos)
        actualizar_automatizaciones_por_movimiento(movimiento_eliminado, movimientos)
    return redirect(url_for("resumen"))


@app.route("/resumen/agregar", methods=["POST"])
def agregar_desde_resumen():
    tipo = request.form.get("tipo", "Gasto")
    if tipo not in TIPOS_VALIDOS:
        tipo = "Gasto"
    guardar_movimiento(
        {
            "fecha": request.form.get("fecha", ""),
            "tipo": tipo,
            "categoria": request.form.get("categoria", "").strip(),
            "descripcion": request.form.get("descripcion", "").strip(),
            "monto": float(request.form.get("monto", 0) or 0),
        }
    )
    return redirect(f"{url_for('resumen')}#movimientos")


@app.route("/gastos-fijos", methods=["GET", "POST"])
@app.route("/automatizacion", methods=["GET", "POST"])
def automatizacion():
    if request.method == "POST":
        tipo = request.form.get("tipo", "Gasto")
        if tipo not in TIPOS_AUTOMATIZACION:
            tipo = "Gasto"
        try:
            dia_mes = int(request.form.get("dia_mes", 1) or 1)
        except ValueError:
            dia_mes = 1
        automatizaciones = leer_automatizaciones()
        automatizaciones.append(
            {
                "tipo": tipo,
                "categoria": request.form.get("categoria", "").strip(),
                "descripcion": request.form.get("descripcion", "").strip(),
                "monto": float(request.form.get("monto", 0) or 0),
                "dia_mes": min(max(dia_mes, 1), 31),
                "activo": True,
                "ultimo_confirmado": "",
                "ticket_ultimo": "",
                "ultimo_anulado": "",
                "razon_anulado": "",
            }
        )
        escribir_automatizaciones(automatizaciones)
        return redirect(url_for("automatizacion"))

    asegurar_sueldo_automatico()
    periodo = periodo_actual()
    automatizaciones = sorted(
        sincronizar_automatizaciones_confirmadas(),
        key=lambda item: (
            item["categoria"].lower(),
            item["descripcion"].lower(),
            item["tipo"].lower(),
        ),
    )
    pendientes = [
        item
        for item in automatizaciones
        if item["activo"]
        and item.get("ultimo_confirmado") != periodo
        and not esta_anulada(item, periodo)
    ]
    confirmadas = [
        item
        for item in automatizaciones
        if item["activo"] and item.get("ultimo_confirmado") == periodo
    ]
    anuladas = [
        item
        for item in automatizaciones
        if item["activo"] and esta_anulada(item, periodo)
    ]
    total_gastos_fijos = sum(
        item["monto"]
        for item in automatizaciones
        if item["activo"] and item["tipo"] == "Gasto" and not esta_anulada(item, periodo)
    )
    total_gastos_fijos_sin_arriendo = sum(
        item["monto"]
        for item in automatizaciones
        if item["activo"]
        and item["tipo"] == "Gasto"
        and not esta_anulada(item, periodo)
        and "arriendo" not in f"{item['categoria']} {item['descripcion']}".lower()
    )
    total_ahorros_planificados = sum(
        item["monto"]
        for item in automatizaciones
        if item["activo"] and item["tipo"] == "Ahorro" and not esta_anulada(item, periodo)
    )
    compromiso_mensual = total_gastos_fijos + total_ahorros_planificados
    sueldo = ultimo_sueldo(leer_movimientos())
    sueldo_monto = sueldo[1]["monto"] if sueldo else 0
    return render_template(
        "automatizacion.html",
        automatizaciones=automatizaciones,
        pendientes=pendientes,
        confirmadas=confirmadas,
        anuladas=anuladas,
        periodo=periodo,
        total_gastos_fijos=total_gastos_fijos,
        total_gastos_fijos_sin_arriendo=total_gastos_fijos_sin_arriendo,
        total_ahorros_planificados=total_ahorros_planificados,
        compromiso_mensual=compromiso_mensual,
        sueldo_menos_compromisos=sueldo_monto - compromiso_mensual,
    )


@app.route("/automatizacion/confirmar/<int:automatizacion_id>", methods=["POST"])
def confirmar_automatizacion(automatizacion_id):
    automatizaciones = leer_automatizaciones()
    if automatizacion_id < 0 or automatizacion_id >= len(automatizaciones):
        return redirect(url_for("automatizacion"))

    item = automatizaciones[automatizacion_id]
    descripcion = item["descripcion"] or item["categoria"]
    fecha = request.form.get("fecha") or proxima_fecha_mensual(item["dia_mes"])
    guardar_movimiento(
        {
            "fecha": fecha,
            "tipo": item["tipo"],
            "categoria": item["categoria"],
            "descripcion": descripcion,
            "monto": item["monto"],
        }
    )
    item["ultimo_confirmado"] = periodo_movimiento_ciclo(fecha) or periodo_actual()
    item["ticket_ultimo"] = ""
    item["ultimo_anulado"] = ""
    item["razon_anulado"] = ""
    automatizaciones[automatizacion_id] = item
    escribir_automatizaciones(automatizaciones)
    return redirect(url_for("automatizacion"))


@app.route("/automatizacion/anular/<int:automatizacion_id>", methods=["POST"])
def anular_automatizacion(automatizacion_id):
    automatizaciones = leer_automatizaciones()
    if automatizacion_id < 0 or automatizacion_id >= len(automatizaciones):
        return redirect(url_for("automatizacion"))

    razon = request.form.get("razon_anulado", "").strip()
    if not razon:
        return redirect(url_for("automatizacion"))

    item = automatizaciones[automatizacion_id]
    item["ultimo_anulado"] = periodo_actual()
    item["razon_anulado"] = razon
    item["ultimo_confirmado"] = ""
    item["ticket_ultimo"] = ""
    automatizaciones[automatizacion_id] = item
    escribir_automatizaciones(automatizaciones)
    return redirect(url_for("automatizacion"))


@app.route("/automatizacion/desanular/<int:automatizacion_id>", methods=["POST"])
def desanular_automatizacion(automatizacion_id):
    automatizaciones = leer_automatizaciones()
    if automatizacion_id < 0 or automatizacion_id >= len(automatizaciones):
        return redirect(url_for("automatizacion"))

    item = automatizaciones[automatizacion_id]
    if esta_anulada(item):
        item["ultimo_anulado"] = ""
        item["razon_anulado"] = ""
        automatizaciones[automatizacion_id] = item
        escribir_automatizaciones(automatizaciones)
    return redirect(url_for("automatizacion"))


@app.route("/gastos-fijos/descargar")
def descargar_gastos_fijos():
    periodo = periodo_actual()
    salida = []
    salida.append(
        [
            "Periodo",
            "Tipo",
            "Descripcion",
            "Categoria",
            "Dia del mes",
            "Monto",
            "Estado",
        ]
    )
    for item in sorted(
        sincronizar_automatizaciones_confirmadas(),
        key=lambda fila: (
            fila["descripcion"].lower(),
            fila["categoria"].lower(),
            fila["tipo"].lower(),
        ),
    ):
        if item.get("ultimo_confirmado") == periodo:
            estado = "Confirmado"
        elif esta_anulada(item, periodo):
            estado = f"Anulado: {item.get('razon_anulado', '')}"
        else:
            estado = "Pendiente"
        salida.append(
            [
                periodo,
                item["tipo"],
                item["descripcion"] or "Sin descripcion",
                item["categoria"] or "Sin categoria",
                item["dia_mes"],
                int(item["monto"]) if item["monto"].is_integer() else item["monto"],
                estado,
            ]
        )

    contenido = "\ufeff" + "\n".join(
        ";".join(str(valor).replace(";", ",") for valor in fila) for fila in salida
    )
    return Response(
        contenido,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=gastos_fijos_{periodo}.csv"
        },
    )


@app.route("/automatizacion/editar/<int:automatizacion_id>", methods=["GET", "POST"])
def editar_automatizacion(automatizacion_id):
    automatizaciones = leer_automatizaciones()
    if automatizacion_id < 0 or automatizacion_id >= len(automatizaciones):
        return redirect(url_for("automatizacion"))

    item = automatizaciones[automatizacion_id]
    if request.method == "POST":
        tipo = request.form.get("tipo", item["tipo"])
        if tipo not in TIPOS_AUTOMATIZACION:
            tipo = item["tipo"]
        try:
            dia_mes = int(request.form.get("dia_mes", item["dia_mes"]) or item["dia_mes"])
        except ValueError:
            dia_mes = item["dia_mes"]
        item.update(
            {
                "tipo": tipo,
                "categoria": request.form.get("categoria", "").strip(),
                "descripcion": request.form.get("descripcion", "").strip(),
                "monto": float(request.form.get("monto", 0) or 0),
                "dia_mes": min(max(dia_mes, 1), 31),
            }
        )
        automatizaciones[automatizacion_id] = item
        escribir_automatizaciones(automatizaciones)
        return redirect(url_for("automatizacion"))

    return render_template("editar_automatizacion.html", item=item)


@app.route("/automatizacion/eliminar/<int:automatizacion_id>", methods=["POST"])
def eliminar_automatizacion(automatizacion_id):
    automatizaciones = leer_automatizaciones()
    if 0 <= automatizacion_id < len(automatizaciones):
        automatizaciones.pop(automatizacion_id)
        escribir_automatizaciones(automatizaciones)
    return redirect(url_for("automatizacion"))


@app.route("/deudas", methods=["GET", "POST"])
def deudas():
    if request.method == "POST":
        tipo = request.form.get("tipo", "Me deben")
        if tipo not in TIPOS_DEUDA:
            tipo = "Me deben"
        deudas_lista = leer_deudas()
        deudas_lista.append(
            {
                "fecha": request.form.get("fecha", ""),
                "tipo": tipo,
                "persona": request.form.get("persona", "").strip(),
                "categoria": request.form.get("categoria", "").strip(),
                "descripcion": request.form.get("descripcion", "").strip(),
                "monto": float(request.form.get("monto", 0) or 0),
                "estado": "Pendiente",
                "fecha_pago": "",
            }
        )
        escribir_deudas(deudas_lista)
        return redirect(url_for("deudas"))

    deudas_lista = leer_deudas()
    pendientes = [item for item in deudas_lista if item["estado"] != "Pagada"]
    pagadas = [item for item in deudas_lista if item["estado"] == "Pagada"]
    me_deben = [item for item in pendientes if item["tipo"] == "Me deben"]
    debo = [item for item in pendientes if item["tipo"] == "Debo"]
    total_me_deben = sum(item["monto"] for item in me_deben)
    total_debo = sum(item["monto"] for item in debo)
    return render_template(
        "deudas.html",
        deudas=deudas_lista,
        pendientes=pendientes,
        pagadas=pagadas,
        me_deben=me_deben,
        debo=debo,
        total_me_deben=total_me_deben,
        total_debo=total_debo,
        balance_deudas=total_me_deben - total_debo,
    )


@app.route("/deudas/pagar/<int:deuda_id>", methods=["POST"])
def pagar_deuda(deuda_id):
    deudas_lista = leer_deudas()
    if deuda_id < 0 or deuda_id >= len(deudas_lista):
        return redirect(url_for("deudas"))

    item = deudas_lista[deuda_id]
    if item["estado"] != "Pagada":
        fecha_pago = request.form.get("fecha_pago") or date.today().isoformat()
        tipo_movimiento = "Ingreso" if item["tipo"] == "Me deben" else "Gasto"
        guardar_movimiento(
            {
                "fecha": fecha_pago,
                "tipo": tipo_movimiento,
                "categoria": item["categoria"] or "Deudas",
                "descripcion": f"{item['tipo']} - {item['persona']} | {item['descripcion']}",
                "monto": item["monto"],
            }
        )
        item["estado"] = "Pagada"
        item["fecha_pago"] = fecha_pago
        deudas_lista[deuda_id] = item
        escribir_deudas(deudas_lista)
    return redirect(url_for("deudas"))


@app.route("/historico")
def historico():
    vista = request.args.get("vista", "diaria")
    if vista not in {"diaria", "semanal", "mensual"}:
        vista = "diaria"
    filtro_tipo = request.args.get("tipo", "Todos")
    if filtro_tipo not in TIPOS_VALIDOS | {"Todos"}:
        filtro_tipo = "Todos"
    filas, maximo, eje_y, filas_deudas, maximo_deudas, eje_y_deudas = resumen_historico(vista)
    totales = {
        "ingresos": sum(fila["ingresos"] for fila in filas),
        "gastos": sum(fila["gastos"] for fila in filas),
        "ahorros": sum(fila["ahorros"] for fila in filas),
        "me_deben": sum(fila["me_deben"] for fila in filas),
        "debo": sum(fila["debo"] for fila in filas),
    }
    datasets_por_tipo = {
        "Ingreso": {
            "label": "Ingresos",
            "values": [fila["ingresos"] for fila in filas],
            "color": "#15803d",
            "details": [operaciones_json(fila["detalle_ingresos"], "Ingresos") for fila in filas],
        },
        "Gasto": {
            "label": "Gastos",
            "values": [fila["gastos"] for fila in filas],
            "color": "#c2410c",
            "details": [operaciones_json(fila["detalle_gastos"], "Gastos") for fila in filas],
        },
        "Ahorro": {
            "label": "Ahorros",
            "values": [fila["ahorros"] for fila in filas],
            "color": "#7c3aed",
            "details": [operaciones_json(fila["detalle_ahorros"], "Ahorros") for fila in filas],
        },
    }
    datasets_movimientos = (
        list(datasets_por_tipo.values())
        if filtro_tipo == "Todos"
        else [datasets_por_tipo[filtro_tipo]]
    )
    return render_template(
        "historico.html",
        vista=vista,
        filtro_tipo=filtro_tipo,
        filas=filas,
        datasets_movimientos=datasets_movimientos,
        maximo=maximo,
        eje_y=eje_y,
        filas_deudas=filas_deudas,
        maximo_deudas=maximo_deudas,
        eje_y_deudas=eje_y_deudas,
        totales=totales,
    )


@app.route("/resumen")
def resumen():
    asegurar_sueldo_automatico()
    todos_movimientos = leer_movimientos()
    ciclos = opciones_ciclos(todos_movimientos)
    ciclo_seleccionado = request.args.get("ciclo") or (
        ciclos[0]["valor"] if ciclos else clave_ciclo(date.today(), todos_movimientos)
    )
    if ciclos and ciclo_seleccionado not in {item["valor"] for item in ciclos}:
        ciclo_seleccionado = ciclos[0]["valor"]
    ciclo_etiqueta = next(
        (item["etiqueta"] for item in ciclos if item["valor"] == ciclo_seleccionado),
        etiqueta_ciclo(ciclo_seleccionado),
    )
    movimientos, periodo_inicio, periodo_fin = movimientos_de_ciclo(
        todos_movimientos, ciclo_seleccionado
    )
    busqueda = request.args.get("q", "").strip()
    filtro_tipo = request.args.get("tipo", "Todos")
    semanas, _, _ = calcular_semanas_restantes(date.today(), periodo_fin)
    ingresos = sum(item["monto"] for item in movimientos if item["tipo"] == "Ingreso")
    gastos = sum(item["monto"] for item in movimientos if item["tipo"] == "Gasto")
    ahorros = sum(item["monto"] for item in movimientos if item["tipo"] == "Ahorro")
    disponible = ingresos - gastos - ahorros
    cuota_semanal = disponible / semanas if semanas > 0 else 0
    totales = {}
    for item in movimientos:
        clave = (item["tipo"], item["categoria"])
        totales[clave] = totales.get(clave, 0) + item["monto"]
    por_categoria = [
        {"tipo": tipo, "categoria": categoria, "monto": monto}
        for (tipo, categoria), monto in totales.items()
    ]
    por_categoria.sort(key=lambda item: (item["tipo"], -item["monto"]))

    gastos_por_categoria_base = [
        item for item in por_categoria if item["tipo"] == "Gasto" and item["monto"] > 0
    ]
    gastos_por_categoria = gastos_por_categoria_base[:7]
    otros_gastos = gastos_por_categoria_base[7:]
    if otros_gastos:
        gastos_por_categoria.append(
            {
                "tipo": "Gasto",
                "categoria": "Otros",
                "monto": sum(item["monto"] for item in otros_gastos),
            }
        )
    gastos_por_categoria, torta_gastos, total_gastos_categoria = preparar_segmentos(
        gastos_por_categoria
    )

    deuda = sum(
        item["monto"]
        for item in movimientos
        if item["tipo"] == "Gasto" and "deuda" in item["categoria"].lower()
    )
    costos_sin_deuda = max(gastos - deuda, 0)
    disponible_ingresos = max(ingresos - gastos - ahorros, 0)
    distribucion_ingresos = [
        {"categoria": "Gastos", "monto": costos_sin_deuda, "color": "#1f6feb"},
        {"categoria": "Deuda", "monto": deuda, "color": "#c2410c"},
        {"categoria": "Ahorro", "monto": ahorros, "color": "#7c3aed"},
        {"categoria": "Disponible", "monto": disponible_ingresos, "color": "#15803d"},
    ]
    distribucion_ingresos = [item for item in distribucion_ingresos if item["monto"] > 0]
    distribucion_ingresos, torta_ingresos, total_distribucion_ingresos = preparar_segmentos(
        distribucion_ingresos
    )

    movimientos_filtrados = movimientos
    if filtro_tipo in TIPOS_VALIDOS:
        movimientos_filtrados = [
            item for item in movimientos_filtrados if item["tipo"] == filtro_tipo
        ]
    if busqueda:
        texto = busqueda.lower()
        movimientos_filtrados = [
            item
            for item in movimientos_filtrados
            if texto
            in " ".join(
                [
                    item["fecha"],
                    item["tipo"],
                    item["categoria"],
                    item["descripcion"],
                    str(item["monto"]),
                ]
            ).lower()
        ]

    return render_template(
        "resumen.html",
        ingresos=ingresos,
        gastos=gastos,
        ahorros=ahorros,
        balance=ingresos - gastos,
        disponible=disponible,
        cuota_semanal=cuota_semanal,
        periodo_inicio=periodo_inicio,
        periodo_fin=periodo_fin,
        ciclos=ciclos,
        ciclo_seleccionado=ciclo_seleccionado,
        ciclo_etiqueta=ciclo_etiqueta,
        por_categoria=por_categoria,
        gastos_por_categoria=gastos_por_categoria,
        torta_gastos=torta_gastos,
        total_gastos_categoria=total_gastos_categoria,
        distribucion_ingresos=distribucion_ingresos,
        torta_ingresos=torta_ingresos,
        total_distribucion_ingresos=total_distribucion_ingresos,
        movimientos=movimientos,
        movimientos_filtrados=movimientos_filtrados,
        busqueda=busqueda,
        filtro_tipo=filtro_tipo,
    )


if __name__ == "__main__":
    asegurar_csv()
    app.run(debug=True)
