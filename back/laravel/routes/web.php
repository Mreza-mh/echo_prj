<?php

use Illuminate\Support\Facades\Route;

Route::get('/', function () {
    return view('welcome');
});


use App\Services\RabbitMQService;

Route::get('/send', function () {
    $mq = new RabbitMQService();
    $mq->publish('my_queue', ['msg' => 'hello from laravel 12']);

    return 'Message sent!';
});

