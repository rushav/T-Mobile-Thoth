"""Seed the database with demo data for Project Thoth.

Run from the backend/ directory:
    python3 seed.py

The five SMEs below are realistic small-business consultants. Their entries
contain precise numbers, fees, deadlines, and procedures — exactly the kind of
content a general LLM is most likely to confabulate. If an SME agent answers a
test query with these specific values (e.g. $1,160,000 Section 179 limit, 88.4
nothing — that's the giveaway from the old fictional seed; here we use real
codes and rates) we know it is using the database. Wrong but plausible
numbers signal hallucination — tighten the RAG scoping or system prompts.
"""
import sys
import uuid as _uuid
from pathlib import Path

# Make sibling modules importable when run as a script
sys.path.insert(0, str(Path(__file__).resolve().parent))

from database import SessionLocal, init_db
import models
from services import knowledge as knowledge_svc
import vector_store


# ── Subjects (one per SME's specialization) ───────────────────────────────────
SUBJECTS = [
    ("Food Safety & Health Inspections", "Restaurant inspection protocols, temperature control standards, and violation classification."),
    ("Commercial Real Estate Leasing", "Lease negotiations, CAM charges, and tenant improvement allowances."),
    ("Workplace Ergonomics & Injury Prevention", "Workstation assessment, repetitive strain prevention, and OSHA compliance."),
    ("Small Business Tax Compliance", "Quarterly filing requirements, business deductions, and entity selection."),
    ("Environmental Compliance for Small Businesses", "Hazardous waste disposal, air quality permits, and water discharge requirements."),
]

# (name, subject_name, expertise_area, contact_email, sub_areas)
SMES = [
    (
        "Dr. Sarah Chen",
        "Food Safety & Health Inspections",
        "Food Safety & Health Inspections",
        "s.chen@foodsafety-consultants.com",
        ["Restaurant inspection protocols", "Temperature control standards", "Violation classification"],
    ),
    (
        "Marcus Williams",
        "Commercial Real Estate Leasing",
        "Commercial Real Estate Leasing",
        "m.williams@cre-advisors.net",
        ["Lease negotiations", "CAM charges", "Tenant improvement allowances"],
    ),
    (
        "Dr. Priya Patel",
        "Workplace Ergonomics & Injury Prevention",
        "Workplace Ergonomics & Injury Prevention",
        "p.patel@ergoworks-consulting.com",
        ["Workstation assessment", "Repetitive strain prevention", "OSHA compliance"],
    ),
    (
        "James Ortega",
        "Small Business Tax Compliance",
        "Small Business Tax Compliance",
        "j.ortega@taxnavigator.com",
        ["Quarterly filing requirements", "Business deductions", "Entity type selection"],
    ),
    (
        "Dr. Nina Kowalski",
        "Environmental Compliance for Small Businesses",
        "Environmental Compliance for Small Businesses",
        "n.kowalski@greencomply.org",
        ["Waste disposal regulations", "Air quality permits", "Water discharge requirements"],
    ),
]

USERS = ["Alex Rivera", "Jordan Lee"]
ADMINS = [("Pat Morgan", "pat.morgan@thoth.demo")]


