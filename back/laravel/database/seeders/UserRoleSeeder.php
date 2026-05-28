<?php

namespace Database\Seeders;

use App\Enums\UserRole;
use App\Models\User;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Hash;

class UserRoleSeeder extends Seeder
{
    public function run(): void
    {
        $password = '123456'; // رمز پیش‌فرض
        $commonData = [
            'password' => Hash::make($password),
            'email_verified_at' => now(),
            'is_verify' => true,
        ];

        $users = [
            UserRole::admin->value => [
                'name' => 'ادمین سیستم',
                'email' => 'admin@example.com',
            ],
            UserRole::doctor->value => [
                'name' => 'دکتر نمونه',
                'email' => 'doctor@example.com',
            ],
            UserRole::nurse->value => [
                'name' => 'پرستار نمونه',
                'email' => 'nurse@example.com',
            ],
            UserRole::operator->value => [
                'name' => 'اپراتور نمونه',
                'email' => 'operator@example.com',
            ],
            UserRole::monshi->value => [
                'name' => 'منشی نمونه',
                'email' => 'monshi@example.com',
            ],
            UserRole::user->value => [
                'name' => 'مشتری نمونه',
                'email' => 'user@example.com',
            ],
        ];

        foreach ($users as $role => $data) {
            User::updateOrCreate(
                ['email' => strtolower($data['email'])],
                array_merge($commonData, [
                    'name' => $data['name'],
                    'role' => $role,
                ])
            );
        }

        echo "UserRoleSeeder executed.\n";
    }
}
