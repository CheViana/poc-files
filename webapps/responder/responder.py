from aiohttp import web, ClientSession
import os
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
    # reply_broker = os.getenv("REPLY_BROKER", "http://kafka-broker-ingress.knative-eventing.svc.cluster.local/knative-eventing/wonderland-broker")
    reply_key = request.headers.get("ce-kafkaheadercereplykey", "111")

    # async with ClientSession() as session:
    #     async with session.post(
    #         reply_broker,
    #         json={
    #             'status': 'received',
    #             'key': reply_key
    #         },
    #         headers={
    #             'Content-Type': 'application/json',
    #             "Ce-Id": f"reply-{reply_key}-{get_random_str()}",
    #             "Ce-Specversion": "1.0",
    #             "Ce-Type": "reply",
    #             "Ce-Source": "wonderland-responder",
    #             "Ce-callbackkey": reply_key
    #         }
    #     ) as resp:
    #         status = resp.status
    #         response_text = await resp.text()
    #         print(f"Fired callback {status} {response_text}")

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
