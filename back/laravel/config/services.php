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
                'google/gemma-3-27b-it:free',
                'qwen/qwen-2.5-7b-instruct:free',
                'google/gemini-2.0-flash-lite-preview-02-05:free',
            ],
        ],

        'arvan' => [
            'key' => env('ARVAN_AI_KEY'),
            'base_url' => 'https://arvancloudai.ir/gateway/models/Gemma-4-31B-IT/g6T_fBj_XKgBXq_lSFElXCsc8IRpgk7wiPj_rmIXJJcI3-z5IL075ZR0i7GZWY8_0Egd3j18vOEncIn8WXVaSYNpDH-t5JtVuGCdVMSXGc_nXxRe-Ne_Mrn4QxARZmA8VT8I9qrGUWerBIF_MIQ-pS9YAKJjDwVF7LE_mn97t2fDhlnlGB33chkUkTU7AJ8L4TuIz40Zy88DEf9H20p8SR8Ag6mrrF6MhhGXPWgF2IqV36Qp2ZdMM7BdzUKrm8TEKlc/v1/chat/completions',
            'model' => 'Gemma-4-31B-IT-h7ojx',
        ],

    ],

];
