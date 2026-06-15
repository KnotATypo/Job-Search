import atexit
import datetime
import os
import re
from functools import wraps
from typing import List, Tuple

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify
from waitress import serve

from job_search.base_site import BaseSite
from job_search.model import (
    Job,
    Listing,
    SearchQuery,
    User,
    BlacklistTerm,
    Location,
    SiteQuery,
    Site,
    JobStatus,
    db,
    Status,
)
from job_search.search import search
from job_search.utilities.auto_apply import run_applier, notify_user
from job_search.utilities.clean import clean
from job_search.utilities.job_util import pass_blacklist
from job_search.utilities.logger import logger, configure_logging

INVALID_REQUEST = "Invalid request"
JOB_NOT_FOUND = "Job not found or not yours."

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

scheduler = BackgroundScheduler(daemon=True)


@app.route("/set_user", methods=["GET", "POST"])
def set_user():
    if "user_id" in session:
        del session["user_id"]
        del session["username"]

    usernames = [u.username for u in User.select().order_by(User.username)]
    if request.method == "POST":
        username = request.form.get("username")
        if username and username in usernames:
            session["username"] = username
            session["user_id"] = User.get(User.username == username).id
            flash(f"User set to {username}")
            return redirect(url_for("index"))
        else:
            flash("Please select a valid username.")
    return render_template("set_user.html", usernames=usernames)


