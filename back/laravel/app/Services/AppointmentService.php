<?php

namespace App\Services;

use App\Exceptions\ErrorException;
use App\Http\Requests\Appointment\AppointmentCreateRequest;
use App\Http\Requests\Appointment\AvailableSlotsRequest;
use App\Models\Appointment;
use App\Models\AppointmentResource;
use App\Models\Service;
use App\Models\Staff;
use App\Models\Status;
use App\Models\Resource;
use Illuminate\Http\Request;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\DB;

class AppointmentService
{

    private const ACTIVE_APPOINTMENT_STATUSES = [
        'pending',
        'confirmed',
    ];


    /* --------------------------------------------------------------------------
       (1) GET STAFF WORKING HOURS → No StaffSchedule — Using staff->schedule JSON
    ---------------------------------------------------------------------------*/
    private function getStaffWorkingHours($staff_id, $date)
    {
        try {
            $staff = Staff::find($staff_id);

            if (!$staff || empty($staff->schedule)) {
                return [
                    Carbon::parse($date . ' 00:00'),
                    Carbon::parse($date . ' 23:59'),
                ];
            }

            $schedule = is_string($staff->schedule)
                ? json_decode($staff->schedule, true)
                : $staff->schedule;

            if (!is_array($schedule)) {
                return [
                    Carbon::parse($date . ' 00:00'),
                    Carbon::parse($date . ' 23:59'),
                ];
            }

            $days_map = [
                0 => 'sun', 1 => 'mon', 2 => 'tue',
                3 => 'wed', 4 => 'thu', 5 => 'fri', 6 => 'sat',
            ];

            $day_name = $days_map[Carbon::parse($date)->dayOfWeek];

            $day_schedule = collect($schedule)->firstWhere('day', $day_name);

            if (!$day_schedule) {
                return [
                    Carbon::parse($date . ' 00:00'),
                    Carbon::parse($date . ' 23:59'),
                ];
            }

            return [
                Carbon::parse($date . ' ' . ($day_schedule['start_time'] ?? '00:00')),
                Carbon::parse($date . ' ' . ($day_schedule['end_time'] ?? '23:59')),
            ];
        } catch (\Throwable $e) {
            return [
                Carbon::parse($date . ' 00:00'),
                Carbon::parse($date . ' 23:59'),
            ];
        }
    }


    /* --------------------------------------------------------------------------
       (2) GET BOOKED SLOTS → status_id instead of status
    ---------------------------------------------------------------------------*/
    private function getBookedSlots($staff_id, $date)
    {
        $active_status_ids = Status::whereIn('title', self::ACTIVE_APPOINTMENT_STATUSES)->pluck('id');

        $book_appointment = Appointment::where('staff_id', $staff_id)
            ->whereDate('date_of_turn', $date)
            ->whereIn('status_id', $active_status_ids)
            ->get(['start_time', 'end_time']);

        return $book_appointment->map(function ($app) use ($date) {
            return [
                'start' => Carbon::parse($date . ' ' . $app->start_time),
                'end' => Carbon::parse($date . ' ' . $app->end_time),
            ];
        })->toArray();
    }


    private function generateAndFilterSlots(Carbon $start_work, Carbon $end_work, int $duration, array $booked_slots)
    {
        $available_slots = [];
        $current = $start_work->copy();

        while (true) {
            $slot_end = $current->copy()->addMinutes($duration);

            if ($slot_end->greaterThan($end_work)) break;

            $slot_start = $current->copy();

            $is_booked = false;
            foreach ($booked_slots as $b) {
                if ($slot_start->lessThan($b['end']) && $slot_end->greaterThan($b['start'])) {
                    $is_booked = true;
                    break;
                }
            }

            if (!$is_booked) {
                $available_slots[] = [
                    'start_time' => $slot_start->format('H:i'),
                    'end_time'   => $slot_end->format('H:i'),
                ];
            }

            $current = $slot_end->copy();
        }

        return $available_slots;
    }