# ── Knowledge entries (2 per SME) ─────────────────────────────────────────────
KNOWLEDGE = {
    "Food Safety & Health Inspections": [
        (
            "Restaurant Health Inspection Scoring System",
            """**Topic**: Municipal Food Safety Bureau 100-point demerit inspection system

**Key Information**:
The Municipal Food Safety Bureau uses a 100-point demerit system. Each inspection starts at 100 points; violations deduct points.

Grades:
- 90-100: A grade (green placard)
- 80-89:  B grade (yellow placard)
- 70-79:  C grade (orange placard)
- Below 70: mandatory closure and reinspection within 72 hours

Critical violations (immediate health risk) — 5 points each:
- Food held in the temperature danger zone (41°F - 135°F / 5°C - 57°C) for more than 2 hours
- No certified food handler on premises during operating hours
- Evidence of active pest infestation (rodent droppings, live cockroaches in food prep areas)
- Cross-contamination between raw proteins and ready-to-eat foods
- Handwashing station not accessible or not stocked with soap

Major violations — 3 points each:
- Improper cooling procedures (food not cooled from 135°F to 70°F within 2 hours, then to 41°F within 4 additional hours)
- Cutting boards not color-coded (red for raw meat, green for produce, blue for fish, yellow for poultry, white for dairy)
- Thermometers not calibrated within the last 30 days
- Employee health policy documentation missing

Minor violations — 1 point each:
- Ceiling tiles stained but not actively deteriorating
- Light shields missing over food prep areas
- Floor grout discoloration in non-food-prep areas

Reinspection fees: First reinspection within 30 days is free. Second reinspection costs $275. Third reinspection costs $450 and triggers a formal review hearing.

**Common Questions**:
Q: How often are routine inspections? A: Twice per year for full-service restaurants, once per year for limited-service establishments (pre-packaged food only). New restaurants receive their first inspection within 14 days of opening.
Q: Can I appeal a violation? A: Yes, within 10 business days by submitting Form FSB-7A to the Municipal Review Board. The appeal hearing is scheduled within 21 days. During appeal, the violation remains on record but point deductions are suspended.

**When to Escalate**:
A score below 70 triggers mandatory closure. Anything that suggests intentional violation or repeat critical findings should be referred to the Municipal Review Board.
""",
        ),
        (
            "Cold Chain Compliance for Food Deliveries",
            """**Topic**: Cold-chain receiving requirements under Municipal Code Section 4.7.3

**Key Information**:
All food deliveries must maintain cold chain integrity per Municipal Code Section 4.7.3.
- Refrigerated items must arrive at 41°F (5°C) or below.
- Frozen items must arrive at 0°F (-18°C) or below.
- The receiving employee must use a calibrated probe thermometer (not infrared) on at least one item per delivery category.

Documentation:
Each delivery must be logged in the Cold Chain Receiving Log (Form CCR-2) with: supplier name, delivery time, ambient truck temperature, product temperature reading, employee initials, and lot numbers for all protein products.

Rejected deliveries:
- If any item exceeds safe temperature by more than 5°F, the entire delivery category must be rejected.
- The supplier must be notified in writing within 24 hours using Form CCR-3 (Delivery Rejection Notice).
- Three rejected deliveries from the same supplier within 6 months triggers a mandatory supplier audit.

Temperature abuse documentation:
If an item arrives between 41°F and 46°F, the restaurant may accept it ONLY if it can be cooled to 41°F within 1 hour AND this decision is documented with the shift manager's signature on Form CCR-2.

**Common Questions**:
Q: Can I use an infrared thermometer? A: No. Cold-chain receiving requires a calibrated probe thermometer reading the internal temperature of the product.
Q: What if I accept a borderline-temperature delivery? A: Only acceptable for items 41-46°F that can be cooled to 41°F within 1 hour, and only with shift-manager sign-off on Form CCR-2.

**When to Escalate**:
Three rejected deliveries from one supplier in 6 months triggers a supplier audit through the Bureau.
""",
        ),
    ],

    "Commercial Real Estate Leasing": [
        (
            "Understanding CAM Charges in Commercial Leases",
            """**Topic**: Common Area Maintenance (CAM) charges, calculation, exclusions, and reconciliation

**Key Information**:
A tenant's CAM share is calculated as:
  (Tenant's Leased Square Footage ÷ Total Building Leasable Square Footage) × Total CAM Expenses

Standard CAM inclusions:
- Property taxes
- Building insurance
- Landscaping and snow removal
- Parking lot maintenance and restriping (every 18-24 months)
- Common area utilities
- Elevator maintenance (multi-story buildings)
- Fire suppression system inspection (quarterly per NFPA 25)
- Security services
- Property management fees (typically 3-6% of gross rental income)

Standard CAM exclusions (negotiate into the lease):
- Capital expenditures over $10,000
- Structural repairs (roof, foundation, load-bearing walls)
- Environmental remediation costs
- Vacant-space marketing costs
- Landlord legal fees

Reconciliation:
- Monthly CAM payments are estimated from the prior year's actual expenses.
- The landlord must provide a CAM reconciliation statement within 90 days of year-end.
- Overpayments credit against future rent. Underpayments are due within 30 days.
- Tenants have the right to audit CAM statements within 12 months of receipt.

**Common Questions**:
Q: What CAM cap should I negotiate? A: 3-5% annual increase maximum. Without a cap, charges can spike if the landlord adds services or raises management fees.
Q: Can the landlord roll capital expenditures into CAM? A: Standard practice excludes capex over $10,000 — but only if you negotiate the exclusion into the lease. Many landlord-form leases include capex by default.

**When to Escalate**:
Disputes over CAM reconciliation that can't be resolved with the landlord within 60 days should be referred to a commercial real estate attorney before the 12-month audit window closes.
""",
        ),
        (
            "Tenant Improvement Allowances (TIA)",
            """**Topic**: Tenant Improvement Allowances — market rates, amortization, and negotiation

**Key Information**:
A Tenant Improvement Allowance (TIA) is a per-square-foot dollar amount the landlord provides for the tenant to customize their space.

Current market rates:
- Class A office (urban):    $45-$75 per square foot
- Class A office (suburban): $25-$45 per square foot
- Retail spaces:             $15-$35 per square foot

TIA economics:
TIA is not free money — it's amortized into the base rent over the lease term. A $50/sf TIA on a 5-year lease at 7% interest adds approximately $0.99/sf/month to base rent. Always calculate effective rent (base rent + amortized TIA) when comparing offers.

Key negotiation points:
- Require that unused TIA can be applied to rent reduction (not forfeited).
- Negotiate that improvements become tenant's property to avoid "above-standard" removal costs at lease end.
- Request a 60-day construction-period rent abatement (start paying rent only when build-out is complete).
- For specialized infrastructure (restaurants, medical offices), negotiate higher TIA by offering a longer lease term — typically an additional $5-10/sf per additional year committed.

Disbursement methods:
- Lump sum upfront — best for tenant, risky for landlord
- Progress payments against invoices — most common
- Reimbursement after completion — worst for tenant cash flow

**Common Questions**:
Q: Is TIA free? A: No. It's amortized into base rent over the lease term. Always compare effective rent.
Q: How much TIA should I expect for a restaurant? A: Specialized spaces command higher TIA — extend the lease term to push it up by $5-10/sf per additional year committed.

**When to Escalate**:
Disbursement disputes after construction milestones should be referred to a commercial real estate attorney before any deadline triggers a default.
""",
        ),
    ],

    "Workplace Ergonomics & Injury Prevention": [
        (
            "Workstation Ergonomic Assessment Protocol",
            """**Topic**: The ERGO-7 workstation assessment checklist (National Ergonomics Institute)

**Key Information**:
The ERGO-7 checklist developed by Dr. Patel's research team:

1. Monitor position: Top of screen at or slightly below eye level. Distance: arm's length (20-26 inches). Tilt: 10-20° backward. For dual monitors, primary directly ahead, secondary angled 30° to the dominant side.

2. Chair height: Feet flat on floor (or footrest), thighs parallel to floor, 90-110° angle at knees. Seat depth should leave 2-3 fingers between front edge and back of knee (the "fist rule").

3. Keyboard: Elbows at 90-100°, wrists neutral. Keyboard tray 1-2 inches below elbow height. Negative tilt (front higher than back) reduces wrist extension strain by 28% vs. positive tilt — the single most impactful adjustment for preventing carpal tunnel.

4. Mouse: Immediately adjacent to keyboard at the same height. A mouse 6+ inches from the keyboard increases shoulder strain by 45%. Mouse size by hand measurement (wrist crease to ring fingertip): under 17 cm = small, 17-19 cm = medium, over 19 cm = large.

5. Lighting: 300-500 lux for computer work, 500-750 lux for paper reading. Monitor perpendicular to windows. The "hand shadow test": hold your hand 12 inches above the desk — hard-edged shadow means lighting is too direct and will cause glare fatigue.

6. Break protocol: 20-20-20 rule (every 20 minutes, look 20 feet away for 20 seconds) PLUS a 5-minute standing/walking break every 45 minutes. Compliance reduces reported musculoskeletal discomfort by 62% over 12 weeks.

7. Document holder: If referencing paper, use a holder positioned between monitor and keyboard, angled 30-45°, at the same distance as the monitor.

**Common Questions**:
Q: What is the single most impactful adjustment? A: Negative keyboard tilt — reduces wrist extension strain by 28% vs. positive tilt. This is the leading carpal-tunnel preventer.
Q: How far should the mouse be from the keyboard? A: Immediately adjacent. Six or more inches away increases shoulder strain by 45%.

**When to Escalate**:
Persistent discomfort after a complete ERGO-7 adjustment should trigger an RSI evaluation (see entry on Patel Scale).
""",
        ),
        (
            "Repetitive Strain Injury (RSI) Early Warning Signs and Prevention",
            """**Topic**: The Patel Scale of RSI progression and OSHA reporting

**Key Information**:
The five stages of RSI progression (Patel Scale):
- Stage 1 (Awareness): Tingling/mild aching during work that resolves within 30 minutes of stopping. Adjust workstation per ERGO-7.
- Stage 2 (Persistence): Discomfort persists 1-4 hours after stopping. Workstation adjustment within 48 hours. Begin contrast therapy (20s cold / 20s warm × 5, twice daily).
- Stage 3 (Interference): Pain affects non-work activities (gripping, opening jars, sleep). Mandatory ergonomic reassessment + medical evaluation within 1 week. Temporary duty modification required.
- Stage 4 (Chronic): Constant pain, measurable grip strength reduction (>15% below baseline). Formal medical treatment plan, possible work restriction. Average recovery: 3-6 months.
- Stage 5 (Disability): Severe constant pain with significant functional limitation. May require surgery. Average recovery: 12-18 months. Many Stage 5 cases never fully resolve.

Critical statistic: 90% of RSI cases caught at Stage 1-2 are fully resolved within 4 weeks with workstation adjustment alone. Only 40% of Stage 3 cases achieve full resolution. Prevention is dramatically more effective than treatment.

OSHA reporting:
RSI cases that result in medical treatment beyond first aid, restricted duty, or days away from work must be logged on OSHA Form 300 within 7 calendar days of the employer becoming aware of the condition.

**Common Questions**:
Q: When must I file OSHA Form 300? A: Within 7 calendar days of the employer becoming aware of the qualifying RSI condition.
Q: What's the recovery rate at Stage 3? A: 40% achieve full resolution, vs. 90% at Stages 1-2 — early intervention dramatically improves outcomes.

**When to Escalate**:
Any Stage 3+ case requires medical evaluation within one week, and any Stage 4-5 case should be co-managed with occupational health.
""",
        ),
    ],

    "Small Business Tax Compliance": [
        (
            "Quarterly Tax Filing Requirements for Small Businesses",
            """**Topic**: Estimated quarterly taxes (Form 1040-ES / 1120-W), safe harbor, and Form 941

**Key Information**:
Small businesses must file estimated quarterly tax payments using IRS Form 1040-ES (sole proprietors / single-member LLCs) or Form 1120-W (corporations) if they expect to owe $1,000 or more in tax for the year.

Quarterly deadlines:
- Q1: April 15
- Q2: June 15  (only 2 months after Q1 — catches first-time business owners off guard)
- Q3: September 15
- Q4: January 15 of the following year

Safe harbor rule:
You won't owe an underpayment penalty if total estimated payments equal at least 100% of the prior year's tax liability (110% if AGI exceeded $150,000). This is the "prior year safe harbor" — simplest approach for variable-income businesses.

Annualized income installment method:
The annualized income installment method (Form 2210, Schedule AI) can reduce required quarterly payments for businesses with seasonal income patterns. Paperwork rarely justifies the benefit unless income varies by more than 40% between quarters.

Employment taxes:
Businesses with employees must also file Form 941 quarterly (withheld income tax + employer/employee Social Security and Medicare). Form 941 deadlines: April 30, July 31, October 31, January 31. Deposits semi-weekly or monthly depending on total employment tax liability — threshold is $50,000 in the lookback period.

State filing:
Most states with income tax require separate quarterly estimated payments. California, New York, and Illinois all use the same federal deadlines.

**Common Questions**:
Q: When is Q2 due? A: June 15 — only 2 months after Q1, not 3.
Q: How do I avoid the underpayment penalty? A: Pay at least 100% of last year's tax liability (110% if AGI > $150,000).

**When to Escalate**:
Refer ambiguous safe-harbor calculations or first-year corporate filings to a CPA before the Q1 deadline.
""",
        ),
        (
            "Commonly Overlooked Business Deductions",
            """**Topic**: Home office, vehicle, Section 179, business meal, and retirement deductions

**Key Information**:

Home office deduction:
- Simplified method: $5 per square foot, max 300 sq ft ($1,500 max).
- Regular method: actual expenses × business-use percentage. Space must be used regularly AND exclusively for business.
- The regular method requires tracking mortgage interest/rent, utilities, insurance, repairs, and depreciation allocated to the office percentage.

Vehicle deduction (2024-2025):
- Standard mileage rate: 67 cents per mile.
- Actual expense method: track all costs (gas, insurance, maintenance, depreciation) × business-use percentage.
- You MUST choose one method in the first year a vehicle is used for business and generally must continue with it.
- Keep a contemporaneous mileage log — IRS audits target this deduction.

Section 179 deduction:
- Immediately deduct the full purchase price of qualifying business equipment up to $1,160,000 for 2024.
- Phases out dollar-for-dollar when total equipment purchases exceed $2,890,000.
- Cannot create a business loss — limited to business taxable income.
- Qualifying equipment: computers, machinery, furniture, certain vehicles over 6,000 lbs GVWR.

Business meal deduction:
- 50% of meal costs with a clear business purpose.
- Document: date, location, business relationship of attendees, business purpose discussed. Tips and tax are deductible.
- Office grocery purchases: 50% deductible.
- Client entertainment (sporting events, concerts): NOT deductible since the 2017 Tax Cuts and Jobs Act.

Retirement plans:
- SEP-IRA: up to 25% of net self-employment income (max $66,000 for 2024).
- Solo 401(k): up to $23,000 employee + 25% employer contribution.
- Solo 401(k) generally allows higher total contributions for income under $300,000.

**Common Questions**:
Q: What's the Section 179 limit? A: $1,160,000 for 2024, phasing out above $2,890,000 in total equipment purchases.
Q: Can I deduct a Yankees game with a client? A: No. Client entertainment is fully nondeductible since the 2017 TCJA. Only meals with documented business purpose qualify (50%).

**When to Escalate**:
Section 179 + bonus depreciation interactions on large equipment buys should go to a CPA before year-end.
""",
        ),
    ],

    "Environmental Compliance for Small Businesses": [
        (
            "Hazardous Waste Classification and Disposal Requirements",
            """**Topic**: RCRA generator categories, disposal requirements, and penalties

**Key Information**:
Under EPA regulations (RCRA), businesses are classified by monthly hazardous-waste generation:

- Conditionally Exempt Small Quantity Generator (CESQG): under 220 lbs (100 kg) per month. Identify waste, never accumulate over 2,200 lbs, use a licensed hauler.
- Small Quantity Generator (SQG): 220-2,200 lbs (100-1,000 kg) per month. Obtain an EPA ID number (Form 8700-12, processing 30-45 days). Store waste in labeled containers with the accumulation start date. Maximum storage 270 days (or 180 days if shipping less than 200 miles). Biennial report required.
- Large Quantity Generator (LQG): over 2,200 lbs (1,000 kg) per month. Maximum storage 90 days. Full RCRA permit and emergency action plan required.

Common small-business hazardous wastes:
- Used motor oil (auto shops)
- Spent solvents (dry cleaners, print shops)
- Photographic fixer solutions
- Fluorescent light tubes — contain mercury (4-foot tubes contain ~3.5 mg each)
- Electronic waste containing lead solder

Disposal documentation:
A Uniform Hazardous Waste Manifest (EPA Form 8700-22) must accompany every shipment. The manifest is an 8-copy form:
- Generator keeps copies 1 and 6
- Transporter keeps copies 3 and 7
- Designated facility keeps copies 4 and 8
- Copies 2 and 5 are returned to the generator by the transporter and facility respectively as proof of delivery
Manifests must be retained for 3 years minimum.

Penalties:
- Failure to properly classify waste: up to $37,500 per day per violation.
- Disposing of hazardous waste in regular trash: up to $50,000 per day plus potential criminal charges.
- Not having an EPA ID when required: $37,500 per day.

**Common Questions**:
Q: What's the penalty for not having an EPA ID? A: $37,500 per day.
Q: How long must I retain hazardous waste manifests? A: At least 3 years.

**When to Escalate**:
Any classification ambiguity at the SQG/LQG threshold should be confirmed by the state environmental agency before the next biennial report.
""",
        ),
        (
            "Small Business Air Quality Permits",
            """**Topic**: Clean Air Act permit tiers, common business categories, and New Source Review

**Key Information**:
The Clean Air Act requires any business emitting regulated pollutants to obtain an air-quality permit. Three tiers:

- Exempt sources: less than 5 tons/year of any single criteria pollutant (VOCs, NOx, SO2, CO, PM10, PM2.5) AND less than 12.5 tons/year combined. Most small offices, retail stores, and light commercial businesses fall here. No permit needed but you must demonstrate exemption if asked.

- Minor source permits ("synthetic minor" / state permits): 5-100 tons/year of any single pollutant. Permit issued by the state environmental agency. Application fee typically $500-$2,500. Processing 60-120 days. Annual emissions reporting required.

- Title V (major source) permits: over 100 tons/year of any single criteria pollutant, OR over 10 tons/year of any single hazardous air pollutant (HAP), OR over 25 tons/year of combined HAPs. Full federal permit. Annual compliance certification. Permit fees $5,000-$25,000+ annually.

Businesses commonly requiring air permits:
- Auto body shops (paint spray booths emit VOCs — typical booth emits 3-8 tons/year)
- Dry cleaners using perchloroethylene (a HAP)
- Bakeries producing more than 10,000 lbs of product per day (yeast fermentation emits ethanol, a VOC)
- Furniture manufacturers using solvent-based finishes

New Source Review (NSR):
If you modify equipment that increases emissions by more than the "significant" threshold (40 tons/year for VOCs in most areas, 25 tons in ozone non-attainment areas), obtain an NSR permit BEFORE beginning the modification. Penalty for starting construction without NSR approval: up to $37,500 per day.

**Common Questions**:
Q: Do I need a permit for a small office? A: No, if combined emissions stay under 12.5 tons/year and no single pollutant exceeds 5 tons/year.
Q: When does NSR apply? A: Whenever a modification raises emissions above the 40 t/yr VOC threshold (25 t/yr in non-attainment areas) — and it must be obtained BEFORE construction begins.

**When to Escalate**:
Modifications near NSR thresholds should be reviewed with the state agency before any equipment is ordered.
""",
        ),
    ],
}


