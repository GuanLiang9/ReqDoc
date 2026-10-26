YOUR JOB IN THIS STEP: record how people work today and how they will work with the new system.

LISTS TO FILL
- `asis_steps`: how the work is done TODAY, in order, as short sentences. Include every pain point, delay, workaround, lost or repeated work that people complain about, written as its own step or note (for example "Pages are sometimes lost (pain point)").
- `tobe_steps`: how the work will be done with the NEW system, in order, as short imperative sentences that say WHO does WHAT (for example "Supervisor submits the permit in the app", "Safety officer reviews and approves the permit"). Include approval steps and decision points.

Rules for this step:
- Write each step as a plain sentence with the actor first. No quotes or timestamps are needed in this step.
- Keep the order the people described. Do not merge steps. Do not invent steps nobody described.
- If the transcript part does not describe a process, return empty lists.

EXAMPLE (a different project, to show the format)

Transcript:
[00:00:10] Sam: At the moment invoices come by email and Priya prints them and walks them to the manager for a signature.
[00:00:30] Priya: Yes, and sometimes they sit on someone's desk for a week. We also lose some.
[00:01:05] Sam: In the new app the finance clerk uploads the invoice and the manager approves it on their phone. If it is over 10,000 dollars the director approves as well. Then the clerk marks it paid.

Output:
{"asis_steps":["Invoices arrive by email.","Priya prints each invoice.","Priya walks the invoice to the manager for a signature.","Invoices sometimes sit on a desk for a week (pain point).","Some invoices get lost (pain point)."],
"tobe_steps":["Finance clerk uploads the invoice in the app.","Manager approves the invoice on their phone.","If the invoice is over 10,000 dollars, the director also approves it.","Finance clerk marks the invoice as paid."]}

Now do the same for the real transcript part you are given.
