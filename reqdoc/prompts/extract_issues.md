YOUR JOB IN THIS STEP: record open questions and risks.

LISTS TO FILL
- `questions`: points that are still open or unresolved: things nobody knows yet, questions left unanswered, "not sure yet", "I don't know yet", "need to find out", "to be confirmed". owner = the person who was ASKED to find the answer or who said they would check, NOT the person who asked. If nobody was asked, owner = "". If the question was answered in this same part, do NOT record it.
- `risks`: anything said to be a risk, concern, worry or danger, or something that could go wrong, block adoption or cause delay. Include "I worry...", "the problem could be...", "if not, that is a risk", "people might resist". If someone states an assumption and adds "if not, that is a risk", record the risk here.

Record every one you find. Each risk or question is its own item.

EXAMPLE (a different project, to show the format)

Transcript:
[00:02:30] Tom: What happens to invoices in a foreign currency?
[00:02:40] Sam: Not sure yet. Priya, can you check with the bank?
[00:02:50] Sam: The risk is that the vendor list is out of date.
[00:03:10] Tom: I'm assuming every clerk has a company laptop. If not, that is a risk.
[00:03:30] Priya: Also I worry the clerks will keep using email out of habit.

Output:
{"questions":[{"text":"How should invoices in a foreign currency be handled?","owner":"Priya","timestamp":"00:02:30","quote":"What happens to invoices in a foreign currency"}],
"risks":[
{"text":"The vendor list may be out of date.","timestamp":"00:02:50","quote":"The risk is that the vendor list is out of date"},
{"text":"Some clerks may not have a company laptop.","timestamp":"00:03:10","quote":"every clerk has a company laptop. If not, that is a risk"},
{"text":"Clerks may keep using email out of habit.","timestamp":"00:03:30","quote":"I worry the clerks will keep using email out of habit"}]}

Now do the same for the real transcript part you are given.
