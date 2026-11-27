---
name: Wise Library
description: A library account shown as a lit walnut bookcase inside Home Assistant.
colors:
  back: "#24150e"
  wood: "#4a2d1c"
  wood-light: "#6a4329"
  lip: "#8c6040"
  shelf-under: "#2a180f"
  room: "#150e0b"
  cream: "#f4e6c8"
  soft: "#cdb698"
  card: "#f6ecd6"
  ink: "#2a1b12"
  ink-soft: "#6a5340"
  brass: "#e2c078"
  brass-deep: "#a57b34"
  oxblood: "#7c2a22"
  on-oxblood: "#fbeed6"
  red: "#a12c20"
  green: "#1f6048"
  ribbon-green: "#2c7a5c"
  stamp-ink: "#3b3a78"
typography:
  display:
    fontFamily: "Libre Caslon Display, Georgia, serif"
    fontSize: "33px"
    fontWeight: 400
    lineHeight: 1.04
  headline:
    fontFamily: "Libre Caslon Display, Georgia, serif"
    fontSize: "27px"
    fontWeight: 400
    lineHeight: 1.1
  title:
    fontFamily: "Libre Caslon Display, Georgia, serif"
    fontSize: "23px"
    fontWeight: 400
    lineHeight: 1.12
  body:
    fontFamily: "Figtree, Segoe UI, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "tnum"
  label:
    fontFamily: "Figtree, sans-serif"
    fontSize: "11.5px"
    fontWeight: 700
    letterSpacing: "0.16em"
  typed:
    fontFamily: "Courier Prime, ui-monospace, monospace"
    fontSize: "12px"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "0.02em"
rounded:
  paper: "2px"
  plate: "3px"
  sheet: "6px"
  button: "8px"
  round: "50%"
spacing:
  case-side: "13px"
  gutter-shelf: "14px"
  gutter-room: "20px"
  gutter-tablet: "24px"
  board: "34px"
  touch: "44px"
components:
  icon-button:
    textColor: "{colors.cream}"
    rounded: "{rounded.round}"
    size: "44px"
  back-button:
    textColor: "{colors.cream}"
    rounded: "22px"
    height: "44px"
    padding: "0 14px 0 6px"
  action-disc:
    backgroundColor: "{colors.oxblood}"
    textColor: "{colors.on-oxblood}"
    rounded: "{rounded.round}"
    size: "58px"
  button-go:
    backgroundColor: "{colors.oxblood}"
    textColor: "{colors.on-oxblood}"
    rounded: "{rounded.button}"
    padding: "0 22px"
    height: "44px"
  button-quiet:
    textColor: "{colors.ink}"
    rounded: "{rounded.button}"
    padding: "0 22px"
    height: "44px"
  text-link:
    textColor: "{colors.brass}"
    height: "44px"
    padding: "0 4px"
  brass-plate:
    backgroundColor: "{colors.brass}"
    typography: "{typography.label}"
    rounded: "{rounded.plate}"
    padding: "5px 16px"
  label-card:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    typography: "{typography.typed}"
    padding: "3px 6px 2px"
  slip:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.paper}"
    padding: "10px 12px"
  notice:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.plate}"
    padding: "10px 12px"
  sheet:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sheet}"
    padding: "22px 20px 20px"
---

# Design System: Wise Library

## Overview

**Creative North Star: "The Lit Bookcase"**

The panel is drawn as one piece of furniture: a walnut bookcase with a lamp above it. Loans stand face out on shelves in return order. Under each loan, on the shelf board, sits a brass holder with a typed cream card that states the return date and the days left. Reservations lie on their own shelf beside a paper slip with the library's own words. Tapping a book opens a full-screen room where that book stands alone under a picture light, in a background tinted by its cover colour, with a small shelf of spines along the bottom to move between books.

Everything is dark only (`color-scheme: dark`). Light comes from above and is warm. Text on wood is cream. Text on paper is dark ink. Brass marks fittings and links. Oxblood marks the one primary action. The system is phone first with a tablet layout second, and the bookcase stops growing at 980px wide.

