import os
from kafka import KafkaConsumer
from kafka import KafkaProducer
from kafka.errors import KafkaError


BOOTSTRAP = os.getenv(
    'BOOTSTRAP',
    'my-cluster-kafka-bootstrap.knative-eventing:9092'
)
INPUT_TOPIC = os.getenv(
    'INPUT_TOPIC',
    'knative-broker-knative-eventing-front-broker'
)
OUTPUT_TOPIC = os.getenv('OUTPUT_TOPIC', 'my_topic')


consumer = KafkaConsumer(INPUT_TOPIC, bootstrap_servers=[BOOTSTRAP])
producer = KafkaProducer(bootstrap_servers=[BOOTSTRAP])


for message in consumer:
    print("Received %s:%d:%d: headers=%s value=%s" % (
        message.topic, message.partition, message.offset,
        message.headers, message.value
    ))
    producer.send(OUTPUT_TOPIC, value=message.value, headers=message.headers)
    producer.flush()
    print(f'Passed message to {OUTPUT_TOPIC}')
