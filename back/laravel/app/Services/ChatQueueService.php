<?php

namespace App\Services;

use Illuminate\Support\Facades\Log;

class ChatQueueService
{
    public function __construct(private RabbitMQService $rabbitMQ) {}

    public function dispatch(array $messages, ?array $currentSlots = null, ?int $userId = null): void
    {
        try {
            $lastMessage = end($messages) ?: null;

            $this->rabbitMQ->publish(
                config('rabbitmq.queues.ai_chat') ?: 'ai_chat',
                [
                    'type' => 'chat_message',
                    'user_id' => $userId,
                    'last_message' => $lastMessage,
                    'messages_count' => count($messages),
                    'current_slots' => $currentSlots,
                    'queued_at' => now()->toIso8601String(),
                ]
            );
        } catch (\Throwable $e) {
            Log::warning('Failed to queue chat message', [
                'error' => $e->getMessage(),
                'user_id' => $userId,
            ]);
        }
    }
}