The server sends a Content Security Policy of `default-src 'self'; style-src 'self'; img-src 'self'`. That shapes the build: there are no inline styles, no `data:` URIs and no third-party assets. Cover images come from the app's own origin. Wood grain comes from two SVG files (`wood-h.svg`, `wood-v.svg`). Colour arrives through the stylesheet or through SVG presentation attributes. The one per-item value, a cover tint for a room page or a spine, is set as a custom property through the CSSOM. The three fonts are self-hosted woff2 files under the SIL Open Font License, with the licence texts beside them in `fonts/`.

A book shows a real cover when the app holds one. Open Library can replace the library image when its exact-ISBN cover is larger in both dimensions. It is an image served by the app itself at `/api/cover/<isbn>`, cropped to the 2:3 book shape from the top. When there is no cover, or the image fails to load, `covers.js` draws a fallback from the title alone: one of twelve palettes and one of eleven motifs, each chosen by a hash of the title, with seeded variation inside the motif and the title typeset in Caslon capitals. The same title always draws the same fallback. A drawn cover is an illustration made by the panel, not library data. Both kinds sit under the same hinge shadow, top highlight and page edge.

The room page and the spine of a book take a tint from its cover: the average colour of the real cover, sampled on a small canvas once it has loaded, or the ground colour of the fallback palette.

**Key Characteristics:**
- One continuous object: crown, shelves and empty shelves run to the bottom of the screen.
- Depicted materials: grained wood, brass, cream paper, books with a hinge shadow and a page edge.
- Real covers first, drawn covers as the fallback, and a room tinted by whichever is shown.
- Status is a ribbon on the book plus words on the label, never colour alone.
- Three type voices: Caslon for sentences and titles, Figtree for the interface, bold typewriter for dates.
- Motion is small and stops under `prefers-reduced-motion`.

## Colors

A warm, low-chroma brown field with cream text, brass fittings and one deep red for action. Hues stay between red and yellow, except the green of a renewal and the indigo of a neutral date stamp.

### Primary
- **Oxblood** (`oxblood`): the action disc in the book room and the filled button style. It is also the focus ring colour on cream paper surfaces. Text and icons on it use **On Oxblood** (`on-oxblood`).

### Secondary
- **Brass** (`brass`) and **Deep Brass** (`brass-deep`): section plates, label holders, the picture light, text links, the default focus ring, the outline of the active spine and the selection colour. Brass text also states what the library offers for a loan in the book room ("Can be renewed to" a date, or that renewal is not offered). The two run as a gradient on metal parts, light at the top.

### Tertiary
- **Marker Red** (`red`): the ribbon and the label text of a loan that is due within three days or is overdue, and the date stamp in the same states.
- **Renewal Green** (`green`): label and stamp text of a renewed loan. **Ribbon Green** (`ribbon-green`) is the lighter green of the renewed ribbon, which sits on dark covers.
- **Stamp Indigo** (`stamp-ink`): the date stamp on the ticket of a loan that needs no attention.

### Neutral
- **Case Back** (`back`): page background behind and inside the bookcase.
- **Walnut** (`wood`), **Light Walnut** (`wood-light`), **Shelf Lip** (`lip`), **Shelf Underside** (`shelf-under`): the shelf board from its lit top edge to its shadowed lower edge. The crown and the floor of the book room use the same family.
- **Room Dark** (`room`): base of the full-screen book room. Each page mixes its cover tint into this with `color-mix`.
- **Cream** (`cream`): primary text on wood. **Soft Cream** (`soft`): secondary text on wood, such as the sync time and the branch line.
- **Card** (`card`): every paper surface: label cards, slips, the ticket, the notice, the connection sheet.
- **Ink** (`ink`) and **Soft Ink** (`ink-soft`): primary and secondary text on paper.

### Named Rules
**The Ribbon And Words Rule.** A loan state is shown by a ribbon on the book and by words on its label ("3 days", "late", "renewed"). Red and green only reinforce it. Due soon and overdue share the same red ribbon and are told apart by the words.

**The Paper Carries Ink Rule.** Dark ink text appears only on Card surfaces. Text placed directly on wood or in the room is Cream or Soft Cream.

**The One Oxblood Rule.** Oxblood fills only the primary action. It is not used for decoration or for status. Covers are exempt: a real cover has its own colours, and one fallback palette has an oxblood ground.

## Typography

