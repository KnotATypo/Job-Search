import json
import tkinter as tk
from time import sleep
from tkinter.font import Font
from typing import List

from model import Job, JobToListing, Listing


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
        self.jobs = Job.select().where(Job.status == "new")

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
        self.next_job()

    def yes(self, arg):
        self.flash("#388659")
        self.next_job()

    def undo(self, arg):
        self.flash("#2081C3")

    def flash(self, colour: str) -> None:
        self.title_label.configure(fg=colour)
        self.company_label.configure(fg=colour)
        self.window.update()
        sleep(0.2)
        self.title_label.configure(fg="black")
        self.company_label.configure(fg="black")
        self.window.update()

    def next_job(self):
        self.index += 1
        self.title_label.configure(text=self.jobs[self.index].title)
        self.company_label.configure(text=self.jobs[self.index].company)
        self.summary_label.configure(text=self.summaries[self.index][0])
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

        with open("../config/config_fulltime.json", "r") as file:
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


def main():
    window = tk.Tk()
    App(window)
    window.mainloop()


if __name__ == "__main__":
    main()
