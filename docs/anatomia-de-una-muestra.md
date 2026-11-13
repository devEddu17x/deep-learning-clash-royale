# Anatomía del Dataset: Entradas, Salidas y Muestras Reales

Este documento detalla con precisión qué contiene el dataset consolidado de Clash Royale, qué datos componen una muestra individual, qué recibe el modelo como entrada y qué genera exactamente como salida.

---

## 1. Visión General del Dataset Completo

El dataset representa un conjunto supervisado y multimodal construido a partir de 49 videos de partidas competitivas reales, almacenado en Cloudflare R2 bajo el prefijo `dataset/`:

| Componente             | Volumen exacto                         | Ubicación en Cloudflare R2                       |
| ---------------------- | -------------------------------------- | ------------------------------------------------ |
| Manifiesto consolidado | 3190 decisiones tácticas estructuradas | `s3://cr-videos/dataset/train.jsonl`             |
| Banco de imágenes      | 12760 fotogramas JPEG (4 por muestra)  | `s3://cr-videos/dataset/images/*.jpg`            |
| Shards individuales    | 41 archivos particionados por video    | `s3://cr-videos/dataset/shards/<video_id>.jsonl` |
| Catálogo oficial       | 160 cartas estándar + metadatos        | `s3://cr-videos/metadata/cards_catalog.json`     |

Del total de 3190 decisiones:

- **2662 muestras (83.45 %)** corresponden a jugadas activas de cartas en la arena.
- **528 muestras (16.55 %)** corresponden a decisiones pasivas de esperar para acumular elixir.

---

## 2. ¿Qué es exactamente una Entrada (Input X)?

Una entrada representa el **estado visual del juego** en el instante en que el jugador debe decidir qué hacer.

### A. Para el modelo baseline de esta entrega (Keras / MobileNetV3)

- **Entrada única:** El fotograma de decisión actual (`_t-0s.jpg`), tomado exactamente 0.8 segundos antes de que la carta toque la arena (para evitar fuga de información).
- **Forma del tensor:** `[Batch, 384, 216, 3]` en punto flotante normalizado entre `0.0` y `1.0`.
- **Qué información visual contiene la imagen:**
  - El estado del combate en la arena (tropas enemigas cruzando los puentes, vida de las torres).
  - La barra morada de elixir en la parte inferior (cuánto recurso tiene disponible).
  - Las 4 cartas en la mano del jugador entre las cuales puede elegir.

### B. Para el modelo VLM multimodal final (Unidad II)

- **Entrada temporal:** Los 4 fotogramas secuenciales a resolución nativa 540×960 píxeles:
  - `t-6s.jpg`: Qué ocurría hace 6 segundos.
  - `t-4s.jpg`: Qué ocurría hace 4 segundos.
  - `t-2s.jpg`: Qué ocurría hace 2 segundos.
  - `t-0s.jpg`: Situación actual en la decisión.
- Esta secuencia temporal permite al modelo deducir velocidad de tropas enemigas, trayectoria de proyectiles y tasa de recarga de elixir.

---

## 3. ¿Qué es exactamente una Salida (Output Y)?

La salida esperada del sistema es una **recomendación táctica formulada directamente en lenguaje natural humano**.

### El texto generado (Target Text):

- Si la situación amerita jugar una carta:
  `"Juega Ariete de batalla detrás del puente izquierdo."`
  `"Juega Cañón en el centro del campo propio."`
  `"Juega Bola de fuego sobre la torre derecha rival."`
- Si la situación amerita esperar:
  `"esperar"`

### Cómo lo emite el modelo baseline de Keras:

Internamente, el modelo baseline es multitarea y predice dos variables numéricas mediante sus cabezas lineales:

1. `prediccion_carta`: Probabilidad sobre 161 clases (160 cartas estándar + clase 160 para esperar).
2. `prediccion_zona`: Probabilidad sobre 10 zonas de la arena (zonas 1 a 9 + zona 0 para neutral/esperar).

Una función de post-procesamiento (`recomendar_jugada`) toma los dos índices de mayor probabilidad y ensambla la frase final:
`f"Juega {nombre_carta} {frase_zona}."` o `"esperar"`.

---

## 4. Ejemplos Reales Extraídos del Archivo `dataset/train.jsonl`

A continuación se muestran dos registros JSON reales extraídos directamente del dataset maestro:

### Ejemplo A: Muestra de Jugada Activa de Carta (`play`)

```json
{
  "sample_id": "IZrTA60YB7I_m1_play_001",
  "video_id": "IZrTA60YB7I",
  "match_index": 1,
  "action_type": "play",
  "timestamp_sec": 8.6,
  "t_decision_sec": 7.8,
  "frames": [
    "images/IZrTA60YB7I_m1_play_001_t-6s.jpg",
    "images/IZrTA60YB7I_m1_play_001_t-4s.jpg",
    "images/IZrTA60YB7I_m1_play_001_t-2s.jpg",
    "images/IZrTA60YB7I_m1_play_001_t-0s.jpg"
  ],
  "card_name_es": "El Tronco",
  "card_key": "the-log",
  "hand_slot": 3,
  "placement_coord": [0.7497, 0.97],
  "placement_zone": "detrás de la torre del rey",
  "zone_id": 6,
  "target_text": "Juega El Tronco detrás de la torre del rey.",
  "metadata": {
    "spawn_method": "label",
    "spawn_conf": 0.673,
    "label_visible_at_decision": false
  }
}
```

### Ejemplo B: Muestra de Acción Pasiva de Espera (`wait`)

```json
{
  "sample_id": "IZrTA60YB7I_m1_wait_001",
  "video_id": "IZrTA60YB7I",
  "match_index": 1,
  "action_type": "wait",
  "timestamp_sec": 19.8,
  "t_decision_sec": 19.8,
  "frames": [
    "images/IZrTA60YB7I_m1_wait_001_t-6s.jpg",
    "images/IZrTA60YB7I_m1_wait_001_t-4s.jpg",
    "images/IZrTA60YB7I_m1_wait_001_t-2s.jpg",
    "images/IZrTA60YB7I_m1_wait_001_t-0s.jpg"
  ],
  "card_name_es": null,
  "card_key": null,
  "hand_slot": null,
  "placement_coord": null,
  "placement_zone": null,
  "zone_id": null,
  "target_text": "esperar",
  "metadata": {
    "gap_duration_sec": 10.0
  }
}
```

---

## 5. Resumen de Flujo de Datos

```text
[Fotograma de Decisión: t-0s.jpg (384×216×3)]
                      │
                      ▼
        [Modelo de Visión Keras (MobileNetV3)]
                      │
           ┌──────────┴──────────┐
           ▼                     ▼
[Predicción de Carta]   [Predicción de Zona]
  ("El Tronco")     ("detrás de la torre del rey")
           └──────────┬──────────┘
                      ▼
         [Función recomendar_jugada()]
                      │
                      ▼
[Salida de Texto: "Juega El Tronco detrás de la torre del rey."]
```
