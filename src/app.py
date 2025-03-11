import tkinter as tk
import webbrowser
from time import sleep
from tkinter.font import Font
from typing import List, Tuple

from model import Job, JobToListing, Listing
from sites.indeed import Indeed
from sites.jora import Jora
from sites.linkedin import LinkedIn
from sites.seek import Seek
from sites.site import Site


class TriageWindow:
    window: tk.Toplevel
    jobs: List[Job]
    font: Font
    title_font: Font
    index = 0
    title_label: tk.Label
    company_label: tk.Label
    summary_label: tk.Label
    progress_label: tk.Label
    summaries: List[List[str]]
    summary_index: int
    status_label: tk.Label

    def __init__(self, window: tk.Toplevel) -> None:
        self.jobs = Job.select().where(Job.status == "new").execute()

        self.window = window
        self.font = Font(family="Calibri", size=18)
        self.title_font = Font(family="Calibri", size=22, weight="bold")
        self.summaries = []
        self.summary_index = 0

        # Configure window
        window.configure(bg="#f5f5f5")  # Light gray background
        window.title("Triage - Job Search")

        # Calculate window size
        max_width = 1000  # Set a reasonable default width
        window.geometry(f"{max_width}x800")  # Fixed height for better readability

        # Load summaries
        for j in self.jobs:
            mapping = JobToListing.select(JobToListing).where(JobToListing.job_id == j.id).join(Listing).execute()
            summaries = []
            for map in mapping:
                summary = map.listing_id.summary
                if summary == "":
                    continue
                summaries.append(summary)
            self.summaries.append(summaries)

        if len(self.jobs) == 0:
            self.window.destroy()
            return
        job = self.jobs[0]
        summaries = self.summaries[0]

        # Header with progress indicator
        header_frame = tk.Frame(master=window, bg="#388659", padx=10, pady=10)
        header_frame.pack(fill="x")

        header_label = tk.Label(master=header_frame, text="Triage Mode", font=self.title_font, bg="#388659", fg="white")
        header_label.pack(side="left", padx=10)

        self.progress_label = tk.Label(
            master=header_frame,
            text=f"Job 1 of {len(self.jobs)}",
            font=Font(family="Calibri", size=16),
            bg="#388659",
            fg="white",
        )
        self.progress_label.pack(side="right", padx=10)

        # Main content area
        content_frame = tk.Frame(master=window, bg="#f5f5f5", padx=20, pady=20)
        content_frame.pack(fill="both", expand=True)

        # Job title with border
        title_frame = tk.Frame(master=content_frame, bg="#f5f5f5", pady=10)
        title_frame.pack(fill="x")

        tk.Label(
            master=title_frame,
            text="Job Title:",
            font=Font(family="Calibri", size=14, weight="bold"),
            bg="#f5f5f5",
            fg="#555555",
        ).pack(anchor="w")

        self.title_label = tk.Label(
            master=title_frame,
            text=job.title if len(job.title) < 200 else job.title[:200].strip(),
            font=self.title_font,
            bg="#f5f5f5",
            fg="#2081C3",  # Blue color for title
            wraplength=max_width - 50,
            justify="left",
        )
        self.title_label.pack(anchor="w", pady=(5, 0))

        # Company name
        company_frame = tk.Frame(master=content_frame, bg="#f5f5f5", pady=10)
        company_frame.pack(fill="x")

        tk.Label(
            master=company_frame,
            text="Company:",
            font=Font(family="Calibri", size=14, weight="bold"),
            bg="#f5f5f5",
            fg="#555555",
        ).pack(anchor="w")

        self.company_label = tk.Label(
            master=company_frame,
            text=job.company,
            font=self.font,
            bg="#f5f5f5",
            fg="#333333",
            wraplength=max_width - 50,
            justify="left",
        )
        self.company_label.pack(anchor="w", pady=(5, 0))

        # Summary with border and scrollable area
        summary_frame = tk.Frame(master=content_frame, bg="#f5f5f5", pady=10)
        summary_frame.pack(fill="both", expand=True)

        tk.Label(
            master=summary_frame,
            text=f"Summary (1 of {len(summaries)}):",
            font=Font(family="Calibri", size=14, weight="bold"),
            bg="#f5f5f5",
            fg="#555555",
        ).pack(anchor="w")

        summary_container = tk.Frame(
            master=summary_frame, bg="white", highlightbackground="#dddddd", highlightthickness=1, padx=10, pady=10
        )
        summary_container.pack(fill="both", expand=True, pady=(5, 0))

        self.summary_label = tk.Label(
            master=summary_container,
            text=summaries[0],
            font=Font(family="Calibri", size=14),
            bg="white",
            fg="#333333",
            wraplength=max_width - 80,
            justify="left",
        )
        self.summary_label.pack(fill="both", expand=True, anchor="w")

        # Action buttons and keyboard shortcuts
        action_frame = tk.Frame(master=window, bg="#f0f0f0", padx=20, pady=15)
        action_frame.pack(fill="x")

        # Yes button (green)
        yes_button = tk.Button(
            master=action_frame,
            text="Interested (Y)",
            font=self.font,
            bg="#388659",  # Green
            fg="white",
            activebackground="#2D6A4F",
            activeforeground="white",
            command=lambda: self.yes(None),
            padx=10,
            pady=5,
            width=15,
        )
        yes_button.pack(side="left", padx=10)

        # No button (red)
        no_button = tk.Button(
            master=action_frame,
            text="Not Interested (N)",
            font=self.font,
            bg="#FE4A49",  # Red
            fg="white",
            activebackground="#D01C1F",
            activeforeground="white",
            command=lambda: self.no(None),
            padx=10,
            pady=5,
            width=15,
        )
        no_button.pack(side="right", padx=10)

        # Status bar for feedback
        status_frame = tk.Frame(master=window, bg="#e0e0e0", padx=10, pady=5)
        status_frame.pack(fill="x", side="bottom")

        self.status_label = tk.Label(
            master=status_frame,
            text="Keyboard shortcuts: Y = Interested, N = Not Interested, U = Undo, S = Next Summary",
            font=Font(family="Calibri", size=12),
            bg="#e0e0e0",
            fg="#555555",
        )
        self.status_label.pack(side="left")

        # Bind keyboard shortcuts
        window.bind("n", self.no)
        window.bind("y", self.yes)
        window.bind("u", self.undo)
        window.bind("s", self.next_summary)

    def no(self, arg):
        self.flash("#FE4A49")
        self.jobs[self.index].status = "not_interested"
        self.jobs[self.index].save()
        self.status_label.configure(text="Job marked as Not Interested")
        self.next_job()

    def yes(self, arg):
        self.flash("#388659")
        self.jobs[self.index].status = "interested"
        self.jobs[self.index].save()
        self.status_label.configure(text="Job marked as Interested")
        self.next_job()

    def undo(self, arg):
        if self.index > 0:
            self.flash("#2081C3")
            self.jobs[self.index - 1].status = "new"
            self.jobs[self.index - 1].save()
            self.index -= 2  # Go back two steps (one for the undo, one because next_job will increment)
            self.status_label.configure(text="Previous action undone")
            self.next_job()
        else:
            self.status_label.configure(text="Nothing to undo")

    def flash(self, colour: str) -> None:
        self.title_label.configure(fg=colour)
        self.company_label.configure(fg=colour)
        self.summary_label.configure(fg=colour)
        self.window.update()
        sleep(0.2)
        # Reset colors after flash
        self.title_label.configure(fg="#2081C3")
        self.company_label.configure(fg="#333333")
        self.summary_label.configure(fg="#333333")

    def next_job(self):
        self.index += 1
        self.summary_index = 0  # Reset summary index for new job

        if self.index >= len(self.jobs):
            self.status_label.configure(text="No more jobs to triage")
            sleep(1)  # Give user time to see the message
            self.window.destroy()
            return

        # Update progress indicator
        self.progress_label.configure(text=f"Job {self.index + 1} of {len(self.jobs)}")

        # Update job information
        title = self.jobs[self.index].title
        self.title_label.configure(text=title if len(title) < 200 else title[:200].strip())
        self.company_label.configure(text=self.jobs[self.index].company)

        # Update summary and its count
        summaries = self.summaries[self.index]
        summary_text = summaries[0] if summaries else "No summary available"
        self.summary_label.configure(text=summary_text)

        # Update summary count label
        summary_count = len(summaries)
        summary_label_text = f"Summary (1 of {summary_count}):" if summary_count > 0 else "Summary:"
        for widget in self.summary_label.master.master.winfo_children():
            if isinstance(widget, tk.Label) and widget != self.summary_label:
                widget.configure(text=summary_label_text)
                break

        # Reset status message
        self.status_label.configure(
            text="Keyboard shortcuts: Y = Interested, N = Not Interested, U = Undo, S = Next Summary"
        )

        self.window.update()

    def next_summary(self, arg):
        summaries = self.summaries[self.index]
        if not summaries:
            self.status_label.configure(text="No summaries available for this job")
            return

        self.summary_index += 1
        if self.summary_index >= len(summaries):
            self.summary_index = 0

        # Update summary text
        self.summary_label.configure(text=summaries[self.summary_index])

        # Update summary count label
        summary_count = len(summaries)
        summary_label_text = f"Summary ({self.summary_index + 1} of {summary_count}):"
        for widget in self.summary_label.master.master.winfo_children():
            if isinstance(widget, tk.Label) and widget != self.summary_label:
                widget.configure(text=summary_label_text)
                break

        self.status_label.configure(text=f"Showing summary {self.summary_index + 1} of {summary_count}")
        self.window.update()


