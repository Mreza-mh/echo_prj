<?php

namespace App\Http\Controllers;

use App\Http\Requests\Appointment\AppointmentCreateRequest;
use App\Http\Requests\Appointment\AvailableSlotsRequest;
use App\Http\Responses\ApiResponse;
use App\Services\AppointmentService;

use App\Models\Appointment;

class AppointmentController
{
    protected AppointmentService $appointmentService;

    public function __construct(AppointmentService $appointmentService){
        $this->appointmentService = $appointmentService;
    }

    /**
     * @OA\Post(
     *     path="/appointment/get-available-slots",
     *     tags={"Appointment"},
     *     summary="دریافت زمان‌های خالی برای رزرو",
     *     @OA\RequestBody(
     *         required=true,
     *         @OA\JsonContent(
     *             required={"service_id","staff_id","date"},
     *             @OA\Property(property="service_id", type="integer", example=1),
     *             @OA\Property(property="staff_id", type="integer", example=3),
     *             @OA\Property(property="date", type="string", format="date", example="2026-01-05")
     *         )
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="زمان‌های خالی بازگردانده شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="عملیات موفق"),
     *             @OA\Property(
     *                 property="data",
     *                 type="array",
     *                 @OA\Items(type="object",
     *                     @OA\Property(property="start_time", type="string", example="09:00"),
     *                     @OA\Property(property="end_time", type="string", example="09:30")
     *                 )
     *             )
     *         )
     *     )
     * )
     */

    public function getAvailableSlots(AvailableSlotsRequest $request){
        $result = $this->appointmentService->getAvailableSlots($request);
        return ApiResponse::success($result['data'], $result['message']);
    }

    /**
     * @OA\Post(
     *     path="/appointment/add-appointment",
     *     tags={"Appointment"},
     *     summary="ثبت نوبت جدید",
     *     @OA\RequestBody(
     *         required=true,
     *         @OA\JsonContent(
     *             required={"user_id","staff_id","service_id","date_of_turn","start_time"},
     *             @OA\Property(property="user_id", type="integer", example=5),
     *             @OA\Property(property="staff_id", type="integer", example=2),
     *             @OA\Property(property="service_id", type="integer", example=7),
     *             @OA\Property(property="date_of_turn", type="string", format="date", example="2026-01-05"),
     *             @OA\Property(property="start_time", type="string", example="14:30"),
     *             @OA\Property(property="type", type="string", example="Online"),
     *             @OA\Property(property="permissible_interference", type="boolean", example=false),
     *             @OA\Property(
     *                 property="resource_ids",
     *                 type="array",
     *                 @OA\Items(type="integer"),
     *                 example={1,2}
     *             )
     *         )
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="نوبت با موفقیت ثبت شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="نوبت با موفقیت ثبت شد"),
     *             @OA\Property(property="data", type="object")
     *         )
     *     )
     * )
     */

    public function addAppointment(AppointmentCreateRequest $request){
        $result = $this->appointmentService->addAppointment($request);
        return ApiResponse::success($result['data'], $result['message']);
    }

    /**
     * @OA\Patch(
     *     path="/appointment/edit-appointment/{id}",
     *     tags={"Appointment"},
     *     summary="ویرایش نوبت",
     *     @OA\Parameter(
     *         name="id",
     *         in="path",
     *         required=true,
     *         @OA\Schema(type="integer"),
     *         example=10
     *     ),
     *     @OA\RequestBody(
     *         required=true,
     *         @OA\JsonContent(
     *             required={"user_id","staff_id","service_id","date_of_turn","start_time"},
     *             @OA\Property(property="user_id", type="integer", example=5),
     *             @OA\Property(property="staff_id", type="integer", example=2),
     *             @OA\Property(property="service_id", type="integer", example=7),
     *             @OA\Property(property="date_of_turn", type="string", format="date", example="2026-01-05"),
     *             @OA\Property(property="start_time", type="string", example="14:30"),
     *             @OA\Property(property="type", type="string", example="Online"),
     *             @OA\Property(property="permissible_interference", type="boolean", example=false),
     *             @OA\Property(
     *                 property="resource_ids",
     *                 type="array",
     *                 @OA\Items(type="integer"),
     *                 example={1,2}
     *             )
     *         )
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="نوبت با موفقیت ویرایش شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="نوبت با موفقیت ویرایش شد"),
     *             @OA\Property(property="data", type="object")
     *         )
     *     )
     * )
     */

