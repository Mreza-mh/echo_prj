<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use App\Models\Resource;

class ResourceSeeder extends Seeder
{
    public function run(): void
    {
        $resources = [
            [
                'resource_name' => 'اتاق معاینه ۱',
                'resource_type' => 'room',
            ],
            [
                'resource_name' => 'اتاق معاینه ۲',
                'resource_type' => 'room',
            ],
            [
                'resource_name' => 'اتاق تزریقات',
                'resource_type' => 'room',
            ],
            [
                'resource_name' => 'سونوگرافی',
                'resource_type' => 'device',
            ],
            [
                'resource_name' => 'نوار قلب',
                'resource_type' => 'device',
            ],
            [
                'resource_name' => 'سیت‌اسکن',
                'resource_type' => 'device',
            ],
        ];

        foreach ($resources as $data) {
            Resource::updateOrCreate(
                ['resource_name' => $data['resource_name']], // جلوگیری از تکراری شدن
                [
                    'resource_type' => $data['resource_type'],
                ]
            );
        }

        echo "ResourceSeeder executed successfully.\n";
    }
}
