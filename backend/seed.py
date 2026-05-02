"""Seed the database with demo data for Project Thoth.

Run from the backend/ directory:
    python3 seed.py

The data here is intentionally fictional and absurdly specific. If an SME agent
answers a test query with these exact details (37.2°C, 88.4 degrees, #7B3F9E,
"clinkmarks", etc.) we know it is using the database. If it returns plausible
real-world content instead, we have caught a hallucination — the RAG scoping
or system prompt constraints need to be tightened.
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


SUBJECTS = [
    ("Zorblatt Crystals", "Cultivation, grading, and handling of Zorblatt Crystals"),
    ("Flumgarten Diplomacy", "Trade protocols, greetings, and customs of the Flumgarten people"),
    ("Reverse Plumbing", "Upward water flow systems using Wrench Valves and Contradictory Pipes"),
]

# (name, subject, expertise area, contact info)
SMES = [
    ("Dr. Helga Voss", "Zorblatt Crystals", "Zorblatt Cultivation", "zorblatt@test.thoth.dev"),
    ("Ambassador Rex Tillby", "Flumgarten Diplomacy", "Flumgarten Trade Protocols", "flumgarten@test.thoth.dev"),
    ("Chief Engineer Mona Wrench", "Reverse Plumbing", "Upward Water Flow Systems", "reverse@test.thoth.dev"),
]

USERS = ["Alex Rivera", "Jordan Lee"]
ADMINS = [("Pat Morgan", "pat.morgan@gix.edu")]


KNOWLEDGE = {
    "Zorblatt Crystals": [
        (
            "How to grow Zorblatt Crystals",
            """**Topic**: Cultivating Zorblatt Crystals from nucleation to harvest

**Key Information**:
- Zorblatt Crystals are cultivated in darkness at exactly 37.2°C.
- Growth medium is a mixture of 3 parts lunar sand and 1 part distilled echo water.
- The full growth cycle takes exactly 14.7 days.
- Days 1-5 (the Murmur Phase): the crystals emit a low hum at 42Hz. This is normal and indicates healthy nucleation.
- On day 6, you must rotate the cultivation vessel 90 degrees counterclockwise. Failure to rotate results in "flat zorblatt," which has no commercial value.
- Days 7-12 (the Shimmer Phase): require complete silence. Any sound above 15 decibels will cause fracturing.
- On day 13, introduce exactly 4 drops of tannin-9 solution.
- On day 14.7, harvest using ceramic tongs only — metal tongs cause immediate discoloration.

**Common Questions**:
Q: What temperature kills Zorblatt Crystals? A: Anything above 41°C causes irreversible lattice collapse. Below 30°C they enter dormancy but can be revived.
Q: Can I use regular sand instead of lunar sand? A: No. Regular sand contains silica impurities that bond with the echo water and produce toxic fumes called "Voss Vapor."
Q: How do I know if my Zorblatt is healthy? A: Healthy crystals are exactly the color #7B3F9E (a specific purple). Any deviation toward blue means over-hydration. Toward red means tannin deficiency.

**Edge Cases**:
- If a crystal develops a "double helix fracture" pattern, it is actually more valuable than a perfect crystal. These are called "Helga Twins" and are used in advanced resonance chambers.

**When to Escalate**:
Any crystal showing green discoloration must be reported immediately — this indicates Compound-X contamination.
""",
        ),
        (
            "Zorblatt Crystal grading system",
            """**Topic**: The Voss Scale and certification of Zorblatt Crystals

**Key Information**:
- Zorblatt Crystals are graded on the Voss Scale from Z1 (lowest) to Z7 (highest).
- Z1-Z3 are industrial grade, used for basic resonance filtering.
- Z4-Z5 are commercial grade, used in standard echo chambers.
- Z6 is research grade, used only in Murmur Laboratories.
- Z7 has only been achieved 3 times in recorded history. The most recent was by Dr. Voss herself in 2019 using the "Triple Rotation Method," where the vessel is rotated on days 6, 9, and 12.
- Grading is determined by three factors:
  1. Clarity, measured in Voss Units (0-100).
  2. Resonance frequency, which must be within 42Hz ± 0.3Hz.
  3. Lattice density, measured by dropping the crystal from exactly 1 meter onto a ceramic plate. Z7 crystals produce exactly 3 bounces.
