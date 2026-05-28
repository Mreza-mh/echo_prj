<?php

namespace App\Services;

use App\Enums\StaffRoleType;
use App\Enums\UserRole;
use App\Exceptions\ErrorException;
use App\Http\Requests\Resource\ResourceFilterRequest;
use App\Http\Requests\Resource\ResourceCreateRequest;
use App\Http\Requests\Resource\ResourceEditRequest;
use App\Models\Resource;
use App\Models\Staff;
use Illuminate\Support\Facades\Auth;

class ResourceService
{
    public function getResourceList(ResourceFilterRequest $request)
    {
        $is_paginate = $request->filled('is_paginate') ? filter_var($request->is_paginate, FILTER_VALIDATE_BOOLEAN) : false;
        $count_item  = $request->filled('count_item') ? filter_var($request->count_item, FILTER_VALIDATE_INT) : 10;

        $query = Resource::query();

        if ($request->filled('resource_name')) {
            $query->where('resource_name', 'like', '%' . $request->resource_name . '%');
        }

        if ($request->filled('resource_type')) {
            $query->where('resource_type', $request->resource_type);
        }

        $resources = $is_paginate ? $query->paginate($count_item) : $query->get();

        return [
            'message' => 'لیست منابع با موفقیت دریافت شد',
            'data'    => $resources
        ];
    }

    public function getResource($resource_id)
    {
        $resource = Resource::where('id', $resource_id)->first();
        if(!$resource){
            throw new ErrorException('منبع مورد نظر وجود ندارد!');
        }

        return [
            'message' => 'منبع با موفقیت دریافت شد',
            'data'    => $resource
        ];
    }

    public function addResource(ResourceCreateRequest $request)
    {
        $resource = Resource::create([
            'resource_name'   => $request->resource_name,
            'resource_type'   => $request->resource_type,
        ]);

        return [
            'message' => 'منبع با موفقیت افزوده شد',
            'data'    => $resource
        ];
    }

    public function editResource(ResourceEditRequest $request, $resource_id)
    {
        $resource = Resource::where('id', $resource_id)->first();
        if(!$resource){
            throw new ErrorException('منبع مورد نظر وجود ندارد!');
        }

        $resource->fill([
            'resource_name'   => $request->resource_name,
            'resource_type'   => $request->resource_type,
        ])->save();

        return [
            'message' => 'منبع با موفقیت ویرایش شد',
            'data'    => $resource
        ];
    }

    public function deleteResource($resource_id)
    {
        $resource = Resource::where('id', $resource_id)->first();
        if(!$resource){
            throw new ErrorException('منبع مورد نظر وجود ندارد!');
        }

        $resource->delete();

        return [
            'message' => 'منبع با موفقیت حذف شد',
            'data'    => null
        ];
    }
}
