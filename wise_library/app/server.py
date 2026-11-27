import asyncio
import json
import logging
import os
import re
import secrets
import time
import traceback
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from aiohttp import web
from .domain import PortalError, AuthenticationError, library_only, summarize, validate_session
from .bridge import MqttBridge
from .portal import Portal

APP_DIR = Path(__file__).parent
STATIC = APP_DIR / 'static'
log = logging.getLogger('wise_library')
DEFAULTS = {'branch_id':'2709', 'account_id':'home', 'poll_interval_minutes':60,
            'timezone':'Europe/Amsterdam', 'mqtt_host':'core-mosquitto', 'mqtt_port':1883,
            'mqtt_username':'', 'mqtt_password':'', 'library_username':'', 'library_password':''}


def write_private(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value), encoding='utf-8')
    temporary.chmod(0o600)
    temporary.replace(path)


class Runtime:
    def __init__(self, options, data_dir):
        self.options = options
        self.data_dir = data_dir
        self.csrf = secrets.token_urlsafe(32)
        self.last_success = None
        self.error = None
        self.snapshot = None
        self.busy = False
        self.auth_blocked = False
        self.last_requested = 0
        self.wake = asyncio.Event()
        self.bridge = MqttBridge(options)
        self.portal = Portal(options['branch_id'], data_dir / 'storage-state.json',
                             username=options.get('library_username', ''), password=options.get('library_password', ''))

    async def refresh(self):
        self.busy = True
        log.info('Refresh started')
        try:
            loans, reservations, refreshed = await self.portal.read()
            write_private(self.data_dir / 'storage-state.json', validate_session(library_only(refreshed)))
            now = datetime.now(ZoneInfo(self.options['timezone']))
            summary = summarize(loans, now.date())
            summary['reservation_count'] = len(reservations)
            self.last_success = now.isoformat()
            self.snapshot = {**summary, 'loans':loans, 'reservations':reservations}
            self.bridge.update(summary, {'loans':loans, 'reservations':reservations, 'last_success':self.last_success})
            self.error = None
            self.auth_blocked = False
            log.info('Refresh succeeded: %d loans, %d reservations', len(loans), len(reservations))
        except AuthenticationError as error:
            log.warning('Refresh failed; automatic refresh paused until Refresh is pressed or the app restarts: %s',
                        error)
            self.error = str(error)
            self.auth_blocked = True
            self.bridge.unavailable()
        except PortalError as error:
            log.warning('Refresh failed: %s', error)
            self.error = str(error)
            self.bridge.unavailable()
        except Exception as error:
            # Browser exception messages can contain URLs or auth details; log only the type and our code location.
            frames = traceback.extract_tb(error.__traceback__)
            frame = [f for f in frames if Path(f.filename).is_relative_to(APP_DIR)][-1]
            log.error('Refresh failed: %s at %s:%s', type(error).__name__, Path(frame.filename).name, frame.lineno)
            self.error = ('Refresh failed. Check the session, network and supported Dutch portal layout. '
                          'Details are in the app log.')
            self.bridge.unavailable()
        finally:
            self.busy = False

    async def poll(self):
        self.bridge.start()
        try:
            while True:
                configured = bool(self.options.get('library_username') and self.options.get('library_password'))
                if not self.auth_blocked and (configured or (self.data_dir / 'storage-state.json').exists()):
                    await self.refresh()
                try:
                    await asyncio.wait_for(self.wake.wait(), self.options['poll_interval_minutes'] * 60)
                except asyncio.TimeoutError:
                    pass
                self.wake.clear()
        finally:
            self.bridge.stop()


def create_app(runtime, local=False):
    @web.middleware
    async def protect(request, handler):
        if local:
            trusted = request.remote in {'127.0.0.1','::1'} and request.host.split(':')[0] in {'127.0.0.1','localhost'}
        else:
            trusted = request.remote == '172.30.32.2'
        if not trusted:
            raise web.HTTPForbidden(text='Use Home Assistant ingress.')
        if request.method != 'GET' and not secrets.compare_digest(request.headers.get('X-CSRF-Token',''), runtime.csrf):
            raise web.HTTPForbidden(text='Reload the panel before trying again.')
        response = await handler(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; object-src 'none'; base-uri 'none'"
        return response

    async def index(request):
        return web.FileResponse(STATIC / 'index.html')

    async def status(request):
        return web.json_response({'csrf':runtime.csrf, 'busy':runtime.busy, 'error':runtime.error,
            'credentials_configured':bool(runtime.options.get('library_username') and runtime.options.get('library_password')),
            'last_success':runtime.last_success, 'mqtt_connected':runtime.bridge.connected,
            'session_present':(runtime.data_dir / 'storage-state.json').exists(), 'snapshot':runtime.snapshot,
            'portal_url':f"https://bibliotheek.wise.oclc.org/wise-apps/opac/branch/{runtime.options['branch_id']}/my-account"})

    async def session(request):
        if runtime.busy:
            raise web.HTTPConflict(text='A refresh is running; try again shortly.')
        try:
            state = validate_session(await request.json())
        except (ValueError, TypeError, AttributeError):
            raise web.HTTPBadRequest(text='Invalid session file or unsupported library hosts.') from None
        write_private(runtime.data_dir / 'storage-state.json', state)
        runtime.error = None
        runtime.auth_blocked = False
        runtime.wake.set()
        return web.json_response({'ok':True})

    async def refresh(request):
        configured = bool(runtime.options.get('library_username') and runtime.options.get('library_password'))
        if not configured and not (runtime.data_dir / 'storage-state.json').exists():
            raise web.HTTPConflict(text='Enter your library credentials in the app Configuration tab, or import a session first.')
        if runtime.busy or time.monotonic() - runtime.last_requested < 60:
            raise web.HTTPTooManyRequests(text='Please wait one minute between refresh requests.')
        runtime.last_requested = time.monotonic()
        runtime.auth_blocked = False
        runtime.wake.set()
        return web.json_response({'ok':True})

    app = web.Application(middlewares=[protect], client_max_size=2 * 1024 * 1024)
    app.router.add_get('/', index)
    app.router.add_get('/api/status', status)
    app.router.add_post('/api/session', session)
    app.router.add_post('/api/refresh', refresh)
    app.router.add_static('/static/', STATIC)
    return app


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    options = dict(DEFAULTS)
    config = Path(os.environ.get('WISE_OPTIONS', '/data/options.json'))
    if config.exists():
        options.update(json.loads(config.read_text(encoding='utf-8')))
    if not re.fullmatch(r'[0-9]{1,8}', options['branch_id']) or not re.fullmatch(r'[a-z0-9_]{1,32}', options['account_id']):
        raise SystemExit('Invalid branch_id or account_id.')
    if not 15 <= options['poll_interval_minutes'] <= 1440:
        raise SystemExit('poll_interval_minutes must be between 15 and 1440.')
    ZoneInfo(options['timezone'])
    data_dir = Path(os.environ.get('WISE_DATA', '/data/session'))
    data_dir.mkdir(parents=True, exist_ok=True)
    data_dir.chmod(0o700)
    runtime = Runtime(options, data_dir)
    local = os.environ.get('WISE_LOCAL') == '1'
    app = create_app(runtime, local)

    async def polling(application):
        task = asyncio.create_task(runtime.poll())
        yield
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    app.cleanup_ctx.append(polling)
    web.run_app(app, host='127.0.0.1' if local else '0.0.0.0', port=8099, access_log=None)


if __name__ == '__main__':
    main()