class ReadingWindow:
    window: tk.Toplevel
    font: Font
    title_font: Font
    jobs: List[Tuple[Job, List[Listing]]]
    index: int
    title_label: tk.Label
    company_label: tk.Label
    progress_label: tk.Label
    seek_button: tk.Button
    jora_button: tk.Button
    indeed_button: tk.Button
    linkedin_button: tk.Button
    status_label: tk.Label

    def __init__(self, window: tk.Toplevel) -> None:
        self.jobs = []
        jobs = Job.select(Job).where(Job.status == "interested").execute()
        for index, job in enumerate(jobs):
            job_id = job.id
            listings = JobToListing.select().where(JobToListing.job_id == job_id).join(Listing).execute()
            self.jobs.append((job, [l.listing_id for l in listings]))

        self.window = window
        self.font = Font(family="Calibri", size=18)
        self.title_font = Font(family="Calibri", size=22, weight="bold")

        # Configure window
        window.configure(bg="#f5f5f5")  # Light gray background
        window.title("Reading - Job Search")
        window.geometry("700x750")  # Larger window for better readability

        self.index = -1

        # Header with progress indicator
        header_frame = tk.Frame(master=window, bg="#2081C3", padx=10, pady=10)  # Blue header
        header_frame.pack(fill="x")

        header_label = tk.Label(
            master=header_frame, text="Reading Mode", font=self.title_font, bg="#2081C3", fg="white"
        )
        header_label.pack(side="left", padx=10)

        self.progress_label = tk.Label(
            master=header_frame,
            text="",  # Will be set in next_job
            font=Font(family="Calibri", size=16),
            bg="#2081C3",
            fg="white",
        )
        self.progress_label.pack(side="right", padx=10)

        # Main content area
        content_frame = tk.Frame(master=window, bg="#f5f5f5", padx=20, pady=20)
        content_frame.pack(fill="both", expand=True)

        # Job title
        title_frame = tk.Frame(master=content_frame, bg="#f5f5f5", pady=10)
        title_frame.pack(fill="x")

        tk.Label(
            master=title_frame,
            text="Job Title:",
            font=Font(family="Calibri", size=14, weight="bold"),
            bg="#f5f5f5",
            fg="#555555",
        ).pack(anchor="w")

        self.title_label = tk.Label(
            master=title_frame,
            text="",  # Will be set in next_job
            font=self.title_font,
            bg="#f5f5f5",
            fg="#2081C3",  # Blue color for title
            wraplength=650,
            justify="left",
        )
        self.title_label.pack(anchor="w", pady=(5, 0))

        # Company name
        company_frame = tk.Frame(master=content_frame, bg="#f5f5f5", pady=10)
        company_frame.pack(fill="x")

        tk.Label(
            master=company_frame,
            text="Company:",
            font=Font(family="Calibri", size=14, weight="bold"),
            bg="#f5f5f5",
            fg="#555555",
        ).pack(anchor="w")

        self.company_label = tk.Label(
            master=company_frame,
            text="",  # Will be set in next_job
            font=self.font,
            bg="#f5f5f5",
            fg="#333333",
            wraplength=650,
            justify="left",
        )
        self.company_label.pack(anchor="w", pady=(5, 0))

        # Listings section with styled buttons
        listings_frame = tk.Frame(master=content_frame, bg="#f5f5f5", pady=15)
        listings_frame.pack(fill="x")

        tk.Label(
            master=listings_frame,
            text="View Job Listings:",
            font=Font(family="Calibri", size=14, weight="bold"),
            bg="#f5f5f5",
            fg="#555555",
        ).pack(anchor="w", pady=(0, 10))

        buttons_frame = tk.Frame(master=listings_frame, bg="#f5f5f5")
        buttons_frame.pack(fill="x")

        # Site buttons with distinctive colors
        self.seek_button = tk.Button(
            master=buttons_frame,
            text="Seek",
            font=self.font,
            command=lambda: self.open_link(Seek()),
            bg="#e60278",  # Seek pink
            fg="white",
            activebackground="#c00064",
            activeforeground="white",
            padx=15,
            pady=5,
        )

        self.jora_button = tk.Button(
            master=buttons_frame,
            text="Jora",
            font=self.font,
            command=lambda: self.open_link(Jora()),
            bg="#0d3880",  # Jora blue
            fg="white",
            activebackground="#092a60",
            activeforeground="white",
            padx=15,
            pady=5,
        )

        self.indeed_button = tk.Button(
            master=buttons_frame,
            text="Indeed",
            font=self.font,
            command=lambda: self.open_link(Indeed()),
            bg="#003a9b",  # Indeed blue
            fg="white",
            activebackground="#002c76",
            activeforeground="white",
            padx=15,
            pady=5,
        )

        self.linkedin_button = tk.Button(
            master=buttons_frame,
            text="LinkedIn",
            font=self.font,
            command=lambda: self.open_link(LinkedIn()),
            bg="#0077b5",  # LinkedIn blue
            fg="white",
            activebackground="#005e8c",
            activeforeground="white",
            padx=15,
            pady=5,
        )

        # Action buttons
        action_frame = tk.Frame(master=window, bg="#f0f0f0", padx=20, pady=15)
        action_frame.pack(fill="x")

        action_label = tk.Label(
            master=action_frame,
            text="Actions:",
            font=Font(family="Calibri", size=14, weight="bold"),
            bg="#f0f0f0",
            fg="#555555",
        )
        action_label.pack(anchor="w", pady=(0, 10))

        buttons_container = tk.Frame(master=action_frame, bg="#f0f0f0")
        buttons_container.pack(fill="x")

        # Like button (green)
        like_button = tk.Button(
            master=buttons_container,
            text="Like (L)",
            font=self.font,
            command=self.like,
            bg="#388659",  # Green
            fg="white",
            activebackground="#2D6A4F",
            activeforeground="white",
            padx=15,
            pady=5,
            width=12,
        )
        like_button.pack(side="left", padx=10)

        # Dislike button (red)
        dislike_button = tk.Button(
            master=buttons_container,
            text="Dislike (D)",
            font=self.font,
            command=self.dislike,
            bg="#FE4A49",  # Red
            fg="white",
            activebackground="#D01C1F",
            activeforeground="white",
            padx=15,
            pady=5,
            width=12,
        )
        dislike_button.pack(side="right", padx=10)

        # Status bar for feedback
        status_frame = tk.Frame(master=window, bg="#e0e0e0", padx=10, pady=5)
        status_frame.pack(fill="x", side="bottom")

        self.status_label = tk.Label(
            master=status_frame,
            text="Keyboard shortcuts: L = Like, D = Dislike",
            font=Font(family="Calibri", size=12),
            bg="#e0e0e0",
            fg="#555555",
        )
        self.status_label.pack(side="left")

        # Bind keyboard shortcuts
        window.bind("l", lambda e: self.like())
        window.bind("d", lambda e: self.dislike())

        self.next_job()

    def next_job(self):
        self.index += 1
        if self.index >= len(self.jobs):
            self.status_label.configure(text="No more jobs to review")
            sleep(1)  # Give user time to see the message
            self.window.destroy()
            return

        job = self.jobs[self.index]

        # Update progress indicator
        self.progress_label.configure(text=f"Job {self.index + 1} of {len(self.jobs)}")

        # Update job information
        title = job[0].title
        self.title_label.configure(text=title if len(title) < 200 else title[:200].strip())
        self.company_label.configure(text=job[0].company)

        # Reset status message
        self.status_label.configure(text="Keyboard shortcuts: L = Like, D = Dislike")

        # Handle job site buttons
        sites = ["seek", "jora", "indeed", "linkedin"]
        available_sites = []

        # First hide all buttons
        self.seek_button.pack_forget()
        self.jora_button.pack_forget()
        self.indeed_button.pack_forget()
        self.linkedin_button.pack_forget()

        # Then show only the available ones
        for listing in job[1]:
            match listing.site:
                case "seek":
                    self.seek_button.pack(padx=10, pady=10, side="left")
                    available_sites.append("Seek")
                    sites.remove("seek")
                case "jora":
                    self.jora_button.pack(padx=10, pady=10, side="left")
                    available_sites.append("Jora")
                    sites.remove("jora")
                case "indeed":
                    self.indeed_button.pack(padx=10, pady=10, side="left")
                    available_sites.append("Indeed")
                    sites.remove("indeed")
                case "linkedin":
                    self.linkedin_button.pack(padx=10, pady=10, side="left")
                    available_sites.append("LinkedIn")
                    sites.remove("linkedin")

        # Update status with available sites
        if available_sites:
            sites_text = ", ".join(available_sites)
            self.status_label.configure(text=f"Available on: {sites_text} | Keyboard shortcuts: L = Like, D = Dislike")

        self.window.update()

    def open_link(self, site: Site):
        try:
            listings = self.jobs[self.index][1]
            matching_listings = [l for l in listings if l.site == site.SITE_STRING]

            if not matching_listings:
                self.status_label.configure(text=f"No {site.SITE_STRING} listing available for this job")
                return

            job_id = matching_listings[0].id
            link = site.build_job_link(job_id)
            webbrowser.open(link)

            self.status_label.configure(text=f"Opening {site.SITE_STRING.capitalize()} listing in browser")
        except Exception as e:
            self.status_label.configure(text=f"Error opening link: {str(e)}")

    def like(self):
        try:
            self.jobs[self.index][0].status = "liked"
            self.jobs[self.index][0].save()

            # Flash green feedback
            self.title_label.configure(fg="#388659")  # Green
            self.window.update()
            sleep(0.2)
            self.title_label.configure(fg="#2081C3")  # Back to blue

            self.status_label.configure(text="Job marked for applying")
            self.next_job()
        except Exception as e:
            self.status_label.configure(text=f"Error: {str(e)}")

    def dislike(self):
        try:
            self.jobs[self.index][0].status = "not_interested"
            self.jobs[self.index][0].save()

            # Flash red feedback
            self.title_label.configure(fg="#FE4A49")  # Red
            self.window.update()
            sleep(0.2)
            self.title_label.configure(fg="#2081C3")  # Back to blue

            self.status_label.configure(text="Job marked as not interested")
            self.next_job()
        except Exception as e:
            self.status_label.configure(text=f"Error: {str(e)}")


