<?php

namespace App\Services;

class RabbitMQService
{
    private $host;
    private $port;
    private $user;
    private $password;
    private $vhost;

    public function __construct()
    {
        $this->host = env('RABBITMQ_HOST', 'localhost');
        $this->port = env('RABBITMQ_PORT', 5672);
        $this->user = env('RABBITMQ_USER', 'guest');
        $this->password = env('RABBITMQ_PASSWORD', 'guest');
        $this->vhost = urlencode(env('RABBITMQ_VHOST', '/'));
    }

    private function connect()
    {
        $url = "http://{$this->host}:15672/api";

        return [$url, $this->user, $this->password];
    }

    public function publish($queue, $message)
    {
        [$url, $user, $pass] = $this->connect();

        $payload = [
            'properties' => [],
            'routing_key' => $queue,
            'payload' => is_string($message) ? $message : json_encode($message),
            'payload_encoding' => 'string'
        ];

        $ch = curl_init("$url/exchanges/%2F/amq.default/publish");
        curl_setopt($ch, CURLOPT_USERPWD, "$user:$pass");
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload));
        curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

        $result = curl_exec($ch);
        $err = curl_error($ch);

        curl_close($ch);

        if ($err) {
            throw new \Exception("RabbitMQ publish error: $err");
        }

        return json_decode($result, true);
    }

    public function consume($queue)
    {
        [$url, $user, $pass] = $this->connect();

        $ch = curl_init("$url/queues/%2F/$queue/get");
        curl_setopt($ch, CURLOPT_USERPWD, "$user:$pass");
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode([
            'count' => 1,
            'requeue' => false,
            'encoding' => 'auto'
        ]));
        curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

        $result = curl_exec($ch);
        $err = curl_error($ch);

        curl_close($ch);

        if ($err) {
            throw new \Exception("RabbitMQ consume error: $err");
        }

        return json_decode($result, true);
    }
}
