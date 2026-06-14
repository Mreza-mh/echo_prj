<?php

return [

    /*
    |--------------------------------------------------------------------------
    | Third Party Services
    |--------------------------------------------------------------------------
    |
    | This file is for storing the credentials for third party services such
    | as Mailgun, Postmark, AWS and more. This file provides the de facto
    | location for this type of information, allowing packages to have
    | a conventional file to locate the various service credentials.
    |
    */

    'postmark' => [
        'key' => env('POSTMARK_API_KEY'),
    ],

    'resend' => [
        'key' => env('RESEND_API_KEY'),
    ],

    'ses' => [
        'key' => env('AWS_ACCESS_KEY_ID'),
        'secret' => env('AWS_SECRET_ACCESS_KEY'),
        'region' => env('AWS_DEFAULT_REGION', 'us-east-1'),
    ],

    'slack' => [
        'notifications' => [
            'bot_user_oauth_token' => env('SLACK_BOT_USER_OAUTH_TOKEN'),
            'channel' => env('SLACK_BOT_USER_DEFAULT_CHANNEL'),
        ],
    ],

    // 'openrouter' => [
    //     'key' => env('OPENROUTER_KEY'),
    // ],

    'ai' => [
        'provider' => env('AI_PROVIDER', 'arvan'), // openrouter | arvan

        'openrouter' => [
            'key' => env('OPENROUTER_API_KEY'),
            'base_url' => 'https://openrouter.ai/api/v1/chat/completions',
            'models' => [
                'google/gemma-3-12b-it:free',
                'qwen/qwen-2.5-7b-instruct:free',
                'google/gemini-2.0-flash-lite-preview-02-05:free',
            ],
        ],

        'arvan' => [
            'key' => env('ARVAN_AI_KEY'),
            'base_url' => env('ARVAN_AI_BASE_URL'),
            'model' => env('ARVAN_AI_MODEL', 'Gemma-4-31B-IT-h7ojx'),
            'timeout' => (int) env('ARVAN_AI_TIMEOUT', 90),
            'connect_timeout' => (int) env('ARVAN_AI_CONNECT_TIMEOUT', 15),
        ],

        'timeout' => (int) env('AI_HTTP_TIMEOUT', 60),
        'connect_timeout' => (int) env('AI_HTTP_CONNECT_TIMEOUT', 10),

    ],

];
