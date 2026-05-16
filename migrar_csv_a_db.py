import csv

from app import (
    AUTOMATIZACION_COLUMNAS,
    AUTOMATIZACIONES_PATH,
    COLUMNAS,
    CSV_PATH,
    DEUDA_COLUMNAS,
    DEUDAS_PATH,
    asegurar_db,
    escribir_automatizaciones,
    escribir_deudas,
    escribir_movimientos,
    usar_base_datos,
)


def leer_csv(path, columnas):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as archivo:
        reader = csv.DictReader(archivo)
        return [{columna: fila.get(columna, "") for columna in columnas} for fila in reader]


def normalizar_movimientos(items):
    for item in items:
        item["monto"] = float(item.get("monto") or 0)
    return items


def normalizar_automatizaciones(items):
    for item in items:
        item["monto"] = float(item.get("monto") or 0)
        item["dia_mes"] = int(item.get("dia_mes") or 1)
        item["activo"] = item.get("activo", "Si") != "No"
    return items


def normalizar_deudas(items):
    for item in items:
        item["monto"] = float(item.get("monto") or 0)
    return items


def main():
    if not usar_base_datos():
        raise SystemExit(
            "No hay conexion a PostgreSQL. Revisa DATABASE_URL, Finanzas/.env o Finanzas/link.txt."
        )

    asegurar_db()
    movimientos = normalizar_movimientos(leer_csv(CSV_PATH, COLUMNAS))
    automatizaciones = normalizar_automatizaciones(
        leer_csv(AUTOMATIZACIONES_PATH, AUTOMATIZACION_COLUMNAS)
    )
    deudas = normalizar_deudas(leer_csv(DEUDAS_PATH, DEUDA_COLUMNAS))

    escribir_movimientos(movimientos)
    escribir_automatizaciones(automatizaciones)
    escribir_deudas(deudas)

    print(f"Movimientos migrados: {len(movimientos)}")
    print(f"Gastos fijos migrados: {len(automatizaciones)}")
    print(f"Deudas migradas: {len(deudas)}")


if __name__ == "__main__":
    main()
