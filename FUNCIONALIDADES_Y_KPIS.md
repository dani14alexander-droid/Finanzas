# Finanzas: funciones y cálculos

Esta aplicación registra ingresos, gastos, ahorros y deudas en pesos chilenos. Organiza los movimientos por ciclos de sueldo y muestra un panel del ciclo actual, un resumen por ciclo y un histórico. Las cifras son cálculos a partir de los registros de la aplicación; no son una conciliación con una cuenta bancaria.

## Secciones de la aplicación

| Sección | Qué permite hacer |
| --- | --- |
| Panel | Consultar los indicadores del ciclo actual, recomendaciones, gasto variable diario o semanal y movimientos recientes. |
| Resumen | Elegir un ciclo, revisar y editar movimientos, comparar categorías con el ciclo anterior, ver la distribución de gastos y recursos, y exportar los movimientos a Excel. |
| Planificación | Añadir ingresos, gastos y ahorros previstos; combinar lo registrado con compromisos pendientes y cuotas; fijar metas porcentuales por macrocategoría. Los importes planificados no modifican los movimientos reales. |
| Macrocategorías | Administrar categorías y asignar categorías de gasto o ahorro a las macrocategorías de planificación. |
| Gastos fijos | Crear y administrar registros recurrentes, confirmarlos o anularlos por periodo, separarlos en partes y consultar su historial. |
| Histórico | Filtrar por fecha y tipo; ver ingresos, gastos, ahorros, dinero disponible y deudas en vistas diaria, semanal o mensual. Los registros futuros se excluyen del histórico. |
| Deudas | Registrar lo que te deben y lo que debes, compras en cuotas, préstamos recibidos, compras compartidas, abonos parciales e historial de pagos. El gráfico por persona permite ver saldos pendientes o montos originales. |

En móvil, los gráficos del Panel, Resumen, Histórico y Deudas tienen un control para abrir una vista horizontal ampliada. Los formularios de movimientos y deudas rechazan fechas posteriores a la fecha actual de Chile.

## Periodos y conceptos básicos

- **Ciclo:** si hay un ingreso identificado como sueldo, comienza en la fecha del último sueldo aplicable y termina el día anterior al penúltimo día hábil del mes siguiente. Los ciclos antiguos sin fecha de sueldo usan meses calendario. La fecha del penúltimo día hábil también se usa para el sueldo automático.
- **Saldo anterior:** el disponible recalculado del ciclo previo se incorpora al ciclo actual si el ciclo previo tiene movimientos. Un saldo positivo entra como ingreso «Saldo anterior» y uno negativo como gasto. Los arrastres guardados por versiones anteriores se descartan para evitar duplicaciones.
- **Monto efectivo de un gasto:** normalmente es el monto registrado menos los abonos de compras compartidas asociados a ese gasto, con mínimo cero. En la categoría **Efectivo** se usa la suma de sus subgastos, limitada al monto registrado.
- **Ahorro flexible:** cada registro ordinario de esta categoría aporta `monto registrado − retiros detallados`, con mínimo cero, al ahorro neto. Los retiros detallados se suman a los gastos del ciclo. Los ahorros de otras categorías aportan su monto completo. Un préstamo marcado como financiado desde ahorro es un caso especial: resta su principal del ahorro acumulado y sus cobros lo restituyen.
- **Flujo de cuentas por cobrar:** `restituciones cobradas + cobros de préstamos financiados desde ahorro − préstamos otorgados registrados como cuenta por cobrar`. Este flujo afecta el disponible, pero no se clasifica como ingreso o gasto ordinario.

## Indicadores del Panel y Resumen

| Indicador | Cálculo |
| --- | --- |
| Ingresos | Suma de movimientos de tipo **Ingreso** del ciclo; incluye un saldo anterior positivo cuando corresponde. |
| Gastos | Suma de gastos efectivos. En Panel, el gasto de categoría **Deuda** se muestra aparte como compromiso; los retiros detallados de Ahorro flexible se suman a gastos. |
| Ahorro del ciclo | Suma de aportes netos de movimientos **Ahorro** del ciclo. |
| Disponible | `ingresos − gastos − compromisos de deuda − ahorro del ciclo + flujo de cuentas por cobrar` en Panel. En Resumen, los compromisos de deuda ya están dentro de gastos, por lo que se usa `ingresos − gastos − ahorro del ciclo + flujo`. |
| Gastos y compromisos | `gastos + compromisos de deuda` en Panel. |
| Referencia o cuota semanal | `disponible ÷ semanas restantes`. Las semanas son el techo de los días desde hoy hasta el fin del ciclo, ambos inclusive, dividido por 7; el mínimo es una semana. |
| Cuentas por cobrar | Suma, para cada deuda pendiente de tipo **Me deben**, de `máximo(monto original − monto cobrado, 0)`. Es un saldo actual, no el total prestado históricamente. |
| Ahorros acumulados | Suma histórica de aportes netos por categoría de ahorro según los movimientos guardados. |