class ApplyingWindow:
    window: tk.Toplevel
    font: Font
    title_font: Font
    title_label: tk.Label
    company_label: tk.Label
    site_buttons: dict
    job: Tuple[Job, List[Listing]]
    status_label: tk.Label
    job_count: int = 0

    def __init__(self, window: tk.Toplevel):
        self.window = window
        self.font = Font(family="Calibri", size=18)
        self.title_font = Font(family="Calibri", size=22, weight="bold")

        # Configure window
        window.configure(bg="#f5f5f5")  # Light gray background
        window.title("Applying - Job Search")
        window.geometry("700x550")  # Larger window for better readability

        # Count total jobs in this stage
        self.job_count = len(Job.select(Job).where(Job.status == "liked").execute())

        # Header with job count
        header_frame = tk.Frame(master=window, bg="#FE4A49", padx=10, pady=10)  # Red header
        header_frame.pack(fill="x")

        header_label = tk.Label(
            master=header_frame, text="Applying Mode", font=self.title_font, bg="#FE4A49", fg="white"
        )
        header_label.pack(side="left", padx=10)

        job_count_label = tk.Label(
            master=header_frame,
            text=f"Jobs to apply: {self.job_count}",
            font=Font(family="Calibri", size=16),
            bg="#FE4A49",
            fg="white",
        )
        job_count_label.pack(side="right", padx=10)

        # Main content area
        content_frame = tk.Frame(master=window, bg="#f5f5f5", padx=20, pady=20)
        content_frame.pack(fill="both", expand=True)

        # Job title
        title_frame = tk.Frame(master=content_frame, bg="#f5f5f5", pady=10)
        title_frame.pack(fill="x")

        tk.Label(
            master=title_frame,
            text="Job Title:",
            font=Font(family="Calibri", size=14, weight="bold"),
            bg="#f5f5f5",
            fg="#555555",
        ).pack(anchor="w")

        self.title_label = tk.Label(
            master=title_frame,
            text="",  # Will be set in get_job
            font=self.title_font,
            bg="#f5f5f5",
            fg="#2081C3",  # Blue color for title
            wraplength=650,
            justify="left",
        )
        self.title_label.pack(anchor="w", pady=(5, 0))

        # Company name
        company_frame = tk.Frame(master=content_frame, bg="#f5f5f5", pady=10)
        company_frame.pack(fill="x")

        tk.Label(
            master=company_frame,
            text="Company:",
            font=Font(family="Calibri", size=14, weight="bold"),
            bg="#f5f5f5",
            fg="#555555",
        ).pack(anchor="w")

        self.company_label = tk.Label(
            master=company_frame,
            text="",  # Will be set in get_job
            font=self.font,
            bg="#f5f5f5",
            fg="#333333",
            wraplength=650,
            justify="left",
        )
        self.company_label.pack(anchor="w", pady=(5, 0))

        # Job listings section
        listings_frame = tk.Frame(master=content_frame, bg="#f5f5f5", pady=15)
        listings_frame.pack(fill="x")

        tk.Label(
            master=listings_frame,
            text="Open Job Listings:",
            font=Font(family="Calibri", size=14, weight="bold"),
            bg="#f5f5f5",
            fg="#555555",
        ).pack(anchor="w", pady=(0, 10))

        # Container for site buttons
        self.site_buttons_frame = tk.Frame(master=listings_frame, bg="#f5f5f5")
        self.site_buttons_frame.pack(fill="x")

        # Create site buttons dictionary
        self.site_buttons = {
            "seek": tk.Button(
                master=self.site_buttons_frame,
                text="Seek",
                font=self.font,
                command=lambda: self.open_site("seek"),
                bg="#e60278",  # Seek pink
                fg="white",
                activebackground="#c00064",
                activeforeground="white",
                padx=15,
                pady=5,
            ),
            "jora": tk.Button(
                master=self.site_buttons_frame,
                text="Jora",
                font=self.font,
                command=lambda: self.open_site("jora"),
                bg="#0d3880",  # Jora blue
                fg="white",
                activebackground="#092a60",
                activeforeground="white",
                padx=15,
                pady=5,
            ),
            "indeed": tk.Button(
                master=self.site_buttons_frame,
                text="Indeed",
                font=self.font,
                command=lambda: self.open_site("indeed"),
                bg="#003a9b",  # Indeed blue
                fg="white",
                activebackground="#002c76",
                activeforeground="white",
                padx=15,
                pady=5,
            ),
            "linkedin": tk.Button(
                master=self.site_buttons_frame,
                text="LinkedIn",
                font=self.font,
                command=lambda: self.open_site("linkedin"),
                bg="#0077b5",  # LinkedIn blue
                fg="white",
                activebackground="#005e8c",
                activeforeground="white",
                padx=15,
                pady=5,
            ),
        }

        # Open all button
        open_all_button = tk.Button(
            master=listings_frame,
            text="Open All Listings",
            font=self.font,
            command=self.open,
            bg="#2081C3",  # Blue
            fg="white",
            activebackground="#0B5394",
            activeforeground="white",
            padx=15,
            pady=5,
            width=15,
        )
        open_all_button.pack(pady=15)

        # Action buttons
        action_frame = tk.Frame(master=window, bg="#f0f0f0", padx=20, pady=15)
        action_frame.pack(fill="x")

        action_label = tk.Label(
            master=action_frame,
            text="Application Status:",
            font=Font(family="Calibri", size=14, weight="bold"),
            bg="#f0f0f0",
            fg="#555555",
        )
        action_label.pack(anchor="w", pady=(0, 10))

        buttons_container = tk.Frame(master=action_frame, bg="#f0f0f0")
        buttons_container.pack(fill="x")

        # Applied button (green)
        applied_button = tk.Button(
            master=buttons_container,
            text="Applied (A)",
            font=self.font,
            command=lambda: self.set_status("applied"),
            bg="#388659",  # Green
            fg="white",
            activebackground="#2D6A4F",
            activeforeground="white",
            padx=15,
            pady=5,
            width=12,
        )
        applied_button.pack(side="left", padx=10)

        # Ignore button (red)
        ignore_button = tk.Button(
            master=buttons_container,
            text="Ignore (I)",
            font=self.font,
            command=lambda: self.set_status("not_interested"),
            bg="#FE4A49",  # Red
            fg="white",
            activebackground="#D01C1F",
            activeforeground="white",
            padx=15,
            pady=5,
            width=12,
        )
        ignore_button.pack(side="right", padx=10)

        # Status bar for feedback
        status_frame = tk.Frame(master=window, bg="#e0e0e0", padx=10, pady=5)
        status_frame.pack(fill="x", side="bottom")

        self.status_label = tk.Label(
            master=status_frame,
            text="Keyboard shortcuts: A = Applied, I = Ignore",
            font=Font(family="Calibri", size=12),
            bg="#e0e0e0",
            fg="#555555",
        )
        self.status_label.pack(side="left")

        # Bind keyboard shortcuts
        window.bind("a", lambda e: self.set_status("applied"))
        window.bind("i", lambda e: self.set_status("not_interested"))

        # Load the first job
        self.get_job()

    def set_status(self, status: str):
        try:
            if not hasattr(self, "job") or not self.job:
                self.status_label.configure(text="No job currently loaded")
                return

            self.job[0].status = status
            self.job[0].save()

            # Visual feedback
            if status == "applied":
                self.title_label.configure(fg="#388659")  # Green
                self.status_label.configure(text="Job marked as applied")
            else:
                self.title_label.configure(fg="#FE4A49")  # Red
                self.status_label.configure(text="Job marked as ignored")

            self.window.update()
            sleep(0.2)

            # Get next job
            self.get_job()
        except Exception as e:
            self.status_label.configure(text=f"Error: {str(e)}")

    def get_job(self):
        query = Job.select(Job).where(Job.status == "liked").limit(1).execute()
        if len(query) == 0:
            self.status_label.configure(text="No more jobs to apply for")
            sleep(1)  # Give user time to see the message
            self.window.destroy()
            return

        job = query[0]
        listings = JobToListing.select().where(JobToListing.job_id == job.id).join(Listing).execute()
        self.job = (job, [l.listing_id for l in listings])

        # Update job information
        title = job.title
        self.title_label.configure(text=title if len(title) < 200 else title[:200].strip(), fg="#2081C3")
        self.company_label.configure(text=job.company)

        # Update site buttons
        for button in self.site_buttons.values():
            button.pack_forget()

        available_sites = []
        for listing in self.job[1]:
            site = listing.site
            if site in self.site_buttons:
                self.site_buttons[site].pack(padx=10, pady=10, side="left")
                available_sites.append(site.capitalize())

        # Update status with available sites
        if available_sites:
            sites_text = ", ".join(available_sites)
            self.status_label.configure(
                text=f"Available on: {sites_text} | Keyboard shortcuts: A = Applied, I = Ignore"
            )
        else:
            self.status_label.configure(text="No job listings available | Keyboard shortcuts: A = Applied, I = Ignore")

    def open_site(self, site_name: str):
        """Open a specific job site listing"""
        try:
            if not hasattr(self, "job") or not self.job:
                self.status_label.configure(text="No job currently loaded")
                return

            listings = self.job[1]
            matching_listings = [l for l in listings if l.site == site_name]

            if not matching_listings:
                self.status_label.configure(text=f"No {site_name} listing available for this job")
                return

            job_id = matching_listings[0].id

            # Get the appropriate site class
            site_class = None
            match site_name:
                case "seek":
                    site_class = Seek()
                case "jora":
                    site_class = Jora()
                case "indeed":
                    site_class = Indeed()
                case "linkedin":
                    site_class = LinkedIn()

            if site_class:
                link = site_class.build_job_link(job_id)
                webbrowser.open(link)
                self.status_label.configure(text=f"Opening {site_name.capitalize()} listing in browser")
            else:
                self.status_label.configure(text=f"Unknown site: {site_name}")

        except Exception as e:
            self.status_label.configure(text=f"Error opening link: {str(e)}")

    def open(self):
        """Open all available job listings"""
        try:
            if not hasattr(self, "job") or not self.job:
                self.status_label.configure(text="No job currently loaded")
                return

            opened_count = 0
            for listing in self.job[1]:
                site_name = listing.site
                if site_name in ["seek", "jora", "indeed", "linkedin"]:
                    self.open_site(site_name)
                    opened_count += 1
                    sleep(0.5)  # Small delay between opening tabs

            if opened_count > 0:
                self.status_label.configure(text=f"Opened {opened_count} job listings in browser")
            else:
                self.status_label.configure(text="No job listings available to open")

        except Exception as e:
            self.status_label.configure(text=f"Error opening links: {str(e)}")


