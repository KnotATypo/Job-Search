import json
import tkinter as tk
import webbrowser
from time import sleep
from tkinter.font import Font
from typing import List, Tuple

from model import Job, JobToListing, Listing
from sites.indeed import Indeed
from sites.jora import Jora
from sites.seek import Seek
from sites.site import Site


class TriageWindow:
    window: tk.Toplevel
    jobs: List[Job]
    font: Font
    index = 0
    title_label: tk.Label
    company_label: tk.Label
    summary_label: tk.Label
    summaries: List[List[str]]
    summary_index: int

    def __init__(self, window: tk.Toplevel) -> None:
        self.jobs = Job.select().where(Job.status == "new").execute()

        self.window = window
        self.font = Font(family="Calibri", size=20)
        self.summaries = []
        self.summary_index = 0

        max_width = 0
        for job in self.jobs:
            max_width = max(self.font.measure(job.title), max_width)
            max_width = max(self.font.measure(job.company), max_width)
        window.geometry(f"{max_width}x{max(int(max_width / 6), 300)}")

        for j in self.jobs:
            mapping = JobToListing.select(JobToListing).where(JobToListing.job_id == j.id).join(Listing).execute()
            summaries = []
            for map in mapping:
                summary = map.listing_id.summary
                if summary == "":
                    continue
                summaries.append(summary)
            self.summaries.append(summaries)

        job = self.jobs[0]
        summaries = self.summaries[0]

        title_frame = tk.Frame(master=window)
        company_frame = tk.Frame(master=window)
        summary_frame = tk.Frame(master=window)
        self.title_label = tk.Label(master=title_frame, text=job.title, font=self.font)
        self.company_label = tk.Label(master=company_frame, text=job.company, font=self.font)
        self.summary_label = tk.Label(
            master=summary_frame,
            text=summaries[0],
            font=Font(family="Calibri", size=15),
            wraplength=max_width - 150,
        )
        next_summary_button = tk.Button(master=summary_frame, text="Next", command=self.next_summary)
        self.title_label.pack(pady=15)
        self.company_label.pack(pady=15)
        self.summary_label.pack(pady=15)
        next_summary_button.pack(pady=15)
        title_frame.pack()
        company_frame.pack()
        summary_frame.pack()

        window.bind("n", self.no)
        window.bind("y", self.yes)
        window.bind("u", self.undo)
        window.bind("s", self.next_summary_arg)

    def no(self, arg):
        self.flash("#FE4A49")
        self.jobs[self.index].status = "not_interested"
        self.jobs[self.index].save()
        self.next_job()

    def yes(self, arg):
        self.flash("#388659")
        self.jobs[self.index].status = "interested"
        self.jobs[self.index].save()
        self.next_job()

    def undo(self, arg):
        self.flash("#2081C3")
        self.jobs[self.index - 1].status = "new"
        self.jobs[self.index - 1].save()

    def flash(self, colour: str) -> None:
        self.title_label.configure(fg=colour)
        self.company_label.configure(fg=colour)
        self.summary_label.configure(fg=colour)
        self.window.update()
        sleep(0.2)

    def next_job(self):
        self.index += 1
        if self.index >= len(self.jobs):
            self.window.destroy()
            return
        self.title_label.configure(text=self.jobs[self.index].title, fg="black")
        self.company_label.configure(text=self.jobs[self.index].company, fg="black")
        self.summary_label.configure(text=self.summaries[self.index][0], fg="black")
        self.window.update()

    def next_summary_arg(self, arg):
        self.next_summary()

    def next_summary(self):
        self.summary_index += 1
        if self.summary_index >= len(self.summaries[self.index]):
            self.summary_index = 0
        self.summary_label.configure(text=self.summaries[self.index][self.summary_index])
        self.window.update()


class ConfigWindow:
    window: tk.Toplevel
    font: Font

    def __init__(self, window: tk.Toplevel) -> None:
        self.window = window
        self.font = Font(family="Calibri", size=16)

        with open("../config/config.json", "r") as file:
            config = json.load(file)

        button_frame = tk.Frame(master=self.window)
        fulltime_button = tk.Button(button_frame, text="Full time", width=20, height=5)
        parttime_button = tk.Button(button_frame, text="Part time", width=20, height=5)
        fulltime_button.grid(row=0, column=0)
        parttime_button.grid(row=0, column=1)
        button_frame.pack()

        text = tk.Text(window, font=self.font)
        text.insert(tk.INSERT, json.dumps(config, indent=4))

        self.window.geometry("600x700")


