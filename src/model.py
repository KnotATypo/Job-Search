from peewee import (
    MySQLDatabase,
    Model,
    AutoField,
    CharField,
    ForeignKeyField,
    IntegerField,
    CompositeKey,
)

db = MySQLDatabase("job_search", user="dev", password="password", host="jobs.lan")
db.connect()


class Job(Model):
    id = AutoField(primary_key=True)
    title = CharField()
    company = CharField()
    type = CharField()
    status = CharField(default="new")

    class Meta:
        database = db


class Listing(Model):
    id = CharField(primary_key=True)
    site = CharField()
    summary = CharField()

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
