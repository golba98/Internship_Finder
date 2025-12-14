import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re
from copy import deepcopy
from pathlib import Path
from urllib.parse import urljoin
from PyPDF2 import PdfReader


DEFAULT_CANDIDATE_PROFILE = {
    'education': 'Computer Science degree/diploma',
    'skills': [
        'Python', 'JavaScript', 'Java', 'SQL',
        'HTML', 'CSS', 'Git', 'React', 'Node.js'
    ],
    'experience': 'Some programming projects and coursework',
    'location_preference': 'South Africa',
    'work_preference': 'Remote'
}

DEFAULT_SKILL_KEYWORDS = {
    'python', 'javascript', 'java', 'sql', 'html', 'css', 'git', 'react',
    'node', 'c++', 'c#', 'aws', 'docker', 'angular', 'vue', 'typescript',
    'kubernetes', 'azure', 'rest', 'graphql', 'django', 'flask'
}

DEGREE_KEYWORDS = [
    'computer science', 'software engineering', 'information technology',
    'informatics', 'data science', 'engineering', 'computer engineering'
]

LOCATION_KEYWORDS = [
    'cape town', 'johannesburg', 'durban', 'pretoria', 'south africa'
]

def get_default_candidate_profile():
    """Return a copy of the default profile so callers can modify it safely."""
    return deepcopy(DEFAULT_CANDIDATE_PROFILE)


def _extract_text_from_resume(path):
    path = Path(path)
    if path.suffix.lower() == '.pdf':
        reader = PdfReader(str(path))
        return '\n'.join(page.extract_text() or '' for page in reader.pages)
    return path.read_text(encoding='utf-8', errors='ignore')


def _infer_degree(text):
    lower = text.lower()
    for degree in DEGREE_KEYWORDS:
        if degree in lower:
            return degree.title()
    return None


def _infer_location(text):
    lower = text.lower()
    for location in LOCATION_KEYWORDS:
        if location in lower:
            return location.title()
    return None


def _infer_skills(text):
    text_lower = text.lower()
    return sorted({skill for skill in DEFAULT_SKILL_KEYWORDS if skill in text_lower})


