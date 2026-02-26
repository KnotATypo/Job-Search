import atexit
import os
from functools import wraps
from typing import List, Tuple

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify
from peewee import OperationalError
from waitress import serve

from job_search import util
from job_search.clean import clean
from job_search.create_summary import create_summary
from job_search.logger import logger, configure_logging
from job_search.model import Job, Listing, SearchQuery, User, BlacklistTerm, Location, SiteQuery, Site
from job_search.search import search
from job_search.sites.jora import Jora
from job_search.sites.linkedin import LinkedIn
from job_search.sites.seek import Seek

INVALID_REQUEST = "Invalid request"
JOB_NOT_FOUND = "Job not found or not yours."

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

scheduler = BackgroundScheduler(daemon=True)


def get_current_user():
    username = session.get("username")
    user_id = session.get("user_id")
    if not username and not user_id:
        return None
    return username, user_id


# Route to select/set username
@app.route("/set_username", methods=["GET", "POST"])
def set_username():
    usernames = [u.username for u in User.select().order_by(User.username)]
    if request.method == "POST":
        username = request.form.get("username")
        if username and username in usernames:
            session["username"] = username
            session["user_id"] = User.get(User.username == username).id
            flash(f"Username set to {username}")
            return redirect(url_for("index"))
        else:
            flash("Please select a valid username.")
    return render_template("set_username.html", usernames=usernames)


@app.route("/health_check")
def health_check():
    return jsonify({"status": "ok"})


