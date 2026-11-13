"""Reproduce la tabla de resultados experimentales del README.

Ejecutar desde la raíz del proyecto:

    python -m ejemplos.reproducir_resultados
"""

from core import matematicas as mat
from core.decodificador import PoliticaDesempate
from core.simulacion import crear_generador, experimento_con_sin_codigo, simular_ber, transmitir_mensaje

SEMILLA = 2026
BITS = 100_000


def tabla_ber() -> None:
    print(f"\nBER residual: teoría vs. simulación ({BITS:,} bits por punto, semilla {SEMILLA}, desempate aleatorio)")
    print(f"{'n':>3} {'p':>5} {'R':>7} {'BER canal':>10} {'P_e teórica':>12} {'BER simulada':>13} {'IC 95 %':>23} {'¿en IC?':>8}")
    # Un solo generador para toda la tabla: cada punto usa números aleatorios distintos
    # (reutilizar la misma semilla en cada punto los haría estadísticamente dependientes).
    _, rng = crear_generador(SEMILLA)
    dentro = total = 0
    for n in (1, 2, 3, 4, 5, 7):
        for p in (0.01, 0.1, 0.2):
            r = simular_ber(n, p, BITS, politica=PoliticaDesempate.ALEATORIO, generador=rng)
            teo = mat.probabilidad_error_bit(n, p)
            bajo, alto = r.intervalo_95
            print(f"{n:>3} {p:>5} {mat.tasa_codigo(n):>7.4f} {r.ber_canal:>10.5f} {teo:>12.3e} "
                  f"{r.ber_residual:>13.3e} [{bajo:.2e}, {alto:.2e}] {'sí' if bajo <= teo <= alto else 'no':>8}")
            total += 1
            dentro += bajo <= teo <= alto
    print(f"Valores teóricos dentro del IC 95 %: {dentro} de {total} (se espera ~95 %)")


def ejemplo_mensaje() -> None:
    print("\nTransmisión del mensaje 'Hola, Teoría de Códigos' con semilla 7")
    for n, p in ((1, 0.1), (3, 0.1), (5, 0.1), (4, 0.2)):
        r = transmitir_mensaje("Hola, Teoría de Códigos", n, p, semilla=7)
        print(f"n={n} p={p}: errores canal={r.errores_introducidos}, residuales={r.errores_residuales}, "
              f"ambiguos={r.ambiguedades}, resultado={r.estado.value}, recuperado={r.mensaje_recuperado!r}")


def comparacion_con_sin_codigo() -> None:
    print("\nCon y sin código: 500 mensajes aleatorios de 160 bits, p = 0.1, semilla 2026, desempate aleatorio")
    print(f"{'n':>3} {'R':>6} {'BER sin código':>15} {'BER con código':>15} {'P_e teórica':>12} {'íntegros sin':>13} {'íntegros con':>13}")
    for n in (3, 5, 7):
        e = experimento_con_sin_codigo(n, 0.1, 160, 500, semilla=SEMILLA)
        print(f"{n:>3} {1 / n:>6.3f} {e.sin_codigo.ber_residual:>15.4f} {e.con_codigo.ber_residual:>15.5f} "
              f"{e.ber_teorica_con_codigo:>12.5f} {e.mensajes_ok_sin_codigo:>9}/500 {e.mensajes_ok_con_codigo:>9}/500")


def capacidad() -> None:
    print("Capacidad del BSC")
    for p in (0.0, 0.01, 0.05, 0.1, 0.2, 0.3, 0.5):
        print(f"p = {p:<5} H2 = {mat.entropia_binaria(p):.4f}  C = {mat.capacidad_bsc(p):.4f}")


if __name__ == "__main__":
    capacidad()
    comparacion_con_sin_codigo()
    tabla_ber()
    ejemplo_mensaje()
