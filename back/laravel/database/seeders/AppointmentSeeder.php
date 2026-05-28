<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use App\Models\Staff;
use App\Models\Service;
use App\Models\Resource;
use App\Models\Appointment;
use Carbon\Carbon;

class AppointmentSeeder extends Seeder
{
    public function run(): void
    {
        $staffs    = Staff::all();
        $services  = Service::all()->keyBy('id');
        $resources = Resource::all()->keyBy('resource_name');

        $patientIds = range(6, 1005);

        // جلوگیری از تداخل منابع
        $resourceLocks = [];

        // جلوگیری از دریافت همزمان چند نوبت توسط یک بیمار
        $userLocks = [];

        // Mapping سرویس → ریسورس
        $serviceResourceMap = [
            1 => ['اتاق معاینه ۱', 'اتاق معاینه ۲'],
            2 => ['اتاق معاینه ۱', 'اتاق معاینه ۲'],
            3 => ['اتاق تزریقات'],
            4 => ['اتاق تزریقات'],
            5 => ['اتاق معاینه ۲'],
            6 => ['اتاق معاینه ۱', 'اتاق معاینه ۲'],
        ];

        // از 3 روز قبل تا 7 روز بعد
        for ($i = -3; $i <= 7; $i++) {

            $date = Carbon::now()->addDays($i);
            $dayName = strtolower($date->format('l'));

            foreach ($staffs as $staff) {

                $schedule = collect($staff->schedule)->firstWhere('day', $dayName);
                if (!$schedule) continue;

                foreach ($schedule['slots'] as $slot) {

                    $slotStart = Carbon::parse($date->format('Y-m-d') . ' ' . $slot['start']);
                    $slotEnd   = Carbon::parse($date->format('Y-m-d') . ' ' . $slot['end']);

                    $current = $slotStart->copy();

                    while ($current < $slotEnd) {

                        $service = $services->random();
                        $durationObj = Carbon::parse($service->duration);

                        $appointmentEnd =
                            $current->copy()
                                ->addHours($durationObj->hour)
                                ->addMinutes($durationObj->minute)
                                ->addSeconds($durationObj->second);

                        if ($appointmentEnd > $slotEnd) break;

                        $resourceNames = $serviceResourceMap[$service->id];

                        $candidateResources = collect($resourceNames)->map(function ($name) use ($resources) {
                            return $resources[$name];
                        });

                        // انتخاب ریسورس آزاد
                        $resource = $candidateResources->first(function ($r) use ($current, $resourceLocks) {
                            return !isset($resourceLocks[$r->id]) ||
                                $current >= $resourceLocks[$r->id];
                        });

                        if (!$resource) break;

                        // انتخاب بیمار آزاد (بدون تداخل زمانی)
                        $userId = collect($patientIds)->first(function ($pid) use ($current, $userLocks) {
                            return !isset($userLocks[$pid]) || $current >= $userLocks[$pid];
                        });

                        // اگر همه بیماران در آن زمان مشغول بودند → نوبت ساخته نشود
                        if (!$userId) break;

                        // ساخت نوبت
                        $appointment = Appointment::create([
                            'user_id'     => $userId,
                            'staff_id'    => $staff->id,
                            'service_id'  => $service->id,
                            'date_of_turn' => $current->format('Y-m-d'),
                            'start_time'  => $current->format('Y-m-d H:i:s'),
                            'end_time'    => $appointmentEnd->format('Y-m-d H:i:s'),
                            'status_id'   => 1,
                            'reservation_type'         => 'Online',
                            'permissible_interference' => 0,
                        ]);

                        // اتصال resource
                        $appointment->resources()->attach($resource->id);

                        // قفل ریسورس
                        $resourceLocks[$resource->id] = $appointmentEnd->copy();

                        // قفل بیمار
                        $userLocks[$userId] = $appointmentEnd->copy();

                        // برو به نوبت بعدی
                        $current = $appointmentEnd->copy();
                    }
                }
            }
        }
    }
}
