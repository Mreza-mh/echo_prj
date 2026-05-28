<?php

namespace App\Services;

use App\Enums\StaffRoleType;
use App\Enums\UserRole;
use App\Exceptions\ErrorException;
use App\Http\Requests\Status\StatusFilterRequest;
use App\Http\Requests\Status\StatusCreateRequest;
use App\Http\Requests\Status\StatusEditRequest;
use App\Models\Staff;
use App\Models\Status;
use Illuminate\Support\Facades\Auth;

class StatusService
{
    public function getStatusList(StatusFilterRequest $request)
    {
        $is_paginate = $request->filled('is_paginate') ? filter_var($request->is_paginate, FILTER_VALIDATE_BOOLEAN) : false;
        $count_item  = $request->filled('count_item') ? filter_var($request->count_item, FILTER_VALIDATE_INT) : 10;

        $query = Status::query();

        if ($request->filled('title')) {
            $query->where('title', 'like', '%' . $request->title . '%');
        }

        if ($request->filled('label')) {
            $query->where('label', 'like', '%' . $request->label . '%');
        }

        $statuses = $is_paginate ? $query->paginate($count_item) : $query->get();

        return [
            'message' => 'لیست وضعیت‌ها با موفقیت دریافت شد',
            'data'    => $statuses
        ];
    }

    public function getStatus($status_id)
    {
        $status = Status::where('id', $status_id)->first();
        if(!$status){
            throw new ErrorException('وضعیت مورد نظر وجود ندارد!');
        }

        return [
            'message' => 'وضعیت با موفقیت دریافت شد',
            'data'    => $status
        ];
    }

    public function addStatus(StatusCreateRequest $request)
    {
        $status = Status::create([
            'title' => $request->title,
            'label' => $request->label,
        ]);

        return [
            'message' => 'وضعیت با موفقیت افزوده شد',
            'data'    => $status
        ];
    }

    public function editStatus(StatusEditRequest $request, $status_id)
    {
        $status = Status::where('id', $status_id)->first();
        if(!$status){
            throw new ErrorException('وضعیت مورد نظر وجود ندارد!');
        }

        $status->fill([
            'title' => $request->title,
            'label' => $request->label,
        ])->save();

        return [
            'message' => 'وضعیت با موفقیت ویرایش شد',
            'data'    => $status
        ];
    }

    public function deleteStatus($status_id)
    {
        $status = Status::where('id', $status_id)->first();
        if(!$status){
            throw new ErrorException('وضعیت مورد نظر وجود ندارد!');
        }

        $status->delete();

        return [
            'message' => 'وضعیت با موفقیت حذف شد',
            'data'    => null
        ];
    }
}
