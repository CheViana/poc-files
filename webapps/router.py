from aiohttp import web, ClientSession, BasicAuth
import datetime
import secrets
import string

app = web.Application()

cluster_ingresses = [
    "localhost:7777",
    "34.41.248.142:80"
]

async def on_startup(app):
    app["ingress_session"] = {}
    for ingress in cluster_ingresses:
        app["ingress_session"][ingress] = ClientSession()
    app["urls_cache"] = {}
    app["trabsfer_job_store"] = [
        {
            "ingress": "34.41.248.142:80",
            "path": "knative-eventing%2Fcount-en-broker",
            "job_name": "transferJobs/OPI8437548298833795632",
            "project_id" :"charged-scholar-399420",
        }
    ]


async def on_shutdown(app):
    try:
        session = app['airflow_session']
        await session.close()
    except KeyError:
        pass


app.on_shutdown.append(on_shutdown)
app.on_startup.append(on_startup)


async def hello(request):
    return web.Response(text="Hello, world")


def get_random_str():
    return ''.join(
        secrets.choice(string.ascii_lowercase + string.digits) for i in range(8)
    )


async def call_test_event(request):
    path = request.query['path']
    test_event = {"Hello": "Broker"}
    test_headers = {
        'Content-Type': 'application/json',
        "Ce-Id": f"event_{get_random_str()}",
        "Ce-Specversion": "1.0",
        "Ce-Type": "count-en",
        "Ce-Source": "local-dag-count-en-words",
    }
    resolved_ingress = None

    url_to_call = None
    if path in app["urls_cache"]:
        url_to_call = app["urls_cache"][path]["url"]
        ingress = app["urls_cache"][path]["ingress"]
        async with app['ingress_session'][ingress].post(
            url_to_call,
            json=test_event,
            headers=test_headers,
        ) as resp:
            status = resp.status
            if status != 202:
                print(f"Ingress {ingress} has no path {path}, clean cache")
                del app["urls_cache"][path]
            else:
                resolved_ingress = ingress
    
    if not resolved_ingress:
        for ingress in cluster_ingresses:
            url_to_check = f"http://{ingress}/{path}"

            try:
                async with app['ingress_session'][ingress].post(
                    url_to_check,
                    json=test_event,
                    headers=test_headers,
                ) as resp:
                    status = resp.status
                    response_text = await resp.text()
                    if status != 202:
                        print(f"Ingress {ingress} has no path {path}: status {status}, response {response_text}")
                        continue
                    app["urls_cache"][path] = {"url": url_to_check, "ingress": ingress}
                    print(f"Ingress {ingress} is a match for path {path}")
                    resolved_ingress = ingress
                    break
            except Exception as ex:
                print(f"Ingress {ingress} got error for path {path}: ex {ex}")
                continue
    
    for job_data in app["trabsfer_job_store"]:
        if job_data["ingress"] == resolved_ingress:
            return web.json_response(data={
                "job_name": job_data["job_name"],
                "project_id": job_data["project_id"],
                "ingress": resolved_ingress
            })

    return web.Response(text=f"Cant find broker or transfer job for {path}", status=200)


async def call(request):
    path = request.query['path']
    data = await request.json()
    incom_headers = request.headers
    print(f"Received {data}, headers {incom_headers}")

    # process headers
    ce_headers = {k: v for k, v in incom_headers.items() if (
        k.lower().startswith('ce-') or k.lower() == 'Content-Type'
    )}

    url_to_call = None
    if path in app["urls_cache"]:
        url_to_call = app["urls_cache"][path]["url"]
        ingress = app["urls_cache"][path]["ingress"]
        async with app['ingress_session'][ingress].post(
            url_to_call,
            json=data,
            headers=ce_headers,
        ) as resp:
            status = resp.status
            if status != 202:
                print(f"Ingress {ingress} has no path {path}, clean cache")
                del app["urls_cache"][path]
            else:
                response_text = await resp.text()
                return web.Response(text=f"Accepted, status {status}, response {response_text}", status=202)

    for ingress in cluster_ingresses:
        url_to_check = f"http://{ingress}/{path}"

        try:
            async with app['ingress_session'][ingress].post(
                url_to_check,
                json=data,
                headers=ce_headers,
            ) as resp:
                status = resp.status
                response_text = await resp.text()
                if status != 202:
                    print(f"Ingress {ingress} has no path {path}: status {status}, response {response_text}")
                    continue
                app["urls_cache"][path] = {"url": url_to_check, "ingress": ingress}
                print(f"Ingress {ingress} is a match for path {path}")
        except Exception as ex:
            print(f"Ingress {ingress} got error for path {path}: ex {ex}")
            continue

    return web.Response(text=f"Accepted, status {status}, response {response_text}", status=202)


app.add_routes([web.post('/call', call)])
app.add_routes([web.post('/call/', call)])
app.add_routes([web.post('/call-test-event', call_test_event)])
app.add_routes([web.post('/call-test-event/', call_test_event)])
app.add_routes([web.get('/', hello)])
web.run_app(app, port=8084)
