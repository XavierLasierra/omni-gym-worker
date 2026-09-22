from pydantic import BaseModel, Field


class Gym(BaseModel):
    id: str
    name: str
    url: str


class ScrapeWork(BaseModel):
    gyms: list[Gym] = Field(default_factory=list)


class DueClass(BaseModel):
    gymClassId: str
    accountId: str
    className: str
    classTime: str
    targetDate: str
    gymUrl: str
    bookingWindowHours: int = 48


class BookingWork(BaseModel):
    classesToBook: list[DueClass] = Field(default_factory=list)


class Credentials(BaseModel):
    username: str
    password: str
