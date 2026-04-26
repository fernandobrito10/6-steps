# 🎬 Connect The Stars — Roadmap para Claude Code

## Objetivo
Dado dois atores, encontrar o **menor caminho possível** entre eles usando a API do TMDB.
Exemplo: `Tom Hanks → [filme] → Ator X → [filme] → Lupita Nyong'o`

---

## Stack recomendada
- **Linguagem:** Python 3.10+
- **API:** TMDB (The Movie Database) — https://www.themoviedb.org/settings/api
- **Algoritmo:** BFS bidirecional (busca em largura dos dois lados simultaneamente)
- **Cache:** SQLite local (para evitar re-fetch e respeitar rate limit)
- **Libs:** `httpx` (async HTTP), `asyncio`, `sqlite3`, `collections.deque`

---

## Estrutura de Arquivos

```
connect_the_stars/
├── main.py              # Entry point: recebe os dois atores e imprime o caminho
├── bfs.py               # Algoritmo BFS bidirecional
├── tmdb.py              # Wrapper da API TMDB (busca atores, filmes, elenco)
├── cache.py             # Cache SQLite para atores e filmes já buscados
├── models.py            # Dataclasses: Actor, Movie, Connection
└── config.py            # TMDB_API_KEY e constantes (max_depth, delays, etc.)
```

---

## Fase 1 — Setup e Wrapper TMDB (`tmdb.py`)

### Endpoints necessários:
| Função | Endpoint TMDB |
|---|---|
| Buscar ator por nome | `GET /search/person?query={nome}` |
| Buscar filmografia do ator | `GET /person/{id}/movie_credits` |
| Buscar elenco de um filme | `GET /movie/{id}/credits` |

### Regras importantes:
- Usar **`httpx.AsyncClient`** com semaphore para controlar concorrência (máx 40 req/s no TMDB)
- Filtrar filmes com `popularity > 5` e `vote_count > 50` para evitar ruído
- Ignorar filmes do tipo "Documentary" e "Talk Show" (geralmente criam conexões espúrias)
- Guardar apenas atores com `order < 15` no elenco (personagens principais)

```python
# Exemplo de assinatura das funções em tmdb.py
async def search_actor(name: str) -> Actor | None
async def get_actor_movies(actor_id: int) -> list[Movie]
async def get_movie_cast(movie_id: int) -> list[Actor]
```

---

## Fase 2 — Cache SQLite (`cache.py`)

Evita refazer chamadas já feitas. Estrutura do banco:

```sql
CREATE TABLE actors (
    id INTEGER PRIMARY KEY,
    name TEXT,
    popularity REAL,
    fetched_at TIMESTAMP
);

CREATE TABLE movies (
    id INTEGER PRIMARY KEY,
    title TEXT,
    year INTEGER,
    popularity REAL
);

CREATE TABLE actor_movies (
    actor_id INTEGER,
    movie_id INTEGER,
    PRIMARY KEY (actor_id, movie_id)
);

CREATE TABLE movie_cast (
    movie_id INTEGER,
    actor_id INTEGER,
    billing_order INTEGER,
    PRIMARY KEY (movie_id, actor_id)
);
```

- TTL do cache: 7 dias (dados do TMDB não mudam muito)
- Verificar cache antes de qualquer chamada HTTP

---

## Fase 3 — Algoritmo BFS Bidirecional (`bfs.py`)

### Por que BFS bidirecional?
O BFS normal explora **exponencialmente** a partir de um lado só.
O bidirecional expande dos **dois lados ao mesmo tempo** e para quando as fronteiras se encontram — reduz drasticamente o espaço de busca.

### Pseudocódigo:

```
frontier_a = {actor_start}   # expande a partir do ator A
frontier_b = {actor_end}     # expande a partir do ator B
visited_a  = {actor_start: None}
visited_b  = {actor_end: None}

while frontier_a e frontier_b não vazias:
    # Expandir o lado menor (heurística)
    se len(frontier_a) <= len(frontier_b):
        nova_frontier = expandir(frontier_a, visited_a)
        se nova_frontier intersecta visited_b:
            return reconstruir_caminho(intersecção, visited_a, visited_b)
        frontier_a = nova_frontier
    else:
        [mesmo para o lado B]
```