def _infer_experience(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    lower = [line.lower() for line in lines]
    for keyword in ['experience', 'projects', 'work history', 'role']:
        for idx, line in enumerate(lower):
            if keyword in line:
                snippet = ' '.join(lines[idx:idx + 3])
                return snippet[:400]
    return ' '.join(lines[:5])[:400]


def build_profile_from_resume(resume_path, *, base_profile=None):
    """Use resume text to populate or update a candidate profile."""
    profile = get_default_candidate_profile()
    if base_profile:
        profile.update(base_profile)
    resume_text = _extract_text_from_resume(resume_path)
    if not resume_text:
        raise ValueError("Resume did not contain extractable text")

    inferred_skills = _infer_skills(resume_text)
    if inferred_skills:
        profile['skills'] = inferred_skills

    inferred_degree = _infer_degree(resume_text)
    if inferred_degree:
        profile['education'] = inferred_degree

    inferred_location = _infer_location(resume_text)
    if inferred_location:
        profile['location_preference'] = inferred_location

    inferred_experience = _infer_experience(resume_text)
    if inferred_experience:
        profile['experience'] = inferred_experience

    return profile


def run_internship_search(candidate_profile=None, *, verbose=True):
    """Run the finder with the provided profile and return the finder instance."""
    profile = candidate_profile or get_default_candidate_profile()
    finder = InternshipFinder(profile)
    finder.find_internships(verbose=verbose)
    return finder


class InternshipFinder:
    def __init__(self, candidate_profile):
        """
        Initialize the internship finder with candidate profile
        
        Args:
            candidate_profile: dict with keys like 'skills', 'education', 'experience'
        """
        self.candidate_profile = candidate_profile
        self.internships = []
        
    def scrape_pnet(self, verbose=True):
        """Scrape PNet for South African CS internships"""
        if verbose:
            print("🔍 Scraping PNet...")
        try:
            # PNet internship search URL for Computer Science
            url = "https://www.pnet.co.za/jobs/computer-science-internship-results.html"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find job listings (adjust selectors based on actual site structure)
            job_cards = soup.find_all('div', class_='job-card') or soup.find_all('article', class_='job')
            
            for job in job_cards[:10]:  # Limit to first 10
                try:
                    title_elem = job.find('h2') or job.find('h3') or job.find('a', class_='job-title')
                    company_elem = job.find(class_=re.compile('company|employer'))
                    desc_elem = job.find(class_=re.compile('description|summary'))
                    location_elem = job.find(class_=re.compile('location'))
                    
                    link_elem = job.find('a', href=True)
                    href = link_elem['href'] if link_elem else ''
                    if href and not href.startswith('http'):
                        href = urljoin('https://www.pnet.co.za', href)
                    if title_elem:
                        internship = {
                            'company': company_elem.text.strip() if company_elem else 'Company not listed',
                            'title': title_elem.text.strip(),
                            'description': desc_elem.text.strip()[:200] if desc_elem else 'No description',
                            'location': location_elem.text.strip() if location_elem else 'South Africa',
                            'remote_onsite': self._determine_work_mode(
                                title_elem.text + (desc_elem.text if desc_elem else '')
                            ),
                            'source': 'PNet',
                            'link': href or 'https://www.pnet.co.za'
                        }
                        self.internships.append(internship)
                except Exception as e:
                    continue
                    
        except Exception as e:
            if verbose:
                print(f"❌ Error scraping PNet: {e}")
    
    def scrape_careers24(self, verbose=True):
        """Scrape Careers24 for South African CS internships"""
        if verbose:
            print("🔍 Scraping Careers24...")
        try:
            url = "https://www.careers24.com/jobs/internships/information-technology"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find job listings
            job_cards = soup.find_all('div', class_=re.compile('job|listing'))
            
            for job in job_cards[:10]:
                try:
                    title_elem = job.find('h2') or job.find('h3') or job.find('a')
                    company_elem = job.find(class_=re.compile('company'))
                    desc_elem = job.find(class_=re.compile('desc'))
                    
                    if title_elem and 'intern' in title_elem.text.lower():
                        link_elem = job.find('a', href=True)
                        href = link_elem['href'] if link_elem else ''
                        if href and not href.startswith('http'):
                            href = urljoin('https://www.careers24.com', href)
                        internship = {
                            'company': company_elem.text.strip() if company_elem else 'Company not listed',
                            'title': title_elem.text.strip(),
                            'description': desc_elem.text.strip()[:200] if desc_elem else 'No description',
                            'location': 'South Africa',
                            'remote_onsite': self._determine_work_mode(
                                title_elem.text + (desc_elem.text if desc_elem else '')
                            ),
                            'source': 'Careers24',
                            'link': href or 'https://www.careers24.com'
                        }
                        self.internships.append(internship)
                except Exception as e:
                    continue
                    
        except Exception as e:
            if verbose:
                print(f"❌ Error scraping Careers24: {e}")
    
    def scrape_linkedin_jobs(self, verbose=True):
        """Scrape LinkedIn for South African CS internships"""
        if verbose:
            print("🔍 Searching LinkedIn Jobs...")
        try:
            # LinkedIn job search URL
            url = "https://www.linkedin.com/jobs/search/?keywords=computer%20science%20internship&location=South%20Africa"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # LinkedIn often requires authentication, so this is a basic attempt
            job_cards = soup.find_all('div', class_=re.compile('job'))
            
            for job in job_cards[:10]:
                try:
                    title_elem = job.find('h3') or job.find('a')
                    company_elem = job.find('h4') or job.find(class_=re.compile('company'))
                    
                    if title_elem:
                        internship = {
                            'company': company_elem.text.strip() if company_elem else 'Company not listed',
                            'title': title_elem.text.strip(),
                            'description': 'Check LinkedIn for full details',
                            'location': 'South Africa',
                            'remote_onsite': self._determine_work_mode(title_elem.text),
                            'source': 'LinkedIn'
                        }
                        self.internships.append(internship)
                except Exception as e:
                    continue
                    
        except Exception as e:
            if verbose:
                print(f"❌ Error scraping LinkedIn: {e}")

    def scrape_jobmail(self, verbose=True):
        """Scrape JobMail for South African CS internships"""
        if verbose:
            print("🔍 Scraping JobMail...")
        try:
            url = "https://www.jobmail.co.za/jobs/computer-science-internship"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')

            job_cards = soup.find_all(
                ['article', 'div', 'li'],
                class_=re.compile('job|listing|result', re.IGNORECASE)
            )

            for job in job_cards[:12]:
                try:
                    title_elem = job.find('h2') or job.find('h3') or job.find('a')
                    company_elem = job.find(class_=re.compile('company|employer', re.IGNORECASE))
                    desc_elem = job.find(class_=re.compile('summary|desc|details', re.IGNORECASE))
                    location_elem = job.find(class_=re.compile('location|place|city', re.IGNORECASE))
                    link_elem = job if job.name == 'a' and job.has_attr('href') else job.find('a', href=True)
                    href = link_elem['href'] if link_elem else ''
                    if href and not href.startswith('http'):
                        href = urljoin(url, href)

                    if title_elem:
                        internship = {
                            'company': company_elem.text.strip() if company_elem else 'Company not listed',
                            'title': title_elem.text.strip(),
                            'description': desc_elem.text.strip()[:200] if desc_elem else 'Check JobMail for details',
                            'location': location_elem.text.strip() if location_elem else 'South Africa',
                            'remote_onsite': self._determine_work_mode(
                                title_elem.text + (desc_elem.text if desc_elem else '')
                            ),
                            'source': 'JobMail',
                            'link': href or url
                        }
                        self.internships.append(internship)
                except Exception:
                    continue
        except Exception as e:
            if verbose:
                print(f"❌ Error scraping JobMail: {e}")

    def scrape_careerjunction(self, verbose=True):
        """Scrape CareerJunction for South African internships"""
        if verbose:
            print("🔍 Scraping CareerJunction...")
        try:
            url = "https://www.careerjunction.co.za/jobs/computer-science-internship"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')

            job_cards = soup.find_all(
                ['article', 'div', 'li'],
                class_=re.compile('job|listing|result', re.IGNORECASE)
            )

            for job in job_cards[:12]:
                try:
                    title_elem = job.find('h2') or job.find('h3') or job.find('a')
                    company_elem = job.find(class_=re.compile('company|employer', re.IGNORECASE))
                    desc_elem = job.find(class_=re.compile('summary|desc|blurb', re.IGNORECASE))
                    location_elem = job.find(class_=re.compile('location|city', re.IGNORECASE))
                    link_elem = job if job.name == 'a' and job.has_attr('href') else job.find('a', href=True)
                    href = link_elem['href'] if link_elem else ''
                    if href and not href.startswith('http'):
                        href = urljoin(url, href)

                    if title_elem:
                        internship = {
                            'company': company_elem.text.strip() if company_elem else 'Company not listed',
                            'title': title_elem.text.strip(),
                            'description': desc_elem.text.strip()[:200] if desc_elem else 'Check CareerJunction for details',
                            'location': location_elem.text.strip() if location_elem else 'South Africa',
                            'remote_onsite': self._determine_work_mode(
                                title_elem.text + (desc_elem.text if desc_elem else '')
                            ),
                            'source': 'CareerJunction',
                            'link': href or url
                        }
                        self.internships.append(internship)
                except Exception:
                    continue
        except Exception as e:
            if verbose:
                print(f"❌ Error scraping CareerJunction: {e}")

    def scrape_indeed(self, verbose=True):
        """Scrape Indeed South Africa for CS internships"""
        if verbose:
            print("🔍 Scraping Indeed ZA...")
        try:
            url = "https://za.indeed.com/jobs?q=computer+science+internship&l=South+Africa"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')

            job_cards = soup.select('a.tapItem, div.job_seen_beacon')

            for job in job_cards[:12]:
                try:
                    title_elem = job.find('h2') or job.find('span', class_=re.compile('jobTitle')) or job.find('a')
                    company_elem = job.find(class_=re.compile('companyName')) or job.find('span', class_=re.compile('company'))
                    desc_elem = job.find('div', class_=re.compile('job-snippet|summary', re.IGNORECASE))
                    location_elem = job.find('div', class_=re.compile('companyLocation'))
                    link_elem = job if job.name == 'a' and job.has_attr('href') else job.find('a', href=True)
                    href = link_elem['href'] if link_elem else ''
                    if href and not href.startswith('http'):
                        href = urljoin('https://za.indeed.com', href)

                    if title_elem:
                        internship = {
                            'company': company_elem.text.strip() if company_elem else 'Company not listed',
                            'title': title_elem.text.strip(),
                            'description': desc_elem.text.strip()[:200] if desc_elem else 'See Indeed listing',
                            'location': location_elem.text.strip() if location_elem else 'South Africa',
                            'remote_onsite': self._determine_work_mode(
                                title_elem.text + (desc_elem.text if desc_elem else '')
                            ),
                            'source': 'Indeed ZA',
                            'link': href or url
                        }
                        self.internships.append(internship)
                except Exception:
                    continue
        except Exception as e:
            if verbose:
                print(f"❌ Error scraping Indeed ZA: {e}")
    
    def add_sample_internships(self, verbose=True):
        """Add sample internships for demonstration (in case scraping doesn't work)"""
        if verbose:
            print("📝 Adding sample internships...")
        samples = [
            {
                'company': 'Standard Bank',
                'title': 'Software Development Internship',
                'description': 'Looking for Computer Science students to join our digital team. Work on Java, Python, and cloud technologies.',
                'location': 'Johannesburg, Gauteng',
                'remote_onsite': 'Hybrid',
                'source': 'Sample'
            },
            {
                'company': 'Naspers/Prosus',
                'title': 'Data Science Internship Programme',
                'description': 'Join our data science team working on machine learning and analytics projects. Python, SQL, and data visualization required.',
                'location': 'Cape Town, Western Cape',
                'remote_onsite': 'Onsite',
                'source': 'Sample'
            },
            {
                'company': 'Takealot',
                'title': 'Full Stack Development Intern',
                'description': 'Work with React, Node.js, and AWS. Build e-commerce features and learn from experienced developers.',
                'location': 'Cape Town, Western Cape',
                'remote_onsite': 'Hybrid',
                'source': 'Sample'
            },
            {
                'company': 'Allan Gray',
                'title': 'IT Internship - Software Engineering',
                'description': 'Financial services company seeking CS graduates. C#, .NET, SQL Server experience preferred.',
                'location': 'Cape Town, Western Cape',
                'remote_onsite': 'Onsite',
                'source': 'Sample'
            },
            {
                'company': 'Discovery',
                'title': 'Graduate Software Developer Programme',
                'description': 'Health and insurance company looking for developers. Angular, Java, microservices architecture.',
                'location': 'Sandton, Gauteng',
                'remote_onsite': 'Hybrid',
                'source': 'Sample'
            },
            {
                'company': 'BBD',
                'title': 'Junior Developer Internship',
                'description': 'Custom software development company. Work on various client projects using modern tech stack.',
                'location': 'Multiple locations',
                'remote_onsite': 'Hybrid',
                'source': 'Sample'
            },
            {
                'company': 'Amazon Web Services',
                'title': 'Cloud Support Internship',
                'description': 'Remote internship supporting AWS customers. Learn cloud technologies and customer service.',
                'location': 'South Africa',
                'remote_onsite': 'Remote',
                'source': 'Sample'
            }
        ]
        self.internships.extend(samples)
    
    def _determine_work_mode(self, text):
        """Determine if the job is remote, onsite, or hybrid"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['remote', 'work from home', 'wfh']):
            return 'Remote'
        elif any(word in text_lower for word in ['hybrid', 'flexible']):
            return 'Hybrid'
        else:
            return 'Onsite'
    
    def evaluate_candidacy(self, internship):
        """
        Evaluate if the candidate is a good fit for the internship
        
        Returns:
            dict: {'match_score': int (0-100), 'reason': str, 'good_fit': bool}
        """
        score = 0
        reasons = []
        
        # Get candidate skills and education
        candidate_skills = set(skill.lower() for skill in self.candidate_profile.get('skills', []))
        education = self.candidate_profile.get('education', '').lower()
        experience = self.candidate_profile.get('experience', '').lower()
        
        # Combine internship text for analysis
        job_text = (internship['title'] + ' ' + internship['description']).lower()
        
        # Check for education match (CS degree/diploma)
        if 'computer science' in education or 'software' in education or 'information technology' in education:
            score += 30
            reasons.append("✅ Relevant educational background")
        else:
            reasons.append("⚠️ Education background unclear")
        
        # Check for skill matches
        common_skills = ['python', 'java', 'javascript', 'react', 'sql', 'c++', 'c#', 
                        'html', 'css', 'git', 'docker', 'aws', 'node', 'angular']
        
        matched_skills = []
        for skill in common_skills:
            if skill in job_text and skill in candidate_skills:
                matched_skills.append(skill)
        
        if matched_skills:
            score += min(30, len(matched_skills) * 10)
            reasons.append(f"✅ Skills match: {', '.join(matched_skills)}")
        else:
            # Check if any candidate skills match
            for skill in candidate_skills:
                if skill in job_text and len(skill) > 2:  # Avoid short matches
                    matched_skills.append(skill)
            
            if matched_skills:
                score += 20
                reasons.append(f"✅ Some skills match: {', '.join(matched_skills[:3])}")
            else:
                reasons.append("⚠️ No direct skill matches found")
        
        # Location preference
        location_pref = self.candidate_profile.get('location_preference', '').lower()
        if location_pref:
            if location_pref in internship['location'].lower():
                score += 10
                reasons.append("✅ Preferred location")
        
        # Remote preference
        work_pref = self.candidate_profile.get('work_preference', '').lower()
        if work_pref:
            if work_pref in internship['remote_onsite'].lower():
                score += 10
                reasons.append("✅ Preferred work mode")
        
        # Experience level check
        if 'experience' in self.candidate_profile and self.candidate_profile['experience']:
            score += 10
            reasons.append("✅ Has relevant experience")
        
        # Enthusiasm bonus (if they have CS background, give them a chance!)
        if score < 40 and ('computer' in education or 'software' in education):
            score += 20
            reasons.append("✅ Strong potential for learning")
        
        good_fit = score >= 50
        
        return {
            'match_score': min(score, 100),
            'reasons': reasons,
            'good_fit': good_fit
        }
    
    def find_internships(self, *, verbose=True, work_mode_filter='Remote', apply_profile_filters=False):
        """Main method to find all internships.

        Args:
            verbose (bool): print progress to console when True
            work_mode_filter (str|None): if provided, only keep internships where
                the `remote_onsite` field contains this string (case-insensitive).
                Default is 'Remote' to return only remote roles.
        """
        if verbose:
            print("\n" + "="*60)
            print("🎓 SOUTH AFRICAN CS INTERNSHIP FINDER")
            print("="*60 + "\n")
        
        # Try scraping various sites
        self.scrape_pnet(verbose=verbose)
        self.scrape_careers24(verbose=verbose)
        self.scrape_linkedin_jobs(verbose=verbose)
        self.scrape_jobmail(verbose=verbose)
        self.scrape_careerjunction(verbose=verbose)
        self.scrape_indeed(verbose=verbose)
        
        # Add samples if scraping yielded few results
        if len(self.internships) < 5:
            self.add_sample_internships(verbose=verbose)
        
        # Remove duplicates based on title and company
        seen = set()
        unique_internships = []
        for internship in self.internships:
            key = (internship['company'].lower(), internship['title'].lower())
            if key not in seen:
                seen.add(key)
                unique_internships.append(internship)
        
        # Apply location/work preference filters from the candidate profile
        filtered = unique_internships
        if apply_profile_filters:
            location_pref = self.candidate_profile.get('location_preference', '').strip().lower()
            work_pref = self.candidate_profile.get('work_preference', '').strip().lower()
            if location_pref:
                filtered = [i for i in filtered if location_pref in i.get('location', '').lower()]

            def matches_work_mode(entry, pref):
                mode = entry.get('remote_onsite', '').lower()
                text = (entry.get('title', '') + ' ' + entry.get('description', '')).lower()
                return pref in mode or pref in text

            if work_pref and work_pref != 'any':
                filtered = [i for i in filtered if matches_work_mode(i, work_pref)]

        # If filtering removed all internships, fall back to the broader list so the GUI still shows something
        if not filtered and unique_internships:
            filtered = unique_internships

        # Apply explicit filter argument (e.g., Remote) if requested
        if work_mode_filter:
            wm = work_mode_filter.lower()
            if wm == 'remote':
                # Treat Hybrid as acceptable for remote searches and also check title/description for remote mentions
                def is_remote_like(i):
                    mode = i.get('remote_onsite', '').lower()
                    text = (i.get('title', '') + ' ' + i.get('description', '')).lower()
                    return ('remote' in mode) or ('hybrid' in mode) or ('remote' in text)

                filtered = [i for i in filtered if is_remote_like(i)]
            else:
                filtered = [i for i in filtered if wm in i.get('remote_onsite', '').lower()]
            self.internships = filtered
        else:
            self.internships = filtered

        if verbose:
            print(f"\n✅ Found {len(self.internships)} internship opportunities!\n")
        
        return self.internships
    
    def display_results(self):
        """Display internships with candidacy evaluation"""
        if not self.internships:
            print("❌ No internships found. Try again later.")
            return
        
        print("\n" + "="*60)
        print("📊 INTERNSHIP OPPORTUNITIES & YOUR FIT")
        print("="*60 + "\n")
        
        for idx, internship in enumerate(self.internships, 1):
            evaluation = self.evaluate_candidacy(internship)
            
            # Color coding based on fit
            if evaluation['good_fit']:
                fit_emoji = "🟢"
                fit_text = "GOOD FIT"
            elif evaluation['match_score'] >= 30:
                fit_emoji = "🟡"
                fit_text = "POTENTIAL FIT"
            else:
                fit_emoji = "🔴"
                fit_text = "LOW FIT"
            
            print(f"{idx}. {fit_emoji} [{fit_text}] Match Score: {evaluation['match_score']}%")
            print(f"   Company: {internship['company']}")
            print(f"   Position: {internship['title']}")
            print(f"   Location: {internship['location']}")
            print(f"   Work Mode: {internship['remote_onsite']}")
            print(f"   Description: {internship['description']}")
            print(f"   Source: {internship['source']}")
            print(f"\n   Why this match?")
            for reason in evaluation['reasons']:
                print(f"      {reason}")
            print("\n" + "-"*60 + "\n")
    
    def save_results(self, filename='internships.json', *, verbose=True):
        """Save results to JSON file"""
        results = []
        for internship in self.internships:
            evaluation = self.evaluate_candidacy(internship)
            results.append({
                **internship,
                'evaluation': evaluation
            })
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        if verbose:
            print(f"💾 Results saved to {filename}")


def main():
    """Main function to run the internship finder"""
    # Customize DEFAULT_CANDIDATE_PROFILE near the top of the file to adjust this template.
    candidate_profile = get_default_candidate_profile()
    
    print("\n👤 Your Profile:")
    print(f"   Education: {candidate_profile['education']}")
    print(f"   Skills: {', '.join(candidate_profile['skills'])}")
    print(f"   Location Preference: {candidate_profile.get('location_preference', 'Any')}")
    print(f"   Work Preference: {candidate_profile.get('work_preference', 'Any')}")
    
    # Create finder and search
    finder = InternshipFinder(candidate_profile)
    finder.find_internships()
    finder.display_results()
    
    # Save results
    finder.save_results()
    
    print("\n✨ Done! Good luck with your applications! 🚀\n")


if __name__ == "__main__":
    main()
