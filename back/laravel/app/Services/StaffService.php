<?php

namespace App\Services;

use App\Enums\StaffRoleType;
use App\Enums\UserRole;
use App\Exceptions\ErrorException;
use App\Http\Requests\Staff\StaffFilterRequest;
use App\Http\Requests\Staff\StaffCreateRequest;
use App\Http\Requests\Staff\StaffEditRequest;
use App\Http\Requests\Staff\StaffScheduleRequest;
use App\Models\Staff;
use Illuminate\Support\Facades\Auth;

class StaffService
{

    public function getStaffList(StaffFilterRequest $request)
    {
        $is_paginate = $request->filled('is_paginate') ? filter_var($request->is_paginate, FILTER_VALIDATE_BOOLEAN) : false;
        $count_item  = $request->filled('count_item') ? filter_var($request->count_item, FILTER_VALIDATE_INT) : 10;

        $query = Staff::with(['user:id,name,mobile,role', 'expertise:id,title']);

        if ($request->filled('expertise_id')) {
            $query->where('staffs.expertise_id', $request->expertise_id);
        }
        if ($request->filled('day')) {
            // JSON column filtering: contains day
            $query->whereJsonContains('schedule', [['day' => $request->day]]);
            //TODO: اگه بالایی ارور داد اینو بزار:
            //TODO: $query->whereJsonContains('schedule', ['day' => $request->day]);
        }

        $staffs = $is_paginate ? $query->paginate($count_item) : $query->get();

        // اضافه کردن اطلاعات اضافی برای سازگاری با فرانت‌اند
        $staffs->each(function ($staff) {
            $staff->name = $staff->user->name; // نام کاربر به عنوان نام پرسنل
            $staff->expertise_name = $staff->expertise->title ?? null; // عنوان تخصص
            $staff->role = $staff->user->role ?? null;
            //$staff->organization_staff_id = $staff->id; // ایدی برای سازگاری
        });

        return [
            'message' => 'لیست پرسنل ها با موفقیت دریافت شد',
            'data'    => $staffs
        ];
    }

    public function getStaff($staff_id)
    {
        $staff = Staff::where('id', $staff_id)->with(['user', 'expertise'])->first();

        if ($staff == null) {
            throw new ErrorException('پرسنل وجود ندارد!');
        }

        return [
            'message' => 'پرسنل مورد نظر با موفقیت دریافت شد',
            'data'    => $staff
        ];
    }

    public function addStaff(StaffCreateRequest $request)
    {
        $staff = Staff::create([
            'user_id'         => $request->user_id,
            'expertise_id'    => $request->expertise_id,
        ]);

        return [
            'message' => 'پرسنل با موفقیت افزوده شد',
            'data'    => $staff
        ];
    }

    public function addStaffSchedule(StaffScheduleRequest $request, $staff_id)
    {
        $staff = Staff::where('id', $staff_id)->first();

        if ($staff == null) {
            throw new ErrorException('پرسنل وجود ندارد!');
        }

        $staff = Staff::update([
            'schedule' => $request->schedule,
        ]);

        return [
            'message' => 'برنامه کاری با موفقیت افزوده شد',
            'data'    => $staff
        ];
    }

    //    public function StaffScheduleList(StaffFilterRequest $request)
//    {
//        $staff = Staff::where('id', $staff_id)->first();
//
//        if ($staff == null) {
//            throw new ErrorException('پرسنل وجود ندارد!');
//        }
//
//        $staff = Staff::update([
//            'schedule' => $request->schedule,
//        ]);
//
//        return [
//            'message' => 'برنامه کاری با موفقیت افزوده شد',
//            'data'    => $staff
//        ];
//    }

    public function editStaff(StaffEditRequest $request, $staff_id)
    {
        $staff = Staff::where('id', $staff_id)->first();

        if ($staff == null) {
            throw new ErrorException('پرسنل وجود ندارد!');
        }

        $staff->fill([
            'user_id'         => $request->user_id,
            'expertise_id'    => $request->expertise_id,
            'schedule' => $request->schedule,
        ])->save();

        return [
            'message' => 'پرسنل با موفقیت ویرایش شد',
            'data'    => $staff
        ];
    }

    public function deleteStaff($staff_id)
    {
        $staff = Staff::where('id', $staff_id)->first();

        if ($staff == null) {
            throw new ErrorException('پرسنل وجود ندارد!');
        }

        $staff->delete();

        return [
            'message' => 'پرسنل با موفقیت حذف شد',
            'data'    => null
        ];
    }
}
