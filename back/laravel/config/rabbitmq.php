<?php

return [

    'host' => env('RABBITMQ_HOST', 'localhost'),
    'port' => (int) env('RABBITMQ_PORT', 5672),
    'user' => env('RABBITMQ_USER', 'guest'),
    'password' => env('RABBITMQ_PASSWORD', 'guest'),
    'vhost' => env('RABBITMQ_VHOST', '/'),

    'queues' => [
        'video_processing' => env('RABBITMQ_QUEUE_VIDEO', 'video_processing'),
        'email_sending' => env('RABBITMQ_QUEUE_EMAIL', 'email_sending'),
        'report_generation' => env('RABBITMQ_QUEUE_REPORT', 'report_generation'),
        'ai_chat' => env('RABBITMQ_QUEUE_CHAT', 'ai_chat'),
        'default' => env('RABBITMQ_QUEUE_DEFAULT', 'my_queue'),
    ],

];
