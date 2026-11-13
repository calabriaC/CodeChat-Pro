# CodeChat Pro — Documentación técnica

Tema 6 · Canal binario simétrico y códigos de repetición
Integrantes: Alberto Aponte, Ethan Barreneche, Carlos Calabria, Angel Fontalvo

Este documento explica el fundamento matemático, el funcionamiento del núcleo línea por línea, cómo se miden los resultados y cómo se verificaron. Está pensado para que cada integrante pueda estudiar el sistema y defenderlo ante preguntas, incluidas las de cambiar un parámetro y predecir el resultado.

---

## 1. Arquitectura

```text
main.py                     Punto de entrada: crea la ventana (python main.py)
core/                       Núcleo matemático (no depende de la interfaz)
  matematicas.py            Conversión UTF-8 <-> bits, parámetros, H2(p), C, P_e
  codificador.py            Codificador de repetición (implementación propia)
  canal_bsc.py              Canal binario simétrico (implementación propia)
  decodificador.py          Decodificador por mayoría (implementación propia)
  metricas.py               BER, recuperación, intervalo de Wilson
  simulacion.py             Transmisión de extremo a extremo y experimentos
almacenamiento/gestor_json.py   Historial JSON con escritura atómica
interfaz/                   PySide6: inicio, transmisión, laboratorio, resultados, historial
tests/                      224 pruebas con pytest
ejemplos/reproducir_resultados.py   Regenera las tablas de resultados
```

Flujo de una transmisión:

```text
texto --UTF-8--> bits u (k bits) --codificador--> c (k·n bits) --BSC(p)--> y --mayoría--> û --UTF-8--> texto
            \--------------------------------- BSC(p) (escenario sin código) -----------------> texto
```

La interfaz solo llama a funciones de `core/`. Por eso todo el núcleo se puede probar sin abrir ventanas.

---

## 2. El código de repetición

Para un bit de información b, la palabra código es b repetido n veces:

| Parámetro | Valor | Ejemplo n = 5 |
|---|---|---|
| Longitud | n | 5 |
| Bits de información por bloque | k = 1 | 1 |
| Número de palabras código | M = 2ᵏ = 2 | {00000, 11111} |
| Distancia mínima | d = n | 5 |
| Tasa | R = k/n = 1/n | 0.2 |
| Redundancia | n − 1 bits por bit útil | 4 |
| Errores detectados (garantía) | d − 1 = n − 1 | 4 |
| Errores corregidos (garantía) | t = ⌊(d − 1)/2⌋ = ⌊(n − 1)/2⌋ | 2 |

**¿Por qué d = n?** Solo hay dos palabras, 0ⁿ y 1ⁿ, y difieren en las n posiciones.

**¿Por qué detecta n − 1 errores?** Con entre 1 y n − 1 bits invertidos, el bloque recibido mezcla ceros y unos. Por tanto no es una palabra código, y el receptor sabe que hubo error. Con n errores llega la *otra* palabra código y el error pasa inadvertido.

**¿Por qué corrige t = ⌊(n − 1)/2⌋?** Si hay a lo sumo t errores, la palabra enviada sigue teniendo mayoría en el bloque recibido. Es decir, es la palabra a menor distancia de Hamming, y la decisión por mayoría coincide con la decodificación por distancia mínima.

**Detección frente a corrección frente a mayoría.** El receptor no conoce el mensaje original. Lo único que observa es si el bloque es o no una palabra código (detección). La mayoría siempre produce una decisión, pero esa decisión solo está *garantizada* como correcta con ≤ t errores. Con más errores se equivoca sin saberlo. En la aplicación, «bloques con error detectado» es información del receptor, mientras que «bloques corregidos» y «errores residuales» son datos del simulador, que sí conoce el original.

**Longitudes pares.** Con n par puede haber empate: n/2 unos y n/2 ceros. Por eso t(n par) = t(n − 1). Por ejemplo, n = 4 corrige 1 error, igual que n = 3. Políticas de empate implementadas: marcar como ambiguo (predeterminada; el bit no se inventa), elegir 0, elegir 1 o elegir al azar.

