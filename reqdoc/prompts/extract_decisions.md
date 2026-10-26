YOUR JOB IN THIS STEP: record decisions and glossary terms.

LISTS TO FILL
- `decisions`: anything the group agreed, settled, chose, postponed or excluded. Look for "agreed", "decided", "let's go with", "OK so", "we will use", "that is decided", "not now", "phase two", "out of scope", and recaps such as "to sum up".
  - Record each decision once. If a recap repeats a decision you already have, do not record it again. If a recap contains a decision you do not have yet, record it.
  - decided_by = the person who stated or confirmed it.
- `glossary`: abbreviations, acronyms and special terms that a new reader would need explained, including terms people spell out ("permit to work, PTW for short" gives term "PTW", meaning "Permit to work"). Only terms that appear in the transcript.

EXAMPLE (a different project, to show the format)

Transcript:
[00:02:10] Sam: OK so we agreed the director limit is 10,000 dollars.
[00:02:50] Sam: We also call this the AP team, accounts payable.
[00:04:00] Tom: Let's go with email notifications, not SMS.
[00:04:30] Priya: Reporting dashboards can wait, phase two.
[00:05:00] Sam: To sum up: director limit 10,000 dollars, email notifications, dashboards in phase two.

Output:
{"decisions":[
{"text":"The director approval limit is 10,000 dollars.","decided_by":"Sam","timestamp":"00:02:10","quote":"we agreed the director limit is 10,000 dollars"},
{"text":"Notifications will be sent by email, not SMS.","decided_by":"Tom","timestamp":"00:04:00","quote":"Let's go with email notifications, not SMS"},
{"text":"Reporting dashboards are postponed to phase two.","decided_by":"Priya","timestamp":"00:04:30","quote":"Reporting dashboards can wait, phase two"}],
"glossary":[{"term":"AP","meaning":"Accounts payable"}]}

Now do the same for the real transcript part you are given.
