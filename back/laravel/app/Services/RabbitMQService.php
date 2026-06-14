<?php

namespace App\Services;

use PhpAmqpLib\Channel\AMQPChannel;
use PhpAmqpLib\Connection\AMQPStreamConnection;
use PhpAmqpLib\Message\AMQPMessage;

class RabbitMQService
{
    private ?AMQPStreamConnection $connection = null;

    private ?AMQPChannel $channel = null;

    public function publish(string $queue, mixed $message, bool $durable = true): void
    {
        $channel = $this->channel();
        $this->declareQueue($channel, $queue, $durable);

        $body = is_string($message) ? $message : json_encode($message, JSON_UNESCAPED_UNICODE);

        $channel->basic_publish(
            new AMQPMessage($body, [
                'delivery_mode' => AMQPMessage::DELIVERY_MODE_PERSISTENT,
                'content_type' => 'application/json',
            ]),
            '',
            $queue
        );
    }

    /**
     * @param  callable(string $body, AMQPMessage $message): void  $callback
     */
    public function consume(string $queue, callable $callback, bool $durable = true): void
    {
        $channel = $this->channel();
        $this->declareQueue($channel, $queue, $durable);

        $channel->basic_qos(0, 1, false);

        $channel->basic_consume(
            $queue,
            '',
            false,
            false,
            false,
            false,
            function (AMQPMessage $message) use ($callback): void {
                try {
                    $callback($message->getBody(), $message);
                    $message->ack();
                } catch (\Throwable $e) {
                    $message->nack(false, true);
                    throw $e;
                }
            }
        );

        while ($channel->is_consuming()) {
            $channel->wait();
        }
    }

    public function pull(string $queue, bool $durable = true): ?array
    {
        $channel = $this->channel();
        $this->declareQueue($channel, $queue, $durable);

        $message = $channel->basic_get($queue);

        if ($message === null) {
            return null;
        }

        $payload = $message->getBody();
        $message->ack();

        $decoded = json_decode($payload, true);

        return [
            'payload' => is_array($decoded) ? json_encode($decoded, JSON_UNESCAPED_UNICODE) : $payload,
            'data' => $decoded ?? $payload,
        ];
    }

    public function disconnect(): void
    {
        if ($this->channel !== null) {
            $this->channel->close();
            $this->channel = null;
        }

        if ($this->connection !== null) {
            $this->connection->close();
            $this->connection = null;
        }
    }

    public function __destruct()
    {
        $this->disconnect();
    }

    private function channel(): AMQPChannel
    {
        if ($this->channel !== null && $this->channel->is_open()) {
            return $this->channel;
        }

        $config = config('rabbitmq');

        $this->connection = new AMQPStreamConnection(
            $config['host'],
            $config['port'],
            $config['user'],
            $config['password'],
            $config['vhost']
        );

        $this->channel = $this->connection->channel();

        return $this->channel;
    }

    private function declareQueue(AMQPChannel $channel, string $queue, bool $durable): void
    {
        $channel->queue_declare(
            $queue,
            false,
            $durable,
            false,
            false
        );
    }
}