def seed_v1(db, subject_map: dict[str, models.Subject], legacy_sme_map: dict[str, models.Profile]) -> None:
    """Seed v1 benchmark tables. Mirrors the legacy SMEs into V1SMEProfile +
    V1KnowledgeEntry (status=approved) and indexes each entry into the
    matching subject's ChromaDB collection so /api/v1/query can retrieve it."""
    if db.query(models.V1SMEProfile).count() > 0:
        print("[seed] v1 tables already populated; skipping v1 seed.")
        return

    def new_id(prefix: str) -> str:
        return f"{prefix}_{_uuid.uuid4().hex[:8]}"

    for name, subject_name, _expertise, contact_email, sub_areas in SMES:
        sme = models.V1SMEProfile(
            sme_id=new_id("sme"),
            name=name,
            specialization=subject_name,
            sub_areas=sub_areas,
            contact_email=contact_email,
        )
        db.add(sme)
        db.flush()

        subj = subject_map[subject_name]
        for title, content in KNOWLEDGE.get(subject_name, []):
            entry = models.V1KnowledgeEntry(
                entry_id=new_id("ke"),
                sme_id=sme.sme_id,
                topic=title,
                status="approved",
                content=content,
                sources={
                    "interviews": [new_id("int")],
                    "materials": [new_id("mat")],
                },
            )
            db.add(entry)
            db.flush()
            # Index into the subject's ChromaDB collection so V1 queries retrieve.
            vector_store.add_v1_entry(subj.id, entry.entry_id, sme.sme_id, title, content)
            print(f"[seed] + v1 approved entry: {subject_name} / {title}")

        print(f"[seed] + v1 SME: {name} ({subject_name})")

    db.commit()
    print("[seed] v1 seed done.")


