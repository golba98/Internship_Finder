South African CS Internship Finder

A Python project that aggregates Computer Science internship opportunities from multiple South African job boards, evaluates your fit, and surfaces clickable links so you can open any listing directly from the GUI.

Highlights
- Broad scraping: pulls CS internship listings from Careers24, PNet, LinkedIn, JobMail, CareerJunction, and Indeed South Africa.
- Candidate scoring: analyzes your education, skills, experience, location, and work-style preferences (defaults to Computer Science + South Africa + Remote) and provides a 0–100 percent match score with explanatory reasons.
- Resume import: PyPDF2 extracts keywords from a PDF or text resume to populate the GUI form automatically.
- GUI with clickable links: the Tkinter interface never prints to the terminal; it shows scrollable results and adds a clickable Listing URL for each internship.
- JSON snapshot: internships.json stores the combined data and evaluations every time you run the finder.
- Sample fallback data: curated sample internships appear if the scrapers temporarily return few or no listings.

Installation
Run the following command:
python -m pip install -r requirements.txt

Dependencies:
requests, beautifulsoup4, lxml, PyPDF2

CLI Edge Case (optional)
- The scraper uses the defaults in DEFAULT_CANDIDATE_PROFILE but you can customize that dictionary or pass your own profile to run_internship_search().
- Run python index.py if you want a quick terminal output plus the JSON dump. This mode is useful for automation or debugging, but the GUI offers a richer experience.

Recommended GUI Workflow
Run the following command:
python gui.py

- Fill out education, experience summary, comma-separated skills, location, and work preference.
- Click Find Internships to run the scraping and scoring pipeline.
- Every result block includes the company, title, location, work mode, description, scraping source, scoring reasons, and a clickable Listing line that opens in your default browser.
- Use Reset profile to restore the built-in defaults.
- Use Clear results to wipe the pane and remove stored link handlers.
- Use Import resume to pre-populate the form from a PDF or text file.

Extending the Finder
- Add more job board scrapers inside InternshipFinder.
- Adjust scoring logic in evaluate_candidacy() to change weights, add new keywords, or additional reasoning statements.
- Update DEFAULT_SKILL_KEYWORDS to match your ideal tech stack.

Privacy and Publishing Tips
- Avoid committing personal files such as resumes, secrets, or any local paths to version control.
- Add a LICENSE file to state how others may reuse your project.
- Mention in the README that the scrapers rely on external sites and that users should respect each site’s robots.txt and terms of service.

Notes
- Scraping fragile HTML structures may break after site redesigns.
- When regular sources return few hits, the tool falls back to a curated sample set.
- The GUI is meant for personal use and does not send any telemetry; everything stays local.