class App:
    window: tk.Tk
    font: Font
    title_font: Font
    active_window: str = None

    def __init__(self, window: tk.Tk) -> None:
        self.window = window
        window.title("Job Search")
        window.configure(bg="#f0f0f0")  # Light gray background

        self.font = Font(family="Calibri", size=20)
        self.title_font = Font(family="Calibri", size=24, weight="bold")

        # Title label
        title_frame = tk.Frame(window, bg="#f0f0f0")
        title_label = tk.Label(
            title_frame, text="Job Search", font=self.title_font, bg="#f0f0f0", fg="#2081C3"  # Blue color for title
        )
        title_label.pack(pady=20)
        title_frame.pack(fill="x")

        # Workflow stages frame
        workflow_frame = tk.Frame(window, bg="#f0f0f0")
        workflow_label = tk.Label(
            workflow_frame, text="Workflow Stages:", font=Font(family="Calibri", size=16, weight="bold"), bg="#f0f0f0"
        )
        workflow_label.pack(anchor="w", padx=20, pady=(10, 5))
        workflow_frame.pack(fill="x")

        # Buttons frame with better styling
        buttons_frame = tk.Frame(window, bg="#f0f0f0")

        # Count jobs in each stage
        triage_count = len(Job.select().where(Job.status == "new").execute())
        reading_count = len(Job.select().where(Job.status == "interested").execute())
        applying_count = len(Job.select().where(Job.status == "liked").execute())

        # Triage button with count
        triage_button = tk.Button(
            buttons_frame,
            text=f"Triage ({triage_count})",
            font=self.font,
            command=self.spawn_triage,
            bg="#388659",  # Green
            fg="white",
            activebackground="#2D6A4F",
            activeforeground="white",
            relief=tk.RAISED,
            borderwidth=2,
            padx=10,
            width=15,
        )
        triage_button.pack(padx=20, pady=10, fill="x")

        # Reading button with count
        reading_button = tk.Button(
            buttons_frame,
            text=f"Reading ({reading_count})",
            font=self.font,
            command=self.spawn_reading,
            bg="#2081C3",  # Blue
            fg="white",
            activebackground="#0B5394",
            activeforeground="white",
            relief=tk.RAISED,
            borderwidth=2,
            padx=10,
            width=15,
        )
        reading_button.pack(padx=20, pady=10, fill="x")

        # Applying button with count
        applying_button = tk.Button(
            buttons_frame,
            text=f"Applying ({applying_count})",
            font=self.font,
            command=self.spawn_applying,
            bg="#FE4A49",  # Red
            fg="white",
            activebackground="#D01C1F",
            activeforeground="white",
            relief=tk.RAISED,
            borderwidth=2,
            padx=10,
            width=15,
        )
        applying_button.pack(padx=20, pady=10, fill="x")

        buttons_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Help text
        help_frame = tk.Frame(window, bg="#f0f0f0")
        help_text = "Select a workflow stage to begin"
        help_label = tk.Label(
            help_frame, text=help_text, font=Font(family="Calibri", size=12, slant="italic"), bg="#f0f0f0", fg="#555555"
        )
        help_label.pack(pady=10)
        help_frame.pack(fill="x")

        window.geometry("450x500")

    def spawn_triage(self) -> None:
        child = tk.Toplevel(self.window)
        child.transient(self.window)
        child.title("Triage")
        TriageWindow(child)

    def spawn_reading(self) -> None:
        child = tk.Toplevel(self.window)
        child.transient(self.window)
        child.title("Reading")
        ReadingWindow(child)

    def spawn_applying(self) -> None:
        child = tk.Toplevel(self.window)
        child.transient(self.window)
        child.title("Applying")
        ApplyingWindow(child)


def main():
    window = tk.Tk()
    App(window)
    window.mainloop()


if __name__ == "__main__":
    main()
