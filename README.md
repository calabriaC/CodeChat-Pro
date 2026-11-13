# CodeChat Pro — Tema 6: Canal binario simétrico

**Universidad del Norte · Teoría de Códigos (MAT 4215) · Proyecto final 202630**

**Integrantes:** Alberto Aponte · Ethan Barreneche · Carlos Calabria · Angel Fontalvo

**Aplicativo de escritorio** (Python + PySide6) para transmitir mensajes de texto por un **canal binario simétrico BSC(p)** con un **código de repetición de longitud n**. Permite medir el error con y sin código, y comparar lo que logra la repetición con la **capacidad de Shannon** C = 1 − H₂(p).

| Requisito de la guía | Implementación (núcleo propio, sin librerías de codificación) |
|---|---|
| Codificador | [core/codificador.py](core/codificador.py): repite cada bit n veces (`101`, n=3 → `111000111`) |
| Canal | [core/canal_bsc.py](core/canal_bsc.py): invierte cada bit con probabilidad p (semilla configurable) |
| Decodificador | [core/decodificador.py](core/decodificador.py): mayoría por bloque, detección de bloques inválidos, políticas de empate |
| Métrica | [core/metricas.py](core/metricas.py), [core/simulacion.py](core/simulacion.py): BER antes/después, mensajes íntegros, con y sin código |

## Instalación y ejecución (Windows, PowerShell)

Requisitos: Python 3.12 o superior (probado con Python 3.14.8 en Windows 11) y Git.

```powershell
git clone https://github.com/calabriaC/CodeChat-Pro.git
cd CodeChat-Pro
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # si PowerShell lo bloquea: Set-ExecutionPolicy -Scope Process Bypass
pip install -r requirements.txt       # PySide6, NumPy, Matplotlib, Pytest (PyInstaller opcional)
python main.py                        # abre la aplicación (sin navegador ni internet)
python -m pytest                      # 224 pruebas automáticas
python -m ejemplos.reproducir_resultados   # regenera las tablas de resultados
```

Secciones: **Inicio** · **Transmisión** (mensaje en vivo, receptor con y sin código) · **Laboratorio BSC** (experimentos repetidos, presets n = 3, 5, 7) · **Resultados** (gráfica error frente a tasa, capacidad, fundamento matemático) · **Historial** (JSON en `data/historial.json`, se crea solo).

## Resultados principales (verificados)

Código de repetición: (n, M, d) = (n, 2, n), k = 1, R = 1/n, corrige t = ⌊(n−1)/2⌋ y detecta n − 1 errores por bloque. Valores teóricos exactos con p = 0.1 y **experimento** de 500 mensajes aleatorios de 160 bits enviados **sin y con código por el mismo canal** (semilla 2026):

| n | t | R | P_e teórica | BER sin código (medida) | BER con código (medida) | Mensajes íntegros sin → con código |
|---|---|---|---|---|---|---|
| 3 | 1 | 0.333 | 0.0280 | 0.1018 | 0.0280 | 0 → 9 de 500 |
| 5 | 2 | 0.200 | 0.00856 | 0.1003 | 0.00886 | 0 → 128 de 500 |
| 7 | 3 | 0.143 | 0.00273 | 0.1004 | 0.00299 | 0 → 306 de 500 |

Capacidad: C(0) = 1, C(0.01) = 0.919, C(0.05) = 0.714, C(0.1) = 0.531, C(0.2) = 0.278, C(0.3) = 0.119, C(0.5) = 0.

**Conclusión.** Al crecer n el error residual cae (0.1 → 0.028 → 0.0086 → 0.0027), pero la tasa también cae (1 → 1/3 → 1/5 → 1/7). Con p = 0.1 ni siquiera n = 21 (R ≈ 0.048) alcanza P_e ≤ 10⁻⁶, aunque C = 0.531. Shannon garantiza códigos con error tan pequeño como se quiera para cualquier R < C; la repetición solo lo consigue haciendo R → 0. Por eso no es un código eficiente. La validación estadística está en [docs/documentacion_tecnica.md](docs/documentacion_tecnica.md#8-verificación): la cobertura medida del IC 95 % es del 95 %.

## Herramientas utilizadas y declaración de uso de IA

- **Bibliotecas:** PySide6 (interfaz), Matplotlib (gráficas), NumPy (solo generador aleatorio con semilla y contenedores; los algoritmos del núcleo son bucles explícitos), Pytest (pruebas), JSON (historial).
- **Claude Code (Anthropic, modelo Claude Opus 5.5):** asistente de programación. Se usó para generar la estructura del proyecto, el código del núcleo y de la interfaz, las pruebas automáticas, esta documentación y la verificación numérica de las fórmulas, a partir de las especificaciones y la guía del equipo.
- **[Completar por el equipo]:** otras herramientas de IA usadas (por ejemplo, para redactar las especificaciones) y su propósito.
- **[Completar por el equipo]:** qué revisó, comprendió y validó cada integrante (por ejemplo, el cálculo a mano de P_e para n = 3, 5, 7 y la ejecución de las pruebas).

## Fuentes

1. I. Y. Gómez G., *Proyecto final — Aplicaciones de la Teoría de Códigos*, Universidad del Norte, 2026 (guía del curso).
2. C. E. Shannon, “A Mathematical Theory of Communication,” *Bell System Technical Journal*, 27, 379–423 y 623–656, 1948.
3. T. M. Cover y J. A. Thomas, *Elements of Information Theory*, 2.ª ed., Wiley, 2006 (cap. 7: capacidad del canal).
4. D. J. C. MacKay, *Information Theory, Inference, and Learning Algorithms*, Cambridge University Press, 2003 (cap. 1: códigos de repetición en el BSC).
5. R. Hill, *A First Course in Coding Theory*, Oxford University Press, 1986.
6. E. B. Wilson, “Probable inference, the law of succession, and statistical inference,” *JASA*, 22, 209–212, 1927 (intervalo de confianza).
7. Documentación oficial de Qt for Python (PySide6), NumPy, Matplotlib y pytest.

Documentación técnica completa con ejemplos numéricos: [docs/documentacion_tecnica.md](docs/documentacion_tecnica.md).
