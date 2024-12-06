import json
import tkinter as tk
from time import sleep
from tkinter.font import Font
from typing import List

from model import Job


class TriageWindow:
    window: tk.Toplevel
    jobs: List[Job]
    font: Font
    index = 0
    title_label: tk.Label
    company_label: tk.Label

    def __init__(self, window: tk.Toplevel) -> None:
        self.jobs = Job.select()

        self.window = window
        self.font = Font(family="Calibri", size=20)

        max_width = 0
        for job in self.jobs:
            max_width = max(self.font.measure(job.title), max_width)
            max_width = max(self.font.measure(job.company), max_width)
        window.geometry(f"{max_width}x{max(int(max_width / 5), 300)}")

        job = self.jobs[0]

        frame_a = tk.Frame(master=window)
        frame_b = tk.Frame(master=window)
        self.title_label = tk.Label(master=frame_a, text=job.title, font=self.font)
        self.company_label = tk.Label(master=frame_b, text=job.company, font=self.font)
        self.title_label.pack(pady=30)
        self.company_label.pack()
        frame_a.pack()
        frame_b.pack()

        window.bind("n", self.no)
        window.bind("y", self.yes)
        window.bind("u", self.undo)

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
