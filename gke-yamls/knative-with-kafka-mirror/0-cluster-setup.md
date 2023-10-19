Create new cluster. 

Create namespace knative-eventing.

Follow https://strimzi.io/quickstarts/ to install kafka in knative-eventing namespace, and use gke-yamls/kafka-cluster.yaml as kafka cluster resource instead of the one used in quickstart (kafka-single-persistent.yaml).
Follow https://knative.dev/docs/install/yaml-install/eventing/install-eventing-with-yaml/#install-knative-eventing to install knative eventing, install all kafka conponents too: kafka sink, kafka broker, kafka event source. 
Use https://knative.dev/blog/articles/single-node-kafka-development/#setting-the-kafka-broker-class-as-default to configure broker config to be Kafka broker class (replication: 1).

Also install https://knative.dev/docs/eventing/sources/kafka-source/. kafka-source-dispatcher will have 0 pods until some kafka sources are created.