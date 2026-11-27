// The portal supplies no cover image, so each book gets a drawn cover that depends only on its title.
const SVG = 'http://www.w3.org/2000/svg';

const PALETTES = [
  {ground: '#253159', ink: '#f1d9a6', second: '#c98a4b', deep: '#161d3a'},
  {ground: '#b9573a', ink: '#f8e7cb', second: '#f3c877', deep: '#6f2f24'},
  {ground: '#1d4648', ink: '#f6e3b0', second: '#7fb0a4', deep: '#123031'},
  {ground: '#33523f', ink: '#f0e2b8', second: '#d9a55a', deep: '#1e3327'},
  {ground: '#3a2549', ink: '#f3dcae', second: '#f0c768', deep: '#241630'},
  {ground: '#2c2a36', ink: '#e8dcc0', second: '#e07a3a', deep: '#17161d'},
  {ground: '#7c2a22', ink: '#f6e4c4', second: '#e2b866', deep: '#4f1712'},
  {ground: '#1f3f5c', ink: '#f2e3bf', second: '#e0a44e', deep: '#122a40'},
  {ground: '#4b3828', ink: '#f3e2c2', second: '#d8a24a', deep: '#2c2016'},
  {ground: '#5a2d3f', ink: '#f6dfc8', second: '#e9a66b', deep: '#371a26'},
  {ground: '#56603a', ink: '#f3e8c4', second: '#e7b65c', deep: '#333a20'},
  {ground: '#274b57', ink: '#f0e4c6', second: '#e58c5a', deep: '#15303a'},
];
const SIZES = [21, 19, 17, 15.5];

function hash(text) {
  let value = 2166136261;
  for (const char of text) value = Math.imul(value ^ char.codePointAt(0), 16777619);
  return value >>> 0;
}

// A small seeded generator, so one title always draws the same cover.
function seeded(seed) {
  let state = seed;
  return (low, high) => {
    state = (state + 0x6d2b79f5) | 0;
    let mixed = Math.imul(state ^ (state >>> 15), 1 | state);
    mixed = (mixed + Math.imul(mixed ^ (mixed >>> 7), 61 | mixed)) ^ mixed;
    return Math.round(low + (((mixed ^ (mixed >>> 14)) >>> 0) / 4294967296) * (high - low));
  };
}

const times = (count, draw) => Array.from({length: count}, (_, index) => draw(index)).join('');

function sunOverHills({second, deep}, pick) {
  return `<circle cx="${pick(56, 144)}" cy="216" r="${pick(26, 38)}" fill="${second}"/>
    <path d="M0 250c50-26 90-16 200-30v80H0z" fill="${deep}" opacity=".75"/>
    <path d="M0 276c60-22 120-6 200-22v46H0z" fill="${deep}"/>`;
}

function rays({ground, ink, second, deep}, pick) {
  const count = pick(7, 11);
  const ray = index => {
    const angle = Math.PI * (0.1 + (0.8 * index) / (count - 1));
    return `M100 246L${Math.round(100 - 86 * Math.cos(angle))} ${Math.round(246 - 86 * Math.sin(angle))}`;
  };
  return `<path d="${times(count, ray)}" stroke="${ink}" stroke-width="1.8" stroke-linecap="round" opacity=".85"/>
    <circle cx="100" cy="246" r="26" fill="${ground}"/><circle cx="100" cy="246" r="15" fill="${second}"/>
    <path d="M0 268h200v32H0z" fill="${deep}"/>`;
}

function reeds({ink, second, deep}, pick) {
  const reed = () => {
    const x = pick(20, 180);
    const top = pick(176, 214);
    return `<path d="M${x} 300V${top}" stroke="${deep}" stroke-width="2.6" stroke-linecap="round"/>
      <rect x="${x - 4}" y="${top - 8}" width="8" height="24" rx="4" fill="${second}"/>`;
  };
  return `<circle cx="${pick(0, 1) ? 52 : 148}" cy="188" r="20" fill="${ink}"/>
    <path d="M0 252h200v48H0z" fill="${deep}"/>${times(pick(3, 6), reed)}`;
}

