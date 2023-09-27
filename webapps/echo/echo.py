from aiohttp import web


app = web.Application()


async def hello(request):
    return web.Response(text="Hello, world")


async def echo(request):
    data = await request.text()
    print(f"Received request {data}, headers {request.headers}")
    return web.Response(text=f"Received request {data}")


app.add_routes([web.post('/echo/', echo)])
app.add_routes([web.post('/echo', echo)])
app.add_routes([web.get('/echo/', echo)])
app.add_routes([web.get('/echo', echo)])
app.add_routes([web.get('/', hello)])
web.run_app(app, port=8083)
