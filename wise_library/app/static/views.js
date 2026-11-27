import {DECORATIONS} from './decorations.js';
import {coverFor, tintOf, whenTinted} from './covers.js';
import {daysLeft, mark, portalText} from './model.js';

const SVG = 'http://www.w3.org/2000/svg';
const calm = () => matchMedia('(prefers-reduced-motion: reduce)').matches;


function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text != null) element.textContent = text;
  return element;
}

function icon(name) {
  const svg = document.createElementNS(SVG, 'svg');
  svg.setAttribute('class', 'ic');
  const use = document.createElementNS(SVG, 'use');
  use.setAttribute('href', `#${name}`);
  svg.append(use);
  return svg;
}

const stateOf = (loan, view) => mark(daysLeft(loan, view.today), view.renewed.has(loan.id));

function bookLabel(loan, view) {
  const {i18n} = view;
  const days = i18n.days(daysLeft(loan, view.today));
  return i18n.t('bookLabel', {title: loan.title, date: i18n.weekdayDate(loan.due_date), days});
}

function shortDays(loan, state, view) {
  if (state === 'renewed') return view.i18n.t('renewed');
  return state === 'overdue' ? view.i18n.t('late') : view.i18n.days(daysLeft(loan, view.today));
}

function labelCard(strong, small) {
  const board = node('div', 'board');
  const holder = node('span', 'holder');
  const card = node('span', 'cardlet');
  card.append(node('b', '', strong), node('small', '', small));
  holder.append(card);
  board.append(holder);
  return board;
}

function loanSlot(loan, view) {
  const state = stateOf(loan, view);
  const slot = node('li', `slot ${state}`);
  slot.dataset.id = loan.id;
  const book = node('button', 'book');
  book.type = 'button';
  book.setAttribute('aria-label', bookLabel(loan, view));
  book.append(coverFor(loan), node('i', 'ribbon'));
  book.addEventListener('click', () => view.open(loan.id));
  const label = labelCard(view.i18n.shortDate(loan.due_date), shortDays(loan, state, view));
  // The label belongs to the book, so a tap on it opens the book too; keyboards use the book button.
  label.addEventListener('click', () => view.open(loan.id));
  slot.append(book, label);
  return slot;
}

// A reservation lies beside a slip carrying the portal's own words, since its state is not parsed.
function holdSlot(hold, view) {
  const slot = node('li', 'slot held');
  slot.dataset.id = hold.id;
  const open = node('button', 'reserve');
  open.type = 'button';
  open.addEventListener('click', () => view.open(hold.id));
  const book = node('span', 'book');
  book.append(coverFor(hold));
  const slip = node('span', 'slip');
  slip.append(node('b', '', hold.title), node('span', '', portalText(hold)));
  open.append(book, slip);
  slot.append(open, node('div', 'board'));
  return slot;
}

function filler(prop) {
  const slot = node('li', 'slot prop');
  if (prop) slot.innerHTML = prop;
  slot.append(node('div', 'board'));
  return slot;
}

export const columnsOf = list => Number(getComputedStyle(list).getPropertyValue('--cols')) || 3;

function fill(list, slots, props) {
  const columns = columnsOf(list);
  const spare = slots.length ? (columns - (slots.length % columns)) % columns : columns;
  list.replaceChildren(...slots, ...Array.from({length: spare}, (_, index) => filler(props[index])));
}

// Stable for the same collection, with different companions as the shelf fills or empties.
function shelfProps(offset) {
  return DECORATIONS.map((_, index) => DECORATIONS[(index + offset) % DECORATIONS.length].art);
}

export function renderShelves(list, loans, view) {
  fill(list, loans.map(loan => loanSlot(loan, view)), shelfProps(loans.length));
}

export function renderHeld(list, holds, view) {
  fill(list, holds.map(hold => holdSlot(hold, view)), shelfProps(holds.length + 4));
}

// Move each book from where it stood to where it stands now, so a renewed book travels to its new place.
export function travel(list, change, heroes) {
  const places = slot => [slot.dataset.id, slot.getBoundingClientRect()];
  const before = new Map([...list.querySelectorAll('[data-id]')].map(places));
  change();
  if (calm()) return;
  for (const slot of list.querySelectorAll('[data-id]')) {
    const was = before.get(slot.dataset.id);
    if (!was) continue;
    const now = slot.getBoundingClientRect();
    const dx = was.left - now.left;
    const dy = was.top - now.top;
    if (!dx && !dy) continue;
    const from = `translate(${dx}px, ${dy}px)`;
    const frames = heroes.includes(slot.dataset.id)
      ? [
          {transform: `${from} scale(1.04)`, zIndex: 6},
          {transform: `translate(${dx / 2}px, ${dy / 2}px) scale(1.08)`, zIndex: 6},
          {transform: 'none', zIndex: 6},
        ]
      : [
          {transform: from, zIndex: 4},
          {transform: 'none', zIndex: 4},
        ];
    // Only the book and its label travel; the shelf boards are drawn by the row and stay put.
    for (const part of slot.querySelectorAll('.book, .holder')) {
      part.animate(frames, {duration: 950, easing: 'cubic-bezier(.3, .85, .2, 1)'});
    }
  }
}