**Display Font:** Libre Caslon Display 400 (with Georgia, serif)
**Body Font:** Figtree, variable 400 to 700 (with Segoe UI, system-ui, sans-serif)
**Label/Mono Font:** Courier Prime 700 (with ui-monospace, monospace)

**Character:** A book-title serif says the sentences, a plain humanist sans runs the interface, and a bold typewriter face prints dates as a library would stamp them. Numerals are tabular everywhere (`font-variant-numeric: tabular-nums`).

### Hierarchy
- **Display** (400, 33px, 1.04): the sentence at the top of a book's room, such as "Back on Monday".
- **Headline** (400, 27px, 1.1; 32px from 700px wide): the glance sentence in the crown.
- **Title** (400, 23px, 1.12): the book title in the room. The same face runs at 24px for the sheet heading, 20px for the app name and 16px on a reservation slip.
- **Body** (400, 14px, 1.5): running text in the sheet. Supporting lines on wood run at 13.5px to 15px. Emphasis inside a line uses weight 600 to 650 and Cream, not a second colour.
- **Label** (700, 11.5px, 0.16em, uppercase): the section name on a brass plate. This is the section heading itself, an `h2`.
- **Typed** (Courier Prime 700, 12px on label cards, 13px on stamps, uppercase): short dates only.

### Named Rules
**The Typed Date Rule.** Courier Prime prints dates on label cards and stamps. It is not used for sentences, titles or controls.

**The One Weight Of Caslon Rule.** Caslon is loaded at weight 400 only. Hierarchy within the display face comes from size.

## Layout

The bookcase is a flex column that fills the viewport height (`min-height: 100dvh`), centred, at most 980px wide, with a 13px wooden side on each edge. The crown sits at the top with 14px side padding (24px from 700px). Below it each section starts with a rail, 40px high or more, that holds a brass plate on the left and a text link on the right.

Shelves are a CSS grid of equal columns. A book is 88px wide at a 2:3 ratio, and a shelf row (`--row`) is the book height plus 44px, of which the bottom 34px is the board. The boards belong to the row, not to a book: the shelf list draws them as one repeating gradient across its full width, and a pseudo-element lays the `wood-h.svg` grain over the board bands through a mask. Each place on the shelf only reserves a 34px cell for its label. Columns: 3 below 520px, 4 from 520px, 5 from 700px (book width 104px), 6 from 900px. The reservation shelf uses 1 column, 2 from 700px. Unused places on the last row are filled by small props (a candle, a sleeping cat, a plant), and a repeating gradient continues empty shelves to the bottom of the screen.

The book room is a full-viewport dialog. Each book is one page with vertical scroll snap: sentence at the top, the book on a stand in the middle, a wooden floor at the bottom with the title on the left and the action on the right. Side padding is 20px. From 700px the floor content is a centred 472px column plus an 88px action column.

Every control is at least 44px in its smallest dimension. The 34px by 58px spines extend their hit area with a pseudo-element.

**The Shelf Is The Grid Rule.** Items sit on shelf boards in return order, left to right and top to bottom. There is no separate list view.

## Elevation & Depth

Depth is depicted, not abstract. Light falls from above: a radial lamp glow lies over the top 460px of the shelves, every shelf bay darkens at its top where the board above shades it, and objects cast shadows down and slightly to the right. Wood parts use inset highlights and inset dark lines for their edges. There is no generic elevation scale.