    public function editAppointment(AppointmentCreateRequest $request, $id){
        $result = $this->appointmentService->editAppointment($request, $id);
        return ApiResponse::success($result['data'], $result['message']);
    }

    /**
     * @OA\Get(
     *     path="/appointment/get-appointment/{id}",
     *     tags={"Appointment"},
     *     summary="دریافت جزئیات یک نوبت",
     *     @OA\Parameter(name="id", in="path", required=true, @OA\Schema(type="integer"), example=12),
     *     @OA\Response(
     *         response=200,
     *         description="جزئیات نوبت بازگردانده شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="اطلاعات نوبت با موفقیت دریافت شد"),
     *             @OA\Property(property="data", type="object")
     *         )
     *     )
     * )
     */

    public function getAppointment($id){
        $appointment = Appointment::with(['resources', 'staff'])->findOrFail($id);
        return ApiResponse::success($appointment, 'اطلاعات نوبت با موفقیت دریافت شد');
    }

    /**
     * @OA\Post(
     *     path="/appointment/get-calendar-dashboard",
     *     tags={"Appointment"},
     *     summary="دریافت اطلاعات جامع تقویم برای داشبورد منشی",
     *     @OA\RequestBody(
     *         required=true,
     *         @OA\JsonContent(
     *             required={"date"},
     *             @OA\Property(property="date", type="string", format="date", example="2026-01-05"),
     *             @OA\Property(
     *                 property="staff_ids",
     *                 type="array",
     *                 @OA\Items(type="integer"),
     *                 example={1,2}
     *             ),
     *             @OA\Property(
     *                 property="resource_ids",
     *                 type="array",
     *                 @OA\Items(type="integer"),
     *                 example={3}
     *             ),
     *             @OA\Property(
     *                 property="user_ids",
     *                 type="array",
     *                 @OA\Items(type="integer"),
     *                 example={5,6}
     *             )
     *         )
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="اطلاعات تقویم بازگردانده شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="اطلاعات تقویم با موفقیت دریافت شد"),
     *             @OA\Property(
     *                 property="data",
     *                 type="object",
     *                 @OA\Property(property="date", type="string", example="2026-01-05"),
     *                 @OA\Property(
     *                     property="timeline",
     *                     type="array",
     *                     @OA\Items(
     *                         type="object",
     *                         @OA\Property(property="staff_id", type="integer", example=1),
     *                         @OA\Property(property="staff_name", type="string", example="دکتر احمدی"),
     *                         @OA\Property(property="expertise", type="string", example="قلب و عروق"),
     *                         @OA\Property(
     *                             property="working_periods",
     *                             type="array",
     *                             @OA\Items(
     *                                 type="object",
     *                                 @OA\Property(property="start", type="string", example="08:00"),
     *                                 @OA\Property(property="end", type="string", example="12:00")
     *                             )
     *                         ),
     *                         @OA\Property(
     *                             property="appointments",
     *                             type="array",
     *                             @OA\Items(
     *                                 type="object",
     *                                 @OA\Property(property="id", type="integer", example=1),
     *                                 @OA\Property(property="customer_name", type="string", example="علی محمدی"),
     *                                 @OA\Property(property="service_name", type="string", example="معاینه قلب"),
     *                                 @OA\Property(property="start", type="string", example="09:00"),
     *                                 @OA\Property(property="end", type="string", example="09:30"),
     *                                 @OA\Property(property="status", type="string", example="تایید شده")
     *                             )
     *                         )
     *                     )
     *                 ),
     *                 @OA\Property(
     *                     property="resource_usage",
     *                     type="array",
     *                     @OA\Items(
     *                         type="object",
     *                         @OA\Property(property="resource_id", type="integer", example=1),
     *                         @OA\Property(property="resource_name", type="string", example="اتاق ۱"),
     *                         @OA\Property(property="resource_type", type="string", example="room"),
     *                         @OA\Property(
     *                             property="usage",
     *                             type="array",
     *                             @OA\Items(
     *                                 type="object",
     *                                 @OA\Property(property="start", type="string", example="09:00"),
     *                                 @OA\Property(property="end", type="string", example="09:30"),
     *                                 @OA\Property(property="staff", type="string", example="دکتر احمدی")
     *                             )
     *                         )
     *                     )
     *                 ),
     *                 @OA\Property(
     *                     property="summary",
     *                     type="object",
     *                     @OA\Property(property="total_appointments", type="integer", example=10),
     *                     @OA\Property(property="confirmed_count", type="integer", example=8),
     *                     @OA\Property(property="pending_count", type="integer", example=2)
     *                 )
     *             )
     *         )
     *     )
     * )
     */

