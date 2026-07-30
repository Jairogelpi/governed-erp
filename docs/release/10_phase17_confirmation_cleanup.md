# Phase 17 confirmation compensation runbook

This runbook applies only to an isolated, explicitly authorized staging
experiment. It does not authorize a production action.

## Stop conditions

Stop if a generated picking is `done`, a payment exists, manufacturing or
purchasing progressed, records cannot be identified exactly, or separate
compensation approval is absent.

## Required order

1. Re-read the order and every Evidence Pack record.
2. Cancel only generated pickings that are not completed.
3. Reverse a posted invoice through Odoo's standard linked credit-note
   workflow; never delete it.
4. Post the credit note if Odoo leaves it in draft.
5. Verify both residuals are zero, the relationship remains and documentary
   net effect is zero.
6. Cancel the order only after downstream compensation is verified.
7. Re-read every record and attach sanitized final states to evidence.

## Required final evidence

- original run remains `failed`;
- order and uncompleted picking are cancelled;
- original invoice remains posted with payment state `reversed`;
- linked credit note remains posted;
- both residuals and documentary net effect are zero;
- no record or Evidence Pack was deleted.

This is manual compensation. No executable public compensation capability
exists in the current product.