### Shadow Vocabulary
- **Crown** (`box-shadow: inset 0 -3px 0 #2a180f, inset 0 -5px 0 var(--lip), 0 10px 18px rgb(0 0 0 / .55)`): the top of the case over the first shelf.
- **Shelf board** (no `box-shadow`; a gradient band per row: 2px `var(--lip)`, then `var(--wood-light)` through `#553420` to `var(--wood)`, then 2px `#2a180f`): lit lip above, dark edge below, drawn by the shelf list.
- **Shelf bay** (`background: linear-gradient(rgb(0 0 0 / .62), transparent 34px)`): the shade under the board above, at the top of each place on the shelf.
- **Book** (`box-shadow: 3px 0 0 -1px #e9dcc0, 4.5px 0 0 -1px #b3a180, 0 0 0 .5px rgb(0 0 0 / .5), 9px 5px 12px -5px rgb(0 0 0 / .8)`): the first two layers draw the page edge, the last is the cast shadow. A gradient overlay adds the hinge shadow and a warm highlight at the top.
- **Brass** (`box-shadow: 0 1px 0 rgb(255 240 200 / .6) inset, 0 2px 4px rgb(0 0 0 / .55)`): plates and label holders.
- **Paper** (`box-shadow: 0 0 0 1px #d9c9a6 inset, 0 6px 10px -4px rgb(0 0 0 / .6)`): slips and the ticket.
- **Sheet** (`box-shadow: 0 0 0 1px #cdb88f inset, 0 0 0 4px var(--card) inset, 0 0 0 5px #cdb88f inset, 0 18px 34px -8px rgb(0 0 0 / .8)`): a double ruled border and a deep shadow.

### Named Rules
**The Lit From Above Rule.** Highlights sit on top edges and shadows fall below. A new part takes its edges and its shadow from the material it depicts.

## Shapes

Corners are small. Paper is nearly square (1.5px to 2px). Brass plates, the notice and the stamp use 3px. Books use 2px on the spine side and 4px on the open side (3px and 6px in the room). The connection sheet uses 6px and buttons 8px. Circles are for icon buttons, the action disc and the attention dot.

Ribbons are a 9px wide strip with a notched end, cut with `clip-path`. Slips and the ticket are rotated slightly (0.6 and 3 degrees), and a book that is due soon or overdue leans 2.5 degrees. Borders are rare: the stamp has a 1.5px outline in its text colour, the sheet has a dashed rule above its form, and the quiet button has a 1.5px Soft Ink outline.

## Components

### Buttons
- **Icon button:** 44px circle, no fill, a 22px line icon with a 1.75 stroke in the current text colour. Disabled is 45% opacity. The refresh icon spins while a sync runs. The connection button shows a library card icon. On devices with hover, hovering adds a faint cream tint (10%).
- **Back button:** one control in the book room made of a chevron and the word "Library" in Caslon at 20px, 44px high with fully rounded ends (22px). It has the same hover tint on hover devices only.
- **Action disc:** a 58px oxblood circle with a radial highlight, a 2px Deep Brass ring and a 12.5px label beneath it, 88px wide in total. It scales to 0.93 while pressed. As a button it renews a loan and carries the refresh icon. As a link it opens Wise and carries the "opens elsewhere" icon: "Open in Wise" for a loan the library does not offer for renewal, "Manage in Wise" for a reservation.
- **Renew confirm:** renewing takes two taps on the same control. The first tap changes the label from "Renew" to "Tap again to renew". A second tap within 4 seconds renews, and the label reads "Renewing…" with the button disabled at 60% opacity. Without a second tap the label returns. The shelf's "Renew all" text button behaves the same way. The step is stated in words; the control does not change colour.
- **Crown name button:** the title named in the crown's second line is a plain button, Cream at weight 600 with a faint underline, that opens that book.
- **Filled button:** 44px high, 8px corners, oxblood with On Oxblood text at 14.5px and weight 650. The stylesheet defines it. The current markup renders only the quiet variant.
- **Quiet button:** the same shape with no fill, Ink text and a 1.5px Soft Ink outline, used on the sheet.
- **Text link or text button:** Brass, 13.5px at weight 600, underlined 1.5px thick with a 4px offset, with a 15px icon and a 44px minimum height. The same style serves a link that opens Wise ("opens elsewhere" icon) and the "Renew all" button in the shelf header (refresh icon), which is shown only when at least one loan can be renewed.
- **Focus:** a 2.5px Brass outline offset 3px. On the sheet the outline is Oxblood.

### Brass plate
The section heading. Uppercase Figtree label in dark brown on a brass gradient with a drawn rivet at each end. The item count follows the name at weight 600.

### Label card
A brass holder (2.5px frame) centred on the shelf board under each loan, holding a Card with the typed short date and the days left. Text turns Marker Red when the loan is due within three days or overdue, and Renewal Green when it was renewed. A tap on the label opens the book, like a tap on the book itself; keyboard users reach it through the book button. When a loan becomes renewed the date lands with a short stamp animation (0.45s).

