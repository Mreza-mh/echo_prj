<?php

namespace App\Services;

use App\Exceptions\ErrorException;
use App\Http\Requests\Service\ServiceCreateRequest;
use App\Http\Requests\Service\ServiceEditRequest;
use App\Http\Requests\Service\ServiceFilterRequest;
use App\Models\Service;
use App\Models\Staff;
use Illuminate\Support\Facades\Auth;

class ServiceService
{

    public function getServiceList(ServiceFilterRequest $request){
        $is_paginate = $request->filled('is_paginate') ? filter_var($request->is_paginate, FILTER_VALIDATE_BOOLEAN) : false;
        $count_item = $request->filled('count_item') ? filter_var($request->count_item, FILTER_VALIDATE_INT) : 10;

        $query = Service::query();

        if ($request->filled('title')) {
            $query->where('title', 'like', '%' . $request->title . '%');
        }

        $services = $is_paginate ? $query->paginate($count_item) : $query->get();

        return [
            'message' => 'لیست سرویس ها با موفقیت دریافت شد',
            'data'    => $services
        ];
    }

    public function getService($service_id){
        $service = Service::where('id', $service_id)->first();
        if($service == null){
            throw new ErrorException('سرویس وجود ندارد!');
        }

        return [
            'message' => 'سرویس مورد نظر با موفقیت دریافت شد',
            'data'    => $service
        ];

    }

    public function addService(ServiceCreateRequest $request){
        $service = Service::create([
            'title'          => $request->title,
            'duration' => $request->duration,
            'price'       => $request->price,
        ]);

        return [
            'message' => 'سرویس با موفقیت افزوده شد',
            'data'    => $service
        ];
    }

    public function editService(ServiceEditRequest $request, $service_id){
        $service = Service::where('id', $service_id)->first();
        if($service == null){
            throw new ErrorException('سرویس وجود ندارد!');
        }
        $service->fill(
            $request->only([
                'title',
                'duration',
                'price'
            ])
        );
        $service->save();

        return [
            'message' => 'سرویس با موفقیت ویرایش شد',
            'data'    => $service
        ];
    }

    public function deleteService($service_id){
        $service = Service::where('id', $service_id)->first();
        if($service == null){
            throw new ErrorException('سرویس وجود ندارد!');
        }
        $service->delete();

        return [
            'message' => 'سرویس با موفقیت حذف شد',
            'data'    => null
        ];
    }
}