@app.route("/health_check", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"})


def require_user(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("set_user"))
        return f(*args, **kwargs)

    return decorated_function


@app.route("/", methods=["GET"])
@require_user
def index():
    """Main page with workflow stages"""
    user_id = session["user_id"]

    triage_count = JobStatus.select().where((JobStatus.status == Status.NEW) & (JobStatus.user == user_id)).count()
    reading_count = (
        JobStatus.select().where((JobStatus.status == Status.INTERESTED) & (JobStatus.user == user_id)).count()
    )
    applying_count = JobStatus.select().where((JobStatus.status == Status.LIKED) & (JobStatus.user == user_id)).count()
    applied_count = JobStatus.select().where((JobStatus.status == Status.APPLIED) & (JobStatus.user == user_id)).count()

    return render_template(
        "index.html",
        triage_count=triage_count,
        reading_count=reading_count,
        applying_count=applying_count,
        applied_count=applied_count,
    )


@app.route("/triage", methods=["GET"])
@app.route("/triage/<job_id>", methods=["GET"])
@require_user
def triage(job_id=None):
    """Triage page for new jobs"""

    if job_id is None:
        jobs = list(
            Job.select()
            .join(JobStatus)
            .where((JobStatus.status == Status.NEW) & (JobStatus.user == session["user_id"]))
        )
        if len(jobs) == 0:
            return redirect(url_for("index"))
        return redirect(url_for("triage", job_id=jobs[0].id))

    # Get the next job to triage
    job = Job.get(Job.id == job_id)

    if not job:
        flash("No more jobs to triage!")
        return redirect(url_for("index"))

    # Get listings for this job
    listings = list(Listing.select().where(Listing.job == job))

    return render_template("triage.html", job=job, listings=listings)


@app.route("/update_status", methods=["POST"])
@require_user
def update_status():
    """Handle triage actions (yes/no)"""

    job_id = request.form.get("job_id")
    new_status = request.form.get("status")
    redirect_page = request.form.get("redirect_page")

    if not job_id or new_status not in [
        "New",
        "Interested",
        "Not Interested",
        "Liked",
        "Applied",
        "Complete",
        "Blacklist",
    ]:
        flash(INVALID_REQUEST)
        return redirect(url_for("index"))

    job = Job.get_or_none((Job.id == job_id))

    if not job:
        flash(JOB_NOT_FOUND)
        return redirect(url_for("index"))

    JobStatus.update(status=Status(new_status)).where(
        (JobStatus.user == session["user_id"]) & (JobStatus.job == job_id)
    ).execute()

    flash(f"Marked '{job.title}' as {new_status}")

    return redirect(url_for(redirect_page if redirect_page is not None else "index"))


@app.route("/reading_list", methods=["GET"])
@require_user
def reading_list():
    """Applied jobs page"""
    jobs = (
        Job.select()
        .join(JobStatus)
        .where((JobStatus.status == Status.INTERESTED) & (JobStatus.user == session["user_id"]))
    )

    return render_template("reading_list.html", jobs=jobs)


@app.route("/reading", defaults={"job_id": None}, methods=["GET"])
@app.route("/reading/<job_id>", methods=["GET"])
@require_user
def reading(job_id):
    """Reading page for interested jobs"""

    if job_id is None:
        # Get the next job to read
        jobs = list(
            Job.select()
            .join(JobStatus)
            .where((JobStatus.status == Status.INTERESTED) & (JobStatus.user == session["user_id"]))
        )
        if len(jobs) == 0:
            return redirect(url_for("index"))
        return redirect(url_for("reading", job_id=jobs[0].id))

    job = Job.select().where(Job.id == job_id).join(Listing).first()

    if not job or job is None:
        flash("Job not found!")
        return redirect(url_for("index"))

    listings, sites = get_site_links(job)

    return render_template("reading.html", job=job, listings=listings, sites=sites)


@app.route("/applying", methods=["GET"])
@require_user
def applying():
    """Applying page for liked jobs"""
    # Get the next job to apply for
    job = (
        Job.select()
        .join(JobStatus)
        .where((JobStatus.status == Status.LIKED) & (JobStatus.user == session["user_id"]))
        .first()
    )

    if not job:
        flash("No more jobs to apply for!")
        return redirect(url_for("index"))

    listings, sites = get_site_links(job)

    return render_template("applying.html", job=job, listings=listings, sites=sites)


def get_site_links(job: Job) -> Tuple[List[Listing], List[Tuple[str, str]]]:
    """Generate site links for a job"""

    listings = list(Listing.select().where(Listing.job == job))
    sites = []
    for listing in listings:
        site_instance = BaseSite.get_site_instance(listing.site.name)
        sites.append((listing.site.name, site_instance.build_listing_link(listing.id)))

    return listings, sites


@app.route("/search_queries", methods=["POST"])
@require_user
def add_search_query():
    term = request.form.get("term")
    if not term:
        return jsonify({"error": "No term provided"}), 400

    auto_apply = True if request.form.get("auto_apply") else False

    sq = SearchQuery.create(
        term=term, user=session["user_id"], auto_apply=auto_apply, days_since_post=2 if auto_apply else 0
    )
    if auto_apply:
        # Only enable Seek for auto-apply jobs
        SiteQuery.create(site="seek", query=sq.id)
    else:
        # Otherwise, enable query for all sites
        for site in Site.select():
            SiteQuery.create(site=site.id, query=sq.id)

    return jsonify({"success": True})


@app.route("/search_queries/<query_id>", methods=["DELETE"])
def delete_search_query(query_id):
    sq = SearchQuery.get(SearchQuery.id == query_id)
    sq.delete_instance(recursive=True)
    return jsonify({"success": True})


@app.route("/search_queries/<query_id>", methods=["PATCH"])
def update_search_query(query_id):
    data = request.get_json()
    remote = data["remote"]
    location = data["location"]
    sites = data["sites"]

    st = SearchQuery.get_or_none((SearchQuery.id == query_id))
    st.remote = remote
    st.location = Location(location)
    st.save()

    for site, value in sites.items():
        site_query = SiteQuery.get_or_none(SiteQuery.site == site, SiteQuery.query == query_id)
        if site_query is None and value:
            SiteQuery.create(site=site, query=query_id)
        elif site_query is not None and not value:
            site_query.delete_instance()

    return jsonify({"success": True})


@app.route("/manage_search_queries", methods=["GET"])
@require_user
def manage_search_queries():
    queries = list(
        SearchQuery.select()
        .where(SearchQuery.user == session["user_id"], SearchQuery.auto_apply == False)
        .order_by(SearchQuery.id)
    )
    queries = add_sites(queries)

    return render_template("manage_search_queries.html", queries=queries)


@app.route("/blacklist_terms", methods=["GET"])
@require_user
def get_blacklist_terms():
    requested_type = request.args.get("type")
    terms = [
        bt.term
        for bt in BlacklistTerm.select().where(
            (BlacklistTerm.user == session["user_id"]) & (BlacklistTerm.type == requested_type)
        )
    ]
    return jsonify(terms)


@app.route("/blacklist_terms", methods=["POST"])
@require_user
def add_blacklist_term():
    term = request.form.get("term")
    if not term:
        return jsonify({"error": "No term provided"}), 400
    try:
        term_type = request.args.get("type")
        BlacklistTerm.create(term=term, type=term_type, user=session["user_id"])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/blacklist_terms/<term>", methods=["DELETE"])
@require_user
def delete_blacklist_term(term):
    requested_type = request.args.get("type")
    q = BlacklistTerm.delete().where(
        (BlacklistTerm.term == term)
        & (BlacklistTerm.user == session["user_id"])
        & (BlacklistTerm.type == requested_type)
    )
    deleted = q.execute()
    return jsonify({"deleted": deleted})


@app.route("/manage_blacklist_terms", methods=["GET"])
@require_user
def manage_blacklist_terms():
    return render_template("manage_blacklist_terms.html")


@app.route("/run_blacklist", methods=["POST"])
@require_user
def run_blacklist():
    user_id = session["user_id"]

    new_statuses = JobStatus.select().where((JobStatus.user == user_id) & (JobStatus.status == Status.NEW))
    filtered_count = 0
    for status in new_statuses:
        if not pass_blacklist(status.job, user_id):
            status.status = Status.BLACKLIST
            status.save()
            filtered_count += 1

    return jsonify({"message": f"Blacklist run. {filtered_count} jobs filtered."})


@app.route("/applied", methods=["GET", "POST"])
@require_user
def applied():
    """Get applied jobs"""
    if request.method == "POST":
        term = request.form.get("search-job-field", "")
        auto_applied = request.form.get("auto-applied")

        status_to_match = Status.AUTO_APPLIED if auto_applied == "true" else Status.APPLIED
        jobs = set(
            Job.select()
            .join(JobStatus)
            .where(
                (JobStatus.status == status_to_match)
                & (JobStatus.user == session["user_id"])
                & ((Job.title.ilike("%" + term + "%")) | (Job.company.ilike("%" + term + "%")))
            )
        )

    else:
        jobs = (
            Job.select()
            .join(JobStatus)
            .where((JobStatus.status == Status.APPLIED), (JobStatus.user == session["user_id"]))
        )

    jobs_with_sites = []
    for job in jobs:
        jobs_with_sites.append((job, get_site_links(job)[1]))

    return render_template("applied.html", jobs=jobs_with_sites)


@app.route("/auto_applier_setup", methods=["POST"])
@require_user
def auto_applier_setup():
    user = User.get(User.id == session["user_id"])
    errors = {}

    email_address = request.form.get("email", "")
    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email_address):
        errors["email"] = "Invalid email address."
    elif "@gmail.com" not in email_address:
        errors["email"] = "Only Gmail addresses are currently supported."

    password = request.form.get("password", "")
    if not re.match(r"(?:[a-z]{4} ){3}[a-z]{4}", password):
        errors["password"] = "Password should be 4 sets of 4 lowercase letters."

    webhook = request.form.get("webhook", "")
    if not re.match(r"https://discord\.com/api/webhooks/\d+/\w+", webhook):
        errors["webhook"] = "Invalid webhook URL."

    if len(errors) > 0:
        return render_template(
            "applier_setup.html",
            errors=errors,
            values={"email": email_address, "password": password, "webhook": webhook},
        )
    else:
        user.email = email_address
        user.email_password = password
        user.webhook_url = webhook
        user.save()
        return redirect(url_for("auto_applier_terms"))


