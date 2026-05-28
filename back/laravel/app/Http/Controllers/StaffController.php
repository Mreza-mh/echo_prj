<?php

namespace App\Http\Controllers;

use App\Http\Requests\Staff\StaffFilterRequest;
use App\Http\Requests\Staff\StaffCreateRequest;
use App\Http\Requests\Staff\StaffEditRequest;
use App\Http\Requests\Staff\StaffScheduleRequest;
use App\Http\Responses\ApiResponse;
use App\Services\StaffService;

class StaffController
{
    protected StaffService $staffService;

    public function __construct(StaffService $staffService)
    {
        $this->staffService = $staffService;
    }

    /**
     * @OA\Post(
     *     path="/staff/list",
     *     tags={"Staff"},
     *     summary="دریافت لیست کارمندان",
     *     @OA\RequestBody(
     *         required=false,
     *         @OA\JsonContent(
     *             @OA\Property(property="is_paginate", type="boolean", example=true),
     *             @OA\Property(property="count_item", type="integer", example=10),
     *             @OA\Property(property="expertise_id", type="integer", example=2),
     *             @OA\Property(property="day", type="string", example="sat")
     *         )
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="لیست کارمندان بازگشت داده شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="لیست پرسنل ها با موفقیت دریافت شد"),
     *             @OA\Property(property="data", type="array", @OA\Items(type="object"))
     *         )
     *     )
     * )
     */
    public function getStaffList(StaffFilterRequest $request)
    {
        $result = $this->staffService->getStaffList($request);
        return ApiResponse::success($result['data'], $result['message']);
    }

    /**
     * @OA\Get(
     *     path="/staff/{staff_id}",
     *     tags={"Staff"},
     *     summary="دریافت جزئیات یک کارمند",
     *     @OA\Parameter(
     *         name="staff_id",
     *         in="path",
     *         required=true,
     *         @OA\Schema(type="integer")
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="جزئیات کارمند بازگشت داده شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="پرسنل مورد نظر با موفقیت دریافت شد"),
     *             @OA\Property(property="data", type="object")
     *         )
     *     )
     * )
     */
    public function getStaff($staff_id)
    {
        $result = $this->staffService->getStaff($staff_id);
        return ApiResponse::success($result['data'], $result['message']);
    }

    /**
     * @OA\Post(
     *     path="/staff/add",
     *     tags={"Staff"},
     *     summary="افزودن کارمند جدید",
     *     @OA\RequestBody(
     *         required=true,
     *         @OA\JsonContent(
     *             required={"user_id","expertise_id","schedule"},
     *             @OA\Property(property="user_id", type="integer", example=5),
     *             @OA\Property(property="expertise_id", type="integer", example=2),
     *             @OA\Property(
     *                 property="schedule",
     *                 type="array",
     *                 @OA\Items(
     *                     @OA\Property(property="day", type="string", example="sat"),
     *                     @OA\Property(property="start_time", type="string", example="09:00:00"),
     *                     @OA\Property(property="end_time", type="string", example="12:00:00")
     *                 )
     *             )
     *         )
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="کارمند با موفقیت اضافه شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="پرسنل با موفقیت افزوده شد"),
     *             @OA\Property(property="data", type="object")
     *         )
     *     )
     * )
     */
    public function addStaff(StaffCreateRequest $request)
    {
        $result = $this->staffService->addStaff($request);
        return ApiResponse::success($result['data'], $result['message']);
    }

    /**
     * @OA\Patch(
     *     path="/staff/edit/{staff_id}",
     *     tags={"Staff"},
     *     summary="ویرایش کارمند",
     *     @OA\Parameter(
     *         name="staff_id",
     *         in="path",
     *         required=true,
     *         @OA\Schema(type="integer")
     *     ),
     *     @OA\RequestBody(
     *         required=false,
     *         @OA\JsonContent(
     *             @OA\Property(property="user_id", type="integer", example=5),
     *             @OA\Property(property="expertise_id", type="integer", example=2),
     *             @OA\Property(
     *                 property="schedule",
     *                 type="array",
     *                 @OA\Items(
     *                     @OA\Property(property="day", type="string", example="sun"),
     *                     @OA\Property(property="start_time", type="string", example="14:00:00"),
     *                     @OA\Property(property="end_time", type="string", example="18:00:00")
     *                 )
     *             )
     *         )
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="کارمند با موفقیت ویرایش شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="پرسنل با موفقیت ویرایش شد"),
     *             @OA\Property(property="data", type="object")
     *         )
     *     )
     * )
     */
    public function editStaff(StaffEditRequest $request, $staff_id)
    {
        $result = $this->staffService->editStaff($request, $staff_id);
        return ApiResponse::success($result['data'], $result['message']);
    }

    /**
     * @OA\Delete (
     *     path="/staff/delete/{staff_id}",
     *     tags={"Staff"},
     *     summary="حذف کارمند",
     *     @OA\Parameter(
     *         name="staff_id",
     *         in="path",
     *         required=true,
     *         @OA\Schema(type="integer")
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="کارمند با موفقیت حذف شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="پرسنل با موفقیت حذف شد"),
     *             @OA\Property(property="data", type="object", example=null)
     *         )
     *     )
     * )
     */
    public function deleteStaff($staff_id)
    {
        $result = $this->staffService->deleteStaff($staff_id);
        return ApiResponse::success($result['data'], $result['message']);
    }


    /**
     * @OA\Post(
     *     path="/staff-schedule/add/{staff_id}",
     *     tags={"Staff Schedule"},
     *     summary="افزودن برنامه زمانی برای کارمند",
     *     description="این متد برنامه زمانی هفتگی یک کارمند را ثبت می‌کند.",
     *     security={{"bearerAuth":{}}},
     *
     *     @OA\Parameter(
     *         name="staff_id",
     *         in="path",
     *         required=true,
     *         description="شناسه کارمند",
     *         @OA\Schema(type="integer", example=5)
     *     ),
     *
     *     @OA\RequestBody(
     *         required=true,
     *         @OA\JsonContent(
     *             required={"schedule"},
     *             @OA\Property(
     *                 property="schedule",
     *                 type="array",
     *                 @OA\Items(
     *                     type="object",
     *                     required={"day","start_time","end_time"},
     *                     @OA\Property(property="day", type="string", example="sat", description="روز هفته"),
     *                     @OA\Property(property="start_time", type="string", format="time", example="08:00:00"),
     *                     @OA\Property(property="end_time", type="string", format="time", example="14:00:00")
     *                 )
     *             )
     *         )
     *     ),
     *
     *     @OA\Response(
     *         response=200,
     *         description="برنامه زمانی با موفقیت ثبت شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="برنامه زمانی با موفقیت ثبت شد"),
     *             @OA\Property(property="data", type="array", @OA\Items(type="object"))
     *         )
     *     ),
     *
     *     @OA\Response(
     *         response=400,
     *         description="خطای اعتبارسنجی",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=false),
     *             @OA\Property(property="message", type="string", example="زمان پایان باید بعد از زمان شروع باشد.")
     *         )
     *     )
     * )
     */
    public function addStaffSchedule(StaffScheduleRequest $request, $staff_id)
    {
        $result = $this->staffService->addStaffSchedule($request, $staff_id);
        return ApiResponse::success($result['data'], $result['message']);
    }
}
