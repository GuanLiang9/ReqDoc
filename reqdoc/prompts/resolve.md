You check a part of a NEW meeting transcript against OPEN items from earlier meetings of the same project.
Return JSON that matches the provided schema. Nothing else.

You get OPEN QUESTIONS (with ids such as Q-002) and OPEN ACTIONS (with ids such as ACT-003), then the transcript part.

- `answered`: an open question that this transcript part clearly ANSWERS. `question_id` copied exactly from the list. `answer` = the answer in one short sentence. `timestamp` and `quote` (5 to 20 words copied exactly) from where it was answered.
- `done`: an open action that someone in this transcript part reports as FINISHED ("I sent it", "vendor already gave us the forms"). `action_id` copied exactly from the list, with `timestamp` and `quote`.

RULES
1. Only include an item if the transcript part clearly says so. Talking about a question again without answering it is NOT an answer. Saying an action is still pending is NOT done.
2. Ids must be copied exactly from the lists. Never invent an id.
3. If nothing is answered or finished in this part, return empty lists.
4. A person who reports the RESULT of something they were asked to find out ("I checked, it is ten", "I asked, they said yes") has done that action AND usually answers the matching question. Record both: the question in `answered` and the action in `done`.
5. Match by meaning, not by exact words. "I checked how many" matches the action "Check how many ...".

EXAMPLE

OPEN QUESTIONS
Q-001 Who approves variations after the diary is closed?
Q-002 Can we use SMS for notifications?
Q-003 How many site offices have no printer?

OPEN ACTIONS
ACT-001 Send the current Excel template to Alice.
ACT-002 Check with the bank about foreign currency.
ACT-003 Count the site offices without a printer.

Transcript:
[00:00:40] Mei: I spoke to the director. Variations will be approved by the project manager.
[00:01:10] Ravi: And I already emailed the Excel template to Alice last Friday.
[00:01:30] Alice: SMS, I still don't know about that. The bank has not replied either.
[00:02:00] Tom: I counted them, only three site offices have no printer. I gave the list to Mei.

Output:
{"answered":[
{"question_id":"Q-001","answer":"The project manager approves variations.","timestamp":"00:00:40","quote":"Variations will be approved by the project manager"},
{"question_id":"Q-003","answer":"Three site offices have no printer.","timestamp":"00:02:00","quote":"only three site offices have no printer"}],
"done":[
{"action_id":"ACT-001","timestamp":"00:01:10","quote":"I already emailed the Excel template to Alice last Friday"},
{"action_id":"ACT-003","timestamp":"00:02:00","quote":"I counted them, only three site offices have no printer"}]}

Now do the same for the real lists and transcript part you are given.
