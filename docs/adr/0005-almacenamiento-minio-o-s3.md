# ADR 0005 — MinIO en local, S3 en el despliegue, un solo adaptador

- Estado: aceptada
- Fecha: 2026-09-22

## Contexto

RNF-09 pide guardar las fotografias en MinIO o en S3 y **un archivo que permita
cambiar entre los dos**. En local no queremos depender de una cuenta de AWS; en
el futuro queremos desplegar en S3 sin reescribir nada.

## Decision

`app/core/storage/`:

- `port.py` — `StoragePort`: `save`, `get`, `delete`, `presigned_url`.
- `s3_storage.py` — **un solo adaptador para MinIO y para S3**, porque hablan el
  mismo protocolo. Lo unico que cambia es la configuracion.
- `local_storage.py` — disco, para tests y para trabajar sin Docker.
- `factory.py` — **el archivo del RNF-09**. Lee `STORAGE_PROVIDER`
  (`minio` | `s3` | `local`) y devuelve el adaptador ya configurado.

Migrar de MinIO a S3 es cambiar variables de entorno: `STORAGE_PROVIDER=s3`,
credenciales y region. Ni una linea de codigo.

Ademas, las descargas van por **URL firmada**: el telefono baja la imagen
directamente del almacenamiento y los bytes no pasan por la API. En CRIS todo el
contenido se transmitia a traves del backend.

## Consecuencias

- Dentro de Docker la API habla con MinIO por la red interna
  (`http://minio:9000`), pero quien abre la URL firmada es el telefono o el
  navegador, que ven `http://localhost:9000`. Por eso hay dos clientes: uno para
  operar y otro para firmar (`S3_PUBLIC_ENDPOINT`). En el emulador de Android esa
  variable es `http://10.0.2.2:9000`.
- Cuando el backend no emite URLs firmadas (disco local), la API sirve la imagen
  por `GET /photos/{id}/raw`. El cliente no nota la diferencia: siempre recibe una
  `url`.
- El borrado de un archivo puede fallar despues de borrar la fila. Se registra en
  el log y queda un huerfano en el bucket, que es preferible a una fila que
  apunta a un archivo inexistente.
