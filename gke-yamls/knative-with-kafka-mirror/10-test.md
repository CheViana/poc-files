Launch listener for reply-topic:

```
kubectl -n knative-eventing run kafka-consumer2 -ti --image=quay.io/strimzi/kafka:0.37.0-kafka-3.5.1 --rm=true --restart=Never -- bin/kafka-console-consumer.sh --bootstrap-server my-cluster-kafka-bootstrap:9092 --topic reply-topic --from-beginning --property print.headers=true
```

In pther tab, launch client for input-topic:

```
kubectl -n knative-eventing run kafka-producer -ti --image=quay.io/strimzi/kafka:0.37.0-kafka-3.5.1 --rm=true --restart=Never -- bin/kafka-console-producer.sh --bootstrap-server my-cluster-kafka-bootstrap:9092 --topic input-topic --property parse.headers=true  --property headers.delimiter=\t --property headers.separator=, --property headers.key.separator=:
```

And post following payload to input-topic:

```
Ce-Id:777783,Ce-Specversion:1,Ce-Type:call,Ce-replykey:123129,Ce-Source:kafkaprodsh\t{"msg":"with resp9"}
```

The message should arrive to reply-topic with matching reply key:

```
ce_specversion:1.0,ce_id:reply-123129-ljuz90i7,ce_source:wonderland-responder,ce_type:reply,content-type:application/json; charset=utf-8,ce_callbackkey:123129  {"status": "wonder received", "key": "123129"}
```