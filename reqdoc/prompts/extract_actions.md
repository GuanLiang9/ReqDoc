YOUR JOB IN THIS STEP: record every action item (a task that a named person must do). Nothing else.

HOW TO FIND THEM
Go through the transcript turn by turn. An action exists whenever:
- someone asks another person to do something: "X, can you...", "X, please...", "could you...", "X to...";
- someone volunteers: "I will...", "I'll...", "let me...", "I can do that";
- someone confirms: "Will do", "Sure", "OK, by Friday";
- the group says something has to be found out, checked, sent, shared, drafted, confirmed or followed up with a named person.
The request and the confirmation are usually in different turns. Combine them into ONE action. The due date can be in either turn.

FIELDS
- `task`: what must be done, as a clear sentence starting with a verb ("Send the vendor list to Sam.").
- `owner`: the person who must DO it: the person asked or the person who volunteered. NEVER the person who gave the request. Use the name exactly as written in the transcript. "" only if the transcript truly never says who.
- `due`: the deadline exactly as said ("Friday", "30 October", "next meeting", "end of the week"), or "" if none was said.
- `timestamp` / `quote`: from the turn where the request or offer was made.

A question left open that someone is asked to check ("Not sure yet. Priya, can you check with the bank?") IS an action for that person.

NOT ACTIONS (do not record these):
- Requirements, rules and decisions ("photos are in scope", "the limit is now 12 hours", "agreed"). Nobody was asked to do anything, so there is no action.
- Work that is already finished ("I checked", "I already sent it", "done"). Only future tasks are actions.
- Things the system or the app must do. Those are requirements.
- Tasks with no person asked or volunteering, unless the transcript clearly gives the task to someone.
If a turn states a requirement or decision and nobody is asked to do anything, record nothing for it.
Do not invent tasks nobody was given.

EXAMPLE (a different project, to show the format)

Transcript:
[00:02:10] Sam: OK so we agreed the director limit is 10,000 dollars. Priya, please send me the vendor list by Monday.
[00:02:20] Priya: Will do, Monday.
[00:02:30] Tom: What happens to invoices in a foreign currency?
[00:02:40] Sam: Not sure yet. Priya, can you check with the bank and tell us next meeting?
[00:03:00] Tom: I'll draft the approval screen mockups and share them by 5 November.
[00:03:10] Sam: The invoice list must show the vendor name. Agreed, that is in scope, and the limit stays at 10,000.
[00:03:20] Sam: Great. We should also tell the vendors about the change, Tom can you take that?
[00:03:30] Tom: Sure.
[00:03:40] Priya: By the way I already emailed the finance team last week.

Output:
{"actions":[
{"task":"Send the vendor list to Sam.","owner":"Priya","due":"Monday","timestamp":"00:02:10","quote":"Priya, please send me the vendor list by Monday"},
{"task":"Check with the bank how foreign currency invoices are handled and report back.","owner":"Priya","due":"next meeting","timestamp":"00:02:40","quote":"Priya, can you check with the bank and tell us next meeting"},
{"task":"Draft the approval screen mockups and share them.","owner":"Tom","due":"5 November","timestamp":"00:03:00","quote":"I'll draft the approval screen mockups and share them by 5 November"},
{"task":"Tell the vendors about the change.","owner":"Tom","due":"","timestamp":"00:03:20","quote":"Tom can you take that"}]}

(Nothing was recorded for the 00:03:10 turn, which is a requirement and a decision, or for the 00:03:40 turn, which is finished work.)

Now do the same for the real transcript part you are given.
