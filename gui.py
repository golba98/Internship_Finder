import webbrowser
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from copy import deepcopy

from index import DEFAULT_CANDIDATE_PROFILE, InternshipFinder, build_profile_from_resume


class InternshipFinderGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("South African CS Internship Finder")
        self.geometry("960x720")
        self.minsize(820, 600)
        self.search_thread = None

        self._build_interface()
        self._prefill_profile()

    def _build_interface(self):
        self.columnconfigure(0, weight=1)
        header = ttk.Label(
            self,
            text="South African CS Internship Finder",
            font=("Segoe UI", 18, "bold"),
            anchor="center"
        )
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 6))

        content = ttk.Frame(self)
        content.grid(row=1, column=0, sticky="nsew", padx=12, pady=8)
        content.columnconfigure(0, weight=3)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(1, weight=1)

        profile_frame = ttk.LabelFrame(content, text="Candidate profile")
        profile_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=4)
        profile_frame.columnconfigure(0, weight=1)

        ttk.Label(profile_frame, text="Education").grid(row=0, column=0, sticky="w", pady=(8, 0))
        self.education_var = tk.StringVar()
        ttk.Entry(profile_frame, textvariable=self.education_var, width=60).grid(row=1, column=0, sticky="ew", padx=4)

        ttk.Label(profile_frame, text="Experience (brief summary)").grid(row=2, column=0, sticky="w", pady=(10, 0))
        self.experience_text = scrolledtext.ScrolledText(profile_frame, height=4, wrap=tk.WORD)
        self.experience_text.grid(row=3, column=0, sticky="ew", padx=4)

        ttk.Label(profile_frame, text="Skills (comma separated)").grid(row=4, column=0, sticky="w", pady=(10, 0))
        self.skills_text = scrolledtext.ScrolledText(profile_frame, height=4, wrap=tk.WORD)
        self.skills_text.grid(row=5, column=0, sticky="ew", padx=4)

        bottom_row = ttk.Frame(profile_frame)
        bottom_row.grid(row=6, column=0, sticky="ew", pady=10)
        bottom_row.columnconfigure(0, weight=1)
        bottom_row.columnconfigure(1, weight=1)

        ttk.Label(bottom_row, text="Location preference").grid(row=0, column=0, sticky="w")
        self.location_var = tk.StringVar()
        ttk.Entry(bottom_row, textvariable=self.location_var).grid(row=1, column=0, sticky="ew", padx=(0, 6))

        ttk.Label(bottom_row, text="Work preference").grid(row=0, column=1, sticky="w")
        self.work_pref_var = tk.StringVar()
        ttk.Combobox(
            bottom_row,
            textvariable=self.work_pref_var,
            values=["Any", "Remote", "Hybrid", "Onsite"],
            state="readonly"
        ).grid(row=1, column=1, sticky="ew")

        controls_frame = ttk.Frame(content)
        controls_frame.grid(row=0, column=1, sticky="nsew")
        controls_frame.columnconfigure(0, weight=1)

        self.run_button = ttk.Button(controls_frame, text="Find Internships", command=self.run_search)
        self.run_button.grid(row=0, column=0, sticky="ew", padx=4, pady=(8, 4))

        ttk.Button(controls_frame, text="Reset profile", command=self.reset_profile).grid(row=1, column=0, sticky="ew", padx=4, pady=4)
        ttk.Button(controls_frame, text="Clear results", command=self.clear_results).grid(row=2, column=0, sticky="ew", padx=4, pady=4)
        ttk.Button(controls_frame, text="Import resume", command=self._import_resume).grid(row=3, column=0, sticky="ew", padx=4, pady=4)

        self.progress = ttk.Progressbar(controls_frame, mode="indeterminate")
        self.progress.grid(row=4, column=0, sticky="ew", padx=4, pady=(4, 2))

        self.status_var = tk.StringVar(value="Ready to search")
        ttk.Label(controls_frame, textvariable=self.status_var, wraplength=200, justify="center").grid(row=5, column=0, sticky="ew", padx=4, pady=(6, 0))

        results_frame = ttk.LabelFrame(content, text="Search output")
        results_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(10, 4))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)

        self.results_text = scrolledtext.ScrolledText(results_frame, wrap=tk.WORD, state="disabled")
        self.results_text.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self.results_text.tag_configure("link", foreground="blue", underline=1)
        self.results_text.tag_bind("link", "<Enter>", lambda e: self.results_text.config(cursor="hand2"))
        self.results_text.tag_bind("link", "<Leave>", lambda e: self.results_text.config(cursor=""))
        self.results_text.tag_bind("link", "<Button-1>", self._open_link)
        self._link_targets = {}

    def _set_status(self, message):
        self.status_var.set(message)

    def _set_busy(self, busy):
        if busy:
            self.run_button.config(state="disabled")
            self.progress.start(10)
        else:
            self.run_button.config(state="normal")
            self.progress.stop()

    def _import_resume(self):
        path = filedialog.askopenfilename(
            title="Import resume text",
            filetypes=[("PDF files", "*.pdf"), ("Text files", "*.txt"), ("All files", "*")]
        )
        if not path:
            return

        self._set_status("📄 Parsing resume...")
        try:
            base_profile = self._collect_profile()
            imported = build_profile_from_resume(path, base_profile=base_profile)
            self.education_var.set(imported['education'])
            self.experience_text.delete("1.0", tk.END)
            self.experience_text.insert(tk.END, imported['experience'])
            self.skills_text.delete("1.0", tk.END)
            self.skills_text.insert(tk.END, ", ".join(imported['skills']))
            self.location_var.set(imported.get('location_preference', ""))
            self.work_pref_var.set(imported.get('work_preference', "Any"))
            self._set_status("✅ Resume imported")
        except Exception as exc:
            messagebox.showerror("Resume import failed", str(exc))
            self._set_status("❌ Resume import failed")

    def _prefill_profile(self):
        profile = deepcopy(DEFAULT_CANDIDATE_PROFILE)
        self.education_var.set(profile['education'])
        self.experience_text.delete("1.0", tk.END)
        self.experience_text.insert(tk.END, profile['experience'])
        self.skills_text.delete("1.0", tk.END)
        self.skills_text.insert(tk.END, ", ".join(profile['skills']))
        self.location_var.set(profile['location_preference'])
        self.work_pref_var.set(profile.get('work_preference', "Any"))

    def _collect_profile(self):
        skills_raw = self.skills_text.get("1.0", tk.END)
        skills = [skill.strip() for skill in skills_raw.split(',') if skill.strip()]
        experience = self.experience_text.get("1.0", tk.END).strip()

        return {
            'education': self.education_var.get().strip(),
            'skills': skills,
            'experience': experience,
            'location_preference': self.location_var.get().strip(),
            'work_preference': self.work_pref_var.get()
        }

    def run_search(self):
        if self.search_thread and self.search_thread.is_alive():
            return
        profile = self._collect_profile()
        self.clear_results()
        self._set_status("🔄 Running search...")
        self._set_busy(True)
        self.search_thread = threading.Thread(target=self._search_worker, args=(profile,), daemon=True)
        self.search_thread.start()

    def _search_worker(self, profile):
        try:
            finder = InternshipFinder(profile)
            finder.find_internships(verbose=False, apply_profile_filters=False, work_mode_filter=None)
            results = []
            for internship in finder.internships:
                evaluation = finder.evaluate_candidacy(internship)
                results.append((internship, evaluation))
            self.after(0, self._display_search_results, results)
        except Exception as exc:
            self.after(0, self._handle_search_error, exc)

    def _display_search_results(self, results):
        self._set_busy(False)
        count = len(results)
        self._set_status(f"✅ Found {count} internship{'s' if count != 1 else ''}")
        self.results_text.config(state="normal")
        if count == 0:
            self.results_text.insert(tk.END, "No internships found. Try again later.")
        else:
            for idx, (internship, evaluation) in enumerate(results, start=1):
                fit_status = "GOOD FIT" if evaluation['good_fit'] else "POTENTIAL FIT" if evaluation['match_score'] >= 30 else "LOW FIT"
                fit_icon = "🟢" if evaluation['good_fit'] else "🟡" if evaluation['match_score'] >= 30 else "🔴"
                lines = [
                    f"{idx}. {fit_icon} [{fit_status}] Match Score: {evaluation['match_score']}%",
                    f"   Company: {internship['company']}",
                    f"   Position: {internship['title']}",
                    f"   Location: {internship['location']}",
                    f"   Work Mode: {internship['remote_onsite']}",
                    f"   Description: {internship['description']}",
                    f"   Source: {internship['source']}",
                    "   Reasons:",
                ]
                for reason in evaluation['reasons']:
                    lines.append(f"      - {reason}")
                lines.append("\n")
                self.results_text.insert(tk.END, "\n".join(lines))
                if internship.get('link'):
                    self._insert_listing_link(internship['link'])
        self.results_text.config(state="disabled")

    def _insert_listing_link(self, url):
        prefix = "   Listing: "
        start = self.results_text.index(tk.END)
        self.results_text.insert(tk.END, f"{prefix}{url}\n")
        end = self.results_text.index(tk.END)
        link_tag = f"link_{len(self._link_targets)}"
        self._link_targets[link_tag] = url
        self.results_text.tag_add("link", start, end)
        self.results_text.tag_add(link_tag, start, end)

    def _open_link(self, event):
        tags = event.widget.tag_names("current")
        for tag in tags:
            if tag.startswith("link_") and tag in self._link_targets:
                webbrowser.open(self._link_targets[tag])
                return

    def _handle_search_error(self, exc):
        self._set_busy(False)
        self._set_status("❌ Search failed")
        messagebox.showerror("Search failed", str(exc))

    def clear_results(self):
        self.results_text.config(state="normal")
        self.results_text.delete("1.0", tk.END)
        self.results_text.config(state="disabled")
        self._link_targets.clear()
        self._set_status("Results cleared")

    def reset_profile(self):
        self._prefill_profile()
        self._set_status("Profile reset to defaults")


def main():
    app = InternshipFinderGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