### Ejemplo manual de codificación

Mensaje `101`, n = 3 → `111 000 111` (longitud 3 → 9). Prueba: `test_ejemplo_manual_101_con_n_3`.

### Ejemplo manual de decodificación

Se recibe `101 010 110`, con un error por bloque:

| Bloque | Ceros | Unos | Decisión | ¿Es palabra código? |
|---|---|---|---|---|
| 101 | 1 | 2 | 1 | no → error detectado |
| 010 | 2 | 1 | 0 | no → error detectado |
| 110 | 1 | 2 | 1 | no → error detectado |

Se recupera `101`: los tres errores se corrigieron porque cada bloque tenía 1 ≤ t = 1 error. Si el primer bloque hubiera llegado como `001` (2 errores > t), la mayoría decide 0. Es un **error residual**: se detecta que el bloque no es válido, pero se corrige mal. Pruebas: `test_ejemplo_manual_conteo_por_bloque` y `test_dos_errores_en_n3_engañan_al_decodificador`.

---

## 3. El canal binario simétrico

Cada bit se invierte de forma independiente con probabilidad p:

P(recibir 1 | enviar 0) = P(recibir 0 | enviar 1) = p, con 0 ≤ p ≤ 0.5.

**Implementación** ([core/canal_bsc.py](../core/canal_bsc.py)): para cada bit se toma un número uniforme u ∈ [0, 1). Si u < p, el bit se invierte (`1 - bit`). Como P(u < p) = p, la probabilidad de inversión es exactamente p. Con p = 0 nunca se cumple u < 0, así que el canal es perfecto. El generador de NumPy con semilla solo produce los uniformes. Con la misma semilla se repite exactamente el mismo experimento.

**p frente a proporción observada.** p es un parámetro teórico. La proporción de bits invertidos en una transmisión concreta es una variable aleatoria con media p y desviación típica √(p(1−p)/N). La aplicación siempre muestra ambas por separado.

---

## 4. Probabilidad de error residual

Sea J ~ Binomial(n, p) el número de bits invertidos en un bloque. La mayoría se equivoca cuando J > n/2.

**n impar:**

P_e(n, p) = Σ_{j=(n+1)/2}^{n} C(n, j) pʲ (1 − p)ⁿ⁻ʲ

**n par con desempate aleatorio** (el empate acierta la mitad de las veces):

P_e(n, p) = P(J > n/2) + ½ · P(J = n/2)

Con política «ambiguo», P(J > n/2) son errores confirmados y P(J = n/2) son bits ambiguos. Se cuentan por separado.

### Cálculo a mano con p = 0.1 (q = 0.9)

| n | Términos | P_e |
|---|---|---|
| 3 | C(3,2)p²q + p³ = 3(0.01)(0.9) + 0.001 = 0.027 + 0.001 | **0.028** |
| 5 | 10p³q² + 5p⁴q + p⁵ = 0.0081 + 0.00045 + 0.00001 | **0.00856** |
| 7 | 35p⁴q³ + 21p⁵q² + 7p⁶q + p⁷ = 0.0025515 + 0.0001701 + 0.0000063 + 0.0000001 | **0.002728** |

n = 4: P(J > 2) = 4p³q + p⁴ = 0.0037 y P(J = 2) = 6p²q² = 0.0486, así que P_e = 0.0037 + 0.0243 = 0.028 = P_e(3). En general P_e(2m) = P_e(2m − 1): el bit extra de un código par no reduce el error, solo crea la posibilidad de empate. Prueba: `test_codigo_par_equivale_al_impar_anterior`.

### Valores de referencia

