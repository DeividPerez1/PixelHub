# Pla de refactorització a `asyncio`

## Context

PixelHub es troba actualment en una arquitectura de **Practice 1**:

- el servidor utilitza `socket` directament;
- `accept()`, `recv()` i `sendall()` són operacions bloquejants;
- només es processa un client cada vegada;
- el client utilitza una connexió TCP síncrona;
- el routing i els serveis són síncrons;
- l'accés a la base de dades utilitza SQLAlchemy síncron.

La **Practice 2** requereix una arquitectura asíncrona que pugui mantenir
diverses connexions actives i continuar atenent nous clients mentre espera
operacions d'entrada/sortida.

L'objectiu d'aquest pla és canviar el transport i la concurrència sense
trencar el routing, els serveis ni el protocol JSON existent.

---

## 1. Estat actual contra els requisits

### Checklist de l'estat actual

| Àrea | Estat actual | Practice 2 | Acció necessària |
| --- | --- | --- | --- |
| Acceptació de connexions | `socket.accept()` bloquejant | Servidor no bloquejant | Substituir per `asyncio.start_server()` |
| Lectura de peticions | `connection.recv()` en un bucle síncron | Lectura asíncrona | Utilitzar `StreamReader.read()` o `readuntil()` |
| Escriptura de respostes | `sendall()` bloquejant | Escriptura asíncrona | Utilitzar `StreamWriter.write()` i `await drain()` |
| Clients simultanis | Un client per iteració del bucle | Múltiples clients concurrents | Crear una coroutine per connexió |
| Event loop | No existeix | Necessari | Afegir `asyncio.run(main())` |
| Client | `socket.create_connection()` i `recv()` | Client asíncron | Utilitzar `asyncio.open_connection()` |
| Final de petició | El client fa `shutdown(SHUT_WR)` | EOF asíncron | Utilitzar `writer.write_eof()` quan sigui compatible |
| Final de resposta | El servidor tanca el socket | Tancament ordenat | `writer.close()` i `await writer.wait_closed()` |
| Desconnexions | Només es detecten amb `recv()` buit | EOF i errors de stream | Gestionar `b""`, `ConnectionResetError`, `BrokenPipeError` i `IncompleteReadError` |
| Error d'un client | Pot interrompre el flux de la connexió actual | Ha d'aïllar-se | Capturar errors per client i mantenir el servidor actiu |
| Sessions DB | SQLAlchemy síncron | No ha de bloquejar l'event loop | Executar el bloc DB en un fil o migrar a Async SQLAlchemy |
| Routing | `ACTION_HANDLERS` i `REPOSITORIES` ja existeixen | S'ha de conservar | Reutilitzar-los dins del handler asíncron |
| Serveis | Processadors síncrons | Es poden conservar inicialment | Executar-los fora de l'event loop |
| Protocol | JSON amb `accion` i `datos` | Es vol conservar | No cal canviar el contracte |
| Tests | Tests de routing síncron | Cobertura d'async pendent | Afegir tests de streams, concurrència i tancament |
| Tipatge | Tipatge parcial | Coroutines i streams tipats | Afegir anotacions a handlers i helpers |

### Elements que ja es poden conservar

No cal reescriure tota l'aplicació. Aquestes parts continuen sent vàlides:

- `ACTION_HANDLERS`;
- `REPOSITORIES`;
- `validate_request()`;
- `error_response()`;
- els DTO i els models;
- els serveis de cada entitat;
- el format de petició i resposta;
- la configuració de l'adreça i el port.

La primera fase ha de modificar principalment el transport i el punt
d'execució de les operacions síncrones.

---

## 2. Solució proposada per al servidor

### 2.1. Substituir sockets manuals per streams d'`asyncio`

El servidor ha d'utilitzar:

```python
server = await asyncio.start_server(
    handle_client,
    host=SERVER_HOST,
    port=SERVER_PORT,
)
```

`asyncio.start_server()` accepta connexions en segon pla i invoca
`handle_client(reader, writer)` per cada connexió. Cada handler és una
coroutine independent, de manera que una espera de xarxa d'un client no
impedeix acceptar ni processar altres clients.

Estructura recomanada:

```python
async def main() -> None:
    server = await asyncio.start_server(
        handle_client,
        SERVER_HOST,
        SERVER_PORT,
    )

    addresses = ", ".join(str(sock.getsockname()) for sock in server.sockets or [])
    print(f"PixelHub async server listening on {addresses}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
```

