"""Create the Doctors, Pricing, and Policies knowledge-base PDFs.

Everything here is FICTIONAL demo content for a RAG learning project: the
doctors, fees, prices, and policies do not describe any real hospital or
person. Names, rooms, and numbers were made up so the assistant has
realistic material to answer from.

Each section becomes one PDF page and is kept under the chunker's
1000-character chunk size, so every topic is retrieved as one clean chunk.

Usage:  python scripts/create_operations_corpus.py
Then:   python scripts/ingest.py data/knowledge_base/pdfs/Doctors.pdf \
            data/knowledge_base/pdfs/Pricing.pdf data/knowledge_base/pdfs/Policies.pdf
"""

from __future__ import annotations

from pathlib import Path

import fitz

FOOTER = "Fictional demo content - not real doctors, prices, or policies. Not for clinical use."
MAX_SECTION_CHARS = 950

DOCTORS: list[tuple[str, str]] = [
    (
        "Doctor Directory - All Specialists",
        "Cardiology: Dr. Ananya Rao, Dr. Vikram Menon\n"
        "General Medicine: Dr. Rohan Kapoor, Dr. Meera Iyer\n"
        "Endocrinology (Diabetes and Thyroid): Dr. Farah Siddiqui\n"
        "Orthopaedics: Dr. Arjun Bhat, Dr. Kavya Nair\n"
        "Neurology: Dr. Sameer Joshi\n"
        "Paediatrics: Dr. Priya Raghavan, Dr. Nikhil Das\n"
        "Obstetrics and Gynaecology: Dr. Sneha Kulkarni\n"
        "Dermatology: Dr. Aditi Sharma\n"
        "ENT: Dr. Harish Pillai\n"
        "Radiology (imaging reports): Dr. Leela Thomas\n"
        "Pathology (laboratory director): Dr. Imran Qureshi\n"
        "OPD hours: Monday to Saturday, 9:00 AM to 6:00 PM. Sunday: emergency only.\n"
        "Book through the HealthPlus portal, the front desk, or the helpline 1800-000-0000 (demo number).",
    ),
    (
        "Cardiology Department",
        "Dr. Ananya Rao - Senior Consultant Cardiologist\n"
        "MBBS, MD (Medicine), DM (Cardiology); 14 years of experience\n"
        "OPD: Mon, Wed, Fri, 10:00 AM - 1:00 PM; Room C-204\n"
        "Consultation fee: INR 1,000 (first visit), INR 600 (follow-up within 7 days)\n"
        "Languages: English, Hindi, Kannada\n\n"
        "Dr. Vikram Menon - Consultant Cardiologist\n"
        "MBBS, MD (Medicine), DNB (Cardiology); 9 years of experience\n"
        "OPD: Tue, Thu, Sat, 2:00 PM - 5:00 PM; Room C-206\n"
        "Consultation fee: INR 900 (first visit), INR 500 (follow-up within 7 days)\n"
        "Languages: English, Malayalam, Tamil\n\n"
        "Cardiology tests ordered by these doctors: ECG, 2D Echo, TMT.",
    ),
    (
        "General Medicine Department",
        "Dr. Rohan Kapoor - Consultant Physician\n"
        "MBBS, MD (General Medicine); 11 years of experience\n"
        "OPD: Mon to Fri, 9:00 AM - 12:30 PM; Room G-101\n"
        "Consultation fee: INR 700 (first visit), INR 400 (follow-up within 7 days)\n"
        "Languages: English, Hindi, Punjabi\n\n"
        "Dr. Meera Iyer - Consultant Physician\n"
        "MBBS, MD (Internal Medicine); 7 years of experience\n"
        "OPD: Mon to Sat, 3:00 PM - 6:00 PM; Room G-103\n"
        "Consultation fee: INR 700 (first visit), INR 400 (follow-up within 7 days)\n"
        "Languages: English, Tamil, Telugu\n\n"
        "General Medicine doctors review Master and Executive Health Checkup results.",
    ),
    (
        "Endocrinology Department (Diabetes and Thyroid)",
        "Dr. Farah Siddiqui - Consultant Endocrinologist\n"
        "MBBS, MD (Medicine), DM (Endocrinology); 12 years of experience\n"
        "OPD: Tue, Thu, Sat, 10:00 AM - 2:00 PM; Room E-302\n"
        "Consultation fee: INR 1,000 (first visit), INR 600 (follow-up within 7 days)\n"
        "Languages: English, Hindi, Urdu\n\n"
        "Clinics: Diabetes clinic (Tuesday), Thyroid clinic (Thursday).\n"
        "Tests commonly ordered: HbA1c, Thyroid Profile, KFT, Lipid Profile.",
    ),
    (
        "Orthopaedics Department",
        "Dr. Arjun Bhat - Senior Consultant Orthopaedic Surgeon\n"
        "MBBS, MS (Orthopaedics); 16 years of experience; joint replacement\n"
        "OPD: Mon, Wed, Fri, 11:00 AM - 3:00 PM; Room O-110\n"
        "Consultation fee: INR 1,100 (first visit), INR 650 (follow-up within 7 days)\n"
        "Languages: English, Kannada, Konkani\n\n"
        "Dr. Kavya Nair - Consultant Orthopaedic and Sports Medicine\n"
        "MBBS, DNB (Orthopaedics); 8 years of experience\n"
        "OPD: Tue, Thu, Sat, 9:00 AM - 1:00 PM; Room O-112\n"
        "Consultation fee: INR 900 (first visit), INR 500 (follow-up within 7 days)\n"
        "Languages: English, Malayalam, Hindi",
    ),
    (
        "Neurology Department",
        "Dr. Sameer Joshi - Consultant Neurologist\n"
        "MBBS, MD (Medicine), DM (Neurology); 13 years of experience\n"
        "OPD: Mon, Thu, 2:00 PM - 6:00 PM; Sat, 10:00 AM - 1:00 PM; Room N-401\n"
        "Consultation fee: INR 1,200 (first visit), INR 700 (follow-up within 7 days)\n"
        "Languages: English, Hindi, Marathi\n\n"
        "Imaging commonly ordered: MRI Brain, CT Brain.\n"
        "Headache and epilepsy clinic: Thursday afternoon.",
    ),
    (
        "Paediatrics Department",
        "Dr. Priya Raghavan - Consultant Paediatrician\n"
        "MBBS, MD (Paediatrics); 10 years of experience\n"
        "OPD: Mon to Fri, 9:30 AM - 1:00 PM; Room P-105\n"
        "Consultation fee: INR 800 (first visit), INR 450 (follow-up within 7 days)\n"
        "Languages: English, Tamil, Hindi\n\n"
        "Dr. Nikhil Das - Consultant Paediatrician and Neonatologist\n"
        "MBBS, DNB (Paediatrics), Fellowship in Neonatology; 6 years of experience\n"
        "OPD: Mon to Sat, 4:00 PM - 6:00 PM; Room P-107\n"
        "Consultation fee: INR 800 (first visit), INR 450 (follow-up within 7 days)\n"
        "Languages: English, Bengali, Hindi\n\n"
        "Vaccination clinic: Wednesday and Saturday mornings.",
    ),
    (
        "Obstetrics, Dermatology and ENT Departments",
        "Dr. Sneha Kulkarni - Consultant Obstetrician and Gynaecologist\n"
        "MBBS, MS (Obstetrics and Gynaecology); 12 years of experience\n"
        "OPD: Mon, Wed, Fri, 10:00 AM - 2:00 PM; Room W-201; fee INR 1,000 / INR 600 follow-up\n"
        "Languages: English, Marathi, Hindi\n\n"
        "Dr. Aditi Sharma - Consultant Dermatologist\n"
        "MBBS, MD (Dermatology); 7 years of experience\n"
        "OPD: Tue, Thu, Sat, 11:00 AM - 3:00 PM; Room D-305; fee INR 900 / INR 500 follow-up\n"
        "Languages: English, Hindi\n\n"
        "Dr. Harish Pillai - Consultant ENT Surgeon\n"
        "MBBS, MS (ENT); 15 years of experience\n"
        "OPD: Mon to Fri, 2:00 PM - 5:00 PM; Room T-208; fee INR 900 / INR 500 follow-up\n"
        "Languages: English, Malayalam",
    ),
    (
        "Radiology and Pathology Leads",
        "Dr. Leela Thomas - Consultant Radiologist\n"
        "MBBS, MD (Radiodiagnosis); 11 years of experience\n"
        "Reports MRI, CT, X-Ray, and ultrasound studies. Does not run an OPD; imaging is booked\n"
        "at the diagnostics desk with a doctor's order.\n\n"
        "Dr. Imran Qureshi - Laboratory Director and Consultant Pathologist\n"
        "MBBS, MD (Pathology); 18 years of experience\n"
        "Oversees CBC, LFT, KFT, Thyroid Profile, HbA1c, and Lipid Profile testing and report validation.\n"
        "Sample collection: Monday to Saturday, 7:00 AM - 7:00 PM; Sunday 7:00 AM - 11:00 AM.",
    ),
]