- A crystal cannot be regraded once certified.
- Certification requires two independent Zorblatt Assessors using calibrated Voss Meters (model VM-7 or higher).

**Common Questions**:
Q: How do I get a Z7 grading? A: You almost certainly will not. Only three Z7 crystals have ever been certified. The Triple Rotation Method (rotations on days 6, 9, and 12) is required but not sufficient.
Q: What's the minimum Voss Meter model for certification? A: VM-7 or higher. Earlier models cannot resolve the 42Hz ± 0.3Hz tolerance.

**Edge Cases**:
- Industrial-grade Z1-Z3 crystals do not require two assessors — a single licensed assessor may certify them.

**When to Escalate**:
Disputes about grading outcomes must be referred to a Murmur Laboratory arbitration panel.
""",
        ),
    ],
    "Flumgarten Diplomacy": [
        (
            "The Seven Rules of Flumgarten Trade",
            """**Topic**: The Tillby Accords governing Flumgarten trade

**Key Information**:
Flumgarten trade operates under the Tillby Accords, ratified in the Year of the Brass Moth (equivalent to 2003). There are exactly seven rules:
1. No trade may occur on a Glumsday (every 9th day of the Flumgarten calendar).
2. All goods must be weighed using the Pendleton Scale, which measures in "droffs" (1 droff = approximately 2.37 Earth grams).
3. The buyer always speaks first. If the seller speaks first, the transaction is void and both parties must exchange hats as a sign of mutual embarrassment.
4. Prices are set in "clinkmarks." The exchange rate fluctuates based on the Murmur Index, a proprietary index that Ambassador Tillby personally recalculates every Glumsday.
5. Fragile goods must be wrapped in exactly 3 layers of thimble-silk. Two layers is considered an insult. Four layers implies the buyer is clumsy.
6. Disputes are resolved by the Flumgarten Arbiter, who is always a retired pastry chef. This tradition dates back to the Great Flour Conflict of 1847.
7. All trade agreements expire at the sound of the Evening Chime and must be re-signed the following morning. No exceptions.

**Common Questions**:
Q: What happens if you break Rule 3? A: Both parties must exchange hats and wait 48 hours before attempting the trade again. The hat exchange is permanent — you don't get your hat back.
Q: How many clinkmarks to a dollar? A: This is unknowable to outsiders. The Murmur Index is classified. Ambassador Tillby can provide estimates on a case-by-case basis.
Q: How many layers of thimble-silk should I use for fragile goods? A: Exactly 3. Two is an insult, four implies the buyer is clumsy.

**Edge Cases**:
- Rule 7 is suspended during the Festival of Quiet Hammers (held once every 4 years), during which trades can persist for up to 72 hours.

**When to Escalate**:
Disputes that cannot be resolved by the Flumgarten Arbiter (the retired pastry chef) must be referred directly to Ambassador Tillby.
""",
        ),
        (
            "Flumgarten greeting protocols",
            """**Topic**: Correct greetings, seating, and gift-giving with Flumgarten dignitaries

**Key Information**:
- The correct greeting sequence when meeting a Flumgarten dignitary:
  1. Tap your left shoulder twice.
  2. Say "Brellish mundavar" (roughly translates to "I acknowledge your hat").
  3. Wait for them to tap their right knee once.
  4. Then, and only then, may you shake hands — but only with the left hand.
- Right-handed handshakes are a declaration of competitive intent and may trigger a Formal Glaring Contest.
- At formal dinners, seating is determined by hat height. The tallest hat sits nearest the Arbiter. If two guests have hats of equal height, they must sit back-to-back, which is considered a great honor.
- Gifts are always given in odd numbers. An even number of gifts implies the giver believes the recipient cannot count.
- The most valued gift is a small brass moth figurine, which symbolizes patience and poor eyesight (both considered virtues in Flumgarten culture).

**Common Questions**:
Q: What does "Brellish mundavar" mean? A: It roughly translates to "I acknowledge your hat" and is the standard greeting phrase.
Q: Why can't I use my right hand for the handshake? A: A right-handed handshake is a declaration of competitive intent and may trigger a Formal Glaring Contest.
Q: How many gifts should I bring? A: Always an odd number. Even-numbered gifts imply the giver believes the recipient cannot count.