`async with server` permet tancar el servidor correctament quan la coroutine
principal es cancel·la o el procés rep una interrupció.

### 2.2. Handler d'una connexió

El handler ha de separar clarament quatre passos:

1. llegir les dades;
2. descodificar JSON;
3. validar i executar el routing;
4. escriure la resposta i tancar el stream.

Esquema recomanat:

```python
async def handle_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> None:
    peer = writer.get_extra_info("peername")

    try:
        request_data = await reader.read(BUFFER_SIZE)
        if not request_data:
            return

        request = json.loads(request_data.decode("utf-8"))
        response = await create_response_async(request)
        writer.write(json.dumps(response).encode("utf-8"))
        await writer.drain()
    except (ConnectionResetError, BrokenPipeError):
        # El client ha desaparegut abans de rebre la resposta.
        return
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        response = error_response(f"Invalid request: {error}")
        writer.write(json.dumps(response).encode("utf-8"))
        await writer.drain()
    except Exception as error:
        print(f"Server request error from {peer}: {error}")
        response = error_response(f"Internal server error: {error}")
        try:
            writer.write(json.dumps(response).encode("utf-8"))
            await writer.drain()
        except (ConnectionResetError, BrokenPipeError):
            pass
    finally:
        writer.close()
        await writer.wait_closed()
```

La implementació definitiva ha d'afegir anotacions completes i evitar que un
error d'una connexió cancel·li el servidor principal.

### 2.3. Framing del protocol

El protocol actual utilitza un missatge per connexió i EOF com a senyal de final
de petició. Això es pot mantenir en la primera migració:

- el client envia un JSON;
- el client fa `write_eof()`;
- el servidor llegeix fins a EOF;
- el servidor envia una resposta;
- el servidor tanca la connexió.

Per tant, la lectura més fidel al comportament actual és:

```python
request_data = await reader.read()
```

No s'ha d'utilitzar únicament `await reader.read(BUFFER_SIZE)` si una petició
pot superar aquesta mida, perquè podria deixar dades pendents. Si es vol
limitar la mida màxima, cal acumular fragments amb un límit explícit i retornar
un error quan se superi.

Una millora posterior seria introduir framing explícit, per exemple:

- missatges delimitats per `newline`, utilitzant `readline()`;
- o un prefix de longitud.

Aquesta millora no és necessària per completar la primera migració i canviaria
el protocol actual.

### 2.4. Mantenir el routing i la capa de serveis

La funció actual `_create_response()` pot convertir-se en una funció asíncrona
o mantenir una part pura síncrona:

```python
def validate_request_data(request: dict[str, Any]) -> dict[str, Any]:
    validated_request, validation_error = validate_request(
        request,
        set(ACTION_HANDLERS),
    )
    if validation_error:
        return validation_error
    return validated_request
```

La validació no fa I/O i pot continuar sent síncrona. En canvi, la part que
crea la sessió, instancia el repositori i executa el servei ha de sortir de
l'event loop si continua sent síncrona:

```python
async def process_database_action_async(
    action: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    return await asyncio.to_thread(
        _process_database_action,
        action,
        data,
    )
```

Això conserva `ACTION_HANDLERS`, `REPOSITORIES` i els processadors actuals,
però evita executar SQLAlchemy síncron dins del fil de l'event loop.

---

## 3. Solució proposada per al client

### 3.1. Obrir una connexió asíncrona

`client/network_client.py` ha de passar a una API asíncrona:

```python
async def send_request(
    action: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reader, writer = await asyncio.open_connection(
        SERVER_HOST,
        SERVER_PORT,
    )

    try:
        request = {"accion": action, "datos": payload or {}}
        writer.write(json.dumps(request).encode("utf-8"))
        await writer.drain()
        writer.write_eof()

        response_data = await reader.read()
        if not response_data:
            return _error_response("The server returned an empty response.")

        response = json.loads(response_data.decode("utf-8"))
        if not isinstance(response, dict):
            return _error_response("The server returned an invalid response.")
        return response
    except (OSError, asyncio.IncompleteReadError, json.JSONDecodeError) as error:
        return _error_response(str(error))
    finally:
        writer.close()
        await writer.wait_closed()
```

El nom `send_request` pot conservar-se, però ara els callers hauran de fer:

