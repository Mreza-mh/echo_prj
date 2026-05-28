<?php

namespace App\Http\Controllers;

use App\Http\Requests\Service\ServiceFilterRequest;
use App\Http\Requests\Service\ServiceCreateRequest;
use App\Http\Requests\Service\ServiceEditRequest;
use App\Http\Responses\ApiResponse;
use App\Services\ServiceService;

class ServiceController
{
    protected ServiceService $serviceService;

    public function __construct(ServiceService $serviceService)
    {
        $this->serviceService = $serviceService;
    }

    /**
     * @OA\Post(
     *     path="/service/list",
     *     tags={"Service"},
     *     summary="دریافت لیست سرویس‌ها",
     *     @OA\RequestBody(
     *         required=false,
     *         @OA\JsonContent(
     *             @OA\Property(property="is_paginate", type="boolean", example=true),
     *             @OA\Property(property="count_item", type="integer", example=10),
     *             @OA\Property(property="title", type="string", example="ویزیت عمومی")
     *         )
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="لیست سرویس‌ها بازگشت داده شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="لیست سرویس ها با موفقیت دریافت شد"),
     *             @OA\Property(property="data", type="array", @OA\Items(type="object"))
     *         )
     *     )
     * )
     */
    public function getServiceList(ServiceFilterRequest $request)
    {
        $result = $this->serviceService->getServiceList($request);
        return ApiResponse::success($result['data'], $result['message']);
    }

    /**
     * @OA\Get(
     *     path="/service/{service_id}",
     *     tags={"Service"},
     *     summary="دریافت جزئیات یک سرویس",
     *     @OA\Parameter(
     *         name="service_id",
     *         in="path",
     *         required=true,
     *         @OA\Schema(type="integer")
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="جزئیات سرویس بازگشت داده شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="سرویس مورد نظر با موفقیت دریافت شد"),
     *             @OA\Property(property="data", type="object")
     *         )
     *     )
     * )
     */
    public function getService($service_id)
    {
        $result = $this->serviceService->getService($service_id);
        return ApiResponse::success($result['data'], $result['message']);
    }

    /**
     * @OA\Post(
     *     path="/service/add",
     *     tags={"Service"},
     *     summary="افزودن سرویس جدید",
     *     @OA\RequestBody(
     *         required=true,
     *         @OA\JsonContent(
     *             required={"title"},
     *             @OA\Property(property="title", type="string", example="ویزیت عمومی"),
     *             @OA\Property(property="duration", type="string", example="00:30:00"),
     *             @OA\Property(property="price", type="number", example=50000)
     *         )
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="سرویس با موفقیت اضافه شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="سرویس با موفقیت افزوده شد"),
     *             @OA\Property(property="data", type="object")
     *         )
     *     )
     * )
     */
    public function addService(ServiceCreateRequest $request)
    {
        $result = $this->serviceService->addService($request);
        return ApiResponse::success($result['data'], $result['message']);
    }

    /**
     * @OA\Patch(
     *     path="/service/edit/{service_id}",
     *     tags={"Service"},
     *     summary="ویرایش سرویس",
     *     @OA\Parameter(
     *         name="service_id",
     *         in="path",
     *         required=true,
     *         @OA\Schema(type="integer")
     *     ),
     *     @OA\RequestBody(
     *         required=false,
     *         @OA\JsonContent(
     *             @OA\Property(property="title", type="string", example="ویزیت تخصصی"),
     *             @OA\Property(property="duration", type="string", example="01:00:00"),
     *             @OA\Property(property="price", type="number", example=100000)
     *         )
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="سرویس با موفقیت ویرایش شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="سرویس با موفقیت ویرایش شد"),
     *             @OA\Property(property="data", type="object")
     *         )
     *     )
     * )
     */
    public function editService(ServiceEditRequest $request, $service_id)
    {
        $result = $this->serviceService->editService($request, $service_id);
        return ApiResponse::success($result['data'], $result['message']);
    }

    /**
     * @OA\Delete(
     *     path="/service/delete/{service_id}",
     *     tags={"Service"},
     *     summary="حذف سرویس",
     *     @OA\Parameter(
     *         name="service_id",
     *         in="path",
     *         required=true,
     *         @OA\Schema(type="integer")
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="سرویس با موفقیت حذف شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="سرویس با موفقیت حذف شد"),
     *             @OA\Property(property="data", type="object", example=null)
     *         )
     *     )
     * )
     */
    public function deleteService($service_id)
    {
        $result = $this->serviceService->deleteService($service_id);
        return ApiResponse::success($result['data'], $result['message']);
    }
}
