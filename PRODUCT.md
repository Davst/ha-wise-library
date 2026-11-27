# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

One reader at home, a member of Bibliotheek AanZet, who borrows physical books. She opens the panel on her phone
through Home Assistant, most often for a quick glance (is anything due, is a reservation ready) and to renew a loan
on the spot. A tablet is the second surface. She normally has 0 to 6 books out; 15 is the maximum.

## Product Purpose

Bring her library account into Home Assistant: what she has borrowed, when it goes back, what she has reserved, and
the few actions that keep it in order (renew, cancel a reservation). Success is that she never has to open the Wise
portal for the routine things, and never returns a book late by surprise.

## Positioning

It lives where the rest of her home already is. The same data feeds Home Assistant sensors, so reminders and
automations come from the home, not from another app or an email.

## Operating Context

- Runs as a Home Assistant app, shown in the sidebar through Supervisor ingress. No host port is exposed.
- Reads the Dutch Wise portal with a dedicated browser session and publishes sensors through MQTT discovery.
- Polls hourly by default; manual refresh is limited to once a minute. A failed read keeps the last successful
  result on screen, visibly stale.
- Sessions expire. Sign-in is configured in Home Assistant; a session file can be imported when extra verification
  is required.

## Capabilities and Constraints

- Loans carry a title, author, ISBN, a return date, the lending branch, the copy barcode (the app's id for a loan,
  because it survives a renewal) and whether the library offers a renewal and until when. Reservations carry a title
  and the portal's own status text, across three lists: standard, first-available and sequential.
- Covers start with the library's images, fetched by ISBN from inside the signed-in page. Open Library is checked
  by exact ISBN once for a larger image; temporary failures retry later. Both are served from the app's data folder.
  A book without either real cover gets a drawn cover. Spines take the colour of the front cover.
- Renew and renew all work inside the app (verified on a real account 2026-11-27): the app clears the page's
  default selection, selects only the chosen loans, presses the portal's renew button and waits for its
  confirmation. Cancel reservation still opens Wise: no populated reservation list has been inspected.
- Content Security Policy allows only same-origin scripts, styles, images and fonts. No inline styles or scripts,
  no third-party fonts or images.
- Static HTML, CSS and JavaScript served by the app; no build step.
- English and Dutch, following the Home Assistant language. Titles and portal status text stay as the library
  writes them.
- Physical materials only. E-books and audiobooks are out of scope.

## Brand Commitments

- Name: Wise Library.
- The reader likes a cozy reading aesthetic; the panel should feel warm and personal while staying quick to use.
- Animation is welcome where it is small and kind, never where it slows a renewal down.

## Evidence on Hand

- Real loan and reservation data once the account is connected. No real-account snapshot is stored in the
  repository, and none may be committed.
- No cover art, author names or reading history exist. Do not invent them as if they were library data.

## Product Principles

1. The glance answers itself: what is due and what is ready is readable before any tap.
2. One thumb, one confirm: a renewal takes a tap and a confirmation, nothing more.
3. Real pile, real states: zero books, six books and fifteen books each look intended, and so do stale data,
   a failed sync and a signed-out session.
4. Say what the library said: status and dates come from the portal unchanged; the panel never guesses.
5. Warmth serves the task: character lives in the details and never costs a tap.

## Accessibility & Inclusion

Honour reduced-motion preferences, keep touch targets at least 44 px, and never carry due or overdue status by
colour alone.
