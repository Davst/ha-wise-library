const DAY = 86_400_000;

// Noon keeps a date-only value on the same calendar day in every time zone.
export const atNoon = iso => new Date(`${iso}T12:00:00`);

export function isoDay(date) {
  const pad = number => String(number).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export const daysLeft = (loan, today) => Math.round((atNoon(loan.due_date) - atNoon(isoDay(today))) / DAY);

// A book that is due soon or overdue says so even if it was renewed earlier in this session.
export function mark(days, renewed) {
  if (days < 0) return 'overdue';
  if (days <= 3) return 'soon';
  return renewed ? 'renewed' : 'later';
}

export const inReturnOrder = loans =>
  [...loans].sort((a, b) => a.due_date.localeCompare(b.due_date) || a.title.localeCompare(b.title));

export function renewedIds(before, after) {
  const earlier = new Map(before.map(loan => [loan.id, loan.due_date]));
  return after.filter(loan => earlier.has(loan.id) && loan.due_date > earlier.get(loan.id)).map(loan => loan.id);
}

export function glance(loans, today) {
  const ordered = inReturnOrder(loans);
  if (!ordered.length) return {kind: 'none'};
  const late = ordered.filter(loan => daysLeft(loan, today) < 0);
  if (late.length) return {kind: 'overdue', count: late.length, loan: late[0]};
  const soon = ordered.filter(loan => daysLeft(loan, today) <= 3);
  if (soon.length) return {kind: 'soon', count: soon.length, loan: soon[0], days: daysLeft(soon[0], today)};
  return {kind: 'later', loan: ordered[0]};
}

// The portal's card text usually opens with the title, which the panel already shows beside it.
export function portalText(hold) {
  const lines = hold.details.split('\n').map(line => line.trim()).filter(Boolean);
  if (lines[0] === hold.title) lines.shift();
  return lines.join('\n');
}
