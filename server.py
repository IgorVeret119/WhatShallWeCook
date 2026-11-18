"""Local development server: python server.py, then http://127.0.0.1:8000."""
import argparse
import json
import re
import secrets
from http.cookies import SimpleCookie,CookieError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from recipes import ROOT, detail, search
from nutrition import adjust, catalog
from favorites import set_favorite
from preferences import get_preferences,save_preferences,merge_exclusions

class Handler(BaseHTTPRequestHandler):
    def respond(self, status, body, mime='application/json; charset=utf-8'):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        if getattr(self,'new_profile_cookie',None):
            self.send_header('Set-Cookie','pet_profile='+self.new_profile_cookie+'; Path=/; Max-Age=31536000; HttpOnly; SameSite=Lax')
        self.end_headers()
        self.wfile.write(body)

    def profile_token(self):
        if hasattr(self,'_profile_token'):
            return self._profile_token
        cookies=SimpleCookie()
        try:cookies.load(self.headers.get('Cookie',''))
        except CookieError:pass
        value=cookies['pet_profile'].value if 'pet_profile' in cookies else ''
        if not re.fullmatch(r'[a-f0-9]{64}',value):
            value=secrets.token_hex(32)
            self.new_profile_cookie=value
        self._profile_token=value
        return value

    def profile_search_params(self,params):
        preferences=get_preferences(self.profile_token())
        if preferences['excluded_products']:
            params['exclude']=merge_exclusions(preferences,params.get('exclude',''))
        if preferences['liked_products']:
            params['preferred']=','.join(preferences['liked_products'])
        return params

    def do_GET(self):
        url = urlsplit(self.path)
        try:
            if len(self.path) > 8192:
                return self.respond(414, {'error': 'Слишком длинный запрос.'})
            if url.path == '/':
                self.profile_token()
                return self.respond(200, (ROOT / 'app' / 'index.html').read_bytes(), 'text/html; charset=utf-8')
            if url.path == '/preferences.js':
                return self.respond(200,(ROOT/'app'/'preferences.js').read_bytes(),'text/javascript; charset=utf-8')
            if url.path == '/nutrition-search.js':
                return self.respond(200,(ROOT/'app'/'nutrition-search.js').read_bytes(),'text/javascript; charset=utf-8')
            if url.path == '/kitchen-background.jpg':
                return self.respond(200,(ROOT/'app'/'kitchen-background.jpg').read_bytes(),'image/jpeg')
            if url.path == '/title-calligraphy.png':
                return self.respond(200,(ROOT/'app'/'title-calligraphy.png').read_bytes(),'image/png')
            if url.path == '/title-calligraphy-en.png':
                return self.respond(200,(ROOT/'app'/'title-calligraphy-en.png').read_bytes(),'image/png')
            if url.path == '/i18n.js':
                return self.respond(200,(ROOT/'app'/'i18n.js').read_bytes(),'text/javascript; charset=utf-8')
            if url.path == '/theme.css':
                return self.respond(200,(ROOT/'app'/'theme.css').read_bytes(),'text/css; charset=utf-8')
            if url.path == '/api/preferences':
                return self.respond(200,get_preferences(self.profile_token()))
            if url.path == '/planner.js':
                return self.respond(200,(ROOT/'app'/'planner.js').read_bytes(),'text/javascript; charset=utf-8')
            if url.path == '/favorites.js':
                return self.respond(200,(ROOT/'app'/'favorites.js').read_bytes(),'text/javascript; charset=utf-8')
            if url.path == '/api/favorites':
                params={k:v[-1] for k,v in parse_qs(url.query).items()}
                params['favorites_only']='1'
                return self.respond(200,search(self.profile_search_params(params)))
            if url.path == '/api/recipes':
                params = {k: v[-1] for k, v in parse_qs(url.query).items()}
                return self.respond(200, search(self.profile_search_params(params)))
            if url.path == '/api/nutrition/foods':
                exclusions=merge_exclusions(get_preferences(self.profile_token()),parse_qs(url.query).get('exclude',[''])[-1])
                return self.respond(200,{'foods':catalog(exclusions)})
            balance=re.fullmatch(r'/api/recipes/(\d+)/balance',url.path)
            if balance:
                params={k:v[-1] for k,v in parse_qs(url.query).items()}
                item=detail(int(balance.group(1)),language=params.get('lang','ru'))
                if not item:
                    return self.respond(404,{'error':'Рецепт не найден.'})
                params['exclude']=merge_exclusions(get_preferences(self.profile_token()),params.get('exclude',''))
                return self.respond(200,adjust(item,params))
            if url.path.startswith('/api/recipes/'):
                language = parse_qs(url.query).get('lang', ['ru'])[-1]
                item = detail(int(url.path.rsplit('/', 1)[1]), language=language)
                return self.respond(200 if item else 404, item or {'error': 'Рецепт не найден.'})
            return self.respond(404, {'error': 'Страница не найдена.'})
        except ValueError as error:
            self.respond(400, {'error': str(error)})
        except Exception:
            import traceback
            traceback.print_exc()
            self.respond(500, {'error': 'Ошибка базы данных. Подробности в консоли сервера.'})

    def update_favorite(self,saved):
        try:
            url=urlsplit(self.path)
            match=re.fullmatch(r'/api/favorites/(\d+)',url.path)
            if not match:
                return self.respond(404,{'error':'Страница не найдена.'})
            origin=self.headers.get('Origin')
            if origin and urlsplit(origin).netloc!=self.headers.get('Host'):
                return self.respond(403,{'error':'Недопустимый источник запроса.'})
            recipe_id=int(match.group(1))
            if saved and not detail(recipe_id):
                return self.respond(404,{'error':'Рецепт не найден.'})
            return self.respond(200,set_favorite(recipe_id,saved))
        except ValueError as error:
            return self.respond(400,{'error':str(error)})
        except Exception:
            import traceback
            traceback.print_exc()
            return self.respond(500,{'error':'Не удалось сохранить любимое блюдо. Попробуйте ещё раз.'})

    def do_POST(self):
        self.update_favorite(True)

    def do_DELETE(self):
        self.update_favorite(False)

    def do_PUT(self):
        try:
            if urlsplit(self.path).path!='/api/preferences':
                return self.respond(404,{'error':'Страница не найдена.'})
            origin=self.headers.get('Origin')
            if origin and urlsplit(origin).netloc!=self.headers.get('Host'):
                return self.respond(403,{'error':'Недопустимый источник запроса.'})
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=16384:
                return self.respond(400,{'error':'Некорректный размер списка.'})
            updates=json.loads(self.rfile.read(size).decode('utf-8'))
            return self.respond(200,save_preferences(self.profile_token(),updates))
        except (ValueError,UnicodeError) as error:
            return self.respond(400,{'error':str(error)})
        except Exception:
            import traceback
            traceback.print_exc()
            return self.respond(500,{'error':'Не удалось сохранить продукты. Попробуйте ещё раз.'})

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f'Recipe search: http://{args.host}:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == '__main__':
    main()
