from pydantic import BaseModel
from datetime import date

class ReportOut(BaseModel):
    station_id: int
    station_name: str
    date: date
    avg: float
    status: str

    class Config:
        orm_mode = True