| p | sin código (n = 1) | n = 3 | n = 5 | n = 7 |
|---|---|---|---|---|
| 0.01 | 0.01 | 2.98·10⁻⁴ | 9.85·10⁻⁶ | 3.42·10⁻⁷ |
| 0.05 | 0.05 | 7.25·10⁻³ | 1.16·10⁻³ | 1.94·10⁻⁴ |
| 0.1 | 0.1 | 0.028 | 8.56·10⁻³ | 2.73·10⁻³ |
| 0.2 | 0.2 | 0.104 | 0.0579 | 0.0333 |
| 0.3 | 0.3 | 0.216 | 0.163 | 0.126 |
| 0.5 | 0.5 | 0.5 | 0.5 | 0.5 |

### Error por bit frente a fallo del mensaje

Un mensaje de k bits se recupera íntegro solo si los k bits se deciden bien:

P(fallo del mensaje) = 1 − (1 − P_e)ᵏ (sin código: 1 − (1 − p)ᵏ)

Para 160 bits (20 caracteres) y p = 0.1: sin código 0.99999995; n = 3: 0.989; n = 5: 0.747; n = 7: 0.354. Aunque P_e por bit sea pequeña, los mensajes largos fallan a menudo.

---

## 5. Capacidad de Shannon

H₂(p) = −p log₂ p − (1 − p) log₂(1 − p), C = 1 − H₂(p) bits por uso del canal.

- p = 0: por convenio 0 · log₂ 0 = 0, así que H₂ = 0 y **C = 1**.
- p = 0.5: H₂ = 1, así que **C = 0**: la salida es independiente de la entrada.
- C decrece al crecer p en [0, 0.5]. Prueba: `test_capacidad_decrece_con_p`.

Ejemplo: H₂(0.1) = 0.1 · 3.3219 + 0.9 · 0.1520 = 0.3322 + 0.1368 = 0.4690, así que C(0.1) = 0.5310.

| p | 0 | 0.01 | 0.05 | 0.1 | 0.2 | 0.3 | 0.5 |
|---|---|---|---|---|---|---|---|
| C | 1 | 0.919 | 0.714 | 0.531 | 0.278 | 0.119 | 0 |

**R frente a C.** El teorema de codificación de canal dice que para toda tasa R < C existen códigos cuya probabilidad de error es tan pequeña como se quiera (con longitud de bloque suficientemente grande). Para R > C, eso es imposible. Cumplir R < C **no** garantiza que un código concreto tenga error pequeño. Por ejemplo, con p = 0.1 el código n = 3 tiene R = 0.333 < C = 0.531, pero P_e = 0.028.

### ¿Por qué la repetición no es un buen código según Shannon?

1. Su error solo tiende a 0 cuando n → ∞, y entonces R = 1/n → 0: la fiabilidad se compra renunciando a la tasa.
2. Ejemplo numérico: para P_e ≤ 10⁻⁶ con p = 0.01 hace falta n = 7 (R = 0.143, el 16 % de C = 0.919); con p = 0.05 hace falta n = 15 (R = 0.067). Con p = 0.1 ni n = 21 lo consigue (P_e(21) = 1.35·10⁻⁶, R = 0.048), aunque C = 0.531.
3. Cada bloque protege un solo bit (k = 1): la redundancia no se comparte entre bits. Familias como Hamming, BCH, Reed-Solomon, LDPC y los códigos polares codifican muchos bits a la vez y se acercan mucho más a la capacidad.

---

## 6. Núcleo línea por línea

### Codificador ([core/codificador.py](../core/codificador.py))

```python
n = validar_longitud(n)            # entero entre 1 y 21
mensaje = validar_bits(bits)       # cada elemento debe ser 0 o 1
palabra_codigo = []
for bit in mensaje.tolist():       # recorrer los bits de información
    for _ in range(n):             # repetir el bit n veces
        palabra_codigo.append(bit)
```

La salida tiene longitud k · n.

### Canal ([core/canal_bsc.py](../core/canal_bsc.py))