    /* --------------------------------------------------------------------------
       (3) Get Available Slots →Organization Removed, same output kept
    ---------------------------------------------------------------------------*/
    public function getAvailableSlots(AvailableSlotsRequest $request)
    {
        $service = Service::where('id',$request->service_id)->first();
                if (!$service) {
            throw new ErrorException('خدمت یافت نشد.');
        }

        $date = Carbon::parse($request->date)->format('Y-m-d');

        // Duration
        if (!empty($service->duration)) {
            $parts = explode(':', $service->duration);
            if (count($parts) >= 2) {
                $duration = ((int)$parts[0] * 60) + (int)$parts[1];
            }
        }

        [$start_work, $end_work] = $this->getStaffWorkingHours($request->staff_id, $date);

        $booked = $this->getBookedSlots($request->staff_id, $date);

        $available = $this->generateAndFilterSlots($start_work, $end_work, $duration, $booked);

        return [
            'message' => 'زمان‌های خالی با موفقیت دریافت شدند',
            'data'    => $available,
        ];
    }


    /* --------------------------------------------------------------------------
       (4) Add Appointment → no organization, fixed FK fields
    ---------------------------------------------------------------------------*/
    public function addAppointment(AppointmentCreateRequest $request)
    {
        $service = Service::find($request->service_id);
        if (!$service) {
            throw new ErrorException('خدمت یافت نشد.');
        }

        $staff = Staff::find($request->staff_id);
        if (!$staff) {
            throw new ErrorException('کارمند یافت نشد.');
        }

        $appointment_date = Carbon::parse($request->date_of_turn)->format('Y-m-d');
        $start_time = $request->start_time;

        // duration from service
        $duration = 30;
        if (!empty($service->duration)) {
            $p = explode(':', $service->duration);
            $duration = ((int)$p[0] * 60) + (int)$p[1];
        }

        $start_dt = Carbon::parse("$appointment_date $start_time");
        $end_dt   = $start_dt->copy()->addMinutes($duration);
        $end_time = $end_dt->format('H:i');

        $active_status_ids = Status::whereIn('title', self::ACTIVE_APPOINTMENT_STATUSES)->pluck('id');

        $conflict = Appointment::where('staff_id', $request->staff_id)
            ->whereDate('date_of_turn', $appointment_date)
            ->whereIn('status_id', $active_status_ids)
            ->where(fn($q) => $q->where('start_time', '<', $end_time)->where('end_time', '>', $start_time))
            ->exists();

        $allow = filter_var($request->permissible_interference, FILTER_VALIDATE_BOOLEAN);

        if ($conflict && !$allow) {
            throw new ErrorException('کارمند در این بازه زمانی مشغول است.');
        }

        return DB::transaction(function () use ($request, $appointment_date, $start_time, $end_time, $allow, $active_status_ids) {

            $initial_title = $allow ? 'confirmed' : 'pending';
            $initial_status = Status::firstOrCreate(
                ['title' => $initial_title],
                ['label' => $initial_title == 'confirmed' ? 'تایید شده' : 'در انتظار']
            );

            $appointment = Appointment::create([
                'user_id'                 => $request->user_id,
                'staff_id'                => $request->staff_id,
                'service_id'              => $request->service_id,
                'date_of_turn'            => $appointment_date,
                'start_time'              => $start_time,
                'end_time'                => $end_time,
                'status_id'               => $initial_status->id,
                'reservation_type'        => $request->type ?? 'Online',
                'permissible_interference'=> $allow,
            ]);

            if (!empty($request->resource_ids)) {
                $bulk = [];
                foreach ($request->resource_ids as $r) {
                    $bulk[] = [
                        'appointment_id' => $appointment->id,
                        'resource_id'    => $r,
                    ];
                }
                AppointmentResource::insert($bulk);
            }

            return [
                'message' => 'نوبت با موفقیت ثبت شد',
                'data'    => $appointment,
            ];
        });
    }