El Panel toma el ciclo actual y calcula sus indicadores con los movimientos de ese ciclo. Resumen permite escoger un ciclo anterior y aplica las mismas reglas de monto efectivo y ahorro neto. La comparación de categorías muestra la diferencia en pesos entre el ciclo elegido y el anterior. Los porcentajes de los gráficos circulares se calculan dividiendo cada segmento por la suma de los segmentos mostrados.

## Gasto variable y meta

El gráfico de gasto variable excluye gastos que coinciden con automatizaciones de gasto fijo. En gastos de **Efectivo** usa la fecha y categoría de cada subgasto. Solo muestra días hasta el menor entre hoy y el fin del ciclo.

| Indicador | Cálculo |
| --- | --- |
| Ingresos para la meta | Ingresos registrados del ciclo, sin «Saldo anterior». |
| Compromiso mensual | Suma de automatizaciones que cuentan en el periodo. |
| Meta diaria | `(ingresos para la meta − compromiso mensual + flujo de cuentas por cobrar) ÷ días del ciclo`. |
| Meta semanal | El mismo numerador dividido por `techo(días del ciclo ÷ 7)`. |
| Gasto promedio diario | Gasto variable registrado hasta la fecha visible dividido por los días transcurridos del ciclo, contando los días sin gasto. |
| Sobre la meta / Upperstock | Suma diaria de `máximo(gasto del día − meta diaria, 0)`. |
| Margen no utilizado / Understock | Suma diaria de `máximo(meta diaria − gasto del día, 0)`. |

Los contadores «días sobre la meta» y «días bajo la meta» comparan cada día visible con la meta diaria. La vista semanal agrupa los gastos en bloques de siete días; la evaluación de Upperstock y Understock sigue siendo diaria.

## Indicadores de gastos fijos

La sección de gastos fijos considera las automatizaciones que cuentan en el periodo actual. **Gastos fijos** suma las de tipo Gasto; **Gastos fijos sin Aporte** excluye las anuladas y aquellas cuya categoría o descripción contiene «aporte al hogar»; **Ahorros planificados** suma las de tipo Ahorro. **Compromiso mensual** es `gastos fijos + ahorros planificados`. **Sueldo menos compromisos** usa el monto del último sueldo registrado menos ese compromiso mensual.

## Deudas y préstamos

Una deuda pendiente conserva `saldo = máximo(monto original − abonos registrados, 0)`. En **Deudas**, «Me deben» suma los saldos a favor, «Debo» suma los saldos por pagar y el balance neto es `Me deben − Debo`. El gráfico en modo **Pendientes** usa esos saldos; en modo **Histórico** usa los montos originales de las deudas filtradas.

Un préstamo otorgado crea una cuenta por cobrar. Cada cobro parcial disminuye el saldo pendiente. Una compra compartida puede asociarse a un gasto: sus abonos reducen el monto efectivo de ese gasto. Una deuda en cuotas distribuye el monto original entre el número de cuotas; los abonos actualizan el saldo y las cuotas pagadas. Un préstamo recibido se registra como ingreso de origen y sus pagos como gastos.

Si el préstamo otorgado se financia desde **Ahorro flexible**, su principal se resta del ahorro acumulado; cada abono lo repone. El movimiento de la cuenta por cobrar y el movimiento de ahorro se compensan en el disponible: prestar desde un ahorro ya separado y recuperarlo en ese mismo ahorro no aumenta ni reduce el dinero disponible para gastar.

## Planificación y metas

Planificación parte de los importes registrados del ciclo y añade ingresos, gastos y ahorros planificados. Suma los gastos fijos y ahorros recurrentes pendientes; las cuotas pendientes de deudas **Debo** en modalidad **Cuotas** se añaden a los gastos previstos. Su disponible proyectado es:

`ingresos registrados + ingresos planificados − gastos registrados − gastos fijos pendientes − cuotas pendientes − gastos planificados − ahorros registrados − ahorros fijos pendientes − ahorros planificados + flujo de cuentas por cobrar`.

Para una meta porcentual, `objetivo = ingresos proyectados × porcentaje ÷ 100`. El avance mostrado es `mínimo(actual ÷ objetivo × 100, 100)` si el objetivo es positivo. «Libre» usa `máximo(disponible proyectado, 0)`; las demás macrocategorías toman los movimientos asignados y, para «Gastos fijos», los compromisos calculados del ciclo.

## Histórico

Los gráficos agrupan movimientos y deudas por día, semana o mes. Cada periodo suma sus ingresos, gastos efectivos y ahorros netos; el balance del periodo es `ingresos − gastos − ahorros + flujo de cuentas por cobrar`. La curva de disponible acumula esas variaciones dentro de cada ciclo y se reinicia al comienzo del siguiente. Las barras de deudas por periodo usan el monto original de las deudas registradas en cada periodo.

## Fuente de los cálculos

Las fórmulas anteriores describen la implementación de `app.py`, principalmente `calcular_dashboard`, `resumen`, `datos_gastos_variables`, `calcular_planificacion`, `resumen_historico`, `monto_efectivo_movimiento`, `monto_ahorro_neto`, `flujo_cuentas_por_cobrar` y `saldo_cuentas_por_cobrar`. Los datos se guardan en PostgreSQL cuando está configurado; la aplicación también admite archivos CSV.
