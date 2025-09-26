from peewee import (
    Model,
    AutoField,
    CharField,
    ForeignKeyField,
    IntegerField,
    CompositeKey,
    TextField,
    PostgresqlDatabase,
)


db = PostgresqlDatabase("job_search", user="josh", password="password", host="monitoring.lan")
db.connect()


class Job(Model):
    id = AutoField(primary_key=True)
    title = TextField()
    company = TextField()
    status = CharField(default="new")

    class Meta:
        database = db


class Listing(Model):
    id = CharField(primary_key=True)
    site = CharField()
    summary_path = TextField()

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


db.create_tables([Job, Listing, JobToListing, PageCount], safe=True)