function stars({second, deep}, pick) {
  const star = () => `<use href="#cover-star" x="${pick(24, 176)}" y="${pick(166, 244)}"/>`;
  return `<g fill="${second}">${times(pick(5, 9), star)}</g>
    <path d="M0 270l40-10 30 6 34-${pick(14, 30)} 40 16 56-12v30H0z" fill="${deep}"/>`;
}

function windows({second, deep}, pick) {
  const arch = (x, width) => {
    const outer = width / 2;
    const inner = outer - 8;
    return `<path d="M${x} 300V214a${outer} ${outer} 0 0 1 ${width} 0v86z" fill="${deep}"/>
      <path d="M${x + 8} 300V216a${inner} ${inner} 0 0 1 ${width - 16} 0v84z" fill="${second}"/>
      <path d="M${x + outer} 190v110M${x + 8} 244h${width - 16}" stroke="${deep}" stroke-width="3"/>`;
  };
  return pick(0, 1) ? arch(64, 72) : arch(26, 62) + arch(112, 62);
}

function waves({ink, second}, pick) {
  const wave = index => `<path d="M14 ${290 - index * 22}c20-12 38 12 58 0s38 12 58 0 38 12 56 0"/>`;
  return `<circle cx="${pick(40, 160)}" cy="${pick(168, 190)}" r="${pick(11, 17)}" fill="${second}"/>
    <g fill="none" stroke="${ink}" stroke-width="2" stroke-linecap="round" opacity=".7">${times(pick(3, 5), wave)}</g>`;
}

function mountains({second, deep}, pick) {
  const near = pick(50, 86);
  const far = pick(120, 156);
  return `<circle cx="${pick(0, 1) ? 36 : 166}" cy="178" r="12" fill="${second}"/>
    <path d="M${far - 70} 300L${far} ${pick(196, 222)}l70 104z" fill="${deep}" opacity=".7"/>
    <path d="M${near - 76} 300L${near} ${pick(176, 204)}l76 124z" fill="${deep}"/>`;
}

function crescent({ground, ink, second}, pick) {
  const dot = () => `<circle cx="${pick(20, 180)}" cy="${pick(170, 284)}" r="2"/>`;
  return `<circle cx="100" cy="222" r="36" fill="${ink}"/>
    <circle cx="${pick(0, 1) ? 116 : 84}" cy="212" r="33" fill="${ground}"/>
    <g fill="${second}">${times(pick(3, 6), dot)}</g>`;
}

function sprig({second}, pick) {
  const pairs = pick(3, 5);
  const leaves = index => {
    const y = 276 - index * 24;
    return `<ellipse cx="82" cy="${y}" rx="16" ry="7" transform="rotate(28 82 ${y})"/>
      <ellipse cx="118" cy="${y - 10}" rx="16" ry="7" transform="rotate(-28 118 ${y - 10})"/>`;
  };
  return `<path d="M100 300V${276 - pairs * 24}" stroke="${second}" stroke-width="2.5" stroke-linecap="round"/>
    <g fill="${second}">${times(pairs, leaves)}</g>`;
}

function rings({ink, second}, pick) {
  const x = pick(64, 136);
  const ring = index => `<circle cx="${x}" cy="232" r="${14 + index * 13}"/>`;
  return `<g fill="none" stroke="${ink}" stroke-width="1.8" opacity=".6">${times(pick(3, 5), ring)}</g>
    <circle cx="${x}" cy="232" r="6" fill="${second}"/>`;
}

function tree({second, deep}, pick) {
  const x = pick(70, 130);
  return `<path d="M0 286c60-22 130-22 200 0v14H0z" fill="${deep}"/>
    <path d="M${x} 284v-50" stroke="${deep}" stroke-width="7" stroke-linecap="round"/>
    <circle cx="${x}" cy="216" r="${pick(26, 34)}" fill="${second}"/>
    <circle cx="${x + pick(-22, 22)}" cy="${pick(196, 206)}" r="${pick(14, 20)}" fill="${second}" opacity=".8"/>`;
}

const MOTIFS = [sunOverHills, rays, reeds, stars, windows, waves, mountains, crescent, sprig, rings, tree];

const words = title => title.toUpperCase().split(/\s+/).filter(Boolean);
const limitAt = size => Math.floor(176 / (size * 0.74));

