<?php

namespace App\Services;

use App\Enums\StaffRoleType;
use App\Enums\UserRole;
use App\Exceptions\ErrorException;
use App\Http\Requests\Expertise\ExpertiseFilterRequest;
use App\Http\Requests\Expertise\ExpertiseCreateRequest;
use App\Http\Requests\Expertise\ExpertiseEditRequest;
use App\Models\Expertise;
use App\Models\Staff;
use Illuminate\Support\Facades\Auth;

class ExpertiseService
{
    public function getExpertiseList(ExpertiseFilterRequest $request)
    {
        $is_paginate = $request->filled('is_paginate') ? filter_var($request->is_paginate, FILTER_VALIDATE_BOOLEAN) : false;
        $count_item  = $request->filled('count_item') ? filter_var($request->count_item, FILTER_VALIDATE_INT) : 10;

        $query = Expertise::query();

        if ($request->filled('title')) {
            $query->where('title', 'like', "%{$request->title}%");
        }

        if ($request->filled('label')) {
            $query->where('label', 'like', "%{$request->label}%");
        }

        $expertises = $is_paginate ? $query->paginate($count_item) : $query->get();

        return [
            'message' => 'لیست تخصص‌ها با موفقیت دریافت شد',
            'data'    => $expertises
        ];
    }

    public function getExpertise($expertise_id)
    {
        $expertise = Expertise::where('id', $expertise_id)->first();

        if (!$expertise) {
            throw new ErrorException('تخصص مورد نظر یافت نشد');
        }

        return [
            'message' => 'تخصص با موفقیت دریافت شد',
            'data'    => $expertise
        ];
    }

    public function addExpertise(ExpertiseCreateRequest $request)
    {
        $expertise = Expertise::create([
            'title' => $request->title,
            'label' => $request->label,
        ]);

        return [
            'message' => 'تخصص با موفقیت ایجاد شد',
            'data'    => $expertise
        ];
    }

    public function editExpertise(ExpertiseEditRequest $request, $expertise_id)
    {
        $expertise = Expertise::where('id', $expertise_id)->first();

        if (!$expertise) {
            throw new ErrorException('تخصص مورد نظر یافت نشد');
        }

        $expertise->fill([
            'title' => $request->title,
            'label' => $request->label,
        ])->save();

        return [
            'message' => 'تخصص با موفقیت ویرایش شد',
            'data'    => $expertise
        ];
    }

    public function deleteExpertise($expertise_id)
    {
        $expertise = Expertise::where('id', $expertise_id)->first();

        if (!$expertise) {
            throw new ErrorException('تخصص مورد نظر یافت نشد');
        }

        $expertise->delete();

        return [
            'message' => 'تخصص با موفقیت حذف شد',
            'data'    => null
        ];
    }
}
