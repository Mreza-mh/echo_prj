<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use App\Models\Service;

class ServiceSeeder extends Seeder
{
    public function run(): void
    {
        $services = [
            [
                'title'    => 'ویزیت عمومی',
                'duration' => '00:20:00',
                'price'    => 150000,
            ],
            [
                'title'    => 'ویزیت متخصص',
                'duration' => '00:30:00',
                'price'    => 250000,
            ],
            [
                'title'    => 'تزریق',
                'duration' => '00:10:00',
                'price'    => 50000,
            ],
            [
                'title'    => 'نمونه گیری آزمایشگاه',
                'duration' => '00:25:00',
                'price'    => 120000,
            ],
            [
                'title'    => 'مشاوره روانشناسی',
                'duration' => '00:45:00',
                'price'    => 300000,
            ],
            [
                'title'    => 'فیزیوتراپی',
                'duration' => '01:00:00',
                'price'    => 350000,
            ]
        ];

        foreach ($services as $data) {
            Service::updateOrCreate(
                ['title' => $data['title']],
                [
                    'duration' => $data['duration'],
                    'price'    => $data['price'],
                ]
            );
        }

        echo "ServiceSeeder executed successfully.\n";
    }
}
