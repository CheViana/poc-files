from aiohttp import web
import secrets
import string

app = web.Application()


async def hello(request):
    return web.Response(text="Hello, world")


def get_random_str():
    return ''.join(
        secrets.choice(string.ascii_lowercase + string.digits) for i in range(8)
    )


async def responder(request):
    data = await request.json()
    print(f"Received request {data}, headers {request.headers}")
    reply_key = request.headers.get("ce-kafkaheadercereplykey", "111")
    return web.json_response({'status': 'wonder received','key': reply_key}, headers={
        "Ce-Id": f"reply-{reply_key}-{get_random_str()}",
        "Ce-Specversion": "1.0",
        "Ce-Type": "reply",
        "Ce-Source": "wonderland-responder",
        "Ce-callbackkey": reply_key
    }, content_type='application/json')


app.add_routes([web.post('/responder/', responder)])
app.add_routes([web.post('/responder', responder)])
app.add_routes([web.get('/responder/', responder)])
app.add_routes([web.get('/responder', responder)])
app.add_routes([web.get('/', hello)])
web.run_app(app, port=8083)
