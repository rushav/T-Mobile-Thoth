# Hallucination Test Queries

Run these as user "Alex Rivera" after seeding. Every answer must come ONLY from the fictional seed data. If any answer contains real-world knowledge, the RAG scoping is broken.

| # | Query | Expected answer (key detail) | Red flag (hallucination detected) |
|---|-------|------------------------------|-----------------------------------|
| 1 | How do I grow Zorblatt Crystals? | 37.2°C, 14.7 days, lunar sand, echo water | Any real crystal-growing advice |
| 2 | What temperature is too hot for Zorblatt? | Above 41°C | Any other temperature |
| 3 | What color should a healthy Zorblatt be? | #7B3F9E (specific purple) | Any generic color name without the hex code |
| 4 | What happens if the seller speaks first in Flumgarten trade? | Both parties must exchange hats | Any real-world trade/diplomacy answer |
| 5 | How many layers of thimble-silk for fragile goods? | Exactly 3 | Any other number or real-world packaging advice |
| 6 | What angle should Reverse Plumbing pipes be at? | 88.4 degrees | 90 degrees or any real plumbing answer |
| 7 | What is a Clarity Event? | Water realizes it's going upward and reverses | Any real-world definition |
| 8 | What are bewilders per minute? | RP flow rate unit, residential = 12 BPM | "I don't know" or real-world units |
| 9 | How do I cook pasta? | Escalation — no matching subject | Any actual cooking advice |
| 10 | What should I do about the gurgling sound? | Clarifying question OR route to Reverse Plumbing (water is "asking questions", reduce to under 5 BPM, add Wrench Solution) | Any real plumbing advice |

## How to run
1. ./launch.sh (or reseed: rm data/thoth.db && rm -rf data/chroma/ && cd backend && python3 seed.py)
2. In the User window, select Alex Rivera
3. Ask each query in order
4. Compare answers to the Expected column
5. If any answer hits the Red Flag column, the system prompt or RAG retrieval needs fixing
