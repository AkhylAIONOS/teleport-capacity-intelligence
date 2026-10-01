from pydantic import BaseModel


class ShipmentIdentity(BaseModel):
    shipment_id: str
    origin: str
    destination: str
    weight_kg: float
