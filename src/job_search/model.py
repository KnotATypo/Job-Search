import datetime
import os
from enum import Enum

from dotenv import load_dotenv
from peewee import (
    Model,
    AutoField,
    CharField,
    ForeignKeyField,
    IntegerField,
    CompositeKey,
    TextField,
    PostgresqlDatabase,
    BooleanField,
    DateTimeField,
)
from peewee_enum_field import EnumField

load_dotenv()

db = PostgresqlDatabase(
    os.getenv("DATABASE_NAME"),
    user=os.getenv("DATABASE_USER"),
    password=os.getenv("DATABASE_PASSWORD"),
    host=os.getenv("DATABASE_HOST"),
)
db.connect()


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    id = AutoField(primary_key=True)
    username = CharField(unique=True)


class Job(BaseModel):
    id = AutoField(primary_key=True)
    title = TextField()
    company = TextField()


class JobStatus(BaseModel):
    user = ForeignKeyField(User)
    job = ForeignKeyField(Job)
    status = CharField(default="new")

    class Meta:
        primary_key = CompositeKey("user", "job")


class Listing(BaseModel):
    id = TextField(primary_key=True)
    job = ForeignKeyField(Job)
    site = CharField()
    summary = TextField()
    timestamp = DateTimeField(default=datetime.datetime.now)


class PageCount(BaseModel):
    site = CharField()
    query = CharField()
    pages = IntegerField(default=1)

    class Meta:
        primary_key = CompositeKey("site", "query")


class Location(Enum):
    Australia = "Australia"
    Brisbane = "Brisbane"
    Melbourne = "Melbourne"
    Sydney = "Sydney"
    Adelaide = "Adelaide"
    Perth = "Perth"
    Darwin = "Darwin"
    Hobart = "Hobart"


class SearchQuery(BaseModel):
    id = AutoField(primary_key=True)
    term = CharField()
    remote = BooleanField(default=False)
    location = EnumField(Location, default=Location.Australia)
    user = ForeignKeyField(User)


class Site(BaseModel):
    id = TextField(primary_key=True)
    name = TextField()


class SiteQuery(BaseModel):
    """
    Maps queries to the sites they are for.
    """

    query = ForeignKeyField(SearchQuery)
    site = ForeignKeyField(Site)

    class Meta:
        primary_key = CompositeKey("site", "query")


class BlacklistTerm(BaseModel):
    id = AutoField(primary_key=True)
    term = CharField()
    type = CharField()
    user = ForeignKeyField(User)


db.create_tables([Job, JobStatus, Listing, PageCount, SearchQuery, Site, SiteQuery, BlacklistTerm, User], safe=True)
