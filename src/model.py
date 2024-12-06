from peewee import (
    MySQLDatabase,
    Model,
    AutoField,
    CharField,
    ForeignKeyField,
    IntegerField,
    CompositeKey,
    TextField,
)

from util import is_server

db = MySQLDatabase("job_search", user="dev", password="password", host="localhost" if is_server() else "jobs.lan")
db.connect()


class Job(Model):
    id = AutoField(primary_key=True)
    title = TextField()
    company = TextField()
    type = CharField()
    status = CharField(default="new")

    class Meta:
        database = db


class Listing(Model):
    id = CharField(primary_key=True)
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
    type = CharField()
    pages = IntegerField(default=1)

    class Meta:
        database = db
        primary_key = CompositeKey("site", "query", "type")


db.create_tables([Job, Listing, JobToListing, PageCount], safe=True)
