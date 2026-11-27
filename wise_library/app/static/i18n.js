import {atNoon} from './model.js';

const TEXT = {
  en: {
    locale: 'en-GB',
    appName: 'Library',
    refresh: 'Refresh library',
    close: 'Close',
    borrowed: 'Borrowed',
    reserved: 'Reserved',
    renew: 'Renew',
    renewAll: 'Renew all',
    renewConfirm: 'Tap again to renew',
    renewAllConfirm: 'Tap again to renew all',
    renewing: 'Renewing…',
    renewsTo: 'Can be renewed to {date}.',
    notOffered: 'The library offers no renewal for this book right now.',
    openInWise: 'Open in Wise',
    manageInWise: 'Manage in Wise',
    renewed: 'renewed',
    today: 'today',
    day: '1 day',
    days: '{n} days',
    lateDay: '1 day late',
    lateDays: '{n} days late',
    late: 'late',
    bookLabel: '{title}, back {date}, {days}',
    holdLabel: '{title}, reserved',
    glanceNone: 'Nothing borrowed right now.',
    glanceOverdueOne: 'One book is overdue.',
    glanceOverdueMany: '{n} books are overdue.',
    glanceToday: 'One book goes back today.',
    glanceTomorrow: 'One book goes back tomorrow.',
    glanceOn: 'One book goes back {weekday}.',
    glanceSoonMany: '{n} books go back within three days.',
    glanceLater: 'Nothing is due until {date}.',
    glanceWaiting: 'Waiting for the first sync.',
    glanceConnect: 'Connect your library card.',
    glanceOpening: 'Opening the library…',
    reservedOne: 'One reservation.',
    reservedMany: '{n} reservations.',
    shelfReady: 'Your shelf is ready for something new.',
    backOn: 'Back on {weekday}',
    backDate: 'Back {date}',
    lateSince: 'Due since {date}',
    inDays: 'in {days}',
    lentBy: 'Lent by {branch}',
    position: '{at} of {total}',
    statusRefreshing: 'Refreshing…',
    statusAttention: 'Needs attention',
    statusSynced: 'Synced {time}',
    statusNotConnected: 'Not connected',
    statusOffline: 'Panel disconnected',
    stale: 'The books below are from the last successful sync, {time}.',
    panelUnavailable: 'Panel connection unavailable. Reopen it through Home Assistant.',
    connectTitle: 'Connect in Home Assistant settings.',
    connectConfigured: 'Automatic sign\u2011in is configured.',
    connectSession: 'Your session is saved.',
    connectHow:
      'Open Settings → Apps → Wise Library → Configuration. Enter your library username and password, ' +
      'then save and restart the app.',
    connectNote:
      'Credentials stay in Home Assistant. Sessions are reused; sign-in runs only when needed. ' +
      'For logins that need extra verification, import a session file instead.',
    importLabel: 'Optional: import a library session',
    importButton: 'Import session',
    importTooLarge: 'Choose a session JSON file smaller than 2 MB.',
    importDone: 'Session imported. Checking your library…',
    lastSync: 'Last successful sync · {time}',
    waitingCredentials: 'Credentials configured. Waiting for the first successful sync…',
    waitingSession: 'Session imported. Waiting for the first successful sync…',
    needCredentials: 'Enter your library credentials in the app Configuration tab to connect.',
    mqttOn: 'Home Assistant · MQTT connected',
    mqttOff: 'Home Assistant · MQTT disconnected',
    openConnection: 'Library card and connection',
  },
  nl: {
    locale: 'nl-NL',
    appName: 'Bibliotheek',
    refresh: 'Bibliotheek verversen',
    close: 'Sluiten',
    borrowed: 'Geleend',
    reserved: 'Gereserveerd',
    renew: 'Verlengen',
    renewAll: 'Alles verlengen',
    renewConfirm: 'Tik nogmaals om te verlengen',
    renewAllConfirm: 'Tik nogmaals om alles te verlengen',
    renewing: 'Verlengen…',
    renewsTo: 'Te verlengen tot {date}.',
    notOffered: 'De bibliotheek biedt dit boek nu niet aan om te verlengen.',
    openInWise: 'Openen in Wise',
    manageInWise: 'Beheren in Wise',
    renewed: 'verlengd',
    today: 'vandaag',
    day: '1 dag',
    days: '{n} dagen',
    lateDay: '1 dag te laat',
    lateDays: '{n} dagen te laat',
    late: 'te laat',
    bookLabel: '{title}, terug op {date}, {days}',
    holdLabel: '{title}, gereserveerd',
    glanceNone: 'Op dit moment niets geleend.',
    glanceOverdueOne: 'Eén boek is te laat.',
    glanceOverdueMany: '{n} boeken zijn te laat.',
    glanceToday: 'Eén boek moet vandaag terug.',
    glanceTomorrow: 'Eén boek moet morgen terug.',
    glanceOn: 'Eén boek moet {weekday} terug.',
    glanceSoonMany: '{n} boeken moeten binnen drie dagen terug.',
    glanceLater: 'Niets hoeft terug vóór {date}.',
    glanceWaiting: 'Wachten op de eerste synchronisatie.',
    glanceConnect: 'Koppel je bibliotheekpas.',
    glanceOpening: 'De bibliotheek gaat open…',
    reservedOne: 'Eén reservering.',
    reservedMany: '{n} reserveringen.',
    shelfReady: 'Je plank is klaar voor iets nieuws.',
    backOn: '{weekday} terug',
    backDate: 'Terug op {date}',
    lateSince: 'Te laat sinds {date}',
    inDays: 'over {days}',
    lentBy: 'Geleend bij {branch}',
    position: '{at} van {total}',
    statusRefreshing: 'Verversen…',
    statusAttention: 'Aandacht nodig',
    statusSynced: 'Bijgewerkt {time}',
    statusNotConnected: 'Niet verbonden',
    statusOffline: 'Paneel niet verbonden',
    stale: 'De boeken hieronder komen uit de laatste geslaagde synchronisatie, {time}.',
    panelUnavailable: 'Geen verbinding met het paneel. Open het opnieuw via Home Assistant.',
    connectTitle: 'Koppel in de instellingen van Home Assistant.',
    connectConfigured: 'Automatisch inloggen is ingesteld.',
    connectSession: 'Je sessie is opgeslagen.',
    connectHow:
      'Open Instellingen → Apps → Wise Library → Configuratie. Vul je gebruikersnaam en wachtwoord van de ' +
      'bibliotheek in, sla op en herstart de app.',
    connectNote:
      'Inloggegevens blijven in Home Assistant. Sessies worden hergebruikt; inloggen gebeurt alleen als het ' +
      'nodig is. Vraagt het inloggen om extra verificatie, importeer dan een sessiebestand.',
    importLabel: 'Optioneel: een bibliotheeksessie importeren',
    importButton: 'Sessie importeren',
    importTooLarge: 'Kies een sessiebestand (JSON) kleiner dan 2 MB.',
    importDone: 'Sessie geïmporteerd. Je bibliotheek wordt gecontroleerd…',
    lastSync: 'Laatste geslaagde synchronisatie · {time}',
    waitingCredentials: 'Inloggegevens ingesteld. Wachten op de eerste geslaagde synchronisatie…',
    waitingSession: 'Sessie geïmporteerd. Wachten op de eerste geslaagde synchronisatie…',
    needCredentials: 'Vul je inloggegevens in op het tabblad Configuratie van de app om te koppelen.',
    mqttOn: 'Home Assistant · MQTT verbonden',
    mqttOff: 'Home Assistant · MQTT niet verbonden',
    openConnection: 'Bibliotheekpas en verbinding',
  },
};

