# ERPGuard Evolution — Memoria TFM (BORRADOR)

> **Nota para el autor, léela antes de usar este documento**: esto es un
> borrador generado a partir del estado real del repositorio en
> 2026-08-02 (commit `87c402c` en `main`, más el trabajo de la Fase 22
> sobre la rama `feat/phase22-tfm-delivery-and-release-freeze`). Cada
> afirmación factual está anclada a un artefacto real (test, endpoint,
> archivo de evidencia, número de benchmark) — no hay cifras inventadas.
> Aun así, esto NO es una memoria terminada: falta la voz del autor, la
> bibliografía real (las citas están marcadas `TODO`), una revisión de
> estilo académico completa, y la decisión final sobre qué recortar para
> caber en el límite de 20 páginas. Edítalo, no lo entregues tal cual.
> El límite de 20 páginas de la Sec 39.1 es un límite de *contenido*, no
> de líneas de este archivo Markdown — la maquetación final decidirá
> cuántas páginas ocupa cada sección.

---

## 1.0 Resumen ejecutivo

ERPGuard Evolution es un backend gobernado que conecta el análisis
analítico de un ERP (Odoo) con la ejecución de acciones reales sobre ese
mismo ERP, manteniendo en todo momento una frontera de seguridad
explícita: casi todo el sistema es de solo lectura o simulado, y el
conjunto de escrituras reales permitidas es pequeño, listado por código
(`allowlist`) y deliberadamente incapaz de una "escritura genérica" sobre
el ERP. El proyecto demuestra que es posible construir una capa de
gobernanza — recomendación → aprobación independiente → borrador de
acción acotado → enrutamiento canary determinista → permiso firmado de
un solo uso → verificación de postcondiciones → medición de resultado no
causal → paquete de evidencia sellado y verificable — sin renunciar a
que cada paso sea auditable y sin generar una sola escritura no
autorizada sobre el ERP conectado.

El sistema se comparó, mediante un banco de pruebas determinista de 120
casos (`erpguard/benchmark/`, Especificación 93), contra un flujo fijo
sin gobernanza (`fixed_workflow`). El resultado (`BenchmarkRun`
`benchmarkrun_a822cc4414564953b0e89f1b27eb3d53`, ver Sección 4): la
configuración gobernada (`erpguard_candidate`) alcanzó una tasa de éxito
de tarea del 100% (IC 95%: 96.9%-100%) y una tasa de efectos secundarios
inseguros del 0%, frente al 54.2% y 25% respectivamente del flujo fijo
sin gobernanza. El coste de esa seguridad es medible y honesto: la
configuración gobernada bloquea un 16.7% de casos que un revisor humano
consideraría legítimos (`false_block_rate`) — una decisión de diseño
conservadora, no un error, discutida en la Sección 9.

## 1.5 Problema y objetivos

**Problema**: los sistemas de agentes de IA con acceso a herramientas de
ERP tienden a ofrecer, por diseño, ejecución sin fricción — el problema
que este proyecto ataca no es "¿puede un LLM rellenar un formulario de
Odoo?" sino "¿puede hacerlo de forma que cada acción sea explicable,
revisable por una persona distinta de quien la propuso, deshecha por
construcción si algo cambia entre la planificación y la ejecución, y
medible en su resultado real sin fingir causalidad que no se puede
demostrar?".

**Objetivos** (TODO: alinear literalmente con los objetivos formales de
la propuesta de TFM si difieren):

1. Diseñar e implementar una capa de gobernanza de decisión-a-resultado
   sobre un ERP real (Odoo), con permisos firmados de un solo uso y
   verificación de postcondiciones.
2. Implementar un enrutador canary operacional determinista para
   desplegar cambios de forma incremental y medible.
3. Medir el resultado realizado de una recomendación frente a su
   estimación, sin emitir una afirmación causal no soportada por el
   diseño experimental.
4. Sellar toda la cadena de evidencia (dato → diagnóstico →
   recomendación → aprobación → ejecución → postcondiciones →
   enrutamiento → resultado) en un artefacto verificable e inmutable.
5. Comparar cuantitativamente el comportamiento gobernado frente a un
   agente sin gobernanza sobre un banco de pruebas reproducible.

## 2.0 Estado del arte

TODO (autor): situar este trabajo frente a (a) sistemas de agentes con
uso de herramientas (tool-use) sobre software empresarial, (b) marcos de
gobernanza de agentes de IA / "AI agent guardrails", (c) sistemas de
control de cambios canary en ingeniería de software aplicados a
decisiones de negocio en lugar de despliegues de código, (d) medición de
resultados (uplift/causal inference) y por qué este proyecto
deliberadamente NO reivindica una medición causal (ver interpretation.py
y la Sección 9 de la Especificación 92). Citar bibliografía real —
placeholders abajo.