### Book
A button holding a cover at 2:3: the library's real cover image when the app holds one, otherwise the drawn SVG fallback. A real cover fills the shape with `object-fit: cover`, aligned to the top. A ribbon hangs from the top edge when the loan is due soon, overdue or renewed. Keyboard focus lifts it 5px, and so does hovering on devices with hover. Its accessible name states title, date and days left. After a renewal, each book and its label holder move from their old place to their new place in return order over 950ms, raised above the shelf while they move. The renewed book also grows slightly on the way. The shelf boards do not move.

### Reservation slip
A reserved book stands beside a Card slip with the title in Caslon and the portal's status text, unchanged, in Soft Ink, clamped to three lines.

### Book room
A full-screen dialog that rises in over 0.45s, with the back button at the top left. The phone's back gesture closes it too. Each page shows the display sentence, a brass picture light, the cover on a stand with a ticket tucked behind it carrying the stamped date, and a wooden floor. The floor holds the title, the author when the library supplies one, the lending branch, and a Brass line that says what the library offers: "Can be renewed to" a date beside a Renew disc, or a note that renewal is not offered beside an "Open in Wise" disc. A reservation page shows the portal's text on a Card block and a "Manage in Wise" disc. A strip of illustrated spines along the bottom selects a book. Each spine shows a crop of the lower cover above a cover-tinted panel with a rotated, truncated title; the full title remains in its accessible label and tooltip. Light covers use dark title ink. Reservations use their own cover art and tint too. The thin shelf they stand on is drawn by the room, so it stays in place while the strip scrolls sideways. The active spine lifts 9px and gets a Brass outline. Spines carry the same ribbons as the books.

### Notice
A Card block in the crown with Ink text at 13.5px, used for stale data and errors.

### Connection sheet
A bottom-anchored dialog on Card, at most 520px wide, with a double ruled border, a Caslon heading, body text in Ink, fine print in Soft Ink and a file input styled like the quiet button. It closes from its corner button or from a tap outside it.

### Motion
One easing, `cubic-bezier(.2, .9, .2, 1)`, serves state changes. Ambient motion is slow and small: the lamp glow, candle flame, sleeping cat's breathing, terrarium glimmers, rising tea steam. Shelf artwork lives in `decorations.js`; each drawing's visible base meets its viewBox bottom, and animation leaves its contact points fixed. Plants and the ceramic bird remain still. Spare slots use a stable selection from the catalog based on collection size. A global rule removes all CSS animation and transition under `prefers-reduced-motion: reduce`, and the scripted shelf travel and smooth scrolling check the same preference.

## Do's and Don'ts

### Do:
- **Do** keep every asset same-origin and every style in `style.css` or in SVG attributes. Set a per-item value, such as a cover tint, as a custom property through the CSSOM.
- **Do** show a loan state with a ribbon and with words on the label, then add Marker Red or Renewal Green.
- **Do** put dark Ink text on Card surfaces and Cream text on wood.
- **Do** light new parts from above: highlight on the top edge, shadow below.
- **Do** keep controls at least 44px, or extend the hit area as the spines do.
- **Do** print the portal's status text and dates as the library wrote them.
- **Do** show a real cover when the app holds one, and fall back to the drawn cover when it does not or the image fails.
- **Do** confirm a renewal with a second tap on the same control, and say each step in words on its label.
- **Do** limit hover effects to `@media (hover: hover)`.
- **Do** check `prefers-reduced-motion` in any scripted animation, since the stylesheet rule covers CSS only.

### Don't:
- **Don't** use inline styles, `data:` URIs or third-party fonts, images or scripts. The Content Security Policy blocks them.
- **Don't** carry due, overdue or renewed status by colour alone.
- **Don't** fill anything but the primary action with Oxblood.
- **Don't** set sentences, titles or controls in Courier Prime.
- **Don't** present a drawn fallback cover as the book's real cover, and don't show an author or a renewal date the library did not supply.
- **Don't** load a cover from another origin. Covers come through the app at `/api/cover/<isbn>`.
- **Don't** offer Renew for a loan the library does not offer for renewal. Show the note and the link to Wise.
- **Don't** add a light theme by flipping tokens. The system is dark only and its materials are drawn for that.
