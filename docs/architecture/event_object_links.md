# Event/object link scalability hardening

Variant Discovery now reads `canonical_event_objects` instead of scanning all
tenant events for every object. The table stores `tenant_id`, `event_id`,
`object_id` and `qualifier`, with tenant/event/object indexes and a uniqueness
constraint for retry safety. Migration `0007_event_object_links` backfills
links from the existing OCEL object maps; new imports write links transactionally.

Case projection performs one relational join and excludes objects with no event
links, so empty cases cannot become empty variants. The canonical vocabulary is
`customer`, `product`, `quote`, `sales_order` and `approval`; native Odoo model
and record references are retained inside object `native` attributes.