```python
response = await send_request("ping")
```

Les vistes actuals són síncrones. Per integrar-les amb el client asíncron hi ha
dues opcions:

1. convertir les funcions de les vistes i el menú en `async def`, i afegir
   `await` a cada crida de xarxa;
2. mantenir el menú síncron i encapsular la petició amb
   `asyncio.run(send_request(...))`.

Es recomana la primera opció si el client també ha de fer diverses operacions
concurrents. Si el client continuarà sent un menú interactiu d'una sola acció,
la segona opció redueix l'abast del canvi, però no és adequada per cridar
`asyncio.run()` quan ja hi ha un event loop actiu.

### 3.2. Timeouts del client

La connexió ha d'estar protegida amb un timeout:

```python
reader, writer = await asyncio.wait_for(
    asyncio.open_connection(SERVER_HOST, SERVER_PORT),
    timeout=SOCKET_TIMEOUT,
)
```

Per a la lectura completa de la resposta també es pot utilitzar:

```python
response_data = await asyncio.wait_for(
    reader.read(),
    timeout=SOCKET_TIMEOUT,
)
```

Els timeouts han de retornar un error explícit i tancar sempre el writer.

---

## 4. Gestió del cicle de vida de les connexions

### Objectius

- detectar EOF i desconnexions;
- tancar recursos encara que hi hagi excepcions;
- evitar writers o sessions obertes;
- mantenir el servidor viu després d'un error d'un client;
- evitar que una connexió lenta bloquegi les altres.

### Regles d'implementació

1. **Un `StreamWriter` per connexió.** No s'ha de compartir entre clients.
2. **Tancar sempre el writer en `finally`.**
3. Després de `writer.close()`, esperar `await writer.wait_closed()`.
4. Tractar `b""` com EOF i sortir sense intentar processar una petició buida.
5. Capturar `ConnectionResetError` i `BrokenPipeError` com a desconnexions
   normals, sense fer caure el servidor.
6. Capturar errors de JSON i retornar un error de protocol quan el client
   continua connectat.
7. Capturar errors inesperats per client, registrar-los i continuar servint.
8. No fer `except Exception` sense registrar l'error. El catch general ha de
   tenir una resposta o un log clar.
9. Aplicar un timeout de lectura per evitar connexions que obren un socket i
   no envien mai dades.
10. Considerar un límit de bytes per petició per evitar acumulacions il·limitades.

Exemple de protecció contra clients lents:

```python
request_data = await asyncio.wait_for(
    reader.read(),
    timeout=SOCKET_TIMEOUT,
)
```

### Cancel·lació i tancament del servidor

En un tancament ordenat:

- deixar d'acceptar connexions noves;
- esperar o cancel·lar les tasques actives;
- tancar les connexions pendents;
- tancar el servidor;
- alliberar recursos de base de dades.

Per a la primera versió es pot confiar en la gestió de tasques de
`asyncio.start_server`. Si es vol un tancament controlat i observable, cal
mantenir un conjunt `set[asyncio.Task[None]]` de connexions actives i eliminar
cada tasca quan finalitza.

---

## 5. Impacte de la base de dades

### Problema de mantenir SQLAlchemy síncron dins de l'event loop

Les crides actuals com:

- `session.get(...)`;
- `session.scalars(...)`;
- `session.add(...)`;
- `session.delete(...)`;
- `session.commit()` o `rollback()`;

poden fer I/O de xarxa, esperar el pool de connexions o executar consultes
costoses. Si s'executen directament dins d'una coroutine, bloquegen el fil de
l'event loop durant tota l'operació.

Conseqüències:

- altres clients no poden avançar mentre una consulta espera;
- augmenta la latència de totes les connexions;
- el servidor pot semblar bloquejat encara que el transport sigui asíncron;
- una consulta lenta impedeix gestionar nous esdeveniments.

Convertir només `recv()` i `sendall()` a `asyncio` no resol aquest problema.

### Opció A: `asyncio.to_thread` — recomanada per a la primera iteració

La solució incremental és executar tota l'operació de base de dades en un fil:

```python
async def process_database_action_async(
    action: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    return await asyncio.to_thread(
        _process_database_action,
        action,
        data,
    )
```

Punts importants:

- crear i tancar la `Session` dins del mateix worker;
- no compartir una `Session` entre coroutines o clients;
- no passar objectes ORM vius a l'event loop;
- convertir el resultat a DTO o diccionari abans de tornar;
- configurar i revisar la mida del pool de fils;
- considerar un `ThreadPoolExecutor` dedicat si cal limitar la concurrència
  de la base de dades;
- recordar que cancel·lar l'`await` no atura necessàriament una operació que
  ja està executant-se dins del fil.

Aquesta opció permet conservar els serveis i repositoris actuals i redueix el
risc de la migració.

### Opció B: Async SQLAlchemy — repte opcional

La migració completa utilitzaria:

- `create_async_engine`;
- `async_sessionmaker`;
- `AsyncSession`;
- dialectes asíncrons, com `asyncpg` per PostgreSQL o `aiosqlite` per SQLite;
- repositoris amb `await session.execute(...)`, `await session.commit()` i
  `await session.delete(...)`.

Avantatges:

- l'accés a base de dades és asíncron de punta a punta;
- no consumeix un fil per cada operació bloquejant;
- millor escalabilitat quan hi ha moltes consultes concurrents.

Costos:

- cal modificar `domain/db.py`;
- cal modificar els repositoris;
- cal adaptar els serveis que depenen de sessions síncrones;
- cal revisar `work_unit`, migracions i fixtures;
- cal canviar dependències i la configuració del dialecte;
- cal assegurar que cap propietat ORM provoqui lazy loading síncron;
- cal reescriure una part important dels tests.

### Decisió proposada

1. **Practice 2 inicial:** usar `asyncio.to_thread` amb la unitat de treball
   síncrona actual.
2. Mesurar latència, nombre de clients concurrents i ocupació del pool de fils.
3. Fer Async SQLAlchemy com a repte opcional o segona fase si la càrrega
   justifica el cost.

Aquesta decisió compleix la concurrència del transport sense obligar a
reescriure simultàniament tota la capa de persistència.

---

## 6. Proves necessàries

Cal ampliar els tests actuals sense eliminar els tests unitaris síncrons de
validació i routing.

### Tests del servidor async

- `ping` retorna una resposta correcta;
- una petició vàlida es dirigeix al mateix `ACTION_HANDLERS`;
- JSON invàlid retorna una resposta d'error;
- una petició buida no executa cap servei;
- EOF del client es gestiona sense excepció no controlada;
- una desconnexió abans de la resposta no atura el servidor;
- el writer es tanca en cas correcte i en cas d'excepció;
- un error d'un client no afecta una segona connexió.

### Tests de concurrència

- obrir dues o més connexions alhora;
- fer que una connexió esperi I/O;
- comprovar que una altra connexió pot completar-se;
- verificar que el servidor pot acceptar nous clients mentre hi ha peticions
  actives;
- comprovar que una operació DB en un fil no bloqueja una coroutine de control.

### Tests del client async

- connexió correcta;
- timeout d'obertura;
- timeout de lectura;
- resposta buida;
- JSON invàlid;
- resposta que no és un objecte;
- tancament del writer en tots els camins.

### Tests d'integració

Iniciar un servidor en un port de proves, executar diverses peticions reals i
aturar-lo al final del fixture. No s'ha d'utilitzar el port de producció
durant els tests.

---

## 7. Pla d'acció pas a pas

### Fase 1 — Preparació i contracte

1. Confirmar que el protocol actual continua sent un missatge JSON per
   connexió.
2. Decidir si es manté EOF com a framing inicial.
3. Fixar constants de timeout i mida màxima de petició.
4. Crear tests async mínims abans de modificar el servidor.
5. Revisar els punts on el client assumeix que `send_request()` és síncron.

### Fase 2 — Aïllar la lògica independent del transport

6. Separar la validació pura de `_create_response()`.
7. Mantenir `ACTION_HANDLERS` i `REPOSITORIES` sense canvis funcionals.
8. Fer que el processament DB síncron sigui una funció ben delimitada.
9. Afegir anotacions a `reader`, `writer`, peticions, respostes i coroutines.

### Fase 3 — Refactoritzar el servidor

10. Importar `asyncio` i substituir `socket.socket()` manual.
11. Implementar `asyncio.start_server()`.
12. Crear `async def handle_client(reader, writer)`.
13. Implementar lectura fins a EOF amb timeout.
14. Reutilitzar el JSON, la validació i les respostes existents.
15. Executar `_process_database_action()` amb `asyncio.to_thread`.
16. Escriure amb `writer.write()` i `await writer.drain()`.
17. Tancar sempre amb `writer.close()` i `await writer.wait_closed()`.
18. Afegir logs de connexió, desconnexió i excepcions per client.
19. Afegir tancament ordenat de la tasca principal.

