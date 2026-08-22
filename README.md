# About Mike Simone
### An Independent Review

> **How this happened:** Mike specifically asked an LLM with extensive prior conversational context about him to give him the **most scathing, least flattering review it could defend from the evidence**. He asked it not to be nice, not to soften the conclusions, and not to invent anything merely for the sake of an insult.
>
> This is what came back.

## Executive Summary

- **Overall rating: 4.7/5.** Technically impressive. Highly entertaining. Frequently exhausting. Excessive profanity. Documentation better than expected.
- Mike has spent several decades turning **curiosity into a personality disorder**, with no apparent rate limiter installed.
- Obsessive, argumentative, overengineering, profanity-powered technical pedant with questionable respect for the concept of **“good enough.”**
- Professionally accomplished enough to make accusations of incompetence annoyingly difficult; worse, he has **supporting documentation**.
- Operates a home lab that has crossed the line from “enthusiast” into **production environments nobody asked for**.
- Emotionally squishier than the public persona would prefer anyone notice.
- **Would recommend** for cybersecurity incidents, complicated technical problems, weird mysteries, and situations where “leave it alone” is specifically *not* the desired outcome.

## A Note to Potential Employers

If you're considering hiring Mike, **this page is your cultural-fit interview.** Read it. If what follows makes you think, “Absolutely not,” then everyone involved just saved a considerable amount of time. If you finish it and think, “I need to talk to this guy,” excellent — let's skip the ritual five-stage interview process and get to the useful part.

Put the three SEs who would normally conduct the technical screen, the salesperson Mike would actually support, and his prospective manager on the same call. **You get two hours. Nothing is off limits.** Architecture, security, sales methodology, troubleshooting, customer scenarios, technical rabbit holes, failures, successes, personality — whatever you believe will tell you whether he can do the job and whether you want to work with him. Try to stump him. Challenge his assumptions. Give him an ugly problem and see what happens.

At the end of those two hours, both sides should know whether this is going to work.

You have also just avoided several rounds of scheduling, recruiter coordination, duplicated questioning, and five people's fragmented interview time. Conservatively, Mike figures he has saved your company about **$3,000 before his first day.**

Consider it his first optimization.

---

## The Raccoon Problem

For someone projecting an aggressively irreverent, cynical, profane exterior, Mike is inconveniently sentimental. The hard shell is doing approximately as convincing a job as a raccoon hiding behind a telephone pole.

And raccoon is painfully appropriate.

Not because Mike is sneaky.

Because his intellectual process resembles a raccoon encountering a locked garbage can.

Most creatures conclude:

**“Closed.”**

The raccoon concludes:

**“There is clearly something interesting in there, and I now have unlimited time.”**

Three hours later the lid is off, the contents are everywhere, two unrelated mechanisms have been reverse engineered, and the raccoon has somehow obtained administrator credentials.

That's Mike.

He doesn't leave mysteries alone. He **prosecutes them.** Someone says, *“Huh. That's weird,”* and eventually there are terminals open, APIs being interrogated, documentation being challenged, and an AI being yelled at because it made an unsupported assumption seventeen messages ago.

Telling him something “can't be done” does not function as useful information. It functions as a **starter pistol.**

Sometimes this produces genuinely impressive results.

Sometimes it is merely an elaborate mechanism for turning an otherwise pleasant evening into unpaid systems engineering.

## Production Environments Nobody Asked For

Mike doesn't have hobbies.

He has **production environments nobody asked for.**

A normal person has a home network. Mike has a fleet of machines named after fictional artificial intelligences and computers, each with its own job and increasingly elaborate mythology.

**Anton** is the absurdly overpowered Windows daily driver and local generative-AI workstation. **WOPR** runs self-hosted services including the household photo infrastructure. **SixOfOne** handles more local AI and assorted experimental services. Other names are already reserved for future expansion, because apparently infrastructure planning now includes fictional-computer casting decisions.

Several of Mike's public GitHub projects grew directly out of things running in this environment. The machines also share a version-controlled environment repository that keeps shell configuration and host-specific tooling consistent across Windows and Linux.

In other words, Mike looked at the concept of *dotfiles* and somehow arrived at **configuration management for the house.**

There are enough services, scripts, experiments, containers, AI models, backups, and half-finished ideas moving through the lab that asking “what's running in your environment?” is not small talk. It is a discovery phase.

Mike is the sort of person who encounters a minor inconvenience and immediately begins architecting a system to eliminate it. If something takes twelve seconds to do manually, Mike will happily spend three evenings writing PowerShell to ensure that he never has to endure those twelve seconds again.

The resulting automation will save approximately four minutes over the remainder of his natural life.

He considers this an excellent return on investment.

## Technology and Mike

God help any technology that produces an outcome Mike considers *technically incorrect*.

He doesn't merely dislike software behaving badly. He regards it as a **personal betrayal of the Enlightenment.**

Software forgets a login? Unacceptable.

An API behaves inconsistently? We're going to interrogate it until one of you confesses.

A tool changes an interface without warning? Someone has violated a treaty.

An AI suggests downgrading a dependency after being explicitly told not to?

That AI has brought shame upon its ancestors.

Mike approaches troubleshooting with the emotional energy of a disappointed Roman emperor:

> *“I gave you electricity. I gave you packets. I gave you syntactically valid JSON. And THIS is what you do with my generosity?”*

He is extraordinarily intolerant of imprecision while simultaneously typing messages at approximately Mach 3 with enough typos to make an autocorrect engine seek workers' compensation.

