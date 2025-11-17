import os

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
)

load_dotenv()

db = PostgresqlDatabase(
    os.getenv("DATABASE_NAME"),
    user=os.getenv("DATABASE_USER"),
    password=os.getenv("DATABASE_PASSWORD"),
    host=os.getenv("DATABASE_HOST"),
)
db.connect()


class Job(Model):
    id = AutoField(primary_key=True)
    title = TextField()
    company = TextField()
    status = CharField(default="new")
    username = CharField()

    class Meta:
        database = db


class Listing(Model):
    id = TextField(primary_key=True)
    site = CharField()
    summary = TextField()

    class Meta:
        database = db


class JobToListing(Model):
    job_id = ForeignKeyField(Job)
    listing_id = ForeignKeyField(Listing)

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


class SearchTerm(Model):
    id = AutoField(primary_key=True)
    term = CharField()
    remote = BooleanField(default=False)
    user = ForeignKeyField(User, backref="search_terms")

    class Meta:
        database = db


class BlacklistTerm(Model):
    id = AutoField(primary_key=True)
    term = CharField()
    user = ForeignKeyField(User, backref="blacklist_terms")

    class Meta:
        database = db


db.create_tables([Job, Listing, JobToListing, PageCount, SearchTerm, BlacklistTerm, User], safe=True)
