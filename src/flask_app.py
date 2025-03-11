from flask import Flask, render_template, redirect, url_for, request, flash
from model import Job, JobToListing, Listing
from sites.indeed import Indeed
from sites.jora import Jora
from sites.linkedin import LinkedIn
from sites.seek import Seek
from sites.site import Site

app = Flask(__name__)
app.secret_key = 'job_search_secret_key'  # For flash messages

@app.route('/')
def index():
    """Main page with workflow stages"""
    # Count jobs in each stage
    triage_count = len(Job.select().where(Job.status == "new").execute())
    reading_count = len(Job.select().where(Job.status == "interested").execute())
    applying_count = len(Job.select().where(Job.status == "liked").execute())
    
    return render_template('index.html', 
                          triage_count=triage_count,
                          reading_count=reading_count,
                          applying_count=applying_count)

@app.route('/triage')
def triage():
    """Triage page for new jobs"""
    # Get the next job to triage
    job = Job.select().where(Job.status == "new").first()
    
    if not job:
        flash("No more jobs to triage!")
        return redirect(url_for('index'))
    
    # Get listings for this job
    listings = list(JobToListing.select().where(JobToListing.job_id == job.id).join(Listing).execute())
    
    return render_template('triage.html', job=job, listings=listings)

@app.route('/triage/action', methods=['POST'])
def triage_action():
    """Handle triage actions (yes/no/undo)"""
    job_id = request.form.get('job_id')
    action = request.form.get('action')
    
    if not job_id or not action:
        flash("Invalid request")
        return redirect(url_for('triage'))
    
    job = Job.get_by_id(job_id)
    
    if action == 'yes':
        job.status = 'interested'
        job.save()
        flash(f"Marked '{job.title}' as interested")
    elif action == 'no':
        job.status = 'not_interested'
        job.save()
        flash(f"Marked '{job.title}' as not interested")
    elif action == 'undo':
        # Get the most recently updated job that's not new
        prev_job = Job.select().where(Job.status != "new").order_by(Job.id.desc()).first()
        if prev_job:
            prev_job.status = 'new'
            prev_job.save()
            flash(f"Undid action for '{prev_job.title}'")
    
    return redirect(url_for('triage'))

@app.route('/reading')
def reading():
    """Reading page for interested jobs"""
    # Get the next job to read
    job = Job.select().where(Job.status == "interested").first()
    
    if not job:
        flash("No more jobs to read!")
        return redirect(url_for('index'))
    
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
    
    return render_template('reading.html', job=job, listings=listings, sites=sites)

@app.route('/reading/action', methods=['POST'])
def reading_action():
    """Handle reading actions (like/dislike)"""
    job_id = request.form.get('job_id')
    action = request.form.get('action')
    
    if not job_id or not action:
        flash("Invalid request")
        return redirect(url_for('reading'))
    
    job = Job.get_by_id(job_id)
    
    if action == 'like':
        job.status = 'liked'
        job.save()
        flash(f"Liked '{job.title}'")
    elif action == 'dislike':
        job.status = 'not_interested'
        job.save()
        flash(f"Disliked '{job.title}'")
    
    return redirect(url_for('reading'))

@app.route('/applying')
def applying():
    """Applying page for liked jobs"""
    # Get the next job to apply for
    job = Job.select().where(Job.status == "liked").first()
    
    if not job:
        flash("No more jobs to apply for!")
        return redirect(url_for('index'))
    
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
    
    return render_template('applying.html', job=job, listings=listings, sites=sites)

@app.route('/applying/action', methods=['POST'])
def applying_action():
    """Handle applying actions (status update)"""
    job_id = request.form.get('job_id')
    status = request.form.get('status')
    
    if not job_id or not status:
        flash("Invalid request")
        return redirect(url_for('applying'))
    
    job = Job.get_by_id(job_id)
    job.status = status
    job.save()
    flash(f"Updated status for '{job.title}' to {status}")
    
    return redirect(url_for('applying'))

if __name__ == '__main__':
    app.run(debug=True)