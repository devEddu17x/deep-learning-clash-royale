# Dataset limpiado automáticamente (sin verificación humana)

- Muestras: **23** (18 jugadas + 5 esperas)
- Proporción de esperas: 22% (objetivo 15–20 %)
- Cada registro tiene `human_verified: false`. Para uso en entrenamiento debe pasar por la revisión humana del notebook 3.2.

## Resumen por video

| video_id | estado | candidatos | jugadas_aceptadas | esperas | chat_muestras | muestras_destello_corregidas | muestras_escaneadas |
|---|---|---|---|---|---|---|---|
| 4Tt7nuuy-Bg | ok | 33 | 2 | 1 | 0 | 45 | 1790 |
| KcLv14GDAns | ok | 37 | 11 | 3 | 2 | 18 | 2320 |
| QnFw3kiwOqo | ok | 42 | 5 | 1 | 4 | 48 | 1750 |

## Motivos de descarte de candidatos de jugada

| motivo | candidatos |
|---|---|
| coste_inconsistente_con_caida_de_elixir | 33 |
| carta_slot_o_historia_insuficiente | 26 |
| localizacion_ambigua | 18 |
| zona_fuera_de_campo_propio | 10 |
| carta_ambiguo | 5 |
| frames_no_validos | 1 |
| carta_excluida_del_proyecto | 1 |

Aceptados automáticamente: 18 de 112

## Reglas de limpieza aplicadas

1. Sin oclusión por chat/emote en la ventana de la jugada ni en los 4 frames de entrada.
2. Carta identificada con confianza suficiente (estado `propuesta`) y presente en el catálogo permitido (sin evoluciones, héroes, campeones ni cartas de evento).
3. Coste de la carta coherente con la caída de elixir (±1), con el elixir ya corregido de destellos.
4. Posición localizada dentro del campo propio y sin ambigüedad entre dos zonas.
5. Seis segundos de historia disponibles; frame actual 0.5–0.8 s antes del despliegue (sin filtración).
6. Esperas: tramos de ≥3 s sin eventos ni caídas de elixir, separadas ≥6 s, sin chat.

## Limitaciones conocidas

- Las esperas no están auditadas: una jugada omitida por el detector podría haberse etiquetado como espera.
- La zona sale de una propuesta automática (cambio de imagen), que puede confundirse con movimiento de tropas.
- Jugadas con hechizos al campo rival, evoluciones o cartas excluidas se descartan: el dataset no las cubre.
- Detector y catálogo no se midieron contra una anotación manual completa.