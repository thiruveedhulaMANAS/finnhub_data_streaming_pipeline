# Finnhub_data_streaming_pipeline

The project is a streaming data pipeline based on the Finnhub.io API/websocket for real-time trade data and stream processing.
It is designed with a purpose to showcase key aspects of streaming pipeline development & architecture, providing low latency, scalability & availability.

## Architecture
![finnhub_streaming_data_pipeline_diagram](https://github.com/thiruveedhulaMANAS/finnhub_data_streaming_pipeline/blob/main/architecture.png)

The diagram above provides a detailed insight into pipeline's architecture.

**Data source**: We use the [Finnhub WebSocket API](https://finnhub.io/) to get real-time stock market data, allowing for real-time updates and analysis of stock prices, transactions, and other financial data for informed decision-making and market monitoring.

**Data ingestion layer**: A containerized Python programme called FinnhubProducer connects to the Finnhub.io websocket to collect data. It forwards messages to the Kafka broker.

**Message Broker**: The message broker (kafkaservice pod) gets messages from the finnhub_producer. To get Kafka up and running, we must first build a topic for Finnhub. To manage Kafka metadata, the zookeeper pod is launched before Kafka.

**Stream Processor**: A Spark instance is launched to consume and process data from the Kafka topic on Finnhub. The PySpark script spark/streamprocessor.py is sent to the Spark cluster manager, who assigns it a worker. This application connects to the Kafka broker to get messages, which are then transformed with Spark Structured Streaming and loaded into Cassandra tables.

**Processed Data Storage**: The processed data from the preceding Spark operation is stored and served using a Cassandra cluster. When Cassandra begins, we must first construct the keyspace market as well as tables for transactions and running averages. The market contains raw comment data.The trades table contains raw data, whereas the market.running_averages table has aggregated data.

**Data Visualisation**: Grafana connects to the Cassandra database for data visualisation. It searches Cassandra for aggregated data and displays it visually to users through a dashboard. For analysis, the dashboard displays the following panels:
  - `Price`: Showcase the real-time price of company stocks of all time.
![price_panel](https://github.com/thiruveedhulaMANAS/finnhub_data_streaming_pipeline/blob/main/output/price.png)
  - `Volume`: Showcase the real-time volume of company stocks of all time.
![price_panel](https://github.com/thiruveedhulaMANAS/finnhub_data_streaming_pipeline/blob/main/output/volume.png)
  - `average_price_multiply_volume`: Showcase the real-time average (price * volume) of company stocks of all time.
![price_panel](https://github.com/thiruveedhulaMANAS/finnhub_data_streaming_pipeline/blob/main/output/average_price_multiply_volume.png)