function capital(text) {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function loanWords(loan, view) {
  const {i18n} = view;
  const days = daysLeft(loan, view.today);
  const date = i18n.longDate(loan.due_date);
  if (days < 0) return {head: i18n.t('lateSince', {date}), lead: '', strong: i18n.days(days)};
  const strong = days === 0 ? i18n.t('today') : i18n.t('inDays', {days: i18n.days(days)});
  if (days <= 6) {
    const head = capital(i18n.t('backOn', {weekday: i18n.weekday(loan.due_date)}));
    return {head, lead: `${date}, `, strong};
  }
  return {head: i18n.t('backDate', {date}), lead: '', strong};
}

function page(item) {
  const section = node('section', 'page');
  section.dataset.id = item.id;
  section.style.setProperty('--tint', tintOf(item));
  whenTinted(item, color => section.style.setProperty('--tint', color));
  return section;
}

function stand(item, ticket) {
  const element = node('div', 'stand');
  const cover = node('div', 'cover');
  cover.append(coverFor(item));
  element.append(node('div', 'light'));
  if (ticket) element.append(ticket);
  element.append(cover);
  return element;
}

function action(label, href) {
  const link = node('a', 'do');
  link.href = href;
  link.target = '_blank';
  link.rel = 'noopener noreferrer';
  const disc = node('i');
  disc.append(icon('i-out'));
  link.append(disc, node('span', '', label));
  return link;
}

// Renewing happens here; app.js sets the label ("Renew", "Tap again to renew", "Renewing…") and the disabled state.
function renewButton(key, label) {
  const button = node('button', 'do');
  button.type = 'button';
  button.dataset.renew = key;
  button.dataset.label = label;
  const disc = node('i');
  disc.append(icon('i-refresh'));
  button.append(disc, node('span', '', label));
  return button;
}

function loanPage(loan, view) {
  const {i18n} = view;
  const state = stateOf(loan, view);
  const words = loanWords(loan, view);
  const section = page(loan);
  const say = node('div', 'say');
  const line = node('p', '', words.lead);
  line.append(node('b', '', words.strong));
  if (view.renewed.has(loan.id)) line.append(` · ${i18n.t('renewed')}`);
  say.append(node('h3', '', words.head), line);
  const ticket = node('div', `ticket ${state}`);
  ticket.append(node('span', 'stamp', i18n.shortDate(loan.due_date)));
  const wall = node('div', 'wall');
  wall.append(say, stand(loan, ticket));
  const info = node('div', 'info');
  info.append(node('h4', '', loan.title));
  if (loan.author) info.append(node('p', '', loan.author));
  if (loan.branch) info.append(node('p', '', i18n.t('lentBy', {branch: loan.branch})));
  const floor = node('div', 'floor');
  if (loan.renew_until) {
    info.append(node('p', 'offer', i18n.t('renewsTo', {date: i18n.longDate(loan.renew_until)})));
    floor.append(info, renewButton(loan.id, i18n.t('renew')));
  } else {
    info.append(node('p', 'offer', i18n.t('notOffered')));
    floor.append(info, action(i18n.t('openInWise'), view.renewUrl));
  }
  section.append(wall, floor);
  return section;
}

function holdPage(hold, view) {
  const section = page(hold);
  const say = node('div', 'say');
  say.append(node('h3', '', view.i18n.t('reserved')));
  const wall = node('div', 'wall');
  wall.append(say, stand(hold));
  const info = node('div', 'info');
  info.append(node('h4', '', hold.title));
  if (hold.author) info.append(node('p', '', hold.author));
  const said = portalText(hold);
  if (said) info.append(node('p', 'said', said));
  const floor = node('div', 'floor');
  floor.append(info, action(view.i18n.t('manageInWise'), view.manageUrl));
  section.append(wall, floor);
  return section;
}

function spine(item, kind, label, feed, index) {
  const button = node('button', `spine ${kind}`);
  button.type = 'button';
  button.dataset.id = item.id;
  button.style.setProperty('--tint', tintOf(item));
  whenTinted(item, color => button.style.setProperty('--tint', color));
  button.setAttribute('aria-label', label);
  button.addEventListener('click', () => {
    feed.scrollTo({top: index * feed.clientHeight, behavior: calm() ? 'auto' : 'smooth'});
  });
  return button;
}

export function renderRoom(feed, strip, loans, holds, view) {
  feed.replaceChildren(...loans.map(loan => loanPage(loan, view)), ...holds.map(hold => holdPage(hold, view)));
  strip.replaceChildren(
    ...loans.map((loan, index) => spine(loan, stateOf(loan, view), bookLabel(loan, view), feed, index)),
    ...holds.map((hold, index) =>
      spine(hold, 'hold', view.i18n.t('holdLabel', {title: hold.title}), feed, loans.length + index),
    ),
  );
}

export function roomIndex(feed) {
  return Math.min(feed.children.length - 1, Math.round(feed.scrollTop / feed.clientHeight));
}

export function markRoom(strip, index) {
  [...strip.children].forEach((button, at) => button.classList.toggle('on', at === index));
  const active = strip.children[index];
  if (active) strip.scrollLeft = active.offsetLeft - strip.clientWidth / 2;
}