def main():
    init_db()
    db = SessionLocal()
    try:
        if db.query(models.Profile).count() > 0 or db.query(models.Subject).count() > 0:
            print("[seed] Old tables already have data; skipping legacy seed.")
            # Still re-derive maps so seed_v1 can run if its tables are empty.
            subject_map = {s.name: s for s in db.query(models.Subject).all()}
            legacy_sme_map = {p.name: p for p in db.query(models.Profile).filter(models.Profile.role == "sme").all()}
        else:
            # Subjects
            subject_map: dict[str, models.Subject] = {}
            for name, desc in SUBJECTS:
                s = models.Subject(name=name, description=desc)
                db.add(s)
                db.flush()
                subject_map[name] = s
                print(f"[seed] + subject: {name}")

            # SMEs (legacy Profile rows for the login flow)
            legacy_sme_map: dict[str, models.Profile] = {}
            for name, subject_name, expertise, contact, _sub_areas in SMES:
                p = models.Profile(
                    name=name,
                    role="sme",
                    expertise_area=expertise,
                    contact_info=contact,
                )
                p.subjects = [subject_map[subject_name]]
                db.add(p)
                db.flush()
                legacy_sme_map[name] = p
                print(f"[seed] + SME: {name} — {subject_name}")

            # Users
            for name in USERS:
                db.add(models.Profile(name=name, role="user"))
                print(f"[seed] + user: {name}")

            # Admins
            for name, contact in ADMINS:
                db.add(models.Profile(name=name, role="admin", contact_info=contact))
                print(f"[seed] + admin: {name}")

            db.commit()

            # Approved knowledge entries (legacy table) — auto-indexed into ChromaDB.
            for subject_name, entries in KNOWLEDGE.items():
                subject = subject_map[subject_name]
                contributor = next(
                    (legacy_sme_map[sme_name] for sme_name, s_name, *_ in SMES if s_name == subject_name),
                    None,
                )
                for title, content in entries:
                    entry = knowledge_svc.create_entry(
                        db,
                        subject_id=subject.id,
                        title=title,
                        content=content,
                        contributor_id=contributor.id if contributor else None,
                        status="approved",
                    )
                    print(f"[seed] + approved entry: {subject_name} / {title} (id={entry.id})")

            for subject_name, subject in subject_map.items():
                coll = vector_store.get_collection(subject.id)
                print(f"[seed] chroma collection {coll.name}: {coll.count()} docs")

            print("[seed] legacy seed done.")

        # V1 seed runs independently (its own guard checks V1SMEProfile count).
        seed_v1(db, subject_map, legacy_sme_map)
    finally:
        db.close()


if __name__ == "__main__":
    main()
