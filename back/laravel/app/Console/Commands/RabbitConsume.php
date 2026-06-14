<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use App\Services\RabbitMQService;

class RabbitConsume extends Command
{
    protected $signature = 'rabbitmq:consume {queue=my_queue}';
    protected $description = 'Consume messages from RabbitMQ queue';

    public function handle()
    {
        $mq = new RabbitMQService();

        $this->info('Listening...');

        while (true) {
            $messages = $mq->consume($this->argument('queue'));

            if (!empty($messages)) {
                foreach ($messages as $msg) {
                    $this->info('Received: ' . $msg['payload']);
                }
            }

            sleep(1);
        }
    }
}
