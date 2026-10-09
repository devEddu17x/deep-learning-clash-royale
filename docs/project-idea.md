## Qué queremos hacer

Hoy, quien quiere mejorar en Clash Royale mira horas de videos de youtubers e intenta imitar lo que ve, pero nadie le dice qué hacer en su propia partida, justo en el momento en que tiene que decidir. Queremos construir un modelo que mire la partida mientras se juega y diga en lenguaje natural qué carta jugar y dónde colocarla, como lo haría un jugador experto en esa misma situación. El modelo no necesita un dataset con estadísticas de cartas o reglas de juego, la idea es que aprenda a partir de las decisiones tomadas por jugadores expertos en las partidas observadas.

## Entrada

Una partida de Clash Royale dura 3 minutos. El modelo recibe 4 imágenes de la partida: hace 6s, hace 4s, hace 2s y actual. Cada imagen contiene visualmente:
Tropas (posición, salud, estado: atacando / recibiendo daño / ambos )
Torres de ambos jugadores (salud)
Las 4 cartas que el jugador tiene en mano.
El elixir disponible. (0-10)
Consideramos estos segundos para definir la trayectoria de las tropas y cartas ya usadas por el rival para definir la mejor respuesta como lo haría un humano real.
Salida
Texto en lenguaje natural que indica qué carta jugar y en qué zona de la arena. Por ejemplo: "Juega Valquiria detrás del puente izquierdo".

## Nuestro dataset

Lo construiremos con videos de YouTube que muestran la partida. Estimamos 240 partidas (12 horas de juego). Con 1 frame por segundo (43K imágenes), considerando 45 jugadas por jugador nos da un total de aprox de 10K jugadas. Por ahora, pensamos detectar la carta jugada y su posición mediante visión por computadora en los videos, convirtiendo la acción a texto con plantillas. Pero aún nos encontramos explorando otras formas de recolección.

## Qué somos y qué no somos

No buscamos clasificar.
No predecimos si una partida se gana o se pierde.
No usamos CSVs de resultados de partidas, como CSV de Kaggle con millones de batallas entre jugadores top (solo trae mazos y resultados en tabla, sin imágenes).
Queremos ver la partida, igual que un jugador mirando la pantalla, y escribir en lenguaje natural qué jugada realizar.
Ejemplo de video para el dataset: https://youtu.be/LRX8zTKrrt4?t=376
