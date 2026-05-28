<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use App\Models\Staff;
use App\Models\User;

class StaffSeeder extends Seeder
{
    public function run(): void
    {
        // کارمندان فرضی: دکتر، پرستار، اپراتور، منشی
        $employees = [
            [
                'user_id'    => 2,
                'expertise_id' => 1, // General Doctor
                'schedule'   => self::doctorSchedule(),
            ],
            [
                'user_id'    => 3,
                'expertise_id' => 2, // Nurse
                'schedule'   => self::nurseSchedule(),
            ],
            [
                'user_id'    => 4,
                'expertise_id' => 3, // Operator
                'schedule'   => self::operatorSchedule(),
            ],
            [
                'user_id'    => 5,
                'expertise_id' => 4, // Receptionist
                'schedule'   => self::receptionistSchedule(),
            ],
        ];

        foreach ($employees as $emp) {
            Staff::updateOrCreate(
                ['user_id' => $emp['user_id']],
                [
                    'expertise_id' => $emp['expertise_id'],
                    'schedule'     => $emp['schedule'],
                ]
            );
        }
    }


    // ------------------------------
    // SCHEDULES
    // ------------------------------

    private static function doctorSchedule()
    {
        return [
            [
                'day' => 'saturday',
                'slots' => [
                    ['start' => '08:00', 'end' => '12:00'],
                    ['start' => '16:00', 'end' => '20:00'],
                ]
            ],
            [
                'day' => 'sunday',
                'slots' => [
                    ['start' => '09:00', 'end' => '13:00'],
                    ['start' => '17:00', 'end' => '21:00'],
                ]
            ],
            [
                'day' => 'monday',
                'slots' => [
                    ['start' => '08:30', 'end' => '12:30'],
                    ['start' => '15:00', 'end' => '19:00'],
                ]
            ],
            [
                'day' => 'tuesday',
                'slots' => [
                    ['start' => '10:00', 'end' => '14:00'],
                ]
            ],
            [
                'day' => 'wednesday',
                'slots' => [
                    ['start' => '08:00', 'end' => '12:00'],
                ]
            ]
        ];
    }


    private static function nurseSchedule()
    {
        return [
            [
                'day' => 'saturday',
                'slots' => [
                    ['start' => '08:00', 'end' => '16:00'],
                ]
            ],
            [
                'day' => 'sunday',
                'slots' => [
                    ['start' => '08:00', 'end' => '16:00'],
                ]
            ],
            [
                'day' => 'monday',
                'slots' => [
                    ['start' => '08:00', 'end' => '20:00'],
                ]
            ],
            [
                'day' => 'tuesday',
                'slots' => [
                    ['start' => '12:00', 'end' => '20:00'],
                ]
            ],
            [
                'day' => 'wednesday',
                'slots' => [
                    ['start' => '08:00', 'end' => '14:00'],
                ]
            ],
            [
                'day' => 'thursday',
                'slots' => [
                    ['start' => '09:00', 'end' => '13:00'],
                ]
            ]
        ];
    }


    private static function operatorSchedule()
    {
        return [
            [
                'day' => 'saturday',
                'slots' => [
                    ['start' => '09:00', 'end' => '17:00'],
                ]
            ],
            [
                'day' => 'sunday',
                'slots' => [
                    ['start' => '09:00', 'end' => '17:00'],
                ]
            ],
            [
                'day' => 'monday',
                'slots' => [
                    ['start' => '09:00', 'end' => '17:00'],
                ]
            ],
            [
                'day' => 'tuesday',
                'slots' => [
                    ['start' => '09:00', 'end' => '17:00'],
                ]
            ],
            [
                'day' => 'wednesday',
                'slots' => [
                    ['start' => '09:00', 'end' => '17:00'],
                ]
            ]
        ];
    }


    private static function receptionistSchedule()
    {
        return [
            [
                'day' => 'saturday',
                'slots' => [
                    ['start' => '08:00', 'end' => '18:00'],
                ]
            ],
            [
                'day' => 'sunday',
                'slots' => [
                    ['start' => '08:00', 'end' => '18:00'],
                ]
            ],
            [
                'day' => 'monday',
                'slots' => [
                    ['start' => '08:00', 'end' => '18:00'],
                ]
            ],
            [
                'day' => 'tuesday',
                'slots' => [
                    ['start' => '08:00', 'end' => '18:00'],
                ]
            ],
            [
                'day' => 'wednesday',
                'slots' => [
                    ['start' => '08:00', 'end' => '18:00'],
                ]
            ],
            [
                'day' => 'thursday',
                'slots' => [
                    ['start' => '08:00', 'end' => '14:00'],
                ]
            ]
        ];
    }
}
