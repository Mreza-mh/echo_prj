<?php

namespace App\Console\Commands;

use App\Services\RabbitMQService;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\Log;

class RabbitConsume extends Command
{
    protected $signature = 'rabbitmq:consume
                            {queue? : Queue name (defaults to my_queue)}
                            {--poll : Poll one message at a time instead of blocking consume}';

    protected $description = 'Consume messages from a RabbitMQ queue';

    public function handle(RabbitMQService $rabbitMQ): int
    {
        $queue = $this->argument('queue') ?? config('rabbitmq.queues.default', 'my_queue');

        $this->info("Listening on queue: {$queue}");

        if ($this->option('poll')) {
            return $this->poll($rabbitMQ, $queue);
        }

        try {
            $rabbitMQ->consume($queue, function (string $body) use ($queue): void {
                $this->processMessage($queue, $body);
            });
        } catch (\Throwable $e) {
            $this->error('Consumer stopped: '.$e->getMessage());
            Log::error('RabbitMQ consumer error', [
                'queue' => $queue,
                'error' => $e->getMessage(),
            ]);

            return self::FAILURE;
        }

        return self::SUCCESS;
    }

    private function poll(RabbitMQService $rabbitMQ, string $queue): int
    {
        while (true) {
            $message = $rabbitMQ->pull($queue);

            if ($message !== null) {
                $this->processMessage($queue, $message['payload']);
            }

            sleep(1);
        }
    }

    private function processMessage(string $queue, string $body): void
    {
        $this->info("[{$queue}] Received: {$body}");
        Log::info('RabbitMQ message received', [
            'queue' => $queue,
            'body' => $body,
        ]);
    }
}
