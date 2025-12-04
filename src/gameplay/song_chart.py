"""
Song charts para el juego de ritmo - Formato escalable con clase Song
Cada canción es un objeto Song con metadatos
Chart format: lista de tuplas (key, time)
  - key: número de tecla (0-23 para 24 teclas)
  - time: tiempo en segundos cuando debe tocarse
"""

from src.gameplay.rythm_game import Song

# Modo Aprender - Muy lento y simple
MODO_APRENDER = Song(
    title="Aprender",
    chart=[
        (0, 3.0), (2, 5.5), (4, 8.0), (7, 10.5),
        (7, 13.0), (4, 15.5), (2, 18.0), (0, 20.5),
    ],
    difficulty="Muy Fácil",
    bpm=60
)

# Tutorial Fácil - Escala simple
TUTORIAL_FACIL = Song(
    title="Tutorial Fácil",
    chart=[
        # Escala ascendente - teclas blancas
        (0, 2.0), (2, 3.5), (4, 5.0), (5, 6.5),
        (7, 8.0), (9, 9.5), (11, 11.0), (12, 12.5),
        # Escala descendente
        (12, 14.0), (11, 15.5), (9, 17.0), (7, 18.5),
        (5, 20.0), (4, 21.5), (2, 23.0), (0, 24.5),
    ],
    difficulty="Fácil",
    bpm=80
)

# Twinkle Twinkle Little Star
TWINKLE_TWINKLE = Song(
    title="Twinkle Twinkle",
    chart=[
        # Twinkle twinkle little star - Do Do Sol Sol La La Sol
        (0, 1.0), (0, 1.5), (7, 2.0), (7, 2.5),
        (9, 3.0), (9, 3.5), (7, 4.0),
        # Fa Fa Mi Mi Re Re Do
        (5, 5.0), (5, 5.5), (4, 6.0), (4, 6.5),
        (2, 7.0), (2, 7.5), (0, 8.0),
        # Sol Sol Fa Fa Mi Mi Re
        (7, 9.0), (7, 9.5), (5, 10.0), (5, 10.5),
        (4, 11.0), (4, 11.5), (2, 12.0),
        # Sol Sol Fa Fa Mi Mi Re
        (7, 13.0), (7, 13.5), (5, 14.0), (5, 14.5),
        (4, 15.0), (4, 15.5), (2, 16.0),
        # Do Do Sol Sol La La Sol
        (0, 17.0), (0, 17.5), (7, 18.0), (7, 18.5),
        (9, 19.0), (9, 19.5), (7, 20.0),
    ],
    difficulty="Normal",
    bpm=120
)

# Happy Birthday
HAPPY_BIRTHDAY = Song(
    title="Happy Birthday",
    chart=[
        # Happy Birthday - La La Si Do La Do (La)
        (9, 1.0), (9, 1.5), (11, 2.0), (12, 2.5),
        (9, 3.0), (14, 3.5), (12, 4.5),
        # Happy Birthday - La La Si Do La Re (Do)
        (9, 5.5), (9, 6.0), (11, 6.5), (12, 7.0),
        (9, 7.5), (16, 8.0), (14, 9.0),
        # Happy Birthday - La La Do Si La Sol (Fa)
        (9, 10.0), (9, 10.5), (12, 11.0), (11, 11.5),
        (9, 12.0), (7, 12.5), (5, 13.5),
    ],
    difficulty="Fácil",
    bpm=110
)

# Canción Avanzada - Patrón rápido
DESAFIO_AVANZADO = Song(
    title="Desafío Avanzado",
    chart=[
        # Patrón rápido ascendente
        (0, 1.0), (2, 1.3), (4, 1.6), (5, 1.9),
        (7, 2.2), (9, 2.5), (11, 2.8), (12, 3.1),
        # Descendente rápido
        (12, 3.5), (11, 3.8), (9, 4.1), (7, 4.4),
        (5, 4.7), (4, 5.0), (2, 5.3), (0, 5.6),
        # Patrón final con arpegios
        (0, 6.0), (4, 6.3), (7, 6.6), (12, 6.9),
        (7, 7.2), (4, 7.5), (0, 8.0),
    ],
    difficulty="Difícil",
    bpm=160
)

# Lista de todas las canciones disponibles
ALL_SONGS = [
    MODO_APRENDER,
    TUTORIAL_FACIL,
    HAPPY_BIRTHDAY,
    TWINKLE_TWINKLE,
    DESAFIO_AVANZADO
]