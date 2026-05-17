import os
import sys

from erpguard.adapters.odoo.client import OdooClient
from erpguard.adapters.odoo.config import OdooConfig


def main() -> int:
    missing = [name for name in ("ODOO_URL", "ODOO_DB", "ODOO_USERNAME", "ODOO_API_KEY") if not os.getenv(name)]
    if missing:
        print(f"Missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        return 2

    config = OdooConfig(
        url=os.environ["ODOO_URL"],
        database=os.environ["ODOO_DB"],
        username=os.environ["ODOO_USERNAME"],
        api_key=os.environ["ODOO_API_KEY"],
    )
    client = OdooClient(config)
    version = client.version()
    uid = client.authenticate()
    orders = client.search_read("sale.order", [], ["id", "name", "state", "amount_total"], limit=1)

    print("Odoo smoke read succeeded")
    print(f"server_version={version.get('server_version')}")
    print(f"uid={uid}")
    if orders:
        order = orders[0]
        print(
            "sale_order="
            f"id:{order.get('id')} "
            f"name:{order.get('name')} "
            f"state:{order.get('state')} "
            f"amount_total:{order.get('amount_total')}"
        )
    else:
        print("sale_order=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