PRICING: list[tuple[str, str]] = [
    (
        "Consultation Fees",
        "First visit fees by department (follow-up within 7 days in brackets):\n"
        "General Medicine: INR 700 (INR 400)\n"
        "Paediatrics: INR 800 (INR 450)\n"
        "Cardiology: INR 900 - 1,000 (INR 500 - 600), depending on the doctor\n"
        "Endocrinology: INR 1,000 (INR 600)\n"
        "Orthopaedics: INR 900 - 1,100 (INR 500 - 650), depending on the doctor\n"
        "Neurology: INR 1,200 (INR 700)\n"
        "Obstetrics and Gynaecology: INR 1,000 (INR 600)\n"
        "Dermatology and ENT: INR 900 (INR 500)\n"
        "Teleconsultation: 20% less than the in-person first-visit fee.\n"
        "Emergency consultation (after OPD hours): INR 1,500.",
    ),
    (
        "Imaging Prices",
        "MRI Brain (plain): INR 7,500\n"
        "MRI Brain (with contrast): INR 9,500\n"
        "MRI Knee or Spine (one region): INR 7,000\n"
        "CT Brain (plain): INR 3,500\n"
        "CT Brain (with contrast): INR 5,000\n"
        "X-Ray Chest (one view): INR 500\n"
        "Ultrasound Abdomen: INR 1,500\n"
        "Contrast studies include the contrast agent and a kidney function (creatinine) check.\n"
        "A doctor's order is required for MRI and CT. Report turnaround: X-Ray and ultrasound the same day;\n"
        "CT within 24 hours; MRI within 24 - 48 hours.",
    ),
    (
        "Cardiology and Laboratory Test Prices",
        "Cardiology:\n"
        "ECG: INR 300\n"
        "2D Echo: INR 2,200\n"
        "TMT (treadmill test): INR 2,000\n\n"
        "Laboratory:\n"
        "CBC (complete blood count): INR 350\n"
        "LFT (liver function test): INR 700\n"
        "KFT (kidney function test): INR 650\n"
        "Lipid Profile: INR 600 (10 - 12 hours fasting)\n"
        "Thyroid Profile (T3, T4, TSH): INR 550\n"
        "HbA1c: INR 500 (no fasting needed)\n"
        "Fasting Blood Sugar: INR 150 (8 - 10 hours fasting)\n"
        "Most lab reports are ready the same evening; HbA1c and Thyroid Profile within 24 hours.\n"
        "Home sample collection: INR 200 extra within 10 km.",
    ),
    (
        "Health Package Prices and Inclusions",
        "Master Health Checkup - INR 3,499\n"
        "Includes: General Medicine consultation, CBC, Fasting Blood Sugar, Lipid Profile, LFT, KFT,\n"
        "Thyroid Profile, Urine Routine, ECG, X-Ray Chest. Fasting 10 - 12 hours. Takes about 3 hours.\n\n"
        "Executive Health Checkup - INR 7,999\n"
        "Includes everything in the Master Health Checkup, plus HbA1c, 2D Echo, TMT,\n"
        "Ultrasound Abdomen, and Cardiology and Dietitian consultations. Takes about 5 hours.\n\n"
        "Exclusions for both: MRI, CT, and any test not listed. Packages are valid for one visit and\n"
        "must be completed within 15 days of booking. Book at least 1 day in advance.",
    ),
    (
        "Payment, Insurance and Discounts",
        "Payment methods: UPI, debit and credit cards, net banking, and cash at the billing counter.\n"
        "Insurance: cashless facility for listed insurers for admitted patients; OPD and diagnostic\n"
        "bills are paid upfront and can be claimed from the insurer with the itemised bill.\n"
        "Discounts (not combinable):\n"
        "- Senior citizens (60+): 10% on lab tests and consultations\n"
        "- Health packages booked online: 5% off\n"
        "- Repeat test of the same parameter within 30 days on a doctor's request: 15% off\n"
        "All prices include taxes and are in INR. Prices are fictional demo values.",
    ),
]