@app.route("/auto_applier_terms", methods=["GET", "POST"])
@require_user
def auto_applier_terms():
    user = User.get(User.id == session["user_id"])
    if not user.email:
        return render_template("applier_setup.html", errors={}, values={})
    else:
        queries = list(
            SearchQuery.select()
            .where(SearchQuery.user == user, SearchQuery.auto_apply == True)
            .order_by(SearchQuery.id)
        )
        queries = add_sites(queries)
        return render_template("applier_terms.html", queries=queries)


def add_sites(queries: list[SearchQuery]) -> list[SearchQuery]:
    sites = list(Site.select())
    for query in queries:
        sites_to_query = [sq.site.id for sq in SiteQuery.select().where(SiteQuery.query == query.id)]
        query.sites = {
            site.id: {"value": "true" if site.id in sites_to_query else "false", "name": site.name} for site in sites
        }
    return queries


@app.before_request
def _db_connect():
    if db.is_closed():
        db.connect()


@app.teardown_request
def _db_close(_):
    if not db.is_closed():
        db.close()


def run_tasks():
    with db:
        search()
        clean()


def run_apply():
    with db:
        users = User.select().where(User.email.is_null(False))
        for user in users:
            run_applier(user)


def run_apply_notify():
    with db:
        users = User.select().where(User.webhook_url.is_null(False))
        for user in users:
            notify_user(user, datetime.datetime.now() - datetime.timedelta(hours=24))


def start():
    configure_logging()
    logger.info("Scheduling tasks")
    # TODO Make this configurable through .env or web gui
    scheduler.add_job(run_tasks, "cron", hour=1, minute=0)
    scheduler.add_job(run_apply, trigger="cron", hour="*", minute="0")
    scheduler.add_job(run_apply_notify, trigger="cron", hour="10", minute="0")
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())
    logger.info("Tasks scheduled")

    logger.info("Starting Flask app")
    serve(app, host="0.0.0.0", port=3232)


if __name__ == "__main__":
    start()