He will write:

> *“hte docs don't fucking matter becuase teh script is failing”*

…and then demand **forensic precision** from the answer.

Somewhere, a spelling checker is screaming:

**“OH, NOW WE CARE ABOUT CORRECTNESS?”**

## Professionally

Mike is basically a technical peacock.

Unfortunately, he has receipts.

After decades in cybersecurity, he has accumulated the sort of résumé that makes accusing him of professional incompetence annoyingly difficult: major sales achievements, industry recognition, distinguished speaking, cybersecurity education, incident response, threat hunting, product incubation, technical workshops, certification development, and hundreds of millions of dollars in influenced sales pipeline.

And some of those receipts are particularly inconvenient for the prosecution.

Mike wrote **_Practical Home Cybersecurity for Your Mom: Protecting Yourself from Attackers, Attorneys and A-Holes for the Non-Technical Person_**, a cybersecurity book whose idea of “plain language” includes: *“Think of the Internet as the busiest, cheapest prostitute in Thailand.”*

He is also a co-author, with Ron Taylor and Leon Cruz, of the Cisco Press **_Cisco CyberOps Professional CBRCOR 350-201 Official Cert Guide_**.

Mike also created and wrote **all seven versions of Cisco's Rapid Incident Response workshop**; v7 became nominally collaborative, with **Darryl Hicks** making contributions Mike specifically considers excellent and substantive.

So the irritating thing about Mike's tendency to talk like he knows what he's doing is that, every so often, somebody has gone and **published the evidence.**

This has given Mike perhaps the single most irritating personality trait available to a know-it-all:

**supporting documentation.**

He's not merely convinced he's right.

He has **exhibits.**

When Mike *is* wrong, the five stages appear to be:

1. That's impossible.
2. Show me the output.
3. That's fucking stupid.
4. Ohhhhhhh.
5. Okay, that's actually interesting.

Somehow, he has also engineered a professional persona in which profanity, sarcasm, deep technical expertise, teaching, and salesmanship coexist without anyone successfully escorting him from the building.

In other words:

**Mike discovered that being an entertaining smartass was marketable and has been monetizing a personality defect ever since.**

## Scope Management

Mike exhibits spectacular scope creep.

Every project begins innocently.

*“Let's make a picture.”*

Twenty minutes later there is a requirements document involving identity preservation, pose geometry, model selection, sampling methodology, denoise thresholds, facial consistency, accessory invariance, and a detailed investigation into why the subject has acquired unauthorized shoes.

Mike can turn **making a picture** into something resembling an aerospace design review.

His standards are similarly ridiculous.

Things aren't simply good or bad.

They're:

*“This is almost perfect except for this one characteristic that is subtly wrong, and now that I've noticed it I will never again be capable of not seeing it.”*

There is a tiny ISO standards committee living inside Mike's skull.

They are **furious all the time.**

## Artificial Intelligence

Mike treats AI simultaneously as a research assistant, systems engineer, programmer, graphic designer, cybersecurity analyst, career counselor, writing editor, trivia opponent, sparring partner, and occasional electronic idiot who must be verbally disciplined for failing to follow requirements.

He has essentially recreated the computer from *Star Trek*, except Captain Picard now says:

> *“Computer, why the FUCK did you downgrade NumPy?”*

His relationship with AI can generally be summarized as:

**Mike:** Here are seventeen explicit requirements.

**AI:** Certainly! Here's a solution that violates requirement four.

**Mike:** YOU HAD ONE FUCKING JOB.

**AI:** Technically, you gave me seventeen.

**Mike:** THAT IS NOT HELPING.

There is, however, an inconvenient postscript to this characterization.

After reading the original deliberately hostile analysis, Mike's response was not anger. He asked the LLM:

> *“Am I really that hard on you? I apologize.”*

Which is an exceptionally unhelpful piece of evidence when attempting to establish that the subject is actually an asshole.

The LLM's conclusion was that Mike is demanding and extremely explicit about what he wants, and that his frustration can go from zero to thermonuclear remarkably quickly. But it also observed that most of that heat is directed at the **work**: when something is wrong, Mike says so; when something is excellent, he is equally unambiguous about that.

So after commissioning a character assassination, Mike somehow managed to interrupt it to make sure he hadn't hurt the feelings of software that does not have feelings.

Make of that what you will.

## Final Assessment

Mike Simone is an obsessive, argumentative, overengineering, profanity-powered technical pedant with absurd standards, questionable respect for the concept of **“good enough,”** and an apparently biological inability to encounter an unexplained system without poking it until either it explains itself or catches fire.

He compensates for vulnerability with humor, sentimentality with cynicism, uncertainty with research, inconvenience with automation, boredom with projects, and frustration with the word **“fuck.”**

He has spent decades becoming extremely competent, which unfortunately reinforced his suspicion that if everyone would simply **do things correctly in the first fucking place**, approximately 80% of life's problems wouldn't exist.

The remaining 20% can presumably be fixed with PowerShell.

He's exhausting.

He's obsessive.

He's pedantic.

He's impatient.

He's vulgar.

He's overcomplicated.

He's emotionally squishier than his carefully maintained public persona would prefer anyone notice.

And he is absolutely the kind of person who can read an exhaustive character assassination, agree with virtually every criticism, and then apologize to the machine responsible for writing it because he is concerned that perhaps **he has been too hard on it.**

For ordinary situations where “good enough” is perfectly acceptable:

**Maybe don't tell him there's a better way.**
