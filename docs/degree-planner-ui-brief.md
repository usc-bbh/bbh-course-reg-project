# Four-Year Degree Planner — UI Brief (Francis)

_Written 2026-08-17. Everything you need to start is in this file. Where a decision is yours, it says so._

---

## What you're building

The **Four-Year Degree Planner**.

A student gives it their situation and a proposed multi-year plan; it tells them whether
that plan gets them to a degree, and if not, what's missing.

**This is NOT the Next-Semester Validator.** That's Agastya and Tanzil's workflow right now. — it takes one proposed
semester and checks whether the student can register for it. Different tool, different
person, don't build it. 

If you find yourself building a "can I register for these classes
next term" screen, stop, you've drifted into Agastya's project.


Tanzil's wireframe (below) contains **both** tools. You only want the four-year planner
half. Cut the other half out. Also cut the placeholder she created for an AI chatbot.

---

## Start here

Tanzil built a wireframe in v0/Vercel that is already good:

**https://v0-plansc-course-planner.vercel.app/**

Use it for layout and flow. You are not married to it — improve it where you see something better — but don't start from a blank page when a decent design already exists.

Two other things already exist, use them:

| What                                                | Use it for                                                                 |
| --------------------------------------------------- | -------------------------------------------------------------------------- |
| Tanzil's validator GUI (in this repo, `validator/`) | Look and feel. It's already styled in USC cardinal-and-gold. Match it.     |
| Agastya's running Next-Semester Validator prototype | Ask him questions about what worked and what didn't. Don't copy its scope. |

---

## Decision you own: Vercel or Netlify

The team nominally picked Netlify, but that was Agastya's choice and there was no strong reason behind it. Tanzil's wireframe is on Vercel. Both are defensible.

**You decide which to use, and decide before Thursday night's all-hands.** Spend an hour on it, not a
day — and don't wait for the decision to start building. Get something running on whichever one you
are leaning toward today; if you switch, you'll switch a small app, which is cheap. Here's how to spend
that hour:

- Talk to **Agastya** — he's the Netlify person on the team.
- Talk to **Tanzil** — she's the Vercel person, and she built the thing you're starting from.
- Post one message in the channel saying which you picked and the one-line reason.

Then stop thinking about it and build.

**The thing that makes this choice cheap:** whichever you pick, use **no platform-specific features**. No serverless functions, no platform-specific auth, no edge middleware. If everything runs in the browser, moving between the two later is about twenty minutes of work instead of a rewrite.

If you pick Vercel and start from Tanzil's wireframe: no porting at all. If you pick Netlify:
be aware that a Next.js app built for Vercel needs the `@netlify/plugin-nextjs` adapter, and the parts that usually break are middleware, image optimization, and server components. The way around all of it is to not use any of them — a plain front end that does its work in the browser deploys anywhere. Claude can help you with this; tell it which of the two you chose and paste any build error you hit.

---

## Hard constraint: the student's data never leaves their browser

We really really want to avoid handling PII if we can. A STARS report contains a real student's academic record. It gets read and processed **client-side only**. Nothing derived from it goes to a server.

Practically: all the checking logic runs in the browser. The only thing that may come from a server is public catalogue data (degree requirements, course lists). Design accordingly from day one — retrofitting this is painful.

---

## Two things you must stub, not build

You are going to want data you don't have yet. Do not wait for it, and do not build it
yourself. In both cases: write a function that ignores its arguments and returns a fixed,
hard-coded object. Build the whole UI against those fixed objects.

### 1. The analysis layer

This is the thing that will eventually decide whether a plan works. It does not exist yet.

Write a single function — call it `analyzePlan(...)` — that ignores everything you pass it and
returns **the same hard-coded result every time**. Make that fixed result rich enough that
every screen has something to render:

- a few semesters with courses in them
- at least one requirement marked satisfied
- at least one requirement marked **not** satisfied, with a reason
- at least one warning ("this course is only offered in the fall")

Then build every screen against it.

### 2. The parsed STARS report

Abhi and Agastya are building the STARS parser. It isn't finished and its exact output shape
isn't settled.

So write a function that returns a **fake parsed STARS object** — courses completed, class
standing, declared major, catalogue year, whatever you need — and build against that.

**This is the useful part:** whatever you find yourself needing from that fake object is
exactly what you should be asking Abhi and Agastya to produce. You'll almost certainly need
things they haven't planned for. That's the point. Find the mismatch now, while it's cheap.

---

## Thursday night's all-hands

We want to talk about your progress there, so come with something to show — even a rough page with
the stub data in it. Two things to be ready to say:

1. Which platform you picked and why (one sentence).
2. What you needed from the STARS parser or the analysis layer that doesn't exist yet. That's the
   most useful thing you can bring, because it's what the rest of the team has to react to.

Working and ugly beats polished and unfinished. Nobody is expecting a finished tool two days in.

---

## Definition of done (by 2026-08-24)

1. **A running, deployed four-year degree planner** on whichever platform you picked. A
   student can enter their situation and a proposed plan and get a (fake but plausible)
   answer back. Every screen renders. Nothing crashes.
2. **Half a page written down**, in `docs/degree-planner-ui-notes.md`, covering three things:
   - **What the page captures from the student.** Just the list of facts — major, minor,
     catalogue year, courses already taken, and so on. Not how you collected them; whether
     it's a dropdown or a text box is your business.
   - **The fixed object your analysis stub returns.** Paste it in. That's your statement of
     what you need the real analysis layer to hand back.
   - **What you needed and couldn't get.** Anything you had to invent, guess, or fake because
     nobody could tell you. Be specific and don't be shy — this list is genuinely one of the
     more useful things you can produce, because several of these are open questions nobody
     has answered yet.

Write item 2 **at the end, from what you actually built.** Don't write it first and then build
to it. If they disagree, what you built wins and the notes get corrected.

---

## Things that will waste your week

- **Building Agastya's tool by mistake.** Reread the top of this file if you're unsure.
- **Spending three days on porting.** If the platform decision is eating your week, you picked
  wrong; take the one where the code already runs.
- **Waiting for the STARS parser, or for the analysis layer.** Both are stubs. You are not
  blocked on anyone.
- **Making it pretty before it works.** Match the validator's colors and move on.

---

## Who to ask

- **Netlify / deployment** — Agastya (may be slow to reply; don't block on him)
- **The wireframe, Vercel, anything React** — Tanzil
- **STARS parser output** — Abhi and Agastya
- **Anything else** — post in the channel; Vishal is back 2026-08-24

Claude can help with all of this. Paste this file in when you start a session with it so it
knows what you're building and what the constraints are.
