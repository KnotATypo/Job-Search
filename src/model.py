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
    username = CharField()  # New field for multi-user support

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
    term = CharField()  # Removed unique=True
    user = ForeignKeyField(User, backref="search_terms")  # Attach to user

    class Meta:
        database = db


class BlacklistTerm(Model):
    id = AutoField(primary_key=True)
    term = CharField()
    user = ForeignKeyField(User, backref="blacklist_terms")

    class Meta:
        database = db


db.create_tables([Job, Listing, JobToListing, PageCount, SearchTerm, BlacklistTerm, User], safe=True)