def require_user(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not get_current_user():
            return redirect(url_for("set_username"))
        return f(*args, **kwargs)

    return decorated_function


@app.route("/")
@require_user
def index():
    """Main page with workflow stages"""
    username, user_id = get_current_user()
    triage_count = -1
    while triage_count < 0:
        try:
            triage_count = Job.select().where((Job.status == "new") & (Job.user == user_id)).count()
            reading_count = Job.select().where((Job.status == "interested") & (Job.user == user_id)).count()
            applying_count = Job.select().where((Job.status == "liked") & (Job.user == user_id)).count()
            applied_count = Job.select().where((Job.status == "applied") & (Job.user == user_id)).count()
        except OperationalError as e:
            logger.warn(f"Database error: {type(e).__name__} - {e}")

    return render_template(
        "index.html",
        triage_count=triage_count,
        reading_count=reading_count,
        applying_count=applying_count,
        applied_count=applied_count,
    )


@app.route("/triage")
@app.route("/triage/<job_id>")
@require_user
def triage(job_id=None):
    """Triage page for new jobs"""
    _, user_id = get_current_user()

    if job_id is None:
        jobs = list(Job.select().where((Job.status == "new") & (Job.user == user_id)))
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


@app.route("/triage/action", methods=["POST"])
def triage_action():
    """Handle triage actions (yes/no)"""
    job_id = request.form.get("job_id")
    action = request.form.get("action")

    if not job_id or not action:
        flash(INVALID_REQUEST)
        return redirect(url_for("triage"))

    job = Job.get_or_none((Job.id == job_id))

    if not job:
        flash(JOB_NOT_FOUND)
        return redirect(url_for("triage"))

    if action == "interested":
        job.status = "interested"
        job.save()
        flash(f"Marked '{job.title}' for further review")
    elif action == "not_interested":
        job.status = "not_interested"
        job.save()
        flash(f"Skipped '{job.title}'")

    return redirect(url_for("triage"))


@app.route("/reading_list")
@require_user
def reading_list():
    """Applied jobs page"""
    _, user_id = get_current_user()
    jobs = Job.select().where((Job.status == "interested") & (Job.user == user_id))

    return render_template("reading_list.html", jobs=jobs)


@app.route("/reading", defaults={"job_id": None})
@app.route("/reading/<job_id>")
@require_user
def reading(job_id):
    """Reading page for interested jobs"""
    _, user_id = get_current_user()

    if job_id is None:
        # Get the next job to read
        job = Job.select().where((Job.status == "interested") & (Job.user == user_id)).join(Listing).first()
    else:
        job = Job.select().where(Job.id == job_id).join(Listing).first()

    if not job or job is None:
        flash("Job not found!")
        return redirect(url_for("index"))

    listings, sites = get_site_links(job)

    return render_template("reading.html", job=job, listings=listings, sites=sites)


@app.route("/reading/action", methods=["POST"])
def reading_action():
    """Handle reading actions (like/dislike)"""
    job_id = request.form.get("job_id")
    action = request.form.get("action")

    if not job_id or not action:
        flash(INVALID_REQUEST)
        return redirect(url_for("reading"))

    job = Job.get_or_none((Job.id == job_id))

    if not job:
        flash(JOB_NOT_FOUND)
        return redirect(url_for("reading"))

    if action == "liked":
        job.status = "liked"
        job.save()
        flash(f"Marked '{job.title}' for application")
    elif action == "not_interested":
        job.status = "not_interested"
        job.save()
        flash(f"Marked '{job.title}' as not a good fit")

    return redirect(url_for("reading"))


@app.route("/applying")
@require_user
def applying():
    """Applying page for liked jobs"""
    _, user_id = get_current_user()
    # Get the next job to apply for
    job = Job.select().where((Job.status == "liked") & (Job.user == user_id)).first()

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
        if listing.site == "seek":
            sites.append(("Seek", Seek.get_url(listing.id)))
        elif listing.site == "jora":
            sites.append(("Jora", Jora.get_url(listing.id)))
        elif listing.site == "linkedin":
            sites.append(("LinkedIn", LinkedIn.get_url(listing.id)))

    return listings, sites


@app.route("/applying/action", methods=["POST"])
@require_user
def applying_action():
    """Handle applying actions (status update)"""
    job_id = request.form.get("job_id")
    status = request.form.get("status")

    if not job_id or not status:
        flash(INVALID_REQUEST)
        return redirect(url_for("applying"))

    job = Job.get_by_id(job_id)
    job.status = status
    job.save()
    if status == "applied":
        flash(f"Marked '{job.title}' as application submitted")
    elif status == "not_interested":
        flash(f"Marked '{job.title}' as not pursuing")

    return redirect(url_for("applying"))


@app.route("/search_queries", methods=["POST"])
@require_user
def add_search_query():
    term = request.form.get("term")
    if not term:
        return jsonify({"error": "No term provided"}), 400

    _, user_id = get_current_user()
    sq = SearchQuery.create(term=term, user=user_id)
    for site in list(Site.select()):
        # By default, enable query for all sites
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


@app.route("/manage_search_queries")
@require_user
def manage_search_queries():
    _, user_id = get_current_user()
    queries = list(SearchQuery.select().where(SearchQuery.user == user_id).order_by(SearchQuery.id))
    sites = list(Site.select())
    for query in queries:
        sites_to_query = [sq.site.id for sq in SiteQuery.select().where(SiteQuery.query == query.id)]
        query.sites = {
            site.id: {"value": "true" if site.id in sites_to_query else "false", "name": site.name} for site in sites
        }

    return render_template("manage_search_queries.html", queries=queries)


@app.route("/blacklist_terms", methods=["GET"])
@require_user
def get_blacklist_terms():
    _, user_id = get_current_user()
    requested_type = request.args.get("type")
    terms = [
        bt.term
        for bt in BlacklistTerm.select().where((BlacklistTerm.user == user_id) & (BlacklistTerm.type == requested_type))
    ]
    return jsonify(terms)


@app.route("/blacklist_terms", methods=["POST"])
@require_user
def add_blacklist_term():
    term = request.form.get("term")
    if not term:
        return jsonify({"error": "No term provided"}), 400
    _, user_id = get_current_user()
    try:
        term_type = request.args.get("type")
        BlacklistTerm.create(term=term, type=term_type, user=user_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/blacklist_terms/<term>", methods=["DELETE"])
@require_user
def delete_blacklist_term(term):
    _, user_id = get_current_user()
    requested_type = request.args.get("type")
    q = BlacklistTerm.delete().where(
        (BlacklistTerm.term == term) & (BlacklistTerm.user == user_id) & (BlacklistTerm.type == requested_type)
    )
    deleted = q.execute()
    return jsonify({"deleted": deleted})


@app.route("/manage_blacklist_terms")
def manage_blacklist_terms():
    return render_template("manage_blacklist_terms.html")


@app.route("/run_blacklist", methods=["POST"])
@require_user
def run_blacklist():
    username, user_id = get_current_user()

    new_jobs = Job.select().where((Job.status == "new") & (Job.user == user_id))
    filtered_count = 0
    for job in new_jobs:
        if util.apply_blacklist(job):
            filtered_count += 1

    return jsonify({"message": f"Blacklist run for {username}. {filtered_count} jobs filtered."})


@app.route("/applied")
@require_user
def applied():
    """Applied jobs page"""
    _, user_id = get_current_user()
    jobs = Job.select().where((Job.status == "applied") & (Job.user == user_id))

    jobs_with_sites = []
    for job in jobs:
        jobs_with_sites.append((job, get_site_links(job)[1]))

    return render_template("applied.html", jobs=jobs_with_sites)


@app.route("/complete_job", methods=["POST"])
def complete_job():
    job_id = request.form.get("job_id")
    job = Job.get_or_none((Job.id == job_id))
    if job:
        job.status = "complete"
        job.save()
        flash(f"Job '{job.title}' marked as complete and hidden.")
    else:
        flash(JOB_NOT_FOUND)
    return redirect(url_for("applied"))


def start():
    configure_logging()
    logger.info("Scheduling tasks")
    # TODO Make these configurable through .env or web gui
    scheduler.add_job(search, "cron", hour=22, minute=0)
    scheduler.add_job(create_summary, "cron", hour=0, minute=0)
    scheduler.add_job(clean, "cron", day="*/2", hour=0, minute=0)
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())
    logger.info("Tasks scheduled")

    logger.info("Starting Flask app")
    serve(app, host="0.0.0.0", port=3232)


if __name__ == "__main__":
    start()
