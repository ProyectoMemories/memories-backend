# Spec: recuerdos — Tareas

## Dominio

- [x] Entidad `Photo` con asociacion y orden
- [x] Entidad `Memory` con sus invariantes
      · test: `tests/unit/test_memory_entity.py`
- [x] Puertos `MemoryRepository` y `PhotoRepository` (siempre con `owner_id`)
- [x] `revive_selector` como servicio de dominio

## Infraestructura

- [x] Tablas `memories` y `photos`, un archivo por tabla
- [x] Migracion `0001` generada con `--autogenerate`
- [x] Mappers y repositorios SQLAlchemy
- [x] Consultas de calendario, "en este dia" y aleatoria

## Casos de uso

- [x] `UploadPhoto` con validacion de formato y firma binaria
      · test: `tests/unit/test_image_validator.py`
- [x] `CreateMemory` · test: `test_crear_un_recuerdo_con_sus_fotografias`
- [x] `ListMemories` con paginacion y filtros
- [x] `GetMemory` · `UpdateMemory` · `DeleteMemory`
- [x] `AttachPhotos` · `RemovePhoto` (no deja quitar la ultima)
- [x] `GetMemoryCalendar` · test: `test_el_calendario_cuenta_los_recuerdos_de_cada_dia`
- [x] `ReviveMemories` · test: `test_revivir_devuelve_recuerdos_de_este_dia_en_otro_ano`
- [x] `GetPhotoContent` y `DeletePhoto`

## Interfaz HTTP

- [x] `photos_router` y `memories_router`
- [x] Esquemas de peticion y respuesta
- [x] `dependencies.py` con todo el cableado
- [x] URLs firmadas en las respuestas (`PhotoUrlService`)

## Privacidad

- [x] `owner_id` en la firma de todos los puertos
- [x] Test que intenta leer, editar y borrar datos ajenos
      · `tests/integration/test_privacy.py`

## Pendientes

- [ ] Limpieza periodica de fotografias huerfanas
- [ ] Miniaturas (hoy el cliente descarga la imagen completa en el listado)
- [ ] Cerrar P15: mecanismo definitivo de "revivir"
- [ ] Cerrar P13, P14 y P16 (maximo de fotos, ubicacion, campos obligatorios)
