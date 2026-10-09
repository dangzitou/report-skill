# Writing daily & weekly reports

> Distilled from 20+ highly-saved Xiaohongshu (RedNote) posts by big-tech PMs, engineering leads and interns who got return offers, plus the Pyramid Principle / PREP / SCQA.
> This guide is also the style contract report-skill hands to the AI.

## 0. Know your reader

- **Your lead has 30 seconds.** They manage many people and skim. They want three things: **progress, problems, plan**.
- **Communication is visibility.** Good work that nobody can see doesn't get counted. The report is how your lead sees your week.
- **Leaders buy peace of mind.** "Stable" and "in progress" say nothing; "zero incidents this week after the migration" lets them sleep.
- **First impressions stick.** Put the most important conclusion in the first line.
- **Hand them a multiple-choice question, not an essay question.** A problem without options just pushes the work back up.

## 1. Daily vs weekly vs monthly

| Report | Focus | In one line |
| --- | --- | --- |
| Daily | **Facts** | Where things stand, what's at risk, what's next. No reflections |
| Weekly | **Change** | What moved, what got stuck, what's new since last week. **Not five dailies glued together** |
| Monthly | **Meaning** | What outcome and value it produced, what you learned, what you'll change |

## 2. Nine rules

1. **Lead with the conclusion (PREP / pyramid).** Start with a one-line summary, then the key results, then the details.
2. **Outcomes, not activity.**
   - ❌ Worked on login
   - ✅ Shipped phone + OTP login, self-tested (2d)
3. **Action + result + number.** Counts, time, percentages, lines changed, blast radius. Tie numbers to **time and money** where you honestly can.
4. **Big rocks first.** Put the most important project first and fold the small chores into one line.
5. **Report what you prevented.** Bugs caught, risks removed and incidents that never happened are value too.
6. **Problem = symptom → cause → options → ask.** Offer two options and say which one you lean toward.
7. **Plans must be checkable.** Keep it to 1–3 items, each with a deadline and a deliverable. "Keep pushing X" is not a plan.
8. **Neutral tone.** Cross-team issues are facts and status only, with no blame and no venting.
9. **Phone-friendly.** Use short lines and numbering, and bold the key conclusions.

## 3. Bonus points (weekly)

- **Leverage:** docs, scripts and tools other people can reuse.
- **Negative results count:** "[Not recommended] approach A doesn't converge on current data, likely because …"
- **Growth:** one line on what you learned and where you already applied it.
- **Alignment:** tie the plan to the team's goals or metrics.

## 4. Red lines for AI-written reports

- **Never invent.** If a number, outcome or business impact is not in the source data, leave it out or mark it `[to confirm]`. The AI organizes the facts; the human confirms them.
- **Don't inflate.** Tweaking one config value is not "optimized system performance". Leads notice, and you lose trust.
- **Get attribution right.** Don't claim teammates' work, and when it's team work, state your own part.
- **Redact** secrets, credentials, customer data and anything sensitive.
- **No AI voice.** Skip buzzwords like "leverage", "empower", "seamless" and "robust", and skip triplets and exclamation marks.
