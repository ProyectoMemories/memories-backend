---
description: Corre lint, formato, dependencias, tipos y pruebas del repo
---
Fase: Pruebas.

Ejecuta, en este orden:

```bash
ruff check .
ruff format --check .
lint-imports
mypy
pytest
```

Resume el resultado. Si algo falla, explica la causa y propone el arreglo.
**Nunca** cambies un test para que pase sin avisarlo.