```python
uniformes = self.generador.random(len(enviados)).tolist()   # u ~ U[0,1) por bit
for bit, u in zip(enviados, uniformes):
    if u < p:                      # sucede con probabilidad p
        recibidos.append(1 - bit)  # inversión 0 <-> 1
        errores.append(True)
    else:
        recibidos.append(bit)
        errores.append(False)
```

### Decodificador ([core/decodificador.py](../core/decodificador.py))

```python
if len(secuencia) % n != 0: raise ValueError(...)   # la longitud debe ser divisible entre n
for inicio in range(0, len(secuencia), n):
    bloque = secuencia[inicio:inicio + n]
    ceros = unos = 0
    for bit in bloque:                 # 1-2. contar ceros y unos
        if bit == 1: unos += 1
        else: ceros += 1
    if unos > ceros: decision = 1      # 3-4. comparar y decidir
    elif ceros > unos: decision = 0
    else: ...                          # empate (n par): aplicar la política
    no_codigo = ceros != 0 and unos != 0   # error detectado por el receptor
```

### Cambios en vivo: predecir antes de ejecutar

| Cambio | Predicción | Dónde verlo |
|---|---|---|
| p = 0 | No hay errores; el mensaje llega igual con o sin código | Transmisión |
| p = 0.5 | El canal destruye la información: P_e = 0.5 para todo n, C = 0 | Resultados |
| n = 1 | No hay protección: errores residuales = errores del canal | Transmisión |
| n = 3 → n = 4 | Mismo P_e (desempate aleatorio); con política «ambiguo» aparecen bits «?» | Laboratorio BSC |
| n = 3 → 5 → 7 con p = 0.1 | P_e: 0.028 → 0.0086 → 0.0027; R: 0.333 → 0.2 → 0.143 | Laboratorio BSC |
| p = 0.1 → 0.2 con n = 5 | P_e: 0.0086 → 0.058; C: 0.531 → 0.278 | Resultados |
| 2 errores en un bloque de n = 3 | Error residual (2 > t = 1), aunque se detecta | Prueba `test_dos_errores_en_n3_engañan_al_decodificador` |

---

## 7. Métricas y diseño de los experimentos

- **BER del canal:** bits invertidos / bits transmitidos. Estima p.
- **BER residual:** bits útiles incorrectos / bits útiles, tras decodificar. Sin código coincide con la del canal; con código estima P_e.
- **Bits ambiguos:** empates no resueltos. No son error ni acierto y se reportan aparte.
- **Mensaje íntegro:** sin errores residuales ni ambigüedades.
- **Comparación justa** (`experimento_con_sin_codigo`): cada ensayo genera un mensaje aleatorio y lo envía por el *mismo* BSC(p) sin código y con código. Los dos escenarios usan la misma p y los mismos mensajes. Con código se transmiten k·n bits; sin código, k.
- **Intervalo de confianza:** Wilson al 95 % para la BER experimental. Si se observan 0 errores, solo se informa la cota superior.
- **Texto UTF-8:** si los bytes recuperados no forman UTF-8 válido, la recuperación se declara fallida: no hay texto recuperado y se muestran los bytes en hexadecimal. Nunca se reemplazan en silencio.

Una sola transmisión aleatoria no es concluyente. Las conclusiones se basan en el Laboratorio BSC (cientos de mensajes) y en las simulaciones con decenas de miles de bits por punto.

---

## 8. Verificación

**Pruebas automáticas** (`python -m pytest`): 224 pruebas, todas pasan en Python 3.14.8 sobre Windows 11. Cubren:
- Codificación para n = 1…21 y el caso manual `101`.
- Decodificación sin ruido, corrección de todos los patrones de hasta t errores, comportamiento con más de t errores, empates y las cuatro políticas.
- Detección de hasta n − 1 errores.
- Canal con p = 0 y p = 0.5, proporción observada cercana a p y reproducibilidad por semilla.
- UTF-8 de ida y vuelta, y UTF-8 inválido.
- d, R, t, H₂ y C, incluidos los casos límite.
- P_e calculada a mano para n = 3, 4, 5 y 7, y la identidad P_e(2m) = P_e(2m − 1).
- Monte Carlo frente a teoría (±5σ).
- Historial JSON: lectura, escritura atómica, archivo corrupto y duplicados.
- Transmisión de extremo a extremo con y sin código.

