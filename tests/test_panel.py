"""Drive the panel in Chromium against the real app routes, with a fake runtime behind them."""

import json
import tempfile
import time
import unittest
from datetime import date
from pathlib import Path

from aiohttp.test_utils import TestServer
from playwright.async_api import async_playwright
from test_server import FakeRuntime

from wise_library.app.domain import summarize
from wise_library.app.server import create_app

TODAY = date(2026, 11, 27)
OFFER = "2026-12-28"
STORK = {
    "id": "101",
    "title": "Het lied van ooievaar en dromedaris",
    "author": "",
    "isbn": "",
    "cover": False,
    "due_date": "2026-11-30",
    "branch": "AanZet Dordrecht",
    "renew_until": OFFER,
    "renew_id": "9101",
}
CAMINO = {
    **STORK,
    "id": "102",
    "renew_id": "9102",
    "title": "De Camino",
    "due_date": "2026-12-04",
    "branch": "AanZet Zwijndrecht",
}
LIGHT = {**STORK, "id": "103", "renew_id": "9103", "title": "Wij zijn licht", "due_date": "2026-12-11"}
HOLD = {
    "id": "hold|De zeven zussen|STANDARD|0",
    "title": "De zeven zussen",
    "author": "",
    "isbn": "",
    "cover": False,
    "details": "De zeven zussen\nLigt klaar tot 02-12-2026",
    "collection": "STANDARD",
}
LOANS_URL = "https://bibliotheek.wise.oclc.org/wise-apps/opac/branch/2709/my-account/checkouts/physical-materials"
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360f8cfc0f01f0005000201"
    "a5f645400000000049454e44ae426082"
)
REFUSED = "The library refused the sign-in."


def snapshot(loans, reservations=()):
    return {
        **summarize(loans, TODAY),
        "reservation_count": len(reservations),
        "loans": loans,
        "reservations": list(reservations),
    }


class PanelTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = FakeRuntime(Path(self.tmp.name))
        self.runtime.options.update(library_username="reader", library_password="secret")
        self.runtime.last_requested = time.monotonic() - 3600
        self.runtime.last_success = "2026-11-27T09:02:00+01:00"
        self.runtime.snapshot = snapshot([CAMINO, STORK, LIGHT], [HOLD])
        self.server = TestServer(create_app(self.runtime, local=True))
        await self.server.start_server()
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch()
        await self.use(locale="en-GB")

    async def asyncTearDown(self):
        await self.browser.close()
        await self.playwright.stop()
        await self.server.close()
        self.tmp.cleanup()

    async def use(self, locale, width=390, height=844):
        self.context = await self.browser.new_context(
            viewport={"width": width, "height": height}, locale=locale, timezone_id="Europe/Amsterdam"
        )
        self.page = await self.context.new_page()
        self.console = []
        self.page.on("console", lambda message: self.console.append(message.text))
        await self.page.clock.set_fixed_time("2026-11-27T10:00:00")

    async def open(self):
        await self.page.goto(f"http://127.0.0.1:{self.server.port}/")
        await self.page.locator("#sync:not(:empty)").wait_for()

    async def labels(self):
        return await self.page.locator("#shelves .slot[data-id] .cardlet").all_inner_texts()

    async def show_decorations(self):
        await self.open()
        await self.page.evaluate("""async () => {
            const {DECORATIONS} = await import('/static/decorations.js');
            document.querySelector('#shelves').innerHTML = DECORATIONS.map(item =>
                `<li class="slot prop" data-decoration="${item.key}">${item.art}<div class="board"></div></li>`).join('');
        }""")

    async def test_reservation_status_is_a_compact_label_on_the_board(self):
        await self.open()
        for width in (390, 1100):
            await self.page.set_viewport_size({"width": width, "height": 900})
            dimensions = await self.page.locator('#held .slot').evaluate("""el => {
                const board = el.querySelector('.board').getBoundingClientRect();
                const label = el.querySelector('.slip').getBoundingClientRect();
                return [label.top >= board.top, label.bottom <= board.bottom, label.height <= 30];
            }""")
            self.assertEqual(dimensions, [True, True, True])
        await self.page.locator('#held .slip').click()
        await self.page.locator('#room[open]').wait_for()
        self.assertIn(HOLD['title'], await self.page.locator('#room .page').last.inner_text())

    async def test_sparse_shelves_get_more_unique_decorations_per_row(self):
        await self.use(locale='en-GB', width=1100, height=1000)
        density = []
        for count in (4, 15):
            self.runtime.snapshot = snapshot([
                {**CAMINO, 'id':str(i), 'title':f'Book {i}'} for i in range(count)
            ], [{**HOLD, 'id':f'hold{i}'} for i in range(5)])
            await self.open()
            keys = await self.page.locator('[data-decoration]').evaluate_all(
                '(els) => els.map(el => el.dataset.decoration)')
            self.assertEqual(len(keys), len(set(keys)), keys)
            self.assertIn('cat', keys)
            self.assertIn('candle', keys)
            density.append(await self.page.locator('#shelves').evaluate("""el => {
                const rows = el.children.length / Number(getComputedStyle(el).getPropertyValue('--cols'));
                return el.querySelectorAll('[data-decoration]').length / rows;
            }"""))
        self.assertGreater(density[0], density[1], density)

    async def test_composed_shelves_always_include_companions_and_keep_reservations_below(self):
        await self.open()
        for count in (0, 1, 4, 9, 15):
            for width in (320, 390, 820, 1100):
                await self.page.set_viewport_size({"width": width, "height": 900})
                await self.page.evaluate("""async count => {
                    const {renderShelves} = await import('/static/views.js');
                    const loans = Array.from({length:count}, (_, i) => ({
                        id:String(i), title:'Book '+i, due_date:'2026-12-07', cover:false
                    }));
                    const {translator} = await import('/static/i18n.js');
                    renderShelves(document.querySelector('#shelves'), loans, {
                        today:new Date('2026-11-27T12:00:00'), renewed:new Set(), i18n:translator('en'), open:()=>{}
                    });
                }""", count)
                self.assertEqual(await self.page.locator('#shelves [data-decoration="cat"]').count(), 1)
                self.assertEqual(await self.page.locator('#shelves [data-decoration="candle"]').count(), 1)
                self.assertEqual(await self.page.locator('#shelves [data-id]').evaluate_all(
                    '(els) => els.map(e => Number(e.dataset.id))'), list(range(count)))
                self.assertEqual(await self.page.locator('#shelves').evaluate(
                    '(el) => el.children.length % Number(getComputedStyle(el).getPropertyValue("--cols"))'), 0)
                self.assertEqual(await self.page.locator('#held .reserve').count(), 1)
        boxes = await self.page.evaluate("""() => [document.querySelector('#shelves').getBoundingClientRect().bottom,
            document.querySelector('#reserved').getBoundingClientRect().top]""")
        self.assertLessEqual(boxes[0], boxes[1])

    async def test_plants_stay_still_while_tea_steam_rises(self):
        await self.show_decorations()
        plants = self.page.locator('[data-decoration="pothos"], [data-decoration="fern"], [data-decoration="flowers"]')
        self.assertEqual(await plants.evaluate_all(
            '(items) => items.flatMap(el => el.getAnimations({subtree:true})).length'), 0)
        steam = self.page.locator('.steam-wisp').first
        self.assertGreater(await steam.evaluate('(el) => el.getAnimations().length'), 0)
        self.assertEqual(await self.page.locator('.steam-wisp').count(), 3)

    async def test_flame_base_stays_at_the_wick_throughout_a_flicker(self):
        await self.show_decorations()
        offsets = await self.page.locator('.flame').evaluate("""el => {
            const animation = el.getAnimations()[0];
            animation.pause();
            return [0, 400, 800, 1200, 1600].map(time => {
                animation.currentTime = time;
                const matrix = new DOMMatrix(getComputedStyle(el).transform);
                const origin = getComputedStyle(el).transformOrigin.split(' ').map(parseFloat);
                const point = new DOMPoint(30-origin[0], 40-origin[1]).matrixTransform(matrix);
                return Math.hypot(point.x+origin[0]-30, point.y+origin[1]-40);
            });
        }""")
        self.assertTrue(all(offset < .01 for offset in offsets), offsets)

    async def test_decorations_rest_on_the_board_and_respect_reduced_motion(self):
        await self.show_decorations()
        self.assertEqual(await self.page.locator('#shelves .prop').count(), 10)
        self.assertEqual(await self.page.locator('[data-decoration="hourglass"]').count(), 0)
        for width in (320, 390, 820, 1100):
            await self.page.set_viewport_size({"width": width, "height": 1000})
            gaps = await self.page.locator('#shelves .prop').evaluate_all("""slots => slots.map(slot => {
                const anchor = slot.querySelector('[data-foot]');
                if (!anchor) return 0; // The corner web attaches overhead, not to the board.
                const svg = slot.querySelector('svg');
                const point = new DOMPoint(0, Number(anchor.dataset.foot)).matrixTransform(svg.getScreenCTM());
                return slot.querySelector('.board').getBoundingClientRect().top - point.y;
            })""")
            self.assertTrue(all(abs(gap) < 0.75 for gap in gaps), gaps)
        self.assertGreater(await self.page.locator('.cat-breath').evaluate('(el) => el.getAnimations().length'), 0)
        await self.page.emulate_media(reduced_motion='reduce')
        self.assertEqual(await self.page.locator('#shelves').evaluate(
            '(el) => el.getAnimations({subtree:true}).length'), 0)

    async def states(self):
        return await self.page.locator("#shelves .slot[data-id]").evaluate_all("slots => slots.map(s => s.className)")

    async def test_books_stand_in_return_order_with_their_dates(self):
        await self.open()
        titles = await self.page.locator("#shelves .book").evaluate_all("books => books.map(b => b.ariaLabel)")
        self.assertEqual(
            [title.split(",")[0] for title in titles],
            ["Het lied van ooievaar en dromedaris", "De Camino", "Wij zijn licht"],
        )
        dates = [label.split()[:2] for label in await self.labels()]
        self.assertEqual(dates, [["30", "NOV"], ["4", "DEC"], ["11", "DEC"]])

    async def test_glance_names_the_day_and_the_book_that_goes_back_next(self):
        await self.open()
        self.assertEqual(await self.page.inner_text("#glance"), "One book goes back Monday.")
        self.assertEqual(await self.page.inner_text("#also"), "Het lied van ooievaar en dromedaris · One reservation.")

    async def test_glance_gives_the_next_date_when_nothing_is_close(self):
        self.runtime.snapshot = snapshot([LIGHT, CAMINO])
        await self.open()
        self.assertEqual(await self.page.inner_text("#glance"), "Nothing is due until Fri 4 Dec.")
        self.assertTrue(await self.page.is_hidden("#reserved"))

    async def test_due_soon_and_overdue_books_are_marked_in_words_and_with_a_ribbon(self):
        late = {**LIGHT, "due_date": "2026-11-25"}
        self.runtime.snapshot = snapshot([late, STORK, CAMINO])
        await self.open()
        self.assertEqual(await self.page.inner_text("#glance"), "One book is overdue.")
        self.assertEqual(await self.states(), ["slot overdue", "slot soon", "slot later"])
        self.assertEqual([label.split(None, 2)[2] for label in await self.labels()], ["late", "3 days", "7 days"])
        self.assertIn("2 days late", await self.page.locator("#shelves .book >> nth=0").get_attribute("aria-label"))
        self.assertEqual(await self.page.locator("#shelves .ribbon:visible").count(), 2)

    async def test_renewed_loan_is_marked_and_travels_to_its_place_in_return_order(self):
        await self.open()
        self.runtime.snapshot = snapshot([CAMINO, {**STORK, "due_date": "2026-12-21"}, LIGHT], [HOLD])
        await self.page.click("#refresh")
        renewed = self.page.locator("#shelves .slot.renewed")
        await renewed.wait_for()
        self.assertGreater(await renewed.locator(".book").evaluate("book => book.getAnimations().length"), 0)
        self.assertIn("Het lied van ooievaar", await renewed.locator(".book").get_attribute("aria-label"))
        self.assertEqual((await self.labels())[-1].split(), ["21", "DEC", "renewed"])
        self.assertEqual(await self.page.inner_text("#glance"), "Nothing is due until Fri 4 Dec.")

    async def test_renewed_loan_that_is_still_due_soon_keeps_the_due_soon_mark(self):
        self.runtime.snapshot = snapshot([{**STORK, "due_date": "2026-11-28"}, CAMINO])
        await self.open()
        self.runtime.snapshot = snapshot([STORK, CAMINO])
        await self.page.click("#refresh")
        await self.page.locator("#shelves .cardlet", has_text="30 NOV").wait_for()
        self.assertEqual(await self.states(), ["slot soon", "slot later"])

    async def test_dutch_is_used_when_home_assistant_stores_nl(self):
        await self.context.add_init_script("localStorage.setItem('selectedLanguage', JSON.stringify('nl'))")
        await self.open()
        self.assertEqual(await self.page.inner_text("#glance"), "Eén boek moet maandag terug.")
        self.assertEqual(await self.page.get_attribute("html", "lang"), "nl")
        self.assertEqual((await self.labels())[0].split(None, 2)[2], "3 dagen")

    async def test_browser_language_decides_when_home_assistant_stored_none_or_nonsense(self):
        await self.use(locale="nl-NL")
        await self.open()
        self.assertEqual(await self.page.get_attribute("html", "lang"), "nl")
        await self.use(locale="en-GB")
        await self.context.add_init_script("localStorage.setItem('selectedLanguage', 'not json')")
        await self.open()
        self.assertEqual(await self.page.inner_text("#glance"), "One book goes back Monday.")

    async def test_failed_sync_keeps_the_last_books_and_says_when_they_are_from(self):
        self.runtime.error = REFUSED
        await self.open()
        self.assertEqual(
            await self.page.inner_text("#notice"),
            f"{REFUSED} The books below are from the last successful sync, 27 Nov 2026, 09:02.",
        )
        self.assertEqual(await self.page.inner_text("#sync"), "Needs attention")
        self.assertEqual(await self.page.locator("#shelves .book").count(), 3)
        self.assertTrue(await self.page.is_visible("#attention"))

    async def test_lost_status_connection_is_said_and_keeps_the_books(self):
        await self.open()
        await self.page.route("**/api/status", lambda route: route.abort())
        await self.page.locator("#sync", has_text="Panel disconnected").wait_for(timeout=9000)
        self.assertEqual(
            await self.page.inner_text("#notice"), "Panel connection unavailable. Reopen it through Home Assistant."
        )
        self.assertEqual(await self.page.locator("#shelves .book").count(), 3)

    async def test_illustrated_spines_keep_titles_and_navigate_with_missing_cover_art(self):
        self.runtime.snapshot = snapshot([
            {**STORK, "isbn": "9781234567897", "cover": True}, CAMINO
        ], [HOLD])
        await self.open()
        await self.page.locator('#shelves .slot[data-id="101"]').click()
        spine = self.page.locator('#strip .spine[data-id="101"]')
        await spine.locator('.spine-art svg').wait_for()
        self.assertEqual(await spine.locator('.spine-title').inner_text(), STORK['title'])
        size = await spine.bounding_box()
        self.assertGreaterEqual(size['width'], 44)
        self.assertGreaterEqual(size['height'], 88)
        await self.page.locator('#strip .spine[data-id="102"]').click()
        await self.page.locator('#strip .spine.on[data-id="102"]').wait_for()
        self.assertEqual(await self.page.locator('#strip .spine.hold .spine-title').inner_text(), HOLD['title'])

    async def test_tapping_a_book_opens_it_alone_with_what_the_library_offers(self):
        await self.open()
        await self.page.click("#shelves .book >> nth=0")
        page = self.page.locator("#room[open] .page >> nth=0")
        self.assertEqual(await page.locator("h3").inner_text(), "Back on Monday")
        self.assertEqual(await page.locator(".say p").inner_text(), "30 November, in 3 days")
        self.assertEqual(await page.locator(".info p >> nth=0").inner_text(), "Lent by AanZet Dordrecht")
        self.assertEqual(await page.locator(".info .offer").inner_text(), "Can be renewed to 28 December.")
        self.assertEqual(await page.locator("button.do").inner_text(), "Renew")
        self.assertEqual(await self.page.inner_text("#position"), "Borrowed · 1 of 3")

    async def test_a_book_the_library_does_not_offer_for_renewal_links_to_wise_instead(self):
        self.runtime.snapshot = snapshot([{**STORK, "renew_until": None}, CAMINO], [HOLD])
        await self.open()
        await self.page.click("#shelves .book >> nth=0")
        page = self.page.locator("#room[open] .page >> nth=0")
        self.assertEqual(
            await page.locator(".info .offer").inner_text(), "The library offers no renewal for this book right now."
        )
        link = page.locator("a.do")
        self.assertEqual(await link.get_attribute("href"), LOANS_URL)
        self.assertEqual(await link.get_attribute("rel"), "noopener noreferrer")

    async def test_renewing_takes_two_taps_and_asks_the_app_to_renew_that_book(self):
        await self.open()
        await self.page.click("#shelves .book >> nth=0")
        button = self.page.locator('#room[open] [data-renew="101"]')
        await button.click()
        self.assertEqual(await button.inner_text(), "Tap again to renew")
        self.assertEqual(self.runtime.renewed, [])
        await button.click()
        await self.page.wait_for_timeout(300)
        self.assertEqual(self.runtime.renewed, [["9101"]])

    async def test_renew_all_asks_for_every_book_the_library_offers(self):
        self.runtime.snapshot = snapshot([STORK, {**CAMINO, "renew_until": None}, LIGHT], [HOLD])
        await self.open()
        button = self.page.locator("#renew-all")
        await button.click()
        self.assertEqual(await button.inner_text(), "Tap again to renew all")
        await button.click()
        await self.page.wait_for_timeout(300)
        self.assertEqual(self.runtime.renewed, [["9101", "9103"]])

    async def test_renew_all_is_hidden_when_nothing_can_be_renewed(self):
        self.runtime.snapshot = snapshot([{**STORK, "renew_until": None}], [HOLD])
        await self.open()
        self.assertTrue(await self.page.is_hidden("#renew-all"))

    async def test_a_renewal_the_library_refused_is_shown_with_its_reason(self):
        self.runtime.renewal = {"n": 1, "ids": ["101"], "state": "failed", "message": "The library did not confirm."}
        await self.open()
        self.assertEqual(await self.page.inner_text("#notice"), "The library did not confirm.")

    async def test_the_real_cover_is_shown_and_a_missing_file_falls_back_to_the_drawn_one(self):
        isbn = "9780306406157"
        (Path(self.tmp.name) / "covers" / f"{isbn}.img").write_bytes(PNG)
        self.runtime.snapshot = snapshot(
            [{**STORK, "isbn": isbn, "cover": True}, {**CAMINO, "isbn": "9781234567897", "cover": True}]
        )
        await self.open()
        real = self.page.locator("#shelves .book img.real")
        await real.wait_for()
        self.assertTrue((await real.get_attribute("src")).endswith(f"/api/cover/{isbn}?v=2"))
        await self.page.locator("#shelves .slot[data-id] >> nth=1 >> svg.art").wait_for()
        self.assertEqual(await self.page.locator("#shelves .book img.real").count(), 1)
        await self.page.locator("#shelves .book").first.click()
        await self.page.locator("#strip .spine-art svg.art").wait_for()
        self.assertEqual(await self.page.locator("#strip .spine-art img.real").count(), 1)
        self.assertEqual(await self.page.locator("#strip .spine-art svg.art").count(), 1)

    async def test_reservation_shows_the_portal_words_on_the_shelf_and_when_opened(self):
        await self.open()
        slip = self.page.locator("#held .slip")
        self.assertEqual(await slip.locator("b").text_content(), "De zeven zussen")
        self.assertEqual(await slip.locator("span").inner_text(), "Ligt klaar tot 02-12-2026")
        await self.page.click("#held .reserve")
        page = self.page.locator("#room[open] .page >> nth=3")
        await self.page.locator("#position", has_text="Reserved").wait_for()
        self.assertEqual(await page.locator(".said").inner_text(), "Ligt klaar tot 02-12-2026")
        self.assertTrue((await page.locator("a.do").get_attribute("href")).endswith("/my-account/my-holds"))

    async def test_empty_shelf_and_missing_connection_each_say_so(self):
        self.runtime.snapshot = snapshot([])
        await self.open()
        self.assertEqual(await self.page.inner_text("#glance"), "Nothing borrowed right now.")
        self.assertEqual(await self.page.inner_text("#also"), "Your shelf is ready for something new.")
        self.runtime.snapshot = None
        self.runtime.last_success = None
        self.runtime.options.update(library_username="", library_password="")
        await self.open()
        self.assertEqual(await self.page.inner_text("#glance"), "Connect your library card.")
        self.assertTrue(await self.page.is_disabled("#refresh"))

    async def test_refresh_refused_by_the_rate_limit_shows_the_reason(self):
        self.runtime.last_requested = time.monotonic()
        await self.open()
        await self.page.click("#refresh")
        await self.page.wait_for_selector("#notice:not([hidden])")
        self.assertEqual(await self.page.inner_text("#notice"), "Please wait one minute between refresh requests.")

    async def test_session_import_still_posts_with_the_csrf_token(self):
        await self.open()
        await self.page.click("#open-connection")
        cookie = {"name": "s", "value": "v", "domain": "bibliotheek.wise.oclc.org", "path": "/"}
        body = json.dumps({"cookies": [cookie], "origins": []}).encode()
        upload = {"name": "storage-state.json", "mimeType": "application/json", "buffer": body}
        await self.page.set_input_files("#session-file", upload)
        await self.page.click("#session-form button")
        await self.page.locator("#upload-message:not(:empty)").wait_for()
        self.assertEqual(await self.page.inner_text("#upload-message"), "Session imported. Checking your library…")
        self.assertTrue((Path(self.tmp.name) / "storage-state.json").exists())

    async def test_touch_targets_meet_forty_four_pixels(self):
        await self.open()
        await self.page.click("#shelves .book >> nth=0")
        sizes = await self.page.evaluate(
            """() => {
                const box = element => element.getBoundingClientRect();
                const spine = document.querySelector('.spine');
                const reach = getComputedStyle(spine, '::before');
                const spineWidth = box(spine).width - parseFloat(reach.left) - parseFloat(reach.right);
                const link = box(document.getElementById('renew-all')).height;
                const button = box(document.getElementById('refresh')).width;
                return [link, button, box(document.querySelector('#room a.do')).height, spineWidth];
            }"""
        )
        self.assertEqual([size >= 44 for size in sizes], [True, True, True, True])

    async def test_tablet_width_composes_complete_rows_with_companions(self):
        await self.use(locale="en-GB", width=820, height=1180)
        await self.open()
        self.assertEqual(await self.page.locator("#shelves .slot").count(), 10)
        self.assertEqual(await self.page.locator("#shelves .book").count(), 3)

    async def test_back_control_takes_taps_on_its_label_and_the_phone_back_gesture(self):
        await self.open()
        await self.page.click("#shelves .book >> nth=0")
        await self.page.locator("#room[open]").wait_for()
        await self.page.get_by_role("button", name="Library", exact=True).click()
        await self.page.locator("#room").wait_for(state="hidden")
        await self.page.click("#shelves .book >> nth=1")
        await self.page.locator("#room[open]").wait_for()
        await self.page.go_back()
        await self.page.locator("#room").wait_for(state="hidden")
        self.assertTrue(await self.page.is_visible("#shelves"))

    async def test_tapping_a_date_label_or_the_named_book_opens_that_book(self):
        await self.open()
        await self.page.click("#shelves .slot[data-id] >> nth=1 >> .cardlet")
        self.assertEqual(await self.page.inner_text("#position"), "Borrowed · 2 of 3")
        await self.page.keyboard.press("Escape")
        await self.page.locator("#room").wait_for(state="hidden")
        await self.page.click("#also button")
        self.assertEqual(await self.page.inner_text("#position"), "Borrowed · 1 of 3")

    async def test_tapping_outside_the_connection_sheet_closes_it(self):
        await self.open()
        await self.page.click("#open-connection")
        await self.page.locator("#connection[open]").wait_for()
        await self.page.mouse.click(195, 30)
        await self.page.locator("#connection").wait_for(state="hidden")

    async def test_panel_runs_inside_the_content_security_policy(self):
        await self.open()
        await self.page.click("#shelves .book >> nth=0")
        await self.page.wait_for_selector("#room[open] .cover svg")
        loaded = "document.fonts.ready.then(() => document.fonts.check('20px \"Libre Caslon Display\"'))"
        self.assertTrue(await self.page.evaluate(loaded))
        self.assertEqual([line for line in self.console if "Content Security Policy" in line or "Refused" in line], [])

    async def test_selecting_book_animates_cover_and_respects_reduced_motion(self):
        await self.open()
        await self.page.locator('#shelves .book').first.click()
        cover = self.page.locator('#feed .page').first.locator('.cover')
        self.assertGreater(await cover.evaluate('(el) => el.getAnimations().length'), 0)
        await self.page.emulate_media(reduced_motion='reduce')
        await self.page.evaluate("document.querySelector('#room').close()")
        await self.page.locator('#shelves .book').first.click()
        self.assertEqual(await cover.evaluate('(el) => el.getAnimations().length'), 0)