    /* --------------------------------------------------------------------------
       (5) EDIT Appointment (same as add, but update)
    ---------------------------------------------------------------------------*/
    public function editAppointment(AppointmentCreateRequest $request, $id)
    {
        $appointment = Appointment::findOrFail($id);

        $service = Service::find($request->service_id);
        if (!$service) throw new ErrorException('خدمت یافت نشد.');

        $staff = Staff::find($request->staff_id);
        if (!$staff) throw new ErrorException('کارمند یافت نشد.');

        $appointment_date = $request->date_of_turn;
        $start_time = $request->start_time;

        $duration = 30;
        if (!empty($service->duration)) {
            $p = explode(':', $service->duration);
            $duration = ((int)$p[0] * 60) + (int)$p[1];
        }

        $end_time = Carbon::parse($start_time)->copy()->addMinutes($duration)->format('H:i');

        $active_status_ids = Status::whereIn('title', self::ACTIVE_APPOINTMENT_STATUSES)->pluck('id');

        $conflict = Appointment::where('staff_id', $request->staff_id)
            ->where('id', '!=', $id)
            ->whereDate('date_of_turn', $appointment_date)
            ->whereIn('status_id', $active_status_ids)
            ->where(fn($q) => $q->where('start_time', '<', $end_time)->where('end_time', '>', $start_time))
            ->exists();

        $allow = filter_var($request->permissible_interference, FILTER_VALIDATE_BOOLEAN);

        if ($conflict && !$allow)
            throw new ErrorException('کارمند در این بازه زمانی مشغول است.');

        return DB::transaction(function () use ($request, $appointment, $appointment_date, $start_time, $end_time, $allow) {

            $initial_title = $allow ? 'confirmed' : 'pending';
            $initial_status = Status::firstOrCreate(
                ['title' => $initial_title],
                ['label' => $initial_title == 'confirmed' ? 'تایید شده' : 'در انتظار']
            );

            $appointment->update([
                'user_id'                 => $request->user_id,
                'staff_id'                => $request->staff_id,
                'service_id'              => $request->service_id,
                'date_of_turn'            => $appointment_date,
                'start_time'              => $start_time,
                'end_time'                => $end_time,
                'status_id'               => $initial_status->id,
                'reservation_type'        => $request->type ?? 'Online',
                'permissible_interference'=> $allow,
            ]);

            AppointmentResource::where('appointment_id', $appointment->id)->delete();

            if (!empty($request->resource_ids)) {
                $bulk = [];
                foreach ($request->resource_ids as $r) {
                    $bulk[] = [
                        'appointment_id' => $appointment->id,
                        'resource_id'    => $r,
                    ];
                }
                AppointmentResource::insert($bulk);
            }

            return [
                'message' => 'نوبت با موفقیت ویرایش شد',
                'data'    => $appointment,
            ];
        });
    }


/* --------------------------------------------------------------------------
       (6) Calendar Dashboard → outputs unchanged, organization removed
    ---------------------------------------------------------------------------*/
    public function getCalendarDashboard(Request $request)
    {
        $date = Carbon::parse($request->date)->format('Y-m-d');
        $staff_ids = $request->staff_ids ?? [];
        $resource_ids = $request->resource_ids ?? [];
        $user_ids = $request->user_ids ?? [];

        // If no staff_ids provided and user is a doctor, filter by their staff ID
        if (empty($staff_ids)) {
            $user = Auth::user();
            if ($user && $user->role === 'doctor') {
                $staff = Staff::where('user_id', $user->id)->first();
                if ($staff) {
                    $staff_ids = [$staff->id];
                }
            }
        }

        $staff_query = Staff::with(['user', 'expertise']);
        if (!empty($staff_ids)) {
            $staff_query->whereIn('id', $staff_ids);
        }
        $staffs = $staff_query->get();

        $resources = Resource::when(!empty($resource_ids), fn($q) => $q->whereIn('id', $resource_ids))->get();

        $appointments = Appointment::with(['user', 'staff.user', 'service', 'status', 'resources'])
            ->when(!empty($staff_ids), fn($q) => $q->whereIn('staff_id', $staff_ids))
            ->when(!empty($resource_ids), fn($q) =>
            $q->whereHas('resources', fn($rq) => $rq->whereIn('resource_id', $resource_ids))
            )
            ->when(!empty($user_ids), fn($q) => $q->whereIn('user_id', $user_ids))
            ->whereDate('date_of_turn', $date)
            ->get();

        $timeline = $staffs->map(function ($staff) use ($appointments, $date) {

            $staff_apps = $appointments->where('staff_id', $staff->id);

            [$start, $end] = $this->getStaffWorkingHours($staff->id, $date);

            return [
                'staff_id' => $staff->id,
                'staff_name' => $staff->user->name ?? 'نامشخص',
                'expertise' => $staff->expertise->title ?? 'بدون تخصص',
                'working_hours' => [
                    'start' => $start->format('H:i'),
                    'end'   => $end->format('H:i')
                ],
                'appointments' => $staff_apps->map(function ($app) {
                    return [
                        'id' => $app->id,
                        'customer_name' => $app->user->name ?? 'مشتری گذری',
                        'customer_user_id' => $app->user_id,
                        'customer_info' => [
                            'id' => $app->user->id ?? null,
                            'name' => $app->user->name ?? 'مشتری گذری',
                            'phone' => $app->user->phone ?? null,
                            'email' => $app->user->email ?? null,
                        ],
                        'service_name' => $app->service->title ?? 'خدمت نامشخص',
                        'start' => $app->start_time,
                        'end'   => $app->end_time,
                        'status' => $app->status->label ?? 'نامشخص',
                        'status_title' => $app->status->title ?? '',
                        'resources' => $app->resources->pluck('resource_name'),
                    ];
                })->values(),
            ];
        });

        $resource_usage = $resources->map(function ($resource) use ($appointments) {

            $use = $appointments->filter(fn($app) => $app->resources->contains('id', $resource->id));

            return [
                'resource_id' => $resource->id,
                'resource_name' => $resource->resource_name,
                'resource_type' => $resource->resource_type,
                'usage' => $use->map(function ($app) {
                    return [
                        'start' => $app->start_time,
                        'end' => $app->end_time,
                        'staff' => $app->staff->user->name ?? 'نامشخص',
                        'customer_user_id' => $app->user_id,
                        'customer_name' => $app->user->name ?? 'مشتری گذری',
                    ];
                })->values(),
            ];
        });

        return [
            'date' => $date,
            'timeline' => $timeline,
            'resource_usage' => $resource_usage,
            'summary' => [
                'total_appointments' => $appointments->count(),
                'confirmed_count' => $appointments->where('status.title', 'confirmed')->count(),
                'pending_count' => $appointments->where('status.title', 'pending')->count(),
            ],
        ];
    }

    public function getCurrentAppointment()
    {
        $now = Carbon::now();
        $today = $now->format('Y-m-d');
        $current_time = $now->format('H:i:s');

        $active_status_ids = Status::whereIn('title', self::ACTIVE_APPOINTMENT_STATUSES)->pluck('id');

        $query = Appointment::with(['user','staff.user','service','status']);

        // Filter by doctor's staff ID if user is a doctor
        $user = Auth::user();
        if ($user && $user->role === 'doctor') {
            $staff = Staff::where('user_id', $user->id)->first();
            if ($staff) {
                $query->where('staff_id', $staff->id);
            }
        }

        $appointment = $query
            ->whereDate('date_of_turn', $today)
            ->whereIn('status_id', $active_status_ids)
            ->where('start_time', '<=', $current_time)
            ->where('end_time', '>', $current_time)
            ->first();

        if (!$appointment) {
            return [
                'message' => 'در حال حاضر هیچ نوبتی در حال اجرا نیست.',
                'data' => null
            ];
        }

        return [
            'message' => 'نوبت فعلی یافت شد.',
            'data' => $appointment
        ];
    }

}
