from pydantic import BaseModel


class CarrierOptionDecision(BaseModel):
    option_id: str
    carrier: str
    total_landed_cost: float
    feasible: bool
    reason: str
