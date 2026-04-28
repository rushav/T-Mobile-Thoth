"""Seed the database with demo data for Project Thoth.

Run from the backend/ directory:
    python seed.py
"""
import sys
from pathlib import Path

# Make sibling modules importable when run as a script
sys.path.insert(0, str(Path(__file__).resolve().parent))

from database import SessionLocal, init_db
import models
from services import knowledge as knowledge_svc
import vector_store


SUBJECTS = [
    ("Coffee", "Coffee brewing, beans, equipment, drinks"),
    ("Milk Tea", "Boba, tea types, toppings, preparation methods"),
    ("Cars", "Vehicle maintenance, buying advice, common repairs"),
]

# (name, subject, expertise area, contact info)
SMES = [
    ("Lisa Li", "Coffee", "Brewing Methods", "lisa.li@gix.edu"),
    ("Mengting Li", "Milk Tea", "Boba & Tea Bases", "mengting.li@gix.edu"),
    ("Rushav", "Cars", "Maintenance & Buying", "rushav@gix.edu"),
]

USERS = ["Alex Rivera", "Jordan Lee"]
ADMINS = [("Pat Morgan", "pat.morgan@gix.edu")]


KNOWLEDGE = {
    "Coffee": [
        (
            "How to brew pour-over coffee",
            """**Topic**: Pour-over brewing method

**Key Information**:
- Use a 1:16 coffee-to-water ratio (e.g., 20g coffee to 320g water).
- Grind size should be medium — like sea salt, not too fine, not too coarse.
- Water temperature should be 195-205°F (90-96°C), just off the boil.
- Start with a bloom: pour 2x the coffee weight in water (40g for 20g coffee), wait 30-45 seconds for CO2 to release.
- Then pour in slow, concentric circles. Total brew time should be 3-4 minutes.
- If coffee tastes sour, grind finer or use hotter water. If bitter, grind coarser or use cooler water.

**Common Questions**:
Q: What's the best grinder for pour-over? A: A burr grinder gives consistent particle size. Blade grinders create uneven grounds which leads to uneven extraction.
Q: Do I need a gooseneck kettle? A: Highly recommended. It gives you control over pour speed and placement.
Q: How do I know if my grind size is right? A: If total brew time is under 3 minutes, grind finer. Over 4 minutes, grind coarser.

**Edge Cases**:
- Darker roasts need slightly lower temperature (190-195°F) and coarser grind.
- Light roasts can handle higher temps.

**When to Escalate**:
Questions about specific equipment recommendations or troubleshooting a specific grinder model.
""",
        ),
        (
            "Types of coffee beans and roast levels",
            """**Topic**: Coffee bean varieties and roasting

**Key Information**:
- Two main species: Arabica (smoother, more complex, ~60% of world production) and Robusta (stronger, more bitter, more caffeine, ~40%).
- Light roast: light brown, no oil on surface, highest acidity, most origin flavor, highest caffeine by volume.
- Medium roast: medium brown, balanced flavor, slightly less caffeine than light.
- Dark roast: dark brown to almost black, oily surface, bold/smoky flavor, lowest acidity, lowest caffeine by volume.
- Single origin means beans from one farm/region. Blends combine beans from multiple origins for consistency.
- Popular origins: Ethiopia (fruity, floral), Colombia (nutty, chocolate), Brazil (low acidity, nutty), Kenya (bright, berry-like).

**Common Questions**:
Q: Which roast has the most caffeine? A: Light roast has slightly more caffeine per scoop because the beans are denser. The difference is small.
Q: What's the difference between Arabica and Robusta? A: Arabica is smoother with more flavor complexity. Robusta is stronger, more bitter, has about 2x the caffeine, and is cheaper to grow.

**Edge Cases**:
- "Specialty coffee" specifically means Arabica beans scoring 80+ on a 100-point scale by certified graders.

**When to Escalate**:
For questions about roasting at home or sourcing green beans, connect with a roasting specialist.
""",
        ),
    ],
    "Milk Tea": [
        (
            "How to make classic boba milk tea",
            """**Topic**: Classic brown sugar boba milk tea

**Key Information**:
- Base tea: use strong-brewed black tea (Assam or Ceylon work best). Brew 2x stronger than normal — you're diluting with milk and ice.
- Tea to milk ratio: about 2:1 tea to milk. Whole milk gives the creamiest result. Oat milk is the best non-dairy alternative.
- Sweetness: traditionally uses brown sugar or simple syrup. Most shops offer 0%, 25%, 50%, 75%, 100% sweetness levels.
- Boba (tapioca pearls): cook in boiling water 15-20 minutes, then soak in brown sugar syrup for at least 30 minutes for flavor and that glossy look.
- Serve over ice. Shake or stir vigorously for a frothy texture.
- Boba should be used within 4 hours — they harden after that.

**Common Questions**:
Q: Why are my boba pearls hard in the center? A: They were undercooked. Boil longer (20+ min) and make sure water is at a rolling boil the entire time.
Q: Can I make boba ahead of time? A: Cook them same-day. They don't keep well overnight even in syrup.
Q: What's the difference between boba and popping pearls? A: Boba are chewy tapioca balls. Popping pearls are juice-filled spheres that burst when bitten — completely different texture.

**Edge Cases**:
- Quick-cook boba (5 min) exist but the texture is noticeably worse than traditional pearls.

**When to Escalate**:
For sourcing specific brands of tapioca pearls or commercial-scale preparation, connect with a specialist.
""",
        ),
        (
            "Tea types used in milk tea",
            """**Topic**: Different tea bases for milk tea drinks

**Key Information**:
- Black tea (Assam, Ceylon): most common base. Strong, malty flavor that holds up to milk. Default for classic milk tea.
- Oolong: semi-oxidized, floral and smooth. Great for lighter milk teas. Popular in Taiwanese-style shops.
- Jasmine green tea: light, fragrant. Used in fruit tea combinations more than milk tea.
- Thai tea: uses Assam tea with star anise, cardamom, and orange food coloring. Mixed with condensed milk and evaporated milk.
- Matcha: Japanese green tea powder. Whisked into hot water or milk for matcha latte. Not technically "milk tea" but commonly on the same menus.
- Taro: not actually a tea — it's a root vegetable. Taro powder or paste is blended with milk for a sweet, purple, nutty drink.

**Common Questions**:
Q: Which tea is best for a beginner? A: Classic Assam black tea milk tea at 50% sweetness. Balanced and approachable.
Q: Is taro milk tea actually tea? A: Usually not. Most shops blend taro powder with milk. Some add a splash of green tea but it's optional.

**Edge Cases**:
- "Cheese tea" uses a savory cream cheese foam on top of tea (usually oolong or green). Sounds weird but it's a major trend.

**When to Escalate**:
Questions about specific shop recipes or regional variations may need a specialist.
""",
        ),
    ],
    "Cars": [
        (
            "Basic car maintenance schedule",
            """**Topic**: Routine maintenance every car owner should know

**Key Information**:
- Oil change: every 5,000-7,500 miles for conventional oil, 7,500-10,000 for synthetic. Check your owner's manual.
- Tire rotation: every 5,000-7,500 miles. Extends tire life by evening out wear patterns.
- Tire pressure: check monthly. Correct PSI is on the sticker inside driver's door jamb, NOT on the tire sidewall.
- Brake inspection: every 12,000-15,000 miles. Brake pads typically last 30,000-70,000 miles.
- Air filter: replace every 15,000-30,000 miles. A clogged filter reduces fuel efficiency.
- Coolant flush: every 30,000 miles or 5 years, whichever comes first.
- Battery: typical lifespan is 3-5 years. Have it tested annually after year 3.

**Common Questions**:
Q: What happens if I skip an oil change? A: Oil breaks down and loses lubricating properties. Leads to engine sludge, increased wear, potentially engine failure. Most important maintenance item.
Q: How do I know when I need new brakes? A: Squealing when braking (wear indicator), grinding (pads are gone — urgent), or car pulling to one side.

**Edge Cases**:
- Short trips in cold weather may need more frequent oil changes — engine doesn't fully warm up, leading to moisture contamination.

**When to Escalate**:
For model-specific service intervals or unusual symptoms, consult a certified mechanic.
""",
        ),
        (
            "What to check before buying a used car",
            """**Topic**: Used car buying guide

**Key Information**:
- Always get a vehicle history report (Carfax or AutoCheck). Check for: accidents, title status, number of owners, service records.
- Exterior: look for mismatched paint, uneven panel gaps, rust around wheel wells.
- Interior: test ALL electronics. Check for water stains on ceiling (flood damage). Smell for mold.
- Under the hood: check oil (should be amber/brown, not black or milky). Look for leaks. Check belt condition.
- Test drive: highway AND city. Listen for unusual sounds. Test brakes hard. Feel for vibrations.
- Always get a pre-purchase inspection from an independent mechanic ($100-200, can save thousands).
- Check KBB and Edmunds for fair market value.

**Common Questions**:
Q: How many miles is too many? A: Maintenance matters more than mileage. A well-maintained 100k highway car can be better than a neglected 50k city car. Average is 12,000-15,000 miles/year.
Q: Dealer or private seller? A: Dealers offer more protections and sometimes warranties but charge more. Private sellers are cheaper but buyer-beware.

**Edge Cases**:
- If the seller won't let you get a pre-purchase inspection, walk away. No legitimate reason to refuse.

**When to Escalate**:
For legal/title disputes or financing questions, involve a specialist.
""",
        ),
    ],
}


def main():
    init_db()
    db = SessionLocal()
    try:
        if db.query(models.Profile).count() > 0 or db.query(models.Subject).count() > 0:
            print("[seed] Database already has data; skipping. Delete data/thoth.db to reseed.")
            return

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
    finally:
        db.close()


if __name__ == "__main__":
    main()