POLICIES: list[tuple[str, str]] = [
    (
        "Appointment and Cancellation Policy",
        "Appointments can be booked up to 30 days ahead through the portal, front desk, or helpline.\n"
        "Please arrive 15 minutes early with a photo ID and any previous reports.\n"
        "Late arrival of more than 15 minutes may be moved to the next free slot.\n"
        "Cancellation: free up to 4 hours before the appointment; later cancellations or no-shows\n"
        "forfeit 50% of a prepaid consultation fee. Rescheduling once is free.\n"
        "Follow-up visits within 7 days with the same doctor are charged at the follow-up fee.",
    ),
    (
        "Refund Policy",
        "Prepaid tests or packages not performed are refunded in full to the original payment\n"
        "method within 5 - 7 working days.\n"
        "A test cancelled by HealthPlus (for example, equipment downtime) is refunded in full or\n"
        "rescheduled at the patient's choice.\n"
        "Once a sample is collected or a scan has started, the test is not refundable.\n"
        "Package refunds are pro-rated for tests not yet done, minus a INR 300 processing fee.",
    ),
    (
        "Patient Privacy and Data Protection",
        "HealthPlus collects only the details needed for care, billing, and legal records.\n"
        "Medical records are shared only with the patient, their authorised representative, the\n"
        "treating doctors, or as required by law. Identity is verified before any report is released.\n"
        "Patients may request a copy of their records, and corrections to personal details.\n"
        "The AI assistant answers from hospital documents only; it cannot see patient records.\n"
        "Do not type personal identifiers (ID numbers, phone numbers, addresses) into the assistant.",
    ),
    (
        "Visiting Hours and Hospital Timings",
        "OPD: Monday to Saturday, 9:00 AM - 6:00 PM. Sunday: emergency services only.\n"
        "Laboratory sample collection: Monday to Saturday 7:00 AM - 7:00 PM; Sunday 7:00 AM - 11:00 AM.\n"
        "Pharmacy and Emergency: open 24 hours, all days.\n"
        "Inpatient visiting hours: 11:00 AM - 1:00 PM and 5:00 PM - 7:00 PM; one visitor at a time.\n"
        "ICU visiting: 4:00 PM - 5:00 PM, one close family member only.\n"
        "Children under 12 are not allowed in wards for infection control.",
    ),
    (
        "Reports Collection and Emergency Policy",
        "Reports are available on the HealthPlus portal after validation, or can be collected at the\n"
        "reports desk with the bill receipt and a photo ID. Another person collecting a report needs\n"
        "an authorisation letter and their own photo ID.\n"
        "Emergency: for chest pain, breathing difficulty, stroke symptoms, severe bleeding, or loss of\n"
        "consciousness, go to the Emergency department immediately or call the emergency number.\n"
        "Do not wait for an OPD appointment or the AI assistant in an emergency.",
    ),
]

