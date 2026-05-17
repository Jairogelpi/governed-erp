from pydantic import BaseModel, Field


class OdooConfig(BaseModel):
    url: str
    database: str
    username: str
    api_key: str = Field(repr=False)
    formula_model: str = "x.sale.formula.line"
    capacity_field: str = "x_capacity_ml"