### Função `expandir(frontier, visited)`:
1. Para cada ator na frontier:
   - Busca os filmes dele (cache → TMDB)
   - Para cada filme:
     - Busca o elenco (cache → TMDB)
     - Para cada ator do elenco ainda não visitado:
       - Adiciona ao visited com ponteiro de volta
       - Adiciona à nova frontier

### Reconstrução do caminho:
- Do ponto de encontro, seguir os ponteiros de `visited_a` de volta até actor_start
- Seguir os ponteiros de `visited_b` de volta até actor_end
- Concatenar e inverter → caminho completo

---

## Fase 4 — Modelos de Dados (`models.py`)

```python
from dataclasses import dataclass

@dataclass
class Actor:
    id: int
    name: str
    popularity: float

@dataclass
class Movie:
    id: int
    title: str
    year: int
    popularity: float

@dataclass
class Step:
    actor: Actor
    via_movie: Movie  # filme que conecta ao próximo passo
```

---

## Fase 5 — Entry Point (`main.py`)

```python
# Uso:
# python main.py "Tom Hanks" "Lupita Nyong'o"

import asyncio, sys
from bfs import find_shortest_path
from tmdb import search_actor

async def main():
    name_a, name_b = sys.argv[1], sys.argv[2]

    actor_a = await search_actor(name_a)
    actor_b = await search_actor(name_b)

    if not actor_a or not actor_b:
        print("Ator não encontrado.")
        return

    path = await find_shortest_path(actor_a, actor_b)

    if not path:
        print("Nenhuma conexão encontrada.")
        return

    # Imprimir o caminho
    for i, step in enumerate(path):
        print(f"{step.actor.name}")
        if step.via_movie:
            print(f"  └─ {step.via_movie.title} ({step.via_movie.year})")

asyncio.run(main())
```

---

## Fase 6 — Otimizações Importantes

### Prioridade na expansão (heurística de popularidade):
- Expandir primeiro os **atores mais populares** (têm mais filmes, criam mais pontes)
- Usar `priority queue` (heapq) em vez de deque pura: atores com maior popularidade têm prioridade

### Filtros para reduzir ruído:
- Ignorar filmes com `vote_count < 50` (muito obscuros, geram falsos atalhos)
- Ignorar atores com `popularity < 1.0`
- Ignorar filmes de gêneros: Documentary (99), Talk (10767), News (10763)

### Rate limiting:
```python
# Em tmdb.py
semaphore = asyncio.Semaphore(30)  # máx 30 requests simultâneos
```

### Timeout de segurança:
- Máximo de 6 níveis de profundidade (além disso, provavelmente não há conexão via filmes mainstream)

---

## Ordem de implementação sugerida para o Claude Code

1. `config.py` — API key e constantes
2. `models.py` — dataclasses simples
3. `cache.py` — SQLite com funções get/set
4. `tmdb.py` — 3 funções async + rate limiter
5. `bfs.py` — BFS bidirecional com reconstrução de caminho
6. `main.py` — CLI e output formatado
7. **Testes**: testar com pares conhecidos como `Kevin Bacon → Meryl Streep`

---

## Prompt sugerido para colar no Claude Code

```
Crie um projeto Python chamado connect_the_stars seguindo este roadmap.

O projeto deve:
- Usar a API do TMDB (vou fornecer a API key via variável de ambiente TMDB_API_KEY)
- Implementar BFS bidirecional para encontrar o menor caminho entre dois atores
- Ter cache SQLite para evitar re-fetch
- Usar httpx async com semaphore para respeitar o rate limit do TMDB
- Filtrar filmes pouco conhecidos (vote_count < 50) e gêneros irrelevantes (documentary, talk show)
- Expandir atores por ordem de popularidade (mais populares primeiro)
- Ter um CLI simples: python main.py "Ator A" "Ator B"

Estrutura de arquivos: config.py, models.py, cache.py, tmdb.py, bfs.py, main.py

Comece pelos arquivos base (config, models, cache) e depois implemente o tmdb.py e o bfs.py.
```

---

## Por que vai funcionar melhor que antes?

| Problema anterior | Solução aqui |
|---|---|
| BFS unidirecional explora demais | BFS bidirecional reduz espaço exponencialmente |
| Filmes obscuros criando caminhos falsos | Filtro por vote_count e gênero |
| Re-fetch repetido da API | Cache SQLite persistente |
| Sem prioridade na expansão | Popularidade como heurística |
| Rate limit da TMDB | Semaphore async controlado |