    public function getCalendarDashboard(\Illuminate\Http\Request $request){
        $result = $this->appointmentService->getCalendarDashboard($request);
        return ApiResponse::success($result, 'اطلاعات تقویم با موفقیت دریافت شد');
    }

    /**
     * @OA\Get(
     *     path="/appointment/get-current-appointment",
     *     tags={"Appointment"},
     *     summary="دریافت نوبت در حال اجرا (الان)",
     *     description="چک می‌کند که در این لحظه کدام نوبت فعال در حال انجام است.",
     *     @OA\Response(
     *         response=200,
     *         description="اطلاعات نوبت فعلی بازگردانده شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="نوبت فعلی یافت شد"),
     *             @OA\Property(property="data", type="object", nullable=true)
     *         )
     *     )
     * )
     */
    public function getCurrentAppointment(\Illuminate\Http\Request $request)
    {
        $result = $this->appointmentService->getCurrentAppointment($request->staff_id);
        return ApiResponse::success($result['data'], $result['message']);
    }

    /**
     * @OA\Post(
     *     path="/appointment/list",
     *     tags={"Appointment"},
     *     summary="دریافت لیست نوبت‌ها",
     *     @OA\RequestBody(
     *         required=false,
     *         @OA\JsonContent(
     *             @OA\Property(property="date", type="string", format="date", example="2026-01-05"),
     *             @OA\Property(property="is_paginate", type="boolean", example=false),
     *             @OA\Property(property="staff_id", type="integer", example=2)
     *         )
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="لیست نوبت‌ها بازگردانده شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="عملیات موفق"),
     *             @OA\Property(
     *                 property="data",
     *                 type="array",
     *                 @OA\Items(
     *                     type="object",
     *                     @OA\Property(property="id", type="integer", example=1),
     *                     @OA\Property(property="service_id", type="integer", example=1),
     *                     @OA\Property(property="user_id", type="integer", example=1),
     *                     @OA\Property(property="staff_id", type="integer", example=1),
     *                     @OA\Property(property="date_of_turn", type="string", format="date", example="2026-01-05"),
     *                     @OA\Property(property="start_time", type="string", format="time", example="09:00:00"),
     *                     @OA\Property(property="end_time", type="string", format="time", example="09:30:00"),
     *                     @OA\Property(property="status_id", type="integer", example=1),
     *                     @OA\Property(property="reservation_type", type="string", example="online"),
     *                     @OA\Property(property="permissible_interference", type="boolean", example=true),
     *                     @OA\Property(property="created_at", type="string", format="date-time"),
     *                     @OA\Property(property="updated_at", type="string", format="date-time")
     *                 )
     *             )
     *         )
     *     )
     * )
     */
    public function listAppointments(\Illuminate\Http\Request $request)
    {
        $query = Appointment::with(['user', 'staff.user', 'service', 'status']);

        $user = \Illuminate\Support\Facades\Auth::user();
        if ($user && $user->role === 'doctor') {
            $staff = \App\Models\Staff::where('user_id', $user->id)->first();
            if ($staff) {
                $query->where('staff_id', $staff->id);
            }
        }

        if ($request->filled('date')) {
            $query->whereDate('date_of_turn', $request->date);
        }

        $isPaginate = $request->filled('is_paginate') ? filter_var($request->is_paginate, FILTER_VALIDATE_BOOLEAN) : false;
        
        $appointments = $isPaginate ? $query->paginate(10) : $query->get();

        return ApiResponse::success($appointments, 'عملیات موفق');
    }

}
