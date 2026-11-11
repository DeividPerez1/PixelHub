# PixelHub Practice 2: arquitectura asíncrona

## Objectiu

PixelHub ha evolucionat d'una arquitectura de Practice 1, basada en sockets
bloquejants i un client per vegada, a una arquitectura de Practice 2 basada en
`asyncio`.

El canvi permet que el servidor mantingui diverses connexions actives i
continuï acceptant i processant clients mentre una altra connexió espera dades
de xarxa o una operació de base de dades.

La migració conserva:

- el protocol JSON existent;
- el routing de `ACTION_HANDLERS`;
- els repositoris;
- els serveis de domini;
- la base de dades SQLAlchemy síncrona;
- els menús Rich síncrons.

---

## Arquitectura

```text
┌────────────────────┐
│ Client Rich        │
│ menú síncron       │
└─────────┬──────────┘
          │ send_request_sync()
          │ asyncio.run()
          ▼
┌────────────────────┐
│ Client asyncio     │
│ asyncio.open_conn  │
└─────────┬──────────┘
          │ TCP + JSON + EOF
          ▼
┌─────────────────────────────────────┐
│ Servidor asyncio                    │
│ asyncio.start_server()              │
│ una handle_client() per connexió    │
└─────────┬───────────────────────────┘
          │ asyncio.to_thread()
          ▼
┌─────────────────────────────────────┐
│ Routing i domini síncrons            │
│ validate_request                    │
│ ACTION_HANDLERS                      │
│ services + repositories              │
│ SQLAlchemy Session                   │
└─────────────────────────────────────┘
```

### Fitxers principals

- `server/server.py`: event loop, servidor TCP, cicle de vida i dispatch.
- `client/network_client.py`: client async i adaptador síncron.
- `server/protocol.py`: validació de la petició.
- `server/services/`: processadors de les operacions CRUD.
- `server/domain/repository.py`: accés a les entitats amb SQLAlchemy.
- `server/domain/db.py`: engine i sessions de la base de dades.

---

## Servidor amb `asyncio.start_server`

El servidor s'inicia amb:

```python
asyncio.run(start_server())
```

`start_server()` crea un `asyncio.Server` i registra `handle_client` com a
callback. Cada connexió rebuda rep el seu propi `StreamReader` i
`StreamWriter`.

A diferència de la implementació anterior, el servidor no executa:

- `socket.accept()`;
- `socket.recv()`;
- `socket.sendall()`.

Les operacions de xarxa són coroutines i cedeixen el control a l'event loop
quan esperen dades.

---

## Cicle de vida d'una connexió

### 1. Acceptació

`asyncio.start_server()` accepta una connexió i programa una execució de
`handle_client(reader, writer)`.

Les connexions són independents: una no comparteix el seu `StreamReader`,
`StreamWriter` ni la seva sessió de base de dades amb una altra.

### 2. Lectura

El client escriu el JSON i envia EOF amb `writer.write_eof()`. El servidor
executa:

```python
request_data = await reader.read()
```

La lectura espera fins que el client finalitza l'enviament. El timeout evita
que una connexió oberta sense dades ocupi recursos indefinidament.

Una lectura de `b""` indica EOF sense petició i es tracta com una desconnexió
normal.

### 3. Descodificació

La funció `_decode_request()` separa la conversió de bytes a text i de text a
objecte JSON. Si el JSON és invàlid, el servidor retorna una resposta d'error
en lloc d'intentar executar cap servei.

### 4. Validació i routing

`_create_response()` continua utilitzant `validate_request()` i el conjunt
`ACTION_HANDLERS`. El routing no canvia per la migració async.

L'acció `ping` es resol directament perquè no necessita accés a la base de
dades. La resta d'accions es processen mitjançant el servei i el repositori
corresponents.

### 5. Execució de la base de dades

Les funcions de servei i SQLAlchemy continuen sent síncrones. Per no
bloquejar l'event loop, el servidor les executa així:

```python
response = await asyncio.to_thread(
    _process_database_action,
    action,
    data,
)
```

La sessió es crea, utilitza i tanca completament dins de la funció que corre al
worker. Això evita compartir objectes `Session` entre coroutines.

### 6. Escriptura

La resposta es converteix a JSON i s'envia amb:

```python
writer.write(encoded_response)
await writer.drain()
```

`drain()` permet que el transport gestioni la pressió del buffer si el client
és lent.

### 7. Tancament