**Resultados reproducibles** (`python -m ejemplos.reproducir_resultados`, semilla 2026):

| n | BER sin código | BER con código | P_e teórica | Mensajes íntegros sin → con |
|---|---|---|---|---|
| 3 | 0.1018 | 0.02799 | 0.02800 | 0 → 9 de 500 |
| 5 | 0.1003 | 0.00886 | 0.00856 | 0 → 128 de 500 |
| 7 | 0.1004 | 0.00299 | 0.00273 | 0 → 306 de 500 |

(500 mensajes de 160 bits, p = 0.1.)

En la tabla de 18 puntos (n ∈ {1, 2, 3, 4, 5, 7}, p ∈ {0.01, 0.1, 0.2}, 100 000 bits por punto) del mismo script, 14 de los 18 valores teóricos caen dentro del IC 95 % de su estimación. Es menos que el ~95 % esperado, así que se comprobó la calibración del simulador con muchas réplicas independientes:

| Caso | Réplicas | Cobertura del IC 95 % |
|---|---|---|
| n = 1, p = 0.1, 10 000 bits | 600 | 570/600 = 95.0 % |
| n = 1, p = 0.01, 10 000 bits | 600 | 573/600 = 95.5 % |
| n = 3, p = 0.1, 5 000 bits | 400 | 381/400 = 95.3 % |
| n = 7, p = 0.1, 5 000 bits | 300 | 285/300 = 95.0 % |

La cobertura coincide con el 95 % nominal, por lo que el canal, el decodificador y el intervalo están bien calibrados. Además, con 40 semillas distintas (4 millones de bits por valor de p), la proporción media de errores del canal quedó a +1.13σ, +0.61σ y +0.20σ de p = 0.01, 0.1 y 0.2. El resultado 14/18 de esa semilla es, por tanto, una fluctuación aleatoria, que se informa tal cual en lugar de buscar otra semilla.

---

## 9. Historial JSON

Archivo `data/historial.json`, creado al guardar la primera transmisión. Cada registro (esquema v2) incluye:
- Datos del experimento: `id`, `fecha_hora`, `mensaje_original`, `longitud_codigo`, `probabilidad_error`, `semilla`, `politica_desempate`.
- Bits: `bits_originales`, `bits_codificados`, `bits_recibidos`, `bits_decodificados` (con `?` para los ambiguos) y `posiciones_alteradas`.
- Conteos: `errores_introducidos`, `bloques_detectados`, `errores_residuales`, `empates`, `ambiguedades`.
- Resultado: `mensaje_recuperado` (null si no es recuperable), `utf8_valido`, `resultado`.
- Valores teóricos: `tasa_codigo`, `distancia_minima`, `capacidad_correccion`, `capacidad_canal`, `probabilidad_error_bit_teorica`.
- `sin_codigo`: las métricas del escenario sin código.

La escritura es atómica: se escribe un temporal, se hace `fsync` y luego `os.replace`. Un archivo dañado se respalda como `historial.corrupto-*.json` y la aplicación continúa. No se admiten registros con `id` repetido.

---

## 10. Limitaciones

- El BSC supone errores independientes; no modela ráfagas.
- Solo se implementa el código de repetición. Los códigos más eficientes se mencionan como contraste teórico.
- Los algoritmos con bucles explícitos priorizan la claridad sobre la velocidad. Las simulaciones grandes tardan unos segundos y se ejecutan en segundo plano.
- La aplicación transmite texto. No se implementó transmisión de imágenes: la guía pide texto *o* imagen.
- Las simulaciones son pseudoaleatorias y reproducibles con semilla. Sus resultados son estimaciones con incertidumbre, no valores exactos.
