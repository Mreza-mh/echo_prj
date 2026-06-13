<?php

namespace App\Providers;

use App\Services\ChatQueueService;
use App\Services\RabbitMQService;
use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    /**
     * Register any application services.
     */
    public function register(): void
    {
        $this->app->singleton(RabbitMQService::class);
        $this->app->singleton(ChatQueueService::class);
    }

    /**
     * Bootstrap any application services.
     */
    public function boot(): void
    {
        //
    }
}