El `finally` del handler sempre executa:

```python
writer.close()
await writer.wait_closed()
```

Això allibera el socket tant en una resposta correcta com després d'un error,
un timeout o una desconnexió del client.

---

## Gestió d'errors i desconnexions

Cada client té un bloc `try...except...finally` independent.

### Errors tractats

- `asyncio.TimeoutError`: client inactiu o operació de xarxa massa lenta;
- `ConnectionResetError`: el client ha tancat sobtadament;
- `BrokenPipeError`: no es pot escriure la resposta;
- `UnicodeDecodeError`: bytes que no són UTF-8;
- `json.JSONDecodeError`: petició que no és JSON vàlid;
- `ValueError`: JSON vàlid però amb una forma incorrecta;
- `Exception`: error inesperat de servei o base de dades, registrat per
  connexió.

Un error d'un client no cancel·la `start_server()` ni impedeix acceptar
connexions noves.

---

## Client asíncron i menús Rich

La funció async és:

```python
async def send_request(action, payload=None):
    ...
```

Utilitza `asyncio.open_connection()`, escriu la petició, espera `drain()`, envia
EOF i llegeix la resposta fins que el servidor tanca el stream.

Els menús Rich no s'han de convertir en coroutines. Poden utilitzar:

```python
send_request_sync("get_all_users")
```

Aquest adaptador executa:

```python
asyncio.run(send_request(action, payload))
```

La funció síncrona conserva la interfície que necessita el menú, mentre que la
comunicació TCP real és asíncrona.

---

## Estratègia `asyncio.to_thread` per a SQLAlchemy

### Per què és necessari

SQLAlchemy està configurat amb `create_engine()` i `Session` síncrona. Les
consultes, commits, rollbacks i esperes del pool poden bloquejar el fil de
l'event loop.

Si es cridessin directament dins d'una coroutine, una consulta lenta podria
impedir que tots els altres clients avancessin.

### Solució actual

`asyncio.to_thread()` envia l'operació síncrona a un worker del pool de fils.
L'event loop queda lliure per continuar gestionant sockets i altres handlers.

La regla és:

> Una operació de servei completa i la seva `Session` viuen dins del mateix
> worker i no es comparteixen amb cap altra coroutine.

### Avantatges

- canvi petit i fàcil d'entendre;
- conserva els serveis i repositoris actuals;
- no obliga a canviar el model de domini;
- permet completar Practice 2 abans de fer una migració major.

### Limitacions

- cada operació bloquejant consumeix un fil;
- cancel·lar l'`await` no atura necessàriament una consulta ja iniciada;
- el rendiment final depèn del pool de fils i del pool de connexions DB;
- no és tan escalable com Async SQLAlchemy per càrregues molt altes.

Async SQLAlchemy queda com a millora posterior, no com a requisit d'aquesta
fase.

---

## Flux complet d'una petició

```text
Rich menu
   │
   ├─ send_request_sync(action, payload)
   │
   ├─ asyncio.run(send_request(...))
   │
   ├─ asyncio.open_connection()
   │
   ├─ write(JSON) + await drain() + write_eof()
   │
   └────────────── TCP ──────────────►
                                      handle_client()
                                        │
                                        ├─ await reader.read()
                                        ├─ decode JSON
                                        ├─ validate_request()
                                        ├─ await asyncio.to_thread(...)
                                        ├─ encode JSON
                                        ├─ writer.write()
                                        └─ await writer.drain()
   ◄──────────── resposta JSON ────────┘
   │
   ├─ await reader.read()
   └─ writer.close() + await wait_closed()
```

---

## Posada en marxa

Servidor:

```powershell
python server/server.py
```

Client:

```powershell
python client/app.py
```

El client continua presentant els menús Rich de forma síncrona. Només la
crida de xarxa s'executa a través de l'event loop.

---

## Criteris de validació

La implementació compleix Practice 2 quan:

- el servidor utilitza `asyncio.start_server`;
- el client utilitza `asyncio.open_connection`;
- diverses connexions poden estar actives alhora;
- un client lent no bloqueja la lectura d'altres clients;
- la base de dades síncrona s'executa amb `asyncio.to_thread`;
- el routing i els serveis existents continuen funcionant;
- EOF, timeouts, JSON invàlid i desconnexions tenen un comportament definit;
- cada writer es tanca en un `finally`;
- els menús Rich no necessiten convertir-se en async.