class ReadingWindow:
    window: tk.Toplevel
    font: Font
    jobs: List[Tuple[Job, List[Listing]]]
    index: int
    tc_label: tk.Label
    seek_button: tk.Button
    jora_button: tk.Button
    indeed_button: tk.Button

    def __init__(self, window: tk.Toplevel) -> None:
        self.jobs = []
        jobs = Job.select(Job).where(Job.status == "interested").execute()
        for index, job in enumerate(jobs):
            job_id = job.id
            listings = JobToListing.select().where(JobToListing.job_id == job_id).join(Listing).execute()
            self.jobs.append((job, [l.listing_id for l in listings]))

        self.window = window
        self.font = Font(family="Calibri", size=20)
        self.window.geometry("500x400")

        self.index = -1

        heading_frame = tk.Frame(master=self.window)
        self.tc_label = tk.Label(master=heading_frame, font=self.font)
        self.tc_label.pack(pady=15)
        heading_frame.pack()

        listing_frame = tk.Frame(master=self.window)
        tk.Label(master=listing_frame, text="Listings", font=self.font).pack(pady=10)
        self.seek_button = tk.Button(
            master=listing_frame, text="Seek", font=self.font, command=lambda: self.open_link(Seek())
        )
        self.jora_button = tk.Button(
            master=listing_frame, text="Jora", font=self.font, command=lambda: self.open_link(Jora())
        )
        self.indeed_button = tk.Button(
            master=listing_frame, text="Indeed", font=self.font, command=lambda: self.open_link(Indeed())
        )
        listing_frame.pack()

        action_frame = tk.Frame(master=self.window)
        tk.Label(master=action_frame, text="Actions", font=self.font).pack(pady=10)
        tk.Button(master=action_frame, text="Like", font=self.font, command=self.like).pack(
            padx=10, pady=10, side="left"
        )
        tk.Button(master=action_frame, text="Dislike", font=self.font, command=self.dislike).pack(
            padx=10, pady=10, side="left"
        )
        action_frame.pack(padx=10, pady=10)

        self.next_job()

    def next_job(self):
        self.index += 1
        print(self.index, len(self.jobs))
        if self.index >= len(self.jobs):
            self.window.destroy()
            return
        job = self.jobs[self.index]
        self.tc_label.configure(text=f"{job[0].title}")

        sites = ["seek", "jora", "indeed"]
        for listing in job[1]:
            match listing.site:
                case "seek":
                    self.seek_button.pack(padx=10, pady=10, side="left")
                    sites.remove("seek")
                case "jora":
                    self.jora_button.pack(padx=10, pady=10, side="left")
                    sites.remove("jora")
                case "indeed":
                    self.indeed_button.pack(padx=10, pady=10, side="left")
                    sites.remove("indeed")

        for site in sites:
            match site:
                case "seek":
                    self.seek_button.pack_forget()
                case "jora":
                    self.jora_button.pack_forget()
                case "indeed":
                    self.indeed_button.pack_forget()

        self.window.update()

    def open_link(self, site: Site):
        listings = self.jobs[self.index][1]
        job_id = [l for l in listings if l.site == site.SITE_STRING][0].id
        link = site.build_job_link(job_id)
        webbrowser.open(link)

    def like(self):
        self.jobs[self.index][0].status = "liked"
        self.jobs[self.index][0].save()
        self.next_job()

    def dislike(self):
        self.jobs[self.index][0].status = "not_interested"
        self.jobs[self.index][0].save()
        self.next_job()


class ApplyingWindow:
    window: tk.Toplevel
    font: Font
    open_button: tk.Button
    job: Tuple[Job, List[Listing]]

    def __init__(self, window: tk.Toplevel):
        self.window = window
        self.font = Font(family="Calibri", size=20)
        self.get_job()

        self.open_button = tk.Button(master=self.window, text="Open", font=self.font, command=self.open)
        self.open_button.pack(padx=10, pady=10)

        tk.Label(master=self.window, text="Actions", font=self.font).pack(pady=10)
        action_frame = tk.Frame(master=self.window)
        tk.Button(master=action_frame, text="Applied", font=self.font, command=lambda: self.set_status("applied")).pack(
            padx=10, pady=10, side="left"
        )
        tk.Button(
            master=action_frame, text="Ignore", font=self.font, command=lambda: self.set_status("not_interested")
        ).pack(padx=10, pady=10, side="left")
        action_frame.pack(padx=10, pady=10)

    def set_status(self, status: str):
        self.job[0].status = status
        self.job[0].save()
        self.get_job()

    def get_job(self):
        query = Job.select(Job).where(Job.status == "liked").limit(1).execute()
        if len(query) == 0:
            self.window.destroy()
            return
        job = query[0]
        listings = JobToListing.select().where(JobToListing.job_id == job.id).join(Listing).execute()
        self.job = (job, [l.listing_id for l in listings])
        self.window.update()

    def open(self):
        for listing in self.job[1]:
            match listing.site:
                case "seek":
                    webbrowser.open(Seek().build_job_link(listing.id))
                case "jora":
                    webbrowser.open(Jora().build_job_link(listing.id))
                case "indeed":
                    webbrowser.open(Indeed().build_job_link(listing.id))


class App:
    window: tk.Tk
    font: Font

    def __init__(self, window: tk.Tk) -> None:
        self.window = window
        window.title("Job Search")

        self.font = Font(family="Calibri", size=20)

        triage_button = tk.Button(window, text="Triage", font=self.font, command=self.spawn_triage)
        triage_button.pack(padx=10, pady=10)

        config_button = tk.Button(window, text="Config", font=self.font, command=self.spawn_config)
        config_button.pack(padx=10, pady=10)

        reading_button = tk.Button(window, text="Reading", font=self.font, command=self.spawn_reading)
        reading_button.pack(padx=10, pady=10)

        reading_button = tk.Button(window, text="Applying", font=self.font, command=self.spawn_applying)
        reading_button.pack(padx=10, pady=10)

        window.geometry("400x350")

    def spawn_triage(self) -> None:
        child = tk.Toplevel(self.window)
        child.transient(self.window)
        child.title("Triage")
        TriageWindow(child)

    def spawn_config(self) -> None:
        child = tk.Toplevel(self.window)
        child.transient(self.window)
        child.title("Config")
        ConfigWindow(child)

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