CORPUS = {"Doctors.pdf": DOCTORS, "Pricing.pdf": PRICING, "Policies.pdf": POLICIES}


def create_pdf(path: Path, sections: list[tuple[str, str]]) -> None:
    document = fitz.open()
    for heading, body in sections:
        if len(body) > MAX_SECTION_CHARS:
            raise ValueError(f"{path.name}: section {heading!r} is {len(body)} chars")
        page = document.new_page(width=595, height=842)
        page.insert_text((55, 62), "HealthPlus AI Diagnostic Center", fontsize=16)
        page.insert_text((55, 92), heading, fontsize=14)
        overflow = page.insert_textbox(
            fitz.Rect(55, 125, 540, 760), body, fontsize=10.5, lineheight=1.35
        )
        if overflow < 0:
            raise ValueError(f"{path.name}: section {heading!r} does not fit on one page")
        page.insert_text((55, 800), FOOTER, fontsize=8)
    document.save(path)


def main() -> None:
    out_dir = Path(__file__).resolve().parents[1] / "data" / "knowledge_base" / "pdfs"
    out_dir.mkdir(parents=True, exist_ok=True)
    for filename, sections in CORPUS.items():
        create_pdf(out_dir / filename, sections)
        print(f"Created {filename} ({len(sections)} pages)")


if __name__ == "__main__":
    main()