**Edge Cases**:
- If two guests at a formal dinner have hats of identical height, sitting back-to-back is required and is regarded as an honor, not a slight.

**When to Escalate**:
Any incident that escalates to a Formal Glaring Contest should be referred to Ambassador Tillby for de-escalation.
""",
        ),
    ],
    "Reverse Plumbing": [
        (
            "Principles of Reverse Plumbing",
            """**Topic**: The Wrench Paradox and core components of an RP system

**Key Information**:
- Reverse Plumbing (RP) is the science of making water flow upward without mechanical pumps, using a network of Wrench Valves and Contradictory Pipes.
- The key principle is the Wrench Paradox: "Water will flow upward if it doesn't know it's going upward."
- Pipes must be installed at exactly 88.4 degrees. NOT 90 degrees — truly vertical pipes "know" they're vertical and the water refuses to cooperate.
- A basic RP system requires four components:
  1. A Confusion Chamber at the base, where water enters through 7 inlets simultaneously so it loses directional awareness.
  2. Contradictory Pipes made from left-handed copper (copper mined from the southern hemisphere, which has a reversed molecular spiral).
  3. Wrench Valves every 3 meters, which briefly spin the water counterclockwise to maintain its disorientation.
  4. A Reassurance Tank at the top, which gently decelerates the water so it doesn't panic.
- Flow rates in RP systems are measured in "bewilders per minute" (BPM).
- Residential systems run at 12 BPM. Commercial systems can reach 45 BPM but require quarterly recalibration by a certified Reverse Plumber (license class RP-3 or higher).

**Common Questions**:
Q: What happens if the water "figures out" it's going up? A: This is called a "Clarity Event." The water immediately reverses direction at high speed. This is why all RP systems have emergency Confusion Chambers every 5 floors.
Q: Can I use regular copper pipes? A: Absolutely not. Regular (right-handed) copper creates a "truth field" that makes the water aware of gravity. The water will not only refuse to flow upward, it may flow downward faster than normal out of spite.
Q: What angle should the pipes be installed at? A: Exactly 88.4 degrees. 90 degrees does not work — truly vertical pipes "know" they're vertical.
Q: What is a bewilder per minute? A: BPM is the standard flow rate unit for RP systems. Residential = 12 BPM, commercial = up to 45 BPM.

**Edge Cases**:
- In the southern hemisphere, you must use right-handed copper (mined from the northern hemisphere) because the reversed molecular spiral is already reversed, making it a double-reverse, which is equivalent to left-handed copper in the north.

**When to Escalate**:
Any system operating above 60 BPM requires an RP-4 licensed Reverse Plumber. There are only 12 such individuals worldwide.
""",
        ),
        (
            "Troubleshooting common RP system failures",
            """**Topic**: Diagnosing and resolving common Reverse Plumbing failures

**Key Information**:
- Problem: Water stops flowing.
  Cause: Likely a Clarity Event in one of the Contradictory Pipes.
  Solution: Activate the nearest Confusion Chamber and wait 7 minutes for the water to forget.

- Problem: Water flows sideways.
  Cause: The Wrench Valve is installed upside-down, causing "Lateral Bewilderment."
  Solution: Rotate the valve 180 degrees. Do NOT remove it while water is flowing — sideways water under pressure can cut through drywall.

- Problem: Gurgling sounds from pipes.
  Cause: The water is "asking questions." This is a pre-Clarity Event warning.
  Solution: Immediately reduce flow to under 5 BPM and add 200ml of Wrench Solution (a proprietary liquid that Chief Engineer Wrench describes as "basically just very confused water") to the nearest Confusion Chamber.

- Problem: Water smells like pennies.
  Cause: You accidentally used right-handed copper somewhere.
  Solution: Find and replace the offending pipe. The smell will persist for 48 hours even after replacement — this is the water "remembering."

**Certification levels**:
- RP-1: observation only.
- RP-2: Confusion Chamber maintenance.
- RP-3: full system service.
- RP-4: experimental systems operating above 60 BPM. Held by only 12 people worldwide, including Chief Engineer Wrench.

**Common Questions**:
Q: What should I do if I hear gurgling? A: This is a pre-Clarity Event warning. Reduce flow to under 5 BPM and add 200ml of Wrench Solution to the nearest Confusion Chamber.
Q: Can I service an RP system with an RP-1 license? A: No. RP-1 only allows observation. Service requires RP-3 or higher.