function wrap(title, limit) {
  const lines = [];
  for (const whole of words(title)) {
    const pieces = whole.length > limit ? whole.match(new RegExp(`.{1,${limit - 1}}`, 'gu')) : [whole];
    pieces.forEach((piece, index) => {
      const word = index < pieces.length - 1 ? `${piece}-` : piece;
      const joined = `${lines.at(-1)} ${word}`;
      if (index === 0 && lines.length && joined.length <= limit) lines[lines.length - 1] = joined;
      else lines.push(word);
    });
  }
  return lines;
}

// The largest size that keeps every word whole within five lines; only the smallest size may break a word.
function typeset(title) {
  const longest = Math.max(...words(title).map(word => word.length), 1);
  const fits = size => longest <= limitAt(size) && wrap(title, limitAt(size)).length <= 5;
  const size = SIZES.find(fits) ?? SIZES.at(-1);
  return {size, lines: wrap(title, limitAt(size)).slice(0, 5)};
}

function shape(name, attributes) {
  const element = document.createElementNS(SVG, name);
  for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, value);
  return element;
}

export const paletteFor = title => PALETTES[hash(title) % PALETTES.length];

export function drawCover(title) {
  const palette = paletteFor(title);
  const pick = seeded(hash(`${title}|cover`));
  const motif = MOTIFS[hash(`${title}|motif`) % MOTIFS.length];
  const {size, lines} = typeset(title);
  const ruleY = 50 + (lines.length - 1) * size * 1.2;
  const svg = shape('svg', {class: 'art', viewBox: '0 0 200 300', preserveAspectRatio: 'xMidYMid slice'});
  svg.setAttribute('aria-hidden', 'true');
  svg.innerHTML = `<rect width="200" height="300" fill="${palette.ground}"/>${motif(palette, pick)}
    <path d="M82 ${ruleY}h36" stroke="${palette.ink}" stroke-width="1.5" opacity=".6"/>
    <rect x="7" y="7" width="186" height="286" fill="none" stroke="${palette.ink}" opacity=".28"/>`;
  lines.forEach((line, index) => {
    const y = (36 + index * size * 1.2).toFixed(1);
    const text = shape('text', {class: 'cover-title', x: 100, y, 'font-size': size, fill: palette.ink});
    text.textContent = line;
    svg.append(text);
  });
  // The grain filter is an attribute, not a stylesheet rule, so it resolves inside this document in every engine.
  svg.append(shape('rect', {width: 200, height: 300, fill: '#fff', filter: 'url(#grain)', opacity: 0.2}));
  return svg;
}

const tints = new Map();

export const tintOf = item => tints.get(item.isbn) ?? paletteFor(item.title).ground;

// A cover the app holds is the real one; the colour of the room and of the spine is taken from it.
export function coverFor(item) {
  if (!item.cover) return drawCover(item.title);
  const image = document.createElement('img');
  image.className = 'art real';
  image.alt = '';
  image.decoding = 'async';
  image.src = `./api/cover/${item.isbn}?v=2`;
  image.addEventListener('error', () => image.replaceWith(drawCover(item.title)), {once: true});
  return image;
}

function averageColor(image) {
  const canvas = document.createElement('canvas');
  canvas.width = 12;
  canvas.height = 18;
  const context = canvas.getContext('2d');
  context.drawImage(image, 0, 0, canvas.width, canvas.height);
  const {data} = context.getImageData(0, 0, canvas.width, canvas.height);
  const total = [0, 0, 0];
  for (let at = 0; at < data.length; at += 4) for (let part = 0; part < 3; part++) total[part] += data[at + part];
  const pixels = data.length / 4;
  return `rgb(${total.map(sum => Math.round(sum / pixels)).join(' ')})`;
}

export function whenTinted(item, apply) {
  if (!item.cover || tints.has(item.isbn)) return;
  const image = new Image();
  image.addEventListener('load', () => {
    try {
      tints.set(item.isbn, averageColor(image));
    } catch {
      return; // an unreadable image keeps the colour drawn for the title
    }
    apply(tints.get(item.isbn));
  });
  image.src = `./api/cover/${item.isbn}?v=2`;
}
