
# Setup kn-PoC-v0.1 from scratch

Prereqs: Linux machine with python3.10, GCP cloud account with ability to create small cluster.
Checkout this repo to local machine.
Export path where it got checked out as `KN_POC_HOME` env var:

```
export KN_POC_HOME='/home/jane/Documents/airflow'
```

Ensure this env var and env vars created further will be available throughout your local env (in all terminal tabs).

## Part one: GKE cluster setup

### Create GKE cluster

Create GCP project.
Create GKE cluster - one zone, at least 3 nodes. 2 vCPU, 8Gb mem, disk type standard or SSD 100Gb is fine. This is all for one node. Can do one node (or more) of type c2-standard-8.

### Bucket and transfer jobs

Create Google storage bucket in the GCP project that was just created. Save it's name.
Add 2 directories in the bucket: *words-list* and *results*. Alt, create 2 buckets and put directory *words-list* in one and *results* into another.
Create 2 [Google storage transfer jobs](https://cloud.google.com/storage-transfer/docs/create-transfers):
- from local directory `${KN_POC_HOME}/textfiles` to GS bucket/words-list
- from GS bucket/results to local directory `${KN_POC_HOME}/results`

Create service account that has permissions to run transfer jobs (role Storage Transfer User), and that can edit/create files in the buckets (role Storage Object User). Generate keys for the service account. Save them to local files in this repo:

- `dags/gcp-creds.json`
- `webapps/count-en/gcp-creds.json`

### Kafka and knative

Follow https://strimzi.io/quickstarts/ to install kafka in knative-eventing namespace, and use gke-yamls/kafka-cluster.yaml as kafka cluster resource instead of the one used in quickstart (kafka-single-persistent.yaml).
Follow https://knative.dev/docs/install/yaml-install/eventing/install-eventing-with-yaml/#install-knative-eventing to install knative eventing, install all kafka conponents too: kafka sink, kafka broker, kafka event source. kafka-source-dispatcher will have 0 pods until some kafka sources are created.


### Create broker

Create broker - *gke-yamls/broker.yaml*, and broker external LB - *gke-yamls/broker-ext-lb.yaml*

### Deploy count-en apps to GKE

Build docker image for webapps/count-en. Setup Google artifact registry for the current GCP project and publish image there:

```
> airflow/webapps$ docker build -t count-en ./count-en
> airflow/webapps$ docker tag count-en <cluster>.pkg.dev/<project-id>/<...>/count-en:latest
> airflow/webapps$ docker push <cluster>.pkg.dev/<project-id>/<...>/count-en:latest
```

Deploy 2 apps to GKE cluster which was previously created.

Deploy app (faking version 1.0.0) - can use Google Cloud console UI (GKE -> Workloads -> Deploy btn):
- pick uploaded image count-en from Google artifact registry
- add env vars:

```
KN_POC_BUCKET_WORDSLIST = "river-sand"  # name of bucket with incoming transfer job
KN_POC_BUCKET_RESULTS = "river-sand" # name of bucket with outgoing transfer job
```

`KN_POC_BUCKET_RESULTS` and `KN_POC_BUCKET_WORDSLIST` are same bucket in this PoC. You can also update `webapps/count-en/Dockerfile` and put these env vars in it.

- app name *count-en*, namespace knative-eventing
- enable service, type ClusterIP, map port 80 to 8083 container port

Deploy app (faking version 2.0.0):
- pick uploaded image count-en from Google artifact registry
- add env vars:

```
KN_POC_BUCKET_WORDSLIST = "river-sand"  # name of bucket with incoming transfer job
KN_POC_BUCKET_RESULTS = "river-sand" # name of bucket with outgoing transfer job
```

- app name *count-en-v2*, namespace knative-eventing
- enable service, type ClusterIP, map port 80 to 8083 container port

Scale apps to 1 replica instead of 3.
Wait for workloads and services to become available.

### Create knative triggers

Create triggers - *gke-yamls/triggers.yaml*

### Test: send event to broker and check count-en app logs something

Navigate to GKE services, pick broker-external, get the public IP.
Send event, from any terminal with internet access:

```
wget -O - -S --post-data '{"msg":"Hello from outside!"}' --header "Content-Type: application/json" --header "Ce-Id: 123131455" --header "Ce-Specversion: 1.0" --header "Ce-Type: count-en" --header "Ce-appversion: 1.0.0" --header "Ce-Source: command-line" http://<publicIP>:80/knative-eventing/count-en-broker
```

With this example event data `count-en` should just log record `{"msg":"Hello from outside!"}`. Change `"Ce-appversion: 1.0.0"` to `"Ce-appversion: 2.0.0"` and check `count-en-v2` logs too.


## Part two: local setup

Prereqs: machine with python (py3.10 was used, py3.9+ should be fine)

### Airflow

[Install Airflow](https://airflow.apache.org/).
Update `airflow.cfg` to allow [basic auth](https://airflow.apache.org/docs/apache-airflow/stable/security/api.html#basic-authentication). Add user and password to basic auth section.
Add directory `${KN_POC_HOME}/dags` to the list of paths airflow fetches DAGs from.

Setup following env vars:

```
export KN_POC_AIRFLOW_API="http://localhost:8080/api/v1"  # API web endpoint of Airflow
export KN_POC_AIRFLOW_USER='jane'  # airflow user from basic auth config in airflow.cfg
export KN_POC_AIRFLOW_PASSWORD='jane'  # airflow password from basic auth config in airflow.cfg
```

Launch `airflow standalone`.

### Input web app

In another terminal window (ensure env vars defined before are available in this window), launch input web app:

```
pip install aiohttp
python webapps/input.py
```

### Router web app and nginx endpoint

Launch nginx endpoint at localhost:7777, but make sure it doesn't reply 20X on /call-test-event/?path=... . Or can just skip this and not launch nginx endpoint.

Create env var with the public IP of external load balancer for count-en broker:

```
export KN_POC_BROKER_LB="34.12....:80"
```

Launch router:

```
pip install aiohttp
python webapps/router.py
```


## Part three: run it all


We launch DAG by sending HTTP request to input web app:

```
curl --request POST -H "Content-Type: application/json" --data '{"filepath": "${KN_POC_HOME}/inputfiles/lorem2.txt", "email": "email@myemail.com", "appversion": "1.0.0"}' http://localhost:8085/run/count_en_words
```

and check see processing happening in Airflow UI (localhost:8080).

For input file, can use the ones in `${KN_POC_HOME}/inputfiles` or provide path to your own text file.


# TODO:

+ count-en: do really count EN words, instead of filtering out words from hardcoded list with 60 latin words.
+ jaegger/prometeus for knative


## Part four: Airflow in the cloud

In the GKE cluster created before, scale nodes up to 5. Create namespace `airflow`. Apply `gke-yamls/storageclass-airflow.yaml` and make sure [DefaultStorageClass](https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/#defaultstorageclass) admission controller is enabled (it is enabled by default).

Install [airflow using helm](https://airflow.apache.org/docs/helm-chart/stable/index.html):

```
helm upgrade --install airflow apache-airflow/airflow --namespace airflow --set executor=KubernetesExecutor
```