### Fase 4 — Refactoritzar el client

20. Substituir `socket.create_connection()` per `asyncio.open_connection()`.
21. Fer `send_request()` asíncrona.
22. Substituir `sendall()` per `write()` i `await drain()`.
23. Fer `write_eof()` després d'enviar el JSON.
24. Llegir la resposta amb `await reader.read()`.
25. Afegir timeouts i gestió d'errors.
26. Tancar sempre el writer.
27. Actualitzar les vistes o afegir un adaptador controlat per al menú.
28. Actualitzar els punts d'entrada amb `asyncio.run()`.

### Fase 5 — Validació

29. Executar els tests unitaris existents.
30. Executar els tests async del servidor i del client.
31. Fer una prova amb diversos clients simultanis.
32. Fer una prova amb un client que es desconnecta sobtadament.
33. Fer una prova amb una consulta DB lenta o simulada.
34. Comprovar que el servidor continua responent mentre la consulta lenta està
    en un worker.
35. Revisar que no queden sockets, writers, sessions o tasks obertes.

### Fase 6 — Opcional: Async SQLAlchemy

36. Avaluar mètriques de la solució amb fils.
37. Si és necessari, afegir el dialecte asíncron adequat.
38. Crear `AsyncEngine` i `async_sessionmaker`.
39. Migrar un repositori senzill com a prova pilot.
40. Adaptar els serveis i el patró de transacció.
41. Migrar progressivament la resta de repositoris.
42. Comparar resultats, errors, rendiment i complexitat amb la solució basada
    en `to_thread`.

---

## 8. Criteris d'acceptació

La migració de Practice 2 es considerarà completa quan:

- el servidor s'iniciï amb `asyncio.run()`;
- utilitzi `asyncio.start_server()`;
- pugui mantenir diverses connexions concurrents;
- no utilitzi `accept()`, `recv()` ni `sendall()` bloquejants en el camí async;
- una connexió lenta no impedeixi atendre altres clients;
- els errors i les desconnexions siguin aïllats per connexió;
- tots els writers es tanquin amb `wait_closed()`;
- el routing i els serveis continuïn funcionant;
- les operacions SQLAlchemy no bloquegin l'event loop;
- el client utilitzi `asyncio.open_connection()`;
- els tests cobreixin concurrència, EOF, timeouts i errors;
- el codi mantingui type hints, estil PEP 8 i docstrings on siguin útils.

---

## 9. Riscos i mitigacions

| Risc | Impacte | Mitigació |
| --- | --- | --- |
| Executar SQLAlchemy síncron directament | Bloqueig global de l'event loop | `asyncio.to_thread` o Async SQLAlchemy |
| Llegir només un buffer | Peticions truncades | Llegir fins a EOF o introduir framing |
| No tancar writers | Fuites de sockets | `finally` amb `close()` i `wait_closed()` |
| `asyncio.run()` dins d'un loop existent | `RuntimeError` | Fer la cadena de crides async o usar un adaptador únic |
| Compartir una `Session` | Condicions de cursa i errors ORM | Una sessió per operació i per worker |
| Cancel·lació d'un worker DB | Operació de fons encara activa | Dissenyar transaccions curtes i timeouts DB |
| Error no aïllat | Caiguda del servidor | Handler per connexió amb logging i excepcions controlades |
| Canvi prematur a Async SQLAlchemy | Refactor massa gran | Fer primer la migració de transport i `to_thread` |
| Framing basat només en EOF | Connexions obertes indefinidament | Timeout i límit de petició |

---

## Recomanació final

La ruta més segura és:

1. mantenir el protocol JSON actual;
2. migrar el servidor a `asyncio.start_server`;
3. migrar el client a `asyncio.open_connection`;
4. conservar routing i serveis;
5. executar la unitat de treball síncrona amb `asyncio.to_thread`;
6. cobrir el cicle de vida amb tests de concurrència;
7. deixar Async SQLAlchemy com a millora opcional basada en mètriques.

Això entrega una Practice 2 funcional amb canvis controlats, evita bloquejar
l'event loop i conserva la feina ja feta a la capa de domini i serveis.

