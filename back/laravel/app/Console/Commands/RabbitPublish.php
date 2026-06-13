<?php

namespace App\Console\Commands;

use App\Services\RabbitMQService;
use Illuminate\Console\Command;

class RabbitPublish extends Command
{
    protected $signature = 'rabbitmq:publish
                            {queue=my_queue : Queue name}
                            {--message= : JSON or plain text message}';

    protected $description = 'Publish a test message to a RabbitMQ queue';

    public function handle(RabbitMQService $rabbitMQ): int
    {
        $queue = $this->argument('queue');
        $raw = $this->option('message') ?? json_encode([
            'msg' => 'hello from laravel',
            'timestamp' => now()->toIso8601String(),
        ], JSON_UNESCAPED_UNICODE);

        $decoded = json_decode($raw, true);
        $payload = json_last_error() === JSON_ERROR_NONE ? $decoded : $raw;

        $rabbitMQ->publish($queue, $payload);

        $this->info("Message published to queue: {$queue}");

        return self::SUCCESS;
    }
}
