# Spec: album compartido — Requisitos

- Capacidad del PRD: CP-07 (condicionada)
- Estado: **bloqueado**. No hay codigo escrito, y es deliberado.

## Por que esta parado

El PRD v3.0 dice, en su propia pagina de aprobacion, que la definicion de album
(pendiente **P17**) es *necesaria para aprobar el documento*. Hoy no esta
decidido:

- ¿Un recuerdo pertenece a un album, o un album agrupa recuerdos que siguen
  siendo del recuerdo de su dueno?
- ¿Un recuerdo puede estar en varios albumes?
- ¿Que puede hacer una persona invitada: solo mirar, comentar, anadir sus propios
  recuerdos?
- ¿Que ve exactamente del recuerdo ajeno: las fotos, la descripcion, la fecha?
- ¿Que pasa con lo compartido cuando el dueno borra el recuerdo o el album?
- ¿Se puede salir de un album? ¿Quien puede expulsar?

Implementar sin esas respuestas seria inventar producto, y el PRD es explicito:
*"cualquier idea nueva se registra primero como fuera del MVP y solo se incorpora
si los tres integrantes lo deciden de forma explicita"*.

Ademas esta el pendiente **P18**: el equipo debe fijar, antes de la etapa de
arquitectura, el criterio para retirar el album del MVP si resulta demasiado
complejo.

## Lo unico decidido

- El album lo crea alguien, que es su **dueno**, y decide a quien invitar
  (PRD, definiciones).
- Nada es publico: compartir es siempre una decision explicita del dueno
  (principio 4).
- Los recuerdos siguen siendo privados salvo lo que el album exponga.

## Historias de usuario (borrador, sin aprobar)

### HU-01 — Crear un album e invitar

> Como duena de recuerdos, quiero agrupar algunos y compartirlos con personas
> concretas, para revivirlos juntos.

Criterios de aceptacion: **por definir** cuando se cierre P17.

### HU-02 — Ver un album al que me invitaron

> Como persona invitada, quiero ver el album, para participar de esos recuerdos.

Criterios de aceptacion: **por definir**.

## Que hace falta para desbloquear

1. Decision del equipo sobre P17 (que es un album y que pueden hacer los
   invitados).
2. Decision sobre P18 (criterio para retirarlo del MVP).
3. Elegir uno de los dos modelos de datos de [design.md](design.md).

Mientras tanto, el backend **no** expone ningun endpoint de albumes.
