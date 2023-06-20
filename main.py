from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Date, create_engine
from sqlalchemy.orm import relationship, Session, sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import create_engine
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import date, timedelta
import uvicorn
import os

SQLALCHEMY_DATABASE_URL = "postgresql://User:password@localhost:5432/newDB"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, index=True)
    last_name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    phone = Column(String)
    birthday = Column(Date)
    additional_info = Column(String)


Base.metadata.create_all(bind=engine)

class ContactBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    birthday: date
    additional_info: Optional[str] = None

class ContactCreate(ContactBase):
    pass

class ContactUpdate(ContactBase):
    first_name: Optional[str] = Field(None)
    last_name: Optional[str] = Field(None)
    email: Optional[EmailStr] = Field(None)
    phone: Optional[str] = Field(None)
    birthday: Optional[date] = Field(None)
    additional_info: Optional[str] = Field(None)

class ContactInDB(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    birthday: date
    additional_info: Optional[str] = None

    class Config:
        orm_mode = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI()

@app.post("/contacts/", response_model=ContactInDB)
def create_contact(contact: ContactCreate, db: Session = Depends(get_db)):
    db_contact = db.query(Contact).filter(Contact.email == contact.email).first()
    if db_contact:
        raise HTTPException(status_code=400, detail="Email already registered")
    db_contact = Contact(**contact.dict())
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact

@app.get("/contacts/", response_model=List[ContactInDB])
def read_contacts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    contacts = db.query(Contact).offset(skip).limit(limit).all()
    return contacts

@app.get("/contacts/{contact_id}", response_model=ContactInDB)
def read_contact(contact_id: int, db: Session = Depends(get_db)):
    db_contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return db_contact

@app.put("/contacts/{contact_id}", response_model=ContactInDB)
def update_contact(contact_id: int, contact: ContactUpdate, db: Session = Depends(get_db)):
    db_contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    for key, value in contact.dict(exclude_unset=True).items():
        setattr(db_contact, key, value)
    db.commit()
    db.refresh(db_contact)
    return db_contact

@app.delete("/contacts/{contact_id}")
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    db_contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    db.delete(db_contact)
    db.commit()
    return {"detail": "Contact deleted"}, 204

@app.get("/contacts/search/", response_model=List[ContactInDB])
def search_contacts(query: str, db: Session = Depends(get_db)):
    contacts = db.query(Contact).filter((Contact.first_name.ilike('%{}%'.format(query))) |
                                         (Contact.last_name.ilike('%{}%'.format(query))) |
                                         (Contact.email.ilike('%{}%'.format(query)))).all()
    return contacts

@app.get("/contacts/upcoming_birthdays", response_model=List[ContactInDB])
def get_upcoming_birthdays(db: Session = Depends(get_db)):
    today = date.today()
    next_week = today + timedelta(days=7)
    contacts = db.query(Contact).filter((Contact.birthday >= today) & (Contact.birthday <= next_week)).all()
    return contacts

#@app.get("/")
#def read_root():
#    return {"Hello": "World"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)