// Home Assistant's front-end stores the chosen language JSON-encoded under `selectedLanguage` on this origin.
export function pickLanguage(stored, browser) {
  let chosen = null;
  try {
    chosen = JSON.parse(stored);
  } catch {
    // Another application writes this key; a value that is not JSON counts as no choice.
  }
  return String(chosen || browser).toLowerCase().startsWith('nl') ? 'nl' : 'en';
}

export function translator(language) {
  const text = TEXT[language];
  const t = (key, values = {}) => text[key].replace(/\{(\w+)\}/g, (_, name) => values[name]);
  const format = (iso, options) => atNoon(iso).toLocaleDateString(text.locale, options).replaceAll('.', '');
  const shortDate = iso => format(iso, {day: 'numeric', month: 'short'});
  return {
    t,
    language,
    weekday: iso => format(iso, {weekday: 'long'}),
    longDate: iso => format(iso, {day: 'numeric', month: 'long'}),
    shortDate,
    weekdayDate: iso => `${format(iso, {weekday: 'short'})} ${shortDate(iso)}`,
    time: stamp => new Date(stamp).toLocaleTimeString(text.locale, {hour: '2-digit', minute: '2-digit'}),
    dateTime: stamp => new Date(stamp).toLocaleString(text.locale, {dateStyle: 'medium', timeStyle: 'short'}),
    days(count) {
      if (count === 0) return t('today');
      if (count < 0) return count === -1 ? t('lateDay') : t('lateDays', {n: -count});
      return count === 1 ? t('day') : t('days', {n: count});
    },
  };
}