- TODO: cita sobre agentic tool-use / function calling.
- TODO: cita sobre seguridad de agentes de IA / guardrails.
- TODO: cita sobre canary releases / progressive delivery.
- TODO: cita sobre medición de causalidad vs. correlación en sistemas de
  producción.

## 2.0 Diseño de investigación

Pregunta de investigación operacionalizada como comparación de tres
configuraciones sobre un conjunto de datos sintético común (Especificación
93, `erpguard/benchmark/dataset_generator.py`, semilla 92, 120 casos
distribuidos en 10 categorías: `valid_complete` (30), `ambiguous` (15),
`incomplete` (15), `duplicate_retry` (10), `high_risk_actions` (10),
`indirect_prompt_injection` (10), `missing_entities` (10),
`policy_violations` (10), `identity_cross_tenant` (5), `state_drift`
(5)):

- **`fixed_workflow`** — un flujo determinista sin capa de gobernanza,
  la línea base "ingenua".
- **`erpguard_candidate`** — el sistema real de este proyecto
  (`validate_pricing_scenario`, aprobación obligatoria, verificación de
  postcondiciones), reutilizando la lógica de producción, no una
  reimplementación paralela "de juguete".
- **`direct_tool_agent`** — un agente LLM con acceso a herramientas sin
  ninguna capa de gobernanza (el único punto del código donde se invoca
  un LLM), deliberadamente inseguro, para medir el peor caso realista.
  Requiere `ANTHROPIC_API_KEY` real y un flag explícito
  (`ERPGUARD_ALLOW_BENCHMARK_DIRECT_AGENT=true`); sin ambos, cada caso
  se marca honestamente `not_run`, nunca como aprobado o fallado por
  omisión.

Catorce métricas (Sec 28.3, `erpguard/benchmark/metrics.py`) como
funciones puras sobre los resultados: tasa de éxito de tarea, tasa de
efecto secundario inseguro, tasa de bloqueo correcto/incorrecto,
precisión de resolución de entidad, tasa de prevención de duplicados,
cobertura de postcondiciones, completitud de evidencia, repetibilidad
determinista, latencia media, coste medio de tokens, carga de revisión
humana, regresiones introducidas/prevenidas. Intervalos de confianza al
95% vía Wilson (`erpguard/domain/canary/metrics.py::wilson_interval`,
reutilizado, no reimplementado).

**Limitación de diseño reconocida**: el conjunto de datos es sintético.
Los resultados validan la lógica de gobernanza frente a un conjunto de
casos controlado y reproducible; no demuestran resultados de conversión
comercial reales (ver el propio `disclaimer` embebido en cada informe
generado, Sección 4).

## 3.0 Arquitectura

Arquitectura en capas dominio/aplicación por área
(`erpguard/domain/<area>/`, `erpguard/application/<area>/service.py`,
`erpguard/db/model_packages/<area>.py`), FastAPI + SQLAlchemy + Alembic,
SQLite para tests y PostgreSQL en CI (con ciclo de downgrade/upgrade
verificado en cada push).

Cadena de gobernanza de decisión-a-resultado (Especificación 92):

```text
oportunidad de margen (MarginOpportunity)
  -> recomendación gobernada (GovernedRecommendation, congelada al enviar)
  -> aprobación independiente (vinculada al hash exacto del contenido)
  -> borrador de acción acotado (GovernedActionDraft)
  -> enrutamiento canary operacional (sha256 determinista, sin RNG, sin LLM)
  -> permiso firmado de un solo uso (ExecutionRun)
  -> escritura Odoo controlada (sales.quote.create_pricing_scenario_draft)
  -> verificación de postcondiciones (estado draft, cero efectos colaterales)
  -> medición de resultado (OutcomeMeasurementPlan, sin afirmación causal)
  -> paquete de evidencia sellado (DecisionOutcomeEvidenceBundle,
     encadenado por hash, inmutable, verificable)
```

Cada capacidad de escritura real es explícita, con feature flag
false-by-default, y estructuralmente incapaz de ejecutar un método RPC
genérico contra el ERP (verificado por test:
`for forbidden in ("execute_raw", "call_method", "model", "method"):
assert not hasattr(plugin, forbidden)`).

Diagramas completos: `docs/architecture/decision_to_outcome_flow.md`
(8 diagramas Mermaid).

## 2.5 Implementación

Componentes principales entregados a lo largo de las fases 0-22:

- Identidad/tenants, conexiones unificadas cifradas, Connector SDK v2
  (Fake + Odoo).
- Eventos canónicos con forma OCEL, descubrimiento de variantes de
  proceso.
