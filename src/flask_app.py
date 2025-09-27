from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify
from peewee import OperationalError
from waitress import serve

from model import Job, JobToListing, Listing, SearchTerm, User, BlacklistTerm
from sites.indeed import Indeed
from sites.jora import Jora
from sites.linkedin import LinkedIn
from sites.seek import Seek

app = Flask(__name__)
app.secret_key = "job_search_secret_key"  # For flash messages


# Helper to get current username from session
def get_current_username():
    username = session.get("username")
    if not username:
        return None
    return username


# Route to select/set username
@app.route("/set_username", methods=["GET", "POST"])
def set_username():
    usernames = [u.username for u in User.select().order_by(User.username)]
    if request.method == "POST":
        username = request.form.get("username")
        if username and username in usernames:
            session["username"] = username
            flash(f"Username set to {username}")
            return redirect(url_for("index"))
        else:
            flash("Please select a valid username.")
    return render_template("set_username.html", usernames=usernames)


# Decorator to require username selection
from functools import wraps


def require_username(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not get_current_username():
            return redirect(url_for("set_username"))
        return f(*args, **kwargs)

    return decorated_function


@app.route("/")
@require_username
def index():
    """Main page with workflow stages"""
    username = get_current_username()
    triage_count = -1
    while triage_count < 0:
        try:
            triage_count = Job.select().where((Job.status == "new") & (Job.username == username)).count()
            reading_count = Job.select().where((Job.status == "interested") & (Job.username == username)).count()
            applying_count = Job.select().where((Job.status == "liked") & (Job.username == username)).count()
        except OperationalError:
            print("Database error")

    return render_template(
        "index.html",
        triage_count=triage_count,
        reading_count=reading_count,
        applying_count=applying_count,
        username=username,
    )


@app.route("/triage")
@require_username
def triage():
    """Triage page for new jobs"""
    username = get_current_username()
    # Get the next job to triage
    job = Job.select().where((Job.status == "new") & (Job.username == username)).first()

    if not job:
        flash("No more jobs to triage!")
        return redirect(url_for("index"))

    # Get listings for this job
    listings = list(JobToListing.select().where(JobToListing.job_id == job.id).join(Listing).execute())

    return render_template("triage.html", job=job, listings=listings, username=username)


@app.route("/triage/action", methods=["POST"])
@require_username
def triage_action():
    """Handle triage actions (yes/no/undo)"""
    username = get_current_username()
    job_id = request.form.get("job_id")
    action = request.form.get("action")

    if not job_id or not action:
        flash("Invalid request")
        return redirect(url_for("triage"))

    job = Job.get_or_none((Job.id == job_id) & (Job.username == username))

    if not job:
        flash("Job not found or not yours.")
        return redirect(url_for("triage"))

    if action == "interested":
        job.status = "interested"
        job.save()
        flash(f"Marked '{job.title}' for further review")
    elif action == "not_interested":
        job.status = "not_interested"
        job.save()
        flash(f"Skipped '{job.title}'")
    elif action == "undo":
        # Get the most recently updated job that's not new
        prev_job = (
            Job.select().where((Job.status != "new") & (Job.username == username)).order_by(Job.id.desc()).first()
        )
        if prev_job:
            prev_job.status = "new"
            prev_job.save()
            flash(f"Undid action for '{prev_job.title}'")

    return redirect(url_for("triage"))


@app.route("/reading")
@require_username
def reading():
    """Reading page for interested jobs"""
    username = get_current_username()
    # Get the next job to read
    job = Job.select().where((Job.status == "interested") & (Job.username == username)).first()

    if not job:
        flash("No more jobs to read!")
        return redirect(url_for("index"))

    # Get listings for this job
    listings = list(JobToListing.select().where(JobToListing.job_id == job.id).join(Listing).execute())

    # Create site objects for links
    sites = []
    for listing in listings:
        if listing.listing_id.site == "seek":
            sites.append(("Seek", Seek.get_url(listing.listing_id.id)))
        elif listing.listing_id.site == "indeed":
            sites.append(("Indeed", Indeed.get_url(listing.listing_id.id)))
        elif listing.listing_id.site == "jora":
            sites.append(("Jora", Jora.get_url(listing.listing_id.id)))
        elif listing.listing_id.site == "linkedin":
            sites.append(("LinkedIn", LinkedIn.get_url(listing.listing_id.id)))

    return render_template("reading.html", job=job, listings=listings, sites=sites, username=username)


@app.route("/reading/action", methods=["POST"])
@require_username
def reading_action():
    """Handle reading actions (like/dislike)"""
    username = get_current_username()
    job_id = request.form.get("job_id")
    action = request.form.get("action")

    if not job_id or not action:
        flash("Invalid request")
        return redirect(url_for("reading"))

    job = Job.get_or_none((Job.id == job_id) & (Job.username == username))

    if not job:
        flash("Job not found or not yours.")
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
@require_username
def applying():
    """Applying page for liked jobs"""
    username = get_current_username()
    # Get the next job to apply for
    job = Job.select().where((Job.status == "liked") & (Job.username == username)).first()

    if not job:
        flash("No more jobs to apply for!")
        return redirect(url_for("index"))

    # Get listings for this job
    listings = list(JobToListing.select().where(JobToListing.job_id == job.id).join(Listing).execute())

    # Create site objects for links
    sites = []
    for listing in listings:
        if listing.listing_id.site == "seek":
            sites.append(("Seek", Seek.get_url(listing.listing_id.id)))
        elif listing.listing_id.site == "indeed":
            sites.append(("Indeed", Indeed.get_url(listing.listing_id.id)))
        elif listing.listing_id.site == "jora":
            sites.append(("Jora", Jora.get_url(listing.listing_id.id)))
        elif listing.listing_id.site == "linkedin":
            sites.append(("LinkedIn", LinkedIn.get_url(listing.listing_id.id)))

    return render_template("applying.html", job=job, listings=listings, sites=sites, username=username)


@app.route("/applying/action", methods=["POST"])
@require_username
def applying_action():
    """Handle applying actions (status update)"""
    username = get_current_username()
    job_id = request.form.get("job_id")
    status = request.form.get("status")

    if not job_id or not status:
        flash("Invalid request")
        return redirect(url_for("applying"))

    job = Job.get_by_id(job_id)
    job.status = status
    job.save()
    if status == "applied":
        flash(f"Marked '{job.title}' as application submitted")
    elif status == "not_interested":
        flash(f"Marked '{job.title}' as not pursuing")
    else:
        flash(f"Updated status for '{job.title}' to {status}")

    return redirect(url_for("applying"))


@app.route("/search_terms", methods=["GET"])
@require_username
def get_search_terms():
    username = get_current_username()
    user = User.get(User.username == username)
    terms = [st.term for st in SearchTerm.select().where(SearchTerm.user == user)]
    return jsonify(terms)


@app.route("/search_terms", methods=["POST"])
@require_username
def add_search_term():
    term = request.form.get("term")
    if not term:
        return jsonify({"error": "No term provided"}), 400
    username = get_current_username()
    user = User.get(User.username == username)
    try:
        SearchTerm.create(term=term, user=user)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/search_terms/<term>", methods=["DELETE"])
@require_username
def delete_search_term(term):
    username = get_current_username()
    user = User.get(User.username == username)
    q = SearchTerm.delete().where((SearchTerm.term == term) & (SearchTerm.user == user))
    deleted = q.execute()
    return jsonify({"deleted": deleted})


@app.route("/manage_search_terms")
@require_username
def manage_search_terms():
    return render_template("manage_search_terms.html")


@app.route("/blacklist_terms", methods=["GET"])
@require_username
def get_blacklist_terms():
    username = get_current_username()
    user = User.get(User.username == username)
    terms = [bt.term for bt in BlacklistTerm.select().where(BlacklistTerm.user == user)]
    return jsonify(terms)


@app.route("/blacklist_terms", methods=["POST"])
@require_username
def add_blacklist_term():
    term = request.form.get("term")
    if not term:
        return jsonify({"error": "No term provided"}), 400
    username = get_current_username()
    user = User.get(User.username == username)
    try:
        BlacklistTerm.create(term=term, user=user)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/blacklist_terms/<term>", methods=["DELETE"])
@require_username
def delete_blacklist_term(term):
    username = get_current_username()
    user = User.get(User.username == username)
    q = BlacklistTerm.delete().where((BlacklistTerm.term == term) & (BlacklistTerm.user == user))
    deleted = q.execute()
    return jsonify({"deleted": deleted})


@app.route("/manage_blacklist_terms")
@require_username
def manage_blacklist_terms():
    return render_template("manage_blacklist_terms.html")


if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=80)
