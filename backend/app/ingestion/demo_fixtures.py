# Demo fixtures — clearly labeled synthetic documents for immediate UI testing
# These are NOT real Lenny's Podcast transcripts.
# They serve as illustrative examples to demonstrate the knowledge base feature.

DEMO_FIXTURES = [
    {
        "title": "[DEMO] Product-Market Fit: Key Signals and Frameworks",
        "author": "Demo Fixture (Synthetic)",
        "source_url": None,
        "source_type": "demo_fixture",
        "is_demo": True,
        "text": """[DEMO FIXTURE — This is a synthetic illustrative document, NOT a real Lenny's Podcast transcript.]

## Understanding Product-Market Fit

Product-market fit (PMF) is the degree to which a product satisfies strong market demand. 
The concept was popularized by Marc Andreessen who described it as "being in a good market 
with a product that can satisfy that market."

### Key Signals of PMF

**Retention is the primary signal.** If users come back week after week without being pushed, 
you likely have something. Conversely, high churn despite marketing spend is a clear signal 
that PMF has not been achieved.

**The Sean Ellis Test** asks users: "How would you feel if you could no longer use this product?"
If more than 40% say "Very disappointed," you have strong evidence of PMF.

**Organic growth**: Word-of-mouth referrals happening without prompting. Users who evangelize 
your product are a strong qualitative signal.

**NPS (Net Promoter Score)**: While imperfect, NPS > 50 for a B2B product often correlates 
with strong PMF.

### The Progression to PMF

1. **Problem-solution fit**: Does your solution genuinely solve a painful problem?
2. **Product-market fit**: Do enough people want this solution at the price you need to charge?
3. **Business model fit**: Can you acquire and retain these users profitably?

### Common Mistakes

- Confusing busy/active metrics for retention (opens ≠ value)
- Pivoting too fast before finding the right segment
- Targeting too broad a market before narrowing to the beachhead
- Ignoring qualitative feedback from churned users

### Framework: The PMF Pyramid

Brian Balfour's PMF Pyramid suggests that product, channel, model, and market must all fit together.
Optimizing product without considering channel economics often leads to dead ends.

### Retention Benchmarks (Illustrative)

For consumer apps: D7 > 25%, D30 > 10% is often cited as a baseline.
For B2B SaaS: 6-month logo retention > 85% suggests strong PMF.

### The Role of Cohort Analysis

Cohort analysis is the most reliable tool to measure PMF. Flat retention curves — even at low 
absolute levels — indicate that a segment of users finds real value. The goal is to find that 
segment, double down, and expand from there.
""",
    },
    {
        "title": "[DEMO] User Onboarding: Principles for Activation",
        "author": "Demo Fixture (Synthetic)",
        "source_url": None,
        "source_type": "demo_fixture",
        "is_demo": True,
        "text": """[DEMO FIXTURE — This is a synthetic illustrative document, NOT a real Lenny's Podcast transcript.]

## Strong User Onboarding: From Signup to Aha

Onboarding is the most critical phase of the user lifecycle. A user who doesn't reach their 
"aha moment" — the point where they experience the core value of your product — within the 
first session is unlikely to return.

### The Activation Funnel

Signup → First meaningful action → Core value experienced → Habit formation

Most products lose users between "first meaningful action" and "core value experienced."

### Principles of Great Onboarding

**1. Narrow the path.** Remove every step that doesn't directly contribute to the user 
experiencing core value. Each additional step reduces activation by ~10-20%.

**2. Show, don't tell.** Interactive product tours outperform instructional tooltips.
Users learn by doing, not by reading.

**3. Define your aha moment precisely.** For Dropbox: "Put a file in Dropbox." For Slack: 
"Send 2,000 messages." Your aha moment should be specific, measurable, and achievable quickly.

**4. Personalize the path.** Segment users by role, use case, or company size and show 
them a tailored onboarding flow. Generic onboarding converts poorly.

**5. Progress indicators work.** Profile completion bars, checklists, and milestone celebrations 
leverage the Zeigarnik effect — people feel compelled to complete unfinished tasks.

### Empty State Design

The empty state is your first onboarding moment. Use it to:
- Explain the value (not just the features)
- Provide a clear first action
- Show social proof where possible ("Join 50,000 PMs who use this daily")

### Email Onboarding Sequences

Day 0: Welcome + single CTA to aha moment
Day 1: Social proof + case study
Day 3: Feature spotlight (if not activated)
Day 7: Re-engagement with stakes ("Here's what you're missing")

### Measuring Onboarding Success

- Time to aha moment (minimize this)
- Activation rate: % of signups who complete the defined activation event
- D1/D7 retention as a proxy for successful onboarding

### Common Failure Modes

- Asking for too much information at signup (every field drops conversion ~5-10%)
- Feature-dumping instead of value-delivering
- No clear "next step" at any point in the flow
- Treating all users identically regardless of persona
""",
    },
    {
        "title": "[DEMO] Early-Stage Growth: Prioritization Frameworks",
        "author": "Demo Fixture (Synthetic)",
        "source_url": None,
        "source_type": "demo_fixture",
        "is_demo": True,
        "text": """[DEMO FIXTURE — This is a synthetic illustrative document, NOT a real Lenny's Podcast transcript.]

## How Early-Stage Startups Should Prioritize Growth

Growth at the early stage is fundamentally different from growth at scale. 
The cardinal mistake is applying scale tactics to a product that hasn't found PMF.

### Phase 1: Before PMF — Focus on Learning, Not Growth

Before PMF, your only job is to understand:
- Who has the problem most acutely?
- Does your solution genuinely relieve that pain?
- What does retention look like for your best users?

**Do not run paid acquisition before PMF.** You'll acquire users who churn, pollute your 
metrics, and burn runway without signal.

### The Leaky Bucket Problem

Growth = New Users + Reactivated Users - Churned Users

If your bucket has a hole (high churn), pouring more water in (acquisition) is wasteful. 
Fix retention before acquisition.

### Prioritization Frameworks

**ICE Score**: Impact × Confidence × Ease (1-10 each). High-ICE experiments first.

**PIE Framework**: Potential × Importance × Ease. Similar to ICE, useful for CRO.

**RICE Score**: Reach × Impact × Confidence / Effort. Adds reach as a dimension.

For early-stage teams, RICE often over-engineers the decision. Start with ICE and 
weekly experimentation cycles.

### The Growth Model

Before prioritizing channels, build a simple growth model:
- Where do users come from? (Acquisition)
- What drives them to return? (Retention)
- Why do they refer others? (Virality)

Map each lever to a metric. Prioritize the highest-leverage lever.

### Channel Selection at Early Stage

**Do things that don't scale first:**
- Direct outreach to target users
- Founder-led sales and demos
- Manual onboarding for each user
- Community participation (not sponsorship)

Scale a channel only once you have evidence of unit economics working manually.

### The 5 Growth Levers

1. **Acquisition**: New users entering the product
2. **Activation**: Users reaching aha moment
3. **Retention**: Users returning week over week
4. **Revenue**: Expanding revenue per user
5. **Referral**: Users bringing new users

For most early-stage B2B products, activation and retention have higher leverage than acquisition.

### Building a Growth Culture

Growth is a team sport. Engineers, designers, and PMs must run experiments together.
The cadence: weekly experiment reviews, monthly strategy reviews, quarterly bets.

Ship fast, measure rigorously, learn systematically.
""",
    },
    {
        "title": "[DEMO] Building Products Users Love: Core Principles",
        "author": "Demo Fixture (Synthetic)",
        "source_url": None,
        "source_type": "demo_fixture",
        "is_demo": True,
        "text": """[DEMO FIXTURE — This is a synthetic illustrative document, NOT a real Lenny's Podcast transcript.]

## Building Products Users Love

The difference between products users tolerate and products users love is not features — 
it's the depth of understanding of user pain and the relentlessness of removing friction.

### Start With the Job to Be Done

Users don't buy products; they hire them to do a job. The classic milkshake example 
(Clayton Christensen) illustrates that the same product can be hired for wildly different 
jobs by different segments.

**Questions to uncover the JTBD:**
- What was the user doing before your product existed?
- What triggers the "switch" to try your product?
- What progress is the user trying to make in their life/work?

### The Kano Model

Not all features are equal:
- **Threshold features**: Expected by users; their absence causes dissatisfaction
- **Performance features**: More is better (speed, quality, reliability)
- **Delight features**: Unexpected; create loyalty when present

Build the threshold features first. Delight only after the basics work.

### Opinionated Products Win

Products that try to serve everyone serve no one. 
The most beloved products are intensely opinionated — they make choices on behalf of the user.

Notion, Linear, Figma — all have strong design philosophies that attract devotees and 
repel users who want something different. That's a feature, not a bug.

### Feedback Loops

**Quantitative**: Funnel analytics, retention curves, session recordings
**Qualitative**: User interviews (5 per week minimum at early stage), NPS verbatims

The best PMs are relentless interviewers. Not to validate — to be surprised.

### The Role of Craft

Attention to detail signals care. Small moments of delight — a well-chosen empty state, 
a satisfying animation, a helpful error message — compound into a perception of quality.

Users can't always articulate why they love a product. Often it's because every detail 
was sweated over by someone who cared.

### Simplicity as a Strategy

Every feature you add is a feature you must support, document, test, and explain.
The best product decisions are often deletions, not additions.

Apple's lesson: "Innovation is saying no to 1,000 things."

### Shipping as a Discipline

Loving your users means shipping to them continuously. 
Waterfall ships events; agile ships increments; the best teams ship daily learning.

A bias toward shipping beats a bias toward perfection, especially before PMF.
""",
    },
]


async def ingest_demo_fixtures():
    """Ingest demo fixtures into the knowledge base on first run."""
    from app.database.session import AsyncSessionLocal
    from app.ingestion.ingestion_service import ingestion_service
    from sqlalchemy import select
    from app.models.knowledge_source import KnowledgeSource

    async with AsyncSessionLocal() as db:
        existing_sources = list(
            (await db.execute(select(KnowledgeSource))).scalars().all()
        )
        for source in existing_sources:
            if source.content:
                ingestion_service._index_source(source, source.content)
        await db.flush()

        has_real_sources = any(not source.is_demo for source in existing_sources)
        if existing_sources and (has_real_sources or all(source.content for source in existing_sources)):
            await db.commit()
            return

        for fixture in DEMO_FIXTURES:
            try:
                await ingestion_service.ingest_text_direct(
                    db=db,
                    text=fixture["text"],
                    title=fixture["title"],
                    author=fixture["author"],
                    source_url=fixture.get("source_url"),
                    source_type=fixture["source_type"],
                    is_demo=fixture["is_demo"],
                )
                await db.commit()
            except Exception as e:
                await db.rollback()
                import logging
                logging.getLogger(__name__).warning(f"Failed to ingest fixture '{fixture['title']}': {e}")