- Candidatos de proceso inmutables por tenant, replay histórico
  determinista, motor de regresión y Prueba de Mejora ("Proof of
  Improvement").
- Compilador de proceso a habilidad ("skill") v2, runtime de permisos
  de ejecución firmados de un solo uso.
- Confirmación gobernada de pedidos Odoo reales, modo shadow, feed
  operacional shadow.
- Inteligencia de decisión (lecturas Odoo acotadas → snapshot analítico
  inmutable → métricas de margen versionadas → oportunidades con
  evidencia).
- Especificación 92 completa (los cuatro workstreams A/B/C/D descritos
  arriba).
- Especificación 93 — ERPRiskBench (banco de pruebas comparativo).
- Especificación 94 — aplicación web de producto (React + TypeScript,
  cliente API generado desde el propio esquema OpenAPI del backend).
- Especificación 95 — esta fase: empaquetado, validación de instalación
  limpia, y evidencia de liberación.

## 4.0 Experimento y resultados

**No se re-teclean cifras a mano aquí más allá de las ya citadas en el
resumen ejecutivo** — la fuente de verdad es el artefacto generado:

- `BenchmarkRun` id: `benchmarkrun_a822cc4414564953b0e89f1b27eb3d53`
- Informe completo: `docs/benchmark/reports/benchmarkrun_a822cc4414564953b0e89f1b27eb3d53.report.json`
- Resultados crudos por caso: `docs/benchmark/reports/benchmarkrun_a822cc4414564953b0e89f1b27eb3d53.raw_results.json`
- Regenerable con: `python scripts/export_benchmark_report.py`
- Dataset: `docs/benchmark/datasets/quote_to_order_v1_seed92.{jsonl,manifest.json}`
  (hash: `92cb284cf0d55b18b33c2ef937fff74055b3d18413b297b1be130af6abbe0056`)

Comparación ejecutada: `fixed_workflow` vs. `erpguard_candidate`, 120
casos cada una, 1 repetición. `direct_tool_agent` **no** se incluyó en
esta ejecución concreta (requiere `ANTHROPIC_API_KEY` real, no
configurada en este entorno) — TODO (autor): ejecutar
`python scripts/export_benchmark_report.py --include-direct-agent` con
una clave real antes de la entrega si se quiere el tercer brazo completo
en la memoria final; sin él, el argumento "vs. agente sin gobernanza"
se apoya en el diseño del propio arm (Sección 2.0) más que en un
resultado numérico de esa configuración concreta.

Resultados desglosados (IC 95% Wilson):

| Métrica | `fixed_workflow` | `erpguard_candidate` |
| --- | --- | --- |
| Tasa de éxito de tarea | 54.17% [45.3%, 62.8%] | 100% [96.9%, 100%] |
| Tasa de efecto secundario inseguro | 25.0% [18.1%, 33.4%] | 0% [0%, 3.1%] |
| Tasa de bloqueo correcto | 50.0% [41.2%, 58.8%] | 100% [96.9%, 100%] |
| Tasa de bloqueo incorrecto (falso positivo) | 0% | 16.67% [11.1%, 24.3%] |
| Resolución de entidad | 0% | 100% |
| Prevención de duplicados | 0% | 100% |

Por categoría, la diferencia más informativa: en `high_risk_actions`,
`identity_cross_tenant`, `policy_violations` y `state_drift` —
exactamente las categorías diseñadas para exigir gobernanza —
`fixed_workflow` obtiene 0% de éxito de tarea con 100% de efecto
secundario inseguro (es decir, "tiene éxito" produciendo el efecto no
autorizado), mientras `erpguard_candidate` obtiene 100% de éxito de
tarea con 0% de efecto inseguro en las mismas categorías.

## 1.5 Seguridad e interpretabilidad

Modelo de amenazas operacional: `docs/security/operational_canary_threat_model.md`,
14 casos de amenaza, cada uno con su mitigación real y el test que la
ejercita (no un documento de intenciones de diseño). Ejemplos: alteración
de oportunidad (bloqueada por listeners `before_update`/`before_delete`
del ORM), sustitución de recomendación (el alcance de aprobación está
vinculado al hash exacto del contenido), reutilización de aprobación de
un solo uso, manipulación del bucket canary (función pura
`sha256(tenant_id, canary_policy_id, process_key, business_object_key)
mod 10000`, sin semilla controlable por el llamante), fuga de secretos
(escaneo de nombres de campo tipo `secret`/`credential`/`password` antes
de sellar cualquier paquete de evidencia).

Interpretabilidad: cada resultado medido lleva adjunta, literalmente, la
cadena `observed_change_is_not_a_causal_claim`
(`erpguard/domain/outcomes/interpretation.py`) — no en una nota a pie de
página, sino en el propio campo de la API y en la pantalla de producto
correspondiente (Especificación 94). El ROI neto solo se calcula cuando
se ha suministrado explícitamente un coste de implementación; en caso
contrario el campo es `null`, nunca estimado por defecto.

## 1.0 Valor de producto

El valor no reivindicado es tan importante como el reivindicado (Sec 5
de la Especificación 92, Sec 29 de la especificación maestra prohíben
explícitamente reclamar ROI comercial garantizado, soporte universal de
ERP, u optimización autónoma). Lo que el sistema demuestra, con
evidencia real: (1) es posible dar a un agente de IA o a un flujo
automatizado capacidad de proponer y ejecutar cambios sobre un ERP real
sin darle una superficie de escritura genérica; (2) cada acción real
queda ligada por hash a la evidencia que la motivó, a quién la aprobó
(una persona distinta de quien la propuso) y a la verificación de que
el estado tras la ejecución es el esperado; (3) el enrutamiento canary
permite exponer un cambio a una fracción determinista y auditable del
tráfico antes de una promoción completa; (4) todo lo anterior se puede
empaquetar en un artefacto único, verificable por un tercero
(`GET /v1/decision-outcome-evidence/{id}/verify`), sin depender de la
palabra de quien ejecutó la acción.

## 1.0 Limitaciones y conclusiones

Consolidado honesto de huecos conocidos, sin suavizar:

1. **El pilar decision-to-outcome no tiene ruta Fake-ERP.** Todo camino
   para crear una `MarginOpportunity` requiere una lectura Odoo real
   acotada (`POST /v1/decision-intelligence/snapshots`); no existe hoy
   un equivalente de datos sintéticos en la API pública. Descubierto y
   documentado durante la validación de instalación limpia de esta
   fase (`scripts/validate_demo_install.py`); no resuelto — resolverlo
   sería trabajo de una fase de producto, no de esta fase de
   empaquetado.
2. **`erpguard_candidate` bloquea un 16.7% de casos legítimos**
   (`false_block_rate`). Decisión de diseño conservadora — preferir un
   falso bloqueo revisable a un falso positivo de ejecución — pero es un
   coste real de fricción operativa, no gratis.
3. **Solo `formula_guard` tiene un evaluador de decisión real**; el
   proceso Quote-to-Order declara también `approval_gate`, sin
   evaluador — el motor de replay lo marca `needs_clarification` en
   lugar de fingir un resultado.
4. **Solo 4 de las 11 categorías de regresión del Sec 16 son
   detectables** con el único evaluador de política real existente.
5. **`direct_tool_agent` no se ejecutó con una clave de API real** en
   la comparación citada en la Sección 4 de este documento — el tercer
   brazo del experimento existe en el código y está probado
   (`tests/test_phase20_benchmark_runner.py`), pero el resultado
   numérico de esta memoria se apoya en dos de las tres configuraciones.
6. **No existe mecanismo de autenticación de producción real.**
   `POST /internal/dev-tokens` es un puente de arranque explícitamente
   no productivo, documentado como tal en su propio módulo.
7. **No existe borrado/retención de datos personales** — ver
   `docs/tfm/annexes/data_rights_and_gdpr.md`.
8. **`erpguard.db.session.init_db()` tenía un hueco real** (tablas de
   replay/prueba/paquete de habilidad/ejecución nunca se creaban) hasta
   que esta fase lo encontró ejecutando de verdad el script de
   validación de instalación contra un servidor vivo, y lo corrigió.
   Se documenta aquí como ejemplo metodológico: varios de los huecos
   más significativos de este proyecto no se encontraron leyendo
   código, se encontraron ejecutándolo de verdad contra un servidor en
   marcha.
9. **Los especificaciones Playwright E2E de la Fase 21 no se han
   ejecutado** contra un backend en marcha en esta sesión — son
   sintácticamente correctas (`playwright test --list` las resuelve)
   pero no verificadas en ejecución.
10. **El escaneo de dependencias (`pip-audit`) es informativo, no
    bloqueante**, en el pipeline de CI — ver la nota en
    `.github/workflows/ci.yml`.

**Conclusión**: el proyecto demuestra, con evidencia real y reproducible
(no solo diseño de intenciones), que una capa de gobernanza sobre
acciones de ERP puede reducir a cero los efectos secundarios inseguros
medidos frente a una línea base sin gobernanza, a un coste medible de
fricción por falsos bloqueos, manteniendo cada acción real trazable,
aprobada por una persona distinta de quien la propuso, y empaquetada en
evidencia verificable de forma independiente. Las limitaciones anteriores
son reales y deben leerse junto con los resultados, no en una sección
aparte que nadie lee.

## 0.5 Bibliografía

TODO (autor): sustituir por citas reales. Placeholders por tema:

- TODO: agentic tool-use / function-calling LLMs.
- TODO: AI agent safety / guardrails.
- TODO: canary releases / progressive delivery en ingeniería de
  software.
- TODO: inferencia causal vs. correlación en sistemas de producción.
- TODO: gobierno de datos / GDPR aplicado a sistemas de IA.