**Edge Cases**:
- The penny-smell from right-handed copper contamination persists 48 hours after the pipe is replaced. This is normal and does not indicate ongoing contamination.

**When to Escalate**:
Any system operating above 60 BPM, or any failure that does not match one of the diagnoses above, requires an RP-4 licensed engineer.
""",
        ),
    ],
}


def seed_v1(db) -> None:
    """Seed v1 benchmark tables with fictional SME data."""
    if db.query(models.V1SMEProfile).count() > 0:
        print("[seed] v1 tables already have data; skipping v1 seed.")
        return

    def new_id(prefix: str) -> str:
        return f"{prefix}_{_uuid.uuid4().hex[:8]}"

    v1_smes_data = [
        {
            "name": "Dr. Helga Voss",
            "specialization": "Zorblatt Crystals",
            "sub_areas": ["Crystal cultivation", "Voss Scale grading", "Z7 certification"],
            "contact_email": "zorblatt@test.thoth.dev",
        },
        {
            "name": "Ambassador Rex Tillby",
            "specialization": "Flumgarten Diplomacy",
            "sub_areas": ["Tillby Accords trade rules", "Greeting protocols", "Clinkmark exchange"],
            "contact_email": "flumgarten@test.thoth.dev",
        },
        {
            "name": "Chief Engineer Mona Wrench",
            "specialization": "Reverse Plumbing",
            "sub_areas": ["Wrench Paradox", "Contradictory Pipe installation", "RP-4 certification"],
            "contact_email": "reverse@test.thoth.dev",
        },
    ]

    spec_to_subject = {
        "Zorblatt Crystals": "Zorblatt Crystals",
        "Flumgarten Diplomacy": "Flumgarten Diplomacy",
        "Reverse Plumbing": "Reverse Plumbing",
    }

    for sme_data in v1_smes_data:
        sme = models.V1SMEProfile(sme_id=new_id("sme"), **sme_data)
        db.add(sme)
        db.flush()

        subject_key = spec_to_subject[sme_data["specialization"]]
        for title, content in KNOWLEDGE.get(subject_key, []):
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
            print(f"[seed] + v1 approved entry: {sme_data['specialization']} / {title}")

        print(f"[seed] + v1 SME: {sme_data['name']} ({sme_data['specialization']})")

    db.commit()
    print("[seed] v1 seed done.")


def main():
    init_db()
    db = SessionLocal()
    try:
        if db.query(models.Profile).count() > 0 or db.query(models.Subject).count() > 0:
            print("[seed] Old tables already have data; skipping old seed.")
        else:
            # Subjects
            subject_map: dict[str, models.Subject] = {}
            for name, desc in SUBJECTS:
                s = models.Subject(name=name, description=desc)
                db.add(s)
                db.flush()
                subject_map[name] = s
                print(f"[seed] + subject: {name}")

            # SMEs
            sme_map: dict[str, models.Profile] = {}
            for name, subject_name, expertise, contact in SMES:
                p = models.Profile(
                    name=name,
                    role="sme",
                    expertise_area=expertise,
                    contact_info=contact,
                )
                p.subjects = [subject_map[subject_name]]
                db.add(p)
                db.flush()
                sme_map[name] = p
                print(f"[seed] + SME: {name} — {subject_name} ({expertise})")

            # Users
            for name in USERS:
                db.add(models.Profile(name=name, role="user"))
                print(f"[seed] + user: {name}")

            # Admins
            for name, contact in ADMINS:
                db.add(models.Profile(name=name, role="admin", contact_info=contact))
                print(f"[seed] + admin: {name}")

            db.commit()

            # Approved knowledge entries + ChromaDB
            for subject_name, entries in KNOWLEDGE.items():
                subject = subject_map[subject_name]
                contributor = next(
                    (sme for sme_name, s_name, _, _ in SMES if s_name == subject_name for sme in [sme_map[sme_name]]),
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

            # Verify ChromaDB
            for subject_name, subject in subject_map.items():
                coll = vector_store.get_collection(subject.id)
                print(f"[seed] chroma collection {coll.name}: {coll.count()} docs")

            print("[seed] Done.")

        # V1 seed — independent guard inside seed_v1() itself
        seed_v1(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
