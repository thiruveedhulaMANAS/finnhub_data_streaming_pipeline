from pyspark.sql import SparkSession
from pyspark.sql.types import StructField, StructType, IntegerType, DoubleType, StringType, TimestampType,LongType
from pyspark.sql.functions import col, from_json, current_timestamp,udf,avg
import uuid

import os
import sys

os.environ['PYSPARK_PYTHON'] = sys.executable
os.environ['PYSPARK_DRIVER_PYTHON'] = sys.executable
# Create a SparkSession
spark = SparkSession \
    .builder \
    .appName("Kafka") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.2.0,com.datastax.spark:spark-cassandra-connector_2.12:3.1.0") \
    .config("spark.cassandra.connection.host", 'localhost') \
    .config('spark.cassandra.connection.port', '9042') \
    .config('spark.cassandra.output.consistency.level','ONE') \
    .getOrCreate()

# Set the log level to ERROR
spark.sparkContext.setLogLevel("ERROR")

# Read data from Kafka
df = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "finnhub") \
    .option("startingOffsets", "latest") \
    .load()

# Define the schema for the JSON data
finnhub_schema = StructType([
    StructField('p', DoubleType(), False),
    StructField('s', StringType(), False),
    StructField('c', StringType(), False),
    StructField('t', LongType(), False),
    StructField('v', DoubleType(), False)
])

# Define a User Defined Function (UDF) to generate UUIDs
def make_uuid():
    return udf(lambda: str(uuid.uuid1()), StringType())()

# Parse JSON data and perform transformations
parsed_df = df.selectExpr("CAST(value AS STRING)") \
    .select(from_json(col("value"), finnhub_schema).alias("data")) \
    .select("data.*")

update_df = parsed_df.withColumn("uuid", make_uuid()) \
    .withColumnRenamed("c", "trade_conditions") \
    .withColumnRenamed("p", "price") \
    .withColumnRenamed("s", "symbol") \
    .withColumnRenamed("t", "trade_timestamp") \
    .withColumnRenamed("v", "volume") \
    .withColumn("trade_timestamp", (col("trade_timestamp") / 1000).cast(TimestampType())) \
    .withColumn("ingest_timestamp", current_timestamp())

# Print the schema
#update_df.printSchema()

cassandra_keyspace = "market"
cassandra_table = "trades"
def writeToCassandra(writeDF, epochId):
    writeDF.write \
        .format("org.apache.spark.sql.cassandra") \
        .mode("append") \
        .options(table=cassandra_table, keyspace=cassandra_keyspace) \
        .save()
    print("inserting data into cassandra....")

# Apply the foreachBatch function to the transformed DataFrame
query = update_df.writeStream \
    .foreachBatch(writeToCassandra) \
    .outputMode("update") \
    .start()


summary_df = update_df.withColumn("price_volume_multiply",(col("price")*col("volume")))\
            .withWatermark("trade_timestamp","15 seconds")\
            .groupBy("symbol")\
            .agg(avg("price_volume_multiply").alias("price_volume_multiply"))

finalsummarydf = summary_df.withColumn("uuid",make_uuid())\
                    .withColumn("ingest_timestamp",current_timestamp())


# def running_averages(writeDF,epochid):
#     writeDF.write \
#         .format("org.apache.spark.sql.cassandra") \
#         .mode("append") \
#         .options(table="running_averages_15_sec", keyspace="finnhub") \
#         .save()

# query2 = finalsummarydf.writeStream \
#             .trigger(processingTime="5 seconds")\
#             .foreachBatch(running_averages)\
#             .outputMode("update")\
#             .start()

query2 =finalsummarydf.writeStream.trigger(processingTime="5 seconds") \
    .foreachBatch(
        lambda batchDF, batchID: batchDF.write.format("org.apache.spark.sql.cassandra") \
            .options(table="running_averages_15_sec", keyspace="market") \
            .mode("append").save()
            ).outputMode("update").start()
query.awaitTermination()
query2.awaitTermination()