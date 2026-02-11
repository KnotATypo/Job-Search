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


class Listing(Model):
    id = TextField(primary_key=True)
    site = CharField()
    summary = TextField()
    timestamp = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = db


class PageCount(Model):
    site = CharField()
    query = CharField()
    pages = IntegerField(default=1)

    class Meta:
        database = db
        primary_key = CompositeKey("site", "query")


class User(Model):
    id = AutoField(primary_key=True)
    username = CharField(unique=True)

    class Meta:
        database = db


class Job(Model):
    id = AutoField(primary_key=True)
    title = TextField()
    company = TextField()
    status = CharField(default="new")
    user = ForeignKeyField(User)

    class Meta:
        database = db


class JobToListing(Model):
    job_id = ForeignKeyField(Job)
    listing_id = ForeignKeyField(Listing)

    class Meta:
        database = db


class Location(Enum):
    Australia = "Australia"
    Brisbane = "Brisbane"
    Melbourne = "Melbourne"
    Sydney = "Sydney"
    Adelaide = "Adelaide"
    Perth = "Perth"
    Darwin = "Darwin"
    Hobart = "Hobart"


class SearchQuery(Model):
    id = AutoField(primary_key=True)
    term = CharField()
    remote = BooleanField(default=False)
    location = EnumField(Location, default=Location.Australia)
    user = ForeignKeyField(User)

    class Meta:
        database = db


class Site(Model):
    id = TextField(primary_key=True)
    name = TextField()

    class Meta:
        database = db


class SiteQuery(Model):
    """
    Maps queries to the sites they are for.
    """

    query = ForeignKeyField(SearchQuery)
    site = ForeignKeyField(Site)

    class Meta:
        database = db
        primary_key = CompositeKey("site", "query")


class BlacklistTerm(Model):
    id = AutoField(primary_key=True)
    term = CharField()
    type = CharField()
    user = ForeignKeyField(User)

    class Meta:
        database = db


db.create_tables([Job, Listing, JobToListing, PageCount, SearchQuery, Site, SiteQuery, BlacklistTerm, User], safe=True)
