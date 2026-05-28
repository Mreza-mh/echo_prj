<?php

namespace App\Providers;

use Illuminate\Foundation\Support\Providers\AuthServiceProvider as ServiceProvider;
use Laravel\Passport\Passport;

class AuthServiceProvider extends ServiceProvider
{


    /**
     * Register services.
     */
    public function register(): void
    {
        //
    }

    /**
     * Bootstrap services.
     */
    public function boot(): void
    {
        Passport::tokensCan([
            'user' => 'User scope',
            'admin' => 'Admin scope',
            'super_admin' => 'Super admin scope',
            'doctor' => 'Doctor scope',
            'nurse' => 'Nurse scope',
            'operator' => 'Operator scope',
            'monshi' => 'Monshi scope',
        ]);
    }

}
